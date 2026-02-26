import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from services.auth import check_access as _check_access, safe_join
from services.config_parser import resolve_path, read_json_config
from services.report import regenerate_report as _regen_report
from services.jtl_parser import list_result_folders, find_result_folder, parse_jtl, compare_runs, ensure_summary
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

def _find_jtl(folder_path: Path) -> Path | None:
    """Find the best JTL file for stats: prefer filtered.jtl over results.jtl.

    filtered.jtl is the source of truth when filtering was applied at run time
    or regeneration time. Falls back to results.jtl, then any *.jtl file.
    """
    filtered = folder_path / "filtered.jtl"
    if filtered.exists():
        return filtered
    results_jtl = folder_path / "results.jtl"
    if results_jtl.exists():
        return results_jtl
    jtl_files = list(folder_path.glob("*.jtl"))
    return jtl_files[0] if jtl_files else None


# Track active regeneration — lock prevents concurrent runs
_regen_lock = asyncio.Lock()
_active_regen_folder: str | None = None


@router.get("/results")
async def results_page(request: Request):
    project = request.app.state.project
    return templates.TemplateResponse("results.html", {
        "request": request,
        "project_name": project.get("name", "JMeter Dashboard"),
        "active_page": "results",
    })


@router.get("/api/results/list")
async def api_list_results(request: Request, page: int = 0, per_page: int = 0, q: str = ""):
    """List results with optional pagination and search.

    page/per_page=0 means no pagination (return all). page is 1-based.
    q filters by folder name (case-insensitive substring match).
    Each folder includes compact metrics from run_summary.json when available.
    """
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folders = list_result_folders(results_dir)

    # Search filter
    if q:
        q_lower = q.lower()
        folders = [f for f in folders if q_lower in f["name"].lower()]

    total = len(folders)

    # Pagination
    if page > 0 and per_page > 0:
        start = (page - 1) * per_page
        folders = folders[start:start + per_page]

    # Enrich with metrics from run_summary.json (lazy — computed on first access)
    for f in folders:
        folder_path = Path(f["path"])
        summary = ensure_summary(folder_path)
        if summary and "stats" in summary:
            s = summary["stats"]
            f["metrics"] = {
                "avg": s.get("avg"),
                "p95": s.get("p95"),
                "error_pct": s.get("error_pct"),
                "throughput": s.get("throughput"),
                "peak_vus": s.get("peak_vus"),
                "total_samples": s.get("total_samples"),
            }

    return {"folders": folders, "total": total}


@router.get("/api/results/{folder}/stats")
async def api_result_stats(request: Request, folder: str):
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folder_path = find_result_folder(results_dir, folder)
    if not folder_path:
        return JSONResponse(status_code=404, content={"error": "Folder not found"})
    jtl_path = _find_jtl(folder_path)
    if not jtl_path:
        return JSONResponse(status_code=404, content={"error": "No JTL file found"})
    stats = parse_jtl(jtl_path)
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
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to open report"})


@router.get("/api/results/{folder}/report/{path:path}")
async def api_serve_report(request: Request, folder: str, path: str):
    """Serve files from the HTML report directory."""
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folder_path = find_result_folder(results_dir, folder)
    if not folder_path:
        return JSONResponse(status_code=404, content={"error": "Folder not found"})
    report_dir = folder_path / "report"
    file_path = safe_join(report_dir, path)
    if file_path is None:
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
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to open folder"})


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
    try:
        shutil.rmtree(str(folder_path))
        return {"ok": True}
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to delete result folder"})


@router.post("/api/results/bulk-delete")
async def api_bulk_delete(request: Request):
    """Delete multiple result folders at once."""
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()
    folders = body.get("folders", [])
    if not folders:
        return JSONResponse(status_code=400, content={"error": "No folders specified"})

    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    results = []

    for folder_name in folders:
        folder_path = find_result_folder(results_dir, folder_name)
        if not folder_path:
            results.append({"folder": folder_name, "ok": False, "error": "Not found"})
            continue
        try:
            shutil.rmtree(str(folder_path))
            results.append({"folder": folder_name, "ok": True})
        except Exception as e:
            results.append({"folder": folder_name, "ok": False, "error": str(e)})

    return {"results": results}


