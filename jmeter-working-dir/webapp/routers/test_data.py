import json
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from services.config_parser import resolve_path, get_project_root, get_active_slaves, read_json_config
from services.auth import check_access as _check_access, safe_join
from services.data import list_csv_files, preview_csv, preview_split, build_csv
from services.slaves import distribute_files, build_ssh_configs

APP_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = APP_DIR / "templates"
CSV_TEMPLATES_FILE = APP_DIR / "csv_templates.json"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


def _load_csv_templates() -> dict:
    if CSV_TEMPLATES_FILE.exists():
        try:
            return json.loads(CSV_TEMPLATES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_csv_templates(data: dict):
    CSV_TEMPLATES_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


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
    file_path = safe_join(data_dir, filename)
    if file_path is None:
        return JSONResponse(status_code=403, content={"error": "Access denied"})
    result = preview_csv(file_path, rows=min(rows, 10000))
    return result


@router.get("/api/data/download/{filename}")
async def api_download_csv(request: Request, filename: str):
    project = request.app.state.project
    data_dir = resolve_path(project, "test_data_dir")
    file_path = safe_join(data_dir, filename)
    if file_path is None:
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
    file_path = safe_join(data_dir, filename)
    if file_path is None:
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

    old_path = safe_join(data_dir, old_name)
    new_path = safe_join(data_dir, new_name)
    if old_path is None or new_path is None:
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
async def api_upload_data(request: Request, file: UploadFile, overwrite: bool = False):
    """Upload a CSV file to the test data directory.

    Returns 409 if file exists and overwrite is not set.
    Pass ?overwrite=true to replace an existing file.
    """
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    data_dir = resolve_path(project, "test_data_dir")

    if not file.filename or not file.filename.endswith(".csv"):
        return JSONResponse(status_code=400, content={"error": "Only .csv files are accepted"})

    MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
    CHUNK_SIZE = 1024 * 1024  # 1 MB
    data_dir.mkdir(parents=True, exist_ok=True)
    dest = safe_join(data_dir, file.filename)
    if dest is None:
        return JSONResponse(status_code=403, content={"error": "Invalid filename"})

    if dest.exists() and not overwrite:
        return JSONResponse(status_code=409, content={"error": f"{file.filename} already exists. Use overwrite=true to replace."})

    # Stream to disk in chunks to avoid loading entire file into memory
    total_size = 0
    try:
        with open(dest, "wb") as f:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE:
                    f.close()
                    dest.unlink(missing_ok=True)
                    return JSONResponse(status_code=413, content={"error": f"File too large (>{MAX_UPLOAD_SIZE // (1024*1024)} MB). Maximum is 100 MB."})
                f.write(chunk)
    except Exception:
        dest.unlink(missing_ok=True)
        return JSONResponse(status_code=500, content={"error": "Upload failed"})

    return {"ok": True, "filename": file.filename, "size": total_size}


@router.post("/api/distribute/preview")
async def api_preview_split(request: Request):
    """Preview how a CSV would be split across slaves.

    Body: {"file": "name.csv", "offset": 0, "size": 0}
    """
    body = await request.json()
    project = request.app.state.project
    project_root = get_project_root(project)
    data_dir = resolve_path(project, "test_data_dir")

    fname = body.get("file", "")
    fpath = safe_join(data_dir, fname)
    if fpath is None:
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
        fpath = safe_join(data_dir, fname)
        if fpath is None:
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
    ssh_configs = build_ssh_configs(all_slaves, vm_config)

    results = await distribute_files(slave_ips, ssh_configs, items, data_dir)

    ok_count = sum(1 for r in results if r.get("ok"))
    total = len(results)
    return {"ok": ok_count == total, "results": results, "summary": f"{ok_count}/{total} transfers succeeded"}


# --- CSV Builder Templates ---

@router.get("/api/data/templates")
async def api_list_csv_templates():
    """Return all saved CSV builder templates."""
    return {"templates": _load_csv_templates()}


@router.post("/api/data/templates")
async def api_save_csv_template(request: Request):
    """Save a CSV builder template. Body: {"name": "...", "columns": [...]}"""
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()
    name = body.get("name", "").strip()
    columns = body.get("columns", [])
    if not name:
        return JSONResponse(status_code=400, content={"error": "Template name is required"})
    templates_data = _load_csv_templates()
    templates_data[name] = columns
    _save_csv_templates(templates_data)
    return {"ok": True}


@router.delete("/api/data/templates/{name}")
async def api_delete_csv_template(request: Request, name: str):
    """Delete a CSV builder template by name."""
    denied = _check_access(request)
    if denied:
        return denied
    templates_data = _load_csv_templates()
    templates_data.pop(name, None)
    _save_csv_templates(templates_data)
    return {"ok": True}
