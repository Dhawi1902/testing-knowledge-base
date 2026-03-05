"""Entry point: python -m webapp"""
import sys
import uvicorn

from services.settings import load_settings

if __name__ == "__main__":
    settings = load_settings()
    server = settings.get("server", {})

    host = server.get("host", "127.0.0.1")
    port = server.get("port", 5080)
    base_path = (server.get("base_path") or "").rstrip("/")

    if server.get("allow_external"):
        host = "0.0.0.0"

    # Allow CLI overrides: python -m webapp --port 9000 --host 0.0.0.0
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
        elif arg == "--host" and i + 1 < len(args):
            host = args[i + 1]

    url = f"http://{host}:{port}{base_path}/"
    print(f"Starting LoadLitmus on {url}")
    if base_path:
        print(f"  Base path: {base_path}")
    if host == "0.0.0.0":
        print("  External access enabled — accessible from other machines on the network")

    dev_mode = "--dev" in args or "--reload" in args
    if dev_mode:
        print("  Development mode — auto-reload enabled")
    uvicorn.run("main:app", host=host, port=port, reload=dev_mode)
