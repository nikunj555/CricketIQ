import { getShotAnimation, ShotAnimationDefinition } from './shotAnimations';
import type { ReferenceShotDefinition } from '../components/RealisticBatterVisualizer';

export interface ShotVariant {
  id: number;
  seed: number;
  tempo: number;
  strideScale: number;
  leanOffset: number;
  followThroughScale: number;
}

// Three deliberately restrained profiles. Geometry is adjusted by small amounts;
// the authored shot path, swing plane and footwork mode remain unchanged.
const SHOT_BOUNDS: Record<string, { stride: number; lean: number; finish: number }> = {};
const lastVariantByShot: Record<string, number> = {};
const variantBagsByShot: Record<string, number[]> = {};
[
  [['Cover Drive', 'Straight Drive', 'On Drive', 'Off Drive', 'Lofted Drive'], 0.04, 2.0, 0.05],
  [['Forward Defensive', 'Back-foot Defensive'], 0.025, 1.0, 0.025],
  [['Back-foot Punch', 'Square Cut', 'Late Cut', 'Upper Cut'], 0.035, 1.5, 0.04],
  [['Pull Shot', 'Hook Shot'], 0.035, 2.0, 0.04],
  [['Flick Shot', 'Leg Glance', 'Clip Shot'], 0.03, 1.5, 0.035],
  [['Sweep', 'Slog Sweep', 'Reverse Sweep', 'Paddle Sweep'], 0.03, 1.5, 0.035],
  [['Slog', 'Switch Hit'], 0.04, 2.0, 0.045],
  [['Scoop Shot', 'Ramp Shot'], 0.025, 1.0, 0.03],
  [['Helicopter Shot'], 0.025, 1.0, 0.03],
].forEach(([names, stride, lean, finish]) => {
  (names as string[]).forEach((name) => { SHOT_BOUNDS[name] = { stride: stride as number, lean: lean as number, finish: finish as number }; });
});

export function createShotVariant(id: number, shotName: string): ShotVariant {
  const shot = getShotAnimation(shotName);
  const seed = ((shot?.id || shotName).split('').reduce((sum, c) => sum + c.charCodeAt(0), id * 7919)) >>> 0;
  const index = ((id % 3) + 3) % 3;
  const bounds = SHOT_BOUNDS[shot?.name || shotName] || { stride: 0.025, lean: 1, finish: 0.025 };
  const signs = [-1, 0, 1];
  const sign = signs[index];
  return {
    id, seed,
    tempo: [0.94, 1, 1.06][index],
    strideScale: 1 + bounds.stride * sign,
    leanOffset: bounds.lean * sign,
    followThroughScale: 1 + bounds.finish * sign,
  };
}

export function getShotVariationBounds(shotName: string): { stride: number; lean: number; finish: number } {
  const canonicalName = getShotAnimation(shotName)?.name || shotName;
  return { ...(SHOT_BOUNDS[canonicalName] || { stride: 0.025, lean: 1, finish: 0.025 }) };
}

export function nextShotVariant(previousId: number, shotName: string): ShotVariant {
  // Per-shot shuffled bag. The previous variant is excluded from each refill.
  const key = (getShotAnimation(shotName)?.name || shotName).toLowerCase();
  const last = lastVariantByShot[key] ?? previousId;
  let bag = variantBagsByShot[key] || [];
  if (bag.length === 0) {
    bag = [0, 1, 2].filter((id) => id !== ((last % 3) + 3) % 3);
    for (let i = bag.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [bag[i], bag[j]] = [bag[j], bag[i]];
    }
  }
  const chosen = bag.shift()!;
  variantBagsByShot[key] = bag;
  lastVariantByShot[key] = chosen;
  return createShotVariant(chosen, shotName);
}

export function varyShotAnimation(animation: ShotAnimationDefinition, variant: ShotVariant): ShotAnimationDefinition {
  const direction = variant.seed % 2 ? 1 : -1;
  const phases = Object.fromEntries(Object.entries(animation.phases).map(([key, phase]) => {
    const isStride = key === 'stride';
    const isSwing = key === 'downswing' || key === 'impact' || key === 'follow_through';
    const scale = isStride ? variant.strideScale : key === 'follow_through' ? variant.followThroughScale : 1;
    const tweak = (p: [number, number, number]): [number, number, number] => [p[0] * scale + (isSwing ? direction * 0.008 : 0), p[1], p[2]];
    return [key, {
      ...phase,
      durationWeight: phase.durationWeight / variant.tempo,
      head: { ...phase.head, x: phase.head.x + (isSwing ? direction * 0.008 : 0) },
      torso: { ...phase.torso, leanDeg: phase.torso.leanDeg + (isSwing ? variant.leanOffset : 0), hip: tweak(phase.torso.hip), chest: tweak(phase.torso.chest) },
      leadLeg: { ...phase.leadLeg, footPos: tweak(phase.leadLeg.footPos), kneePos: tweak(phase.leadLeg.kneePos) },
      bat: { ...phase.bat, tipPos: tweak(phase.bat.tipPos) },
    }];
  }));
  return { ...animation, phases };
}

export function varyReferenceShot(definition: ReferenceShotDefinition, variant: ShotVariant): ReferenceShotDefinition {
  const direction = variant.seed % 2 ? 1 : -1;
  const phases = Object.fromEntries(Object.entries(definition.phases).map(([key, item]) => {
    const pose = item.keyframe_pose;
    const swing = ['downswing', 'impact', 'follow_through'].includes(key);
    return [key, { ...item, keyframe_pose: {
      ...pose,
      lead_stride_x: pose.lead_stride_x * (key === 'stride' ? variant.strideScale : 1),
      head_offset_x: pose.head_offset_x + (swing ? direction * 0.008 : 0),
      torso_lean: pose.torso_lean + (swing ? variant.leanOffset : 0),
      bat_tip_x: pose.bat_tip_x * (key === 'follow_through' ? variant.followThroughScale : 1),
      duration_weight: pose.duration_weight / variant.tempo,
    } }];
  }));
  return { ...definition, phases };
}

