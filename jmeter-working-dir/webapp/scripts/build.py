"""Build LoadLitmus into a standalone executable.

Usage:
    cd webapp
    python scripts/build.py

Output:
    dist/loadlitmus.exe

Requirements:
    pip install ".[dev]"  (installs pyinstaller)
"""
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

WEBAPP_DIR = Path(__file__).resolve().parent.parent
SPEC_FILE = WEBAPP_DIR / "loadlitmus.spec"
DIST_DIR = WEBAPP_DIR / "dist"
EXE_NAME = "loadlitmus.exe" if sys.platform == "win32" else "loadlitmus"
EXE_PATH = DIST_DIR / EXE_NAME

SMOKE_PORT = 15080
SMOKE_TIMEOUT = 30  # seconds


def step(msg: str):
    print(f"\n{'=' * 60}")
    print(f"  {msg}")
    print(f"{'=' * 60}\n")


def build():
    """Run PyInstaller with the spec file."""
    step("Building with PyInstaller")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        str(SPEC_FILE),
    ]
    result = subprocess.run(cmd, cwd=str(WEBAPP_DIR))
    if result.returncode != 0:
        print("BUILD FAILED")
        sys.exit(1)

    if not EXE_PATH.exists():
        print(f"ERROR: Expected output not found: {EXE_PATH}")
        sys.exit(1)

    size_mb = EXE_PATH.stat().st_size / (1024 * 1024)
    print(f"Built: {EXE_PATH} ({size_mb:.1f} MB)")


def smoke_test():
    """Start the exe, wait for it to serve, verify HTTP 200, then kill it."""
    step("Running smoke test")

    proc = subprocess.Popen(
        [str(EXE_PATH), "serve", "--port", str(SMOKE_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(DIST_DIR),
    )

    url = f"http://127.0.0.1:{SMOKE_PORT}/"
    print(f"Waiting for {url} ...")

    try:
        start = time.time()
        while time.time() - start < SMOKE_TIMEOUT:
            try:
                resp = urllib.request.urlopen(url, timeout=2)
                status = resp.getcode()
                if status in (200, 307):
                    print(f"Smoke test PASSED (HTTP {status})")
                    return
            except (urllib.error.URLError, ConnectionRefusedError, OSError):
                time.sleep(1)

        print(f"Smoke test FAILED — no response within {SMOKE_TIMEOUT}s")
        sys.exit(1)
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def print_summary():
    """Print build summary."""
    sys.path.insert(0, str(WEBAPP_DIR))
    from __version__ import __version__

    size_mb = EXE_PATH.stat().st_size / (1024 * 1024)

    step("Build Summary")
    print(f"  Version:  {__version__}")
    print(f"  Output:   {EXE_PATH}")
    print(f"  Size:     {size_mb:.1f} MB")
    print(f"  Platform: {sys.platform}")
    print(f"  Python:   {sys.version.split()[0]}")
    print()


if __name__ == "__main__":
    build()
    smoke_test()
    print_summary()
