const fs = require('fs');
const path = require('path');

const targetJsonPath = path.resolve(__dirname, '../frontend/src/data/shotAnimations.json');

// Helper to round coordinates cleanly
const r = (val) => Math.round(val * 1000) / 1000;
const r3 = (arr) => [r(arr[0]), r(arr[1]), r(arr[2])];

// Derives bat geometry and strict 8cm handle grip along bat axis
function getBatAndGrip(topW, rawBotW, length = 0.88, axisAngleDeg = null, lateralZ = null) {
  let dx = rawBotW[0] - topW[0];
  let dy = rawBotW[1] - topW[1];
  let dz = rawBotW[2] - topW[2];
  let len = Math.hypot(dx, dy, dz);

  let ux, uy, uz;
  if (len < 0.01 && axisAngleDeg !== null) {
    const rad = (axisAngleDeg * Math.PI) / 180;
    ux = Math.sin(rad);
    uy = -Math.cos(rad);
    uz = lateralZ !== null ? lateralZ : 0;
  } else {
    ux = dx / (len || 1);
    uy = dy / (len || 1);
    uz = dz / (len || 1);
  }

  // Standardize hand separation to 8.0 cm along bat axis
  const standardHandSpan = 0.08;
  const botW = [
    r(topW[0] + ux * standardHandSpan),
    r(topW[1] + uy * standardHandSpan),
    r(topW[2] + uz * standardHandSpan)
  ];

  // Butt sits 5% of bat length above the top wrist along -u
  const buttEnd = [
    r(topW[0] - ux * 0.05 * length),
    r(topW[1] - uy * 0.05 * length),
    r(topW[2] - uz * 0.05 * length)
  ];

  // Tip sits at bat length from butt along +u
  const tipPos = [
    r(buttEnd[0] + ux * length),
    r(buttEnd[1] + uy * length),
    r(buttEnd[2] + uz * length)
  ];

  return {
    topW: r3(topW),
    botW: botW,
    handlePos: r3(topW),
    tipPos: tipPos,
    buttEnd: buttEnd,
    axis: [r(ux), r(uy), r(uz)]
  };
}

