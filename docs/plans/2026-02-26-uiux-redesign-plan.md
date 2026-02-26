# UI/UX Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the JMeter Test Dashboard from functional to professional with a "Linear meets Vercel" aesthetic — clean developer tool with modern spacing and polish.

**Architecture:** CSS-first redesign in two phases. Phase 1 rebuilds the design system (tokens, icons, interaction components) so every page benefits. Phase 2 applies the system page-by-page with UX fixes. No framework change — stays vanilla HTML/CSS/JS. No backend changes.

**Tech Stack:** CSS custom properties, Lucide inline SVGs (33 icons), Jinja2 macros, vanilla JS

**Design Doc:** `docs/plans/2026-02-26-uiux-redesign-design.md`

---

## Phase 1: Design System + Interaction Patterns

### Task 1: CSS Token Refresh — Colors, Typography, Spacing, Radius

Rework the CSS custom properties and add utility classes. This is the foundation everything else builds on.

**Files:**
- Modify: `webapp/static/css/style.css:1-47` (`:root` and `[data-theme="dark"]` blocks)
- Modify: `webapp/static/css/style.css:105-124` (`.nav-item` active state)

**Step 1: Update `:root` variables (style.css lines 2-25)**

Replace the existing `:root` block with refined tokens:

```css
/* ===== CSS Variables ===== */
:root {
    /* Layout */
    --sidebar-width: 240px;
    --topbar-height: 56px;

    /* Colors — Light */
    --color-bg: #f8fafc;
    --color-bg-secondary: #f1f5f9;
    --color-surface: #ffffff;
    --color-surface-alt: #f1f5f9;
    --color-surface-hover: #e2e8f0;
    --color-sidebar: #0f172a;
    --color-sidebar-hover: #1e293b;
    --color-sidebar-active: #3b82f6;
    --color-primary: #3b82f6;
    --color-primary-hover: #2563eb;
    --color-primary-subtle: rgba(59, 130, 246, 0.1);
    --color-danger: #ef4444;
    --color-danger-hover: #dc2626;
    --color-danger-subtle: rgba(239, 68, 68, 0.1);
    --color-success: #22c55e;
    --color-success-subtle: rgba(34, 197, 94, 0.1);
    --color-warning: #f59e0b;
    --color-warning-subtle: rgba(245, 158, 11, 0.1);
    --color-text: #0f172a;
    --color-text-secondary: #64748b;
    --color-text-tertiary: #94a3b8;
    --color-border: #e2e8f0;

    /* Radius */
    --radius-sm: 4px;
    --radius: 6px;
    --radius-lg: 8px;
    --radius-xl: 12px;

    /* Shadows */
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.08);
    --shadow-lg: 0 4px 12px rgba(0, 0, 0, 0.1);

    /* Typography */
    --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --font-mono: 'Consolas', 'Monaco', 'Courier New', monospace;
}
```

**Step 2: Update `[data-theme="dark"]` block (style.css lines 28-47)**

Replace with refined dark tokens:

```css
[data-theme="dark"] {
    --color-bg: #0c1222;
    --color-bg-secondary: #162032;
    --color-surface: #1a2332;
    --color-surface-alt: #162032;
    --color-surface-hover: #243044;
    --color-sidebar: #0a0f1a;
    --color-sidebar-hover: #162032;
    --color-border: #1e3048;
    --color-text: #e2e8f0;
    --color-text-secondary: #8b9bb5;
    --color-text-tertiary: #5a6a80;
    --color-primary-subtle: rgba(59, 130, 246, 0.15);
    --color-danger-subtle: rgba(239, 68, 68, 0.15);
    --color-success-subtle: rgba(34, 197, 94, 0.15);
    --color-warning-subtle: rgba(245, 158, 11, 0.15);
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
    --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.3);
    --shadow-lg: 0 4px 12px rgba(0, 0, 0, 0.4);
}
[data-theme="dark"] th { background: var(--color-surface-alt); }
[data-theme="dark"] tr:hover td { background: var(--color-surface-hover); }
[data-theme="dark"] .log-output { background: #0a0f1a; }
[data-theme="dark"] .badge-success, [data-theme="dark"] .badge-danger,
[data-theme="dark"] .badge-warning, [data-theme="dark"] .badge-info { color: #fff; }
[data-theme="dark"] .toast-warning { color: #1e293b; }
```

**Step 3: Add typography scale classes (append after variables, before existing component styles)**

Add after the dark theme block (around line 48):

```css
/* ===== Typography Scale ===== */
.text-2xl { font-size: 1.5rem; font-weight: 700; line-height: 1.2; }
.text-xl { font-size: 1.25rem; font-weight: 600; line-height: 1.3; }
.text-lg { font-size: 1.05rem; font-weight: 600; line-height: 1.4; }
.text-base { font-size: 0.875rem; font-weight: 400; line-height: 1.5; }
.text-sm { font-size: 0.8125rem; font-weight: 400; line-height: 1.5; }
.text-xs { font-size: 0.75rem; font-weight: 400; line-height: 1.5; }
.text-mono { font-family: var(--font-mono); }
.text-secondary { color: var(--color-text-secondary); }
.text-tertiary { color: var(--color-text-tertiary); }
```

**Step 4: Add spacing utility classes**

Add after typography:

