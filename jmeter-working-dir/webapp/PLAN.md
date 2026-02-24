# PLAN.md — JMeter Test Dashboard Implementation Plan

## Summary

Build a self-contained FastAPI web dashboard that wraps all JMeter performance testing operations (config editing, slave management, test execution, results browsing) into a single UI. Deployed per-project, no database, fully file-based.

---

## Phase 1: Foundation & Project Setup

### 1.1 Scaffold the Project

- [ ] Create `webapp/requirements.txt` with dependencies:
  ```
  fastapi>=0.104.0
  uvicorn[standard]>=0.24.0
  jinja2>=3.1.0
  python-multipart>=0.0.6
  websockets>=12.0
  aiofiles>=23.0
  pandas>=2.0
  paramiko>=3.4
  scp>=0.14
  ```
- [ ] Create `webapp/main.py`:
  - FastAPI app instance
  - Mount static files at `/static`
  - Jinja2 template directory
  - Include all routers
  - Startup event: auto-detect project structure → generate `project.json` if missing
- [ ] Create `webapp/project.json` template (auto-generated):
  ```json
  {
    "name": "",
    "project_root": "..",
    "jmeter_path": "",
    "paths": {
      "jmx_dir": "",
      "config_dir": "",
      "config_properties": "",
      "results_dir": "",
      "test_data_dir": "",
      "scripts_dirs": [],
      "slaves_file": ""
    }
  }
  ```

### 1.2 Base Template & Layout

- [ ] Create `templates/base.html`:
  - Sidebar navigation (6 pages)
  - Top bar with project name (from `project.json`)
  - Content block
  - Toast notification area
  - Responsive layout (sidebar collapses on small screens)
- [ ] Create `static/css/style.css`:
  - CSS variables for colors/spacing (easy theming)
  - Sidebar styles
  - Card components
  - Table styles
  - Form styles
  - Button variants (primary, danger, outline)
  - Status badges (green/red/yellow)
  - Modal component
- [ ] Create `static/js/app.js`:
  - Toast notification helper
  - Fetch wrapper with error handling
  - WebSocket connection manager
  - Confirm dialog helper

### 1.3 Project Config Service

- [ ] Create `services/config_parser.py`:
  - `load_project_config()` — read `project.json`
  - `save_project_config(data)` — write `project.json`
  - `auto_detect_project()` — scan parent dir for known folders, populate `project.json`
  - `resolve_path(key)` — resolve relative path from `project.json` to absolute
  - `detect_jmeter_path()` — check PATH, common install dirs (Windows + Linux)
  - `read_config_properties(path)` — parse Java `.properties` format to dict
  - `write_config_properties(path, data)` — write dict back to `.properties`
  - `read_json_config(path)` — read JSON config file
  - `write_json_config(path, data)` — write JSON config file
  - `read_slaves_file(path)` — parse `slaves.txt` to list of IPs
  - `write_slaves_file(path, ips)` — write list of IPs to `slaves.txt`

---

## Phase 2: Dashboard Page

### 2.1 Dashboard Router & Template

- [ ] Create `routers/dashboard.py`:
  - `GET /` — render dashboard with:
    - Project name and root path
    - Quick stats: number of JMX files, number of result folders, number of slaves
    - Last test run info (most recent result folder — name, date, size)
    - Slave status summary (count of up/down if SSH is available)
    - Quick action buttons: Run Test, Open Results, Edit Config
- [ ] Create `templates/dashboard.html`:
  - Stats cards row (JMX count, results count, slaves count)
  - Last run card (folder name, date, link to results page)
  - Slave status card (list with green/red dots)
  - Quick actions card (buttons linking to other pages)

### 2.2 Dashboard API Endpoints

- [ ] `GET /api/dashboard/stats` — return project stats as JSON
- [ ] `GET /api/dashboard/last-run` — return most recent result folder info
- [ ] `GET /api/dashboard/slave-status` — return slave ping/SSH status (async, with timeout)

---

## Phase 3: Configuration Page

### 3.1 Config Router

- [ ] Create `routers/config.py`:
  - `GET /config` — render config page with tabs:
    - Tab 1: `config.properties` (key-value form)
    - Tab 2: `vm_config.json` (structured form)
    - Tab 3: `slaves.txt` (editable list with add/remove)
    - Tab 4: Settings / `project.json` (paths, JMeter location)

### 3.2 Config API Endpoints

- [ ] `GET /api/config/properties` — return config.properties as JSON
- [ ] `PUT /api/config/properties` — save config.properties from JSON
- [ ] `GET /api/config/vm` — return vm_config.json
- [ ] `PUT /api/config/vm` — save vm_config.json
- [ ] `GET /api/config/slaves` — return slaves list
- [ ] `PUT /api/config/slaves` — save slaves list
- [ ] `GET /api/config/project` — return project.json
- [ ] `PUT /api/config/project` — save project.json
- [ ] `POST /api/config/detect-jmeter` — auto-detect JMeter installation path

### 3.3 Config Template

- [ ] Create `templates/configuration.html`:
  - Tabbed interface
  - config.properties: dynamic key-value rows, add/remove fields, save button
  - vm_config.json: structured form (SSH section, split section, scripts section)
  - slaves.txt: sortable list, add IP button, remove button per row, bulk edit textarea toggle
  - Settings: JMeter path with browse/detect button, folder path mappings

---

## Phase 4: Test Data Page

### 4.1 Data Service

