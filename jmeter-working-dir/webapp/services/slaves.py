import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

_executor = ThreadPoolExecutor(max_workers=20)


def _ssh_connect_test(ip: str, ssh_config: dict, timeout: int = 5) -> dict:
    """Test SSH connectivity to a slave. Returns status dict."""
    try:
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            ip,
            username=ssh_config.get("user", "root"),
            password=ssh_config.get("password", ""),
            timeout=timeout,
        )
        client.close()
        return {"ip": ip, "status": "up", "error": None}
    except Exception as e:
        return {"ip": ip, "status": "down", "error": str(e)}


def _run_ssh_command(ip: str, ssh_config: dict, command: str, timeout: int = 30) -> dict:
    """Run a command on a slave via SSH."""
    try:
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            ip,
            username=ssh_config.get("user", "root"),
            password=ssh_config.get("password", ""),
            timeout=10,
        )
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")
        exit_code = stdout.channel.recv_exit_status()
        client.close()
        return {"ip": ip, "ok": exit_code == 0, "output": output, "error": error, "exit_code": exit_code}
    except Exception as e:
        return {"ip": ip, "ok": False, "output": "", "error": str(e), "exit_code": -1}


async def check_slave_status(ip: str, ssh_config: dict) -> dict:
    """Async wrapper for SSH connectivity test."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _ssh_connect_test, ip, ssh_config)


async def check_all_slaves(slave_ips: list[str], ssh_configs: dict[str, dict]) -> list[dict]:
    """Check status of all slaves in parallel. ssh_configs maps IP → config."""
    tasks = [check_slave_status(ip, ssh_configs.get(ip, {})) for ip in slave_ips]
    return await asyncio.gather(*tasks)


async def start_jmeter_server(ip: str, ssh_config: dict) -> dict:
    """Start JMeter server on a slave."""
    script = ssh_config.get("jmeter_scripts", {}).get("start", "")
    if not script:
        return {"ip": ip, "ok": False, "error": "Start script not configured"}
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _run_ssh_command, ip, ssh_config, f"nohup {script} > /dev/null 2>&1 &")


async def stop_jmeter_server(ip: str, ssh_config: dict) -> dict:
    """Stop JMeter server on a slave."""
    script = ssh_config.get("jmeter_scripts", {}).get("stop", "")
    if not script:
        return {"ip": ip, "ok": False, "error": "Stop script not configured"}
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
        import paramiko
        from scp import SCPClient

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            ip,
            username=ssh_config.get("user", "root"),
            password=ssh_config.get("password", ""),
            timeout=10,
        )
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
    except Exception as e:
        return {"ip": ip, "file": local_path.name, "ok": False, "detail": str(e)}


def _distribute_items(
    slave_ips: list[str], ssh_configs: dict[str, dict], items: list[dict],
    data_dir: Path,
) -> list[dict]:
    """Process a list of distribution items, each with its own mode.

    Each item: {"file_path": Path, "mode": "copy"|"split", "offset": int, "size": int}
    ssh_configs maps IP → merged SSH config (including dest_path).
    """
    import numpy as np

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
