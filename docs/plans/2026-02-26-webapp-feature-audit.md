# Webapp Feature Audit — 2026-02-26

Page-by-page review of the JMeter Test Dashboard webapp, identifying missing features, UX issues, and bugs.

---

## Dashboard

| # | Finding | Type | Priority |
|---|---------|------|----------|
| 1 | **Alerts not clickable** — e.g. "1 result(s) missing HTML report" is display-only. Should link to Results page or highlight the affected folder | Missing | v1 |
| 2 | **Run History capped at 10** — no "View All" link or pagination | Missing | v1 |
| 3 | **Monitoring cards always "Not configured"** — no link to Integrations settings to fix it | UX | v1 |

## Test Plans & Runner

| # | Finding | Type | Priority |
|---|---------|------|----------|
| 4 | **No Dry Run button** — backend supports `dry_run=True` but no UI button to execute without saving results | Missing | v1 |
| 5 | **Command Preview hard to read** — long single-line string with absolute paths, no wrapping or copy button | UX | v1 |
| 6 | **No duplicate/clone test plan** | Missing | v1 |
| 7 | **No rename test plan** | Missing | v1 |
| 8 | **No sound on test complete** — browser notification only (and only when tab is in background) | Missing | v1 |
| 9 | **Filter label presets** — currently one global pattern in Settings. Should have presets on runner page per test plan (e.g. "MAYA transactions only", "HTTP only") | Missing | v1 |

## Results

| # | Finding | Type | Priority |
|---|---------|------|----------|
| 10 | **No bulk delete** — checkboxes exist but only wire to Download/Compare/Regenerate. No "Delete Selected" | Missing | v1 |
| 11 | **No result alias/label** — folder names are date-based (e.g. `20260225_6`). Add a display name/label stored in `run_summary.json`, keep folder name as-is | Missing | v1 |
| 12 | **No pagination** — backend has `page`/`per_page` params but UI loads everything at once | Missing | v1 |
| 13 | **AI Analyze button missing** — backend has `POST /api/results/{folder}/analyze` but no trigger in UI | Missing | v2 |
| 14 | **No view analysis panel** — `GET /api/results/{folder}/analysis` exists but no UI to display findings | Missing | v2 |
| 15 | **Ollama config mismatch** — Settings saves to `settings.json` but analyze endpoint reads from `project.json` | Bug | v2 |

## Test Data

| # | Finding | Type | Priority |
|---|---------|------|----------|
| 16 | **Upload CSV can't overwrite** — backend supports `overwrite=true` param but frontend never sends it. Duplicate filename → 409, must delete first | Missing | v1 |

## Fleet — v1

### Provisioning
| # | Finding | Type | Priority |
|---|---------|------|----------|
| 17 | **Provision button** — SSH into slave, run idempotent setup (Java, JMeter, dirs, scripts, firewall). Linux only | Missing | v1 |
| 18 | **Provision status check** — detect what's installed per slave (Java ✓ JMeter ✓ Scripts ✓ Data ✓) | Missing | v1 |
| 19 | **Bulk provision** — provision multiple slaves at once | Missing | v1 |
| 20 | **Always refresh scripts** — overwrite `start-slave.sh` / `stop-slave.sh` with latest version on every provision | Missing | v1 |

### Runtime
| # | Finding | Type | Priority |
|---|---------|------|----------|
| 21 | **JMeter heap settings in UI** — edit Xms, Xmx, GC algo from VM Configuration panel, applied on slave start | Missing | v1 |
| 22 | **View slave log** — fetch `~/jmeter-slave/jmeter-slave.log` via SSH and display in UI | Missing | v1 |
| 23 | **Restart button** — stop + start in one click (currently separate) | Missing | v1 |

### Config
| # | Finding | Type | Priority |
|---|---------|------|----------|
| 24 | **Standardized paths** — `~/jmeter-slave/` driven by `vm_config.json`, no hardcoded paths | Missing | v1 |
| 25 | **Global vm_config + per-slave overrides** — global defaults with override support per slave (pattern already exists) | Missing | v1 |
| 26 | **JMeter Properties editor** — two-tab panel (Master/Slave) managing `user.properties` overrides with searchable catalog from `jmeter.properties` | Done | v1 |

