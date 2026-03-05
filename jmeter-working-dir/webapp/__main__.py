"""CLI entry point for LoadLitmus.

Usage:
    loadlitmus              Start the dashboard (default)
    loadlitmus serve        Start the dashboard
    loadlitmus init [path]  Scaffold a new project directory
    loadlitmus --version    Print version and exit
"""
import argparse
import json
import sys
from pathlib import Path

# Ensure the webapp directory is on sys.path so sibling modules
# (services, __version__, etc.) are importable when run via python -m webapp.
_webapp_dir = str(Path(__file__).resolve().parent)
if _webapp_dir not in sys.path:
    sys.path.insert(0, _webapp_dir)

from __version__ import __version__


def cmd_serve(args):
    """Start the LoadLitmus web dashboard."""
    import uvicorn
    from services.settings import load_settings

    settings = load_settings()
    server = settings.get("server", {})

    host = server.get("host", "127.0.0.1")
    port = server.get("port", 5080)
    base_path = (server.get("base_path") or "").rstrip("/")

    if server.get("allow_external"):
        host = "0.0.0.0"

    # CLI overrides
    if args.host:
        host = args.host
    if args.port:
        port = args.port

    url = f"http://{host}:{port}{base_path}/"
    print(f"Starting LoadLitmus v{__version__} on {url}")
    if base_path:
        print(f"  Base path: {base_path}")
    if host == "0.0.0.0":
        print("  External access enabled")

    dev_mode = args.dev
    if dev_mode:
        print("  Development mode — auto-reload enabled")
    uvicorn.run("main:app", host=host, port=port, reload=dev_mode)


def cmd_init(args):
    """Scaffold a new LoadLitmus project directory."""
    target = Path(args.path).resolve()

    # Check if project already exists
    markers = ["config.properties", "slaves.txt", "test_plan", "config"]
    existing = [m for m in markers if (target / m).exists()]
    if existing:
        print(f"Project already exists in {target}")
        print(f"  Found: {', '.join(existing)}")
        print("  Skipping init to avoid overwriting existing files.")
        return

    # Create folder structure
    folders = ["config", "test_plan", "test_data", "results"]
    for folder in folders:
        (target / folder).mkdir(parents=True, exist_ok=True)

    # Create slaves.txt (empty JSON array)
    (target / "slaves.txt").write_text("[]", encoding="utf-8")

    # Create config.properties template
    config_template = """\
# LoadLitmus project configuration
# Uncomment and edit the properties below for your test

# test_plan=test_plan/your_test.jmx
# student=10
# rampUp=10
# loop=1
# thinkTime=3000
"""
    (target / "config.properties").write_text(config_template, encoding="utf-8")

    # Create empty vm_config.json
    (target / "config" / "vm_config.json").write_text("{}", encoding="utf-8")

    print(f"Project initialized in {target}")
    print()
    print("  Created:")
    for folder in folders:
        print(f"    {folder}/")
    print("    slaves.txt")
    print("    config.properties")
    print("    config/vm_config.json")
    print()
    print("  Next steps:")
    print(f"    1. Place your .jmx files in {target / 'test_plan'}")
    print("    2. Run: loadlitmus serve")
    print(f"       (or: cd {target} && python -m webapp)")


def main():
    """Parse CLI arguments and dispatch to the appropriate command."""
    parser = argparse.ArgumentParser(
        prog="loadlitmus",
        description="LoadLitmus — performance test dashboard",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"LoadLitmus {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")

    # serve subcommand
    serve_parser = subparsers.add_parser("serve", help="Start the web dashboard")
    serve_parser.add_argument("--host", type=str, default=None, help="Bind host")
    serve_parser.add_argument("--port", type=int, default=None, help="Bind port")
    serve_parser.add_argument("--dev", action="store_true", help="Enable auto-reload")

    # init subcommand
    init_parser = subparsers.add_parser("init", help="Scaffold a new project directory")
    init_parser.add_argument("path", nargs="?", default=".", help="Target directory (default: current)")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    else:
        # Default to serve (no subcommand or explicit 'serve')
        if not hasattr(args, "host"):
            args = parser.parse_args(["serve"])
        cmd_serve(args)


if __name__ == "__main__":
    main()
