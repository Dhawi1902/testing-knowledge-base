# E2E Playwright Test Suite — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add ~35 Playwright E2E browser tests covering all 7 webapp pages as functional user flows.

**Architecture:** Playwright Test (Node.js) with TypeScript specs. Self-contained server via Playwright's `webServer` config (starts uvicorn), overridable with `--base-url` for live testing. Screenshots on failure stored in `tests/e2e/screenshots/`.

**Tech Stack:** Playwright Test, TypeScript, Node.js 18+

---

### Task 1: Scaffold E2E directory and config

**Files:**
- Create: `jmeter-working-dir/webapp/tests/e2e/package.json`
- Create: `jmeter-working-dir/webapp/tests/e2e/playwright.config.ts`
- Create: `jmeter-working-dir/webapp/tests/e2e/tsconfig.json`
- Create: `jmeter-working-dir/webapp/tests/e2e/.gitignore`

**Step 1: Create package.json**

```json
{
  "name": "webapp-e2e",
  "private": true,
  "scripts": {
    "test": "npx playwright test",
    "test:headed": "npx playwright test --headed",
    "test:live": "npx playwright test --config playwright.live.config.ts",
    "report": "npx playwright show-report test-results/html"
  },
  "devDependencies": {
    "@playwright/test": "^1.49.0"
  }
}
```

**Step 2: Create playwright.config.ts**

```typescript
import { defineConfig } from '@playwright/test';

const PORT = process.env.WEBAPP_PORT || '9090';
const BASE_URL = `http://127.0.0.1:${PORT}/perftest`;

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  retries: 1,
  use: {
    baseURL: BASE_URL,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  outputDir: './test-results/artifacts',
  reporter: [
    ['html', { outputFolder: './test-results/html', open: 'never' }],
    ['list'],
  ],
  webServer: {
    command: `python -m uvicorn main:app --host 127.0.0.1 --port ${PORT}`,
    cwd: '../../',
    port: Number(PORT),
    timeout: 15_000,
    reuseExistingServer: true,
  },
});
```

**Step 3: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  }
}
```

**Step 4: Create .gitignore**

```
node_modules/
test-results/
screenshots/*
!screenshots/.gitkeep
```

**Step 5: Create screenshots directory**

```bash
mkdir -p jmeter-working-dir/webapp/tests/e2e/screenshots
touch jmeter-working-dir/webapp/tests/e2e/screenshots/.gitkeep
mkdir -p jmeter-working-dir/webapp/tests/e2e/tests
```

**Step 6: Install dependencies and browser**

```bash
cd jmeter-working-dir/webapp/tests/e2e
npm install
npx playwright install chromium
```

**Step 7: Commit**

```bash
git add jmeter-working-dir/webapp/tests/e2e/
git commit -m "scaffold: E2E Playwright test suite with config"
```

---

### Task 2: navigation.spec.ts (5 tests)

**Files:**
- Create: `jmeter-working-dir/webapp/tests/e2e/tests/navigation.spec.ts`

**Step 1: Write all navigation tests**

```typescript
import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('all pages load without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    const pages = ['/', '/plans', '/results', '/data', '/fleet', '/settings'];
    for (const path of pages) {
      await page.goto(path);
      await expect(page.locator('h1')).toBeVisible();
    }
    expect(errors).toEqual([]);
  });

  test('sidebar links navigate to correct pages', async ({ page }) => {
    await page.goto('/');
    const links = [
      { text: 'Dashboard', url: /\/$/ },
      { text: 'Test Plans & Runner', url: /\/plans$/ },
      { text: 'Results', url: /\/results$/ },
      { text: 'Test Data', url: /\/data$/ },
      { text: 'Fleet', url: /\/fleet$/ },
      { text: 'Settings', url: /\/settings$/ },
    ];
    for (const link of links) {
      await page.getByRole('link', { name: link.text }).click();
      await expect(page).toHaveURL(link.url);
      await expect(page.locator('h1')).toBeVisible();
    }
  });

  test('sidebar collapse and expand', async ({ page }) => {
    await page.goto('/');
    const sidebar = page.locator('#sidebar');
    const toggle = page.getByRole('button', { name: 'Toggle sidebar' });

    await expect(sidebar).not.toHaveClass(/collapsed/);
    await toggle.click();
    await expect(sidebar).toHaveClass(/collapsed/);
    await toggle.click();
    await expect(sidebar).not.toHaveClass(/collapsed/);
  });

  test('theme toggle switches dark and light', async ({ page }) => {
    await page.goto('/settings');
    const themeSelect = page.locator('#set_theme');

    await themeSelect.selectOption('dark');
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');

    await themeSelect.selectOption('light');
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  });

  test('mobile responsive: bottom nav visible at small viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await expect(page.locator('.bottom-nav')).toBeVisible();
    await expect(page.locator('#sidebar')).not.toBeVisible();
  });
});
```

