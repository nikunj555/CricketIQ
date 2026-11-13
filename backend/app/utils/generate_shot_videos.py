import cv2
import numpy as np
import math
import json
import logging
from pathlib import Path
from backend.app.core.config import settings
from backend.app.repositories.session_repository import session_repo
from backend.app.services.video_service import video_service
from backend.app.services.geometry_service import geometry_service

logger = logging.getLogger(__name__)

# Primary cricket shots to generate distinct video clips and analysis sessions for
SHOT_CONFIGS = [
    {
        "id": "demo_cover_drive",
        "shot_type": "Cover Drive",
        "category": "Drives",
        "filename": "sample_cover_drive.mp4",
        "title": "Front-Foot Cover Drive",
        "primary_action": "front_foot_drive",
        "target_area": "Cover / Extra Cover",
        "description": "Classical front-foot drive through the off side with a bent lead knee and high leading elbow."
    },
    {
        "id": "demo_straight_drive",
        "shot_type": "Straight Drive",
        "category": "Drives",
        "filename": "sample_straight_drive.mp4",
        "title": "Textbook Straight Drive",
        "primary_action": "straight_drive",
        "target_area": "Past Bowler / Mid-Off / Mid-On",
        "description": "Straight pendulum drive past the bowler with vertical bat presentation and head over the front knee."
    },
    {
        "id": "demo_pull_shot",
        "shot_type": "Pull Shot",
        "category": "Cross-Bat & Horizontal",
        "filename": "sample_pull_shot.mp4",
        "title": "Back-Foot Pull Shot",
        "primary_action": "pull_shot",
        "target_area": "Mid-Wicket / Square Leg",
        "description": "Cross-bat attacking stroke played off the back foot with rotational hip torque through square leg."
    },
    {
        "id": "demo_forward_defensive",
        "shot_type": "Forward Defensive",
        "category": "Defensive Strokes",
        "filename": "sample_forward_defensive.mp4",
        "title": "Compact Forward Defensive",
        "primary_action": "forward_defensive",
        "target_area": "Pitch Surface (Deadened)",
        "description": "Solid front-foot defensive block with soft hands directly below the eye line and no follow-through."
    },
    {
        "id": "demo_square_cut",
        "shot_type": "Square Cut",
        "category": "Cuts",
        "filename": "sample_square_cut.mp4",
        "title": "Attacking Square Cut",
        "primary_action": "square_cut",
        "target_area": "Point / Backward Point",
        "description": "Back-and-across slash hitting down on the ball through the point region with arms fully extended."
    },
    {
        "id": "demo_sweep",
        "shot_type": "Sweep",
        "category": "Sweeps",
        "filename": "sample_sweep.mp4",
        "title": "Low Classical Sweep",
        "primary_action": "sweep",
        "target_area": "Backward Square Leg / Fine Leg",
        "description": "Horizontal sweeping stroke played by kneeling low on the back knee to meet spin bowling."
    }
]

