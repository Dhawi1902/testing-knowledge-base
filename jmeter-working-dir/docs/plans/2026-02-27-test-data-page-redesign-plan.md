# Test Data Page Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the Test Data page to match the polished visual style of Dashboard, Plans, and Results pages — with stat cards, template cards, full-width table, and mobile responsive card layout.

**Architecture:** Pure frontend changes across two files: HTML template (structure + JS) and CSS (styling + mobile). No backend changes. Dual-render pattern (table + cards) for mobile, same as Results page.

**Tech Stack:** Jinja2 templates, vanilla JS, CSS custom properties, Lucide icons via `{{ icon() }}` macro.

**Design doc:** `docs/plans/2026-02-27-test-data-page-redesign-design.md`

---

### Task 1: CSV Files — Card Header with Icon + Badges

**Files:**
- Modify: `jmeter-working-dir/webapp/templates/data.html:20-23`

**Step 1: Update card header**

Replace the current CSV Files card header (lines 20-22) with the new pattern matching Dashboard/Results:

```html
<div class="card-header">
    <span class="card-title">{{ icon('database', 16) }} CSV Files</span>
    <div class="flex gap-8 items-center">
        <span class="badge badge-info" id="fileCountBadge">0 files</span>
        {% if access_level != 'viewer' %}
        <label class="btn btn-outline btn-sm" style="margin:0;cursor:pointer;">
            {{ icon('upload', 14) }} <span class="btn-label">Upload</span>
            <input type="file" accept=".csv" onchange="uploadCsv(false)" hidden>
        </label>
        {% endif %}
        <button class="btn btn-outline btn-sm" onclick="loadFiles()" data-tooltip="Refresh">
            {{ icon('refresh-cw', 14) }} <span class="btn-label">Refresh</span>
        </button>
    </div>
</div>
```

This moves the Upload button up to the header (currently buried at bottom of CSV Builder) and adds a file count badge. Wrap button text in `.btn-label` for mobile icon-only.

**Step 2: Run tests**

Run: `cd jmeter-working-dir/webapp && python -m pytest tests/ -q`
Expected: All 303 tests pass (no backend changes).

---

### Task 2: CSV Files — Stat Strip

**Files:**
- Modify: `jmeter-working-dir/webapp/templates/data.html` — add stat strip HTML after card-header
- Modify: `jmeter-working-dir/webapp/templates/data.html` — update `loadFiles()` JS (line 867+)

**Step 1: Add stat strip HTML**

Insert after the card-header div (before the table-wrapper):

```html
<div class="grid-4 mb-12" id="csvStats">
    <div class="stat-card">
        <div class="stat-value" id="statFiles">-</div>
        <div class="stat-label">Files</div>
    </div>
    <div class="stat-card">
        <div class="stat-value" id="statRows">-</div>
        <div class="stat-label">Total Rows</div>
    </div>
    <div class="stat-card">
        <div class="stat-value" id="statSize">-</div>
        <div class="stat-label">Total Size</div>
    </div>
    <div class="stat-card">
        <div class="stat-value" id="statCols">-</div>
        <div class="stat-label">Unique Columns</div>
    </div>
</div>
```

**Step 2: Update loadFiles() to populate stats**

In `loadFiles()` (around line 867), after building the file list, add stat computation:

```javascript
// Update stats
const totalRows = mainFiles.reduce((s, f) => s + (f.rows || 0), 0);
const totalSize = mainFiles.reduce((s, f) => s + (f.size_bytes || 0), 0);
const uniqueCols = new Set(mainFiles.flatMap(f => (f.columns || []))).size;
document.getElementById('statFiles').textContent = mainFiles.length;
document.getElementById('statRows').textContent = totalRows.toLocaleString();
document.getElementById('statSize').textContent = formatSize(totalSize);
document.getElementById('statCols').textContent = uniqueCols;
document.getElementById('fileCountBadge').textContent = mainFiles.length + ' file' + (mainFiles.length !== 1 ? 's' : '');
```

Also hide stats when empty (show empty state), show when files exist.

**Step 3: Run tests**

Run: `cd jmeter-working-dir/webapp && python -m pytest tests/ -q`

---

### Task 3: CSV Files — Full-Width Table with Fixed Layout

**Files:**
- Modify: `jmeter-working-dir/webapp/templates/data.html:27-33` — add column classes to `<th>` elements
- Modify: `jmeter-working-dir/webapp/static/css/style.css` — add `.csv-table` column width rules

