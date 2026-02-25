# Webapp Page-by-Page Evaluation

This document captures the evaluation of each page in the JMeter Dashboard webapp.
Each page section covers: current issues (code quality), improvement suggestions (features/UX), and implementation priority.

---

## 1. Dashboard

**Files:** `routers/dashboard.py`, `templates/dashboard.html`

### Current Issues (Code Quality)

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | Circular import — `from routers.settings import load_settings` (router importing router) | dashboard.py:40 | Medium |
| 2 | Unescaped HTML — `runner_label` and `lr.name` used raw in innerHTML | dashboard.html:103, 123 | Low |
| 3 | Heavy inline styles on monitoring cards | dashboard.html:139-146 | Low |
| 4 | Scattered inline styles (`width:100px`, `margin-top`, `flex-wrap`) | dashboard.html:53,66,92,106,128 | Low |
| 5 | Inconsistent `BASE_PATH` usage — mix of template literal and string concatenation | dashboard.html:107 vs 112 | Low |

### Current State

The dashboard has 4 stat cards (test plan count, result count, slave count, mode), runner status, last test run metadata, quick action links, and monitoring links. The stat cards show **static facts that rarely change** — once the project is set up, these numbers stay the same for days. The "Last Test Run" card only shows metadata (folder name, date, size) without any performance data.

### Improvement Suggestions

#### Tier 1 — Quick wins (data already exists in codebase)

| Card | What it shows | Why it matters | Backend needed |
|------|--------------|----------------|----------------|
| **Last Run Summary** | Avg response time, error rate, throughput, p95 from latest JTL | See results without navigating to results page | Parse latest JTL (jtl_parser.py already exists) |
| **Run History** | Mini table of last 5 runs with key metrics + trend arrows (better/worse) | Spot regressions at a glance | New `/api/dashboard/recent-runs` endpoint |
| **Runner Status (enhanced)** | When running: elapsed time, live sample count via WebSocket | Know if a long test is stalled | Extend process_manager info |
| **Disk Usage** | Total size of results directory, folder count | Warns before disk fills up | Simple `rglob('*')` size sum |

#### Tier 2 — More impactful (needs new backend work)

| Card | What it shows | Why it matters |
|------|--------------|----------------|
| **Trend Chart** | Sparkline of avg response time across last 10 runs | Visual regression detection |
| **Slave Health** | Green/red dots for each slave (cached from last check) | Know immediately if a slave is down before starting a test |
| **Alerts/Warnings** | "3 results have no report", "Slave X was down last check", "Disk usage > 90%" | Proactive issue surfacing |

#### Tier 3 — Nice to have

| Card | What it shows |
|------|--------------|
| **Comparison widget** | Pick 2 runs from dropdowns, see side-by-side delta |
| **Notes/annotations** | Pin a note like "baseline run before deploy v2.3" |

### Recommendation

Start with Tier 1 — it transforms the dashboard from a link page into something you'd actually check first. The main new work:

1. `/api/dashboard/recent-runs` — returns metrics for last 5 runs (parse JTL summaries, not full files)
2. Enhance "Last Run" card to show actual performance numbers (avg, p95, error rate, throughput)
3. Disk usage calculation
4. Keep Quick Actions and Monitoring cards as secondary content

---

## 2. Test Plans

**Files:** `routers/test_plans.py`, `templates/test_plans.html`

### Bugs (must fix — introduced during refactoring)

| # | Bug | Location | Impact |
|---|-----|----------|--------|
| 1 | ~~Stale ID `filterUsernames` — should be `filterSubResults`~~ FIXED | test_plans.html:522 (`setConfigLocked`) | ~~Config controls don't lock during test run~~ |
| 2 | ~~Stale variable `filterLabelPattern` — should be `labelPattern`~~ FIXED | test_plans.html:299, 351-352 | ~~Presets never save/restore the filter pattern~~ |

### Security (must fix)

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 3 | ~~**Path traversal**~~ FIXED — all 4 `jmx_dir / filename` joins now use `safe_join()` | test_plans.py:58, 71, 231, 247 | ~~High~~ |
| 4 | No upload size limit (same issue fixed in test_data.py) | test_plans.py:250 | Medium |
| 5 | ~~`escHtml` used in onclick attributes~~ FIXED — now uses `escAttr` | test_plans.html:407-408 | ~~Low~~ |
| 6 | WebSocket `ws_runner_logs` has no auth check | test_plans.py:156 | Low (read-only) |

### Filter UX (feature alignment with regenerate modal)

