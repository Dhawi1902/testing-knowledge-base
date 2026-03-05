# Fleet Monitoring Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the tiny inline sparklines and summary bar with a real monitoring dashboard featuring canvas time-series charts, a fleet heatmap, and per-slave drill-down panels.

**Architecture:** A new `fleet-charts.js` file provides a lightweight canvas chart engine (`FleetChart` class). When monitoring is ON, a dashboard section renders above the slave list with a heatmap, fleet averages, and 4 overlay charts (CPU, RAM, Network, JVM). Each slave card gains a clickable metrics row that expands into a per-slave drill-down with dedicated charts. All data stays in-memory via `Fleet.chartData`.

**Tech Stack:** Vanilla JS + HTML5 Canvas (no external libraries), existing FastAPI polling endpoint, CSS grid for dashboard layout.

**Design doc:** `docs/plans/2026-03-03-fleet-monitoring-dashboard-design.md`

---

### Task 1: Canvas Chart Engine — FleetChart Class

**Files:**
- Create: `webapp/static/js/fleet-charts.js`

The core rendering engine. A `FleetChart` class that draws time-series line charts on `<canvas>` with:
- Multiple overlaid series (one per slave, different colors)
- Auto-scaling Y axis
- Time axis with HH:MM labels
- Hover crosshair with tooltip showing exact values
- Smooth animated entry of new points
- 5-minute rolling window
- Dark mode support via CSS variable detection

