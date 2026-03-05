"""Authentication, access control, and path safety for the webapp."""
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("jmeter_dashboard")

from fastapi import Request
from fastapi.responses import JSONResponse

from services.paths import get_data_dir

_SETTINGS_FILE = get_data_dir() / "settings.json"
_AUTH_DEFAULTS = {"token": "", "cookie_name": "jmeter_token", "cookie_max_age": 86400}


# --- Path safety ---

def safe_join(base: Path, user_input: str) -> Path | None:
    """Safely join user-supplied path to a base directory.

    Returns resolved Path if within base, None if traversal detected.
    """
    try:
        resolved = (base / user_input).resolve()
        base_resolved = base.resolve()
        if resolved == base_resolved or str(resolved).startswith(str(base_resolved) + os.sep):
            return resolved
    except (ValueError, OSError):
        pass
    return None


# --- Token hashing ---

def hash_token(token: str) -> str:
    """SHA-256 hash of a token. Returns hex digest."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _is_sha256_hex(value: str) -> bool:
    """Check if a string looks like a SHA-256 hex digest (64 hex chars)."""
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def migrate_token_if_needed():
    """One-time migration: if token exists and is not a SHA-256 hash, hash it."""
    if not _SETTINGS_FILE.exists():
        return
    try:
        data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        token = data.get("auth", {}).get("token", "")
        if token and not _is_sha256_hex(token):
            data["auth"]["token"] = hash_token(token)
            _SETTINGS_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
    except Exception:
        logger.warning("Failed to migrate auth token", exc_info=True)


# --- Auth helpers ---

def is_localhost(request: Request) -> bool:
    """Check if request originates from localhost."""
    host = request.client.host if request.client else ""
    return host in ("127.0.0.1", "::1", "localhost")


def get_auth_config() -> dict:
    """Read auth config from settings.json."""
    if _SETTINGS_FILE.exists():
        try:
            data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            return {**_AUTH_DEFAULTS, **data.get("auth", {})}
        except Exception:
            logger.warning("Failed to load auth config", exc_info=True)
    return {**_AUTH_DEFAULTS}


def get_auth_token() -> str:
    """Read auth_token from settings.json. Empty string = no auth required."""
    return get_auth_config().get("token", "")


def verify_token(token: str) -> bool:
    """Check if the provided token matches the stored hash."""
    stored = get_auth_token()
    if not stored:
        return True
    return hmac.compare_digest(hash_token(token), stored)


def get_access_level(request: Request) -> str:
    """Determine access level: 'admin' or 'viewer'.

    - Localhost -> always admin
    - Valid token cookie -> admin
    - No token configured -> everyone is admin
    - Remote without valid token -> viewer (read-only)
    """
    if is_localhost(request):
        return "admin"

    stored_hash = get_auth_token()
    if not stored_hash:
        return "admin"

    auth_config = get_auth_config()
    cookie_name = auth_config.get("cookie_name", "jmeter_token")
    token = request.cookies.get(cookie_name, "")
    if token and hmac.compare_digest(hash_token(token), stored_hash):
        return "admin"

    return "viewer"


def check_access(request: Request):
    """Return 403 JSONResponse if viewer, None if allowed."""
    if getattr(request.state, "access_level", "viewer") == "viewer":
        return JSONResponse(status_code=403, content={"error": "Access denied — token required"})
    return None
