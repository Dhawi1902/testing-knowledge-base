# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Performance testing project for **MAYA Portal** (Universiti Malaya's Academic Portal - SITS:Vision system). The goal is to create and execute JMeter scripts for load testing critical user workflows.

## Target Application

- **Production URL**: `https://maya-cloud.um.edu.my/sitsvision/wrd/siw_lgn`
- **PREP Environment**: `https://printis-prep.um.edu.my/sitsvision/wrd/siw_lgn`
- **Report Viewer**: `https://cloudunity.um.edu.my/reportcradle/reportviewer.aspx`
- **System**: SITS:Vision (Student Information System)

## Directory Structure

```
PerfTest/
├── script/
│   ├── jmeter/          # JMeter test plans (.jmx files)
│   └── playwright/      # Helper scripts for request capture
├── test_case/           # SAZ recordings and BlazeMeter captures per scenario
│   ├── ME-01/           # Mark Entry SAZ data (raw/*_c.txt, *_s.txt, *_m.xml)
│   ├── MC-02/           # Mark Confirmation SAZ data
│   ├── VRA-03/          # View Report SAZ data
│   ├── MAYA-ME-Ovr/     # Complete workflow + report-saz (cloudunity recording)
│   ├── Maya-Student/    # Student workflow SAZ data
│   └── Reset_password/  # Password reset SAZ data
├── requirement/         # Test cases (Excel) and user manuals (PDF)
├── results/             # JTL logs, execution logs, HTML captures
├── docs/                # Implementation notes (dynamic mark entry)
├── reference/           # Example HTML pages and JSON structures
├── test_data/           # CSV test data and per-slave distributions
│   ├── master_student_data.csv   # Full student dataset
│   └── slaves_data/              # Per-VM split data (IP subfolders)
├── config/              # JSON configuration files
│   ├── vm_config.json            # SSH, split, JMeter server settings
│   └── student_data_config.json  # ID prefixes and ranges
├── bin/                 # Batch scripts for Windows
│   ├── data/                     # Data generation and distribution
│   ├── jmeter/                   # Server management and test execution
│   └── test/                     # Local test runners
├── utils/               # Python utilities for distributed testing
├── slaves.txt           # List of slave VM IPs (one per line)
├── fiddler/             # Fiddler proxy configs and filter sets
└── screenshot/          # Captured screenshots from test runs
```

## Commands

### JMeter
```bash
# Run MAYA-lect.jmx in GUI mode (primary lecturer workflow)
jmeter -t script/jmeter/MAYA-lect.jmx

# Run complete workflow in non-GUI mode with results
jmeter -n -t script/jmeter/MAYA_Complete_Workflow.jmx \
  -l results/complete_workflow_$(date +%Y%m%d_%H%M%S).jtl \
  -e -o results/html_report_$(date +%Y%m%d_%H%M%S)/
```

### Playwright (Request Capture & Analysis)
```bash
node script/playwright/capture-login.js
node script/playwright/get-html.js
node script/playwright/capture-mark-entry-final.js
```

### SAZ File Extraction

```bash
# Fiddler .saz files are ZIP archives
unzip test_case/ME-01/ME-01.saz -d test_case/ME-01/ME-01-SAZ/

# Key files in extracted SAZ:
#   *_c.txt = Client request (headers + POST body)
#   *_s.txt = Server response (headers + response body)
#   *_m.xml = Metadata (timing, status codes)
```

### Python Utilities

```bash
# Install dependencies first
pip install -r requirements.txt

# Generate master student data from config
python utils/generate_master_data.py

# Split and distribute test data to slave VMs
python utils/split_and_copy_to_vms.py --offset 0 --size 15000

# Manage JMeter servers on slave VMs
python utils/manage_jmeter_servers.py start
python utils/manage_jmeter_servers.py stop
python utils/manage_jmeter_servers.py status
```

### Windows Batch Scripts (bin/)

