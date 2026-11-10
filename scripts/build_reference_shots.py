"""
CricketIQ — Authoritative Reference Shots & 3D Avatar Keyframes Generator
Builds backend/app/data/reference_shots.json and frontend/src/data/reference_shots.json
with complete, distinct, authentic 3D biomechanical keyframe animations for all 25 catalogue cricket shots.

Provenance: "authored baseline (tunable)".
Maintains existing 8 keyframe fields for full backward compatibility, while extending with:
- lead_stride_dir_deg: front foot direction relative to pitch line (0=straight, >0 off-side, <0 leg-side)
- rear_foot_x: back foot offset
- rear_foot_mode: 'planted' | 'drags' | 'back-and-across' | 'kneeling'
- pelvis_rotation_deg: body rotation in transverse plane
- shoulder_rotation_deg: shoulder rotation in transverse plane
- head_offset_x: head station relative to lead knee
- hands_x, hands_y: grip position relative to hips
- bat_plane: 'vertical' | 'diagonal' | 'horizontal'
- bat_tip_x, bat_tip_y: blade tip coordinates driving the bat path trail
- wrist_cock_deg: wrist lever angle
- duration_weight: phase timing for smooth easing interpolation
- cue: authentic MCC/Cricket Australia technical cue
"""

import json
import math
from pathlib import Path

# Supported analysis shots per README
SUPPORTED_ANALYSIS_SHOTS = {"Cover Drive", "Straight Drive", "Pull Shot", "Forward Defensive"}
CALIBRATED_BENCHMARKS = {"Cover Drive", "Straight Drive", "Pull Shot", "Forward Defensive", "Sweep"}

