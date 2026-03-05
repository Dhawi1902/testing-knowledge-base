"""Path resolution helpers for source and PyInstaller frozen mode.

Two path contexts exist when running as a frozen exe:
  - App assets (templates, static, config/) live in sys._MEIPASS (temp extraction dir)
  - User data (settings.json, project.json, logs/) live in CWD (where the exe was launched)

In source mode both resolve to the same webapp/ directory.
"""
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """Return the directory containing app assets (templates, static, etc.).

    In source mode: returns the webapp/ directory.
    In PyInstaller frozen mode: returns sys._MEIPASS (temp extraction dir).
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def get_data_dir() -> Path:
    """Return the directory for user data (settings, project config, logs).

    In source mode: returns the webapp/ directory (same as get_app_dir).
    In PyInstaller frozen mode: returns CWD (where the exe was launched).
    """
    if getattr(sys, "frozen", False):
        return Path.cwd()
    return Path(__file__).resolve().parent.parent