The regenerate modal in results.html has a visible text input for the label pattern + quick-fill buttons. The test plans page hides the pattern entirely — it loads silently from `config.properties` with no way to see or edit it. The preset system stores it as a hidden `_filter_label_pattern` special key (which is broken due to bug #2).

**Proposed fix:**
| # | Change | Detail |
|---|--------|--------|
| 7 | Show label pattern input next to filter toggle | Same layout as regen modal: text input + quick-fill buttons for common patterns |
| 8 | Remove `_filter_label_pattern` hack from presets | Save filter toggle + pattern as regular visible values, not hidden special key |
| 9 | ~~Remove backward compat fallbacks~~ DONE | Dropped `filter_usernames`/`filter_label_pattern` from both filter-config and filter-info endpoints |

### Missing Feature

| # | Feature | Detail |
|---|---------|--------|
| 10 | Delete test plan button | Add DELETE endpoint + confirmation dialog, same pattern as results page delete |

### Code Quality (nice to have)

| # | Issue | Location |
|---|-------|----------|
| 11 | Live stat cards have repeated `style="padding:10px;"` on all 7 cards | test_plans.html:103-130 |
| 12 | `populatePlanSelect` builds options with `innerHTML +=` in a loop | test_plans.html:215-217 |

### What's Solid

- Log streaming via WebSocket + buffer recovery — reconnects and replays missed output
- Live JMeter summary parsing (throughput, avg RT, error rate, VU counts) from log lines
- Slave progress tracking with per-slave status badges during distributed runs
- Preset system (save/apply/delete parameter sets)
- Command preview updates live on param change
- Elapsed timer, desktop notifications on test completion
- Mobile action bar, keyboard shortcut (Ctrl+Enter to start)
- JMeter GUI conflict warning

---

## 3. Results

**Files:** `routers/results.py`, `templates/results.html`

### Security (must fix)

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | ~~**Path traversal**~~ FIXED — `find_result_folder()` now uses `safe_join()` internally, protecting all 13 callers. Secondary `{path:path}` check in `api_serve_report` also uses `safe_join()`. | jtl_parser.py:89, results.py:105 | ~~**High**~~ |
| 2 | **Race condition** — `_active_regen` is a module-level global. Two concurrent regeneration requests overwrite each other's process reference, so "stop" could kill the wrong process. | results.py:37, 207, 225, 298-301 | Medium |
| 3 | ~~**Internal errors leaked**~~ FIXED — replaced `str(e)` with generic messages in all 5 endpoints | results.py:94, 133, 154, 388, 426 | ~~Low~~ |

### Code Quality

| # | Issue | Location |
|---|-------|----------|
| 4 | **Zip logic duplicated** — `_zip_report_to_file()` (lines 328-339) and `api_download_bundle` (lines 404-417) do the same zip-report-with-metadata logic separately | results.py |
| 5 | **Regen button ID mismatch** — element ID uses `escHtml` (`regen-${eName}`) but lookup uses `escAttr` value (`regen-` + folder from onclick). Breaks if folder name contains `'` | results.html:124 vs 212 |
| 6 | **Modal footer inline styles** — flex layout + border-top styling hardcoded | results.html:85 |
| 7 | **Inline `flex-wrap:wrap`** on action cells — repeated for every row | results.html:134 |
| 8 | ~~**Backward compat fallback still present**~~ FIXED — removed from `api_filter_info` | results.py:282-285 |

### Filter Behavior Gap

The `jtl_filter.py` script bundles sub-result removal with label regex filtering — they cannot be used independently. When `filter_sub_results` is OFF, the entire filter step is skipped, meaning you **cannot** apply a label regex without also removing sub-results.

**Proposed fix:** Make `jtl_filter.py` accept a flag to control sub-result removal independently from label pattern filtering.

### Download Gaps

Current downloads (single + bundle) explicitly **exclude JTL files** — only the `report/` directory + metadata is zipped. There is no way to download the raw JTL.

**Proposed fix:**
| # | Change | Detail |
|---|--------|--------|
| 9 | **"Include JTL" checkbox in download** | Add a download confirmation dialog with opt-in JTL inclusion. Default off (JTLs can be hundreds of MB). Show JTL file size as warning. |
| 10 | **Show JTL files per result** | Expand `_folder_info` to return JTL file list (name + size). Display in table or expandable row. |

### Missing Features

| # | Feature | Detail |
|---|---------|--------|
| 11 | **Stats preview** | Click a result row to expand inline per-transaction table (avg RT, p95, error rate, throughput). Data already available from `parse_jtl()`. |
| 12 | **Sort by column** | Table column headers clickable to sort by name, date, size |
| 13 | **Analysis badge** | Show icon/badge in results list if analysis is cached for that folder |
| 14 | **Bulk regenerate** | Selected folders regenerated in sequence |
| 15 | **Hide size column for viewers** | Size is only actionable for admins (delete decisions). Hide or conditionalize for viewer role. |

### What's Solid

- Regenerate modal with filter pre-fill from `regen_info.json` / `run_info.json`
- Atomic report swap (temp dir → rename) — prevents broken state during generation
- Download bundle for multiple reports
- Compare functionality with color-coded change percentages
- Stop regeneration (frontend AbortController + backend process kill)
- Filtered.jtl cleanup after regeneration
- AI analysis integration with Ollama + rule-based analysis with caching
- Search/filter on results list
- Select-all checkbox + multi-select for compare and bundle download

---

## 4. Test Data

**Files:** `routers/test_data.py`, `templates/test_data.html`, `services/data.py`

### Security (must fix)

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | ~~**Path traversal on upload**~~ FIXED — upload now uses `safe_join()` | test_data.py:137 | ~~**High**~~ |
| 2 | ~~**Path traversal on build**~~ FIXED — `build_csv()` now uses `safe_join()` | data.py:195 | ~~**High**~~ |
| 3 | **Upload reads entire file before size check** — 100MB limit exists but `await file.read()` loads it all into memory first. A 2GB upload consumes 2GB RAM before rejection. | test_data.py:138-139 | Medium |
| 4 | ~~**`escHtml` in onclick attributes**~~ FIXED — replaced with `escAttr` for rename, delete, preview buttons | test_data.html:840, 843, 850, 948 | ~~Low~~ |
| 5 | ~~**Internal error leaked**~~ FIXED — `preview_csv` now returns generic message | data.py:51 | ~~Low~~ |

### Code Quality

| # | Issue | Location |
|---|-------|----------|
| 6 | **Column color badges inline** — complex inline styles with 8-color palette hardcoded in JS string template | test_data.html:847 |
| 7 | **`preview_csv` reads file twice** — once to count total rows, then again with pandas for data. Wasteful for large files. | data.py:40-43 |
| 8 | ~~**Custom preset onclick uses `escHtml`**~~ FIXED — replaced with `escAttr` | test_data.html:506-508 |
| 9 | **Distribute preview has heavy inline styles** — table styling, flex layouts, margins all inline | test_data.html:712-780 |

### Improvement Suggestions

| # | Feature | Detail |
|---|---------|--------|
| 10 | **Streaming upload size check** | Check `Content-Length` header or read in chunks instead of loading entire file into memory before checking size |
| 11 | **Distribute progress** | Currently all-or-nothing. Show per-slave transfer status as they complete, not just final summary. |
| 12 | **Validate uploaded CSV** | Check that uploaded CSV has valid headers and is parseable before saving |

### What's Solid

- CSV Builder with 5 column types (sequential, static, random_pick, expression, sequence)
- Built-in presets + custom preset system with localStorage persistence
- Client-side preview before generation — shows sample rows instantly
- Distribute to slaves with per-file copy/split mode + offset/size control
- Split preview showing per-slave data distribution with sample rows
- Inline rename with click-outside-to-cancel UX
- Progressive preview loading (50 → 500 → load all)
- Path traversal checks on all endpoints via shared `safe_join()` helper

---

## 5. Scripts — REMOVED

**Files:** `routers/scripts.py`, `templates/scripts.html` (files kept for reference, router disconnected)

### Verdict: ~~Candidate for removal~~ DONE

Removed from navigation and router registration. The page ran arbitrary .py/.bat/.sh scripts via HTTP — never used, security surface, zero unique capability over terminal.

- Router removed from `main.py`
- Sidebar link removed from `base.html`
- Files kept in codebase for potential future re-use

---

## 6. Slaves

**Files:** `routers/config.py` (slave endpoints), `templates/slaves.html`, `services/slaves.py`

### Security

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **No auth on status endpoint** — `api_slave_status` has no `_check_access`. Any viewer can trigger SSH connections to all slaves. Read-only but triggers network activity. | config.py:141 | Medium |
| 2 | ~~**`escHtml` in onchange attributes**~~ FIXED — config panel now uses `escAttr` for IP and values | slaves.html:410-425 | ~~Low~~ |
| 3 | **`str(e)` leaked** — SSH error messages returned to client. Could expose internal network info. | slaves.py:48, 70, 145 | Low |
| 4 | **No IP validation** — `addSlave()` accepts any string with no format validation | slaves.html:348-356 | Low |

### Code Quality

| # | Issue | Location |
|---|-------|----------|
| 5 | **Duplicate paramiko client creation** — same `SSHClient()` + `AutoAddPolicy` + `connect()` pattern repeated 3 times | slaves.py:36-44, 54-62, 123-130 |
| 6 | **Repeated slave loading pattern** — `slaves_path` + `read_slaves()` repeated 4 times in config.py | config.py:91, 146, 177, 196 |
| 7 | **Unused top-level `import pandas`** — only used inside `_distribute_items`, should be lazy import | slaves.py:5 |
| 8 | **VM Config collapse is inline JS** — long onclick handler on card header | slaves.html:46 |
| 9 | **Grid view heavy inline styles** | slaves.html:204-218 |

### Architecture Gap: Start/Stop Script Dependency

Current setup assumes JMeter start/stop scripts are **pre-deployed on slaves**. The webapp just calls them via SSH. This breaks when:
- Setting up a new project with fresh slaves (no scripts exist yet)
- Slaves have JMeter installed at different locations
- Mixing OCI VMs with developer laptops

**Proposed fix:** Build start/stop commands directly from config instead of relying on pre-deployed scripts:
- Store JMeter install path per slave (or global default + per-slave override)
- Webapp constructs the actual `jmeter-server` command from the path
- Option to deploy/sync scripts to slaves from the webapp

### Missing Features

| # | Feature | Detail |
|---|---------|--------|
| 10 | **Slave nickname** | Friendly name per slave (e.g. "Dev Laptop", "OCI VM #3") — currently only identified by IP |
| 11 | **Per-VM JMeter paths** | Per-slave override for JMeter install location and script paths. Currently all slaves share the same start/stop script. Needed when mixing OCI VMs + laptops with different layouts. |
| 12 | **Individual start/stop** | Can only start/stop ALL servers. Add per-slave start/stop buttons. |
| 13 | **Auto status check** | Have to manually click "Check Status". Could auto-check on page load or on a timer. |
| 14 | **SSH key authentication** | Currently only password auth. Should support SSH key files for more secure setups. |
| 15 | **Drag-to-reorder** | Slave order matters for data distribution (split). Allow drag to reorder. |
| 16 | **Windows slave support** | `nohup {script} > /dev/null 2>&1 &` is Linux-only. Need per-slave OS flag (linux/windows) and platform-appropriate commands (`start /b`, PowerShell, etc.) |

### What's Solid

- List view + Grid view with localStorage preference
- Bulk selection (select all, bulk enable/disable/remove)
- Inline IP editing with commit-on-blur UX
- Per-slave SSH overrides via expandable config panel (user, password, dest_path)
- Parallel SSH status checks via ThreadPoolExecutor
- Summary bar with VM count, enabled/disabled, online counts
- Start/Stop all servers in parallel with result summary
- Auto-refresh status after start/stop (3s delay)
- Collapsible VM Configuration section
- `build_ssh_configs()` shared helper for SSH config merging

---

## 7. Settings

**Files:** `routers/settings.py`, `templates/settings.html`

### Security (must fix)

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | ~~**Token exposed to viewers**~~ FIXED — `GET /api/settings` now returns `token_set: true/false` instead of the hash. Token is never exposed. | settings.py:93-101 | ~~**High**~~ |
| 2 | ~~**No auth by default**~~ FIXED — First run auto-generates a secure token (`secrets.token_urlsafe(32)`), hashes it, shows once on setup page + console. Auth enabled from the start. | main.py lifespan | ~~**High**~~ |
| 3 | **System info no auth** — `api_system_info` exposes OS version, Java/JMeter/Python versions, and disk usage to anyone | settings.py:117 | Low |
| 4 | **No validation on settings save** — accepts arbitrary JSON, could overwrite auth config with malformed data | settings.py:103-105 | Low |

### ~~Architecture Gap: Token Management~~ FIXED

Token flow has been secured:
- Token hashed with SHA-256 before storage (`services/auth.py:hash_token`)
- `GET /api/settings` returns `token_set: true/false`, never the hash
- `PUT /api/settings` hashes new tokens, preserves existing hash when empty, supports `clear_token` flag
- Token compared with `hmac.compare_digest` (constant-time, prevents timing attacks)
- First run auto-generates token, shows once on setup page + console, stores only hash
- `migrate_token_if_needed()` auto-hashes any existing plain-text tokens at startup
- "Remove Token" button in Settings UI for disabling auth

### Code Quality

| # | Issue | Location |
|---|-------|----------|
| 5 | **Heavy inline styles on form layouts** — `flex-wrap:wrap`, `min-width`, `flex:1/2` on nearly every form group | settings.html throughout |
| 6 | **Two separate API calls in save** — `saveAllSettings()` saves settings.json then project.json. If second fails, state is inconsistent. | settings.html:413-424 |
| 7 | **Report settings separate save button** — Report tab has its own Save separate from the main Save. Could confuse users. | settings.html:251 vs 11 |
| 8 | **System info cards inline styles** | settings.html:503-506 |

### Missing Features

| # | Feature | Detail |
|---|---------|--------|
| 9 | **Export/Import settings** | Backup/restore settings.json + project.json as a single download. Useful when setting up new projects. |
| 10 | **Settings validation** | Validate port range, URL formats, path existence before saving. Currently accepts anything. |
| 11 | **Config properties editor** | `config.properties` is edited on a separate Config page. Could integrate here under Project tab. |

### What's Solid

- Tabbed layout (General, Project, Report, Integrations, System) — well organized
- Live theme preview before save
- JMeter auto-detect from PATH and common locations
- Report graph toggles with Heavy/Light categorization and quick presets (Disable Heavy, Enable All, Reset)
- System info display (JMeter, Java, Python, OS, disk usage)
- Access control (viewer gets all inputs readonly/disabled)
- Server restart with automatic redirect to new address
- Ollama connection test with model listing
- Token visibility toggle
- Granularity selector for report generation

---

## Future Plans

Items discussed during evaluation that go beyond fixing current issues. These represent new capabilities for the webapp.

### Slaves & Distributed Testing

| # | Feature | Detail | Complexity |
|---|---------|--------|------------|
| F1 | **Windows slave support** | Current start/stop commands are Linux-only (`nohup`, `/dev/null`). Need per-slave OS flag (linux/windows) and platform-appropriate commands. | Medium |
| F2 | **All JMeter properties via webapp** | Manage the full `jmeter.properties` / `user.properties` from the webapp — not just `config.properties`. Would need a properties file editor with sections. | Medium |
| F3 | **Modify properties on all slaves** | Push JMeter properties to slave VMs via SSH. Currently only data files can be distributed. Properties should follow the same distribute pattern. | Medium |
| F4 | **Backend listener override properties** | Allow configuring backend listener properties (InfluxDB/Graphite) from the webapp. Currently using an extension plugin; built-in backend listener behavior in distributed testing is untested — properties may break when slaves run with different configs. Needs experimentation first. | High (research needed) |
| F5 | **Self-contained start/stop** | Build JMeter server commands from config (install path + args) instead of relying on pre-deployed scripts on slaves. | Medium |
| F6 | **Per-VM JMeter paths** | Per-slave override for JMeter install location. Needed when mixing OCI VMs + developer laptops. | Low |
| F7 | **Slave nickname** | Friendly name per slave (e.g. "Dev Laptop", "OCI VM #3"). | Low |

### Security & Setup

| # | Feature | Detail | Complexity |
|---|---------|--------|------------|
| F8 | ~~**Setup-time token generation**~~ DONE | Auto-generates secure token on first run, shows once on setup page + console, stores hash only. | ~~Low~~ |
| F9 | **SSH key authentication** | Support SSH key files in addition to password auth. | Low |

### Results & Reporting

| # | Feature | Detail | Complexity |
|---|---------|--------|------------|
| F10 | **JTL download with opt-in** | "Include JTL" checkbox in download dialog. Default off due to large file sizes. | Low |
| F11 | **Stats preview in results list** | Expandable row showing per-transaction stats without opening full report. | Medium |
| F12 | **Sort by column** | Clickable column headers in results table. | Low |

### Dashboard

| # | Feature | Detail | Complexity |
|---|---------|--------|------------|
| F13 | **Last run summary** | Avg RT, error rate, throughput, p95 from latest JTL on the dashboard. | Low |
| F14 | **Run history** | Mini table of last 5 runs with trend arrows. | Medium |
| F15 | **Disk usage card** | Total results directory size with warning when low. | Low |

---

## Cross-Cutting Issues

Recurring patterns found across multiple pages. Fixing these systematically (once, in the right place) is more efficient than page-by-page.

### 1. ~~Path Traversal (5 pages — HIGH)~~ FIXED

~~User-supplied filenames/folder names joined directly with base directories without `.resolve()` + boundary check.~~

**Fixed:** Added `safe_join()` helper to `services/auth.py`. Applied to:
- `find_result_folder()` in `jtl_parser.py` (protects all 13 callers in results.py)
- 4 path joins in `test_plans.py` (params, open, download, upload)
- 7 inline checks replaced + upload protected in `test_data.py`
- `build_csv` output path in `data.py`
- Secondary `{path:path}` check in `results.py:api_serve_report`

### 2. ~~`escHtml` vs `escAttr` in onclick/onchange (4 pages — LOW)~~ FIXED

~~`escHtml` handles `& < > "` but not `'`. When used inside `onclick="fn('${value}')"`, a value with `'` breaks out of the attribute.~~

**Fixed:** Replaced `escHtml` with `escAttr` in all attribute contexts:
- Test Plans — preset apply/delete buttons
- Test Data — rename, delete, preview buttons + custom preset onclick
- Scripts — runScript button
- Slaves — config panel onchange handlers + input values

### 3. ~~Internal Errors Leaked (4 pages — LOW)~~ FIXED (results + data)

~~`str(e)` returned directly to client, potentially exposing file paths, hostnames, or stack traces.~~

**Fixed:** Replaced `str(e)` with generic messages in:
- Results — all 5 endpoints (open report, open folder, delete, download, bundle)
- Test Data — `preview_csv` and `preview_split`

**Kept as-is (diagnostic, admin-only):**
- Slaves — SSH errors are diagnostic information for admins configuring infrastructure
- Settings — subprocess failures in system-info (admin-only endpoint)

### 4. Inline Styles (all pages — LOW)

Every page has extensive inline styles for flex layouts, spacing, borders. Common patterns that should be CSS classes:

| Pattern | Occurrences | Suggested class |
|---------|-------------|-----------------|
| `display:flex;gap:16px;flex-wrap:wrap;` | ~20+ | `.form-row` |
| `flex:1;min-width:200px;` | ~15+ | `.form-col` |
| `padding:12px 16px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:8px;` | ~8 | `.surface-card` |
| `font-weight:600;` on h3 section headers | ~12 | `.section-title` |

---

## What's Left

Beyond the page-specific findings and future plans, these are project-level gaps.

### Must Have (before sharing with team)

| # | Item | Detail |
|---|------|--------|
| 1 | ~~**Fix all High severity security issues**~~ DONE | ~~Path traversal (5 pages), token exposed to viewers, no auth by default.~~ All fixed: `safe_join()`, token hashing, first-run token generation. |
| 2 | ~~**Fix refactoring bugs**~~ DONE | Fixed stale `filterUsernames` → `filterSubResults` and `filterLabelPattern` → `labelPattern` in test_plans.html. |
| 3 | ~~**Remove backward compat fallbacks**~~ DONE | Removed `filter_usernames`/`filter_label_pattern` from filter-config and filter-info endpoints. |

### Should Have (quality of life)

| # | Item | Detail |
|---|------|--------|
| 4 | ~~**Tests**~~ DONE | 165 pytest tests across 8 files (auth, config, dashboard, data, plans, results, settings, security). 53% code coverage. CI/CD via GitHub Actions. |
| 5 | ~~**Setup wizard / first-run flow**~~ PARTIAL | Token generation done (auto-generate + show once + hash). Path validation and JMeter detection already existed in setup.html. |
| 6 | ~~**Server-side logging**~~ DONE | RotatingFileHandler to `logs/app.log` (5MB max, 3 backups). API requests logged with method, path, status, duration. Errors include stack traces. |
| 7 | ~~**API docs**~~ DONE | FastAPI auto-generated docs at `{base_path}/docs` (Swagger UI) and `{base_path}/redoc` (ReDoc). |
| 8 | ~~**Remove Scripts page**~~ DONE | Router disconnected from main.py, sidebar link removed from base.html. Files kept for reference. |

### Nice to Have

| # | Item | Detail |
|---|------|--------|
| 9 | **Setup script** | `setup.py` or shell script that checks prerequisites (Python, JMeter, Java), installs pip deps, creates default configs. Replaces need for Docker — JMeter needs bare-metal resources for accurate load generation. |
| 10 | ~~**README for webapp**~~ DONE | `webapp/README.md` — setup instructions, architecture overview, config reference, testing, logging, new machine setup. |
| 11 | ~~**Mobile UX audit**~~ DONE | Removed hardcoded SVG max-width on dashboard. All pages checked for responsive behavior. |
| 12 | ~~**Accessibility**~~ DONE | ARIA roles on modals (`role="dialog"`, `aria-modal`), tabs (`role="tablist"`, `aria-selected`), table headers (`scope`, `aria-sort`, keyboard nav), focus-visible styles, aria-labels on buttons. |
| 13 | **Error boundary / global error handler** | Frontend currently has per-function try/catch. A global `api()` wrapper error handler would be more consistent. |

### Fix Priority Order

All items complete:

1. ~~**Security fixes**~~ DONE — path traversal, token hashing, auth defaults, config properties auth bypass
2. ~~**Bug fixes**~~ DONE — stale variable names from refactoring
3. ~~**Remove dead code**~~ DONE — Scripts page removed, backward compat fallbacks removed
4. ~~**Add tests**~~ DONE — 165 tests, 53% code coverage, CI/CD via GitHub Actions
5. ~~**Setup wizard**~~ DONE — first-run token generation + path validation
6. ~~**Cross-cutting cleanup**~~ DONE — `escAttr` applied, error messages genericized, inline styles → CSS classes
7. ~~**Dashboard improvements**~~ DONE — Tier 1 (last run summary, recent runs, disk usage) + Tier 2 (trend chart, slave health, alerts)
8. ~~**Future features**~~ DONE — Windows slaves, properties management, SSH key auth, individual slave start/stop, per-VM JMeter paths, slave nicknames, filter gap fix, stats preview, bulk regenerate

---

## Code-Level Evaluation (2026-02-25)

Deep code review of the entire webapp codebase. Overall rating: **7.8 / 10**.

### Scorecard

| Category | Score | Notes |
|----------|-------|-------|
| Architecture | 8.0 | Clean router/service split, file-based design fits the domain |
| Security | 8.5 | `safe_join`, constant-time token compare, 27 viewer-denial tests |
| Process Management | 8.0 | Non-blocking drain buffer, reconnectable WebSocket, graceful stop |
| Frontend | 7.5 | CSS design system, responsive, accessible — no framework overhead |
| Testing | 7.0 | 165 tests, good fixtures — but weak assertions and 53% coverage |
| Code Quality | 7.5 | Thin handlers, consistent patterns — some async and atomic write gaps |
| Documentation | 9.0 | CLAUDE.md files are exceptional for onboarding |

### Architecture Findings

| # | Finding | Location | Severity |
|---|---------|----------|----------|
| A1 | `load_settings()` in `routers/settings.py` causes router-to-router imports | dashboard.py imports from settings.py, config.py | Medium |
| A2 | Report regeneration logic (~115 lines) duplicated in `api_regenerate_report` and `api_bulk_regenerate` | results.py:157-272, 291-366 | Medium |
| A3 | `get_project()` helper defined in main.py but never used — all routers read `request.app.state.project` directly | main.py:228 | Low |
| A4 | Module-level mutable globals (`_regen_lock`, `_active_regen`, `_active_regen_folder`) in a router module | results.py:38-40 | Low |
| A5 | JTL parse cache (`*.summary.json`) is a pragmatic local cache — good design | jtl_parser.py:138-150 | Strength |
| A6 | `ProcessManager` singleton correctly returns 409 on concurrent test starts | process_manager.py:174-178 | Strength |

### Async Correctness

| # | Finding | Location | Severity |
|---|---------|----------|----------|
| AC1 | `asyncio.get_event_loop()` deprecated since Python 3.10 — should be `asyncio.get_running_loop()` | process_manager.py:68 | Medium |
| AC2 | `post_proc.wait(timeout=600)` blocks the event loop inside `_drain_output` async task | process_manager.py:103 | Medium |
| AC3 | `load_settings()` synchronous in async handlers (acceptable now, debt for growth) | Called from dashboard.py:40, etc. | Low |
| AC4 | `run_in_executor` for `proc.stdout.readline` is correct — preserves event loop health | process_manager.py:79 | Strength |
| AC5 | `asyncio.sleep(0.1)` polling in `subscribe_output` is pragmatic — `asyncio.Event` would be cleaner | process_manager.py:147 | Low |

### Security Findings (New)

| # | Finding | Location | Severity |
|---|---------|----------|----------|
| S1 | Missing `samesite="strict"` on auth cookie — minor CSRF surface | main.py:214 | Low |
| S2 | No token = everyone is admin, no startup warning log | auth.py:103-105 | Low |
| S3 | `detect_jmeter_path()` hardcodes version numbers (5.6.3, 5.6.2) — glob would be more robust | config_parser.py | Low |
| S4 | `save_settings()` not atomic — crash mid-write corrupts `settings.json` | settings.py:76-80 | Medium |

### Testing Findings

| # | Finding | Location | Severity |
|---|---------|----------|----------|
| T1 | Weak assertion: `assert "labels" in data or ... or "error" not in data` — vacuously true | test_results_api.py:30-31 | Medium |
| T2 | Overly permissive: `assert r.status_code in (404, 200)` for a "not found" test | test_results_api.py:34 | Medium |
| T3 | Weak OR: `assert data.get("running") is False or data.get("status") != "running"` | test_plans_api.py:163 | Medium |
| T4 | Known test data (2 JTL rows) but assertions don't verify exact outputs | test_results_api.py:25-31 | Low |
| T5 | No WebSocket integration tests | test_plans_api.py | Low |
| T6 | Session-scoped fixtures with proper `monkeypatch` isolation — well designed | conftest.py | Strength |
| T7 | Three client fixtures (admin, viewer, authed_remote) cover all access levels | conftest.py | Strength |

### Frontend Findings

| # | Finding | Location | Severity |
|---|---------|----------|----------|
| F1 | `WSManager` has no reconnection/retry — network hiccup silently kills log stream | app.js:164-197 | Medium |
| F2 | `.log-output` uses `word-break: break-all` — splits log lines at non-intuitive points; `overflow-wrap: anywhere` is better | style.css | Low |
| F3 | `escAttr` double-quote escaping relies on browser `innerHTML` getter behavior — fragile | app.js:205 | Low |
| F4 | CSS design system with variables, dark/light theming, responsive breakpoints — solid | style.css:1-47 | Strength |
| F5 | `api()` wrapper auto-shows toast on errors + propagates for caller handling | app.js:94-116 | Strength |

### Process Management Findings

| # | Finding | Location | Severity |
|---|---------|----------|----------|
| P1 | No `creationflags` on Windows — distributed JMeter child processes survive master termination | process_manager.py | Medium |
| P2 | Race condition: `stop()` sets `_active_process = None` while `_drain_task` may still be running | process_manager.py | Low |
| P3 | Non-blocking drain buffer with late-connect support — well designed | process_manager.py | Strength |
| P4 | Graceful `terminate()` → 5s timeout → `kill()` escalation — correct | process_manager.py:154-165 | Strength |

### Top 5 Recommendations

1. **Extract regeneration logic** from results.py into `services/jmeter.py` — eliminates duplication (A2)
2. **Fix `asyncio.get_event_loop()`** and make `post_proc.wait()` non-blocking (AC1, AC2)
3. **Move `load_settings()`** to `services/` — breaks router-to-router import chain (A1)
4. **Strengthen test assertions** — replace OR-chains with exact value checks (T1-T4)
5. **Add atomic writes** for settings.json — write to temp, then `os.replace` (S4)

---

## Page-by-Page Walkthrough Changes (2026-02-25)

Changes agreed during live walkthrough session. Each page lists what to add, remove, and modify.

### Page 1: Dashboard (`/`)

#### Completed (already applied)

| # | Change | Status |
|---|--------|--------|
| D1 | **Remove trend chart** — overall throughput across runs is not actionable; the SVG sparkline + `renderTrendChart()` function removed | DONE |
| D2 | **Add VUs column** to Run History table — shows `peak_vus` from `max(allThreads)` in JTL | DONE |
| D3 | **Add Peak VUs card** to Last Test Run summary — first stat card in the mini grid | DONE |
| D4 | **Delete old summary caches** — removed `*.summary.json` so they regenerate with the new `peak_vus` field | DONE |

#### Pending: Eager Post-Run Summary

**Problem:** Summary stats are currently generated lazily on first dashboard load (parses the full JTL). This means the first viewer after a test run pays a multi-second parsing cost.

**Solution:** Generate `run_summary.json` eagerly in the post-run pipeline, immediately after JMeter exits.

**What `run_summary.json` contains** (single file, replaces both `run_info.json` and `*.summary.json`):

```json
{
  "test_plan": "MAYA-Student-v9.jmx",
  "timestamp": "2026-02-04T10:06:47",
  "mode": "distributed",
  "slaves": ["10.0.0.1", "10.0.0.2"],
  "params": {
    "student": "15000",
    "rampUp": "300",
    "thinkTime": "3000",
    "loop": "1"
  },
  "filter": {
    "sub_results": true,
    "label_pattern": ""
  },
  "stats": {
    "peak_vus": 15000,
    "total_samples": 3372071,
    "avg": 5681.2,
    "median": 4200.0,
    "p90": 15000.0,
    "p95": 27029.0,
    "p99": 45000.0,
    "min": 10,
    "max": 120000,
    "error_count": 295700,
    "error_pct": 8.77,
    "throughput": 3753.05,
    "duration_sec": 898.3,
    "start_time": 1738656407000,
    "end_time": 1738657305000
  },
  "transactions": [
    {"label": "Login", "samples": 15000, "avg": 1200.0, "p95": 3500.0, "error_pct": 0.5},
    {"label": "Enrolment", "samples": 15000, "avg": 8500.0, "p95": 25000.0, "error_pct": 12.3}
  ]
}
```

**Where it's generated:**
- Post-run pipeline in `process_manager.py` `_drain_output`, after JMeter exits, before JTL filter
- Calls `parse_jtl()` on the raw JTL (which writes the cache as a side effect)
- Merges with `run_info` (test plan, params, slaves, filter config) into one file

**Scope:**
- All new runs (via webapp) → eager generation
- All result folders with a JTL → `run_summary.json` exists
- Legacy results (no summary) → lazy fallback: parse JTL on first access, write cache
- Regenerated results → summary re-generated from filtered JTL

**Impact on dashboard:**
- Dashboard reads pre-built JSON files — zero parsing, zero delay
- No "last 10" limitation on data availability; all results have summaries

#### Pending: Layout Reorder

**Problem:** Current layout is organized by data type, not by user priority. Static stat cards (rarely change) are at the top; alerts (need immediate attention) are buried below history.

**Current order:**
1. Stat cards (Test Plans, Results, Slaves, Mode)
2. Runner Status + Last Test Run
3. Run History table
4. Alerts (hidden when empty)
5. Quick Actions + Disk Usage + Monitoring

**Proposed order (priority-based):**

| Row | Content | Rationale |
|-----|---------|-----------|
| 1 | **Runner Status + Alerts** (side by side) | First question: is anything running or broken? Alerts visible immediately, not hidden. If no alerts, runner takes full width. |
| 2 | **Last Test Run** (full width, with metric cards) | Second question: how did the last run go? |
| 3 | **Run History** table (full width) | Context: how does it compare to previous runs? |
| 4 | **Quick Actions + Stat Cards + Disk Usage** (3 cols) | Action row: what now? Stat cards demoted here — they're reference info, not actionable. |
| 5 | **Monitoring** (Grafana/InfluxDB links) | External links, lowest priority |

**Key design decisions:**
- Alerts move from row 4 (hidden) to row 1 — if something is wrong, you see it first
- Stat cards move from row 1 to row 4 — test plan count / slave count rarely changes
- Monitoring stays last — external links are least used
- Runner status stays prominent — the "is something running?" question is always first

---

## 2. Test Plans & Runner

**Files:** `routers/test_plans.py`, `templates/test_plans.html`, `services/jmeter.py`, `services/process_manager.py`

### Current Issues (Code Quality)

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | `asyncio.get_event_loop()` deprecated — should be `asyncio.get_running_loop()` | process_manager.py:68 | Medium |
| 2 | `proc.wait()` is blocking the event loop — should be `await loop.run_in_executor(None, proc.wait)` | process_manager.py:83 | Medium |
| 3 | Live stats parsed in browser only — not shared with backend/dashboard | test_plans.html:609 | Medium |
| 4 | No post-run phase distinction — UI shows "Idle" while post-commands (filter + report) still running | process_manager.py:86-111 | Medium |
| 5 | `filtered.jtl` deleted after report generation — loses the clean data source | process_manager.py:126-131 | Medium |
| 6 | Presets are plan-agnostic — no warning when applying a preset from a different plan | test_plans.html:335-366 | Low |
| 7 | Stopping a test only kills the local controller — slaves keep running in distributed mode | process_manager.py:154-166 | High |

### Current State

The page has two main sections:
- **Configure & Run** — plan selection (dropdown), parameter form (auto-extracted from `__P()` refs in JMX), preset system, command preview, filter toggle, start/stop buttons
- **Live Output** — real-time stat cards (throughput, avg RT, errors, active/started/finished VUs), slave progress badges, collapsible raw log via WebSocket

Supporting features: upload/download/delete plans, "Edit in JMeter GUI" (localhost only), global properties modal, elapsed timer, Ctrl+Enter shortcut, browser notification on completion, JMeter GUI conflict warning, config locking during runs, mobile action bar.

### Changes Agreed

#### P1: Live stats don't survive page navigation

**Problem:** When you leave `/plans` mid-test and return, the WebSocket reconnects and raw log recovers from buffer, but the live summary cards (throughput, avg RT, errors, VUs) show dashes until the next JMeter summary line arrives. Could be minutes between summary lines on slow tests.

**Fix:** On reconnect, replay buffered log lines through `parseLogLine()` to restore the live summary cards from the last known values.

#### P2: No post-run phase distinction

**Problem:** After JMeter exits, JTL filtering + report generation still runs as post-commands in `_drain_output()`. But the UI shows "Idle" because `is_running` checks `process.poll()` on the main process only. User might navigate to results and find an incomplete report.

**Fix:** Add a `is_post_processing` state to the process manager. The UI shows "Post-processing..." badge during this phase. The runner status only goes to "Idle" after all post-commands complete.

#### P3: Stop deleting `filtered.jtl`

**Problem:** `filtered.jtl` is deleted after report generation (process_manager.py:126-131). This means:
- Dashboard/results stats read from `results.jtl` (raw, includes sub-results) — **stats don't match the HTML report**
- Summary generation has to re-parse the larger raw JTL
- Report regeneration has to re-filter

**Fix:** Keep `filtered.jtl`. All stats (dashboard, results page, `run_summary.json`) read from `filtered.jtl` when it exists, falling back to `results.jtl` when no filtering was applied. Stats always match the HTML report.

#### P4: Two-phase `run_summary.json`

Linked to Dashboard change (see Section 1). Two phases:

1. **Pre-run** (at `build_jmeter_command` time, before JMeter starts):
   - Write `run_summary.json` with: test plan name, parameters used, slaves, mode, start time, filter config
   - Replaces current `run_info.json`

2. **Post-run stats** (lazy, on first access):
   - Read from `filtered.jtl` (or `results.jtl` if no filtering)
   - Append JTL stats to existing `run_summary.json`
   - No eager JTL parsing in the post-run pipeline — avoids adding time to post-processing

**Why lazy, not eager:** Post-run pipeline already includes JTL filtering + report generation (slow). Adding JTL parsing would extend it further. Lazy generation from the smaller `filtered.jtl` is fast enough on first access.

#### P5: Live stats shared with dashboard

**Problem:** Live stats on `/plans` are parsed from JMeter stdout in the browser. Dashboard has no access to these values — it only knows a test is running, not how it's going.

**Fix:** The process manager stores the latest parsed summary values (throughput, avg RT, errors, VUs) from log lines on the backend side. The dashboard's runner status card can display real-time performance during a run. Single source of truth.

#### P6: Remove global properties from Plans page

**Problem:** `config.properties` served as a parameter default mechanism, but JMX scripts already provide defaults via `__P(name, default)`. The global properties modal and "Save to Defaults" button are redundant and cause confusion (additive-only merge accumulates stale keys from different plans).

**What to remove from the Plans page:**
- "Edit Global Properties" button and modal
- "Save to Defaults" button
- All references to `config.properties` for parameter defaults

**What to migrate:**
- `filter_sub_results` and `label_pattern` → move to `settings.json` or `project.json`
- `results_dir` → already in `project.json` paths

**What stays unchanged:**
- `config.properties` file itself — not deleted, still works for legacy batch script CLI runs
- The webapp just stops reading/writing it for parameter management

#### P7: Distributed mode stop — slave cleanup

**Problem:** `stop()` only kills the local JMeter controller process (`process.terminate()`). In distributed mode, slave JVMs continue running their thread groups. Slaves need `jmeter-server` restart before accepting new tests.

**Approaches to investigate (not implementing now — needs testing):**

| # | Approach | How it works | Pros | Cons |
|---|----------|-------------|------|------|
| 1 | **Shutdown port (UDP 4445)** | Send "Shutdown" or "StopTestNow" to localhost:4445. Propagates to slaves via RMI while master is alive. | Clean, no slave restart needed | Must send before killing master |
| 2 | **`shutdown.sh` / `stoptest.sh`** | JMeter's built-in scripts that send UDP to shutdown port | Same as above, just a wrapper | Same as above |
| 3 | **`-X` flag at start** | Add `-X` to JMeter command — slaves exit after test completion | Simple, clean shutdown | Only works for normal completion, not mid-test stop |
| 4 | **Stop master gracefully first** | Use shutdown port to stop master (propagates to slaves), instead of `process.terminate()` | Proper distributed cleanup | Slightly slower than kill |
| 5 | **SSH kill + restart** | SSH to each slave, kill JMeter, restart `jmeter-server` | Guaranteed to work | Destructive, needs SSH access, requires service restart |

**Recommendation:** Option 4 (graceful master stop via shutdown port) as primary, with Option 5 as fallback. Add `-X` flag by default for normal completions. Needs real distributed environment testing.

#### P8: Presets — plan-aware or warn on mismatch

**Problem:** Presets are saved globally. A preset from Plan A can be applied to Plan B, even if parameters don't overlap. No warning, silently does nothing for mismatched keys.

**Fix options (decide during implementation):**
- A) Scope presets per-plan (stored under plan filename key)
- B) Keep global but show warning: "3 of 5 preset values don't match this plan's parameters"
- C) Keep global, only apply matching keys, highlight which ones matched

