#!/usr/bin/env python3
"""
Collect the parent folder from all slave VMs to local machine via SCP.
Each run saves into a timestamped folder for audit trail.
After successful download, clears files on slaves but keeps folder structure.

Usage:
    python utils/collect_from_slaves.py
    python utils/collect_from_slaves.py --local-dir results/failed_response
"""

import sys
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

try:
    import paramiko
    from scp import SCPClient
except ImportError:
    print("Error: Required libraries not installed.")
    print("Install using: pip install paramiko scp")
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


def ssh_connect(host: str, user: str, password: str) -> paramiko.SSHClient:
    """Create and return an SSH connection."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, username=user, password=password, timeout=10)
    return ssh


def collect_and_clear(host: str, user: str, password: str,
                      remote_path: str, local_dest: Path) -> Tuple[bool, str]:
    """Download a remote folder from a slave, then clear files but keep folders."""
    try:
        ssh = ssh_connect(host, user, password)

        # Check if remote folder exists
        stdin, stdout, stderr = ssh.exec_command(f"test -d {remote_path} && echo EXISTS")
        result = stdout.read().decode().strip()
        if result != "EXISTS":
            ssh.close()
            return (False, f"Remote folder not found: {remote_path}")

        # Check if there are any files to collect
        stdin, stdout, stderr = ssh.exec_command(f"find {remote_path} -type f | head -1")
        has_files = stdout.read().decode().strip()
        if not has_files:
            ssh.close()
            return (True, "No files to collect (empty)")

        # Create local destination
        local_dest.mkdir(parents=True, exist_ok=True)

        # Download folder recursively
        with SCPClient(ssh.get_transport()) as scp:
            scp.get(remote_path, str(local_dest), recursive=True)

        # Clear files on slave but keep directory structure
        # find <path> -type f -delete: removes only files, leaves folders intact
        stdin, stdout, stderr = ssh.exec_command(f"find {remote_path} -type f -delete")
        stdout.channel.recv_exit_status()
        err = stderr.read().decode().strip()

        ssh.close()

        if err:
            return (True, f"Downloaded, but cleanup warning: {err}")

        return (True, "Downloaded and cleared")

    except paramiko.AuthenticationException:
        return (False, f"Authentication failed for {host}")
    except paramiko.SSHException as e:
        return (False, f"SSH error: {e}")
    except Exception as e:
        return (False, f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Collect parent folder from all slave VMs to local machine',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--config',
        type=Path,
        default=None,
        help='Path to VM config JSON file (default: config/vm_config.json)'
    )

    parser.add_argument(
        '--local-dir',
        type=Path,
        default=None,
        help='Local base directory to save collected files (default: results/collected/<folder_name>)'
    )

    args = parser.parse_args()

    # Resolve config path
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

    # Get remote parent folder
    create_folders_cfg = config.get('create_folders')
    if not create_folders_cfg:
        print("[ERROR] 'create_folders' not set in config.")
        return 1

    remote_path = create_folders_cfg.get('parent', '').rstrip('/')
    if not remote_path:
        print("[ERROR] 'create_folders.parent' is empty in config.")
        return 1

    # Resolve local destination with timestamp subfolder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.local_dir:
        local_base = args.local_dir / timestamp
    else:
        folder_name = remote_path.rsplit('/', 1)[-1]
        local_base = repo_root / "results" / "collected" / folder_name / timestamp

    # Read slaves
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
    print(f"Collecting from slaves")
    print(f"{'='*60}")
    print(f"Remote path:  {remote_path}")
    print(f"Local path:   {local_base}")
    print(f"Run:          {timestamp}")
    print(f"Targets:      {len(slave_hosts)} VM(s)")
    print(f"{'='*60}\n")

    success_count = 0
    failed_hosts = []

    for i, host in enumerate(slave_hosts):
        local_dest = local_base / host
        print(f"[{i+1}/{len(slave_hosts)}] {host}: Downloading to {local_dest} ...")

        success, message = collect_and_clear(
            host=host,
            user=ssh_config['user'],
            password=ssh_config['password'],
            remote_path=remote_path,
            local_dest=local_dest
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
    print(f"Files saved to: {local_base}")

    if failed_hosts:
        print(f"Failed:  {', '.join(failed_hosts)}")

    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    exit(main())