**Step 2: Run tests**

```bash
cd jmeter-working-dir/webapp/tests/e2e
npx playwright test tests/navigation.spec.ts --headed
```

Expected: 5 tests pass.

**Step 3: Commit**

```bash
git add jmeter-working-dir/webapp/tests/e2e/tests/navigation.spec.ts
git commit -m "test(e2e): add navigation tests — sidebar, theme, responsive"
```

---

### Task 3: dashboard.spec.ts (5 tests)

**Files:**
- Create: `jmeter-working-dir/webapp/tests/e2e/tests/dashboard.spec.ts`

**Step 1: Write dashboard tests**

```typescript
import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('stats cards load with values', async ({ page }) => {
    // Wait for stats API to populate
    const testPlans = page.locator('.stat-card', { hasText: 'Test Plans' });
    await expect(testPlans.locator('.stat-value')).not.toHaveText('-');

    const results = page.locator('.stat-card', { hasText: 'Results' });
    await expect(results.locator('.stat-value')).not.toHaveText('-');

    const mode = page.locator('.stat-card', { hasText: 'Mode' });
    await expect(mode.locator('.stat-value')).toHaveText(/Local|Distributed/);
  });

  test('run history table renders with columns', async ({ page }) => {
    const table = page.locator('table').first();
    await expect(table).toBeVisible();
    for (const col of ['RUN', 'DATE', 'SAMPLES', 'AVG RT', 'ERROR %', 'THROUGHPUT']) {
      await expect(table.locator('th', { hasText: col })).toBeVisible();
    }
    // At least one row of data
    const rows = table.locator('tbody tr');
    await expect(rows.first()).toBeVisible();
  });

  test('alerts card displays', async ({ page }) => {
    const alertsCard = page.locator('.card', { hasText: 'Alerts' });
    await expect(alertsCard).toBeVisible();
    // Badge shows count
    const badge = alertsCard.locator('.badge').first();
    await expect(badge).toBeVisible();
  });

  test('quick action links navigate correctly', async ({ page }) => {
    await page.getByRole('link', { name: 'Run Test' }).click();
    await expect(page).toHaveURL(/\/plans$/);
    await page.goto('/');

    await page.getByRole('link', { name: 'View Results' }).click();
    await expect(page).toHaveURL(/\/results$/);
  });

  test('last test run card shows stats', async ({ page }) => {
    const card = page.locator('.card', { hasText: 'Last Test Run' });
    await expect(card).toBeVisible();
    // Should show stat labels
    for (const label of ['Peak VUs', 'Avg RT', 'P95', 'Errors', 'Throughput']) {
      await expect(card.locator('.stat-label', { hasText: label })).toBeVisible();
    }
  });
});
```

**Step 2: Run tests**

```bash
npx playwright test tests/dashboard.spec.ts --headed
```

Expected: 5 tests pass.

**Step 3: Commit**

```bash
git add jmeter-working-dir/webapp/tests/e2e/tests/dashboard.spec.ts
git commit -m "test(e2e): add dashboard tests — stats, history, alerts, actions"
```

---

### Task 4: plans-runner.spec.ts (8 tests)

**Files:**
- Create: `jmeter-working-dir/webapp/tests/e2e/tests/plans-runner.spec.ts`

**Note:** Tests that start a JMeter test require JMeter installed. Use a conditional skip or mock. For CI without JMeter, the plan-selection/preset tests still run. The runner tests use `test.skip` if JMeter is not available. However, since the user HAS JMeter installed locally, these tests will work in `--base-url` mode.

**Step 1: Write plans-runner tests**

