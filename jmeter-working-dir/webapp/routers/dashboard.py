from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from services.config_parser import resolve_path, get_project_root, read_slaves, get_active_slaves
from services.jmeter import list_jmx_files
from services.jtl_parser import count_result_folders, get_latest_result_folder, list_result_folders, parse_jtl
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
    from services.settings import load_settings
    settings = load_settings()
    monitoring = settings.get("monitoring", {})

    return {
        "jmx_count": len(jmx_files),
        "results_count": results_count,
        "slaves_count": len(all_slaves),
        "active_slaves_count": len(active_slaves),
        "mode": "distributed" if active_slaves else "local",
        "runner_active": jmeter_process_manager.is_running,
        "runner_post_processing": jmeter_process_manager.is_post_processing,
        "runner_label": jmeter_process_manager.active_label,
        "live_stats": jmeter_process_manager.live_stats,
        "grafana_url": monitoring.get("grafana_url", ""),
        "influxdb_url": monitoring.get("influxdb_url", ""),
    }


@router.get("/api/dashboard/last-run")
async def api_last_run(request: Request):
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    latest = get_latest_result_folder(results_dir)
    if latest and latest.get("has_jtl") and latest.get("jtl_file"):
        try:
            stats = parse_jtl(latest["jtl_file"])
        except Exception:
            stats = {}
        if "overall" in stats:
            latest["stats"] = stats["overall"]
    return {"last_run": latest}


@router.get("/api/dashboard/recent-runs")
async def api_recent_runs(request: Request):
    """Return the last 10 result folders with key performance metrics."""
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folders = list_result_folders(results_dir)[:10]
    runs = []
    for f in folders:
        run = {"name": f["name"], "date": f["date"], "has_jtl": f["has_jtl"]}
        if f["has_jtl"] and f.get("jtl_file"):
            try:
                stats = parse_jtl(f["jtl_file"])
            except Exception:
                stats = {}
            if "overall" in stats:
                run["stats"] = {
                    "total_samples": stats["overall"]["total_samples"],
                    "avg": stats["overall"]["avg"],
                    "p95": stats["overall"]["p95"],
                    "error_pct": stats["overall"]["error_pct"],
                    "throughput": stats["overall"]["throughput"],
                    "peak_vus": stats["overall"].get("peak_vus", 0),
                }
        runs.append(run)
    return {"runs": runs}


@router.get("/api/dashboard/disk-usage")
async def api_disk_usage(request: Request):
    """Return total size of results directory."""
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    total_size = 0
    file_count = 0
    if results_dir.is_dir():
        for f in results_dir.rglob("*"):
            if f.is_file():
                try:
                    total_size += f.stat().st_size
                    file_count += 1
                except OSError:
                    pass
    folder_count = count_result_folders(results_dir)
    return {
        "total_bytes": total_size,
        "file_count": file_count,
        "folder_count": folder_count,
    }


@router.get("/api/dashboard/alerts")
async def api_alerts(request: Request):
    """Return active warnings/alerts for the dashboard."""
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    alerts = []

    folders = list_result_folders(results_dir)

    # Results with JTL but no HTML report
    no_report = [f for f in folders if f["has_jtl"] and not f["has_report"]]
    if no_report:
        names = ", ".join(f["name"] for f in no_report[:5])
        suffix = f" (+{len(no_report) - 5} more)" if len(no_report) > 5 else ""
        alerts.append({
            "level": "warning",
            "message": f"{len(no_report)} result(s) missing HTML report",
            "detail": names + suffix,
            "link": "/results",
        })

    # Disk usage check
    total_size = 0
    if results_dir.is_dir():
        for f in results_dir.rglob("*"):
            if f.is_file():
                try:
                    total_size += f.stat().st_size
                except OSError:
                    pass
    if total_size > 5 * 1024 ** 3:
        alerts.append({
            "level": "danger",
            "message": f"Results directory very large ({total_size / 1024**3:.1f} GB)",
            "link": "/results",
        })
    elif total_size > 1 * 1024 ** 3:
        alerts.append({
            "level": "warning",
            "message": f"Results directory exceeds 1 GB ({total_size / 1024**3:.1f} GB)",
            "link": "/results",
        })

    # Empty result folders (no JTL and no report)
    empty = [f for f in folders if not f["has_jtl"] and not f["has_report"]]
    if empty:
        alerts.append({
            "level": "info",
            "message": f"{len(empty)} result folder(s) with no data",
            "link": "/results",
        })

    # Slave health from cached status
    from routers.config import get_cached_slave_status
    slaves, _ts = get_cached_slave_status()
    down = [s for s in slaves if s.get("status") == "down"]
    if down:
        ips = ", ".join(s["ip"] for s in down)
        alerts.append({
            "level": "danger",
            "message": f"{len(down)} slave(s) unreachable",
            "detail": ips,
            "link": "/slaves",
        })

    return {"alerts": alerts}


@router.get("/api/dashboard/slave-health")
async def api_slave_health(request: Request):
    """Return cached slave status from most recent check."""
    from routers.config import get_cached_slave_status
    slaves, checked_at = get_cached_slave_status()
    return {"slaves": slaves, "checked_at": checked_at}
