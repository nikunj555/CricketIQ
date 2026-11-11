/**
 * CricketIQ — Biomechanical Shot Animation Generator & Verifier
 * Generates authoritative, distinct 7-phase keyframes across all 25 catalogue shots.
 * Enforces anatomical constraints and bat-grip kinematics.
 */

const fs = require('fs');
const path = require('path');

// 25 Catalogue Cricket Shots
const SHOT_NAMES = [
  'Straight Drive',
  'Cover Drive',
  'On Drive',
  'Off Drive',
  'Lofted Drive',
  'Forward Defensive',
  'Back-foot Defensive',
  'Back-foot Punch',
  'Square Cut',
  'Late Cut',
  'Upper Cut',
  'Pull Shot',
  'Hook Shot',
  'Flick Shot',
  'Leg Glance',
  'Clip Shot',
  'Sweep',
  'Slog Sweep',
  'Reverse Sweep',
  'Paddle Sweep',
  'Slog',
  'Switch Hit',
  'Scoop Shot',
  'Ramp Shot',
  'Helicopter Shot'
];

function createKeyframe(cfg) {
  const {
    phaseKey,
    label,
    durationWeight = 1.0,
    cue,
    techniquePoints = [],
    head,
    torso,
    leadLeg,
    rearLeg,
    leadArm,
    rearArm,
    bat
  } = cfg;

  return {
    phaseKey,
    label,
    durationWeight,
    cue,
    techniquePoints,
    head: {
      x: head.x,
      y: head.y,
      z: head.z,
      tiltDeg: head.tiltDeg || 0,
      overFrontKnee: !!head.overFrontKnee
    },
    torso: {
      leanDeg: torso.leanDeg || 0,
      sideLeanDeg: torso.sideLeanDeg || 0,
      rotationDeg: torso.rotationDeg || 0,
      hip: torso.hip,
      chest: torso.chest
    },
    leadLeg: {
      hipAngleDeg: leadLeg.hipAngleDeg,
      kneeAngleDeg: leadLeg.kneeAngleDeg,
      ankleAngleDeg: leadLeg.ankleAngleDeg,
      kneePos: leadLeg.kneePos,
      footPos: leadLeg.footPos,
      isKneeling: !!leadLeg.isKneeling
    },
    rearLeg: {
      hipAngleDeg: rearLeg.hipAngleDeg,
      kneeAngleDeg: rearLeg.kneeAngleDeg,
      ankleAngleDeg: rearLeg.ankleAngleDeg,
      kneePos: rearLeg.kneePos,
      footPos: rearLeg.footPos,
      isKneeling: !!rearLeg.isKneeling
    },
    leadArm: {
      shoulderPos: leadArm.shoulderPos,
      elbowPos: leadArm.elbowPos,
      elbowAngleDeg: leadArm.elbowAngleDeg,
      wristPos: leadArm.wristPos
    },
    rearArm: {
      shoulderPos: rearArm.shoulderPos,
      elbowPos: rearArm.elbowPos,
      elbowAngleDeg: rearArm.elbowAngleDeg,
      wristPos: rearArm.wristPos
    },
    bat: {
      angleDeg: bat.angleDeg,
      bladeFaceDeg: bat.bladeFaceDeg || 0,
      handlePos: bat.handlePos,
      tipPos: bat.tipPos,
      swingPlane: bat.swingPlane
    }
  };
}

// Compute bat tip and handle position strictly derived from hands and bat axis
function deriveBatGeometry(topWrist, bottomWrist, length = 0.88, axisAngleDeg = null, lateralZ = 0) {
  let dx = bottomWrist[0] - topWrist[0];
  let dy = bottomWrist[1] - topWrist[1];
  let dz = bottomWrist[2] - topWrist[2];
  let len = Math.hypot(dx, dy, dz);

  let ux, uy, uz;
  if (len < 0.04 && axisAngleDeg !== null) {
    const rad = (axisAngleDeg * Math.PI) / 180;
    ux = Math.sin(rad);
    uy = -Math.cos(rad);
    uz = lateralZ;
  } else {
    ux = dx / (len || 1);
    uy = dy / (len || 1);
    uz = dz / (len || 1);
  }

  // Butt sits 5% above top wrist along -u
  const buttEnd = [
    topWrist[0] - ux * 0.05 * length,
    topWrist[1] - uy * 0.05 * length,
    topWrist[2] - uz * 0.05 * length
  ];

  // Tip sits at length from butt
  const tipPos = [
    buttEnd[0] + ux * length,
    buttEnd[1] + uy * length,
    buttEnd[2] + uz * length
  ];

  return {
    handlePos: topWrist,
    tipPos: tipPos,
    buttEnd: buttEnd,
    axis: [ux, uy, uz]
  };
}

console.log('Building all 25 shot definitions...');
// We will generate the complete data structure