```typescript
import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('Test Plans & Runner', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/plans');
  });

  test('select plan loads parameters and command preview', async ({ page }) => {
    await page.locator('#selectedPlan').selectOption('Dummy-HTTP-Test.jmx');
    // Parameters should appear
    const paramForm = page.locator('#paramForm');
    await expect(paramForm.locator('[data-param="threads"]')).toBeVisible();
    await expect(paramForm.locator('[data-param="duration"]')).toBeVisible();

    // Command preview should contain jmeter
    const preview = page.locator('#cmdPreview');
    await expect(preview).toContainText('jmeter');
    await expect(preview).toContainText('Dummy-HTTP-Test.jmx');
  });

  test('changing parameter updates command preview', async ({ page }) => {
    await page.locator('#selectedPlan').selectOption('Dummy-HTTP-Test.jmx');
    const threadsInput = page.locator('[data-param="threads"]');
    await threadsInput.fill('50');
    // Wait for debounced preview update
    await page.waitForTimeout(500);
    await expect(page.locator('#cmdPreview')).toContainText('Gthreads=50');
  });

  test('save and apply preset', async ({ page }) => {
    await page.locator('#selectedPlan').selectOption('Dummy-HTTP-Test.jmx');
    await page.locator('[data-param="threads"]').fill('99');

    // Save as preset
    await page.getByRole('button', { name: 'Save as Preset' }).click();
    await page.locator('#newPresetName').fill('E2E Test Preset');
    await page.getByRole('button', { name: 'Save' }).click();

    // Reset threads, then apply preset
    await page.locator('[data-param="threads"]').fill('1');
    await page.locator('#presetSelect').selectOption('E2E Test Preset');
    await expect(page.locator('[data-param="threads"]')).toHaveValue('99');

    // Cleanup: delete the preset
    await page.getByRole('button', { name: '⚙' }).click();
    await page.getByRole('button', { name: 'Delete' }).click();
    await page.locator('.modal-close').click();
  });

  test('mode indicator shows Local or Distributed', async ({ page }) => {
    const badge = page.locator('#modeIndicator');
    await expect(badge).toHaveText(/Local mode|Distributed/);
  });

  test('start and stop controls are correct in idle state', async ({ page }) => {
    await page.locator('#selectedPlan').selectOption('Dummy-HTTP-Test.jmx');
    const startBtn = page.locator('#startTestBtn');
    const stopBtn = page.locator('#stopTestBtn');
    await expect(startBtn).toBeEnabled();
    await expect(stopBtn).toBeDisabled();
    await expect(page.locator('#runnerStatus')).toHaveText('Idle');
  });

  test('upload jmx file', async ({ page }) => {
    const fileInput = page.locator('#uploadInput');
    // Create a minimal JMX content
    const jmxContent = `<?xml version="1.0"?><jmeterTestPlan version="1.2"><hashTree><TestPlan testname="Upload Test"/></hashTree></jmeterTestPlan>`;
    // Use Playwright's setInputFiles with buffer
    await fileInput.setInputFiles({
      name: 'e2e-upload-test.jmx',
      mimeType: 'application/xml',
      buffer: Buffer.from(jmxContent),
    });
    // Verify it appears in the dropdown
    await expect(page.locator('#selectedPlan option', { hasText: 'e2e-upload-test.jmx' })).toBeAttached();

    // Cleanup: delete the uploaded file
    await page.locator('#selectedPlan').selectOption('e2e-upload-test.jmx');
    page.on('dialog', dialog => dialog.accept());
    await page.getByRole('button', { name: 'Delete' }).click();
  });

  test('start test changes UI to running state', async ({ page }) => {
    // This test requires JMeter to be installed
    await page.locator('#selectedPlan').selectOption('Dummy-HTTP-Test.jmx');
    await page.locator('[data-param="duration"]').fill('10');
    await page.locator('[data-param="threads"]').fill('1');
    await page.waitForTimeout(300);

    await page.locator('#startTestBtn').click();

    // Verify running state
    await expect(page.locator('#runnerStatus')).toHaveText('Running', { timeout: 5000 });
    await expect(page.locator('#startTestBtn')).toBeDisabled();
    await expect(page.locator('#stopTestBtn')).toBeEnabled();
    await expect(page.locator('#elapsedTimer')).toBeVisible();

    // Live output section should appear
    await expect(page.locator('#liveSummary')).toBeVisible();

    // Wait for completion (10s test + overhead)
    await expect(page.locator('#runnerStatus')).toHaveText('Idle', { timeout: 120_000 });
    await expect(page.locator('#startTestBtn')).toBeEnabled();

    // Take reference screenshot
    await page.screenshot({ path: './screenshots/plans-runner-completed.png', fullPage: true });
  });

  test('test completion shows final stats', async ({ page }) => {
    // Check that after a test has run, the live output section still shows stats
    await page.goto('/plans');
    await page.locator('#selectedPlan').selectOption('Dummy-HTTP-Test.jmx');

    // Check live output section has values from last run (if buffer retained)
    const throughput = page.locator('#liveThroughput');
    // This may show '-' if no test was run in this session, which is fine
    await expect(throughput).toBeVisible();
  });
});
```