```js
/* Fleet Charts — Lightweight canvas time-series for fleet monitoring */

const CHART_COLORS = [
    '#3b82f6', '#22c55e', '#f59e0b', '#ef4444',
    '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'
];

class FleetChart {
    constructor(canvas, options) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.opts = Object.assign({
            title: '',
            yMin: 0,
            yMax: null,       // null = auto-scale
            yLabel: '%',
            yFixed: 0,        // decimal places
            windowMs: 5 * 60 * 1000, // 5 min rolling window
            gridLines: 4,
            showLegend: true,
        }, options);
        this.series = {};     // { seriesId: { label, colorIdx, points: [{t, v}] } }
        this.hoverX = null;
        this.hoverY = null;
        this._raf = null;
        this._dirty = true;
        this._setupInteraction();
        this._startLoop();
    }

    addSeries(id, label) {
        if (this.series[id]) return;
        const idx = Object.keys(this.series).length % CHART_COLORS.length;
        this.series[id] = { label, colorIdx: idx, points: [] };
    }

    addPoint(seriesId, timestamp, value) {
        if (!this.series[seriesId]) return;
        this.series[seriesId].points.push({ t: timestamp, v: value });
        this._trimPoints(seriesId);
        this._dirty = true;
    }

    _trimPoints(seriesId) {
        const pts = this.series[seriesId].points;
        const cutoff = Date.now() - this.opts.windowMs - 30000; // 30s grace
        while (pts.length > 0 && pts[0].t < cutoff) pts.shift();
    }

    _setupInteraction() {
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            this.hoverX = e.clientX - rect.left;
            this.hoverY = e.clientY - rect.top;
            this._dirty = true;
        });
        this.canvas.addEventListener('mouseleave', () => {
            this.hoverX = null;
            this.hoverY = null;
            this._dirty = true;
        });
    }

    _startLoop() {
        const loop = () => {
            if (this._dirty) {
                this._render();
                this._dirty = false;
            }
            this._raf = requestAnimationFrame(loop);
        };
        this._raf = requestAnimationFrame(loop);
    }

    _getYBounds() {
        if (this.opts.yMax != null) return { min: this.opts.yMin, max: this.opts.yMax };
        let max = 10;
        for (const s of Object.values(this.series)) {
            for (const p of s.points) {
                if (p.v > max) max = p.v;
            }
        }
        // Round up to nice number
        max = Math.ceil(max * 1.15);
        if (max <= 100 && this.opts.yLabel === '%') max = 100;
        return { min: this.opts.yMin, max };
    }

    _render() {
        const c = this.canvas;
        const ctx = this.ctx;
        const dpr = window.devicePixelRatio || 1;
        const w = c.clientWidth;
        const h = c.clientHeight;
        c.width = w * dpr;
        c.height = h * dpr;
        ctx.scale(dpr, dpr);

        // Colors from CSS vars or fallback
        const style = getComputedStyle(document.documentElement);
        const textColor = style.getPropertyValue('--color-text-secondary').trim() || '#94a3b8';
        const gridColor = style.getPropertyValue('--color-border').trim() || '#e2e8f0';
        const bgColor = style.getPropertyValue('--color-surface').trim() || '#ffffff';

        // Layout
        const pad = { top: 24, right: 12, bottom: 28, left: 44 };
        const plotW = w - pad.left - pad.right;
        const plotH = h - pad.top - pad.bottom;

        // Clear
        ctx.fillStyle = bgColor;
        ctx.fillRect(0, 0, w, h);

        // Title
        ctx.fillStyle = textColor;
        ctx.font = '600 11px system-ui, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(this.opts.title, pad.left, 14);

        // Y axis
        const yBounds = this._getYBounds();
        ctx.font = '10px system-ui, sans-serif';
        ctx.textAlign = 'right';
        ctx.strokeStyle = gridColor;
        ctx.lineWidth = 0.5;
        for (let i = 0; i <= this.opts.gridLines; i++) {
            const frac = i / this.opts.gridLines;
            const y = pad.top + plotH - frac * plotH;
            const val = yBounds.min + frac * (yBounds.max - yBounds.min);
            // Grid line
            ctx.beginPath();
            ctx.moveTo(pad.left, y);
            ctx.lineTo(pad.left + plotW, y);
            ctx.stroke();
            // Label
            ctx.fillStyle = textColor;
            ctx.fillText(val.toFixed(this.opts.yFixed) + (i === this.opts.gridLines ? this.opts.yLabel : ''), pad.left - 4, y + 3);
        }

        // Time bounds
        const now = Date.now();
        const tMin = now - this.opts.windowMs;
        const tMax = now;

        // Time axis labels
        ctx.textAlign = 'center';
        ctx.fillStyle = textColor;
        const timeSteps = 5;
        for (let i = 0; i <= timeSteps; i++) {
            const frac = i / timeSteps;
            const x = pad.left + frac * plotW;
            const t = tMin + frac * (tMax - tMin);
            const d = new Date(t);
            const lbl = d.getMinutes().toString().padStart(2, '0') + ':' + d.getSeconds().toString().padStart(2, '0');
            ctx.fillText(lbl, x, h - 6);
        }

        // Plot each series
        const toX = t => pad.left + ((t - tMin) / (tMax - tMin)) * plotW;
        const toY = v => pad.top + plotH - ((v - yBounds.min) / (yBounds.max - yBounds.min)) * plotH;

        const seriesIds = Object.keys(this.series);
        for (const id of seriesIds) {
            const s = this.series[id];
            const pts = s.points.filter(p => p.t >= tMin);
            if (pts.length < 2) continue;
            ctx.strokeStyle = CHART_COLORS[s.colorIdx];
            ctx.lineWidth = 1.8;
            ctx.lineJoin = 'round';
            ctx.lineCap = 'round';
            ctx.beginPath();
            ctx.moveTo(toX(pts[0].t), toY(pts[0].v));
            for (let i = 1; i < pts.length; i++) {
                ctx.lineTo(toX(pts[i].t), toY(pts[i].v));
            }
            ctx.stroke();
        }

        // Hover crosshair + tooltip
        if (this.hoverX != null && this.hoverX >= pad.left && this.hoverX <= pad.left + plotW) {
            // Vertical crosshair
            ctx.strokeStyle = textColor;
            ctx.lineWidth = 0.5;
            ctx.setLineDash([3, 3]);
            ctx.beginPath();
            ctx.moveTo(this.hoverX, pad.top);
            ctx.lineTo(this.hoverX, pad.top + plotH);
            ctx.stroke();
            ctx.setLineDash([]);

            // Find closest time
            const hoverT = tMin + ((this.hoverX - pad.left) / plotW) * (tMax - tMin);

            // Tooltip
            let tooltipLines = [];
            const hoverDate = new Date(hoverT);
            tooltipLines.push(hoverDate.getHours().toString().padStart(2, '0') + ':' +
                hoverDate.getMinutes().toString().padStart(2, '0') + ':' +
                hoverDate.getSeconds().toString().padStart(2, '0'));

            for (const id of seriesIds) {
                const s = this.series[id];
                const pts = s.points;
                let closest = null, minDist = Infinity;
                for (const p of pts) {
                    const d = Math.abs(p.t - hoverT);
                    if (d < minDist) { minDist = d; closest = p; }
                }
                if (closest && minDist < 30000) {
                    tooltipLines.push(`${s.label}: ${closest.v.toFixed(this.opts.yFixed)}${this.opts.yLabel}`);
                    // Draw dot at closest point
                    ctx.fillStyle = CHART_COLORS[s.colorIdx];
                    ctx.beginPath();
                    ctx.arc(toX(closest.t), toY(closest.v), 3, 0, Math.PI * 2);
                    ctx.fill();
                }
            }

            if (tooltipLines.length > 1) {
                this._drawTooltip(ctx, this.hoverX, this.hoverY, tooltipLines, textColor, bgColor, w);
            }
        }

        // Legend
        if (this.opts.showLegend && seriesIds.length > 1) {
            ctx.font = '10px system-ui, sans-serif';
            ctx.textAlign = 'left';
            let lx = pad.left + plotW - seriesIds.length * 80;
            for (const id of seriesIds) {
                const s = this.series[id];
                ctx.fillStyle = CHART_COLORS[s.colorIdx];
                ctx.fillRect(lx, 6, 8, 8);
                ctx.fillStyle = textColor;
                ctx.fillText(s.label, lx + 11, 14);
                lx += Math.max(ctx.measureText(s.label).width + 20, 60);
            }
        }
    }

    _drawTooltip(ctx, mx, my, lines, textColor, bgColor, canvasW) {
        ctx.font = '10px system-ui, sans-serif';
        const lineH = 14;
        const padX = 8, padY = 6;
        const maxW = Math.max(...lines.map(l => ctx.measureText(l).width));
        const tipW = maxW + padX * 2;
        const tipH = lines.length * lineH + padY * 2;
        let tx = mx + 10;
        let ty = my - tipH / 2;
        if (tx + tipW > canvasW) tx = mx - tipW - 10;
        if (ty < 0) ty = 0;

        ctx.fillStyle = bgColor;
        ctx.strokeStyle = textColor;
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.roundRect(tx, ty, tipW, tipH, 4);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = textColor;
        ctx.textAlign = 'left';
        lines.forEach((line, i) => {
            ctx.font = i === 0 ? 'bold 10px system-ui, sans-serif' : '10px system-ui, sans-serif';
            ctx.fillText(line, tx + padX, ty + padY + (i + 1) * lineH - 3);
        });
    }

    resize() {
        this._dirty = true;
    }

    destroy() {
        if (this._raf) cancelAnimationFrame(this._raf);
        this._raf = null;
    }
}

// ===== Dashboard Manager =====
// Manages the 4 fleet-wide charts + per-slave drill-down charts

const FleetDashboard = {
    charts: {},          // { cpu: FleetChart, ram: FleetChart, net: FleetChart, jvm: FleetChart }
    drillCharts: {},     // { 'ip_cpu': FleetChart, 'ip_ram': FleetChart, ... }
    expandedDrill: null, // IP of expanded drill-down, or null
    _resizeHandler: null,

    init() {
        const cpuCanvas = document.getElementById('dashCpuChart');
        const ramCanvas = document.getElementById('dashRamChart');
        const netCanvas = document.getElementById('dashNetChart');
        const jvmCanvas = document.getElementById('dashJvmChart');
        if (!cpuCanvas) return;

        this.charts.cpu = new FleetChart(cpuCanvas, {
            title: 'CPU Usage', yMax: 100, yLabel: '%', yFixed: 0
        });
        this.charts.ram = new FleetChart(ramCanvas, {
            title: 'RAM Usage', yMax: 100, yLabel: '%', yFixed: 0
        });
        this.charts.net = new FleetChart(netCanvas, {
            title: 'Network Throughput', yMax: null, yLabel: ' KB/s', yFixed: 0
        });
        this.charts.jvm = new FleetChart(jvmCanvas, {
            title: 'JVM RSS Memory', yMax: null, yLabel: ' MB', yFixed: 0
        });

        // Ensure series exist for all slaves
        Fleet.slaveData.forEach(s => this._ensureSeries(s.ip));

        // Resize handler
        this._resizeHandler = () => Object.values(this.charts).forEach(c => c.resize());
        window.addEventListener('resize', this._resizeHandler);
    },

    _ensureSeries(ip) {
        const label = _slaveLabel(ip);
        for (const [key, chart] of Object.entries(this.charts)) {
            chart.addSeries(ip, label);
        }
    },

    pushMetrics(ip, data) {
        this._ensureSeries(ip);
        const now = Date.now();
        if (data.cpu_percent != null)
            this.charts.cpu.addPoint(ip, now, data.cpu_percent);
        if (data.ram_percent != null)
            this.charts.ram.addPoint(ip, now, data.ram_percent);
        if (data.jvm_rss_mb != null)
            this.charts.jvm.addPoint(ip, now, data.jvm_rss_mb);

        // Network throughput (delta from previous sample)
        const netRx = data.net_rx_bytes;
        const netTx = data.net_tx_bytes;
        if (netRx != null && netTx != null) {
            if (!Fleet._prevNetBytes) Fleet._prevNetBytes = {};
            const prev = Fleet._prevNetBytes[ip];
            if (prev) {
                const dtSec = (now - prev.ts) / 1000;
                if (dtSec > 0) {
                    const rxKBs = Math.max(0, (netRx - prev.rx) / 1024 / dtSec);
                    const txKBs = Math.max(0, (netTx - prev.tx) / 1024 / dtSec);
                    this.charts.net.addPoint(ip, now, rxKBs + txKBs); // combined throughput
                }
            }
            Fleet._prevNetBytes[ip] = { rx: netRx, tx: netTx, ts: now };
        }

        // Update drill-down if expanded for this IP
        if (this.expandedDrill === ip) {
            this._pushDrillMetrics(ip, data, now);
        }
    },

    _pushDrillMetrics(ip, data, now) {
        const prefix = ip + '_';
        if (this.drillCharts[prefix + 'cpu'] && data.cpu_percent != null)
            this.drillCharts[prefix + 'cpu'].addPoint(ip, now, data.cpu_percent);
        if (this.drillCharts[prefix + 'ram'] && data.ram_percent != null)
            this.drillCharts[prefix + 'ram'].addPoint(ip, now, data.ram_percent);
    },

    initDrillDown(ip) {
        // Destroy previous drill-down charts
        this.destroyDrillDown();
        this.expandedDrill = ip;

        const cpuCanvas = document.getElementById('drillCpuChart_' + CSS.escape(ip));
        const ramCanvas = document.getElementById('drillRamChart_' + CSS.escape(ip));
        if (!cpuCanvas || !ramCanvas) return;

        const label = _slaveLabel(ip);
        this.drillCharts[ip + '_cpu'] = new FleetChart(cpuCanvas, {
            title: 'CPU — ' + label, yMax: 100, yLabel: '%', showLegend: false
        });
        this.drillCharts[ip + '_ram'] = new FleetChart(ramCanvas, {
            title: 'RAM — ' + label, yMax: 100, yLabel: '%', showLegend: false
        });
        this.drillCharts[ip + '_cpu'].addSeries(ip, label);
        this.drillCharts[ip + '_ram'].addSeries(ip, label);

        // Backfill from chart data
        const cpuPts = this.charts.cpu.series[ip]?.points || [];
        const ramPts = this.charts.ram.series[ip]?.points || [];
        cpuPts.forEach(p => this.drillCharts[ip + '_cpu'].addPoint(ip, p.t, p.v));
        ramPts.forEach(p => this.drillCharts[ip + '_ram'].addPoint(ip, p.t, p.v));
    },

    destroyDrillDown() {
        for (const c of Object.values(this.drillCharts)) c.destroy();
        this.drillCharts = {};
        this.expandedDrill = null;
    },

    show() {
        const el = document.getElementById('fleetDashboard');
        if (el) el.style.display = '';
        if (!this.charts.cpu) this.init();
    },

    hide() {
        const el = document.getElementById('fleetDashboard');
        if (el) el.style.display = 'none';
    },

    destroy() {
        for (const c of Object.values(this.charts)) c.destroy();
        this.charts = {};
        this.destroyDrillDown();
        if (this._resizeHandler) window.removeEventListener('resize', this._resizeHandler);
    }
};

function _slaveLabel(ip) {
    const s = Fleet.slaveData.find(sl => sl.ip === ip);
    return s && s.nickname ? s.nickname : ip;
}
```