@router.post("/api/results/{folder}/regenerate")
async def api_regenerate_report(request: Request, folder: str):
    """Regenerate HTML report using async service (non-blocking)."""
    denied = _check_access(request)
    if denied:
        return denied

    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    filter_sub_results = body.get("filter_sub_results", True)
    label_pattern = body.get("label_pattern", "")

    if label_pattern:
        try:
            re.compile(label_pattern)
        except re.error as e:
            return JSONResponse(status_code=400, content={"error": f"Invalid regex pattern: {e}"})

    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folder_path = find_result_folder(results_dir, folder)
    if not folder_path:
        return JSONResponse(status_code=404, content={"error": "Folder not found"})

    global _active_regen_folder
    if _regen_lock.locked():
        return JSONResponse(status_code=409, content={"error": f"Regeneration already in progress for '{_active_regen_folder}'"})

    jmeter_path = project.get("jmeter_path", "jmeter")

    async with _regen_lock:
        _active_regen_folder = folder
        try:
            result = await _regen_report(folder_path, jmeter_path, filter_sub_results, label_pattern)
            if not result.get("ok"):
                return JSONResponse(status_code=500, content={"error": result.get("error", "Unknown error")})
            return result
        finally:
            _active_regen_folder = None


@router.get("/api/results/{folder}/labels")
async def api_result_labels(request: Request, folder: str):
    """Return unique labels from JTL for the label picker (F9)."""
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folder_path = find_result_folder(results_dir, folder)
    if not folder_path:
        return JSONResponse(status_code=404, content={"error": "Folder not found"})
    jtl_path = _find_jtl(folder_path)
    if not jtl_path:
        return JSONResponse(status_code=404, content={"error": "No JTL file found"})
    stats = parse_jtl(jtl_path)
    labels = [t["label"] for t in stats.get("transactions", [])]
    return {"labels": labels}


@router.post("/api/results/bulk-regenerate")
async def api_bulk_regenerate(request: Request):
    """Regenerate reports for multiple folders sequentially using async service.

    Uses per-result saved filter settings from regen_info.json/run_summary.json
    when use_saved_settings=true, falling back to request body defaults.
    """
    denied = _check_access(request)
    if denied:
        return denied
    body = await request.json()
    folders = body.get("folders", [])
    default_filter = body.get("filter_sub_results", True)
    default_pattern = body.get("label_pattern", "")
    use_saved = body.get("use_saved_settings", False)
    if not folders:
        return JSONResponse(status_code=400, content={"error": "No folders specified"})

    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    jmeter_path = project.get("jmeter_path", "jmeter")
    results = []

    for folder_name in folders:
        folder_path = find_result_folder(results_dir, folder_name)
        if not folder_path:
            results.append({"folder": folder_name, "ok": False, "error": "Not found"})
            continue

        # Per-result settings (14.4.7)
        filt = default_filter
        pat = default_pattern
        if use_saved:
            for info_name in ("regen_info.json", "run_summary.json", "run_info.json"):
                info_path = folder_path / info_name
                if info_path.exists():
                    try:
                        info = json.loads(info_path.read_text(encoding="utf-8"))
                        filt = info.get("filter_sub_results", filt)
                        pat = info.get("label_pattern", pat)
                        break
                    except Exception:
                        pass

        result = await _regen_report(folder_path, jmeter_path, filt, pat)
        results.append({"folder": folder_name, **result})

    return {"results": results}


