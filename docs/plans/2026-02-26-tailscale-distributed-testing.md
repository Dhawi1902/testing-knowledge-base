# Tailscale for JMeter Distributed Testing — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable Windows PC as JMeter master controlling OCI slaves via Tailscale VPN, bypassing CGNAT.

**Architecture:** Install Tailscale on all 3 machines (Windows PC, slave-1, slave-2) to create a mesh network. Update JMeter RMI configuration to use Tailscale IPs so the bidirectional master↔slave communication works regardless of NAT. No webapp code changes needed — all config is JMeter-side.

**Tech Stack:** Tailscale VPN, JMeter 5.6.3, OCI Oracle Linux 9, Windows 11

---

## Current State

| Machine | Role | Public IP | Private IP | Problem |
|---------|------|-----------|------------|---------|
| Windows PC | Master | Behind CGNAT | 192.168.x.x | Slaves can't reach it |
| jmeter-slave-1 | Worker | 149.118.146.140 | 10.0.0.123 | `start-slave.sh` advertises private IP |
| jmeter-slave-2 | Worker | 149.118.137.181 | 10.0.0.188 | `start-slave.sh` advertises private IP |

**Root cause:** RMI is bidirectional. Master → slave works (slaves have public IPs). Slave → master callback fails (CGNAT blocks inbound). Even between OCI slaves, `start-slave.sh` advertises the private IP (`10.0.0.x`) via `hostname -I`, which isn't routable from outside the VCN.

**After Tailscale:** All 3 machines get `100.x.y.z` IPs that route to each other through encrypted tunnels, bypassing all NAT.

---

## Task 1: Install Tailscale on Windows PC

**Step 1: Download and install**

- Go to https://tailscale.com/download/windows
- Download the installer
- Run installer, follow prompts
- Sign in with your Google/GitHub account

**Step 2: Note your Tailscale IP**

- Tailscale icon appears in system tray
- Click it → your IP is shown (e.g., `100.64.1.1`)
- Write it down — you'll need it later

**Step 3: Verify it's running**

```powershell
tailscale status
```

Expected: Shows your machine as online with a `100.x.y.z` IP.

---

## Task 2: Install Tailscale on Slave-1 (OCI Oracle Linux 9)

**Step 1: SSH into slave-1**

```bash
ssh -i ssh_key/ssh-key-2026-02-25.key opc@149.118.146.140
```

**Step 2: Install Tailscale**

```bash
# Add Tailscale repo and install
curl -fsSL https://tailscale.com/install.sh | sh
```

**Step 3: Start and authenticate**

```bash
sudo tailscale up
```

This prints a URL. Open it in your browser and log in with the **same account** you used on Windows.

**Step 4: Note the Tailscale IP**

```bash
tailscale ip -4
```

Expected: Something like `100.64.1.2`. Write it down.

**Step 5: Verify connectivity to Windows PC**

```bash
ping <windows-tailscale-ip>
```

Expected: Replies come back. This proves the tunnel works.

---

## Task 3: Install Tailscale on Slave-2 (OCI Oracle Linux 9)

Same steps as Task 2, but on slave-2:

```bash
ssh -i ssh_key/ssh-key-2026-02-25.key opc@149.118.137.181
```

Then:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4
```

Note the IP (e.g., `100.64.1.3`).

Verify connectivity:

```bash
ping <windows-tailscale-ip>
ping <slave1-tailscale-ip>
```

Expected: Both respond.

---

## Task 4: Verify Full Mesh Connectivity

From your **Windows PC**, test all connections:

```powershell
ping <slave1-tailscale-ip>
ping <slave2-tailscale-ip>
```

From **slave-1**:

```bash
ping <slave2-tailscale-ip>
ping <windows-tailscale-ip>
```

All pings should succeed. If any fail, check Tailscale status on that machine (`tailscale status`).

---

## Task 5: Update `start-slave.sh` on Both Slaves

The current script uses `hostname -I` which returns the OCI private IP (`10.0.0.x`). We need it to use the Tailscale IP instead.

**On each slave**, SSH in and edit the start script:

```bash
ssh -i ssh_key/ssh-key-2026-02-25.key opc@<slave-public-ip>
nano ~/jmeter-PT/linux/start-slave.sh
```

**Change this line:**

```bash
HOST_IP=$(hostname -I | awk '{print $1}')
```

**To:**

```bash
# Use Tailscale IP if available, otherwise fall back to system IP
if command -v tailscale &> /dev/null && tailscale status &> /dev/null; then
    HOST_IP=$(tailscale ip -4)
else
    HOST_IP=$(hostname -I | awk '{print $1}')
