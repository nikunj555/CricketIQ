import pkg from '../node_modules/@playwright/test/index.js';
const { chromium } = pkg;
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const outDir = path.resolve(__dirname, '../../storage/annotated/shots_raw');
const shotName = 'Helicopter Shot';
const slug = 'helicopter-shot';

console.log(`Capturing single shot: "${shotName}"...`);

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle' });
await page.waitForTimeout(1000);

// Navigate to Library tab
const libraryTabBtn = page.locator('button:has-text("Shot Library"), a:has-text("Shot Library")').first();
if (await libraryTabBtn.isVisible()) {
  await libraryTabBtn.click();
  await page.waitForTimeout(1000);
}

// Locate Helicopter Shot
const shotCard = page.locator(`text="${shotName}"`).first();
if (await shotCard.isVisible({ timeout: 5000 })) {
  await shotCard.click();
  await page.waitForTimeout(600);

  // Switch to 2D blueprint mode if available
  const blueprintBtn = page.locator('button:has-text("2D Kinematic Blueprint")').first();
  if (await blueprintBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await blueprintBtn.click();
    await page.waitForTimeout(400);
  }

  // Pause
  const pauseBtn = page.locator('button[title="Pause Animation"]').first();
  if (await pauseBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
    await pauseBtn.click();
    await page.waitForTimeout(200);
  }

  // Impact
  const impactBtn = page.locator('button:has-text("Impact")').first();
  if (await impactBtn.isVisible({ timeout: 1000 })) {
    await impactBtn.click();
    await page.waitForTimeout(350);
    const canvas = page.locator('canvas').first();
    await canvas.screenshot({ path: path.join(outDir, `${slug}_impact.png`) });
  }

  // Follow-through
  const finishBtn = page.locator('button:has-text("Follow-through")').first();
  if (await finishBtn.isVisible({ timeout: 1000 })) {
    await finishBtn.click();
    await page.waitForTimeout(350);
    const canvas = page.locator('canvas').first();
    await canvas.screenshot({ path: path.join(outDir, `${slug}_finish.png`) });
  }
}

await browser.close();
console.log('Helicopter Shot capture finished.');
