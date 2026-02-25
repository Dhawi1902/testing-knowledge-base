# E2E Playwright Test Suite Design

**Date**: 2026-02-25
**Status**: Approved
**Scope**: JMeter Dashboard webapp (`jmeter-working-dir/webapp/`)

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Test depth | Functional flows (B) | 198 API tests cover endpoints; E2E covers UI flows working together |
| Server mode | Both (C) | Self-contained for CI, `--base-url` for live testing |
| Test runner | Playwright Test (Node.js) | Better reporting, screenshot diffing, official tooling |

## Directory Structure

```
webapp/tests/e2e/
├── package.json
├── playwright.config.ts
├── TEST_PLAN.md
├── screenshots/
├── test-results/
├── fixtures/
│   └── server.ts
├── tests/
│   ├── navigation.spec.ts
│   ├── dashboard.spec.ts
│   ├── plans-runner.spec.ts
│   ├── results.spec.ts
│   ├── test-data.spec.ts
│   ├── fleet.spec.ts
│   └── settings.spec.ts
└── .gitignore
```

## Test Coverage (~35 tests)

### navigation.spec.ts (5 tests)
- All 6 pages load without JS errors
- Sidebar navigation works (click each link, verify URL + heading)
- Sidebar collapse/expand toggle
- Theme toggle (dark/light) persists across pages
- Mobile responsive: sidebar hidden, bottom nav visible

### dashboard.spec.ts (5 tests)
- Dashboard loads with stats cards (test plans count, results count, slaves, mode)
- Run history table renders with correct columns
- Alerts card shows warnings (e.g., missing HTML report)
- Quick action links navigate to correct pages
- Last test run card displays stats

### plans-runner.spec.ts (8 tests)
- Select plan populates parameters and command preview
- Change parameter values updates command preview
- Save and apply preset
- Start test: status changes to Running, controls lock, timer starts
- Live stats update during test run
- Test completion: status returns to Idle, stats show final values
- Stop test mid-run
- Upload new .jmx file

### results.spec.ts (5 tests)
- Results list loads with correct columns
- Expand stats row shows performance metrics
- Search filter narrows results
- Select 2 results and compare (diff panel)
- Regenerate modal opens with filter options

### test-data.spec.ts (5 tests)
- CSV files list loads
- CSV builder: add columns, set types, preview
- Generate CSV and verify it appears in list
- Upload CSV file
- Delete CSV file with confirmation

### fleet.spec.ts (4 tests)
- Slave list loads with configured slaves
- Add new slave (IP entry)
- Toggle slave enable/disable
- VM config section expand and save

### settings.spec.ts (4 tests)
- Tab switching works (General, Project, Report, Integrations, System)
- Save settings persists values
- Theme toggle changes appearance immediately
- System info tab shows JMeter/Java/Python versions

## Server Fixture

Self-contained mode uses Playwright's `webServer` config to start uvicorn on a random port before tests and shut it down after. Live mode uses `--base-url` to skip server startup.

## Screenshot Strategy

- **On failure**: Playwright auto-captures (built-in)
- **Reference**: Captured during key test states for TEST_PLAN.md documentation
- **Location**: `tests/e2e/screenshots/` (gitignored except reference shots)

## Config

- Headless by default, `--headed` for debugging
- 1 retry for flaky WebSocket timing
- 30s timeout per test
- HTML reporter for CI