**Commit:** `feat(fleet): add canvas chart engine for fleet monitoring dashboard`

---

### Task 2: Fleet State Extensions

**Files:**
- Modify: `webapp/static/js/fleet-core.js`

Add new state fields and update `recordMetrics()` to feed chart data. Remove old `miniSparkline()` and `inlineMetrics()` (replaced by dashboard). Keep `progressBar()` — still used in drill-down.

**Changes to `window.Fleet` object** — add after `_countdownTimer: null`:
```js
    chartData: {},         // { ip: [{ts, cpu, ram, disk, net_rx, net_tx, jvm_rss, load, threads}] }
    _prevNetBytes: {},     // { ip: {rx, tx, ts} } for throughput delta
    drillDownIp: null,     // IP of expanded drill-down, or null
```

**Update `recordMetrics()`** — extend to store all metrics + push to FleetDashboard:
```js
function recordMetrics(ip, metrics) {
    // Store in chartData (5-min rolling window)
    if (!Fleet.chartData[ip]) Fleet.chartData[ip] = [];
    const arr = Fleet.chartData[ip];
    arr.push({ ts: Date.now(), ...metrics });
    const cutoff = Date.now() - 5 * 60 * 1000;
    while (arr.length > 0 && arr[0].ts < cutoff) arr.shift();

    // Push to dashboard charts if initialized
    if (typeof FleetDashboard !== 'undefined' && FleetDashboard.charts.cpu) {
        FleetDashboard.pushMetrics(ip, metrics);
    }
}
```