---

## 3. Results

**Files:** `routers/results.py`, `templates/results.html`, `services/jtl_parser.py`, `services/analysis.py`

### Current Issues (Code Quality)

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | Blocking `subprocess.run()` / `proc.communicate()` in regeneration — blocks event loop for minutes | results.py:221,233,344 | High |
| 2 | Stats/compare/labels/analysis all read first `*.jtl` found — no preference for `filtered.jtl` | results.py:68-71,283-286,413-418,558-563 | Medium |
| 3 | Regeneration deletes `filtered.jtl` (same issue as process_manager) | results.py:194-195,243-244 | Medium |
| 4 | Bulk regenerate uses hardcoded `filter_sub_results: true, label_pattern: ''` — ignores per-result saved settings | results.html:414 | Medium |
| 5 | Download zip uses `ZIP_STORED` (no compression) — wastes bandwidth for text-heavy HTML reports | results.py:448,489,516 | Low |

### Current State

The page shows a sortable/searchable table of all result folders with actions per row: Stats preview (expandable), Open report (localhost: filesystem, remote: API proxy), Download (zip with optional JTL), Regenerate (modal with filter options + label picker), Open folder (localhost), Delete.

Multi-select features: Compare (2 results side-by-side), Bulk regenerate, Bundle download.

Regeneration is atomic (generates to temp dir, swaps on success) with abort support. Analysis engine supports rule-based + AI (Ollama).

