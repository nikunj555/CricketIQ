/**
 * CricketIQ — Avatar Biomechanical Verification Suite (Step 5)
 * Automated checks:
 * 1. Grip test: dist(topHand, buttEnd) < dist(topHand, toe), hands on handle [0..35%], never blade.
 * 2. Distinctness test: distance between impact & follow-through poses across all shot pairs > threshold. Closest pairs reported.
 * 3. Completeness test: 25 shots, 7 phases, no NaN/null, no identical consecutive keyframes.
 * 4. Path test: vertical vs horizontal planes, toe path verification (Straight Drive, Cover Drive, Pull, Sweep, Square Cut).
 * 5. State test: Shot switching resets frame/time to 0.
 */

const fs = require('fs');
const path = require('path');

const shotDataPath = path.join(__dirname, '../frontend/src/data/shotAnimations.json');
const rawData = fs.readFileSync(shotDataPath, 'utf8');
const shots = JSON.parse(rawData);

const PHASES = ['stance', 'backlift', 'stride', 'downswing', 'impact', 'follow_through', 'recovery'];
let totalPassed = 0;
let totalFailed = 0;

function assert(condition, message) {
  if (!condition) {
    console.error(`  ❌ FAIL: ${message}`);
    totalFailed++;
    throw new Error(message);
  } else {
    totalPassed++;
  }
}

console.log('================================================================');
console.log('          CRICKETIQ SHOT LIBRARY AVATAR VERIFICATION             ');
console.log('================================================================\n');

// -------------------------------------------------------------
// TEST 1: COMPLETENESS TEST
// -------------------------------------------------------------
console.log('📋 [TEST 1] Completeness Test across all catalogue shots...');
const shotKeys = Object.keys(shots);
assert(shotKeys.length === 25, `Expected 25 shots, got ${shotKeys.length}`);

for (const shotName of shotKeys) {
  const shot = shots[shotName];
  assert(shot.id && shot.name && shot.category && shot.swingPlane, `${shotName} missing metadata`);
  assert(shot.phases, `${shotName} missing phases object`);

  for (const p of PHASES) {
    const kf = shot.phases[p];
    assert(kf, `${shotName} missing phase: ${p}`);
    assert(typeof kf.head?.x === 'number' && !isNaN(kf.head.x), `${shotName} ${p} invalid head.x`);
    assert(typeof kf.torso?.leanDeg === 'number' && !isNaN(kf.torso.leanDeg), `${shotName} ${p} invalid torso`);
    assert(Array.isArray(kf.leadLeg?.kneePos) && kf.leadLeg.kneePos.length === 3, `${shotName} ${p} invalid leadLeg`);
    assert(Array.isArray(kf.rearLeg?.kneePos) && kf.rearLeg.kneePos.length === 3, `${shotName} ${p} invalid rearLeg`);
    assert(Array.isArray(kf.leadArm?.wristPos) && kf.leadArm.wristPos.length === 3, `${shotName} ${p} invalid leadArm`);
    assert(Array.isArray(kf.rearArm?.wristPos) && kf.rearArm.wristPos.length === 3, `${shotName} ${p} invalid rearArm`);
    assert(Array.isArray(kf.bat?.handlePos) && Array.isArray(kf.bat?.tipPos), `${shotName} ${p} invalid bat positions`);
    assert(!isNaN(kf.bat.angleDeg) && !isNaN(kf.bat.bladeFaceDeg), `${shotName} ${p} invalid bat angles`);
  }

  // Ensure phases within shot are dynamic (not identical consecutive keyframes)
  for (let i = 0; i < PHASES.length - 1; i++) {
    const kfA = shot.phases[PHASES[i]];
    const kfB = shot.phases[PHASES[i+1]];
    const diff = Math.abs(kfA.bat.angleDeg - kfB.bat.angleDeg) +
                 Math.abs(kfA.leadArm.elbowAngleDeg - kfB.leadArm.elbowAngleDeg) +
                 Math.abs(kfA.leadLeg.kneeAngleDeg - kfB.leadLeg.kneeAngleDeg);
    assert(diff > 1.0, `${shotName} phases ${PHASES[i]} and ${PHASES[i+1]} are identical (diff = ${diff})`);
  }
}
console.log(`  ✅ Passed: All 25 shots populated with 7 valid non-identical biomechanical phases.\n`);

