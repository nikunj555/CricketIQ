/**
 * CricketIQ Biomechanical Shot Technique Catalog
 * 
 * Authoritative, non-repeating biomechanical definitions for all 25 catalogue cricket shots.
 * Each shot possesses its own distinct backlift, impact, and finish keyframe poses,
 * solved with 2-bone Inverse Kinematics and unwrapped forward bat paths.
 */

export interface HandOffset {
  x: number; // Horizontal offset relative to neck in normalized torso lengths
  y: number; // Vertical offset relative to neck (negative is below neck)
}

export interface ShotKeyframeDef {
  batAngleDeg: number; // Unwrapped degrees (forward swing over shoulder, never through legs)
  hands: HandOffset;
}

export interface ShotImpactDef {
  hipShift: number; // Lateral pelvic translation along X
  strideX: number; // Front-foot stride length along X (positive = forward)
  strideDirDeg: number; // Footwork angle (0 = straight down pitch, +28 = off-side cover, -15 = on-side)
  leadKneeAngle: number; // Front knee flexion angle (180 = straight, 125 = drive, 95 = sweep)
  rearKneeAngle: number; // Back knee flexion angle (155 = upright drive, 76 = kneeling sweep)
  torsoLean: number; // Torso inclination in degrees (positive = leaning forward over ball)
  batAngleDeg: number; // Unwrapped impact blade angle
  hands: HandOffset; // Hand position relative to neck
  shoulderOpeningDeg: number; // Shoulder rotation (0 = side-on, 45-75 = open)
  rearFootMode?: 'planted' | 'drags' | 'back-and-across' | 'kneeling';
}

export interface ShotTechniqueEntry {
  name: string;
  slug: string;
  category: 'Drives' | 'Defense' | 'Back-foot' | 'Leg-side' | 'Sweeps' | 'Innovation';
  intent: string; // One-line coaching intent
  backlift: ShotKeyframeDef;
  impact: ShotImpactDef;
  finish: ShotKeyframeDef;
  isHandsSwitched?: boolean;
}