**Remove these functions entirely** (no longer needed):
- `miniSparkline()`
- `inlineMetrics()`

**Keep**: `progressBar()`, `recordMetrics()` (now updated)

**Commit:** `feat(fleet): extend Fleet state for chart data and network deltas`

---

### Task 3: Dashboard HTML + Script Tag

**Files:**
- Modify: `webapp/templates/_fleet_slaves.html`
- Modify: `webapp/templates/slaves.html`

**In `_fleet_slaves.html`** — replace the `<!-- Fleet Summary Bar -->` block with the full dashboard section:

```html
<!-- Fleet Dashboard -->
<div class="fleet-dashboard" id="fleetDashboard" style="display:none;">
    <div class="dash-header">
        <div class="dash-heatmap" id="dashHeatmap"></div>
        <div class="dash-averages" id="dashAverages"></div>
        <div class="dash-live">
            <span class="live-indicator" id="liveIndicator"></span>
            <span class="text-xs text-light" id="monitorIntervalLabel"></span>
            <span class="text-xs text-light" id="nextPollLabel"></span>
        </div>
    </div>
    <div class="dash-charts">
        <div class="dash-chart-wrap">
            <canvas id="dashCpuChart"></canvas>
        </div>
        <div class="dash-chart-wrap">
            <canvas id="dashRamChart"></canvas>
        </div>
        <div class="dash-chart-wrap">
            <canvas id="dashNetChart"></canvas>
        </div>
        <div class="dash-chart-wrap">
            <canvas id="dashJvmChart"></canvas>
        </div>
    </div>
</div>
```

