"""Tests for path helpers -- frozen exe vs source mode."""
import sys
from pathlib import Path
from unittest.mock import patch

from services.paths import get_app_dir, get_data_dir


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


def test_get_data_dir_source_mode():
    """In source mode, get_data_dir() returns the same webapp/ directory."""
    result = get_data_dir()
    assert result == get_app_dir()
    assert (result / "main.py").exists()


def test_get_data_dir_frozen_mode(tmp_path):
    """In frozen mode, get_data_dir() returns CWD (not _MEIPASS)."""
    with patch.object(sys, "frozen", True, create=True), \
         patch("services.paths.Path") as MockPath:
        MockPath.cwd.return_value = tmp_path
        result = get_data_dir()
        assert result == tmp_path
        MockPath.cwd.assert_called_once()
