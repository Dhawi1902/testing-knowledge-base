import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from services.config_parser import resolve_path, read_json_config
from services.jmeter import REPORT_OPTIMIZE_PROPS
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


def _check_access(request: Request):
    """Return 403 JSONResponse if viewer, None if allowed."""
    if getattr(request.state, "access_level", "viewer") == "viewer":
        return JSONResponse(status_code=403, content={"error": "Access denied — token required"})
    return None


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


@router.post("/api/results/{folder}/open-report")
async def api_open_report(request: Request, folder: str):
    """Open the report index.html in the default browser (localhost only)."""
    if not getattr(request.state, "is_localhost", False):
        return JSONResponse(status_code=403, content={"error": "Only available from localhost"})
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folder_path = find_result_folder(results_dir, folder)
    if not folder_path:
        return JSONResponse(status_code=404, content={"error": "Folder not found"})
    report_index = folder_path / "report" / "index.html"
    if not report_index.exists():
        return JSONResponse(status_code=404, content={"error": "No report found"})
    try:
        if sys.platform == "win32":
            os.startfile(str(report_index))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(report_index)])
        else:
            subprocess.Popen(["xdg-open", str(report_index)])
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


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
    if not getattr(request.state, "is_localhost", False):
        return JSONResponse(status_code=403, content={"error": "Only available from localhost"})
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


@router.delete("/api/results/{folder}")
async def api_delete_result(request: Request, folder: str):
    """Delete a result folder permanently."""
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folder_path = find_result_folder(results_dir, folder)
    if not folder_path:
        return JSONResponse(status_code=404, content={"error": "Folder not found"})
    # Security: ensure path is within results dir
    if not str(folder_path.resolve()).startswith(str(results_dir.resolve())):
        return JSONResponse(status_code=403, content={"error": "Access denied"})
    try:
        shutil.rmtree(str(folder_path))
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/api/results/{folder}/regenerate")
async def api_regenerate_report(request: Request, folder: str):
    """Regenerate HTML report: always filters JTL first, then generates report."""
    denied = _check_access(request)
    if denied:
        return denied

    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folder_path = find_result_folder(results_dir, folder)
    if not folder_path:
        return JSONResponse(status_code=404, content={"error": "Folder not found"})

    # Find original JTL (always use results.jtl, not filtered.jtl)
    jtl_path = folder_path / "results.jtl"
    if not jtl_path.exists():
        jtl_files = [f for f in folder_path.glob("*.jtl") if f.name != "filtered.jtl"]
        if not jtl_files:
            return JSONResponse(status_code=404, content={"error": "No JTL file found"})
        jtl_path = jtl_files[0]

    report_dir = folder_path / "report"
    report_tmp = folder_path / "report_tmp"
    filtered_jtl_path = folder_path / "filtered.jtl"

    # Clean up leftovers
    if report_tmp.exists():
        shutil.rmtree(str(report_tmp))
    if filtered_jtl_path.exists():
        filtered_jtl_path.unlink()

    jmeter_path = project.get("jmeter_path", "jmeter")

    # Step 1: Always filter JTL (removes sub-results + variables)
    app_dir = Path(__file__).resolve().parent.parent
    filter_result = subprocess.run(
        [sys.executable, str(app_dir / "jtl_filter.py"), str(jtl_path), str(filtered_jtl_path)],
        capture_output=True, text=True, timeout=600,
    )
    if filter_result.returncode != 0:
        return JSONResponse(status_code=500, content={"error": f"Filter failed: {filter_result.stderr}"})

    # Step 2: Generate report to temp dir (don't destroy old report until success)
    result = subprocess.run(
        [jmeter_path, "-g", str(filtered_jtl_path), "-o", str(report_tmp)] + REPORT_OPTIMIZE_PROPS,
        capture_output=True, text=True, timeout=600,
    )

    # Clean up filtered JTL
    if filtered_jtl_path.exists():
        filtered_jtl_path.unlink()

    if result.returncode != 0:
        # Failed — clean up temp, keep old report intact
        if report_tmp.exists():
            shutil.rmtree(str(report_tmp))
        return JSONResponse(status_code=500, content={"error": f"Report generation failed: {result.stderr[:500]}"})

    # Success — swap temp report in
    if report_dir.exists():
        shutil.rmtree(str(report_dir))
    report_tmp.rename(report_dir)

    return {"ok": True, "message": "Report regenerated"}


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


# --- Download ---

def _zip_report_to_file(folder_path: Path, folder_name: str, zip_path: Path):
    """Create a zip of the report directory on disk (excludes JTL files)."""
    report_dir = folder_path / "report"
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_STORED) as zf:
        if report_dir.is_dir():
            for f in report_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, f"{folder_name}/report/{f.relative_to(report_dir)}")
        for meta in ("run_info.json", "config.properties"):
            meta_path = folder_path / meta
            if meta_path.exists():
                zf.write(meta_path, f"{folder_name}/{meta}")


def _dir_size(path: Path) -> int:
    """Get total size of a directory in bytes."""
    total = 0
    if path.is_dir():
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return total


@router.get("/api/results/{folder}/size")
async def api_result_size(request: Request, folder: str):
    """Return the size of the report directory."""
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folder_path = find_result_folder(results_dir, folder)
    if not folder_path:
        return JSONResponse(status_code=404, content={"error": "Folder not found"})
    report_dir = folder_path / "report"
    size = _dir_size(report_dir)
    return {"report_size": size}


@router.get("/api/results/{folder}/download")
async def api_download_report(request: Request, folder: str):
    """Download the report folder as a zip (no JTL). Writes to temp file to handle large reports."""
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folder_path = find_result_folder(results_dir, folder)
    if not folder_path:
        return JSONResponse(status_code=404, content={"error": "Folder not found"})
    if not (folder_path / "report").is_dir():
        return JSONResponse(status_code=404, content={"error": "No report found in this result"})

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()
    try:
        _zip_report_to_file(folder_path, folder, Path(tmp.name))
        return FileResponse(
            tmp.name,
            media_type="application/zip",
            filename=f"{folder}_report.zip",
            background=_cleanup_temp(tmp.name),
        )
    except Exception as e:
        os.unlink(tmp.name)
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/api/results/download-bundle")
async def api_download_bundle(request: Request):
    """Download multiple result reports as a single zip (no JTL). Writes to temp file."""
    body = await request.json()
    folders = body.get("folders", [])
    if not folders:
        return JSONResponse(status_code=400, content={"error": "No folders specified"})
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()
    try:
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_STORED) as zf:
            for folder_name in folders:
                folder_path = find_result_folder(results_dir, folder_name)
                if not folder_path:
                    continue
                report_dir = folder_path / "report"
                if report_dir.is_dir():
                    for f in report_dir.rglob("*"):
                        if f.is_file():
                            zf.write(f, f"{folder_name}/report/{f.relative_to(report_dir)}")
                for meta in ("run_info.json", "config.properties"):
                    meta_path = folder_path / meta
                    if meta_path.exists():
                        zf.write(meta_path, f"{folder_name}/{meta}")
        return FileResponse(
            tmp.name,
            media_type="application/zip",
            filename="reports_bundle.zip",
            background=_cleanup_temp(tmp.name),
        )
    except Exception as e:
        os.unlink(tmp.name)
        return JSONResponse(status_code=500, content={"error": str(e)})


class _cleanup_temp:
    """Background task to delete temp file after response is sent."""
    def __init__(self, path: str):
        self.path = path
    async def __call__(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass


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
