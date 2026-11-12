import pkg from '../node_modules/@playwright/test/index.js';
const { chromium } = pkg;
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const refPath = path.resolve(__dirname, '../src/data/reference_shots.json');
const refData = JSON.parse(fs.readFileSync(refPath, 'utf8'));
const shotNames = Object.keys(refData);

const outDir = path.resolve(__dirname, '../../storage/annotated/shots_raw');
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

console.log(`Starting standalone browser capture for ${shotNames.length} shots...`);

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle' });
await page.waitForTimeout(1000);

// Navigate to Library tab by clicking sidebar button
const libraryTabBtn = page.locator('button:has-text("Shot Library"), a:has-text("Shot Library")').first();
if (await libraryTabBtn.isVisible()) {
  await libraryTabBtn.click();
  await page.waitForTimeout(1000);
}

for (let i = 0; i < shotNames.length; i++) {
  const shotName = shotNames[i];
  const slug = shotName.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  console.log(`[${i + 1}/${shotNames.length}] Capturing "${shotName}"...`);

  // Locate card by text
  const shotCard = page.locator(`text="${shotName}"`).first();
  if (await shotCard.isVisible({ timeout: 2000 }).catch(() => false)) {
    await shotCard.click();
    await page.waitForTimeout(500);

    // Switch to 2D blueprint mode if available
    const blueprintBtn = page.locator('button:has-text("2D Kinematic Blueprint")').first();
    if (await blueprintBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
      await blueprintBtn.click();
      await page.waitForTimeout(300);
    }

    // Pause animation
    const pauseBtn = page.locator('button[title="Pause Animation"]').first();
    if (await pauseBtn.isVisible({ timeout: 500 }).catch(() => false)) {
      await pauseBtn.click();
      await page.waitForTimeout(100);
    }

    // Impact (Phase 5 / index 4)
    const impactBtn = page.locator('button:has-text("Impact")').first();
    if (await impactBtn.isVisible({ timeout: 500 }).catch(() => false)) {
      await impactBtn.click();
      await page.waitForTimeout(300);
      const canvas = page.locator('canvas').first();
      if (await canvas.isVisible({ timeout: 500 }).catch(() => false)) {
        await canvas.screenshot({ path: path.join(outDir, `${slug}_impact.png`) });
      }
    }

    // Follow-through (Phase 6 / index 5)
    const finishBtn = page.locator('button:has-text("Follow-through")').first();
    if (await finishBtn.isVisible({ timeout: 500 }).catch(() => false)) {
      await finishBtn.click();
      await page.waitForTimeout(300);
      const canvas = page.locator('canvas').first();
      if (await canvas.isVisible({ timeout: 500 }).catch(() => false)) {
        await canvas.screenshot({ path: path.join(outDir, `${slug}_finish.png`) });
      }
    }

    // Close modal
    const closeBtn = page.locator('button:has(svg.lucide-x)').first();
    if (await closeBtn.isVisible({ timeout: 500 }).catch(() => false)) {
      await closeBtn.click();
      await page.waitForTimeout(250);
    }
  } else {
    console.warn(`Card for "${shotName}" not immediately found on library page.`);
  }
}

await browser.close();
console.log('Capture finished.');
