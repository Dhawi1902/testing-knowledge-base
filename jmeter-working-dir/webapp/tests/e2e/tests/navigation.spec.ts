import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('all pages load without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    const pages = ['', 'plans', 'results', 'data', 'fleet', 'settings'];
    for (const path of pages) {
      await page.goto(path);
      await expect(page.locator('.page-title')).toBeVisible();
    }
    expect(errors).toEqual([]);
  });

  test('sidebar links navigate to correct pages', async ({ page }) => {
    await page.goto('');
    const links = [
      { text: 'Dashboard', url: /\/$/ },
      { text: 'Test Plans & Runner', url: /\/plans$/ },
      { text: 'Results', url: /\/results$/ },
      { text: 'Test Data', url: /\/data$/ },
      { text: 'Fleet', url: /\/fleet$/ },
      { text: 'Settings', url: /\/settings$/ },
    ];
    for (const link of links) {
      await page.locator('.sidebar-nav .nav-item', { hasText: link.text }).click();
      await expect(page).toHaveURL(link.url);
      await expect(page.locator('.page-title')).toBeVisible();
    }
  });

  test('sidebar collapse and expand', async ({ page }) => {
    await page.goto('');
    const sidebar = page.locator('#sidebar');

    // Sidebar starts expanded
    await expect(sidebar).not.toHaveClass(/collapsed/);

    // Click « button to collapse
    await page.locator('#sidebarToggle').click();
    await expect(sidebar).toHaveClass(/collapsed/);

    // Click ☰ menu button (now visible) to expand
    await page.locator('#menuBtn').click();
    await expect(sidebar).not.toHaveClass(/collapsed/);
  });

  test('theme toggle switches dark and light', async ({ page }) => {
    await page.goto('settings');
    const themeSelect = page.locator('#set_theme');

    await themeSelect.selectOption('dark');
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');

    await themeSelect.selectOption('light');
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  });

  test('mobile responsive: bottom nav visible at small viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('');
    await expect(page.locator('#bottomNav')).toBeVisible();
    // Sidebar is off-screen (translateX(-100%)) on mobile unless .open is added
    await expect(page.locator('#sidebar')).not.toHaveClass(/\bopen\b/);
  });
});
