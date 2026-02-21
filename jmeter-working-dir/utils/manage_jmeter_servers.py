#!/usr/bin/env python3
"""
Manage JMeter servers across VMs via SSH.
Usage: python manage_jmeter_servers.py {start|stop|status|restart}
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
    """Execute command on remote host via SSH.

    Returns:
        (success, stdout, stderr)
    """
    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect
        ssh.connect(
            hostname=host,
            username=user,
            password=password,
            timeout=10
        )

        # Execute command
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)

        # Read output
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


def manage_jmeter_servers(action: str, config_path: Path, custom_start_script: str = None, custom_stop_script: str = None) -> None:
    """Manage JMeter servers across all VMs."""

    # Load configuration
    config = load_config(config_path)
    ssh_config = config['ssh_config']

    # Get jmeter scripts from config or use custom/default
    jmeter_scripts = config.get('jmeter_scripts', {})
    start_script = custom_start_script or jmeter_scripts.get('start', '/home/jmeter/start.sh')
    stop_script = custom_stop_script or jmeter_scripts.get('stop', '/home/jmeter/stop.sh')

    # Load slaves
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

    # cd into the script directory so JMeter's user.dir is correct
    script_dir = start_script.rsplit('/', 1)[0]

    # Map action to command
    commands = {
        'start': f'cd {script_dir} && {start_script}',
        'stop': f'cd {script_dir} && {stop_script}',
        'status': 'ps aux | grep jmeter-server | grep -v grep',
        'restart': f'cd {script_dir} && {stop_script} && sleep 2 && {start_script}'
    }

    if action not in commands:
        print(f"[ERROR] Invalid action: {action}")
        print(f"Valid actions: {', '.join(commands.keys())}")
        return

    command = commands[action]

    print(f"{'='*60}")
    print(f"Action: {action.upper()}")
    print(f"Command: {command}")
    print(f"Targets: {len(slave_hosts)} VM(s)")
    print(f"{'='*60}\n")

    # Execute command on each VM
    success_count = 0
    failed_hosts = []

    for i, host in enumerate(slave_hosts):
        print(f"[{i+1}/{len(slave_hosts)}] {host}: {action}ing JMeter server...")

        success, stdout, stderr = execute_remote_command(
            host=host,
            user=ssh_config['user'],
            password=ssh_config['password'],
            command=command,
            timeout=30
        )

        if success:
            print(f"  [OK] {action.capitalize()} successful")
            if stdout:
                for line in stdout.split('\n'):
                    print(f"       {line}")
            success_count += 1
        else:
            print(f"  [FAILED] {action.capitalize()} failed")
            if stderr:
                for line in stderr.split('\n'):
                    print(f"       {line}")
            failed_hosts.append(host)

        print()

    # Summary
    print(f"{'='*60}")
    print(f"Summary: {action.upper()}")
    print(f"{'='*60}")
    print(f"Success: {success_count}/{len(slave_hosts)} VM(s)")

    if failed_hosts:
        print(f"Failed:  {', '.join(failed_hosts)}")

    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description='Manage JMeter servers across VMs',
        epilog='Examples:\n'
               '  python manage_jmeter_servers.py start\n'
               '  python manage_jmeter_servers.py stop\n'
               '  python manage_jmeter_servers.py status\n',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'action',
        choices=['start', 'stop', 'status', 'restart'],
        help='Action to perform on JMeter servers'
    )

    parser.add_argument(
        '--config',
        type=Path,
        default=None,
        help='Path to VM config JSON file (default: config/vm_config.json)'
    )

    parser.add_argument(
        '--start-script',
        type=str,
        default=None,
        help='Path to start script on remote VM (default: from config or /home/jmeter/start.sh)'
    )

    parser.add_argument(
        '--stop-script',
        type=str,
        default=None,
        help='Path to stop script on remote VM (default: from config or /home/jmeter/stop.sh)'
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

    manage_jmeter_servers(args.action, config_path, args.start_script, args.stop_script)
    return 0


if __name__ == "__main__":
    exit(main())