// 25 Catalogue definitions
const shotsConfig = [
  // 1. Straight Drive
  {
    name: 'Straight Drive',
    category: 'Drives',
    swingPlane: 'vertical',
    ballTraj: { line: 'Middle Stump', length: 'Full Pitch', pitch: [1.2, 0, 0.0], contact: [0.48, 0.28, 0.0] },
    details: {
      commonMistakes: [
        'Head falling over to the off side away from the line of the ball',
        'Bottom hand overpowering the top hand, causing an aerial slice',
        'Over-striding causing hip lock and loss of vertical pendulum'
      ],
      drills: [
        'Drop ball drill directly under the nose with high front elbow check',
        'Cone striking drill focusing on straight follow-through back to bowler',
        'One-hand lead arm progression hitting along crease line'
      ]
    },
    cues: {
      stance: 'Balanced upright stance, weight evenly distributed on balls of feet',
      backlift: 'High vertical backlift pointing straight toward slip cordon',
      stride: 'Decisive front-foot stride along the line of delivery, head over knee',
      downswing: 'Pendulum swing down the line led smoothly by high front elbow',
      impact: 'Dead-straight impact under the eye-line, blade full face to bowler',
      follow_through: 'High classical V finish, both arms extending toward long-off/long-on',
      recovery: 'Push firmly off front foot, returning to balanced ready base'
    },
    kinematics: {
      // Stance
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      // Backlift
      backlift: { hip: [-0.04, 0.90, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 165, elbowAngle: 110, batAngle: -55, topW: [-0.06, 1.05, 0.14], botW: [-0.09, 1.11, 0.10], torsoRot: 12 },
      // Stride
      stride: { hip: [0.12, 0.88, 0], leadFoot: [0.48, 0, 0], rearFoot: [-0.16, 0, -0.02], kneeAngle: 132, elbowAngle: 125, batAngle: -25, topW: [0.04, 1.06, 0.04], botW: [0.01, 1.08, 0.01] },
      // Downswing
      downswing: { hip: [0.16, 0.85, 0], leadFoot: [0.48, 0, 0], rearFoot: [-0.16, 0, -0.02], kneeAngle: 124, elbowAngle: 142, batAngle: 4, topW: [0.22, 0.88, 0.04], botW: [0.20, 0.80, 0.02] },
      // Impact
      impact: { hip: [0.18, 0.86, 0], leadFoot: [0.48, 0, 0], rearFoot: [-0.16, 0, -0.02], kneeAngle: 118, rearKneeAngle: 145, elbowAngle: 145, batAngle: 10, topW: [0.32, 0.74, 0.04], botW: [0.30, 0.65, 0.02], torsoLean: 26, torsoRot: 28 },
      // Follow-through
      follow_through: { hip: [0.20, 0.88, 0], leadFoot: [0.48, 0, 0], rearFoot: [-0.16, 0, -0.02], kneeAngle: 122, rearKneeAngle: 150, elbowAngle: 160, batAngle: -85, topW: [0.30, 1.25, 0.04], botW: [0.28, 1.34, 0.02], torsoLean: 18, torsoRot: 40 }
    }
  },

  // 2. Cover Drive
  {
    name: 'Cover Drive',
    category: 'Drives',
    swingPlane: 'angled_off',
    ballTraj: { line: 'Off Stump Channel', length: 'Full / Overpitched', pitch: [1.2, 0, 0.22], contact: [0.42, 0.26, 0.24] },
    details: {
      commonMistakes: [
        'Reaching for the ball without committing front foot to the pitch',
        'Bottom hand grip too tight closing the bat face',
        'Slashing across the line instead of swinging inside-out'
      ],
      drills: [
        'Cover target gate drill with two cones placed at extra cover',
        'Tee-ball drill stationed 25cm outside off stump',
        'High elbow hold progression verifying front shoulder line'
      ]
    },
    cues: {
      stance: 'Balanced ready stance, head steady, eyes aligned with off stump',
      backlift: 'Fluid cocked backlift angling toward slips and gully',
      stride: 'Decisive footwork across to the off side, planting foot near ball line',
      downswing: 'Leading elbow drives smoothly along the angled-off path',
      impact: 'Crisp strike through covers, front knee bent 120°, head over ball',
      follow_through: 'Exquisite high finish curling gracefully over the front shoulder',
      recovery: 'Push firmly off front foot, recovering back to balanced stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.04, 0.90, 0.02], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 165, elbowAngle: 110, batAngle: -50, topW: [-0.06, 1.05, 0.16], botW: [-0.09, 1.11, 0.12], torsoRot: 15 },
      stride: { hip: [0.10, 0.88, 0.06], leadFoot: [0.42, 0, 0.25], rearFoot: [-0.16, 0, -0.05], kneeAngle: 135, elbowAngle: 122, batAngle: -25, topW: [0.04, 1.06, 0.08], botW: [0.02, 1.08, 0.11] },
      downswing: { hip: [0.14, 0.84, 0.08], leadFoot: [0.42, 0, 0.25], rearFoot: [-0.16, 0, -0.05], kneeAngle: 126, elbowAngle: 138, batAngle: 9, topW: [0.20, 0.86, 0.12], botW: [0.18, 0.78, 0.16] },
      impact: { hip: [0.16, 0.85, 0.09], leadFoot: [0.42, 0, 0.25], rearFoot: [-0.16, 0, -0.05], kneeAngle: 120, rearKneeAngle: 142, elbowAngle: 140, batAngle: 18, topW: [0.30, 0.72, 0.18], botW: [0.28, 0.63, 0.23], torsoLean: 28, torsoRot: 32 },
      follow_through: { hip: [0.18, 0.88, 0.09], leadFoot: [0.42, 0, 0.25], rearFoot: [-0.16, 0, -0.05], kneeAngle: 124, rearKneeAngle: 148, elbowAngle: 155, batAngle: -75, topW: [0.24, 1.28, 0.22], botW: [0.22, 1.36, 0.26], torsoLean: 20, torsoRot: 44 }
    }
  },

  // 3. On Drive
  {
    name: 'On Drive',
    category: 'Drives',
    swingPlane: 'angled_leg',
    ballTraj: { line: 'Middle and Leg', length: 'Full Pitch', pitch: [1.2, 0, -0.15], contact: [0.44, 0.27, -0.16] },
    details: {
      commonMistakes: [
        'Playing around front pad instead of bringing bat down cleanly',
        'Closing bat face prematurely and spooning a leading edge to cover',
        'Front shoulder opening too early losing control of mid-on line'
      ],
      drills: [
        'Mid-on target cone drill emphasizing holding front shoulder closed',
        'Drop ball drill outside leg stump with high vertical finish',
        'Two-tee drill checking straight path inside front pad'
      ]
    },
    cues: {
      stance: 'Well balanced stance, head upright, eyes fixed on delivery stride',
      backlift: 'Vertical backlift with top hand slightly guiding bat face',
      stride: 'Stride slightly across toward mid-on, clearing room inside front pad',
      downswing: 'Swing arc accelerating smoothly down towards mid-on',
      impact: 'Presented full face angled toward mid-on under front eye',
      follow_through: 'Poised high follow-through pointing straight to long-on',
      recovery: 'Step back cleanly into balanced batting base'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.04, 0.90, -0.02], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 165, elbowAngle: 110, batAngle: -52, topW: [-0.06, 1.05, 0.12], botW: [-0.09, 1.11, 0.08], torsoRot: 10 },
      stride: { hip: [0.10, 0.88, -0.04], leadFoot: [0.44, 0, -0.16], rearFoot: [-0.16, 0, -0.04], kneeAngle: 134, elbowAngle: 124, batAngle: -25, topW: [0.04, 1.06, 0.0], botW: [0.02, 1.08, -0.03] },
      downswing: { hip: [0.14, 0.85, -0.05], leadFoot: [0.44, 0, -0.16], rearFoot: [-0.16, 0, -0.04], kneeAngle: 125, elbowAngle: 136, batAngle: 6, topW: [0.20, 0.87, -0.04], botW: [0.18, 0.79, -0.06] },
      impact: { hip: [0.16, 0.86, -0.06], leadFoot: [0.44, 0, -0.16], rearFoot: [-0.16, 0, -0.04], kneeAngle: 120, rearKneeAngle: 144, elbowAngle: 138, batAngle: 14, topW: [0.30, 0.73, -0.08], botW: [0.28, 0.64, -0.10], torsoLean: 25, torsoRot: 26 },
      follow_through: { hip: [0.18, 0.88, -0.06], leadFoot: [0.44, 0, -0.16], rearFoot: [-0.16, 0, -0.04], kneeAngle: 124, rearKneeAngle: 148, elbowAngle: 156, batAngle: -80, topW: [0.28, 1.26, -0.12], botW: [0.26, 1.35, -0.14], torsoLean: 18, torsoRot: 38 }
    }
  },

  // 4. Off Drive
  {
    name: 'Off Drive',
    category: 'Drives',
    swingPlane: 'angled_off',
    ballTraj: { line: 'Off Stump', length: 'Full Pitch', pitch: [1.2, 0, 0.12], contact: [0.46, 0.27, 0.14] },
    details: {
      commonMistakes: [
        'Front toe pointing too straight causing bat to drag wide',
        'Incomplete weight transfer leaving batter off-balance',
        'Top hand loose allowing bottom hand to steer the ball'
      ],
      drills: [
        'Mid-off target corridor boundary scoring drill',
        'Front-foot alignment check with marker chalk',
        'Shadow swings checking full presentation of willow'
      ]
    },
    cues: {
      stance: 'Relaxed balanced stance, eyes level watching bowler hand',
      backlift: 'Vertical backlift with natural wrist cock',
      stride: 'Stride toward mid-off, toe angled slightly to the off side',
      downswing: 'Bat flowing smoothly down the line toward mid-off',
      impact: 'Presented full face squarely toward mid-off under eye line',
      follow_through: 'High upright finish pointing directly towards mid-off',
      recovery: 'Push back into balanced batting stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.04, 0.90, 0.01], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 165, elbowAngle: 110, batAngle: -52, topW: [-0.06, 1.05, 0.14], botW: [-0.09, 1.11, 0.10], torsoRot: 12 },
      stride: { hip: [0.11, 0.88, 0.04], leadFoot: [0.46, 0, 0.14], rearFoot: [-0.16, 0, -0.04], kneeAngle: 133, elbowAngle: 124, batAngle: -25, topW: [0.04, 1.06, 0.05], botW: [0.02, 1.08, 0.02] },
      downswing: { hip: [0.15, 0.85, 0.05], leadFoot: [0.46, 0, 0.14], rearFoot: [-0.16, 0, -0.04], kneeAngle: 125, elbowAngle: 138, batAngle: 7, topW: [0.21, 0.87, 0.08], botW: [0.19, 0.79, 0.06] },
      impact: { hip: [0.17, 0.86, 0.05], leadFoot: [0.46, 0, 0.14], rearFoot: [-0.16, 0, -0.04], kneeAngle: 121, rearKneeAngle: 144, elbowAngle: 142, batAngle: 15, topW: [0.31, 0.73, 0.10], botW: [0.29, 0.64, 0.08], torsoLean: 26, torsoRot: 30 },
      follow_through: { hip: [0.19, 0.88, 0.05], leadFoot: [0.46, 0, 0.14], rearFoot: [-0.16, 0, -0.04], kneeAngle: 123, rearKneeAngle: 149, elbowAngle: 158, batAngle: -82, topW: [0.28, 1.26, 0.14], botW: [0.26, 1.35, 0.12], torsoLean: 19, torsoRot: 40 }
    }
  },

  // 5. Lofted Drive
  {
    name: 'Lofted Drive',
    category: 'Drives',
    swingPlane: 'overhead',
    ballTraj: { line: 'Middle Stump', length: 'Full Toss / Overpitched', pitch: [1.1, 0, 0.0], contact: [0.52, 0.35, 0.04] },
    details: {
      commonMistakes: [
        'Head tilting back too early causing a skier to mid-off',
        'Swinging across the line instead of extending through V',
        'Loss of balance leaving back foot floating off the crease'
      ],
      drills: [
        'Drop ball drill clearing boundary cones on the full',
        'Weighted bat extension drill over front shoulder',
        'Balance board hitting checking solid base on contact'
      ]
    },
    cues: {
      stance: 'Slightly wider aggressive stance, ready to launch through the ball',
      backlift: 'Exaggerated high backlift providing long accelerating pendulum',
      stride: 'Longer assertive stride, body taller, hips preparing to thrust',
      downswing: 'Explosive swing accelerating steeply up through the delivery line',
      impact: 'Struck cleanly on the upswing with full arm extension',
      follow_through: 'Very high majestic follow-through, bat completing over the shoulder',
      recovery: 'Controlled step back to neutral ready stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.20, 0, 0], rearFoot: [-0.18, 0, -0.05], kneeAngle: 160, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.04, 0.90, 0], leadFoot: [0.20, 0, 0], rearFoot: [-0.18, 0, -0.05], kneeAngle: 164, elbowAngle: 115, batAngle: -65, topW: [-0.08, 1.15, 0.14], botW: [-0.12, 1.22, 0.10], torsoRot: 14 },
      stride: { hip: [0.14, 0.89, 0.02], leadFoot: [0.52, 0, 0.05], rearFoot: [-0.18, 0, -0.02], kneeAngle: 130, elbowAngle: 130, batAngle: -35, topW: [0.06, 1.10, 0.04], botW: [0.03, 1.12, 0.01] },
      downswing: { hip: [0.18, 0.87, 0.02], leadFoot: [0.52, 0, 0.05], rearFoot: [-0.18, 0, -0.02], kneeAngle: 128, elbowAngle: 148, batAngle: 15, topW: [0.26, 0.92, 0.04], botW: [0.24, 0.84, 0.02] },
      impact: { hip: [0.22, 0.89, 0.02], leadFoot: [0.52, 0, 0.05], rearFoot: [-0.18, 0, -0.02], kneeAngle: 126, rearKneeAngle: 148, elbowAngle: 155, batAngle: 38, topW: [0.36, 0.84, 0.04], botW: [0.34, 0.75, 0.02], torsoLean: 14, torsoRot: 32 },
      follow_through: { hip: [0.24, 0.92, 0.02], leadFoot: [0.52, 0, 0.05], rearFoot: [-0.18, 0, -0.02], kneeAngle: 132, rearKneeAngle: 155, elbowAngle: 168, batAngle: -110, topW: [0.28, 1.45, 0.04], botW: [0.26, 1.54, 0.02], torsoLean: 8, torsoRot: 48 }
    }
  },

  // 6. Forward Defensive
  {
    name: 'Forward Defensive',
    category: 'Defensive Strokes',
    swingPlane: 'vertical',
    ballTraj: { line: 'Off Stump Channel', length: 'Good Length', pitch: [1.3, 0, 0.08], contact: [0.30, 0.22, 0.06] },
    details: {
      commonMistakes: [
        'Pushing hands hard at the ball instead of absorbing impact softly',
        'Gap between bat and front pad leaving gate open to bowled/LBW',
        'Head falling to off side losing sight of the ball on impact'
      ],
      drills: [
        'Tennis ball soft-hands drill dropping ball within crease rectangle',
        'Bat-pad closeness check with folded towel between thigh and handle',
        'Blindfold reaction sound drill feeling ball contact off the sweet spot'
      ]
    },
    cues: {
      stance: 'Relaxed balanced stance, eyes level, soft hands resting near hip',
      backlift: 'Controlled compact backlift, top hand in total control',
      stride: 'Short soft stride, head leading over ball and front pad',
      downswing: 'Smooth vertical descent with soft relaxed hands',
      impact: 'Dead bat angled downwards, ball smothered directly under eyes',
      follow_through: 'Minimal follow-through, holding textbook defensive pose dead still',
      recovery: 'Push back into balanced batting stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.03, 0.91, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 165, elbowAngle: 108, batAngle: -45, topW: [-0.05, 1.00, 0.12], botW: [-0.08, 1.05, 0.09], torsoRot: 10 },
      stride: { hip: [0.06, 0.89, 0.02], leadFoot: [0.30, 0, 0.04], rearFoot: [-0.16, 0, -0.04], kneeAngle: 140, elbowAngle: 116, batAngle: -20, topW: [0.02, 1.02, 0.03], botW: [0.0, 1.04, 0.01] },
      downswing: { hip: [0.08, 0.87, 0.02], leadFoot: [0.30, 0, 0.04], rearFoot: [-0.16, 0, -0.04], kneeAngle: 134, elbowAngle: 122, batAngle: 2, topW: [0.14, 0.84, 0.04], botW: [0.12, 0.76, 0.02] },
      impact: { hip: [0.09, 0.88, 0.02], leadFoot: [0.30, 0, 0.04], rearFoot: [-0.16, 0, -0.04], kneeAngle: 128, rearKneeAngle: 144, elbowAngle: 125, batAngle: 8, topW: [0.24, 0.68, 0.04], botW: [0.22, 0.59, 0.02], torsoLean: 28, torsoRot: 22 },
      // Soft absorption & check pose: hands cushion the ball, blade angle settles down into turf
      follow_through: { hip: [0.09, 0.88, 0.02], leadFoot: [0.30, 0, 0.04], rearFoot: [-0.16, 0, -0.04], kneeAngle: 128, rearKneeAngle: 144, elbowAngle: 116, batAngle: -4, topW: [0.26, 0.64, 0.04], botW: [0.24, 0.54, 0.02], torsoLean: 25, torsoRot: 25, followWeight: 0.6 }
    }
  },

  // 7. Back-foot Defensive
  {
    name: 'Back-foot Defensive',
    category: 'Defensive Strokes',
    swingPlane: 'vertical',
    ballTraj: { line: 'Off Stump', length: 'Short of a Length', pitch: [1.5, 0, 0.06], contact: [0.05, 0.65, 0.04] },
    details: {
      commonMistakes: [
        'Weight rocking onto heels causing balance to topple backwards',
        'Hands away from body reaching for the ball outside eye-line',
        'Not getting back and across off stump to cover line'
      ],
      drills: [
        'Back-foot drop ball from bounce platform dropping at toes',
        'Crease line backward movement check on rubber matting',
        'Reaction ball wall rebound catching in defensive cup'
      ]
    },
    cues: {
      stance: 'Athletic ready stance, weight primed on balls of feet',
      backlift: 'Vertical backlift with top hand strong and dominant',
      stride: 'Back foot steps back and across off stump, body rising tall and side-on',
      downswing: 'Compact vertical drop of the blade close to the chest',
      impact: 'Soft hands absorbing impact directly under the eyes at chest height',
      follow_through: 'No follow-through, bat absorbed and dead at hip level',
      recovery: 'Step forward back into standard batting stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.08, 0.93, 0.02], leadFoot: [0.10, 0, 0], rearFoot: [-0.22, 0, 0.06], kneeAngle: 164, elbowAngle: 110, batAngle: -45, topW: [-0.10, 1.08, 0.12], botW: [-0.13, 1.14, 0.09], torsoRot: 14 },
      stride: { hip: [-0.12, 0.94, 0.04], leadFoot: [0.02, 0, 0.02], rearFoot: [-0.22, 0, 0.06], kneeAngle: 160, elbowAngle: 112, batAngle: -20, topW: [-0.06, 1.04, 0.06], botW: [-0.08, 1.06, 0.03] },
      downswing: { hip: [-0.12, 0.94, 0.04], leadFoot: [0.02, 0, 0.02], rearFoot: [-0.22, 0, 0.06], kneeAngle: 162, elbowAngle: 110, batAngle: 2, topW: [0.02, 0.90, 0.04], botW: [0.0, 0.82, 0.02] },
      impact: { hip: [-0.12, 0.94, 0.04], leadFoot: [0.02, 0, 0.02], rearFoot: [-0.22, 0, 0.06], kneeAngle: 164, rearKneeAngle: 160, elbowAngle: 105, batAngle: 8, topW: [0.06, 0.82, 0.04], botW: [0.04, 0.73, 0.02], torsoLean: 10, torsoRot: 18 },
      // Soft check & recoil: hands cushion the rising bounce, bat dead under eyes
      follow_through: { hip: [-0.12, 0.94, 0.04], leadFoot: [0.02, 0, 0.02], rearFoot: [-0.22, 0, 0.06], kneeAngle: 164, rearKneeAngle: 160, elbowAngle: 114, batAngle: -4, topW: [0.07, 0.80, 0.04], botW: [0.05, 0.70, 0.02], torsoLean: 8, torsoRot: 20, followWeight: 0.6 }
    }
  },

  // 8. Back-foot Punch
  {
    name: 'Back-foot Punch',
    category: 'Back-foot and Cut Shots',
    swingPlane: 'vertical',
    ballTraj: { line: 'Off Stump / Just Outside', length: 'Short of a Length', pitch: [1.5, 0, 0.12], contact: [0.08, 0.62, 0.08] },
    details: {
      commonMistakes: [
        'Slashing wildly instead of punching through with high front elbow',
        'Not rising onto toes causing hands to hit upward into the air',
        'Bottom hand rolling too early dragging ball into leg side'
      ],
      drills: [
        'Side-arm short ball punch drill between cover and point cones',
        'Step back and across agility ladder footwork drill',
        'Medicine ball chest push developing explosive punch power'
      ]
    },
    cues: {
      stance: 'Poised upright stance, ready to push back onto toes',
      backlift: 'Crisp high backlift giving leverage above ball height',
      stride: 'Back foot steps back and across, body standing tall on ball of foot',
      downswing: 'Short punchy descent with high elevated lead elbow',
      impact: 'Punchy strike at waist level toward cover/point with high elbow',
      follow_through: 'Short crisp finish at chest level, body poised and balanced',
      recovery: 'Step forward back into balanced batting stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.08, 0.94, 0.02], leadFoot: [0.10, 0, 0], rearFoot: [-0.24, 0, 0.08], kneeAngle: 165, elbowAngle: 115, batAngle: -50, topW: [-0.10, 1.12, 0.14], botW: [-0.13, 1.18, 0.10], torsoRot: 16 },
      stride: { hip: [-0.14, 0.95, 0.04], leadFoot: [0.04, 0, 0.02], rearFoot: [-0.24, 0, 0.08], kneeAngle: 162, elbowAngle: 120, batAngle: -22, topW: [-0.04, 1.08, 0.06], botW: [-0.06, 1.10, 0.03] },
      downswing: { hip: [-0.14, 0.95, 0.04], leadFoot: [0.04, 0, 0.02], rearFoot: [-0.24, 0, 0.08], kneeAngle: 160, elbowAngle: 128, batAngle: 6, topW: [0.06, 0.94, 0.06], botW: [0.04, 0.86, 0.04] },
      impact: { hip: [-0.14, 0.95, 0.04], leadFoot: [0.04, 0, 0.02], rearFoot: [-0.24, 0, 0.08], kneeAngle: 158, rearKneeAngle: 162, elbowAngle: 132, batAngle: 16, topW: [0.14, 0.82, 0.08], botW: [0.12, 0.73, 0.06], torsoLean: 12, torsoRot: 24 },
      follow_through: { hip: [-0.14, 0.95, 0.04], leadFoot: [0.04, 0, 0.02], rearFoot: [-0.24, 0, 0.08], kneeAngle: 160, rearKneeAngle: 162, elbowAngle: 140, batAngle: -45, topW: [0.18, 1.05, 0.10], botW: [0.16, 1.12, 0.08], torsoLean: 10, torsoRot: 32 }
    }
  },

  // 9. Square Cut
  {
    name: 'Square Cut',
    category: 'Back-foot and Cut Shots',
    swingPlane: 'horizontal',
    ballTraj: { line: 'Wide Outside Off', length: 'Short of a Length', pitch: [1.5, 0, 0.35], contact: [0.02, 0.70, 0.45] },
    details: {
      commonMistakes: [
        'Cutting balls that are too close to off stump resulting in inside edges',
        'Failing to get on top of the bounce and slicing aerially to gully',
        'Not transferring weight onto back foot across off stump'
      ],
      drills: [
        'Horizontal broomstick chop drill rolling wrists on top of ball',
        'High tee drill positioned 40cm outside off stump cutting downward',
        'Back-foot lateral shuffle drill crossing off-stump guideline'
      ]
    },
    cues: {
      stance: 'Side-on balanced stance, relaxed grip, eyes scanning off side',
      backlift: 'High horizontal cocked backlift behind the head over off stump',
      stride: 'Back foot deep back and across towards off stump, side-on body',
      downswing: 'Horizontal cross-bat descending chop towards backward point',
      impact: 'Purely HORIZONTAL bat across chest, wrists rolling on top',
      follow_through: 'Full horizontal finish across body at shoulder height',
      recovery: 'Push off back foot returning to balanced stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.08, 0.92, 0.06], leadFoot: [0.08, 0, 0.04], rearFoot: [-0.26, 0, 0.18], kneeAngle: 165, elbowAngle: 112, batAngle: -48, topW: [-0.14, 1.18, 0.20], botW: [-0.18, 1.22, 0.26], torsoRot: 22 },
      stride: { hip: [-0.16, 0.92, 0.10], leadFoot: [0.02, 0, 0.05], rearFoot: [-0.26, 0, 0.18], kneeAngle: 162, elbowAngle: 114, batAngle: -15, topW: [-0.08, 1.16, 0.18], botW: [-0.10, 1.16, 0.24] },
      downswing: { hip: [-0.16, 0.91, 0.12], leadFoot: [0.02, 0, 0.05], rearFoot: [-0.26, 0, 0.18], kneeAngle: 162, elbowAngle: 118, batAngle: 45, topW: [0.02, 1.08, 0.20], botW: [0.0, 1.08, 0.26] },
      // HORIZONTAL cross-bat impact out to off-side (+Z)!
      impact: { hip: [-0.16, 0.91, 0.12], leadFoot: [0.02, 0, 0.05], rearFoot: [-0.26, 0, 0.18], kneeAngle: 162, rearKneeAngle: 158, elbowAngle: 120, batAngle: 88, topW: [0.12, 1.05, 0.22], botW: [0.10, 1.05, 0.30], torsoLean: 14, torsoRot: 35 },
      follow_through: { hip: [-0.16, 0.92, 0.12], leadFoot: [0.02, 0, 0.05], rearFoot: [-0.26, 0, 0.18], kneeAngle: 164, rearKneeAngle: 158, elbowAngle: 135, batAngle: 110, topW: [0.08, 0.98, 0.20], botW: [0.06, 0.98, 0.28], torsoLean: 12, torsoRot: 48 }
    }
  },

  // 10. Late Cut
  {
    name: 'Late Cut',
    category: 'Back-foot and Cut Shots',
    swingPlane: 'horizontal',
    ballTraj: { line: 'Just Outside Off Stump', length: 'Short of a Length', pitch: [1.5, 0, 0.18], contact: [-0.04, 0.60, 0.22] },
    details: {
      commonMistakes: [
        'Playing the shot too early in front of the body line',
        'Hard hands deflecting the ball straight into keeper gloves',
        'Not rolling wrists downward toward the turf'
      ],
      drills: [
        'Late contact drill catching/guiding balls past the rear hip',
        'Third man cone placement scoring through the slip corridor',
        'Soft wrist deflection drill using reaction tennis balls'
      ]
    },
    cues: {
      stance: 'Relaxed side-on stance, soft grip, head poised watching line',
      backlift: 'Vertical backlift with delicate relaxed wrists',
      stride: 'Back foot steps back close to off stump, waiting for ball to arrive',
      downswing: 'Delayed descending stroke with feather-soft wrists',
      impact: 'Late contact past the hip, blade open angled down toward third man',
      follow_through: 'Low short finish, wrists rolling over downwards toward the ground',
      recovery: 'Controlled step back to neutral ready stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.08, 0.92, 0.04], leadFoot: [0.06, 0, 0.02], rearFoot: [-0.24, 0, 0.12], kneeAngle: 165, elbowAngle: 110, batAngle: -45, topW: [-0.12, 1.12, 0.20], botW: [-0.15, 1.16, 0.16], torsoRot: 18 },
      stride: { hip: [-0.14, 0.92, 0.06], leadFoot: [-0.02, 0, 0.04], rearFoot: [-0.24, 0, 0.12], kneeAngle: 164, elbowAngle: 112, batAngle: -15, topW: [-0.08, 1.08, 0.14], botW: [-0.10, 1.08, 0.20] },
      downswing: { hip: [-0.14, 0.91, 0.08], leadFoot: [-0.02, 0, 0.04], rearFoot: [-0.24, 0, 0.12], kneeAngle: 164, elbowAngle: 112, batAngle: 30, topW: [-0.02, 0.95, 0.14], botW: [-0.04, 0.92, 0.20] },
      // Late contact past the hip!
      impact: { hip: [-0.14, 0.91, 0.08], leadFoot: [-0.02, 0, 0.04], rearFoot: [-0.24, 0, 0.12], kneeAngle: 164, rearKneeAngle: 160, elbowAngle: 112, batAngle: 58, topW: [0.02, 0.85, 0.16], botW: [0.0, 0.78, 0.24], torsoLean: 15, torsoRot: 28 },
      follow_through: { hip: [-0.14, 0.91, 0.08], leadFoot: [-0.02, 0, 0.04], rearFoot: [-0.24, 0, 0.12], kneeAngle: 164, rearKneeAngle: 160, elbowAngle: 115, batAngle: 75, topW: [0.0, 0.72, 0.14], botW: [-0.02, 0.65, 0.22], torsoLean: 14, torsoRot: 32 }
    }
  },

  // 11. Upper Cut
  {
    name: 'Upper Cut',
    category: 'Back-foot and Cut Shots',
    swingPlane: 'overhead',
    ballTraj: { line: 'Off Stump Bouncer', length: 'Short Pitch Bouncer', pitch: [1.7, 0, 0.15], contact: [0.0, 1.25, 0.18] },
    details: {
      commonMistakes: [
        'Not rising onto toes causing hands to get cramped at eye level',
        'Rolling wrists over instead of allowing the ball to fly upward',
        'Stepping into the line instead of giving room for upward swing'
      ],
      drills: [
        'Bouncer simulation upward guide drill over third man rope',
        'Calf-raise balance drill holding high upward extension',
        'Reaction ball catching above forehead level'
      ]
    },
    cues: {
      stance: 'Tall athletic stance, watching bouncer trajectory intently',
      backlift: 'High cocked backlift, hands rising to chest height',
      stride: 'Back foot back, rising high onto toes to meet the steep bounce',
      downswing: 'Upward ramp-like acceleration under the high bouncer',
      impact: 'Steep upward bat strike lifting ball over point and slips',
      follow_through: 'High lofty finish over off side with arms fully elevated',
      recovery: 'Descend off toes back into balanced batting stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.06, 0.96, 0.02], leadFoot: [0.08, 0, 0.02], rearFoot: [-0.20, 0, 0.06], kneeAngle: 166, elbowAngle: 118, batAngle: -55, topW: [-0.10, 1.22, 0.16], botW: [-0.14, 1.28, 0.12], torsoRot: 16 },
      stride: { hip: [-0.10, 0.98, 0.04], leadFoot: [0.0, 0, 0.04], rearFoot: [-0.20, 0, 0.06], kneeAngle: 166, elbowAngle: 122, batAngle: -35, topW: [-0.04, 1.20, 0.10], botW: [-0.06, 1.22, 0.06] },
      downswing: { hip: [-0.10, 0.98, 0.04], leadFoot: [0.0, 0, 0.04], rearFoot: [-0.20, 0, 0.06], kneeAngle: 165, elbowAngle: 128, batAngle: -15, topW: [0.04, 1.18, 0.10], botW: [0.02, 1.14, 0.06] },
      // Steep rising bat!
      impact: { hip: [-0.10, 0.98, 0.04], leadFoot: [0.0, 0, 0.04], rearFoot: [-0.20, 0, 0.06], kneeAngle: 165, rearKneeAngle: 164, elbowAngle: 135, batAngle: -42, topW: [0.10, 1.15, 0.10], botW: [0.08, 1.08, 0.16], torsoLean: 6, torsoRot: 24 },
      follow_through: { hip: [-0.10, 0.98, 0.04], leadFoot: [0.0, 0, 0.04], rearFoot: [-0.20, 0, 0.06], kneeAngle: 168, rearKneeAngle: 166, elbowAngle: 155, batAngle: -75, topW: [0.14, 1.48, 0.12], botW: [0.12, 1.56, 0.18], torsoLean: 4, torsoRot: 36 }
    }
  },

  // 12. Pull Shot
  {
    name: 'Pull Shot',
    category: 'Short-ball Attacking Shots',
    swingPlane: 'horizontal',
    ballTraj: { line: 'Middle and Leg Bouncer', length: 'Short Pitch Bouncer', pitch: [1.6, 0, -0.10], contact: [0.08, 0.85, -0.22] },
    details: {
      commonMistakes: [
        'Looking away or taking eyes off the ball as it bounces',
        'Hitting on the up and sending an aerial catch to mid-wicket',
        'Not swivelling hips leaving weight stranded on front foot'
      ],
      drills: [
        'Medicine ball rotational throw into wall from back foot',
        'Horizontal tennis ball pull drill rolling wrists on contact',
        'Pivot swivel footwork drill on agility cones'
      ]
    },
    cues: {
      stance: 'Solid balanced base, eyes locked onto bowler release point',
      backlift: 'High horizontal cocked backlift, hips initiating swivel',
      stride: 'Back foot moves back and across to off stump, front foot clearing',
      downswing: 'Powerful horizontal cross-bat swing accelerating to leg side',
      impact: 'Struck well in front of chest, rolling wrists to keep ball down',
      follow_through: 'Full follow-through, bat wrapping around back and rear shoulder',
      recovery: 'Controlled step back to neutral batting stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.06, 0.92, -0.02], leadFoot: [0.14, 0, -0.04], rearFoot: [-0.22, 0, 0.04], kneeAngle: 164, elbowAngle: 115, batAngle: -50, topW: [-0.10, 1.18, 0.12], botW: [-0.14, 1.24, 0.08], torsoRot: 20 },
      stride: { hip: [-0.10, 0.92, -0.04], leadFoot: [0.08, 0, -0.14], rearFoot: [-0.22, 0, 0.04], kneeAngle: 156, elbowAngle: 122, batAngle: -10, topW: [-0.02, 1.15, -0.02], botW: [-0.04, 1.16, -0.06] },
      downswing: { hip: [-0.10, 0.92, -0.04], leadFoot: [0.08, 0, -0.14], rearFoot: [-0.22, 0, 0.04], kneeAngle: 154, elbowAngle: 130, batAngle: 45, topW: [0.12, 1.08, -0.10], botW: [0.10, 1.08, -0.14] },
      // Pure HORIZONTAL cross-bat impact at chest level!
      impact: { hip: [-0.10, 0.92, -0.04], leadFoot: [0.08, 0, -0.14], rearFoot: [-0.22, 0, 0.04], kneeAngle: 146, rearKneeAngle: 155, elbowAngle: 136, batAngle: 86, topW: [0.22, 1.02, -0.15], botW: [0.18, 1.02, -0.19], torsoLean: 14, torsoRot: 38 },
      follow_through: { hip: [-0.08, 0.94, -0.04], leadFoot: [0.08, 0, -0.14], rearFoot: [-0.22, 0, 0.04], kneeAngle: 150, rearKneeAngle: 158, elbowAngle: 150, batAngle: 150, topW: [0.10, 0.98, -0.25], botW: [0.06, 0.98, -0.28], torsoLean: 10, torsoRot: 58 }
    }
  },

  // 13. Hook Shot
  {
    name: 'Hook Shot',
    category: 'Short-ball Attacking Shots',
    swingPlane: 'horizontal',
    ballTraj: { line: 'Leg Stump / Head Height', length: 'Bouncer', pitch: [1.6, 0, -0.15], contact: [0.04, 1.35, -0.20] },
    details: {
      commonMistakes: [
        'Closing eyes or flinching on the head-high bouncer',
        'Top-edging to fine leg by getting underneath the bounce',
        'Feet tangled up without completing the pivot swivel'
      ],
      drills: [
        'Tennis ball head-height swivel hook drill with helmet',
        'Overhead medicine ball rotational toss',
        'Back-foot pivot rotation drill checking full hip clearance'
      ]
    },
    cues: {
      stance: 'Sharp athletic stance, ready to swivel quickly onto back foot',
      backlift: 'High elevated backlift primed at shoulder height',
      stride: 'Back foot pivots on toe, torso rotating aggressively to leg side',
      downswing: 'Horizontal sweep of the blade at head height',
      impact: 'Crisp horizontal strike at eye/helmet height, rolling wrists',
      follow_through: 'Violent rotational finish completing high over front shoulder',
      recovery: 'Step back into balanced ready stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.06, 0.93, -0.02], leadFoot: [0.12, 0, -0.04], rearFoot: [-0.20, 0, 0.02], kneeAngle: 164, elbowAngle: 120, batAngle: -55, topW: [-0.10, 1.25, 0.12], botW: [-0.14, 1.30, 0.08], torsoRot: 22 },
      stride: { hip: [-0.10, 0.94, -0.04], leadFoot: [0.04, 0, -0.16], rearFoot: [-0.20, 0, 0.02], kneeAngle: 158, elbowAngle: 125, batAngle: -10, topW: [-0.02, 1.25, -0.04], botW: [-0.04, 1.26, -0.08] },
      downswing: { hip: [-0.10, 0.94, -0.04], leadFoot: [0.04, 0, -0.16], rearFoot: [-0.20, 0, 0.02], kneeAngle: 156, elbowAngle: 135, batAngle: 45, topW: [0.12, 1.20, -0.12], botW: [0.10, 1.20, -0.16] },
      // Head/throat-high bouncer hook: tall posture, wrists rolled high over bounce
      impact: { hip: [-0.10, 0.96, -0.04], leadFoot: [0.04, 0, -0.16], rearFoot: [-0.20, 0, 0.02], kneeAngle: 160, rearKneeAngle: 164, elbowAngle: 148, batAngle: 106, topW: [0.20, 1.34, -0.16], botW: [0.16, 1.34, -0.20], torsoLean: 4, torsoRot: 58 },
      follow_through: { hip: [-0.08, 0.96, -0.04], leadFoot: [0.04, 0, -0.16], rearFoot: [-0.20, 0, 0.02], kneeAngle: 162, rearKneeAngle: 165, elbowAngle: 158, batAngle: 165, topW: [0.08, 1.28, -0.28], botW: [0.04, 1.28, -0.32], torsoLean: 4, torsoRot: 74 }
    }
  },

  // 14. Flick Shot
  {
    name: 'Flick Shot',
    category: 'Leg-side and Wrist-oriented Strokes',
    swingPlane: 'angled_leg',
    ballTraj: { line: 'Middle and Leg Stump', length: 'Full Pitch', pitch: [1.2, 0, -0.12], contact: [0.38, 0.32, -0.12] },
    details: {
      commonMistakes: [
        'Closing bat face too early leading to a leading edge to cover',
        'Falling over to the off side losing sight of the ball',
        'Not getting weight transferred firmly onto the front foot'
      ],
      drills: [
        'Wrist whip drill using reaction balls flicked between mid-on and mid-wicket',
        'Front-foot balance hold drill maintaining posture after wrist flick',
        'Target gate drill directing flicks between short mid-wicket cones'
      ]
    },
    cues: {
      stance: 'Relaxed stance, eyes level watching ball release',
      backlift: 'Vertical backlift with relaxed wrists ready to whip',
      stride: 'Front foot strides across the line, weight transferring forward',
      downswing: 'Bat descends down the line before wrists initiate whip',
      impact: 'Sharp wrist turn closing bat face smoothly toward mid-wicket',
      follow_through: 'Flowing leg-side finish, bat wrapping across front pad',
      recovery: 'Push off front foot back into balanced batting stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.03, 0.91, -0.02], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 165, elbowAngle: 110, batAngle: -50, topW: [-0.05, 1.05, 0.12], botW: [-0.08, 1.10, 0.08], torsoRot: 10 },
      stride: { hip: [0.10, 0.88, -0.04], leadFoot: [0.40, 0, -0.14], rearFoot: [-0.16, 0, -0.04], kneeAngle: 135, elbowAngle: 122, batAngle: -22, topW: [0.04, 1.04, 0.0], botW: [0.02, 1.06, -0.03] },
      downswing: { hip: [0.14, 0.86, -0.05], leadFoot: [0.40, 0, -0.14], rearFoot: [-0.16, 0, -0.04], kneeAngle: 128, elbowAngle: 128, batAngle: 6, topW: [0.18, 0.88, -0.04], botW: [0.16, 0.80, -0.06] },
      impact: { hip: [0.16, 0.86, -0.06], leadFoot: [0.40, 0, -0.14], rearFoot: [-0.16, 0, -0.04], kneeAngle: 118, rearKneeAngle: 145, elbowAngle: 122, batAngle: 28, topW: [0.28, 0.74, -0.08], botW: [0.26, 0.65, -0.10], torsoLean: 24, torsoRot: 36 },
      follow_through: { hip: [0.18, 0.88, -0.06], leadFoot: [0.40, 0, -0.14], rearFoot: [-0.16, 0, -0.04], kneeAngle: 128, rearKneeAngle: 148, elbowAngle: 145, batAngle: -65, topW: [0.25, 1.18, -0.14], botW: [0.23, 1.26, -0.16], torsoLean: 18, torsoRot: 42 }
    }
  },

  // 15. Leg Glance
  {
    name: 'Leg Glance',
    category: 'Leg-side and Wrist-oriented Strokes',
    swingPlane: 'angled_leg',
    ballTraj: { line: 'Leg Stump / Down Leg', length: 'Full / Good Length', pitch: [1.3, 0, -0.15], contact: [0.26, 0.35, -0.10] },
    details: {
      commonMistakes: [
        'Playing around front pad instead of bringing bat down inside pad line',
        'Hitting too hard instead of letting bowler pace do the work',
        'Closing bat face too violently spooning catch to leg slip'
      ],
      drills: [
        'Fine leg deflection drill with speed-gun tennis deliveries',
        'Pad-line clearance drill guiding ball softly past wicketkeeper',
        'Soft wrist roll progression on low bounce balls'
      ]
    },
    cues: {
      stance: 'Side-on balanced stance, relaxed wrists, watching leg-line delivery',
      backlift: 'Vertical relaxed backlift, top hand in firm guiding control',
      stride: 'Front foot steps across the line of off stump, opening leg-side angle',
      downswing: 'Soft vertical descent with gentle relaxed forearms',
      impact: 'Delicate deflection off the angled face toward fine leg',
      follow_through: 'Short wrists-led follow-through, holding textbook balance',
      recovery: 'Push back into balanced batting stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.03, 0.91, -0.02], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 165, elbowAngle: 108, batAngle: -45, topW: [-0.05, 1.02, 0.12], botW: [-0.08, 1.07, 0.08], torsoRot: 8 },
      stride: { hip: [0.06, 0.89, -0.02], leadFoot: [0.28, 0, -0.10], rearFoot: [-0.16, 0, -0.04], kneeAngle: 142, elbowAngle: 116, batAngle: -18, topW: [0.02, 1.02, 0.0], botW: [0.0, 1.04, -0.02] },
      downswing: { hip: [0.08, 0.88, -0.03], leadFoot: [0.28, 0, -0.10], rearFoot: [-0.16, 0, -0.04], kneeAngle: 138, elbowAngle: 118, batAngle: 4, topW: [0.12, 0.88, -0.02], botW: [0.10, 0.80, -0.04] },
      impact: { hip: [0.10, 0.88, -0.04], leadFoot: [0.28, 0, -0.10], rearFoot: [-0.16, 0, -0.04], kneeAngle: 136, rearKneeAngle: 148, elbowAngle: 120, batAngle: 12, topW: [0.20, 0.78, -0.05], botW: [0.18, 0.69, -0.07], torsoLean: 20, torsoRot: 22 },
      follow_through: { hip: [0.11, 0.89, -0.04], leadFoot: [0.28, 0, -0.10], rearFoot: [-0.16, 0, -0.04], kneeAngle: 138, rearKneeAngle: 150, elbowAngle: 128, batAngle: -35, topW: [0.18, 0.98, -0.08], botW: [0.16, 1.05, -0.10], torsoLean: 16, torsoRot: 28, followWeight: 0.7 }
    }
  },

  // 16. Clip Shot
  {
    name: 'Clip Shot',
    category: 'Leg-side and Wrist-oriented Strokes',
    swingPlane: 'angled_leg',
    ballTraj: { line: 'Middle and Leg', length: 'Full Length', pitch: [1.2, 0, -0.10], contact: [0.35, 0.30, -0.10] },
    details: {
      commonMistakes: [
        'Over-rotation of torso dragging ball aerially to deep mid-wicket',
        'Head failing to commit over the pitch of the ball',
        'Front knee locked rigid restricting wrist whip'
      ],
      drills: [
        'Clip and hold drill hitting along ground past mid-wicket cone',
        'Drop ball drill outside front toe whipping through crease',
        'Single-leg balance drill finishing high on toes'
      ]
    },
    cues: {
      stance: 'Relaxed stance, watching ball release, hands soft near hip',
      backlift: 'Vertical backlift with high front elbow control',
      stride: 'Stride firmly toward pitch of the ball on middle/leg stump',
      downswing: 'Wrists accelerate smoothly downward through delivery line',
      impact: 'Sharp wrist whip at knee height across delivery line',
      follow_through: 'Flowing follow-through across body toward mid-wicket',
      recovery: 'Push firmly off front foot returning to ready base'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.03, 0.91, -0.02], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 165, elbowAngle: 110, batAngle: -50, topW: [-0.05, 1.05, 0.12], botW: [-0.08, 1.10, 0.08], torsoRot: 10 },
      stride: { hip: [-0.06, 0.93, -0.02], leadFoot: [0.12, 0, -0.05], rearFoot: [-0.18, 0, 0.02], kneeAngle: 155, elbowAngle: 112, batAngle: -15, topW: [-0.02, 0.98, 0.0], botW: [-0.04, 1.02, -0.02] },
      downswing: { hip: [-0.06, 0.93, -0.02], leadFoot: [0.12, 0, -0.05], rearFoot: [-0.18, 0, 0.02], kneeAngle: 154, elbowAngle: 116, batAngle: 3, topW: [0.06, 0.88, -0.02], botW: [0.04, 0.80, -0.04] },
      impact: { hip: [-0.06, 0.93, -0.02], leadFoot: [0.12, 0, -0.05], rearFoot: [-0.18, 0, 0.02], kneeAngle: 154, rearKneeAngle: 158, elbowAngle: 118, batAngle: 8, topW: [0.10, 0.82, -0.04], botW: [0.08, 0.74, -0.06], torsoLean: 12, torsoRot: 18 },
      follow_through: { hip: [-0.05, 0.94, -0.02], leadFoot: [0.12, 0, -0.05], rearFoot: [-0.18, 0, 0.02], kneeAngle: 156, rearKneeAngle: 160, elbowAngle: 126, batAngle: -45, topW: [0.08, 1.05, -0.08], botW: [0.06, 1.12, -0.10], torsoLean: 10, torsoRot: 25 }
    }
  },

  // 17. Sweep
  {
    name: 'Sweep',
    category: 'Sweep-family Strokes',
    swingPlane: 'horizontal',
    ballTraj: { line: 'Middle and Leg / Full', length: 'Full Pitch / Yorker', pitch: [1.1, 0, -0.10], contact: [0.55, 0.22, -0.25] },
    details: {
      commonMistakes: [
        'Top-edging high into the air by failing to roll wrists over the ball',
        'Not getting rear knee all the way down on the ground, losing balance',
        'Reaching too far in front instead of striking under the nose'
      ],
      drills: [
        'Kneeling tennis ball sweep drill rolling blade along grass',
        'Target zone sweep drill aiming between square leg and fine leg',
        'Lead shoulder dip drill maintaining head directly over front knee'
      ]
    },
    cues: {
      stance: 'Balanced ready base, eyes focused, anticipating full delivery',
      backlift: 'High horizontal backlift cocked back behind shoulders',
      stride: 'BIG STRIDE: Lead foot forward, REAR KNEE KNEELING ON TURF',
      downswing: 'Blade descending low, skimming horizontally near turf surface',
      impact: 'Horizontal contact struck in front of lead pad under nose',
      follow_through: 'Full horizontal sweep finishing high over leg-side shoulder',
      recovery: 'Push firmly off front foot, rising from knee to ready stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.04, 0.90, -0.02], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 165, elbowAngle: 110, batAngle: -50, topW: [-0.06, 1.05, 0.12], botW: [-0.09, 1.11, 0.08], torsoRot: 14 },
      // Kneeling stride!
      stride: { hip: [0.15, 0.60, -0.02], leadFoot: [0.56, 0, -0.08], rearFoot: [-0.20, 0, 0], kneeAngle: 110, elbowAngle: 116, batAngle: -25, topW: [0.08, 0.72, -0.02], botW: [0.06, 0.73, -0.05], isKneeling: true },
      downswing: { hip: [0.20, 0.48, -0.02], leadFoot: [0.56, 0, -0.08], rearFoot: [-0.20, 0, 0], kneeAngle: 96, elbowAngle: 122, batAngle: 45, topW: [0.24, 0.46, -0.08], botW: [0.22, 0.42, -0.12], isKneeling: true },
      // REAR KNEE ON GROUND! Horizontal sweep skimming turf surface
      impact: { hip: [0.22, 0.46, -0.02], leadFoot: [0.56, 0, -0.08], rearFoot: [-0.20, 0, 0], kneeAngle: 90, rearKneeAngle: 50, elbowAngle: 130, batAngle: 88, topW: [0.36, 0.26, -0.12], botW: [0.34, 0.20, -0.18], torsoLean: 36, torsoRot: 40, isKneeling: true },
      follow_through: { hip: [0.24, 0.50, -0.02], leadFoot: [0.56, 0, -0.08], rearFoot: [-0.20, 0, 0], kneeAngle: 92, rearKneeAngle: 52, elbowAngle: 142, batAngle: 140, topW: [0.18, 0.55, -0.25], botW: [0.14, 0.55, -0.29], torsoLean: 32, torsoRot: 58, isKneeling: true }
    }
  },

  // 18. Slog Sweep
  {
    name: 'Slog Sweep',
    category: 'Sweep-family Strokes',
    swingPlane: 'overhead',
    ballTraj: { line: 'Middle Stump', length: 'Full Pitch / Slot', pitch: [1.1, 0, -0.05], contact: [0.54, 0.30, -0.15] },
    details: {
      commonMistakes: [
        'Loss of shape caused by violent wild swinging',
        'Head lifting up before ball makes contact with sweet spot',
        'Swinging across the line too early hitting down his own throat'
      ],
      drills: [
        'Cow corner boundary clearance drop drill with weighted ball',
        'Stable knee base medicine ball rotational throw',
        'Two-knee stability drill finishing with high bat aloft'
      ]
    },
    cues: {
      stance: 'Aggressive balanced base, preparing explosive knee drop',
      backlift: 'Massive elevated backlift giving maximum swing radius',
      stride: 'Assertive stride onto knee, setting stable launching platform',
      downswing: 'Explosive upward swing arc accelerating towards cow corner',
      impact: 'Powerful strike underneath ball, launching high over mid-wicket',
      follow_through: 'Full violent rotation, bat completing high above shoulders',
      recovery: 'Controlled push off front foot back to neutral stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.04, 0.90, -0.02], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 165, elbowAngle: 115, batAngle: -60, topW: [-0.08, 1.15, 0.12], botW: [-0.12, 1.22, 0.08], torsoRot: 16 },
      stride: { hip: [0.15, 0.68, -0.02], leadFoot: [0.56, 0, -0.06], rearFoot: [-0.20, 0, 0], kneeAngle: 118, elbowAngle: 120, batAngle: -30, topW: [0.08, 0.88, 0.0], botW: [0.06, 0.90, -0.03], isKneeling: true },
      downswing: { hip: [0.20, 0.52, -0.02], leadFoot: [0.56, 0, -0.06], rearFoot: [-0.20, 0, 0], kneeAngle: 105, elbowAngle: 135, batAngle: 30, topW: [0.22, 0.68, -0.06], botW: [0.20, 0.68, -0.10], isKneeling: true },
      impact: { hip: [0.24, 0.52, -0.02], leadFoot: [0.56, 0, -0.06], rearFoot: [-0.20, 0, 0], kneeAngle: 98, rearKneeAngle: 58, elbowAngle: 145, batAngle: 65, topW: [0.34, 0.55, -0.10], botW: [0.30, 0.55, -0.14], torsoLean: 26, torsoRot: 45, isKneeling: true },
      follow_through: { hip: [0.26, 0.55, -0.02], leadFoot: [0.56, 0, -0.06], rearFoot: [-0.20, 0, 0], kneeAngle: 102, rearKneeAngle: 60, elbowAngle: 160, batAngle: -105, topW: [0.25, 1.25, -0.18], botW: [0.22, 1.34, -0.22], torsoLean: 18, torsoRot: 65, isKneeling: true }
    }
  },

  // 19. Reverse Sweep
  {
    name: 'Reverse Sweep',
    category: 'Sweep-family Strokes',
    swingPlane: 'horizontal',
    ballTraj: { line: 'Leg Stump / Outside Leg', length: 'Full Pitch', pitch: [1.1, 0, -0.12], contact: [0.52, 0.24, 0.15] },
    details: {
      commonMistakes: [
        'Failing to switch hand dominance cleanly on handle',
        'Hitting ball while falling backwards off the knee',
        'Gloves exposed to rising deliveries resulting in catch to slips'
      ],
      drills: [
        'Stationary grip-switch kneeling drill guiding balls past point',
        'Reaction tee drill with switched hands striking off-side cone',
        'Paddle-to-reverse alternate sweep transition drill'
      ]
    },
    cues: {
      stance: 'Alert ready stance, preparing rapid grip switch and knee drop',
      backlift: 'HANDS SWITCH: Rear hand grips top, lead hand takes bottom grip',
      stride: 'Down on knee, body crouched low, blade presented to off side',
      downswing: 'Horizontal sweep directed into the off side toward third man',
      impact: 'Inverted horizontal bat face striking ball to third man/point',
      follow_through: 'Flowing reverse finish accelerating high toward backward point',
      recovery: 'Switch grip back to orthodox, rising from knee to stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      // Hands switch in backlift!
      backlift: { hip: [-0.04, 0.90, 0.02], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 165, elbowAngle: 110, batAngle: 50, topW: [-0.04, 1.05, 0.10], botW: [-0.07, 1.10, 0.14], torsoRot: -14, isSwitch: true },
      stride: { hip: [0.15, 0.68, 0.04], leadFoot: [0.52, 0, 0.10], rearFoot: [-0.20, 0, 0], kneeAngle: 115, elbowAngle: 116, batAngle: 25, topW: [0.08, 0.85, 0.05], botW: [0.06, 0.86, 0.08], isKneeling: true, isSwitch: true },
      downswing: { hip: [0.18, 0.50, 0.06], leadFoot: [0.52, 0, 0.10], rearFoot: [-0.20, 0, 0], kneeAngle: 100, elbowAngle: 120, batAngle: -45, topW: [0.20, 0.62, 0.10], botW: [0.18, 0.62, 0.14], isKneeling: true, isSwitch: true },
      // Switched hands striking off side!
      impact: { hip: [0.20, 0.48, 0.08], leadFoot: [0.52, 0, 0.10], rearFoot: [-0.20, 0, 0], kneeAngle: 98, rearKneeAngle: 55, elbowAngle: 120, batAngle: -84, topW: [0.30, 0.46, 0.14], botW: [0.26, 0.46, 0.18], torsoLean: 32, torsoRot: -35, isKneeling: true, isSwitch: true },
      follow_through: { hip: [0.22, 0.52, 0.08], leadFoot: [0.52, 0, 0.10], rearFoot: [-0.20, 0, 0], kneeAngle: 102, rearKneeAngle: 58, elbowAngle: 135, batAngle: -130, topW: [0.18, 0.75, 0.24], botW: [0.14, 0.75, 0.28], torsoLean: 28, torsoRot: -50, isKneeling: true, isSwitch: true }
    }
  },

  // 20. Paddle Sweep
  {
    name: 'Paddle Sweep',
    category: 'Sweep-family Strokes',
    swingPlane: 'horizontal',
    ballTraj: { line: 'Leg Stump / Down Leg', length: 'Full Length', pitch: [1.2, 0, -0.15], contact: [0.54, 0.24, -0.18] },
    details: {
      commonMistakes: [
        'Swinging too hard instead of delicately paddling with soft wrists',
        'Not reaching far enough in front to meet ball before it breaks',
        'Body falling backwards losing control of contact height'
      ],
      drills: [
        'Fine leg bucket collection drill paddling balls into bucket',
        'Delicate soft-touch paddle drill with tennis balls',
        'Knee balance paddle hold drill checking still head'
      ]
    },
    cues: {
      stance: 'Relaxed balanced stance, eyes tracking delivery trajectory',
      backlift: 'Low compact horizontal backlift, soft wrists ready to paddle',
      stride: 'Stride long onto knee, getting down low beneath the ball line',
      downswing: 'Soft gentle sweep across the delivery line',
      impact: 'Delicate paddle brush off the blade face toward fine leg',
      follow_through: 'Gentle, short follow-through, bat resting softly low',
      recovery: 'Push off front foot, rising from knee back to stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.04, 0.90, -0.02], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 165, elbowAngle: 108, batAngle: -45, topW: [-0.06, 1.02, 0.10], botW: [-0.09, 1.08, 0.06], torsoRot: 12 },
      stride: { hip: [0.15, 0.65, -0.03], leadFoot: [0.54, 0, -0.12], rearFoot: [-0.20, 0, 0], kneeAngle: 112, elbowAngle: 114, batAngle: -20, topW: [0.08, 0.82, -0.02], botW: [0.06, 0.83, -0.05], isKneeling: true },
      downswing: { hip: [0.20, 0.48, -0.04], leadFoot: [0.54, 0, -0.12], rearFoot: [-0.20, 0, 0], kneeAngle: 98, elbowAngle: 118, batAngle: 35, topW: [0.18, 0.58, -0.06], botW: [0.16, 0.58, -0.10], isKneeling: true },
      impact: { hip: [0.22, 0.46, -0.05], leadFoot: [0.54, 0, -0.12], rearFoot: [-0.20, 0, 0], kneeAngle: 96, rearKneeAngle: 54, elbowAngle: 118, batAngle: 72, topW: [0.28, 0.42, -0.12], botW: [0.24, 0.42, -0.16], torsoLean: 38, torsoRot: 32, isKneeling: true },
      follow_through: { hip: [0.23, 0.48, -0.05], leadFoot: [0.54, 0, -0.12], rearFoot: [-0.20, 0, 0], kneeAngle: 98, rearKneeAngle: 55, elbowAngle: 124, batAngle: 95, topW: [0.20, 0.60, -0.18], botW: [0.16, 0.60, -0.22], torsoLean: 35, torsoRot: 40, isKneeling: true, followWeight: 0.7 }
    }
  },

  // 21. Slog
  {
    name: 'Slog',
    category: 'Power and Innovative Shots',
    swingPlane: 'overhead',
    ballTraj: { line: 'Middle Stump', length: 'Full / Slot', pitch: [1.1, 0, -0.05], contact: [0.36, 0.35, -0.25] },
    details: {
      commonMistakes: [
        'Swinging across the line too early losing connection with ball',
        'Head pulling off the line of delivery, slicing the ball aerially',
        'Locked front leg stopping fluid hips rotational release'
      ],
      drills: [
        'Rotational medicine ball launch drill into boundary nets',
        'Full toss power striking drill clearing cow corner boundary',
        'Front-foot clearing step drill on agility markers'
      ]
    },
    cues: {
      stance: 'Wide athletic power base, ready to clear front leg and launch',
      backlift: 'High violent backlift cocked high above rear shoulder',
      stride: 'Wide aggressive stride clearing front leg to open up hips',
      downswing: 'Massive upward swing arc accelerating violently to leg side',
      impact: 'Heavy brutal impact launching ball high toward mid-wicket boundary',
      follow_through: 'Full follow-through with torso rotating 360° through the ball',
      recovery: 'Controlled step back to neutral ready stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.20, 0, 0], rearFoot: [-0.18, 0, -0.05], kneeAngle: 160, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.04, 0.90, -0.04], leadFoot: [0.20, 0, 0], rearFoot: [-0.18, 0, -0.05], kneeAngle: 164, elbowAngle: 118, batAngle: -65, topW: [-0.08, 1.20, 0.14], botW: [-0.12, 1.26, 0.10], torsoRot: 22 },
      stride: { hip: [0.12, 0.88, -0.10], leadFoot: [0.44, 0, -0.28], rearFoot: [-0.18, 0, -0.02], kneeAngle: 138, elbowAngle: 125, batAngle: -35, topW: [0.04, 1.12, -0.02], botW: [0.02, 1.14, -0.06] },
      downswing: { hip: [0.16, 0.86, -0.12], leadFoot: [0.44, 0, -0.28], rearFoot: [-0.18, 0, -0.02], kneeAngle: 134, elbowAngle: 138, batAngle: 25, topW: [0.18, 0.92, -0.08], botW: [0.16, 0.90, -0.12] },
      impact: { hip: [0.18, 0.87, -0.14], leadFoot: [0.44, 0, -0.28], rearFoot: [-0.18, 0, -0.02], kneeAngle: 132, rearKneeAngle: 148, elbowAngle: 145, batAngle: 75, topW: [0.28, 0.80, -0.15], botW: [0.24, 0.78, -0.20], torsoLean: 16, torsoRot: 55 },
      follow_through: { hip: [0.20, 0.90, -0.14], leadFoot: [0.44, 0, -0.28], rearFoot: [-0.18, 0, -0.02], kneeAngle: 138, rearKneeAngle: 155, elbowAngle: 165, batAngle: -115, topW: [0.18, 1.40, -0.22], botW: [0.14, 1.48, -0.26], torsoLean: 10, torsoRot: 80 }
    }
  },

  // 22. Switch Hit
  {
    name: 'Switch Hit',
    category: 'Power and Innovative Shots',
    swingPlane: 'angled_off',
    ballTraj: { line: 'Middle Stump', length: 'Full / Slot', pitch: [1.1, 0, 0.0], contact: [0.42, 0.32, 0.28] },
    details: {
      commonMistakes: [
        'Delayed foot transition leaving batter locked in no-man stance',
        'Loss of balance during the handedness pivot before ball arrives',
        'Over-swinging with non-dominant arm losing control of blade'
      ],
      drills: [
        'Mirror stance transition agility drill switching feet on delivery stride',
        'Non-dominant arm tee striking drill building muscle memory',
        'Switch-hit balance hold progression checking head alignment'
      ]
    },
    cues: {
      stance: 'STANCE REVERSES: Batter pivots completely to opposite handedness',
      backlift: 'Mirrored high backlift prepared in new dominant stance',
      stride: 'Front foot strides aggressively into the off-side line in new orientation',
      downswing: 'Fluid swing accelerating through the line with switched dominance',
      impact: 'Clean strike through covers in mirrored orientation',
      follow_through: 'High glorious mirrored follow-through holding textbook balance',
      recovery: 'Pivot smoothly back into original orthodox batting stance'
    },
    kinematics: {
      // Mirrored stance from the start!
      stance: { hip: [0, 0.92, 0], leadFoot: [-0.18, 0, 0], rearFoot: [0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: -18, topW: [-0.04, 0.82, 0.02], botW: [-0.01, 0.76, 0.01], isSwitch: true },
      backlift: { hip: [0.04, 0.90, 0.02], leadFoot: [-0.18, 0, 0], rearFoot: [0.16, 0, -0.05], kneeAngle: 165, elbowAngle: 110, batAngle: 50, topW: [0.06, 1.05, 0.16], botW: [0.09, 1.11, 0.12], torsoRot: -15, isSwitch: true },
      stride: { hip: [0.10, 0.88, 0.06], leadFoot: [0.42, 0, 0.25], rearFoot: [-0.16, 0, -0.05], kneeAngle: 135, elbowAngle: 122, batAngle: 25, topW: [0.04, 1.06, 0.08], botW: [0.02, 1.08, 0.05], isSwitch: true },
      downswing: { hip: [0.14, 0.84, 0.08], leadFoot: [0.42, 0, 0.25], rearFoot: [-0.16, 0, -0.05], kneeAngle: 126, elbowAngle: 138, batAngle: -9, topW: [0.20, 0.86, 0.12], botW: [0.18, 0.78, 0.10], isSwitch: true },
      impact: { hip: [0.16, 0.85, 0.09], leadFoot: [0.42, 0, 0.25], rearFoot: [-0.16, 0, -0.05], kneeAngle: 122, rearKneeAngle: 142, elbowAngle: 138, batAngle: 20, topW: [0.30, 0.72, 0.18], botW: [0.28, 0.63, 0.15], torsoLean: 26, torsoRot: -32, isSwitch: true },
      follow_through: { hip: [0.18, 0.88, 0.09], leadFoot: [0.42, 0, 0.25], rearFoot: [-0.16, 0, -0.05], kneeAngle: 126, rearKneeAngle: 148, elbowAngle: 155, batAngle: 75, topW: [0.24, 1.28, 0.25], botW: [0.22, 1.36, 0.22], torsoLean: 18, torsoRot: -44, isSwitch: true }
    }
  },

  // 23. Scoop Shot
  {
    name: 'Scoop Shot',
    category: 'Power and Innovative Shots',
    swingPlane: 'ramp',
    ballTraj: { line: 'Middle / Leg Yorker', length: 'Full Yorker', pitch: [1.0, 0, 0.0], contact: [0.44, 0.18, 0.02] },
    details: {
      commonMistakes: [
        'Getting head trapped in line of ball, risking serious facial injury',
        'Not crouching low enough to get underneath the yorker trajectory',
        'Blade face too vertical causing ball to deflect down into wickets'
      ],
      drills: [
        'Foam ball scoop ramp drill deflecting ball over wicketkeeper net',
        'Deep crouch squat stability drill holding low foundation',
        'Underneath bat-face angle check using slow reaction feeds'
      ]
    },
    cues: {
      stance: 'Low athletic stance, ready to step across and crouch deep',
      backlift: 'Bat held low and ready, stepping across towards off stump',
      stride: 'VERY LOW CROUCH: Stepping across, hips dropping low to turf',
      downswing: 'Bat scooping directly underneath the delivery line',
      impact: 'Bat angled backward/upward under ball, lifting over keeper',
      follow_through: 'High finish behind head, bat pointing directly over wicketkeeper',
      recovery: 'Push out of deep crouch back into balanced ready stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.04, 0.85, 0.02], leadFoot: [0.20, 0, 0.02], rearFoot: [-0.14, 0, -0.04], kneeAngle: 150, elbowAngle: 105, batAngle: -35, topW: [-0.04, 0.95, 0.08], botW: [-0.07, 1.00, 0.05], torsoRot: 10 },
      // Deep crouch!
      stride: { hip: [0.12, 0.52, 0.04], leadFoot: [0.44, 0, 0.04], rearFoot: [-0.05, 0, 0.04], kneeAngle: 95, elbowAngle: 110, batAngle: 15, topW: [0.14, 0.65, 0.04], botW: [0.12, 0.68, 0.02] },
      downswing: { hip: [0.14, 0.44, 0.04], leadFoot: [0.44, 0, 0.04], rearFoot: [-0.05, 0, 0.04], kneeAngle: 88, elbowAngle: 120, batAngle: 65, topW: [0.24, 0.48, 0.04], botW: [0.22, 0.46, 0.02] },
      // Bat scooping backward/upward!
      impact: { hip: [0.15, 0.42, 0.04], leadFoot: [0.44, 0, 0.04], rearFoot: [-0.05, 0, 0.04], kneeAngle: 84, rearKneeAngle: 80, elbowAngle: 130, batAngle: 118, topW: [0.32, 0.38, 0.04], botW: [0.30, 0.34, 0.02], torsoLean: 42, torsoRot: 20 },
      follow_through: { hip: [0.16, 0.46, 0.04], leadFoot: [0.44, 0, 0.04], rearFoot: [-0.05, 0, 0.04], kneeAngle: 90, rearKneeAngle: 85, elbowAngle: 145, batAngle: 160, topW: [0.26, 0.85, 0.04], botW: [0.22, 0.88, 0.02], torsoLean: 35, torsoRot: 25 }
    }
  },

  // 24. Ramp Shot
  {
    name: 'Ramp Shot',
    category: 'Power and Innovative Shots',
    swingPlane: 'ramp',
    ballTraj: { line: 'Outside Off Bouncer', length: 'Bouncer / Short', pitch: [1.6, 0, 0.15], contact: [0.28, 0.72, 0.14] },
    details: {
      commonMistakes: [
        'Attempting to hit too hard instead of using the bowler pace',
        'Not stepping inside the line, getting cramped by the rising delivery',
        'Blade angle too flat hitting ball straight back into the turf'
      ],
      drills: [
        'Short-pitch pace ramp drill guiding balls over fine leg/keeper netting',
        'Inside-out footwork step drill clearing line of off stump',
        'Blade face angle calibration drill on reaction bowling feeds'
      ]
    },
    cues: {
      stance: 'Athletic mobile stance, watching bowler pace and short pitch',
      backlift: 'Compact backlift ready to step inside and elevate blade',
      stride: 'Crouched low, stepping inside line to use bowler pace',
      downswing: 'Blade lifts up like a ramp positioned above delivery path',
      impact: 'Delicate deflection off angled face lifting ball over keeper head',
      follow_through: 'High finish holding the angled ramp blade aloft over head',
      recovery: 'Step back to neutral balanced batting stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.04, 0.88, 0.04], leadFoot: [0.14, 0, 0.06], rearFoot: [-0.14, 0, -0.02], kneeAngle: 155, elbowAngle: 110, batAngle: -30, topW: [-0.04, 1.05, 0.10], botW: [-0.07, 1.10, 0.06], torsoRot: 14 },
      stride: { hip: [0.06, 0.65, 0.08], leadFoot: [0.30, 0, 0.14], rearFoot: [-0.10, 0, 0.02], kneeAngle: 125, elbowAngle: 116, batAngle: 10, topW: [0.08, 0.88, 0.08], botW: [0.06, 0.86, 0.05] },
      downswing: { hip: [0.08, 0.58, 0.08], leadFoot: [0.30, 0, 0.14], rearFoot: [-0.10, 0, 0.02], kneeAngle: 116, elbowAngle: 120, batAngle: 45, topW: [0.14, 0.82, 0.10], botW: [0.12, 0.78, 0.07] },
      impact: { hip: [0.10, 0.56, 0.08], leadFoot: [0.30, 0, 0.14], rearFoot: [-0.10, 0, 0.02], kneeAngle: 110, rearKneeAngle: 115, elbowAngle: 122, batAngle: 82, topW: [0.22, 0.76, 0.12], botW: [0.20, 0.70, 0.09], torsoLean: 26, torsoRot: 22 },
      follow_through: { hip: [0.12, 0.60, 0.08], leadFoot: [0.30, 0, 0.14], rearFoot: [-0.10, 0, 0.02], kneeAngle: 118, rearKneeAngle: 122, elbowAngle: 135, batAngle: 115, topW: [0.20, 1.12, 0.14], botW: [0.16, 1.16, 0.10], torsoLean: 20, torsoRot: 26 }
    }
  },

  // 25. Helicopter Shot
  {
    name: 'Helicopter Shot',
    category: 'Power and Innovative Shots',
    swingPlane: 'overhead',
    ballTraj: { line: 'Middle and Leg Yorker', length: 'Toe-Crushing Yorker', pitch: [0.9, 0, -0.06], contact: [0.44, 0.16, -0.06] },
    details: {
      commonMistakes: [
        'Failure to dig out yorker on toes resulting in clean-bowled dismissal',
        'Premature wrist snap losing leverage through the ball',
        'Torso falling forward off balance onto the pitch'
      ],
      drills: [
        'Toe-crushing yorker dig-out drill with weighted rubber ball',
        'Full 360-degree overhead bat rotation wrist mobility drill',
        'Wide stance stability balance drill with resistance band'
      ]
    },
    cues: {
      stance: 'Deep wide stance back in crease, bottom hand primed for wrist snap',
      backlift: 'Vertical backlift with strong bottom-hand tension',
      stride: 'Firm stride opening stance, eyes locked on yorker trajectory',
      downswing: 'Explosive downward dig followed by ferocious bottom-hand whip',
      impact: 'Dug out right off the toes, bottom hand snapping violently through',
      follow_through: 'Full 360-degree overhead helicopter rotation of bat and body',
      recovery: 'Controlled step back into balanced batting stance'
    },
    kinematics: {
      stance: { hip: [0, 0.92, 0], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 162, elbowAngle: 100, batAngle: 18, topW: [0.04, 0.82, 0.02], botW: [0.01, 0.76, 0.01] },
      backlift: { hip: [-0.04, 0.90, -0.02], leadFoot: [0.18, 0, 0], rearFoot: [-0.16, 0, -0.05], kneeAngle: 165, elbowAngle: 115, batAngle: -55, topW: [-0.06, 1.10, 0.12], botW: [-0.09, 1.16, 0.08], torsoRot: 14 },
      stride: { hip: [0.10, 0.85, -0.04], leadFoot: [0.46, 0, -0.08], rearFoot: [-0.16, 0, 0], kneeAngle: 126, elbowAngle: 125, batAngle: -25, topW: [0.06, 1.02, 0.0], botW: [0.04, 1.04, -0.03] },
      downswing: { hip: [0.14, 0.80, -0.04], leadFoot: [0.46, 0, -0.08], rearFoot: [-0.16, 0, 0], kneeAngle: 118, elbowAngle: 135, batAngle: 8, topW: [0.22, 0.78, -0.04], botW: [0.20, 0.70, -0.06] },
      impact: { hip: [0.16, 0.81, -0.05], leadFoot: [0.46, 0, -0.08], rearFoot: [-0.16, 0, 0], kneeAngle: 112, rearKneeAngle: 138, elbowAngle: 148, batAngle: 24, topW: [0.32, 0.62, -0.06], botW: [0.30, 0.52, -0.08], torsoLean: 30, torsoRot: 36 },
      // Helicopter 360 rotation overhead!
      follow_through: { hip: [0.18, 0.85, -0.05], leadFoot: [0.46, 0, -0.08], rearFoot: [-0.16, 0, 0], kneeAngle: 118, rearKneeAngle: 145, elbowAngle: 165, batAngle: -135, topW: [0.15, 1.45, -0.15], botW: [0.10, 1.52, -0.18], torsoLean: 14, torsoRot: 85 }
    }
  }
];