- [ ] Create `services/data.py`:
  - `generate_master_data(config_path)` — run generate_master_data.py as subprocess
  - `preview_csv(file_path, rows=50)` — read first N rows of CSV
  - `get_csv_stats(file_path)` — row count, column names, file size
  - `split_data(master_csv, slave_ips, offset, size)` — split CSV for distribution
  - `distribute_data(slave_ips, local_splits, ssh_config)` — SCP files to VMs
  - These wrap existing Python utilities where possible (import or subprocess)

### 4.2 Data Router

- [ ] Create `routers/test_data.py`:
  - `GET /data` — render test data page
  - `POST /api/data/generate` — trigger master data generation (returns task ID)
  - `GET /api/data/preview/{filename}` — preview CSV file
  - `GET /api/data/files` — list CSV files in test_data/
  - `POST /api/data/split` — split master CSV (params: offset, size)
  - `POST /api/data/distribute` — distribute to slaves (SCP)
  - `GET /api/data/status/{task_id}` — check async task status

### 4.3 Data Template

- [ ] Create `templates/test_data.html`:
  - Section: Master Data — file info, [Generate] button, [Preview] button
  - Section: Split & Distribute — offset/size inputs, slave list with row counts, [Split] → [Distribute]
  - Section: CSV Browser — list all CSVs in test_data/, click to preview
  - Preview modal: table view of first 50 rows
  - Progress indicators for generate/split/distribute operations

---

## Phase 5: Test Plans & Runner Page

### 5.1 JMeter Service

- [ ] Create `services/jmeter.py`:
  - `list_jmx_files(jmx_dir)` — find all .jmx files
  - `extract_jmx_params(jmx_path)` — parse JMX XML, find `__P()` and `__property()` calls, extract param names and defaults
  - `open_in_jmeter(jmeter_path, jmx_path)` — launch JMeter GUI with test plan (subprocess, non-blocking)
  - `build_jmeter_command(config, jmx_path, slaves, result_dir)` — build CLI command from config (see CLI Mapping below)
  - `run_test(jmx_path, params, slaves, result_dir)` — execute JMeter in non-GUI mode
  - `stop_test(process)` — gracefully stop running test
  - `get_running_test()` — check if a test is currently running

#### CLI Mapping (Convention-Based)

`config.properties` uses a convention: reserved keys map to direct JMeter args, everything else is sent as `-G` (global property to slaves).

**Reserved keys** (direct JMeter args, NOT sent as -G):

| Key | Maps to | Example |
|-----|---------|---------|
| `test_plan` | `-t <path>` | `test_plan/MAYA-Student-v9.jmx` |

**All other keys** → sent as `-G{key}={value}` (including CSV paths):

```properties
# CSV paths — sent as -G, JMX references via __P()
# Supports multiple CSV Data Set Configs, each with its own key
student_csv=test_data/student_data.csv
lecturer_csv=test_data/lecturer_data.csv

# Test parameters
student=15000
rampUp=300
loop=1
thinkTime=3000
logout=true
runId=STE010
syncTimer=false
dynatrace.tsn=MAYA-Student
dynatrace.lsn=CE-01-Enrolment
```

**Adding new properties**: Any new key added via the Config page automatically becomes a `-G` flag. No code changes needed — the webapp iterates all non-reserved keys and passes them as `-G`.

**Command preview**: The Runner UI shows the full generated command before execution so the user can verify.

### 5.2 Process Manager

- [ ] Create `services/process_manager.py`:
  - `run_process(cmd, cwd)` — run subprocess, return process handle
  - `stream_output(process)` — async generator yielding stdout/stderr lines
  - `kill_process(process)` — terminate subprocess
  - Track active processes (only one JMeter test at a time)

### 5.3 Runner Router

- [ ] Create `routers/test_plans.py`:
  - `GET /plans` — render test plans & runner page
  - `GET /api/plans/list` — list JMX files with metadata
  - `GET /api/plans/{filename}/params` — extract parameters from JMX
  - `POST /api/plans/{filename}/open` — open in JMeter GUI
  - `POST /api/runner/start` — start test execution
  - `POST /api/runner/stop` — stop running test
  - `GET /api/runner/status` — check if test is running
  - `WebSocket /ws/runner/logs` — live log stream

### 5.4 Test Presets

- [ ] Presets stored in `webapp/presets.json`:
  ```json
  {
    "Baseline": {"student": 10, "rampUp": 10, "loop": 1, "thinkTime": 3000},
    "Stress": {"student": 100, "rampUp": 60, "loop": 1, "thinkTime": 500},
    "Spike": {"student": 500, "rampUp": 30, "loop": 1, "thinkTime": 100, "syncTimer": true}
  }
  ```
- [ ] `GET /api/runner/presets` — list saved presets
- [ ] `POST /api/runner/presets` — save new preset
- [ ] `DELETE /api/runner/presets/{name}` — delete preset

### 5.5 Test Plans & Runner Template

- [ ] Create `templates/test_plans.html`:
  - **Top section — Test Plans table:**
    - Columns: filename, detected params count, file size, last modified
    - Action buttons: [Edit] (opens JMeter), [Run] (scrolls to runner with script pre-selected)
  - **Bottom section — Test Runner:**
    - Script selector (dropdown, pre-filled if [Run] was clicked)
    - Parameter form (dynamically populated from JMX params)
    - Preset selector (dropdown) + [Save as Preset] button
    - Slave selection (checkboxes from slaves.txt, or "local only")
    - [Start Test] / [Stop Test] buttons
    - Live log output area (monospace, auto-scroll, WebSocket-fed)
    - Status indicator (idle / running / completed / error)

