#!/usr/bin/env python3
"""
Create folders on all slave VMs via SSH.
Reads 'create_folders' from vm_config.json: a parent path and a list of child folder names.

Usage:
    python utils/create_folder_on_slaves.py
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


def execute_remote_command(host: str, user: str, password: str, command: str, timeout: int = 30) -> Tuple[bool, str, str]:
    """Execute command on remote host via SSH."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(
            hostname=host,
            username=user,
            password=password,
            timeout=10
        )

        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)

        stdout_text = stdout.read().decode().strip()
        stderr_text = stderr.read().decode().strip()
        exit_status = stdout.channel.recv_exit_status()

        ssh.close()

        return (exit_status == 0, stdout_text, stderr_text)

    except paramiko.AuthenticationException:
        return (False, "", f"Authentication failed for {host}")
    except paramiko.SSHException as e:
        return (False, "", f"SSH error: {e}")
    except Exception as e:
        return (False, "", f"Error: {e}")


def create_folders_on_slaves(folder_paths: List[str], config_path: Path) -> None:
    """Create folders on all slave VMs."""

    config = load_config(config_path)
    ssh_config = config['ssh_config']

    repo_root = Path(__file__).resolve().parents[1]
    slaves_file_name = config.get('slaves_file', 'slaves.txt')
    slaves_file = repo_root / slaves_file_name

    if not slaves_file.exists():
        print(f"[ERROR] Slaves file not found: {slaves_file}")
        return

    slave_hosts = read_slaves(slaves_file)
    if not slave_hosts:
        print(f"[ERROR] No slave hosts found in {slaves_file}")
        return

    # Build a single mkdir -p command for all paths
    paths_str = " ".join(folder_paths)
    command = f"mkdir -p {paths_str}"

    print(f"{'='*60}")
    print(f"Creating {len(folder_paths)} folder(s):")
    for fp in folder_paths:
        print(f"  - {fp}")
    print(f"Command: {command}")
    print(f"Targets: {len(slave_hosts)} VM(s)")
    print(f"{'='*60}\n")

    success_count = 0
    failed_hosts = []

    for i, host in enumerate(slave_hosts):
        print(f"[{i+1}/{len(slave_hosts)}] {host}: Creating folders...")

        success, stdout, stderr = execute_remote_command(
            host=host,
            user=ssh_config['user'],
            password=ssh_config['password'],
            command=command,
            timeout=30
        )

        if success:
            print(f"  [OK] Folders created")
            success_count += 1
        else:
            print(f"  [FAILED] {stderr}")
            failed_hosts.append(host)

        print()

    print(f"{'='*60}")
    print(f"Summary")
    print(f"{'='*60}")
    print(f"Success: {success_count}/{len(slave_hosts)} VM(s)")

    if failed_hosts:
        print(f"Failed:  {', '.join(failed_hosts)}")

    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description='Create folders on all slave VMs via SSH',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--config',
        type=Path,
        default=None,
        help='Path to VM config JSON file (default: config/vm_config.json)'
    )

    args = parser.parse_args()

    if args.config:
        config_path = args.config
    else:
        repo_root = Path(__file__).resolve().parents[1]
        config_path = repo_root / "config" / "vm_config.json"

    if not config_path.exists():
        print(f"[ERROR] Config file not found: {config_path}")
        return 1

    config = load_config(config_path)
    create_folders_cfg = config.get('create_folders')
    if not create_folders_cfg:
        print("[ERROR] 'create_folders' not set in config.")
        return 1

    parent = create_folders_cfg.get('parent', '').rstrip('/')
    children = create_folders_cfg.get('children', [])

    if not parent:
        print("[ERROR] 'create_folders.parent' is empty in config.")
        return 1

    if not children:
        print("[ERROR] 'create_folders.children' is empty in config. Add child folder names to the list.")
        return 1

    # Build full paths: parent/child for each child
    folder_paths = [f"{parent}/{child}" for child in children]

    print(f"Using folders from config:\n  Parent: {parent}")
    print(f"  Children: {', '.join(children)}\n")

    create_folders_on_slaves(folder_paths, config_path)
    return 0


if __name__ == "__main__":
    exit(main())