```cmd
:: Generate master student data
bin\data\generate_master_data.bat

:: Split and distribute data to slave VMs
bin\data\split_and_distribute.bat [offset] [size]

:: Manage JMeter slave servers
bin\jmeter\start_servers.bat
bin\jmeter\stop_servers.bat
bin\jmeter\status_servers.bat

:: Run distributed JMeter test
bin\jmeter\run_distributed.bat script/jmeter/MAYA-Student.jmx
```

## Test Scenarios

| ID | Scenario | Description |
|----|----------|-------------|
| ME-01 | Mark Entry | Login → Assessments → Mark Entry → Enter marks → Save → Calculate |
| MC-02 | Mark Confirmation | Assessments → Mark Confirmation → Confirm Module Results |
| VRA-03 | View Report | Report → ASM12PS → Select parameters → Run Report → View in cloudunity |
| CE-01 | Student Enrolment | Student-side module registration workflow |

## JMeter Scripts

| File | Description | Status |
|------|-------------|--------|
| `MAYA-Student-v9.jmx` | **Student enrolment** with parameterized thinkTime for stress testing | Active, primary |
| `MAYA_Login_Test_v5.jmx` | **Login stress test** with Synchronizing Timer for D-day spike simulation | Active, stress test |
| `MAYA-lect.jmx` | Lecturer workflow: Dynamic mark entry with pagination, grade caching, cloudunity | Active |
| `MAYA_Complete_Workflow.jmx` | Combined ME-01 + MC-02 + VRA-03 (19 transactions, no cloudunity) | Stable reference |

### Script Parameters (use `-G` for distributed testing)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `-Gstudent` | 10 | Total threads (divided across slaves) |
| `-GrampUp` | 10 | Ramp-up time in seconds |
| `-Gloop` | 1 | Number of loops per thread |
| `-GthinkTime` | 3000 | Think time between requests (ms) - reduce for stress test |
| `-Glogout` | true | Logout after test (clears session) |
| `-GrunId` | STE003 | Test run ID for Dynatrace LTN |
| `-GsyncTimer` | false | Enable Synchronizing Timer (v5 only) for spike test |
| `-Gdynatrace.tsn` | MAYA-Student | Dynatrace Test Set Name |
| `-Gdynatrace.lsn` | CE-01-Enrolment | Dynatrace Load Script Name |

## SITS:Vision Login Correlation

The login form uses dynamic tokens that must be extracted from the GET response before POST:

| Token | Regex Pattern |
|-------|---------------|
| `FORM_VERIFICATION_TOKEN` | `name="FORM_VERIFICATION_TOKEN\.DUMMY\.MENSYS\.1" value="([^"]+)"` |
| `%.DUMMY.MENSYS.1` | `name="%\.DUMMY\.MENSYS\.1" value="([^"]+)"` |
| `%.WEB_HEAD.MENSYS.1` | `name="%\.WEB_HEAD\.MENSYS\.1" value="([^"]+)"` |
| `%.DUMMY_B.MENSYS` | `name="%\.DUMMY_B\.MENSYS" value="([^"]+)"` |

**Important**: HTML attribute order is `type="hidden" name="..." value="..."` - do not include `type` between `name` and `value` in regex patterns.

### Login Flow

1. **GET Login Page** → Extract all dynamic tokens
2. **POST Login** → Submit with extracted tokens + credentials
3. **GET Portal** → Follow JavaScript redirect (extract `HREF.DUMMY.MENSYS.1`)

### Form Field Names

| Purpose | Field Name |
|---------|------------|
| Username | `MUA_CODE.DUMMY.MENSYS.1` |
| Password | `PASSWORD.DUMMY.MENSYS.1` |
| Submit | `BP101.DUMMY_B.MENSYS` |

## SITS:Vision Navigation Correlation

**CRITICAL**: SITS:Vision uses dynamic session tokens in ALL navigation URLs. Static URLs will fail with "Portal error" responses.