**In `slaves.html`** — add fleet-charts.js script tag before fleet-slaves.js:
```html
<script src="{{ bp }}/static/js/fleet-charts.js?v={{ asset_v }}"></script>
```

**Commit:** `feat(fleet): add dashboard HTML section and chart canvas elements`

---

### Task 4: Dashboard Rendering + Heatmap + Averages

**Files:**
- Modify: `webapp/static/js/fleet-slaves.js`

**Replace `renderMonitoringPanel()`** with `renderDashboard()`:

```js
function renderDashboard() {
    const dashboard = document.getElementById('fleetDashboard');
    if (!dashboard) return;

    const hasData = Object.keys(Fleet.resourceData).length > 0;
    if (!Fleet._metricsTimer || !hasData) {
        FleetDashboard.hide();
        return;
    }
    FleetDashboard.show();

    // Heatmap
    renderHeatmap();

    // Fleet averages
    renderDashAverages();

    // Interval + countdown labels (same logic as before)
    const intervalLabel = document.getElementById('monitorIntervalLabel');
    if (intervalLabel) {
        const secs = Fleet._metricsInterval / 1000;
        intervalLabel.textContent = secs >= 60 ? `every ${secs/60}m` : `every ${secs}s`;
    }
    const nextEl = document.getElementById('nextPollLabel');
    if (nextEl && Fleet._lastPollTs) {
        const elapsed = Date.now() - Fleet._lastPollTs;
        const remaining = Math.max(0, Math.round((Fleet._metricsInterval - elapsed) / 1000));
        nextEl.textContent = `next: ${remaining}s`;
    }
}

function renderHeatmap() {
    const el = document.getElementById('dashHeatmap');
    if (!el) return;
    let html = '';
    Fleet.slaveData.forEach((s, i) => {
        if (s.enabled === false) return;
        const r = Fleet.resourceData[s.ip];
        const cpu = r ? r.cpu_percent : null;
        let color;
        if (cpu == null) color = 'var(--color-border)';
        else if (cpu > 80) color = '#ef4444';
        else if (cpu > 50) color = '#f59e0b';
        else color = '#22c55e';
        const label = s.nickname || s.ip;
        const title = cpu != null ? `${label}: CPU ${cpu}%` : `${label}: no data`;
        html += `<span class="heatmap-cell" style="background:${color}" title="${title}" onclick="scrollToSlave('${escAttr(s.ip)}')" data-ip="${escAttr(s.ip)}"></span>`;
    });
    el.innerHTML = html;
}

function renderDashAverages() {
    const el = document.getElementById('dashAverages');
    if (!el) return;
    let cpuSum = 0, ramSum = 0, diskSum = 0, loadSum = 0, netSum = 0;
    let count = 0, jmeterUp = 0, totalEnabled = 0;

    Fleet.slaveData.forEach(s => {
        if (s.enabled === false) return;
        totalEnabled++;
        const r = Fleet.resourceData[s.ip];
        if (!r) return;
        if (r.cpu_percent != null) { cpuSum += r.cpu_percent; count++; }
        if (r.ram_percent != null) { ramSum += r.ram_percent; }
        if (r.disk_percent != null) { diskSum += r.disk_percent; }
        if (r.load_1m != null) { loadSum += r.load_1m; }
        if (r.jmeter_running) jmeterUp++;
        // Network throughput
        const prev = Fleet._prevNetBytes?.[s.ip];
        if (prev && prev.kbps != null) netSum += prev.kbps;
    });

    if (count === 0) { el.innerHTML = '<span class="text-light">Waiting for data...</span>'; return; }

    const avgCpu = Math.round(cpuSum / count);
    const avgRam = Math.round(ramSum / count);
    const avgDisk = Math.round(diskSum / count);
    const avgLoad = (loadSum / count).toFixed(2);

    el.innerHTML = `<span>CPU: <strong>${avgCpu}%</strong></span>` +
        `<span>RAM: <strong>${avgRam}%</strong></span>` +
        `<span>Disk: <strong>${avgDisk}%</strong></span>` +
        `<span>Load: <strong>${avgLoad}</strong></span>` +
        `<span>JMeter: <strong>${jmeterUp}/${totalEnabled}</strong> up</span>`;
}

function scrollToSlave(ip) {
    const entry = document.querySelector(`.slave-entry [onclick*="${ip}"], .vm-card [onclick*="${ip}"]`);
    if (!entry) return;
    const card = entry.closest('.slave-entry') || entry.closest('.vm-card');
    if (card) {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        card.classList.add('flash-highlight');
        setTimeout(() => card.classList.remove('flash-highlight'), 1500);
    }
}
```