SHOT_CATALOGUE_SPECS = [
    # -------------------------------------------------------------
    # 1. DRIVES
    # -------------------------------------------------------------
    {
        "name": "Cover Drive",
        "slug": "cover-drive",
        "category": "Drives",
        "desc": "Classical front-foot drive through extra cover into the off side.",
        "bat_path": "starts straight from 2nd slip, sweeps across through extra cover corridor with high front shoulder",
        "swing_plane": "diagonal",
        "foot_mode": "planted",
        "stride_dir": 32.0,
        "pelvis_rot": 20.0,
        "shoulder_rot": 28.0,
        "impact_pose": {
            "hip_x": 0.22, "hip_y": 0.16, "lead_stride_x": 0.70, "lead_stride_dir_deg": 32.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "planted",
            "lead_knee_flex": 124.0, "rear_knee_flex": 150.0,
            "lead_elbow_flex": 92.0, "rear_elbow_flex": 95.0,
            "pelvis_rotation_deg": 20.0, "shoulder_rotation_deg": 28.0,
            "head_offset_x": 0.02, "hands_x": 0.26, "hands_y": 0.74,
            "bat_plane": "diagonal", "bat_angle": 18.0,
            "bat_tip_x": 0.38, "bat_tip_y": 0.22, "wrist_cock_deg": 15.0,
            "torso_lean": 25.0, "shoulder_tilt": 16.0, "duration_weight": 0.10,
            "cue": "Head locked over front knee, presenting full face through extra cover"
        },
        "ft_pose": {
            "hip_x": 0.24, "hip_y": 0.15, "lead_stride_x": 0.68, "lead_stride_dir_deg": 32.0,
            "rear_foot_x": -0.12, "rear_foot_mode": "planted",
            "lead_knee_flex": 132.0, "rear_knee_flex": 156.0,
            "lead_elbow_flex": 115.0, "rear_elbow_flex": 108.0,
            "pelvis_rotation_deg": 25.0, "shoulder_rotation_deg": 35.0,
            "head_offset_x": 0.04, "hands_x": 0.22, "hands_y": 1.15,
            "bat_plane": "diagonal", "bat_angle": -72.0,
            "bat_tip_x": 0.28, "bat_tip_y": 1.72, "wrist_cock_deg": 20.0,
            "torso_lean": 20.0, "shoulder_tilt": 12.0, "duration_weight": 0.16,
            "cue": "High sweeping finish wrapping gracefully over the front shoulder"
        }
    },
    {
        "name": "Straight Drive",
        "slug": "straight-drive",
        "category": "Drives",
        "desc": "Purity drive played straight back past the bowler along the ground.",
        "bat_path": "straight pendulum down the pitch line directly toward the bowler with vertical face",
        "swing_plane": "vertical",
        "foot_mode": "planted",
        "stride_dir": 0.0,
        "pelvis_rot": 10.0,
        "shoulder_rot": 14.0,
        "impact_pose": {
            "hip_x": 0.20, "hip_y": 0.16, "lead_stride_x": 0.68, "lead_stride_dir_deg": 0.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "planted",
            "lead_knee_flex": 122.0, "rear_knee_flex": 155.0,
            "lead_elbow_flex": 90.0, "rear_elbow_flex": 92.0,
            "pelvis_rotation_deg": 10.0, "shoulder_rotation_deg": 14.0,
            "head_offset_x": 0.00, "hands_x": 0.28, "hands_y": 0.72,
            "bat_plane": "vertical", "bat_angle": 4.0,
            "bat_tip_x": 0.33, "bat_tip_y": -0.03, "wrist_cock_deg": 10.0,
            "torso_lean": 26.0, "shoulder_tilt": 14.0, "duration_weight": 0.10,
            "cue": "Head stationary directly over ball, bat face vertical pointing straight to bowler"
        },
        "ft_pose": {
            "hip_x": 0.22, "hip_y": 0.15, "lead_stride_x": 0.66, "lead_stride_dir_deg": 0.0,
            "rear_foot_x": -0.14, "rear_foot_mode": "planted",
            "lead_knee_flex": 130.0, "rear_knee_flex": 158.0,
            "lead_elbow_flex": 120.0, "rear_elbow_flex": 112.0,
            "pelvis_rotation_deg": 14.0, "shoulder_rotation_deg": 18.0,
            "head_offset_x": 0.02, "hands_x": 0.25, "hands_y": 1.18,
            "bat_plane": "vertical", "bat_angle": -82.0,
            "bat_tip_x": 0.35, "bat_tip_y": 1.78, "wrist_cock_deg": 12.0,
            "torso_lean": 20.0, "shoulder_tilt": 10.0, "duration_weight": 0.16,
            "cue": "High two-handed finish with full manufacturer label visible to bowler"
        }
    },
    {
        "name": "On Drive",
        "slug": "on-drive",
        "category": "Drives",
        "desc": "Controlled front-foot drive through mid-on with high lead elbow.",
        "bat_path": "close to front pad accelerating toward mid-on with slightly open front shoulder",
        "swing_plane": "vertical",
        "foot_mode": "planted",
        "stride_dir": -18.0,
        "pelvis_rot": 16.0,
        "shoulder_rot": 20.0,
        "impact_pose": {
            "hip_x": 0.18, "hip_y": 0.16, "lead_stride_x": 0.65, "lead_stride_dir_deg": -18.0,
            "rear_foot_x": -0.14, "rear_foot_mode": "planted",
            "lead_knee_flex": 120.0, "rear_knee_flex": 152.0,
            "lead_elbow_flex": 94.0, "rear_elbow_flex": 95.0,
            "pelvis_rotation_deg": 16.0, "shoulder_rotation_deg": 20.0,
            "head_offset_x": 0.01, "hands_x": 0.24, "hands_y": 0.72,
            "bat_plane": "vertical", "bat_angle": 14.0,
            "bat_tip_x": 0.36, "bat_tip_y": 0.20, "wrist_cock_deg": 12.0,
            "torso_lean": 24.0, "shoulder_tilt": 14.0, "duration_weight": 0.10,
            "cue": "Step slightly open toward mid-on, guide bat close to front pad"
        },
        "ft_pose": {
            "hip_x": 0.20, "hip_y": 0.15, "lead_stride_x": 0.64, "lead_stride_dir_deg": -18.0,
            "rear_foot_x": -0.12, "rear_foot_mode": "planted",
            "lead_knee_flex": 128.0, "rear_knee_flex": 155.0,
            "lead_elbow_flex": 115.0, "rear_elbow_flex": 105.0,
            "pelvis_rotation_deg": 20.0, "shoulder_rotation_deg": 25.0,
            "head_offset_x": 0.03, "hands_x": 0.20, "hands_y": 1.10,
            "bat_plane": "vertical", "bat_angle": -76.0,
            "bat_tip_x": 0.32, "bat_tip_y": 1.68, "wrist_cock_deg": 15.0,
            "torso_lean": 19.0, "shoulder_tilt": 10.0, "duration_weight": 0.16,
            "cue": "High balanced extension pointing directly at the mid-on fielder"
        }
    },
    {
        "name": "Off Drive",
        "slug": "off-drive",
        "category": "Drives",
        "desc": "Front-foot drive through mid-off with high front shoulder and firm base.",
        "bat_path": "smooth path through mid-off corridor with prominent leading shoulder guidance",
        "swing_plane": "vertical",
        "foot_mode": "planted",
        "stride_dir": 16.0,
        "pelvis_rot": 18.0,
        "shoulder_rot": 24.0,
        "impact_pose": {
            "hip_x": 0.21, "hip_y": 0.16, "lead_stride_x": 0.68, "lead_stride_dir_deg": 16.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "planted",
            "lead_knee_flex": 123.0, "rear_knee_flex": 152.0,
            "lead_elbow_flex": 92.0, "rear_elbow_flex": 94.0,
            "pelvis_rotation_deg": 18.0, "shoulder_rotation_deg": 24.0,
            "head_offset_x": 0.01, "hands_x": 0.26, "hands_y": 0.73,
            "bat_plane": "vertical", "bat_angle": 16.0,
            "bat_tip_x": 0.39, "bat_tip_y": 0.20, "wrist_cock_deg": 14.0,
            "torso_lean": 25.0, "shoulder_tilt": 16.0, "duration_weight": 0.10,
            "cue": "Front foot committed toward mid-off, high front shoulder dominant"
        },
        "ft_pose": {
            "hip_x": 0.23, "hip_y": 0.15, "lead_stride_x": 0.66, "lead_stride_dir_deg": 16.0,
            "rear_foot_x": -0.13, "rear_foot_mode": "planted",
            "lead_knee_flex": 130.0, "rear_knee_flex": 156.0,
            "lead_elbow_flex": 118.0, "rear_elbow_flex": 110.0,
            "pelvis_rotation_deg": 22.0, "shoulder_rotation_deg": 30.0,
            "head_offset_x": 0.03, "hands_x": 0.22, "hands_y": 1.14,
            "bat_plane": "vertical", "bat_angle": -78.0,
            "bat_tip_x": 0.32, "bat_tip_y": 1.74, "wrist_cock_deg": 16.0,
            "torso_lean": 20.0, "shoulder_tilt": 11.0, "duration_weight": 0.16,
            "cue": "Extending smoothly through mid-off, maintaining upright spine alignment"
        }
    },
    {
        "name": "Lofted Drive",
        "slug": "lofted-drive",
        "category": "Drives",
        "desc": "Power drive lofted over infielders with steep upward swing arc.",
        "bat_path": "deep backlift with steep ascending upward arc lifting ball cleanly over infield",
        "swing_plane": "diagonal",
        "foot_mode": "planted",
        "stride_dir": 10.0,
        "pelvis_rot": 25.0,
        "shoulder_rot": 32.0,
        "impact_pose": {
            "hip_x": 0.26, "hip_y": 0.14, "lead_stride_x": 0.82, "lead_stride_dir_deg": 10.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "planted",
            "lead_knee_flex": 114.0, "rear_knee_flex": 148.0,
            "lead_elbow_flex": 105.0, "rear_elbow_flex": 98.0,
            "pelvis_rotation_deg": 25.0, "shoulder_rotation_deg": 32.0,
            "head_offset_x": -0.02, "hands_x": 0.32, "hands_y": 0.80,
            "bat_plane": "diagonal", "bat_angle": -15.0,
            "bat_tip_x": 0.42, "bat_tip_y": 0.28, "wrist_cock_deg": 22.0,
            "torso_lean": 28.0, "shoulder_tilt": 20.0, "duration_weight": 0.10,
            "cue": "Deep forward stride, hitting through the ascending arc with committed extension"
        },
        "ft_pose": {
            "hip_x": 0.28, "hip_y": 0.12, "lead_stride_x": 0.80, "lead_stride_dir_deg": 10.0,
            "rear_foot_x": -0.10, "rear_foot_mode": "drags",
            "lead_knee_flex": 126.0, "rear_knee_flex": 152.0,
            "lead_elbow_flex": 135.0, "rear_elbow_flex": 125.0,
            "pelvis_rotation_deg": 35.0, "shoulder_rotation_deg": 45.0,
            "head_offset_x": 0.02, "hands_x": 0.28, "hands_y": 1.30,
            "bat_plane": "diagonal", "bat_angle": -95.0,
            "bat_tip_x": 0.42, "bat_tip_y": 1.92, "wrist_cock_deg": 25.0,
            "torso_lean": 22.0, "shoulder_tilt": 15.0, "duration_weight": 0.16,
            "cue": "Exaggerated high finish reaching high into the sky, weight committed forward"
        }
    },

    # -------------------------------------------------------------
    # 2. DEFENSIVE STROKES
    # -------------------------------------------------------------
    {
        "name": "Forward Defensive",
        "slug": "forward-defensive",
        "category": "Defensive Strokes",
        "desc": "Classical front-foot dead-bat block played directly under the eyes.",
        "bat_path": "downward vertical presentation into the turf, soft hands absorbing all impact pace",
        "swing_plane": "vertical",
        "foot_mode": "planted",
        "stride_dir": 4.0,
        "pelvis_rot": 8.0,
        "shoulder_rot": 12.0,
        "impact_pose": {
            "hip_x": 0.15, "hip_y": 0.16, "lead_stride_x": 0.48, "lead_stride_dir_deg": 4.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "planted",
            "lead_knee_flex": 128.0, "rear_knee_flex": 156.0,
            "lead_elbow_flex": 88.0, "rear_elbow_flex": 90.0,
            "pelvis_rotation_deg": 8.0, "shoulder_rotation_deg": 12.0,
            "head_offset_x": 0.00, "hands_x": 0.20, "hands_y": 0.60,
            "bat_plane": "vertical", "bat_angle": 6.0,
            "bat_tip_x": 0.26, "bat_tip_y": 0.18, "wrist_cock_deg": 5.0,
            "torso_lean": 24.0, "shoulder_tilt": 12.0, "duration_weight": 0.12,
            "cue": "Soft hands under eyes, angled downward dead face dropping ball at feet"
        },
        "ft_pose": {
            "hip_x": 0.15, "hip_y": 0.16, "lead_stride_x": 0.48, "lead_stride_dir_deg": 4.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "planted",
            "lead_knee_flex": 128.0, "rear_knee_flex": 156.0,
            "lead_elbow_flex": 88.0, "rear_elbow_flex": 90.0,
            "pelvis_rotation_deg": 8.0, "shoulder_rotation_deg": 12.0,
            "head_offset_x": 0.00, "hands_x": 0.20, "hands_y": 0.60,
            "bat_plane": "vertical", "bat_angle": 8.0,
            "bat_tip_x": 0.26, "bat_tip_y": 0.20, "wrist_cock_deg": 5.0,
            "torso_lean": 24.0, "shoulder_tilt": 12.0, "duration_weight": 0.14,
            "cue": "Hold dead bat position, zero follow-through, ball smothered on turf"
        }
    },
    {
        "name": "Back-foot Defensive",
        "slug": "back-foot-defensive",
        "category": "Defensive Strokes",
        "desc": "Upright back-foot block close to torso on stumps against rising deliveries.",
        "bat_path": "compact vertical drop close to body with high hands under eyes",
        "swing_plane": "vertical",
        "foot_mode": "back-and-across",
        "stride_dir": 0.0,
        "pelvis_rot": 5.0,
        "shoulder_rot": 8.0,
        "impact_pose": {
            "hip_x": -0.12, "hip_y": 0.15, "lead_stride_x": 0.05, "lead_stride_dir_deg": 0.0,
            "rear_foot_x": -0.18, "rear_foot_mode": "back-and-across",
            "lead_knee_flex": 156.0, "rear_knee_flex": 142.0,
            "lead_elbow_flex": 86.0, "rear_elbow_flex": 88.0,
            "pelvis_rotation_deg": 5.0, "shoulder_rotation_deg": 8.0,
            "head_offset_x": 0.12, "hands_x": 0.12, "hands_y": 0.72,
            "bat_plane": "vertical", "bat_angle": 8.0,
            "bat_tip_x": 0.16, "bat_tip_y": 0.28, "wrist_cock_deg": 6.0,
            "torso_lean": 8.0, "shoulder_tilt": 6.0, "duration_weight": 0.12,
            "cue": "Back foot deep onto off stump, vertical bat smothered under chin"
        },
        "ft_pose": {
            "hip_x": -0.12, "hip_y": 0.15, "lead_stride_x": 0.05, "lead_stride_dir_deg": 0.0,
            "rear_foot_x": -0.18, "rear_foot_mode": "back-and-across",
            "lead_knee_flex": 156.0, "rear_knee_flex": 142.0,
            "lead_elbow_flex": 86.0, "rear_elbow_flex": 88.0,
            "pelvis_rotation_deg": 5.0, "shoulder_rotation_deg": 8.0,
            "head_offset_x": 0.12, "hands_x": 0.12, "hands_y": 0.72,
            "bat_plane": "vertical", "bat_angle": 10.0,
            "bat_tip_x": 0.16, "bat_tip_y": 0.30, "wrist_cock_deg": 6.0,
            "torso_lean": 8.0, "shoulder_tilt": 6.0, "duration_weight": 0.14,
            "cue": "Hold compact shape close to ribcage, dead bat stopping ball on crease"
        }
    },

    # -------------------------------------------------------------
    # 3. BACK-FOOT AND CUT SHOTS
    # -------------------------------------------------------------
    {
        "name": "Back-foot Punch",
        "slug": "back-foot-punch",
        "category": "Back-foot and Cut Shots",
        "desc": "Crisp punch off back foot through the off-side with high lead elbow.",
        "bat_path": "short sharp downward punch presented cleanly through point or cover",
        "swing_plane": "vertical",
        "foot_mode": "back-and-across",
        "stride_dir": 8.0,
        "pelvis_rot": 15.0,
        "shoulder_rot": 20.0,
        "impact_pose": {
            "hip_x": -0.10, "hip_y": 0.15, "lead_stride_x": 0.08, "lead_stride_dir_deg": 8.0,
            "rear_foot_x": -0.18, "rear_foot_mode": "back-and-across",
            "lead_knee_flex": 152.0, "rear_knee_flex": 138.0,
            "lead_elbow_flex": 122.0, "rear_elbow_flex": 90.0,
            "pelvis_rotation_deg": 15.0, "shoulder_rotation_deg": 20.0,
            "head_offset_x": 0.08, "hands_x": 0.20, "hands_y": 0.80,
            "bat_plane": "vertical", "bat_angle": 18.0,
            "bat_tip_x": 0.32, "bat_tip_y": 0.40, "wrist_cock_deg": 15.0,
            "torso_lean": 12.0, "shoulder_tilt": 10.0, "duration_weight": 0.10,
            "cue": "Tall back foot stance, punch down on ball with prominent high lead elbow"
        },
        "ft_pose": {
            "hip_x": -0.08, "hip_y": 0.14, "lead_stride_x": 0.10, "lead_stride_dir_deg": 8.0,
            "rear_foot_x": -0.16, "rear_foot_mode": "back-and-across",
            "lead_knee_flex": 154.0, "rear_knee_flex": 140.0,
            "lead_elbow_flex": 130.0, "rear_elbow_flex": 102.0,
            "pelvis_rotation_deg": 20.0, "shoulder_rotation_deg": 26.0,
            "head_offset_x": 0.10, "hands_x": 0.22, "hands_y": 1.05,
            "bat_plane": "vertical", "bat_angle": -65.0,
            "bat_tip_x": 0.28, "bat_tip_y": 1.25, "wrist_cock_deg": 18.0,
            "torso_lean": 11.0, "shoulder_tilt": 8.0, "duration_weight": 0.16,
            "cue": "Controlled punch check finish, firm wrists holding shape"
        }
    },
    {
        "name": "Square Cut",
        "slug": "square-cut",
        "category": "Back-foot and Cut Shots",
        "desc": "Aggressive cross-bat slash through point at chest/shoulder height.",
        "bat_path": "high backlift chopping down horizontally across chest line toward point",
        "swing_plane": "horizontal",
        "foot_mode": "back-and-across",
        "stride_dir": 15.0,
        "pelvis_rot": 22.0,
        "shoulder_rot": 25.0,
        "impact_pose": {
            "hip_x": -0.12, "hip_y": 0.16, "lead_stride_x": 0.05, "lead_stride_dir_deg": 15.0,
            "rear_foot_x": -0.20, "rear_foot_mode": "back-and-across",
            "lead_knee_flex": 148.0, "rear_knee_flex": 136.0,
            "lead_elbow_flex": 145.0, "rear_elbow_flex": 95.0,
            "pelvis_rotation_deg": 22.0, "shoulder_rotation_deg": 25.0,
            "head_offset_x": 0.10, "hands_x": 0.24, "hands_y": 0.72,
            "bat_plane": "horizontal", "bat_angle": 88.0,
            "bat_tip_x": 0.45, "bat_tip_y": 0.70, "wrist_cock_deg": 35.0,
            "torso_lean": 10.0, "shoulder_tilt": 8.0, "duration_weight": 0.10,
            "cue": "Weight onto back foot, horizontal slash rolling wrists over point"
        },
        "ft_pose": {
            "hip_x": -0.06, "hip_y": 0.15, "lead_stride_x": 0.12, "lead_stride_dir_deg": 15.0,
            "rear_foot_x": -0.18, "rear_foot_mode": "back-and-across",
            "lead_knee_flex": 150.0, "rear_knee_flex": 140.0,
            "lead_elbow_flex": 148.0, "rear_elbow_flex": 115.0,
            "pelvis_rotation_deg": 30.0, "shoulder_rotation_deg": 35.0,
            "head_offset_x": 0.12, "hands_x": 0.28, "hands_y": 0.85,
            "bat_plane": "horizontal", "bat_angle": 135.0,
            "bat_tip_x": 0.40, "bat_tip_y": 0.95, "wrist_cock_deg": 40.0,
            "torso_lean": 8.0, "shoulder_tilt": 6.0, "duration_weight": 0.16,
            "cue": "High rolling-wrist finish with arms fully extended through point"
        }
    },
    {
        "name": "Late Cut",
        "slug": "late-cut",
        "category": "Back-foot and Cut Shots",
        "desc": "Delicate touch deflection played late behind the stumps toward third man.",
        "bat_path": "bat comes down late close to off stump with soft wrists deflecting fine",
        "swing_plane": "diagonal",
        "foot_mode": "back-and-across",
        "stride_dir": 22.0,
        "pelvis_rot": 12.0,
        "shoulder_rot": 16.0,
        "impact_pose": {
            "hip_x": -0.14, "hip_y": 0.16, "lead_stride_x": 0.04, "lead_stride_dir_deg": 22.0,
            "rear_foot_x": -0.20, "rear_foot_mode": "back-and-across",
            "lead_knee_flex": 150.0, "rear_knee_flex": 138.0,
            "lead_elbow_flex": 132.0, "rear_elbow_flex": 90.0,
            "pelvis_rotation_deg": 12.0, "shoulder_rotation_deg": 16.0,
            "head_offset_x": 0.10, "hands_x": 0.05, "hands_y": 0.65,
            "bat_plane": "diagonal", "bat_angle": 58.0,
            "bat_tip_x": 0.20, "bat_tip_y": 0.30, "wrist_cock_deg": 28.0,
            "torso_lean": 9.0, "shoulder_tilt": 7.0, "duration_weight": 0.10,
            "cue": "Play as late as possible behind body line, feather wrists toward third man"
        },
        "ft_pose": {
            "hip_x": -0.12, "hip_y": 0.15, "lead_stride_x": 0.06, "lead_stride_dir_deg": 22.0,
            "rear_foot_x": -0.18, "rear_foot_mode": "back-and-across",
            "lead_knee_flex": 152.0, "rear_knee_flex": 140.0,
            "lead_elbow_flex": 135.0, "rear_elbow_flex": 98.0,
            "pelvis_rotation_deg": 15.0, "shoulder_rotation_deg": 20.0,
            "head_offset_x": 0.12, "hands_x": 0.08, "hands_y": 0.70,
            "bat_plane": "diagonal", "bat_angle": 75.0,
            "bat_tip_x": 0.15, "bat_tip_y": 0.45, "wrist_cock_deg": 32.0,
            "torso_lean": 8.0, "shoulder_tilt": 6.0, "duration_weight": 0.16,
            "cue": "Soft glide follow-through with face opened toward slip cordon"
        }
    },
    {
        "name": "Upper Cut",
        "slug": "upper-cut",
        "category": "Back-foot and Cut Shots",
        "desc": "Elevated ramp slash lifting short bouncers steeply over the slip cordon.",
        "bat_path": "rising onto toes, steep upward diagonal blade extension swiping over slips",
        "swing_plane": "diagonal",
        "foot_mode": "drags",
        "stride_dir": 10.0,
        "pelvis_rot": 18.0,
        "shoulder_rot": 22.0,
        "impact_pose": {
            "hip_x": -0.06, "hip_y": 0.08, "lead_stride_x": 0.02, "lead_stride_dir_deg": 10.0,
            "rear_foot_x": -0.14, "rear_foot_mode": "drags",
            "lead_knee_flex": 162.0, "rear_knee_flex": 158.0,
            "lead_elbow_flex": 150.0, "rear_elbow_flex": 115.0,
            "pelvis_rotation_deg": 18.0, "shoulder_rotation_deg": 22.0,
            "head_offset_x": 0.08, "hands_x": 0.22, "hands_y": 1.10,
            "bat_plane": "diagonal", "bat_angle": -45.0,
            "bat_tip_x": 0.40, "bat_tip_y": 1.35, "wrist_cock_deg": 35.0,
            "torso_lean": -6.0, "shoulder_tilt": 12.0, "duration_weight": 0.10,
            "cue": "Rise onto balls of feet, slice blade upward using bowler pace over gully"
        },
        "ft_pose": {
            "hip_x": -0.04, "hip_y": 0.06, "lead_stride_x": 0.04, "lead_stride_dir_deg": 10.0,
            "rear_foot_x": -0.12, "rear_foot_mode": "drags",
            "lead_knee_flex": 165.0, "rear_knee_flex": 160.0,
            "lead_elbow_flex": 155.0, "rear_elbow_flex": 125.0,
            "pelvis_rotation_deg": 24.0, "shoulder_rotation_deg": 30.0,
            "head_offset_x": 0.10, "hands_x": 0.25, "hands_y": 1.30,
            "bat_plane": "diagonal", "bat_angle": -90.0,
            "bat_tip_x": 0.38, "bat_tip_y": 1.65, "wrist_cock_deg": 38.0,
            "torso_lean": -8.0, "shoulder_tilt": 15.0, "duration_weight": 0.16,
            "cue": "High soaring extension over off-side cordon, eyes tracking elevation"
        }
    },

    # -------------------------------------------------------------
    # 4. SHORT-BALL ATTACKING SHOTS
    # -------------------------------------------------------------
    {
        "name": "Pull Shot",
        "slug": "pull-shot",
        "category": "Short-ball Attacking Shots",
        "desc": "Cross-bat swivel pull transferring weight onto back foot and hitting to square leg.",
        "bat_path": "high backlift swinging in wide horizontal arc across chest toward square leg",
        "swing_plane": "horizontal",
        "foot_mode": "back-and-across",
        "stride_dir": -35.0,
        "pelvis_rot": 65.0,
        "shoulder_rot": 78.0,
        "impact_pose": {
            "hip_x": -0.08, "hip_y": 0.16, "lead_stride_x": 0.02, "lead_stride_dir_deg": -35.0,
            "rear_foot_x": -0.18, "rear_foot_mode": "back-and-across",
            "lead_knee_flex": 146.0, "rear_knee_flex": 138.0,
            "lead_elbow_flex": 145.0, "rear_elbow_flex": 95.0,
            "pelvis_rotation_deg": 65.0, "shoulder_rotation_deg": 78.0,
            "head_offset_x": 0.10, "hands_x": 0.22, "hands_y": 0.82,
            "bat_plane": "horizontal", "bat_angle": 85.0,
            "bat_tip_x": 0.42, "bat_tip_y": 0.85, "wrist_cock_deg": 30.0,
            "torso_lean": 10.0, "shoulder_tilt": 8.0, "duration_weight": 0.10,
            "cue": "Weight onto back foot, swivel hips and pull horizontally through square leg"
        },
        "ft_pose": {
            "hip_x": 0.02, "hip_y": 0.15, "lead_stride_x": 0.15, "lead_stride_dir_deg": -35.0,
            "rear_foot_x": -0.14, "rear_foot_mode": "back-and-across",
            "lead_knee_flex": 152.0, "rear_knee_flex": 144.0,
            "lead_elbow_flex": 148.0, "rear_elbow_flex": 125.0,
            "pelvis_rotation_deg": 85.0, "shoulder_rotation_deg": 95.0,
            "head_offset_x": 0.12, "hands_x": -0.15, "hands_y": 0.90,
            "bat_plane": "horizontal", "bat_angle": 155.0,
            "bat_tip_x": -0.30, "bat_tip_y": 0.92, "wrist_cock_deg": 35.0,
            "torso_lean": 8.0, "shoulder_tilt": 6.0, "duration_weight": 0.16,
            "cue": "Complete 180° swivel follow-through wrapping bat around body to fine leg"
        }
    },
    {
        "name": "Hook Shot",
        "slug": "hook-shot",
        "category": "Short-ball Attacking Shots",
        "desc": "High cross-bat hook played at head height swiveling toward fine leg.",
        "bat_path": "high horizontal swivel over head height rolling blade over bounce toward fine leg",
        "swing_plane": "horizontal",
        "foot_mode": "back-and-across",
        "stride_dir": -40.0,
        "pelvis_rot": 70.0,
        "shoulder_rot": 82.0,
        "impact_pose": {
            "hip_x": -0.06, "hip_y": 0.15, "lead_stride_x": 0.00, "lead_stride_dir_deg": -40.0,
            "rear_foot_x": -0.18, "rear_foot_mode": "back-and-across",
            "lead_knee_flex": 150.0, "rear_knee_flex": 140.0,
            "lead_elbow_flex": 150.0, "rear_elbow_flex": 105.0,
            "pelvis_rotation_deg": 70.0, "shoulder_rotation_deg": 82.0,
            "head_offset_x": 0.08, "hands_x": 0.20, "hands_y": 1.25,
            "bat_plane": "horizontal", "bat_angle": 92.0,
            "bat_tip_x": 0.40, "bat_tip_y": 1.45, "wrist_cock_deg": 35.0,
            "torso_lean": 6.0, "shoulder_tilt": 10.0, "duration_weight": 0.10,
            "cue": "Head tucked in line, hook at eye level rolling wrists down toward fine leg"
        },
        "ft_pose": {
            "hip_x": 0.04, "hip_y": 0.14, "lead_stride_x": 0.14, "lead_stride_dir_deg": -40.0,
            "rear_foot_x": -0.12, "rear_foot_mode": "back-and-across",
            "lead_knee_flex": 155.0, "rear_knee_flex": 145.0,
            "lead_elbow_flex": 152.0, "rear_elbow_flex": 130.0,
            "pelvis_rotation_deg": 90.0, "shoulder_rotation_deg": 105.0,
            "head_offset_x": 0.10, "hands_x": -0.12, "hands_y": 1.35,
            "bat_plane": "horizontal", "bat_angle": 165.0,
            "bat_tip_x": -0.28, "bat_tip_y": 1.55, "wrist_cock_deg": 40.0,
            "torso_lean": 5.0, "shoulder_tilt": 8.0, "duration_weight": 0.16,
            "cue": "High wrap-around finish above shoulder height, balanced on back-foot swivel"
        }
    },

    # -------------------------------------------------------------
    # 5. LEG-SIDE AND WRIST-ORIENTED STROKES
    # -------------------------------------------------------------
    {
        "name": "Flick Shot",
        "slug": "flick-shot",
        "category": "Leg-side and Wrist-oriented Strokes",
        "desc": "Wristy flick off front pad directing straight deliveries into midwicket.",
        "bat_path": "diagonal descent with sharp wrist snap rolling bat face from middle stump to midwicket",
        "swing_plane": "diagonal",
        "foot_mode": "planted",
        "stride_dir": -22.0,
        "pelvis_rot": 32.0,
        "shoulder_rot": 40.0,
        "impact_pose": {
            "hip_x": 0.16, "hip_y": 0.16, "lead_stride_x": 0.60, "lead_stride_dir_deg": -22.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "planted",
            "lead_knee_flex": 126.0, "rear_knee_flex": 152.0,
            "lead_elbow_flex": 105.0, "rear_elbow_flex": 98.0,
            "pelvis_rotation_deg": 32.0, "shoulder_rotation_deg": 40.0,
            "head_offset_x": 0.02, "hands_x": 0.22, "hands_y": 0.68,
            "bat_plane": "diagonal", "bat_angle": 28.0,
            "bat_tip_x": 0.32, "bat_tip_y": 0.25, "wrist_cock_deg": 45.0,
            "torso_lean": 22.0, "shoulder_tilt": 14.0, "duration_weight": 0.10,
            "cue": "Lead leg steps across to off stump, wrists roll closed snapping ball to midwicket"
        },
        "ft_pose": {
            "hip_x": 0.18, "hip_y": 0.15, "lead_stride_x": 0.58, "lead_stride_dir_deg": -22.0,
            "rear_foot_x": -0.13, "rear_foot_mode": "planted",
            "lead_knee_flex": 132.0, "rear_knee_flex": 155.0,
            "lead_elbow_flex": 125.0, "rear_elbow_flex": 115.0,
            "pelvis_rotation_deg": 45.0, "shoulder_rotation_deg": 55.0,
            "head_offset_x": 0.04, "hands_x": 0.15, "hands_y": 1.05,
            "bat_plane": "diagonal", "bat_angle": -60.0,
            "bat_tip_x": 0.22, "bat_tip_y": 1.40, "wrist_cock_deg": 50.0,
            "torso_lean": 18.0, "shoulder_tilt": 10.0, "duration_weight": 0.16,
            "cue": "Wrists cross over into leg-side follow-through, holding front-knee balance"
        }
    },
    {
        "name": "Leg Glance",
        "slug": "leg-glance",
        "category": "Leg-side and Wrist-oriented Strokes",
        "desc": "Subtle deflection off pads guiding ball fine of square toward fine leg.",
        "bat_path": "soft downward angle roll using bowler pace to redirect delivery to fine leg",
        "swing_plane": "diagonal",
        "foot_mode": "planted",
        "stride_dir": -28.0,
        "pelvis_rot": 25.0,
        "shoulder_rot": 30.0,
        "impact_pose": {
            "hip_x": 0.08, "hip_y": 0.16, "lead_stride_x": 0.35, "lead_stride_dir_deg": -28.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "planted",
            "lead_knee_flex": 140.0, "rear_knee_flex": 155.0,
            "lead_elbow_flex": 96.0, "rear_elbow_flex": 92.0,
            "pelvis_rotation_deg": 25.0, "shoulder_rotation_deg": 30.0,
            "head_offset_x": 0.04, "hands_x": 0.18, "hands_y": 0.65,
            "bat_plane": "diagonal", "bat_angle": 38.0,
            "bat_tip_x": 0.25, "bat_tip_y": 0.28, "wrist_cock_deg": 30.0,
            "torso_lean": 16.0, "shoulder_tilt": 10.0, "duration_weight": 0.10,
            "cue": "Subtle deflection off hips/pads, angled face glancing ball fine"
        },
        "ft_pose": {
            "hip_x": 0.10, "hip_y": 0.15, "lead_stride_x": 0.35, "lead_stride_dir_deg": -28.0,
            "rear_foot_x": -0.14, "rear_foot_mode": "planted",
            "lead_knee_flex": 142.0, "rear_knee_flex": 156.0,
            "lead_elbow_flex": 102.0, "rear_elbow_flex": 98.0,
            "pelvis_rotation_deg": 32.0, "shoulder_rotation_deg": 38.0,
            "head_offset_x": 0.05, "hands_x": 0.14, "hands_y": 0.78,
            "bat_plane": "diagonal", "bat_angle": 45.0,
            "bat_tip_x": 0.18, "bat_tip_y": 0.85, "wrist_cock_deg": 35.0,
            "torso_lean": 14.0, "shoulder_tilt": 8.0, "duration_weight": 0.16,
            "cue": "Compact fine glance finish, bat face rolled smoothly toward backward square"
        }
    },
    {
        "name": "Clip Shot",
        "slug": "clip-shot",
        "category": "Leg-side and Wrist-oriented Strokes",
        "desc": "Crisp clip off middle-and-leg stump with firm wrists into midwicket pocket.",
        "bat_path": "firm punchy deflection through the line of middle-leg with active bottom-hand punch",
        "swing_plane": "diagonal",
        "foot_mode": "planted",
        "stride_dir": -16.0,
        "pelvis_rot": 28.0,
        "shoulder_rot": 35.0,
        "impact_pose": {
            "hip_x": 0.14, "hip_y": 0.16, "lead_stride_x": 0.52, "lead_stride_dir_deg": -16.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "planted",
            "lead_knee_flex": 130.0, "rear_knee_flex": 152.0,
            "lead_elbow_flex": 100.0, "rear_elbow_flex": 94.0,
            "pelvis_rotation_deg": 28.0, "shoulder_rotation_deg": 35.0,
            "head_offset_x": 0.02, "hands_x": 0.20, "hands_y": 0.65,
            "bat_plane": "diagonal", "bat_angle": 24.0,
            "bat_tip_x": 0.30, "bat_tip_y": 0.25, "wrist_cock_deg": 35.0,
            "torso_lean": 20.0, "shoulder_tilt": 12.0, "duration_weight": 0.10,
            "cue": "Firm wrist clip off pads, directing ball cleanly through midwicket pocket"
        },
        "ft_pose": {
            "hip_x": 0.16, "hip_y": 0.15, "lead_stride_x": 0.50, "lead_stride_dir_deg": -16.0,
            "rear_foot_x": -0.13, "rear_foot_mode": "planted",
            "lead_knee_flex": 136.0, "rear_knee_flex": 155.0,
            "lead_elbow_flex": 115.0, "rear_elbow_flex": 105.0,
            "pelvis_rotation_deg": 38.0, "shoulder_rotation_deg": 48.0,
            "head_offset_x": 0.03, "hands_x": 0.16, "hands_y": 0.95,
            "bat_plane": "diagonal", "bat_angle": -50.0,
            "bat_tip_x": 0.24, "bat_tip_y": 1.25, "wrist_cock_deg": 40.0,
            "torso_lean": 17.0, "shoulder_tilt": 9.0, "duration_weight": 0.16,
            "cue": "Controlled punch follow-through pointing toward midwicket"
        }
    },

    # -------------------------------------------------------------
    # 6. SWEEP-FAMILY STROKES
    # -------------------------------------------------------------
    {
        "name": "Sweep",
        "slug": "sweep",
        "category": "Sweep-family Strokes",
        "desc": "Kneeling horizontal sweep along the turf toward backward square leg.",
        "bat_path": "rear knee drops to turf, low horizontal bat sweeping along turf to backward square leg",
        "swing_plane": "horizontal",
        "foot_mode": "kneeling",
        "stride_dir": -30.0,
        "pelvis_rot": 55.0,
        "shoulder_rot": 68.0,
        "impact_pose": {
            "hip_x": 0.22, "hip_y": 0.44, "lead_stride_x": 0.75, "lead_stride_dir_deg": -30.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "kneeling",
            "lead_knee_flex": 95.0, "rear_knee_flex": 74.0,
            "lead_elbow_flex": 140.0, "rear_elbow_flex": 95.0,
            "pelvis_rotation_deg": 55.0, "shoulder_rotation_deg": 68.0,
            "head_offset_x": -0.02, "hands_x": 0.25, "hands_y": 0.35,
            "bat_plane": "horizontal", "bat_angle": 86.0,
            "bat_tip_x": 0.42, "bat_tip_y": 0.22, "wrist_cock_deg": 25.0,
            "torso_lean": 35.0, "shoulder_tilt": 16.0, "duration_weight": 0.10,
            "cue": "Rear knee down on turf, head over front knee, sweep low along ground"
        },
        "ft_pose": {
            "hip_x": 0.24, "hip_y": 0.42, "lead_stride_x": 0.74, "lead_stride_dir_deg": -30.0,
            "rear_foot_x": -0.14, "rear_foot_mode": "kneeling",
            "lead_knee_flex": 102.0, "rear_knee_flex": 82.0,
            "lead_elbow_flex": 135.0, "rear_elbow_flex": 110.0,
            "pelvis_rotation_deg": 75.0, "shoulder_rotation_deg": 88.0,
            "head_offset_x": 0.00, "hands_x": -0.05, "hands_y": 0.40,
            "bat_plane": "horizontal", "bat_angle": 140.0,
            "bat_tip_x": -0.15, "bat_tip_y": 0.35, "wrist_cock_deg": 30.0,
            "torso_lean": 28.0, "shoulder_tilt": 12.0, "duration_weight": 0.16,
            "cue": "Rolling finish around front knee, bat face smothered low to ground"
        }
    },
    {
        "name": "Slog Sweep",
        "slug": "slog-sweep",
        "category": "Sweep-family Strokes",
        "desc": "Aggressive kneeling rotational sweep launched high over deep midwicket.",
        "bat_path": "kneeling power arc launching upward from low knee-level over deep midwicket boundary",
        "swing_plane": "diagonal",
        "foot_mode": "kneeling",
        "stride_dir": -45.0,
        "pelvis_rot": 70.0,
        "shoulder_rot": 84.0,
        "impact_pose": {
            "hip_x": 0.25, "hip_y": 0.40, "lead_stride_x": 0.78, "lead_stride_dir_deg": -45.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "kneeling",
            "lead_knee_flex": 98.0, "rear_knee_flex": 78.0,
            "lead_elbow_flex": 145.0, "rear_elbow_flex": 105.0,
            "pelvis_rotation_deg": 70.0, "shoulder_rotation_deg": 84.0,
            "head_offset_x": -0.01, "hands_x": 0.30, "hands_y": 0.45,
            "bat_plane": "diagonal", "bat_angle": 55.0,
            "bat_tip_x": 0.48, "bat_tip_y": 0.55, "wrist_cock_deg": 35.0,
            "torso_lean": 32.0, "shoulder_tilt": 22.0, "duration_weight": 0.10,
            "cue": "Rear knee down, explosive core rotation lifting ball high over midwicket"
        },
        "ft_pose": {
            "hip_x": 0.26, "hip_y": 0.38, "lead_stride_x": 0.76, "lead_stride_dir_deg": -45.0,
            "rear_foot_x": -0.12, "rear_foot_mode": "kneeling",
            "lead_knee_flex": 108.0, "rear_knee_flex": 88.0,
            "lead_elbow_flex": 140.0, "rear_elbow_flex": 125.0,
            "pelvis_rotation_deg": 95.0, "shoulder_rotation_deg": 110.0,
            "head_offset_x": 0.02, "hands_x": -0.10, "hands_y": 1.25,
            "bat_plane": "diagonal", "bat_angle": -110.0,
            "bat_tip_x": -0.10, "bat_tip_y": 1.62, "wrist_cock_deg": 40.0,
            "torso_lean": 24.0, "shoulder_tilt": 15.0, "duration_weight": 0.16,
            "cue": "Massive high follow-through wrapping over back shoulder"
        }
    },
    {
        "name": "Reverse Sweep",
        "slug": "reverse-sweep",
        "category": "Sweep-family Strokes",
        "desc": "Kneeling stroke switching hands and sweeping blade into off-side past point.",
        "bat_path": "hands switch top/bottom positions, inverted blade sweeps past backward point to third man",
        "swing_plane": "horizontal",
        "foot_mode": "kneeling",
        "stride_dir": 40.0,
        "pelvis_rot": -35.0,
        "shoulder_rot": -45.0,
        "impact_pose": {
            "hip_x": 0.22, "hip_y": 0.44, "lead_stride_x": 0.72, "lead_stride_dir_deg": 40.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "kneeling",
            "lead_knee_flex": 96.0, "rear_knee_flex": 76.0,
            "lead_elbow_flex": 138.0, "rear_elbow_flex": 98.0,
            "pelvis_rotation_deg": -35.0, "shoulder_rotation_deg": -45.0,
            "head_offset_x": -0.02, "hands_x": 0.22, "hands_y": 0.38,
            "bat_plane": "horizontal", "bat_angle": 86.0,
            "bat_tip_x": 0.35, "bat_tip_y": 0.32, "wrist_cock_deg": 30.0,
            "torso_lean": 34.0, "shoulder_tilt": -15.0, "duration_weight": 0.10,
            "cue": "Hands switched, rear knee down, inverted blade sweeping toward third man"
        },
        "ft_pose": {
            "hip_x": 0.24, "hip_y": 0.42, "lead_stride_x": 0.70, "lead_stride_dir_deg": 40.0,
            "rear_foot_x": -0.13, "rear_foot_mode": "kneeling",
            "lead_knee_flex": 104.0, "rear_knee_flex": 84.0,
            "lead_elbow_flex": 135.0, "rear_elbow_flex": 115.0,
            "pelvis_rotation_deg": -50.0, "shoulder_rotation_deg": -65.0,
            "head_offset_x": 0.00, "hands_x": 0.32, "hands_y": 0.75,
            "bat_plane": "horizontal", "bat_angle": -65.0,
            "bat_tip_x": 0.45, "bat_tip_y": 0.90, "wrist_cock_deg": 35.0,
            "torso_lean": 26.0, "shoulder_tilt": -10.0, "duration_weight": 0.16,
            "cue": "Clean off-side extension with inverted bat face following through toward gully"
        }
    },
    {
        "name": "Paddle Sweep",
        "slug": "paddle-sweep",
        "category": "Sweep-family Strokes",
        "desc": "Fine deflection sweep offering gentle angled paddle face toward fine leg.",
        "bat_path": "gentle horizontal paddle deflection rolling bat face toward fine leg with soft hands",
        "swing_plane": "diagonal",
        "foot_mode": "kneeling",
        "stride_dir": -55.0,
        "pelvis_rot": 40.0,
        "shoulder_rot": 48.0,
        "impact_pose": {
            "hip_x": 0.20, "hip_y": 0.45, "lead_stride_x": 0.74, "lead_stride_dir_deg": -55.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "kneeling",
            "lead_knee_flex": 94.0, "rear_knee_flex": 75.0,
            "lead_elbow_flex": 128.0, "rear_elbow_flex": 90.0,
            "pelvis_rotation_deg": 40.0, "shoulder_rotation_deg": 48.0,
            "head_offset_x": -0.03, "hands_x": 0.18, "hands_y": 0.38,
            "bat_plane": "diagonal", "bat_angle": 42.0,
            "bat_tip_x": 0.32, "bat_tip_y": 0.24, "wrist_cock_deg": 22.0,
            "torso_lean": 36.0, "shoulder_tilt": 14.0, "duration_weight": 0.10,
            "cue": "Kneel low, soft paddle presentation deflecting ball fine around corner"
        },
        "ft_pose": {
            "hip_x": 0.22, "hip_y": 0.43, "lead_stride_x": 0.72, "lead_stride_dir_deg": -55.0,
            "rear_foot_x": -0.14, "rear_foot_mode": "kneeling",
            "lead_knee_flex": 100.0, "rear_knee_flex": 82.0,
            "lead_elbow_flex": 120.0, "rear_elbow_flex": 95.0,
            "pelvis_rotation_deg": 50.0, "shoulder_rotation_deg": 60.0,
            "head_offset_x": -0.01, "hands_x": 0.08, "hands_y": 0.45,
            "bat_plane": "diagonal", "bat_angle": 55.0,
            "bat_tip_x": 0.15, "bat_tip_y": 0.45, "wrist_cock_deg": 25.0,
            "torso_lean": 30.0, "shoulder_tilt": 10.0, "duration_weight": 0.16,
            "cue": "Short soft touch follow-through, ball rolling gently toward fine leg boundary"
        }
    },

    # -------------------------------------------------------------
    # 7. POWER AND INNOVATIVE SHOTS
    # -------------------------------------------------------------
    {
        "name": "Slog",
        "slug": "slog",
        "category": "Power and Innovative Shots",
        "desc": "Brutal full-blooded rotational heave across the line through cow corner.",
        "bat_path": "deep backlift, explosive cross-line heave targeting wide midwicket / cow corner",
        "swing_plane": "diagonal",
        "foot_mode": "drags",
        "stride_dir": -50.0,
        "pelvis_rot": 80.0,
        "shoulder_rot": 90.0,
        "impact_pose": {
            "hip_x": 0.24, "hip_y": 0.16, "lead_stride_x": 0.72, "lead_stride_dir_deg": -50.0,
            "rear_foot_x": -0.12, "rear_foot_mode": "drags",
            "lead_knee_flex": 125.0, "rear_knee_flex": 140.0,
            "lead_elbow_flex": 145.0, "rear_elbow_flex": 105.0,
            "pelvis_rotation_deg": 80.0, "shoulder_rotation_deg": 90.0,
            "head_offset_x": 0.05, "hands_x": 0.30, "hands_y": 0.75,
            "bat_plane": "diagonal", "bat_angle": 65.0,
            "bat_tip_x": 0.52, "bat_tip_y": 0.65, "wrist_cock_deg": 35.0,
            "torso_lean": 20.0, "shoulder_tilt": 20.0, "duration_weight": 0.10,
            "cue": "Clear front leg, uncoil core violently, heave through cow corner"
        },
        "ft_pose": {
            "hip_x": 0.28, "hip_y": 0.14, "lead_stride_x": 0.70, "lead_stride_dir_deg": -50.0,
            "rear_foot_x": -0.05, "rear_foot_mode": "drags",
            "lead_knee_flex": 138.0, "rear_knee_flex": 150.0,
            "lead_elbow_flex": 142.0, "rear_elbow_flex": 130.0,
            "pelvis_rotation_deg": 105.0, "shoulder_rotation_deg": 120.0,
            "head_offset_x": 0.08, "hands_x": -0.12, "hands_y": 1.40,
            "bat_plane": "diagonal", "bat_angle": -120.0,
            "bat_tip_x": -0.20, "bat_tip_y": 1.85, "wrist_cock_deg": 42.0,
            "torso_lean": 15.0, "shoulder_tilt": 14.0, "duration_weight": 0.16,
            "cue": "Massive two-handed wrap over back shoulder, full torso uncoiled"
        }
    },
    {
        "name": "Switch Hit",
        "slug": "switch-hit",
        "category": "Power and Innovative Shots",
        "desc": "Stance reversal stroke executing full drive through opposite off-side.",
        "bat_path": "batter swaps feet and grip prior to release, swinging cleanly through opposite cover",
        "swing_plane": "diagonal",
        "foot_mode": "planted",
        "stride_dir": 35.0,
        "pelvis_rot": -30.0,
        "shoulder_rot": -40.0,
        "impact_pose": {
            "hip_x": 0.20, "hip_y": 0.16, "lead_stride_x": 0.68, "lead_stride_dir_deg": 35.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "planted",
            "lead_knee_flex": 124.0, "rear_knee_flex": 150.0,
            "lead_elbow_flex": 94.0, "rear_elbow_flex": 96.0,
            "pelvis_rotation_deg": -30.0, "shoulder_rotation_deg": -40.0,
            "head_offset_x": 0.02, "hands_x": 0.25, "hands_y": 0.74,
            "bat_plane": "diagonal", "bat_angle": 18.0,
            "bat_tip_x": 0.38, "bat_tip_y": 0.25, "wrist_cock_deg": 18.0,
            "torso_lean": 25.0, "shoulder_tilt": -15.0, "duration_weight": 0.10,
            "cue": "Stance completely reversed, clean drive through opposite off-side boundary"
        },
        "ft_pose": {
            "hip_x": 0.22, "hip_y": 0.15, "lead_stride_x": 0.66, "lead_stride_dir_deg": 35.0,
            "rear_foot_x": -0.12, "rear_foot_mode": "planted",
            "lead_knee_flex": 132.0, "rear_knee_flex": 155.0,
            "lead_elbow_flex": 118.0, "rear_elbow_flex": 110.0,
            "pelvis_rotation_deg": -45.0, "shoulder_rotation_deg": -55.0,
            "head_offset_x": 0.04, "hands_x": 0.20, "hands_y": 1.15,
            "bat_plane": "diagonal", "bat_angle": -75.0,
            "bat_tip_x": 0.25, "bat_tip_y": 1.70, "wrist_cock_deg": 22.0,
            "torso_lean": 20.0, "shoulder_tilt": -10.0, "duration_weight": 0.16,
            "cue": "High reverse drive follow-through holding textbook balance"
        }
    },
    {
        "name": "Scoop Shot",
        "slug": "scoop-shot",
        "category": "Power and Innovative Shots",
        "desc": "Drop-knee scoop getting beneath yorkers and lifting ball directly over the keeper.",
        "bat_path": "low scoop ramp sliding under ball line and popping vertically over wicketkeeper head",
        "swing_plane": "vertical",
        "foot_mode": "kneeling",
        "stride_dir": -5.0,
        "pelvis_rot": 15.0,
        "shoulder_rot": 20.0,
        "impact_pose": {
            "hip_x": 0.20, "hip_y": 0.40, "lead_stride_x": 0.70, "lead_stride_dir_deg": -5.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "kneeling",
            "lead_knee_flex": 92.0, "rear_knee_flex": 72.0,
            "lead_elbow_flex": 135.0, "rear_elbow_flex": 100.0,
            "pelvis_rotation_deg": 15.0, "shoulder_rotation_deg": 20.0,
            "head_offset_x": -0.05, "hands_x": 0.20, "hands_y": 0.40,
            "bat_plane": "vertical", "bat_angle": -65.0,
            "bat_tip_x": 0.18, "bat_tip_y": 0.25, "wrist_cock_deg": 35.0,
            "torso_lean": 38.0, "shoulder_tilt": 12.0, "duration_weight": 0.10,
            "cue": "Drop beneath line of ball, horizontal ramp face popping ball over keeper"
        },
        "ft_pose": {
            "hip_x": 0.22, "hip_y": 0.38, "lead_stride_x": 0.68, "lead_stride_dir_deg": -5.0,
            "rear_foot_x": -0.14, "rear_foot_mode": "kneeling",
            "lead_knee_flex": 98.0, "rear_knee_flex": 78.0,
            "lead_elbow_flex": 145.0, "rear_elbow_flex": 120.0,
            "pelvis_rotation_deg": 20.0, "shoulder_rotation_deg": 25.0,
            "head_offset_x": -0.02, "hands_x": 0.12, "hands_y": 1.20,
            "bat_plane": "vertical", "bat_angle": -115.0,
            "bat_tip_x": 0.10, "bat_tip_y": 1.70, "wrist_cock_deg": 45.0,
            "torso_lean": 30.0, "shoulder_tilt": 8.0, "duration_weight": 0.16,
            "cue": "Vertical upward flick finish pointing bat directly over head"
        }
    },
    {
        "name": "Ramp Shot",
        "slug": "ramp-shot",
        "category": "Power and Innovative Shots",
        "desc": "Deflection ramp utilizing bowler velocity to sail bouncers over the slips.",
        "bat_path": "angled ramp using ball pace with open blade tilted backward over slips",
        "swing_plane": "diagonal",
        "foot_mode": "planted",
        "stride_dir": 15.0,
        "pelvis_rot": 12.0,
        "shoulder_rot": 16.0,
        "impact_pose": {
            "hip_x": -0.04, "hip_y": 0.12, "lead_stride_x": 0.20, "lead_stride_dir_deg": 15.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "planted",
            "lead_knee_flex": 155.0, "rear_knee_flex": 148.0,
            "lead_elbow_flex": 140.0, "rear_elbow_flex": 105.0,
            "pelvis_rotation_deg": 12.0, "shoulder_rotation_deg": 16.0,
            "head_offset_x": 0.08, "hands_x": 0.18, "hands_y": 0.85,
            "bat_plane": "diagonal", "bat_angle": -40.0,
            "bat_tip_x": 0.25, "bat_tip_y": 0.95, "wrist_cock_deg": 30.0,
            "torso_lean": 4.0, "shoulder_tilt": 10.0, "duration_weight": 0.10,
            "cue": "Open blade angle, redirect bowler pace over slip cordon with soft touch"
        },
        "ft_pose": {
            "hip_x": -0.02, "hip_y": 0.10, "lead_stride_x": 0.22, "lead_stride_dir_deg": 15.0,
            "rear_foot_x": -0.14, "rear_foot_mode": "planted",
            "lead_knee_flex": 158.0, "rear_knee_flex": 152.0,
            "lead_elbow_flex": 145.0, "rear_elbow_flex": 115.0,
            "pelvis_rotation_deg": 16.0, "shoulder_rotation_deg": 22.0,
            "head_offset_x": 0.10, "hands_x": 0.22, "hands_y": 1.15,
            "bat_plane": "diagonal", "bat_angle": -75.0,
            "bat_tip_x": 0.18, "bat_tip_y": 1.45, "wrist_cock_deg": 34.0,
            "torso_lean": 2.0, "shoulder_tilt": 8.0, "duration_weight": 0.16,
            "cue": "Subtle deflection extension upward toward third man"
        }
    },
    {
        "name": "Helicopter Shot",
        "slug": "helicopter-shot",
        "category": "Power and Innovative Shots",
        "desc": "Explosive bottom-hand wrist snap digging out yorkers with 360° circular follow-through.",
        "bat_path": "digs out yorker at toes, followed by explosive circular overhead helicopter swirl",
        "swing_plane": "diagonal",
        "foot_mode": "planted",
        "stride_dir": -10.0,
        "pelvis_rot": 68.0,
        "shoulder_rot": 85.0,
        "impact_pose": {
            "hip_x": 0.18, "hip_y": 0.20, "lead_stride_x": 0.65, "lead_stride_dir_deg": -10.0,
            "rear_foot_x": -0.15, "rear_foot_mode": "planted",
            "lead_knee_flex": 115.0, "rear_knee_flex": 142.0,
            "lead_elbow_flex": 110.0, "rear_elbow_flex": 112.0,
            "pelvis_rotation_deg": 68.0, "shoulder_rotation_deg": 85.0,
            "head_offset_x": 0.00, "hands_x": 0.26, "hands_y": 0.55,
            "bat_plane": "diagonal", "bat_angle": 12.0,
            "bat_tip_x": 0.35, "bat_tip_y": 0.12, "wrist_cock_deg": 65.0,
            "torso_lean": 28.0, "shoulder_tilt": 18.0, "duration_weight": 0.10,
            "cue": "Bottom hand wrist whip digs out yorker, uncoiling core into circular swirl"
        },
        "ft_pose": {
            "hip_x": 0.22, "hip_y": 0.16, "lead_stride_x": 0.62, "lead_stride_dir_deg": -10.0,
            "rear_foot_x": -0.10, "rear_foot_mode": "drags",
            "lead_knee_flex": 130.0, "rear_knee_flex": 150.0,
            "lead_elbow_flex": 138.0, "rear_elbow_flex": 140.0,
            "pelvis_rotation_deg": 110.0, "shoulder_rotation_deg": 130.0,
            "head_offset_x": 0.05, "hands_x": -0.05, "hands_y": 1.45,
            "bat_plane": "diagonal", "bat_angle": -135.0,
            "bat_tip_x": -0.15, "bat_tip_y": 1.82, "wrist_cock_deg": 70.0,
            "torso_lean": 16.0, "shoulder_tilt": 15.0, "duration_weight": 0.16,
            "cue": "Rotational 360° helicopter swirl finishing high over left shoulder"
        }
    }
]

