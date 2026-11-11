"""
Generates frontend/src/data/shotAnimations.ts with complete, distinct 3D biomechanical keyframe animations
for all 25 cricket shots in CricketIQ.
Every shot has 7 phases with individual joint angles, foot positions, head positions, bat orientations,
ball trajectories, technical cues, common mistakes, and drills.
Provenance: "authored baseline (tunable)".
"""

import json
from pathlib import Path

# Load definitions
from generate_shot_animations_data import shots_data

def build_phase_keyframe(shot, phase_name, p_idx):
    weights = [1.0, 0.8, 0.85, 0.45, 0.35, 1.15, 0.90]
    weight = weights[p_idx]
    cue = shot["cues"][phase_name]

    # Stance defaults
    st_hip = [0.0, 0.92, 0.0]
    st_lead_foot = [0.20, 0.0, 0.0]
    st_rear_foot = [-0.15, 0.0, -0.05]
    st_bat_handle = [0.02, 0.82, 0.0]
    st_bat_tip = [0.08, 0.12, 0.0]
    st_lead_wrist = [0.04, 0.82, 0.02]
    st_rear_wrist = [0.0, 0.82, -0.02]

    imp_hip = shot["hip"]
    imp_lead_foot = shot["leadStride"]
    imp_rear_foot = shot["rearFoot"]
    imp_handle = shot["handle"]
    imp_tip = shot["batTip"]
    imp_bat_angle = shot["batAngle"]
    imp_lead_knee = shot["leadKnee"]
    imp_rear_knee = shot["rearKnee"]
    imp_lead_elbow = shot["leadElbow"]
    imp_rear_elbow = shot["rearElbow"]
    imp_torso_lean = shot["torsoLean"]
    imp_torso_side = shot["torsoSideLean"]
    imp_torso_rot = shot["torsoRot"]

    ft_bat_angle = shot["ftBatAngle"]
    ft_tip = shot["ftBatTip"]
    is_kneeling = shot["kneeling"]

    # Interpolation factors across 7 phases (0..6)
    if p_idx == 0: # Stance
        hip = st_hip
        lead_foot = st_lead_foot
        rear_foot = st_rear_foot
        lead_knee = 162.0; rear_knee = 160.0
        lead_elbow = 100.0; rear_elbow = 105.0
        torso_lean = 14.0; torso_side = 0.0; torso_rot = 0.0
        bat_angle = 20.0
        handle = st_bat_handle
        tip = st_bat_tip
        lead_wrist = st_lead_wrist
        rear_wrist = st_rear_wrist
        over_knee = False
        kneeling_rear = False

    elif p_idx == 1: # Backlift
        hip = [st_hip[0] - 0.04, st_hip[1] - 0.02, st_hip[2]]
        lead_foot = st_lead_foot
        rear_foot = st_rear_foot
        lead_knee = 165.0; rear_knee = 155.0
        lead_elbow = 110.0; rear_elbow = 80.0
        torso_lean = 12.0; torso_side = 2.0; torso_rot = -10.0
        bat_angle = -50.0
        handle = [-0.08, 1.05, 0.12]
        tip = [-0.22, 1.62, 0.28]
        lead_wrist = [-0.06, 1.05, 0.14]
        rear_wrist = [-0.10, 1.05, 0.10]
        over_knee = False
        kneeling_rear = False

    elif p_idx == 2: # Stride
        # Transition foot toward impact position
        hip = [st_hip[0] + (imp_hip[0] - st_hip[0]) * 0.7, st_hip[1] + (imp_hip[1] - st_hip[1]) * 0.6, imp_hip[2] * 0.7]
        lead_foot = [st_lead_foot[0] + (imp_lead_foot[0] - st_lead_foot[0]) * 0.85, 0.0, imp_lead_foot[2] * 0.85]
        rear_foot = imp_rear_foot
        lead_knee = 162.0 + (imp_lead_knee - 162.0) * 0.6
        rear_knee = 160.0 + (imp_rear_knee - 160.0) * 0.5
        lead_elbow = 110.0 + (imp_lead_elbow - 110.0) * 0.4
        rear_elbow = 95.0
        torso_lean = 14.0 + (imp_torso_lean - 14.0) * 0.6
        torso_side = imp_torso_side * 0.6
        torso_rot = imp_torso_rot * 0.5
        bat_angle = -25.0
        handle = [-0.02, 1.08, imp_handle[2] * 0.5]
        tip = [-0.12, 1.68, imp_tip[2] * 0.5]
        lead_wrist = [0.0, 1.08, imp_handle[2] * 0.5 + 0.02]
        rear_wrist = [-0.04, 1.08, imp_handle[2] * 0.5 - 0.02]
        over_knee = imp_lead_foot[0] > 0.35 and not is_kneeling
        kneeling_rear = False

    elif p_idx == 3: # Downswing
        # Bat accelerating down the line
        hip = [imp_hip[0] * 0.9, imp_hip[1] * 0.95, imp_hip[2] * 0.9]
        lead_foot = imp_lead_foot
        rear_foot = imp_rear_foot
        lead_knee = 162.0 + (imp_lead_knee - 162.0) * 0.85
        rear_knee = 160.0 + (imp_rear_knee - 160.0) * 0.8
        lead_elbow = imp_lead_elbow
        rear_elbow = imp_rear_elbow
        torso_lean = imp_torso_lean * 0.85
        torso_side = imp_torso_side * 0.85
        torso_rot = imp_torso_rot * 0.8
        bat_angle = imp_bat_angle * 0.5
        handle = [imp_handle[0] - 0.08, imp_handle[1] + 0.15, imp_handle[2] * 0.8]
        tip = [imp_tip[0] - 0.15, imp_tip[1] + 0.35, imp_tip[2] * 0.8]
        lead_wrist = [handle[0] + 0.02, handle[1], handle[2] + 0.02]
        rear_wrist = [handle[0] - 0.02, handle[1], handle[2] - 0.02]
        over_knee = imp_lead_foot[0] > 0.35
        kneeling_rear = is_kneeling

    elif p_idx == 4: # Impact (Full authentic per-shot keyframe)
        hip = imp_hip
        lead_foot = imp_lead_foot
        rear_foot = imp_rear_foot
        lead_knee = imp_lead_knee
        rear_knee = imp_rear_knee
        lead_elbow = imp_lead_elbow
        rear_elbow = imp_rear_elbow
        torso_lean = imp_torso_lean
        torso_side = imp_torso_side
        torso_rot = imp_torso_rot
        bat_angle = imp_bat_angle
        handle = imp_handle
        tip = imp_tip
        lead_wrist = [handle[0] + 0.02, handle[1], handle[2] + 0.02]
        rear_wrist = [handle[0] - 0.02, handle[1], handle[2] - 0.02]
        over_knee = (imp_lead_foot[0] > 0.35) and (not is_kneeling or p_idx == 4)
        kneeling_rear = is_kneeling

    elif p_idx == 5: # Follow-through
        hip = [imp_hip[0] + 0.02, imp_hip[1] + 0.02, imp_hip[2]]
        lead_foot = imp_lead_foot
        rear_foot = imp_rear_foot
        lead_knee = imp_lead_knee + 4.0
        rear_knee = imp_rear_knee + 2.0
        lead_elbow = imp_lead_elbow + 15.0
        rear_elbow = imp_rear_elbow + 10.0
        torso_lean = max(10.0, imp_torso_lean - 4.0)
        torso_side = imp_torso_side * 0.8
        torso_rot = imp_torso_rot * 1.2
        bat_angle = ft_bat_angle
        handle = [ft_tip[0] - 0.12, ft_tip[1] - 0.55, ft_tip[2] * 0.7]
        tip = ft_tip
        lead_wrist = [handle[0] + 0.03, handle[1], handle[2] + 0.02]
        rear_wrist = [handle[0] - 0.03, handle[1], handle[2] - 0.02]
        over_knee = imp_lead_foot[0] > 0.35
        kneeling_rear = is_kneeling

    else: # Recovery
        hip = [st_hip[0] + 0.05, st_hip[1] - 0.02, 0.0]
        lead_foot = [st_lead_foot[0] + 0.08, 0.0, 0.0]
        rear_foot = st_rear_foot
        lead_knee = 150.0; rear_knee = 152.0
        lead_elbow = 105.0; rear_elbow = 110.0
        torso_lean = 16.0; torso_side = 0.0; torso_rot = 0.0
        bat_angle = 30.0
        handle = [0.06, 0.78, 0.02]
        tip = [0.12, 0.18, 0.02]
        lead_wrist = [0.08, 0.78, 0.04]
        rear_wrist = [0.04, 0.78, 0.0]
        over_knee = False
        kneeling_rear = False

    # Chest & Head positions via forward kinematics
    chest_y = hip[1] + 0.42 * (1.0 - torso_lean * 0.003)
    chest_x = hip[0] + 0.38 * (torso_lean / 90.0)
    chest_z = hip[2] + 0.15 * (torso_side / 90.0)
    chest = [round(chest_x, 3), round(chest_y, 3), round(chest_z, 3)]

    head_x = chest[0] + 0.18 * (torso_lean / 90.0)
    head_y = chest[1] + 0.26
    head_z = chest[2] + 0.08 * (torso_side / 90.0)
    head = {
        "x": round(head_x, 3),
        "y": round(head_y, 3),
        "z": round(head_z, 3),
        "tiltDeg": round(torso_lean * 0.3, 1),
        "overFrontKnee": over_knee
    }

    # Shoulder positions
    sh_span = 0.36
    lead_sh = [round(chest[0] + 0.04, 3), round(chest[1] + 0.02, 3), round(chest[2] + sh_span * 0.5, 3)]
    rear_sh = [round(chest[0] - 0.04, 3), round(chest[1] + 0.02, 3), round(chest[2] - sh_span * 0.5, 3)]

    # Elbow joint positions
    lead_el = [
        round((lead_sh[0] + lead_wrist[0]) / 2 + 0.08, 3),
        round((lead_sh[1] + lead_wrist[1]) / 2 + 0.04, 3),
        round((lead_sh[2] + lead_wrist[2]) / 2 + 0.04, 3)
    ]
    rear_el = [
        round((rear_sh[0] + rear_wrist[0]) / 2 - 0.04, 3),
        round((rear_sh[1] + rear_wrist[1]) / 2 - 0.04, 3),
        round((rear_sh[2] + rear_wrist[2]) / 2 - 0.04, 3)
    ]

    # Knee positions
    lead_knee_y = (hip[1] + lead_foot[1]) / 2
    if is_kneeling and p_idx >= 3:
        rear_knee_y = 0.08
    else:
        rear_knee_y = (hip[1] + rear_foot[1]) / 2

    lead_knee_pt = [round((hip[0] + lead_foot[0]) / 2 + 0.05, 3), round(lead_knee_y, 3), round(lead_foot[2], 3)]
    rear_knee_pt = [round((hip[0] + rear_foot[0]) / 2 - 0.04, 3), round(rear_knee_y, 3), round(rear_foot[2], 3)]

    points = [
        f"Head aligned over front knee: {'Yes' if over_knee else 'Anchored'}",
        f"Lead knee flexion target: {int(lead_knee)}°",
        f"Bat path plane: {shot['swingPlane']}",
        f"Torso lean forward: {int(torso_lean)}°"
    ]

    return {
        "phaseKey": phase_name,
        "label": f"{p_idx + 1}. {phase_name.replace('_', ' ').title()}",
        "durationWeight": weight,
        "cue": cue,
        "techniquePoints": points,
        "head": head,
        "torso": {
            "leanDeg": round(torso_lean, 1),
            "sideLeanDeg": round(torso_side, 1),
            "rotationDeg": round(torso_rot, 1),
            "hip": [round(hip[0], 3), round(hip[1], 3), round(hip[2], 3)],
            "chest": chest
        },
        "leadLeg": {
            "hipAngleDeg": round(180.0 - lead_knee * 0.5, 1),
            "kneeAngleDeg": round(lead_knee, 1),
            "ankleAngleDeg": round(80.0 + (180.0 - lead_knee) * 0.2, 1),
            "kneePos": lead_knee_pt,
            "footPos": [round(lead_foot[0], 3), round(lead_foot[1], 3), round(lead_foot[2], 3)],
            "isKneeling": False
        },
        "rearLeg": {
            "hipAngleDeg": round(180.0 - rear_knee * 0.5, 1),
            "kneeAngleDeg": round(rear_knee, 1),
            "ankleAngleDeg": round(80.0 + (180.0 - rear_knee) * 0.2, 1),
            "kneePos": rear_knee_pt,
            "footPos": [round(rear_foot[0], 3), round(rear_foot[1], 3), round(rear_foot[2], 3)],
            "isKneeling": kneeling_rear
        },
        "leadArm": {
            "shoulderPos": lead_sh,
            "elbowPos": lead_el,
            "elbowAngleDeg": round(lead_elbow, 1),
            "wristPos": [round(lead_wrist[0], 3), round(lead_wrist[1], 3), round(lead_wrist[2], 3)]
        },
        "rearArm": {
            "shoulderPos": rear_sh,
            "elbowPos": rear_el,
            "elbowAngleDeg": round(rear_elbow, 1),
            "wristPos": [round(rear_wrist[0], 3), round(rear_wrist[1], 3), round(rear_wrist[2], 3)]
        },
        "bat": {
            "angleDeg": round(bat_angle, 1),
            "bladeFaceDeg": round(imp_torso_rot, 1),
            "handlePos": [round(handle[0], 3), round(handle[1], 3), round(handle[2], 3)],
            "tipPos": [round(tip[0], 3), round(tip[1], 3), round(tip[2], 3)],
            "swingPlane": shot["swingPlane"]
        }
    }

