from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from services.config_parser import (
    load_project_config,
    save_project_config,
    resolve_path,
    get_project_root,
    read_config_properties,
    write_config_properties,
    read_json_config,
    write_json_config,
    read_slaves,
    write_slaves,
    get_active_slaves,
    detect_jmeter_path,
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
PROJECT_JSON = Path(__file__).resolve().parent.parent / "project.json"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


def _check_access(request: Request):
    """Return 403 JSONResponse if viewer, None if allowed."""
    if getattr(request.state, "access_level", "viewer") == "viewer":
        return JSONResponse(status_code=403, content={"error": "Access denied — token required"})
    return None


@router.get("/slaves")
async def slaves_page(request: Request):
    project = request.app.state.project
    return templates.TemplateResponse("slaves.html", {
        "request": request,
        "project_name": project.get("name", "JMeter Dashboard"),
        "active_page": "slaves",
    })


# --- config.properties ---

@router.get("/api/config/properties")
async def get_properties(request: Request):
    project = request.app.state.project
    props_path = resolve_path(project, "config_properties")
    props = read_config_properties(props_path)
    return {"path": str(props_path), "properties": props}


class PropertiesUpdate(BaseModel):
    properties: dict[str, str]


@router.put("/api/config/properties")
async def save_properties(request: Request, data: PropertiesUpdate):
    project = request.app.state.project
    props_path = resolve_path(project, "config_properties")
    write_config_properties(props_path, data.properties)
    return {"ok": True}


# --- vm_config.json ---

@router.get("/api/config/vm")
async def get_vm_config(request: Request):
    project = request.app.state.project
    config_dir = resolve_path(project, "config_dir")
    vm_path = config_dir / "vm_config.json"
    data = read_json_config(vm_path)
    return {"path": str(vm_path), "config": data}


@router.put("/api/config/vm")
async def save_vm_config(request: Request, body: dict):
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    config_dir = resolve_path(project, "config_dir")
    vm_path = config_dir / "vm_config.json"
    write_json_config(vm_path, body.get("config", body))
    return {"ok": True}


# --- slaves.txt ---

@router.get("/api/config/slaves")
async def get_slaves(request: Request):
    project = request.app.state.project
    slaves_path = get_project_root(project) / project["paths"].get("slaves_file", "slaves.txt")
    slaves = read_slaves(slaves_path)
    return {"path": str(slaves_path), "slaves": slaves}


@router.put("/api/config/slaves")
async def save_slaves(request: Request):
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()
    project = request.app.state.project
    slaves_path = get_project_root(project) / project["paths"].get("slaves_file", "slaves.txt")
    slaves = body.get("slaves", [])
    write_slaves(slaves_path, slaves)
    return {"ok": True}


# --- project.json (Settings) ---

@router.get("/api/config/project")
async def get_project_config(request: Request):
    project = request.app.state.project
    return {"config": project}


@router.put("/api/config/project")
async def save_project_config_route(request: Request, body: dict):
    denied = _check_access(request)
    if denied:
        return denied
    config_data = body.get("config", body)
    save_project_config(PROJECT_JSON, config_data)
    request.app.state.project = config_data
    return {"ok": True}


@router.post("/api/config/detect-jmeter")
async def detect_jmeter(request: Request):
    path = detect_jmeter_path()
    if path:
        return {"path": path}
    return JSONResponse(status_code=404, content={"error": "JMeter not found in PATH or common locations"})


# --- Slave Management ---

from services.slaves import check_all_slaves, start_all_servers, stop_all_servers  # noqa: E402


def _build_ssh_configs(slaves: list[dict], vm_config: dict) -> dict[str, dict]:
    """Build per-slave SSH configs by merging global defaults with per-slave overrides.
    Returns {ip: merged_ssh_config}.
    """
    global_ssh = vm_config.get("ssh_config", {})
    global_scripts = vm_config.get("jmeter_scripts", {})
    configs = {}
    for s in slaves:
        ip = s["ip"]
        overrides = s.get("overrides", {})
        merged = {**global_ssh, "jmeter_scripts": global_scripts}
        if overrides.get("user"):
            merged["user"] = overrides["user"]
        if overrides.get("password"):
            merged["password"] = overrides["password"]
        if overrides.get("dest_path"):
            merged["dest_path"] = overrides["dest_path"]
        configs[ip] = merged
    return configs


@router.get("/api/slaves/status")
async def api_slave_status(request: Request):
    project = request.app.state.project
    project_root = get_project_root(project)
    slaves_path = project_root / project["paths"].get("slaves_file", "slaves.txt")
    slaves = read_slaves(slaves_path)
    if not slaves:
        return {"slaves": []}
    active_ips = [s["ip"] for s in slaves if s.get("enabled", True)]
    if not active_ips:
        return {"slaves": [{"ip": s["ip"], "status": "disabled", "enabled": s.get("enabled", True)} for s in slaves]}
    config_dir = resolve_path(project, "config_dir")
    vm_config = read_json_config(config_dir / "vm_config.json")
    ssh_configs = _build_ssh_configs(slaves, vm_config)
    results = await check_all_slaves(active_ips, ssh_configs)
    # Merge enabled flag and include disabled slaves
    result_map = {r["ip"]: r for r in results}
    merged = []
    for s in slaves:
        if s.get("enabled", True) and s["ip"] in result_map:
            entry = result_map[s["ip"]]
            entry["enabled"] = True
            merged.append(entry)
        else:
            merged.append({"ip": s["ip"], "status": "disabled", "enabled": s.get("enabled", True)})
    return {"slaves": merged}


@router.post("/api/slaves/start")
async def api_start_servers(request: Request):
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    project_root = get_project_root(project)
    slaves_path = project_root / project["paths"].get("slaves_file", "slaves.txt")
    slaves = read_slaves(slaves_path)
    ips = [s["ip"] for s in slaves if s.get("enabled", True)]
    if not ips:
        return {"results": []}
    config_dir = resolve_path(project, "config_dir")
    vm_config = read_json_config(config_dir / "vm_config.json")
    ssh_configs = _build_ssh_configs(slaves, vm_config)
    results = await start_all_servers(ips, ssh_configs)
    return {"results": results}


@router.post("/api/slaves/stop")
async def api_stop_servers(request: Request):
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    project_root = get_project_root(project)
    slaves_path = project_root / project["paths"].get("slaves_file", "slaves.txt")
    slaves = read_slaves(slaves_path)
    ips = [s["ip"] for s in slaves if s.get("enabled", True)]
    if not ips:
        return {"results": []}
    config_dir = resolve_path(project, "config_dir")
    vm_config = read_json_config(config_dir / "vm_config.json")
    ssh_configs = _build_ssh_configs(slaves, vm_config)
    results = await stop_all_servers(ips, ssh_configs)
    return {"results": results}