fi
```

This way:
- If Tailscale is installed and running → uses Tailscale IP (for cross-network master)
- If Tailscale is not running → falls back to the original behavior (for OCI-to-OCI master)

**Do this on both slave-1 and slave-2.**

---

## Task 6: Configure Windows JMeter (Master Side)

Edit your local JMeter properties file:

```
C:\Users\user\Documents\VTC\2026\testing-knowledge-base\jmeter-working-dir\apache-jmeter-5.6.3\bin\jmeter.properties
```

> **Note:** Adjust the path if your JMeter is installed elsewhere. Check `settings.json` for `jmeter_path`.

Add or update these lines:

```properties
# Tailscale — master advertises its Tailscale IP for RMI callbacks
java.rmi.server.hostname=<windows-tailscale-ip>

# Pin the RMI callback port so firewalls don't block random ports
client.rmi.localport=50000
```

Replace `<windows-tailscale-ip>` with the actual `100.x.y.z` from Task 1.

---

## Task 7: Update Webapp Fleet Config

Update `slaves.txt` to use the Tailscale IPs so the webapp sends `-R` with the right addresses:

**File:** `jmeter-working-dir/slaves.txt`

```json
[
  {"ip": "<slave1-tailscale-ip>", "enabled": true},
  {"ip": "<slave2-tailscale-ip>", "enabled": true}
]
```

Alternatively, do this through the webapp Fleet page (`/perftest/fleet`).

---

## Task 8: Restart Slaves and Test

**Step 1: Restart JMeter slaves**

On each slave (via SSH or webapp Fleet page):

```bash
~/jmeter-PT/linux/stop-slave.sh
~/jmeter-PT/linux/start-slave.sh
```

Verify the log shows the Tailscale IP:

```bash
cat ~/jmeter-PT/linux/jmeter-slave.log
```

Expected: `Starting JMeter slave on 100.64.x.x...` (Tailscale IP, not `10.0.0.x`)

**Step 2: Test RMI connectivity from Windows**

Quick test from PowerShell:

```powershell
Test-NetConnection -ComputerName <slave1-tailscale-ip> -Port 1099
Test-NetConnection -ComputerName <slave2-tailscale-ip> -Port 1099
```

Expected: `TcpTestSucceeded: True` for both.

**Step 3: Run a distributed test**

Either through the webapp or CLI:

```cmd
jmeter -n -t test_plan/your-test.jmx -R <slave1-tailscale-ip>,<slave2-tailscale-ip> -Jserver.rmi.ssl.disable=true -l results/test.jtl
```

Expected: Test starts, both slaves execute, results come back, JTL file has data.

---

## Task 9: Update `setup-linux-slave.sh` (Repo)

Update the repo's setup script so future slaves get the Tailscale-aware `start-slave.sh`.

**File:** `jmeter-working-dir/setup-linux-slave.sh` (line 91)

**Change:**

```bash
HOST_IP=$(hostname -I | awk '{print $1}')
```

**To:**

```bash
# Use Tailscale IP if available (for cross-network master), otherwise system IP
if command -v tailscale &> /dev/null && tailscale status &> /dev/null; then
    HOST_IP=$(tailscale ip -4)
else
    HOST_IP=$(hostname -I | awk '{print $1}')
fi
```

**Commit:**

```bash
git add jmeter-working-dir/setup-linux-slave.sh
git commit -m "feat: support Tailscale IP in start-slave.sh for cross-network distributed testing"
```

---

## Task 10: Update Documentation

Update `jmeter/docs/15-oci-linux-slave-setup.md` — add a section about Tailscale setup:

- Why it's needed (CGNAT blocks RMI callbacks)
- Installation steps (link to Tailscale docs)
- Updated "My Setup" table with Tailscale IPs column
- Note about `start-slave.sh` auto-detecting Tailscale

Update `jmeter/docs/12-distributed-testing.md` — add a note in the NAT/troubleshooting section about Tailscale as a solution.

---

## Summary: IP Reference Table (fill in after setup)

| Machine | Public IP | Private IP | Tailscale IP | Role |
|---------|-----------|------------|--------------|------|
| Windows PC | Behind CGNAT | 192.168.x.x | `100.___.___.___` | Master |
| jmeter-slave-1 | 149.118.146.140 | 10.0.0.123 | `100.___.___.___` | Worker |
| jmeter-slave-2 | 149.118.137.181 | 10.0.0.188 | `100.___.___.___` | Worker |

## Rollback

If something goes wrong, you can always:
1. Stop Tailscale on the slaves (`sudo tailscale down`)
2. Slaves fall back to `hostname -I` (private IP)
3. Use slave-1 as master with public OCI IPs (the old approach)
