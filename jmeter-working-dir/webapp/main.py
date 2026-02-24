import os
import sys
import subprocess
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.config_parser import load_project_config, auto_detect_project
from services.auth import is_localhost as _is_localhost, get_access_level, get_auth_token, get_auth_config

APP_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
PROJECT_JSON = APP_DIR / "project.json"

# Read base_path from settings (e.g. "/perftest")
from routers.settings import load_settings as _load_settings
_settings = _load_settings()
BASE_PATH = (_settings.get("server", {}).get("base_path") or "").rstrip("/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: auto-detect project structure if project.json missing
    first_run = not PROJECT_JSON.exists()
    if first_run:
        auto_detect_project(PROJECT_JSON)
    app.state.project = load_project_config(PROJECT_JSON)
    app.state.first_run = first_run
    yield


app = FastAPI(title="JMeter Test Dashboard", lifespan=lifespan)

# Mount static files
app.mount(f"{BASE_PATH}/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Make base_path available in all templates as {{ bp }}
templates.env.globals["bp"] = BASE_PATH


# --- Global error handler ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if request.url.path.startswith(f"{BASE_PATH}/api/"):
        return JSONResponse(status_code=500, content={"error": str(exc)})
    # For page requests, return a simple error page
    return templates.TemplateResponse("base.html", {
        "request": request,
        "project_name": "Error",
        "active_page": "",
    }, status_code=500)


# --- First-run setup redirect ---

@app.get(f"{BASE_PATH}/setup")
async def setup_page(request: Request):
    project = request.app.state.project
    return templates.TemplateResponse("setup.html", {
        "request": request,
        "project": project,
    })


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
        response = JSONResponse(content={"ok": True, "redirect": next_url})
        response.set_cookie(key=cookie_name, value=token, max_age=max_age, httponly=True)
        return response
    return JSONResponse(content={"ok": False, "error": "Invalid token"})


# --- Complete setup endpoint ---

@app.post(f"{BASE_PATH}/api/setup/complete")
async def complete_setup(request: Request):
    request.app.state.first_run = False
    return {"ok": True}


def get_project(request: Request) -> dict:
    """Get project config from app state."""
    return request.app.state.project


# --- Server restart ---

@app.post(f"{BASE_PATH}/api/server/restart")
async def restart_server():
    """Restart the server with updated settings."""
    from routers.settings import load_settings
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
from routers import dashboard, config, test_data, test_plans, results, scripts, settings  # noqa: E402


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
for _mod in [dashboard, config, test_data, test_plans, results, scripts, settings]:
    if hasattr(_mod, 'templates'):
        _mod.templates.env.globals["bp"] = BASE_PATH
        _patch_template_response(_mod.templates)

app.include_router(dashboard.router, prefix=BASE_PATH)
app.include_router(config.router, prefix=BASE_PATH)
app.include_router(test_data.router, prefix=BASE_PATH)
app.include_router(test_plans.router, prefix=BASE_PATH)
app.include_router(results.router, prefix=BASE_PATH)
app.include_router(scripts.router, prefix=BASE_PATH)
app.include_router(settings.router, prefix=BASE_PATH)


# --- Root redirect when base_path is set ---
if BASE_PATH:
    @app.get("/")
    async def root_redirect():
        return RedirectResponse(url=f"{BASE_PATH}/")
