import logging
import logging.handlers
import os
import secrets
import sys
import subprocess
import asyncio
import time
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.config_parser import load_project_config, auto_detect_project
from services.auth import (
    is_localhost as _is_localhost,
    get_access_level,
    get_auth_token,
    get_auth_config,
    migrate_token_if_needed,
    hash_token,
)

APP_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
PROJECT_JSON = APP_DIR / "project.json"

# --- Logging setup (G1) ---
LOG_DIR = APP_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("jmeter_dashboard")
logger.setLevel(logging.INFO)

_handler = logging.handlers.RotatingFileHandler(
    LOG_DIR / "app.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8",
)
_handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S",
))
logger.addHandler(_handler)

# Read base_path from settings (e.g. "/perftest")
from services.settings import load_settings as _load_settings
_settings = _load_settings()
BASE_PATH = (_settings.get("server", {}).get("base_path") or "").rstrip("/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting JMeter Dashboard")
    migrate_token_if_needed()

    # Startup: auto-detect project structure if project.json missing
    first_run = not PROJECT_JSON.exists()
    if first_run:
        auto_detect_project(PROJECT_JSON)
    app.state.project = load_project_config(PROJECT_JSON)
    app.state.first_run = first_run

    # On first run, generate a secure access token
    if first_run:
        plain_token = secrets.token_urlsafe(32)
        app.state.setup_token = plain_token
        # Save the hash to settings.json
        from services.settings import load_settings as _load_s, save_settings as _save_s
        settings = _load_s()
        settings.setdefault("auth", {})["token"] = hash_token(plain_token)
        _save_s(settings)
        # Print to console as backup
        print(f"\n{'=' * 60}")
        print(f"  FIRST RUN — Access Token: {plain_token}")
        print(f"  Save this! It will not be shown again.")
        print(f"{'=' * 60}\n")
    else:
        app.state.setup_token = None

    yield


app = FastAPI(
    title="JMeter Test Dashboard",
    lifespan=lifespan,
    docs_url=f"{BASE_PATH}/docs",
    redoc_url=f"{BASE_PATH}/redoc",
    openapi_url=f"{BASE_PATH}/openapi.json",
)

# Mount static files
app.mount(f"{BASE_PATH}/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Make base_path available in all templates as {{ bp }}
templates.env.globals["bp"] = BASE_PATH

# Cache-busting version from file modification times
_static_files = [STATIC_DIR / "css" / "style.css", STATIC_DIR / "js" / "app.js"]
_asset_version = hex(int(sum(f.stat().st_mtime for f in _static_files if f.exists())))[2:][:8]
templates.env.globals["asset_v"] = _asset_version


# --- Global error handler ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    if request.url.path.startswith(f"{BASE_PATH}/api/"):
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})
    return templates.TemplateResponse("base.html", {
        "request": request,
        "project_name": "Error",
        "active_page": "",
    }, status_code=500)


# --- First-run setup redirect ---