### Connectivity
| # | Finding | Type | Priority |
|---|---------|------|----------|
| 27 | **Test SSH connection** — verify SSH works before provisioning (wrong key? wrong IP?) | Missing | v1 |
| 28 | **Test RMI port** — check if port 1099 is reachable from master | Missing | v1 |

### Data
| # | Finding | Type | Priority |
|---|---------|------|----------|
| 29 | **Distribute data from Fleet page** — quick "Sync Data" button (currently only on Test Data page) | Missing | v1 |

### Monitoring
| # | Finding | Type | Priority |
|---|---------|------|----------|
| 30 | **Slave resource usage** — CPU/RAM during test run, to detect slave bottlenecks | Missing | v1 |
| 31 | **Health history** — persist status checks, show trend over time | Missing | v1 |

### Cleanup
| # | Finding | Type | Priority |
|---|---------|------|----------|
| 32 | **Clean test data on slaves** — wipe old CSVs | Missing | v1 |
| 33 | **Clean old logs** — wipe `jmeter-slave.log` | Missing | v1 |

## Fleet — v2

| # | Finding | Type | Priority |
|---|---------|------|----------|
| 34 | **Distribute JMeter plugins** — push `.jar` files to `/opt/jmeter/lib/ext/` | Missing | v2 |
| 35 | **Update JMeter version** — download new version on all slaves at once | Missing | v2 |
| 36 | **Update Java version** — update across all slaves | Missing | v2 |
| 37 | **Disk space per slave** — show available disk to avoid "no space left" mid-test | Missing | v2 |
| 38 | **Windows slave support** — provision and manage Windows-based slaves | Missing | v2 |

## Settings

| # | Finding | Type | Priority |
|---|---------|------|----------|
| 20 | **Console DOM warning** on Fleet and Settings pages (password field not in form) | Minor | v1 |

---

## Decisions

