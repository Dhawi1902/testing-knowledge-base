# CLAUDE.md — LoadLitmus Web App

This file provides guidance to Claude Code when working on the web app.

## Overview

**LoadLitmus** — a self-contained web dashboard for managing performance test projects. Currently built around JMeter, with plans to support additional testing tools. The app is deployed **per-project** — it lives inside the project directory and operates on the files around it. No database; everything is file-based.

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
├── main.py                  # FastAPI app, auth middleware, logging, first-run redirect
├── __main__.py              # Entry point: python -m webapp
├── __version__.py           # Version: "0.5.0" — single source of truth
├── requirements.txt         # Runtime Python dependencies (dev deps in pyproject.toml)
├── project.json             # Project-specific config (auto-generated on first run)
├── settings.json            # App settings (auto-generated on first save)
├── presets.json             # Saved test parameter presets
├── jmeter_properties.json   # User-defined JMeter properties (F2)
├── jtl_filter.py            # JTL filter script (sub-results, variables, regex)
├── pyproject.toml           # Package metadata, entry point, dependency split
├── loadlitmus.spec          # PyInstaller build spec for standalone exe
├── routers/
│   ├── dashboard.py         # GET / — stats, trends, alerts, slave health, disk usage
│   ├── config.py            # Slaves page, VM config, properties, JMeter props, slave mgmt
│   ├── test_data.py         # CSV builder, generate, split, distribute, preview
│   ├── test_plans.py        # JMX management, runner, presets, filter config
│   ├── results.py           # Results listing, reports, regeneration, compare, download, analysis
│   ├── scripts.py           # Discover and run .py/.bat (REMOVED from nav, kept for reference)
│   └── settings.py          # App settings CRUD, export/import, report config, system info
├── services/
│   ├── auth.py              # Token auth, access control (admin/viewer), path safety (safe_join)
│   ├── jmeter.py            # Build JMeter commands, REPORT_OPTIMIZE_PROPS, parse JMX
│   ├── slaves.py            # SSH operations (start/stop/status, file distribution, paramiko)
│   ├── data.py              # CSV generation (5 column types), split, distribute
│   ├── paths.py             # get_app_dir() — path resolution for source and frozen exe
│   ├── config_parser.py     # Read/write config.properties, vm_config, slaves (JSON format)
│   ├── jmx_patcher.py       # JMX XML patching (Backend Listener, etc.)
│   ├── jtl_parser.py        # Parse JTL files with JSON caching for summary stats
│   ├── analysis.py          # Rule-based analysis + optional Ollama AI
│   ├── report.py            # Async report regeneration (filter JTL + generate)
│   ├── report_properties.py # Report graph configuration management
│   ├── settings.py          # Settings service (load/save/validate settings.json)
│   └── process_manager.py   # Subprocess runner with WebSocket output streaming
├── config/
│   └── report.properties    # Default report generation properties
├── prompts/
│   └── analysis.txt         # Ollama prompt template
├── scripts/
│   └── build.py             # PyInstaller build automation + smoke test
├── static/
│   ├── css/style.css        # Design system (tokens, utilities, components, light/dark themes)
│   ├── js/app.js            # Core utilities (API, theme, sidebar, tabs, modals, toasts, dropdowns)
│   └── favicon.svg          # SVG gauge icon (indigo gradient)
├── templates/
│   ├── icons.html           # Lucide SVG icon macros (39 icons)
│   ├── base.html            # Layout: sidebar nav, topbar, theme toggle, confirm/prompt modals
│   ├── dashboard.html       # Stats, trend chart, alerts, slave health, disk usage
│   ├── test_plans.html      # JMX selector, params, presets, execution, live summary, logs
│   ├── results.html         # Results table, compare, download, sortable columns
│   ├── test_data.html       # CSV builder (5 types), file management, distribution
│   ├── slaves.html          # List/grid views, enable/disable, SSH overrides, nicknames
│   ├── settings.html        # 5 tabs: General, Project, Report, Integrations, System
│   ├── setup.html           # First-run setup wizard
│   └── token.html           # Token entry page for remote users
├── tests/                   # pytest suite (320 tests, 56% code coverage)
│   ├── conftest.py          # Fixtures: temp dirs, admin/viewer clients, test data
│   ├── test_auth.py         # Auth middleware, token verification, access levels
│   ├── test_config_api.py   # VM config, slaves, project, properties, JMeter props
│   ├── test_dashboard_api.py # Dashboard stats, recent runs, trends, alerts
│   ├── test_data_api.py     # CSV upload, build, preview, distribute
│   ├── test_plans_api.py    # JMX list, params, presets, delete, filter config
│   ├── test_results_api.py  # Results listing, reports, download, compare, regenerate
│   ├── test_security.py     # Viewer-denied tests for all write endpoints
│   └── test_settings_api.py # Settings CRUD, export/import, report settings
├── logs/                    # Rotating app logs (auto-created)
├── CLAUDE.md                # This file
├── README.md                # Setup, architecture, config reference, new machine setup
├── PLAN.md                  # Original implementation plan
├── PHASE_PLAN.md            # Improvement phases A-G status tracker
└── EVALUATION.md            # Page-by-page evaluation and audit findings
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

