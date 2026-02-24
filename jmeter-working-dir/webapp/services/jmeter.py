import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from services.config_parser import (
    get_project_root,
    resolve_path,
    read_config_properties,
    get_active_slaves,
)

APP_DIR = Path(__file__).resolve().parent.parent
RESERVED_KEYS = {"test_plan", "results_dir", "filter_usernames", "filter_label_pattern"}

# JMeter report properties to reduce report size
# (forces CSV format for regeneration, disables heavy over-time graphs that bloat graph.js)
REPORT_OPTIMIZE_PROPS = [
    "-Jjmeter.save.saveservice.output_format=csv",
    "-Jjmeter.reportgenerator.graph.responseTimeOverTime.enabled=false",
    "-Jjmeter.reportgenerator.graph.latenciesOverTime.enabled=false",
    "-Jjmeter.reportgenerator.graph.bytesThroughputOverTime.enabled=false",
    "-Jjmeter.reportgenerator.graph.connectTimeOverTime.enabled=false",
]


def list_jmx_files(project_config: dict) -> list[dict]:
    """Find all .jmx files in the configured JMX directory."""
    jmx_dir = resolve_path(project_config, "jmx_dir")
    if not jmx_dir.is_dir():
        return []
    files = []
    for f in sorted(jmx_dir.glob("*.jmx")):
        stat = f.stat()
        files.append({
            "filename": f.name,
            "path": str(f),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return files


def extract_jmx_params(jmx_path: str | Path) -> list[dict]:
    """Parse JMX XML and extract __P() and __property() parameter references."""
    jmx_path = Path(jmx_path)
    if not jmx_path.exists():
        return []
    content = jmx_path.read_text(encoding="utf-8", errors="replace")
    params = {}
    # Match __P(name,default) and __P(name)
    for m in re.finditer(r'\$\{__(?:P|property)\(([^,)]+)(?:,([^)]*))?\)\}', content):
        name = m.group(1).strip()
        default = m.group(2).strip() if m.group(2) else ""
        if name not in params:
            params[name] = default
    return [{"name": k, "default": v} for k, v in params.items()]


def open_in_jmeter(jmeter_path: str, jmx_path: str) -> bool:
    """Launch JMeter GUI with a test plan (non-blocking)."""
    if not jmeter_path or not Path(jmeter_path).exists():
        return False
    try:
        subprocess.Popen(
            [jmeter_path, "-t", jmx_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        return True
    except OSError:
        return False


def build_jmeter_command(
    project_config: dict,
    jmx_filename: str,
    overrides: dict | None = None,
    filter_usernames: bool = False,
    filter_label_pattern: str = "",
    dry_run: bool = False,
) -> tuple[list[str], str, list[list[str]]]:
    """
    Build the JMeter CLI command from config.properties.

    Convention:
    - 'test_plan' is reserved -> maps to -t
    - Only params detected in the JMX script (__P() refs) -> -G{key}={value}

    Returns (cmd_list, result_dir_path, post_commands).
    post_commands is a list of subprocess commands to run after JMeter finishes.

    If dry_run=True, no directories are created and no snapshots are saved.
    Used by get_command_preview() to avoid side effects.
    """
    jmeter_path = project_config.get("jmeter_path", "jmeter")
    project_root = get_project_root(project_config)
    props_path = resolve_path(project_config, "config_properties")
    props = read_config_properties(props_path)

    # Resolve test plan
    if jmx_filename:
        jmx_dir = resolve_path(project_config, "jmx_dir")
        test_plan_path = str(jmx_dir / jmx_filename)
    else:
        test_plan_rel = props.get("test_plan", "")
        test_plan_path = str(project_root / test_plan_rel)

    # Detect which params the script actually uses
    script_params = {p["name"] for p in extract_jmx_params(test_plan_path)}

    # Build effective values: script defaults from config.properties, overridden by UI values
    effective = {}
    for name in script_params:
        if name in props:
            effective[name] = props[name]
    if overrides:
        for name, value in overrides.items():
            if name in script_params:
                effective[name] = value

    # Determine result directory path
    results_dir = resolve_path(project_config, "results_dir")
    today = datetime.now().strftime("%Y%m%d")
    date_group_dir = results_dir / today

    if dry_run:
        # Estimate next folder number without creating anything
        if date_group_dir.is_dir():
            existing = [d.name for d in date_group_dir.iterdir() if d.is_dir() and d.name.startswith(today)]
            n = len(existing) + 1
        else:
            n = 1
    else:
        date_group_dir.mkdir(parents=True, exist_ok=True)
        existing = [d.name for d in date_group_dir.iterdir() if d.is_dir() and d.name.startswith(today)]
        n = len(existing) + 1

    result_folder = f"{today}_{n}"
    result_dir = date_group_dir / result_folder
    jtl_path = str(result_dir / "results.jtl")
    report_dir = str(result_dir / "report")

    if not dry_run:
        result_dir.mkdir(parents=True, exist_ok=True)

    # Add slaves (enabled only)
    slaves_path = project_root / project_config["paths"].get("slaves_file", "slaves.txt")
    slaves = get_active_slaves(slaves_path)

    # Build command
    cmd = [jmeter_path, "-n", "-t", test_plan_path]
    if slaves:
        cmd.extend(["-R", ",".join(slaves)])

    # Add -G flags only for parameters used by the script
    for key, value in effective.items():
        cmd.append(f"-G{key}={value}")

    # JTL output
    cmd.extend(["-l", jtl_path])

    # Post-commands for report generation
    post_commands: list[list[str]] = []
    if filter_usernames:
        # Don't generate report inline — filter JTL first, then generate
        filtered_jtl = str(result_dir / "filtered.jtl")
        filter_cmd = [sys.executable, str(APP_DIR / "jtl_filter.py"), jtl_path, filtered_jtl]
        if filter_label_pattern:
            filter_cmd.append(filter_label_pattern)
        post_commands.append(filter_cmd)
        post_commands.append([jmeter_path, "-g", filtered_jtl, "-o", report_dir] + REPORT_OPTIMIZE_PROPS)
    else:
        # Generate report inline with JMeter
        cmd.extend(["-e", "-o", report_dir] + REPORT_OPTIMIZE_PROPS)

    # Save config snapshot and run info (only on real runs)
    if not dry_run:
        _save_run_snapshot(result_dir, props_path, jmx_filename, effective, slaves, filter_usernames)

    return cmd, str(result_dir), post_commands


def _save_run_snapshot(
    result_dir: Path,
    props_path: Path,
    jmx_filename: str,
    overrides: dict,
    slaves: list[str],
    filter_usernames: bool,
):
    """Save config.properties copy and run_info.json to the result directory."""
    # Copy config.properties
    if props_path.exists():
        shutil.copy2(str(props_path), str(result_dir / "config.properties"))

    # Write run info
    run_info = {
        "timestamp": datetime.now().isoformat(),
        "test_plan": jmx_filename,
        "overrides": overrides,
        "slaves": slaves,
        "mode": "distributed" if slaves else "local",
        "filter_usernames": filter_usernames,
    }
    (result_dir / "run_info.json").write_text(
        json.dumps(run_info, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def get_command_preview(project_config: dict, jmx_filename: str, overrides: dict | None = None) -> str:
    """Return the command as a string for preview in the UI (no side effects)."""
    cmd, _result_dir, _post = build_jmeter_command(project_config, jmx_filename, overrides, dry_run=True)
    return " ".join(cmd)
