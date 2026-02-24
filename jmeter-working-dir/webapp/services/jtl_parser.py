import json
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def _quick_folder_size(folder: Path) -> int:
    """Estimate folder size from top-level files + JTL files only (no deep rglob)."""
    total = 0
    try:
        for f in folder.iterdir():
            if f.is_file():
                total += f.stat().st_size
    except OSError:
        pass
    return total


def _folder_info(d: Path) -> dict:
    """Build metadata dict for a single result folder."""
    stat = d.stat()
    has_report = (d / "report" / "index.html").exists()
    jtl_files = list(d.glob("*.jtl"))
    has_jtl = len(jtl_files) > 0
    date = datetime.fromtimestamp(stat.st_mtime).isoformat()

    # Override date with actual run start time from cached JTL summary
    if has_jtl and jtl_files:
        cache_path = jtl_files[0].parent / f"{jtl_files[0].name}.summary.json"
        if cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                start_ms = cached.get("overall", {}).get("start_time")
                if start_ms:
                    date = datetime.fromtimestamp(start_ms / 1000).isoformat()
            except Exception:
                pass

    return {
        "name": d.name,
        "path": str(d),
        "date": date,
        "size": _quick_folder_size(d),
        "has_report": has_report,
        "has_jtl": has_jtl,
        "jtl_file": str(jtl_files[0]) if jtl_files else None,
        "jtl_files": [f.name for f in jtl_files],
        "has_analysis": (d / "analysis_cache.json").exists(),
    }


def _is_run_folder(d: Path) -> bool:
    """Check if a directory is a result-run folder (contains JTL or report)."""
    return any(d.glob("*.jtl")) or (d / "report" / "index.html").exists()


def _collect_run_folders(results_dir: Path) -> list[Path]:
    """Collect result-run folders, handling date-group nesting.

    Supports both flat and nested layouts:
      - Flat:   results_dir/20260204_1/results.jtl
      - Nested: results_dir/20260204/20260204_1/results.jtl
    """
    run_folders = []
    if not results_dir.is_dir():
        return run_folders
    for d in results_dir.iterdir():
        if not d.is_dir():
            continue
        if _is_run_folder(d):
            run_folders.append(d)
        else:
            # Check one level deeper (date-group folder)
            for sub in d.iterdir():
                if sub.is_dir() and _is_run_folder(sub):
                    run_folders.append(sub)
    return run_folders


def list_result_folders(results_dir: Path) -> list[dict]:
    """List result folders sorted by modification time (newest first)."""
    folders = [_folder_info(d) for d in _collect_run_folders(results_dir)]
    folders.sort(key=lambda x: x["date"], reverse=True)
    return folders


def count_result_folders(results_dir: Path) -> int:
    """Fast count of result folders (no metadata)."""
    return len(_collect_run_folders(results_dir))


def get_latest_result_folder(results_dir: Path) -> dict | None:
    """Get only the most recent result folder (no full scan)."""
    run_folders = _collect_run_folders(results_dir)
    if not run_folders:
        return None
    latest = max(run_folders, key=lambda d: d.stat().st_mtime)
    if latest is None:
        return None
    return _folder_info(latest)


def find_result_folder(results_dir: Path, folder_name: str) -> Path | None:
    """Find a result folder by name, handling date-group nesting.

    Tries direct lookup first, then searches one level deeper.
    Returns None if folder not found or if the path would escape results_dir.
    """
    from services.auth import safe_join

    direct = safe_join(results_dir, folder_name)
    if direct is not None and direct.is_dir():
        return direct
    # Search inside date-group folders
    if results_dir.is_dir():
        for d in results_dir.iterdir():
            if d.is_dir():
                nested = safe_join(d, folder_name)
                if nested is not None and nested.is_dir():
                    return nested
    return None


