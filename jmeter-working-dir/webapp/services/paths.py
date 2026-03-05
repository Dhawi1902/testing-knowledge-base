"""Path resolution helpers for source and PyInstaller frozen mode."""
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """Return the directory containing app assets (templates, static, etc.).

    In source mode: returns the directory containing main.py (webapp/).
    In PyInstaller frozen mode: returns sys._MEIPASS (temp extraction dir).
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent
