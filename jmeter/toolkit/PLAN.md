# JMeter Toolkit — Generalization Plan

## Context

The `jmeter-working-dir/` contains a production JMeter distributed testing framework tightly coupled to MAYA Portal (UM). The goal is to extract and generalize this into a reusable `jmeter/toolkit/` that can be copied into any new performance testing project.

The knowledge base docs (14 sections, all complete and generic) already reference `scripts/` and `samples/` folders that don't exist yet. This plan connects the toolkit to the docs.

### Key Decisions (from discussion)

- **Model A**: Toolkit as self-contained template you copy into new projects
- **Single `project.json`**: Replaces `config.properties` + `slaves.txt` + `vm_config.json` + `student_data_config.json` + `jtl_filter_config.json`
- **SSH auth**: Support both password (`credentials.json`, gitignored, per-slave overrides) and SSH key
- **Webapp**: Slim — runner, results, slaves, config editor. Already fully implemented (not scaffolded), just needs generalization
- **Runner**: Batch thin launcher → Python `run_test.py` (replaces broken `SE_run_jmeter.bat`)
- **Dynatrace/Grafana**: Opt-in (present in config = enabled)
- **Monitoring**: `docker-compose.yml` for InfluxDB + Grafana
- **DOCX reports**: Deferred
- **MAYA**: Preserved as `jmeter/examples/maya/` case study

---

## Target Structure

```
jmeter/
├── docs/                         # Already done (14 sections)
├── toolkit/                      # Copy this into new projects
│   ├── project.json.example
│   ├── credentials.json.example
│   ├── .gitignore
│   ├── setup.bat                 # First-time: Python check, venv, deps
│   ├── init.bat                  # Project init: copy examples, create dirs
│   ├── requirements.txt
│   ├── test_plan/                # User puts .jmx files here
│   ├── test_data/                # Generated/imported CSV files
│   ├── results/                  # Auto-created by runner
│   ├── extensions/               # JMeter plugins to deploy
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── common.py             # NEW shared module (SSH, config, iteration)
│   │   ├── run_test.py           # NEW replaces SE_run_jmeter.bat
│   │   ├── manage_servers.py     # Start/stop/status JMeter on slaves
│   │   ├── generate_data.py      # Config-driven ID generation
│   │   ├── split_and_distribute.py  # Split CSV + SCP to slaves
│   │   ├── setup_slave.py        # NEW bootstrap slave VMs
│   │   ├── collect_from_slaves.py
│   │   ├── clear_files.py
│   │   ├── create_folders.py
│   │   ├── deploy_extensions.py
│   │   ├── fetch_logs.py
│   │   ├── set_slave_ip.py
│   │   └── filter_jtl.py
│   ├── bin/
│   │   └── run.bat               # Thin launcher → python utils/run_test.py
│   ├── webapp/                   # Dashboard (generalized)
│   │   ├── main.py
│   │   ├── __main__.py
│   │   ├── requirements.txt
│   │   ├── presets.json
│   │   ├── prompts/analysis.txt
│   │   ├── routers/              # dashboard, config, test_data, test_plans, results, scripts, settings
│   │   ├── services/             # config_parser, jmeter, jtl_parser, analysis, data, slaves, process_manager
│   │   ├── templates/
│   │   └── static/
│   └── monitoring/
│       ├── docker-compose.yml    # InfluxDB + Grafana
│       └── grafana/
│           ├── provisioning/     # Auto-provision datasource + dashboard
│           └── dashboards/       # Pre-built JMeter dashboard JSON
├── examples/
│   └── maya/                     # MAYA case study
│       ├── README.md
│       ├── project.json          # Pre-filled MAYA config
│       └── correlation-notes.md  # SITS:Vision patterns
└── samples/
    ├── sample-test.jmx           # Minimal demo JMX with __P() params
    └── sample-data.csv           # 100-row example CSV
```

---

## Files NOT Carried Forward (Delete)

| File | Reason |
|------|--------|
| `utils/copy_to_vm.py` | Hardcoded credentials, superseded |
| `utils/test_data.py` | Hardcoded ID ranges, superseded by `generate_master_data.py` |
| `utils/custom_test_data.py` | 1 line of incomplete code |
| `utils/select_test_data.py` | Hardcoded OFFSET/SIZE, superseded |
| `utils/split_test_data.py` | Merged into `split_and_distribute.py` with `--local-only` flag |
| `utils/distribute_test_data.bat` | Duplicate of Python SCP approach (uses pscp) |
| `config/student_data_config copy.json` | Invalid JSON (two root objects), copy artifact |
| `bin/test/SE_run_jmeter.bat` | JMeter command commented out, prints fake "success" |
| `run_jmeter.bat` (root) | One-liner `jmeter`, no value |
| `webapp/CLAUDE.md`, `webapp/PLAN.md` | Working-dir specific |
| `webapp/project.json` | Replaced by toolkit-root `project.json` |

