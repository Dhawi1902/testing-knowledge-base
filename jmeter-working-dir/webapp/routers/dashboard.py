from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from services.config_parser import resolve_path, get_project_root, read_slaves_file
from services.jmeter import list_jmx_files
from services.jtl_parser import count_result_folders, get_latest_result_folder

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


@router.get("/")
async def dashboard_page(request: Request):
    project = request.app.state.project
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "project_name": project.get("name", "JMeter Dashboard"),
        "active_page": "dashboard",
    })


@router.get("/api/dashboard/stats")
async def api_dashboard_stats(request: Request):
    project = request.app.state.project
    project_root = get_project_root(project)

    jmx_files = list_jmx_files(project)
    results_dir = resolve_path(project, "results_dir")
    results_count = count_result_folders(results_dir)
    slaves_path = project_root / project["paths"].get("slaves_file", "slaves.txt")
    slaves = read_slaves_file(slaves_path)

    return {
        "jmx_count": len(jmx_files),
        "results_count": results_count,
        "slaves_count": len(slaves),
    }


@router.get("/api/dashboard/last-run")
async def api_last_run(request: Request):
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    latest = get_latest_result_folder(results_dir)
    return {"last_run": latest}
