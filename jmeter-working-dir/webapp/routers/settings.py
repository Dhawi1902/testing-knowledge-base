import json
import platform
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates


def _check_access(request: Request):
    """Return 403 JSONResponse if viewer, None if allowed."""
    if getattr(request.state, "access_level", "viewer") == "viewer":
        return JSONResponse(status_code=403, content={"error": "Access denied — token required"})
    return None

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
APP_DIR = Path(__file__).resolve().parent.parent
SETTINGS_FILE = APP_DIR / "settings.json"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()

DEFAULT_SETTINGS = {
    "theme": "light",
    "sidebar_collapsed": False,
    "server": {
        "domain": "",
        "host": "127.0.0.1",
        "port": 8080,
        "allow_external": False,
        "base_path": "",
    },
    "runner": {
        "auto_scroll": True,
        "max_log_lines": 1000,
        "confirm_before_stop": True,
    },
    "results": {
        "sort_order": "newest",
    },
    "analysis": {
        "ollama_url": "http://localhost:11434",
        "ollama_model": "llama3.1:8b",
        "ollama_timeout": 120,
    },
    "auth": {
        "token": "",
        "cookie_name": "jmeter_token",
        "cookie_max_age": 86400,
    },
    "monitoring": {
        "grafana_url": "",
        "influxdb_url": "",
    },
}


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            # Merge with defaults for any missing keys
            merged = {**DEFAULT_SETTINGS}
            for key, val in data.items():
                if isinstance(val, dict) and isinstance(merged.get(key), dict):
                    merged[key] = {**merged[key], **val}
                elif isinstance(val, list):
                    merged[key] = val
                else:
                    merged[key] = val
            return merged
        except Exception:
            pass
    return {**DEFAULT_SETTINGS}


def save_settings(settings: dict):
    SETTINGS_FILE.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


@router.get("/settings")
async def settings_page(request: Request):
    project = request.app.state.project
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "project_name": project.get("name", "JMeter Dashboard"),
        "active_page": "settings",
    })


@router.get("/api/settings")
async def api_get_settings():
    return {"settings": load_settings()}


@router.put("/api/settings")
async def api_save_settings(request: Request):
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()
    settings = body.get("settings", {})
    save_settings(settings)
    return {"ok": True}


def _run_cmd(cmd: list[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return (r.stdout.strip() or r.stderr.strip())
    except Exception:
        return "N/A"


@router.get("/api/settings/system-info")
async def api_system_info():
    # JMeter version
    jmeter_version = _run_cmd(["jmeter", "--version"])
    # Extract just the version line if verbose output
    for line in jmeter_version.splitlines():
        if "apache jmeter" in line.lower() or line.strip().startswith("5.") or line.strip().startswith("4."):
            jmeter_version = line.strip()
            break

    # Java version
    java_out = _run_cmd(["java", "-version"])
    java_version = java_out.splitlines()[0] if java_out != "N/A" else "N/A"

    # Python version
    python_version = platform.python_version()

    # Disk space
    usage = shutil.disk_usage(str(APP_DIR))
    disk = {
        "total_gb": round(usage.total / (1024**3), 1),
        "used_gb": round(usage.used / (1024**3), 1),
        "free_gb": round(usage.free / (1024**3), 1),
        "percent": round(usage.used / usage.total * 100, 1),
    }

    # OS
    os_info = f"{platform.system()} {platform.release()}"

    return {
        "jmeter": jmeter_version,
        "java": java_version,
        "python": python_version,
        "os": os_info,
        "disk": disk,
    }
