# UI/UX Redesign — Design Document

**Date:** 2026-02-26
**Goal:** Transform the JMeter Test Dashboard from functional to professional, targeting a "Linear meets Vercel" aesthetic — clean, dark-mode-first developer tool with modern SaaS spacing and polish.

**Constraints:**
- No framework switch — stays vanilla HTML/CSS/JS with Jinja2 templates
- No build step — Lucide icons are inline SVGs, not npm imports
- Backend untouched — all changes are templates, CSS, and JS
- Mobile responsive behavior preserved

---

## Current State Summary

The webapp has solid functional bones (928-line CSS, 239-line app.js, 6 pages) but several issues undermine professionalism:

**UI Issues:**
- Unicode nav icons (snowman for Fleet, duplicate hamburger) — inconsistent and amateurish
- No typography scale — all headings use `.card-title` or inline bold
- ~97 inline `style=""` blocks — no spacing utilities beyond `mb-8/16/24`
- Missing CSS classes: `--color-bg-secondary` undefined, `.btn-close` unstyled, no `.modal-footer`
- Theme toggle buried in Settings > General tab

**UX Issues:**
- `window.confirm()` used 20+ times — unstyled, no context preview, breaks dark theme
- `window.prompt()` used 4 times — no validation, no feedback
- No loading/skeleton states — pages flash empty then populate
- No empty states — blank page when lists are empty
- Results page: 5 equal-weight action buttons per row, cognitive overload
- Fleet: gear button at `opacity: 0.4` — users can't discover per-slave config
- Settings: two Save buttons with unclear scope
- Dashboard: everything has equal visual weight, no information hierarchy

---

## Phase 1: Design System + Interaction Patterns

### 1.1 Color Palette Refinement

Keep primary blue (`#3b82f6`). Refine supporting tokens:

| Token | Light | Dark | Notes |
|-------|-------|------|-------|
| `--color-bg` | `#f8fafc` | `#0c1222` | Cooler, deeper dark |
| `--color-surface` | `#ffffff` | `#1a2332` | Clean white / lifted dark |
| `--color-surface-alt` | `#f1f5f9` | `#162032` | Subtle differentiation |
| `--color-surface-hover` | `#e2e8f0` | `#243044` | **New** — row/card hover |
| `--color-border` | `#e2e8f0` | `#1e3048` | Subtler dark borders |
| `--color-text` | `#0f172a` | `#e2e8f0` | Bolder light text |
| `--color-text-secondary` | `#64748b` | `#8b9bb5` | Rename from `text-light` |
| `--color-text-tertiary` | `#94a3b8` | `#5a6a80` | **New** — timestamps, placeholders |
| `--color-bg-secondary` | `#f1f5f9` | `#162032` | **New** — fixes broken preset hover |

### 1.2 Typography Scale

Named classes replacing all ad-hoc font sizes:

```
.text-2xl    1.5rem / 700    Page titles (topbar)
.text-xl     1.25rem / 600   Card headers
.text-lg     1.05rem / 600   Section titles within cards
.text-base   0.875rem / 400  Body text (14px base)
.text-sm     0.8125rem / 400 Labels, metadata
.text-xs     0.75rem / 400   Badges, timestamps
.text-mono   Consolas        IPs, paths, commands, stat values
```

Font stack unchanged — system fonts are correct for a developer tool.

### 1.3 Spacing Scale

Utility classes for margin, padding, and gap on a 4px grid:

```
4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48
```

Generated as `.m-{n}`, `.mt-{n}`, `.mb-{n}`, `.ml-{n}`, `.mr-{n}`, `.p-{n}`, `.pt-{n}`, `.pb-{n}`, `.pl-{n}`, `.pr-{n}`, `.gap-{n}`.

This eliminates the ~97 inline style blocks.

### 1.4 Border Radius

Tighten for a sharper, more professional feel:

```
--radius-sm:  4px   Inputs, badges, small elements
--radius:     6px   Buttons, dropdowns
--radius-lg:  8px   Cards, modals
--radius-xl:  12px  Large containers (rare)
```

### 1.5 Lucide Icons

Replace all Unicode characters with Lucide inline SVGs:

**Navigation (18px):**
| Page | Icon |
|------|------|
| Dashboard | `LayoutDashboard` |
| Test Plans & Runner | `Play` |
| Results | `BarChart3` |
| Test Data | `Database` |
| Fleet | `Server` |
| Settings | `Settings` |

**Inline icons (16px):** `Trash2`, `Plus`, `Download`, `RefreshCw`, `Upload`, `Copy`, `ExternalLink`, `ChevronDown`, `ChevronRight`, `X`, `Check`, `AlertTriangle`, `Info`, `Search`, `Edit2`, `MoreHorizontal`, `Eye`, `EyeOff`, `Sun`, `Moon`, `Terminal`, `FolderOpen`, `FileText`, `Zap`, `Activity`

**Status indicators (14px):** `Circle` (filled/stroke for online/offline), `Loader2` (spinning for checking)

Implementation: Create a `icons.html` Jinja2 partial with SVG macros. Templates call `{% include 'icons.html' %}` and use `{{ icon('play', 18) }}`.

### 1.6 Core Interaction Components