export const SHOT_TECHNIQUES: Record<string, ShotTechniqueEntry> = {
  // =========================================================================
  // FRONT-FOOT DRIVES
  // =========================================================================
  'Straight Drive': {
    name: 'Straight Drive',
    slug: 'straight-drive',
    category: 'Drives',
    intent: 'Drive straight down the ground past the bowler with a vertical bat, full arm extension, and high hands finish.',
    backlift: {
      batAngleDeg: 228,
      hands: { x: -0.06, y: -0.22 }
    },
    impact: {
      hipShift: 0.16,
      strideX: 0.62,
      strideDirDeg: 0,
      leadKneeAngle: 128,
      rearKneeAngle: 154,
      torsoLean: 22,
      batAngleDeg: 180,
      hands: { x: 0.24, y: -0.36 },
      shoulderOpeningDeg: 12,
      rearFootMode: 'planted'
    },
    finish: {
      batAngleDeg: 102,
      hands: { x: 0.32, y: -0.04 }
    }
  },

  'Cover Drive': {
    name: 'Cover Drive',
    slug: 'cover-drive',
    category: 'Drives',
    intent: 'Stride toward the line of the off-stump, keep shoulders closed, and drive through extra cover with hands high.',
    backlift: {
      batAngleDeg: 234,
      hands: { x: -0.08, y: -0.20 }
    },
    impact: {
      hipShift: 0.18,
      strideX: 0.58,
      strideDirDeg: 28,
      leadKneeAngle: 124,
      rearKneeAngle: 148,
      torsoLean: 24,
      batAngleDeg: 176,
      hands: { x: 0.22, y: -0.34 },
      shoulderOpeningDeg: 22,
      rearFootMode: 'planted'
    },
    finish: {
      batAngleDeg: 114,
      hands: { x: 0.26, y: -0.02 }
    }
  },

  'Off Drive': {
    name: 'Off Drive',
    slug: 'off-drive',
    category: 'Drives',
    intent: 'Drive through mid-off between straight and cover with a vertical blade, elevated front elbow, and high finish.',
    backlift: {
      batAngleDeg: 230,
      hands: { x: -0.07, y: -0.21 }
    },
    impact: {
      hipShift: 0.17,
      strideX: 0.60,
      strideDirDeg: 14,
      leadKneeAngle: 126,
      rearKneeAngle: 150,
      torsoLean: 23,
      batAngleDeg: 178,
      hands: { x: 0.23, y: -0.35 },
      shoulderOpeningDeg: 16,
      rearFootMode: 'planted'
    },
    finish: {
      batAngleDeg: 108,
      hands: { x: 0.29, y: -0.03 }
    }
  },

  'On Drive': {
    name: 'On Drive',
    slug: 'on-drive',
    category: 'Drives',
    intent: 'Open the front hip and shoulder slightly, presenting the full face through mid-on close to the front pad.',
    backlift: {
      batAngleDeg: 222,
      hands: { x: -0.04, y: -0.24 }
    },
    impact: {
      hipShift: 0.14,
      strideX: 0.56,
      strideDirDeg: -12,
      leadKneeAngle: 132,
      rearKneeAngle: 156,
      torsoLean: 20,
      batAngleDeg: 184,
      hands: { x: 0.20, y: -0.37 },
      shoulderOpeningDeg: 42,
      rearFootMode: 'planted'
    },
    finish: {
      batAngleDeg: 122,
      hands: { x: 0.21, y: -0.08 }
    }
  },

  'Lofted Drive': {
    name: 'Lofted Drive',
    slug: 'lofted-drive',
    category: 'Drives',
    intent: 'Clear the infield with a taller base, slight upward bat path through the line, and elevated follow-through.',
    backlift: {
      batAngleDeg: 242,
      hands: { x: -0.10, y: -0.16 }
    },
    impact: {
      hipShift: 0.12,
      strideX: 0.52,
      strideDirDeg: 6,
      leadKneeAngle: 138,
      rearKneeAngle: 152,
      torsoLean: 14,
      batAngleDeg: 164,
      hands: { x: 0.25, y: -0.30 },
      shoulderOpeningDeg: 28,
      rearFootMode: 'planted'
    },
    finish: {
      batAngleDeg: 84,
      hands: { x: 0.36, y: 0.14 }
    }
  },

  // =========================================================================
  // DEFENCE
  // =========================================================================
  'Forward Defensive': {
    name: 'Forward Defensive',
    slug: 'forward-defensive',
    category: 'Defense',
    intent: 'Smother the ball right beside the front pad with soft hands, vertical face, and no follow-through.',
    backlift: {
      batAngleDeg: 216,
      hands: { x: -0.03, y: -0.25 }
    },
    impact: {
      hipShift: 0.15,
      strideX: 0.54,
      strideDirDeg: 0,
      leadKneeAngle: 128,
      rearKneeAngle: 158,
      torsoLean: 25,
      batAngleDeg: 180,
      hands: { x: 0.22, y: -0.38 },
      shoulderOpeningDeg: 6,
      rearFootMode: 'planted'
    },
    finish: {
      batAngleDeg: 178,
      hands: { x: 0.22, y: -0.38 } // Soft hands, no follow-through
    }
  },

  'Back-foot Defensive': {
    name: 'Back-foot Defensive',
    slug: 'back-foot-defensive',
    category: 'Defense',
    intent: 'Press back and across toward off-stump, rise with the bounce, and drop the ball with a high front elbow.',
    backlift: {
      batAngleDeg: 218,
      hands: { x: -0.05, y: -0.22 }
    },
    impact: {
      hipShift: -0.16,
      strideX: -0.14,
      strideDirDeg: 0,
      leadKneeAngle: 162,
      rearKneeAngle: 158,
      torsoLean: 8,
      batAngleDeg: 180,
      hands: { x: -0.02, y: -0.32 },
      shoulderOpeningDeg: 8,
      rearFootMode: 'back-and-across'
    },
    finish: {
      batAngleDeg: 176,
      hands: { x: -0.04, y: -0.34 }
    }
  },

  // =========================================================================
  // BACK-FOOT SHOTS
  // =========================================================================
  'Back-foot Punch': {
    name: 'Back-foot Punch',
    slug: 'back-foot-punch',
    category: 'Back-foot',
    intent: 'Rock back and across, stand tall, and punch crisply through the covers with a compact, short follow-through.',
    backlift: {
      batAngleDeg: 226,
      hands: { x: -0.08, y: -0.18 }
    },
    impact: {
      hipShift: -0.15,
      strideX: -0.12,
      strideDirDeg: 18,
      leadKneeAngle: 158,
      rearKneeAngle: 160,
      torsoLean: 10,
      batAngleDeg: 174,
      hands: { x: 0.08, y: -0.28 },
      shoulderOpeningDeg: 18,
      rearFootMode: 'back-and-across'
    },
    finish: {
      batAngleDeg: 138,
      hands: { x: 0.16, y: -0.18 }
    }
  },

  'Square Cut': {
    name: 'Square Cut',
    slug: 'square-cut',
    category: 'Back-foot',
    intent: 'Move back and across, extend the arms fully, and snap the wrists down on a horizontal bat past point.',
    backlift: {
      batAngleDeg: 245,
      hands: { x: -0.12, y: -0.12 }
    },
    impact: {
      hipShift: -0.18,
      strideX: -0.16,
      strideDirDeg: 35,
      leadKneeAngle: 156,
      rearKneeAngle: 148,
      torsoLean: 12,
      batAngleDeg: 92,
      hands: { x: 0.18, y: -0.26 },
      shoulderOpeningDeg: 24,
      rearFootMode: 'back-and-across'
    },
    finish: {
      batAngleDeg: 46,
      hands: { x: 0.22, y: -0.14 }
    }
  },

  'Late Cut': {
    name: 'Late Cut',
    slug: 'late-cut',
    category: 'Back-foot',
    intent: 'Wait deep in the crease, play late beside the body, and glide the ball fine past third slip with a downward blade.',
    backlift: {
      batAngleDeg: 220,
      hands: { x: -0.06, y: -0.20 }
    },
    impact: {
      hipShift: -0.20,
      strideX: -0.20,
      strideDirDeg: 20,
      leadKneeAngle: 160,
      rearKneeAngle: 152,
      torsoLean: 6,
      batAngleDeg: 146,
      hands: { x: -0.06, y: -0.34 },
      shoulderOpeningDeg: 10,
      rearFootMode: 'back-and-across'
    },
    finish: {
      batAngleDeg: 156,
      hands: { x: -0.08, y: -0.38 }
    }
  },

  'Upper Cut': {
    name: 'Upper Cut',
    slug: 'upper-cut',
    category: 'Back-foot',
    intent: "Stand tall against the short ball, use the bowler's pace, and ramp the blade upward over the slips.",
    backlift: {
      batAngleDeg: 215,
      hands: { x: -0.04, y: -0.18 }
    },
    impact: {
      hipShift: -0.12,
      strideX: -0.10,
      strideDirDeg: 10,
      leadKneeAngle: 164,
      rearKneeAngle: 162,
      torsoLean: 2,
      batAngleDeg: 128,
      hands: { x: 0.08, y: -0.16 },
      shoulderOpeningDeg: 15,
      rearFootMode: 'back-and-across'
    },
    finish: {
      batAngleDeg: 72,
      hands: { x: 0.16, y: 0.06 }
    }
  },

  'Pull Shot': {
    name: 'Pull Shot',
    slug: 'pull-shot',
    category: 'Back-foot',
    intent: 'Shift weight to the back foot, swivel the hips, and roll the wrists on a horizontal bat through mid-wicket.',
    backlift: {
      batAngleDeg: 248,
      hands: { x: -0.14, y: -0.10 }
    },
    impact: {
      hipShift: -0.12,
      strideX: -0.14,
      strideDirDeg: -20,
      leadKneeAngle: 154,
      rearKneeAngle: 146,
      torsoLean: 10,
      batAngleDeg: 96,
      hands: { x: 0.14, y: -0.20 },
      shoulderOpeningDeg: 65,
      rearFootMode: 'back-and-across'
    },
    finish: {
      batAngleDeg: 28,
      hands: { x: -0.12, y: -0.06 }
    }
  },

  'Hook Shot': {
    name: 'Hook Shot',
    slug: 'hook-shot',
    category: 'Back-foot',
    intent: 'Get inside the line of the bouncer, swivel above chest height, and roll the wrists to keep the ball down.',
    backlift: {
      batAngleDeg: 254,
      hands: { x: -0.16, y: -0.06 }
    },
    impact: {
      hipShift: -0.14,
      strideX: -0.16,
      strideDirDeg: -22,
      leadKneeAngle: 152,
      rearKneeAngle: 144,
      torsoLean: 8,
      batAngleDeg: 86,
      hands: { x: 0.10, y: -0.10 }, // Contact at shoulder/chin level
      shoulderOpeningDeg: 75,
      rearFootMode: 'back-and-across'
    },
    finish: {
      batAngleDeg: 22,
      hands: { x: -0.16, y: -0.02 }
    }
  },

  // =========================================================================
  // LEG-SIDE SHOTS
  // =========================================================================
  'Flick Shot': {
    name: 'Flick Shot',
    slug: 'flick-shot',
    category: 'Leg-side',
    intent: 'Stride across to the pitch, present the face, and whip the wrists sharply off the pads through mid-wicket.',
    backlift: {
      batAngleDeg: 224,
      hands: { x: -0.05, y: -0.22 }
    },
    impact: {
      hipShift: 0.13,
      strideX: 0.52,
      strideDirDeg: -16,
      leadKneeAngle: 126,
      rearKneeAngle: 154,
      torsoLean: 18,
      batAngleDeg: 178,
      hands: { x: 0.18, y: -0.38 },
      shoulderOpeningDeg: 35,
      rearFootMode: 'planted'
    },
    finish: {
      batAngleDeg: 124,
      hands: { x: 0.22, y: -0.16 }
    }
  },

  'Leg Glance': {
    name: 'Leg Glance',
    slug: 'leg-glance',
    category: 'Leg-side',
    intent: 'Use soft hands and subtle wrist deflection to guide the ball off the pads fine towards fine leg.',
    backlift: {
      batAngleDeg: 218,
      hands: { x: -0.04, y: -0.24 }
    },
    impact: {
      hipShift: 0.10,
      strideX: 0.44,
      strideDirDeg: -10,
      leadKneeAngle: 136,
      rearKneeAngle: 156,
      torsoLean: 16,
      batAngleDeg: 182,
      hands: { x: 0.14, y: -0.36 },
      shoulderOpeningDeg: 25,
      rearFootMode: 'planted'
    },
    finish: {
      batAngleDeg: 162,
      hands: { x: 0.12, y: -0.35 }
    }
  },

  'Clip Shot': {
    name: 'Clip Shot',
    slug: 'clip-shot',
    category: 'Leg-side',
    intent: 'Step forward across the line and clip the ball through mid-wicket with closed wrists and a fluid follow-through.',
    backlift: {
      batAngleDeg: 226,
      hands: { x: -0.06, y: -0.20 }
    },
    impact: {
      hipShift: 0.12,
      strideX: 0.50,
      strideDirDeg: -18,
      leadKneeAngle: 130,
      rearKneeAngle: 152,
      torsoLean: 19,
      batAngleDeg: 174,
      hands: { x: 0.16, y: -0.34 },
      shoulderOpeningDeg: 40,
      rearFootMode: 'planted'
    },
    finish: {
      batAngleDeg: 116,
      hands: { x: 0.19, y: -0.14 }
    }
  },

  // =========================================================================
  // SWEEPS
  // =========================================================================
  'Sweep': {
    name: 'Sweep',
    slug: 'sweep',
    category: 'Sweeps',
    intent: 'Stride low along the pitch, drop the rear knee to the turf, and sweep horizontally in front of the pad.',
    backlift: {
      batAngleDeg: 240,
      hands: { x: -0.10, y: -0.18 }
    },
    impact: {
      hipShift: 0.22,
      strideX: 0.72,
      strideDirDeg: -5,
      leadKneeAngle: 98,
      rearKneeAngle: 78,
      torsoLean: 32,
      batAngleDeg: 92,
      hands: { x: 0.28, y: -0.52 },
      shoulderOpeningDeg: 38,
      rearFootMode: 'kneeling'
    },
    finish: {
      batAngleDeg: 42,
      hands: { x: 0.32, y: -0.38 }
    }
  },

  'Slog Sweep': {
    name: 'Slog Sweep',
    slug: 'slog-sweep',
    category: 'Sweeps',
    intent: 'Drop onto the rear knee, get under the ball with a powerful heave, and launch it high over deep mid-wicket.',
    backlift: {
      batAngleDeg: 246,
      hands: { x: -0.12, y: -0.12 }
    },
    impact: {
      hipShift: 0.20,
      strideX: 0.70,
      strideDirDeg: -8,
      leadKneeAngle: 102,
      rearKneeAngle: 76,
      torsoLean: 28,
      batAngleDeg: 108,
      hands: { x: 0.26, y: -0.46 },
      shoulderOpeningDeg: 55,
      rearFootMode: 'kneeling'
    },
    finish: {
      batAngleDeg: 58,
      hands: { x: 0.30, y: 0.04 }
    }
  },

  'Reverse Sweep': {
    name: 'Reverse Sweep',
    slug: 'reverse-sweep',
    category: 'Sweeps',
    intent: 'Switch hand positions, drop the rear knee, and sweep backwards past point with the reverse face.',
    backlift: {
      batAngleDeg: 236,
      hands: { x: -0.08, y: -0.16 }
    },
    impact: {
      hipShift: 0.18,
      strideX: 0.68,
      strideDirDeg: 15,
      leadKneeAngle: 100,
      rearKneeAngle: 80,
      torsoLean: 30,
      batAngleDeg: 268, // Reversed face pointing backward
      hands: { x: 0.24, y: -0.50 },
      shoulderOpeningDeg: 30,
      rearFootMode: 'kneeling'
    },
    finish: {
      batAngleDeg: 305,
      hands: { x: 0.18, y: -0.34 }
    },
    isHandsSwitched: true
  },

  'Paddle Sweep': {
    name: 'Paddle Sweep',
    slug: 'paddle-sweep',
    category: 'Sweeps',
    intent: 'Kneel low, reach well forward with soft hands, and paddle the ball fine behind the wicketkeeper.',
    backlift: {
      batAngleDeg: 232,
      hands: { x: -0.06, y: -0.20 }
    },
    impact: {
      hipShift: 0.24,
      strideX: 0.74,
      strideDirDeg: -5,
      leadKneeAngle: 94,
      rearKneeAngle: 75,
      torsoLean: 34,
      batAngleDeg: 134,
      hands: { x: 0.32, y: -0.56 },
      shoulderOpeningDeg: 28,
      rearFootMode: 'kneeling'
    },
    finish: {
      batAngleDeg: 154,
      hands: { x: 0.30, y: -0.50 }
    }
  },

  // =========================================================================
  // POWER & INNOVATION
  // =========================================================================
  'Slog': {
    name: 'Slog',
    slug: 'slog',
    category: 'Innovation',
    intent: 'Clear front leg to open the hips, establish a wide powerful base, and heave across the line to cow corner.',
    backlift: {
      batAngleDeg: 252,
      hands: { x: -0.14, y: -0.10 }
    },
    impact: {
      hipShift: 0.08,
      strideX: 0.48,
      strideDirDeg: -30,
      leadKneeAngle: 135,
      rearKneeAngle: 145,
      torsoLean: 14,
      batAngleDeg: 104,
      hands: { x: 0.18, y: -0.24 },
      shoulderOpeningDeg: 70,
      rearFootMode: 'drags'
    },
    finish: {
      batAngleDeg: 32,
      hands: { x: -0.06, y: 0.02 }
    }
  },

  'Switch Hit': {
    name: 'Switch Hit',
    slug: 'switch-hit',
    category: 'Innovation',
    intent: 'Pivot stance and swap grip completely before delivery to execute an authoritative drive from the opposite stance.',
    backlift: {
      batAngleDeg: 232,
      hands: { x: -0.08, y: -0.18 }
    },
    impact: {
      hipShift: -0.16,
      strideX: 0.58,
      strideDirDeg: -25,
      leadKneeAngle: 126,
      rearKneeAngle: 150,
      torsoLean: 22,
      batAngleDeg: 176,
      hands: { x: -0.22, y: -0.34 },
      shoulderOpeningDeg: 22,
      rearFootMode: 'planted'
    },
    finish: {
      batAngleDeg: 110,
      hands: { x: -0.24, y: -0.04 }
    },
    isHandsSwitched: true
  },

  'Scoop Shot': {
    name: 'Scoop Shot',
    slug: 'scoop-shot',
    category: 'Innovation',
    intent: 'Crouch deep on both knees beneath the bounce, open the face skyward, and scoop over the wicketkeeper.',
    backlift: {
      batAngleDeg: 218,
      hands: { x: -0.06, y: -0.22 }
    },
    impact: {
      hipShift: 0.10,
      strideX: 0.44,
      strideDirDeg: 0,
      leadKneeAngle: 86,
      rearKneeAngle: 80,
      torsoLean: 26,
      batAngleDeg: 142,
      hands: { x: 0.12, y: -0.48 },
      shoulderOpeningDeg: 15,
      rearFootMode: 'kneeling'
    },
    finish: {
      batAngleDeg: 78,
      hands: { x: 0.16, y: -0.14 }
    }
  },

  'Ramp Shot': {
    name: 'Ramp Shot',
    slug: 'ramp-shot',
    category: 'Innovation',
    intent: 'Get inside the line, arch the upper body, and ramp the fast delivery up over the keeper head.',
    backlift: {
      batAngleDeg: 220,
      hands: { x: -0.05, y: -0.20 }
    },
    impact: {
      hipShift: -0.10,
      strideX: -0.10,
      strideDirDeg: 0,
      leadKneeAngle: 155,
      rearKneeAngle: 152,
      torsoLean: 4,
      batAngleDeg: 132,
      hands: { x: 0.08, y: -0.14 },
      shoulderOpeningDeg: 20,
      rearFootMode: 'back-and-across'
    },
    finish: {
      batAngleDeg: 68,
      hands: { x: 0.12, y: 0.12 }
    }
  },

  'Helicopter Shot': {
    name: 'Helicopter Shot',
    slug: 'helicopter-shot',
    category: 'Innovation',
    intent: 'Dig out the yorker with massive bottom-hand wrist snap, finishing with the trademark 360-degree overhead blade rotation.',
    backlift: {
      batAngleDeg: 248,
      hands: { x: -0.12, y: -0.14 }
    },
    impact: {
      hipShift: 0.10,
      strideX: 0.52,
      strideDirDeg: 0,
      leadKneeAngle: 122,
      rearKneeAngle: 148,
      torsoLean: 24,
      batAngleDeg: 172,
      hands: { x: 0.22, y: -0.42 },
      shoulderOpeningDeg: 45,
      rearFootMode: 'drags'
    },
    finish: {
      batAngleDeg: 38, // Unwrapped overhead helicopter rotation
      hands: { x: 0.14, y: 0.18 }
    }
  }
};

