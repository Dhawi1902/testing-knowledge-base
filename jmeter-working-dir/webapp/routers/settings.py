import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

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
    "endpoints": [
        {"name": "MAYA Production", "url": "https://maya-cloud.um.edu.my/sitsvision/wrd/siw_lgn"},
        {"name": "MAYA PREP", "url": "https://printis-prep.um.edu.my/sitsvision/wrd/siw_lgn"},
        {"name": "Cloudunity Report Viewer", "url": "https://cloudunity.um.edu.my/reportcradle/reportviewer.aspx"},
    ],
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
                    merged[key] = val  # Lists replace entirely (e.g. endpoints)
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
    body = await request.json()
    settings = body.get("settings", {})
    save_settings(settings)
    return {"ok": True}
