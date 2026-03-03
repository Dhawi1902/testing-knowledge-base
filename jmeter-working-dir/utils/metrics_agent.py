#!/usr/bin/env python3
"""Lightweight metrics agent for JMeter slave monitoring.

Runs an HTTP server on port 9100 (configurable) that returns
CPU, RAM, JMeter status, and JVM memory as JSON.

Usage:
    python3 metrics_agent.py              # port 9100
    python3 metrics_agent.py --port 9200  # custom port

Requires: Python 3.6+ (stdlib only, no pip install needed)
"""
import http.server
import json
import os
import socket
import subprocess
import sys


PORT = 9100


def get_cpu():
    """CPU usage from /proc/stat (two samples, 200ms apart)."""
    try:
        import time

        def read_stat():
            with open("/proc/stat") as f:
                parts = f.readline().split()
            # user, nice, system, idle, iowait, irq, softirq, steal
            vals = list(map(int, parts[1:9]))
            idle = vals[3] + vals[4]
            total = sum(vals)
            return idle, total

        idle1, total1 = read_stat()
        time.sleep(0.2)
        idle2, total2 = read_stat()
        d_idle = idle2 - idle1
        d_total = total2 - total1
        return round((1.0 - d_idle / d_total) * 100, 1) if d_total > 0 else 0.0
    except Exception:
        return None


def get_ram():
    """RAM from /proc/meminfo."""
    try:
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    info[parts[0].rstrip(":")] = int(parts[1])
        total = info.get("MemTotal", 0) // 1024
        available = info.get("MemAvailable", 0) // 1024
        used = total - available
        return {
            "ram_total_mb": total,
            "ram_used_mb": used,
            "ram_percent": round(used / total * 100, 1) if total > 0 else 0.0,
        }
    except Exception:
        return {"ram_total_mb": None, "ram_used_mb": None, "ram_percent": None}


def get_disk():
    """Disk usage for / partition from df."""
    try:
        r = subprocess.run(
            ["df", "-BM", "/"],
            capture_output=True, text=True, timeout=3,
        )
        lines = r.stdout.strip().split("\n")
        if len(lines) < 2:
            return {"disk_percent": None, "disk_used_gb": None, "disk_total_gb": None}
        parts = lines[1].split()
        total_mb = int(parts[1].rstrip("M"))
        used_mb = int(parts[2].rstrip("M"))
        return {
            "disk_total_gb": round(total_mb / 1024, 1),
            "disk_used_gb": round(used_mb / 1024, 1),
            "disk_percent": round(used_mb / total_mb * 100, 1) if total_mb > 0 else 0.0,
        }
    except Exception:
        return {"disk_percent": None, "disk_used_gb": None, "disk_total_gb": None}


def get_load():
    """1-minute load average from /proc/loadavg."""
    try:
        with open("/proc/loadavg") as f:
            return round(float(f.read().split()[0]), 2)
    except Exception:
        return None


def get_network():
    """Network bytes from /proc/net/dev (all interfaces except lo)."""
    try:
        rx_total = tx_total = 0
        with open("/proc/net/dev") as f:
            for line in f:
                if ":" not in line:
                    continue
                iface, data = line.split(":", 1)
                if iface.strip() == "lo":
                    continue
                parts = data.split()
                rx_total += int(parts[0])
                tx_total += int(parts[8])
        return {"net_rx_bytes": rx_total, "net_tx_bytes": tx_total}
    except Exception:
        return {"net_rx_bytes": None, "net_tx_bytes": None}


def get_jmeter_status():
    """Check if JMeter server is listening on port 1099."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        up = sock.connect_ex(("127.0.0.1", 1099)) == 0
        sock.close()
        return up
    except Exception:
        return False


def get_jvm_stats():
    """Get JVM memory usage and thread count from /proc if JMeter is running."""
    try:
        r = subprocess.run(
            ["pgrep", "-f", "ApacheJMeter"],
            capture_output=True, text=True, timeout=3,
        )
        pids = [p.strip() for p in r.stdout.strip().split("\n") if p.strip()]
        if not pids:
            return None
        pid = pids[0]
        rss_kb = 0
        threads = 0
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    rss_kb = int(line.split()[1])
                elif line.startswith("Threads:"):
                    threads = int(line.split()[1])
        return {"jvm_pid": int(pid), "jvm_rss_mb": rss_kb // 1024, "jvm_threads": threads}
    except Exception:
        return None


def collect_metrics():
    """Collect all metrics into a single dict."""
    ram = get_ram()
    disk = get_disk()
    net = get_network()
    jmeter_up = get_jmeter_status()
    result = {
        "cpu_percent": get_cpu(),
        **ram,
        **disk,
        "load_1m": get_load(),
        **net,
        "jmeter_running": jmeter_up,
    }
    if jmeter_up:
        jvm = get_jvm_stats()
        if jvm:
            result.update(jvm)
    return result


class MetricsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        data = collect_metrics()
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # suppress request logs


if __name__ == "__main__":
    port = PORT
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--port" and i < len(sys.argv) - 1:
            port = int(sys.argv[i + 1])
    server = http.server.HTTPServer(("0.0.0.0", port), MetricsHandler)
    print(f"Metrics agent listening on port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
