import json
from pathlib import Path

import numpy as np
import pandas as pd
import httpx

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


# ===== JTL Pre-Processor =====

def preprocess_jtl(jtl_path: Path) -> dict:
    """Parse raw JTL into compact summary (~2-4KB JSON)."""
    try:
        df = pd.read_csv(jtl_path, low_memory=False)
    except Exception as e:
        return {"error": str(e)}

    if "elapsed" not in df.columns:
        return {"error": "JTL missing 'elapsed' column"}

    elapsed = df["elapsed"].dropna()
    success_col = df["success"].astype(str).str.lower() if "success" in df.columns else pd.Series(["true"] * len(df))
    total = len(df)
    error_count = int((success_col != "true").sum())

    # Duration and throughput
    duration_sec = 0
    if "timeStamp" in df.columns:
        ts = df["timeStamp"]
        duration_sec = round((ts.max() - ts.min()) / 1000.0, 1)

    throughput = round(total / duration_sec, 2) if duration_sec > 0 else 0

    summary = {
        "test_info": {
            "date": "",
            "duration_sec": duration_sec,
            "total_samples": total,
        },
        "overall": {
            "avg_rt": round(float(elapsed.mean()), 1),
            "p50": round(float(elapsed.median()), 1),
            "p90": round(float(np.percentile(elapsed, 90)), 1),
            "p95": round(float(np.percentile(elapsed, 95)), 1),
            "p99": round(float(np.percentile(elapsed, 99)), 1),
            "min": int(elapsed.min()),
            "max": int(elapsed.max()),
            "error_rate": round(error_count / total * 100, 2) if total > 0 else 0,
            "throughput": throughput,
        },
        "per_transaction": [],
        "time_series": {},
    }

    # Per-transaction breakdown
    if "label" in df.columns:
        for label, group in df.groupby("label"):
            g_elapsed = group["elapsed"].dropna()
            g_success = group["success"].astype(str).str.lower() if "success" in group.columns else pd.Series(["true"] * len(group))
            g_errors = int((g_success != "true").sum())
            g_total = len(group)

            # Error breakdown by response code
            errors_by_code = {}
            if "responseCode" in group.columns and g_errors > 0:
                failed = group[g_success != "true"]
                for code, count in failed["responseCode"].value_counts().items():
                    errors_by_code[str(code)] = int(count)

            summary["per_transaction"].append({
                "label": str(label),
                "samples": g_total,
                "avg": round(float(g_elapsed.mean()), 1),
                "p95": round(float(np.percentile(g_elapsed, 95)), 1),
                "error_rate": round(g_errors / g_total * 100, 2) if g_total > 0 else 0,
                "errors": errors_by_code,
            })

    # Time series (30-second intervals)
    if "timeStamp" in df.columns:
        ts = df["timeStamp"]
        start = ts.min()
        interval_ms = 30000
        intervals = []
        avg_rts = []
        throughputs = []
        error_counts = []
        active_threads_list = []

        t = start
        while t < ts.max():
            mask = (ts >= t) & (ts < t + interval_ms)
            chunk = df[mask]
            if len(chunk) > 0:
                label = f"{int((t - start) / 1000)}s"
                intervals.append(label)
                avg_rts.append(round(float(chunk["elapsed"].mean()), 1))
                throughputs.append(round(len(chunk) / (interval_ms / 1000.0), 1))
                chunk_success = chunk["success"].astype(str).str.lower() if "success" in chunk.columns else pd.Series(["true"] * len(chunk))
                error_counts.append(int((chunk_success != "true").sum()))
                if "allThreads" in chunk.columns:
                    active_threads_list.append(int(chunk["allThreads"].max()))
            t += interval_ms

        summary["time_series"] = {
            "intervals": intervals,
            "avg_response_time": avg_rts,
            "throughput": throughputs,
            "error_count": error_counts,
        }
        if active_threads_list:
            summary["time_series"]["active_threads"] = active_threads_list

    return summary


# ===== Rule-Based Analysis =====

