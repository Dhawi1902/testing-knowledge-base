# 15. OCI Linux Slave Setup (Hands-On)

This is a practical, step-by-step guide for setting up JMeter slave (worker) machines on Oracle Cloud Infrastructure (OCI) Linux VMs. This covers the exact steps I followed to get distributed testing working with OCI free-tier instances.

For the theory behind distributed testing, see [Section 12](12-distributed-testing.md). For automation scripts, see [Section 14](14-automation-batch.md).


## Prerequisites

- An OCI account (free trial with $300 credits or Always Free tier)
- An SSH key pair generated during instance creation (OCI generates this for you, or you provide your own)
- A terminal with SSH access (Git Bash, WSL, or Cygwin on Windows; native terminal on Mac/Linux)

---

## Step 1: Create OCI Instances

1. Go to **OCI Console > Compute > Instances > Create Instance**

2. Configure:
   - **Name:** `jmeter-slave-1` (use a clear naming convention)
   - **Image:** Oracle Linux 9 (default, works well)
   - **Shape:** `VM.Standard.E5.Flex` — 1 OCPU, 12GB RAM is a good starting point
   - **Networking:** Select your VCN and **public subnet** (so you get a public IP for SSH access)
   - **SSH key:** Upload your public key or let OCI generate one (download and save the private key immediately — you won't get another chance)

3. Click **Create**

4. Repeat for additional slaves (`jmeter-slave-2`, etc.)

> **Free tier note:** Always Free gives you 2x AMD Micro instances (1GB RAM each) — usable but very limited for JMeter. The $300 trial credits let you create more powerful shapes like E5.Flex.

**After creation, note down the public IPs from the instance details page.**

---

## Step 2: Configure OCI Networking

OCI has **two layers of firewall**: the VCN Security List (cloud level) and the OS firewall (instance level). Both must allow the JMeter ports.

### Add Ingress Rules to the Security List

1. Go to **Networking > Virtual Cloud Networks > your VCN**

2. Click the **Security** tab

3. Click **Default Security List for [your-vcn]** (the one attached to your public subnet)

4. Click **Add Ingress Rules**

5. Add these rules:

| Source CIDR | Protocol | Destination Port | Description |
|-------------|----------|-----------------|-------------|
| `0.0.0.0/0` | TCP | `22` | SSH (usually already exists) |
| `0.0.0.0/0` | TCP | `1099` | JMeter RMI |
| `0.0.0.0/0` | TCP | `50000-50100` | JMeter RMI dynamic ports |

> **Security note:** `0.0.0.0/0` allows access from anywhere. For production, restrict the Source CIDR to your office IP or VPN range.

---

## Step 3: SSH Into the Instance

OCI Linux instances use `opc` as the default user:

```bash
# Set key permissions (required on first use)
chmod 600 ssh_key/ssh-key-2026-02-25.key

# Connect
ssh -i ssh_key/ssh-key-2026-02-25.key opc@<PUBLIC_IP>
```

If you get a "Permission denied" error:
- Check the key file permissions (`chmod 600`)
- Verify you're using the correct key (the one generated/uploaded during instance creation)
- Verify the username is `opc` (default for Oracle Linux on OCI)

---

## Step 4: Install Java

JMeter requires Java 8 or higher. I use Java 17 (LTS):

```bash
sudo dnf install -y java-17-openjdk java-17-openjdk-devel
```

Verify:

```bash
java -version
# Expected: openjdk version "17.0.x"
```

---

## Step 5: Install JMeter

Download and install JMeter to `/opt/jmeter`:

```bash
cd /opt

# Download JMeter 5.6.3
sudo wget https://dlcdn.apache.org//jmeter/binaries/apache-jmeter-5.6.3.tgz

# Extract
sudo tar -xzf apache-jmeter-5.6.3.tgz

# Create a symlink for convenience
sudo ln -sfn /opt/apache-jmeter-5.6.3 /opt/jmeter

# Clean up the archive
sudo rm -f apache-jmeter-5.6.3.tgz
```

Verify:

```bash
/opt/jmeter/bin/jmeter --version
# Should show: Apache JMeter 5.6.3
```

> **Important:** Use the **same JMeter version** on all slaves and the controller. Version mismatches cause silent failures in distributed mode.

---

## Step 6: Create Project Directories

Create a consistent directory structure across all slaves:

```bash
PROJECT_DIR="/home/opc/jmeter-PT/linux"

sudo mkdir -p ${PROJECT_DIR}/test_data
sudo mkdir -p ${PROJECT_DIR}/failed_response

# Create subfolders for failed response captures (match your test plan structure)
for folder in get_login_page post_login_fail homepage enrolment_button \
              module_selection_page add_selected_module verify_selection_page \
              submit_page submit_registration complete_registration logout; do
    sudo mkdir -p ${PROJECT_DIR}/failed_response/${folder}
done

# Set ownership to opc
sudo chown -R opc:opc /home/opc/jmeter-PT
```

The directory structure should look like:

```
/home/opc/jmeter-PT/linux/
├── test_data/              ← CSV data files go here
├── failed_response/        ← JMeter saves failed response bodies here
│   ├── get_login_page/
│   ├── post_login_fail/
│   ├── homepage/
│   └── ... (one per sampler)
├── start-slave.sh
├── stop-slave.sh
└── jmeter-slave.log        ← Created when slave starts
```

---

## Step 7: Create Start/Stop Scripts

### start-slave.sh

```bash
cat > /home/opc/jmeter-PT/linux/start-slave.sh << 'EOF'
#!/bin/bash
JMETER_HOME="/opt/jmeter"
HOST_IP=$(hostname -I | awk '{print $1}')

# JVM heap settings — adjust based on your instance memory
export JVM_ARGS="-Xms512m -Xmx1g -XX:+UseG1GC -XX:MaxGCPauseMillis=100 -XX:G1ReservePercent=20"

# Kill any existing jmeter-server process
pkill -f "jmeter-server" 2>/dev/null || true
sleep 1

echo "Starting JMeter slave on ${HOST_IP}..."
nohup ${JMETER_HOME}/bin/jmeter-server \
    -Djava.rmi.server.hostname=${HOST_IP} \
    -Dserver.rmi.localport=50000 \
    -Dserver_port=1099 \
    -Dserver.rmi.ssl.disable=true \
    > /home/opc/jmeter-PT/linux/jmeter-slave.log 2>&1 &

echo "JMeter slave PID: $!"
echo "Log: /home/opc/jmeter-PT/linux/jmeter-slave.log"
EOF

chmod +x /home/opc/jmeter-PT/linux/start-slave.sh
```

**Key flags explained:**

- `-Djava.rmi.server.hostname` — tells RMI to use the private IP (important for OCI where the instance only knows its private IP)
- `-Dserver.rmi.localport=50000` — fixes the dynamic RMI port so we can open it in the firewall
- `-Dserver_port=1099` — the main JMeter RMI port
- `-Dserver.rmi.ssl.disable=true` — disables RMI SSL (JMeter 5.x enables it by default and looks for `rmi_keystore.jks` which doesn't exist). Safe for internal/testing networks
- `nohup ... &` — runs in the background so it survives after you disconnect SSH

### stop-slave.sh

```bash
cat > /home/opc/jmeter-PT/linux/stop-slave.sh << 'EOF'
#!/bin/bash
echo "Stopping JMeter slave..."
pkill -f "jmeter-server" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "JMeter slave stopped."
else
    echo "No JMeter slave process found."
fi
EOF

chmod +x /home/opc/jmeter-PT/linux/stop-slave.sh
```

---

## Step 8: Configure OS Firewall

Oracle Linux uses `firewalld`. Open the JMeter ports:

```bash
sudo firewall-cmd --permanent --add-port=1099/tcp
sudo firewall-cmd --permanent --add-port=50000-50100/tcp
sudo firewall-cmd --reload
```

Verify:

```bash
sudo firewall-cmd --list-ports
# Expected: 1099/tcp 50000-50100/tcp
```

> **Note:** This is the **OS-level** firewall. The OCI Security List (Step 2) is the **cloud-level** firewall. Both must be configured.

---

## Step 9: Set Environment Variables

Add JMeter and Java paths to the opc user's profile:

```bash
cat >> /home/opc/.bashrc << 'EOF'

# JMeter environment
export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which java))))
export JMETER_HOME=/opt/jmeter
export PATH=$JMETER_HOME/bin:$PATH
EOF
```

Apply immediately:

```bash
source /home/opc/.bashrc
```

---

## Step 10: Verify the Setup

Run these checks:

```bash
# Java
java -version

# JMeter
jmeter --version

# Firewall ports
sudo firewall-cmd --list-ports

# Directory structure
ls -la /home/opc/jmeter-PT/linux/

# Scripts are executable
file /home/opc/jmeter-PT/linux/start-slave.sh
```

---

## Step 11: Start JMeter Slave

```bash
bash /home/opc/jmeter-PT/linux/start-slave.sh
```

Check it's running:

```bash
# Check process
ps aux | grep jmeter-server

# Check log
tail -20 /home/opc/jmeter-PT/linux/jmeter-slave.log
```

You should see something like:

```
Created remote object: UnicastServerRef2 [liveRef: [endpoint:[10.0.0.123:50000]...]]
```

To stop:

```bash
bash /home/opc/jmeter-PT/linux/stop-slave.sh
```

---

## My Setup

This is what I ended up with:

| Machine | Role | OS | Public IP | Private IP | JMeter |
|---------|------|----|-----------|------------|--------|
| jmeter-slave-1 | Worker | Oracle Linux 9 | 149.118.146.140 | 10.0.0.123 | 5.6.3 |
| jmeter-slaves-2 | Worker | Oracle Linux 9 | 149.118.137.181 | 10.0.0.188 | 5.6.3 |
| My PC | Controller | Windows 11 | N/A (local) | N/A | 5.6.3 |

**OCI specs:** VM.Standard.E5.Flex — 1 OCPU, 12GB RAM each.

**SSH access:** Key-based authentication using the key generated during OCI instance creation, stored in `ssh_key/` folder.

---

## Troubleshooting

### "Connection refused" when starting slave

- Check if Java is installed: `java -version`
- Check JMeter path: `ls /opt/jmeter/bin/jmeter-server`
- Check the log: `tail -50 /home/opc/jmeter-PT/linux/jmeter-slave.log`

### Controller can't reach the slave

Two firewalls to check:
1. **OCI Security List** — Ingress rules for ports 1099 and 50000-50100 (OCI Console)

2. **OS firewall** — `sudo firewall-cmd --list-ports` should show both port ranges

Test connectivity from your controller:

```bash
# From your PC (replace with slave's public IP)
telnet 149.118.146.140 1099
```

### RMI hostname mismatch

If the slave reports its **private IP** (10.x.x.x) but the controller connects via the **public IP**, you need to set the RMI hostname to the public IP:

```bash
# In start-slave.sh, change HOST_IP to the public IP:
HOST_IP="149.118.146.140"  # Use the public IP instead of hostname -I
```

### "Permission denied" on SSH

```bash
# Fix key permissions
chmod 600 ssh_key/ssh-key-2026-02-25.key

# Verify the username (OCI default is opc, NOT root)
ssh -i ssh_key/ssh-key-2026-02-25.key opc@<IP>
```

### RMI SSL — `rmi_keystore.jks` not found

JMeter 5.x enables RMI SSL by default. Without a keystore file, you'll see:

```
java.io.FileNotFoundException: rmi_keystore.jks (No such file or directory)
```

**Fix** — disable RMI SSL on **both** controller and slave sides:

- **Slave side:** Already handled in `start-slave.sh` with `-Dserver.rmi.ssl.disable=true`

- **Controller side (option A):** Set in `jmeter.properties`:
  ```properties
  server.rmi.ssl.disable=true
  ```
- **Controller side (option B):** Pass as CLI flag:
  ```bat
  jmeter -n -t test.jmx -R slave-ip -Jserver.rmi.ssl.disable=true
  ```

The webapp's `jmeter.py` automatically adds `-Jserver.rmi.ssl.disable=true` when running in distributed mode, but setting it in `jmeter.properties` is more reliable (avoids bytecode caching issues).

### Console shows `summary = 0` but JTL has results

In distributed mode, the JMeter console summariser often shows `summary = 0 in 00:00:00`. This is a **display quirk**, not an actual error.

**What happens:** Workers send results back to the controller via RMI, and the results are written directly to the JTL file. The console summariser doesn't always pick up remote results in real-time.

**How to verify:** Check the JTL file after the test completes:

```bash
# Count result lines (subtract 1 for header)
wc -l results/jmeter-report/<run-folder>/results.jtl

# Check content
head -5 results/jmeter-report/<run-folder>/results.jtl
```

If the JTL has data rows with HTTP 200 status codes, the test worked correctly regardless of what the console showed.

### NAT prevents results from OCI slaves to local PC

**Scenario:** Controller on home/office PC, slaves on OCI cloud.

JMeter distributed testing requires **bidirectional RMI communication**:

1. Controller → Slave (send test plan, start test) — works through NAT
2. Slave → Controller (send results back) — **blocked by NAT**

Your PC behind a home/office router has no public IP. The slaves can't initiate connections back to the controller.

**Symptoms:**

- Test starts on slaves (visible in slave logs)
- Controller shows `summary = 0`
- JTL file is empty or has only the header

**Workarounds:**

1. **Port forwarding** on your router — forward `client.rmi.localport` (e.g., 60000) to your PC

2. **VPN** — put controller and slaves on the same virtual network

3. **Run controller on OCI** — use one OCI instance as both controller and storage, then download results

4. **Same LAN** — use office laptops as slaves (no NAT between them)

This is the primary reason we tested locally first (see [Testing Results](#testing-results)).

### Enterprise antivirus (Symantec, etc.) blocks JMeter

Corporate security tools like Symantec Endpoint Protection can silently block JMeter's RMI traffic. Signs:
- Slave connections fail intermittently
- Tests work on personal PC but not on work PC
- No obvious firewall error, just timeouts

**Check if Symantec is running:**
```bash
tasklist | grep -i "ccSvcHst\|sepWsc\|Symantec"
```

**Workaround:** Ask IT to add exceptions for:

- `java.exe` (or the specific JRE used by JMeter)
- TCP ports 1099, 50000-50100
- JMeter installation directory

### JMeter OutOfMemoryError

Increase heap in `start-slave.sh`:

```bash
# For 12GB RAM instance, you can allocate more
export JVM_ARGS="-Xms2g -Xmx8g -XX:+UseG1GC"
```

---

## Testing Results

This section documents the actual testing I did to validate the distributed setup.

### Test Plan Used

Created `Dummy-HTTP-Test.jmx` — a lightweight test plan hitting [httpbin.org](https://httpbin.org) to validate distributed testing without needing access to the actual application under test.

| Transaction | Method | Endpoint | Purpose |
|-------------|--------|----------|---------|
| T01_Get_Homepage | GET | /get | Simple GET request |
| T02_Post_Data | POST | /post | POST with JSON body |
| T03_Get_Delay | GET | /delay/1 | Simulates slow response (1s) |

Parameters (configurable via `-J` flags):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `threads` | 2 | Number of virtual users per slave |
| `rampup` | 5 | Ramp-up period in seconds |
| `duration` | 30 | Test duration in seconds |
| `thinkTime` | 1000 | Think time between transactions (ms) |

### Test 1: PC → OCI Slaves (Cross-network)

**Setup:** Controller on Windows PC (home network) → 2 OCI slaves (Oracle Linux 9)

**Result: Partially worked**

- Controller connected to slaves successfully
- Test started on slave machines (confirmed in slave logs)
- JTL file was empty — slaves couldn't send results back through NAT
- Root cause: PC behind home router, no public IP for RMI callbacks

**Lesson:** Distributed testing across NAT boundaries requires port forwarding or VPN. See [NAT troubleshooting](#nat-prevents-results-from-oci-slaves-to-local-pc).

### Test 2: Local Distributed Test (localhost)

**Setup:** Controller + slave both on same machine (127.0.0.1)

```bash
# Start slave locally
jmeter-server -Djava.rmi.server.hostname=127.0.0.1 -Dserver.rmi.ssl.disable=true

# Run test against local slave
jmeter -n -t Dummy-HTTP-Test.jmx -l results.jtl -R 127.0.0.1 -Jserver.rmi.ssl.disable=true
```

**Result: Success**

- JTL file contained 16 result lines with valid data
- All HTTP responses returned 200 OK
- Console showed `summary = 0` (display quirk) but results were correctly collected
- Proved the distributed testing mechanism works end-to-end

**Sample JTL output:**
```csv
timeStamp,elapsed,label,responseCode,success,threadName,...
1740470940000,1234,GET /get,200,true,127.0.0.1-Users 1-1,...
```

### Test 3: Webapp-Driven Distributed Test

**Setup:** Used the FastAPI webapp to trigger distributed test via the Fleet Management page

**Result: Success** (for local slaves)

- Webapp correctly reads `slaves.txt`, builds JMeter command with `-R` flag
- Automatically adds `-Jserver.rmi.ssl.disable=true` for distributed runs
- Live output shows console summariser in real-time
- JTL results collected and displayed in the Reports page

### Summary of Network Scenarios

| Scenario | Controller | Slaves | Works? | Notes |
|----------|-----------|--------|--------|-------|
| Same machine | localhost | localhost | Yes | Good for validating setup |
| Same LAN | Office PC | Office laptops | Should work | No NAT, same network |
| PC → Cloud | Home PC | OCI VMs | Partial | NAT blocks result callbacks |
| Cloud → Cloud | OCI VM | OCI VMs | Should work | Same VCN, use private IPs |

---

## Tips

- **Use the private IP for RMI hostname** if both controller and slaves are in the same VCN — lower latency and no egress charges

- **Start with a small test** (2-5 threads, 30 seconds) to validate connectivity before running full load

- **Monitor instance resources** during tests — OCI Console > Compute > Instance > Metrics shows CPU and memory

- **Keep JMeter versions identical** across all machines — even minor version differences can cause serialization errors in distributed mode

- **Automate the setup** — the setup script at `jmeter-working-dir/setup-linux-slave.sh` can be run on new instances to repeat this entire process in one command

- **OCI free tier instances (Micro)** have only 1GB RAM — this limits you to about 100-200 threads. The E5.Flex with 12GB RAM can handle 500-1000+ threads depending on script complexity

- **Save your SSH key securely** — OCI does not store private keys. If you lose it, you lose SSH access to the instance