All menu navigation links use dynamic tokens that must be extracted from the previous page:

| Navigation Step          | Extract From     | Regex Pattern                                  | Variable Name     |
|--------------------------|------------------|------------------------------------------------|-------------------|
| Portal → Assessments     | Portal page      | `href="(siw_portal\.url\?[^"]+)" id="STFAS00"` | `ASSESSMENTS_URL` |
| Assessments → Mark Entry | Assessments page | `href="(SIW_MME\.start_url\?[^"]+)"`           | `MARK_ENTRY_URL`  |

**Important**: Never use static URLs like `/siw_sso.mnu_comp_ASSESSMENT_TOP` or `/siw_mme` for navigation - they will return error pages.

## Multi-Service Token Architecture

**CRITICAL**: SITS:Vision uses **different session tokens for different service endpoints**. This is the most important architectural pattern to understand.

### Service Endpoints and Their Tokens

| Service | Endpoint | Token Variables | Used For |
|---------|----------|-----------------|----------|
| **MRK Service** | `/SIW_MRK_SVC.run_process` | `MRK_NKEY`, `MRK_ISS_CODE` | Mark entry grid initialization, data retrieval, save operations |
| **MSA Service** | `/SIW_MSA_SVC.run_process` | `MSA_NKEY`, `MSA_ISS_CODE` | Grade calculation from marks (GET_GRADE) |
| **CAL Service** | `/siw_msa_cal.run_process` | `CAL_NKEY`, `CAL_ISS_CODE` | Final module results calculation |
| **POD Service** | `/siw_pod_ms.amendParams`, `/siw_pod_ms.ajax_in` | `REPORT_NKEY`, `REPORT_ISSKEY` | Report generation (VRA-03) |

### Token Extraction Flow

```text
1. Module Selection → Extract MRK tokens (from JSON response)
2. MRK GET_DATA → Extract MSA tokens (from "ggfm" JSON object in response)
3. MRK RUN_BUTTON → Extract Calculate URL
4. Load Calculate Page → Extract CAL tokens (from HTML form fields + JavaScript)
5. Navigate to Report → Extract POD tokens (from HTML form)
```

**Key Insight**: You cannot reuse tokens between services. Each service validates its own token pair (nkey + issCode/issKey).

## ME-01 Mark Entry Workflow

### Test Data
- **Username**: `00013719`
- **Module**: `BID1011` (Site Planning and Analysis)
- **Components**: Class Test 1 (40%), Final Exam (60%)

### Workflow Steps

| Step | Action | Endpoint/Method |
|------|--------|-----------------|
| 1-2 | Login | GET `/siw_lgn` → POST `/SIW_LGN` → GET Portal |
| 3 | Click Assessments | GET dynamic URL (extracted from portal) |
| 4 | Click Mark Entry | GET dynamic URL (extracted from assessments) |
| 5 | Select Module (BID1011) | POST `/siw_mme.run_process` (processMode=SELECT_MAV) |
| 6 | Enter Marks Online | GET `/siw_msa` |
| 7 | Key in Class Test mark | POST `/SIW_MSA_SVC.run_process` (recordId=1-1-1) |
| 8 | Key in Final Exam mark | POST `/SIW_MSA_SVC.run_process` (recordId=2-1-1) |
| 9 | Save | POST `/SIW_MSA_SVC.run_process` (processMode=SAVE) |
| 10 | Calculate Results | POST `/SIW_MSA_SVC.run_process` (processMode=CALCULATE) |
| 11 | OK/Confirm | POST `/SIW_MSA_SVC.run_process` (processMode=CONFIRM) |

### Mark Entry Field Names
- **Mark fields**: `msa_mrk_widget_MRK.{component}-{student}-{attempt}` (e.g., `msa_mrk_widget_MRK.1-1-1`)
- **Grade fields**: `msa_mrk_widget_GRD.{component}-{student}-{attempt}` (auto-populated)
- **recordId format**: `{component}-{student}-{attempt}` (e.g., `1-1-1` = Component 1, Student 1, Attempt 1)

