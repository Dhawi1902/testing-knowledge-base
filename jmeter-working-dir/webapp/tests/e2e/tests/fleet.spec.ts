import { test, expect } from '@playwright/test';

test.describe('Fleet', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('fleet');
  });

  test('slave list loads with configured slaves', async ({ page }) => {
    const container = page.locator('#slaveContainer');
    await expect(container).toBeVisible();
    // Should show slave entries or empty state (wait for load)
    await page.waitForTimeout(1000);
    const entries = page.locator('.slave-entry');
    const emptyMsg = page.locator('#slaveContainer', { hasText: /No slave VMs configured/i });
    const hasEntries = await entries.count() > 0;
    const hasEmpty = await emptyMsg.isVisible().catch(() => false);
    expect(hasEntries || hasEmpty).toBeTruthy();
  });

  test('add and remove slave', async ({ page }) => {
    // Handle the prompt dialog for adding a slave
    page.once('dialog', async dialog => {
      expect(dialog.type()).toBe('prompt');
      await dialog.accept('10.0.0.99');
    });
    // Click add button
    await page.locator('button', { hasText: '+ Add' }).click();
    await page.waitForTimeout(1000);

    // Verify added
    await expect(page.locator('.slave-entry', { hasText: '10.0.0.99' }).or(
      page.locator('.vm-card', { hasText: '10.0.0.99' })
    )).toBeVisible();

    // Remove it - handle confirm dialog
    page.once('dialog', async dialog => {
      await dialog.accept();
    });
    const entry = page.locator('.slave-entry', { hasText: '10.0.0.99' }).or(
      page.locator('.vm-card', { hasText: '10.0.0.99' })
    );
    await entry.locator('.del-btn').click();
    await page.waitForTimeout(500);
  });

  test('toggle slave enable/disable', async ({ page }) => {
    await page.waitForTimeout(1000);
    const toggles = page.locator('.slave-entry .toggle input[type="checkbox"]');
    if (await toggles.count() > 0) {
      const firstToggle = toggles.first();
      const wasChecked = await firstToggle.isChecked();
      await firstToggle.click();
      await page.waitForTimeout(500);
      const nowChecked = await firstToggle.isChecked();
      expect(nowChecked).not.toBe(wasChecked);
      // Restore original state
      await firstToggle.click();
      await page.waitForTimeout(300);
    }
  });

  test('VM config section is visible', async ({ page }) => {
    // The VM configuration card should exist
    const vmConfig = page.locator('.card', { hasText: 'VM Configuration' });
    await expect(vmConfig).toBeVisible();
  });
});
