import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('');
  });

  test('stats cards load with values', async ({ page }) => {
    // Wait for stats API to populate
    await expect(page.locator('#jmxCount')).not.toHaveText('-', { timeout: 5000 });
    await expect(page.locator('#resultsCount')).not.toHaveText('-');
    await expect(page.locator('#modeLabel')).toHaveText(/Local|Distributed/);
  });

  test('run history table renders with columns', async ({ page }) => {
    const table = page.locator('#runHistory table');
    await expect(table).toBeVisible({ timeout: 5000 });
    for (const col of ['Run', 'Date', 'VUs', 'Samples', 'Avg RT', 'P95', 'Error %', 'Throughput']) {
      await expect(table.locator('th', { hasText: col })).toBeVisible();
    }
    // At least one row of data
    await expect(table.locator('tbody tr').first()).toBeVisible();
  });

  test('alerts card displays', async ({ page }) => {
    const alertsCard = page.locator('#alertsRow');
    await expect(alertsCard).toBeVisible();
    // Badge shows count
    await expect(page.locator('#alertCount')).toBeVisible();
  });

  test('quick action links navigate correctly', async ({ page }) => {
    await page.getByRole('link', { name: 'Run Test' }).click();
    await expect(page).toHaveURL(/\/plans$/);
    await page.goto('');

    await page.getByRole('link', { name: 'View Results' }).click();
    await expect(page).toHaveURL(/\/results$/);
  });

  test('last test run card shows stats', async ({ page }) => {
    const lastRun = page.locator('#lastRun');
    await expect(lastRun).toBeVisible();
    // Should contain stat cards if a test has been run before
    const statCards = lastRun.locator('.stat-card');
    const count = await statCards.count();
    if (count > 0) {
      for (const label of ['Peak VUs', 'Avg RT', 'P95', 'Errors', 'Throughput']) {
        await expect(lastRun.locator('.stat-label', { hasText: label })).toBeVisible();
      }
    }
  });
});
