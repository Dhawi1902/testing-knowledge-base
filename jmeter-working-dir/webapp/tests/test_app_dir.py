"""Tests for get_app_dir() helper -- frozen exe vs source mode."""
import sys
from pathlib import Path
from unittest.mock import patch

from services.paths import get_app_dir


def test_get_app_dir_source_mode():
    """In source mode (no sys.frozen), returns the webapp/ directory."""
    result = get_app_dir()
    assert result.is_dir()
    assert (result / "main.py").exists()


def test_get_app_dir_frozen_mode(tmp_path):
    """In frozen mode (PyInstaller), returns sys._MEIPASS."""
    with patch.object(sys, "frozen", True, create=True), \
         patch.object(sys, "_MEIPASS", str(tmp_path), create=True):
        result = get_app_dir()
        assert result == tmp_path