---

## Phase 1: Foundation

**Goal**: Skeleton that all subsequent phases depend on.

### 1.1 `project.json.example`

```json
{
  "name": "My Performance Test",
  "jmeter_path": "",

  "slaves": [],

  "auth": {
    "method": "password",
    "user": "root",
    "key_file": null
  },

  "slave_config": {
    "jmeter_home": "/opt/jmeter",
    "start_script": "/home/jmeter/start-slave.sh",
    "stop_script": "/home/jmeter/stop-slave.sh",
    "test_data_path": "/home/jmeter/test_data/",
    "extensions_path": "/opt/jmeter/lib/ext/",
    "log_path": "/home/jmeter/jmeter-server.log",
    "jmeter_heap": {
      "xms": "12g",
      "xmx": "24g",
      "gc_algo": "-XX:+UseG1GC -XX:MaxGCPauseMillis=100 -XX:G1ReservePercent=20"
    }
  },

  "test": {
    "test_plan": "test_plan/my-test.jmx",
    "test_data": "test_data/users.csv",
    "threads": 10,
    "rampUp": 10,
    "loop": 1,
    "thinkTime": 3000
  },

  "data_generation": {
    "prefixes": { "USR": { "start": 1, "end": 1000 } },
    "output_filename": "master_data.csv",
    "column_name": "USERNAME",
    "id_width": 6
  },

  "split_config": {
    "offset": 0,
    "size": 1000,
    "csv_filename": "users.csv"
  },

  "jtl_filter": {
    "label_pattern": null,
    "exclude_embedded": true,
    "generate_html_report": true
  },

  "create_folders": {
    "parent": "",
    "children": []
  },

  "grafana": null,
  "dynatrace": null,

  "webapp": {
    "host": "127.0.0.1",
    "port": 8080,
    "base_path": "",
    "theme": "light",
    "endpoints": []
  }
}
```

### 1.2 `credentials.json.example`

```json
{
  "default_password": "your-ssh-password",
  "overrides": {}
}
```

### 1.3 Files to create

| File | Description |
|------|-------------|
| `toolkit/.gitignore` | Based on existing, add `credentials.json`, `results/`, `test_data/slaves_data/`, `venv/` |
| `toolkit/requirements.txt` | `pandas>=2.0`, `numpy>=1.24`, `paramiko>=3.4`, `scp>=0.14` |
| `toolkit/setup.bat` | Check Python 3.10+, create venv, install deps (toolkit + webapp) |
| `toolkit/init.bat` | Copy `.example` files, create `test_plan/`, `test_data/`, `results/`, `extensions/` |
| `toolkit/utils/__init__.py` | Empty |
| `toolkit/utils/common.py` | **Core shared module** — see below |

### 1.4 `common.py` — Key Functions

Eliminates ~450 lines duplicated across 11 source files:

- `get_project_root()` — resolve toolkit root from `utils/` location
- `load_project_config(path=None)` — load `project.json` with error messages
- `load_credentials(path=None)` — load `credentials.json`, return `{}` if missing
- `get_slaves(config)` — extract slave IPs from config
- `get_ssh_credentials(config, credentials, host)` — resolve per-host auth (password vs key, with overrides)
- `ssh_connect(host, ssh_creds)` — paramiko connect with key/password support
- `execute_remote_command(host, ssh_creds, command)` → `(success, stdout, stderr)`
- `scp_upload(host, ssh_creds, local_path, remote_path)` → `(success, message)`
- `scp_download(host, ssh_creds, remote_path, local_path)` → `(success, message)`
- `for_each_slave(config, credentials, operation)` — iterate slaves with progress + summary

**Source reference**: `manage_jmeter_servers.py` has the cleanest version of the duplicated pattern.

---

## Phase 2: Core Utils

**Goal**: Generalize and migrate all kept Python scripts. After this, `bin/run.bat` runs distributed tests.

### 2.1 `utils/run_test.py` (NEW — most important)

Replaces `SE_run_jmeter.bat` logic in Python. Fixes the broken batch properties parser.

