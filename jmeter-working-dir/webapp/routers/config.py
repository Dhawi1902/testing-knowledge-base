import ipaddress
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from services.auth import check_access as _check_access
import asyncio as _asyncio_mod
import json as _json


def _validate_ip(ip: str):
    """Return a 400 JSONResponse if ip is not a valid address, else None."""
    try:
        ipaddress.ip_address(ip)
        return None
    except ValueError:
        return JSONResponse(status_code=400, content={"error": f"Invalid IP address: {ip}"})

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

PROJECT_JSON = Path(__file__).resolve().parent.parent / "project.json"

from services.templates import templates

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


# --- JMeter Properties (user.properties) ---

def _get_jmeter_bin_dir(project: dict) -> Path | None:
    """Derive JMeter bin directory from jmeter_path in project config."""
    jmeter_path = project.get("jmeter_path", "")
    if not jmeter_path:
        return None
    p = Path(jmeter_path)
    # jmeter_path points to jmeter.bat or jmeter — bin dir is its parent
    if p.exists():
        return p.parent
    # Even if the file doesn't exist, try the parent dir
    return p.parent if p.parent.exists() else None


_CATALOG_CACHE: list[dict] | None = None


@router.get("/api/config/jmeter-properties/catalog")
async def get_jmeter_properties_catalog(request: Request):
    """Return the static JMeter property catalog (from official docs)."""
    global _CATALOG_CACHE
    if _CATALOG_CACHE is None:
        catalog_path = Path(__file__).resolve().parent.parent / "static" / "data" / "jmeter_properties_catalog.json"
        with open(catalog_path, "r", encoding="utf-8") as f:
            _CATALOG_CACHE = _json.load(f)
    return {"catalog": _CATALOG_CACHE}


@router.get("/api/config/jmeter-properties/master")
async def get_jmeter_user_properties(request: Request):
    """Read user.properties from JMeter bin directory (master overrides)."""
    project = request.app.state.project
    bin_dir = _get_jmeter_bin_dir(project)
    if not bin_dir:
        return {"properties": {}, "path": ""}
    user_props_path = bin_dir / "user.properties"
    props = read_config_properties(user_props_path)
    return {"properties": props, "path": str(user_props_path)}


@router.put("/api/config/jmeter-properties/master")
async def save_jmeter_user_properties(request: Request, data: PropertiesUpdate):
    """Write user.properties to JMeter bin directory (master overrides)."""
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    bin_dir = _get_jmeter_bin_dir(project)
    if not bin_dir:
        return JSONResponse(status_code=400, content={"error": "JMeter path not configured"})
    user_props_path = bin_dir / "user.properties"
    write_config_properties(user_props_path, data.properties,
                            comments=["JMeter user.properties — managed by JMeter Dashboard webapp"])
    return {"ok": True}


@router.get("/api/config/jmeter-properties/slave")
async def get_slave_user_properties(request: Request):
    """Read slave-user.properties from config directory."""
    project = request.app.state.project
    config_dir = resolve_path(project, "config_dir")
    slave_props_path = config_dir / "slave-user.properties"
    props = read_config_properties(slave_props_path)
    return {"properties": props, "path": str(slave_props_path)}


@router.put("/api/config/jmeter-properties/slave")
async def save_slave_user_properties(request: Request, data: PropertiesUpdate):
    """Write slave-user.properties to config directory."""
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    config_dir = resolve_path(project, "config_dir")
    slave_props_path = config_dir / "slave-user.properties"
    write_config_properties(slave_props_path, data.properties,
                            comments=["Slave user.properties — pushed to slaves during provisioning"])
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
    test_ssh_connection, test_rmi_port,
    provision_slave, check_provision_status,
    distribute_files, fetch_slave_log,
    clean_slave_data, clean_slave_log,
    get_slave_resources, get_all_slave_resources,
    fetch_all_agent_metrics,
)
from services.data import list_csv_files
from services.health_history import load_health_history, record_status_check

# Cache last slave status check for dashboard health dots (E2)
_last_slave_status: list[dict] = []
_last_slave_status_ts: float = 0  # Unix timestamp of last check
_status_lock = _asyncio_mod.Lock()


