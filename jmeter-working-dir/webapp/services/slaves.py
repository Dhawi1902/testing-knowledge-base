import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_executor = ThreadPoolExecutor(max_workers=20)


def build_ssh_configs(slaves: list[dict], vm_config: dict) -> dict[str, dict]:
    """Build per-slave SSH configs by merging global defaults with per-slave overrides.
    Returns {ip: merged_ssh_config}.

    The slave_dir field (default ~/jmeter-slave/) is the base directory on slaves.
    dest_path and jmeter_scripts are derived from slave_dir if not explicitly set.
    All paths use ~ which resolves via $HOME on the remote machine.
    """
    global_ssh = vm_config.get("ssh_config", {})
    global_scripts = vm_config.get("jmeter_scripts", {})
    global_heap = vm_config.get("jmeter_heap", {})
    slave_dir = vm_config.get("slave_dir", "~/jmeter-slave")
    # Normalize: ensure no trailing slash for consistent joining
    slave_dir = slave_dir.rstrip("/")

    configs = {}
    for s in slaves:
        ip = s["ip"]
        overrides = s.get("overrides", {})
        merged = {**global_ssh}

        # Per-slave overrides for SSH fields
        for key in ("user", "password", "dest_path", "jmeter_path", "key_file"):
            if overrides.get(key):
                merged[key] = overrides[key]

        # Per-slave slave_dir override
        effective_slave_dir = overrides.get("slave_dir", slave_dir).rstrip("/")
        merged["slave_dir"] = effective_slave_dir

        # Derive dest_path from slave_dir if not explicitly set
        if not merged.get("dest_path"):
            merged["dest_path"] = f"{effective_slave_dir}/test_data/"

        # Derive jmeter_scripts from slave_dir if not explicitly set
        if global_scripts:
            merged["jmeter_scripts"] = {**global_scripts}
        else:
            merged["jmeter_scripts"] = {
                "start": f"{effective_slave_dir}/start-slave.sh",
                "stop": f"{effective_slave_dir}/stop-slave.sh",
            }

        # Heap settings (global + per-slave override)
        if global_heap:
            merged["jmeter_heap"] = {**global_heap}
        if overrides.get("jmeter_heap"):
            merged.setdefault("jmeter_heap", {})
            merged["jmeter_heap"].update(overrides["jmeter_heap"])

        # Per-slave OS type (default from global)
        merged.setdefault("os", vm_config.get("os", "linux"))
        if overrides.get("os"):
            merged["os"] = overrides["os"]

        configs[ip] = merged
    return configs


def _ssh_connect(ip: str, ssh_config: dict, timeout: int = 10):
    """Create and return a connected paramiko SSH client.
    Supports both password and key-based authentication (F7).
    """
    import paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs = {
        "hostname": ip,
        "username": ssh_config.get("user", "root"),
        "timeout": timeout,
    }
    key_file = ssh_config.get("key_file", "")
    if key_file and Path(key_file).exists():
        connect_kwargs["key_filename"] = key_file
    else:
        connect_kwargs["password"] = ssh_config.get("password", "")
    client.connect(**connect_kwargs)
    return client


def _ssh_connect_test(ip: str, ssh_config: dict, timeout: int = 5) -> dict:
    """Test SSH connectivity to a slave. Returns status dict."""
    try:
        client = _ssh_connect(ip, ssh_config, timeout)
        client.close()
        return {"ip": ip, "status": "up", "error": None}
    except Exception:
        return {"ip": ip, "status": "down", "error": "SSH connection failed"}


def _run_ssh_command(ip: str, ssh_config: dict, command: str, timeout: int = 30) -> dict:
    """Run a command on a slave via SSH."""
    try:
        client = _ssh_connect(ip, ssh_config)
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")
        exit_code = stdout.channel.recv_exit_status()
        client.close()
        return {"ip": ip, "ok": exit_code == 0, "output": output, "error": error, "exit_code": exit_code}
    except Exception:
        return {"ip": ip, "ok": False, "output": "", "error": "SSH command failed", "exit_code": -1}


