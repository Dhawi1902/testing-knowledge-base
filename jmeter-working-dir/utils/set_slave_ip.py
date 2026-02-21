#!/usr/bin/env python3
"""
Update start-slave.sh on each slave VM:
- Sets SLAVE_IP to the VM's own private IP address
- Sets HEAP and GC_ALGO from jmeter_heap config

Usage:
    python utils/set_slave_ip.py
"""

import sys
import argparse
import json
from pathlib import Path
from typing import List, Tuple

try:
    import paramiko
except ImportError:
    print("Error: paramiko not installed.")
    print("Install using: pip install paramiko")
    sys.exit(1)


def load_config(config_path: Path) -> dict:
    """Load VM configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)


def read_slaves(slaves_file: Path) -> List[str]:
    """Read slave IPs from file, filtering out comments and empty lines."""
    slaves = []
    with open(slaves_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                slaves.append(line)
    return slaves


def run_sed(ssh, pattern: str, replacement: str, script_path: str) -> Tuple[bool, str]:
    """Run a sed replacement on the remote script. Returns (success, error)."""
    # Escape special chars in replacement for sed
    replacement_escaped = replacement.replace('/', '\\/').replace('&', '\\&')
    sed_cmd = f"sed -i 's/^{pattern}.*/{pattern}{replacement_escaped}/' {script_path}"
    stdin, stdout, stderr = ssh.exec_command(sed_cmd)
    exit_status = stdout.channel.recv_exit_status()
    err = stderr.read().decode().strip()
    return (exit_status == 0, err)


def update_slave(host: str, user: str, password: str,
                 script_path: str, heap_config: dict) -> Tuple[bool, str]:
    """SSH into slave, update SLAVE_IP, HEAP, and GC_ALGO in start-slave.sh."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, username=user, password=password, timeout=10)

        changes = []

        # --- SLAVE_IP ---
        # Get the private IP (first IP from hostname -I)
        stdin, stdout, stderr = ssh.exec_command("hostname -I | awk '{print $1}'")
        private_ip = stdout.read().decode().strip()

        if not private_ip:
            ssh.close()
            return (False, "Could not detect private IP")

        stdin, stdout, stderr = ssh.exec_command(
            f"grep -oP '^SLAVE_IP=\\K.*' {script_path}"
        )
        current_ip = stdout.read().decode().strip()

        if current_ip != private_ip:
            ok, err = run_sed(ssh, "SLAVE_IP=", private_ip, script_path)
            if not ok:
                ssh.close()
                return (False, f"sed SLAVE_IP failed: {err}")
            changes.append(f"SLAVE_IP={private_ip} (was {current_ip})")
        else:
            changes.append(f"SLAVE_IP={private_ip} (no change)")

        # --- HEAP ---
        if heap_config:
            xms = heap_config.get('xms', '12g')
            xmx = heap_config.get('xmx', '24g')
            heap_value = f'"-Xms{xms} -Xmx{xmx}"'

            stdin, stdout, stderr = ssh.exec_command(
                f"grep -oP '^export HEAP=\\K.*' {script_path}"
            )
            current_heap = stdout.read().decode().strip()

            if current_heap != heap_value:
                ok, err = run_sed(ssh, "export HEAP=", heap_value, script_path)
                if not ok:
                    ssh.close()
                    return (False, f"sed HEAP failed: {err}")
                changes.append(f"HEAP={heap_value}")
            else:
                changes.append(f"HEAP={heap_value} (no change)")

            # --- GC_ALGO ---
            gc_algo = heap_config.get('gc_algo', '-XX:+UseG1GC -XX:MaxGCPauseMillis=100 -XX:G1ReservePercent=20')
            gc_value = f'"{gc_algo}"'

            stdin, stdout, stderr = ssh.exec_command(
                f"grep -oP '^export GC_ALGO=\\K.*' {script_path}"
            )
            current_gc = stdout.read().decode().strip()

            if current_gc != gc_value:
                ok, err = run_sed(ssh, "export GC_ALGO=", gc_value, script_path)
                if not ok:
                    ssh.close()
                    return (False, f"sed GC_ALGO failed: {err}")
                changes.append(f"GC_ALGO={gc_value}")
            else:
                changes.append(f"GC_ALGO={gc_value} (no change)")

        ssh.close()

        return (True, " | ".join(changes))

    except paramiko.AuthenticationException:
        return (False, f"Authentication failed for {host}")
    except paramiko.SSHException as e:
        return (False, f"SSH error: {e}")
    except Exception as e:
        return (False, f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Update SLAVE_IP in start-slave.sh on each slave VM to use its private IP',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--config',
        type=Path,
        default=None,
        help='Path to VM config JSON file (default: config/vm_config.json)'
    )

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]

    if args.config:
        config_path = args.config
    else:
        config_path = repo_root / "config" / "vm_config.json"

    if not config_path.exists():
        print(f"[ERROR] Config file not found: {config_path}")
        return 1

    config = load_config(config_path)
    ssh_config = config['ssh_config']
    script_path = config.get('jmeter_scripts', {}).get('start', '/home/opc/jmeter-PT/linux/start-slave.sh')
    heap_config = config.get('jmeter_heap', {})

    slaves_file_name = config.get('slaves_file', 'slaves.txt')
    slaves_file = repo_root / slaves_file_name

    if not slaves_file.exists():
        print(f"[ERROR] Slaves file not found: {slaves_file}")
        return 1

    slave_hosts = read_slaves(slaves_file)
    if not slave_hosts:
        print(f"[ERROR] No slave hosts found in {slaves_file}")
        return 1

    print(f"{'='*60}")
    print(f"Configure start-slave.sh")
    print(f"{'='*60}")
    print(f"Script:   {script_path}")
    if heap_config:
        print(f"HEAP:     -Xms{heap_config.get('xms', '12g')} -Xmx{heap_config.get('xmx', '24g')}")
        print(f"GC_ALGO:  {heap_config.get('gc_algo', '')}")
    print(f"Targets:  {len(slave_hosts)} VM(s)")
    print(f"{'='*60}\n")

    success_count = 0
    failed_hosts = []

    for i, host in enumerate(slave_hosts):
        print(f"[{i+1}/{len(slave_hosts)}] {host}: Configuring...")

        success, message = update_slave(
            host=host,
            user=ssh_config['user'],
            password=ssh_config['password'],
            script_path=script_path,
            heap_config=heap_config
        )

        if success:
            print(f"  [OK] {message}")
            success_count += 1
        else:
            print(f"  [FAILED] {message}")
            failed_hosts.append(host)

        print()

    print(f"{'='*60}")
    print(f"Summary")
    print(f"{'='*60}")
    print(f"Success: {success_count}/{len(slave_hosts)} VM(s)")

    if failed_hosts:
        print(f"Failed:  {', '.join(failed_hosts)}")

    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    exit(main())
