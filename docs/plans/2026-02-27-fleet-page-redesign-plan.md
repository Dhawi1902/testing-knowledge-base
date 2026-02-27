# Fleet Page Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the Fleet Management page with icon-only header, stat strip, grouped per-slave actions with dropdown, inline style cleanup, and mobile card layout.

**Architecture:** Pure frontend changes to `slaves.html` (Jinja2 + JS) and `style.css`. No backend changes. The page has list view and grid view renderers that both need updating; a `render()` dispatcher calls `renderList()` or `renderGrid()`.

**Tech Stack:** Jinja2 templates, vanilla JS, CSS custom properties, Feather icons via `{{ icon() }}` macro.

**Design doc:** `docs/plans/2026-02-27-fleet-page-redesign-design.md`

---

### Task 1: Add `.btn-xs` utility class and icon-only header buttons

**Files:**
- Modify: `jmeter-working-dir/webapp/static/css/style.css`
- Modify: `jmeter-working-dir/webapp/templates/slaves.html:14-27`

**Context:** The header currently has 7 text-labeled buttons. We convert them all to icon-only with tooltips. The inline style `padding:2px 6px;font-size:11px;` is used ~20 times for small per-slave buttons — we replace it with a `.btn-xs` class.

**Step 1: Add `.btn-xs` to CSS**

In `style.css`, after the existing `.btn-sm` rule (find it with `grep -n 'btn-sm'`), add:

```css
.btn-xs { padding: 2px 6px; font-size: 11px; }
```

**Step 2: Convert header buttons to icon-only**

Replace the `#defaultActions` div (lines 15-27 of `slaves.html`) with:

```html
<div class="flex gap-4 items-center" id="defaultActions">
    {% if access_level != 'viewer' %}<button class="btn btn-outline btn-sm" onclick="addSlave()" data-tooltip="Add slave">{{ icon('plus', 14) }}</button>{% endif %}
    <button class="btn btn-outline btn-sm" onclick="refreshStatus()" id="refreshBtn" data-tooltip="Check status">{{ icon('refresh-cw', 14) }}</button>
    <button class="btn btn-outline btn-sm" onclick="refreshResources()" id="resourcesBtn" data-tooltip="Check resources">{{ icon('cpu', 14) }}</button>
    {% if access_level != 'viewer' %}
    <button class="btn btn-primary btn-sm" onclick="startAll()" id="startAllBtn" data-tooltip="Start all">{{ icon('power', 14) }}</button>
    <button class="btn btn-danger-outline btn-sm" onclick="stopAll()" id="stopAllBtn" data-tooltip="Stop all">{{ icon('stop-circle', 14) }}</button>
    <button class="btn btn-outline btn-sm" onclick="syncData()" data-tooltip="Sync data">{{ icon('upload', 14) }}</button>
    {% endif %}
    <span class="divider-v"></span>
    <button class="btn btn-outline btn-sm view-toggle" id="viewListBtn" onclick="setView('list')" data-tooltip="List view">{{ icon('layers', 14) }}</button>
    <button class="btn btn-outline btn-sm view-toggle" id="viewGridBtn" onclick="setView('grid')" data-tooltip="Grid view">{{ icon('hard-drive', 14) }}</button>
</div>
```

Key changes:
- Removed text labels from all buttons
- Added `data-tooltip` to each
- Changed Stop All from inline danger styles to `.btn-danger-outline`
- Changed gap from `gap-8` to `gap-4` for tighter spacing
- Added icon to Check Status and Resources (previously text-only)

**Step 3: Add icon to card title**

Replace the card-title span (line 11):
```html
<span class="card-title" style="cursor:pointer;" onclick="toggleSlaveList()"><span class="collapse-icon" id="slaveCollapseIcon">&#9660;</span> Slave List</span>
```
With:
```html
<span class="card-title" style="cursor:pointer;" onclick="toggleSlaveList()">{{ icon('server', 16) }} <span class="collapse-icon" id="slaveCollapseIcon">&#9660;</span> Slave List</span>
```

**Step 4: Fix `startAll()`/`stopAll()` JS**

These functions set `btn.textContent = 'Starting...'` which will break with icon-only buttons. Update:

In `startAll()` (~line 634-648):
- Change `btn.textContent = 'Starting...';` → `btn.disabled = true; btn.dataset.tooltip = 'Starting...';`
- Change `btn.textContent = 'Start All';` → `btn.disabled = false; btn.dataset.tooltip = 'Start all';`

