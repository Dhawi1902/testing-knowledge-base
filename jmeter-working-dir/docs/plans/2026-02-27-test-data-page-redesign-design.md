# Test Data Page — Redesign Design

**Date**: 2026-02-27
**Status**: Approved

## Overview

Redesign the Test Data page to match the polished visual style of the already-redesigned Dashboard, Test Plans, and Results pages. Adds stat summaries, template cards, full-width table, improved empty states, and mobile responsive card layout.

## Design Decisions

| Decision | Choice |
|---|---|
| CSV Files stat strip | Yes — 4 mini stat cards (files, rows, size, columns) |
| Template sidebar | Cards with preview info (col count, type hint) |
| Distribute section | Inline with visual upgrade (icon header, empty state, badges) |
| Table actions | Keep visible buttons (Preview, Download, Delete) |
| Table layout | Full-width `table-layout: fixed` with column widths |
| Mobile | Card list for CSV table, stacked builder, same pattern as Results |

## Section 1: CSV Files

### Card Header
- Left: `{{ icon('database', 16) }} CSV Files`
- Right: file count badge + Upload button + Refresh button

### Stat Strip
4 mini stat cards computed client-side from loaded file data:
- **Total Files** — count
- **Total Rows** — sum of all file rows, formatted
- **Total Size** — sum of all file sizes, formatted
- **Columns** — count of unique column names across files

### Table
- `table-layout: fixed; width: 100%`
- `.col-file` — remaining space (flex)
- `.col-columns` — ~200px
- `.col-rows` — ~100px
- `.col-size` — ~100px
- `.col-actions` — ~250px
- File name: monospace, `overflow: hidden; text-overflow: ellipsis`
- Column badges: keep existing color-coding
- Action buttons: `btn btn-outline btn-sm` with 14px icons

### Empty State
Database icon (48px) + "No CSV files yet — upload or generate one below"

## Section 2: CSV Builder

### Card Header
- Left: `{{ icon('wrench', 16) }} CSV Builder`
- Right: active template name as badge (when selected)

### Template Sidebar
Each template becomes a card:
- Name (bold)
- Subtitle: column count + primary type (e.g., "1 col · Sequential ID")
- Active: left border highlight (primary color) + subtle background tint
- `+ Create new`: dashed-border card at top
- Custom presets: small delete icon on hover

### Builder Main Area
- Form inputs: `form-input` and `form-label` utility classes
- Column definitions: subtle border + padding per column block
- Action buttons: consistent `btn btn-outline btn-sm` / `btn btn-primary btn-sm`

## Section 3: Distribute to Slaves

### Card Header
- Left: `{{ icon('share-2', 16) }} Distribute to Slaves`
- Right: queued file count badge

### Empty State
Share icon (48px) + "No files queued — click Add file to start"

### Distribution Items
- Each item: styled row with file selector + mode toggle + remove button
- Split params appear inline when split mode selected

### Action Bar
Add File, Preview, Distribute buttons with icons matching global button patterns.

## Section 4: Mobile Responsive (< 768px)

- **CSV Files table** → card list (filename, column badges, size, 3-dot dropdown for actions)
- **CSV Builder** → template sidebar stacks full-width above builder
- **Distribute** → already card-like, tighten spacing
- **Stat strip** → 2x2 grid instead of 4-across

## Files to Modify

1. `jmeter-working-dir/webapp/templates/data.html` — HTML structure, JS rendering
2. `jmeter-working-dir/webapp/static/css/style.css` — Table widths, card styles, mobile rules