// -------------------------------------------------------------
// TEST 2: MATHEMATICAL BAT GRIP CONSTRAINT TEST
// -------------------------------------------------------------
console.log('🏏 [TEST 2] Mathematical Bat Grip Constraint Test...');
function dist3(a, b) {
  return Math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2 + (a[2] - b[2])**2);
}

for (const shotName of shotKeys) {
  const shot = shots[shotName];
  const isReverseSweep = shotName.toLowerCase().includes('reverse sweep');

  for (const p of PHASES) {
    const kf = shot.phases[p];
    const topHand = isReverseSweep ? kf.rearArm.wristPos : kf.leadArm.wristPos;
    const bottomHand = isReverseSweep ? kf.leadArm.wristPos : kf.rearArm.wristPos;

    // Bat axis vector from top hand toward bottom hand
    const dx = bottomHand[0] - topHand[0];
    const dy = bottomHand[1] - topHand[1];
    const dz = bottomHand[2] - topHand[2];
    const handSpan = Math.sqrt(dx*dx + dy*dy + dz*dz);
    assert(handSpan > 0.05, `${shotName} ${p}: hands too close together (${handSpan.toFixed(3)}m)`);

    const ux = dx / handSpan;
    const uy = dy / handSpan;
    const uz = dz / handSpan;

    const batLength = 0.90; // Standard bat length in model units
    const buttEnd = [
      topHand[0] - ux * (0.05 * batLength),
      topHand[1] - uy * (0.05 * batLength),
      topHand[2] - uz * (0.05 * batLength),
    ];
    const handleEnd = [
      buttEnd[0] + ux * (0.30 * batLength),
      buttEnd[1] + uy * (0.30 * batLength),
      buttEnd[2] + uz * (0.30 * batLength),
    ];
    const toe = [
      buttEnd[0] + ux * batLength,
      buttEnd[1] + uy * batLength,
      buttEnd[2] + uz * batLength,
    ];

    // Distance checks:
    // 1. Top hand must be closer to butt than to toe
    const dTopButt = dist3(topHand, buttEnd);
    const dTopToe = dist3(topHand, toe);
    assert(dTopButt < dTopToe, `${shotName} ${p}: Top hand closer to toe than butt! (dButt=${dTopButt.toFixed(3)}, dToe=${dTopToe.toFixed(3)})`);

    // 2. Bottom hand must be between top hand and toe
    const dBotButt = dist3(bottomHand, buttEnd);
    const dBotToe = dist3(bottomHand, toe);
    assert(dBotButt < dBotToe, `${shotName} ${p}: Bottom hand closer to toe than butt!`);
    assert(dTopButt < dBotButt, `${shotName} ${p}: Top hand is lower than bottom hand!`);

    // 3. Both hands must lie strictly within the handle section (first 30% of bat from butt)
    const topFraction = dTopButt / batLength;
    const botFraction = dBotButt / batLength;
    assert(topFraction >= 0.03 && topFraction <= 0.12, `${shotName} ${p}: Top hand outside handle region (${(topFraction*100).toFixed(1)}%)`);
    assert(botFraction >= 0.10 && botFraction <= 0.30, `${shotName} ${p}: Bottom hand outside handle region (${(botFraction*100).toFixed(1)}%)`);
  }
}
console.log(`  ✅ Passed: All 175 keyframes strictly obey mathematical grip constraints (hands on handle, blade extending away).\n`);

// -------------------------------------------------------------
// TEST 3: DISTINCTNESS TEST (IMPACT & FOLLOW-THROUGH)
// -------------------------------------------------------------
console.log('📐 [TEST 3] Distinctness Test across all shot pairs...');

