import asyncio
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from services.config_parser import resolve_path, get_project_root
from services.data import list_csv_files, preview_csv, get_csv_stats
from services.process_manager import ProcessManager

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()
data_process = ProcessManager()


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
async def api_preview_csv(request: Request, filename: str):
    project = request.app.state.project
    data_dir = resolve_path(project, "test_data_dir")
    file_path = (data_dir / filename).resolve()
    # Security check
    if not str(file_path).startswith(str(data_dir.resolve())):
        return JSONResponse(status_code=403, content={"error": "Access denied"})
    result = preview_csv(file_path)
    return result


@router.post("/api/data/generate")
async def api_generate_data(request: Request):
    """Run generate_master_data.py as subprocess."""
    project = request.app.state.project
    project_root = get_project_root(project)

    # Look for the generate script
    script = None
    for candidate in ["utils/generate_master_data.py", "bin/data/generate_master_data.bat"]:
        p = project_root / candidate
        if p.exists():
            script = p
            break

    if not script:
        return JSONResponse(status_code=404, content={"error": "generate_master_data script not found"})

    if data_process.is_running:
        return JSONResponse(status_code=409, content={"error": "A data process is already running"})

    if script.suffix == ".py":
        cmd = ["python", str(script)]
    else:
        cmd = [str(script)]

    data_process.start(cmd, cwd=project_root, label="generate_master_data")

    # Collect output
    lines = []
    async for line in data_process.stream_output():
        lines.append(line)

    rc = data_process.return_code()
    return {"ok": rc == 0, "output": "\n".join(lines), "return_code": rc}


@router.post("/api/data/split")
async def api_split_data(request: Request):
    """Run split_and_copy_to_vms.py."""
    body = await request.json()
    project = request.app.state.project
    project_root = get_project_root(project)
    offset = body.get("offset", 0)
    size = body.get("size", 15000)

    script = project_root / "utils" / "split_and_copy_to_vms.py"
    if not script.exists():
        return JSONResponse(status_code=404, content={"error": "split_and_copy_to_vms.py not found"})

    if data_process.is_running:
        return JSONResponse(status_code=409, content={"error": "A data process is already running"})

    cmd = ["python", str(script), "--offset", str(offset), "--size", str(size)]
    data_process.start(cmd, cwd=project_root, label="split_and_copy")

    lines = []
    async for line in data_process.stream_output():
        lines.append(line)

    rc = data_process.return_code()
    return {"ok": rc == 0, "output": "\n".join(lines), "return_code": rc}


@router.post("/api/data/distribute")
async def api_distribute_data(request: Request):
    """Run split_and_copy_to_vms.py with distribute flag."""
    body = await request.json()
    project = request.app.state.project
    project_root = get_project_root(project)
    offset = body.get("offset", 0)
    size = body.get("size", 15000)

    script = project_root / "utils" / "split_and_copy_to_vms.py"
    if not script.exists():
        return JSONResponse(status_code=404, content={"error": "split_and_copy_to_vms.py not found"})

    if data_process.is_running:
        return JSONResponse(status_code=409, content={"error": "A data process is already running"})

    cmd = ["python", str(script), "--offset", str(offset), "--size", str(size)]
    data_process.start(cmd, cwd=project_root, label="distribute_data")

    lines = []
    async for line in data_process.stream_output():
        lines.append(line)

    rc = data_process.return_code()
    return {"ok": rc == 0, "output": "\n".join(lines), "return_code": rc}
