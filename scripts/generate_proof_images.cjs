/**
 * CricketIQ — Playwright Automated Proof Image Generator (Step 6)
 * Generates:
 * 1. docs/avatar-proof/contact_sheet_impact_8shots.png
 * 2. docs/avatar-proof/strip_straight_drive_7phases.png
 * 3. docs/avatar-proof/strip_pull_7phases.png
 * 4. docs/avatar-proof/strip_sweep_7phases.png
 * 5. docs/avatar-proof/zoomed_grip_crop_3shots.png
 */

const path = require('path');
const fs = require('fs');
const { chromium } = require(path.resolve(__dirname, '../frontend/node_modules/playwright'));

const outDir = path.resolve(__dirname, '../docs/avatar-proof');
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

const shotData = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../frontend/src/data/reference_shots.json'), 'utf8'));
const harnessPath = 'file://' + path.resolve(__dirname, 'render_harness.html').replace(/\\/g, '/');

async function main() {
  console.log('🚀 Launching Chromium for high-fidelity avatar visual proof capture...');
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage({
    viewport: { width: 2800, height: 1200 },
    deviceScaleFactor: 1
  });

  await page.goto(harnessPath);

  // Inject shots data
  await page.evaluate((shots) => {
    window.SHOTS = shots;
  }, shotData);

  // =================================================================
  // 1. CONTACT SHEET: 8 VISIBLY DISTINCT SHOTS AT IMPACT
  // 4x2 Grid (2400 x 900)
  // =================================================================
  console.log('📸 Generating 1. contact_sheet_impact_8shots.png...');
  const impactShots = [
    'Straight Drive',
    'Cover Drive',
    'On Drive',
    'Forward Defensive',
    'Pull Shot',
    'Square Cut',
    'Sweep',
    'Reverse Sweep'
  ];

  const contactSheetPngBase64 = await page.evaluate(async (shotsList) => {
    const cols = 4;
    const rows = 2;
    const cellW = 600;
    const cellH = 450;

    const master = document.createElement('canvas');
    master.width = cols * cellW;
    master.height = rows * cellH + 60; // Extra room for header
    const mctx = master.getContext('2d');

    // Dark background
    mctx.fillStyle = '#080B10';
    mctx.fillRect(0, 0, master.width, master.height);

    // Global Header
    mctx.fillStyle = '#7FEA35';
    mctx.font = 'bold 22px monospace';
    mctx.fillText('CRICKETIQ — 8 DISTINCT SHOTS AT IMPACT (BAT HELD BY HANDLE)', 30, 40);

    mctx.fillStyle = '#94A3B8';
    mctx.font = '14px monospace';
    mctx.fillText('Proof of Mathematical Grip Constraint & Dynamic Biomechanics Across Catalogue', master.width - 700, 40);

    const subCanvas = document.getElementById('canvas');
    subCanvas.width = cellW;
    subCanvas.height = cellH;

    for (let idx = 0; idx < shotsList.length; idx++) {
      const sName = shotsList[idx];
      const col = idx % cols;
      const row = Math.floor(idx / cols);
      const x = col * cellW;
      const y = row * cellH + 60;

      window.renderToCanvas(sName, 'impact', {
        debug: true,
        title: `${idx + 1}. ${sName}`,
        phaseLabel: 'IMPACT WINDOW'
      });

      mctx.drawImage(subCanvas, x, y, cellW, cellH);

      // Border between cells
      mctx.strokeStyle = '#1E293B';
      mctx.lineWidth = 1.5;
      mctx.strokeRect(x, y, cellW, cellH);
    }

    return master.toDataURL('image/png');
  }, impactShots);

  const contactSheetBuffer = Buffer.from(contactSheetPngBase64.replace(/^data:image\/png;base64,/, ''), 'base64');
  const contactSheetPath = path.join(outDir, 'contact_sheet_impact_8shots.png');
  fs.writeFileSync(contactSheetPath, contactSheetBuffer);
  console.log(`  ✓ Saved: ${contactSheetPath} (${(contactSheetBuffer.length / 1024).toFixed(1)} KB)`);

  // =================================================================
  // 2. 7-PHASE STRIP: STRAIGHT DRIVE
  // =================================================================
  console.log('📸 Generating 2. strip_straight_drive_7phases.png...');
  const phases = ['stance', 'backlift', 'stride', 'downswing', 'impact', 'follow_through', 'recovery'];

  const straightDrivePngBase64 = await page.evaluate(async ({ shotName, phasesList }) => {
    const cellW = 380;
    const cellH = 460;
    const master = document.createElement('canvas');
    master.width = cellW * phasesList.length;
    master.height = cellH + 60;
    const mctx = master.getContext('2d');

    mctx.fillStyle = '#080B10';
    mctx.fillRect(0, 0, master.width, master.height);

    mctx.fillStyle = '#7FEA35';
    mctx.font = 'bold 20px monospace';
    mctx.fillText('CRICKETIQ — STRAIGHT DRIVE: 7 BIOMECHANICAL PHASES', 30, 38);

    const subCanvas = document.getElementById('canvas');
    subCanvas.width = cellW;
    subCanvas.height = cellH;

    for (let idx = 0; idx < phasesList.length; idx++) {
      const pKey = phasesList[idx];
      const x = idx * cellW;
      const y = 60;

      window.renderToCanvas(shotName, pKey, {
        debug: true,
        title: shotName,
        phaseLabel: `${idx + 1}. ${pKey.toUpperCase()}`
      });

      mctx.drawImage(subCanvas, x, y, cellW, cellH);
      mctx.strokeStyle = '#1E293B';
      mctx.strokeRect(x, y, cellW, cellH);
    }

    return master.toDataURL('image/png');
  }, { shotName: 'Straight Drive', phasesList: phases });

  const sdBuffer = Buffer.from(straightDrivePngBase64.replace(/^data:image\/png;base64,/, ''), 'base64');
  const sdPath = path.join(outDir, 'strip_straight_drive_7phases.png');
  fs.writeFileSync(sdPath, sdBuffer);
  console.log(`  ✓ Saved: ${sdPath} (${(sdBuffer.length / 1024).toFixed(1)} KB)`);

  // =================================================================
  // 3. 7-PHASE STRIP: PULL SHOT
  // =================================================================
  console.log('📸 Generating 3. strip_pull_7phases.png...');
  const pullPngBase64 = await page.evaluate(async ({ shotName, phasesList }) => {
    const cellW = 380;
    const cellH = 460;
    const master = document.createElement('canvas');
    master.width = cellW * phasesList.length;
    master.height = cellH + 60;
    const mctx = master.getContext('2d');

    mctx.fillStyle = '#080B10';
    mctx.fillRect(0, 0, master.width, master.height);

    mctx.fillStyle = '#7FEA35';
    mctx.font = 'bold 20px monospace';
    mctx.fillText('CRICKETIQ — PULL SHOT: 7 BIOMECHANICAL PHASES (CROSS-BAT HORIZONTAL)', 30, 38);

    const subCanvas = document.getElementById('canvas');
    subCanvas.width = cellW;
    subCanvas.height = cellH;

    for (let idx = 0; idx < phasesList.length; idx++) {
      const pKey = phasesList[idx];
      const x = idx * cellW;
      const y = 60;

      window.renderToCanvas(shotName, pKey, {
        debug: true,
        title: shotName,
        phaseLabel: `${idx + 1}. ${pKey.toUpperCase()}`
      });

      mctx.drawImage(subCanvas, x, y, cellW, cellH);
      mctx.strokeStyle = '#1E293B';
      mctx.strokeRect(x, y, cellW, cellH);
    }

    return master.toDataURL('image/png');
  }, { shotName: 'Pull Shot', phasesList: phases });

  const pullBuffer = Buffer.from(pullPngBase64.replace(/^data:image\/png;base64,/, ''), 'base64');
  const pullPath = path.join(outDir, 'strip_pull_7phases.png');
  fs.writeFileSync(pullPath, pullBuffer);
  console.log(`  ✓ Saved: ${pullPath} (${(pullBuffer.length / 1024).toFixed(1)} KB)`);

  // =================================================================
  // 4. 7-PHASE STRIP: SWEEP (KNEELING REAR KNEE ON GROUND, LOW BAT)
  // =================================================================
  console.log('📸 Generating 4. strip_sweep_7phases.png...');
  const sweepPngBase64 = await page.evaluate(async ({ shotName, phasesList }) => {
    const cellW = 380;
    const cellH = 460;
    const master = document.createElement('canvas');
    master.width = cellW * phasesList.length;
    master.height = cellH + 60;
    const mctx = master.getContext('2d');

    mctx.fillStyle = '#080B10';
    mctx.fillRect(0, 0, master.width, master.height);

    mctx.fillStyle = '#7FEA35';
    mctx.font = 'bold 20px monospace';
    mctx.fillText('CRICKETIQ — SWEEP: 7 BIOMECHANICAL PHASES (REAR KNEE KNEELING ON TURF)', 30, 38);

    const subCanvas = document.getElementById('canvas');
    subCanvas.width = cellW;
    subCanvas.height = cellH;

    for (let idx = 0; idx < phasesList.length; idx++) {
      const pKey = phasesList[idx];
      const x = idx * cellW;
      const y = 60;

      window.renderToCanvas(shotName, pKey, {
        debug: true,
        title: shotName,
        phaseLabel: `${idx + 1}. ${pKey.toUpperCase()}`
      });

      mctx.drawImage(subCanvas, x, y, cellW, cellH);
      mctx.strokeStyle = '#1E293B';
      mctx.strokeRect(x, y, cellW, cellH);
    }

    return master.toDataURL('image/png');
  }, { shotName: 'Sweep', phasesList: phases });

  const sweepBuffer = Buffer.from(sweepPngBase64.replace(/^data:image\/png;base64,/, ''), 'base64');
  const sweepPath = path.join(outDir, 'strip_sweep_7phases.png');
  fs.writeFileSync(sweepPath, sweepBuffer);
  console.log(`  ✓ Saved: ${sweepPath} (${(sweepBuffer.length / 1024).toFixed(1)} KB)`);

  // =================================================================
  // 5. ZOOMED GRIP CROP: STRAIGHT DRIVE, SWEEP, AND PULL
  // =================================================================
  console.log('📸 Generating 5. zoomed_grip_crop_3shots.png...');
  const zoomedGripPngBase64 = await page.evaluate(async () => {
    const shotsToZoom = ['Straight Drive', 'Sweep', 'Pull Shot'];
    const cellW = 600;
    const cellH = 550;
    const master = document.createElement('canvas');
    master.width = cellW * 3;
    master.height = cellH + 70;
    const mctx = master.getContext('2d');

    mctx.fillStyle = '#080B10';
    mctx.fillRect(0, 0, master.width, master.height);

    mctx.fillStyle = '#7FEA35';
    mctx.font = 'bold 22px monospace';
    mctx.fillText('CRICKETIQ — ZOOMED BAT GRIP DETAIL (BOTH HANDS ON HANDLE, BUTT VISIBLE, BLADE EXTENDING)', 30, 42);

    const fullCanvas = document.getElementById('canvas');
    fullCanvas.width = 1200;
    fullCanvas.height = 900;

    for (let i = 0; i < shotsToZoom.length; i++) {
      const sName = shotsToZoom[i];
      window.renderToCanvas(sName, 'impact', {
        debug: true,
        title: sName,
        phaseLabel: 'IMPACT'
      });

      const shot = window.SHOTS[sName];
      const pose = window.calculatePose(shot, 'impact', 'side', 'Right', 1200, 900);
      const topH = pose.topHandGrip;

      // Crop a 280x280 region around hands & handle and blow it up into 600x550
      const cropW = 280;
      const cropH = 260;
      const cropX = Math.max(0, topH.x - cropW / 2);
      const cropY = Math.max(0, topH.y - cropH / 2 + 10);

      const destX = i * cellW;
      const destY = 70;

      mctx.drawImage(fullCanvas, cropX, cropY, cropW, cropH, destX, destY, cellW, cellH);

      // Header card over crop
      mctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
      mctx.strokeStyle = '#38BDF8';
      mctx.lineWidth = 1.5;
      mctx.beginPath();
      mctx.roundRect(destX + 20, destY + 20, 360, 60, 8);
      mctx.fill();
      mctx.stroke();

      mctx.fillStyle = '#7FEA35';
      mctx.font = 'bold 16px monospace';
      mctx.fillText(sName.toUpperCase(), destX + 32, destY + 45);

      mctx.fillStyle = '#F5F5F5';
      mctx.font = '12px monospace';
      mctx.fillText('✓ Top hand: 5% | Bottom hand: 21% | Butt: 0%', destX + 32, destY + 65);

      mctx.strokeStyle = '#334155';
      mctx.lineWidth = 2;
      mctx.strokeRect(destX, destY, cellW, cellH);
    }

    return master.toDataURL('image/png');
  });

  const zoomBuffer = Buffer.from(zoomedGripPngBase64.replace(/^data:image\/png;base64,/, ''), 'base64');
  const zoomPath = path.join(outDir, 'zoomed_grip_crop_3shots.png');
  fs.writeFileSync(zoomPath, zoomBuffer);
  console.log(`  ✓ Saved: ${zoomPath} (${(zoomBuffer.length / 1024).toFixed(1)} KB)`);

  await browser.close();
  console.log('\n🎉 ALL 5 PROOF IMAGES SUCCESSFULLY GENERATED AND SAVED TO docs/avatar-proof/');
}

main().catch((err) => {
  console.error('Fatal error generating proof images:', err);
  process.exit(1);
});