def render_pitch_background(frame: np.ndarray, width: int, height: int, shot_title: str):
    """Renders a realistic cricket pitch setting with pitch turf, crease lines, and stumps."""
    # Sky / Stadium background gradient
    for y in range(int(height * 0.7)):
        ratio = y / (height * 0.7)
        # Deep stadium floodlit evening tone
        b = int(25 + 15 * ratio)
        g = int(20 + 20 * ratio)
        r = int(18 + 15 * ratio)
        frame[y, :] = (b, g, r)

    # Pitch turf (Green outfield)
    ground_y = int(height * 0.72)
    frame[ground_y:height, :] = (35, 75, 40)

    # Pitch strip (tan clay color)
    pitch_top = ground_y
    cv2.rectangle(frame, (120, pitch_top), (520, height), (70, 115, 145), -1)

    # Popping crease and bowling crease
    crease_x = 240
    cv2.line(frame, (crease_x, pitch_top), (crease_x, height), (220, 220, 220), 2)
    cv2.line(frame, (crease_x - 40, pitch_top), (crease_x - 40, height), (180, 180, 180), 1)

    # Cricket Stumps (Wickets) behind batter
    stump_x = 420
    stump_base_y = pitch_top + 40
    stump_height = 80
    stump_color = (40, 100, 160)
    for sx in (stump_x - 6, stump_x, stump_x + 6):
        cv2.line(frame, (sx, stump_base_y), (sx, stump_base_y - stump_height), stump_color, 3)
    # Bails
    cv2.line(frame, (stump_x - 8, stump_base_y - stump_height), (stump_x + 8, stump_base_y - stump_height), (30, 80, 140), 2)

    # Watermark Header Banner
    cv2.rectangle(frame, (0, 0), (width, 36), (15, 17, 19), -1)
    cv2.line(frame, (0, 36), (width, 36), (48, 52, 56), 1)
    cv2.putText(frame, "CRICKETIQ | Explainable AI Technique Video", (14, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (127, 234, 53), 1, cv2.LINE_AA)
    cv2.putText(frame, shot_title.upper(), (width - 240, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (245, 245, 245), 1, cv2.LINE_AA)

def compute_kinematics_for_frame(action: str, frame_idx: int, num_frames: int):
    """
    Computes precise 2D human joint coordinates (normalized [0, 1]) for a right-handed batsman
    executing the specific cricket shot technique.
    """
    t = frame_idx / max(1, num_frames - 1)
    # Action phases:
    # 0.0 - 0.25: Stance
    # 0.25 - 0.45: Stride / Backswing
    # 0.45 - 0.65: Downswing / Impact
    # 0.65 - 1.00: Follow-through / Finish

    # Default Stance Coordinates (Side-view, facing left towards bowler at x=0)
    # Head at ~(0.48, 0.32), Hips at ~(0.52, 0.54)
    head_x, head_y = 0.48, 0.32
    neck_x, neck_y = 0.49, 0.38
    l_sh_x, l_sh_y = 0.46, 0.40   # Lead (left) shoulder
    r_sh_x, r_sh_y = 0.52, 0.40   # Rear (right) shoulder
    l_hip_x, l_hip_y = 0.49, 0.54 # Lead hip
    r_hip_x, r_hip_y = 0.53, 0.54 # Rear hip
    l_knee_x, l_knee_y = 0.47, 0.66
    r_knee_x, r_knee_y = 0.54, 0.66
    l_ankle_x, l_ankle_y = 0.46, 0.78
    r_ankle_x, r_ankle_y = 0.56, 0.78

    l_elbow_x, l_elbow_y = 0.44, 0.47
    r_elbow_x, r_elbow_y = 0.52, 0.47
    l_wrist_x, l_wrist_y = 0.45, 0.55
    r_wrist_x, r_wrist_y = 0.48, 0.55

    bat_angle_deg = 20.0
    bat_length = 0.22

    if action == "front_foot_drive":
        # Cover Drive: Deep forward stride through covers, lead knee bends to ~115°, high elbow
        if t < 0.25:
            # Stance
            pass
        elif t < 0.45:
            # Backswing & Stride
            s = (t - 0.25) / 0.20
            head_x -= 0.06 * s
            head_y += 0.03 * s
            l_ankle_x -= 0.12 * s
            l_knee_x -= 0.09 * s
            l_knee_y += 0.02 * s
            # Backlift
            r_wrist_y -= 0.12 * s
            l_wrist_y -= 0.10 * s
            bat_angle_deg = 20.0 + 50.0 * s
        elif t < 0.65:
            # Downswing & Impact
            s = (t - 0.45) / 0.20
            head_x = 0.42 - 0.03 * s
            head_y = 0.35
            l_ankle_x = 0.34
            l_knee_x = 0.37
            l_knee_y = 0.68  # Knee strongly bent over foot
            # Lead elbow high
            l_elbow_x = 0.38 - 0.02 * s
            l_elbow_y = 0.42
            # Swing bat down through line
            l_wrist_x = 0.36 + 0.02 * s
            l_wrist_y = 0.52 + 0.06 * s
            r_wrist_x = 0.38 + 0.02 * s
            r_wrist_y = 0.53 + 0.06 * s
            bat_angle_deg = 70.0 - 75.0 * s
        else:
            # Follow-through
            s = (t - 0.65) / 0.35
            head_x = 0.39
            head_y = 0.35 - 0.02 * s
            l_ankle_x = 0.34
            l_knee_x = 0.37
            l_knee_y = 0.68
            # High pendulum finish
            l_elbow_x = 0.34
            l_elbow_y = 0.36 - 0.04 * s
            l_wrist_x = 0.32 - 0.04 * s
            l_wrist_y = 0.44 - 0.10 * s
            r_wrist_x = 0.34 - 0.04 * s
            r_wrist_y = 0.45 - 0.10 * s
            bat_angle_deg = -5.0 - 65.0 * s

    elif action == "straight_drive":
        # Straight Drive: Long stride straight down the ground, upright spine, vertical bat face
        if t < 0.25:
            pass
        elif t < 0.45:
            s = (t - 0.25) / 0.20
            head_x -= 0.07 * s
            l_ankle_x -= 0.13 * s
            l_knee_x -= 0.10 * s
            l_knee_y += 0.01 * s
            r_wrist_y -= 0.10 * s
            bat_angle_deg = 20.0 + 45.0 * s
        elif t < 0.65:
            s = (t - 0.45) / 0.20
            head_x = 0.41
            head_y = 0.34
            l_ankle_x = 0.33
            l_knee_x = 0.36
            l_knee_y = 0.67
            # Very high lead elbow directly along the line
            l_elbow_x = 0.37
            l_elbow_y = 0.40
            l_wrist_x = 0.35
            l_wrist_y = 0.52 + 0.05 * s
            r_wrist_x = 0.37
            r_wrist_y = 0.53 + 0.05 * s
            bat_angle_deg = 65.0 - 70.0 * s  # Comes down straight
        else:
            s = (t - 0.65) / 0.35
            head_x = 0.41
            head_y = 0.34
            l_ankle_x = 0.33
            l_knee_x = 0.36
            l_knee_y = 0.67
            # Classical straight drive high follow-through
            l_elbow_x = 0.35
            l_elbow_y = 0.32
            l_wrist_x = 0.32
            l_wrist_y = 0.36 - 0.06 * s
            r_wrist_x = 0.34
            r_wrist_y = 0.37 - 0.06 * s
            bat_angle_deg = -5.0 - 80.0 * s

    elif action == "pull_shot":
        # Pull Shot: Back-foot shift, chest rotation, horizontal bat swing across the line
        if t < 0.25:
            pass
        elif t < 0.45:
            s = (t - 0.25) / 0.20
            # Weight rocks back and across onto right foot
            head_x += 0.04 * s
            head_y -= 0.02 * s
            r_knee_y += 0.02 * s
            r_knee_x += 0.01 * s
            # Front foot lifted slightly
            l_ankle_y -= 0.04 * s
            l_ankle_x += 0.03 * s
            # High backlift above rear shoulder
            r_wrist_y -= 0.16 * s
            r_wrist_x += 0.04 * s
            l_wrist_y -= 0.14 * s
            l_wrist_x += 0.02 * s
            bat_angle_deg = 30.0 + 60.0 * s
        elif t < 0.65:
            s = (t - 0.45) / 0.20
            head_x = 0.52
            head_y = 0.31
            r_knee_x = 0.55
            r_knee_y = 0.68
            l_ankle_x = 0.48
            l_ankle_y = 0.76
            # Horizontal arm whip across chest
            l_wrist_x = 0.48 - 0.16 * s
            l_wrist_y = 0.44 + 0.02 * s
            r_wrist_x = 0.52 - 0.16 * s
            r_wrist_y = 0.45 + 0.02 * s
            bat_angle_deg = 90.0 - 80.0 * s
        else:
            s = (t - 0.65) / 0.35
            head_x = 0.52
            head_y = 0.31
            r_knee_x = 0.55
            r_knee_y = 0.68
            l_ankle_x = 0.48
            l_ankle_y = 0.76
            # Complete rotational wrap around left shoulder
            l_wrist_x = 0.32 - 0.04 * s
            l_wrist_y = 0.42 - 0.04 * s
            r_wrist_x = 0.34 - 0.04 * s
            r_wrist_y = 0.43 - 0.04 * s
            bat_angle_deg = 10.0 - 95.0 * s

    elif action == "forward_defensive":
        # Forward Defensive: Forward stride, soft hands right under eyes, downward bat angle, NO follow-through
        if t < 0.30:
            pass
        elif t < 0.55:
            s = (t - 0.30) / 0.25
            head_x -= 0.06 * s
            head_y += 0.02 * s
            l_ankle_x -= 0.11 * s
            l_knee_x -= 0.08 * s
            l_knee_y += 0.02 * s
            # Controlled short backlift
            r_wrist_y -= 0.08 * s
            l_wrist_y -= 0.06 * s
            bat_angle_deg = 20.0 + 35.0 * s
        elif t < 0.75:
            # Impact & Soft hands block
            s = (t - 0.55) / 0.20
            head_x = 0.42
            head_y = 0.34
            l_ankle_x = 0.35
            l_knee_x = 0.38
            l_knee_y = 0.68
            # Bat placed right next to front pad
            l_wrist_x = 0.37
            l_wrist_y = 0.54
            r_wrist_x = 0.39
            r_wrist_y = 0.55
            # Bat angled downward ~30 degrees
            bat_angle_deg = 55.0 - 25.0 * s
        else:
            # Holds the pose statically (defensive resilience)
            head_x = 0.42
            head_y = 0.34
            l_ankle_x = 0.35
            l_knee_x = 0.38
            l_knee_y = 0.68
            l_wrist_x = 0.37
            l_wrist_y = 0.54
            r_wrist_x = 0.39
            r_wrist_y = 0.55
            bat_angle_deg = 30.0

    elif action == "square_cut":
        # Square Cut: Back-and-across, horizontal slash hitting down through point
        if t < 0.25:
            pass
        elif t < 0.45:
            s = (t - 0.25) / 0.20
            head_x += 0.03 * s
            r_knee_x += 0.02 * s
            l_ankle_x += 0.04 * s
            # High backlift outside off-stump
            r_wrist_y -= 0.18 * s
            r_wrist_x += 0.03 * s
            l_wrist_y -= 0.16 * s
            bat_angle_deg = 20.0 + 70.0 * s
        elif t < 0.65:
            s = (t - 0.45) / 0.20
            head_x = 0.51
            head_y = 0.33
            r_knee_x = 0.56
            r_knee_y = 0.67
            l_ankle_x = 0.50
            l_ankle_y = 0.78
            # Downward chop through point
            l_wrist_x = 0.48 - 0.14 * s
            l_wrist_y = 0.46 + 0.06 * s
            r_wrist_x = 0.50 - 0.14 * s
            r_wrist_y = 0.47 + 0.06 * s
            bat_angle_deg = 90.0 - 75.0 * s
        else:
            s = (t - 0.65) / 0.35
            head_x = 0.51
            head_y = 0.33
            l_wrist_x = 0.34 - 0.06 * s
            l_wrist_y = 0.52 - 0.04 * s
            r_wrist_x = 0.36 - 0.06 * s
            r_wrist_y = 0.53 - 0.04 * s
            bat_angle_deg = 15.0 - 70.0 * s

    elif action == "sweep":
        # Sweep: Front knee dropped onto turf, low horizontal broom sweep through square leg
        if t < 0.25:
            pass
        elif t < 0.45:
            s = (t - 0.25) / 0.20
            # Sinking low and striding forward
            head_x -= 0.07 * s
            head_y += 0.12 * s
            l_ankle_x -= 0.14 * s
            l_knee_x -= 0.10 * s
            l_knee_y += 0.10 * s
            # Rear knee dropping down towards ground
            r_knee_y += 0.08 * s
            r_ankle_x += 0.02 * s
            # Backlift
            r_wrist_y -= 0.06 * s
            bat_angle_deg = 20.0 + 40.0 * s
        elif t < 0.65:
            s = (t - 0.45) / 0.20
            head_x = 0.41 - 0.02 * s
            head_y = 0.44
            l_ankle_x = 0.32
            l_knee_x = 0.36
            l_knee_y = 0.74
            r_knee_x = 0.52
            r_knee_y = 0.76  # Rear knee almost touching pitch
            r_ankle_y = 0.78
            # Low horizontal sweeping arc
            l_wrist_x = 0.35 + 0.04 * s
            l_wrist_y = 0.58 + 0.02 * s
            r_wrist_x = 0.37 + 0.04 * s
            r_wrist_y = 0.59 + 0.02 * s
            bat_angle_deg = 60.0 - 65.0 * s
        else:
            s = (t - 0.65) / 0.35
            head_x = 0.39
            head_y = 0.44
            l_ankle_x = 0.32
            l_knee_x = 0.36
            l_knee_y = 0.74
            r_knee_y = 0.76
            # Low wrap around back
            l_wrist_x = 0.32 - 0.06 * s
            l_wrist_y = 0.54 - 0.04 * s
            r_wrist_x = 0.34 - 0.06 * s
            r_wrist_y = 0.55 - 0.04 * s
            bat_angle_deg = -5.0 - 75.0 * s

    # Construct complete 33 MediaPipe-compatible landmarks array
    landmarks_33 = []
    for _ in range(33):
        landmarks_33.append({"x": head_x, "y": head_y, "z": 0.0, "visibility": 0.98})

    # Fill in exact landmark indices
    landmarks_33[0] = {"x": round(head_x, 4), "y": round(head_y, 4), "z": 0.0, "visibility": 0.99}  # Nose
    landmarks_33[11] = {"x": round(l_sh_x, 4), "y": round(l_sh_y, 4), "z": 0.05, "visibility": 0.98} # Left shoulder
    landmarks_33[12] = {"x": round(r_sh_x, 4), "y": round(r_sh_y, 4), "z": -0.05, "visibility": 0.98} # Right shoulder
    landmarks_33[13] = {"x": round(l_elbow_x, 4), "y": round(l_elbow_y, 4), "z": 0.04, "visibility": 0.97} # Left elbow
    landmarks_33[14] = {"x": round(r_elbow_x, 4), "y": round(r_elbow_y, 4), "z": -0.04, "visibility": 0.97} # Right elbow
    landmarks_33[15] = {"x": round(l_wrist_x, 4), "y": round(l_wrist_y, 4), "z": 0.06, "visibility": 0.96} # Left wrist
    landmarks_33[16] = {"x": round(r_wrist_x, 4), "y": round(r_wrist_y, 4), "z": -0.02, "visibility": 0.96} # Right wrist
    landmarks_33[23] = {"x": round(l_hip_x, 4), "y": round(l_hip_y, 4), "z": 0.02, "visibility": 0.98} # Left hip
    landmarks_33[24] = {"x": round(r_hip_x, 4), "y": round(r_hip_y, 4), "z": -0.02, "visibility": 0.98} # Right hip
    landmarks_33[25] = {"x": round(l_knee_x, 4), "y": round(l_knee_y, 4), "z": 0.03, "visibility": 0.97} # Left knee
    landmarks_33[26] = {"x": round(r_knee_x, 4), "y": round(r_knee_y, 4), "z": -0.03, "visibility": 0.97} # Right knee
    landmarks_33[27] = {"x": round(l_ankle_x, 4), "y": round(l_ankle_y, 4), "z": 0.04, "visibility": 0.96} # Left ankle
    landmarks_33[28] = {"x": round(r_ankle_x, 4), "y": round(r_ankle_y, 4), "z": -0.04, "visibility": 0.96} # Right ankle
    landmarks_33[31] = {"x": round(l_ankle_x - 0.03, 4), "y": round(l_ankle_y + 0.01, 4), "z": 0.04, "visibility": 0.95} # Left toe
    landmarks_33[32] = {"x": round(r_ankle_x - 0.03, 4), "y": round(r_ankle_y + 0.01, 4), "z": -0.04, "visibility": 0.95} # Right toe

    # Bat tip position
    rad = math.radians(bat_angle_deg)
    bat_tip_x = l_wrist_x + math.sin(rad) * bat_length
    bat_tip_y = l_wrist_y + math.cos(rad) * bat_length

    return {
        "landmarks": landmarks_33,
        "bat_angle_deg": round(bat_angle_deg, 1),
        "bat_tip_x": round(bat_tip_x, 4),
        "bat_tip_y": round(bat_tip_y, 4),
        "wrist_lead": (l_wrist_x, l_wrist_y),
        "wrist_rear": (r_wrist_x, r_wrist_y),
    }

def render_batsman_on_frame(frame: np.ndarray, width: int, height: int, k_info: dict):
    """
    Renders an anatomically proportioned cricket batsman with whites, pads, helmet, gloves, and bat.
    """
    lms = k_info["landmarks"]

    def to_px(pt_norm):
        return int(pt_norm["x"] * width), int(pt_norm["y"] * height)

    p_head = to_px(lms[0])
    p_l_sh = to_px(lms[11])
    p_r_sh = to_px(lms[12])
    p_l_el = to_px(lms[13])
    p_r_el = to_px(lms[14])
    p_l_wr = to_px(lms[15])
    p_r_wr = to_px(lms[16])
    p_l_hip = to_px(lms[23])
    p_r_hip = to_px(lms[24])
    p_l_kn = to_px(lms[25])
    p_r_kn = to_px(lms[26])
    p_l_ank = to_px(lms[27])
    p_r_ank = to_px(lms[28])

    # Palette
    skin = (175, 200, 230)
    whites = (235, 235, 235)
    pads = (245, 245, 245)
    pads_shadow = (200, 205, 210)
    helmet = (120, 45, 25)
    bat_wood = (45, 115, 185)
    bat_handle = (30, 30, 30)
    gloves = (240, 240, 240)

    # 1. Rear Leg (Drawn first for depth)
    cv2.line(frame, p_r_hip, p_r_kn, pads_shadow, 20)
    cv2.line(frame, p_r_kn, p_r_ank, pads_shadow, 18)
    cv2.circle(frame, p_r_kn, 11, pads_shadow, -1)

    # 2. Torso (Cricket Jersey)
    torso_pts = np.array([p_l_sh, p_r_sh, p_r_hip, p_l_hip], np.int32)
    cv2.fillPoly(frame, [torso_pts], whites)
    cv2.polylines(frame, [torso_pts], True, (210, 210, 210), 2)

    # 3. Lead Leg (Foreground with Batting Pad)
    cv2.line(frame, p_l_hip, p_l_kn, pads, 22)
    cv2.line(frame, p_l_kn, p_l_ank, pads, 20)
    cv2.circle(frame, p_l_kn, 12, pads, -1)
    # Cricket shoe / spikes
    cv2.ellipse(frame, (p_l_ank[0] - 8, p_l_ank[1] + 4), (16, 6), 0, 0, 360, (230, 230, 230), -1)

    # 4. Head & Cricket Helmet
    cv2.circle(frame, p_head, 24, skin, -1)
    # Helmet dome
    cv2.ellipse(frame, (p_head[0], p_head[1] - 4), (25, 20), 0, 180, 360, helmet, -1)
    # Helmet visor / grille
    cv2.line(frame, (p_head[0] - 16, p_head[1] + 2), (p_head[0] - 24, p_head[1] + 12), (180, 180, 180), 2)
    cv2.line(frame, (p_head[0] - 8, p_head[1] + 2), (p_head[0] - 18, p_head[1] + 14), (180, 180, 180), 2)

    # 5. Rear Arm
    cv2.line(frame, p_r_sh, p_r_el, whites, 14)
    cv2.line(frame, p_r_el, p_r_wr, skin, 12)

    # 6. Lead Arm
    cv2.line(frame, p_l_sh, p_l_el, whites, 16)
    cv2.line(frame, p_l_el, p_l_wr, skin, 14)

    # 7. Batting Gloves
    cv2.circle(frame, p_l_wr, 10, gloves, -1)
    cv2.circle(frame, p_r_wr, 10, gloves, -1)

    # 8. Cricket Bat (Willow Blade + Rubber Grip Handle)
    tip_px = (int(k_info["bat_tip_x"] * width), int(k_info["bat_tip_y"] * height))
    handle_top = (int(p_l_wr[0] + (p_l_wr[0] - tip_px[0]) * 0.25), int(p_l_wr[1] + (p_l_wr[1] - tip_px[1]) * 0.25))
    # Handle
    cv2.line(frame, p_l_wr, handle_top, bat_handle, 6)
    # Blade
    cv2.line(frame, p_l_wr, tip_px, bat_wood, 14)
    # Bat edge / spine highlight
    cv2.line(frame, p_l_wr, tip_px, (65, 145, 220), 2)

def transcode_to_h264(video_path: Path):
    """Ensures video is encoded in web-standard H.264 for smooth browser playback."""
    try:
        import imageio_ffmpeg, subprocess
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        temp_out = video_path.with_name(f"temp_h264_{video_path.name}")
        cmd = [
            exe, "-y",
            "-i", str(video_path),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(temp_out)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and temp_out.exists():
            temp_out.replace(video_path)
            print(f"Transcoded {video_path.name} to standard H.264.")
    except (subprocess.SubprocessError, OSError, FileNotFoundError) as e:
        print(f"H.264 transcode notice for {video_path.name}: {e}")

def generate_shot_video_and_session(cfg: dict):
    """
    Generates video file, ground-truth landmarks, and seeds analyzed session into database.
    """
    output_path = settings.UPLOADS_DIR / cfg["filename"]
    width, height = 640, 480
    fps = 30.0
    num_frames = 60

    print(f"\n==========================================")
    print(f"Generating video for: {cfg['title']} ({cfg['filename']})")
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    all_frame_landmarks = []

    for f_idx in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        render_pitch_background(frame, width, height, cfg["title"])
        
        k_info = compute_kinematics_for_frame(cfg["primary_action"], f_idx, num_frames)
        all_frame_landmarks.append(k_info)
        
        render_batsman_on_frame(frame, width, height, k_info)
        out.write(frame)

    out.release()
    transcode_to_h264(output_path)

    # Save accompanying ground-truth landmarks JSON
    gt_path = settings.UPLOADS_DIR / f"{output_path.stem}_groundtruth.json"
    with open(gt_path, "w") as f:
        json.dump(all_frame_landmarks, f)

    # Register session in DB
    session_id = cfg["id"]
    print(f"Registering session '{session_id}' in SQLite database...")
    
    # Remove existing session if re-seeding
    existing = session_repo.get_session(session_id)
    if existing:
        session_repo.delete_session(session_id)

    session_repo.create_session(
        session_id=session_id,
        video_filename=cfg["filename"],
        original_path=str(output_path),
        shot_type=cfg["shot_type"],
        handedness="Right",
        camera_angle="Side View"
    )

    print(f"Running video analysis pipeline on '{session_id}'...")
    video_service.process_video_session(session_id)
    print(f"Successfully processed session '{session_id}'!")

def seed_all_shot_sessions():
    print("Beginning Generation and Seeding of Multi-Shot Video Library...")
    for cfg in SHOT_CONFIGS:
        generate_shot_video_and_session(cfg)
    print("\nAll cricket shot video clips generated and seeded successfully!")

if __name__ == "__main__":
    seed_all_shot_sessions()
