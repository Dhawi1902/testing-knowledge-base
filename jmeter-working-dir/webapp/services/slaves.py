import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_executor = ThreadPoolExecutor(max_workers=20)

_SAFE_PATH_RE = re.compile(r'^[~/a-zA-Z0-9._/ -]+$')


def _validate_slave_dir(slave_dir: str) -> None:
    """Validate slave_dir has no shell metacharacters."""
    if not slave_dir or not _SAFE_PATH_RE.match(slave_dir):
        raise ValueError(f"Invalid slave_dir: contains unsafe characters: {slave_dir}")


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
    """Test SSH connectivity and JMeter server status on a slave."""
    try:
        client = _ssh_connect(ip, ssh_config, timeout)
        # Check if JMeter server is listening on RMI port 1099
        stdin, stdout, stderr = client.exec_command(
            "ss -tlnp 2>/dev/null | grep -q ':1099 ' && echo running || echo stopped",
            timeout=10,
        )
        output = stdout.read().decode("utf-8", errors="replace").strip()
        stdout.channel.recv_exit_status()
        client.close()
        jmeter_running = "running" in output
        return {
            "ip": ip,
            "status": "up",
            "jmeter": "running" if jmeter_running else "stopped",
            "error": None,
        }
    except Exception:
        return {"ip": ip, "status": "down", "jmeter": "unknown", "error": "SSH connection failed"}


def _ssh_test_detailed(ip: str, ssh_config: dict, timeout: int = 10) -> dict:
    """Detailed SSH test: connect, run 'echo ok', return diagnostic info."""
    try:
        client = _ssh_connect(ip, ssh_config, timeout)
        stdin, stdout, stderr = client.exec_command("echo ok", timeout=10)
        output = stdout.read().decode("utf-8", errors="replace").strip()
        exit_code = stdout.channel.recv_exit_status()
        client.close()
        if exit_code == 0 and "ok" in output:
            return {"ip": ip, "ok": True, "message": "SSH connection successful"}
        return {"ip": ip, "ok": False, "message": f"Command failed (exit {exit_code}): {output}"}
    except Exception as e:
        return {"ip": ip, "ok": False, "message": str(e)}