// Helper to build keyframe objects from kinematics definition
function buildPhasesForShot(cfg) {
  const k = cfg.kinematics;
  const cues = cfg.cues;
  const plane = cfg.swingPlane;

  // Stance
  const stBat = getBatAndGrip(k.stance.topW, k.stance.botW, 0.88, k.stance.batAngle);
  const stKeyframe = {
    phaseKey: 'stance',
    label: '1. Stance',
    durationWeight: 1.0,
    cue: cues.stance,
    techniquePoints: [
      `Balanced foundation aligned for ${plane} stroke`,
      `Lead knee flexion: ${k.stance.kneeAngle}°`,
      'Hands resting together on handle'
    ],
    head: { x: r(k.stance.hip[0] + 0.08), y: r(k.stance.hip[1] + 0.66), z: r(k.stance.hip[2]), tiltDeg: 4, overFrontKnee: false },
    torso: { leanDeg: 14, sideLeanDeg: 0, rotationDeg: k.stance.isSwitch ? -15 : 0, hip: r3(k.stance.hip), chest: [r(k.stance.hip[0] + 0.06), r(k.stance.hip[1] + 0.40), r(k.stance.hip[2])] },
    leadLeg: { hipAngleDeg: 100, kneeAngleDeg: k.stance.kneeAngle, ankleAngleDeg: 84, kneePos: [r(k.stance.leadFoot[0] - 0.04), r(k.stance.hip[1] * 0.5), r(k.stance.leadFoot[2])], footPos: r3(k.stance.leadFoot), isKneeling: false },
    rearLeg: { hipAngleDeg: 100, kneeAngleDeg: 160, ankleAngleDeg: 84, kneePos: [r(k.stance.rearFoot[0] + 0.04), r(k.stance.hip[1] * 0.5), r(k.stance.rearFoot[2])], footPos: r3(k.stance.rearFoot), isKneeling: false },
    leadArm: { shoulderPos: [r(k.stance.hip[0] + 0.09), r(k.stance.hip[1] + 0.42), r(k.stance.hip[2] + 0.18)], elbowPos: [r(k.stance.hip[0] + 0.14), r(k.stance.hip[1] + 0.20), r(k.stance.hip[2] + 0.14)], elbowAngleDeg: k.stance.elbowAngle, wristPos: stBat.topW },
    rearArm: { shoulderPos: [r(k.stance.hip[0] + 0.02), r(k.stance.hip[1] + 0.42), r(k.stance.hip[2] - 0.18)], elbowPos: [r(k.stance.hip[0] - 0.03), r(k.stance.hip[1] + 0.12), r(k.stance.hip[2] - 0.14)], elbowAngleDeg: 105, wristPos: stBat.botW },
    bat: { angleDeg: k.stance.batAngle, bladeFaceDeg: -10, handlePos: stBat.handlePos, tipPos: stBat.tipPos, swingPlane: plane }
  };

  // Backlift
  const blBat = getBatAndGrip(k.backlift.topW, k.backlift.botW, 0.88, k.backlift.batAngle);
  const blKeyframe = {
    phaseKey: 'backlift',
    label: '2. Backlift',
    durationWeight: 0.9,
    cue: cues.backlift,
    techniquePoints: [
      `Top hand controls backlift height on ${plane} plane`,
      'Stationary head tracking bowler release point',
      `Wrist cock angled at ${k.backlift.batAngle}°`
    ],
    head: { x: r(k.backlift.hip[0] + 0.08), y: r(k.backlift.hip[1] + 0.66), z: r(k.backlift.hip[2]), tiltDeg: 5, overFrontKnee: false },
    torso: { leanDeg: 16, sideLeanDeg: 0, rotationDeg: k.backlift.torsoRot || 12, hip: r3(k.backlift.hip), chest: [r(k.backlift.hip[0] + 0.05), r(k.backlift.hip[1] + 0.40), r(k.backlift.hip[2])] },
    leadLeg: { hipAngleDeg: 102, kneeAngleDeg: k.backlift.kneeAngle, ankleAngleDeg: 84, kneePos: [r(k.backlift.leadFoot[0] - 0.03), r(k.backlift.hip[1] * 0.5), r(k.backlift.leadFoot[2])], footPos: r3(k.backlift.leadFoot), isKneeling: false },
    rearLeg: { hipAngleDeg: 102, kneeAngleDeg: 160, ankleAngleDeg: 84, kneePos: [r(k.backlift.rearFoot[0] + 0.05), r(k.backlift.hip[1] * 0.5), r(k.backlift.rearFoot[2])], footPos: r3(k.backlift.rearFoot), isKneeling: false },
    leadArm: { shoulderPos: [r(k.backlift.hip[0] + 0.08), r(k.backlift.hip[1] + 0.42), r(k.backlift.hip[2] + 0.18)], elbowPos: [r(k.backlift.hip[0] + 0.04), r(k.backlift.hip[1] + 0.22), r(k.backlift.hip[2] + 0.18)], elbowAngleDeg: k.backlift.elbowAngle, wristPos: blBat.topW },
    rearArm: { shoulderPos: [r(k.backlift.hip[0]), r(k.backlift.hip[1] + 0.42), r(k.backlift.hip[2] - 0.18)], elbowPos: [r(k.backlift.hip[0] - 0.08), r(k.backlift.hip[1] + 0.20), r(k.backlift.hip[2] - 0.10)], elbowAngleDeg: 125, wristPos: blBat.botW },
    bat: { angleDeg: k.backlift.batAngle, bladeFaceDeg: -25, handlePos: blBat.handlePos, tipPos: blBat.tipPos, swingPlane: plane }
  };

  // Stride
  const strBat = getBatAndGrip(k.stride.topW, k.stride.botW, 0.88, k.stride.batAngle);
  const strKeyframe = {
    phaseKey: 'stride',
    label: '3. Stride',
    durationWeight: 0.8,
    cue: cues.stride,
    techniquePoints: [
      `Footwork base established: [${k.stride.leadFoot[0]}, ${k.stride.leadFoot[2]}]`,
      `Front knee flexes to ${k.stride.kneeAngle}°`,
      'Head initiates movement toward pitch'
    ],
    head: { x: r(k.stride.hip[0] + 0.12), y: r(k.stride.hip[1] + 0.62), z: r(k.stride.hip[2]), tiltDeg: 6, overFrontKnee: true },
    torso: { leanDeg: 20, sideLeanDeg: 0, rotationDeg: 15, hip: r3(k.stride.hip), chest: [r(k.stride.hip[0] + 0.08), r(k.stride.hip[1] + 0.38), r(k.stride.hip[2])] },
    leadLeg: { hipAngleDeg: 110, kneeAngleDeg: k.stride.kneeAngle, ankleAngleDeg: 88, kneePos: [r(k.stride.leadFoot[0] - 0.04), r(k.stride.isKneeling ? 0.26 : k.stride.hip[1] * 0.45), r(k.stride.leadFoot[2])], footPos: r3(k.stride.leadFoot), isKneeling: false },
    rearLeg: { hipAngleDeg: 105, kneeAngleDeg: k.stride.isKneeling ? 65 : 150, ankleAngleDeg: 84, kneePos: [r(k.stride.rearFoot[0] + (k.stride.isKneeling ? 0.08 : 0.05)), r(k.stride.isKneeling ? 0.06 : k.stride.hip[1] * 0.45), r(k.stride.rearFoot[2])], footPos: r3(k.stride.rearFoot), isKneeling: !!k.stride.isKneeling },
    leadArm: { shoulderPos: [r(k.stride.hip[0] + 0.10), r(k.stride.hip[1] + 0.42), r(k.stride.hip[2] + 0.16)], elbowPos: [r(k.stride.hip[0] + 0.12), r(k.stride.hip[1] + 0.22), r(k.stride.hip[2] + 0.12)], elbowAngleDeg: k.stride.elbowAngle, wristPos: strBat.topW },
    rearArm: { shoulderPos: [r(k.stride.hip[0]), r(k.stride.hip[1] + 0.42), r(k.stride.hip[2] - 0.16)], elbowPos: [r(k.stride.hip[0] - 0.06), r(k.stride.hip[1] + 0.20), r(k.stride.hip[2] - 0.10)], elbowAngleDeg: 120, wristPos: strBat.botW },
    bat: { angleDeg: k.stride.batAngle, bladeFaceDeg: -15, handlePos: strBat.handlePos, tipPos: strBat.tipPos, swingPlane: plane }
  };

  // Downswing
  const dwnBat = getBatAndGrip(k.downswing.topW, k.downswing.botW, 0.88, k.downswing.batAngle);
  const dwnKeyframe = {
    phaseKey: 'downswing',
    label: '4. Downswing',
    durationWeight: 0.5,
    cue: cues.downswing,
    techniquePoints: [
      `Acceleration along ${plane} swing plane`,
      'Leading elbow guiding the path',
      'Weight committed through the line of the stroke'
    ],
    head: { x: r(k.downswing.hip[0] + 0.14), y: r(k.downswing.hip[1] + 0.60), z: r(k.downswing.hip[2]), tiltDeg: 8, overFrontKnee: true },
    torso: { leanDeg: 24, sideLeanDeg: 0, rotationDeg: 22, hip: r3(k.downswing.hip), chest: [r(k.downswing.hip[0] + 0.10), r(k.downswing.hip[1] + 0.36), r(k.downswing.hip[2])] },
    leadLeg: { hipAngleDeg: 115, kneeAngleDeg: k.downswing.kneeAngle, ankleAngleDeg: 90, kneePos: [r(k.downswing.leadFoot[0] - 0.04), r(k.downswing.isKneeling ? 0.26 : k.downswing.hip[1] * 0.42), r(k.downswing.leadFoot[2])], footPos: r3(k.downswing.leadFoot), isKneeling: false },
    rearLeg: { hipAngleDeg: 110, kneeAngleDeg: k.downswing.isKneeling ? 60 : 145, ankleAngleDeg: 86, kneePos: [r(k.downswing.rearFoot[0] + (k.downswing.isKneeling ? 0.08 : 0.06)), r(k.downswing.isKneeling ? 0.06 : k.downswing.hip[1] * 0.42), r(k.downswing.rearFoot[2])], footPos: r3(k.downswing.rearFoot), isKneeling: !!k.downswing.isKneeling },
    leadArm: { shoulderPos: [r(k.downswing.hip[0] + 0.12), r(k.downswing.hip[1] + 0.40), r(k.downswing.hip[2] + 0.16)], elbowPos: [r(k.downswing.hip[0] + 0.16), r(k.downswing.hip[1] + 0.20), r(k.downswing.hip[2] + 0.10)], elbowAngleDeg: k.downswing.elbowAngle, wristPos: dwnBat.topW },
    rearArm: { shoulderPos: [r(k.downswing.hip[0] + 0.02), r(k.downswing.hip[1] + 0.40), r(k.downswing.hip[2] - 0.16)], elbowPos: [r(k.downswing.hip[0] - 0.02), r(k.downswing.hip[1] + 0.18), r(k.downswing.hip[2] - 0.08)], elbowAngleDeg: 130, wristPos: dwnBat.botW },
    bat: { angleDeg: k.downswing.batAngle, bladeFaceDeg: 0, handlePos: dwnBat.handlePos, tipPos: dwnBat.tipPos, swingPlane: plane }
  };

  // Impact
  const impBat = getBatAndGrip(k.impact.topW, k.impact.botW, 0.88, k.impact.batAngle);
  const impKeyframe = {
    phaseKey: 'impact',
    label: '5. Impact',
    durationWeight: 0.35,
    cue: cues.impact,
    techniquePoints: [
      `Lead knee angle: ${k.impact.kneeAngle}°`,
      `Bat plane angle: ${k.impact.batAngle}° (${plane})`,
      `Head position: ${k.impact.leadFoot[0] > 0.3 ? 'Stationed over front knee' : 'Stationed over back foot'}`
    ],
    head: { x: r(k.impact.hip[0] + 0.16), y: r(k.impact.hip[1] + 0.58), z: r(k.impact.hip[2]), tiltDeg: 10, overFrontKnee: true },
    torso: { leanDeg: k.impact.torsoLean || 25, sideLeanDeg: 0, rotationDeg: k.impact.torsoRot || 28, hip: r3(k.impact.hip), chest: [r(k.impact.hip[0] + 0.11), r(k.impact.hip[1] + 0.35), r(k.impact.hip[2])] },
    leadLeg: { hipAngleDeg: 120, kneeAngleDeg: k.impact.kneeAngle, ankleAngleDeg: 92, kneePos: [r(k.impact.leadFoot[0] - 0.03), r(k.impact.isKneeling ? 0.24 : k.impact.hip[1] * 0.40), r(k.impact.leadFoot[2])], footPos: r3(k.impact.leadFoot), isKneeling: false },
    rearLeg: { hipAngleDeg: 115, kneeAngleDeg: k.impact.rearKneeAngle || 140, ankleAngleDeg: 88, kneePos: [r(k.impact.rearFoot[0] + (k.impact.isKneeling ? 0.08 : 0.04)), r(k.impact.isKneeling ? 0.05 : k.impact.hip[1] * 0.40), r(k.impact.rearFoot[2])], footPos: r3(k.impact.rearFoot), isKneeling: !!k.impact.isKneeling },
    leadArm: { shoulderPos: [r(k.impact.hip[0] + 0.14), r(k.impact.hip[1] + 0.38), r(k.impact.hip[2] + 0.16)], elbowPos: [r(k.impact.hip[0] + 0.18), r(k.impact.hip[1] + 0.18), r(k.impact.hip[2] + 0.08)], elbowAngleDeg: k.impact.elbowAngle, wristPos: impBat.topW },
    rearArm: { shoulderPos: [r(k.impact.hip[0] + 0.04), r(k.impact.hip[1] + 0.38), r(k.impact.hip[2] - 0.16)], elbowPos: [r(k.impact.hip[0]), r(k.impact.hip[1] + 0.16), r(k.impact.hip[2] - 0.08)], elbowAngleDeg: 135, wristPos: impBat.botW },
    bat: { angleDeg: k.impact.batAngle, bladeFaceDeg: 0, handlePos: impBat.handlePos, tipPos: impBat.tipPos, swingPlane: plane }
  };

  // Follow-through
  const flwBat = getBatAndGrip(k.follow_through.topW, k.follow_through.botW, 0.88, k.follow_through.batAngle);
  const flwKeyframe = {
    phaseKey: 'follow_through',
    label: '6. Follow-through',
    durationWeight: k.follow_through.followWeight || 0.9,
    cue: cues.follow_through,
    techniquePoints: [
      'Balanced finish holding shape',
      `Arms extended through the finish at ${k.follow_through.batAngle}°`,
      'Weight completely committed to stroke'
    ],
    head: { x: r(k.follow_through.hip[0] + 0.15), y: r(k.follow_through.hip[1] + 0.60), z: r(k.follow_through.hip[2]), tiltDeg: 8, overFrontKnee: true },
    torso: { leanDeg: k.follow_through.torsoLean || 20, sideLeanDeg: 0, rotationDeg: k.follow_through.torsoRot || 40, hip: r3(k.follow_through.hip), chest: [r(k.follow_through.hip[0] + 0.10), r(k.follow_through.hip[1] + 0.36), r(k.follow_through.hip[2])] },
    leadLeg: { hipAngleDeg: 118, kneeAngleDeg: k.follow_through.kneeAngle, ankleAngleDeg: 90, kneePos: [r(k.follow_through.leadFoot[0] - 0.03), r(k.follow_through.isKneeling ? 0.25 : k.follow_through.hip[1] * 0.42), r(k.follow_through.leadFoot[2])], footPos: r3(k.follow_through.leadFoot), isKneeling: false },
    rearLeg: { hipAngleDeg: 112, kneeAngleDeg: k.follow_through.rearKneeAngle || 145, ankleAngleDeg: 86, kneePos: [r(k.follow_through.rearFoot[0] + (k.follow_through.isKneeling ? 0.08 : 0.05)), r(k.follow_through.isKneeling ? 0.05 : k.follow_through.hip[1] * 0.42), r(k.follow_through.rearFoot[2])], footPos: r3(k.follow_through.rearFoot), isKneeling: !!k.follow_through.isKneeling },
    leadArm: { shoulderPos: [r(k.follow_through.hip[0] + 0.12), r(k.follow_through.hip[1] + 0.40), r(k.follow_through.hip[2] + 0.16)], elbowPos: [r(k.follow_through.hip[0] + 0.18), r(k.follow_through.hip[1] + 0.28), r(k.follow_through.hip[2] + 0.08)], elbowAngleDeg: k.follow_through.elbowAngle, wristPos: flwBat.topW },
    rearArm: { shoulderPos: [r(k.follow_through.hip[0] + 0.02), r(k.follow_through.hip[1] + 0.40), r(k.follow_through.hip[2] - 0.16)], elbowPos: [r(k.follow_through.hip[0] + 0.08), r(k.follow_through.hip[1] + 0.25), r(k.follow_through.hip[2] - 0.06)], elbowAngleDeg: 140, wristPos: flwBat.botW },
    bat: { angleDeg: k.follow_through.batAngle, bladeFaceDeg: 0, handlePos: flwBat.handlePos, tipPos: flwBat.tipPos, swingPlane: plane }
  };

  // Recovery
  const recW = [0.08, 0.78, 0.04];
  const recBotW = [0.05, 0.72, 0.02];
  const recBat = getBatAndGrip(recW, recBotW, 0.88, 25);
  const recKeyframe = {
    phaseKey: 'recovery',
    label: '7. Recovery',
    durationWeight: 0.8,
    cue: cues.recovery,
    techniquePoints: [
      'Controlled recoil pushing off the lead foot',
      'Hips and weight re-centering toward crease line',
      'Prepared immediately for following delivery'
    ],
    head: { x: 0.10, y: 1.56, z: 0, tiltDeg: 4, overFrontKnee: false },
    torso: { leanDeg: 14, sideLeanDeg: 0, rotationDeg: 0, hip: [0.05, 0.90, 0], chest: [0.09, 1.30, 0] },
    leadLeg: { hipAngleDeg: 100, kneeAngleDeg: 152, ankleAngleDeg: 84, kneePos: [0.16, 0.45, 0], footPos: [0.26, 0, 0], isKneeling: false },
    rearLeg: { hipAngleDeg: 100, kneeAngleDeg: 158, ankleAngleDeg: 84, kneePos: [-0.10, 0.45, -0.05], footPos: [-0.15, 0, -0.05], isKneeling: false },
    leadArm: { shoulderPos: [0.10, 1.32, 0.18], elbowPos: [0.14, 1.10, 0.14], elbowAngleDeg: 105, wristPos: recBat.topW },
    rearArm: { shoulderPos: [0.02, 1.32, -0.18], elbowPos: [-0.02, 1.02, -0.14], elbowAngleDeg: 110, wristPos: recBat.botW },
    bat: { angleDeg: 25, bladeFaceDeg: 0, handlePos: recBat.handlePos, tipPos: recBat.tipPos, swingPlane: plane }
  };

  return {
    stance: stKeyframe,
    backlift: blKeyframe,
    stride: strKeyframe,
    downswing: dwnKeyframe,
    impact: impKeyframe,
    follow_through: flwKeyframe,
    recovery: recKeyframe
  };
}

// Generate the whole dataset
const fullDataset = {};
for (const cfg of shotsConfig) {
  const phases = buildPhasesForShot(cfg);
  fullDataset[cfg.name] = {
    id: cfg.name.toLowerCase().replace(/[\s-]+/g, '_'),
    name: cfg.name,
    slug: cfg.name.toLowerCase().replace(/[\s_]+/g, '-'),
    category: cfg.category,
    provenance: 'authored baseline (tunable)',
    ballTrajectory: cfg.ballTraj,
    swingPlane: cfg.swingPlane,
    commonMistakes: cfg.details.commonMistakes,
    drills: cfg.details.drills,
    phases: phases
  };
}

fs.writeFileSync(targetJsonPath, JSON.stringify(fullDataset, null, 2), 'utf-8');
console.log(`Successfully generated and wrote all 25 shots to ${targetJsonPath}`);