---

## Phase 6: Results Page

### 6.1 JTL Parser Service

- [ ] Create `services/jtl_parser.py`:
  - `list_result_folders(results_dir)` — list folders sorted by date (newest first)
  - `get_folder_info(folder_path)` — size, file count, has HTML report, has JTL
  - `parse_jtl(jtl_path)` — read JTL CSV with pandas, return:
    - Total samples
    - Average response time
    - Median (p50)
    - 90th percentile (p90)
    - 95th percentile (p95)
    - 99th percentile (p99)
    - Min / Max
    - Error count and error %
    - Throughput (requests/sec)
    - Per-transaction breakdown (group by label)
  - `compare_runs(jtl_path_1, jtl_path_2)` — side-by-side stats comparison

### 6.2 Results Router

- [ ] Create `routers/results.py`:
  - `GET /results` — render results page
  - `GET /api/results/list` — list result folders with metadata
  - `GET /api/results/{folder}/stats` — JTL summary stats
  - `GET /api/results/{folder}/report` — serve HTML report (iframe-compatible)
  - `GET /api/results/{folder}/open` — open folder in OS file explorer
  - `GET /api/results/compare` — compare two result folders (query params: folder1, folder2)

### 6.3 Results Template

- [ ] Create `templates/results.html`:
  - **Results list table:**
    - Columns: folder name, date, size, has report, has JTL
    - Actions: [View Report] [Stats] [Open Folder] [Compare]
  - **Stats modal/panel:**
    - Summary stats table (avg, p50, p90, p95, p99, error %, throughput)
    - Per-transaction breakdown table
  - **Report viewer:**
    - Embedded iframe showing JMeter HTML report
    - Full-screen toggle
  - **Compare view:**
    - Two-column layout
    - Select run A and run B from dropdowns
    - Side-by-side stats with diff highlighting (green = improved, red = degraded)

---

## Phase 7: Custom Scripts Page

### 7.1 Scripts Router

- [ ] Create `routers/scripts.py`:
  - `GET /scripts` — render scripts page
  - `GET /api/scripts/list` — discover .py and .bat files in configured script dirs
  - `POST /api/scripts/run` — execute script as subprocess
  - `WebSocket /ws/scripts/output` — live output stream for running script

### 7.2 Scripts Template

- [ ] Create `templates/scripts.html` (can be minimal):
  - Grouped by directory (bin/data/, bin/jmeter/, utils/)
  - Each script: filename, type (.py/.bat), [Run] button
  - Output panel (like runner log panel)
  - Status per script (idle / running / last run result)

---

## Phase 8: Slave Management (within Configuration + Dashboard)

### 8.1 Slaves Service

- [ ] Create `services/slaves.py`:
  - `check_slave_status(ip, ssh_config)` — SSH connect test, return up/down
  - `check_all_slaves(slave_ips, ssh_config)` — parallel status check
  - `start_jmeter_server(ip, ssh_config, script_path)` — SSH run start script
  - `stop_jmeter_server(ip, ssh_config, script_path)` — SSH run stop script
  - `start_all_servers(slave_ips, ssh_config)` — parallel start
  - `stop_all_servers(slave_ips, ssh_config)` — parallel stop
  - `get_server_log(ip, ssh_config, log_path, tail_lines)` — tail remote log

### 8.2 Slave API Endpoints (under /api/config/slaves/)

- [ ] `GET /api/slaves/status` — status of all slaves
- [ ] `POST /api/slaves/start` — start JMeter servers (all or specific IPs)
- [ ] `POST /api/slaves/stop` — stop JMeter servers
- [ ] `GET /api/slaves/{ip}/log` — tail remote server log

These endpoints are consumed by both the Dashboard (status card) and Configuration (slave management tab) pages.

---

## Phase 9: Polish & First-Run Experience

### 9.1 First-Run Setup Wizard

- [ ] On first launch (no `project.json`):
  1. Welcome screen — "JMeter Test Dashboard"
  2. Auto-detect: scan parent directory, show discovered paths
  3. JMeter path: auto-detect or manual input
  4. Project name: suggest from folder name
  5. Confirm and save → redirect to Dashboard

### 9.2 Error Handling & UX

- [ ] Global error handler — return user-friendly messages
- [ ] Loading spinners for async operations
- [ ] Toast notifications for success/error feedback
- [ ] Confirm dialogs for destructive actions (stop test, overwrite config)
- [ ] Empty states — show helpful messages when no JMX files, no results, etc.

### 9.3 Security Considerations

- [ ] Validate all file paths — prevent path traversal (no `../../etc/passwd`)
- [ ] Sanitize subprocess arguments — prevent command injection
- [ ] Bind to localhost by default (solo use, no auth needed)
- [ ] Do not expose SSH passwords in API responses

---

## Phase 10: Analysis Engine (Rule-Based + Ollama AI)

**Data Classification: PNC (Private and Confidential)** — All analysis runs locally. No data leaves the machine. Ollama runs on-premise, no cloud API calls.

### 10.1 JTL Pre-Processor