async def get_cached_slave_status() -> tuple[list[dict], float]:
    """Return (results, timestamp) from the most recent slave status check."""
    async with _status_lock:
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
            entry = {**result_map[s["ip"]], "enabled": True}
            merged.append(entry)
        else:
            merged.append({"ip": s["ip"], "status": "disabled", "enabled": s.get("enabled", True)})
    # Cache for dashboard health dots
    import time as _time
    global _last_slave_status, _last_slave_status_ts
    async with _status_lock:
        _last_slave_status = merged
        _last_slave_status_ts = _time.time()
        checked_at = _last_slave_status_ts
    # Record to health history (#31)
    config_dir = resolve_path(project, "config_dir")
    record_status_check(config_dir, merged)
    return {"slaves": merged, "checked_at": checked_at}


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
    invalid = _validate_ip(ip)
    if invalid:
        return invalid
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
    invalid = _validate_ip(ip)
    if invalid:
        return invalid
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    if ip not in ssh_configs:
        return JSONResponse(status_code=404, content={"error": f"Slave {ip} not found"})
    result = await stop_jmeter_server(ip, ssh_configs[ip])
    return {"result": result}


@router.post("/api/slaves/{ip}/restart")
async def api_restart_single_slave(request: Request, ip: str):
    """Restart JMeter server on a single slave (stop + start)."""
    invalid = _validate_ip(ip)
    if invalid:
        return invalid
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    if ip not in ssh_configs:
        return JSONResponse(status_code=404, content={"error": f"Slave {ip} not found"})
    stop_result = await stop_jmeter_server(ip, ssh_configs[ip])
    start_result = await start_jmeter_server(ip, ssh_configs[ip])
    return {"stop_result": stop_result, "start_result": start_result}


@router.post("/api/slaves/{ip}/test-ssh")
async def api_test_ssh(request: Request, ip: str):
    """Test SSH connection to a single slave (#27)."""
    invalid = _validate_ip(ip)
    if invalid:
        return invalid
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    if ip not in ssh_configs:
        return JSONResponse(status_code=404, content={"error": f"Slave {ip} not found"})
    result = await test_ssh_connection(ip, ssh_configs[ip])
    return {"result": result}


@router.post("/api/slaves/{ip}/test-rmi")
async def api_test_rmi(request: Request, ip: str):
    """Test RMI port reachability on a slave (#28)."""
    invalid = _validate_ip(ip)
    if invalid:
        return invalid
    denied = _check_access(request)
    if denied:
        return denied
    result = await test_rmi_port(ip)
    return {"result": result}


@router.post("/api/slaves/{ip}/provision")
async def api_provision_slave(request: Request, ip: str):
    """Provision a single slave: Java, JMeter, dirs, scripts, firewall (#17).

    Accepts optional JSON body {"steps": ["java", "scripts", ...]} to run only
    selected components. Omit body or send empty to run all steps.
    """
    invalid = _validate_ip(ip)
    if invalid:
        return invalid
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    if ip not in ssh_configs:
        return JSONResponse(status_code=404, content={"error": f"Slave {ip} not found"})
    # Parse optional step selection
    only_steps = None
    try:
        body = await request.json()
        if body and isinstance(body.get("steps"), list) and body["steps"]:
            only_steps = body["steps"]
    except Exception:
        pass
    result = await provision_slave(ip, ssh_configs[ip], only_steps=only_steps)
    return {"result": result}


@router.post("/api/slaves/{ip}/provision-status")
async def api_provision_status(request: Request, ip: str):
    """Check provision status on a slave: Java, JMeter, scripts, firewall (#18)."""
    invalid = _validate_ip(ip)
    if invalid:
        return invalid
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    if ip not in ssh_configs:
        return JSONResponse(status_code=404, content={"error": f"Slave {ip} not found"})
    result = await check_provision_status(ip, ssh_configs[ip])
    return {"result": result}


# --- Sync Data (#29) ---

@router.post("/api/slaves/sync-data")
async def api_sync_data(request: Request):
    """Distribute test data files to all active slaves (#29).

    Copies all CSV files from test_data/ to each active slave's dest_path.
    """
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    data_dir = resolve_path(project, "test_data_dir")
    csv_files = list_csv_files(data_dir)
    if not csv_files:
        return JSONResponse(status_code=400, content={"error": "No CSV files in test data directory"})

    slaves, active_ips, ssh_configs = _get_slaves(project)
    if not active_ips:
        return JSONResponse(status_code=400, content={"error": "No active slaves configured"})

    items = [{"file_path": data_dir / f["filename"], "mode": "copy", "offset": 0, "size": 0} for f in csv_files]
    results = await distribute_files(active_ips, ssh_configs, items, data_dir)

    ok_count = sum(1 for r in results if r.get("ok"))
    total = len(results)
    return {"ok": ok_count == total, "results": results, "summary": f"{ok_count}/{total} transfers succeeded"}