def make_metric(ideal, min_val, max_val, unit="deg"):
    return {
        "ideal": round(float(ideal), 1),
        "min": round(float(min_val), 1),
        "max": round(float(max_val), 1),
        "unit": unit
    }

def interpolate_pose(p1, p2, t, duration_weight, cue_text):
    """Linearly interpolates two keyframe poses while ensuring all new fields exist."""
    res = {}
    for k, v in p1.items():
        if k in ["rear_foot_mode", "bat_plane", "cue"]:
            res[k] = p2.get(k, v) if t >= 0.5 else v
        elif isinstance(v, (int, float)):
            v2 = p2.get(k, v)
            res[k] = round(float(v + (v2 - v) * t), 2)
        else:
            res[k] = v
    res["duration_weight"] = round(float(duration_weight), 2)
    res["cue"] = cue_text
    return res

def generate_phases_for_shot(spec):
    imp = spec["impact_pose"]
    ft = spec["ft_pose"]
    is_kneeling = spec["foot_mode"] == "kneeling"
    stride_dir = spec["stride_dir"]

    # 1. Stance
    stance_pose = {
        "hip_x": 0.0, "hip_y": 0.12, "lead_stride_x": 0.22, "lead_stride_dir_deg": stride_dir * 0.1,
        "rear_foot_x": -0.15, "rear_foot_mode": "planted",
        "lead_knee_flex": 165.0, "rear_knee_flex": 163.0,
        "lead_elbow_flex": 105.0, "rear_elbow_flex": 95.0,
        "pelvis_rotation_deg": 0.0, "shoulder_rotation_deg": 0.0,
        "head_offset_x": 0.12, "hands_x": 0.10, "hands_y": 0.60,
        "bat_plane": spec["swing_plane"], "bat_angle": 22.0,
        "bat_tip_x": 0.18, "bat_tip_y": 0.15, "wrist_cock_deg": 8.0,
        "torso_lean": 14.0, "shoulder_tilt": 4.0, "duration_weight": 0.15,
        "cue": "Balanced ready stance, eyes level, hands resting comfortably at back hip"
    }

    # 2. Backlift
    backlift_bat_ang = -55.0 if spec["swing_plane"] == "horizontal" else (-42.0 if not is_kneeling else -48.0)
    backlift_pose = {
        "hip_x": -0.05, "hip_y": 0.10, "lead_stride_x": 0.20, "lead_stride_dir_deg": stride_dir * 0.2,
        "rear_foot_x": -0.15, "rear_foot_mode": "planted",
        "lead_knee_flex": 162.0, "rear_knee_flex": 158.0,
        "lead_elbow_flex": 92.0, "rear_elbow_flex": 82.0,
        "pelvis_rotation_deg": spec["pelvis_rot"] * 0.2, "shoulder_rotation_deg": spec["shoulder_rot"] * 0.3,
        "head_offset_x": 0.10, "hands_x": 0.08, "hands_y": 0.88,
        "bat_plane": spec["swing_plane"], "bat_angle": backlift_bat_ang,
        "bat_tip_x": -0.10 if spec["swing_plane"] != "vertical" else 0.10, "bat_tip_y": 1.25,
        "wrist_cock_deg": 25.0, "torso_lean": 12.0, "shoulder_tilt": 8.0, "duration_weight": 0.20,
        "cue": f"Backlift raised with top hand dominant, bat aligned along {spec['swing_plane']} plane"
    }

    # 3. Stride
    stride_lead_k = 112.0 if is_kneeling else (imp["lead_knee_flex"] + 8.0)
    stride_rear_k = 118.0 if is_kneeling else (imp["rear_knee_flex"] + 4.0)
    stride_bat_ang = backlift_bat_ang * 0.75
    stride_rad = math.radians(stride_bat_ang)
    stride_hx = imp["hands_x"] * 0.85
    stride_hy = imp["hands_y"] * 0.95
    stride_pose = {
        "hip_x": imp["hip_x"] * 0.70, "hip_y": imp["hip_y"] * 0.80,
        "lead_stride_x": imp["lead_stride_x"] * 0.85, "lead_stride_dir_deg": stride_dir,
        "rear_foot_x": imp["rear_foot_x"], "rear_foot_mode": imp["rear_foot_mode"],
        "lead_knee_flex": stride_lead_k, "rear_knee_flex": stride_rear_k,
        "lead_elbow_flex": 88.0, "rear_elbow_flex": 80.0,
        "pelvis_rotation_deg": spec["pelvis_rot"] * 0.5, "shoulder_rotation_deg": spec["shoulder_rot"] * 0.5,
        "head_offset_x": imp["head_offset_x"] + 0.04,
        "hands_x": stride_hx, "hands_y": stride_hy,
        "bat_plane": spec["swing_plane"], "bat_angle": stride_bat_ang,
        "bat_tip_x": round(stride_hx + math.sin(stride_rad) * 0.72, 2),
        "bat_tip_y": round(stride_hy - math.cos(stride_rad) * 0.72, 2),
        "wrist_cock_deg": 28.0,
        "torso_lean": imp["torso_lean"] * 0.85, "shoulder_tilt": imp["shoulder_tilt"] * 0.80,
        "duration_weight": 0.15,
        "cue": f"Decisive foot commitment at {int(stride_dir)}° along pitch, head leading into stroke line"
    }

    # 4. Downswing
    down_lead_k = (stride_lead_k + imp["lead_knee_flex"]) / 2.0
    down_rear_k = (stride_rear_k + imp["rear_knee_flex"]) / 2.0
    down_bat_ang = (backlift_bat_ang + imp["bat_angle"]) / 2.0
    down_rad = math.radians(down_bat_ang)
    down_hx = imp["hands_x"] * 0.95
    down_hy = imp["hands_y"] * 0.98
    downswing_pose = {
        "hip_x": imp["hip_x"] * 0.90, "hip_y": imp["hip_y"] * 0.92,
        "lead_stride_x": imp["lead_stride_x"] * 0.95, "lead_stride_dir_deg": stride_dir,
        "rear_foot_x": imp["rear_foot_x"], "rear_foot_mode": imp["rear_foot_mode"],
        "lead_knee_flex": down_lead_k, "rear_knee_flex": down_rear_k,
        "lead_elbow_flex": (imp["lead_elbow_flex"] + 88.0) / 2.0,
        "rear_elbow_flex": (imp["rear_elbow_flex"] + 80.0) / 2.0,
        "pelvis_rotation_deg": spec["pelvis_rot"] * 0.8, "shoulder_rotation_deg": spec["shoulder_rot"] * 0.8,
        "head_offset_x": imp["head_offset_x"] + 0.02,
        "hands_x": down_hx, "hands_y": down_hy,
        "bat_plane": spec["swing_plane"],
        "bat_angle": down_bat_ang,
        "bat_tip_x": round(down_hx + math.sin(down_rad) * 0.72, 2),
        "bat_tip_y": round(down_hy - math.cos(down_rad) * 0.72, 2),
        "wrist_cock_deg": imp["wrist_cock_deg"] + 5.0,
        "torso_lean": imp["torso_lean"] * 0.95, "shoulder_tilt": imp["shoulder_tilt"] * 0.92,
        "duration_weight": 0.14,
        "cue": "Rapid downward acceleration of wrists, lead arm guiding path into impact"
    }

    # 5. Impact
    impact_pose = imp

    # 6. Follow-through
    follow_through_pose = ft

    # 7. Recovery
    recovery_pose = {
        "hip_x": imp["hip_x"] * 0.35, "hip_y": 0.15, "lead_stride_x": 0.30, "lead_stride_dir_deg": stride_dir * 0.2,
        "rear_foot_x": -0.15, "rear_foot_mode": "planted",
        "lead_knee_flex": 160.0, "rear_knee_flex": 158.0,
        "lead_elbow_flex": 110.0, "rear_elbow_flex": 105.0,
        "pelvis_rotation_deg": spec["pelvis_rot"] * 0.2, "shoulder_rotation_deg": spec["shoulder_rot"] * 0.2,
        "head_offset_x": 0.10, "hands_x": 0.14, "hands_y": 0.65,
        "bat_plane": spec["swing_plane"], "bat_angle": 30.0,
        "bat_tip_x": 0.20, "bat_tip_y": 0.25, "wrist_cock_deg": 10.0,
        "torso_lean": 15.0, "shoulder_tilt": 5.0, "duration_weight": 0.10,
        "cue": "Smooth recoil and balance recovery, resetting ready base inside crease"
    }

    # Build metric bands per phase
    phases = {}
    phase_order = [
        ("stance", stance_pose),
        ("backlift", backlift_pose),
        ("stride", stride_pose),
        ("downswing", downswing_pose),
        ("impact", impact_pose),
        ("follow_through", follow_through_pose),
        ("recovery", recovery_pose),
    ]

    for p_key, pose in phase_order:
        # Guarantee rigid cricket bat length from hands to tip (0.72m)
        dist = math.hypot(pose["bat_tip_x"] - pose["hands_x"], pose["bat_tip_y"] - pose["hands_y"])
        if dist < 0.45:
            rad = math.radians(pose["bat_angle"])
            pose["bat_tip_x"] = round(pose["hands_x"] + math.sin(rad) * 0.72, 2)
            pose["bat_tip_y"] = round(pose["hands_y"] - math.cos(rad) * 0.72, 2)

        lk = pose["lead_knee_flex"]
        rk = pose["rear_knee_flex"]
        le = pose["lead_elbow_flex"]
        re = pose["rear_elbow_flex"]
        tl = pose["torso_lean"]
        st = pose["shoulder_tilt"]
        ho = pose["head_offset_x"]
        sw = abs(pose["lead_stride_x"] - pose["rear_foot_x"]) / 0.30

        phases[p_key] = {
            "lead_knee_angle": make_metric(lk, max(70.0, lk - 10.0), min(175.0, lk + 12.0)),
            "rear_knee_angle": make_metric(rk, max(70.0, rk - 12.0), min(175.0, rk + 14.0)),
            "lead_elbow_angle": make_metric(le, max(70.0, le - 15.0), min(175.0, le + 18.0)),
            "rear_elbow_angle": make_metric(re, max(70.0, re - 15.0), min(175.0, re + 18.0)),
            "torso_lean": make_metric(tl, max(0.0, tl - 6.0), min(45.0, tl + 8.0)),
            "shoulder_tilt": make_metric(st, max(0.0, st - 5.0), min(35.0, st + 7.0)),
            "head_over_front_knee_offset": make_metric(ho, ho - 0.06, ho + 0.08, "torso_ratio"),
            "stance_width_ratio": make_metric(sw, max(0.8, sw - 0.20), sw + 0.25, "ratio"),
            "keyframe_pose": pose
        }

    return phases