**Step 1: Add column classes to table headers**

Update the `<thead>` (lines 27-33):

```html
<thead><tr>
    <th class="col-file">File</th>
    <th class="col-columns">Columns</th>
    <th class="col-rows">Rows</th>
    <th class="col-size">Size</th>
    <th class="col-actions">Actions</th>
</tr></thead>
```

**Step 2: Add table class**

Add `csv-table` class to the `<table>` element (line 26):

```html
<table class="csv-table">
```

**Step 3: Add CSS for fixed table layout**

Add after the existing `.results-table` rules (around line 833 in style.css):

```css
/* ----- CSV Files table — fixed layout ----- */
.csv-table { table-layout: fixed; width: 100%; }
.csv-table .col-columns { width: 200px; }
.csv-table .col-rows { width: 100px; text-align: right; }
.csv-table .col-size { width: 100px; text-align: right; }
.csv-table .col-actions { width: 250px; }
.csv-table td:first-child {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: var(--font-mono);
}
```

The `.col-file` column takes remaining space automatically since no width is set.

**Step 4: Update loadFiles() row generation**

In the row generation (around line 885), ensure action buttons use consistent styling:

```javascript
// Action buttons — consistent btn-outline btn-sm pattern
const previewBtn = `<button class="btn btn-outline btn-sm" onclick="previewFile('${ef}')">` +
    `{{ icon('eye', 14) }} Preview</button>`;
const downloadBtn = `<a class="btn btn-outline btn-sm" href="${BASE_PATH}/api/data/download/${encodeURIComponent(f.filename)}">` +
    `{{ icon('download', 14) }} Download</a>`;
const deleteBtn = canEdit ? `<button class="btn btn-outline btn-sm btn-danger-outline" onclick="deleteFile('${ef}')">` +
    `{{ icon('trash-2', 14) }} Delete</button>` : '';
```

Add a `.btn-danger-outline` class in CSS for the red-tinted delete button:
```css
.btn-danger-outline { color: var(--color-danger); border-color: var(--color-danger); }
.btn-danger-outline:hover { background: var(--color-danger); color: #fff; }
```

**Step 5: Verify table renders full-width, no horizontal scroll**

Run: `cd jmeter-working-dir/webapp && python -m pytest tests/ -q`

---

### Task 4: CSV Builder — Card Header + Template Cards

**Files:**
- Modify: `jmeter-working-dir/webapp/templates/data.html:49-50` — card header
- Modify: `jmeter-working-dir/webapp/templates/data.html:54-58` — sidebar structure
- Modify: `jmeter-working-dir/webapp/templates/data.html` — `renderPresetList()` JS (lines 533-556)
- Modify: `jmeter-working-dir/webapp/static/css/style.css:729-735` — sidebar/preset styles

**Step 1: Update CSV Builder card header**

```html
<div class="card-header px-16 py-12">
    <span class="card-title">{{ icon('wrench', 16) }} CSV Builder</span>
    <span class="badge badge-info hidden" id="activeTemplateBadge"></span>
</div>
```

Note: `wrench` icon doesn't exist yet — use `settings` or `edit-2` instead, or add `wrench` to icons.html. Check available icons first: `edit-2` (pencil) is available and fits well. Alternatively use `layers` which is also available.

**Step 2: Update sidebar label + create-new card**

Replace the current sidebar content (lines 55-57):

```html
<div class="sidebar-label">Templates</div>
<button class="preset-card preset-card-new" onclick="createNew()">
    {{ icon('plus', 14) }} Create new
</button>
<div id="presetList"></div>
```

**Step 3: Update renderPresetList() to render cards**

Replace current preset rendering with card-based layout. Each preset card shows:
- Template name (bold)
- Subtitle with column count and primary type
- Active state: left border + tint

