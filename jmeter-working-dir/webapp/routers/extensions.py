"""API endpoints for JMeter extension (JAR plugin) management."""

import asyncio
import shutil
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import JSONResponse

from services.auth import check_access as _check_access, safe_join
from services.config_parser import (
    resolve_path,
    get_project_root,
    read_json_config,
    read_slaves,
    get_active_slaves,
)
from services.slaves import build_ssh_configs, _scp_upload, _executor

router = APIRouter()


def _list_jars(extensions_dir: Path) -> list[dict]:
    """List JAR files in the extensions directory."""
    if not extensions_dir.exists():
        return []
    jars = []
    for p in sorted(extensions_dir.glob("*.jar")):
        stat = p.stat()
        jars.append({
            "filename": p.name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
        })
    return jars


def _resolve_master_ext_dir(project: dict) -> Path | None:
    """Derive the local JMeter lib/ext/ path from jmeter_path."""
    jmeter_path = project.get("jmeter_path", "")
    if not jmeter_path:
        return None
    # jmeter_path is like .../bin/jmeter.bat or .../bin/jmeter
    jmeter_bin = Path(jmeter_path).resolve().parent  # .../bin/
    ext_dir = jmeter_bin.parent / "lib" / "ext"
    if ext_dir.is_dir():
        return ext_dir
    return None


@router.get("/api/extensions")
async def api_list_extensions(request: Request):
    """List all JAR files in the extensions directory."""
    project = request.app.state.project
    extensions_dir = resolve_path(project, "extensions_dir")
    jars = _list_jars(extensions_dir)
    return {"files": jars}


@router.post("/api/extensions/upload")
async def api_upload_extension(request: Request, file: UploadFile, overwrite: bool = False):
    """Upload a JAR file to the extensions directory."""
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    extensions_dir = resolve_path(project, "extensions_dir")

    if not file.filename or not file.filename.endswith(".jar"):
        return JSONResponse(status_code=400, content={"error": "Only .jar files are accepted"})

    MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
    CHUNK_SIZE = 1024 * 1024  # 1 MB
    extensions_dir.mkdir(parents=True, exist_ok=True)
    dest = safe_join(extensions_dir, file.filename)
    if dest is None:
        return JSONResponse(status_code=403, content={"error": "Invalid filename"})

    if dest.exists() and not overwrite:
        return JSONResponse(status_code=409, content={
            "error": f"{file.filename} already exists. Use overwrite=true to replace."
        })

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
                    return JSONResponse(status_code=413, content={
                        "error": f"File too large (>{MAX_UPLOAD_SIZE // (1024*1024)} MB)"
                    })
                f.write(chunk)
    except Exception:
        dest.unlink(missing_ok=True)
        return JSONResponse(status_code=500, content={"error": "Upload failed"})

    return {"ok": True, "filename": file.filename, "size": total_size}


@router.delete("/api/extensions/{filename}")
async def api_delete_extension(request: Request, filename: str):
    """Delete a JAR file from the extensions directory."""
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    extensions_dir = resolve_path(project, "extensions_dir")
    file_path = safe_join(extensions_dir, filename)
    if file_path is None:
        return JSONResponse(status_code=403, content={"error": "Access denied"})
    if not file_path.exists():
        return JSONResponse(status_code=404, content={"error": "File not found"})
    file_path.unlink()
    return {"ok": True, "filename": filename}


@router.post("/api/extensions/install-master")
async def api_install_master(request: Request):
    """Copy selected JARs to the local JMeter lib/ext/ directory.

    Body: {"files": ["a.jar", "b.jar"]}  — if empty/missing, installs all.
    """
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    extensions_dir = resolve_path(project, "extensions_dir")

    ext_dir = _resolve_master_ext_dir(project)
    if ext_dir is None:
        return JSONResponse(status_code=400, content={
            "error": "Cannot resolve JMeter lib/ext/ directory. Check jmeter_path in project config."
        })

    body = await request.json()
    requested = body.get("files", [])

    all_jars = _list_jars(extensions_dir)
    if requested:
        jars = [j for j in all_jars if j["filename"] in requested]
    else:
        jars = all_jars

    if not jars:
        return JSONResponse(status_code=400, content={"error": "No JAR files to install"})

    results = []
    for jar in jars:
        src = extensions_dir / jar["filename"]
        dest = ext_dir / jar["filename"]
        try:
            shutil.copy2(str(src), str(dest))
            results.append({"file": jar["filename"], "ok": True})
        except Exception as e:
            results.append({"file": jar["filename"], "ok": False, "error": str(e)})

    ok_count = sum(1 for r in results if r["ok"])
    return {
        "ok": ok_count == len(results),
        "results": results,
        "dest": str(ext_dir),
        "summary": f"{ok_count}/{len(results)} installed",
    }


def _deploy_to_slaves(
    slave_ips: list[str],
    ssh_configs: dict[str, dict],
    jar_paths: list[Path],
    extensions_path: str,
) -> list[dict]:
    """Deploy JAR files to all slaves via SCP (runs in thread pool)."""
    results = []
    remote_dir = extensions_path.rstrip("/") + "/"
    for jar in jar_paths:
        for ip in slave_ips:
            cfg = ssh_configs.get(ip, {})
            r = _scp_upload(ip, cfg, jar, remote_dir)
            results.append(r)
    return results


@router.post("/api/extensions/deploy-slaves")
async def api_deploy_slaves(request: Request):
    """Deploy selected JARs to all active slaves' extensions_path.

    Body: {"files": ["a.jar", "b.jar"]}  — if empty/missing, deploys all.
    """
    denied = _check_access(request)
    if denied:
        return denied
    project = request.app.state.project
    extensions_dir = resolve_path(project, "extensions_dir")
    project_root = get_project_root(project)

    body = await request.json()
    requested = body.get("files", [])

    all_jars = _list_jars(extensions_dir)
    if requested:
        jars = [j for j in all_jars if j["filename"] in requested]
    else:
        jars = all_jars

    if not jars:
        return JSONResponse(status_code=400, content={"error": "No JAR files to deploy"})

    # Get active slaves
    slaves_path = project_root / project["paths"].get("slaves_file", "slaves.txt")
    slave_ips = get_active_slaves(slaves_path)
    if not slave_ips:
        return JSONResponse(status_code=400, content={"error": "No active slaves configured"})

    # SSH configs
    all_slaves = read_slaves(slaves_path)
    config_dir = resolve_path(project, "config_dir")
    vm_config = read_json_config(config_dir / "vm_config.json")
    ssh_configs = build_ssh_configs(all_slaves, vm_config)

    # extensions_path from vm_config
    extensions_path = vm_config.get("ssh_config", {}).get("extensions_path", "/opt/jmeter/lib/ext/")

    jar_paths = [extensions_dir / j["filename"] for j in jars]

    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(
        _executor, _deploy_to_slaves,
        slave_ips, ssh_configs, jar_paths, extensions_path,
    )

    ok_count = sum(1 for r in results if r.get("ok"))
    total = len(results)
    return {
        "ok": ok_count == total,
        "results": results,
        "summary": f"{ok_count}/{total} transfers succeeded",
    }
