import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from services.config_parser import (
    get_project_root,
    resolve_path,
    read_config_properties,
    get_active_slaves,
)
from services.jmx_patcher import patch_jmx, extract_csv_data_set_configs
from services.report_properties import get_properties_args
from services.settings import atomic_write_json

APP_DIR = Path(__file__).resolve().parent.parent

# Force CSV format for report regeneration from JTL files
CSV_FORMAT_PROP = "-Jjmeter.save.saveservice.output_format=csv"


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


def open_in_jmeter(jmeter_path: str, jmx_path: str, cwd: str | None = None) -> bool:
    """Launch JMeter GUI with a test plan (non-blocking)."""
    if not jmeter_path:
        return False
    # Accept both full path and bare command name (e.g. "jmeter" on PATH)
    if not shutil.which(jmeter_path) and not Path(jmeter_path).exists():
        return False
    try:
        subprocess.Popen(
            [jmeter_path, "-t", jmx_path],
            cwd=cwd,
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
    filter_sub_results: bool = False,
    label_pattern: str = "",
    dry_run: bool = False,
    backend_patches: dict | None = None,
) -> tuple[list[str], str, list[list[str]]]:
    """
    Build the JMeter CLI command.

    Convention:
    - 'test_plan' is reserved -> maps to -t
    - Only params detected in the JMX script (__P() refs) -> -G{key}={value}
    - Parameter defaults come from __P(name,default) in the JMX, not config.properties
    - UI overrides are passed directly

    Returns (cmd_list, result_dir_path, post_commands).
    post_commands is a list of subprocess commands to run after JMeter finishes.

    If dry_run=True, no directories are created and no snapshots are saved.
    Used by get_command_preview() to avoid side effects.

    backend_patches: dict of Backend Listener property overrides (e.g. runId, influxdbUrl).
    If provided, a patched copy of the JMX is written to the result dir and used instead.
    """
    jmeter_path = project_config.get("jmeter_path", "jmeter")
    project_root = get_project_root(project_config)

    # Resolve test plan
    if jmx_filename:
        jmx_dir = resolve_path(project_config, "jmx_dir")
        test_plan_path = str(jmx_dir / jmx_filename)
    else:
        # Legacy fallback: read test_plan from config.properties
        props_path = resolve_path(project_config, "config_properties")
        props = read_config_properties(props_path)
        test_plan_rel = props.get("test_plan", "")
        test_plan_path = str(project_root / test_plan_rel)

    # Detect which params the script actually uses
    script_params = {p["name"] for p in extract_jmx_params(test_plan_path)}

    # Build effective values: only UI overrides for script-detected params
    effective = {}
    if overrides:
        for name, value in overrides.items():
            if name in script_params:
                effective[name] = value

    # Determine result directory path
    results_dir = resolve_path(project_config, "results_dir")
    today = datetime.now().strftime("%Y%m%d")
    date_group_dir = results_dir / today

    def _next_run_number(group_dir: Path, prefix: str) -> int:
        """Find the next run number based on highest existing number, not count."""
        max_n = 0
        if group_dir.is_dir():
            for d in group_dir.iterdir():
                if d.is_dir() and d.name.startswith(prefix + "_"):
                    try:
                        num = int(d.name.split("_", 1)[1])
                        max_n = max(max_n, num)
                    except (ValueError, IndexError):
                        pass
        return max_n + 1

    if dry_run:
        n = _next_run_number(date_group_dir, today)
    else:
        date_group_dir.mkdir(parents=True, exist_ok=True)
        n = _next_run_number(date_group_dir, today)

    result_folder = f"{today}_{n}"
    result_dir = date_group_dir / result_folder
    jtl_path = str(result_dir / "results.jtl")
    report_dir = str(result_dir / "report")

    if not dry_run:
        result_dir.mkdir(parents=True, exist_ok=True)

        # Patch JMX for Backend Listener if patches provided
        if backend_patches:
            # Auto-inject runId from result folder name if not explicitly set
            if "runId" not in backend_patches:
                backend_patches["runId"] = result_folder
            patched_jmx = result_dir / f"patched_{Path(test_plan_path).name}"
            patch_jmx(Path(test_plan_path), backend_patches, patched_jmx)
            if patched_jmx.exists():
                test_plan_path = str(patched_jmx)

    # Add slaves (enabled only)
    slaves_path = project_root / project_config["paths"].get("slaves_file", "slaves.txt")
    slaves = get_active_slaves(slaves_path)

    # Build command
    cmd = [jmeter_path, "-n", "-t", test_plan_path]
    if slaves:
        cmd.extend(["-R", ",".join(slaves)])
        # Disable RMI SSL for distributed testing (matches slave-side config)
        cmd.append("-Jserver.rmi.ssl.disable=true")

    # Add -G flags only for parameters used by the script
    for key, value in effective.items():
        cmd.append(f"-G{key}={value}")

    # JTL output
    cmd.extend(["-l", jtl_path])

    # Post-commands for report generation
    post_commands: list[list[str]] = []
    if filter_sub_results:
        # Don't generate report inline — filter JTL first, then generate
        filtered_jtl = str(result_dir / "filtered.jtl")
        filter_cmd = [sys.executable, str(APP_DIR / "jtl_filter.py"), jtl_path, filtered_jtl]
        if label_pattern:
            filter_cmd.append(label_pattern)
        post_commands.append(filter_cmd)
        post_commands.append(build_report_command(jmeter_path, filtered_jtl, report_dir))
    else:
        # Generate report inline with JMeter
        cmd.extend(["-e", "-o", report_dir, CSV_FORMAT_PROP] + get_properties_args())

    # Save config snapshot and run info (only on real runs)
    if not dry_run:
        props_path = resolve_path(project_config, "config_properties")
        _save_run_snapshot(result_dir, props_path, jmx_filename, test_plan_path,
                          effective, slaves, filter_sub_results, label_pattern,
                          backend_patches=backend_patches)

    return cmd, str(result_dir), post_commands