## Dynamic Mark Entry with Pagination (MAYA-lect.jmx)

The `MAYA-lect.jmx` script handles real-world mark entry with multiple pages of students and grade caching. See `docs/2026-01-27_dynamic-mark-entry.md` for full implementation details.

### Architecture

```text
Grade Lookup Loop (5 iterations: 100, 80, 65, 50, 35)
├── GET_GRADE for each unique mark value
├── Cache grade in JMeter property: grade_for_mark_{itemIID}_{mark}
└── Avoids redundant API calls across pages

Page Loop (While Controller: currentPage <= totalPages)
├── For each page: extract students from GET_DATA response
├── JSR223 builds changesList JSON dynamically
├── Random mark assignment from UNIQUE_MARKS pool
├── Grade lookup from cache (property) instead of API call
├── STORE_PAGE saves all marks for current page
└── Increment page, loop until all pages processed
```

### Key Variables Extracted from GET_DATA Response

| Variable | Description |
|----------|-------------|
| `TOTAL_GROUPS` | Total number of students |
| `TOTAL_PAGES` | Calculated total pages |
| `RECORDS_PER_PAGE` | Students per page (default 20) |
| `ITEMS_COUNT` | Number of assessment components |
| `ITEM_n_IID` | Component n's internal ID |
| `GROUP_n_GID`, `GROUP_n_SGID` | Student n's group/subgroup IDs |
| `MSA_NKEY`, `MSA_ISS_CODE` | Service tokens from `ggfm` JSON object |

### changesList JSON Format

Each mark entry generates a JSON array like:

```json
[{"id":"1-1-1","MRK":"100","GRD":"A+"},{"id":"1-2-1","MRK":"80","GRD":"A-"}]
```

Where `id` = `{componentIID}-{studentGID}-{attemptSGID}`.

## VRA-03: Report Generation with Cloudunity Correlation

Report generation involves two domains: MAYA (SITS:Vision) and cloudunity (ASP.NET Report Viewer).

### POD Service Parameters (Raw POST Body, `~` separated)

```text
MODE=RUNREPORT~NKEY.DUMMY.MENSYS=${RPT_NKEY}~ISSKEY.DUMMY.MENSYS=${RPT_ISSKEY}
~REPORT_LIST.DUMMY.MENSYS=RPT_ASM_312
~PARAMCOD.DUM_PARAM.MENSYS.1.=Lect~OPTIONS.DUM_PARAM.MENSYS.1.=${USERNAME}
~PARAMCOD.DUM_PARAM.MENSYS.2.=Sesi~OPTIONS.DUM_PARAM.MENSYS.2.=${AYR_CODE}
~PARAMCOD.DUM_PARAM.MENSYS.3.=Semester~OPTIONS.DUM_PARAM.MENSYS.3.=${SEMESTER}
~PARAMCOD.DUM_PARAM.MENSYS.4.=Modul~OPTIONS.DUM_PARAM.MENSYS.4.=${MODULE}
~runReportButton=Run+Report
```

Note: `sv-` UUID elements are client-side generated with empty values and can be safely omitted.

### Report Filter Requests (amendParams)

- **Request 36**: Choose report (uses default `${SESSION}` from dropdown, e.g. `2029`)
- **Request 37**: Change semester filter (uses `${AYR_CODE}` from mark entry, e.g. `2025`)
- **Request 38**: Run report (sends all params including `${MODULE}`)

`${SESSION}` and `${AYR_CODE}` are different values: SESSION is the default dropdown value, AYR_CODE is the actual academic year extracted from mark entry flow.

### Cloudunity Report Viewer Correlation Chain