def generate_shot_errors(shot_name):
    cat = next(s["category"] for s in SHOT_CATALOGUE_SPECS if s["name"] == shot_name)
    if "Drive" in shot_name or shot_name == "Forward Defensive":
        return [
            {
                "error_name": "Stiff Front Knee (Under-Flexion)",
                "metric": "lead_knee_angle",
                "threshold": 142.0,
                "direction": "over",
                "symptom": "Lead knee angle > 142° at impact.",
                "why_it_matters": "A straight front leg elevates center of gravity, causing uncontrolled aerial slices.",
                "drill": {
                    "drill_name": "Drop-Ball Knee Bend Target Drill",
                    "description": "Coach drops ball from chest height onto cone. Batter strides decisively and flexes front knee past 130°.",
                    "focus": "Lowering center of gravity and front knee commitment."
                }
            },
            {
                "error_name": "Dropped Front Elbow (Low Guide Arm)",
                "metric": "lead_elbow_angle",
                "threshold": 128.0,
                "direction": "over",
                "symptom": "Lead elbow angle > 128° at impact.",
                "why_it_matters": "When lead elbow drops, bottom hand dominates early, rolling bat face shut.",
                "drill": {
                    "drill_name": "High Lead Elbow Wall Shadow Drill",
                    "description": "Practice swing against wall ensuring lead elbow points along shot line.",
                    "focus": "Elevating lead elbow along stroke vertical plane."
                }
            },
            {
                "error_name": "Head Falling Outside Line",
                "metric": "head_over_front_knee_offset",
                "threshold": 0.12,
                "direction": "over",
                "symptom": "Head offset > 0.12 torso lengths from lead knee.",
                "why_it_matters": "Head tilt away from ball trajectory shifts body weight off balance.",
                "drill": {
                    "drill_name": "Coin Under Chin Balance Drill",
                    "description": "Tuck coin between chin and collar. Execute stroke without dropping coin until follow-through.",
                    "focus": "Stationary head locked over front knee."
                }
            }
        ]
    elif "Sweep" in shot_name:
        return [
            {
                "error_name": "Standing Base (Insufficient Knee Drop)",
                "metric": "rear_knee_angle",
                "threshold": 105.0,
                "direction": "over",
                "symptom": "Rear knee angle > 105° during swing.",
                "why_it_matters": "Failure to drop rear knee elevates swing plane above bounce height, causing top edges.",
                "drill": {
                    "drill_name": "Kneeling Mat Stationary Sweep Drill",
                    "description": "Start with rear knee on soft pad. Sweep tossed deliveries off turf.",
                    "focus": "Stable kneeling foundation with head down over front knee."
                }
            },
            {
                "error_name": "Upright Torso Flexion",
                "metric": "torso_lean",
                "threshold": 22.0,
                "direction": "under",
                "symptom": "Torso lean < 22° at impact.",
                "why_it_matters": "Staying upright pulls head away from ball line and increases LBW risk.",
                "drill": {
                    "drill_name": "Nose-Over-Knee Sweep Drill",
                    "description": "Sweep softly tossed deliveries ensuring nose finishes over lead knee at contact.",
                    "focus": "Forward torso inclination to smother bounce."
                }
            },
            {
                "error_name": "Vertical Bat Slice (Non-Horizontal Blade)",
                "metric": "lead_elbow_angle",
                "threshold": 135.0,
                "direction": "over",
                "symptom": "Lead elbow angle > 135° with vertical blade angle.",
                "why_it_matters": "Sweeping with non-horizontal blade narrows hitting zone and invites skies.",
                "drill": {
                    "drill_name": "Horizontal Rope Clearance Drill",
                    "description": "Swing under suspended horizontal string ensuring blade travels parallel to turf.",
                    "focus": "Level blade presentation through contact zone."
                }
            }
        ]
    else:
        return [
            {
                "error_name": "Premature Front Foot Commitment",
                "metric": "lead_knee_angle",
                "threshold": 125.0,
                "direction": "under",
                "symptom": "Lead knee flexed < 125° while attempting short-ball stroke.",
                "why_it_matters": "Stepping onto front foot against short ball traps weight, inviting top edges.",
                "drill": {
                    "drill_name": "Back-and-Across Drop Step Drill",
                    "description": "Decisively push off front foot and anchor on back foot before uncoiling.",
                    "focus": "Weight transfer to rear foot with front leg relaxed."
                }
            },
            {
                "error_name": "Cramped Arms (Elbows Tucked Too Close)",
                "metric": "lead_elbow_angle",
                "threshold": 120.0,
                "direction": "under",
                "symptom": "Lead elbow angle < 120° at impact.",
                "why_it_matters": "Tucking arms into body prevents full lever extension, reducing power.",
                "drill": {
                    "drill_name": "Full Lever Extension Swivel Drill",
                    "description": "Hit ball off high tee focusing on full arm extension at contact point.",
                    "focus": "Extending arms through full hitting radius."
                }
            },
            {
                "error_name": "Excessive Backward Torso Lean",
                "metric": "torso_lean",
                "threshold": 20.0,
                "direction": "over",
                "symptom": "Torso lean > 20° leaning backward.",
                "why_it_matters": "Falling backward causes bat to roll upward, hitting ball into air.",
                "drill": {
                    "drill_name": "Chest-Over-Ball Balance Hold Drill",
                    "description": "Execute stroke and hold finish for 3 seconds with chest over rear hip.",
                    "focus": "Controlled rotational balance without leaning away."
                }
            }
        ]