def rule_based_analysis(summary: dict, config: dict | None = None) -> dict:
    """Programmatic pattern detection on pre-processed summary."""
    if "error" in summary:
        return {"severity": "info", "error": summary["error"]}

    cfg = config or {}
    bottleneck_threshold = cfg.get("bottleneck_threshold", 3.0)
    error_warning_pct = cfg.get("error_warning_pct", 2.0)
    error_critical_pct = cfg.get("error_critical_pct", 5.0)

    overall = summary.get("overall", {})
    transactions = summary.get("per_transaction", [])
    time_series = summary.get("time_series", {})

    findings = {
        "severity": "info",
        "bottlenecks": [],
        "degradation_point": None,
        "error_patterns": [],
        "throughput_saturation": None,
        "recommendations": [],
    }

    # --- Bottleneck detection: p95 > threshold * median ---
    p50 = overall.get("p50", 0)
    p95 = overall.get("p95", 0)
    if p50 > 0 and p95 > bottleneck_threshold * p50:
        findings["bottlenecks"].append({
            "type": "overall",
            "label": "Overall",
            "p50": p50,
            "p95": p95,
            "ratio": round(p95 / p50, 1),
        })

    for tx in transactions:
        # Flag transactions with high p95 vs avg
        if tx["avg"] > 0 and tx["p95"] > bottleneck_threshold * tx["avg"]:
            findings["bottlenecks"].append({
                "type": "transaction",
                "label": tx["label"],
                "avg": tx["avg"],
                "p95": tx["p95"],
                "ratio": round(tx["p95"] / tx["avg"], 1),
            })

    # --- Error threshold ---
    error_rate = overall.get("error_rate", 0)
    if error_rate > error_critical_pct:
        findings["severity"] = "critical"
        findings["error_patterns"].append({
            "type": "overall_error_rate",
            "rate": error_rate,
            "level": "critical",
        })
    elif error_rate > error_warning_pct:
        if findings["severity"] != "critical":
            findings["severity"] = "warning"
        findings["error_patterns"].append({
            "type": "overall_error_rate",
            "rate": error_rate,
            "level": "warning",
        })

    # Per-transaction error rates
    for tx in transactions:
        if tx["error_rate"] > error_critical_pct:
            findings["error_patterns"].append({
                "type": "transaction_error",
                "label": tx["label"],
                "rate": tx["error_rate"],
                "errors": tx.get("errors", {}),
            })

    # --- Response time degradation ---
    rts = time_series.get("avg_response_time", [])
    threads = time_series.get("active_threads", [])
    intervals = time_series.get("intervals", [])
    if len(rts) >= 4:
        # Find inflection point: where RT jumps > 50% from previous
        for i in range(1, len(rts)):
            if rts[i - 1] > 0 and rts[i] > rts[i - 1] * 1.5:
                findings["degradation_point"] = {
                    "interval": intervals[i] if i < len(intervals) else f"interval {i}",
                    "rt_before": rts[i - 1],
                    "rt_after": rts[i],
                    "threads": threads[i] if i < len(threads) else None,
                }
                if findings["severity"] == "info":
                    findings["severity"] = "warning"
                break

    # --- Throughput saturation (plateau detection) ---
    tps = time_series.get("throughput", [])
    if len(tps) >= 6:
        # Check if throughput plateaus while threads are still increasing
        mid = len(tps) // 2
        first_half_avg = sum(tps[mid:mid + 3]) / 3 if mid + 3 <= len(tps) else 0
        second_half_avg = sum(tps[-3:]) / 3 if len(tps) >= 3 else 0
        if first_half_avg > 0 and abs(second_half_avg - first_half_avg) / first_half_avg < 0.1:
            if threads and threads[-1] > threads[mid] * 1.3:
                findings["throughput_saturation"] = {
                    "plateau_tps": round(second_half_avg, 1),
                    "at_threads": threads[mid] if mid < len(threads) else None,
                }

    # --- Recommendations ---
    if findings["bottlenecks"]:
        findings["recommendations"].append("Investigate bottleneck transactions with high p95/avg ratio — likely contention or backend slowness under load.")
    if findings["degradation_point"]:
        dp = findings["degradation_point"]
        findings["recommendations"].append(f"Performance degrades at {dp['interval']} — consider increasing infrastructure capacity or optimizing the workload at this concurrency level.")
    if error_rate > error_warning_pct:
        findings["recommendations"].append(f"Error rate is {error_rate}% — check server logs for 5xx errors, connection timeouts, or resource exhaustion.")
    if findings["throughput_saturation"]:
        sat = findings["throughput_saturation"]
        findings["recommendations"].append(f"Throughput plateaus at ~{sat['plateau_tps']} req/s — system capacity may be reached. Scale horizontally or optimize backend.")
    if not findings["recommendations"]:
        findings["recommendations"].append("No significant issues detected. Test results look healthy.")

    return findings


# ===== Ollama AI Analysis =====

async def check_ollama_status(base_url: str = "http://localhost:11434") -> dict:
    """Check if Ollama is running and reachable."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                return {"available": True, "models": models}
    except Exception:
        pass
    return {"available": False, "models": []}


async def ai_analysis(
    summary: dict,
    system_context: str = "",
    previous_summary: dict | None = None,
    base_url: str = "http://localhost:11434",
    model: str = "llama3.1:8b",
    timeout: int = 120,
) -> dict:
    """Run AI analysis via local Ollama."""
    # Load prompt template
    template_path = PROMPTS_DIR / "analysis.txt"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = "Analyze this performance test data:\n{summary_json}"

    prompt = template.replace("{system_context}", system_context or "Not provided")
    prompt = prompt.replace("{summary_json}", json.dumps(summary, indent=2))
    prompt = prompt.replace("{previous_summary_json}", json.dumps(previous_summary, indent=2) if previous_summary else "No previous run available")

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{base_url}/api/generate", json={
                "model": model,
                "prompt": prompt,
                "stream": False,
            })
            if resp.status_code == 200:
                data = resp.json()
                return {"ok": True, "report": data.get("response", "")}
            else:
                return {"ok": False, "error": f"Ollama returned {resp.status_code}"}
    except httpx.TimeoutException:
        return {"ok": False, "error": "Ollama request timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ===== Cache =====

def load_cached_analysis(result_dir: Path) -> dict | None:
    """Load cached analysis from results/{folder}/analysis.json."""
    cache_path = result_dir / "analysis.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    return None


def save_analysis_cache(result_dir: Path, analysis: dict):
    """Cache analysis results to results/{folder}/analysis.json."""
    cache_path = result_dir / "analysis.json"
    cache_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