**Update `_applyMetricsResults()`** — change `recordMetrics()` call to pass full metrics object:
```js
// Replace the old recordMetrics call:
//   recordMetrics(r.ip, r.cpu_percent, r.ram_percent);
// With:
recordMetrics(r.ip, {
    cpu_percent: r.cpu_percent,
    ram_percent: r.ram_percent,
    ram_used_mb: r.ram_used_mb,
    ram_total_mb: r.ram_total_mb,
    jvm_rss_mb: r.jvm_rss_mb || null,
    disk_percent: r.disk_percent || null,
    load_1m: r.load_1m || null,
    net_rx_bytes: r.net_rx_bytes || null,
    net_tx_bytes: r.net_tx_bytes || null,
    jvm_threads: r.jvm_threads || null,
});
```

**Update all references**: Replace `renderMonitoringPanel()` with `renderDashboard()` everywhere:
- In `render()` function
- In `startMetricsPolling()` — countdown timer calls `renderDashboard`
- In `stopMetricsPolling()`
- In `toggleMonitoring()`
- In `onIntervalChange()`

**Commit:** `feat(fleet): render dashboard with heatmap, averages, and chart integration`

---

### Task 5: Per-Slave Drill-Down

**Files:**
- Modify: `webapp/static/js/fleet-slaves.js`

**Add drill-down toggle + renderer:**

```js
function toggleDrillDown(ip) {
    if (Fleet.drillDownIp === ip) {
        Fleet.drillDownIp = null;
        FleetDashboard.destroyDrillDown();
    } else {
        Fleet.drillDownIp = ip;
    }
    render();
    // Init charts after DOM is updated
    if (Fleet.drillDownIp) {
        setTimeout(() => FleetDashboard.initDrillDown(ip), 50);
    }
}

function renderDrillDown(ip) {
    const r = Fleet.resourceData[ip];
    if (!r) return '';
    const aIp = escAttr(ip);
    const diskInfo = r.disk_percent != null
        ? `<div class="drill-stat">Disk: ${r.disk_used_gb}/${r.disk_total_gb} GB ${progressBar(r.disk_percent, {warn:80,danger:90})}</div>`
        : '';
    const loadInfo = r.load_1m != null ? `<div class="drill-stat">Load: <strong>${r.load_1m}</strong></div>` : '';
    const jvmInfo = r.jvm_rss_mb != null
        ? `<div class="drill-stat">JVM: <strong>${r.jvm_rss_mb} MB</strong> RSS${r.jvm_threads != null ? ` | ${r.jvm_threads} threads` : ''}</div>`
        : '';
    const netPrev = Fleet._prevNetBytes?.[ip];
    let netInfo = '';
    if (netPrev && netPrev.kbps != null) {
        const val = netPrev.kbps > 1024 ? (netPrev.kbps / 1024).toFixed(1) + ' MB/s' : Math.round(netPrev.kbps) + ' KB/s';
        netInfo = `<div class="drill-stat">Net: <strong>${val}</strong></div>`;
    }

    return `<div class="drill-down-panel">
        <div class="drill-charts">
            <div class="drill-chart-wrap"><canvas id="drillCpuChart_${aIp}"></canvas></div>
            <div class="drill-chart-wrap"><canvas id="drillRamChart_${aIp}"></canvas></div>
        </div>
        <div class="drill-stats">
            ${diskInfo}${loadInfo}${jvmInfo}${netInfo}
        </div>
    </div>`;
}
```