```javascript
function renderPresetList() {
    const el = document.getElementById('presetList');
    // Built-in presets
    const builtIn = [
        { key: 'username_only', name: 'Username Only', desc: '1 col · Sequential ID' },
        { key: 'username_password', name: 'Username + Password', desc: '2 cols · Sequential + Static' },
        { key: 'user_status_email', name: 'User + Status + Email', desc: '3 cols · Seq + Pick + Expression' },
        { key: 'student_data', name: 'Student Data (5 prefixes)', desc: '1 col · Sequential (5 ranges)' },
    ];
    let html = builtIn.map(p =>
        `<button class="preset-card${activePreset === p.key ? ' active' : ''}" onclick="selectPreset('${p.key}')">
            <span class="preset-card-name">${p.name}</span>
            <span class="preset-card-desc">${p.desc}</span>
        </button>`
    ).join('');

    // Custom presets from localStorage
    const custom = JSON.parse(localStorage.getItem('jmeter_csv_presets') || '{}');
    const customKeys = Object.keys(custom);
    if (customKeys.length) {
        html += '<div class="sidebar-sep"></div>';
        html += customKeys.map(name => {
            const cols = custom[name].columns || [];
            const desc = cols.length + ' col' + (cols.length !== 1 ? 's' : '');
            return `<button class="preset-card${activePreset === 'custom:' + name ? ' active' : ''}" onclick="selectPreset('custom:${name}')">
                <span class="preset-card-name">${name}</span>
                <span class="preset-card-desc">${desc}</span>
                <span class="preset-del" onclick="event.stopPropagation();deleteCustomPreset('${name}')">&times;</span>
            </button>`;
        }).join('');
    }
    el.innerHTML = html;
}
```

**Step 4: Update preset card CSS**

Replace `.preset-item` rules (style.css lines 732-735) with:

```css
.preset-card {
    display: flex;
    flex-direction: column;
    width: 100%;
    padding: 8px 12px;
    margin-bottom: 4px;
    border: 1px solid transparent;
    border-radius: 6px;
    background: none;
    cursor: pointer;
    text-align: left;
    color: var(--color-text);
    font-size: 0.8rem;
    position: relative;
}
.preset-card:hover { background: var(--color-surface-alt); }
.preset-card.active {
    border-left: 3px solid var(--color-primary);
    background: var(--color-primary-bg, rgba(59,130,246,0.08));
}
.preset-card-new {
    border: 1px dashed var(--color-border);
    flex-direction: row;
    align-items: center;
    gap: 6px;
    color: var(--color-primary);
    font-weight: 600;
    margin-bottom: 8px;
}
.preset-card-name { font-weight: 600; }
.preset-card-desc { font-size: 0.75rem; color: var(--color-text-secondary); margin-top: 2px; }
.preset-del { position: absolute; top: 8px; right: 8px; opacity: 0; cursor: pointer; color: var(--color-text-secondary); }
.preset-card:hover .preset-del { opacity: 1; }
.preset-del:hover { color: var(--color-danger); }
```

**Step 5: Update active template badge**

In `selectPreset()` function, update the badge:

```javascript
const badge = document.getElementById('activeTemplateBadge');
badge.textContent = presetName;
badge.classList.remove('hidden');
```

**Step 6: Run tests**

---

### Task 5: Distribute to Slaves — Visual Upgrade

**Files:**
- Modify: `jmeter-working-dir/webapp/templates/data.html:106-123` — section HTML
- Modify: `jmeter-working-dir/webapp/static/css/style.css` — dist empty state

**Step 1: Update card header**

```html
<div class="card-header">
    <span class="card-title">{{ icon('share-2', 16) }} Distribute to Slaves</span>
    <span class="badge badge-info hidden" id="distCountBadge">0 files</span>
</div>
```

Note: `share-2` doesn't exist — use `send` (already used on Distribute button, line 115) or `upload`. Use `send` for consistency.

**Step 2: Add empty state**

```html
<div class="empty-state" id="distEmpty">
    {{ icon('send', 48) }}
    <div class="empty-state-title">No files queued</div>
    <div class="empty-state-desc">Click "Add file" to queue files for distribution to slave machines.</div>
</div>
```

**Step 3: Update action buttons**

Style action buttons consistently:

```html
<div class="flex gap-8 mt-12">
    <button class="btn btn-outline btn-sm" onclick="addDistFile()">
        {{ icon('plus', 14) }} Add file
    </button>
    <button class="btn btn-outline btn-sm" onclick="previewDist()">
        {{ icon('eye', 14) }} Preview
    </button>
    {% if access_level != 'viewer' %}
    <button class="btn btn-primary btn-sm" onclick="distributeData()">
        {{ icon('send', 14) }} Distribute
    </button>
    {% endif %}
</div>
```

**Step 4: Update addDistFile() to toggle empty state and badge**

```javascript
function addDistFile() {
    // ... existing logic ...
    document.getElementById('distEmpty').classList.add('hidden');
    const count = document.querySelectorAll('.dist-item').length;
    const badge = document.getElementById('distCountBadge');
    badge.textContent = count + ' file' + (count !== 1 ? 's' : '');
    badge.classList.remove('hidden');
}
```

