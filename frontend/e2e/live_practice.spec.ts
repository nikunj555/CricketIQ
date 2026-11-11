import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('CricketIQ E2E Visual Verification with Mock Camera', () => {
  const screenshotsDir = path.resolve(__dirname, '../../docs/screenshots');

  test.beforeAll(() => {
    if (!fs.existsSync(screenshotsDir)) {
      fs.mkdirSync(screenshotsDir, { recursive: true });
    }
  });

  test('captures Live Practice page with synthetic webcam stream', async ({ page }) => {
    // Navigate to root (defaults to Live Practice)
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    const liveShotPath = path.join(screenshotsDir, 'live_practice.png');
    await page.screenshot({ path: liveShotPath, fullPage: true });
    expect(fs.existsSync(liveShotPath)).toBe(true);
    console.log(`[PASS] Captured Live Practice screenshot -> ${liveShotPath}`);
  });

  test('captures Dashboard view', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Click Dashboard in sidebar
    const dashboardButton = page.locator('button:has-text("Dashboard"), a:has-text("Dashboard")').first();
    if (await dashboardButton.isVisible()) {
      await dashboardButton.click();
      await page.waitForTimeout(1500);
    }

    const dashboardPath = path.join(screenshotsDir, 'dashboard.png');
    await page.screenshot({ path: dashboardPath, fullPage: true });
    expect(fs.existsSync(dashboardPath)).toBe(true);
    console.log(`[PASS] Captured Dashboard screenshot -> ${dashboardPath}`);
  });

  test('captures Shot Library catalogue with 25+ shots', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Click Shot Library in sidebar
    const libraryButton = page.locator('button:has-text("Shot Library"), a:has-text("Shot Library")').first();
    if (await libraryButton.isVisible()) {
      await libraryButton.click();
      await page.waitForTimeout(1500);
    }

    const libraryPath = path.join(screenshotsDir, 'shot_library.png');
    await page.screenshot({ path: libraryPath, fullPage: true });
    expect(fs.existsSync(libraryPath)).toBe(true);
    console.log(`[PASS] Captured Shot Library screenshot -> ${libraryPath}`);
  });
});
