#!/bin/bash
# =============================================================
# JMeter Slave Setup Script for OCI Linux (Oracle Linux 8/9)
# Run as: sudo bash setup-linux-slave.sh
# =============================================================
set -e

echo "========================================="
echo "  JMeter Slave Setup — OCI Linux"
echo "========================================="

JMETER_VERSION="5.6.3"
JMETER_HOME="/opt/jmeter"
JMETER_ARCHIVE="apache-jmeter-${JMETER_VERSION}.tgz"
JMETER_URL="https://dlcdn.apache.org//jmeter/binaries/${JMETER_ARCHIVE}"
OPC_HOME="/home/opc"
PROJECT_DIR="${OPC_HOME}/jmeter-PT/linux"

# -----------------------------------------------------------
# 1. Install Java 17
# -----------------------------------------------------------
echo ""
echo "[1/6] Installing Java 17..."
if java -version 2>&1 | grep -q "17"; then
    echo "  -> Java 17 already installed, skipping."
else
    dnf install -y java-17-openjdk java-17-openjdk-devel
    echo "  -> Java 17 installed."
fi
java -version 2>&1 | head -1

# -----------------------------------------------------------
# 2. Download & Install JMeter
# -----------------------------------------------------------
echo ""
echo "[2/6] Installing JMeter ${JMETER_VERSION}..."
if [ -d "${JMETER_HOME}" ] && [ -f "${JMETER_HOME}/bin/jmeter" ]; then
    echo "  -> JMeter already installed at ${JMETER_HOME}, skipping."
else
    cd /opt
    if [ ! -f "${JMETER_ARCHIVE}" ]; then
        echo "  -> Downloading JMeter..."
        wget -q "${JMETER_URL}" -O "${JMETER_ARCHIVE}"
    fi
    tar -xzf "${JMETER_ARCHIVE}"
    ln -sfn "/opt/apache-jmeter-${JMETER_VERSION}" "${JMETER_HOME}"
    rm -f "${JMETER_ARCHIVE}"
    echo "  -> JMeter installed at ${JMETER_HOME}"
fi
${JMETER_HOME}/bin/jmeter --version 2>&1 | head -3

# -----------------------------------------------------------
# 3. Create project directory structure
# -----------------------------------------------------------
echo ""
echo "[3/6] Creating project directories..."
mkdir -p "${PROJECT_DIR}/test_data"
mkdir -p "${PROJECT_DIR}/failed_response"

# Create failed_response subfolders
FOLDERS=(
    "get_login_page"
    "post_login_fail"
    "homepage"
    "enrolment_button"
    "module_selection_page"
    "add_selected_module"
    "verify_selection_page"
    "submit_page"
    "submit_registration"
    "complete_registration"
    "logout"
)
for folder in "${FOLDERS[@]}"; do
    mkdir -p "${PROJECT_DIR}/failed_response/${folder}"
done

chown -R opc:opc "${OPC_HOME}/jmeter-PT"
echo "  -> Directories created at ${PROJECT_DIR}"

# -----------------------------------------------------------
# 4. Create start/stop scripts
# -----------------------------------------------------------
echo ""
echo "[4/6] Creating start/stop slave scripts..."

cat > "${PROJECT_DIR}/start-slave.sh" << 'SCRIPT'
#!/bin/bash
# Start JMeter in server (slave) mode
JMETER_HOME="/opt/jmeter"
HOST_IP=$(hostname -I | awk '{print $1}')

# Apply heap settings
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
SCRIPT

cat > "${PROJECT_DIR}/stop-slave.sh" << 'SCRIPT'
#!/bin/bash
# Stop JMeter slave process
echo "Stopping JMeter slave..."
pkill -f "jmeter-server" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "JMeter slave stopped."
else
    echo "No JMeter slave process found."
fi
SCRIPT

chmod +x "${PROJECT_DIR}/start-slave.sh"
chmod +x "${PROJECT_DIR}/stop-slave.sh"
chown opc:opc "${PROJECT_DIR}/start-slave.sh" "${PROJECT_DIR}/stop-slave.sh"
echo "  -> Scripts created."

# -----------------------------------------------------------
# 5. Configure firewall
# -----------------------------------------------------------
echo ""
echo "[5/6] Configuring firewall..."
if systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-port=1099/tcp   2>/dev/null || true
    firewall-cmd --permanent --add-port=50000-50100/tcp 2>/dev/null || true
    firewall-cmd --reload
    echo "  -> Firewall rules added (1099, 50000-50100)."
else
    echo "  -> firewalld not running, skipping (iptables or OCI security list handles it)."
fi

# -----------------------------------------------------------
# 6. Add JAVA_HOME and JMETER_HOME to opc profile
# -----------------------------------------------------------
echo ""
echo "[6/6] Setting environment variables..."
PROFILE_FILE="${OPC_HOME}/.bashrc"
if ! grep -q "JMETER_HOME" "${PROFILE_FILE}" 2>/dev/null; then
    cat >> "${PROFILE_FILE}" << 'ENV'

# JMeter environment
export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which java))))
export JMETER_HOME=/opt/jmeter
export PATH=$JMETER_HOME/bin:$PATH
ENV
    echo "  -> Environment variables added to .bashrc"
else
    echo "  -> Environment variables already configured."
fi

# -----------------------------------------------------------
# Summary
# -----------------------------------------------------------
echo ""
echo "========================================="
echo "  Setup Complete!"
echo "========================================="
echo ""
echo "  Java:    $(java -version 2>&1 | head -1)"
echo "  JMeter:  ${JMETER_HOME} (v${JMETER_VERSION})"
echo "  Project: ${PROJECT_DIR}"
echo ""
echo "  To start slave:  sudo -u opc bash ${PROJECT_DIR}/start-slave.sh"
echo "  To stop slave:   sudo -u opc bash ${PROJECT_DIR}/stop-slave.sh"
echo ""
echo "  IMPORTANT: Also add ingress rules in OCI Console:"
echo "    - VCN > Subnet > Security List > Add Ingress Rules"
echo "    - Port 1099 TCP (JMeter RMI)"
echo "    - Port 50000-50100 TCP (RMI dynamic)"
echo "    - Source CIDR: your IP or 0.0.0.0/0"
echo "========================================="
