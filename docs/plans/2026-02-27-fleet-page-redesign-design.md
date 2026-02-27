# Fleet Page — Redesign Design

**Date**: 2026-02-27
**Status**: Approved

## Overview

Redesign the Fleet Management page to match the polished visual style of Dashboard, Test Plans, Results, and Test Data pages. Adds stat strip, icon-only header buttons, grouped per-slave actions with dropdown, inline style cleanup, and mobile responsive card layout.

## Design Decisions

| Decision | Choice |
|---|---|
| Per-slave actions | Grouped: Start/Stop visible, rest in 3-dot dropdown |
| Stat strip | Yes — 4 mini stat cards (Total VMs, Online, Offline, Disabled) |
| Header buttons | Icon-only with tooltips (Add, Check Status, Resources, Start All, Stop All, Sync Data) |
| Mobile layout | Cards on mobile for list view, single-column grid, 2x2 stats |

## Section 1: Card Header

### Title
- Left: `{{ icon('server', 16) }} Slave List`

### Buttons (icon-only with data-tooltip)
- `plus` Add
- `refresh-cw` Check Status
- `cpu` Resources
- `power` Start All (primary style)
- `stop-circle` Stop All (danger outline)
- `upload` Sync Data
- Divider
- `layers` / `hard-drive` view toggle

### Bulk Action Bar
- Unchanged — already well-styled with selection count and action buttons

## Section 2: Stat Strip

4 mini stat cards computed from `slaveData` after load and status check:
- **Total VMs** — `slaveData.length`
- **Online** — enabled slaves with `status === 'up'`
- **Offline** — enabled slaves with `status !== 'up'` and status checked
- **Disabled** — slaves with `enabled === false`

Replaces the current badge-based `#slaveSummary`. Updated in `updateSummary()`.

## Section 3: Per-Slave Actions

### Visible buttons (per slave row/card)
- Status dot + badge
- Start `▶` button
- Stop `■` button
- Enable/Disable toggle
- Gear button (config expand)

### 3-dot dropdown menu
- SSH Test
- RMI Test
- Provision
- Restart
- View Log
- Clean Data
- Clean Log
- separator
- Remove (danger color)

Cuts 9 visible buttons down to 3 + toggle + gear + dropdown.

## Section 4: Inline Styles Cleanup

- Replace `style="padding:2px 6px;font-size:11px;"` with `.btn-xs` utility class
- Replace inline `color:var(--color-danger);border-color:var(--color-danger)` with `.btn-danger-outline`
- Move all remaining inline styles to CSS classes

## Section 5: Mobile Responsive (< 768px)

- **Header buttons**: already icon-only, tighten gaps
- **List view**: switch to card layout (filename, status, Start/Stop, 3-dot)
- **Grid view**: single column
- **Stat strip**: 2x2 grid
- **Config panel**: full-width below card

## Files to Modify

1. `jmeter-working-dir/webapp/templates/slaves.html` — HTML structure, JS rendering
2. `jmeter-working-dir/webapp/static/css/style.css` — `.btn-xs`, card styles, mobile rules