### Changes Agreed

#### R1: All reads should prefer `filtered.jtl`

**Problem:** Multiple endpoints read the first `*.jtl` found, which is typically `results.jtl` (raw, includes sub-results). Stats shown to the user don't match the HTML report (which was generated from filtered data).

**Affected endpoints:**
- `GET /api/results/{folder}/stats` — stats preview
- `GET /api/results/{folder}/labels` — label picker
- `GET /api/results/compare` — run comparison
- `POST /api/results/{folder}/analyze` — analysis engine

**Fix:** All these endpoints should prefer `filtered.jtl` when it exists, falling back to `results.jtl`. Simple helper function:
```python
def _find_jtl(folder_path: Path) -> Path | None:
    filtered = folder_path / "filtered.jtl"
    if filtered.exists():
        return filtered
    jtl_files = [f for f in folder_path.glob("*.jtl") if f.name != "filtered.jtl"]
    return jtl_files[0] if jtl_files else None
```

#### R2: Keep `filtered.jtl` on regeneration

**Problem:** Same as Page 2 P3. Regeneration deletes `filtered.jtl` after report generation.

**Fix:** Remove the delete at results.py:243-244. On re-regeneration, the old `filtered.jtl` is replaced by the new one (delete at line 194-195 stays — it clears the old before re-filtering). The flow becomes:

1. Delete old `filtered.jtl` (clear previous filter)
2. Filter `results.jtl` → new `filtered.jtl`
3. Generate report from `filtered.jtl`
4. **Keep** `filtered.jtl`
5. Invalidate `run_summary.json` stats (filtered data changed, stats need recalculation)

`filtered.jtl` always reflects the last filter settings used. `results.jtl` stays as the raw source of truth for future re-filtering.

#### R3: Non-blocking regeneration

**Problem:** `subprocess.run()` and `proc.communicate()` block the async event loop during filter + report generation. A single regeneration can take minutes for large JTLs, making the entire webapp unresponsive.

**Fix:** Use `asyncio.create_subprocess_exec` for both filter and report generation steps. This allows the event loop to handle other requests during regeneration.

#### R4: Show performance metrics in results table

**Problem:** The results table shows folder name, date, size, and report/JTL badges — but no performance data. Users must click "Stats" on each result individually to see avg RT, error rate, throughput.

**Fix:** With `run_summary.json` available, the results list API can include key metrics (avg RT, p95, error %, throughput, peak VUs) directly. The table shows a compact metrics row or inline badges. No extra API calls needed — data comes from the pre-built summary.

#### R5: Bulk regenerate should respect per-result filter settings

**Problem:** Bulk regeneration sends hardcoded `filter_sub_results: true, label_pattern: ''` for all selected results. This ignores each result's saved filter settings from `regen_info.json` or `run_info.json`.