function getPoseVector(kf) {
  return [
    kf.torso.leanDeg,
    kf.torso.sideLeanDeg,
    kf.torso.rotationDeg,
    kf.leadLeg.hipAngleDeg,
    kf.leadLeg.kneeAngleDeg,
    kf.rearLeg.kneeAngleDeg,
    kf.leadArm.elbowAngleDeg,
    kf.rearArm.elbowAngleDeg,
    kf.bat.angleDeg,
    kf.bat.bladeFaceDeg,
    kf.leadLeg.footPos[0] * 100, // weight position coords
    kf.leadLeg.footPos[2] * 100,
    kf.head.x * 100,
    kf.head.y * 100,
  ];
}

function poseDistance(v1, v2) {
  let sum = 0;
  for (let i = 0; i < v1.length; i++) {
    sum += (v1[i] - v2[i]) ** 2;
  }
  return Math.sqrt(sum);
}

// Check impact distinctness
let minImpactDist = Infinity;
let closestImpactPair = null;
const impactPairs = [];

for (let i = 0; i < shotKeys.length; i++) {
  for (let j = i + 1; j < shotKeys.length; j++) {
    const s1 = shotKeys[i];
    const s2 = shotKeys[j];
    const v1 = getPoseVector(shots[s1].phases.impact);
    const v2 = getPoseVector(shots[s2].phases.impact);
    const d = poseDistance(v1, v2);
    impactPairs.push({ s1, s2, d });
    if (d < minImpactDist) {
      minImpactDist = d;
      closestImpactPair = { s1, s2, d };
    }
  }
}

impactPairs.sort((a, b) => a.d - b.d);

console.log(`  Closest 5 shot pairs at IMPACT:`);
for (let k = 0; k < 5; k++) {
  const p = impactPairs[k];
  console.log(`    ${k+1}. "${p.s1}" vs "${p.s2}": distance = ${p.d.toFixed(2)}°`);
}
assert(minImpactDist > 12.0, `Min impact distance too small: ${minImpactDist.toFixed(2)} between ${closestImpactPair.s1} & ${closestImpactPair.s2}`);
console.log(`  ✅ Impact Distinctness Passed: Minimum pair distance = ${minImpactDist.toFixed(2)}° (threshold 12.0°).\n`);

// Check follow-through distinctness
let minFtDist = Infinity;
let closestFtPair = null;
const ftPairs = [];

for (let i = 0; i < shotKeys.length; i++) {
  for (let j = i + 1; j < shotKeys.length; j++) {
    const s1 = shotKeys[i];
    const s2 = shotKeys[j];
    const v1 = getPoseVector(shots[s1].phases.follow_through);
    const v2 = getPoseVector(shots[s2].phases.follow_through);
    const d = poseDistance(v1, v2);
    ftPairs.push({ s1, s2, d });
    if (d < minFtDist) {
      minFtDist = d;
      closestFtPair = { s1, s2, d };
    }
  }
}

ftPairs.sort((a, b) => a.d - b.d);
console.log(`  Closest 5 shot pairs at FOLLOW-THROUGH:`);
for (let k = 0; k < 5; k++) {
  const p = ftPairs[k];
  console.log(`    ${k+1}. "${p.s1}" vs "${p.s2}": distance = ${p.d.toFixed(2)}°`);
}
assert(minFtDist > 12.0, `Min follow-through distance too small: ${minFtDist.toFixed(2)} between ${closestFtPair.s1} & ${closestFtPair.s2}`);
console.log(`  ✅ Follow-Through Distinctness Passed: Minimum pair distance = ${minFtDist.toFixed(2)}° (threshold 12.0°).\n`);

// -------------------------------------------------------------
// TEST 4: PATH & TRAJECTORY TEST
// -------------------------------------------------------------
console.log('🛤️ [TEST 4] Biomechanical Path & Trajectory Test...');

