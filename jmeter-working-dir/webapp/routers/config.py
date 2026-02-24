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


def get_cached_slave_status() -> list[dict]:
    """Return results from the most recent slave status check."""
    return list(_last_slave_status)


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
    global _last_slave_status
    _last_slave_status = merged
    return {"slaves": merged}


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


# --- JMeter Properties Management (F2/F3/F4) ---

from services.slaves import distribute_files  # noqa: E402

PROPS_FILE = Path(__file__).resolve().parent.parent / "jmeter_properties.json"


def _read_jmeter_properties() -> list[dict]:
    """Read user-defined JMeter properties from jmeter_properties.json."""
    if not PROPS_FILE.exists():
        return []
    try:
        import json as _json
        return _json.loads(PROPS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write_jmeter_properties(props: list[dict]) -> None:
    import json as _json
    PROPS_FILE.write_text(_json.dumps(props, indent=2, ensure_ascii=False), encoding="utf-8")


@router.get("/api/config/jmeter-properties")
async def api_get_jmeter_properties(request: Request):
    """Return user-defined JMeter properties (F2)."""
    return {"properties": _read_jmeter_properties()}


@router.put("/api/config/jmeter-properties")
async def api_save_jmeter_properties(request: Request):
    """Save user-defined JMeter properties (F2)."""
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()
    props = body.get("properties", [])
    _write_jmeter_properties(props)
    return {"ok": True}


@router.post("/api/config/push-properties")
async def api_push_properties(request: Request):
    """Generate jmeter.properties from defined properties and push to all slaves via SCP (F3)."""
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    if not active_ips:
        return {"results": [], "error": "No active slaves"}

    # Generate properties file content
    props = _read_jmeter_properties()
    if not props:
        return {"results": [], "error": "No properties defined"}

    # Write temp properties file
    import tempfile
    content = "# Auto-generated JMeter properties\n"
    for p in props:
        if p.get("key") and p.get("enabled", True):
            content += f"{p['key']}={p.get('value', '')}\n"

    tmp = Path(tempfile.mktemp(suffix=".properties"))
    tmp.write_text(content, encoding="utf-8")

    try:
        items = [{"file_path": tmp, "mode": "copy"}]
        results = await distribute_files(active_ips, ssh_configs, items, tmp.parent)
        return {"results": results}
    finally:
        tmp.unlink(missing_ok=True)
