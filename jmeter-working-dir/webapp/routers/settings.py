import json
import platform
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from services.auth import check_access as _check_access
from services import report_properties

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
    settings = load_settings()
    # Redact token — never expose the hash to clients
    auth = settings.get("auth", {})
    auth["token_set"] = bool(auth.get("token", ""))
    auth.pop("token", None)
    settings["auth"] = auth
    return {"settings": settings}


def _validate_settings(settings: dict) -> str | None:
    """Return error message if settings are invalid, else None."""
    server = settings.get("server", {})
    port = server.get("port")
    if port is not None:
        try:
            port = int(port)
            if not (1 <= port <= 65535):
                return "Port must be between 1 and 65535"
        except (ValueError, TypeError):
            return "Port must be a number"
    for key in ("grafana_url", "influxdb_url"):
        url = settings.get("monitoring", {}).get(key, "")
        if url and not url.startswith(("http://", "https://")):
            return f"{key} must start with http:// or https://"
    analysis = settings.get("analysis", {})
    ollama_url = analysis.get("ollama_url", "")
    if ollama_url and not ollama_url.startswith(("http://", "https://")):
        return "Ollama URL must start with http:// or https://"
    timeout = analysis.get("ollama_timeout")
    if timeout is not None:
        try:
            timeout = int(timeout)
            if timeout < 1:
                return "Ollama timeout must be positive"
        except (ValueError, TypeError):
            return "Ollama timeout must be a number"
    return None


@router.put("/api/settings")
async def api_save_settings(request: Request):
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()
    settings = body.get("settings", {})

    # Validate
    error = _validate_settings(settings)
    if error:
        return JSONResponse(status_code=400, content={"error": error})

    # Handle token: hash if new token provided, preserve existing hash if empty
    auth = settings.get("auth", {})
    submitted_token = auth.get("token", "")
    if submitted_token:
        from services.auth import hash_token
        auth["token"] = hash_token(submitted_token)
    elif auth.get("clear_token"):
        auth["token"] = ""
        auth.pop("clear_token", None)
    else:
        # Empty token submitted — preserve existing stored hash
        existing = load_settings()
        auth["token"] = existing.get("auth", {}).get("token", "")
    settings["auth"] = auth

    save_settings(settings)
    return {"ok": True}


@router.get("/api/settings/export")
async def api_export_settings(request: Request):
    """Export settings as a downloadable JSON file."""
    denied = _check_access(request)
    if denied:
        return denied
    settings = load_settings()
    # Redact auth token for security
    settings.get("auth", {}).pop("token", None)
    return JSONResponse(content=settings, headers={
        "Content-Disposition": "attachment; filename=settings_export.json"
    })


@router.post("/api/settings/import")
async def api_import_settings(request: Request):
    """Import settings from a JSON body."""
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()
    imported = body.get("settings", body)
    error = _validate_settings(imported)
    if error:
        return JSONResponse(status_code=400, content={"error": error})
    # Preserve existing auth token (don't allow import to overwrite)
    existing = load_settings()
    imported.setdefault("auth", {})
    imported["auth"]["token"] = existing.get("auth", {}).get("token", "")
    save_settings(imported)
    return {"ok": True}


def _run_cmd(cmd: list[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return (r.stdout.strip() or r.stderr.strip())
    except Exception:
        return "N/A"


@router.get("/api/settings/system-info")
async def api_system_info(request: Request):
    denied = _check_access(request)
    if denied:
        return denied
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


# --- Report Properties (graph toggles + granularity) ---

@router.get("/api/settings/report")
async def api_get_report_settings():
    """Return current report generation settings (graph states + granularity)."""
    settings = report_properties.load()
    graphs = report_properties.graph_metadata()
    return {"settings": settings, "graphs": graphs}


@router.put("/api/settings/report")
async def api_save_report_settings(request: Request):
    """Save report generation settings and regenerate properties file."""
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()
    settings = body.get("settings", {})
    report_properties.save(settings)
    return {"ok": True}