async def check_slave_status(ip: str, ssh_config: dict) -> dict:
    """Async wrapper for SSH connectivity test."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _ssh_connect_test, ip, ssh_config)


async def check_all_slaves(slave_ips: list[str], ssh_configs: dict[str, dict]) -> list[dict]:
    """Check status of all slaves in parallel. ssh_configs maps IP → config."""
    tasks = [check_slave_status(ip, ssh_configs.get(ip, {})) for ip in slave_ips]
    return await asyncio.gather(*tasks)


def _auto_start_command(ssh_config: dict) -> str:
    """Build an auto-generated JMeter server start command from config (F5)."""
    jmeter_path = ssh_config.get("jmeter_path", "")
    os_type = ssh_config.get("os", "linux")
    if not jmeter_path:
        return ""
    if os_type == "windows":
        return f'{jmeter_path}\\bin\\jmeter-server.bat'
    return f'{jmeter_path}/bin/jmeter-server'


def _auto_stop_command(ssh_config: dict) -> str:
    """Build an auto-generated JMeter server stop command from config (F5)."""
    os_type = ssh_config.get("os", "linux")
    if os_type == "windows":
        return 'taskkill /f /im jmeter-server.bat 2>nul & taskkill /f /im java.exe 2>nul || exit /b 0'
    return 'pkill -f jmeter-server || true'


async def start_jmeter_server(ip: str, ssh_config: dict) -> dict:
    """Start JMeter server on a slave. Uses configured script or auto-generates from jmeter_path."""
    script = ssh_config.get("jmeter_scripts", {}).get("start", "")
    if not script:
        script = _auto_start_command(ssh_config)
    if not script:
        return {"ip": ip, "ok": False, "error": "No start script or JMeter path configured"}
    os_type = ssh_config.get("os", "linux")
    if os_type == "windows":
        cmd = f'start /b {script}'
    else:
        cmd = f'nohup {script} > /dev/null 2>&1 &'
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _run_ssh_command, ip, ssh_config, cmd)


async def stop_jmeter_server(ip: str, ssh_config: dict) -> dict:
    """Stop JMeter server on a slave. Uses configured script or auto-generates."""
    script = ssh_config.get("jmeter_scripts", {}).get("stop", "")
    if not script:
        script = _auto_stop_command(ssh_config)
    if not script:
        return {"ip": ip, "ok": False, "error": "No stop script configured"}
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _run_ssh_command, ip, ssh_config, script)


async def start_all_servers(slave_ips: list[str], ssh_configs: dict[str, dict]) -> list[dict]:
    """Start JMeter servers on all slaves in parallel. ssh_configs maps IP → config."""
    tasks = [start_jmeter_server(ip, ssh_configs.get(ip, {})) for ip in slave_ips]
    return await asyncio.gather(*tasks)


async def stop_all_servers(slave_ips: list[str], ssh_configs: dict[str, dict]) -> list[dict]:
    """Stop JMeter servers on all slaves in parallel. ssh_configs maps IP → config."""
    tasks = [stop_jmeter_server(ip, ssh_configs.get(ip, {})) for ip in slave_ips]
    return await asyncio.gather(*tasks)


# --- File Distribution ---

def _scp_upload(ip: str, ssh_config: dict, local_path: Path, remote_dir: str) -> dict:
    """Upload a file to a slave via SCP."""
    try:
        from scp import SCPClient

        client = _ssh_connect(ip, ssh_config)
        # Ensure remote dir exists
        client.exec_command(f"mkdir -p {remote_dir}")

        with SCPClient(client.get_transport()) as scp:
            scp.put(str(local_path), remote_dir)

        # Verify
        fname = local_path.name
        _, stdout, _ = client.exec_command(f"ls -lh {remote_dir}{fname}")
        verification = stdout.read().decode().strip()
        client.close()

        return {"ip": ip, "file": fname, "ok": True, "detail": verification or "uploaded"}
    except Exception:
        return {"ip": ip, "file": local_path.name, "ok": False, "detail": "SCP upload failed"}


def _distribute_items(
    slave_ips: list[str], ssh_configs: dict[str, dict], items: list[dict],
    data_dir: Path,
) -> list[dict]:
    """Process a list of distribution items, each with its own mode.

    Each item: {"file_path": Path, "mode": "copy"|"split", "offset": int, "size": int}
    ssh_configs maps IP → merged SSH config (including dest_path).
    """
    import numpy as np
    import pandas as pd

    results = []
    num_slaves = len(slave_ips)
    slaves_data_dir = data_dir / "slaves_data"

    for item in items:
        fpath = item["file_path"]
        mode = item["mode"]

        if mode == "copy":
            for ip in slave_ips:
                cfg = ssh_configs.get(ip, {})
                remote_dir = cfg.get("dest_path", "/tmp/")
                if not remote_dir.endswith("/"):
                    remote_dir += "/"
                r = _scp_upload(ip, cfg, fpath, remote_dir)
                results.append(r)
        else:
            # split
            offset = item.get("offset", 0)
            size = item.get("size", 0)
            try:
                df = pd.read_csv(fpath, dtype=str)
            except Exception as e:
                results.append({"ip": "all", "file": fpath.name, "ok": False, "detail": f"Failed to read CSV: {e}"})
                continue

            subset = df.iloc[offset:offset + size] if size > 0 else df.iloc[offset:]
            if subset.empty:
                results.append({"ip": "all", "file": fpath.name, "ok": False, "detail": f"No rows after offset={offset}, size={size} (total={len(df)})"})
                continue

            slaves_data_dir.mkdir(parents=True, exist_ok=True)
            indices = np.array_split(range(len(subset)), num_slaves)
            for i, ip in enumerate(slave_ips):
                cfg = ssh_configs.get(ip, {})
                remote_dir = cfg.get("dest_path", "/tmp/")
                if not remote_dir.endswith("/"):
                    remote_dir += "/"
                chunk = subset.iloc[indices[i]]
                vm_dir = slaves_data_dir / ip
                vm_dir.mkdir(parents=True, exist_ok=True)
                local_chunk = vm_dir / fpath.name
                chunk.to_csv(local_chunk, index=False)

                r = _scp_upload(ip, cfg, local_chunk, remote_dir)
                r["rows"] = len(chunk)
                results.append(r)

    return results


async def distribute_files(
    slave_ips: list[str], ssh_configs: dict[str, dict], items: list[dict], data_dir: Path,
) -> list[dict]:
    """Distribute files to slaves. Each item has its own mode/offset/size.
    ssh_configs maps IP → merged SSH config.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor, _distribute_items,
        slave_ips, ssh_configs, items, data_dir,
    )