```text
Request 38 (RUNREPORT ajax_in)
  → Response JSON: {"REPORT_FRAME":"https://cloudunity.um.edu.my/...?reportinstanceid=XXX&username=YYY"}
  → Extract: RPT_INSTANCE_ID, RPT_ENC_USERNAME

Request 39 (GET reportviewer.aspx?reportinstanceid=...&username=...)
  → Response: Full HTML page with ASP.NET hidden fields
  → Extract: CU_VIEWSTATE, CU_VIEWSTATE_GEN, CU_EVENT_VALIDATION
  → Cookie: ASP.NET_SessionId (auto-managed by JMeter CookieManager)

Request 40 (POST reportviewer.aspx - btnLoadReportTrigger)
  → Sends: __VIEWSTATE, __VIEWSTATEGENERATOR, __EVENTVALIDATION + __EVENTTARGET
  → Response: Full HTML with updated fields
  → Extract: CU_VIEWSTATE_2, CU_VIEWSTATE_GEN_2, CU_EVENT_VALIDATION_2

Request 41 (POST reportviewer.aspx - AsyncLoadTarget)
  → Sends: Updated __VIEWSTATE, __EVENTVALIDATION + __ASYNCPOST=true
  → Response: ASP.NET UpdatePanel delta format (pipe-delimited, NOT HTML)
```

ASP.NET hidden field regex: `name="__VIEWSTATE" id="__VIEWSTATE" value="([^"]+)"`

## User-Defined Variables (MAYA-lect.jmx)

| Variable | Value | Description |
|----------|-------|-------------|
| `USERNAME` | `00013719` | Lecturer staff ID |
| `PASSWORD` | `um12345` | Login password |
| `BASE_URL` | `maya-cloud.um.edu.my` | MAYA portal domain |
| `BASE_URL_2` | `cloudunity.um.edu.my` | Report viewer domain |
| `MARK_VALUE_1` | `100` | Default mark for component 1 |
| `MARK_VALUE_2` | `100` | Default mark for component 2 |
| `UNIQUE_MARKS` | `100,80,65,50,35` | Comma-separated marks for random assignment |
| `SESSION` | `2029` | Default session year from report dropdown |
| `SEMESTER` | `SEMESTER+1` | Semester filter value (URL-encoded) |
| `MODULE` | `BID1008%2CBID1011%2CBID4006` | Module filter (URL-encoded comma list) |

## SAZ File Analysis Workflow

When debugging or understanding new workflows:

1. **Extract SAZ as ZIP**: Fiddler `.saz` files are ZIP archives

   ```bash
   unzip test_case/ME-01/ME-01.saz -d test_case/ME-01/ME-01-SAZ/
   ```

2. **Analyze Request Sequence**:

   ```bash
   cd test_case/ME-01/ME-01-SAZ/raw/
   grep -l "SIW_MSA_SVC\|SIW_MRK_SVC\|siw_msa_cal" *_c.txt
   grep -A 5 "^POST" 173_c.txt
   ```

3. **Token Discovery Pattern**:
   - Search response bodies for JSON containing `"nkey"` and `"issCode"`
   - Check HTML forms for `name="NKEY.DUMMY.MENSYS.1"` patterns
   - Look for JavaScript initialization objects with tokens

## Complete Workflow Architecture (MAYA_Complete_Workflow.jmx)

### ME-01: Mark Entry (Transactions 1-14)

1. Login with token extraction
2. Navigate Portal → Assessments → Mark Entry (dynamic URLs)
3. Select Module → AUTO_RETRIEVE → GET_RESULTS → SELECT_MAV
4. **MRK Service**: INIT_PROCESS → GET_DATA (extracts MSA tokens from `ggfm`)
5. **MSA Service**: INIT_PROCESS → GET_GRADE (Component 1) → GET_GRADE (Component 2)
6. **MRK Service**: STORE_PAGE (save marks) → RUN_BUTTON (extract calculate URL)
7. Load Calculate Page (extract CAL tokens)
8. **CAL Service**: CALCULATE_RESULTS