- [ ] Create `services/analysis.py`:
  - `preprocess_jtl(jtl_path)` — parse raw JTL (potentially millions of rows) into compact summary (~2-4KB):
    ```python
    {
      "test_info": {
        "run_id": "STE010",
        "date": "2026-02-20",
        "duration_sec": 300,
        "total_samples": 312000,
        "total_users": 15000
      },
      "overall": {
        "avg_rt": 1240,
        "p50": 890, "p90": 2100, "p95": 3400, "p99": 8200,
        "min": 45, "max": 32000,
        "error_rate": 2.3,
        "throughput": 420.5
      },
      "per_transaction": [
        {
          "label": "POST /SIW_LGN",
          "samples": 15000,
          "avg": 2400, "p95": 8400,
          "error_rate": 4.1,
          "errors": {"503": 312, "timeout": 45}
        }
      ],
      "time_series": {
        "intervals": ["0-30s", "30-60s", "60-90s"],
        "active_threads": [500, 2000, 5000, 8000],
        "avg_response_time": [200, 400, 600, 900],
        "throughput": [150, 300, 400, 420],
        "error_count": [0, 0, 2, 5]
      },
      "anomalies": [
        {"time": "03:12", "type": "error_spike", "label": "POST /SIW_LGN", "count": 45},
        {"time": "02:30", "type": "rt_jump", "label": "GET /siw_portal", "from": 800, "to": 3200}
      ]
    }
    ```
  - Handles JTL files of any size efficiently (chunked pandas reading)
  - Produces fixed-size output regardless of input size

### 10.2 Rule-Based Analysis (Always Available, Free)

- [ ] `rule_based_analysis(summary)` — programmatic pattern detection:
  - **Bottleneck detection**: p95 > 3x median → flag transaction
  - **Error threshold**: error rate > 5% → critical, > 2% → warning
  - **Throughput saturation**: detect plateau (slope ≈ 0 while users increasing)
  - **Response time degradation**: RT increasing with thread count → find inflection point
  - **Outlier detection**: values beyond 2 standard deviations
  - **Error clustering**: errors concentrated in specific time window
  - Returns structured findings:
    ```python
    {
      "severity": "warning",  # info / warning / critical
      "bottlenecks": [...],
      "degradation_point": {"users": 8200, "rt_jump": "1.2s → 8.4s"},
      "error_patterns": [...],
      "recommendations": [...]
    }
    ```

### 10.3 Ollama AI Analysis (Optional, Local, PNC-Safe)

- [ ] `ai_analysis(summary, system_context, previous_run)` — deep analysis via local Ollama:
  - Connects to Ollama HTTP API (`http://localhost:11434/api/generate`)
  - Uses configurable model (default: `llama3.1:8b` or `mistral`)
  - Sends pre-processed summary only (~2-4KB), never raw JTL data
  - Prompt template includes:
    - Pre-processed test summary
    - System context from `project.json` (e.g., infrastructure details)
    - Previous run summary for comparison (if available)
    - Instruction: analyze bottlenecks, explain degradation, give recommendations
  - Returns natural language report (markdown)
  - Graceful fallback: if Ollama is not running, show rule-based results only
- [ ] `check_ollama_status()` — verify Ollama is running and model is available
- [ ] `list_ollama_models()` — list installed models for selection

### 10.4 Comparison Analysis

- [ ] `compare_analysis(summary_a, summary_b)` — compare two runs:
  - Percentage diff per transaction (avg, p95, error rate, throughput)
  - Highlight improvements (green) and regressions (red)
  - Rule-based: flag any metric that degraded > 20%
  - Ollama (optional): explain likely causes of differences

### 10.5 Analysis API Endpoints

- [ ] `POST /api/results/{folder}/analyze` — run analysis on a result folder
  - Query param: `mode=rules` (default) or `mode=ai`
  - Returns: combined rule-based findings + AI report (if enabled)
- [ ] `GET /api/results/{folder}/analysis` — get cached analysis (if previously run)
- [ ] `POST /api/results/compare-analysis` — compare two runs with analysis
- [ ] `GET /api/analysis/ollama-status` — check if Ollama is available
- [ ] `GET /api/analysis/ollama-models` — list available models

### 10.6 Analysis UI (on Results Page)

- [ ] Add [Analyze] button to each result row
- [ ] Analysis panel (slides open or modal):
  - **Rule-based section** (always shown):
    - Severity badge (info/warning/critical)
    - Bottlenecks table with flagged transactions
    - Degradation point indicator
    - Error pattern summary
    - Recommendations list
  - **AI Insights section** (shown if Ollama available):
    - Toggle: "Enable AI Analysis (Ollama)"
    - Model selector dropdown
    - [Generate AI Report] button
    - Markdown-rendered AI analysis report
    - Loading state while Ollama generates
- [ ] Cache analysis results to `results/{folder}/analysis.json` to avoid re-processing

### 10.7 Configuration (in project.json)

```json
{
  "analysis": {
    "ollama": {
      "enabled": true,
      "base_url": "http://localhost:11434",
      "model": "llama3.1:8b",
      "timeout": 120
    },
    "system_context": "SITS:Vision on OCI. 4 IIS, 16 Tomcat (16-32GB heap), 2 Oracle RAC, 420 uservers per VM. LDAP auth.",
    "rules": {
      "bottleneck_threshold": 3.0,
      "error_warning_pct": 2.0,
      "error_critical_pct": 5.0,
      "degradation_threshold_pct": 20.0
    }
  }
}
```

### 10.8 Analysis Prompt Template

