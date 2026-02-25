from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from services.auth import check_access as _check_access
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


@router.get("/fleet")
async def fleet_page(request: Request):
    project = request.app.state.project
    return templates.TemplateResponse("slaves.html", {
        "request": request,
        "project_name": project.get("name", "JMeter Dashboard"),
        "active_page": "slaves",
    })


@router.get("/slaves")
async def slaves_page_redirect():
    """Backward-compatible redirect from /slaves to /fleet."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="fleet", status_code=301)


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
    denied = _check_access(request)
    if denied:
        return denied
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

from services.slaves import (  # noqa: E402
    check_all_slaves, start_all_servers, stop_all_servers,
    start_jmeter_server, stop_jmeter_server, build_ssh_configs,
)

# Cache last slave status check for dashboard health dots (E2)
_last_slave_status: list[dict] = []
_last_slave_status_ts: float = 0  # Unix timestamp of last check


def get_cached_slave_status() -> tuple[list[dict], float]:
    """Return (results, timestamp) from the most recent slave status check."""
    return list(_last_slave_status), _last_slave_status_ts


def _get_slaves(project: dict) -> tuple[list[dict], list[str], dict[str, dict]]:
    """Load slaves, active IPs, and SSH configs from project config.
    Returns (slaves, active_ips, ssh_configs).
    """
    project_root = get_project_root(project)
    slaves_path = project_root / project["paths"].get("slaves_file", "slaves.txt")
    slaves = read_slaves(slaves_path)
    active_ips = [s["ip"] for s in slaves if s.get("enabled", True)]
    config_dir = resolve_path(project, "config_dir")
    vm_config = read_json_config(config_dir / "vm_config.json")
    ssh_configs = build_ssh_configs(slaves, vm_config)
    return slaves, active_ips, ssh_configs


@router.get("/api/slaves/status")
async def api_slave_status(request: Request):
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    if not slaves:
        return {"slaves": []}
    if not active_ips:
        return {"slaves": [{"ip": s["ip"], "status": "disabled", "enabled": s.get("enabled", True)} for s in slaves]}
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
    # Cache for dashboard health dots
    import time as _time
    global _last_slave_status, _last_slave_status_ts
    _last_slave_status = merged
    _last_slave_status_ts = _time.time()
    return {"slaves": merged, "checked_at": _last_slave_status_ts}


@router.post("/api/slaves/start")
async def api_start_servers(request: Request):
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    if not active_ips:
        return {"results": []}
    results = await start_all_servers(active_ips, ssh_configs)
    return {"results": results}


@router.post("/api/slaves/stop")
async def api_stop_servers(request: Request):
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    if not active_ips:
        return {"results": []}
    results = await stop_all_servers(active_ips, ssh_configs)
    return {"results": results}


@router.post("/api/slaves/{ip}/start")
async def api_start_single_slave(request: Request, ip: str):
    """Start JMeter server on a single slave (F8)."""
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    if ip not in ssh_configs:
        return JSONResponse(status_code=404, content={"error": f"Slave {ip} not found"})
    result = await start_jmeter_server(ip, ssh_configs[ip])
    return {"result": result}


@router.post("/api/slaves/{ip}/stop")
async def api_stop_single_slave(request: Request, ip: str):
    """Stop JMeter server on a single slave (F8)."""
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    if ip not in ssh_configs:
        return JSONResponse(status_code=404, content={"error": f"Slave {ip} not found"})
    result = await stop_jmeter_server(ip, ssh_configs[ip])
    return {"result": result}