@app.get(f"{BASE_PATH}/setup")
async def setup_page(request: Request):
    project = request.app.state.project
    setup_token = getattr(request.app.state, "setup_token", None)
    return templates.TemplateResponse("setup.html", {
        "request": request,
        "project": project,
        "setup_token": setup_token,
    })


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log API requests with method, path, status, and duration."""
    path = request.url.path
    if path.startswith(f"{BASE_PATH}/static"):
        return await call_next(request)
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    if path.startswith(f"{BASE_PATH}/api/"):
        logger.info("%s %s %d %.0fms", request.method, path, response.status_code, ms)
    return response


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Add security headers to all non-static responses."""
    response = await call_next(request)
    if not request.url.path.startswith(f"{BASE_PATH}/static"):
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "connect-src 'self' ws: wss:"
        )
    return response


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Set access_level and is_localhost on every request.
    Redirect remote users to token page if auth_token is configured."""
    path = request.url.path

    # Skip for static files and the token page itself
    if path.startswith(f"{BASE_PATH}/static") or path == f"{BASE_PATH}/token":
        response = await call_next(request)
        return response

    # Set auth state on request
    request.state.is_localhost = _is_localhost(request)
    request.state.access_level = get_access_level(request)

    # If remote, token required, no valid token, and it's a page request -> redirect to token page
    auth_token = get_auth_token()
    if (
        auth_token
        and not request.state.is_localhost
        and request.state.access_level == "viewer"
        and not path.startswith(f"{BASE_PATH}/api/")
        and path != f"{BASE_PATH}/setup"
    ):
        return RedirectResponse(url=f"{BASE_PATH}/token?next={path}")

    response = await call_next(request)
    return response


@app.middleware("http")
async def first_run_redirect(request: Request, call_next):
    # Skip for static files, API calls, and the setup page itself
    path = request.url.path
    if (
        request.app.state.first_run
        and not path.startswith(f"{BASE_PATH}/static")
        and not path.startswith(f"{BASE_PATH}/api/")
        and path != f"{BASE_PATH}/setup"
    ):
        return RedirectResponse(url=f"{BASE_PATH}/setup")
    response = await call_next(request)
    return response


# --- Token auth page ---

@app.get(f"{BASE_PATH}/token")
async def token_page(request: Request):
    return templates.TemplateResponse("token.html", {
        "request": request,
    })


@app.post(f"{BASE_PATH}/api/auth/verify")
async def verify_token_route(request: Request):
    from services.auth import verify_token
    body = await request.json()
    token = body.get("token", "")
    if verify_token(token):
        auth_config = get_auth_config()
        cookie_name = auth_config.get("cookie_name", "jmeter_token")
        max_age = auth_config.get("cookie_max_age", 86400)
        next_url = request.query_params.get("next", f"{BASE_PATH}/")
        if "://" in next_url or next_url.startswith("//"):
            next_url = f"{BASE_PATH}/"
        elif BASE_PATH and not next_url.startswith(BASE_PATH):
            next_url = f"{BASE_PATH}/"
        response = JSONResponse(content={"ok": True, "redirect": next_url})
        response.set_cookie(key=cookie_name, value=token, max_age=max_age, httponly=True, samesite="strict")
        return response
    return JSONResponse(content={"ok": False, "error": "Invalid token"})


# --- Complete setup endpoint ---

@app.post(f"{BASE_PATH}/api/setup/complete")
async def complete_setup(request: Request):
    request.app.state.first_run = False
    request.app.state.setup_token = None  # Clear plain-text token from memory
    return {"ok": True}


def get_project(request: Request) -> dict:
    """Get project config from app state."""
    return request.app.state.project


# --- Server restart ---

@app.post(f"{BASE_PATH}/api/server/restart")
async def restart_server(request: Request):
    """Restart the server with updated settings."""
    from services.auth import check_access
    denied = check_access(request)
    if denied:
        return denied
    from services.settings import load_settings
    settings = load_settings()
    server = settings.get("server", {})
    host = "0.0.0.0" if server.get("allow_external") else server.get("host", "127.0.0.1")
    port = str(server.get("port", 8080))

    # Spawn new server process, then exit current one
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", host, "--port", port],
        cwd=str(APP_DIR),
    )

    # Give the response time to send, then exit
    async def _shutdown():
        await asyncio.sleep(1)
        os._exit(0)

    asyncio.create_task(_shutdown())
    return {"ok": True, "message": f"Restarting on {host}:{port}"}


# Import and include routers
from routers import dashboard, config, test_data, test_plans, results, settings, extensions  # noqa: E402


# --- Patch templates to auto-inject auth context ---

def _patch_template_response(tmpl):
    """Wrap TemplateResponse to auto-inject is_localhost and access_level."""
    _orig = tmpl.TemplateResponse

    def _wrapped(name, context, **kwargs):
        req = context.get("request")
        if req and hasattr(req, "state"):
            context.setdefault("access_level", getattr(req.state, "access_level", "viewer"))
            context.setdefault("is_localhost", getattr(req.state, "is_localhost", False))
        return _orig(name, context, **kwargs)

    tmpl.TemplateResponse = _wrapped


# Set bp (base path) global and auth context on all template instances
_patch_template_response(templates)
for _mod in [dashboard, config, test_data, test_plans, results, settings, extensions]:
    if hasattr(_mod, 'templates'):
        _mod.templates.env.globals["bp"] = BASE_PATH
        _mod.templates.env.globals["asset_v"] = _asset_version
        _patch_template_response(_mod.templates)

app.include_router(dashboard.router, prefix=BASE_PATH)
app.include_router(config.router, prefix=BASE_PATH)
app.include_router(test_data.router, prefix=BASE_PATH)
app.include_router(test_plans.router, prefix=BASE_PATH)
app.include_router(results.router, prefix=BASE_PATH)
app.include_router(settings.router, prefix=BASE_PATH)
app.include_router(extensions.router, prefix=BASE_PATH)


# --- Root redirect when base_path is set ---
if BASE_PATH:
    @app.get("/")
    async def root_redirect():
        return RedirectResponse(url=f"{BASE_PATH}/")
