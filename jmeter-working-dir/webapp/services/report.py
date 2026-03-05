"""Report regeneration service — async, non-blocking.

Centralizes the filter-JTL + generate-report pipeline used by both
single and bulk regeneration endpoints.
"""
import asyncio
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from services.jmeter import build_report_command
from services.report_properties import cleanup_report_html

from services.paths import get_app_dir

APP_DIR = get_app_dir()


async def regenerate_report(
    folder_path: Path,
    jmeter_path: str,
    filter_sub_results: bool = True,
    label_pattern: str = "",
) -> dict:
    """Filter JTL + generate HTML report. Non-blocking (async subprocess).

    Returns {"ok": True/False, "message": str, "error": str|None}.
    """
    # Find original JTL (always use results.jtl, not filtered.jtl)
    jtl_path = folder_path / "results.jtl"
    if not jtl_path.exists():
        jtl_files = [f for f in folder_path.glob("*.jtl") if f.name != "filtered.jtl"]
        if not jtl_files:
            return {"ok": False, "error": "No JTL file found"}
        jtl_path = jtl_files[0]

    report_dir = folder_path / "report"
    report_tmp = folder_path / "report_tmp"
    filtered_jtl_path = folder_path / "filtered.jtl"

    # Clean up leftovers
    if report_tmp.exists():
        shutil.rmtree(str(report_tmp))
    if filtered_jtl_path.exists():
        filtered_jtl_path.unlink()

    try:
        # Step 1: Filter JTL
        source_jtl = jtl_path
        if filter_sub_results:
            filter_cmd = [sys.executable, str(APP_DIR / "jtl_filter.py"),
                          str(jtl_path), str(filtered_jtl_path)]
            if label_pattern:
                filter_cmd.append(label_pattern)
            proc = await asyncio.create_subprocess_exec(
                *filter_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {"ok": False, "error": "JTL filter timed out (10 min)"}
            if proc.returncode != 0:
                return {"ok": False, "error": f"Filter failed: {stderr.decode()[:500]}"}
            source_jtl = filtered_jtl_path

        # Step 2: Generate report to temp dir
        report_cmd = build_report_command(jmeter_path, str(source_jtl), str(report_tmp))
        proc = await asyncio.create_subprocess_exec(
            *report_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            if report_tmp.exists():
                shutil.rmtree(str(report_tmp))
            return {"ok": False, "error": "Report generation timed out (10 min)"}

        if proc.returncode != 0:
            if report_tmp.exists():
                shutil.rmtree(str(report_tmp))
            return {"ok": False, "error": f"Report generation failed: {stderr.decode()[:500]}"}

        # Post-process: remove disabled graph panels
        cleanup_report_html(report_tmp)

        # Swap temp report in
        if report_dir.exists():
            shutil.rmtree(str(report_dir))
        report_tmp.rename(report_dir)

        # Save regeneration filter params
        regen_info = {
            "timestamp": datetime.now().isoformat(),
            "filter_sub_results": filter_sub_results,
            "label_pattern": label_pattern,
        }
        (folder_path / "regen_info.json").write_text(
            json.dumps(regen_info, indent=2), encoding="utf-8"
        )

        return {"ok": True, "message": "Report regenerated"}

    except Exception as e:
        if report_tmp.exists():
            shutil.rmtree(str(report_tmp))
        return {"ok": False, "error": str(e)}
