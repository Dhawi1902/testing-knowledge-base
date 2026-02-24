from pathlib import Path

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from services.config_parser import resolve_path, get_project_root, get_active_slaves, read_json_config
from services.data import list_csv_files, preview_csv, preview_split, build_csv
from services.slaves import distribute_files

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


def _check_access(request: Request):
    """Return 403 JSONResponse if viewer, None if allowed."""
    if getattr(request.state, "access_level", "viewer") == "viewer":
        return JSONResponse(status_code=403, content={"error": "Access denied — token required"})
    return None


@router.get("/data")
async def test_data_page(request: Request):
    project = request.app.state.project
    return templates.TemplateResponse("test_data.html", {
        "request": request,
        "project_name": project.get("name", "JMeter Dashboard"),
        "active_page": "data",
    })


@router.get("/api/data/files")
async def api_list_data_files(request: Request):
    project = request.app.state.project
    data_dir = resolve_path(project, "test_data_dir")
    files = list_csv_files(data_dir)
    return {"files": files}


@router.get("/api/data/preview/{filename:path}")
async def api_preview_csv(request: Request, filename: str, rows: int = 50):
    project = request.app.state.project
    data_dir = resolve_path(project, "test_data_dir")
    file_path = (data_dir / filename).resolve()
    # Security check
    if not str(file_path).startswith(str(data_dir.resolve())):
        return JSONResponse(status_code=403, content={"error": "Access denied"})
    result = preview_csv(file_path, rows=min(rows, 10000))
    return result


@router.get("/api/data/download/{filename}")
async def api_download_csv(request: Request, filename: str):
    project = request.app.state.project
    data_dir = resolve_path(project, "test_data_dir")
    file_path = (data_dir / filename).resolve()
    if not str(file_path).startswith(str(data_dir.resolve())):
        return JSONResponse(status_code=403, content={"error": "Access denied"})
    if not file_path.exists():
        return JSONResponse(status_code=404, content={"error": "File not found"})
    return FileResponse(file_path, filename=filename, media_type="text/csv")


@router.delete("/api/data/delete/{filename}")
async def api_delete_csv(request: Request, filename: str):
    """Delete a CSV file from the test data directory."""
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    data_dir = resolve_path(project, "test_data_dir")
    file_path = (data_dir / filename).resolve()
    if not str(file_path).startswith(str(data_dir.resolve())):
        return JSONResponse(status_code=403, content={"error": "Access denied"})
    if not file_path.exists():
        return JSONResponse(status_code=404, content={"error": "File not found"})
    file_path.unlink()
    return {"ok": True, "filename": filename}


@router.post("/api/data/rename")
async def api_rename_csv(request: Request):
    """Rename a CSV file.  Body: {"old": "a.csv", "new": "b.csv"}"""
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()
    old_name = body.get("old", "").strip()
    new_name = body.get("new", "").strip()
    if not old_name or not new_name:
        return JSONResponse(status_code=400, content={"error": "Both old and new names required"})
    if not new_name.endswith(".csv"):
        new_name += ".csv"

    project = request.app.state.project
    data_dir = resolve_path(project, "test_data_dir")
    data_dir_resolved = str(data_dir.resolve())

    old_path = (data_dir / old_name).resolve()
    new_path = (data_dir / new_name).resolve()
    if not str(old_path).startswith(data_dir_resolved) or not str(new_path).startswith(data_dir_resolved):
        return JSONResponse(status_code=403, content={"error": "Access denied"})
    if not old_path.exists():
        return JSONResponse(status_code=404, content={"error": f"File not found: {old_name}"})
    if new_path.exists():
        return JSONResponse(status_code=400, content={"error": f"File already exists: {new_name}"})

    old_path.rename(new_path)
    return {"ok": True, "old": old_name, "new": new_name}


@router.post("/api/data/build")
async def api_build_data(request: Request):
    """Build a CSV file from column definitions."""
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()
    project = request.app.state.project
    data_dir = resolve_path(project, "test_data_dir")
    result = build_csv(body, data_dir)
    if "error" in result:
        return JSONResponse(status_code=400, content=result)
    return result