In `stopAll()` (~line 654-667):
- Same pattern: use `btn.dataset.tooltip` instead of `btn.textContent`

In `refreshStatus()` (~line 208-235):
- Change `btn.textContent = 'Checking...';` → `btn.dataset.tooltip = 'Checking...';`
- Change `btn.textContent = 'Check Status';` → `btn.dataset.tooltip = 'Check status';`

**Step 5: Run tests**

```bash
cd jmeter-working-dir/webapp && python -m pytest tests/ -q
```

Expected: All 303 tests pass.

---

### Task 2: Stat strip

**Files:**
- Modify: `jmeter-working-dir/webapp/templates/slaves.html:42-52` (HTML) and `updateSummary()` (~line 552)

**Context:** Currently `#slaveSummary` shows badges inline in the header. We replace it with a stat strip below the header (same pattern as Test Data page's `#csvStats`).

**Step 1: Remove old summary badges from header**

Replace the `#slaveSummary` span (line 12):
```html
<span class="text-sm flex gap-4" id="slaveSummary">Loading...</span>
```
With just:
```html
<span class="text-sm text-light" id="lastCheckedLabel"></span>
```
(We keep only the "checked Xm ago" text in the header.)

**Step 2: Add stat strip HTML**

After the `</div>` closing `card-header` (after line 41), before `<div id="slaveBody">`, insert:

```html
<div class="grid grid-4 mb-12" id="fleetStats" style="display:none;padding:0 16px;">
    <div class="stat-card"><div class="stat-value" id="statVMs">-</div><div class="stat-label">Total VMs</div></div>
    <div class="stat-card"><div class="stat-value" id="statOnline">-</div><div class="stat-label">Online</div></div>
    <div class="stat-card"><div class="stat-value" id="statOffline">-</div><div class="stat-label">Offline</div></div>
    <div class="stat-card"><div class="stat-value" id="statDisabled">-</div><div class="stat-label">Disabled</div></div>
</div>
```

**Step 3: Rewrite `updateSummary()` JS**

Replace the entire `updateSummary()` function (~lines 552-565):

```javascript
function updateSummary() {
    const total = slaveData.length;
    const enabled = slaveData.filter(s => s.enabled !== false).length;
    const disabled = total - enabled;
    const checked = slaveData.filter(s => s.status !== null && s.enabled !== false).length;
    const up = slaveData.filter(s => s.enabled !== false && s.status === 'up').length;
    const down = checked - up;

    const statsEl = document.getElementById('fleetStats');
    if (total > 0) {
        statsEl.style.display = '';
        document.getElementById('statVMs').textContent = total;
        document.getElementById('statOnline').textContent = up;
        document.getElementById('statOffline').textContent = down;
        document.getElementById('statDisabled').textContent = disabled;
    } else {
        statsEl.style.display = 'none';
    }

    const lc = formatLastChecked();
    const lcEl = document.getElementById('lastCheckedLabel');
    if (lcEl) lcEl.textContent = lc ? 'checked ' + lc : '';
}
```

**Step 4: Run tests**

```bash
cd jmeter-working-dir/webapp && python -m pytest tests/ -q
```

---

### Task 3: Per-slave actions — grouped buttons + 3-dot dropdown

**Files:**
- Modify: `jmeter-working-dir/webapp/templates/slaves.html` — `renderList()` (~line 282) and `renderGrid()` (~line 338)

**Context:** Each slave currently shows 9 action buttons inline. We keep Start/Stop/Toggle/Gear visible, move SSH/RMI/Provision/Restart/Log/Clean/ClnLog/Remove into a 3-dot dropdown. The dropdown pattern already exists in the codebase (Results page uses it).

**Step 1: Add dropdown icon constant**

Near the top of the `<script>` block (after `let currentView = ...`, ~line 182), add:

```javascript
const ICON_MORE = '{{ icon("more-vertical", 16) }}';
```

**Step 2: Rewrite per-slave actions in `renderList()`**

In the `renderList()` function, replace the `.slave-actions` div content (lines 310-328). The new pattern:

```javascript
<div class="slave-actions">
    ${statusBadge(s)}
    ${provisionBadges(s)}
    ${resourceBadges(s)}
    ${isAdmin && enabled ? `<button class="btn btn-outline btn-xs" onclick="startSingle('${aIp}')" data-tooltip="Start">&#9654;</button>` : ''}
    ${isAdmin && enabled ? `<button class="btn btn-danger-outline btn-xs" onclick="stopSingle('${aIp}')" data-tooltip="Stop">&#9632;</button>` : ''}
    ${isAdmin && enabled ? `<div class="dropdown">
        <button class="btn btn-outline btn-xs" onclick="toggleDropdown(this)">${ICON_MORE}</button>
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
    ${isAdmin ? `<button class="gear-btn${expanded ? ' active' : ''}" onclick="toggleConfig('${aIp}')" data-tooltip="SSH overrides">${gearIcon(expanded)}</button>` : ''}
    ${isAdmin ? `<label class="toggle" title="${enabled ? 'Disable' : 'Enable'}">
        <input type="checkbox" ${enabled ? 'checked' : ''} onchange="toggleSlave('${aIp}', this.checked)">
        <span class="toggle-track"></span>
    </label>` : ''}
</div>
```

Note: Extract the gear SVG into a helper function `gearIcon(expanded)` to avoid the massive inline SVG duplication:

```javascript
function gearIcon(expanded) {
    return '<svg class="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>';
}
```

**Step 3: Apply same pattern to `renderGrid()`**

Replace the action buttons in `renderGrid()` (lines 356-374) with the same grouped buttons + dropdown pattern. The grid card already has a different layout (flex-between header), so the actions go in the same position.

**Step 4: Remove the old `.del-btn` Remove button**

The `× Remove` button is now inside the dropdown, so remove the standalone `del-btn` references from both `renderList()` and `renderGrid()`. The `.del-btn` CSS can stay (harmless).

**Step 5: Run tests**

```bash
cd jmeter-working-dir/webapp && python -m pytest tests/ -q
```

---

### Task 4: Replace remaining inline styles with utility classes

**Files:**
- Modify: `jmeter-working-dir/webapp/templates/slaves.html`

**Context:** After Task 3, scan for remaining inline `style=` attributes on buttons and replace with utility classes.

**Step 1: Find and replace inline button styles**

Search for `style="padding:2px 6px;font-size:11px;"` — these should all be gone after Task 3 (replaced by `.btn-xs`). Verify with grep.

Search for `style="color:var(--color-danger);border-color:var(--color-danger);"` — replace with class `btn-danger-outline`.

Search for `style="color:var(--color-danger);border:1px solid var(--color-danger);background:transparent;"` in the bulk bar Remove button — replace with class `btn-danger-outline`.

**Step 2: Run tests**

```bash
cd jmeter-working-dir/webapp && python -m pytest tests/ -q
```

---

### Task 5: Mobile responsive layout

**Files:**
- Modify: `jmeter-working-dir/webapp/static/css/style.css` — mobile `@media` section

**Context:** On mobile (< 768px), list view should look like cards (similar to Results/Test Data), grid should go single-column, stat strip should be 2x2.

**Step 1: Add mobile CSS**

In the `@media (max-width: 768px)` section, add:

```css
/* Fleet mobile */
#fleetStats { grid-template-columns: 1fr 1fr; }
.slave-grid { grid-template-columns: 1fr; }
.slave-entry { border-radius: 8px !important; margin-bottom: 8px; border-bottom: 1px solid var(--color-border) !important; }
.slave-list .slave-row { flex-wrap: wrap; gap: 6px; }
.slave-list .slave-row .slave-meta { width: 100%; margin-left: 0; }
.slave-list .slave-row .slave-actions { width: 100%; justify-content: flex-start; flex-wrap: wrap; }
.slave-config-panel { flex-direction: column; }
.slave-config-panel .form-group { min-width: 100%; }
```

**Step 2: Run tests**

```bash
cd jmeter-working-dir/webapp && python -m pytest tests/ -q
```

---

### Task 6: Visual verification and cleanup

**Step 1: Desktop verification**

Navigate to `http://localhost:8080/fleet` at full width. Verify:
- Icon-only header buttons with tooltips
- Stat strip shows (if slaves configured) or hidden (if empty)
- Per-slave actions: Start/Stop visible, 3-dot dropdown for rest
- Gear button and toggle still work
- No horizontal scrollbar

**Step 2: Mobile verification**

Resize to 390x844. Verify:
- Stat strip 2x2
- Grid single-column
- List entries card-like
- Header buttons still icon-only and accessible

**Step 3: Run full test suite**

```bash
cd jmeter-working-dir/webapp && python -m pytest tests/ -q
```

Expected: All tests pass.

**Step 4: Commit**

```bash
git add jmeter-working-dir/webapp/templates/slaves.html jmeter-working-dir/webapp/static/css/style.css
git commit -m "style(ui): redesign Fleet page — icon headers, stat strip, grouped actions, mobile"
```
