# E2E Test Plan — Playwright Browser Tests

> 35 automated browser tests across 7 spec files covering all webapp pages.

## Table of Contents

- [Overview](#overview)
- [How to Run](#how-to-run)
- [Test Matrix](#test-matrix)
- [Spec Details](#spec-details)
- [CI Integration](#ci-integration)

---

## Overview

| Metric | Value |
|--------|-------|
| Framework | Playwright Test (TypeScript) |
| Total tests | 35 (+ 1 optional long-running runner test) |
| Spec files | 7 |
| Pages covered | Dashboard, Test Plans & Runner, Results, Test Data, Fleet, Settings, Navigation (cross-page) |
| Browser | Chromium (default) |
| Avg suite time | ~35s (excluding JMeter runner test) |

## How to Run

### Self-contained mode (starts its own server)

```bash
cd jmeter-working-dir/webapp/tests/e2e
npm install
npx playwright install chromium
npx playwright test
```

The `webServer` config in `playwright.config.ts` automatically starts uvicorn on port 9090.

### Against a live server

```bash
# With webapp already running on port 8080 with /perftest base path:
WEBAPP_BASE_PATH=/perftest npx playwright test --grep-invert "start test"
```

### Headed mode (watch tests run)

```bash
npx playwright test --headed
```

### Single spec file

```bash
npx playwright test tests/dashboard.spec.ts
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBAPP_PORT` | `9090` | Port for the auto-started server |
| `WEBAPP_BASE_PATH` | `""` (empty) | URL prefix (e.g., `/perftest`) |

---

## Test Matrix

### navigation.spec.ts (5 tests)

| # | Test | Expected Behavior |
|---|------|-------------------|
| 1 | All pages load without JS errors | Visit all 6 pages, no `pageerror` events fired |
| 2 | Sidebar links navigate to correct pages | Each sidebar nav item navigates to its URL |
| 3 | Sidebar collapse and expand | `#sidebarToggle` collapses, `#menuBtn` expands |
| 4 | Theme toggle switches dark and light | `data-theme` attribute changes on `<html>` |
| 5 | Mobile responsive: bottom nav visible | At 375x667 viewport, `#bottomNav` visible, sidebar not open |

### dashboard.spec.ts (5 tests)

| # | Test | Expected Behavior |
|---|------|-------------------|
| 6 | Stats cards load with values | `#jmxCount`, `#resultsCount`, `#modeLabel` have non-dash values |
| 7 | Run history table renders with columns | Table has Run, Date, Samples, Avg RT, Error %, Throughput columns |
| 8 | Alerts card displays | `#alertsRow` visible with `#alertCount` badge |
| 9 | Quick action links navigate correctly | "Run a Test" → /plans, "View Results" → /results |
| 10 | Last test run card shows stats | `#lastRun` card visible with stat labels |

### plans-runner.spec.ts (7+1 tests)

| # | Test | Expected Behavior |
|---|------|-------------------|
| 11 | Select plan loads parameters and command preview | Selecting Dummy-HTTP-Test.jmx shows threads/duration inputs + jmeter command |
| 12 | Changing parameter updates command preview | Filling threads=50 updates `#cmdPreview` |
| 13 | Save and apply preset | Save preset with threads=99, apply it, verify value restored, cleanup |
| 14 | Mode indicator shows Local or Distributed | `#modeIndicator` has matching text |
| 15 | Start and stop controls are correct in idle state | Start enabled, Stop disabled, status = Idle |
| 16 | Upload jmx file | Upload via buffer, verify in dropdown, cleanup |
| 17 | Test completion shows final stats | `#liveThroughput` attached, `#outputCard` visible |
| 18* | Start test changes UI to running state | *(Long-running, 120s timeout)* Runs JMeter test, verifies Running/Idle transitions |

*Test 18 requires JMeter installed and takes ~90s. Exclude with `--grep-invert "start test"`.

### results.spec.ts (5 tests)

| # | Test | Expected Behavior |
|---|------|-------------------|
| 19 | Results list loads with correct columns | Table has Folder, Date, Size, Report, JTL columns |
| 20 | Expand stats row shows performance metrics | Stats button expands row with Samples/Avg RT/Error |
| 21 | Search filter narrows results | Nonsense query shows "0 of" in `#resultCount` |
| 22 | Select 2 results enables compare button | Checking 2 `.result-check` enables `#compareBtn` |
| 23 | Regenerate modal opens with filter options | Regenerate button opens `#regenModal` with `#regen_filter_sub` |

### test-data.spec.ts (5 tests)

| # | Test | Expected Behavior |
|---|------|-------------------|
| 24 | CSV files list loads | File table visible with Name, Size, Actions columns |
| 25 | CSV builder form has required fields | `#buildFilename` and `#buildRowCount` visible after clicking Create |
| 26 | Generate CSV and verify it appears in list | Build CSV, verify in list, cleanup delete |
| 27 | Upload CSV file | Upload via buffer, verify in list, cleanup delete |
| 28 | Preview modal shows data | Preview button opens `#previewModal` with table content |

### fleet.spec.ts (4 tests)

| # | Test | Expected Behavior |
|---|------|-------------------|
| 29 | Slave list loads with configured slaves | `#slaveContainer` visible with slave rows |
| 30 | Add and remove slave | Add 10.0.0.99 via prompt, verify visible, delete, verify gone |
| 31 | Toggle slave enable/disable | Toggle checkbox changes state and restores |
| 32 | VM config section is visible | VM Configuration card visible |

### settings.spec.ts (4 tests)

| # | Test | Expected Behavior |
|---|------|-------------------|
| 33 | Tab switching works | All 5 tabs (General, Project, Report, Integrations, System) activate panels |
| 34 | Save settings persists values | Change max_log_lines to 2000, save, reload, verify, restore |
| 35 | Theme toggle changes appearance immediately | Dark/light theme changes `data-theme` attribute |
| 36 | System info tab shows versions | System tab shows `#systemInfoCards` with Python version |

---

## CI Integration

Add to GitHub Actions workflow:

```yaml
- name: Run E2E tests
  working-directory: jmeter-working-dir/webapp/tests/e2e
  run: |
    npm ci
    npx playwright install chromium --with-deps
    npx playwright test --grep-invert "start test"
```

The `--grep-invert "start test"` flag skips the JMeter runner test in CI (requires JMeter binary).

## Screenshots

- Failure screenshots: `test-results/artifacts/` (auto-captured)
- Reference screenshots: `screenshots/` (manually captured during runner test)
- HTML report: `test-results/html/` (generated after each run)