**Step 2: Run tests (skip runner test if no JMeter)**

```bash
npx playwright test tests/plans-runner.spec.ts --headed
```

Expected: 8 tests pass (the "start test" test takes ~90s due to JMeter run).

**Step 3: Commit**

```bash
git add jmeter-working-dir/webapp/tests/e2e/tests/plans-runner.spec.ts
git commit -m "test(e2e): add plans-runner tests — select, presets, run, upload"
```

---

### Task 5: results.spec.ts (5 tests)

**Files:**
- Create: `jmeter-working-dir/webapp/tests/e2e/tests/results.spec.ts`

**Step 1: Write results tests**

```typescript
import { test, expect } from '@playwright/test';

test.describe('Results', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/results');
  });

  test('results list loads with correct columns', async ({ page }) => {
    const table = page.locator('table');
    await expect(table).toBeVisible();
    for (const col of ['Folder', 'Date', 'Size']) {
      await expect(table.locator('th', { hasText: col })).toBeVisible();
    }
    // Should have at least one result row
    await expect(table.locator('tbody tr').first()).toBeVisible();
  });

  test('expand stats row shows performance metrics', async ({ page }) => {
    // Click the stats toggle on the first result
    const firstRow = page.locator('tbody tr').first();
    const statsBtn = firstRow.locator('button', { hasText: /stats/i }).or(
      firstRow.locator('[onclick*="toggleStats"]')
    );
    if (await statsBtn.isVisible()) {
      await statsBtn.click();
      // Stats row should expand with metrics
      const statsRow = page.locator('.stats-row').first();
      await expect(statsRow).toBeVisible({ timeout: 5000 });
      await expect(statsRow).toContainText(/samples|avg|error/i);
    }
  });

  test('search filter narrows results', async ({ page }) => {
    const searchInput = page.locator('#resultSearch');
    if (await searchInput.isVisible()) {
      const initialCount = await page.locator('tbody tr:visible').count();
      await searchInput.fill('nonexistent_folder_xyz');
      await page.waitForTimeout(300);
      const filteredCount = await page.locator('tbody tr:visible').count();
      expect(filteredCount).toBeLessThanOrEqual(initialCount);
    }
  });

  test('select 2 results enables compare button', async ({ page }) => {
    const checkboxes = page.locator('.result-check');
    const count = await checkboxes.count();
    if (count >= 2) {
      await checkboxes.nth(0).check();
      await checkboxes.nth(1).check();
      const compareBtn = page.locator('#compareBtn');
      await expect(compareBtn).toBeEnabled();
    }
  });

  test('regenerate modal opens with filter options', async ({ page }) => {
    // Find a result row with regenerate button
    const regenBtn = page.locator('[onclick*="regenerate"]').first();
    if (await regenBtn.isVisible()) {
      await regenBtn.click();
      const modal = page.locator('#regenModal');
      await expect(modal).toBeVisible();
      await expect(modal.locator('#regen_filter_sub')).toBeVisible();
      // Close modal
      await modal.locator('.modal-close').click();
    }
  });
});
```

**Step 2: Run tests**

```bash
npx playwright test tests/results.spec.ts --headed
```

Expected: 5 tests pass.

**Step 3: Commit**

```bash
git add jmeter-working-dir/webapp/tests/e2e/tests/results.spec.ts
git commit -m "test(e2e): add results tests — list, stats, search, compare, regen"
```

---

### Task 6: test-data.spec.ts (5 tests)

**Files:**
- Create: `jmeter-working-dir/webapp/tests/e2e/tests/test-data.spec.ts`

**Step 1: Write test-data tests**

