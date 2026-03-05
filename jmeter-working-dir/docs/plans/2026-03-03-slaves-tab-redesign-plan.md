# Slaves Tab Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the Fleet slaves tab with two-row inline resource cards, a summary bar replacing the bottom monitoring panel, enhanced metrics agent, and historical sparklines.

**Architecture:** Extend `metrics_agent.py` with disk/load/network/thread metrics. Redesign `renderList()` and `renderGrid()` in `fleet-slaves.js` to render two-row cards with inline resource bars. Replace the bottom monitoring panel table with a compact summary strip. Store last 20 data points per slave client-side for sparkline rendering.

**Tech Stack:** Python 3.13 (metrics agent), vanilla JS (no build tools), CSS custom properties, SVG sparklines, FastAPI backend (no API changes needed — agent extension is additive).

---

### Task 1: Extend Metrics Agent

Add disk usage, load average, network I/O, and JMeter thread count to the metrics agent.

**Files:**
- Modify: `jmeter-working-dir/utils/metrics_agent.py`

**Step 1: Add `get_disk()` function**

After `get_ram()` (line 66), add:

```python
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
```

**Step 2: Add `get_load()` function**

```python
def get_load():
    """1-minute load average from /proc/loadavg."""
    try:
        with open("/proc/loadavg") as f:
            return round(float(f.read().split()[0]), 2)
    except Exception:
        return None
```

**Step 3: Add `get_network()` function**

```python
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
```

**Step 4: Add `get_jmeter_threads()` to `get_jvm_stats()`**

Extend the existing `get_jvm_stats()` function — after reading `VmRSS`, also count threads:

```python
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
```

**Step 5: Update `collect_metrics()` to include new fields**

```python
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
```

**Step 6: Verify locally**

Run: `python jmeter-working-dir/utils/metrics_agent.py --help` (just check it parses without error — actual metrics need Linux /proc)

**Step 7: Commit**

```bash
git add jmeter-working-dir/utils/metrics_agent.py
git commit -m "feat(metrics): add disk, load, network, thread metrics to agent"
```

---

### Task 2: Add Metrics History + SVG Sparkline to Fleet Core

Add client-side metrics history tracking and a sparkline SVG renderer.

**Files:**
- Modify: `jmeter-working-dir/webapp/static/js/fleet-core.js`

**Step 1: Add `metricsHistory` to Fleet state**

In the `window.Fleet = { ... }` object (line 11, after `resourceData: {}`), add:

```js
metricsHistory: {},  // { ip: [{ts, cpu, ram}, ...] } — last 20 data points
```

**Step 2: Add `recordMetrics(ip, cpu, ram)` helper**

After the `progressBar()` function, add:

```js
function recordMetrics(ip, cpu, ram) {
    if (!Fleet.metricsHistory[ip]) Fleet.metricsHistory[ip] = [];
    const h = Fleet.metricsHistory[ip];
    h.push({ ts: Date.now(), cpu: cpu, ram: ram });
    if (h.length > 20) h.shift();
}
```

**Step 3: Add `miniSparkline(values, color)` SVG helper**

