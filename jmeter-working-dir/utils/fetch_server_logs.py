#!/usr/bin/env python3
"""
Fetch jmeter-server.log from all slave VMs.
Saves logs with slave IP in filename for easy identification.

Usage:
    python utils/fetch_server_logs.py
    python utils/fetch_server_logs.py --remote-path /custom/path/jmeter-server.log
    python utils/fetch_server_logs.py --output-dir results/logs
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


DEFAULT_LOG_PATH = "/home/opc/jmeter-PT/linux/jmeter-server.log"


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


def fetch_log_file(host: str, user: str, password: str,
                   remote_path: str, local_path: Path) -> Tuple[bool, str, int]:
    """
    Fetch a single log file from a slave VM.

    Returns:
        (success, message, file_size_bytes)
    """
    try:
        # Create SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, username=user, password=password, timeout=10)

        # Check if file exists and get size
        stdin, stdout, stderr = ssh.exec_command(f"stat -c %s {remote_path} 2>/dev/null")
        size_output = stdout.read().decode().strip()

        if not size_output:
            ssh.close()
            return (False, "Log file not found", 0)

        file_size = int(size_output)

        # Create local directory if needed
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Download file
        with SCPClient(ssh.get_transport()) as scp:
            scp.get(remote_path, str(local_path))

        ssh.close()
        return (True, "Downloaded", file_size)

    except paramiko.AuthenticationException:
        return (False, "Authentication failed", 0)
    except paramiko.SSHException as e:
        return (False, f"SSH error: {e}", 0)
    except Exception as e:
        return (False, f"Error: {e}", 0)


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def main():
    parser = argparse.ArgumentParser(
        description='Fetch jmeter-server.log from all slave VMs',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--config',
        type=Path,
        default=None,
        help='Path to VM config JSON file (default: config/vm_config.json)'
    )

    parser.add_argument(
        '--remote-path',
        type=str,
        default=DEFAULT_LOG_PATH,
        help=f'Remote log file path (default: {DEFAULT_LOG_PATH})'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=None,
        help='Output directory (default: results/server_logs/<timestamp>)'
    )

    parser.add_argument(
        '--no-timestamp',
        action='store_true',
        help='Save directly to output dir without timestamp subfolder'
    )

    args = parser.parse_args()

    # Resolve paths
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

    # Determine output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.output_dir:
        if args.no_timestamp:
            output_dir = args.output_dir
        else:
            output_dir = args.output_dir / timestamp
    else:
        output_dir = repo_root / "results" / "server_logs" / timestamp

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

    print("=" * 60)
    print("Fetch JMeter Server Logs")
    print("=" * 60)
    print(f"Remote path:  {args.remote_path}")
    print(f"Output dir:   {output_dir}")
    print(f"Timestamp:    {timestamp}")
    print(f"Targets:      {len(slave_hosts)} VM(s)")
    print("=" * 60)
    print()

    success_count = 0
    failed_hosts = []
    total_size = 0

    for i, host in enumerate(slave_hosts):
        # Create filename with IP address
        log_filename = f"jmeter-server_{host}.log"
        local_path = output_dir / log_filename

        print(f"[{i+1}/{len(slave_hosts)}] {host}...", end=" ", flush=True)

        success, message, file_size = fetch_log_file(
            host=host,
            user=ssh_config['user'],
            password=ssh_config['password'],
            remote_path=args.remote_path,
            local_path=local_path
        )

        if success:
            print(f"[OK] {format_size(file_size)}")
            success_count += 1
            total_size += file_size
        else:
            print(f"[FAILED] {message}")
            failed_hosts.append(host)

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Success:     {success_count}/{len(slave_hosts)} VM(s)")
    print(f"Total size:  {format_size(total_size)}")
    print(f"Saved to:    {output_dir}")

    if failed_hosts:
        print(f"Failed:      {', '.join(failed_hosts)}")

    print("=" * 60)

    if success_count > 0:
        print(f"\nLog files:")
        for f in sorted(output_dir.glob("jmeter-server_*.log")):
            print(f"  - {f.name}")

    return 0 if success_count == len(slave_hosts) else 1


if __name__ == "__main__":
    exit(main())