**Fix options (decide during implementation):**
- A) Use each result's saved filter settings (from `regen_info.json` / `run_info.json`)
- B) Show filter modal first (applies same settings to all selected)
- C) Default to saved settings with an "override all" checkbox in the modal

#### R6: Per-transaction comparison

**Problem:** Compare view only shows overall metrics (avg, median, p90, p95, p99, error_pct, throughput). If one transaction degraded while another improved, it's invisible.

**Fix:** Add a per-transaction comparison table below the overall table. Match transactions by label, show side-by-side metrics with change percentages. Highlight transactions that got significantly worse.

#### R7: Use `ZIP_DEFLATED` for downloads

**Problem:** `ZIP_STORED` means no compression. HTML reports are text-heavy and compress 5-10x. Large reports waste bandwidth unnecessarily.

**Fix:** Change `ZIP_STORED` to `ZIP_DEFLATED` in `_add_report_to_zip` and related zip creation. Optionally keep `ZIP_STORED` for JTL files (they're CSV and compress well, but the zip time for large JTLs might not be worth it).

#### R8: Pagination for large result sets

**Problem:** All result folders are loaded at once. With hundreds of results over time, this gets slow — both the folder scanning and the API response.

**Fix:** Add `?page=1&per_page=25` to `GET /api/results/list`. Backend scans folders once, returns paginated slice. Frontend shows page controls. Search still works across all results (backend-filtered).

---

## 4. Test Data

**Files:** `routers/test_data.py`, `templates/test_data.html`, `services/data.py`, `services/slaves.py`

### Current Issues (Code Quality)

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | Custom CSV templates stored in `localStorage` — not synced across browsers/machines | test_data.html:478-488 | Low |
| 2 | Upload silently overwrites existing files — no duplicate check (inconsistent with test plan upload which returns 409) | test_data.py:136-138 | Medium |

### Current State

Three sections:
- **CSV Files** — table of all CSV files in `test_data/` with columns, row count, size. Actions: preview (modal with progressive loading), download, rename (inline click-to-edit), delete.
- **CSV Builder** — visual column definition with 5 types: Sequential ID (multi-range with prefix/padding), Static, Random Pick (with per-value counts), Expression (reference other columns via `{col_name}`), Sequence (numeric start + step). Built-in templates (4) + custom templates (localStorage). Client-side preview (5 rows) before server-side generation.
- **Distribute to Slaves** — per-file mode selection (copy entire file vs split rows across slaves). Split supports offset/size. Preview shows per-slave row distribution table with data samples. Distribution via SSH/SCP using `vm_config.json` credentials.

### Changes Agreed

#### D1: Move custom templates to server-side storage

**Problem:** Custom CSV builder templates are stored in `localStorage`. They don't sync across browsers or machines. Runner presets (on the Plans page) are stored server-side in `presets.json`. Inconsistent approach.

**Fix:** Store custom CSV templates in a server-side JSON file (e.g. `csv_templates.json`), similar to how runner presets use `presets.json`. Add API endpoints:
- `GET /api/data/templates` — list all templates (built-in + custom)
- `POST /api/data/templates` — save custom template
- `DELETE /api/data/templates/{name}` — delete custom template

Built-in templates remain hardcoded in the backend (not editable). Custom templates are user-created and deletable.

#### D2: Upload duplicate check

**Problem:** CSV upload doesn't check if the file already exists — silently overwrites. Test plan upload returns 409 for duplicates. Inconsistent and potentially destructive.

**Fix:** Check `dest.exists()` before writing. If file exists, return 409 with error message. Optionally add an `overwrite=true` query param for explicit overwrites, with a confirmation dialog in the frontend.

#### D3: Distribution progress streaming

**Problem:** The distribute API (`POST /api/data/distribute`) is synchronous. For many slaves with large files, the UI shows a spinner with no feedback until completion.

**Fix:** Stream progress back to the frontend. Options:
- A) WebSocket for real-time per-slave progress updates
- B) Server-Sent Events (SSE) — simpler, one-directional
- C) Polling — frontend polls a status endpoint periodically

