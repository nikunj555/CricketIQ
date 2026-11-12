import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const refPath = path.resolve(__dirname, '../src/data/reference_shots.json');
const refData = JSON.parse(fs.readFileSync(refPath, 'utf8'));

// Dynamically import shotTechnique via file:// URL
const techModulePath = path.resolve(__dirname, '../src/data/shotTechnique.ts');
const techUrl = pathToFileURL(techModulePath).href;
const { SHOT_TECHNIQUES, getShotTechnique } = await import(techUrl);

console.log('--- Verifying CricketIQ 25 Shot Techniques ---');

const refShots = Object.keys(refData);
console.log(`Loaded ${refShots.length} catalogue shots from reference_shots.json.`);

// 1. Check all 25 shots exist in SHOT_TECHNIQUES
let missing = 0;
for (const shot of refShots) {
  const tech = getShotTechnique(shot);
  if (!tech) {
    console.error(`❌ Missing technique for shot: "${shot}"`);
    missing++;
  } else if (!tech.intent || tech.intent.trim().length === 0) {
    console.error(`❌ Empty intent for shot: "${shot}"`);
    missing++;
  }
}

if (missing > 0) {
  console.error(`FAILED: ${missing} shots failed technique lookup or missing intent.`);
  process.exit(1);
}
console.log('✅ All 25 shots have valid technique definitions and coaching intents.');

// 2. Check no two shots have identical keyframes
const seenSignatures = new Map();
let duplicates = 0;

for (const [shotName, tech] of Object.entries(SHOT_TECHNIQUES)) {
  const sig = JSON.stringify({
    bl_angle: tech.backlift.batAngleDeg,
    bl_hx: tech.backlift.hands.x,
    bl_hy: tech.backlift.hands.y,
    imp_stride: tech.impact.strideX,
    imp_dir: tech.impact.strideDirDeg,
    imp_lk: tech.impact.leadKneeAngle,
    imp_rk: tech.impact.rearKneeAngle,
    imp_lean: tech.impact.torsoLean,
    imp_angle: tech.impact.batAngleDeg,
    imp_hx: tech.impact.hands.x,
    imp_hy: tech.impact.hands.y,
    imp_sh: tech.impact.shoulderOpeningDeg,
    fin_angle: tech.finish.batAngleDeg,
    fin_hx: tech.finish.hands.x,
    fin_hy: tech.finish.hands.y
  });

  if (seenSignatures.has(sig)) {
    console.error(`❌ Duplicate keyframe signature found between "${shotName}" and "${seenSignatures.get(sig)}"`);
    duplicates++;
  } else {
    seenSignatures.set(sig, shotName);
  }
}

if (duplicates > 0) {
  console.error(`FAILED: ${duplicates} duplicate shot techniques detected.`);
  process.exit(1);
}

console.log('✅ All 25 shot techniques have strictly unique biomechanical keyframes.');
console.log('--- Verification Succeeded (100% Pass) ---');
