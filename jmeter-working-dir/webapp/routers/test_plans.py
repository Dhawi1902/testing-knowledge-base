import json
import time
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from services.jmeter import (
    list_jmx_files,
    extract_jmx_params,
    open_in_jmeter,
    build_jmeter_command,
    get_command_preview,
)
from services.config_parser import get_project_root, resolve_path, read_config_properties
from services.process_manager import jmeter_process_manager

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
PRESETS_FILE = Path(__file__).resolve().parent.parent / "presets.json"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


def _check_access(request: Request):
    """Return 403 JSONResponse if viewer, None if allowed."""
    if getattr(request.state, "access_level", "viewer") == "viewer":
        return JSONResponse(status_code=403, content={"error": "Access denied — token required"})
    return None


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
    if not getattr(request.state, "is_localhost", False):
        return JSONResponse(status_code=403, content={"error": "Edit is only available from localhost"})
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
    denied = _check_access(request)
    if denied:
        return denied
    if jmeter_process_manager.is_running:
        return JSONResponse(status_code=409, content={"error": "A test is already running"})
    body = await request.json()
    project = request.app.state.project
    filename = body.get("filename", "")
    overrides = body.get("overrides", {})
    filter_usernames = body.get("filter_usernames", False)
    filter_label_pattern = body.get("filter_label_pattern", "")
    cmd, result_dir, post_commands = build_jmeter_command(
        project, filename, overrides,
        filter_usernames=filter_usernames,
        filter_label_pattern=filter_label_pattern,
    )
    project_root = get_project_root(project)
    run_info = {
        "filename": filename,
        "overrides": overrides,
        "command": " ".join(cmd),
        "result_dir": result_dir,
        "filter_usernames": filter_usernames,
        "filter_label_pattern": filter_label_pattern,
        "started_at": time.time(),
    }
    jmeter_process_manager.start(cmd, cwd=project_root, label=filename,
                                 post_commands=post_commands, run_info=run_info)
    return {"ok": True, "result_dir": result_dir, "command": " ".join(cmd)}


@router.post("/api/runner/stop")
async def api_stop_test(request: Request):
    denied = _check_access(request)
    if denied:
        return denied
    jmeter_process_manager.stop()
    return {"ok": True}


@router.get("/api/runner/status")
async def api_runner_status():
    return {
        "running": jmeter_process_manager.is_running,
        "label": jmeter_process_manager.active_label,
        "run_info": jmeter_process_manager.run_info,
    }


@router.get("/api/runner/buffer")
async def api_runner_buffer():
    """Returns all buffered output lines from the current/last run."""
    return {
        "lines": jmeter_process_manager.output_buffer,
        "running": jmeter_process_manager.is_running,
        "draining": jmeter_process_manager.is_draining,
    }


@router.websocket("/ws/runner/logs")
async def ws_runner_logs(websocket: WebSocket):
    await websocket.accept()
    try:
        start_index = int(websocket.query_params.get("from", "0"))
        if not jmeter_process_manager.is_running and not jmeter_process_manager.is_draining:
            await websocket.send_text("[No active test]")
            await websocket.close()
            return
        async for line in jmeter_process_manager.subscribe_output(start_index):
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


@router.get("/api/runner/filter-config")
async def api_filter_config(request: Request):
    """Return the default filter settings from config.properties."""
    project = request.app.state.project
    props_path = resolve_path(project, "config_properties")
    props = read_config_properties(props_path)
    return {
        "filter_usernames": props.get("filter_usernames", "false").lower() == "true",
        "filter_label_pattern": props.get("filter_label_pattern", ""),
    }


# --- Presets ---

@router.get("/api/runner/presets")
async def api_list_presets():
    return {"presets": _load_presets()}


@router.post("/api/runner/presets")
async def api_save_preset(request: Request):
    denied = _check_access(request)
    if denied:
        return denied
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
async def api_delete_preset(request: Request, name: str):
    denied = _check_access(request)
    if denied:
        return denied
    presets = _load_presets()
    presets.pop(name, None)
    _save_presets(presets)
    return {"ok": True}


# --- Upload / Download ---

@router.get("/api/plans/{filename}/download")
async def api_download_plan(request: Request, filename: str):
    project = request.app.state.project
    jmx_dir = resolve_path(project, "jmx_dir")
    jmx_path = jmx_dir / filename
    if not jmx_path.exists() or not jmx_path.suffix == ".jmx":
        return JSONResponse(status_code=404, content={"error": "File not found"})
    return FileResponse(jmx_path, filename=filename, media_type="application/xml")


@router.post("/api/plans/upload")
async def api_upload_plan(request: Request, file: UploadFile):
    denied = _check_access(request)
    if denied:
        return denied
    if not file.filename or not file.filename.endswith(".jmx"):
        return JSONResponse(status_code=400, content={"error": "Only .jmx files are allowed"})
    project = request.app.state.project
    jmx_dir = resolve_path(project, "jmx_dir")
    jmx_dir.mkdir(parents=True, exist_ok=True)
    dest = jmx_dir / file.filename
    if dest.exists():
        return JSONResponse(status_code=409, content={"error": f"{file.filename} already exists"})
    content = await file.read()
    dest.write_bytes(content)
    return {"ok": True, "filename": file.filename}
