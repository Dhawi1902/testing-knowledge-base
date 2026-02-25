import { test, expect } from '@playwright/test';

test.describe('Results', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('results');
  });

  test('results list loads with correct columns', async ({ page }) => {
    const table = page.locator('table');
    await expect(table).toBeVisible();
    for (const col of ['Folder', 'Date', 'Size', 'Report', 'JTL']) {
      await expect(table.locator('th', { hasText: col })).toBeVisible();
    }
    // Should have at least one result row (loaded async)
    await expect(page.locator('#resultsList tr').first()).toBeVisible({ timeout: 5000 });
  });

  test('expand stats row shows performance metrics', async ({ page }) => {
    // Wait for results to load
    await page.locator('#resultsList tr td').first().waitFor({ timeout: 5000 });
    // Click the Stats button on the first result
    const statsBtn = page.locator('#resultsList button', { hasText: 'Stats' }).first();
    if (await statsBtn.isVisible()) {
      await statsBtn.click();
      // Stats row should expand with metrics
      const statsRow = page.locator('.stats-row:not(.hidden)').first();
      await expect(statsRow).toBeVisible({ timeout: 5000 });
      await expect(statsRow).toContainText(/Samples|Avg RT|Error/i);
    }
  });

  test('search filter narrows results', async ({ page }) => {
    const searchInput = page.locator('#resultSearch');
    await expect(searchInput).toBeVisible();
    // Wait for results to load
    await page.locator('#resultsList tr td').first().waitFor({ timeout: 5000 });
    await searchInput.fill('nonexistent_folder_xyz');
    await page.waitForTimeout(500);
    // Result count should show "0 of" when no results match
    await expect(page.locator('#resultCount')).toContainText('0 of', { timeout: 5000 });
  });

  test('select 2 results enables compare button', async ({ page }) => {
    await page.locator('#resultsList tr td').first().waitFor({ timeout: 5000 });
    const checkboxes = page.locator('.result-check');
    const count = await checkboxes.count();
    if (count >= 2) {
      await checkboxes.nth(0).check();
      await checkboxes.nth(1).check();
      await expect(page.locator('#compareBtn')).toBeEnabled();
    }
  });

  test('regenerate modal opens with filter options', async ({ page }) => {
    await page.locator('#resultsList tr td').first().waitFor({ timeout: 5000 });
    // Find a result row with regenerate button
    const regenBtn = page.locator('#resultsList button', { hasText: 'Regenerate' }).first();
    if (await regenBtn.isVisible()) {
      await regenBtn.click();
      const modal = page.locator('#regenModal');
      await expect(modal).toHaveClass(/active/, { timeout: 3000 });
      await expect(modal.locator('#regen_filter_sub')).toBeVisible();
      // Close modal
      await modal.locator('.btn-close').click();
    }
  });
});