**Styled Confirm Modal**
- Replaces all 20+ `window.confirm()` calls
- Shows context: "Delete result folder `20260225_3`? (245 MB, contains report)"
- Danger-colored action button for destructive actions
- Keyboard: Enter confirms, Escape cancels
- JS API: `confirmAction(message, detail, onConfirm, { danger: true })`

**Inline Prompt Modal**
- Replaces all 4 `window.prompt()` calls
- Input with placeholder, validation, auto-focus
- Focus trap within modal
- JS API: `promptAction(title, placeholder, onSubmit, { validate: fn })`

**`.modal-footer` CSS Class**
- Standardized flex layout: `display:flex; gap:8px; justify-content:flex-end; padding:12px 16px; border-top`
- Replaces all inline-styled modal footers

**Theme Toggle (Topbar)**
- Sun/Moon Lucide icon button in topbar right area
- Instant theme switch with localStorage persistence
- Removed from Settings General tab

**Loading Skeletons**
- Pulsing placeholder blocks (`.skeleton`, `.skeleton-text`, `.skeleton-card`)
- Applied to card bodies and table rows during async loads
- CSS-only animation: `@keyframes pulse` on `background-color`

**Empty States**
- Centered layout: Lucide icon (48px, muted) + heading + description + action button
- Per-page variants: "No test results yet — run your first test", "No slaves configured — add a slave VM", etc.
- CSS class: `.empty-state`, `.empty-state-icon`, `.empty-state-title`, `.empty-state-desc`

**Tooltip Component**
- CSS-only tooltips via `data-tooltip` attribute
- Positioned above by default, auto-flip
- Used for icon-only buttons and keyboard shortcut hints

**Dropdown Menu**
- Click-triggered dropdown for action overflow
- `.dropdown`, `.dropdown-trigger`, `.dropdown-menu`, `.dropdown-item`
- Click outside or Escape to close
- Used on Results page action column and wherever buttons overflow

---

## Phase 2: Page-by-Page UX + Polish

### 2.1 Dashboard (`/`)

| Issue | Fix |
|-------|-----|
| Everything has equal visual weight | Runner Status card gets larger placement, top-left. Alerts get color-coded left border accent. |
| Inline grid layouts everywhere | Replace with named CSS grid classes (`.grid-2`, `.grid-3`, `.grid-1-2-1`) |
| Monitoring cards outside `.card` system | Bring into standard card component |
| No empty state | "No test runs yet" with link to Test Plans page |
| Runner status table hardcoded widths | Flex layout with proper responsive behavior |

### 2.2 Test Plans & Runner (`/plans`)

| Issue | Fix |
|-------|-----|
| Parameter form dense | Cleaner input groups, subtle section dividers between param categories |
| Command preview plain text | Proper code block: monospace, dark bg, copy button |
| Live stats during run | Stat cards get subtle background tint per metric type (green for throughput, blue for samples, red for errors) |
| No shortcut hint | Show "Ctrl+Enter" tooltip on Run button |
| Presets in tab panel | Styled dropdown selector or compact pill list |

### 2.3 Results (`/results`)

| Issue | Fix |
|-------|-----|
| 5 action buttons per row | Keep "Stats" and "Report" visible. Rest goes into 3-dot `MoreHorizontal` dropdown menu |
| Delete confirmation has no context | Styled confirm modal: shows folder name, size, whether report exists |
| Stats preview inconsistent spacing | Clean mini-cards with `.surface-card` and consistent padding |
| Compare UI flat | Side-by-side table with green/red colored cells for better/worse metrics |
| No empty state | "No results yet — run a test from the Test Plans page" |

### 2.4 Test Data (`/data`)

| Issue | Fix |
|-------|-----|
| Preset hover broken (`--color-bg-secondary` undefined) | Fixed by new token |
| Column type as plain dropdown | Icon + label pills or segmented control |
| Preview table plain | Zebra striping, monospace values, `.text-mono` class |
| No feedback during distribute | Progress indicator / toast during upload to slaves |

### 2.5 Fleet (`/slaves`)

| Issue | Fix |
|-------|-----|
| Gear button `opacity: 0.4` | Always-visible `Settings` Lucide icon, normal opacity |
| Add slave via `window.prompt()` | Proper modal: IP input with validation, optional nickname field |
| Config panel hard to see | Accordion with `ChevronRight`/`ChevronDown` indicator, subtle background |
| Status dots alone | Add text label: "Online" / "Offline" / "Checking" next to dot |
| Bulk action bar unstyled | Sticky bottom bar when items selected, with count badge and styled buttons |

### 2.6 Settings (`/settings`)

| Issue | Fix |
|-------|-----|
| Two Save buttons with unclear scope | Single "Save" in sticky footer bar. Unsaved-changes dot indicator on modified tab labels. |
| Theme in General tab | Removed — now topbar toggle. General tab space reclaimed. |
| System info cards inline-styled | Brought into `.card` / `.surface-card` system |
| JMeter properties search | Highlight matching rows on search input |

---

## What's NOT Changing

- No framework switch (stays vanilla HTML/CSS/JS)
- No build step (Lucide SVGs are pasted inline, not imported)
- No backend changes
- No new dependencies
- Mobile responsive breakpoints stay at 768px and 480px
- WebSocket live execution architecture unchanged
- Access control model unchanged
- All existing functionality preserved
