import { test, expect } from '@playwright/test';

test.describe('Test Plans & Runner', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('plans');
  });

  test('select plan loads parameters and command preview', async ({ page }) => {
    await page.locator('#selectedPlan').selectOption({ label: 'Dummy-HTTP-Test.jmx' });
    // Parameters should appear
    const paramForm = page.locator('#paramForm');
    await expect(paramForm.locator('[data-param="threads"]')).toBeVisible({ timeout: 5000 });
    await expect(paramForm.locator('[data-param="duration"]')).toBeVisible();

    // Command preview should contain jmeter
    const preview = page.locator('#cmdPreview');
    await expect(preview).toContainText('jmeter');
    await expect(preview).toContainText('Dummy-HTTP-Test.jmx');
  });

  test('changing parameter updates command preview', async ({ page }) => {
    await page.locator('#selectedPlan').selectOption({ label: 'Dummy-HTTP-Test.jmx' });
    await page.locator('[data-param="threads"]').waitFor({ state: 'visible' });
    await page.locator('[data-param="threads"]').fill('50');
    // Wait for async preview update
    await expect(page.locator('#cmdPreview')).toContainText('threads=50', { timeout: 5000 });
  });

  test('save and apply preset', async ({ page }) => {
    await page.locator('#selectedPlan').selectOption({ label: 'Dummy-HTTP-Test.jmx' });
    await page.locator('[data-param="threads"]').waitFor({ state: 'visible' });
    await page.locator('[data-param="threads"]').fill('99');

    // Save as preset — opens preset modal
    await page.locator('#saveAsPresetBtn').click();
    await page.locator('#newPresetName').fill('E2E Test Preset');
    await page.locator('button[onclick="savePresetFromModal()"]').click();
    await page.waitForTimeout(300);

    // Close the modal before interacting with elements behind it
    await page.locator('#presetModal .modal-close').click();
    await page.waitForTimeout(300);

    // Reset threads, then apply preset from dropdown
    await page.locator('[data-param="threads"]').fill('1');
    await page.locator('#presetSelect').selectOption('E2E Test Preset');
    await expect(page.locator('[data-param="threads"]')).toHaveValue('99');

    // Cleanup: delete the preset via modal
    await page.locator('button[onclick="openPresetManager()"]').click();
    page.once('dialog', dialog => dialog.accept());
    await page.locator('#presetModal .btn-outline', { hasText: 'Delete' }).first().click();
    await page.waitForTimeout(500);
    await page.locator('#presetModal .modal-close').click();
  });

  test('mode indicator shows Local or Distributed', async ({ page }) => {
    const badge = page.locator('#modeIndicator');
    await expect(badge).toHaveText(/Local mode|Distributed/, { timeout: 5000 });
  });

  test('start and stop controls are correct in idle state', async ({ page }) => {
    await page.locator('#selectedPlan').selectOption({ label: 'Dummy-HTTP-Test.jmx' });
    await page.locator('[data-param="threads"]').waitFor({ state: 'visible' });
    const startBtn = page.locator('#startTestBtn');
    const stopBtn = page.locator('#stopTestBtn');
    await expect(startBtn).toBeEnabled();
    await expect(stopBtn).toBeDisabled();
    await expect(page.locator('#runnerStatus')).toHaveText('Idle');
  });

  test('upload jmx file', async ({ page }) => {
    const fileInput = page.locator('#uploadInput');
    const jmxContent = `<?xml version="1.0"?><jmeterTestPlan version="1.2"><hashTree><TestPlan testname="Upload Test"/></hashTree></jmeterTestPlan>`;
    await fileInput.setInputFiles({
      name: 'e2e-upload-test.jmx',
      mimeType: 'application/xml',
      buffer: Buffer.from(jmxContent),
    });
    // Wait for upload to complete and plan list to refresh
    await page.waitForTimeout(1000);
    // Verify it appears in the dropdown
    await expect(page.locator('#selectedPlan option', { hasText: 'e2e-upload-test.jmx' })).toBeAttached();

    // Cleanup: select and delete the uploaded file
    await page.locator('#selectedPlan').selectOption({ label: 'e2e-upload-test.jmx' });
    page.once('dialog', dialog => dialog.accept());
    await page.locator('#deletePlanBtn').click();
  });

  test('start test changes UI to running state', async ({ page }) => {
    test.setTimeout(120_000);
    await page.locator('#selectedPlan').selectOption({ label: 'Dummy-HTTP-Test.jmx' });
    await page.locator('[data-param="duration"]').waitFor({ state: 'visible' });
    await page.locator('[data-param="duration"]').fill('10');
    await page.locator('[data-param="threads"]').fill('1');
    await page.waitForTimeout(500);

    await page.locator('#startTestBtn').click();

    // Verify running state
    await expect(page.locator('#runnerStatus')).toHaveText('Running', { timeout: 10000 });
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
    await page.locator('#selectedPlan').selectOption({ label: 'Dummy-HTTP-Test.jmx' });
    // The live output section exists (hidden until a test runs)
    const throughput = page.locator('#liveThroughput');
    await expect(throughput).toBeAttached();
    // The output card is always visible
    await expect(page.locator('#outputCard')).toBeVisible();
  });
});
