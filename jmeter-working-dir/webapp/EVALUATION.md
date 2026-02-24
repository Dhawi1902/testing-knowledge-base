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
| 4 | **Tests** | Zero test coverage. At minimum: API endpoint tests for auth, path traversal rejection, CRUD operations. FastAPI has `TestClient` built in. |
| 5 | ~~**Setup wizard / first-run flow**~~ PARTIAL | Token generation done (auto-generate + show once + hash). Path validation and JMeter detection already existed in setup.html. |
| 6 | **Server-side logging** | No structured logging. When things fail, there's no audit trail. Add Python `logging` with rotation. |
| 7 | **API docs** | FastAPI auto-generates OpenAPI/Swagger at `/docs`. Currently not exposed or may be behind base_path. Worth enabling for development. |
| 8 | ~~**Remove Scripts page**~~ DONE | Router disconnected from main.py, sidebar link removed from base.html. Files kept for reference. |

### Nice to Have

| # | Item | Detail |
|---|------|--------|
| 9 | **Setup script** | `setup.py` or shell script that checks prerequisites (Python, JMeter, Java), installs pip deps, creates default configs. Replaces need for Docker — JMeter needs bare-metal resources for accurate load generation. |
| 10 | **README for webapp** | Setup instructions, architecture overview, configuration reference. |
| 11 | **Mobile UX audit** | Test plans page has mobile action bar, but other pages haven't been checked for mobile. |
| 12 | **Accessibility** | No a11y audit done. Keyboard navigation, screen reader labels, focus management in modals. |
| 13 | **Error boundary / global error handler** | Frontend currently has per-function try/catch. A global `api()` wrapper error handler would be more consistent. |

### Fix Priority Order

If tackling everything, this is the recommended sequence:

1. ~~**Security fixes**~~ DONE — path traversal, token hashing, auth defaults
2. ~~**Bug fixes**~~ DONE — stale variable names from refactoring
3. ~~**Remove dead code**~~ DONE — Scripts page removed, backward compat fallbacks removed
4. **Add tests** — at least for auth and path traversal
5. ~~**Setup wizard**~~ DONE — first-run token generation + path validation
6. ~~**Cross-cutting cleanup**~~ DONE — `escAttr` applied, error messages genericized. Inline styles kept (cosmetic, no impact).
7. **Dashboard improvements** — Tier 1 (last run summary, run history, disk usage)
8. **Future features** — Windows slaves, properties management, etc.