- **Filter label presets (#9):** Add preset dropdown on runner page. Different test plans need different filter patterns. Reuse the same preset UX pattern already used for test parameters.
- **Result rename (#11):** Use alias/label approach instead of actual folder rename. Store display name in `run_summary.json`. UI shows label when set, falls back to folder name. No file path changes needed.
- **AI features (#13-15):** Deferred to v2. Backend already built — when ready, it's mostly wiring up UI buttons.
- **Fleet provisioning:** Linux only (OCI Oracle Linux). Use default `opc` user. Idempotent setup — safe to run on fresh or cloned instances. Standardized path: `~/jmeter-slave/`. Global vm_config with per-slave overrides.
- **Fleet paths:** `~/jmeter-slave/` resolves via `$HOME` based on SSH user. No hardcoded usernames.
- **Fleet heap:** Configurable in UI via VM Configuration panel. Applied when starting slaves.

---

## Execution Plan — 7 Sessions

### Session 1: Quick Wins
Small, independent fixes across multiple pages. Low risk, fast to ship.

| # | Item | Page |
|---|------|------|
| 1 | Alerts clickable (link to Results) | Dashboard |
| 3 | Monitoring cards → link to Integrations settings | Dashboard |
| 5 | Command Preview wrapping + copy button | Test Plans |
| 8 | Sound on test complete | Test Plans |
| 16 | Upload CSV overwrite support | Test Data |
| 23 | Restart button (stop + start) | Fleet |
| 39 | Console DOM warning fix | Settings |

### Session 2: Test Plans & Runner
All runner page enhancements.

| # | Item |
|---|------|
| 4 | Dry Run button |
| 6 | Duplicate/clone test plan |
| 7 | Rename test plan |
| 9 | Filter label presets |

### Session 3: Results Page
Results table improvements + dashboard tie-in.

| # | Item |
|---|------|
| 10 | Bulk delete |
| 11 | Result alias/label |
| 12 | Pagination (wire up backend params) |
| 2 | Dashboard Run History "View All" (reuses pagination pattern) |

### Session 4: Fleet — Config Foundation
Must be done before provisioning. Sets up paths, config structure, heap UI.

| # | Item |
|---|------|
| 24 | Standardized paths (`~/jmeter-slave/`) |
| 25 | Global vm_config + per-slave overrides |
| 21 | JMeter heap settings in UI |
| 26 | JMeter Properties editor (`user.properties`) |

### Session 5: Fleet — Connectivity & Provisioning
Core provisioning feature. Depends on Session 4.

| # | Item |
|---|------|
| 27 | Test SSH connection |
| 28 | Test RMI port |
| 17 | Provision button |
| 18 | Provision status check |
| 19 | Bulk provision |
| 20 | Always refresh scripts |

### Session 6: Fleet — Data, Logs & Cleanup
Day-to-day slave operations. Depends on Session 4.

| # | Item |
|---|------|
| 29 | Distribute data from Fleet page |
| 22 | View slave log |
| 32 | Clean test data on slaves |
| 33 | Clean old logs |

### Session 7: Fleet — Monitoring
Depends on Sessions 4-5.

| # | Item |
|---|------|
| 30 | Slave resource usage (CPU/RAM) |
| 31 | Health history |

### Dependencies

```
Session 1 (Quick Wins)     ─── independent
Session 2 (Test Plans)     ─── independent
Session 3 (Results)        ─── independent
Session 4 (Fleet Config)   ─── independent
Session 5 (Fleet Provision)─── depends on Session 4
Session 6 (Fleet Data)     ─── depends on Session 4
Session 7 (Fleet Monitor)  ─── depends on Session 4-5
```

Sessions 1, 2, 3, 4 can be done in any order. Sessions 5-7 must come after 4.

### Parallel Execution — 4 Waves

```
Wave 1:  Session 1 alone          (touches files across all pages)
Wave 2:  Session 2 + 3 + 4        (max 3 parallel — different pages, no file conflicts)
Wave 3:  Session 5 + 6            (2 parallel — both depend on Session 4, different features)
Wave 4:  Session 7 alone          (depends on Session 4-5)
```

### How to Start Each Session

Open a new Claude Code session (or Claude chat) and paste the prompt below.
After each session, commit and push before starting the next wave.
If a session runs out of context mid-way, start a new chat with:
"Continue Session N — items X, Y are done. Pick up from item Z."

---

#### Session 1 Prompt

```
Read these files first:
- docs/plans/2026-02-26-webapp-feature-audit.md (full feature list)
- jmeter-working-dir/webapp/CLAUDE.md (project context)

Execute Session 1: Quick Wins (items #1, #3, #5, #8, #16, #23, #39)

For each item:
1. Read the relevant template + router files before changing anything
2. Implement the fix
3. Run tests: cd jmeter-working-dir/webapp && python -m pytest tests/ -x
4. Commit with a descriptive message

Items:
- #1: Dashboard alerts — make them clickable links to the relevant page
- #3: Dashboard monitoring cards — add "Configure" link to /settings (Integrations tab)
- #5: Test Plans command preview — add word-wrap and a "Copy" button
- #8: Test Plans — add audio notification sound when test completes
- #16: Test Data upload CSV — send overwrite=true when file already exists (ask user to confirm)
- #23: Fleet — add "Restart" button (stop + start in one click)
- #39: Settings/Fleet — fix console DOM warning about password field not in form
```

#### Session 2 Prompt

```
Read these files first:
- docs/plans/2026-02-26-webapp-feature-audit.md (full feature list)
- jmeter-working-dir/webapp/CLAUDE.md (project context)

Execute Session 2: Test Plans & Runner (items #4, #6, #7, #9)

For each item:
1. Read test_plans.html, test_plans.py, and jmeter.py before changing anything
2. Implement the feature
3. Add tests for new backend endpoints
4. Run tests: cd jmeter-working-dir/webapp && python -m pytest tests/ -x
5. Commit after each item

Items:
- #4: Dry Run button — add a button next to Start Test that runs JMeter with dry_run=True. Show the command that would execute but don't create result dirs. Backend already supports dry_run param in build_jmeter_command().
- #6: Duplicate/clone test plan — add a "Duplicate" button that copies the .jmx file with a new name (e.g. "Copy of Dummy-HTTP-Test.jmx"). Backend needs a new POST endpoint.
- #7: Rename test plan — add a "Rename" button. Backend needs a new POST endpoint. Update any preset references if needed.
- #9: Filter label presets — add a preset dropdown on the runner page for filter patterns. Different test plans need different filters (e.g. "MAYA transactions only", "HTTP only"). Save/load presets similar to how test parameter presets work. Currently there's one global pattern in Settings > JTL Filter Defaults.
```

#### Session 3 Prompt

```
Read these files first:
- docs/plans/2026-02-26-webapp-feature-audit.md (full feature list)
- jmeter-working-dir/webapp/CLAUDE.md (project context)

Execute Session 3: Results Page (items #10, #11, #12, #2)

For each item:
1. Read results.html, results.py, dashboard.html, dashboard.py before changing anything
2. Implement the feature
3. Add tests for new backend endpoints
4. Run tests: cd jmeter-working-dir/webapp && python -m pytest tests/ -x
5. Commit after each item

Items:
- #10: Bulk delete — add "Delete Selected" button next to existing "Download Selected" and "Compare Selected". Backend needs a new POST /api/results/bulk-delete endpoint. Add confirmation dialog before deleting.
- #11: Result alias/label — add a display name field per result. Store in run_summary.json or run_info.json. Show label in results table when set, fall back to folder name. Add inline edit (click to rename). Do NOT rename the actual folder.
- #12: Pagination — the backend already supports page/per_page/q params in GET /api/results/list. Wire up the frontend to use them instead of loading everything at once. Add page controls at the bottom of the table.
- #2: Dashboard Run History — add a "View All" link below the last 10 runs that navigates to the Results page. Reuse the pagination pattern from #12.
```

#### Session 4 Prompt

```
Read these files first:
- docs/plans/2026-02-26-webapp-feature-audit.md (full feature list, see Fleet sections and Decisions)
- jmeter-working-dir/webapp/CLAUDE.md (project context)
- jmeter-working-dir/config/vm_config.json (current VM config)
- jmeter-working-dir/webapp/services/slaves.py (SSH and slave management)
- jmeter-working-dir/webapp/routers/config.py (fleet router)
- jmeter-working-dir/webapp/templates/slaves.html (fleet template)

Execute Session 4: Fleet — Config Foundation (items #24, #25, #21, #26)

For each item:
1. Read the relevant files before changing anything
2. Implement the feature
3. Add tests
4. Run tests: cd jmeter-working-dir/webapp && python -m pytest tests/ -x
5. Commit after each item

Items:
- #24: Standardized paths — change from hardcoded /home/opc/jmeter-PT/linux/ to ~/jmeter-slave/. The path should resolve via $HOME based on SSH user. Update vm_config.json structure to use a slave_dir field. Update all references in services/slaves.py.
- #25: Global vm_config + per-slave overrides — ensure the existing pattern (global defaults + per-slave overrides) works cleanly for all new fields. The override merge in build_ssh_configs() should handle slave_dir, heap settings, etc.
- #21: JMeter heap settings in UI — add Xms, Xmx, GC algo fields to the VM Configuration panel in slaves.html. Save to vm_config.json jmeter_heap section. These values are used when generating start-slave.sh and when starting slaves.
- #26: JMeter Properties editor — replaced `config.properties` editor with `user.properties` editor. Master tab reads/writes JMeter's `user.properties` via catalog from `jmeter.properties`. Slave tab manages `config/slave-user.properties` pushed during provisioning. Old config.properties endpoints kept for runner backward compatibility. See `docs/plans/2026-02-26-jmeter-properties-editor-design.md`.
```

#### Session 5 Prompt

```
Read these files first:
- docs/plans/2026-02-26-webapp-feature-audit.md (full feature list, see Fleet sections and Decisions)
- jmeter-working-dir/webapp/CLAUDE.md (project context)
- jmeter-working-dir/setup-linux-slave.sh (existing setup script — use as reference for provisioning logic)
- jmeter-working-dir/webapp/services/slaves.py (SSH infrastructure)
- jmeter-working-dir/webapp/routers/config.py (fleet router)
- jmeter-working-dir/webapp/templates/slaves.html (fleet template)
- jmeter-working-dir/config/vm_config.json (VM config with paths and heap)

Execute Session 5: Fleet — Connectivity & Provisioning (items #27, #28, #17, #18, #19, #20)

IMPORTANT context:
- Linux slaves only (OCI Oracle Linux 9)
- SSH user is opc (pre-existing on OCI instances)
- Provisioning must be IDEMPOTENT (safe to run on fresh or cloned instances)
- Slave directory: ~/jmeter-slave/ (from Session 4)
- setup-linux-slave.sh has the full setup logic — adapt it for remote execution via SSH

For each item:
1. Read the relevant files before changing anything
2. Implement the feature
3. Add tests
4. Run tests: cd jmeter-working-dir/webapp && python -m pytest tests/ -x
5. Commit after each item

Items:
- #27: Test SSH connection — add a "Test SSH" button per slave. SSH in, run a simple command (e.g. echo ok), report success/failure with error message. Helps diagnose wrong IP, wrong key, timeout.
- #28: Test RMI port — add a "Test RMI" button per slave. Check if port 1099 is reachable from the master machine. Report success/failure.
- #17: Provision button — add a "Provision" button per slave. SSH in and run idempotent setup: install Java 17 if missing, install JMeter 5.6.3 if missing, create ~/jmeter-slave/ dirs, write start-slave.sh and stop-slave.sh, open firewall ports 1099 and 50000. Show progress/log output in a modal or panel.
- #18: Provision status check — after provisioning (or on demand), check what's installed: Java ✓/✗, JMeter ✓/✗, Scripts ✓/✗, Firewall ✓/✗. Display as status badges per slave.
- #19: Bulk provision — select multiple slaves, provision all at once in parallel.
- #20: Always refresh scripts — on every provision, overwrite start-slave.sh and stop-slave.sh with the latest version (using current vm_config heap settings, paths, etc). This ensures cloned slaves get updated scripts.
```

#### Session 6 Prompt

```
Read these files first:
- docs/plans/2026-02-26-webapp-feature-audit.md (full feature list)
- jmeter-working-dir/webapp/CLAUDE.md (project context)
- jmeter-working-dir/webapp/services/slaves.py (SSH infrastructure)
- jmeter-working-dir/webapp/routers/config.py (fleet router)
- jmeter-working-dir/webapp/templates/slaves.html (fleet template)

Execute Session 6: Fleet — Data, Logs & Cleanup (items #29, #22, #32, #33)

For each item:
1. Read the relevant files before changing anything
2. Implement the feature
3. Add tests
4. Run tests: cd jmeter-working-dir/webapp && python -m pytest tests/ -x
5. Commit after each item

Items:
- #29: Distribute data from Fleet page — add a "Sync Data" button in the Fleet page that triggers the same data distribution as Test Data page. Reuse existing distribute logic from services/slaves.py. Show which files will be sent and progress.
- #22: View slave log — add a "View Log" button per slave that fetches ~/jmeter-slave/jmeter-slave.log via SSH and displays it in a modal or expandable panel. Add a refresh button and auto-scroll.
- #32: Clean test data on slaves — add a "Clean Data" button per slave (or bulk) that deletes CSV files in ~/jmeter-slave/test_data/ via SSH. Add confirmation dialog.
- #33: Clean old logs — add a "Clean Logs" button per slave (or bulk) that truncates or deletes ~/jmeter-slave/jmeter-slave.log via SSH. Add confirmation dialog.
```

#### Session 7 Prompt

```
Read these files first:
- docs/plans/2026-02-26-webapp-feature-audit.md (full feature list)
- jmeter-working-dir/webapp/CLAUDE.md (project context)
- jmeter-working-dir/webapp/services/slaves.py (SSH infrastructure)
- jmeter-working-dir/webapp/routers/config.py (fleet router)
- jmeter-working-dir/webapp/templates/slaves.html (fleet template)

Execute Session 7: Fleet — Monitoring (items #30, #31)

For each item:
1. Read the relevant files before changing anything
2. Implement the feature
3. Add tests
4. Run tests: cd jmeter-working-dir/webapp && python -m pytest tests/ -x
5. Commit after each item

Items:
- #30: Slave resource usage — add CPU and RAM monitoring per slave. SSH in and run system commands (e.g. top -bn1, free -m) to get current usage. Display in the slave card/row. Optionally auto-poll during test runs to detect slave bottlenecks. Show warning if CPU > 80% or RAM > 90%.
- #31: Health history — persist slave status checks (up/down, CPU, RAM, timestamp) to a JSON file or SQLite. Show a simple timeline or sparkline in the Fleet page. Keep last 50 checks per slave. Currently only the most recent check is cached in memory.
```

---

## Summary

| Page | v1 | v2 | Total |
|------|----|----|-------|
| Dashboard | 3 | 0 | 3 |
| Test Plans & Runner | 6 | 0 | 6 |
| Results | 3 | 3 | 6 |
| Test Data | 1 | 0 | 1 |
| Fleet | 17 | 5 | 22 |
| Settings | 1 | 0 | 1 |
| **Total** | **31** | **8** | **39** |