@router.get("/api/results/{folder}/filter-info")
async def api_filter_info(request: Request, folder: str):
    """Return saved filter params from run_info.json or regen_info.json for modal pre-fill."""
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")
    folder_path = find_result_folder(results_dir, folder)
    if not folder_path:
        return {"filter_sub_results": True, "label_pattern": ""}
    # Prefer regen_info (last regeneration), fall back to run_summary, then run_info
    regen_info = folder_path / "regen_info.json"
    run_summary = folder_path / "run_summary.json"
    run_info = folder_path / "run_info.json"
    for info_file in (regen_info, run_summary, run_info):
        if info_file.exists():
            try:
                data = json.loads(info_file.read_text(encoding="utf-8"))
                return {
                    "filter_sub_results": data.get("filter_sub_results", True),
                    "label_pattern": data.get("label_pattern", ""),
                }
            except Exception:
                pass
    return {"filter_sub_results": True, "label_pattern": ""}


@router.post("/api/results/stop-regenerate")
async def api_stop_regenerate(request: Request):
    """Stop a running report regeneration."""
    denied = _check_access(request)
    if denied:
        return denied
    global _active_regen_folder
    if _regen_lock.locked():
        _active_regen_folder = None
        return {"ok": True, "message": "Regeneration will be stopped"}
    return {"ok": True, "message": "No active regeneration"}


@router.get("/api/results/compare")
async def api_compare_results(request: Request, folder1: str, folder2: str):
    project = request.app.state.project
    results_dir = resolve_path(project, "results_dir")

    def locate_jtl(folder_name: str) -> Path | None:
        fp = find_result_folder(results_dir, folder_name)
        if not fp:
            return None
        return _find_jtl(fp)

    jtl1 = locate_jtl(folder1)
    jtl2 = locate_jtl(folder2)
    if not jtl1 or not jtl2:
        return JSONResponse(status_code=404, content={"error": "JTL file not found in one or both folders"})
    result = compare_runs(jtl1, jtl2)
    return result


# --- Download ---

def _add_report_to_zip(zf: zipfile.ZipFile, folder_path: Path, folder_name: str, include_jtl: bool = False):
    """Add a result folder's report + metadata to an open ZipFile."""
    report_dir = folder_path / "report"
    if report_dir.is_dir():
        for f in report_dir.rglob("*"):
            if f.is_file():
                zf.write(f, f"{folder_name}/report/{f.relative_to(report_dir)}")
    for meta in ("run_summary.json", "run_info.json", "config.properties"):
        meta_path = folder_path / meta
        if meta_path.exists():
            zf.write(meta_path, f"{folder_name}/{meta}")
    if include_jtl:
        for jtl in folder_path.glob("*.jtl"):
            zf.write(jtl, f"{folder_name}/{jtl.name}")


def _zip_report_to_file(folder_path: Path, folder_name: str, zip_path: Path):
    """Create a zip of the report directory on disk (excludes JTL files)."""
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        _add_report_to_zip(zf, folder_path, folder_name)


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
async def api_download_report(request: Request, folder: str, include_jtl: bool = False):
    """Download the report folder as a zip. Optionally include JTL files."""
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
        with zipfile.ZipFile(str(tmp.name), "w", zipfile.ZIP_DEFLATED) as zf:
            _add_report_to_zip(zf, folder_path, folder, include_jtl=include_jtl)
        suffix = "_full" if include_jtl else "_report"
        return FileResponse(
            tmp.name,
            media_type="application/zip",
            filename=f"{folder}{suffix}.zip",
            background=_cleanup_temp(tmp.name),
        )
    except Exception:
        os.unlink(tmp.name)
        return JSONResponse(status_code=500, content={"error": "Failed to create download archive"})


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
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
            for folder_name in folders:
                folder_path = find_result_folder(results_dir, folder_name)
                if not folder_path:
                    continue
                _add_report_to_zip(zf, folder_path, folder_name)
        return FileResponse(
            tmp.name,
            media_type="application/zip",
            filename="reports_bundle.zip",
            background=_cleanup_temp(tmp.name),
        )
    except Exception:
        os.unlink(tmp.name)
        return JSONResponse(status_code=500, content={"error": "Failed to create download bundle"})


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

    jtl_path = _find_jtl(folder_path)
    if not jtl_path:
        return JSONResponse(status_code=404, content={"error": "No JTL file found"})

    # Pre-process JTL
    summary = preprocess_jtl(jtl_path)
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