**Modify `renderList()`** — update the `.slave-row-details` section. Replace old inline metrics with clickable metrics summary + drill-down:

```js
// In the slave-row-details div, replace the old hasMetrics logic with:
const hasMetrics = Fleet.resourceData[s.ip] && Fleet.resourceData[s.ip].cpu_percent != null;
const isDrillOpen = Fleet.drillDownIp === s.ip;

// Row 2 content:
`<div class="slave-row-details">
    <div class="slave-status-row">
        ${statusBadge(s)}${provisionBadges(s)}
        ${hasMetrics ? `<span class="metrics-summary" onclick="toggleDrillDown('${aIp}')">
            CPU <strong>${Fleet.resourceData[s.ip].cpu_percent}%</strong>
            RAM <strong>${Fleet.resourceData[s.ip].ram_percent}%</strong>
            ${Fleet.resourceData[s.ip].jvm_rss_mb != null ? `JVM <strong>${Fleet.resourceData[s.ip].jvm_rss_mb}MB</strong>` : ''}
            <span class="drill-arrow ${isDrillOpen ? 'open' : ''}">\u25BC</span>
        </span>` : ''}
        ${s.error ? `<span class="text-sm text-danger">${escHtml(s.error)}</span>` : ''}
    </div>
    ${isDrillOpen ? renderDrillDown(s.ip) : ''}
</div>`
```

**Apply same pattern to `renderGrid()`** — add clickable metrics summary and drill-down to grid cards.

**Commit:** `feat(fleet): add per-slave drill-down with canvas charts and detailed metrics`

---

### Task 6: Network Throughput Delta Storage

**Files:**
- Modify: `webapp/static/js/fleet-charts.js`

Update `FleetDashboard.pushMetrics()` to store computed throughput back into `Fleet._prevNetBytes` for display in drill-down and averages:

```js
// After computing rxKBs and txKBs in pushMetrics():
Fleet._prevNetBytes[ip].kbps = rxKBs + txKBs;
```

This makes `kbps` available to `renderDashAverages()` and `renderDrillDown()`.

**Commit:** `feat(fleet): store computed network throughput for dashboard display`

---

### Task 7: Dashboard CSS

**Files:**
- Modify: `webapp/static/css/style.css`

