"""Tests for the CLI interface (argparse commands)."""
import json
import subprocess
import sys
from pathlib import Path

# python -m webapp must run from the parent of the webapp package
WEBAPP_DIR = str(Path(__file__).resolve().parent.parent.parent)


def test_version_flag():
    """--version prints version and exits."""
    result = subprocess.run(
        [sys.executable, "-m", "webapp", "--version"],
        capture_output=True, text=True, cwd=WEBAPP_DIR,
    )
    assert result.returncode == 0
    assert "LoadLitmus" in result.stdout
    assert "0.5.0" in result.stdout


def test_init_creates_project_structure(tmp_path):
    """init command creates the expected folder structure."""
    result = subprocess.run(
        [sys.executable, "-m", "webapp", "init", str(tmp_path)],
        capture_output=True, text=True, cwd=WEBAPP_DIR,
    )
    assert result.returncode == 0

    # Check folders exist
    assert (tmp_path / "config").is_dir()
    assert (tmp_path / "test_plan").is_dir()
    assert (tmp_path / "test_data").is_dir()
    assert (tmp_path / "results").is_dir()

    # Check files exist
    assert (tmp_path / "slaves.txt").exists()
    assert (tmp_path / "config.properties").exists()
    assert (tmp_path / "config" / "vm_config.json").exists()

    # slaves.txt should be empty JSON array
    content = (tmp_path / "slaves.txt").read_text()
    assert json.loads(content) == []


def test_init_skips_existing_project(tmp_path):
    """init warns and skips if project files already exist."""
    (tmp_path / "config.properties").write_text("existing=true")

    result = subprocess.run(
        [sys.executable, "-m", "webapp", "init", str(tmp_path)],
        capture_output=True, text=True, cwd=WEBAPP_DIR,
    )
    assert result.returncode == 0
    assert "already" in result.stdout.lower()

    # Original file should be untouched
    assert (tmp_path / "config.properties").read_text() == "existing=true"


def test_help_flag():
    """--help prints usage and exits."""
    result = subprocess.run(
        [sys.executable, "-m", "webapp", "--help"],
        capture_output=True, text=True, cwd=WEBAPP_DIR,
    )
    assert result.returncode == 0
    assert "serve" in result.stdout
    assert "init" in result.stdout


def test_init_default_cwd(tmp_path):
    """init with no path uses current directory."""
    # We need PYTHONPATH so the webapp package is importable,
    # while cwd is the tmp_path (the target for init).
    env = {**subprocess.os.environ, "PYTHONPATH": WEBAPP_DIR}
    result = subprocess.run(
        [sys.executable, "-m", "webapp", "init"],
        capture_output=True, text=True, cwd=str(tmp_path), env=env,
    )
    assert result.returncode == 0
    assert (tmp_path / "config").is_dir()
    assert (tmp_path / "slaves.txt").exists()
