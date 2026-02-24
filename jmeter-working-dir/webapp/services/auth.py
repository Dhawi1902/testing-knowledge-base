"""Authentication and access control for the webapp."""
from fastapi import Request


def is_localhost(request: Request) -> bool:
    """Check if request originates from localhost."""
    host = request.client.host if request.client else ""
    return host in ("127.0.0.1", "::1", "localhost")


def get_auth_config() -> dict:
    """Read auth config from settings.json."""
    from routers.settings import load_settings
    settings = load_settings()
    return settings.get("auth", {})


def get_auth_token() -> str:
    """Read auth_token from settings.json. Empty string = no auth required."""
    return get_auth_config().get("token", "")


def verify_token(token: str) -> bool:
    """Check if the provided token matches the configured one."""
    expected = get_auth_token()
    if not expected:
        return True
    return token == expected


def get_access_level(request: Request) -> str:
    """Determine access level: 'admin' or 'viewer'.

    - Localhost -> always admin
    - Valid token cookie -> admin
    - No token configured -> everyone is admin
    - Remote without valid token -> viewer (read-only)
    """
    if is_localhost(request):
        return "admin"

    expected_token = get_auth_token()
    if not expected_token:
        return "admin"

    auth_config = get_auth_config()
    cookie_name = auth_config.get("cookie_name", "jmeter_token")
    token = request.cookies.get(cookie_name, "")
    if token and token == expected_token:
        return "admin"

    return "viewer"
