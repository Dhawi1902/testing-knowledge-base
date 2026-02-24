from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from services.config_parser import resolve_path, get_project_root, read_slaves, get_active_slaves
from services.jmeter import list_jmx_files
from services.jtl_parser import count_result_folders, get_latest_result_folder
from services.process_manager import jmeter_process_manager

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
    all_slaves = read_slaves(slaves_path)
    active_slaves = [s for s in all_slaves if s.get("enabled", True)]

    # Monitoring URLs from settings
    from routers.settings import load_settings
    settings = load_settings()
    monitoring = settings.get("monitoring", {})

    return {
        "jmx_count": len(jmx_files),
        "results_count": results_count,
        "slaves_count": len(all_slaves),
        "active_slaves_count": len(active_slaves),
        "mode": "distributed" if active_slaves else "local",
        "runner_active": jmeter_process_manager.is_running,
        "runner_label": jmeter_process_manager.active_label,
        "grafana_url": monitoring.get("grafana_url", ""),
        "influxdb_url": monitoring.get("influxdb_url", ""),
    }


@router.get("/api/dashboard/last-run")
async def api_last_run(request: Request):
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    latest = get_latest_result_folder(results_dir)
    return {"last_run": latest}