```css
/* ===== Spacing Utilities ===== */
.m-0 { margin: 0; } .m-4 { margin: 4px; } .m-8 { margin: 8px; } .m-12 { margin: 12px; } .m-16 { margin: 16px; } .m-24 { margin: 24px; } .m-32 { margin: 32px; }
.mt-0 { margin-top: 0; } .mt-4 { margin-top: 4px; } .mt-8 { margin-top: 8px; } .mt-12 { margin-top: 12px; } .mt-16 { margin-top: 16px; } .mt-24 { margin-top: 24px; } .mt-32 { margin-top: 32px; }
.mb-0 { margin-bottom: 0; } .mb-4 { margin-bottom: 4px; } .mb-12 { margin-bottom: 12px; } .mb-32 { margin-bottom: 32px; }
.ml-4 { margin-left: 4px; } .ml-8 { margin-left: 8px; } .ml-12 { margin-left: 12px; } .ml-16 { margin-left: 16px; }
.mr-4 { margin-right: 4px; } .mr-8 { margin-right: 8px; } .mr-12 { margin-right: 12px; }
.p-0 { padding: 0; } .p-4 { padding: 4px; } .p-8 { padding: 8px; } .p-12 { padding: 12px; } .p-16 { padding: 16px; } .p-20 { padding: 20px; } .p-24 { padding: 24px; } .p-32 { padding: 32px; }
.pt-0 { padding-top: 0; } .pt-8 { padding-top: 8px; } .pt-12 { padding-top: 12px; } .pt-16 { padding-top: 16px; }
.pb-0 { padding-bottom: 0; } .pb-8 { padding-bottom: 8px; } .pb-12 { padding-bottom: 12px; } .pb-16 { padding-bottom: 16px; }
.pl-8 { padding-left: 8px; } .pl-12 { padding-left: 12px; } .pl-16 { padding-left: 16px; }
.pr-8 { padding-right: 8px; } .pr-12 { padding-right: 12px; } .pr-16 { padding-right: 16px; }
.px-8 { padding-left: 8px; padding-right: 8px; } .px-12 { padding-left: 12px; padding-right: 12px; } .px-16 { padding-left: 16px; padding-right: 16px; }
.py-8 { padding-top: 8px; padding-bottom: 8px; } .py-12 { padding-top: 12px; padding-bottom: 12px; } .py-16 { padding-top: 16px; padding-bottom: 16px; }
.gap-4 { gap: 4px; } .gap-12 { gap: 12px; } .gap-20 { gap: 20px; } .gap-24 { gap: 24px; } .gap-32 { gap: 32px; }
```

**Step 5: Add grid layout utilities**

```css
/* ===== Grid Utilities ===== */
.grid { display: grid; gap: 16px; }
.grid-2 { grid-template-columns: repeat(2, 1fr); }
.grid-3 { grid-template-columns: repeat(3, 1fr); }
.grid-4 { grid-template-columns: repeat(4, 1fr); }
.grid-1-2 { grid-template-columns: 1fr 2fr; }
.grid-2-1 { grid-template-columns: 2fr 1fr; }
.grid-1-2-1 { grid-template-columns: 1fr 2fr 1fr; }
@media (max-width: 768px) {
    .grid-2, .grid-3, .grid-4, .grid-1-2, .grid-2-1, .grid-1-2-1 { grid-template-columns: 1fr; }
}
```

**Step 6: Update `.nav-item.active` to use left accent bar (style.css line 119-123)**

Change from full background fill to a left accent bar (Linear style):

```css
.nav-item.active {
    background: var(--color-sidebar-hover);
    color: #fff;
    border-left: 3px solid var(--color-sidebar-active);
    padding-left: 13px; /* compensate for border */
}
```

**Step 7: Update existing component radius values**

Update `.card` (line 162), `.btn` (line 231), `.form-input` (line 272), `.modal` (line 442), `.badge` (line 391) to use the new radius tokens:
- `.card` → `border-radius: var(--radius-lg);`
- `.btn` → `border-radius: var(--radius);`
- `.form-input, .form-select, .form-textarea` → `border-radius: var(--radius-sm);`
- `.modal` → `border-radius: var(--radius-lg);`
- `.badge` → `border-radius: var(--radius-sm);`

**Step 8: Verify and commit**