phase_names = ["stance", "backlift", "stride", "downswing", "impact", "follow_through", "recovery"]

shots_dict = {}
for s in shots_data:
    phases_dict = {}
    for idx, p_name in enumerate(phase_names):
        phases_dict[p_name] = build_phase_keyframe(s, p_name, idx)

    shots_dict[s["name"]] = {
        "id": s["id"],
        "name": s["name"],
        "slug": s["slug"],
        "category": s["category"],
        "provenance": "authored baseline (tunable)",
        "ballTrajectory": s["ball"],
        "swingPlane": s["swingPlane"],
        "commonMistakes": s["mistakes"],
        "drills": s["drills"],
        "phases": phases_dict
    }

ts_content = f"""/**
 * CricketIQ — Authored 3D Biomechanical Shot Animations
 * Single authoritative source of truth for 3D animation keyframes across all 25 catalogue cricket shots.
 * Provenance: "authored baseline (tunable)".
 * Do not claim measured provenance.
 */

export type SwingPlaneType =
  | 'vertical'
  | 'horizontal'
  | 'angled_off'
  | 'angled_leg'
  | 'overhead'
  | 'ramp';

export interface BallTrajectoryInfo {{
  line: string;
  length: string;
  pitch: [number, number, number];
  contact: [number, number, number];
}}

export interface PhaseKeyframe {{
  phaseKey: 'stance' | 'backlift' | 'stride' | 'downswing' | 'impact' | 'follow_through' | 'recovery';
  label: string;
  durationWeight: number;
  cue: string;
  techniquePoints: string[];
  head: {{
    x: number;
    y: number;
    z: number;
    tiltDeg: number;
    overFrontKnee: boolean;
  }};
  torso: {{
    leanDeg: number;
    sideLeanDeg: number;
    rotationDeg: number;
    hip: [number, number, number];
    chest: [number, number, number];
  }};
  leadLeg: {{
    hipAngleDeg: number;
    kneeAngleDeg: number;
    ankleAngleDeg: number;
    kneePos: [number, number, number];
    footPos: [number, number, number];
    isKneeling: boolean;
  }};
  rearLeg: {{
    hipAngleDeg: number;
    kneeAngleDeg: number;
    ankleAngleDeg: number;
    kneePos: [number, number, number];
    footPos: [number, number, number];
    isKneeling: boolean;
  }};
  leadArm: {{
    shoulderPos: [number, number, number];
    elbowPos: [number, number, number];
    elbowAngleDeg: number;
    wristPos: [number, number, number];
  }};
  rearArm: {{
    shoulderPos: [number, number, number];
    elbowPos: [number, number, number];
    elbowAngleDeg: number;
    wristPos: [number, number, number];
  }};
  bat: {{
    angleDeg: number;
    bladeFaceDeg: number;
    handlePos: [number, number, number];
    tipPos: [number, number, number];
    swingPlane: SwingPlaneType;
  }};
}}

export interface ShotAnimationDefinition {{
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
}}

export const SHOT_ANIMATIONS: Record<string, ShotAnimationDefinition> = {json.dumps(shots_dict, indent=2)};

export function getShotAnimation(idOrName: string): ShotAnimationDefinition {{
  if (!idOrName) return SHOT_ANIMATIONS['Cover Drive'];
  const n = idOrName.trim().toLowerCase();

  // Match by exact key name
  for (const [k, v] of Object.entries(SHOT_ANIMATIONS)) {{
    if (k.toLowerCase() === n) return v;
  }}
  // Match by id or slug
  for (const v of Object.values(SHOT_ANIMATIONS)) {{
    if (v.id.toLowerCase() === n || v.slug.toLowerCase() === n || v.slug.toLowerCase() === n.replace(/\\s+/g, '-')) {{
      return v;
    }}
  }}
  // Substring fallback
  for (const [k, v] of Object.entries(SHOT_ANIMATIONS)) {{
    if (k.toLowerCase().includes(n) || n.includes(k.toLowerCase())) return v;
  }}
  return SHOT_ANIMATIONS['Cover Drive'];
}}

export function getAllShotAnimations(): ShotAnimationDefinition[] {{
  return Object.values(SHOT_ANIMATIONS);
}}
"""

out_file = Path("frontend/src/data/shotAnimations.ts")
out_file.write_text(ts_content, encoding="utf-8")
print(f"Successfully generated {out_file} with {len(shots_dict)} shots!")