**Logic**:
1. Load `project.json`
2. Read `test` section for parameters
3. Read `slaves` for slave list
4. Calculate `threads / len(slaves)` per slave
5. Create timestamped result folder `results/YYYYMMDD_N/`
6. Build JMeter CLI: `-n -t <plan> -R <slaves> -G<key>=<value>` for all test params
7. Include `-Gdynatrace.*` only if `dynatrace` block present
8. Execute JMeter subprocess, stream output
9. Optionally run `filter_jtl.py`
10. Print Grafana link if `grafana` block present

**Source**: `SE_run_jmeter.bat` lines 96-112 (JMeter command), `webapp/services/jmeter.py` `build_jmeter_command()` lines 68-126.

### 2.2 Migrated Utils (11 files)

Each file: remove `load_config()`, `read_slaves()`, SSH boilerplate → import from `common.py`. Read from `project.json` instead of separate config files.

| Source → Target | Key changes |
|------|------|
| `manage_jmeter_servers.py` → `manage_servers.py` | Use common. Read `slave_config.start_script`/`stop_script` from project.json |
| `generate_master_data.py` → `generate_data.py` | Read `data_generation` from project.json |
| `split_and_copy_to_vms.py` → `split_and_distribute.py` | Use common. Read `split_config`. Add `--local-only` flag (subsumes `split_test_data.py`) |
| `collect_from_slaves.py` → `collect_from_slaves.py` | Use common. Read `create_folders.parent` |
| `clear_files_on_slaves.py` → `clear_files.py` | Use common + `for_each_slave()` |
| `create_folder_on_slaves.py` → `create_folders.py` | Use common. Read `create_folders` |
| `deploy_extensions.py` → `deploy_extensions.py` | Use common. Read `slave_config.extensions_path` |
| `fetch_server_logs.py` → `fetch_logs.py` | Use common. Read `slave_config.log_path` (remove hardcoded `/home/opc/` path) |
| `set_slave_ip.py` → `set_slave_ip.py` | Use common. Read `slave_config.jmeter_heap` |
| `filter_jtl.py` → `filter_jtl.py` | Read `jtl_filter` from project.json. Remove DOCX report call. **Already enhanced**: filters sub-results (`-N` suffix labels), unresolved variables (`${...}`), optional regex pattern |

### 2.3 `utils/setup_slave.py` (NEW)

Bootstrap slave VMs:
- `--check`: Verify Java + JMeter on all slaves
- `--configure`: Create dirs, set slave IP, set heap, deploy start/stop scripts
- `--install`: Full setup (Java + JMeter download + configure)

### 2.4 `bin/run.bat`

```batch
@echo off
cd /d "%~dp0.."
if exist venv\Scripts\python.exe (
    venv\Scripts\python utils\run_test.py %*
) else (
    python utils\run_test.py %*
)
```

---

## Phase 3: Webapp Generalization

**Goal**: Make the fully-implemented webapp read from `project.json` instead of legacy multi-file config. Remove MAYA defaults.

The webapp is already working (all routers, services, templates have real logic). Changes are targeted.

### 3.1 Copy `jmeter-working-dir/webapp/` → `toolkit/webapp/`

Copy all files, then apply modifications below. Remove `CLAUDE.md`, `PLAN.md`, `project.json` (webapp-level).

### 3.2 Key modifications

| File | Change |
|------|--------|
| `main.py` | `PROJECT_JSON = APP_DIR.parent / "project.json"` (toolkit root, not webapp dir). Read webapp settings from `project.json.webapp` instead of `settings.json` |
| `services/config_parser.py` | Adapt to read unified `project.json`. `read_config_properties()` builds from `project.json.test`. `read_slaves_file()` reads from `project.json.slaves` array. Keep fallback support for legacy `config.properties`/`slaves.txt` |
| `routers/settings.py` | Remove hardcoded UM URLs from `DEFAULT_SETTINGS.endpoints` (lines 39-43 → empty list). Read/write settings to `project.json.webapp` section |
| `routers/config.py` | Config page becomes a `project.json` editor. Same tabbed UI, data comes from unified config |
| `services/jmeter.py` | `build_jmeter_command()` reads `project.json.test` + `project.json.slaves`. All `test` keys (except `test_plan`) become `-G` flags |
| `services/slaves.py` | Support both password and key auth via `project.json.auth` + `credentials.json` |
| `templates/settings.html` | Change placeholder from `maya-perf.example.com` to generic |

### 3.3 Changes already implemented (in working-dir webapp)

The following changes have been made to the working-dir webapp and should be carried forward during generalization. This represents the current state of the webapp — all pages are fully functional.