Run: `cd jmeter-working-dir/webapp && python -m pytest tests/ -x -q`
Expected: All 198 tests pass (CSS changes don't affect backend tests).

```bash
git add webapp/static/css/style.css
git commit -m "style: refresh CSS tokens — colors, typography scale, spacing utilities, grid helpers"
```

---

### Task 2: Lucide Icon System

Create a Jinja2 macros file with all 33 Lucide SVG icons and integrate into base template.

**Files:**
- Create: `webapp/templates/icons.html`
- Modify: `webapp/templates/base.html:1-5` (add macro import)

**Step 1: Create `icons.html` with Lucide SVG macros**

Create `webapp/templates/icons.html`. Each macro outputs an inline `<svg>` element. The file defines a single `icon(name, size)` macro that switches on icon name.

```html
{% macro icon(name, size=16, cls='') %}
{% set s = size|string %}
<svg class="icon {{ cls }}" width="{{ s }}" height="{{ s }}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
{% if name == 'layout-dashboard' %}<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>
{% elif name == 'play' %}<polygon points="6 3 20 12 6 21 6 3"/>
{% elif name == 'bar-chart-3' %}<path d="M12 20V10"/><path d="M18 20V4"/><path d="M6 20v-4"/>
{% elif name == 'database' %}<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/>
{% elif name == 'server' %}<rect width="20" height="8" x="2" y="2" rx="2" ry="2"/><rect width="20" height="8" x="2" y="14" rx="2" ry="2"/><line x1="6" x2="6.01" y1="6" y2="6"/><line x1="6" x2="6.01" y1="18" y2="18"/>
{% elif name == 'settings' %}<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>
{% elif name == 'trash-2' %}<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/>
{% elif name == 'plus' %}<path d="M5 12h14"/><path d="M12 5v14"/>
{% elif name == 'download' %}<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>
{% elif name == 'refresh-cw' %}<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M3 21v-5h5"/>
{% elif name == 'upload' %}<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/>
{% elif name == 'copy' %}<rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
{% elif name == 'external-link' %}<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
{% elif name == 'chevron-down' %}<path d="m6 9 6 6 6-6"/>
{% elif name == 'chevron-right' %}<path d="m9 18 6-6-6-6"/>
{% elif name == 'chevron-up' %}<path d="m18 15-6-6-6 6"/>
{% elif name == 'x' %}<path d="M18 6 6 18"/><path d="m6 6 12 12"/>
{% elif name == 'check' %}<path d="M20 6 9 17l-5-5"/>
{% elif name == 'alert-triangle' %}<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>
{% elif name == 'info' %}<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>
{% elif name == 'search' %}<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
{% elif name == 'edit-2' %}<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/>
{% elif name == 'more-horizontal' %}<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>
{% elif name == 'eye' %}<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>
{% elif name == 'eye-off' %}<path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49"/><path d="M14.084 14.158a3 3 0 0 1-4.242-4.242"/><path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143"/><path d="m2 2 20 20"/>
{% elif name == 'sun' %}<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>
{% elif name == 'moon' %}<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>
{% elif name == 'terminal' %}<polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/>
{% elif name == 'folder-open' %}<path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"/>
{% elif name == 'file-text' %}<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>
{% elif name == 'zap' %}<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>
{% elif name == 'activity' %}<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>
{% elif name == 'circle' %}<circle cx="12" cy="12" r="10"/>
{% elif name == 'loader-2' %}<path d="M21 12a9 9 0 1 1-6.219-8.56"/>
{% elif name == 'square' %}<rect width="18" height="18" x="3" y="3" rx="2"/>
{% elif name == 'power' %}<path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" x2="12" y1="2" y2="12"/>
{% elif name == 'save' %}<path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7"/><path d="M7 3v4a1 1 0 0 0 1 1h7"/>
{% elif name == 'stop-circle' %}<circle cx="12" cy="12" r="10"/><rect width="6" height="6" x="9" y="9"/>
{% elif name == 'clock' %}<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
{% elif name == 'wifi' %}<path d="M12 20h.01"/><path d="M2 8.82a15 15 0 0 1 20 0"/><path d="M5 12.859a10 10 0 0 1 14 0"/><path d="M8.5 16.429a5 5 0 0 1 7 0"/>
{% elif name == 'wifi-off' %}<path d="M12 20h.01"/><path d="M8.5 16.429a5 5 0 0 1 7 0"/><path d="M2 2l20 20"/><path d="M10.127 5.878A15 15 0 0 1 22 8.82"/><path d="M5 12.859a10 10 0 0 1 5.09-3.273"/>
{% elif name == 'filter' %}<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
{% elif name == 'layers' %}<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22.54 12.43-1.96-.89-8.58 3.91a2 2 0 0 1-1.66 0l-8.58-3.91-1.96.89a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/>
{% elif name == 'hard-drive' %}<line x1="22" x2="2" y1="12" y2="12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><line x1="6" x2="6.01" y1="16" y2="16"/><line x1="10" x2="10.01" y1="16" y2="16"/>
{% endif %}
</svg>
{% endmacro %}
```

**Step 2: Add `.icon` CSS class to style.css**

Add after the typography scale:

```css
/* ===== Icons ===== */
.icon { display: inline-block; vertical-align: middle; flex-shrink: 0; }
.icon-spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
```

**Step 3: Import macro in base.html**

Add at the very top of `webapp/templates/base.html` (before `<!DOCTYPE html>`):

```html
{% from 'icons.html' import icon %}
```

**Step 4: Verify and commit**

Run: `cd jmeter-working-dir/webapp && python -m pytest tests/ -x -q`

```bash
git add webapp/templates/icons.html webapp/static/css/style.css webapp/templates/base.html
git commit -m "feat(ui): add Lucide SVG icon system with 33 icons as Jinja2 macros"
```

---

### Task 3: Replace Navigation Icons

Replace all Unicode character icons in sidebar and bottom nav with Lucide icons.

**Files:**
- Modify: `webapp/templates/base.html:19-39` (sidebar nav items)
- Modify: `webapp/templates/base.html:59-80` (bottom nav)

**Step 1: Replace sidebar nav icons (base.html lines 19-39)**

Each nav item currently looks like:
```html
<a class="nav-item ..." href="...">
    <span class="nav-icon">&#9632;</span> Dashboard
</a>
```

Replace each `<span class="nav-icon">UNICODE</span>` with:
- Line 19: `&#9632;` → `{{ icon('layout-dashboard', 18) }}`
- Line 23: `&#9654;` → `{{ icon('play', 18) }}`
- Line 27: `&#9733;` → `{{ icon('bar-chart-3', 18) }}`
- Line 31: `&#9776;` → `{{ icon('database', 18) }}`
- Line 35: `&#9731;` → `{{ icon('server', 18) }}`
- Line 39: `&#9881;` → `{{ icon('settings', 18) }}`

Keep the `<span class="nav-icon">` wrapper but put the icon macro inside it.

**Step 2: Replace bottom nav icons (base.html lines 61-77)**

- Line 61: `&#9632;` → `{{ icon('layout-dashboard', 20) }}`
- Line 65: `&#9654;` → `{{ icon('play', 20) }}`
- Line 69: `&#9733;` → `{{ icon('bar-chart-3', 20) }}`
- Line 73: `&#9776;` → `{{ icon('database', 20) }}`
- Line 77: `&#9776;` → `{{ icon('more-horizontal', 20) }}`

**Step 3: Update `.nav-icon` CSS to accommodate SVGs**

The current `.nav-icon` may have font-size styling. Update in style.css to work with inline SVGs:

```css
.nav-icon { display: inline-flex; align-items: center; justify-content: center; width: 20px; margin-right: 12px; }
```

**Step 4: Update menu button icon (base.html line 50)**

Replace `&#9776;` in the topbar menu button with `{{ icon('layers', 20) }}`.

**Step 5: Verify visually and commit**

Run: `cd jmeter-working-dir/webapp && python -m webapp` — check sidebar and mobile nav look correct.

```bash
git add webapp/templates/base.html webapp/static/css/style.css
git commit -m "style(nav): replace Unicode icons with Lucide SVGs in sidebar and bottom nav"
```

---

### Task 4: Theme Toggle in Topbar

Add a sun/moon toggle button to the topbar. Remove theme selector from Settings General tab.

**Files:**
- Modify: `webapp/templates/base.html:49-52` (topbar section)
- Modify: `webapp/static/js/app.js:1-5` (theme init)
- Modify: `webapp/templates/settings.html` (remove theme select from General tab)

**Step 1: Add theme toggle button to topbar (base.html lines 49-52)**

After the page title `<h1>`, add a topbar actions area:

```html
<header class="topbar">
    <button class="menu-btn" id="menuBtn" onclick="toggleSidebar()">{{ icon('layers', 20) }}</button>
    <h1 class="page-title">{% block page_title %}Dashboard{% endblock %}</h1>
    <div class="topbar-actions">
        <button class="btn-icon" id="themeToggle" onclick="toggleTheme()" data-tooltip="Toggle theme">
            {{ icon('sun', 18) }}
            {{ icon('moon', 18) }}
        </button>
    </div>
</header>
```

**Step 2: Add `.topbar-actions` and theme toggle CSS**

```css
.topbar-actions { display: flex; align-items: center; gap: 8px; margin-left: auto; }
#themeToggle .icon:last-child { display: none; }
[data-theme="dark"] #themeToggle .icon:first-child { display: none; }
[data-theme="dark"] #themeToggle .icon:last-child { display: inline-block; }
```

**Step 3: Add `toggleTheme()` function to app.js**

Add after the theme IIFE (around line 5):

```javascript
function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
}
```

**Step 4: Remove theme from Settings General tab**

In `settings.html`, find the theme `<select>` in the General tab and remove that form group. Keep the `previewTheme()` function for now (it won't be called).

**Step 5: Verify and commit**

```bash
git add webapp/templates/base.html webapp/static/js/app.js webapp/static/css/style.css webapp/templates/settings.html
git commit -m "feat(ui): add theme toggle to topbar, remove from settings"
```

---

### Task 5: Styled Confirm Modal

Replace all `window.confirm()` calls with a styled in-app modal. This is a core UX improvement.

**Files:**
- Modify: `webapp/static/js/app.js:162-164` (replace `confirmAction`)
- Modify: `webapp/static/css/style.css` (add confirm modal styles)
- Modify: `webapp/templates/base.html` (add confirm modal HTML)
- Modify: 6 template files (update all 16 `confirmAction()` call sites)

**Step 1: Add confirm modal HTML to base.html**

Add before the toast container (before line 83):

```html
<!-- Confirm Modal -->
<div class="modal-overlay" id="confirmModal">
    <div class="modal" style="max-width:420px">
        <div class="modal-header">
            <h3 class="modal-title" id="confirmTitle">Confirm</h3>
            <button class="modal-close" onclick="closeConfirmModal(false)">&times;</button>
        </div>
        <div class="modal-body">
            <p id="confirmMessage"></p>
            <p class="text-sm text-secondary" id="confirmDetail"></p>
        </div>
        <div class="modal-footer">
            <button class="btn btn-outline" onclick="closeConfirmModal(false)">Cancel</button>
            <button class="btn" id="confirmBtn" onclick="closeConfirmModal(true)">Confirm</button>
        </div>
    </div>
</div>
```

**Step 2: Add `.modal-body` and `.modal-footer` CSS**

```css
.modal-body { padding: 16px 20px; }
.modal-footer { display: flex; gap: 8px; justify-content: flex-end; padding: 12px 20px; border-top: 1px solid var(--color-border); }
```

**Step 3: Replace `confirmAction` in app.js (lines 162-164)**

Replace the synchronous `window.confirm` wrapper with a Promise-based styled modal:

```javascript
let _confirmResolve = null;
function confirmAction(message, { title = 'Confirm', detail = '', danger = false } = {}) {
    return new Promise(resolve => {
        _confirmResolve = resolve;
        document.getElementById('confirmTitle').textContent = title;
        document.getElementById('confirmMessage').textContent = message;
        const detailEl = document.getElementById('confirmDetail');
        detailEl.textContent = detail;
        detailEl.style.display = detail ? 'block' : 'none';
        const btn = document.getElementById('confirmBtn');
        btn.className = danger ? 'btn btn-danger' : 'btn btn-primary';
        btn.textContent = danger ? 'Delete' : 'Confirm';
        openModal('confirmModal');
        btn.focus();
    });
}
function closeConfirmModal(result) {
    closeModal('confirmModal');
    if (_confirmResolve) { _confirmResolve(result); _confirmResolve = null; }
}
```

**Step 4: Update all 16 call sites to use async/await**

Since `confirmAction` now returns a Promise instead of a boolean, every call site needs `await`. The pattern changes from:

```javascript
// OLD (synchronous)
if (!confirmAction('Delete?')) return;
doDelete();
```

To:

```javascript
// NEW (async)
if (!await confirmAction('Delete?', { danger: true })) return;
doDelete();
```

**Call sites to update (16 total):**

In `results.html`:
- Line 360: Delete result — add `{ title: 'Delete Result', detail: folder, danger: true }`
- Line 457: Bulk regenerate — add `{ title: 'Regenerate Reports' }`
- Line 531: Bulk delete — add `{ title: 'Delete Results', danger: true }`

In `test_plans.html`:
- Line 401: Apply preset warning
- Line 487: Delete preset — add `{ danger: true }`
- Line 628: Delete filter preset — add `{ danger: true }`
- Line 692: JMeter GUI warning
- Line 711: Stop test — add `{ title: 'Stop Test', danger: true }`
- Line 1009: Delete test plan — add `{ title: 'Delete Test Plan', danger: true }`

In `slaves.html`:
- Line 438: Remove slaves (bulk) — add `{ danger: true }`
- Line 518: Remove slave — add `{ danger: true }`
- Line 623: Start servers
- Line 642: Stop servers — add `{ danger: true }`

In `settings.html`:
- Line 556: Restart server — add `{ title: 'Restart Server' }`

In `test_data.html`:
- Line 423: Overwrite file

In `scripts.html`:
- Line 76: Stop script — add `{ danger: true }`

**Important:** Each function containing a `confirmAction` call must be marked `async`. Check that the containing function signature is updated (e.g., `onclick="deleteResult(folder)"` where `deleteResult` becomes `async function deleteResult(folder)`).

**Step 5: Add keyboard support**

In app.js, add Escape key handler for the confirm modal:

```javascript
document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && document.getElementById('confirmModal').classList.contains('active')) {
        closeConfirmModal(false);
    }
    if (e.key === 'Enter' && document.getElementById('confirmModal').classList.contains('active')) {
        closeConfirmModal(true);
    }
});
```

**Step 6: Run tests and commit**

Run: `cd jmeter-working-dir/webapp && python -m pytest tests/ -x -q`

```bash
git add webapp/static/js/app.js webapp/static/css/style.css webapp/templates/base.html webapp/templates/results.html webapp/templates/test_plans.html webapp/templates/slaves.html webapp/templates/settings.html webapp/templates/test_data.html webapp/templates/scripts.html
git commit -m "feat(ux): replace window.confirm with styled async confirm modal across all pages"
```

---

### Task 6: Styled Prompt Modal

Replace all 4 `window.prompt()` calls with a styled in-app input modal.

**Files:**
- Modify: `webapp/static/js/app.js` (add `promptAction` function)
- Modify: `webapp/templates/base.html` (add prompt modal HTML)
- Modify: `webapp/templates/results.html:511` (set label)
- Modify: `webapp/templates/test_data.html:576` (save preset)
- Modify: `webapp/templates/slaves.html:496` (add slave)
- Modify: `webapp/templates/test_plans.html:1038` (rename plan)

**Step 1: Add prompt modal HTML to base.html**

Add after the confirm modal:

```html
<!-- Prompt Modal -->
<div class="modal-overlay" id="promptModal">
    <div class="modal" style="max-width:420px">
        <div class="modal-header">
            <h3 class="modal-title" id="promptTitle">Input</h3>
            <button class="modal-close" onclick="closePromptModal(null)">&times;</button>
        </div>
        <div class="modal-body">
            <p class="text-sm text-secondary mb-8" id="promptDesc"></p>
            <input type="text" class="form-input" id="promptInput" placeholder="">
            <p class="text-xs text-secondary mt-4" id="promptError" style="color:var(--color-danger);display:none"></p>
        </div>
        <div class="modal-footer">
            <button class="btn btn-outline" onclick="closePromptModal(null)">Cancel</button>
            <button class="btn btn-primary" id="promptBtn" onclick="submitPromptModal()">OK</button>
        </div>
    </div>
</div>
```

**Step 2: Add `promptAction` to app.js**

```javascript
let _promptResolve = null;
let _promptValidate = null;
function promptAction(title, { placeholder = '', defaultValue = '', description = '', validate = null } = {}) {
    return new Promise(resolve => {
        _promptResolve = resolve;
        _promptValidate = validate;
        document.getElementById('promptTitle').textContent = title;
        document.getElementById('promptDesc').textContent = description;
        document.getElementById('promptDesc').style.display = description ? 'block' : 'none';
        const input = document.getElementById('promptInput');
        input.placeholder = placeholder;
        input.value = defaultValue;
        document.getElementById('promptError').style.display = 'none';
        openModal('promptModal');
        input.focus();
        input.select();
    });
}
function submitPromptModal() {
    const value = document.getElementById('promptInput').value.trim();
    if (_promptValidate) {
        const err = _promptValidate(value);
        if (err) {
            const errEl = document.getElementById('promptError');
            errEl.textContent = err;
            errEl.style.display = 'block';
            return;
        }
    }
    closeModal('promptModal');
    if (_promptResolve) { _promptResolve(value); _promptResolve = null; }
}
function closePromptModal(value) {
    closeModal('promptModal');
    if (_promptResolve) { _promptResolve(value); _promptResolve = null; }
}
```

Add Enter key support in the prompt input:

```javascript
document.getElementById('promptInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') submitPromptModal();
    if (e.key === 'Escape') closePromptModal(null);
});
```

**Step 3: Update 4 call sites**

`results.html:511` — Set label:
```javascript
// OLD: const label = prompt('Set label for ' + folder + ' (leave empty to clear):', currentLabel);
const label = await promptAction('Set Label', { placeholder: 'e.g. Baseline 15k users', defaultValue: currentLabel, description: 'Label for ' + folder });
if (label === null) return;
```

`test_data.html:576` — Save preset:
```javascript
// OLD: const name = prompt('Preset name:');
const name = await promptAction('Save Preset', { placeholder: 'e.g. Student Login Data', validate: v => v ? null : 'Name is required' });
if (!name) return;
```

`slaves.html:496` — Add slave:
```javascript
// OLD: const ip = prompt('Enter slave IP address:');
const ip = await promptAction('Add Slave', { placeholder: '10.0.0.1 or 100.64.1.2', description: 'Enter the slave VM IP address', validate: v => v && /^[\d.]+$/.test(v) ? null : 'Enter a valid IP address' });
if (!ip) return;
```

`test_plans.html:1038` — Rename:
```javascript
// OLD: const newName = prompt('Rename test plan:', stem);
const newName = await promptAction('Rename Test Plan', { defaultValue: stem, validate: v => v && v !== stem ? null : 'Enter a new name' });
if (!newName) return;
```

**Step 4: Run tests and commit**

```bash
git add webapp/static/js/app.js webapp/templates/base.html webapp/templates/results.html webapp/templates/test_data.html webapp/templates/slaves.html webapp/templates/test_plans.html
git commit -m "feat(ux): replace window.prompt with styled input modal with validation"
```

---

### Task 7: Loading Skeletons & Empty States

Add skeleton loading placeholders and empty state components.

**Files:**
- Modify: `webapp/static/css/style.css` (add skeleton and empty-state classes)
- Modify: `webapp/templates/base.html` (optional — empty state partial)
- Modify: `webapp/templates/results.html` (add loading skeleton + empty state)
- Modify: `webapp/templates/slaves.html` (add empty state)
- Modify: `webapp/templates/dashboard.html` (loading skeleton for cards)

**Step 1: Add skeleton CSS**

```css
/* ===== Loading Skeletons ===== */
.skeleton { background: var(--color-surface-alt); border-radius: var(--radius-sm); animation: shimmer 1.5s infinite; }
.skeleton-text { height: 14px; margin-bottom: 8px; border-radius: var(--radius-sm); }
.skeleton-text:last-child { width: 60%; }
.skeleton-card { height: 120px; border-radius: var(--radius-lg); }
.skeleton-row { height: 44px; border-radius: var(--radius-sm); margin-bottom: 4px; }
@keyframes shimmer {
    0% { opacity: 0.6; }
    50% { opacity: 0.3; }
    100% { opacity: 0.6; }
}
```

**Step 2: Add empty state CSS**

```css
/* ===== Empty States ===== */
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 48px 24px; text-align: center; }
.empty-state .icon { color: var(--color-text-tertiary); margin-bottom: 16px; }
.empty-state-title { font-size: 1.1rem; font-weight: 600; color: var(--color-text); margin-bottom: 8px; }
.empty-state-desc { font-size: 0.875rem; color: var(--color-text-secondary); margin-bottom: 20px; max-width: 320px; }
```

**Step 3: Add loading skeleton to results.html**

Show skeleton rows while results are being fetched, then swap in the real table or empty state.

**Step 4: Add empty state to results.html**

```html
<div class="empty-state" id="resultsEmpty" style="display:none">
    {{ icon('bar-chart-3', 48) }}
    <div class="empty-state-title">No test results yet</div>
    <div class="empty-state-desc">Run a test from the Test Plans page to see results here.</div>
    <a href="{{ base_path }}/plans" class="btn btn-primary">Go to Test Plans</a>
</div>
```

**Step 5: Add empty state to slaves.html**

```html
<div class="empty-state" id="slavesEmpty" style="display:none">
    {{ icon('server', 48) }}
    <div class="empty-state-title">No slave VMs configured</div>
    <div class="empty-state-desc">Add a slave VM to start distributed testing.</div>
    <button class="btn btn-primary" onclick="addSlave()">Add Slave</button>
</div>
```

**Step 6: Add empty states to dashboard, test_data, test_plans**

Similar pattern for each — icon + title + description + action button. Wire visibility to the data loading logic already in each template's JS.

**Step 7: Run tests and commit**

```bash
git add webapp/static/css/style.css webapp/templates/results.html webapp/templates/slaves.html webapp/templates/dashboard.html webapp/templates/test_data.html webapp/templates/test_plans.html
git commit -m "feat(ux): add loading skeletons and empty states for all data pages"
```

---

### Task 8: Dropdown Menu Component

Add a reusable dropdown menu for action overflow. Used primarily on the Results page.

**Files:**
- Modify: `webapp/static/css/style.css` (dropdown styles)
- Modify: `webapp/static/js/app.js` (dropdown toggle logic)

**Step 1: Add dropdown CSS**

```css
/* ===== Dropdown Menu ===== */
.dropdown { position: relative; display: inline-block; }
.dropdown-menu { position: absolute; right: 0; top: 100%; margin-top: 4px; min-width: 160px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius); box-shadow: var(--shadow-lg); z-index: 50; display: none; padding: 4px 0; }
.dropdown-menu.open { display: block; }
.dropdown-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px; font-size: 0.8125rem; color: var(--color-text); cursor: pointer; white-space: nowrap; border: none; background: none; width: 100%; text-align: left; }
.dropdown-item:hover { background: var(--color-surface-hover); }
.dropdown-item.danger { color: var(--color-danger); }
.dropdown-item.danger:hover { background: var(--color-danger-subtle); }
.dropdown-divider { height: 1px; margin: 4px 0; background: var(--color-border); }
```

**Step 2: Add dropdown JS to app.js**

```javascript
function toggleDropdown(btn) {
    const menu = btn.nextElementSibling;
    const wasOpen = menu.classList.contains('open');
    // Close all open dropdowns first
    document.querySelectorAll('.dropdown-menu.open').forEach(m => m.classList.remove('open'));
    if (!wasOpen) menu.classList.add('open');
}
// Close dropdowns on outside click
document.addEventListener('click', e => {
    if (!e.target.closest('.dropdown')) {
        document.querySelectorAll('.dropdown-menu.open').forEach(m => m.classList.remove('open'));
    }
});
```

**Step 3: Verify and commit**

```bash
git add webapp/static/css/style.css webapp/static/js/app.js
git commit -m "feat(ui): add reusable dropdown menu component"
```

---

### Task 9: Tooltip Component

Add CSS-only tooltips for icon buttons and keyboard shortcuts.

**Files:**
- Modify: `webapp/static/css/style.css`

**Step 1: Add tooltip CSS**

```css
/* ===== Tooltips ===== */
[data-tooltip] { position: relative; }
[data-tooltip]::after { content: attr(data-tooltip); position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%); padding: 4px 8px; font-size: 0.75rem; font-weight: 500; color: #fff; background: #1e293b; border-radius: var(--radius-sm); white-space: nowrap; pointer-events: none; opacity: 0; transition: opacity 0.15s; z-index: 100; margin-bottom: 6px; }
[data-tooltip]:hover::after { opacity: 1; }
[data-theme="dark"] [data-tooltip]::after { background: #e2e8f0; color: #0f172a; }
```

**Step 2: Commit**

```bash
git add webapp/static/css/style.css
git commit -m "feat(ui): add CSS-only tooltip component"
```

---

**Phase 1 checkpoint:** At this point the design system is complete — tokens, icons, confirm/prompt modals, skeletons, empty states, dropdowns, tooltips. Run the full test suite and verify visually before moving to Phase 2.

```bash
cd jmeter-working-dir/webapp && python -m pytest tests/ -v --tb=short
```

---

## Phase 2: Page-by-Page UX + Polish

### Task 10: Dashboard Polish

**Files:**
- Modify: `webapp/templates/dashboard.html` (replace inline grids, add icons, empty state)
- Modify: `webapp/static/css/style.css` (dashboard-specific refinements)

**Changes:**
1. Replace all inline `grid-template-columns` with `.grid-2`, `.grid-3`, `.grid-1-2-1` utility classes
2. Give Runner Status card visual prominence — slightly larger, primary accent border-top
3. Alert items: add Lucide icons (`alert-triangle`, `info`) and color-coded left border
4. Monitoring cards: convert from inline styles to `.card` + `.surface-card`
5. Add empty state for "No test runs yet" in the run history section
6. Replace inline stat card styles with classes
7. Add Lucide icons to Quick Actions buttons (`play`, `refresh-cw`, `folder-open`)

**Commit:**
```bash
git commit -m "style(dashboard): replace inline styles with grid utilities, add icons and empty state"
```

---

### Task 11: Test Plans & Runner Polish

**Files:**
- Modify: `webapp/templates/test_plans.html`
- Modify: `webapp/static/css/style.css`

**Changes:**
1. Command preview: styled code block with dark bg, monospace, copy button with `{{ icon('copy', 14) }}`
2. Add `data-tooltip="Ctrl+Enter"` to the Run button
3. Live execution stat cards: subtle colored tint backgrounds using `--color-*-subtle` tokens (green for throughput, blue for samples, red for errors)
4. Replace inline styles with spacing/grid utilities
5. Add Lucide icons to action buttons (play, stop-circle, trash-2, copy, download, edit-2, file-text)
6. Presets section: cleaner layout
7. Test plans table: add Lucide icons to action column buttons

**Commit:**
```bash
git commit -m "style(plans): add code preview styling, stat card tints, Lucide icons, remove inline styles"
```

---

### Task 12: Results Page — Action Overflow Dropdown + Polish

**Files:**
- Modify: `webapp/templates/results.html`
- Modify: `webapp/static/css/style.css`

**Changes:**
1. **Action buttons → dropdown**: Keep "Stats" toggle and "Report" link visible. Move Download, Regenerate, Open, Delete into a `...` dropdown menu using the component from Task 8
2. Delete confirmation: use the styled confirm modal with context detail (folder name + size)
3. Stats preview: use `.surface-card` with consistent padding
4. Compare table: add green/red background tint for better/worse values
5. Sortable column headers: add `{{ icon('chevron-down', 14) }}` indicator
6. Add loading skeleton rows and empty state from Task 7
7. Replace remaining inline styles with utilities

**Commit:**
```bash
git commit -m "style(results): action dropdown, contextual delete, loading states, remove inline styles"
```

---

### Task 13: Test Data Polish

**Files:**
- Modify: `webapp/templates/test_data.html`

**Changes:**
1. Preset sidebar: hover state now works (fixed `--color-bg-secondary` in Task 1)
2. Preview table: zebra striping via `tr:nth-child(even)` scoped to preview, `.text-mono` on values
3. Column type selector: add small Lucide icon per type in the dropdown options
4. Distribute section: add progress indicator using existing toast or a small inline spinner
5. Replace inline styles with spacing utilities
6. Add empty state for "No CSV files" in the file list

**Commit:**
```bash
git commit -m "style(data): preset hover fix, zebra preview, distribute progress, remove inline styles"
```

---

### Task 14: Fleet Page Polish

**Files:**
- Modify: `webapp/templates/slaves.html`

**Changes:**
1. **Gear button**: change from `opacity: 0.4` to always-visible `{{ icon('settings', 16) }}` with normal opacity
2. **Add slave**: already uses styled prompt modal from Task 6
3. **Config panel accordion**: add `{{ icon('chevron-right', 14) }}` / `{{ icon('chevron-down', 14) }}` toggle indicator
4. **Status dots**: add text label ("Online" / "Offline" / "Checking") next to each dot
5. **Bulk action bar**: style as a sticky bottom bar when items are selected, with count badge
6. **View toggle**: add Lucide icons (`layers` for list, `hard-drive` for grid)
7. Add empty state from Task 7
8. Replace inline styles with spacing utilities

**Commit:**
```bash
git commit -m "style(fleet): visible config toggle, status labels, sticky bulk bar, remove inline styles"
```

---

### Task 15: Settings Page — Single Save + Polish

**Files:**
- Modify: `webapp/templates/settings.html`
- Modify: `webapp/routers/settings.py` (if save endpoints need consolidation)

**Changes:**
1. **Single Save flow**: Remove the separate "Save Report Settings" button. Keep one "Save" button in a sticky footer bar at the bottom of the card. This button saves ALL settings (general + report + integrations).
2. **Unsaved changes indicator**: Add a small dot on the tab label when that tab has unsaved changes. JS tracks changes via `input`/`change` events on form fields.
3. **System info cards**: replace inline-styled cards with `.surface-card` class
4. **Tab icons**: Add Lucide icons to each tab button (settings, folder-open, bar-chart-3, zap, terminal, hard-drive)
5. Remove theme selector from General tab (moved to topbar in Task 4)
6. Replace inline styles with spacing utilities

**Commit:**
```bash
git commit -m "style(settings): single save flow, unsaved indicator, system cards, remove inline styles"
```

---

### Task 16: Final Consistency Pass

**Files:**
- All templates
- `webapp/static/css/style.css`

**Changes:**
1. Audit remaining inline `style=""` attributes — convert to utility classes or scoped CSS
2. Fix `.btn-close` class (add to style.css or change to `.modal-close` in templates)
3. Verify all modals use `.modal-footer` instead of inline styles
4. Check dark mode on every page — ensure no unstyled elements
5. Verify mobile layout (768px) on every page
6. Test all confirm/prompt modals work correctly with async/await
7. Run the full test suite

**Commit:**
```bash
git commit -m "style: final consistency pass — inline styles, modal footers, dark mode audit"
```

---

### Task 17: Update CLAUDE.md and PHASE_PLAN.md

**Files:**
- Modify: `webapp/CLAUDE.md`
- Modify: `webapp/PHASE_PLAN.md`

**Changes:**
1. Update CLAUDE.md:
   - Document the Lucide icon system (`templates/icons.html`, `{{ icon('name', size) }}` macro)
   - Document new interaction components (confirmAction, promptAction — both async/Promise-based)
   - Update component library table (add dropdown, tooltip, skeleton, empty-state)
   - Document CSS utility classes (typography, spacing, grid)
   - Note the theme toggle is in the topbar

2. Update PHASE_PLAN.md:
   - Mark UI/UX redesign phase as complete
   - Note what was done in each task

**Commit:**
```bash
git commit -m "docs: update CLAUDE.md and PHASE_PLAN.md with UI/UX redesign changes"
```
