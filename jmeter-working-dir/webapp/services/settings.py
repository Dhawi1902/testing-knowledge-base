"""Settings service — single source of truth for webapp configuration.

Manages settings.json: load, save (atomic), validate, and provide defaults.
Extracted from routers/settings.py to break circular imports and follow
the service-layer pattern used by jmeter.py, jtl_parser.py, etc.
"""

import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger("jmeter_dashboard")

from services.paths import get_data_dir

APP_DIR = get_data_dir()
SETTINGS_FILE = APP_DIR / "settings.json"

DEFAULT_SETTINGS: dict = {
    "theme": "light",
    "sidebar_collapsed": False,
    "server": {
        "host": "127.0.0.1",
        "port": 8080,
        "allow_external": False,
        "base_path": "",
    },
    "runner": {
        "auto_scroll": True,
        "max_log_lines": 1000,
        "confirm_before_stop": True,
    },
    "filter": {
        "sub_results": True,
        "label_pattern": "",
    },
    "report": {
        "granularity": 60000,
        "graphs": {},
    },
    "results": {
        "sort_order": "newest",
    },
    "analysis": {
        "ollama_url": "http://localhost:11434",
        "ollama_model": "llama3.1:8b",
        "ollama_timeout": 120,
    },
    "auth": {
        "token": "",
        "cookie_name": "jmeter_token",
        "cookie_max_age": 86400,
    },
    "monitoring": {
        "grafana_url": "",
        "influxdb_url": "",
    },
}


def atomic_write_json(path: Path | str, data: dict, indent: int = 2) -> None:
    """Write JSON atomically: temp file + os.replace().

    Prevents corruption if the process is killed mid-write.
    Works on both Windows and Unix (os.replace is atomic on same filesystem).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=indent, ensure_ascii=False)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix=f".{path.stem}_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(path))
    except BaseException:
        # Clean up temp file on any failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_settings() -> dict:
    """Load settings.json, merging with defaults for missing keys."""
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            merged = {**DEFAULT_SETTINGS}
            for key, val in data.items():
                if isinstance(val, dict) and isinstance(merged.get(key), dict):
                    merged[key] = {**merged[key], **val}
                elif isinstance(val, list):
                    merged[key] = val
                else:
                    merged[key] = val
            return merged
        except Exception:
            logger.warning("Failed to load settings.json, using defaults", exc_info=True)
    return {**DEFAULT_SETTINGS}


def save_settings(settings: dict) -> None:
    """Save settings to settings.json atomically."""
    atomic_write_json(SETTINGS_FILE, settings)


def validate_settings(settings: dict) -> str | None:
    """Return error message if settings are invalid, else None."""
    server = settings.get("server", {})
    port = server.get("port")
    if port is not None:
        try:
            port = int(port)
            if not (1 <= port <= 65535):
                return "Port must be between 1 and 65535"
        except (ValueError, TypeError):
            return "Port must be a number"
    for key in ("grafana_url", "influxdb_url"):
        url = settings.get("monitoring", {}).get(key, "")
        if url and not url.startswith(("http://", "https://")):
            return f"{key} must start with http:// or https://"
    analysis = settings.get("analysis", {})
    ollama_url = analysis.get("ollama_url", "")
    if ollama_url and not ollama_url.startswith(("http://", "https://")):
        return "Ollama URL must start with http:// or https://"
    timeout = analysis.get("ollama_timeout")
    if timeout is not None:
        try:
            timeout = int(timeout)
            if timeout < 1:
                return "Ollama timeout must be positive"
        except (ValueError, TypeError):
            return "Ollama timeout must be a number"
    return None