def parse_jtl(jtl_path: str | Path) -> dict:
    """Parse JTL CSV and return summary statistics.

    Results are cached to a .summary.json file next to the JTL.
    Cache is invalidated when the JTL file's mtime changes.
    """
    jtl_path = Path(jtl_path)
    if not jtl_path.exists():
        return {"error": "JTL file not found"}

    # Check cache
    cache_path = jtl_path.parent / f"{jtl_path.name}.summary.json"
    try:
        jtl_mtime = jtl_path.stat().st_mtime
    except OSError:
        jtl_mtime = 0
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if abs(jtl_mtime - cached.get("_jtl_mtime", 0)) < 1:
                cached.pop("_jtl_mtime", None)
                return cached
        except Exception:
            pass

    try:
        df = pd.read_csv(jtl_path, low_memory=False)
    except Exception as e:
        return {"error": f"Failed to parse JTL: {e}"}

    if "elapsed" not in df.columns or "success" not in df.columns:
        return {"error": "JTL file missing required columns (elapsed, success)"}

    elapsed = df["elapsed"].dropna()
    success_col = df["success"].astype(str).str.lower()
    error_count = (success_col != "true").sum()
    total = len(df)

    # Time range
    start_time = 0
    end_time = 0
    if "timeStamp" in df.columns:
        ts = df["timeStamp"]
        start_time = int(ts.min())
        end_time = int(ts.max())
        duration_ms = end_time - start_time
        duration_sec = duration_ms / 1000.0
        throughput = total / duration_sec if duration_sec > 0 else 0
    else:
        duration_sec = 0
        throughput = 0

    overall = {
        "total_samples": int(total),
        "avg": round(float(elapsed.mean()), 1),
        "median": round(float(elapsed.median()), 1),
        "p90": round(float(np.percentile(elapsed, 90)), 1),
        "p95": round(float(np.percentile(elapsed, 95)), 1),
        "p99": round(float(np.percentile(elapsed, 99)), 1),
        "min": int(elapsed.min()),
        "max": int(elapsed.max()),
        "error_count": int(error_count),
        "error_pct": round(error_count / total * 100, 2) if total > 0 else 0,
        "throughput": round(throughput, 2),
        "duration_sec": round(duration_sec, 1),
        "start_time": start_time,
        "end_time": end_time,
    }

    # Per-transaction breakdown
    transactions = []
    if "label" in df.columns:
        for label, group in df.groupby("label"):
            g_elapsed = group["elapsed"].dropna()
            g_success = group["success"].astype(str).str.lower()
            g_errors = (g_success != "true").sum()
            g_total = len(group)
            transactions.append({
                "label": str(label),
                "samples": int(g_total),
                "avg": round(float(g_elapsed.mean()), 1),
                "median": round(float(g_elapsed.median()), 1),
                "p90": round(float(np.percentile(g_elapsed, 90)), 1),
                "p95": round(float(np.percentile(g_elapsed, 95)), 1),
                "min": int(g_elapsed.min()),
                "max": int(g_elapsed.max()),
                "error_count": int(g_errors),
                "error_pct": round(g_errors / g_total * 100, 2) if g_total > 0 else 0,
            })
        transactions.sort(key=lambda x: x["label"])

    result = {"overall": overall, "transactions": transactions}

    # Save cache
    try:
        cache_data = {**result, "_jtl_mtime": jtl_mtime}
        cache_path.write_text(json.dumps(cache_data, indent=2), encoding="utf-8")
    except OSError:
        pass

    return result


def compare_runs(jtl_path_1: str | Path, jtl_path_2: str | Path) -> dict:
    """Compare statistics of two JTL files side by side."""
    stats_a = parse_jtl(jtl_path_1)
    stats_b = parse_jtl(jtl_path_2)

    if "error" in stats_a or "error" in stats_b:
        return {"error": stats_a.get("error") or stats_b.get("error")}

    # Compute diffs for overall metrics
    diff = {}
    for key in ["avg", "median", "p90", "p95", "p99", "error_pct", "throughput"]:
        a_val = stats_a["overall"].get(key, 0)
        b_val = stats_b["overall"].get(key, 0)
        if a_val != 0:
            pct_change = round((b_val - a_val) / a_val * 100, 1)
        else:
            pct_change = 0
        diff[key] = {"a": a_val, "b": b_val, "change_pct": pct_change}

    return {
        "run_a": stats_a,
        "run_b": stats_b,
        "diff": diff,
    }
