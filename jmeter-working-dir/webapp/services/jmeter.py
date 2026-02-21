import os
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from services.config_parser import (
    get_project_root,
    resolve_path,
    read_config_properties,
    read_slaves_file,
)


RESERVED_KEYS = {"test_plan"}


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


def build_jmeter_command(project_config: dict, jmx_filename: str, overrides: dict | None = None) -> tuple[list[str], str]:
    """
    Build the JMeter CLI command from config.properties.

    Convention:
    - 'test_plan' is reserved → maps to -t
    - All other keys → -G{key}={value}

    Returns (cmd_list, result_dir_path).
    """
    jmeter_path = project_config.get("jmeter_path", "jmeter")
    project_root = get_project_root(project_config)
    props_path = resolve_path(project_config, "config_properties")
    props = read_config_properties(props_path)

    # Apply overrides from runner UI
    if overrides:
        props.update(overrides)

    # Resolve test plan
    if jmx_filename:
        jmx_dir = resolve_path(project_config, "jmx_dir")
        test_plan_path = str(jmx_dir / jmx_filename)
    else:
        test_plan_rel = props.get("test_plan", "")
        test_plan_path = str(project_root / test_plan_rel)

    # Create result directory under date-group folder
    results_dir = resolve_path(project_config, "results_dir")
    today = datetime.now().strftime("%Y%m%d")
    date_group_dir = results_dir / today
    date_group_dir.mkdir(parents=True, exist_ok=True)
    # Find next folder number for today
    existing = [d.name for d in date_group_dir.iterdir() if d.is_dir() and d.name.startswith(today)]
    n = len(existing) + 1
    result_folder = f"{today}_{n}"
    result_dir = date_group_dir / result_folder
    result_dir.mkdir(parents=True, exist_ok=True)
    jtl_path = str(result_dir / "results.jtl")
    report_dir = str(result_dir / "report")

    # Build command
    cmd = [jmeter_path, "-n", "-t", test_plan_path]

    # Add slaves
    slaves_path = project_root / project_config["paths"].get("slaves_file", "slaves.txt")
    slaves = read_slaves_file(slaves_path)
    if slaves:
        cmd.extend(["-R", ",".join(slaves)])

    # Add -G flags for all non-reserved keys
    for key, value in props.items():
        if key not in RESERVED_KEYS:
            cmd.append(f"-G{key}={value}")

    # JTL and report
    cmd.extend(["-l", jtl_path, "-e", "-o", report_dir])

    return cmd, str(result_dir)


def get_command_preview(project_config: dict, jmx_filename: str, overrides: dict | None = None) -> str:
    """Return the command as a string for preview in the UI."""
    cmd, result_dir = build_jmeter_command(project_config, jmx_filename, overrides)
    return " ".join(cmd)