#### Navigation & Layout (`base.html`, `style.css`, `app.js`)
- Sidebar with 7 pages: Dashboard, Test Plans & Runner, Results, Test Data, Slave VMs, Scripts, Settings
- Scripts page conditionally hidden for remote users (`{% if is_localhost %}`)
- Mobile responsive: hamburger menu, bottom nav bar (5 items + "More"), sticky action bar
- Dark/light theme with CSS variables and localStorage persistence
- Toast notification system (success/error/warning/info)
- Modal system, tab switching, keyboard shortcuts (Ctrl+Enter for test start)
- Complete CSS design system: cards, buttons, forms, tables, badges, spinners, toggles

#### Access Control (`main.py` middleware)
- Token-based auth for remote users, localhost always admin
- Two roles: admin (full access) and viewer (read-only)
- Auth middleware sets `request.state.is_localhost` and `request.state.access_level`
- Token entry page (`/token`) with cookie-based session
- `_check_access(request)` helper in routers returns 403 for viewers
- Localhost-only: Scripts page, Edit test plan button, Open report/folder buttons

#### Settings Page (`settings.html`, `routers/settings.py`)
- 4-tab layout: General, Project, Integrations, System
- General: server config (domain, port, base path, allow external), appearance (theme, sidebar), runner (auto-scroll, max log lines, confirm stop), results (sort order), security (auth token)
- Project: project name, JMeter path (auto-detect button), all path configs
- Integrations: Grafana/InfluxDB URLs, Ollama AI (URL, model, timeout, test connection)
- System: read-only cards showing JMeter/Java/Python versions, OS, disk space
- Server restart endpoint with change detection
- All inputs disabled for viewer role

#### Test Plans & Runner (`test_plans.html`, `routers/test_plans.py`)
- JMX file selector with size and date, Edit (localhost) / Download / Upload buttons
- Dynamic parameter form generated from JMeter `__P()` parameters
- Real-time command preview
- Preset system: save/load/delete presets, save to defaults, preset manager modal
- Global properties modal for key-value pairs from config.properties
- Filter labels checkbox (integrates with JTL filter)
- Mode indicator badge: "Local mode" or "Distributed (N slaves)"
- Live execution panel with WebSocket streaming:
  - Summary stats grid: Throughput, Avg RT, Error Rate, Total Samples, Active/Started/Finished VUs
  - Slave progress badges (per-IP: Running/Finished/Error)
  - Raw log output (collapsible, auto-scroll toggle)
  - Elapsed timer (HH:MM:SS)
- Start/Stop buttons with mobile action bar

#### Results Page (`results.html`, `routers/results.py`)
- Results table: folder, date, size, report status, JTL status, actions
- Search/filter input with result count
- Per-result actions: Open Report, Download (zip), Regenerate, Open Folder (localhost), Delete
- Bulk: Download Selected (bundle zip), Compare Selected (2 results side-by-side)
- Report open: `os.startfile()` on localhost (avoids proxy timeout for 500+ MB graph.js), API proxy fallback for remote
- Safe regeneration: filter JTL first → generate to `report_tmp/` → swap on success, old report preserved on failure
- Stats and AI Analysis panels removed (backend endpoints kept for future)

#### Test Data Page (`test_data.html`, `routers/test_data.py`, `services/data.py`)
- CSV file management: list, preview (paginated up to 10K rows), download, delete, rename
- CSV Builder with 5 column types:
  - Sequential: multiple ranges with prefix, start, end, zero-padded width
  - Static: single value for all rows
  - Random Pick: values with weighted distribution (counts)
  - Expression: template with `{column_name}` references and `{#}` for row number
  - Sequence: numeric with start and step
- Built-in and custom saved templates
- Client-side preview (first 5 rows) before generation
- File upload support
- Distribution to slaves: Copy (full file) or Split (divide rows) modes, per-slave offset/size, preview with gap indicators, execution with real-time log output

#### Slave VMs Page (`slaves.html`, `routers/config.py`, `services/config_parser.py`)
- Dual view: List and Grid modes (toggle, localStorage persistence)
- Per-slave: status indicator (Online/Offline/Disabled/Checking), enable/disable toggle, inline IP editing, SSH override panel (user/password/dest path), delete
- Slaves stored in JSON format: `[{"ip": "x.x.x.x", "enabled": true}, ...]`
- Auto-migrates plain text (one IP per line) to JSON on first edit
- `get_active_slaves()` returns only enabled IPs for JMeter `-R` flag
- Bulk actions: Enable/Disable selected, Remove selected
- Global actions: Add slave, Check Status (async), Start All / Stop All
- VM config section: SSH defaults, JMeter script paths
- Summary bar: total, enabled/disabled, online counts