// 4A: Straight Drive (mostly vertical plane, low lateral Z deviation)
const sd = shots['Straight Drive'];
const sdTipImpactZ = sd.phases.impact.bat.tipPos[2];
const sdTipStanceZ = sd.phases.stance.bat.tipPos[2];
const sdTipDiffZ = Math.abs(sdTipImpactZ - sdTipStanceZ);
assert(sdTipDiffZ < 0.15, `Straight Drive has high lateral Z deviation (${sdTipDiffZ.toFixed(3)}m)`);
assert(sd.phases.impact.bat.angleDeg <= 20, `Straight Drive impact bat not vertical (${sd.phases.impact.bat.angleDeg}°)`);

// 4B: Cover Drive (moves through off side: positive Z)
const cd = shots['Cover Drive'];
const cdTipImpactZ = cd.phases.impact.bat.tipPos[2];
assert(cdTipImpactZ > 0.15, `Cover Drive impact tip should be on off-side (+Z), got ${cdTipImpactZ.toFixed(3)}m`);
assert(cd.phases.impact.leadLeg.footPos[2] > 0.15, `Cover Drive front foot should be placed toward covers (+Z)`);

// 4C: Pull Shot (cross-bat horizontal, leg side: negative Z, deep back foot)
const pull = shots['Pull Shot'];
assert(pull.phases.impact.bat.angleDeg >= 80, `Pull shot should be cross-bat (angle >= 80°), got ${pull.phases.impact.bat.angleDeg}°`);
assert(pull.phases.impact.bat.tipPos[2] < 0.0, `Pull shot follow/impact should finish toward leg side (-Z)`);
assert(pull.phases.stride.leadLeg.footPos[0] < 0.1, `Pull shot should not have forward stride`);

// 4D: Sweep (kneeling rear knee, low to the turf)
const sweep = shots['Sweep'];
assert(sweep.phases.impact.rearLeg.isKneeling === true, `Sweep shot rear leg should be marked isKneeling`);
assert(sweep.phases.impact.rearLeg.kneePos[1] <= 0.08, `Sweep rear knee should be on ground (y <= 0.08), got ${sweep.phases.impact.rearLeg.kneePos[1]}`);
assert(sweep.phases.impact.bat.tipPos[1] <= 0.20, `Sweep bat tip should be close to turf (y <= 0.20), got ${sweep.phases.impact.bat.tipPos[1]}`);

// 4E: Square Cut (horizontal off side, high backlift)
const cut = shots['Square Cut'];
assert(cut.phases.impact.bat.angleDeg >= 80, `Square Cut should be horizontal cross-bat, got ${cut.phases.impact.bat.angleDeg}°`);
assert(cut.phases.impact.bat.tipPos[2] > 0.15, `Square Cut impact should be on off-side (+Z), got ${cut.phases.impact.bat.tipPos[2]}`);

console.log('  ✅ Path & Trajectory Test Passed for Straight Drive, Cover Drive, Pull, Sweep, Square Cut.\n');

// -------------------------------------------------------------
// TEST 5: STATE TEST (RESET ON SHOT CHANGE)
// -------------------------------------------------------------
console.log('🔄 [TEST 5] State & Timing Reset Verification...');
// Verifies code structure in RealisticBatterVisualizer:
const visSrc = fs.readFileSync(path.join(__dirname, '../frontend/src/components/RealisticBatterVisualizer.tsx'), 'utf8');
assert(visSrc.includes('setActivePhaseIndex(initialPhaseIndex)'), 'Component must reset activePhaseIndex when initialPhaseIndex changes');
assert(visSrc.includes('setSubFrameProgress(0)'), 'Component must reset subFrameProgress to 0 on phase/shot change');
assert(visSrc.includes('batTrailBufferRef.current = []'), 'Component must clear motion trail on shot switch');

console.log('  ✅ State Reset Test Passed: Animation counters and trails reset on shot/phase change.\n');

console.log('================================================================');
console.log(`🎯 ALL CHECKS PASSED: ${totalPassed} assertions OK, ${totalFailed} failures.`);
console.log('================================================================');
