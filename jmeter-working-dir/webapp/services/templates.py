"""Shared Jinja2Templates instance for all routers."""
from pathlib import Path
from fastapi.templating import Jinja2Templates

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
