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
    read_slaves_file,
    write_slaves_file,
    detect_jmeter_path,
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
PROJECT_JSON = Path(__file__).resolve().parent.parent / "project.json"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


@router.get("/config")
async def config_page(request: Request):
    project = request.app.state.project
    return templates.TemplateResponse("configuration.html", {
        "request": request,
        "project_name": project.get("name", "JMeter Dashboard"),
        "active_page": "config",
    })


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
    ips = read_slaves_file(slaves_path)
    return {"path": str(slaves_path), "slaves": ips}


class SlavesUpdate(BaseModel):
    slaves: list[str]


@router.put("/api/config/slaves")
async def save_slaves(request: Request, data: SlavesUpdate):
    project = request.app.state.project
    slaves_path = get_project_root(project) / project["paths"].get("slaves_file", "slaves.txt")
    write_slaves_file(slaves_path, data.slaves)
    return {"ok": True}


# --- project.json (Settings) ---

@router.get("/api/config/project")
async def get_project_config(request: Request):
    project = request.app.state.project
    return {"config": project}


@router.put("/api/config/project")
async def save_project_config_route(request: Request, body: dict):
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


@router.get("/api/slaves/status")
async def api_slave_status(request: Request):
    project = request.app.state.project
    project_root = get_project_root(project)
    slaves_path = project_root / project["paths"].get("slaves_file", "slaves.txt")
    ips = read_slaves_file(slaves_path)
    if not ips:
        return {"slaves": []}
    config_dir = resolve_path(project, "config_dir")
    vm_config = read_json_config(config_dir / "vm_config.json")
    ssh_config = vm_config.get("ssh_config", {})
    # Merge jmeter_scripts into ssh_config for the slave service
    ssh_config["jmeter_scripts"] = vm_config.get("jmeter_scripts", {})
    results = await check_all_slaves(ips, ssh_config)
    return {"slaves": results}


@router.post("/api/slaves/start")
async def api_start_servers(request: Request):
    project = request.app.state.project
    project_root = get_project_root(project)
    slaves_path = project_root / project["paths"].get("slaves_file", "slaves.txt")
    ips = read_slaves_file(slaves_path)
    config_dir = resolve_path(project, "config_dir")
    vm_config = read_json_config(config_dir / "vm_config.json")
    ssh_config = vm_config.get("ssh_config", {})
    ssh_config["jmeter_scripts"] = vm_config.get("jmeter_scripts", {})
    results = await start_all_servers(ips, ssh_config)
    return {"results": results}


@router.post("/api/slaves/stop")
async def api_stop_servers(request: Request):
    project = request.app.state.project
    project_root = get_project_root(project)
    slaves_path = project_root / project["paths"].get("slaves_file", "slaves.txt")
    ips = read_slaves_file(slaves_path)
    config_dir = resolve_path(project, "config_dir")
    vm_config = read_json_config(config_dir / "vm_config.json")
    ssh_config = vm_config.get("ssh_config", {})
    ssh_config["jmeter_scripts"] = vm_config.get("jmeter_scripts", {})
    results = await stop_all_servers(ips, ssh_config)
    return {"results": results}