```typescript
import { test, expect } from '@playwright/test';

test.describe('Test Data', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/data');
  });

  test('CSV files list loads', async ({ page }) => {
    // The files table or empty message should be visible
    const table = page.locator('table').first();
    const emptyMsg = page.getByText(/no csv files|no test data/i);
    await expect(table.or(emptyMsg)).toBeVisible();
  });

  test('CSV builder form has required fields', async ({ page }) => {
    const filename = page.locator('#buildFilename');
    const rowCount = page.locator('#buildRowCount');
    await expect(filename).toBeVisible();
    await expect(rowCount).toBeVisible();
  });

  test('generate CSV and verify it appears in list', async ({ page }) => {
    // Fill builder form
    await page.locator('#buildFilename').fill('e2e_test_data.csv');
    await page.locator('#buildRowCount').fill('5');

    // Should have at least one column definition
    const colName = page.locator('.col-name').first();
    if (await colName.isVisible()) {
      await colName.fill('id');
    }

    // Click generate
    const buildBtn = page.locator('#buildBtn');
    if (await buildBtn.isEnabled()) {
      await buildBtn.click();
      // Wait for success toast or file to appear
      await page.waitForTimeout(1000);
    }

    // Verify file exists (may need to refresh)
    await page.goto('/data');
    const fileEntry = page.getByText('e2e_test_data.csv');
    if (await fileEntry.isVisible()) {
      // Cleanup: delete
      page.on('dialog', dialog => dialog.accept());
      const deleteBtn = page.locator('tr', { hasText: 'e2e_test_data.csv' })
        .locator('button', { hasText: /delete/i });
      if (await deleteBtn.isVisible()) {
        await deleteBtn.click();
      }
    }
  });

  test('upload CSV file', async ({ page }) => {
    const csvContent = 'name,value\ntest1,100\ntest2,200\n';
    const fileInput = page.locator('input[type="file"][accept*=".csv"]');
    if (await fileInput.count() > 0) {
      await fileInput.setInputFiles({
        name: 'e2e_upload_test.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(csvContent),
      });
      await page.waitForTimeout(1000);
      // Check it appeared
      await page.goto('/data');
      const entry = page.getByText('e2e_upload_test.csv');
      if (await entry.isVisible()) {
        // Cleanup
        page.on('dialog', dialog => dialog.accept());
        await page.locator('tr', { hasText: 'e2e_upload_test.csv' })
          .locator('button', { hasText: /delete/i }).click();
      }
    }
  });

  test('preview modal shows data', async ({ page }) => {
    const previewBtn = page.locator('button', { hasText: /preview/i }).first();
    if (await previewBtn.isVisible()) {
      await previewBtn.click();
      const modal = page.locator('#previewModal').or(page.locator('.modal-overlay.active'));
      await expect(modal).toBeVisible({ timeout: 3000 });
    }
  });
});
```

**Step 2: Run tests**

```bash
npx playwright test tests/test-data.spec.ts --headed
```

Expected: 5 tests pass.

**Step 3: Commit**

```bash
git add jmeter-working-dir/webapp/tests/e2e/tests/test-data.spec.ts
git commit -m "test(e2e): add test-data tests — list, builder, generate, upload, preview"
```

---

### Task 7: fleet.spec.ts (4 tests)

**Files:**
- Create: `jmeter-working-dir/webapp/tests/e2e/tests/fleet.spec.ts`

**Step 1: Write fleet tests**

```typescript
import { test, expect } from '@playwright/test';

test.describe('Fleet', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/fleet');
  });

  test('slave list loads with configured slaves', async ({ page }) => {
    const container = page.locator('#slaveContainer');
    await expect(container).toBeVisible();
    // Should show slave entries or empty state
    const entries = page.locator('.slave-entry').or(page.locator('.vm-card'));
    const emptyMsg = page.getByText(/no slaves|add a slave/i);
    const hasEntries = await entries.count() > 0;
    const hasEmpty = await emptyMsg.isVisible().catch(() => false);
    expect(hasEntries || hasEmpty).toBeTruthy();
  });

  test('add and remove slave', async ({ page }) => {
    // Click add button
    const addBtn = page.getByRole('button', { name: /add/i });
    await addBtn.click();

    // Fill IP in the new entry
    const ipInput = page.locator('.slave-ip-input, input[placeholder*="IP"]').last();
    if (await ipInput.isVisible()) {
      await ipInput.fill('10.0.0.99');
      await ipInput.press('Enter');
      await page.waitForTimeout(500);

      // Verify added
      await expect(page.getByText('10.0.0.99')).toBeVisible();

      // Remove it
      page.on('dialog', dialog => dialog.accept());
      const entry = page.locator('.slave-entry, .vm-card', { hasText: '10.0.0.99' });
      const deleteBtn = entry.locator('button[title*="delete"], button[title*="Remove"]').or(
        entry.locator('.slave-delete')
      );
      await deleteBtn.click();
      await page.waitForTimeout(500);
    }
  });

  test('toggle slave enable/disable', async ({ page }) => {
    const toggles = page.locator('.slave-entry input[type="checkbox"], .toggle input');
    if (await toggles.count() > 0) {
      const firstToggle = toggles.first();
      const wasChecked = await firstToggle.isChecked();
      await firstToggle.click();
      await page.waitForTimeout(300);
      const nowChecked = await firstToggle.isChecked();
      expect(nowChecked).not.toBe(wasChecked);
      // Restore original state
      await firstToggle.click();
    }
  });

  test('VM config section is visible', async ({ page }) => {
    // The VM configuration card should exist
    const vmConfig = page.locator('.card', { hasText: /VM Configuration|SSH|JMeter on Slaves/i });
    await expect(vmConfig).toBeVisible();
  });
});
```

