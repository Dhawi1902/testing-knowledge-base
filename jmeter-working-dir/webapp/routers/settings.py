import json
import platform
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from services.auth import check_access as _check_access
from services import report_properties
from services.settings import (
    load_settings,
    save_settings,
    validate_settings,
    DEFAULT_SETTINGS,
    APP_DIR,
)

from services.templates import templates

router = APIRouter()


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


@router.put("/api/settings")
async def api_save_settings(request: Request):
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()
    settings = body.get("settings", {})

    # Validate
    error = validate_settings(settings)
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
    """Export bundled config: settings.json + project.json + report settings."""
    denied = _check_access(request)
    if denied:
        return denied
    settings = load_settings()
    settings.get("auth", {}).pop("token", None)

    # Bundle project.json
    project_json_path = APP_DIR / "project.json"
    project_config = {}
    if project_json_path.exists():
        try:
            project_config = json.loads(project_json_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Bundle report settings
    report_settings = report_properties.load()

    bundle = {
        "_export_version": 1,
        "settings": settings,
        "project": project_config,
        "report": report_settings,
    }
    return JSONResponse(content=bundle, headers={
        "Content-Disposition": "attachment; filename=settings_export.json"
    })


@router.post("/api/settings/import")
async def api_import_settings(request: Request):
    """Import bundled config. Supports both v1 bundle and legacy flat settings."""
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()

    # Detect bundle format
    if body.get("_export_version") == 1:
        imported = body.get("settings", {})
        project_data = body.get("project")
        report_data = body.get("report")
    else:
        imported = body.get("settings", body)
        project_data = None
        report_data = None

    error = validate_settings(imported)
    if error:
        return JSONResponse(status_code=400, content={"error": error})

    # Preserve existing auth token
    existing = load_settings()
    imported.setdefault("auth", {})
    imported["auth"]["token"] = existing.get("auth", {}).get("token", "")
    save_settings(imported)

    # Restore project.json if present
    if project_data:
        project_json_path = APP_DIR / "project.json"
        project_json_path.write_text(json.dumps(project_data, indent=2), encoding="utf-8")

    # Restore report settings if present
    if report_data:
        report_properties.save(report_data)

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
    # JMeter version — read from ApacheJMeter.jar manifest (subprocess hangs on Windows .bat)
    project = request.app.state.project
    jmeter_cmd = project.get("jmeter_path", "jmeter")
    jmeter_version = "N/A"
    try:
        jmeter_bin_dir = Path(jmeter_cmd).resolve().parent
        jar_path = jmeter_bin_dir / "ApacheJMeter.jar"
        if jar_path.is_file():
            import zipfile
            with zipfile.ZipFile(jar_path) as zf:
                with zf.open("META-INF/MANIFEST.MF") as mf:
                    for line in mf.read().decode().splitlines():
                        if line.startswith("Implementation-Version:"):
                            jmeter_version = "Apache JMeter " + line.split(":", 1)[1].strip()
                            break
    except Exception:
        pass

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
