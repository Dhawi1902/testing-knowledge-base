import json
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from services.jmeter import (
    list_jmx_files,
    extract_jmx_params,
    open_in_jmeter,
    build_jmeter_command,
    get_command_preview,
)
from services.config_parser import get_project_root, resolve_path
from services.process_manager import jmeter_process_manager

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
PRESETS_FILE = Path(__file__).resolve().parent.parent / "presets.json"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


def _load_presets() -> dict:
    if PRESETS_FILE.exists():
        return json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
    return {}


def _save_presets(data: dict):
    PRESETS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


@router.get("/plans")
async def test_plans_page(request: Request):
    project = request.app.state.project
    return templates.TemplateResponse("test_plans.html", {
        "request": request,
        "project_name": project.get("name", "JMeter Dashboard"),
        "active_page": "plans",
    })


@router.get("/api/plans/list")
async def api_list_plans(request: Request):
    project = request.app.state.project
    return {"plans": list_jmx_files(project)}


@router.get("/api/plans/{filename}/params")
async def api_plan_params(request: Request, filename: str):
    project = request.app.state.project
    jmx_dir = resolve_path(project, "jmx_dir")
    jmx_path = jmx_dir / filename
    if not jmx_path.exists():
        return JSONResponse(status_code=404, content={"error": "JMX file not found"})
    params = extract_jmx_params(jmx_path)
    return {"params": params}


@router.post("/api/plans/{filename}/open")
async def api_open_plan(request: Request, filename: str):
    project = request.app.state.project
    jmx_dir = resolve_path(project, "jmx_dir")
    jmx_path = jmx_dir / filename
    jmeter_path = project.get("jmeter_path", "")
    if not jmeter_path:
        return JSONResponse(status_code=400, content={"error": "JMeter path not configured"})
    ok = open_in_jmeter(jmeter_path, str(jmx_path))
    if not ok:
        return JSONResponse(status_code=500, content={"error": "Failed to launch JMeter"})
    return {"ok": True}


@router.post("/api/runner/preview")
async def api_command_preview(request: Request):
    body = await request.json()
    project = request.app.state.project
    filename = body.get("filename", "")
    overrides = body.get("overrides", {})
    preview = get_command_preview(project, filename, overrides)
    return {"command": preview}


@router.post("/api/runner/start")
async def api_start_test(request: Request):
    if jmeter_process_manager.is_running:
        return JSONResponse(status_code=409, content={"error": "A test is already running"})
    body = await request.json()
    project = request.app.state.project
    filename = body.get("filename", "")
    overrides = body.get("overrides", {})
    cmd, result_dir = build_jmeter_command(project, filename, overrides)
    project_root = get_project_root(project)
    jmeter_process_manager.start(cmd, cwd=project_root, label=filename)
    return {"ok": True, "result_dir": result_dir, "command": " ".join(cmd)}


@router.post("/api/runner/stop")
async def api_stop_test():
    jmeter_process_manager.stop()
    return {"ok": True}


@router.get("/api/runner/status")
async def api_runner_status():
    return {
        "running": jmeter_process_manager.is_running,
        "label": jmeter_process_manager.active_label,
    }


@router.websocket("/ws/runner/logs")
async def ws_runner_logs(websocket: WebSocket):
    await websocket.accept()
    try:
        if not jmeter_process_manager.is_running:
            await websocket.send_text("[No active test]")
            await websocket.close()
            return
        async for line in jmeter_process_manager.stream_output():
            await websocket.send_text(line)
        rc = jmeter_process_manager.return_code()
        await websocket.send_text(f"\n[Process exited with code {rc}]")
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# --- Presets ---

@router.get("/api/runner/presets")
async def api_list_presets():
    return {"presets": _load_presets()}


@router.post("/api/runner/presets")
async def api_save_preset(request: Request):
    body = await request.json()
    name = body.get("name", "").strip()
    values = body.get("values", {})
    if not name:
        return JSONResponse(status_code=400, content={"error": "Preset name is required"})
    presets = _load_presets()
    presets[name] = values
    _save_presets(presets)
    return {"ok": True}


@router.delete("/api/runner/presets/{name}")
async def api_delete_preset(name: str):
    presets = _load_presets()
    presets.pop(name, None)
    _save_presets(presets)
    return {"ok": True}