#### Dashboard Page (`dashboard.html`, `routers/dashboard.py`)
- Stats grid: test plans count, result folders count, active/total slaves, mode
- Runner status card with test plan name and View Logs / Start Test links
- Last test run card with folder, date, size, report links
- Quick action links: Run Test, View Results, Edit Config, Test Data
- Monitoring cards: Grafana and InfluxDB (link if configured, dimmed if not)

#### JTL Filter (`jtl_filter.py`)
- Removes sub-results (labels ending with `-N`) — ~80-85% of raw JTL rows
- Removes unresolved variables (`${...}` labels)
- Optional regex pattern for additional label filtering
- Real data: 682 MB (3.4M rows) → 153 MB (565K rows)

#### Report Optimization (`services/jmeter.py`)
- `REPORT_OPTIMIZE_PROPS`: disables heavy over-time graphs to reduce graph.js size
- Forces CSV format for regeneration (`-Jjmeter.save.saveservice.output_format=csv`)
- Applied to both inline test runs and standalone regeneration

#### Process Manager (`services/process_manager.py`)
- Subprocess runner with WebSocket output streaming
- Supports post-commands (run sequentially after main process)
- Non-blocking execution

### 3.4 Webapp changes to discuss later

> **Note**: There are additional webapp improvements to discuss in a future session. This phase covers only the generalization needed to decouple from MAYA. UX improvements, new features, and architectural changes to the webapp will be planned separately.

---

## Phase 4: Extras

**Goal**: Monitoring stack and Grafana integration.

| File | Description |
|------|-------------|
| `monitoring/docker-compose.yml` | InfluxDB 1.8 + Grafana with auto-provisioned datasource |
| `monitoring/grafana/provisioning/datasources/influxdb.yml` | InfluxDB datasource auto-config |
| `monitoring/grafana/provisioning/dashboards/default.yml` | Dashboard provisioning |
| `monitoring/grafana/dashboards/jmeter-live.json` | Pre-built JMeter live dashboard |
| `monitoring/README.md` | Setup instructions |
| Update `utils/run_test.py` | Generate timestamped Grafana link after test completion |
| Expand `utils/setup_slave.py` | Full `--install` mode (Java + JMeter download) |

---

## Phase 5: Knowledge Base Integration

**Goal**: Connect toolkit to docs. Create MAYA case study and sample files.

### 5.1 MAYA case study

| File | Content |
|------|---------|
| `examples/maya/README.md` | Case study overview, links to docs |
| `examples/maya/project.json` | Pre-filled MAYA config (VMs, student prefixes, Dynatrace) |
| `examples/maya/correlation-notes.md` | SITS:Vision token patterns, multi-service architecture (extracted from working-dir CLAUDE.md) |

### 5.2 Sample files

| File | Content |
|------|---------|
| `samples/sample-test.jmx` | Minimal JMX with `__P()` params, CSV Data Set, Transaction Controller |
| `samples/sample-data.csv` | 100 rows: USR000001 to USR000100 |

### 5.3 Doc updates

| File | Change |
|------|--------|
| `jmeter/README.md` | Add links to `toolkit/`, `examples/`, `samples/` |
| `jmeter/CLAUDE.md` | Update `scripts/` and `samples/` references to actual locations |
| `jmeter/PLAN.md` | Update directory structure, add toolkit reference |
| `docs/09-execute-analyze.md` | Update `scripts/login-flow.jmx` references |
| `docs/14-automation-batch.md` | Add note referencing the toolkit for production use |

---

## Status

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | Pending | Foundation (project.json, common.py, setup/init) |
| 2 | Pending | Core utils (11 migrated + 2 new) |
| 3 | Pending | Webapp generalization |
| 4 | Pending | Monitoring (docker-compose, Grafana links) |
| 5 | Pending | KB integration (MAYA example, samples, doc updates) |

---

## Verification

After each phase:

- **Phase 1**: `init.bat` creates correct folder structure. `common.py` imports without errors (`python -c "from utils.common import load_project_config"`)
- **Phase 2**: `bin\run.bat` with a sample JMX runs a local JMeter test (no slaves needed). `python utils/manage_servers.py status` reports "no slaves configured" gracefully
- **Phase 3**: `python -m webapp` launches dashboard. Config page loads and displays `project.json` content. Runner page lists JMX files and shows command preview
- **Phase 4**: `docker-compose up` in `monitoring/` starts InfluxDB + Grafana. Grafana accessible at localhost:3000 with pre-configured dashboard
- **Phase 5**: `examples/maya/project.json` is valid JSON. Sample JMX opens in JMeter. Doc links resolve correctly
