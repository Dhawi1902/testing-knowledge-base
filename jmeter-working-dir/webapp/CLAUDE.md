# CLAUDE.md — JMeter Test Dashboard Web App

This file provides guidance to Claude Code when working on the web app.

## Overview

A self-contained web dashboard for managing JMeter performance test projects. The app is deployed **per-project** — it lives inside the project directory and operates on the files around it. No database; everything is file-based.

## Architecture

- **Backend**: FastAPI (Python) with async handlers
- **Frontend**: Vanilla HTML/CSS/JS with Jinja2 templates, no framework
- **No database** — reads/writes project files directly (configs, CSVs, JTLs, JMX)
- **WebSocket** — live log streaming during test execution with real-time stats parsing
- **Process management** — JMeter, Python scripts, batch files run as subprocesses
- **Access control** — token-based auth for remote users, localhost gets full access
- **PNC compliance** — all data stays local, optional Ollama AI runs on-premise

## Directory Structure

```
webapp/
├── main.py                  # FastAPI app, auth middleware, first-run redirect
├── __main__.py              # Entry point: python -m webapp
├── requirements.txt         # Python dependencies
├── project.json             # Project-specific config (auto-generated on first run)
├── settings.json            # App settings (auto-generated on first save)
├── presets.json             # Saved test parameter presets
├── jtl_filter.py            # JTL filter script (sub-results, variables, regex)
├── routers/
│   ├── dashboard.py         # GET / — overview stats, runner status, quick actions
│   ├── config.py            # GET /slaves page, VM config CRUD, slave enable/disable
│   ├── test_data.py         # CSV builder, generate, split, distribute, preview
│   ├── test_plans.py        # JMX selector, params, presets, test execution, WebSocket logs
│   ├── results.py           # Browse results, reports, regenerate, compare, download
│   ├── scripts.py           # Discover and run .py/.bat (localhost only)
│   └── settings.py          # App settings CRUD, system info, server restart
├── services/
│   ├── jmeter.py            # Build JMeter commands, REPORT_OPTIMIZE_PROPS, parse JMX
│   ├── slaves.py            # SSH operations (start/stop/status, paramiko)
│   ├── data.py              # CSV generation (5 column types), split, distribute
│   ├── config_parser.py     # Read/write config.properties, vm_config, slaves (JSON format)
│   ├── jtl_parser.py        # Parse JTL files for summary stats
│   ├── analysis.py          # Rule-based analysis + optional Ollama AI
│   └── process_manager.py   # Subprocess runner with WebSocket output streaming
├── prompts/
│   └── analysis.txt         # Ollama prompt template
├── static/
│   ├── css/style.css        # Complete design system (light/dark themes, responsive)
│   └── js/app.js            # Core utilities (API, theme, sidebar, tabs, modals, toasts)
├── templates/
│   ├── base.html            # Layout: sidebar nav, topbar, mobile bottom nav, theme toggle
│   ├── dashboard.html       # Stats grid, runner status, last run, monitoring links
│   ├── test_plans.html      # JMX selector, params, presets, execution, live summary, logs
│   ├── results.html         # Results table, compare, download bundle
│   ├── test_data.html       # CSV builder (5 types), file management, distribution
│   ├── slaves.html          # List/grid views, enable/disable, SSH overrides, bulk actions
│   ├── settings.html        # 4 tabs: General, Project, Integrations, System
│   ├── setup.html           # First-run setup wizard
│   └── token.html           # Token entry page for remote users
├── CLAUDE.md                # This file
└── PLAN.md                  # Implementation plan (Phase 13 amendments)
```

## Project Root Context

The webapp sits inside a JMeter performance test project. The parent directory (`../`) contains:

- `config/` — JSON configs (`vm_config.json`, `student_data_config.json`)
- `config.properties` — Central test parameters (read by runner for `-G` flags)
- `slaves.txt` — Slave VM IPs (JSON format with enabled flags, backward-compatible with plain text)
- `test_plan/` or `script/jmeter/` — JMX test plans
- `test_data/` — CSV test data and per-slave distributions
- `results/` — JTL logs and HTML report folders
- `bin/` — Windows batch scripts
- `utils/` — Python utilities

