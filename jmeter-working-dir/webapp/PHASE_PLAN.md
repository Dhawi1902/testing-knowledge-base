# Webapp Improvement Phases

Compact reference for remaining EVALUATION.md items. All priority items 1-7 are DONE.

---

## Phase A — Medium Priority Fixes (security/robustness)

| # | Item | File | Detail |
|---|------|------|--------|
| A1 | Race condition on regeneration | results.py:37 | Module-level `_active_regen` global. Concurrent requests overwrite process ref. Use asyncio.Lock or per-folder tracking. |
| A2 | Streaming upload size check | test_data.py:138-139 | `await file.read()` loads entire file before 100MB check. Read in chunks instead. |
| A3 | Upload size limit in test_plans | test_plans.py:250 | Same issue as A2 — no size check at all. |
| A4 | Auth on slave status endpoint | config.py:141 | `api_slave_status` triggers SSH to all slaves with no `_check_access`. Add auth. |

## Phase B — Low Priority Code Quality

| # | Item | File | Detail |
|---|------|------|--------|
| B1 | Unused `import pandas` | slaves.py:5 | Move to lazy import inside `_distribute_items`. |
| B2 | Duplicate SSH client creation (3x) | slaves.py:36,54,123 | Extract `_ssh_connect(host, config)` helper. |
| B3 | Repeated slave loading pattern (4x) | config.py:91,146,177,196 | Extract `_get_slaves(project)` helper. |
| B4 | Zip logic duplicated | results.py:328-339 vs 404-417 | Reuse `_zip_report_to_file` in bundle endpoint. |
| B5 | `preview_csv` reads file twice | data.py:40-43 | Single pandas read, get count from DataFrame. |
| B6 | SSH error messages leak `str(e)` | slaves.py:48,70,145 | Generic messages (or keep for admin diagnostic). |
| B7 | No IP validation in `addSlave()` | slaves.html:348-356 | Basic regex validation on IP/hostname format. |
| B8 | No validation on settings save | settings.py:103-105 | Validate port range, URL format, paths before saving. |
| B9 | System info no auth check | settings.py:117 | Exposes OS/Java/Python versions to anyone. |

## Phase C — Inline Styles → CSS Classes

| Pattern | Occurrences | Class |
|---------|-------------|-------|
| `display:flex;gap:16px;flex-wrap:wrap;` | ~20+ | `.form-row` |
| `flex:1;min-width:200px;` | ~15+ | `.form-col` |
| `padding:12px;background:surface;border;border-radius:8px;` | ~8 | `.surface-card` |
| `font-weight:600;` on h3 section headers | ~12 | `.section-title` |

Pages affected: settings.html, test_data.html, slaves.html, test_plans.html, results.html, dashboard.html

## Phase D — Missing Features (quick wins)

| # | Item | File | Complexity |
|---|------|------|------------|
| D1 | Delete test plan button | test_plans.py/html | Low |
| D2 | Sort results by column | results.html | Low |
| D3 | Analysis badge in results list | results.html | Low |
| D4 | Show JTL files per result | results.html, jtl_parser.py | Low |
| D5 | "Include JTL" checkbox in download | results.html, results.py | Low |
| D6 | Settings export/import | settings.py/html | Low |
| D7 | Settings validation | settings.py | Low |
| D8 | Auto slave status check on page load | slaves.html | Low |
| D9 | Slave nickname | slaves.html, slaves.py | Low |

## Phase E — Dashboard Tier 2

| # | Item | Detail | Complexity |
|---|------|--------|------------|
| E1 | Trend chart | Sparkline of avg RT across last 10 runs | Medium |
| E2 | Slave health dots | Green/red per slave from last status check | Medium |
| E3 | Alerts/warnings | "Disk > 90%", "Slave down", "Results with no report" | Medium |

## Phase F — Future Features (larger scope)

| # | Item | Complexity |
|---|------|------------|
| F1 | Windows slave support (OS flag + platform commands) | Medium |
| F2 | JMeter properties management via webapp | Medium |
| F3 | Push properties to slaves via SSH | Medium |
| F4 | Backend listener override properties | High |
| F5 | Self-contained start/stop (build commands from config) | Medium |
| F6 | Per-VM JMeter paths | Low |
| F7 | SSH key authentication | Low |
| F8 | Individual slave start/stop | Medium |
| F9 | Filter gap (independent sub-result removal vs label regex) | Medium |
| F10 | Stats preview (expandable rows in results) | Medium |
| F11 | Bulk regenerate | Medium |

## Phase G — Project-Level

| # | Item | Detail |
|---|------|--------|
| G1 | Server-side logging | Python `logging` with rotation for audit trail |
| G2 | API docs | Expose FastAPI `/docs` behind base_path |
| G3 | README for webapp | Setup instructions, architecture, config reference |
| G4 | Mobile UX audit | Check all pages beyond test_plans |
| G5 | Accessibility audit | Keyboard nav, screen reader, focus management |

---

## Status

| Phase | Status | Tests |
|-------|--------|-------|
| Priority 1-3 (Security, Bugs, Dead code) | DONE | 124 passing |
| Priority 4 (Tests) | DONE | 124 tests across 8 files |
| Priority 5 (Setup wizard) | DONE | — |
| Priority 6 (Cross-cutting cleanup) | DONE | — |
| Priority 7 (Dashboard Tier 1) | DONE | +15 dashboard tests |
| Phase A (Medium fixes) | DONE | 124 passing |
| Phase B (Code quality) | DONE | 124 passing |
| Phase C (Inline styles) | DONE | 124 passing |
| Phase D (Quick features) | DONE | 124 passing |
| Phase E (Dashboard Tier 2) | DONE | 129 passing |
| Phase F (Future features) | DONE | 137 passing |
| Phase G (Project-level) | DONE | 137 passing |
