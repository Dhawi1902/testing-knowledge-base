import asyncio
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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


async def check_all_slaves(slave_ips: list[str], ssh_config: dict) -> list[dict]:
    """Check status of all slaves in parallel."""
    tasks = [check_slave_status(ip, ssh_config) for ip in slave_ips]
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


async def start_all_servers(slave_ips: list[str], ssh_config: dict) -> list[dict]:
    """Start JMeter servers on all slaves in parallel."""
    tasks = [start_jmeter_server(ip, ssh_config) for ip in slave_ips]
    return await asyncio.gather(*tasks)


async def stop_all_servers(slave_ips: list[str], ssh_config: dict) -> list[dict]:
    """Stop JMeter servers on all slaves in parallel."""
    tasks = [stop_jmeter_server(ip, ssh_config) for ip in slave_ips]
    return await asyncio.gather(*tasks)