The app discovers these paths on first launch and saves them in `project.json`.

## Access Control

Two-tier access system:

| Level | Who | Capabilities |
|-------|-----|-------------|
| **Admin** | Localhost users, or remote users with valid token cookie | Full access: edit config, run tests, delete results, manage slaves |
| **Viewer** | Remote users without token | Read-only: view dashboard, results, reports. No edit/delete/run |

**Localhost-only features** (hidden from remote users entirely):
- Scripts page (nav item + all endpoints)
- Edit test plan button (opens JMeter GUI)
- Open report in filesystem (`os.startfile()`)
- Open result folder in explorer

**Auth flow for remote users:**
1. Request without valid token cookie → redirect to `/token?next=<path>`
2. Enter token → `POST /api/auth/verify` → sets `jmeter_token` cookie
3. Subsequent requests: middleware reads cookie, sets `request.state.access_level`

## Pages (7 main + 1 auth)

| # | Page | Route | Key Features |
|---|------|-------|-------------|
| 1 | Dashboard | `/` | Stats grid (plans, results, slaves, mode), runner status, last run, monitoring links (Grafana/InfluxDB) |
| 2 | Test Plans & Runner | `/plans` | JMX selector, parameter form, presets (save/load/delete), global properties, filter checkbox, mode indicator, live execution with WebSocket (summary stats, slave progress, raw logs), elapsed timer |
| 3 | Results | `/results` | Browse result folders, open/download reports, regenerate (filter → temp dir → safe swap), compare 2 runs, download bundle, access-controlled delete |
| 4 | Test Data | `/data` | CSV builder with 5 column types (Sequential, Static, Random Pick, Expression, Sequence), templates, preview, generate, upload, distribute to slaves (copy/split modes) |
| 5 | Slave VMs | `/slaves` | List/grid view toggle, per-slave enable/disable toggle, SSH override panel, status check, Start/Stop All, bulk actions, VM config editor |
| 6 | Scripts | `/scripts` | Discover .py/.bat files, run with output streaming (localhost only) |
| 7 | Settings | `/settings` | 4 tabs — General (server, appearance, runner, results, security), Project (paths, JMeter detection), Integrations (Grafana, InfluxDB, Ollama), System (JMeter/Java/Python versions, disk space) |
| — | Token | `/token` | Auth token entry for remote users |

## JTL Filter (`jtl_filter.py`)

Standalone script that cleans JTL files before report generation:

```bash
python jtl_filter.py <input.jtl> <output.jtl> [regex_pattern]
```

**Always removes:**
- Sub-results: labels ending with `-0`, `-1`, etc. (Transaction Controller child samples) — typically ~80-85% of rows
- Unresolved variables: labels containing `${...}`

**Optionally removes:**
- Labels not matching a regex pattern (e.g., exclude username rows)

**Impact:** 682 MB (3.4M rows) → 153 MB (565K rows) on real test data.

## Report Optimization

`REPORT_OPTIMIZE_PROPS` in `services/jmeter.py` disables heavy over-time graphs that bloat `graph.js` (can reach 500+ MB):

```python
REPORT_OPTIMIZE_PROPS = [
    "-Jjmeter.save.saveservice.output_format=csv",
    "-Jjmeter.reportgenerator.graph.responseTimeOverTime.enabled=false",
    "-Jjmeter.reportgenerator.graph.latenciesOverTime.enabled=false",
    "-Jjmeter.reportgenerator.graph.bytesThroughputOverTime.enabled=false",
    "-Jjmeter.reportgenerator.graph.connectTimeOverTime.enabled=false",
]
```

**Regeneration flow** (safe, non-destructive):
1. Filter JTL with `jtl_filter.py` → `filtered.jtl`
2. Generate report to `report_tmp/` (old report untouched)
3. On success: delete old `report/`, rename `report_tmp/` → `report/`
4. On failure: clean up temp, old report preserved
5. Always clean up `filtered.jtl`