```css
/* ===== Fleet Dashboard ===== */
.fleet-dashboard {
    padding: 12px 16px;
    border-bottom: 1px solid var(--color-border);
}
.dash-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 12px;
    flex-wrap: wrap;
}
.dash-heatmap {
    display: flex;
    gap: 3px;
    align-items: center;
}
.heatmap-cell {
    width: 20px;
    height: 20px;
    border-radius: 3px;
    cursor: pointer;
    transition: transform 0.15s, box-shadow 0.15s;
}
.heatmap-cell:hover {
    transform: scale(1.3);
    box-shadow: 0 0 6px rgba(0,0,0,0.3);
    z-index: 1;
}
.dash-averages {
    display: flex;
    gap: 12px;
    font-size: 12px;
    flex-wrap: wrap;
}
.dash-averages span { white-space: nowrap; }
.dash-live {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
}
.dash-charts {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}
.dash-chart-wrap {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    overflow: hidden;
    position: relative;
}
.dash-chart-wrap canvas {
    width: 100%;
    height: 160px;
    display: block;
}

/* Metrics summary in slave row */
.metrics-summary {
    cursor: pointer;
    font-size: 12px;
    color: var(--color-text-secondary);
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: 8px;
    transition: background 0.15s;
}
.metrics-summary:hover {
    background: var(--color-bg-alt, color-mix(in srgb, var(--color-border) 30%, var(--color-surface)));
}
.metrics-summary strong {
    color: var(--color-text);
}
.drill-arrow {
    font-size: 8px;
    transition: transform 0.2s;
    display: inline-block;
}
.drill-arrow.open {
    transform: rotate(180deg);
}

/* Drill-down panel */
.drill-down-panel {
    padding: 8px 0;
    border-top: 1px solid var(--color-border);
    margin-top: 4px;
}
.drill-charts {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 8px;
}
.drill-chart-wrap {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    overflow: hidden;
}
.drill-chart-wrap canvas {
    width: 100%;
    height: 120px;
    display: block;
}
.drill-stats {
    display: flex;
    gap: 16px;
    font-size: 12px;
    flex-wrap: wrap;
}
.drill-stat {
    display: flex;
    align-items: center;
    gap: 4px;
}
.drill-stat .monitor-bar {
    width: 80px;
    min-width: 80px;
    height: 14px;
}

/* Heatmap scroll-to flash */
@keyframes flashHighlight {
    0% { box-shadow: 0 0 0 3px var(--color-primary); }
    100% { box-shadow: 0 0 0 0 transparent; }
}
.flash-highlight {
    animation: flashHighlight 1.5s ease-out;
}

/* Mobile overrides */
@media (max-width: 768px) {
    .dash-charts { grid-template-columns: 1fr; }
    .dash-chart-wrap canvas { height: 120px; }
    .drill-charts { grid-template-columns: 1fr; }
    .dash-header { gap: 8px; }
    .heatmap-cell { width: 16px; height: 16px; }
}
```

**Commit:** `style(fleet): add dashboard, heatmap, chart, and drill-down CSS`

---

### Task 8: Integration + Cleanup

**Files:**
- Modify: `webapp/static/js/fleet-slaves.js`
- Modify: `webapp/static/js/fleet-core.js`
- Modify: `webapp/templates/slaves.html`

**Wire up monitoring restore** in `slaves.html` init script — add after monitoring restore:
```js
// Init dashboard if monitoring was already on
if (localStorage.getItem('fleet_monitoring') === 'on') {
    // ... existing monitoring restore code ...
    FleetDashboard.init();
}
```

**Clean up old code:**
- Remove `metricsHistory` from Fleet state (replaced by `chartData`)
- Remove `miniSparkline()` from fleet-core.js (already done in Task 2)
- Remove `inlineMetrics()` from fleet-core.js (already done in Task 2)
- Remove old `.fleet-summary-bar` and `.slave-metrics .monitor-bar` CSS rules
- Remove `#monitoringSummary` from _fleet_slaves.html (replaced by dashboard)

**Update `stopMetricsPolling()`** to also hide dashboard:
```js
function stopMetricsPolling() {
    // ... existing timer cleanup ...
    FleetDashboard.hide();
    FleetDashboard.destroyDrillDown();
    Fleet.drillDownIp = null;
}
```

**Verify:**
- Run: `cd jmeter-working-dir/webapp && python -m pytest tests/ -v --tb=short` — all tests pass
- Run: `node -c static/js/fleet-charts.js && node -c static/js/fleet-core.js && node -c static/js/fleet-slaves.js` — no syntax errors
- Manual: Load `/fleet`, toggle monitoring ON → dashboard with 4 charts appears
- Manual: Click heatmap cell → scrolls to slave with flash
- Manual: Click metrics in slave row → drill-down panel expands with 2 charts
- Manual: Dark mode → charts read CSS variables, render correctly

**Commit:** `feat(fleet): integrate monitoring dashboard, clean up old inline metrics`

---

## Files Summary

| File | Action | Content |
|------|--------|---------|
| `webapp/static/js/fleet-charts.js` | Create | FleetChart class + FleetDashboard manager (~280 lines) |
| `webapp/static/js/fleet-core.js` | Modify | Add chartData/_prevNetBytes state, update recordMetrics(), remove miniSparkline/inlineMetrics |
| `webapp/static/js/fleet-slaves.js` | Modify | Replace renderMonitoringPanel→renderDashboard, add heatmap/averages/drillDown, update slave rows |
| `webapp/templates/_fleet_slaves.html` | Modify | Replace summary bar with dashboard HTML section |
| `webapp/templates/slaves.html` | Modify | Add fleet-charts.js script tag, dashboard init |
| `webapp/static/css/style.css` | Modify | Dashboard grid, heatmap, chart, drill-down, flash animation styles |

## Backend: No Changes

Zero Python changes. All visualization is client-side using existing `/api/slaves/metrics` endpoint.