@router.post("/api/data/upload")
async def api_upload_data(request: Request, file: UploadFile):
    """Upload a CSV file to the test data directory."""
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    data_dir = resolve_path(project, "test_data_dir")

    if not file.filename or not file.filename.endswith(".csv"):
        return JSONResponse(status_code=400, content={"error": "Only .csv files are accepted"})

    data_dir.mkdir(parents=True, exist_ok=True)
    dest = data_dir / file.filename
    content = await file.read()
    dest.write_bytes(content)

    return {"ok": True, "filename": file.filename, "size": len(content)}


@router.post("/api/distribute/preview")
async def api_preview_split(request: Request):
    """Preview how a CSV would be split across slaves.

    Body: {"file": "name.csv", "offset": 0, "size": 0}
    """
    body = await request.json()
    project = request.app.state.project
    project_root = get_project_root(project)
    data_dir = resolve_path(project, "test_data_dir")
    data_dir_resolved = str(data_dir.resolve())

    fname = body.get("file", "")
    fpath = (data_dir / fname).resolve()
    if not str(fpath).startswith(data_dir_resolved):
        return JSONResponse(status_code=403, content={"error": "Access denied"})
    if not fpath.exists():
        return JSONResponse(status_code=404, content={"error": f"File not found: {fname}"})

    # Get active slaves
    slaves_path = project_root / project["paths"].get("slaves_file", "slaves.txt")
    slave_ips = get_active_slaves(slaves_path)
    if not slave_ips:
        return JSONResponse(status_code=400, content={"error": "No active slaves configured"})

    offset = int(body.get("offset", 0))
    size = int(body.get("size", 0))
    result = preview_split(fpath, slave_ips, offset, size)
    if "error" in result:
        return JSONResponse(status_code=400, content=result)
    return result


@router.post("/api/data/distribute")
async def api_distribute_data(request: Request):
    """Distribute CSV files to slaves with per-file mode.

    Body: {"items": [{"file": "name.csv", "mode": "copy"|"split", "offset": 0, "size": 0}, ...]}
    """
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()
    project = request.app.state.project
    project_root = get_project_root(project)
    data_dir = resolve_path(project, "test_data_dir")
    data_dir_resolved = str(data_dir.resolve())

    raw_items = body.get("items", [])
    if not raw_items:
        return JSONResponse(status_code=400, content={"error": "No files selected"})

    # Validate and resolve each item
    items = []
    for item in raw_items:
        fname = item.get("file", "")
        mode = item.get("mode", "copy")
        if mode not in ("copy", "split"):
            return JSONResponse(status_code=400, content={"error": f"Invalid mode '{mode}' for {fname}"})
        fpath = (data_dir / fname).resolve()
        if not str(fpath).startswith(data_dir_resolved):
            return JSONResponse(status_code=403, content={"error": f"Access denied: {fname}"})
        if not fpath.exists():
            return JSONResponse(status_code=404, content={"error": f"File not found: {fname}"})
        items.append({
            "file_path": fpath,
            "mode": mode,
            "offset": int(item.get("offset", 0)),
            "size": int(item.get("size", 0)),
        })

    # Get active slaves
    slaves_path = project_root / project["paths"].get("slaves_file", "slaves.txt")
    slave_ips = get_active_slaves(slaves_path)
    if not slave_ips:
        return JSONResponse(status_code=400, content={"error": "No active slaves configured"})

    # Build per-slave SSH configs (global defaults + per-slave overrides)
    from services.config_parser import read_slaves as _read_slaves
    config_dir = resolve_path(project, "config_dir")
    vm_config = read_json_config(config_dir / "vm_config.json")
    all_slaves = _read_slaves(slaves_path)
    global_ssh = vm_config.get("ssh_config", {})
    ssh_configs = {}
    for s in all_slaves:
        ip = s["ip"]
        overrides = s.get("overrides", {})
        merged = {**global_ssh}
        if overrides.get("user"):
            merged["user"] = overrides["user"]
        if overrides.get("password"):
            merged["password"] = overrides["password"]
        if overrides.get("dest_path"):
            merged["dest_path"] = overrides["dest_path"]
        ssh_configs[ip] = merged

    results = await distribute_files(slave_ips, ssh_configs, items, data_dir)

    ok_count = sum(1 for r in results if r.get("ok"))
    total = len(results)
    return {"ok": ok_count == total, "results": results, "summary": f"{ok_count}/{total} transfers succeeded"}