### MC-02: Mark Confirmation (Transaction 15)

- POST to `/SIW_MSA` with `BP108.DUMMY_B.MENSYS=Confirm Module Results`
- Extracts Report URL for VRA-03

### VRA-03: View Report (Transactions 16-19)

1. Navigate to Report menu (dynamic URL)
2. Open POD system (extract REPORT_NKEY, REPORT_ISSKEY)
3. Set report parameters via `siw_pod_ms.amendParams`
4. Execute report via `siw_pod_ms.ajax_in` with `MODE=RUNREPORT`

### VRA-03 Extended: Cloudunity Report Viewer (Requests 39-41 in MAYA-lect.jmx)

1. GET cloudunity reportviewer (extract ASP.NET ViewState fields)
2. POST btnLoadReportTrigger (trigger report rendering)
3. POST AsyncLoadTarget (retrieve rendered report content)

## Distributed Testing Architecture

### Configuration Files

| File | Purpose |
|------|---------|
| `slaves.txt` | List of slave VM IPs (one per line, `#` for comments) |
| `config/vm_config.json` | SSH credentials, JMeter paths, split settings |
| `config/student_data_config.json` | Student ID prefixes and numeric ranges |

### vm_config.json Structure

```json
{
  "ssh_config": {
    "user": "root",
    "password": "...",
    "dest_path": "/home/opc/jmeter-PT/linux/test_data/"
  },
  "split_config": {
    "offset": 0,
    "size": 15000,
    "csv_filename": "student_data.csv"
  },
  "jmeter_scripts": {
    "start": "/home/opc/jmeter-PT/linux/start-slave.sh",
    "stop": "/home/opc/jmeter-PT/linux/stop-slave.sh"
  }
}
```

### Distributed Test Workflow

1. **Generate master data**: `python utils/generate_master_data.py`
2. **Start slave servers**: `python utils/manage_jmeter_servers.py start`
3. **Distribute test data**: `python utils/split_and_copy_to_vms.py --offset 0 --size 15000`
4. **Configure test**: Edit `config.properties`
5. **Run distributed test**: `SE_run_jmeter.bat`
6. **Stop servers**: `python utils/manage_jmeter_servers.py stop`

### config.properties

Central configuration for distributed tests. Edit this file to configure test parameters:

```properties
# Test plan selection
test_plan=test_plan/MAYA-Student-v9.jmx
student_data=test_data/student_data.csv

# Test parameters (total across all slaves)
student=15000
rampUp=300
loop=1
thinkTime=3000

# Stress test settings
# thinkTime=500    # Reduced for stress
# thinkTime=100    # Extreme stress

# Dynatrace integration
runId=STE010
dynatrace.tsn=MAYA-Student
dynatrace.lsn=CE-01-Enrolment
```

### SE_run_jmeter.bat

Main test execution script that:
- Reads `config.properties` and `slaves.txt`
- Calculates per-slave thread count (`student / slave_count`)
- Creates timestamped result folder (`results/YYYYMMDD_N/`)
- Passes all parameters via `-G` to slaves
- Generates HTML report automatically

### Data Distribution

The `split_and_copy_to_vms.py` script:
1. Reads `master_student_data.csv`
2. Splits rows evenly across VMs listed in `slaves.txt`
3. Saves local copies to `test_data/slaves_data/{VM_IP}/student_data.csv`
4. Uploads via SCP to each VM's `dest_path`

### Python Dependencies

```
pandas
numpy
paramiko
scp
```

Install with: `pip install -r requirements.txt`

## Stress Testing

### Stress Test Configurations

| Test Type | thinkTime | rampUp | Purpose |
|-----------|-----------|--------|---------|
| Baseline | 3000 | 300 | Normal load test |
| Stress | 500 | 60 | High pressure |
| Extreme | 100 | 30 | Maximum stress |
| Spike (v5) | 0 + syncTimer=true | 60 | D-day simulation |

