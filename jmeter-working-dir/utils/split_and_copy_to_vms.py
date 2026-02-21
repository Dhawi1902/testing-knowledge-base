#!/usr/bin/env python3
"""
Split master student data and copy to VMs via SSH.
Usage: python split_and_copy_to_vms.py [--config path/to/config.json] [--offset 0] [--size 1000]
"""

import json
import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np

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


def read_slaves(slaves_file: Path) -> list[str]:
    """Read slave IPs from file, filtering out comments and empty lines."""
    slaves = []
    with open(slaves_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                slaves.append(line)
    return slaves


def split_data(master_df: pd.DataFrame, num_vms: int, offset: int, size: int) -> list:
    """Split master dataframe into chunks for each VM."""
    subset = master_df.iloc[offset:offset+size]
    indices = np.array_split(range(len(subset)), num_vms)
    return [subset.iloc[idx] for idx in indices]


def copy_file_to_vm(local_file: Path, vm_config: dict) -> bool:
    """Copy file to VM via SCP."""

    host = vm_config['host']
    user = vm_config['user']
    password = vm_config['password']
    dest_path = vm_config['dest_path']

    try:
        print(f"  Connecting to {user}@{host}...")

        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to VM
        ssh.connect(
            hostname=host,
            username=user,
            password=password,
            timeout=10
        )

        print(f"  Copying {local_file.name} to {dest_path}...")

        # Create SCP client and upload
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(str(local_file), dest_path)

        # Verify file exists
        filename = local_file.name
        stdin, stdout, stderr = ssh.exec_command(f"ls -lh {dest_path}{filename}")
        output = stdout.read().decode().strip()

        ssh.close()

        if output:
            print(f"  [OK] File verified on remote: {output}")
            return True
        else:
            print(f"  [WARNING] File uploaded but verification failed")
            return True

    except paramiko.AuthenticationException:
        print(f"  [ERROR] Authentication failed for {host}")
        return False
    except paramiko.SSHException as e:
        print(f"  [ERROR] SSH connection failed: {e}")
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def split_and_distribute(config_path: Path, offset: int = None, size: int = None) -> None:
    """Split data and distribute to VMs."""

    # Load configuration
    config = load_config(config_path)
    ssh_config = config['ssh_config']
    split_config = config['split_config']

    # Use command-line args if provided, otherwise use config
    offset = offset if offset is not None else split_config.get('offset', 0)
    size = size if size is not None else split_config.get('size', 1000)
    csv_filename = split_config.get('csv_filename', 'student_data.csv')

    # Paths
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

    print(f"Found {len(slave_hosts)} active slave(s)")

    master_data_path = repo_root / "test_data" / "master_student_data.csv"
    output_dir = repo_root / "test_data" / "slaves_data"

    # Validate master data exists
    if not master_data_path.exists():
        print(f"[ERROR] Master data file not found: {master_data_path}")
        print("Run generate_master_data.bat first!")
        return

    # Load master data
    print(f"Loading master data from: {master_data_path}")
    master_df = pd.read_csv(master_data_path)
    print(f"[OK] Loaded {len(master_df)} records")

    # Split data
    print(f"\nSplitting data (offset={offset}, size={size}) across {len(slave_hosts)} VM(s)...")
    df_splits = split_data(master_df, len(slave_hosts), offset, size)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_file = output_dir / "distribution_summary.txt"

    # Process each VM
    success_count = 0
    with open(summary_file, 'w') as summary:
        summary.write(f"Data Distribution Summary\n")
        summary.write(f"========================\n")
        summary.write(f"Offset: {offset}, Size: {size}\n")
        summary.write(f"Total VMs: {len(slave_hosts)}\n\n")

        for i, host in enumerate(slave_hosts):
            print(f"\n[{i+1}/{len(slave_hosts)}] Processing VM: {host}")

            # Get data split for this VM
            vm_data = df_splits[i]
            first_id = vm_data.iloc[0]['USERNAME']
            last_id = vm_data.iloc[-1]['USERNAME']

            print(f"  Data range: {first_id} to {last_id} ({len(vm_data)} records)")

            # Save to local file
            vm_folder = output_dir / host
            vm_folder.mkdir(parents=True, exist_ok=True)
            local_csv = vm_folder / csv_filename
            vm_data.to_csv(local_csv, index=False)
            print(f"  [OK] Saved locally: {local_csv}")

            # Build VM config for this host
            vm_config = {
                'host': host,
                'user': ssh_config['user'],
                'password': ssh_config['password'],
                'dest_path': ssh_config['dest_path']
            }

            # Copy to VM
            if copy_file_to_vm(local_csv, vm_config):
                success_count += 1
                summary.write(f"{host}: {first_id} - {last_id} ({len(vm_data)} records) [OK]\n")
            else:
                summary.write(f"{host}: {first_id} - {last_id} ({len(vm_data)} records) [FAILED]\n")

    # Print summary
    print(f"\n{'='*50}")
    print(f"Distribution Summary")
    print(f"{'='*50}")
    print(f"Successfully distributed to {success_count}/{len(slave_hosts)} VM(s)")
    print(f"Summary file: {summary_file}")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(description='Split data and copy to VMs')
    parser.add_argument(
        '--config',
        type=Path,
        default=None,
        help='Path to VM config JSON file (default: config/vm_config.json)'
    )
    parser.add_argument(
        '--offset',
        type=int,
        default=None,
        help='Starting row offset (default: from config)'
    )
    parser.add_argument(
        '--size',
        type=int,
        default=None,
        help='Number of rows to process (default: from config)'
    )
    args = parser.parse_args()

    # Determine config path
    if args.config:
        config_path = args.config
    else:
        repo_root = Path(__file__).resolve().parents[1]
        config_path = repo_root / "config" / "vm_config.json"

    if not config_path.exists():
        print(f"[ERROR] Config file not found: {config_path}")
        return 1

    print(f"Using config: {config_path}\n")
    split_and_distribute(config_path, args.offset, args.size)
    return 0


if __name__ == "__main__":
    exit(main())
