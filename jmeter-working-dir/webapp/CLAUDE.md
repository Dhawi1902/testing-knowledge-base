# CLAUDE.md — JMeter Test Dashboard Web App

This file provides guidance to Claude Code when working on the web app.

## Overview

A self-contained web dashboard for managing JMeter performance test projects. The app is deployed **per-project** — it lives inside the project directory and operates on the files around it. No database; everything is file-based.

## Architecture

- **Backend**: FastAPI (Python)
- **Frontend**: HTML/CSS/JS (served by FastAPI via Jinja2 templates or static files)
- **No database** — reads/writes project files directly (configs, CSVs, JTLs, JMX)
- **WebSocket** — for live log streaming during test execution
- **Process management** — launches JMeter, Python scripts, and batch files as subprocesses
- **Analysis engine** — rule-based pattern detection + optional Ollama AI for deep insights
- **PNC compliance** — all data stays local, AI runs via Ollama on-premise, no cloud API calls

## Directory Structure

```
webapp/
├── main.py                  # FastAPI app entry point
├── requirements.txt         # Python dependencies (fastapi, uvicorn, etc.)
├── project.json             # Project-specific config (auto-generated on first run)
├── routers/
│   ├── dashboard.py         # GET / — overview, slave count, last run
│   ├── config.py            # Config file CRUD + GET /slaves (VM status page)
│   ├── test_data.py         # Generate, split, distribute, preview CSV
│   ├── test_plans.py        # List JMX files, extract params, open in JMeter GUI
│   ├── runner.py            # Execute tests, live logs (WebSocket), stop, presets
│   ├── results.py           # Browse results, serve HTML reports, compare runs, JTL stats
│   ├── scripts.py           # Discover and run custom .py/.bat from utils/ and bin/
│   └── settings.py          # App settings CRUD (settings.json), GET /settings page
├── services/
│   ├── jmeter.py            # JMeter process management (run, stop, parse JMX)
│   ├── slaves.py            # SSH operations (start/stop servers, status check)
│   ├── data.py              # CSV generation, splitting, distribution
│   ├── config_parser.py     # Read/write config.properties, vm_config.json, slaves.txt
│   ├── jtl_parser.py        # Parse JTL files for summary stats
│   ├── analysis.py          # Rule-based analysis + Ollama AI integration
│   └── process_manager.py   # Generic subprocess runner with output streaming
├── prompts/
│   └── analysis.txt         # Ollama prompt template for AI analysis
├── static/
│   ├── css/
│   ├── js/
│   └── img/
├── settings.json            # App settings (auto-generated on first save)
├── __main__.py              # Entry point: python -m webapp
├── templates/
│   ├── base.html            # Layout with sidebar navigation (dark/light theme)
│   ├── dashboard.html
│   ├── configuration.html
│   ├── test_data.html
│   ├── test_plans.html
│   ├── runner.html
│   ├── results.html
│   ├── slaves.html          # VM status panel with Start/Stop/Refresh
│   ├── settings.html        # App settings UI
│   └── setup.html           # First-run setup wizard
├── CLAUDE.md                # This file
└── PLAN.md                  # Implementation plan
```

## Project Root Context

The webapp sits inside a JMeter performance test project. The parent directory (`../`) contains:

- `config/` — JSON configs (`vm_config.json`, `student_data_config.json`)
- `config.properties` — Central test parameters
- `slaves.txt` — Slave VM IPs
- `test_plan/` or `script/jmeter/` — JMX test plans
- `test_data/` — CSV test data and per-slave distributions
- `results/` — JTL logs and HTML report folders
- `bin/` — Windows batch scripts
- `utils/` — Python utilities
- `requirements.txt` — Python dependencies (parent project)

The app discovers these paths on first launch and saves them in `project.json`.

## project.json

Auto-generated on first run, user can edit via Settings page:

```json
{
  "name": "MAYA PerfTest",
  "project_root": "..",
  "jmeter_path": "C:/apache-jmeter-5.6.3/bin/jmeter.bat",
  "paths": {
    "jmx_dir": "test_plan",
    "config_dir": "config",
    "config_properties": "config.properties",
    "results_dir": "results",
    "test_data_dir": "test_data",
    "scripts_dirs": ["bin", "utils"],
    "slaves_file": "slaves.txt"
  }
}
```

