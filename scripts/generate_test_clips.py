"""
CricketIQ — Synthetic Test Clip and Dataset Generator
Generates clean, mathematically verified, non-copyrighted synthetic test clips
using OpenCV to render a moving stickman/skeleton with known kinematic angles,
phase markers, and sidecar ground truth landmark JSON.
"""

import os
import json
import math
import numpy as np
import cv2
from pathlib import Path

# Constants for video generation
WIDTH = 640
HEIGHT = 480
FPS = 30.0
NUM_FRAMES = 90  # 3.0 seconds

# Phase partitions (fractions of stroke duration)
PHASE_TIMINGS = [
    ("Stance", 0.0, 0.20),
    ("Backlift", 0.20, 0.40),
    ("Stride", 0.40, 0.55),
    ("Downswing", 0.55, 0.70),
    ("Impact", 0.70, 0.78),
    ("Follow-through", 0.78, 0.88),
    ("Recovery", 0.88, 1.00),
]

def get_phase_at_ratio(ratio: float) -> str:
    for name, start, end in PHASE_TIMINGS:
        if start <= ratio < end:
            return name
    return "Recovery"

def generate_shot_kinematics(shot_type: str, num_frames: int = NUM_FRAMES):
    """
    Computes frame-by-frame 33-point MediaPipe landmarks with precise known
    biomechanical angles for a given shot type.
    """
    frames_landmarks = []
    
    # Base proportions (normalized 0..1 in 640x480 frame)
    hip_center_x = 0.50
    hip_center_y = 0.52
    torso_height = 0.22
    thigh_len = 0.18
    shin_len = 0.18
    upper_arm_len = 0.12
    forearm_len = 0.12
    
    for i in range(num_frames):
        ratio = i / float(num_frames - 1)
        phase = get_phase_at_ratio(ratio)
        
        # Biomechanical trajectory curves by shot
        if shot_type == "Cover Drive":
            if ratio < 0.20: # Stance
                lead_knee_deg = 168.0
                torso_lean_deg = 12.0
                st_w = 1.0
                arm_deg = 20.0
                el_deg = 150.0
                bat_angle_deg = 35.0
            elif ratio < 0.40: # Backlift
                p = (ratio - 0.20) / 0.20
                lead_knee_deg = 168.0 - p * 8.0
                torso_lean_deg = 12.0 + p * 6.0
                st_w = 1.0 + p * 0.1
                arm_deg = 20.0 - p * 70.0  # up-back to -50
                el_deg = 150.0 - p * 40.0   # to 110
                bat_angle_deg = 35.0 + p * 75.0
            elif ratio < 0.55: # Stride
                p = (ratio - 0.40) / 0.15
                lead_knee_deg = 160.0 - p * 20.0
                torso_lean_deg = 18.0 + p * 4.0
                st_w = 1.1 + p * 0.5       # stride expands to 1.6
                arm_deg = -50.0 + p * 20.0
                el_deg = 110.0
                bat_angle_deg = 110.0
            elif ratio < 0.70: # Downswing
                p = (ratio - 0.55) / 0.15
                lead_knee_deg = 140.0 - p * 16.0  # flexes to 124!
                torso_lean_deg = 22.0 + p * 3.0   # reaches 25!
                st_w = 1.6
                arm_deg = -30.0 + p * 65.0       # forward to +35
                el_deg = 110.0 - p * 18.0        # guide elbow to 92!
                bat_angle_deg = 110.0 - p * 90.0 # swings through
            elif ratio < 0.78: # Impact
                lead_knee_deg = 124.0
                torso_lean_deg = 25.0
                st_w = 1.6
                arm_deg = 35.0
                el_deg = 92.0
                bat_angle_deg = 20.0
            else: # Follow-through & Recovery
                p = (ratio - 0.78) / 0.22
                lead_knee_deg = 124.0 + p * 25.0
                torso_lean_deg = 25.0 - p * 10.0
                st_w = 1.6 - p * 0.2
                arm_deg = 35.0 + p * 65.0        # high finish +100
                el_deg = 92.0 - p * 22.0         # flexes to 70
                bat_angle_deg = 20.0 + p * 110.0

        elif shot_type == "Straight Drive":
            if ratio < 0.20:
                lead_knee_deg = 168.0
                torso_lean_deg = 12.0
                st_w = 1.0
                arm_deg = 15.0
                el_deg = 150.0
                bat_angle_deg = 30.0
            elif ratio < 0.40:
                p = (ratio - 0.20) / 0.20
                lead_knee_deg = 168.0 - p * 8.0
                torso_lean_deg = 12.0 + p * 6.0
                st_w = 1.0 + p * 0.1
                arm_deg = 15.0 - p * 55.0        # straight backlift -40
                el_deg = 150.0 - p * 40.0
                bat_angle_deg = 30.0 + p * 75.0
            elif ratio < 0.55:
                p = (ratio - 0.40) / 0.15
                lead_knee_deg = 160.0 - p * 20.0
                torso_lean_deg = 18.0 + p * 4.0
                st_w = 1.1 + p * 0.5
                arm_deg = -40.0 + p * 15.0
                el_deg = 110.0
                bat_angle_deg = 105.0
            elif ratio < 0.70:
                p = (ratio - 0.55) / 0.15
                lead_knee_deg = 140.0 - p * 16.0
                torso_lean_deg = 22.0 + p * 3.0
                st_w = 1.6
                arm_deg = -25.0 + p * 45.0       # swings straight down +20
                el_deg = 110.0 - p * 18.0
                bat_angle_deg = 105.0 - p * 90.0
            elif ratio < 0.78:
                lead_knee_deg = 124.0
                torso_lean_deg = 25.0
                st_w = 1.6
                arm_deg = 20.0
                el_deg = 92.0
                bat_angle_deg = 15.0
            else:
                p = (ratio - 0.78) / 0.22
                lead_knee_deg = 124.0 + p * 25.0
                torso_lean_deg = 25.0 - p * 10.0
                st_w = 1.6 - p * 0.2
                arm_deg = 20.0 + p * 70.0
                el_deg = 92.0 - p * 22.0
                bat_angle_deg = 15.0 + p * 120.0

        else: # Pull Shot
            if ratio < 0.20:
                lead_knee_deg = 160.0
                torso_lean_deg = 10.0
                st_w = 1.0
                arm_deg = 25.0
                el_deg = 140.0
                bat_angle_deg = 45.0
            elif ratio < 0.40:
                p = (ratio - 0.20) / 0.20
                lead_knee_deg = 160.0
                torso_lean_deg = 10.0 - p * 4.0
                st_w = 1.0 - p * 0.1 # back foot transfer
                arm_deg = 25.0 - p * 80.0 # high backlift
                el_deg = 140.0 - p * 30.0
                bat_angle_deg = 45.0 + p * 75.0
            elif ratio < 0.55:
                p = (ratio - 0.40) / 0.15
                lead_knee_deg = 155.0
                torso_lean_deg = 6.0
                st_w = 0.9
                arm_deg = -55.0 + p * 25.0
                el_deg = 110.0
                bat_angle_deg = 120.0
            elif ratio < 0.70:
                p = (ratio - 0.55) / 0.15
                lead_knee_deg = 150.0
                torso_lean_deg = 6.0 - p * 4.0
                st_w = 0.9
                arm_deg = -30.0 + p * 70.0 # horizontal pull swing
                el_deg = 110.0 + p * 35.0  # extended arms!
                bat_angle_deg = 120.0 - p * 80.0
            elif ratio < 0.78:
                lead_knee_deg = 150.0
                torso_lean_deg = 2.0
                st_w = 0.9
                arm_deg = 40.0
                el_deg = 145.0
                bat_angle_deg = 40.0
            else:
                p = (ratio - 0.78) / 0.22
                lead_knee_deg = 150.0 + p * 10.0
                torso_lean_deg = 2.0 + p * 8.0
                st_w = 0.9 + p * 0.1
                arm_deg = 40.0 + p * 60.0
                el_deg = 145.0 - p * 40.0
                bat_angle_deg = 40.0 + p * 90.0

        # Build 33 MediaPipe landmark coordinates using exact forward kinematics
        torso_rad = math.radians(torso_lean_deg)
        
        # Hips
        left_hip_x = hip_center_x - 0.02
        left_hip_y = hip_center_y
        right_hip_x = hip_center_x + 0.02
        right_hip_y = hip_center_y
        
        # Shoulders (offset by torso lean)
        sh_center_x = hip_center_x + torso_height * math.sin(torso_rad)
        sh_center_y = hip_center_y - torso_height * math.cos(torso_rad)
        left_sh_x = sh_center_x - 0.02
        left_sh_y = sh_center_y
        right_sh_x = sh_center_x + 0.02
        right_sh_y = sh_center_y
        
        # Head / Nose
        nose_x = sh_center_x + 0.08 * math.sin(torso_rad)
        nose_y = sh_center_y - 0.08 * math.cos(torso_rad)
        
        # Lead leg (Left leg for right-handed batter in side-on view)
        thigh_a1 = math.radians(25.0 + (st_w - 1.0) * 40.0)
        lead_knee_x = left_hip_x + thigh_len * math.sin(thigh_a1)
        lead_knee_y = left_hip_y + thigh_len * math.cos(thigh_a1)
        shin_a2 = thigh_a1 - math.radians(180.0 - lead_knee_deg)
        lead_ankle_x = lead_knee_x + shin_len * math.sin(shin_a2)
        lead_ankle_y = lead_knee_y + shin_len * math.cos(shin_a2)
        
        # Rear leg (Right leg)
        rear_knee_deg = 150.0
        rear_thigh_a1 = math.radians(-10.0)
        rear_knee_x = right_hip_x + thigh_len * math.sin(rear_thigh_a1)
        rear_knee_y = right_hip_y + thigh_len * math.cos(rear_thigh_a1)
        rear_shin_a2 = rear_thigh_a1 - math.radians(180.0 - rear_knee_deg)
        rear_ankle_x = rear_knee_x + shin_len * math.sin(rear_shin_a2)
        rear_ankle_y = rear_knee_y + shin_len * math.cos(rear_shin_a2)
        
        # Arms & Wrists
        a1 = math.radians(arm_deg)
        lead_elbow_x = left_sh_x + upper_arm_len * math.sin(a1)
        lead_elbow_y = left_sh_y + upper_arm_len * math.cos(a1)
        a2 = a1 - math.radians(180.0 - el_deg)
        lead_wrist_x = lead_elbow_x + forearm_len * math.sin(a2)
        lead_wrist_y = lead_elbow_y + forearm_len * math.cos(a2)
        
        rear_arm_deg = arm_deg + 5.0
        rear_el_deg = el_deg + 3.0
        ra1 = math.radians(rear_arm_deg)
        rear_elbow_x = right_sh_x + upper_arm_len * math.sin(ra1)
        rear_elbow_y = right_sh_y + upper_arm_len * math.cos(ra1)
        ra2 = ra1 - math.radians(180.0 - rear_el_deg)
        rear_wrist_x = rear_elbow_x + forearm_len * math.sin(ra2)
        rear_wrist_y = rear_elbow_y + forearm_len * math.cos(ra2)
        
        # Bat tip
        bat_rad = math.radians(bat_angle_deg)
        bat_tip_x = lead_wrist_x + 0.22 * math.cos(bat_rad - math.pi * 0.5)
        bat_tip_y = lead_wrist_y + 0.22 * math.sin(bat_rad - math.pi * 0.5)

        lms = [{"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 0.99} for _ in range(33)]
        lms[0] = {"x": round(nose_x, 4), "y": round(nose_y, 4), "z": 0.0, "visibility": 0.99}
        lms[11] = {"x": round(left_sh_x, 4), "y": round(left_sh_y, 4), "z": 0.0, "visibility": 0.99}
        lms[12] = {"x": round(right_sh_x, 4), "y": round(right_sh_y, 4), "z": 0.0, "visibility": 0.99}
        lms[13] = {"x": round(lead_elbow_x, 4), "y": round(lead_elbow_y, 4), "z": 0.0, "visibility": 0.99}
        lms[14] = {"x": round(rear_elbow_x, 4), "y": round(rear_elbow_y, 4), "z": 0.0, "visibility": 0.99}
        lms[15] = {"x": round(lead_wrist_x, 4), "y": round(lead_wrist_y, 4), "z": 0.0, "visibility": 0.99}
        lms[16] = {"x": round(rear_wrist_x, 4), "y": round(rear_wrist_y, 4), "z": 0.0, "visibility": 0.99}
        lms[23] = {"x": round(left_hip_x, 4), "y": round(left_hip_y, 4), "z": 0.0, "visibility": 0.99}
        lms[24] = {"x": round(right_hip_x, 4), "y": round(right_hip_y, 4), "z": 0.0, "visibility": 0.99}
        lms[25] = {"x": round(lead_knee_x, 4), "y": round(lead_knee_y, 4), "z": 0.0, "visibility": 0.99}
        lms[26] = {"x": round(rear_knee_x, 4), "y": round(rear_knee_y, 4), "z": 0.0, "visibility": 0.99}
        lms[27] = {"x": round(lead_ankle_x, 4), "y": round(lead_ankle_y, 4), "z": 0.0, "visibility": 0.99}
        lms[28] = {"x": round(rear_ankle_x, 4), "y": round(rear_ankle_y, 4), "z": 0.0, "visibility": 0.99}
        lms[31] = {"x": round(lead_ankle_x - 0.03, 4), "y": round(lead_ankle_y, 4), "z": 0.0, "visibility": 0.99}
        lms[32] = {"x": round(rear_ankle_x - 0.03, 4), "y": round(rear_ankle_y, 4), "z": 0.0, "visibility": 0.99}
        
        frames_landmarks.append({
            "frame_idx": i,
            "phase": phase,
            "lead_knee_deg": round(lead_knee_deg, 1),
            "torso_lean_deg": round(torso_lean_deg, 1),
            "bat_angle_deg": round(bat_angle_deg, 1),
            "bat_tip_x": round(bat_tip_x, 4),
            "bat_tip_y": round(bat_tip_y, 4),
            "landmarks": lms
        })
        
    return frames_landmarks

def render_clip_to_mp4(
    output_path: Path,
    shot_type: str,
    frames_data: list,
    add_second_batter: bool = False
):
    """Renders video frames with OpenCV stickman, kinematic angles, and phase tags."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, FPS, (WIDTH, HEIGHT))
    
    # Bone connectivity pairs
    bones = [
        (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
        (11, 23), (12, 24), (23, 24),
        (23, 25), (25, 27), (24, 26), (26, 28)
    ]
    
    for f_info in frames_data:
        # Background: dark cricket training facility theme
        img = np.full((HEIGHT, WIDTH, 3), (22, 25, 27), dtype=np.uint8)
        
        # Pitch line and crease markers
        cv2.line(img, (0, int(HEIGHT * 0.88)), (WIDTH, int(HEIGHT * 0.88)), (48, 52, 56), 2)
        cv2.line(img, (int(WIDTH * 0.40), int(HEIGHT * 0.82)), (int(WIDTH * 0.40), int(HEIGHT * 0.94)), (120, 125, 130), 2)
        
        lms = f_info["landmarks"]
        
        # Draw non-striker in background if requested
        if add_second_batter:
            ns_x = int(WIDTH * 0.85)
            ns_y = int(HEIGHT * 0.55)
            cv2.circle(img, (ns_x, ns_y - 80), 16, (120, 120, 120), 2)
            cv2.line(img, (ns_x, ns_y - 64), (ns_x, ns_y + 30), (120, 120, 120), 3)
            cv2.line(img, (ns_x, ns_y + 30), (ns_x - 15, ns_y + 110), (120, 120, 120), 3)
            cv2.line(img, (ns_x, ns_y + 30), (ns_x + 15, ns_y + 110), (120, 120, 120), 3)
            cv2.putText(img, "Non-Striker (Track 1)", (ns_x - 50, ns_y - 95), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (140, 140, 140), 1)

        # Draw bones for striker
        for b1, b2 in bones:
            p1 = (int(lms[b1]["x"] * WIDTH), int(lms[b1]["y"] * HEIGHT))
            p2 = (int(lms[b2]["x"] * WIDTH), int(lms[b2]["y"] * HEIGHT))
            cv2.line(img, p1, p2, (127, 234, 53), 3, cv2.LINE_AA) # brand green
            
        # Draw joints
        for idx in [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]:
            p = (int(lms[idx]["x"] * WIDTH), int(lms[idx]["y"] * HEIGHT))
            cv2.circle(img, p, 5, (245, 245, 245), -1, cv2.LINE_AA)
            cv2.circle(img, p, 6, (127, 234, 53), 1, cv2.LINE_AA)
            
        # Draw head circle
        head_p = (int(lms[0]["x"] * WIDTH), int(lms[0]["y"] * HEIGHT))
        cv2.circle(img, head_p, 20, (245, 245, 245), 2, cv2.LINE_AA)
        
        # Draw bat blade
        w_p = (int(lms[15]["x"] * WIDTH), int(lms[15]["y"] * HEIGHT))
        tip_p = (int(f_info["bat_tip_x"] * WIDTH), int(f_info["bat_tip_y"] * HEIGHT))
        cv2.line(img, w_p, tip_p, (210, 180, 140), 7, cv2.LINE_AA) # wooden bat
        cv2.circle(img, w_p, 4, (40, 40, 40), -1) # grip
        
        # Telemetry overlay
        cv2.rectangle(img, (15, 15), (340, 120), (10, 12, 14), -1)
        cv2.rectangle(img, (15, 15), (340, 120), (48, 52, 56), 1)
        
        cv2.putText(img, f"CRICKETIQ SYNTHETIC BENCHMARK", (25, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (127, 234, 53), 1, cv2.LINE_AA)
        cv2.putText(img, f"Stroke : {shot_type}", (25, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (245, 245, 245), 1, cv2.LINE_AA)
        cv2.putText(img, f"Phase  : {f_info['phase']} (F{f_info['frame_idx']:02d}/{NUM_FRAMES})", (25, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (56, 189, 248), 1, cv2.LINE_AA)
        cv2.putText(img, f"Knee Flexion : {f_info['lead_knee_deg']:.1f} deg", (25, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (165, 169, 173), 1, cv2.LINE_AA)
        cv2.putText(img, f"Torso Lean   : {f_info['torso_lean_deg']:.1f} deg", (25, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (165, 169, 173), 1, cv2.LINE_AA)
        
        out.write(img)
        
    out.release()
    print(f"[+] Rendered synthetic test clip: {output_path} ({len(frames_data)} frames)")

def main():
    fixtures_dir = Path("backend/tests/fixtures")
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Generate core test fixtures
    clips_to_generate = [
        ("Cover Drive", fixtures_dir / "cover_drive.mp4", fixtures_dir / "cover_drive_groundtruth.json", False),
        ("Straight Drive", fixtures_dir / "straight_drive.mp4", fixtures_dir / "straight_drive_groundtruth.json", False),
        ("Pull Shot", fixtures_dir / "pull_shot.mp4", fixtures_dir / "pull_shot_groundtruth.json", False),
        ("Cover Drive", fixtures_dir / "two_batters.mp4", fixtures_dir / "two_batters_groundtruth.json", True),
    ]
    
    for shot_name, mp4_path, json_path, multi_batter in clips_to_generate:
        frames = generate_shot_kinematics(shot_name, num_frames=NUM_FRAMES)
        render_clip_to_mp4(mp4_path, shot_name, frames, add_second_batter=multi_batter)
        
        if multi_batter:
            payload = {
                "striker_candidates": {
                    "candidates": [
                        {
                            "track_id": 0,
                            "bbox": [0.26, 0.18, 0.58, 0.88],
                            "is_default": True,
                            "is_suggested_striker": True,
                            "role": "Suggested Striker (Locked)",
                            "wrist_motion_score": 0.45,
                            "confidence": 0.95,
                            "evidence": {"cue1_bat_pose_score": 0.9, "cue3_motion_score": 0.85}
                        },
                        {
                            "track_id": 1,
                            "bbox": [0.70, 0.20, 0.92, 0.85],
                            "is_default": False,
                            "is_suggested_striker": False,
                            "role": "Non Striker (Excluded)",
                            "wrist_motion_score": 0.02,
                            "confidence": 0.30,
                            "evidence": {"cue1_bat_pose_score": 0.1, "cue3_motion_score": 0.05}
                        }
                    ],
                    "default_track_id": 0,
                    "total_persons": 2,
                    "needs_confirmation": False
                },
                "frames": frames
            }
        else:
            payload = frames
            
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"[+] Saved companion groundtruth: {json_path}")
        
    # 2. Generate labelled datasets for supported shots (8 clips across 2 batters)
    labeled_dir = fixtures_dir / "labeled"
    for shot_slug, shot_name in [("cover-drive", "Cover Drive"), ("straight-drive", "Straight Drive")]:
        shot_lab_dir = labeled_dir / shot_slug
        shot_lab_dir.mkdir(parents=True, exist_ok=True)
        for b_idx in (1, 2):
            for c_idx in range(1, 5):
                clip_name = f"batter{b_idx}_clip{c_idx}"
                c_mp4 = shot_lab_dir / f"{clip_name}.mp4"
                c_json = shot_lab_dir / f"{clip_name}_groundtruth.json"
                c_frames = generate_shot_kinematics(shot_name, num_frames=NUM_FRAMES)
                render_clip_to_mp4(c_mp4, shot_name, c_frames, add_second_batter=False)
                with open(c_json, "w", encoding="utf-8") as f:
                    json.dump(c_frames, f, indent=2)
                    
    print("\n[SUCCESS] Generated all synthetic test clips and labeled multi-batter datasets.")

if __name__ == "__main__":
    main()
