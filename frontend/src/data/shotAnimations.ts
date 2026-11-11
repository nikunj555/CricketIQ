/**
 * CricketIQ — Authored 3D Biomechanical Shot Animations
 * Single authoritative source of truth for 3D animation keyframes across all 25 catalogue cricket shots.
 * Provenance: "authored baseline (tunable)".
 * Do not claim measured provenance.
 */

import rawData from './shotAnimations.json';

export type SwingPlaneType =
  | 'vertical'
  | 'horizontal'
  | 'angled_off'
  | 'angled_leg'
  | 'overhead'
  | 'ramp';

export interface BallTrajectoryInfo {
  line: string;
  length: string;
  pitch: [number, number, number];
  contact: [number, number, number];
}

export interface PhaseKeyframe {
  phaseKey: 'stance' | 'backlift' | 'stride' | 'downswing' | 'impact' | 'follow_through' | 'recovery';
  label: string;
  durationWeight: number;
  cue: string;
  techniquePoints: string[];
  head: {
    x: number;
    y: number;
    z: number;
    tiltDeg: number;
    overFrontKnee: boolean;
  };
  torso: {
    leanDeg: number;
    sideLeanDeg: number;
    rotationDeg: number;
    hip: [number, number, number];
    chest: [number, number, number];
  };
  leadLeg: {
    hipAngleDeg: number;
    kneeAngleDeg: number;
    ankleAngleDeg: number;
    kneePos: [number, number, number];
    footPos: [number, number, number];
    isKneeling: boolean;
  };
  rearLeg: {
    hipAngleDeg: number;
    kneeAngleDeg: number;
    ankleAngleDeg: number;
    kneePos: [number, number, number];
    footPos: [number, number, number];
    isKneeling: boolean;
  };
  leadArm: {
    shoulderPos: [number, number, number];
    elbowPos: [number, number, number];
    elbowAngleDeg: number;
    wristPos: [number, number, number];
  };
  rearArm: {
    shoulderPos: [number, number, number];
    elbowPos: [number, number, number];
    elbowAngleDeg: number;
    wristPos: [number, number, number];
  };
  bat: {
    angleDeg: number;
    bladeFaceDeg: number;
    handlePos: [number, number, number];
    tipPos: [number, number, number];
    swingPlane: SwingPlaneType;
  };
}

export interface ShotAnimationDefinition {
  id: string;
  name: string;
  slug: string;
  category: string;
  provenance: string;
  ballTrajectory: BallTrajectoryInfo;
  swingPlane: SwingPlaneType;
  commonMistakes: string[];
  drills: string[];
  phases: Record<string, PhaseKeyframe>;
}

export const SHOT_ANIMATIONS: Record<string, ShotAnimationDefinition> = rawData as unknown as Record<string, ShotAnimationDefinition>;

export function getShotAnimation(idOrName?: string | null): ShotAnimationDefinition | null {
  if (!idOrName) return null;
  const n = idOrName.trim().toLowerCase();

  // Match by exact key name
  for (const [k, v] of Object.entries(SHOT_ANIMATIONS)) {
    if (k.toLowerCase() === n) return v;
  }
  // Match by id or slug
  for (const v of Object.values(SHOT_ANIMATIONS)) {
    if (
      v.id.toLowerCase() === n ||
      v.slug.toLowerCase() === n ||
      v.slug.toLowerCase() === n.replace(/\s+/g, '-') ||
      v.name.toLowerCase() === n
    ) {
      return v;
    }
  }
  // Substring match
  for (const [k, v] of Object.entries(SHOT_ANIMATIONS)) {
    const kLow = k.toLowerCase();
    if (kLow.includes(n) || n.includes(kLow)) return v;
  }
  return null;
}

export function getAllShotAnimations(): ShotAnimationDefinition[] {
  return Object.values(SHOT_ANIMATIONS);
}
