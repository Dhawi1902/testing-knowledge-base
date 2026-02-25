# Webapp Walkthrough Findings

**Date**: 2026-02-25
**Tested on**: Windows 11, Webapp running at `http://127.0.0.1:8080/perftest/`
**Screenshots**: `jmeter-working-dir/webapp/tests/e2e/screenshots/review-*.png`

---

## Bugs

### BUG-1: Dashboard "Edit Config" quick action links to 404

- **Page**: Dashboard
- **Severity**: Medium
- **Steps**: Click "Edit Config" button in Quick Actions card
- **Expected**: Navigate to a config editing page
- **Actual**: Goes to `/perftest/config` which returns `{"detail":"Not Found"}`
- **Fix**: Change link target to `/perftest/settings` (Project tab) or `/perftest/fleet` (VM Configuration section)
- **Screenshot**: `review-01-dashboard.png`

### BUG-2: Runner page has no way to set/view the JTL filter pattern

- **Page**: Test Plans & Runner
- **Severity**: Medium
- **Steps**: Select a test plan, look at the "Filter labels" toggle at the bottom
- **Expected**: Ability to see and/or edit the filter regex pattern before starting a test
- **Actual**: Only a toggle (on/off) is shown. No input field, no indication of what pattern will be applied
- **Context**: The filter pattern CAN be set in two other places:
  - Settings > General > JTL Filter Defaults (has regex input + help text)
  - Results > Regenerate modal (has regex input + label checkboxes + presets)
- **Fix**: Add an expandable section or inline input next to the toggle showing the current pattern from settings, with a link to Settings if the user wants to change it
- **Screenshot**: `review-03-plans-configured.png`

### BUG-3: Settings System tab shows JMeter version as "N/A"

- **Page**: Settings > System tab
- **Severity**: Low
- **Steps**: Go to Settings, click System tab
- **Expected**: Shows JMeter version (e.g. "Apache JMeter 5.6.3")
- **Actual**: Shows "N/A" even though JMeter path is correctly configured in Project tab (`C:\Users\user\Documents\apache-jmeter-5.6.3\...\jmeter.bat`)
- **Root cause**: Detection logic likely runs `jmeter --version` or parses output incorrectly on Windows
- **Screenshot**: (visible in System tab)

---

## UX Issues

### UX-1: Command Preview shows full absolute paths

- **Page**: Test Plans & Runner
- **Impact**: Low
- **Description**: When a plan is selected, the Command Preview box shows the full Windows absolute path for every argument (JMeter binary, test plan, results dir, report.properties). The command wraps across 4+ lines and is hard to read.
- **Suggestion**: Truncate paths or show relative paths with a "Copy full command" button
- **Screenshot**: `review-03-plans-configured.png`

### UX-2: Test Data page has no direct Upload CSV button

- **Page**: Test Data
- **Impact**: Low
- **Description**: The page has a CSV Files table (with Download/Delete) and a CSV Builder (with templates). But there is no "Upload" button to import an existing CSV file. The Test Plans page has an Upload button for .jmx files, but Test Data does not have an equivalent.
- **Suggestion**: Add an Upload button in the CSV Files card header, next to Refresh
- **Screenshot**: `review-05-test-data.png`

### UX-3: Console DOM warning on Fleet page

- **Page**: Fleet
- **Impact**: Cosmetic
- **Description**: Browser console logs: "Password field is not contained in a form". The password input in VM Configuration's SSH Defaults section is not wrapped in a `<form>` element.
- **Suggestion**: Wrap the VM Configuration inputs in a `<form>` tag or add `autocomplete="off"` to suppress the warning

---

## What Works Well

- **Dashboard**: Stats cards, run history table with trend arrows (up/down), alerts card, last test run metrics, disk usage — all load correctly and look polished
- **Results**: Stats expansion with per-label breakdown table, search filter, Regenerate modal with label checkboxes and regex presets — excellent UX
- **Fleet**: Slave list with badges (2 VMs / 0 Enabled / 2 Disabled), enable/disable toggles, VM Configuration with SSH defaults and JMeter scripts
- **Settings**: All 5 tabs functional (General, Project, Report, Integrations, System). Report tab graph toggles with "Disable All Heavy" shortcut and explanation of size impact
- **Navigation**: Sidebar collapse/expand, theme toggle, all 6 pages load without JS errors
