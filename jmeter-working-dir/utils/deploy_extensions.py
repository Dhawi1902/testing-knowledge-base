#!/usr/bin/env python3
"""
Deploy JMeter extensions to slave VMs via SSH.
Usage: python deploy_extensions.py [--config path/to/config.json]

Place extension JAR files in the 'extensions/' folder before running.
"""

import json
import argparse
import sys
from pathlib import Path

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


def deploy_extensions_to_vm(extensions: list[Path], vm_config: dict) -> tuple[bool, list[str]]:
    """Deploy extension files to VM via SCP.

    Returns:
        (success, list of deployed files)
    """
    host = vm_config['host']
    user = vm_config['user']
    password = vm_config['password']
    dest_path = vm_config['extensions_path']

    deployed = []

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

        # Ensure destination directory exists
        ssh.exec_command(f"mkdir -p {dest_path}")

        # Create SCP client and upload each extension
        with SCPClient(ssh.get_transport()) as scp:
            for ext_file in extensions:
                print(f"  Copying {ext_file.name}...")
                scp.put(str(ext_file), dest_path)
                deployed.append(ext_file.name)

        # Verify files exist
        print(f"  Verifying deployment...")
        for ext_file in extensions:
            stdin, stdout, stderr = ssh.exec_command(f"ls -lh {dest_path}{ext_file.name}")
            output = stdout.read().decode().strip()
            if output:
                print(f"  [OK] {ext_file.name}")
            else:
                print(f"  [WARNING] {ext_file.name} - verification failed")

        ssh.close()
        return (True, deployed)

    except paramiko.AuthenticationException:
        print(f"  [ERROR] Authentication failed for {host}")
        return (False, deployed)
    except paramiko.SSHException as e:
        print(f"  [ERROR] SSH connection failed: {e}")
        return (False, deployed)
    except Exception as e:
        print(f"  [ERROR] {e}")
        return (False, deployed)


def deploy_extensions(config_path: Path) -> None:
    """Deploy all extensions from extensions/ folder to all slave VMs."""

    # Load configuration
    config = load_config(config_path)
    ssh_config = config['ssh_config']

    # Check for extensions_path in config
    if 'extensions_path' not in ssh_config:
        print("[ERROR] 'extensions_path' not found in ssh_config")
        print("Add it to config/vm_config.json under ssh_config")
        return

    # Paths
    repo_root = Path(__file__).resolve().parents[1]
    extensions_dir = repo_root / "extensions"
    slaves_file_name = config.get('slaves_file', 'slaves.txt')
    slaves_file = repo_root / slaves_file_name

    # Check extensions directory exists
    if not extensions_dir.exists():
        print(f"[ERROR] Extensions directory not found: {extensions_dir}")
        print("Create the 'extensions/' folder and add JAR files")
        return

    # Find extension files (JAR files)
    extensions = list(extensions_dir.glob("*.jar"))
    if not extensions:
        print(f"[WARNING] No JAR files found in {extensions_dir}")
        print("Add JMeter extension JAR files to the 'extensions/' folder")
        return

    print(f"Found {len(extensions)} extension(s):")
    for ext in extensions:
        print(f"  - {ext.name}")
    print()

    # Load slaves
    if not slaves_file.exists():
        print(f"[ERROR] Slaves file not found: {slaves_file}")
        return

    slave_hosts = read_slaves(slaves_file)
    if not slave_hosts:
        print(f"[ERROR] No slave hosts found in {slaves_file}")
        return

    print(f"Target: {len(slave_hosts)} VM(s)")
    print(f"Destination: {ssh_config['extensions_path']}")
    print("=" * 60)

    # Deploy to each VM
    success_count = 0
    failed_hosts = []

    for i, host in enumerate(slave_hosts):
        print(f"\n[{i+1}/{len(slave_hosts)}] Deploying to {host}")

        vm_config = {
            'host': host,
            'user': ssh_config['user'],
            'password': ssh_config['password'],
            'extensions_path': ssh_config['extensions_path']
        }

        success, deployed = deploy_extensions_to_vm(extensions, vm_config)

        if success:
            success_count += 1
        else:
            failed_hosts.append(host)

    # Summary
    print("\n" + "=" * 60)
    print("Deployment Summary")
    print("=" * 60)
    print(f"Extensions: {len(extensions)} file(s)")
    print(f"Success: {success_count}/{len(slave_hosts)} VM(s)")

    if failed_hosts:
        print(f"Failed: {', '.join(failed_hosts)}")

    print("=" * 60)

    if success_count > 0:
        print("\n[NOTE] Restart JMeter servers to load new extensions:")
        print("  python utils/manage_jmeter_servers.py restart")


def main():
    parser = argparse.ArgumentParser(
        description='Deploy JMeter extensions to slave VMs',
        epilog='Place JAR files in the extensions/ folder before running.'
    )

    parser.add_argument(
        '--config',
        type=Path,
        default=None,
        help='Path to VM config JSON file (default: config/vm_config.json)'
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
    deploy_extensions(config_path)
    return 0


if __name__ == "__main__":
    exit(main())