Given the existing WebSocket pattern from the runner, option A is most consistent.

#### D4: Record test data files in `run_summary.json`

**Problem:** No record of which CSV files (and their contents/row counts) were used for a test run. If test data is modified between runs, you lose context of what data produced which results.

**Fix:** When building the JMeter command (`build_jmeter_command`), scan the JMX for CSV Data Set Config elements to identify referenced data files. Record in `run_summary.json`:
```json
{
  "test_data": [
    {"filename": "master_data.csv", "rows": 45000, "size": 1234567}
  ]
}
```
This gives full reproducibility context: test plan + parameters + slaves + test data = complete run configuration.

---

## 5. Slave VMs

**Files:** `routers/config.py`, `templates/slaves.html`, `services/slaves.py`

### Current Issues (Code Quality)

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | `tempfile.mktemp()` insecure (TOCTOU race) — should use `NamedTemporaryFile` | config.py:315 | Medium |
| 2 | `import json as _json` inside function body — inconsistent with codebase | config.py:263,270 | Low |
| 3 | `noqa: E402` late imports at module level — should restructure | config.py:141,253 | Low |
| 4 | Duplicate rendering logic between `renderList()` and `renderGrid()` (~70% shared) | slaves.html:167-257 | Low |
| 5 | SSH password stored as plain text in `vm_config.json` | config.py:78-86 | Low (local tool) |
| 6 | Module-level mutable `_last_slave_status` — no TTL, no thread safety | config.py:147 | Medium |

### Current State

Three sections:
- **Slave List** — list/grid view toggle, status dots/badges, inline IP editing, nickname support, enable/disable toggle, per-slave SSH overrides (expandable config panel), bulk selection (enable/disable/remove), individual start/stop JMeter server, manual status check via SSH.
- **VM Configuration** — collapsible. Global SSH defaults (user, password, key file, dest path), JMeter path on slaves, OS selection (Linux/Windows), start/stop scripts.
- **JMeter Properties** — collapsible. Manual key-value property editor with per-property enable/disable, InfluxDB Backend Listener preset, push properties file to all slaves via SCP.

### Changes Agreed

#### S1: Remove auto-status check on page load

**Problem:** `refreshStatus()` is called on every page load (slaves.html:741). This triggers SSH connections to all slaves — slow with many slaves, noisy if they're down.

**Fix:** Remove the auto-check. Status is manual-only via the "Check Status" button. Optionally show last-checked timestamp next to status badges so the user knows how stale the data is.

#### S2: Improve status cache with TTL

**Problem:** `_last_slave_status` is a module-level list with no TTL or persistence. Dashboard health dots depend on it, but it's only populated when someone visits `/slaves` and checks status. If nobody checks, the dashboard shows empty/stale health data.

**Fix:** Add a TTL to the cache (e.g. 5 minutes). When the dashboard requests slave health, if the cache is expired, return stale data with a "last checked" timestamp — don't trigger a new check automatically (that's expensive). The frontend can show "checked 2h ago" next to the dots.

#### S3: Remove JMeter Properties section entirely

**Problem:** The current manual key-value JMeter Properties section (including InfluxDB Backend Listener preset and "Push to Slaves") is the wrong approach. Backend Listener properties need to be baked into the JMX file, not passed as command-line flags, because slaves don't receive `-G` flags.

**What to remove:**
- The entire "JMeter Properties" collapsible section from the Slaves page
- The InfluxDB Backend Listener preset
- The "Push to Slaves" button
- `jmeter_properties.json` file and its API endpoints (`GET/PUT /api/config/jmeter-properties`, `POST /api/config/push-properties`)

**What replaces it:** See S4 (JMeter Properties Explorer) and S5 (JMX patching).

#### S4: JMeter Properties Explorer (master + all slaves)

**Problem:** Currently users manually type property keys and hope they spelled them correctly. JMeter has hundreds of properties in `jmeter.properties` with section comments and documentation. Users frequently need to change or add properties in the `bin/` folder of JMeter installations across the fleet. Currently this is done by manually SSH-ing into each slave and editing the file.

**How it works:**
1. Parse `<jmeter_home>/bin/jmeter.properties` from the configured JMeter installation path
2. Extract all properties with defaults, grouped by category (HTTP, Reporting, CSV, etc.)
3. Present as a searchable/filterable list — user can browse, toggle on/off, override values
4. Only user-overridden properties are saved (not the full file)
5. Applied to **both master and all slaves**:
   - Master: via `-J` flags at run time
   - Slaves: push overridden properties file to all slaves via SCP (overwrites `jmeter.properties` on the slave's JMeter installation)
6. Per-project overrides — saved in project config so different projects can have different property profiles

**Where it lives:** Could stay on the Slaves page (renamed to "Fleet Management" or similar) or move to Settings. Decide during implementation.

#### S5: JMX patching at run time

**Problem:** Backend Listener configuration is embedded in the JMX XML. Slaves don't receive global properties (`-G` flags). Values like `run_id` need to change on every run.

**How it works:**
1. When user clicks "Start Test" on the Plans page
2. Before launching JMeter, the webapp:
   - Reads the original JMX
   - Finds Backend Listener elements (and other property-driven elements)
   - Patches their values with current overrides from the Properties Explorer
   - Sets `run_id` = result folder name (e.g. `20260225_3`) — auto-generated per run
   - Writes the patched JMX to the result directory
   - Uses the **patched** JMX for the test run
3. Original JMX stays untouched
4. Patched JMX saved in result folder = full reproducibility

**Dynamic values:**
- `run_id` — auto from result folder name
- `influxdbUrl`, `application`, etc. — from Properties Explorer overrides

#### S6: No start/stop progress for many slaves

**Problem:** Start All / Stop All waits for all SSH commands to complete before responding. With 10+ slaves, the UI shows "Starting..." with no per-slave feedback.

**Fix:** Stream per-slave results as they complete. Options:
- A) Return results progressively (SSE or WebSocket)
- B) Show optimistic UI — update each slave's badge as results come in via polling
Given the existing WebSocket pattern, option A is most consistent.

#### S7: Extract shared rendering logic

**Problem:** `renderList()` and `renderGrid()` share ~70% of the same HTML generation (status badges, action buttons, config panels, selection checkboxes). Any new feature must be added to both.