And on remove: if no items left, show empty state again and hide badge.

**Step 5: Run tests**

---

### Task 6: Mobile Responsive — Card Layout for CSV Files

**Files:**
- Modify: `jmeter-working-dir/webapp/templates/data.html` — add card container + JS rendering
- Modify: `jmeter-working-dir/webapp/static/css/style.css` — mobile rules

**Step 1: Add mobile card container**

After the table-wrapper in CSV Files section:

```html
<div id="csvCards" class="csv-cards"></div>
```

**Step 2: Update loadFiles() to render cards**

Same dual-render pattern as Results page. For each file, generate:

```html
<div class="csv-card">
    <div class="csv-card-header">
        <span class="csv-card-name">{filename}</span>
        <div class="dropdown">
            <button class="btn btn-sm btn-icon btn-ghost" onclick="toggleDropdown(this)">
                {{ icon('more-horizontal', 16) }}
            </button>
            <div class="dropdown-menu">
                <button class="dropdown-item" onclick="previewFile('{fn}')">{{ icon('eye', 14) }} Preview</button>
                <a class="dropdown-item" href="...">{{ icon('download', 14) }} Download</a>
                <div class="dropdown-divider"></div>
                <button class="dropdown-item danger" onclick="deleteFile('{fn}')">{{ icon('trash-2', 14) }} Delete</button>
            </div>
        </div>
    </div>
    <div class="csv-card-meta">{rows} rows · {size}</div>
    <div class="csv-card-badges">{column badges}</div>
</div>
```

**Step 3: Add CSS — hide table, show cards on mobile**

```css
.csv-cards { display: none; }

@media (max-width: 768px) {
    /* CSV Files section */
    .csv-table-wrap { display: none !important; }
    .csv-cards { display: flex !important; flex-direction: column; gap: 8px; }

    .csv-card { border: 1px solid var(--color-border); border-radius: 8px; padding: 12px; }
    .csv-card-header { display: flex; align-items: center; gap: 8px; }
    .csv-card-name {
        flex: 1; font-weight: 600; font-family: var(--font-mono);
        font-size: 0.9rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .csv-card-meta { font-size: 0.8rem; color: var(--color-text-secondary); margin-top: 6px; }
    .csv-card-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px; }

    /* CSV Builder — stack sidebar above builder */
    .csv-builder-layout { flex-direction: column; }
    .preset-sidebar { width: 100%; border-right: none; border-bottom: 1px solid var(--color-border); padding: 8px; }
    .preset-sidebar .preset-card { display: inline-flex; flex-direction: row; gap: 6px; width: auto; }
    .preset-card-desc { display: none; }

    /* Stats grid — 2x2 on mobile */
    #csvStats { grid-template-columns: 1fr 1fr; }

    /* Header buttons icon-only */
    .card-header .btn .btn-label { display: none; }
}
```

**Step 4: Run tests**

---

### Task 7: Add Missing Icons + Polish

**Files:**
- Modify: `jmeter-working-dir/webapp/templates/icons.html` — add `wrench` and `share-2` icons if needed
- Modify: `jmeter-working-dir/webapp/static/css/style.css` — any final polish

**Step 1: Check which icons need adding**

If `wrench` or `share-2` aren't in icons.html, either add them or substitute with available icons (`edit-2` for wrench, `send` for share-2).

**Step 2: Final visual polish**

- Verify column badge colors still work in new table layout
- Verify builder form inputs use `form-input` classes
- Verify dark theme renders correctly
- Ensure action button alignment matches Results page

**Step 3: Run full test suite**

Run: `cd jmeter-working-dir/webapp && python -m pytest tests/ -q`
Expected: All 303 tests pass.

**Step 4: Verify in browser**

1. Desktop (1536x864): full-width table, stat cards, template cards, no overflow
2. Mobile (390x844): CSV cards, stacked builder, icon-only headers
3. Both themes: dark + light mode correct

---

### Task 8: Commit

```bash
git add jmeter-working-dir/webapp/templates/data.html jmeter-working-dir/webapp/static/css/style.css jmeter-working-dir/webapp/templates/icons.html docs/plans/2026-02-27-test-data-page-redesign-design.md docs/plans/2026-02-27-test-data-page-redesign-plan.md
git commit -m "style(test-data): redesign page with stat cards, template cards, full-width table, mobile responsive"
```
