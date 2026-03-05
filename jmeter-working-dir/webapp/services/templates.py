"""Shared Jinja2Templates instance for all routers."""
from fastapi.templating import Jinja2Templates
from services.paths import get_app_dir

TEMPLATE_DIR = get_app_dir() / "templates"

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