## Pages (6 main + 1 auth)

| # | Page | Route | Key Features |
|---|------|-------|-------------|
| 1 | Dashboard | `/` | Stats grid, trend chart (last 10 runs), alerts/warnings, slave health dots, disk usage, runner status, last run summary with metrics, monitoring links |
| 2 | Test Plans & Runner | `/plans` | JMX selector, parameter form, presets (save/load/delete), global properties, filter config, mode indicator, live execution with WebSocket (summary stats, slave progress, raw logs), elapsed timer, delete plans |
| 3 | Results | `/results` | Browse result folders, sortable columns, open/download reports, regenerate (filter → temp dir → safe swap), compare 2 runs, download bundle, stats preview, bulk regenerate, analysis badges |
| 4 | Test Data | `/data` | CSV builder with 5 column types (Sequential, Static, Random Pick, Expression, Sequence), templates, preview, generate, upload, distribute to slaves (copy/split modes) |
| 5 | Slave VMs | `/slaves` | List/grid view, per-slave enable/disable, nicknames, SSH overrides, per-VM JMeter paths, individual + bulk start/stop, status check, Windows slave support, SSH key auth |
| 6 | Settings | `/settings` | 5 tabs — General (server, appearance, runner, results, security), Project (paths, JMeter detection), Report (graph toggles, presets), Integrations (Grafana, InfluxDB, Ollama), System (versions, disk). Export/import settings. |
| — | Token | `/token` | Auth token entry for remote users |

**Removed:** Scripts page (`/scripts`) — router disconnected, sidebar link removed. Files kept for reference.

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

Slaves file supports JSON format with enable/disable flags, nicknames, and per-slave SSH overrides:

```json
[
  {"ip": "10.0.0.1", "enabled": true, "nickname": "SLAVE 1"},
  {"ip": "10.0.0.2", "enabled": false},
  {"ip": "10.0.0.3", "enabled": true, "overrides": {"user": "admin", "key_file": "/path/to/key"}}
]
```

Backward-compatible: auto-migrates plain text (one IP per line) to JSON on first edit. `get_active_slaves()` returns only enabled IPs for JMeter `-R` flag. `read_slaves()` preserves all fields (nickname, overrides) through read/write cycles.

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
    "host": "127.0.0.1",
    "port": 5080,
    "allow_external": false,
    "base_path": ""
  },
  "theme": "dark",
  "sidebar_collapsed": false,
  "runner": { "auto_scroll": true, "max_log_lines": 1000, "confirm_before_stop": true },
  "filter": { "sub_results": true, "label_pattern": "" },
  "report": { "granularity": 60000, "graphs": { "responseTimePercentiles": true, "..." : "..." } },
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
python -m webapp --host 0.0.0.0 --port 5080

# Run the app (development with reload)
cd webapp && uvicorn main:app --reload --host 0.0.0.0 --port 5080

# Run tests
python -m pytest tests/ -v --tb=short

# Run tests with coverage
python -m pytest tests/ -v --tb=short \
  --cov=routers --cov=services --cov=main \
  --cov-report=term-missing
```

### CLI Commands

```bash
# Version
python -m webapp --version          # Print "LoadLitmus 0.5.0"

# Project init
python -m webapp init               # Scaffold project in current directory
python -m webapp init <path>        # Scaffold project in specific directory