### D-Day Spike Simulation (MAYA_Login_Test_v5.jmx)

```bash
# All users login, then hit POST login simultaneously
jmeter -n -t test_plan/MAYA_Login_Test_v5.jmx \
  -Gstudent=24000 -GrampUp=60 -GsyncTimer=true -Glogout=true \
  -R slave1,slave2,...
```

The Synchronizing Timer holds all threads until they've completed GET login page, then releases all POST login requests simultaneously.

## Dynatrace Integration

### X-Dynatrace-Test Header

All scripts include the X-Dynatrace-Test header for request tagging:

```
TSN=${__P(dynatrace.tsn,MAYA-Student)};LSN=${__P(dynatrace.lsn,CE-01-Enrolment)};LTN=${runId};VU=${__threadNum};SC=${USERNAME}
```

| Field | Description | Example |
|-------|-------------|---------|
| TSN | Test Set Name | MAYA-Student |
| LSN | Load Script Name | CE-01-Enrolment |
| LTN | Load Test Name (run ID) | STE010 |
| VU | Virtual User (thread number) | 42 |
| SC | Source Context (student ID) | EAR002666 |

### Dynatrace Request Attribute Configuration

To filter by LTN in Dynatrace:
1. Settings → Server-side service monitoring → Request attributes
2. Request attribute source: HTTP request header
3. Parameter name: `X-Dynatrace-Test`
4. Extract value per regex: `LTN=([^;]+)`

## Infrastructure (SITS:Vision on OCI)

| Component | Count | Notes |
|-----------|-------|-------|
| IIS (Web) | 4 | Front-end load balancers |
| Tomcat (App) | 16 | Heap: 16-32GB each |
| Oracle DB | 2 | RAC cluster |
| Uniface userver | 420/VM | Managed by urouter |
| LDAP | - | Authentication backend |

### Key Bottleneck Points

1. **urouter/userver pool**: 420 × 16 = 6,720 max concurrent connections
2. **LDAP authentication**: Can be bottleneck during login spike
3. **Database lock contention**: Multiple students registering for same module

## Web Dashboard (`webapp/`)

A FastAPI web app for managing this project. See `webapp/CLAUDE.md` for full details.

```bash
# Run the dashboard
cd webapp && python -m webapp
# Or with reload for development
cd webapp && uvicorn main:app --reload --host 127.0.0.1 --port 8080
```

### Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | Stats overview, runner status, last run, monitoring links |
| Test Plans & Runner | `/plans` | JMX selector, params, presets, live execution with WebSocket |
| Results | `/results` | Browse results, reports (filesystem open on localhost), regenerate, compare, download |
| Test Data | `/data` | CSV builder (5 column types), templates, distribute to slaves |
| Slave VMs | `/slaves` | List/grid view, enable/disable, SSH overrides, status check, Start/Stop All |
| Scripts | `/scripts` | Run .py/.bat files (localhost only) |
| Settings | `/settings` | Server, project paths, integrations (Grafana/InfluxDB/Ollama), system info |

### Key Features

- **Access control**: Localhost = admin, remote = needs auth token, viewer mode is read-only
- **JTL filtering**: `jtl_filter.py` removes sub-results (~80-85% reduction) and unresolved variables before report generation
- **Report optimization**: Disables heavy over-time graphs to reduce `graph.js` from 500+ MB
- **Safe regeneration**: Filter → generate to temp dir → swap on success (old report preserved on failure)
- **Report viewing**: `os.startfile()` on localhost bypasses proxy for large reports
- **Slaves JSON format**: Enable/disable per slave, auto-migrates from plain text
- **CSV builder**: Sequential, Static, Random Pick, Expression, Sequence column types
- **Live execution**: WebSocket streaming with parsed summary stats (throughput, avg RT, error rate, samples) and per-slave progress badges
- **Mobile responsive**: Bottom nav bar, hamburger menu, touch-friendly