@router.get("/api/slaves/sync-data/preview")
async def api_sync_data_preview(request: Request):
    """List files that would be synced and target slaves (#29)."""
    project = request.app.state.project
    data_dir = resolve_path(project, "test_data_dir")
    csv_files = list_csv_files(data_dir)
    slaves, active_ips, ssh_configs = _get_slaves(project)
    return {"files": csv_files, "slaves": active_ips}


# --- View Slave Log (#22) ---

@router.get("/api/slaves/{ip}/log")
async def api_slave_log(request: Request, ip: str, tail: int = 200):
    """Fetch jmeter-slave.log from a slave via SSH (#22)."""
    invalid = _validate_ip(ip)
    if invalid:
        return invalid
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    if ip not in ssh_configs:
        return JSONResponse(status_code=404, content={"error": f"Slave {ip} not found"})
    result = await fetch_slave_log(ip, ssh_configs[ip], tail=tail)
    return {"result": result}


# --- Clean Data (#32) ---

@router.post("/api/slaves/{ip}/clean-data")
async def api_clean_data(request: Request, ip: str):
    """Delete CSV files in slave's test_data/ directory (#32)."""
    invalid = _validate_ip(ip)
    if invalid:
        return invalid
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    if ip not in ssh_configs:
        return JSONResponse(status_code=404, content={"error": f"Slave {ip} not found"})
    result = await clean_slave_data(ip, ssh_configs[ip])
    return {"result": result}


@router.post("/api/slaves/bulk-clean-data")
async def api_bulk_clean_data(request: Request):
    """Delete CSV files on multiple slaves (#32)."""
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()
    ips = body.get("ips", [])
    if not ips:
        return JSONResponse(status_code=400, content={"error": "No slaves specified"})
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    import asyncio as _asyncio
    tasks = [clean_slave_data(ip, ssh_configs[ip]) for ip in ips if ip in ssh_configs]
    results = await _asyncio.gather(*tasks)
    return {"results": list(results)}


# --- Clean Logs (#33) ---

@router.post("/api/slaves/{ip}/clean-log")
async def api_clean_log(request: Request, ip: str):
    """Truncate jmeter-slave.log on a slave (#33)."""
    invalid = _validate_ip(ip)
    if invalid:
        return invalid
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    if ip not in ssh_configs:
        return JSONResponse(status_code=404, content={"error": f"Slave {ip} not found"})
    result = await clean_slave_log(ip, ssh_configs[ip])
    return {"result": result}


@router.post("/api/slaves/collect-logs")
async def api_collect_logs(request: Request):
    """Fetch logs from active slaves and save to local disk."""
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()
    requested_ips = body.get("ips", [])
    tail = int(body.get("tail", 0))  # 0 = full log

    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    ips = [ip for ip in requested_ips if ip in ssh_configs] if requested_ips else [ip for ip in active_ips if ip in ssh_configs]
    if not ips:
        return JSONResponse(status_code=400, content={"error": "No slaves available"})

    # Save directory: {project_root}/results/slave-logs/
    from services.config_parser import get_project_root
    log_dir = get_project_root(project) / "results" / "slave-logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    import asyncio as _asyncio
    # Fetch full logs (tail=0 means cat the whole file)
    tasks = [fetch_slave_log(ip, ssh_configs[ip], tail=tail) for ip in ips]
    results = await _asyncio.gather(*tasks)

    saved = []
    for r in results:
        ip = r["ip"]
        safe_ip = ip.replace(":", "_")  # handle IPv6
        fname = f"{safe_ip}_jmeter-slave.log"
        fpath = log_dir / fname
        if r.get("ok") and r.get("log"):
            fpath.write_text(r["log"], encoding="utf-8")
            saved.append({"ip": ip, "ok": True, "file": fname, "size": len(r["log"])})
        else:
            saved.append({"ip": ip, "ok": False, "error": r.get("error", "Empty log")})

    ok_count = sum(1 for s in saved if s["ok"])
    return {
        "ok": ok_count == len(saved),
        "results": saved,
        "dest": str(log_dir),
        "summary": f"{ok_count}/{len(saved)} logs saved",
    }