- [ ] Create `webapp/prompts/analysis.txt`:
  ```
  You are a performance testing expert analyzing JMeter load test results.

  ## System Under Test
  {system_context}

  ## Test Summary
  {summary_json}

  ## Previous Run (for comparison)
  {previous_summary_json}

  ## Task
  Analyze the test results and provide:
  1. Executive summary (2-3 sentences)
  2. Bottlenecks identified (with evidence from the data)
  3. Degradation analysis (at what load did performance degrade, and why)
  4. Error analysis (patterns, root causes)
  5. Comparison with previous run (if provided)
  6. Actionable recommendations (specific, prioritized)

  Keep the analysis concise and actionable. Reference specific numbers from the data.
  ```

---

## Implementation Order (Recommended)

Build in this order to get a usable app as early as possible:

| Step | What | Why First |
|------|------|-----------|
| 1 | Phase 1 (Foundation) | Everything depends on this |
| 2 | Phase 3 (Configuration) | Need config editing to set up project |
| 3 | Phase 5 (Test Plans & Runner) | Core feature — running tests |
| 4 | Phase 6 (Results) | See test output |
| 5 | Phase 2 (Dashboard) | Now there's data to show |
| 6 | Phase 4 (Test Data) | Data management |
| 7 | Phase 8 (Slave Management) | Infrastructure ops |
| 8 | Phase 7 (Custom Scripts) | Nice to have |
| 9 | Phase 9 (Polish) | Final touches |
| 10 | Phase 10 (Analysis Engine) | Rule-based + Ollama AI insights |

---

## File Inventory (Final)

```
webapp/
├── main.py
├── requirements.txt
├── project.json
├── presets.json
├── CLAUDE.md
├── PLAN.md
├── routers/
│   ├── __init__.py
│   ├── dashboard.py
│   ├── config.py
│   ├── test_data.py
│   ├── test_plans.py
│   ├── results.py
│   └── scripts.py
├── services/
│   ├── __init__.py
│   ├── config_parser.py
│   ├── jmeter.py
│   ├── jtl_parser.py
│   ├── analysis.py
│   ├── data.py
│   ├── slaves.py
│   └── process_manager.py
├── prompts/
│   └── analysis.txt
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── app.js
│   └── img/
│       └── logo.svg (optional)
├── templates/
│   ├── base.html
│   ├── setup.html
│   ├── dashboard.html
│   ├── configuration.html
│   ├── test_data.html
│   ├── test_plans.html
│   └── results.html
└── scripts.html (templates/)
```

Total: ~28 files to create.

---

## Tech Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | FastAPI | Async, WebSocket support, already using Python |
| Frontend | Vanilla JS + Jinja2 | Simple, no build step, fast to develop |
| Database | None (file-based) | All data already exists as files |
| CSS | Custom + CSS variables | No dependency, easy theming |
| Deployment | `uvicorn main:app` | Single command, no Docker needed |
| Auth | None | Solo use on localhost |
| State | File system | Results dirs = run history, configs = state |
| AI | Ollama (local) | PNC data — no cloud APIs, all analysis stays on-premise |
| Analysis | Rule-based + AI hybrid | Rules always work (free), AI is optional enhancement |

---

## Phase 11: Settings Page (DONE)

- [x] Create `routers/settings.py` — settings CRUD with file-based storage (`settings.json`)
- [x] Create `templates/settings.html` — Settings UI
- [x] `settings.json` auto-created on first save, merged with defaults on load
- [x] Sections:
  - **Server**: domain, port, allow external access (0.0.0.0), restart button
  - **Appearance**: dark/light theme (CSS custom properties), sidebar collapsed default
  - **Test Runner**: auto-scroll, max log lines, confirm before stop
  - **Results**: default sort order
  - **Target Endpoints**: dynamic list of name+URL pairs (MAYA prod, PREP, cloudunity)
  - **AI Analysis (Ollama)**: base URL, model, timeout, test connection button
- [x] Dark theme via `[data-theme="dark"]` CSS variables in `style.css`
- [x] Theme persisted in `localStorage`, applied on page load from `app.js`
- [x] Server restart via `/api/server/restart` — spawns new uvicorn process, exits old one
- [x] `__main__.py` entry point — `python -m webapp` reads settings.json for host/port

## Phase 12: Slave VMs Page (DONE)

- [x] Add `GET /slaves` route to `config.py` router
- [x] Create `templates/slaves.html` — VM status panel
- [x] Add "Slave VMs" nav item to sidebar in `base.html`
- [x] Features:
  - Summary bar: total VMs, online count, offline count (colored badges)
  - VM card grid: IP, status dot (green/red/amber), status badge, error message
  - **Refresh**: re-checks SSH connectivity to all VMs in parallel
  - **Start All**: starts JMeter servers on all slaves, auto-refreshes after 3s
  - **Stop All**: stops JMeter servers on all slaves (with confirmation)
  - Auto-checks status on page load
- [x] Uses existing APIs: `/api/slaves/status`, `/api/slaves/start`, `/api/slaves/stop`

---

## Future Enhancements (Post-v1)

### F1: InfluxDB + Grafana Real-Time Monitoring

Deploy on-premise InfluxDB and Grafana for real-time test monitoring.