/**
 * Normalizes input name or slug to fetch matching authentic technique.
 */
export function getShotTechnique(nameOrSlug?: string | null): ShotTechniqueEntry {
  if (!nameOrSlug) return SHOT_TECHNIQUES['Cover Drive'];
  const raw = nameOrSlug.trim();
  const lower = raw.toLowerCase().replace(/[-_]/g, ' ');

  if (SHOT_TECHNIQUES[raw]) {
    return SHOT_TECHNIQUES[raw];
  }

  for (const [key, tech] of Object.entries(SHOT_TECHNIQUES)) {
    if (
      key.toLowerCase() === lower ||
      tech.slug === raw.toLowerCase().replace(/[\s_]/g, '-') ||
      tech.slug.replace(/-/g, ' ') === lower
    ) {
      return tech;
    }
  }

  for (const [key, tech] of Object.entries(SHOT_TECHNIQUES)) {
    if (key.toLowerCase().includes(lower) || lower.includes(key.toLowerCase())) {
      return tech;
    }
  }

  return SHOT_TECHNIQUES['Cover Drive'];
}

export interface GeneratedKeyframePose {
  hip_x: number;
  hip_y: number;
  lead_stride_x: number;
  lead_stride_dir_deg: number;
  rear_foot_x: number;
  rear_foot_mode: 'planted' | 'drags' | 'back-and-across' | 'kneeling';
  lead_knee_flex: number;
  rear_knee_flex: number;
  lead_elbow_flex: number;
  rear_elbow_flex: number;
  pelvis_rotation_deg: number;
  shoulder_rotation_deg: number;
  head_offset_x: number;
  hands_x: number;
  hands_y: number;
  bat_plane: 'vertical' | 'diagonal' | 'horizontal';
  bat_angle: number;
  bat_tip_x: number;
  bat_tip_y: number;
  wrist_cock_deg: number;
  torso_lean: number;
  shoulder_tilt: number;
  duration_weight: number;
  cue: string;
}