@router.get("/api/slaves/saved-logs")
async def api_list_saved_logs(request: Request):
    """List locally saved slave log files."""
    project = request.app.state.project
    from services.config_parser import get_project_root
    log_dir = get_project_root(project) / "results" / "slave-logs"
    if not log_dir.is_dir():
        return {"files": []}
    files = []
    for p in sorted(log_dir.glob("*_jmeter-slave.log")):
        stat = p.stat()
        files.append({
            "filename": p.name,
            "ip": p.stem.replace("_jmeter-slave", "").replace("_", ":"),
            "size": stat.st_size,
            "modified": stat.st_mtime,
        })
    return {"files": files, "dest": str(log_dir)}


@router.get("/api/slaves/saved-logs/{filename}")
async def api_view_saved_log(request: Request, filename: str):
    """View or download a saved slave log file."""
    project = request.app.state.project
    from services.config_parser import get_project_root
    from services.auth import safe_join
    log_dir = get_project_root(project) / "results" / "slave-logs"
    file_path = safe_join(log_dir, filename)
    if file_path is None:
        return JSONResponse(status_code=403, content={"error": "Access denied"})
    if not file_path.exists():
        return JSONResponse(status_code=404, content={"error": "File not found"})
    return FileResponse(file_path, filename=filename, media_type="text/plain")


@router.post("/api/slaves/bulk-clean-logs")
async def api_bulk_clean_logs(request: Request):
    """Truncate logs on multiple slaves (#33)."""
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()
    ips = body.get("ips", [])
    if not ips:
        return JSONResponse(status_code=400, content={"error": "No slaves specified"})
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    import asyncio as _asyncio
    tasks = [clean_slave_log(ip, ssh_configs[ip]) for ip in ips if ip in ssh_configs]
    results = await _asyncio.gather(*tasks)
    return {"results": list(results)}


# --- Resource Monitoring (#30) ---

@router.get("/api/slaves/{ip}/resources")
async def api_slave_resources(request: Request, ip: str):
    """Get CPU and RAM usage from a single slave (#30)."""
    invalid = _validate_ip(ip)
    if invalid:
        return invalid
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    if ip not in ssh_configs:
        return JSONResponse(status_code=404, content={"error": f"Slave {ip} not found"})
    result = await get_slave_resources(ip, ssh_configs[ip])
    return {"result": result}


@router.get("/api/slaves/resources")
async def api_all_slave_resources(request: Request):
    """Get CPU and RAM usage from all active slaves (#30)."""
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    slaves, active_ips, ssh_configs = _get_slaves(project)
    if not active_ips:
        return {"results": []}
    results = await get_all_slave_resources(active_ips, ssh_configs)
    return {"results": list(results)}


# --- Agent Metrics (HTTP-based monitoring) ---

@router.get("/api/slaves/metrics")
async def api_all_slave_metrics(request: Request):
    """Fetch metrics from all slaves via HTTP agent (lightweight, no SSH)."""
    project = request.app.state.project
    vm_config = read_json_config(resolve_path(project, "config_dir") / "vm_config.json")
    agent_port = vm_config.get("agent_port", 9100)
    slaves_raw = read_slaves(resolve_path(project, "slaves_file"))
    active_ips = [
        (s if isinstance(s, str) else s["ip"])
        for s in slaves_raw
        if isinstance(s, str) or s.get("enabled", True)
    ]
    if not active_ips:
        return {"results": []}
    results = await fetch_all_agent_metrics(active_ips, port=agent_port)
    result_list = list(results)
    # Record metrics for chart history backfill
    from services.metrics_history import record_metrics
    config_dir = resolve_path(project, "config_dir")
    record_metrics(config_dir, result_list)
    return {"results": result_list}


@router.get("/api/slaves/metrics/history")
async def api_metrics_history(request: Request):
    """Return recent metrics history for chart backfill."""
    project = request.app.state.project
    config_dir = resolve_path(project, "config_dir")
    from services.metrics_history import load_metrics_history
    history = load_metrics_history(config_dir)
    return {"history": history}


# --- Health History (#31) ---

@router.get("/api/slaves/health-history")
async def api_health_history(request: Request):
    """Return health history for all slaves (#31)."""
    project = request.app.state.project
    config_dir = resolve_path(project, "config_dir")
    history = load_health_history(config_dir)
    return {"history": history}


@router.delete("/api/slaves/health-history")
async def api_clear_health_history(request: Request):
    """Clear all health history (#31)."""
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    config_dir = resolve_path(project, "config_dir")
    from services.health_history import save_health_history
    save_health_history(config_dir, {})
    return {"ok": True}