def _save_run_snapshot(
    result_dir: Path,
    props_path: Path,
    jmx_filename: str,
    jmx_path: Path | str,
    overrides: dict,
    slaves: list[str],
    filter_sub_results: bool,
    label_pattern: str = "",
    backend_patches: dict | None = None,
):
    """Save config.properties copy and run_summary.json (pre-run) to result dir.

    run_summary.json is the single source of truth for run metadata + stats.
    Pre-run phase writes metadata; stats are appended lazily on first access.
    Also writes run_info.json for backward compatibility.
    """
    # Copy config.properties
    if props_path.exists():
        shutil.copy2(str(props_path), str(result_dir / "config.properties"))

    now = datetime.now()
    run_meta = {
        "timestamp": now.isoformat(),
        "test_plan": jmx_filename,
        "overrides": overrides,
        "slaves": slaves,
        "mode": "distributed" if slaves else "local",
        "filter_sub_results": filter_sub_results,
        "label_pattern": label_pattern,
    }

    if backend_patches:
        run_meta["backend_patches"] = backend_patches

    # Scan JMX for CSV Data Set Config — record test data files
    jmx_file = Path(jmx_path)
    if jmx_file.exists():
        csv_configs = extract_csv_data_set_configs(jmx_file)
        if csv_configs:
            test_data = []
            for cfg in csv_configs:
                filename = cfg.get("filename", "")
                entry = {"filename": filename, "variables": cfg.get("variableNames", "")}
                # Try to get file stats (row count, size)
                if filename:
                    csv_path = jmx_file.parent / filename
                    if not csv_path.exists():
                        # Try relative to project root
                        csv_path = result_dir.parent.parent.parent / filename
                    if csv_path.exists():
                        try:
                            entry["size"] = csv_path.stat().st_size
                            # Count lines (fast — no full parse)
                            with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
                                entry["rows"] = sum(1 for _ in f)
                        except OSError:
                            pass
                test_data.append(entry)
            run_meta["test_data"] = test_data

    # Write run_summary.json (pre-run phase — stats added lazily later)
    summary = {
        "version": 1,
        "phase": "pre-run",
        **run_meta,
    }
    atomic_write_json(result_dir / "run_summary.json", summary)

    # Backward-compatible run_info.json
    atomic_write_json(result_dir / "run_info.json", run_meta)


def build_report_command(jmeter_path: str, source_jtl: str, output_dir: str) -> list[str]:
    """Build JMeter report generation command. Used by both test runs and regeneration."""
    return [jmeter_path, "-g", source_jtl, "-o", output_dir, CSV_FORMAT_PROP] + get_properties_args()


def get_command_preview(project_config: dict, jmx_filename: str, overrides: dict | None = None) -> str:
    """Return the command as a string for preview in the UI (no side effects)."""
    cmd, _result_dir, _post = build_jmeter_command(project_config, jmx_filename, overrides, dry_run=True)
    return " ".join(cmd)