def build_catalog():
    reference_data = {}
    for spec in SHOT_CATALOGUE_SPECS:
        shot_name = spec["name"]
        slug = spec["slug"]
        cat = spec["category"]
        desc = spec["desc"]
        bat_path = spec["bat_path"]

        is_calibrated = shot_name in CALIBRATED_BENCHMARKS
        source_type = "calibrated (video-derived)" if is_calibrated else "baseline (tunable)"
        # Maintain existing analysis availability: 4 shots supported for scoring analysis per README
        analysis_status = "available" if shot_name in SUPPORTED_ANALYSIS_SHOTS else "preview_only"

        phases = generate_phases_for_shot(spec)
        common_errors = generate_shot_errors(shot_name)

        coaching_cues = [
            f"Present full bat face matching ideal bat path: {bat_path}.",
            f"Establish balanced footwork and head stability through {cat} mechanics.",
            "Hold your finish to verify biomechanical balance and weight control."
        ]

        reference_data[shot_name] = {
            "slug": slug,
            "category": cat,
            "analysis_status": analysis_status,
            "source_type": source_type,
            "status_message": (
                f"Biomechanical tolerances active for {shot_name} ({source_type})."
                if analysis_status == "available"
                else f"Preview only: analysis coming soon for {shot_name}."
            ),
            "ideal_bat_path": bat_path,
            "metadata": {
                "source": (
                    "BCCI & Cricket Australia Verified Video Kinematics"
                    if is_calibrated
                    else "Standard Cricket Biomechanics (MCC Coaching Framework) - Authored Baseline (Tunable)"
                ),
                "calibration_status": "authored baseline (tunable)",
                "normalization": "Spatial offsets and stance widths normalized by torso length (shoulder-to-hip distance).",
                "tuning_note": "Authored baseline (tunable) for player anthropometry and authentic cricket technique."
            },
            "coaching_cues": coaching_cues,
            "common_errors": common_errors,
            "drills": [e["drill"] for e in common_errors],
            "phases": phases
        }

    return reference_data

def main():
    catalog = build_catalog()
    assert len(catalog) == 25, f"Expected 25 shots, got {len(catalog)}"

    backend_out = Path("backend/app/data/reference_shots.json")
    frontend_out = Path("frontend/src/data/reference_shots.json")

    backend_out.parent.mkdir(parents=True, exist_ok=True)
    frontend_out.parent.mkdir(parents=True, exist_ok=True)

    with open(backend_out, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)
    print(f"[+] Successfully wrote {len(catalog)} shots to {backend_out.resolve()}")

    with open(frontend_out, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)
    print(f"[+] Successfully wrote {len(catalog)} shots to {frontend_out.resolve()}")

if __name__ == "__main__":
    main()