**Report viewing on localhost:** Uses `os.startfile()` to open `report/index.html` directly in the default browser, bypassing the FastAPI proxy which can't handle 500+ MB static files.

## Slaves Configuration

Slaves file supports JSON format with enable/disable flags:

```json
[
  {"ip": "10.0.0.1", "enabled": true},
  {"ip": "10.0.0.2", "enabled": false},
  {"ip": "10.0.0.3", "enabled": true}
]
```

Backward-compatible: auto-migrates plain text (one IP per line) to JSON on first edit. `get_active_slaves()` returns only enabled IPs for JMeter `-R` flag.

## CSV Builder Column Types

The Test Data page generates CSV files with these column types:

| Type | Description | Example |
|------|-------------|---------|
| **Sequential** | Multiple ranges with prefix, start, end, zero-padded width | `USR000001` to `USR001000` |
| **Static** | Same value for all rows | `password123` |
| **Random Pick** | Values with weighted distribution (counts) | 60% active, 30% inactive, 10% pending |
| **Expression** | Template with `{column_name}` references and `{#}` for row number | `{USERNAME}@mail.com` |
| **Sequence** | Numeric sequence with start and step | 1, 2, 3, ... |

Supports custom saved templates and built-in presets (Username Only, Username+Password, etc.).

## Key Design Decisions

1. **No database** — all state lives in project files. Test history is derived from the results/ directory.
2. **Per-project deployment** — the app is copied into each project. No multi-project switching.
3. **Relative paths** — all file access is relative to `project_root` (default `..`).
4. **Auto-detection on first run** — scans parent directory for known folder patterns and generates `project.json`.
5. **Process isolation** — JMeter, Python scripts, batch files run as subprocesses. Non-blocking.
6. **WebSocket for live logs** — test execution streams stdout/stderr to browser in real time.
7. **Token auth for remote** — localhost always admin, remote needs token. No user database.
8. **Safe regeneration** — always filter first, generate to temp dir, swap on success. Old report never destroyed until new one succeeds.
9. **Filesystem report viewing** — `os.startfile()` on localhost avoids proxy bottleneck for large reports.

## Settings (settings.json)

App-level configuration stored in `settings.json` (auto-created on first save):

```json
{
  "server": {
    "domain": "",
    "host": "0.0.0.0",
    "port": 8080,
    "allow_external": true,
    "base_path": ""
  },
  "theme": "dark",
  "sidebar_collapsed": false,
  "runner": { "auto_scroll": true, "max_log_lines": 1000, "confirm_before_stop": true },
  "results": { "sort_order": "newest" },
  "analysis": { "ollama_url": "http://localhost:11434", "ollama_model": "llama3.1:8b", "ollama_timeout": 120 },
  "auth": { "token": "", "cookie_name": "jmeter_token", "cookie_max_age": 86400 },
  "monitoring": { "grafana_url": "", "influxdb_url": "" }
}
```

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app (reads settings.json for host/port)
python -m webapp

# Run the app (CLI overrides)
python -m webapp --host 0.0.0.0 --port 8080

# Run the app (development with reload)
cd webapp && uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

## Tech Stack & Dependencies

- **fastapi** — web framework
- **uvicorn** — ASGI server
- **jinja2** — HTML templates
- **python-multipart** — form handling
- **websockets** — live log streaming
- **aiofiles** — async file operations
- **pandas** — CSV and JTL parsing
- **numpy** — statistical analysis (percentiles, outlier detection)
- **httpx** — async HTTP client for Ollama API
- **paramiko** + **scp** — SSH to slave VMs

## Coding Conventions

- Use async/await for all route handlers
- Keep routers thin — business logic goes in services/
- All file paths must go through `project.json` resolution, never hardcode
- Use pathlib.Path for all path operations
- Error responses return JSON with `{"error": "message"}`
- Access control: `_check_access(request)` returns 403 for viewers, `None` for admins
- Localhost check: `getattr(request.state, "is_localhost", False)`
- Frontend uses vanilla JS (no framework) — keep it simple
- CSS uses a single stylesheet with CSS variables for theming (light/dark)
- Mobile responsive: bottom nav bar, hamburger menu, action bar for touch
