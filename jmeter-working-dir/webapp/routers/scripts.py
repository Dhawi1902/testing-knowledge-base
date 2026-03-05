from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from services.config_parser import get_project_root
from services.process_manager import script_process_manager
from services.templates import templates

router = APIRouter()

_LOCALHOST_DENIED = JSONResponse(status_code=403, content={"error": "Scripts are only available from localhost"})


def _check_localhost(request: Request):
    if not getattr(request.state, "is_localhost", False):
        return _LOCALHOST_DENIED
    return None


@router.get("/scripts")
async def scripts_page(request: Request):
    denied = _check_localhost(request)
    if denied:
        return denied
    project = request.app.state.project
    return templates.TemplateResponse("scripts.html", {
        "request": request,
        "project_name": project.get("name", "JMeter Dashboard"),
        "active_page": "scripts",
    })


@router.get("/api/scripts/list")
async def api_list_scripts(request: Request):
    denied = _check_localhost(request)
    if denied:
        return denied
    project = request.app.state.project
    project_root = get_project_root(project)
    scripts_dirs = project["paths"].get("scripts_dirs", [])

    scripts = []
    for dir_name in scripts_dirs:
        dir_path = project_root / dir_name
        if not dir_path.is_dir():
            continue
        for ext in ["*.py", "*.bat", "*.sh"]:
            for f in sorted(dir_path.rglob(ext)):
                rel = str(f.relative_to(project_root)).replace("\\", "/")
                scripts.append({
                    "name": f.name,
                    "path": rel,
                    "directory": dir_name,
                    "type": f.suffix,
                    "size": f.stat().st_size,
                })
    return {"scripts": scripts}


@router.post("/api/scripts/run")
async def api_run_script(request: Request):
    denied = _check_localhost(request)
    if denied:
        return denied
    body = await request.json()
    script_path = body.get("path", "")
    project = request.app.state.project
    project_root = get_project_root(project)

    # Security: resolve and check it's within project
    full_path = (project_root / script_path).resolve()
    if not str(full_path).startswith(str(project_root.resolve())):
        return JSONResponse(status_code=403, content={"error": "Access denied"})
    if not full_path.exists():
        return JSONResponse(status_code=404, content={"error": "Script not found"})

    if script_process_manager.is_running:
        return JSONResponse(status_code=409, content={"error": "A script is already running"})

    if full_path.suffix == ".py":
        cmd = ["python", str(full_path)]
    elif full_path.suffix == ".bat":
        cmd = ["cmd", "/c", str(full_path)]
    elif full_path.suffix == ".sh":
        cmd = ["bash", str(full_path)]
    else:
        return JSONResponse(status_code=400, content={"error": "Unsupported script type"})

    script_process_manager.start(cmd, cwd=project_root, label=full_path.name)
    return {"ok": True, "label": full_path.name}


@router.post("/api/scripts/stop")
async def api_stop_script(request: Request):
    denied = _check_localhost(request)
    if denied:
        return denied
    script_process_manager.stop()
    return {"ok": True}


@router.get("/api/scripts/status")
async def api_script_status(request: Request):
    denied = _check_localhost(request)
    if denied:
        return denied
    return {
        "running": script_process_manager.is_running,
        "label": script_process_manager.active_label,
    }


@router.websocket("/ws/scripts/output")
async def ws_script_output(websocket: WebSocket):
    await websocket.accept()
    if not getattr(websocket.state, "is_localhost", True):
        await websocket.send_text("[Access denied: localhost only]")
        await websocket.close()
        return
    try:
        if not script_process_manager.is_running:
            await websocket.send_text("[No active script]")
            await websocket.close()
            return
        async for line in script_process_manager.stream_output():
            await websocket.send_text(line)
        rc = script_process_manager.return_code()
        await websocket.send_text(f"\n[Script exited with code {rc}]")
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
