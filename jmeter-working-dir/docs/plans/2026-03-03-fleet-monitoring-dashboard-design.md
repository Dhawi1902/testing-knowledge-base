# Fleet Monitoring Dashboard — Live Canvas Charts + Heatmap

**Date**: 2026-03-03
**Status**: Approved
**Scope**: Replace summary bar + inline sparklines with a real monitoring dashboard

## Problem

Current monitoring is underwhelming:
- Tiny 60x16px SVG sparklines — can't read actual trends
- Summary bar shows just averages — no per-slave detail
- Inline metrics crammed into slave card row 2 — cluttered
- No historical visibility — sparklines only hold 20 points, no time axis
- No way to spot which slave is struggling at a glance
- Network I/O shows raw cumulative bytes — useless without delta/throughput

## Design

### 1. Dashboard Section (replaces summary bar)

When monitoring is ON, a full dashboard section appears between the toolbar and slave list:

```
┌─ Fleet Dashboard ─────────────────── Live ● every 30s ─┐
│                                                          │
│  Heatmap        Fleet Averages                           │
│  [■][■][■][■]   CPU: 52%  RAM: 71%  JMeter: 2/4 up     │
│                  Disk: 45%  Load: 1.8  Net: 3.4 MB/s    │
│                                                          │
│  ┌─ CPU ──────────────────── ┐ ┌─ RAM ────────────────┐ │
│  │  100% ┤                   │ │  100% ┤               │ │
│  │       │    ╱╲  ╱╲         │ │       │ ──────────    │ │
│  │   50% ┤ ──╱  ╲╱  ╲──     │ │   50% ┤              │ │
│  │       │               ╲   │ │       │              │ │
│  │    0% ┤                   │ │    0% ┤              │ │
│  │       └──────────────── t │ │       └──────────── t│ │
│  └───────────────────────────┘ └──────────────────────┘ │
│                                                          │
│  ┌─ Network I/O ─────────── ┐ ┌─ JVM Memory ─────────┐ │
│  │  ↑ TX  ↓ RX  (MB/s)      │ │  RSS per slave (MB)   │ │
│  │       ╱╲                  │ │  ═══════ 412          │ │
│  │   ──╱╱  ╲╲──             │ │  ═══════ 380          │ │
│  │       └──────────────── t │ │       └──────────── t│ │
│  └───────────────────────────┘ └──────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

**Layout**: 2x2 grid of canvas charts + heatmap/averages header
**Charts**: CPU (all slaves overlaid), RAM (all slaves overlaid), Network throughput, JVM RSS
**Each chart**: ~300x150px canvas, auto-scaling Y axis, time axis, hover tooltip with exact values
**All slaves overlaid** on same chart with different colors — easy comparison

### 2. Heatmap

Row of colored squares, one per slave:
- Green (#22c55e) → CPU < 50%
- Yellow (#eab308) → CPU 50-80%
- Red (#ef4444) → CPU > 80%
- Gray (#6b7280) → No data / offline

Click a square → scrolls to that slave in the list below and highlights it briefly

### 3. Per-Slave Drill-Down

Click the metrics area on any slave card to expand a detail panel:

```
┌─ 10.0.0.2 — Detailed Metrics ──────────────────────────┐
│  ┌─ CPU ─────────────┐  ┌─ RAM ─────────────┐          │
│  │  canvas 280x120    │  │  canvas 280x120    │          │
│  └────────────────────┘  └────────────────────┘          │
│  ┌─ Disk ────────────┐  ┌─ Network ──────────┐          │
│  │  18.2 / 40 GB     │  │  ↑ 2.3 MB/s        │          │
│  │  ████████░░ 45%   │  │  ↓ 1.1 MB/s        │          │
│  └────────────────────┘  └────────────────────┘          │
│  JVM: 412 MB RSS | 127 threads | Load: 1.23             │
└──────────────────────────────────────────────────────────┘
```

### 4. Canvas Chart Engine

Lightweight chart renderer — no external dependencies:

```
class FleetChart {
    constructor(canvas, options)  // { title, yMax, yLabel, colors }
    addPoint(seriesId, timestamp, value)
    render()                      // requestAnimationFrame loop
    destroy()
}
```

Features:
- Smooth line interpolation
- Auto-scaling Y axis (0-100% for CPU/RAM, auto for MB)
- Time axis with labels (HH:MM)
- Multiple series overlaid (one color per slave)
- Hover crosshair showing exact value + timestamp
- Animated entry of new data points
- 5-minute rolling window (configurable)
- Dark mode support (reads CSS variables)

### 5. Network Throughput Computation

Client-side delta calculation:
- Store previous `net_rx_bytes` / `net_tx_bytes` per slave
- On new poll: `throughput = (current - previous) / interval_seconds`
- Display as KB/s or MB/s with auto-scaling units

### 6. Data Storage

- `Fleet.chartData[ip]` — array of `{ts, cpu, ram, disk, net_rx, net_tx, jvm_rss, load, threads}`
- Rolling window: keep last 5 minutes of data points
- Cleared on page reload (in-memory only)
- `Fleet._prevNetBytes[ip]` — previous network bytes for delta computation

### 7. Interaction Model

- **Monitor button OFF**: No dashboard, no inline metrics — clean slave list
- **Monitor button ON**: Dashboard section appears with live charts + heatmap
- **Click slave metrics row**: Toggles per-slave drill-down panel
- **Click heatmap square**: Scrolls to slave + flash highlight
- **Hover chart**: Crosshair + tooltip with values

### 8. SSE vs Polling Decision

**Keep polling** (not SSE). Reasoning:
- SSE requires backend to maintain long-lived connections per slave — complex
- Current proxy architecture (`/api/slaves/metrics` → fan-out to agents) works well
- Polling interval is user-configurable (10s-2m)
- For 2-8 slaves, polling is perfectly adequate
- SSE adds complexity for minimal gain at this scale
- Can upgrade to SSE later if needed

## Files to Change

- `webapp/static/js/fleet-charts.js` — **NEW**: Canvas chart engine + dashboard renderer
- `webapp/static/js/fleet-core.js` — Add chartData storage, network delta helpers
- `webapp/static/js/fleet-slaves.js` — Dashboard toggle, drill-down, remove old inline metrics
- `webapp/templates/_fleet_slaves.html` — Dashboard section HTML, drill-down containers
- `webapp/templates/slaves.html` — Add fleet-charts.js script tag
- `webapp/static/css/style.css` — Dashboard grid, chart containers, heatmap styles

## Backend: No Changes

All data already available from `/api/slaves/metrics`. Chart engine is pure client-side.