**Fix:** Extract common parts into shared helper functions (`renderSlaveActions(s)`, `renderConfigPanel(s)`, etc.). The list/grid functions only handle layout, not content.

#### S8: Deployment workflow — deploy JMeter scripts to slaves from master

**Problem:** Currently the page can start/stop JMeter server on slaves, but it assumes the start/stop scripts already exist on the slaves. In the past, users manually SSH into each slave, create the start script, configure JMeter, then the master runs a Python script to execute those scripts remotely. There's no way to deploy scripts or configurations from the UI.

**What the page should support:**
1. **Deploy start/stop scripts** — master generates or uploads start/stop scripts and pushes them to all slaves via SCP. Scripts are generated from the VM Configuration form (JMeter path, OS type, JVM args, etc.)
2. **Deploy JMeter configuration** — push `jmeter.properties` overrides, `user.properties`, or other config files to all slaves
3. **Prerequisite check** — before any deployment, verify that each slave has:
   - SSH connectivity (already exists: "Check Status")
   - JMeter installed at the configured path (new: `ls <jmeter_path>/bin/jmeter` or equivalent)
   - Java installed and accessible (new: `java -version` check)
4. **Deployment status** — track what's been deployed to each slave, show last deployment timestamp

**Deployment flow for a new slave:**
1. Add slave IP to the list
2. Check Status → verify SSH connectivity
3. Run prerequisite check → verify JMeter + Java installed
4. Deploy start/stop scripts (auto-generated or custom)
5. Deploy JMeter properties overrides
6. Start JMeter server → ready for distributed testing

#### S9: Windows slave support

**Problem:** The current implementation has basic Windows support (`jmeter-server.bat`, `taskkill`), but several operations assume Linux:
- `_scp_upload()` uses `mkdir -p` — doesn't work on Windows
- Start command uses `nohup ... > /dev/null 2>&1 &` — Linux-only
- Stop command uses `pkill -f jmeter-server` — Linux-only
- File paths use forward slashes

**Current Windows handling (what exists):**
- `_auto_start_command()` returns `jmeter-server.bat` for Windows
- `_auto_stop_command()` returns `taskkill /f /im jmeter-server.bat` for Windows
- `start_jmeter_server()` wraps with `start /b` for Windows
- OS type selectable per-slave via overrides

**What needs fixing:**
1. **Remote directory creation**: `mkdir -p` → `if not exist "%dir%" mkdir "%dir%"` for Windows
2. **SCP upload path handling**: Forward slashes → backslashes for Windows paths
3. **Start command**: `start /b` may not work over SSH — investigate `cmd /c start /b` or PowerShell `Start-Process`
4. **Stop command**: `taskkill` works but may need `wmic` or `Get-Process` as fallback
5. **Prerequisites documentation**: Windows requires OpenSSH Server installed and running (built into Windows 10+, needs enabling). Document steps:
   - Enable OpenSSH Server in Windows Settings → Optional Features
   - Start `sshd` service
   - Configure firewall rule for port 22
   - Test with `ssh user@windows-slave` from master

**SSH on Windows limitations:**
- OpenSSH Server on Windows uses `cmd.exe` as default shell (not PowerShell)
- File upload via SCP works fine (SSH handles the transfer)
- Environment variables and path separators differ
- No `nohup` — use `start /b` or Windows service approach
- The page should detect OS per-slave and generate appropriate commands

#### S10: Page rename consideration

**Problem:** The page is called "Slave VMs" but its scope is expanding beyond just listing VMs. With deployment workflow, properties management, and fleet-wide configuration, it's becoming a fleet management hub.

**Options:**
- A) Keep "Slave VMs" (familiar JMeter terminology)
- B) Rename to "Fleet" or "Fleet Management"
- C) Rename to "Remote Servers"
- Decide during implementation.

---

## 6. Settings

**Files:** `routers/settings.py`, `templates/settings.html`, `services/report_properties.py`

### Current Issues (Code Quality)

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | Two separate API calls in `saveAllSettings()` — saves `settings.json` then `project.json`. If second fails, state is inconsistent | settings.html:446-457 | Medium |
| 2 | Report tab has its own Save button separate from main Save — confusing UX | settings.html:261 | Low |
| 3 | Heavy inline styles on form layouts (`flex-wrap:wrap`, `min-width`, `flex:1/2`) | settings.html throughout | Low |
| 4 | System info cards inline styles | settings.html:503-506 | Low |
| 5 | `save_settings()` writes directly — not atomic (no temp file + rename) | settings.py:76-80 | Low |

### Current State

Five tabs:
- **General** — Server (domain, host, port, base_path, allow_external), Appearance (theme, sidebar), Runner (auto-scroll, max log lines, confirm stop), Results (sort order), Security (auth token)
- **Project** — Project name, description, JMeter home, results dir, config properties file path
- **Report** — Graph toggles (Heavy/Light categories), granularity selector, presets (Disable Heavy, Enable All, Reset), separate Save button
- **Integrations** — Ollama (URL, model, timeout, connection test), Monitoring (Grafana URL, InfluxDB URL)
- **System** — Read-only info cards (JMeter, Java, Python, OS, disk usage)

Supporting features: live theme preview, JMeter auto-detect from PATH, export/import settings as JSON, server restart with redirect, token visibility toggle, access control (viewer = readonly).

### Changes Agreed

#### ST1: Remove "Config Properties File" field from Project tab

**Problem:** The Config Properties File field (`settings.html:183-184`) lets users point to a `config.properties` file. This concept is being deprecated — the webapp will stop reading/writing `config.properties` for parameter management (see P4 on Plans page). The file itself stays for legacy batch scripts but the webapp doesn't need a path to it.

**Fix:** Remove the "Config Properties File" form group from the Project tab. Remove related backend handling if any.

#### ST2: Add filter configuration to Settings

**Problem:** Filter settings (`filter_sub_results`, `label_pattern`) are currently stored in `config.properties` and managed on the Config page. With Config page removal, these need a new home.

**Fix:** Add a "Filtering" section to the General tab (or a new sub-section under Results):
- Toggle: "Filter sub-results" (boolean, default true)
- Input: "Label pattern" (regex string, default empty = no filter)
These get saved to `settings.json` and read by the runner at report generation time.

#### ST3: Merge Report tab save into main Save

**Problem:** The Report tab has its own "Save Report Settings" button that calls a separate API (`PUT /api/settings/report`). The main Save button at the top calls `PUT /api/settings` + `PUT /api/project`. Three API calls total, each independent — if one fails, state is partially saved.

**Fix:** Either:
- A) Merge report settings into the main `settings.json` so one Save covers everything
- B) Keep separate APIs but wire the main Save button to call all of them, removing the Report tab's own Save button
Option A is cleaner — one file, one API, one Save.

#### ST4: Non-atomic settings save

**Problem:** `save_settings()` writes directly to `settings.json`. If the process crashes mid-write, the file could be corrupted.

**Fix:** Write to a temp file in the same directory, then rename (atomic on most filesystems). Low priority but good practice.

#### ST5: JMeter Properties Explorer placement

**Problem:** The Properties Explorer (S4 from Slave VMs page) needs a home. Options:
- A) On the Slaves/Fleet page — close to the slaves it deploys to
- B) In Settings under a new "JMeter Properties" tab — centralized config
- C) Both — browse in Settings, deploy from Slaves page

**Decision:** Defer to implementation. The Properties Explorer is primarily a configuration tool, so Settings is a natural fit. But deployment to slaves is an action that belongs on the Slaves page.

#### ST6: Export/Import already exists — extend to bundle project.json

**Problem:** Export/Import is already implemented (`settings.html:660-681`, `settings.py:166-196`). The original evaluation listed it as missing (Issue #9). However, it only exports `settings.json` — it doesn't include `project.json` or report settings.

**Fix:** Extend export to bundle all config files (`settings.json` + `project.json` + report settings) into a single download. Import should restore all of them. This makes project setup portable.

#### ST7: Simplify Server section — move installation-time settings out of UI

**Problem:** The Server section in the General tab has fields that are better set at installation/startup time rather than through the runtime UI:
- **Domain** — not needed. Cloudflare tunnel (or any reverse proxy) is external to the app and doesn't require the app to know its domain.
- **Host/Port/Allow External** — these are startup arguments. Changing them requires a server restart anyway.

**Fix:** Remove `domain` field entirely. Consider moving `host`, `port`, and `allow_external` to CLI arguments or environment variables only (not UI-configurable). Keep `base_path` in Settings if it's used for URL generation in templates.