/**
 * Linearly interpolates between two numbers.
 */
function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/**
 * Derives the complete 7-phase biomechanical animation from the authored technique keyframes.
 * Guarantees unwrapped forward bat rotation and joint connectivity.
 */
export function generatePhasesFromTechnique(
  technique: ShotTechniqueEntry
): Record<string, { keyframe_pose: GeneratedKeyframePose }> {
  const { backlift, impact, finish } = technique;
  const isKneeling = impact.rearFootMode === 'kneeling';
  const rearFootX = impact.strideX < 0 ? 0.18 : -0.26;

  // Stance baseline
  const stancePose: GeneratedKeyframePose = {
    hip_x: 0.0,
    hip_y: 0.78,
    lead_stride_x: 0.32,
    lead_stride_dir_deg: 0,
    rear_foot_x: -0.26,
    rear_foot_mode: 'planted',
    lead_knee_flex: 165,
    rear_knee_flex: 163,
    lead_elbow_flex: 105,
    rear_elbow_flex: 95,
    pelvis_rotation_deg: 0,
    shoulder_rotation_deg: 0,
    head_offset_x: 0.02,
    hands_x: 0.02,
    hands_y: 0.36,
    bat_plane: 'vertical',
    bat_angle: 180,
    bat_tip_x: -0.06,
    bat_tip_y: 0.04,
    wrist_cock_deg: 18,
    torso_lean: 11,
    shoulder_tilt: 4,
    duration_weight: 1.0,
    cue: 'Balanced upright stance with relaxed grip and level head station.'
  };

  // 1. Backlift
  const backliftPose: GeneratedKeyframePose = {
    hip_x: impact.hipShift * 0.15,
    hip_y: 0.78,
    lead_stride_x: 0.34,
    lead_stride_dir_deg: 0,
    rear_foot_x: -0.26,
    rear_foot_mode: 'planted',
    lead_knee_flex: 160,
    rear_knee_flex: 158,
    lead_elbow_flex: 115,
    rear_elbow_flex: 88,
    pelvis_rotation_deg: -4,
    shoulder_rotation_deg: -8,
    head_offset_x: 0.02,
    hands_x: backlift.hands.x,
    hands_y: 0.78 + 0.44 + backlift.hands.y,
    bat_plane: backlift.batAngleDeg < 140 ? 'horizontal' : backlift.batAngleDeg < 170 ? 'diagonal' : 'vertical',
    bat_angle: backlift.batAngleDeg,
    bat_tip_x: backlift.hands.x + 0.38 * Math.sin((backlift.batAngleDeg * Math.PI) / 180),
    bat_tip_y: 0.78 + 0.44 + backlift.hands.y - 0.38 * Math.cos((backlift.batAngleDeg * Math.PI) / 180),
    wrist_cock_deg: 26,
    torso_lean: impact.torsoLean * 0.5 + 5,
    shoulder_tilt: 6,
    duration_weight: 1.1,
    cue: 'Cock wrists and elevate blade over rear shoulder into batting channel.'
  };

  // 2. Stride
  const strideT = 0.55;
  const strideKnee = lerp(160, impact.leadKneeAngle, strideT);
  const strideHipY = lerp(0.78, isKneeling ? 0.48 : 0.72, strideT);
  const strideHandsX = lerp(backlift.hands.x, impact.hands.x, 0.30);
  const strideHandsY = lerp(0.78 + 0.44 + backlift.hands.y, strideHipY + 0.44 + impact.hands.y, 0.30);
  const strideBatAngle = lerp(backlift.batAngleDeg, impact.batAngleDeg, 0.20);

  const stridePose: GeneratedKeyframePose = {
    hip_x: impact.hipShift * 0.55,
    hip_y: strideHipY,
    lead_stride_x: impact.strideX * 0.75 + (impact.strideX < 0 ? -0.04 : 0.08),
    lead_stride_dir_deg: impact.strideDirDeg,
    rear_foot_x: rearFootX,
    rear_foot_mode: impact.rearFootMode || 'planted',
    lead_knee_flex: strideKnee,
    rear_knee_flex: lerp(158, impact.rearKneeAngle, strideT),
    lead_elbow_flex: 125,
    rear_elbow_flex: 92,
    pelvis_rotation_deg: impact.shoulderOpeningDeg * 0.25,
    shoulder_rotation_deg: impact.shoulderOpeningDeg * 0.25,
    head_offset_x: lerp(0.02, impact.strideX * 0.2, strideT),
    hands_x: strideHandsX,
    hands_y: strideHandsY,
    bat_plane: strideBatAngle < 130 ? 'horizontal' : strideBatAngle < 165 ? 'diagonal' : 'vertical',
    bat_angle: strideBatAngle,
    bat_tip_x: strideHandsX + 0.38 * Math.sin((strideBatAngle * Math.PI) / 180),
    bat_tip_y: strideHandsY - 0.38 * Math.cos((strideBatAngle * Math.PI) / 180),
    wrist_cock_deg: 24,
    torso_lean: lerp(11, impact.torsoLean, strideT),
    shoulder_tilt: 8,
    duration_weight: 0.95,
    cue: 'Decisive footwork toward pitch of delivery while head remains poised.'
  };

  // 3. Downswing
  const downT = 0.85;
  const downHipY = lerp(0.78, isKneeling ? 0.48 : 0.72, downT);
  const downHandsX = lerp(backlift.hands.x, impact.hands.x, 0.75);
  const downHandsY = lerp(0.78 + 0.44 + backlift.hands.y, downHipY + 0.44 + impact.hands.y, 0.75);
  const downBatAngle = lerp(backlift.batAngleDeg, impact.batAngleDeg, 0.65);

  const downswingPose: GeneratedKeyframePose = {
    hip_x: impact.hipShift * 0.85,
    hip_y: downHipY,
    lead_stride_x: impact.strideX,
    lead_stride_dir_deg: impact.strideDirDeg,
    rear_foot_x: rearFootX,
    rear_foot_mode: impact.rearFootMode || 'planted',
    lead_knee_flex: lerp(160, impact.leadKneeAngle, downT),
    rear_knee_flex: lerp(158, impact.rearKneeAngle, downT),
    lead_elbow_flex: 135,
    rear_elbow_flex: 105,
    pelvis_rotation_deg: impact.shoulderOpeningDeg * 0.70,
    shoulder_rotation_deg: impact.shoulderOpeningDeg * 0.70,
    head_offset_x: impact.strideX * 0.22,
    hands_x: downHandsX,
    hands_y: downHandsY,
    bat_plane: downBatAngle < 130 ? 'horizontal' : downBatAngle < 165 ? 'diagonal' : 'vertical',
    bat_angle: downBatAngle,
    bat_tip_x: downHandsX + 0.38 * Math.sin((downBatAngle * Math.PI) / 180),
    bat_tip_y: downHandsY - 0.38 * Math.cos((downBatAngle * Math.PI) / 180),
    wrist_cock_deg: 20,
    torso_lean: lerp(11, impact.torsoLean, downT),
    shoulder_tilt: 10,
    duration_weight: 0.80,
    cue: 'Accelerate blade through stroke corridor leading with the front elbow.'
  };

  // 4. Impact (exact authored biomechanical keyframe)
  const impactHipY = isKneeling ? 0.46 : lerp(0.82, 0.68, (180 - impact.leadKneeAngle) / 65);
  const impactHandsX = impact.hands.x;
  const impactHandsY = impactHipY + 0.44 + impact.hands.y;
  const impactBatAngle = impact.batAngleDeg;

  const impactPose: GeneratedKeyframePose = {
    hip_x: impact.hipShift,
    hip_y: impactHipY,
    lead_stride_x: impact.strideX,
    lead_stride_dir_deg: impact.strideDirDeg,
    rear_foot_x: rearFootX,
    rear_foot_mode: impact.rearFootMode || 'planted',
    lead_knee_flex: impact.leadKneeAngle,
    rear_knee_flex: impact.rearKneeAngle,
    lead_elbow_flex: 142,
    rear_elbow_flex: 118,
    pelvis_rotation_deg: impact.shoulderOpeningDeg,
    shoulder_rotation_deg: impact.shoulderOpeningDeg,
    head_offset_x: impact.strideX * 0.25,
    hands_x: impactHandsX,
    hands_y: impactHandsY,
    bat_plane: impactBatAngle < 130 ? 'horizontal' : impactBatAngle < 165 ? 'diagonal' : 'vertical',
    bat_angle: impactBatAngle,
    bat_tip_x: impactHandsX + 0.38 * Math.sin((impactBatAngle * Math.PI) / 180),
    bat_tip_y: impactHandsY - 0.38 * Math.cos((impactBatAngle * Math.PI) / 180),
    wrist_cock_deg: 15,
    torso_lean: impact.torsoLean,
    shoulder_tilt: 12,
    duration_weight: 0.85,
    cue: technique.intent
  };

  // 5. Follow-through (Finish)
  const finishHandsX = finish.hands.x;
  const finishHandsY = impactHipY + 0.44 + finish.hands.y;
  const finishBatAngle = finish.batAngleDeg;

  const followThroughPose: GeneratedKeyframePose = {
    hip_x: impact.hipShift * 1.05,
    hip_y: impactHipY,
    lead_stride_x: impact.strideX,
    lead_stride_dir_deg: impact.strideDirDeg,
    rear_foot_x: rearFootX,
    rear_foot_mode: impact.rearFootMode || 'planted',
    lead_knee_flex: impact.leadKneeAngle,
    rear_knee_flex: impact.rearKneeAngle,
    lead_elbow_flex: 148,
    rear_elbow_flex: 125,
    pelvis_rotation_deg: Math.min(85, impact.shoulderOpeningDeg + 18),
    shoulder_rotation_deg: Math.min(85, impact.shoulderOpeningDeg + 18),
    head_offset_x: impact.strideX * 0.24,
    hands_x: finishHandsX,
    hands_y: finishHandsY,
    bat_plane: finishBatAngle < 130 ? 'horizontal' : finishBatAngle < 165 ? 'diagonal' : 'vertical',
    bat_angle: finishBatAngle,
    bat_tip_x: finishHandsX + 0.38 * Math.sin((finishBatAngle * Math.PI) / 180),
    bat_tip_y: finishHandsY - 0.38 * Math.cos((finishBatAngle * Math.PI) / 180),
    wrist_cock_deg: 10,
    torso_lean: impact.torsoLean * 0.88,
    shoulder_tilt: 8,
    duration_weight: 1.15,
    cue: 'Hold balanced stroke completion with high front elbow and firm base.'
  };

  // 6. Recovery
  const recoveryPose: GeneratedKeyframePose = {
    hip_x: impact.hipShift * 0.35,
    hip_y: lerp(impactHipY, 0.78, 0.65),
    lead_stride_x: impact.strideX * 0.45,
    lead_stride_dir_deg: 0,
    rear_foot_x: -0.26,
    rear_foot_mode: 'planted',
    lead_knee_flex: lerp(impact.leadKneeAngle, 165, 0.65),
    rear_knee_flex: lerp(impact.rearKneeAngle, 163, 0.65),
    lead_elbow_flex: 110,
    rear_elbow_flex: 98,
    pelvis_rotation_deg: 6,
    shoulder_rotation_deg: 6,
    head_offset_x: 0.04,
    hands_x: lerp(finish.hands.x, 0.04, 0.60),
    hands_y: lerp(finishHandsY, 0.38, 0.60),
    bat_plane: 'vertical',
    bat_angle: lerp(finish.batAngleDeg, 180, 0.60),
    bat_tip_x: 0.0,
    bat_tip_y: 0.08,
    wrist_cock_deg: 16,
    torso_lean: 12,
    shoulder_tilt: 4,
    duration_weight: 1.0,
    cue: 'Reset back into ready athletic stance prepared for next delivery.'
  };

  return {
    stance: { keyframe_pose: stancePose },
    backlift: { keyframe_pose: backliftPose },
    stride: { keyframe_pose: stridePose },
    downswing: { keyframe_pose: downswingPose },
    impact: { keyframe_pose: impactPose },
    follow_through: { keyframe_pose: followThroughPose },
    recovery: { keyframe_pose: recoveryPose }
  };
}
