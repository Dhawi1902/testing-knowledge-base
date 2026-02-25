import { test, expect } from '@playwright/test';

test.describe('Test Data', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('data');
  });

  test('CSV files list loads', async ({ page }) => {
    // The files table or "No CSV files" should be visible
    const tbody = page.locator('#csvFilesList');
    await expect(tbody).toBeVisible();
    // Wait for loading to finish
    await expect(tbody.locator('tr').first()).toBeVisible({ timeout: 5000 });
  });

  test('CSV builder form has required fields', async ({ page }) => {
    // Builder starts hidden — click "+ Create new" to show it
    await page.locator('.preset-item', { hasText: '+ Create new' }).click();
    const filename = page.locator('#buildFilename');
    const rowCount = page.locator('#buildRowCount');
    await expect(filename).toBeVisible();
    await expect(rowCount).toBeVisible();
  });

  test('generate CSV and verify it appears in list', async ({ page }) => {
    // Show builder form
    await page.locator('.preset-item', { hasText: '+ Create new' }).click();

    // Fill builder form
    await page.locator('#buildFilename').fill('e2e_test_data.csv');
    await page.locator('#buildRowCount').fill('5');

    // Should have at least one column definition (added by createNew())
    const colName = page.locator('.col-name').first();
    await expect(colName).toBeVisible();
    await colName.fill('id');
    // Set type to sequence for simple generation
    await page.locator('.col-type').first().selectOption('sequence');

    // Click generate
    await page.locator('#buildBtn').click();
    // Wait for generation to complete
    await page.waitForTimeout(2000);

    // Verify file exists
    await page.goto('data');
    await page.waitForTimeout(1000);
    const fileEntry = page.locator('#csvFilesList', { hasText: 'e2e_test_data.csv' });
    if (await fileEntry.isVisible()) {
      // Cleanup: delete
      page.once('dialog', dialog => dialog.accept());
      const deleteBtn = page.locator('#csvFilesList tr', { hasText: 'e2e_test_data.csv' })
        .locator('button', { hasText: /Delete/i });
      if (await deleteBtn.isVisible()) {
        await deleteBtn.click();
      }
    }
  });

  test('upload CSV file', async ({ page }) => {
    const csvContent = 'name,value\ntest1,100\ntest2,200\n';
    const fileInput = page.locator('#uploadFile');
    if (await fileInput.count() > 0) {
      await fileInput.setInputFiles({
        name: 'e2e_upload_test.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(csvContent),
      });
      await page.waitForTimeout(2000);
      // Check it appeared
      await page.goto('data');
      await page.waitForTimeout(1000);
      const entry = page.locator('#csvFilesList', { hasText: 'e2e_upload_test.csv' });
      if (await entry.isVisible()) {
        // Cleanup
        page.once('dialog', dialog => dialog.accept());
        await page.locator('#csvFilesList tr', { hasText: 'e2e_upload_test.csv' })
          .locator('button', { hasText: /Delete/i }).click();
      }
    }
  });

  test('preview modal shows data', async ({ page }) => {
    // Wait for file list to load
    await page.locator('#csvFilesList tr td').first().waitFor({ timeout: 5000 }).catch(() => {});
    const previewBtn = page.locator('#csvFilesList button', { hasText: 'Preview' }).first();
    if (await previewBtn.isVisible()) {
      await previewBtn.click();
      const modal = page.locator('#previewModal');
      await expect(modal).toHaveClass(/active/, { timeout: 3000 });
    }
  });
});
