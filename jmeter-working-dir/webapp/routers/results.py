import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates

from services.config_parser import resolve_path, read_json_config
from services.jtl_parser import list_result_folders, find_result_folder, parse_jtl, compare_runs
from services.analysis import (
    preprocess_jtl,
    rule_based_analysis,
    ai_analysis,
    check_ollama_status,
    load_cached_analysis,
    save_analysis_cache,
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


@router.get("/results")
async def results_page(request: Request):
    project = request.app.state.project
    return templates.TemplateResponse("results.html", {
        "request": request,
        "project_name": project.get("name", "JMeter Dashboard"),
        "active_page": "results",
    })


@router.get("/api/results/list")
async def api_list_results(request: Request):
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folders = list_result_folders(results_dir)
    return {"folders": folders}


@router.get("/api/results/{folder}/stats")
async def api_result_stats(request: Request, folder: str):
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folder_path = find_result_folder(results_dir, folder)
    if not folder_path:
        return JSONResponse(status_code=404, content={"error": "Folder not found"})
    jtl_files = list(folder_path.glob("*.jtl"))
    if not jtl_files:
        return JSONResponse(status_code=404, content={"error": "No JTL file found"})
    stats = parse_jtl(jtl_files[0])
    return stats


@router.get("/api/results/{folder}/report/{path:path}")
async def api_serve_report(request: Request, folder: str, path: str):
    """Serve files from the HTML report directory."""
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folder_path = find_result_folder(results_dir, folder)
    if not folder_path:
        return JSONResponse(status_code=404, content={"error": "Folder not found"})
    file_path = (folder_path / "report" / path).resolve()
    # Security: ensure path is within results dir
    if not str(file_path).startswith(str(results_dir.resolve())):
        return JSONResponse(status_code=403, content={"error": "Access denied"})
    if not file_path.exists():
        return JSONResponse(status_code=404, content={"error": "File not found"})
    return FileResponse(file_path)


@router.post("/api/results/{folder}/open")
async def api_open_folder(request: Request, folder: str):
    """Open the result folder in OS file explorer."""
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folder_path = find_result_folder(results_dir, folder)
    if not folder_path:
        return JSONResponse(status_code=404, content={"error": "Folder not found"})
    try:
        if sys.platform == "win32":
            os.startfile(str(folder_path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(folder_path)])
        else:
            subprocess.Popen(["xdg-open", str(folder_path)])
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/api/results/compare")
async def api_compare_results(request: Request, folder1: str, folder2: str):
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")

    def find_jtl(folder_name: str) -> Path | None:
        fp = find_result_folder(results_dir, folder_name)
        if not fp:
            return None
        jtls = list(fp.glob("*.jtl"))
        return jtls[0] if jtls else None

    jtl1 = find_jtl(folder1)
    jtl2 = find_jtl(folder2)
    if not jtl1 or not jtl2:
        return JSONResponse(status_code=404, content={"error": "JTL file not found in one or both folders"})
    result = compare_runs(jtl1, jtl2)
    return result


# --- Analysis Engine ---

@router.post("/api/results/{folder}/analyze")
async def api_analyze_result(request: Request, folder: str):
    """Run analysis on a result folder. mode=rules (default) or mode=ai."""
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    mode = body.get("mode", "rules")
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folder_path = find_result_folder(results_dir, folder)

    if not folder_path:
        return JSONResponse(status_code=404, content={"error": "Folder not found"})

    jtl_files = list(folder_path.glob("*.jtl"))
    if not jtl_files:
        return JSONResponse(status_code=404, content={"error": "No JTL file found"})

    # Pre-process JTL
    summary = preprocess_jtl(jtl_files[0])
    if "error" in summary:
        return JSONResponse(status_code=500, content={"error": summary["error"]})

    # Rule-based analysis
    analysis_config = project.get("analysis", {}).get("rules", {})
    rules_result = rule_based_analysis(summary, analysis_config)

    result = {
        "summary": summary,
        "rules": rules_result,
        "ai_report": None,
    }

    # Optional AI analysis
    if mode == "ai":
        ollama_config = project.get("analysis", {}).get("ollama", {})
        base_url = ollama_config.get("base_url", "http://localhost:11434")
        model = ollama_config.get("model", "llama3.1:8b")
        timeout = ollama_config.get("timeout", 120)
        system_context = project.get("analysis", {}).get("system_context", "")
        ai_result = await ai_analysis(summary, system_context, None, base_url, model, timeout)
        result["ai_report"] = ai_result

    # Cache
    save_analysis_cache(folder_path, result)
    return result


@router.get("/api/results/{folder}/analysis")
async def api_get_cached_analysis(request: Request, folder: str):
    """Get cached analysis if available."""
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folder_path = find_result_folder(results_dir, folder)
    if not folder_path:
        return JSONResponse(status_code=404, content={"error": "Folder not found"})
    cached = load_cached_analysis(folder_path)
    if cached:
        return cached
    return JSONResponse(status_code=404, content={"error": "No cached analysis found"})


@router.get("/api/analysis/ollama-status")
async def api_ollama_status(request: Request):
    project = request.app.state.project
    base_url = project.get("analysis", {}).get("ollama", {}).get("base_url", "http://localhost:11434")
    status = await check_ollama_status(base_url)
    return status