# Serve (default command)
python -m webapp                    # Start dashboard (default)
python -m webapp serve              # Explicit serve
python -m webapp serve --port 9000  # Override port
python -m webapp serve --dev        # Enable auto-reload
```

### Build Standalone Exe

```bash
# Install dev dependencies (includes pyinstaller)
pip install ".[dev]"

# Build exe + run smoke test
cd webapp && python scripts/build.py

# Output: dist/loadlitmus.exe (~62 MB)
```

## CI/CD

GitHub Actions workflow at `.github/workflows/webapp-tests.yml`:
- Triggers on push/PR to `jmeter-working-dir/webapp/**`
- Runs on Ubuntu with Python 3.13
- Executes all 320 tests with coverage reporting (minimum 55% enforced)
- Uploads HTML coverage report as artifact

## Logging

API requests logged to `logs/app.log` via `RotatingFileHandler` (5MB max, 3 backups).
- All API requests: method, path, status code, duration (ms)
- Static file requests excluded from logging
- Errors include full stack traces
- Logger name: `jmeter_dashboard`

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

## Design System (UI/UX)

CSS-first design system in `style.css` targeting a "Linear meets Vercel" aesthetic.

### CSS Tokens (Custom Properties)

- **Colors**: `--color-primary`, `--color-danger`, `--color-success`, `--color-warning` + `-hover` and `-subtle` variants
- **Text**: `--color-text`, `--color-text-secondary`, `--color-text-tertiary`
- **Surfaces**: `--color-bg`, `--color-surface`, `--color-surface-alt`, `--color-surface-hover`
- **Radius**: `--radius-sm` (4px), `--radius` (6px), `--radius-lg` (8px), `--radius-xl` (12px)
- **Shadows**: `--shadow`, `--shadow-md`, `--shadow-lg`
- **Typography**: `--font-sans`, `--font-mono`

### Icon System

Lucide SVG icons via Jinja2 macros in `templates/icons.html`:

```jinja2
{% from 'icons.html' import icon %}
{{ icon('play', 18) }}                {# name, size in px #}
{{ icon('loader-2', 14, 'icon-spin') }} {# with CSS class #}
```

For JS-generated HTML, use template-time constants:
```javascript
const ICON_TRASH = `{{ icon('trash-2', 14) }}`;
```

### Utility Classes

- **Typography**: `.text-2xl`, `.text-xl`, `.text-lg`, `.text-base`, `.text-sm`, `.text-xs`, `.text-mono`, `.text-secondary`, `.text-tertiary`
- **Spacing** (4px grid): `.m-{0,4,8,12,16,24,32}`, `.mt-*`, `.mb-*`, `.ml-*`, `.mr-*`, `.p-*`, `.pt-*`, `.pb-*`, `.pl-*`, `.pr-*`, `.px-*`, `.py-*`, `.gap-*`
- **Flex**: `.flex`, `.flex-col`, `.flex-wrap`, `.flex-between`, `.items-center`, `.justify-end`
- **Grid**: `.grid`, `.grid-2`, `.grid-3`, `.grid-4`, `.grid-1-2`, `.grid-2-1`, `.grid-1-2-1`

### Interactive Components

- **Confirm modal**: `await confirmAction('message', { title, detail, danger })` — returns `true`/`false`
- **Prompt modal**: `await promptAction('title', { placeholder, defaultValue, description, validate })` — returns string or `null`
- **Dropdown menu**: `toggleDropdown(btn)` with `.dropdown` > `.dropdown-menu` > `.dropdown-item`
- **Tooltips**: `data-tooltip="text"` attribute (CSS-only)
- **Loading skeletons**: `.skeleton`, `.skeleton-text`, `.skeleton-card`, `.skeleton-row`
- **Empty states**: `.empty-state` > `.empty-state-title` + `.empty-state-desc`

### Modal Sizes

- `.modal-sm` — 420px (confirm/prompt dialogs)
- `.modal-md` — 480px (regen modal)
- `.modal` — 600px (default)
- `.modal-lg` — 900px (large content)

### Theme

Theme toggle in topbar (sun/moon icon). Stored in `localStorage('theme')`. CSS uses `[data-theme="dark"]` selectors for dark overrides.

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
- Icons use Lucide SVG via Jinja2 macros — never add Unicode/emoji icons
- `confirmAction()` and `promptAction()` are async — always use `await`
- Mobile responsive: bottom nav bar, hamburger menu, action bar for touch
