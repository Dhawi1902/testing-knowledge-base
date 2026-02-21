#!/usr/bin/env python3
"""
Script to copy CSV files to VM via SSH with password authentication
Usage: python copy_to_vm.py <local_file>
"""

import sys
import os
from pathlib import Path

try:
    import paramiko
    from scp import SCPClient
except ImportError:
    print("Error: Required libraries not installed.")
    print("Install using: pip install paramiko scp")
    sys.exit(1)

# VM Configuration
VM_HOST = "159.223.53.39"
VM_USER = "root"
VM_PASSWORD = "hH)966663711423aq"
VM_DEST_PATH = "/home/jmeter/test_data/"

def copy_file_to_vm(local_file):
    """Copy file to VM via SCP"""

    # Check if file exists
    if not os.path.exists(local_file):
        print(f"Error: File '{local_file}' not found")
        return False

    try:
        print(f"Connecting to {VM_USER}@{VM_HOST}...")

        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to VM
        ssh.connect(
            hostname=VM_HOST,
            username=VM_USER,
            password=VM_PASSWORD,
            timeout=10
        )

        print(f"Connected successfully!")
        print(f"Copying {local_file} to {VM_DEST_PATH}...")

        # Create SCP client
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(local_file, VM_DEST_PATH)

        print(f"[OK] File copied successfully to {VM_HOST}:{VM_DEST_PATH}")

        # Verify file exists on remote
        filename = os.path.basename(local_file)
        stdin, stdout, stderr = ssh.exec_command(f"ls -lh {VM_DEST_PATH}{filename}")
        output = stdout.read().decode().strip()
        if output:
            print(f"[OK] Verification: {output}")

        ssh.close()
        return True

    except paramiko.AuthenticationException:
        print("Error: Authentication failed. Check username/password.")
        return False
    except paramiko.SSHException as e:
        print(f"Error: SSH connection failed: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python copy_to_vm.py <local_file>")
        print("")
        print("Examples:")
        print("  python copy_to_vm.py test_data/usernames.csv")
        print("  python copy_to_vm.py results/test_results.csv")
        sys.exit(1)

    local_file = sys.argv[1]
    success = copy_file_to_vm(local_file)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