```js
function miniSparkline(values, color) {
    if (!values || values.length < 2) return '';
    const w = 60, h = 16, max = 100;
    const step = w / (values.length - 1);
    const pts = values.map((v, i) => `${(i * step).toFixed(1)},${(h - (v / max) * h).toFixed(1)}`).join(' ');
    return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" style="vertical-align:middle;margin-left:4px;">` +
        `<polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>` +
        `</svg>`;
}
```

**Step 4: Add `inlineMetrics(ip)` helper**

Renders a compact inline metrics row for a slave:

```js
function inlineMetrics(ip) {
    const r = Fleet.resourceData[ip];
    if (!r || r.cpu_percent == null) return '';
    const hist = Fleet.metricsHistory[ip] || [];
    const cpuVals = hist.map(h => h.cpu);
    const ramVals = hist.map(h => h.ram);
    let html = '<div class="slave-metrics">';
    // CPU
    html += `<span class="metric-item">CPU ${progressBar(r.cpu_percent, { warn: 60, danger: 80 })}${miniSparkline(cpuVals, 'var(--color-primary)')}</span>`;
    // RAM
    const ramDetail = r.ram_total_mb ? ` <span class="text-xs text-light">${r.ram_used_mb}/${r.ram_total_mb}MB</span>` : '';
    html += `<span class="metric-item">RAM ${progressBar(r.ram_percent, { warn: 75, danger: 90 })}${miniSparkline(ramVals, 'var(--color-info, #3b82f6)')}${ramDetail}</span>`;
    // JVM RSS
    if (r.jvm_rss_mb != null) {
        const cls = r.jvm_rss_mb > 900 ? 'text-danger' : r.jvm_rss_mb > 600 ? 'text-warning' : '';
        html += `<span class="metric-item"><span class="${cls}" style="font-weight:600;">JVM ${r.jvm_rss_mb}MB</span></span>`;
    }
    // Disk
    if (r.disk_percent != null) {
        html += `<span class="metric-item">Disk ${progressBar(r.disk_percent, { warn: 80, danger: 90 })}</span>`;
    }
    // Load
    if (r.load_1m != null) {
        html += `<span class="metric-item text-sm">Load ${r.load_1m}</span>`;
    }
    // JMeter threads
    if (r.jvm_threads != null) {
        html += `<span class="metric-item text-sm">${r.jvm_threads} threads</span>`;
    }
    html += '</div>';
    return html;
}
```

**Step 5: Commit**

```bash
git add jmeter-working-dir/webapp/static/js/fleet-core.js
git commit -m "feat(fleet): add metrics history, SVG sparkline, and inline metrics helpers"
```

---

### Task 3: Update `_applyMetricsResults` to Record History

**Files:**
- Modify: `jmeter-working-dir/webapp/static/js/fleet-slaves.js` (lines 835-851)

**Step 1: Extend `_applyMetricsResults` to store new fields and record history**

Replace the existing function:

```js
function _applyMetricsResults(results) {
    (results || []).forEach(r => {
        if (r.ok) {
            Fleet.resourceData[r.ip] = {
                cpu_percent: r.cpu_percent,
                ram_percent: r.ram_percent,
                ram_used_mb: r.ram_used_mb,
                ram_total_mb: r.ram_total_mb,
                jmeter_running: r.jmeter_running,
                jvm_rss_mb: r.jvm_rss_mb || null,
                jvm_threads: r.jvm_threads || null,
                disk_percent: r.disk_percent || null,
                disk_used_gb: r.disk_used_gb || null,
                disk_total_gb: r.disk_total_gb || null,
                load_1m: r.load_1m || null,
                net_rx_bytes: r.net_rx_bytes || null,
                net_tx_bytes: r.net_tx_bytes || null,
            };
            // Record for sparklines
            if (r.cpu_percent != null && r.ram_percent != null) {
                recordMetrics(r.ip, r.cpu_percent, r.ram_percent);
            }
            const slave = Fleet.slaveData.find(s => s.ip === r.ip);
            if (slave) slave.jmeter = r.jmeter_running ? 'running' : 'stopped';
        }
    });
    render();
}
```

**Step 2: Commit**

```bash
git add jmeter-working-dir/webapp/static/js/fleet-slaves.js
git commit -m "feat(fleet): record metrics history and store extended resource fields"
```

---

### Task 4: Redesign List View — Two-Row Cards

**Files:**
- Modify: `jmeter-working-dir/webapp/static/js/fleet-slaves.js` — `renderList()` function (lines 73-131)

**Step 1: Rewrite `renderList()` with two-row card layout**

Replace the entire `renderList()` function:

```js
function renderList() {
    const container = document.getElementById('slaveContainer');
    if (!Fleet.slaveData.length) { container.innerHTML = ''; return; }
    const allSelected = Fleet.slaveData.length > 0 && Fleet.slaveData.every(s => Fleet.selected.has(s.ip));
    let html = '<div class="slave-list">';
    if (Fleet.isAdmin) {
        html += `<div class="slave-list-header">
            <label class="check">
                <input type="checkbox" class="select-cb" ${allSelected ? 'checked' : ''} onchange="toggleSelectAll(this.checked)">
                <span class="check-box"></span>
            </label>
            <span>Select all</span>
        </div>`;
    }
    Fleet.slaveData.forEach((s, i) => {
        const enabled = s.enabled !== false;
        const sel = Fleet.selected.has(s.ip);
        const expanded = Fleet.expandedConfigs.has(s.ip);
        const hasOverrides = s.overrides && (s.overrides.user || s.overrides.password || s.overrides.dest_path);
        const aIp = escAttr(s.ip);
        const ipClick = Fleet.isAdmin ? `onclick="editSlaveIp('${aIp}', this)" title="Click to edit"` : '';
        const hasMetrics = Fleet.resourceData[s.ip] && Fleet.resourceData[s.ip].cpu_percent != null;

        html += `<div class="slave-entry${enabled ? '' : ' disabled'}${sel ? ' selected' : ''}">
            <div class="slave-row">
                ${Fleet.isAdmin ? `<label class="check"><input type="checkbox" class="select-cb" ${sel ? 'checked' : ''} onchange="toggleSelect('${aIp}', this.checked)"><span class="check-box"></span></label>` : ''}
                ${statusDot(s)}
                <span class="slave-ip" ${ipClick}>${escHtml(s.ip)}</span>
                <span class="slave-meta">VM #${i + 1}${s.nickname ? ` <em>${escHtml(s.nickname)}</em>` : ''}${hasOverrides ? ' <span class="badge badge-sm">custom</span>' : ''}${historySparkline(s)}</span>
                <div class="slave-actions">
                    ${Fleet.isAdmin && enabled ? `<button class="btn btn-outline btn-xs" onclick="startSingle('${aIp}')" data-tooltip="Start">&#9654;</button>` : ''}
                    ${Fleet.isAdmin && enabled ? `<button class="btn btn-danger-outline btn-xs" onclick="stopSingle('${aIp}')" data-tooltip="Stop">&#9632;</button>` : ''}
                    ${Fleet.isAdmin ? `<button class="gear-btn${expanded ? ' active' : ''}" onclick="toggleConfig('${aIp}')" data-tooltip="SSH overrides">${gearIcon()}</button>` : ''}
                    ${Fleet.isAdmin && enabled ? `<div class="dropdown">
                        <button class="btn btn-outline btn-xs" onclick="toggleDropdown(this)">${Fleet.ICON_MORE}</button>
                        <div class="dropdown-menu">
                            <button class="dropdown-item" onclick="testSsh('${aIp}')">SSH Test</button>
                            <button class="dropdown-item" onclick="testRmi('${aIp}')">RMI Test</button>
                            <button class="dropdown-item" onclick="provisionSingle('${aIp}')">Provision</button>
                            <button class="dropdown-item" onclick="restartSingle('${aIp}')">Restart</button>
                            <button class="dropdown-item" onclick="viewLog('${aIp}')">View Log</button>
                            <button class="dropdown-item" onclick="confirmCleanData('${aIp}')">Clean Data</button>
                            <button class="dropdown-item" onclick="confirmCleanLog('${aIp}')">Clean Log</button>
                            <div class="dropdown-sep"></div>
                            <button class="dropdown-item" style="color:var(--color-danger)" onclick="removeSlave('${aIp}')">Remove</button>
                        </div>
                    </div>` : ''}
                    ${Fleet.isAdmin ? `<label class="toggle" title="${enabled ? 'Disable' : 'Enable'}">
                        <input type="checkbox" ${enabled ? 'checked' : ''} onchange="toggleSlave('${aIp}', this.checked)">
                        <span class="toggle-track"></span>
                    </label>` : ''}
                </div>
            </div>
            <div class="slave-row-details">
                ${hasMetrics ? inlineMetrics(s.ip) : `<div class="slave-status-row">${statusBadge(s)}${provisionBadges(s)}${s.error ? ' <span class="text-sm text-danger">' + escHtml(s.error) + '</span>' : ''}</div>`}
                ${hasMetrics ? `<div class="slave-status-row">${statusBadge(s)}${provisionBadges(s)}</div>` : ''}
            </div>
            ${expanded ? renderConfigPanel(s) : ''}
        </div>`;
    });
    html += '</div>';
    container.innerHTML = html;
}
```

Key changes:
- Row 1: IP, VM#/nickname, sparkline on left; Start, Stop, gear, "...", toggle on right
- Row 2 (`.slave-row-details`): Inline metrics when available, otherwise status/provision badges
- Provision badges + status badge always visible in row 2 (moved from `.slave-actions`)

**Step 2: Commit**

```bash
git add jmeter-working-dir/webapp/static/js/fleet-slaves.js
git commit -m "feat(fleet): redesign list view with two-row inline resource cards"
```

---

### Task 5: Redesign Grid View — Two-Row Cards

**Files:**
- Modify: `jmeter-working-dir/webapp/static/js/fleet-slaves.js` — `renderGrid()` function (lines 134-188)

**Step 1: Rewrite `renderGrid()` with metrics row**

Replace the entire `renderGrid()` function:

```js
function renderGrid() {
    const container = document.getElementById('slaveContainer');
    if (!Fleet.slaveData.length) { container.innerHTML = ''; return; }
    let html = '<div class="slave-grid">';
    Fleet.slaveData.forEach((s, i) => {
        const enabled = s.enabled !== false;
        const sel = Fleet.selected.has(s.ip);
        const expanded = Fleet.expandedConfigs.has(s.ip);
        const hasOverrides = s.overrides && (s.overrides.user || s.overrides.password || s.overrides.dest_path);
        const aIp = escAttr(s.ip);
        const ipClick = Fleet.isAdmin ? `onclick="editSlaveIp('${aIp}', this)" title="Click to edit"` : '';
        const hasMetrics = Fleet.resourceData[s.ip] && Fleet.resourceData[s.ip].cpu_percent != null;

        html += `<div class="vm-card${enabled ? '' : ' disabled'}${sel ? ' selected' : ''}">
            <div class="flex-between gap-8">
                <div class="flex gap-8 items-center">
                    ${Fleet.isAdmin ? `<label class="check"><input type="checkbox" class="select-cb" ${sel ? 'checked' : ''} onchange="toggleSelect('${aIp}', this.checked)"><span class="check-box"></span></label>` : ''}
                    <span class="vm-ip" ${ipClick}>${escHtml(s.ip)}</span>
                    ${hasOverrides ? '<span class="badge badge-sm">custom</span>' : ''}
                </div>
                <div class="flex gap-4 items-center flex-wrap">
                    ${Fleet.isAdmin && enabled ? `<button class="btn btn-outline btn-xs" onclick="startSingle('${aIp}')" data-tooltip="Start">&#9654;</button>` : ''}
                    ${Fleet.isAdmin && enabled ? `<button class="btn btn-danger-outline btn-xs" onclick="stopSingle('${aIp}')" data-tooltip="Stop">&#9632;</button>` : ''}
                    ${Fleet.isAdmin ? `<button class="gear-btn${expanded ? ' active' : ''}" onclick="toggleConfig('${aIp}')" data-tooltip="SSH overrides">${gearIcon()}</button>` : ''}
                    ${Fleet.isAdmin && enabled ? `<div class="dropdown">
                        <button class="btn btn-outline btn-xs" onclick="toggleDropdown(this)">${Fleet.ICON_MORE}</button>
                        <div class="dropdown-menu">
                            <button class="dropdown-item" onclick="testSsh('${aIp}')">SSH Test</button>
                            <button class="dropdown-item" onclick="testRmi('${aIp}')">RMI Test</button>
                            <button class="dropdown-item" onclick="provisionSingle('${aIp}')">Provision</button>
                            <button class="dropdown-item" onclick="restartSingle('${aIp}')">Restart</button>
                            <button class="dropdown-item" onclick="viewLog('${aIp}')">View Log</button>
                            <button class="dropdown-item" onclick="confirmCleanData('${aIp}')">Clean Data</button>
                            <button class="dropdown-item" onclick="confirmCleanLog('${aIp}')">Clean Log</button>
                            <div class="dropdown-sep"></div>
                            <button class="dropdown-item" style="color:var(--color-danger)" onclick="removeSlave('${aIp}')">Remove</button>
                        </div>
                    </div>` : ''}
                    ${Fleet.isAdmin ? `<label class="toggle" title="${enabled ? 'Disable' : 'Enable'}">
                        <input type="checkbox" ${enabled ? 'checked' : ''} onchange="toggleSlave('${aIp}', this.checked)">
                        <span class="toggle-track"></span>
                    </label>` : ''}
                </div>
            </div>
            <div class="vm-card-meta">
                VM #${i + 1}${s.nickname ? ` &mdash; <em>${escHtml(s.nickname)}</em>` : ''}
                ${historySparkline(s)}
            </div>
            <div class="vm-card-status">
                ${statusBadge(s)}${provisionBadges(s)}${s.error ? ' <span class="text-sm text-danger">' + escHtml(s.error) + '</span>' : ''}
            </div>
            ${hasMetrics ? inlineMetrics(s.ip) : ''}
            ${expanded ? renderConfigPanel(s) : ''}
        </div>`;
    });
    html += '</div>';
    container.innerHTML = html;
}
```

**Step 2: Commit**

```bash
git add jmeter-working-dir/webapp/static/js/fleet-slaves.js
git commit -m "feat(fleet): redesign grid view with inline resource metrics"
```

---

### Task 6: Replace Monitoring Panel with Summary Bar

**Files:**
- Modify: `jmeter-working-dir/webapp/static/js/fleet-slaves.js` — `renderMonitoringPanel()` (lines 924-982)
- Modify: `jmeter-working-dir/webapp/templates/_fleet_slaves.html` — monitoring panel div (lines 78-86)

**Step 1: Update HTML template — replace monitoring panel with summary bar**

Replace the monitoring panel div in `_fleet_slaves.html`:

```html
<!-- Fleet Summary Bar -->
<div class="fleet-summary-bar" id="monitoringSummary" style="display:none;">
    <span class="live-indicator" id="liveIndicator"></span>
    <span class="summary-label" id="summaryContent"></span>
    <span class="text-xs text-light" id="monitorIntervalLabel"></span>
    <span class="text-xs text-light" id="nextPollLabel"></span>
</div>
```

**Step 2: Rewrite `renderMonitoringPanel()` → `renderSummaryBar()`**

Replace the function entirely:

```js
function renderMonitoringPanel() {
    const bar = document.getElementById('monitoringSummary');
    if (!bar) return;

    const hasData = Object.keys(Fleet.resourceData).length > 0;
    if (!Fleet._metricsTimer || !hasData) {
        bar.style.display = 'none';
        return;
    }
    bar.style.display = '';

    // Update interval label
    const intervalLabel = document.getElementById('monitorIntervalLabel');
    if (intervalLabel) {
        const secs = Fleet._metricsInterval / 1000;
        intervalLabel.textContent = secs >= 60 ? `every ${secs/60}m` : `every ${secs}s`;
    }

    // Compute averages across enabled slaves
    let cpuSum = 0, ramSum = 0, count = 0, jmeterUp = 0, totalEnabled = 0;
    Fleet.slaveData.forEach(s => {
        if (s.enabled === false) return;
        totalEnabled++;
        const r = Fleet.resourceData[s.ip];
        if (!r) return;
        if (r.cpu_percent != null) { cpuSum += r.cpu_percent; count++; }
        if (r.ram_percent != null) { ramSum += r.ram_percent; }
        if (r.jmeter_running) jmeterUp++;
    });

    const avgCpu = count > 0 ? Math.round(cpuSum / count) : '—';
    const avgRam = count > 0 ? Math.round(ramSum / count) : '—';

    const content = document.getElementById('summaryContent');
    if (content) {
        content.innerHTML = `Avg CPU: <strong>${avgCpu}%</strong> &nbsp;|&nbsp; Avg RAM: <strong>${avgRam}%</strong> &nbsp;|&nbsp; JMeter: <strong>${jmeterUp}/${totalEnabled}</strong> up`;
    }

    // Next poll countdown
    const nextEl = document.getElementById('nextPollLabel');
    if (nextEl && Fleet._lastPollTs) {
        const elapsed = Date.now() - Fleet._lastPollTs;
        const remaining = Math.max(0, Math.round((Fleet._metricsInterval - elapsed) / 1000));
        nextEl.textContent = `next: ${remaining}s`;
    }
}
```

**Step 3: Add `_lastPollTs` tracking**

In `_pollMetrics()`, record the timestamp:

```js
async function _pollMetrics() {
    try {
        Fleet._lastPollTs = Date.now();
        const data = await api('/api/slaves/metrics');
        const results = data.results || [];
        if (results.some(r => r.ok && r.agent)) {
            _applyMetricsResults(results);
        }
    } catch (e) { /* silent fail for auto-poll */ }
}
```

Also add `_lastPollTs: null` to Fleet state in fleet-core.js.

**Step 4: Add countdown timer refresh**

Add a 1-second interval to update the countdown. In `startMetricsPolling()`:

```js
function startMetricsPolling() {
    if (Fleet._metricsTimer) return;
    _pollMetrics();
    Fleet._metricsTimer = setInterval(_pollMetrics, Fleet._metricsInterval);
    Fleet._countdownTimer = setInterval(renderMonitoringPanel, 1000);
}
```

In `stopMetricsPolling()`, also clear the countdown:

```js
function stopMetricsPolling() {
    if (Fleet._metricsTimer) {
        clearInterval(Fleet._metricsTimer);
        Fleet._metricsTimer = null;
    }
    if (Fleet._countdownTimer) {
        clearInterval(Fleet._countdownTimer);
        Fleet._countdownTimer = null;
    }
    localStorage.removeItem('fleet_monitoring');
    renderMonitoringPanel();
}
```

Add `_countdownTimer: null` to Fleet state in fleet-core.js.

**Step 5: Commit**

```bash
git add jmeter-working-dir/webapp/static/js/fleet-slaves.js \
       jmeter-working-dir/webapp/static/js/fleet-core.js \
       jmeter-working-dir/webapp/templates/_fleet_slaves.html
git commit -m "feat(fleet): replace monitoring panel with compact summary bar"
```

---

### Task 7: CSS for Two-Row Cards and Summary Bar

**Files:**
- Modify: `jmeter-working-dir/webapp/static/css/style.css`

**Step 1: Add slave metrics row styles**

After the existing `.slave-list .slave-row .slave-actions` rule (~line 695), add:

```css
/* Row 2: metrics + status details */
.slave-row-details {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 16px 10px;
    flex-wrap: wrap;
}
.slave-status-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}
.slave-metrics {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
    font-size: 12px;
}
.slave-metrics .metric-item {
    display: flex;
    align-items: center;
    gap: 4px;
    white-space: nowrap;
}
.slave-metrics .monitor-bar {
    width: 80px;
    height: 14px;
    min-width: 80px;
}
.slave-metrics .monitor-bar-label {
    font-size: 10px;
}
```

**Step 2: Add summary bar styles**

Replace the `.monitoring-panel` and `.monitoring-header` rules:

```css
/* Fleet Summary Bar */
.fleet-summary-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 16px;
    border-top: 1px solid var(--color-border);
    font-size: 13px;
    background: color-mix(in srgb, var(--color-primary) 4%, var(--color-surface));
}
```

**Step 3: Add grid card meta/status styles**

```css
.vm-card-meta {
    font-size: 12px;
    color: var(--color-text-light);
}
.vm-card-status {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
}
.vm-card .slave-metrics {
    border-top: 1px solid var(--color-border);
    padding-top: 8px;
    margin-top: 4px;
}
```

**Step 4: Add small badge variant**

```css
.badge-sm {
    font-size: 10px;
    padding: 1px 5px;
    background: var(--color-border);
    color: var(--color-text-light);
}
```

**Step 5: Mobile overrides**

Add to the existing `@media (max-width: 768px)` block:

```css
.slave-row-details { padding: 0 12px 8px; }
.slave-metrics { gap: 8px; }
.slave-metrics .monitor-bar { width: 60px; min-width: 60px; }
.fleet-summary-bar { flex-wrap: wrap; font-size: 12px; }
```

**Step 6: Commit**

```bash
git add jmeter-working-dir/webapp/static/css/style.css
git commit -m "style(fleet): CSS for two-row cards, inline metrics, and summary bar"
```

---

### Task 8: Run Tests and Verify

**Files:** None (verification only)

**Step 1: Run backend tests**

```bash
cd jmeter-working-dir/webapp && python -m pytest tests/ -v --tb=short
```

Expected: All tests pass (no backend changes to routers/services).

**Step 2: Start webapp and verify in browser**

```bash
cd jmeter-working-dir/webapp && python __main__.py
```

Open http://localhost:8080/fleet and verify:
- [ ] List view: two-row cards with IP/controls on row 1, status/badges on row 2
- [ ] Grid view: cards show status row + metrics row when monitoring active
- [ ] Enable monitoring: inline CPU/RAM/JVM bars appear in each slave card
- [ ] Summary bar shows at bottom with averages + countdown
- [ ] Sparklines appear after 2+ polling cycles
- [ ] Dark mode: all new elements styled correctly
- [ ] Mobile (375px): metrics wrap, summary bar wraps
- [ ] Disable monitoring: metrics disappear, just status/provision badges remain
- [ ] Settings page tabs still work (backward compatibility)

**Step 3: Final commit if any adjustments needed**

```bash
git add -A
git commit -m "fix(fleet): post-verification adjustments"
```

---

## Summary of Changes

| File | Action | Purpose |
|------|--------|---------|
| `utils/metrics_agent.py` | Modify | Add disk, load, network, thread metrics |
| `static/js/fleet-core.js` | Modify | Add metricsHistory, sparkline SVG, inlineMetrics helper |
| `static/js/fleet-slaves.js` | Modify | Redesign renderList/Grid, summary bar, record history |
| `templates/_fleet_slaves.html` | Modify | Replace monitoring panel div with summary bar |
| `static/css/style.css` | Modify | Two-row card styles, inline metrics, summary bar |