## Pages (8 total)

| # | Page | Route | Description |
|---|------|-------|-------------|
| 1 | Dashboard | `/` | Overview, slave count, last run summary, quick actions |
| 2 | Configuration | `/config` | Edit config.properties, vm_config.json, slaves.txt, project.json |
| 3 | Test Data | `/data` | Generate master data, split & distribute, preview CSV |
| 4 | Test Plans & Runner | `/plans` | Dropdown JMX selector, [Edit] opens JMeter, [Run] with params, presets, live logs |
| 5 | Results | `/results` | Browse result folders, HTML reports, JTL stats, compare runs |
| 6 | Scripts | `/scripts` | Discover and execute .py/.bat from utils/ and bin/ |
| 7 | Slave VMs | `/slaves` | VM status panel — online/offline check, Start All / Stop All JMeter servers |
| 8 | Settings | `/settings` | Server (domain, port, external access), appearance (dark/light theme), test runner, target endpoints, AI analysis (Ollama) |

## Analysis Engine

### Data Classification
All performance test data is **PNC (Private and Confidential)**. The analysis engine runs entirely on-premise:
- **Rule-based analysis**: built-in, no external dependencies
- **AI analysis**: via Ollama (local LLM), no data leaves the machine

### Pipeline
```
Raw JTL (millions of rows)
    → JTL Pre-Processor (pandas, local)
    → Compact Summary (~2-4KB JSON)
    → Rule-Based Analysis (always available, free)
    → Ollama AI Analysis (optional, local)
    → Report (markdown, cached to results/{folder}/analysis.json)
```

### Rule-Based Detection
- Bottleneck: p95 > 3x median
- Error threshold: >2% warning, >5% critical
- Throughput saturation: plateau detection
- Response time degradation: inflection point detection
- Outlier detection: beyond 2 standard deviations

### Ollama Integration
- Endpoint: `http://localhost:11434/api/generate`
- Default model: `llama3.1:8b` (configurable)
- Only receives pre-processed summary, never raw data
- Graceful fallback: if Ollama is down, rule-based results shown

## Key Design Decisions

1. **No database** — all state lives in project files. Test history is derived from the results/ directory.
2. **Per-project deployment** — the app is copied into each project. No multi-project switching.
3. **Relative paths** — all file access is relative to `project_root` (default `..`).
4. **Auto-detection on first run** — scans parent directory for known folder patterns and generates `project.json`.
5. **Process isolation** — JMeter, Python scripts, and batch files run as subprocesses. The web app never blocks on them.
6. **WebSocket for live logs** — test execution streams stdout/stderr to the browser in real time.

## Settings (settings.json)

App-level configuration stored in `settings.json` (auto-created on first save):

```json
{
  "server": {
    "domain": "",
    "host": "0.0.0.0",
    "port": 8080,
    "allow_external": true
  },
  "theme": "dark",
  "sidebar_collapsed": false,
  "runner": { "auto_scroll": true, "max_log_lines": 1000, "confirm_before_stop": true },
  "results": { "sort_order": "newest" },
  "analysis": { "ollama_url": "http://localhost:11434", "ollama_model": "llama3.1:8b", "ollama_timeout": 120 },
  "endpoints": [
    {"name": "MAYA Production", "url": "https://maya-cloud.um.edu.my/sitsvision/wrd/siw_lgn"},
    {"name": "MAYA PREP", "url": "https://printis-prep.um.edu.my/sitsvision/wrd/siw_lgn"},
    {"name": "Cloudunity Report Viewer", "url": "https://cloudunity.um.edu.my/reportcradle/reportviewer.aspx"}
  ]
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
- **paramiko** + **scp** — SSH to slave VMs (reuse from parent project)

## Coding Conventions

- Use async/await for all route handlers
- Keep routers thin — business logic goes in services/
- All file paths must go through `project.json` resolution, never hardcode
- Use pathlib.Path for all path operations
- Error responses return JSON with `{"error": "message"}`
- Frontend uses vanilla JS (no framework) — keep it simple
- CSS uses a single stylesheet with CSS variables for theming
