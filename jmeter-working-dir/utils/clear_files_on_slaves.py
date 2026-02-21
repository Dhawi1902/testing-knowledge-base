#!/usr/bin/env python3
"""
Remove all files inside create_folders.parent on all slave VMs.
Keeps the parent and child directory structure intact.

Usage:
    python utils/clear_files_on_slaves.py
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


def clear_files(host: str, user: str, password: str,
                remote_path: str) -> Tuple[bool, str]:
    """Remove all files inside remote_path, keeping directory structure."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, username=user, password=password, timeout=10)

        # Check if remote folder exists
        stdin, stdout, stderr = ssh.exec_command(f"test -d {remote_path} && echo EXISTS")
        result = stdout.read().decode().strip()
        if result != "EXISTS":
            ssh.close()
            return (False, f"Folder not found: {remote_path}")

        # Count files before deleting
        stdin, stdout, stderr = ssh.exec_command(f"find {remote_path} -type f | wc -l")
        file_count = stdout.read().decode().strip()

        if file_count == "0":
            ssh.close()
            return (True, "Already empty")

        # Delete all files, keep directories
        stdin, stdout, stderr = ssh.exec_command(f"find {remote_path} -type f -delete")
        exit_status = stdout.channel.recv_exit_status()
        err = stderr.read().decode().strip()

        ssh.close()

        if exit_status != 0:
            return (False, f"Delete failed: {err}")

        return (True, f"Removed {file_count} file(s)")

    except paramiko.AuthenticationException:
        return (False, f"Authentication failed for {host}")
    except paramiko.SSHException as e:
        return (False, f"SSH error: {e}")
    except Exception as e:
        return (False, f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Remove all files inside parent folder on all slave VMs (keeps directories)',
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

    create_folders_cfg = config.get('create_folders')
    if not create_folders_cfg:
        print("[ERROR] 'create_folders' not set in config.")
        return 1

    remote_path = create_folders_cfg.get('parent', '').rstrip('/')
    if not remote_path:
        print("[ERROR] 'create_folders.parent' is empty in config.")
        return 1

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
    print(f"Clear files on slaves")
    print(f"{'='*60}")
    print(f"Folder:   {remote_path}")
    print(f"Targets:  {len(slave_hosts)} VM(s)")
    print(f"{'='*60}\n")

    success_count = 0
    failed_hosts = []

    for i, host in enumerate(slave_hosts):
        print(f"[{i+1}/{len(slave_hosts)}] {host}: Clearing files...")

        success, message = clear_files(
            host=host,
            user=ssh_config['user'],
            password=ssh_config['password'],
            remote_path=remote_path
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