async def test_ssh_connection(ip: str, ssh_config: dict) -> dict:
    """Async wrapper for detailed SSH test."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _ssh_test_detailed, ip, ssh_config)


def _test_rmi_port(ip: str, port: int = 1099, timeout: int = 5) -> dict:
    """Test if RMI port is reachable from the master machine (#28)."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        if result == 0:
            return {"ip": ip, "ok": True, "message": f"Port {port} is open"}
        return {"ip": ip, "ok": False, "message": f"Port {port} is closed or unreachable"}
    except Exception as e:
        return {"ip": ip, "ok": False, "message": str(e)}


async def test_rmi_port(ip: str, port: int = 1099) -> dict:
    """Async wrapper for RMI port test."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _test_rmi_port, ip, port)


# --- Provisioning (#17, #18, #19, #20) ---

def generate_start_script(ssh_config: dict) -> str:
    """Generate start-slave.sh content using current vm_config settings (#20)."""
    jmeter_home = "/opt/jmeter"
    slave_dir = ssh_config.get("slave_dir", "~/jmeter-slave")
    _validate_slave_dir(slave_dir)
    heap = ssh_config.get("jmeter_heap", {})
    xms = heap.get("xms", "512m")
    xmx = heap.get("xmx", "1g")
    gc_algo = heap.get("gc_algo", "-XX:+UseG1GC -XX:MaxGCPauseMillis=100 -XX:G1ReservePercent=20")
    jvm_args = f"-Xms{xms} -Xmx{xmx} {gc_algo}".strip()

    return f"""#!/bin/bash
# Start JMeter in server (slave) mode — auto-generated by provisioning
# Usage: start-slave.sh [IP]   (IP passed by webapp, or auto-detected)
JMETER_HOME="{jmeter_home}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Use IP from argument if provided, otherwise detect from system
HOST_IP="${{1:-$(hostname -I | awk '{{print $1}}')}}"

# Apply heap settings
export JVM_ARGS="{jvm_args}"

# Set working directory so JMeter's user.dir resolves relative paths correctly
cd "$SCRIPT_DIR"

# Kill any existing jmeter-server process
pkill -f "jmeter-server" 2>/dev/null || true
sleep 1

echo "Starting JMeter slave on ${{HOST_IP}} (user.dir=$SCRIPT_DIR)..."
nohup ${{JMETER_HOME}}/bin/jmeter-server \\
    -Djava.rmi.server.hostname=${{HOST_IP}} \\
    -Dserver.rmi.localport=50000 \\
    -Dserver_port=1099 \\
    -Dserver.rmi.ssl.disable=true \\
    > {slave_dir}/jmeter-slave.log 2>&1 &

echo "JMeter slave PID: $!"
echo "Log: {slave_dir}/jmeter-slave.log"
"""


def generate_stop_script() -> str:
    """Generate stop-slave.sh content (#20)."""
    return """#!/bin/bash
# Stop JMeter slave process — auto-generated by provisioning
echo "Stopping JMeter slave..."
pkill -f "jmeter-server" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "JMeter slave stopped."
else
    echo "No JMeter slave process found."
fi
"""


"""Provision step identifiers — used by frontend component selection."""
PROVISION_STEPS = ["java", "jmeter", "directories", "scripts", "agent", "firewall", "environment"]


def _provision_slave(ip: str, ssh_config: dict, only_steps: list[str] | None = None) -> dict:
    """Run idempotent provisioning on a single slave via SSH (#17, #20).

    Args:
        only_steps: If given, run only these step IDs. None = run all.

    Steps: Java 21, JMeter 5.6.3, dirs, scripts (always refresh), agent, firewall, env.
    Returns {ip, ok, steps: [{id, name, ok, detail}], status: {java, jmeter, scripts, agent, firewall}}.
    """
    run_all = only_steps is None
    run_set = set(only_steps) if only_steps else set(PROVISION_STEPS)

    steps = []
    status = {"java": False, "jmeter": False, "scripts": False, "agent": False, "firewall": False}
    slave_dir = ssh_config.get("slave_dir", "~/jmeter-slave")
    _validate_slave_dir(slave_dir)

    try:
        client = _ssh_connect(ip, ssh_config, timeout=15)
    except Exception as e:
        steps.append({"id": "ssh", "name": "SSH Connect", "ok": False, "detail": str(e)})
        return {"ip": ip, "ok": False, "steps": steps, "status": status}

    def run(cmd, timeout=60):
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        code = stdout.channel.recv_exit_status()
        return out, err, code

    # 1. Install Java 21
    if "java" in run_set:
        out, err, code = run("java -version 2>&1 | head -1")
        if "21" in out:
            steps.append({"id": "java", "name": "Java 21", "ok": True, "detail": "Already installed"})
            status["java"] = True
        else:
            out2, err2, code2 = run("sudo dnf install -y java-21-openjdk java-21-openjdk-devel 2>&1 | tail -3", timeout=180)
            if code2 == 0:
                steps.append({"id": "java", "name": "Java 21", "ok": True, "detail": "Installed"})
                status["java"] = True
            else:
                steps.append({"id": "java", "name": "Java 21", "ok": False, "detail": (err2 or out2)[:200]})

    # 2. Install JMeter 5.6.3
    if "jmeter" in run_set:
        out, err, code = run("test -f /opt/jmeter/bin/jmeter && echo ok")
        if "ok" in out:
            steps.append({"id": "jmeter", "name": "JMeter 5.6.3", "ok": True, "detail": "Already installed at /opt/jmeter"})
            status["jmeter"] = True
        else:
            jmeter_cmds = (
                "cd /opt && "
                "sudo wget -q https://dlcdn.apache.org//jmeter/binaries/apache-jmeter-5.6.3.tgz -O apache-jmeter-5.6.3.tgz && "
                "sudo tar -xzf apache-jmeter-5.6.3.tgz && "
                "sudo ln -sfn /opt/apache-jmeter-5.6.3 /opt/jmeter && "
                "sudo rm -f apache-jmeter-5.6.3.tgz && "
                "echo installed"
            )
            out2, err2, code2 = run(jmeter_cmds, timeout=300)
            if "installed" in out2:
                steps.append({"id": "jmeter", "name": "JMeter 5.6.3", "ok": True, "detail": "Downloaded and installed"})
                status["jmeter"] = True
            else:
                steps.append({"id": "jmeter", "name": "JMeter 5.6.3", "ok": False, "detail": (err2 or out2)[:200]})

    # 3. Create directories
    if "directories" in run_set:
        out, err, code = run(f"mkdir -p {slave_dir}/test_data && echo ok")
        if "ok" in out:
            steps.append({"id": "directories", "name": "Directories", "ok": True, "detail": f"{slave_dir}/test_data/"})
        else:
            steps.append({"id": "directories", "name": "Directories", "ok": False, "detail": (err or out)[:200]})

    # 4. Write start/stop scripts (ALWAYS refresh — #20)
    if "scripts" in run_set:
        start_content = generate_start_script(ssh_config)
        stop_content = generate_stop_script()
        start_cmd = f"cat > {slave_dir}/start-slave.sh << 'ENDSCRIPT'\n{start_content}ENDSCRIPT\nchmod +x {slave_dir}/start-slave.sh && echo ok"
        out, err, code = run(start_cmd)
        stop_cmd = f"cat > {slave_dir}/stop-slave.sh << 'ENDSCRIPT'\n{stop_content}ENDSCRIPT\nchmod +x {slave_dir}/stop-slave.sh && echo ok"
        out2, err2, code2 = run(stop_cmd)
        if "ok" in out and "ok" in out2:
            steps.append({"id": "scripts", "name": "Scripts", "ok": True, "detail": "start-slave.sh + stop-slave.sh written"})
            status["scripts"] = True
        else:
            steps.append({"id": "scripts", "name": "Scripts", "ok": False, "detail": ((err or out) + " " + (err2 or out2))[:200]})

    # 5. Metrics agent (deploy + systemd service)
    if "agent" in run_set:
        agent_port = ssh_config.get("agent_port", 9100)
        try:
            agent_src = Path(__file__).resolve().parent.parent.parent / "utils" / "metrics_agent.py"
            agent_content = agent_src.read_text()
        except Exception:
            agent_content = ""
        if agent_content:
            agent_cmd = (
                f"cat > {slave_dir}/metrics_agent.py << 'ENDAGENT'\n{agent_content}ENDAGENT\n"
                f"chmod +x {slave_dir}/metrics_agent.py && echo ok"
            )
            out, err, code = run(agent_cmd)
            service_content = (
                "[Unit]\\n"
                "Description=JMeter Slave Metrics Agent\\n"
                "After=network.target\\n\\n"
                "[Service]\\n"
                "Type=simple\\n"
                f"User={ssh_config.get('user', 'opc')}\\n"
                f"ExecStart=/usr/bin/python3 {slave_dir}/metrics_agent.py --port {agent_port}\\n"
                "Restart=always\\n"
                "RestartSec=5\\n\\n"
                "[Install]\\n"
                "WantedBy=multi-user.target"
            )
            svc_cmd = (
                f'echo -e "{service_content}" | sudo tee /etc/systemd/system/jmeter-metrics.service > /dev/null && '
                "sudo systemctl daemon-reload && "
                "sudo systemctl enable jmeter-metrics && "
                "sudo systemctl restart jmeter-metrics && "
                "echo svc_ok"
            )
            out2, err2, code2 = run(svc_cmd)
            if "ok" in out and "svc_ok" in out2:
                steps.append({"id": "agent", "name": "Metrics Agent", "ok": True, "detail": f"Deployed on port {agent_port}"})
                status["agent"] = True
            else:
                steps.append({"id": "agent", "name": "Metrics Agent", "ok": False, "detail": ((err or out) + " " + (err2 or out2))[:200]})
        else:
            steps.append({"id": "agent", "name": "Metrics Agent", "ok": False, "detail": "Agent script not found locally"})

    # 6. Firewall (1099 + 50000 + agent port)
    if "firewall" in run_set:
        agent_port = ssh_config.get("agent_port", 9100)
        out, err, code = run(
            "if systemctl is-active --quiet firewalld 2>/dev/null; then "
            "sudo firewall-cmd --permanent --add-port=1099/tcp 2>/dev/null; "
            "sudo firewall-cmd --permanent --add-port=50000-50100/tcp 2>/dev/null; "
            f"sudo firewall-cmd --permanent --add-port={agent_port}/tcp 2>/dev/null; "
            "sudo firewall-cmd --reload 2>/dev/null; "
            "echo firewall_configured; "
            "else echo no_firewalld; fi"
        )
        if "firewall_configured" in out:
            steps.append({"id": "firewall", "name": "Firewall", "ok": True, "detail": f"Ports 1099, 50000-50100, {agent_port} opened"})
            status["firewall"] = True
        elif "no_firewalld" in out:
            steps.append({"id": "firewall", "name": "Firewall", "ok": True, "detail": "firewalld not running (OCI security list handles it)"})
            status["firewall"] = True
        else:
            steps.append({"id": "firewall", "name": "Firewall", "ok": False, "detail": (err or out)[:200]})

    # 7. Set environment variables
    if "environment" in run_set:
        out, err, code = run(
            'grep -q "JMETER_HOME" ~/.bashrc 2>/dev/null || '
            'echo -e "\\n# JMeter environment\\n'
            'export JAVA_HOME=\\$(dirname \\$(dirname \\$(readlink -f \\$(which java))))\\n'
            'export JMETER_HOME=/opt/jmeter\\n'
            'export PATH=\\$JMETER_HOME/bin:\\$PATH" >> ~/.bashrc && echo ok'
        )
        if code == 0:
            steps.append({"id": "environment", "name": "Environment", "ok": True, "detail": "JAVA_HOME + JMETER_HOME in .bashrc"})
        else:
            steps.append({"id": "environment", "name": "Environment", "ok": False, "detail": (err or out)[:200]})

    client.close()

    all_ok = all(s["ok"] for s in steps)
    return {"ip": ip, "ok": all_ok, "steps": steps, "status": status}


async def provision_slave(ip: str, ssh_config: dict, only_steps: list[str] | None = None) -> dict:
    """Async wrapper for provisioning. Pass only_steps to run subset."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _provision_slave, ip, ssh_config, only_steps)


def _check_provision_status(ip: str, ssh_config: dict) -> dict:
    """Check what's installed on a slave (#18). Returns status badges."""
    status = {"java": False, "jmeter": False, "scripts": False, "agent": False, "firewall": False}
    slave_dir = ssh_config.get("slave_dir", "~/jmeter-slave")
    _validate_slave_dir(slave_dir)

    try:
        client = _ssh_connect(ip, ssh_config, timeout=10)
    except Exception:
        return {"ip": ip, "ok": False, "status": status}

    def run(cmd):
        stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        stdout.channel.recv_exit_status()
        return out

    # Java
    out = run("java -version 2>&1 | head -1")
    status["java"] = "21" in out or "17" in out

    # JMeter
    out = run("test -f /opt/jmeter/bin/jmeter && echo ok")
    status["jmeter"] = "ok" in out

    # Scripts
    out = run(f"test -f {slave_dir}/start-slave.sh && test -f {slave_dir}/stop-slave.sh && echo ok")
    status["scripts"] = "ok" in out

    # Metrics agent
    out = run("systemctl is-active jmeter-metrics 2>/dev/null")
    status["agent"] = "active" in out

    # Firewall
    out = run(
        "if systemctl is-active --quiet firewalld 2>/dev/null; then "
        "firewall-cmd --list-ports 2>/dev/null; "
        "else echo no_firewalld; fi"
    )
    status["firewall"] = "no_firewalld" in out or "1099" in out

    client.close()
    return {"ip": ip, "ok": True, "status": status}


async def check_provision_status(ip: str, ssh_config: dict) -> dict:
    """Async wrapper for provision status check."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _check_provision_status, ip, ssh_config)


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
    loop = asyncio.get_running_loop()
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
        # Script handles nohup/backgrounding internally; pass IP so it doesn't need to auto-detect
        cmd = f'bash {script} {ip}'
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _run_ssh_command, ip, ssh_config, cmd)


async def stop_jmeter_server(ip: str, ssh_config: dict) -> dict:
    """Stop JMeter server on a slave. Uses configured script or auto-generates."""
    script = ssh_config.get("jmeter_scripts", {}).get("stop", "")
    if not script:
        script = _auto_stop_command(ssh_config)
    if not script:
        return {"ip": ip, "ok": False, "error": "No stop script configured"}
    loop = asyncio.get_running_loop()
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
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _executor, _distribute_items,
        slave_ips, ssh_configs, items, data_dir,
    )


# --- View Slave Log (#22) ---

def _fetch_slave_log(ip: str, ssh_config: dict, tail: int = 200) -> dict:
    """Fetch the last N lines of jmeter-server.log via SSH (#22)."""
    slave_dir = ssh_config.get("slave_dir", "~/jmeter-slave")
    _validate_slave_dir(slave_dir)
    tail = max(1, min(int(tail), 10000))
    log_path = f"{slave_dir}/jmeter-server.log"
    try:
        client = _ssh_connect(ip, ssh_config, timeout=10)
        cmd = f"tail -n {tail} {log_path} 2>/dev/null || echo '[Log file not found]'"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
        output = stdout.read().decode("utf-8", errors="replace")
        stdout.channel.recv_exit_status()
        client.close()
        return {"ip": ip, "ok": True, "log": output, "path": log_path}
    except Exception as e:
        return {"ip": ip, "ok": False, "log": "", "path": log_path, "error": str(e)}


async def fetch_slave_log(ip: str, ssh_config: dict, tail: int = 200) -> dict:
    """Async wrapper for fetching slave log."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _fetch_slave_log, ip, ssh_config, tail)


# --- Clean Data (#32) ---

def _clean_slave_data(ip: str, ssh_config: dict) -> dict:
    """Delete CSV files in slave's test_data/ directory via SSH (#32)."""
    slave_dir = ssh_config.get("slave_dir", "~/jmeter-slave")
    _validate_slave_dir(slave_dir)
    data_path = f"{slave_dir}/test_data"
    try:
        client = _ssh_connect(ip, ssh_config, timeout=10)
        # List files before deletion for reporting
        stdin, stdout, stderr = client.exec_command(f"ls {data_path}/*.csv 2>/dev/null | wc -l", timeout=10)
        count = stdout.read().decode().strip()
        stdout.channel.recv_exit_status()
        # Delete CSV files
        stdin, stdout, stderr = client.exec_command(f"rm -f {data_path}/*.csv 2>/dev/null && echo ok", timeout=15)
        out = stdout.read().decode().strip()
        stdout.channel.recv_exit_status()
        client.close()
        return {"ip": ip, "ok": "ok" in out, "files_removed": int(count) if count.isdigit() else 0}
    except Exception as e:
        return {"ip": ip, "ok": False, "error": str(e), "files_removed": 0}


async def clean_slave_data(ip: str, ssh_config: dict) -> dict:
    """Async wrapper for cleaning slave data."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _clean_slave_data, ip, ssh_config)


# --- Clean Logs (#33) ---

def _clean_slave_log(ip: str, ssh_config: dict) -> dict:
    """Truncate jmeter-slave.log on a slave via SSH (#33)."""
    slave_dir = ssh_config.get("slave_dir", "~/jmeter-slave")
    _validate_slave_dir(slave_dir)
    log_path = f"{slave_dir}/jmeter-slave.log"
    try:
        client = _ssh_connect(ip, ssh_config, timeout=10)
        # Get size before truncation
        stdin, stdout, stderr = client.exec_command(f"stat -c%s {log_path} 2>/dev/null || echo 0", timeout=10)
        size_str = stdout.read().decode().strip()
        stdout.channel.recv_exit_status()
        # Truncate
        stdin, stdout, stderr = client.exec_command(f"> {log_path} 2>/dev/null && echo ok", timeout=10)
        out = stdout.read().decode().strip()
        stdout.channel.recv_exit_status()
        client.close()
        size_bytes = int(size_str) if size_str.isdigit() else 0
        return {"ip": ip, "ok": "ok" in out, "bytes_cleared": size_bytes}
    except Exception as e:
        return {"ip": ip, "ok": False, "error": str(e), "bytes_cleared": 0}


async def clean_slave_log(ip: str, ssh_config: dict) -> dict:
    """Async wrapper for cleaning slave log."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _clean_slave_log, ip, ssh_config)


# --- Resource Monitoring (#30) ---

def _get_slave_resources(ip: str, ssh_config: dict) -> dict:
    """Get CPU and RAM usage from a slave via SSH (#30).

    Runs `top -bn1` for CPU and `free -m` for RAM.
    Returns {ip, ok, cpu_percent, ram_percent, ram_used_mb, ram_total_mb}.
    """
    try:
        client = _ssh_connect(ip, ssh_config, timeout=10)
    except Exception as e:
        return {"ip": ip, "ok": False, "error": str(e)}

    result = {"ip": ip, "ok": True}

    # CPU usage — parse idle% from top, compute usage
    try:
        stdin, stdout, stderr = client.exec_command(
            "top -bn1 | grep '%Cpu' | head -1", timeout=10
        )
        cpu_line = stdout.read().decode("utf-8", errors="replace").strip()
        stdout.channel.recv_exit_status()
        # Parse idle percentage: "%Cpu(s): ... XX.X id, ..."
        idle = 0.0
        for part in cpu_line.split(","):
            part = part.strip()
            if "id" in part:
                idle = float(part.split()[0])
                break
        result["cpu_percent"] = round(100.0 - idle, 1)
    except Exception:
        result["cpu_percent"] = None

    # RAM usage — parse from free -m
    try:
        stdin, stdout, stderr = client.exec_command("free -m | grep Mem:", timeout=10)
        mem_line = stdout.read().decode("utf-8", errors="replace").strip()
        stdout.channel.recv_exit_status()
        # "Mem:   total   used   free  shared  buff/cache  available"
        parts = mem_line.split()
        if len(parts) >= 3:
            total_mb = int(parts[1])
            used_mb = int(parts[2])
            result["ram_total_mb"] = total_mb
            result["ram_used_mb"] = used_mb
            result["ram_percent"] = round(used_mb / total_mb * 100, 1) if total_mb > 0 else 0.0
        else:
            result["ram_total_mb"] = None
            result["ram_used_mb"] = None
            result["ram_percent"] = None
    except Exception:
        result["ram_total_mb"] = None
        result["ram_used_mb"] = None
        result["ram_percent"] = None

    client.close()
    return result


async def get_slave_resources(ip: str, ssh_config: dict) -> dict:
    """Async wrapper for getting slave resources."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _get_slave_resources, ip, ssh_config)


async def get_all_slave_resources(
    slave_ips: list[str], ssh_configs: dict[str, dict]
) -> list[dict]:
    """Get resource usage from all slaves in parallel (#30)."""
    tasks = [get_slave_resources(ip, ssh_configs.get(ip, {})) for ip in slave_ips]
    return await asyncio.gather(*tasks)


# --- Metrics Agent (HTTP-based monitoring) ---

def _fetch_agent_metrics(ip: str, port: int = 9100, timeout: int = 3) -> dict:
    """Fetch metrics from the HTTP agent on a slave."""
    import json as _json
    from urllib.request import urlopen
    from urllib.error import URLError
    try:
        url = f"http://{ip}:{port}/metrics"
        with urlopen(url, timeout=timeout) as resp:
            data = _json.loads(resp.read().decode())
        data["ip"] = ip
        data["ok"] = True
        data["agent"] = True
        return data
    except (URLError, OSError, ValueError):
        return {"ip": ip, "ok": False, "agent": False, "error": "Agent unreachable"}


async def fetch_agent_metrics(ip: str, port: int = 9100) -> dict:
    """Async wrapper for HTTP agent metrics fetch."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _fetch_agent_metrics, ip, port)


async def fetch_all_agent_metrics(
    slave_ips: list[str], port: int = 9100
) -> list[dict]:
    """Fetch metrics from all slaves' agents in parallel."""
    tasks = [fetch_agent_metrics(ip, port) for ip in slave_ips]
    return await asyncio.gather(*tasks)
