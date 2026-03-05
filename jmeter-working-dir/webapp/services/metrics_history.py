"""Metrics history — stores recent agent metrics for chart backfill.

Keeps last MAX_ENTRIES_PER_SLAVE entries per slave, dropping anything
older than MAX_AGE_SECONDS. Stored in metrics_history.json in the
config directory, same pattern as health_history.py.
"""

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger("jmeter_dashboard")

MAX_ENTRIES_PER_SLAVE = 60  # ~10 min at 10s, ~30 min at 30s
MAX_AGE_SECONDS = 600       # drop entries older than 10 minutes
_FILENAME = "metrics_history.json"

_METRIC_KEYS = (
    "cpu_percent", "ram_percent", "ram_used_mb", "ram_total_mb",
    "disk_percent", "disk_used_gb", "disk_total_gb", "load_1m",
    "net_rx_bytes", "net_tx_bytes", "jvm_rss_mb", "jvm_threads",
    "jmeter_running",
)


def _path(config_dir: Path) -> Path:
    return config_dir / _FILENAME


def load_metrics_history(config_dir: Path) -> dict[str, list[dict]]:
    """Load metrics history from JSON file. Returns {ip: [entries]}."""
    path = _path(config_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        logger.warning("Failed to load metrics history", exc_info=True)
    return {}


def record_metrics(config_dir: Path, results: list[dict]) -> None:
    """Record metrics poll results. Trims old entries and saves to disk."""
    history = load_metrics_history(config_dir)
    ts = time.time()
    cutoff = ts - MAX_AGE_SECONDS

    for r in results:
        ip = r.get("ip", "")
        if not ip or not r.get("ok"):
            continue
        entry: dict = {"ts": ts}
        for key in _METRIC_KEYS:
            if r.get(key) is not None:
                entry[key] = r[key]
        if ip not in history:
            history[ip] = []
        history[ip].append(entry)
        # Trim: drop old + cap count
        history[ip] = [
            e for e in history[ip] if e["ts"] > cutoff
        ][-MAX_ENTRIES_PER_SLAVE:]

    path = _path(config_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history), encoding="utf-8")
