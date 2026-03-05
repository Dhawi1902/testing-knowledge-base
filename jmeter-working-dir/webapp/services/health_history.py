"""Health history persistence — stores slave status checks to JSON (#31).

Keeps last MAX_ENTRIES checks per slave. Each entry has:
  {timestamp, status, cpu_percent, ram_percent}
"""

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger("jmeter_dashboard")

MAX_ENTRIES = 50
_HISTORY_FILENAME = "health_history.json"


def _get_history_path(config_dir: Path) -> Path:
    """Return path to health_history.json in the config directory."""
    return config_dir / _HISTORY_FILENAME


def load_health_history(config_dir: Path) -> dict[str, list[dict]]:
    """Load health history from JSON file. Returns {ip: [entries]}."""
    path = _get_history_path(config_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        logger.warning("Failed to load health history", exc_info=True)
    return {}


def save_health_history(config_dir: Path, history: dict[str, list[dict]]) -> None:
    """Save health history to JSON file."""
    path = _get_history_path(config_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2), encoding="utf-8")


def record_status_check(
    config_dir: Path,
    status_results: list[dict],
    resource_data: dict[str, dict] | None = None,
) -> dict[str, list[dict]]:
    """Record a status check with optional resource data.

    status_results: list of {ip, status, ...} from check_all_slaves
    resource_data: optional {ip: {cpu_percent, ram_percent, ...}} from resource check

    Returns the updated history.
    """
    history = load_health_history(config_dir)
    ts = time.time()
    resource_data = resource_data or {}

    for result in status_results:
        ip = result.get("ip", "")
        if not ip:
            continue
        entry = {
            "timestamp": ts,
            "status": result.get("status", "unknown"),
        }
        # Add resource data if available
        res = resource_data.get(ip, {})
        if res.get("ok"):
            entry["cpu_percent"] = res.get("cpu_percent")
            entry["ram_percent"] = res.get("ram_percent")

        if ip not in history:
            history[ip] = []
        history[ip].append(entry)
        # Trim to max entries
        if len(history[ip]) > MAX_ENTRIES:
            history[ip] = history[ip][-MAX_ENTRIES:]

    save_health_history(config_dir, history)
    return history
