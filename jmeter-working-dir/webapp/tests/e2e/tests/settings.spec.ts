import { test, expect } from '@playwright/test';

test.describe('Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('settings');
  });

  test('tab switching works', async ({ page }) => {
    const tabs = ['General', 'Project', 'Report', 'Integrations', 'System'];
    for (const tab of tabs) {
      await page.locator('.tab-btn', { hasText: tab }).click();
      // Corresponding panel should become active
      const panel = page.locator(`.tab-panel.active`);
      await expect(panel).toBeVisible();
    }
  });

  test('save settings persists values', async ({ page }) => {
    // Change max log lines
    const logLines = page.locator('#set_max_log_lines');
    await logLines.selectOption('2000');

    // Save
    const saveBtn = page.locator('.card-header .btn-primary', { hasText: 'Save' });
    await saveBtn.click();
    await page.waitForTimeout(500);

    // Reload and verify
    await page.reload();
    await expect(page.locator('#set_max_log_lines')).toHaveValue('2000');

    // Restore default
    await page.locator('#set_max_log_lines').selectOption('1000');
    await page.locator('.card-header .btn-primary', { hasText: 'Save' }).click();
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
    await expect(systemCards).toContainText(/Python/i, { timeout: 5000 });
  });
});