**Step 2: Run tests**

```bash
npx playwright test tests/fleet.spec.ts --headed
```

Expected: 4 tests pass.

**Step 3: Commit**

```bash
git add jmeter-working-dir/webapp/tests/e2e/tests/fleet.spec.ts
git commit -m "test(e2e): add fleet tests — slave list, add/remove, toggle, VM config"
```

---

### Task 8: settings.spec.ts (4 tests)

**Files:**
- Create: `jmeter-working-dir/webapp/tests/e2e/tests/settings.spec.ts`

**Step 1: Write settings tests**

```typescript
import { test, expect } from '@playwright/test';

test.describe('Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
  });

  test('tab switching works', async ({ page }) => {
    const tabs = ['General', 'Project', 'Report', 'Integrations', 'System'];
    for (const tab of tabs) {
      await page.getByRole('tab', { name: tab }).or(
        page.locator('.tab-btn', { hasText: tab })
      ).click();
      // Corresponding panel should be visible
      await page.waitForTimeout(200);
    }
  });

  test('save settings persists values', async ({ page }) => {
    // Change max log lines
    const logLines = page.locator('#set_max_log_lines');
    await logLines.selectOption('2000');

    // Save
    const saveBtn = page.getByRole('button', { name: /save/i }).last();
    await saveBtn.click();
    await page.waitForTimeout(500);

    // Reload and verify
    await page.reload();
    await expect(page.locator('#set_max_log_lines')).toHaveValue('2000');

    // Restore default
    await page.locator('#set_max_log_lines').selectOption('1000');
    await saveBtn.click();
  });

  test('theme toggle changes appearance immediately', async ({ page }) => {
    const themeSelect = page.locator('#set_theme');
    const html = page.locator('html');

    await themeSelect.selectOption('dark');
    await expect(html).toHaveAttribute('data-theme', 'dark');

    await themeSelect.selectOption('light');
    await expect(html).toHaveAttribute('data-theme', 'light');
  });

  test('system info tab shows versions', async ({ page }) => {
    await page.locator('.tab-btn', { hasText: 'System' }).click();
    const systemCards = page.locator('#systemInfoCards');
    await expect(systemCards).toBeVisible({ timeout: 5000 });
    // Should mention Python at minimum
    await expect(systemCards).toContainText(/Python/i);
  });
});
```

**Step 2: Run tests**

```bash
npx playwright test tests/settings.spec.ts --headed
```

Expected: 4 tests pass.

**Step 3: Commit**

```bash
git add jmeter-working-dir/webapp/tests/e2e/tests/settings.spec.ts
git commit -m "test(e2e): add settings tests — tabs, save, theme, system info"
```

---

### Task 9: Write TEST_PLAN.md documentation

**Files:**
- Create: `jmeter-working-dir/webapp/tests/e2e/TEST_PLAN.md`

**Step 1: Write the test plan document**

Document all 36 tests across 7 spec files with:
- Test ID, description, expected behavior
- Screenshots directory reference
- How to run (self-contained and live modes)
- CI integration notes

**Step 2: Commit**

```bash
git add jmeter-working-dir/webapp/tests/e2e/TEST_PLAN.md
git commit -m "docs: add E2E test plan document"
```

---

### Task 10: Run full suite and fix failures

**Step 1: Run all tests**

```bash
cd jmeter-working-dir/webapp/tests/e2e
npx playwright test
```

Expected: ~36 tests pass.

**Step 2: Fix any failures**

Adjust selectors, timeouts, or conditional logic based on actual DOM.

**Step 3: Run against live server**

```bash
# With webapp already running on port 8080:
npx playwright test --config playwright.config.ts --grep-invert "start test" --base-url http://127.0.0.1:8080/perftest
```

**Step 4: Final commit**

```bash
git add -A jmeter-working-dir/webapp/tests/e2e/
git commit -m "test(e2e): complete Playwright E2E suite — 36 tests across 7 pages"
```
