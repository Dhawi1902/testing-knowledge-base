import json
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from services.settings import atomic_write_json


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


def _preferred_jtl(d: Path) -> Path | None:
    """Find best JTL: prefer filtered.jtl over results.jtl, then any *.jtl."""
    filtered = d / "filtered.jtl"
    if filtered.exists():
        return filtered
    results_jtl = d / "results.jtl"
    if results_jtl.exists():
        return results_jtl
    jtl_files = list(d.glob("*.jtl"))
    return jtl_files[0] if jtl_files else None


def ensure_summary(folder_path: Path) -> dict | None:
    """Ensure run_summary.json has stats. Parse JTL lazily if needed.

    Called from dashboard recent-runs, results list, and stats endpoints.
    Returns the summary dict, or None if no JTL exists.

    - If run_summary.json already has stats (phase=complete), return it.
    - If run_summary.json exists without stats (phase=pre-run), parse JTL and append.
    - If run_summary.json doesn't exist (legacy folder), create from scratch.
    """
    summary_path = folder_path / "run_summary.json"
    existing = {}
    if summary_path.exists():
        try:
            existing = json.loads(summary_path.read_text(encoding="utf-8"))
            if existing.get("phase") == "complete" and "stats" in existing:
                return existing
        except Exception:
            pass

    # Find JTL to parse stats from
    jtl_path = _preferred_jtl(folder_path)
    if not jtl_path:
        return existing or None

    stats = parse_jtl(jtl_path)
    if "error" in stats:
        return existing or None

    # Build or update summary
    if not existing:
        # Legacy folder — bootstrap from run_info.json if available
        run_info_path = folder_path / "run_info.json"
        if run_info_path.exists():
            try:
                existing = json.loads(run_info_path.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
        existing["version"] = 1

    existing["phase"] = "complete"
    existing["stats"] = stats.get("overall", {})
    existing["transactions"] = stats.get("transactions", [])
    existing["jtl_source"] = jtl_path.name

    try:
        atomic_write_json(summary_path, existing)
    except OSError:
        pass

    return existing


def _folder_info(d: Path) -> dict:
    """Build metadata dict for a single result folder."""
    stat = d.stat()
    has_report = (d / "report" / "index.html").exists()
    jtl_files = list(d.glob("*.jtl"))
    has_jtl = len(jtl_files) > 0
    preferred = _preferred_jtl(d)
    date = datetime.fromtimestamp(stat.st_mtime).isoformat()

    # Override date with actual run start time from run_summary or JTL cache
    if preferred:
        # Try run_summary.json first (new format)
        summary_path = d / "run_summary.json"
        start_found = False
        if summary_path.exists():
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                start_ms = summary.get("stats", {}).get("start_time")
                if start_ms:
                    date = datetime.fromtimestamp(start_ms / 1000).isoformat()
                    start_found = True
            except Exception:
                pass
        # Fall back to legacy .summary.json cache
        if not start_found:
            cache_path = preferred.parent / f"{preferred.name}.summary.json"
            if cache_path.exists():
                try:
                    cached = json.loads(cache_path.read_text(encoding="utf-8"))
                    start_ms = cached.get("overall", {}).get("start_time")
                    if start_ms:
                        date = datetime.fromtimestamp(start_ms / 1000).isoformat()
                except Exception:
                    pass

    # Label/alias from run_summary.json
    label = ""
    summary_path = d / "run_summary.json"
    if summary_path.exists():
        try:
            summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
            label = summary_data.get("label", "")
        except Exception:
            pass

    return {
        "name": d.name,
        "label": label,
        "path": str(d),
        "date": date,
        "size": _quick_folder_size(d),
        "has_report": has_report,
        "has_jtl": has_jtl,
        "jtl_file": str(preferred) if preferred else None,
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

    if len(df) == 0:
        empty_overall = {
            "total_samples": 0, "avg": 0, "median": 0,
            "p90": 0, "p95": 0, "p99": 0, "min": 0, "max": 0,
            "error_count": 0, "error_pct": 0, "throughput": 0,
            "duration_sec": 0, "start_time": 0, "end_time": 0, "total_vus": 0,
        }
        result = {"overall": empty_overall, "transactions": []}
        try:
            cache_path.write_text(
                json.dumps({**result, "_jtl_mtime": jtl_mtime}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass
        return result

    elapsed = df["elapsed"].dropna()
    success_col = df["success"].astype(str).str.lower()
    error_count = (success_col != "true").sum()
    total = len(df)

    # Time range
    start_time = 0
    end_time = 0
    if "timeStamp" in df.columns:
        ts = df["timeStamp"].dropna()
        start_time = int(ts.min()) if len(ts) > 0 else 0
        end_time = int(ts.max()) if len(ts) > 0 else 0
        duration_ms = end_time - start_time
        duration_sec = duration_ms / 1000.0
        throughput = total / duration_sec if duration_sec > 0 else 0
    else:
        duration_sec = 0
        throughput = 0

    # Total virtual users — count distinct thread names to handle distributed mode
    # (allThreads only shows per-slave count, not the aggregate)
    total_vus = 0
    if "threadName" in df.columns:
        total_vus = int(df["threadName"].nunique())
    elif "allThreads" in df.columns:
        at = df["allThreads"].dropna()
        total_vus = int(at.max()) if len(at) > 0 else 0

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
        "total_vus": total_vus,
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
    """Compare statistics of two JTL files side by side.

    Returns overall diff and per-transaction breakdown matched by label.
    """
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

    # Per-transaction comparison — match by label
    tx_a = {t["label"]: t for t in stats_a.get("transactions", [])}
    tx_b = {t["label"]: t for t in stats_b.get("transactions", [])}
    all_labels = sorted(set(tx_a.keys()) | set(tx_b.keys()))
    tx_diff = []
    compare_keys = ["avg", "median", "p90", "p95", "error_pct"]
    for label in all_labels:
        entry = {"label": label, "a": tx_a.get(label), "b": tx_b.get(label), "diff": {}}
        if entry["a"] and entry["b"]:
            for key in compare_keys:
                av = entry["a"].get(key, 0)
                bv = entry["b"].get(key, 0)
                pct = round((bv - av) / av * 100, 1) if av != 0 else 0
                entry["diff"][key] = {"a": av, "b": bv, "change_pct": pct}
        tx_diff.append(entry)

    return {
        "run_a": stats_a,
        "run_b": stats_b,
        "diff": diff,
        "transaction_diff": tx_diff,
    }
