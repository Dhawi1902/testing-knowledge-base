# Slaves Tab Redesign — Inline Resource Cards + Enhanced Monitoring

**Date**: 2026-03-03
**Status**: Approved
**Approach**: A — Inline Resource Cards

## Problem

The slaves tab has three issues:
1. **List view clutter** — IP, nickname, sparkline, status/provision badges, 6+ action buttons all crammed in one row. No visual hierarchy; everything has equal weight.
2. **Monitoring panel disconnected** — CPU/RAM/JVM shown in a separate table at the bottom, hard to correlate with the slave it belongs to.
3. **Missing useful info** — No disk usage, load average, network I/O, JMeter thread counts, or uptime at a glance.

## Design

### 1. Two-Row Slave Cards (List View)

Each slave becomes a compact two-row card:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [☑] ● 100.125.26.29  VM #1 "worker-east"  ████████████  ▶ ■ ⚙ [···] ⏻ │
│     CPU ██████░░░░ 58%   RAM ████████░░ 78%   JVM 412MB   ⬆ 2h 14m    │
└──────────────────────────────────────────────────────────────────────────┘
```

**Row 1** (identity + controls):
- Checkbox (admin), status dot, IP (editable), VM#, nickname, health sparkline
- Right side: Start, Stop, gear (SSH overrides), "..." dropdown menu, enable/disable toggle

**Row 2** (metrics + status):
- Inline mini progress bars for CPU, RAM
- JVM RSS value (color-coded)
- Uptime (time since last up transition from health history)
- Status badge + provision badges
- When monitoring is off: shows just status badge + provision badges
- When monitoring is on: shows resource bars + JVM + uptime + provision badges

### 2. Summary Bar (replaces bottom monitoring panel)

Compact fleet-wide summary strip when monitoring is active:

```
● Live  |  Avg CPU: 52%  |  Avg RAM: 71%  |  2/2 JMeter Up  |  Next poll: 12s
```

### 3. Enhanced Metrics Agent

Extend `metrics_agent.py` to also report:
- **Disk usage**: `disk_percent`, `disk_used_gb`, `disk_total_gb` (/ partition)
- **Load average**: `load_1m` (1-minute load average)
- **Network I/O**: `net_rx_bytes`, `net_tx_bytes` (cumulative, delta computed client-side)
- **JMeter threads**: `jmeter_threads` (active thread count from /proc)

### 4. Historical Sparklines

- Store last 20 data points per slave in `Fleet.metricsHistory[ip]` (array of {ts, cpu, ram})
- Render tiny inline SVG sparklines next to CPU/RAM bars
- Data persisted only in-memory (resets on page reload)

### 5. Grid View

Grid cards get the same two-row treatment — resource bars in a second row below the card header.

## Files to Change

- `utils/metrics_agent.py` — Add disk, load, network, thread metrics
- `webapp/static/js/fleet-slaves.js` — Redesign `renderList()`, `renderGrid()`, `renderMonitoringPanel()` → `renderSummaryBar()`, add `metricsHistory` tracking
- `webapp/static/js/fleet-core.js` — Add `metricsHistory` to Fleet state, add sparkline SVG helper
- `webapp/static/css/style.css` — New styles for two-row cards, summary bar, inline metrics
- `webapp/templates/_fleet_slaves.html` — Update monitoring panel div → summary bar div

## Backend: No API changes needed

The `/api/slaves/metrics` endpoint already proxies to the metrics agent. The agent extension is backward-compatible (new fields added alongside existing ones).