- [ ] **InfluxDB Backend Listener config** — manage plugin settings from Configuration page
- [ ] **JMX patching for dynamic fields** — the InfluxDB2 Listener plugin ([mderevyankoaqa/jmeter-influxdb2-listener-plugin](https://github.com/mderevyankoaqa/jmeter-influxdb2-listener-plugin)) does not reliably resolve `__P()` in its config fields (confirmed in [issue #20](https://github.com/mderevyankoaqa/jmeter-influxdb2-listener-plugin/issues/20)). The webapp should:
  - Parse the JMX XML before each run
  - Find the Backend Listener element (`InfluxDatabaseBackendListenerClient`)
  - Patch dynamic fields (e.g., `runId`, `testTitle`) with values from the Runner UI
  - Save patched JMX (temp copy or in-place with backup)
  - Run JMeter with the patched JMX — slaves receive correct values via RMI serialization
  - This bypasses the `__P()` resolution issue entirely
- [ ] **Grafana dashboard embed** — iframe or link to Grafana from Dashboard page
- [ ] **InfluxDB connection test** — verify connectivity from Configuration page

#### JMX Patching Implementation Detail

```python
# services/jmeter.py — patch_jmx_backend_listener()
import xml.etree.ElementTree as ET

def patch_jmx(jmx_path, patches: dict) -> str:
    """
    Patch Backend Listener fields in JMX before run.
    patches = {"runId": "STE010", "testTitle": "Stress Test 10"}
    Returns path to patched JMX (temp file).
    """
    tree = ET.parse(jmx_path)
    # Find BackendListener elements
    # Update <stringProp name="runId">...</stringProp>
    # Save to temp file
    # Return temp path
```

#### InfluxDB Configuration (in project.json)

```json
{
  "influxdb": {
    "enabled": false,
    "url": "http://localhost:8086",
    "org": "perftest",
    "bucket": "jmeter",
    "token": "",
    "grafana_url": "http://localhost:3000/d/jmeter"
  }
}
```

### F2: Trend Analysis Across Multiple Runs

- [ ] Track metrics across all runs — build trend data from cached `analysis.json` files
- [ ] Line charts: p95 response time over test runs, throughput trends, error rate trends
- [ ] Detect performance regressions across releases

### F3: Dedicated Analysis Page with Chat

- [ ] Upgrade from [Analyze] button to full page (`/analysis`)
- [ ] Chat-style follow-up questions to Ollama ("why did login degrade?", "what changed since last run?")
- [ ] Auto-analysis triggered on test completion
- [ ] Multi-run trend analysis with AI commentary

### F4: Result Config Summary

- [ ] Store test parameters (threads, ramp-up, think time, plan name, etc.) with each result
- [ ] Display config summary on results list for easy differentiation between date-based result names

### F5: Result Tagging / Labeling

- [ ] Add clickable tags to results (e.g. "baseline", "stress", "after-fix", "v2")
- [ ] Filter results by tag
- [ ] Useful for finding specific runs among 50+ results

### F6: Health Check for Target Endpoints

- [ ] Ping button per endpoint in Settings or Dashboard
- [ ] Show reachability status and response time

### F7: Browser Notifications

- [ ] Browser push notifications for: test completed, test failed/errored
- [ ] Notification when test exceeds a duration threshold
- [ ] Works even when user is in another tab or app

### F8: Keyboard Shortcuts

- [ ] `Ctrl+Enter` to start test, `Ctrl+.` to stop
- [ ] `Ctrl+,` to open settings
- [ ] Number keys (`1-8`) to switch pages

### F9: DOCX Report Export

- [ ] Export result summaries as DOCX for sharing with stakeholders
- [ ] Details TBD

### F10: Compare Results (Summary View)

- [ ] Side-by-side comparison of two test runs
- [ ] Summary-only view to spot regressions quickly

---

## Phase 13: Webapp Amendments (Pre-Generalization)

**Goal**: Stabilize and improve the webapp before generalizing it into the toolkit. These changes address usability gaps, access control, and missing features identified during review.

**Status**: Pending — do this before toolkit Phase 3 (Webapp Generalization).

---

### 13.1 Access Control — Token-Based Auth (Cookie)

**Scope**: Medium | **Files**: `main.py`, `services/auth.py` (new), `templates/token.html` (new), `settings.json`

**Problem**: Webapp will be accessed remotely. Need read-only for viewers, full access for admins.

**Design**:
- Add `auth_token` field to `settings.json` (empty = no auth required)
- New `services/auth.py`:
  - `verify_token(token)` — check against `settings.json`
  - `is_localhost(request)` — check if `request.client.host` is `127.0.0.1` or `::1`
  - `get_access_level(request)` → `"admin"` | `"viewer"` | `"unauthorized"`
    - Localhost → always admin
    - Valid token cookie → admin
    - No token, remote → viewer (read-only)
- FastAPI middleware on every request:
  - If `auth_token` is set and request is remote and no valid cookie → show token entry page
  - Set `request.state.access_level` for use in routers/templates
- Token entry page (`templates/token.html`):
  - Simple form: "Enter access token"
  - On submit → set `jmeter_token` cookie, redirect to original URL
- Templates receive `access_level` via Jinja2 context:
  - `viewer`: hide Run, Stop, Edit Config, Start/Stop Slaves buttons
  - `admin`: full access

---

### 13.2 Conditional Edit Button — Localhost Only

**Scope**: Small | **Files**: `routers/test_plans.py`, `templates/test_plans.html`

**Problem**: "Edit in JMeter GUI" spawns a local process. From a remote browser, this opens JMeter on the server with no display, creating zombie processes.

**Changes**:
- Pass `is_localhost` flag to template context in `GET /plans`
- In `test_plans.html`: wrap Edit button in `{% if is_localhost %}` block
- In `POST /api/plans/{filename}/open`: reject with 403 if not localhost

---

### 13.3 Scripts Page — Hidden, Localhost Only

**Scope**: Small | **Files**: `main.py`, `templates/base.html`, `routers/scripts.py`

**Changes**:
- In `base.html`: wrap Scripts nav item in `{% if is_localhost %}` block
- In `routers/scripts.py`: all endpoints check `is_localhost`, return 403 for remote
- Scripts page still exists at `/scripts` but is invisible and inaccessible to remote users

---

### 13.4 Remove Endpoints from Settings

**Scope**: Small | **Files**: `routers/settings.py`, `templates/settings.html`

**Problem**: Target endpoints section is MAYA-specific and not needed in the generalized version.

**Changes**:
- Remove `endpoints` from `DEFAULT_SETTINGS` in `settings.py`
- Remove endpoints section from `settings.html` template
- Remove related API handlers (`/api/settings/endpoints` if separate)
- Leave `settings.json` backward-compatible (ignore `endpoints` key if present)

---

### 13.5 Settings: System Info Section

**Scope**: Small | **Files**: `routers/settings.py`, `templates/settings.html`

**Changes**:
- Add `GET /api/settings/system-info` endpoint:
  - JMeter version: run `jmeter --version` and parse output
  - Java version: run `java -version` and parse
  - Python version: `sys.version`
  - Disk space: `shutil.disk_usage()` on results directory
  - OS: `platform.platform()`
- Add "System Information" section to `settings.html`:
  - Read-only cards showing each value
  - Load on page open via API call

---

### 13.6 Local Mode — Support Running Without Slaves

**Scope**: Small | **Files**: `services/jmeter.py`, `templates/test_plans.html`

**Problem**: Runner always builds `-R <slaves>` command. Should work without slaves for local testing.

**Changes**:
- In `jmeter.py` `build_jmeter_command()`:
  - If slave list is empty → omit `-R` flag entirely
  - Command becomes: `jmeter -n -t <plan> -G<params> -l <jtl> -e -o <report>`
- In `test_plans.html`:
  - Show "Local mode (no slaves)" indicator when slaves list is empty
  - Runner UI still works — just no slave selection section

---

### 13.7 Slaves Enable/Disable Toggle

**Scope**: Medium | **Files**: `services/config_parser.py`, `routers/config.py`, `templates/slaves.html`, `services/jmeter.py`

**Problem**: Currently slaves are add/remove only. Removing loses the IP; re-adding is tedious.

**Design**:
- Change slaves storage from plain text list to JSON:
  ```json
  [
    {"ip": "10.0.0.1", "enabled": true},
    {"ip": "10.0.0.2", "enabled": false},
    {"ip": "10.0.0.3", "enabled": true}
  ]
  ```
- Backward compatibility: if `slaves.txt` exists (plain text), migrate to JSON format on first read
- In `config_parser.py`:
  - `read_slaves()` → returns full list with enabled flags
  - `get_active_slaves()` → returns only enabled IPs
  - `write_slaves()` → saves JSON format
- In `slaves.html`:
  - Toggle switch per slave row (enabled/disabled)
  - Disabled slaves shown greyed out
  - Start/Stop only applies to enabled slaves
- In `jmeter.py`:
  - `build_jmeter_command()` uses `get_active_slaves()` for `-R` flag

---

### 13.8 Filter Username Toggle on Runner

**Scope**: Small | **Files**: `routers/test_plans.py`, `templates/test_plans.html`, `services/jmeter.py`

**Problem**: Username filtering in JTL is hardcoded. Should be optional at run time.

**Changes**:
- Add checkbox to runner UI: "Filter usernames from results" (default: checked)
- Pass `filter_usernames` flag in `POST /api/runner/start` body
- In run chain (Python, not batch):
  1. Run JMeter → raw `.jtl`
  2. If `filter_usernames` → run `filter_jtl.py` → filtered `.jtl`
  3. Generate HTML report from final `.jtl`
- All three steps chained in Python via `subprocess.run()` — no batch nesting issues

---

### 13.9 Save Config Snapshot Per Run

**Scope**: Small | **Files**: `services/jmeter.py`

**Problem**: No record of what config was used for each test run. Can't compare settings between runs.

**Changes**:
- After creating the timestamped results folder, before launching JMeter:
  - Copy `config.properties` → `results/YYYYMMDD_N/config.properties`
  - Write `results/YYYYMMDD_N/run_info.json`:
    ```json
    {
      "timestamp": "2026-02-22T14:30:00",
      "test_plan": "test_plan/MAYA-Student-v9.jmx",
      "slaves": ["10.0.0.1", "10.0.0.3"],
      "mode": "distributed",
      "params": {"student": 15000, "rampUp": 300, "loop": 1},
      "filter_usernames": true,
      "triggered_by": "webapp"
    }
    ```
- On results page: show config summary badge/tooltip for each run

---

### 13.10 JTL Filter + Report Regeneration on Results Page

**Scope**: Medium | **Files**: `routers/results.py`, `templates/results.html`, `services/jtl_parser.py`

**Problem**: Can't re-filter or regenerate reports for old results.

**Changes**:
- Add "Regenerate Report" button per result row
- On click → modal with filter options:
  - Checkbox: exclude `${USERNAME}` entries
  - Checkbox: exclude embedded resources
  - Text input: label regex pattern (optional)
- `POST /api/results/{folder}/regenerate`:
  - Run `filter_jtl.py` with selected filters → produce filtered `.jtl`
  - Run `jmeter -g filtered.jtl -o report/` → regenerate HTML report
  - Return success with link to new report
- Show progress/status during regeneration

---

### 13.11 Report Open in New Tab

**Scope**: Small | **Files**: `templates/results.html`

**Changes**:
- Add "Open in New Tab" button next to the existing overlay/iframe view
- Button: `<a href="/api/results/{folder}/report/index.html" target="_blank">`
- Path is already known from the iframe `src` — just expose it as a link

---

### 13.12 Results Comparison — Finish Stubbed View

**Scope**: Medium | **Files**: `templates/results.html`, `routers/results.py`, `services/jtl_parser.py`

**Problem**: `compareSelected()` function exists but diff rendering is incomplete.

**Changes**:
- Complete `compareSelected()` JavaScript:
  - Fetch stats for both selected runs via `/api/results/{folder}/stats`
  - Render side-by-side table with columns: Metric | Run A | Run B | Diff
  - Color coding: green = improved (lower RT, higher throughput), red = degraded
- Include per-transaction breakdown comparison
- Show config diff if `run_info.json` exists for both (from 13.9)

---

### 13.13 Analysis Cache — Finish Incomplete Functions

**Scope**: Small | **Files**: `services/analysis.py`

**Problem**: `load_cached_analysis()` and `save_analysis_cache()` are referenced but not fully implemented. Each Analyze click re-processes the full JTL.

**Changes**:
- `save_analysis_cache(folder_path, analysis_data)`:
  - Write to `results/{folder}/analysis.json`
- `load_cached_analysis(folder_path)`:
  - Read `results/{folder}/analysis.json` if exists
  - Return `None` if missing or older than the JTL file
- In `/api/results/{folder}/analyze`:
  - Check cache first → return cached if valid
  - Otherwise run analysis → save cache → return

---

### 13.14 Dashboard Enhancements

**Scope**: Small | **Files**: `routers/dashboard.py`, `templates/dashboard.html`

**Changes**:
- **Grafana/InfluxDB quick links**:
  - Read URLs from `settings.json` (or `project.json`)
  - Show as cards — greyed out with "Not configured" if URLs are empty
  - Clickable (opens new tab) when configured
- **Run card improvements**:
  - Show currently selected test plan name
  - Show thread count and active slave count
  - Show mode: "Distributed (3 slaves)" or "Local mode"
  - Quick-launch button to /plans page

---

### 13.15 Live Logs: Auto-Scroll + Summary Panel

**Scope**: Medium | **Files**: `templates/test_plans.html`, `static/js/app.js`

**Changes**:
- **Auto-scroll**: scroll log container to bottom on each WebSocket message
  - Add toggle: "Auto-scroll" checkbox (default on), user can disable to read earlier output
- **Live summary panel** above the raw logs:
  - Parse `summary +` lines from JMeter output via regex:
    ```
    summary +  500 in 00:00:30 = 16.7/s Avg: 1200 Min: 50 Max: 5000 Err: 2 (0.40%)
    ```
  - Update cards in real-time: Throughput | Avg RT | Error Rate | Total Samples
  - Parse slave start/finished lines for per-slave progress (#13.16)

---

### 13.16 Slave Progress During Test

**Scope**: Medium | **Files**: `templates/test_plans.html`, `static/js/app.js`

**Problem**: During distributed tests, no visibility into which slaves have finished.

**Changes**:
- Parse WebSocket log stream for slave lifecycle lines:
  - `Starting the test on 10.0.0.1:1099` → mark slave as "Running"
  - `Finished the test on 10.0.0.1:1099` → mark slave as "Finished"
  - Connection errors → mark slave as "Error"
- Show slave progress panel (part of the live summary in 13.15):
  - Table or pill badges: IP | Status (Running / Finished / Error)
  - Counter: "3/5 slaves finished"
- Only visible during distributed runs (hidden in local mode)

---

### Implementation Order

Build in dependency order, grouping related changes:

| Step | Items | Description | Depends On |
|------|-------|-------------|------------|
| 1 | 13.1 | Access control (token/cookie auth) | — |
| 2 | 13.2, 13.3 | Localhost-only features (edit button, scripts page) | 13.1 |
| 3 | 13.4, 13.5 | Settings cleanup (remove endpoints, add system info) | — |
| 4 | 13.7 | Slaves enable/disable toggle | — |
| 5 | 13.6 | Local mode support | 13.7 (needs active slaves logic) |
| 6 | 13.8, 13.9 | Runner improvements (filter toggle, config snapshot) | — |
| 7 | 13.10, 13.11 | Results: regenerate reports, open in new tab | — |
| 8 | 13.12, 13.13 | Results: comparison view, analysis cache | — |
| 9 | 13.14 | Dashboard enhancements | — |
| 10 | 13.15, 13.16 | Live logs: summary panel, auto-scroll, slave progress | — |

---

### Phase 13 Status

| # | Item | Status |
|---|------|--------|
| 13.1 | Token-based access control | Pending |
| 13.2 | Conditional edit button | Pending |
| 13.3 | Scripts page hidden | Pending |
| 13.4 | Remove endpoints | Pending |
| 13.5 | System info in settings | Pending |
| 13.6 | Local mode | Pending |
| 13.7 | Slaves enable/disable | Pending |
| 13.8 | Filter username toggle | Pending |
| 13.9 | Config snapshot per run | Pending |
| 13.10 | JTL filter + report regen | Pending |
| 13.11 | Report open in new tab | Pending |
| 13.12 | Results comparison | Pending |
| 13.13 | Analysis cache | Pending |
| 13.14 | Dashboard enhancements | Pending |
| 13.15 | Live logs: auto-scroll + summary | Pending |
| 13.16 | Slave progress during test | Pending |
