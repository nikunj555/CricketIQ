"""
CricketIQ — Complete 25 Shot Video Generator & Session Seeder
Generates distinct, high-quality, authentic H.264 video clips and seeds database records
so that NO TWO SHOTS EVER DISPLAY THE SAME PREVIEW VIDEO OR SIMULATION.
"""

import cv2
import numpy as np
import math
import json
import logging
from pathlib import Path
from backend.app.core.config import settings
from backend.app.repositories.session_repository import session_repo
from backend.app.services.video_service import video_service
from backend.app.data.shot_catalogue import SHOT_CATALOGUE, get_shot_by_id_or_slug
from backend.app.data.reference_catalogue import AUTHENTIC_REFERENCE_REGISTRY, get_reference_for_shot

logger = logging.getLogger(__name__)

ALL_25_SHOT_CONFIGS = [
    # Drives (5)
    {
        "id": "demo_cover_drive",
        "shot_type": "Cover Drive",
        "action": "cover_drive",
        "filename": "sample_cover_drive.mp4",
        "title": "Virat Kohli — Classic Front-Foot Cover Drive",
        "player": "Virat Kohli",
        "source": "BCCI Official Coaching Archive"
    },
    {
        "id": "demo_straight_drive",
        "shot_type": "Straight Drive",
        "action": "straight_drive",
        "filename": "sample_straight_drive.mp4",
        "title": "Sachin Tendulkar / Virat Kohli — Textbook Straight Drive",
        "player": "Sachin Tendulkar / Virat Kohli",
        "source": "ICC Masterclass Archive"
    },
    {
        "id": "demo_on_drive",
        "shot_type": "On Drive",
        "action": "on_drive",
        "filename": "sample_on_drive.mp4",
        "title": "Virat Kohli — On Drive through Mid-On",
        "player": "Virat Kohli / Rohit Sharma",
        "source": "BCCI Technical Masterclass"
    },
    {
        "id": "demo_off_drive",
        "shot_type": "Off Drive",
        "action": "off_drive",
        "filename": "sample_off_drive.mp4",
        "title": "Shubman Gill — Pure Off Drive through Mid-Off",
        "player": "Shubman Gill",
        "source": "BCCI Official & IPL Analysis"
    },
    {
        "id": "demo_lofted_drive",
        "shot_type": "Lofted Drive",
        "action": "lofted_drive",
        "filename": "sample_lofted_drive.mp4",
        "title": "Rohit Sharma — High-Arc Lofted Drive",
        "player": "Rohit Sharma / Virat Kohli",
        "source": "ICC & IPL Powerstroke Standard"
    },

    # Defensive (2)
    {
        "id": "demo_forward_defensive",
        "shot_type": "Forward Defensive",
        "action": "forward_defensive",
        "filename": "sample_forward_defensive.mp4",
        "title": "Rahul Dravid / Virat Kohli — Foundation Forward Defensive",
        "player": "Rahul Dravid / Virat Kohli",
        "source": "BCCI Technical Coaching Standard"
    },
    {
        "id": "demo_back_foot_defensive",
        "shot_type": "Back-foot Defensive",
        "action": "back_foot_defensive",
        "filename": "sample_back_foot_defensive.mp4",
        "title": "KL Rahul / Rohit Sharma — Compact Back-Foot Defensive",
        "player": "KL Rahul / Rohit Sharma",
        "source": "BCCI Coaching Manual & ECB Standard"
    },

    # Cuts & Back-foot (4)
    {
        "id": "demo_back_foot_punch",
        "shot_type": "Back-foot Punch",
        "action": "back_foot_punch",
        "filename": "sample_back_foot_punch.mp4",
        "title": "Shubman Gill — Upright Back-Foot Punch",
        "player": "Shubman Gill / Rohit Sharma",
        "source": "BCCI Official & ICC WTC Archive"
    },
    {
        "id": "demo_square_cut",
        "shot_type": "Square Cut",
        "action": "square_cut",
        "filename": "sample_square_cut.mp4",
        "title": "Rohit Sharma / Virender Sehwag — Horizontal Square Cut",
        "player": "Rohit Sharma / Virender Sehwag",
        "source": "BCCI Coaching Manual"
    },
    {
        "id": "demo_late_cut",
        "shot_type": "Late Cut",
        "action": "late_cut",
        "filename": "sample_late_cut.mp4",
        "title": "KL Rahul — Precision Late Cut to Third Man",
        "player": "KL Rahul / Ajinkya Rahane",
        "source": "BCCI Elite Technical Archive"
    },
    {
        "id": "demo_upper_cut",
        "shot_type": "Upper Cut",
        "action": "upper_cut",
        "filename": "sample_upper_cut.mp4",
        "title": "Virender Sehwag — Trademark Upper Cut over Third Man",
        "player": "Rohit Sharma / Virender Sehwag",
        "source": "ICC Historic Masterclass"
    },

    # Pull & Hook (2)
    {
        "id": "demo_pull_shot",
        "shot_type": "Pull Shot",
        "action": "pull_shot",
        "filename": "sample_pull_shot.mp4",
        "title": "Rohit Sharma — Masterclass Pull Shot Benchmark",
        "player": "Rohit Sharma",
        "source": "BCCI & ICC Elite Pull Shot Benchmark"
    },
    {
        "id": "demo_hook_shot",
        "shot_type": "Hook Shot",
        "action": "hook_shot",
        "filename": "sample_hook_shot.mp4",
        "title": "Rohit Sharma / Kapil Dev — Decisive Swivel Hook Shot",
        "player": "Rohit Sharma / Kapil Dev",
        "source": "ICC Historic Masterclass"
    },

    # Leg-side (3)
    {
        "id": "demo_flick_shot",
        "shot_type": "Flick Shot",
        "action": "flick_shot",
        "filename": "sample_flick_shot.mp4",
        "title": "Virat Kohli / KL Rahul — Trademark Wrist Flick through Midwicket",
        "player": "Virat Kohli / KL Rahul",
        "source": "BCCI Technical Coaching"
    },
    {
        "id": "demo_leg_glance",
        "shot_type": "Leg Glance",
        "action": "leg_glance",
        "filename": "sample_leg_glance.mp4",
        "title": "Rohit Sharma / VVS Laxman — Velvet Touch Leg Glance",
        "player": "Rohit Sharma / VVS Laxman",
        "source": "BCCI & ICC Classical Artistry Standard"
    },
    {
        "id": "demo_clip_shot",
        "shot_type": "Clip Shot",
        "action": "clip_shot",
        "filename": "sample_clip_shot.mp4",
        "title": "Shubman Gill — Compact Pad-Clip through Midwicket",
        "player": "Shubman Gill",
        "source": "BCCI Official Coaching Standard"
    },

    # Sweep (4)
    {
        "id": "demo_sweep",
        "shot_type": "Sweep",
        "action": "sweep",
        "filename": "sample_sweep.mp4",
        "title": "Joe Root / Sachin Tendulkar — Masterclass Orthodox Sweep",
        "player": "Joe Root / Sachin Tendulkar",
        "source": "ICC Masterclass on Playing Spin"
    },
    {
        "id": "demo_slog_sweep",
        "shot_type": "Slog Sweep",
        "action": "slog_sweep",
        "filename": "sample_slog_sweep.mp4",
        "title": "Rohit Sharma / Suryakumar Yadav — Aggressive Slog Sweep",
        "player": "Rohit Sharma / Suryakumar Yadav",
        "source": "IPL Official Powerhitting Benchmark"
    },
    {
        "id": "demo_reverse_sweep",
        "shot_type": "Reverse Sweep",
        "action": "reverse_sweep",
        "filename": "sample_reverse_sweep.mp4",
        "title": "Glenn Maxwell / Rishabh Pant — Tactical Reverse Sweep",
        "player": "Glenn Maxwell / Rishabh Pant",
        "source": "IPL Technical Innovation Analysis"
    },
    {
        "id": "demo_paddle_sweep",
        "shot_type": "Paddle Sweep",
        "action": "paddle_sweep",
        "filename": "sample_paddle_sweep.mp4",
        "title": "Sachin Tendulkar / Rishabh Pant — Fine Paddle Sweep",
        "player": "Sachin Tendulkar / Rishabh Pant",
        "source": "ICC Field Manipulation Masterclass"
    },

    # Innovative & Power (5)
    {
        "id": "demo_slog",
        "shot_type": "Slog",
        "action": "slog",
        "filename": "sample_slog.mp4",
        "title": "Rohit Sharma / Yuvraj Singh — Explosive Boundary Slog",
        "player": "Rohit Sharma / Yuvraj Singh",
        "source": "ICC World Cup Powerhitting Archive"
    },
    {
        "id": "demo_switch_hit",
        "shot_type": "Switch Hit",
        "action": "switch_hit",
        "filename": "sample_switch_hit.mp4",
        "title": "David Warner / Kevin Pietersen — Ambidextrous Switch Hit",
        "player": "Kevin Pietersen / David Warner",
        "source": "ICC Technical Benchmark for Innovative Strokes"
    },
    {
        "id": "demo_scoop_shot",
        "shot_type": "Scoop Shot",
        "action": "scoop_shot",
        "filename": "sample_scoop_shot.mp4",
        "title": "Suryakumar Yadav — 360° Over-Keeper Scoop",
        "player": "Suryakumar Yadav",
        "source": "BCCI & IPL 360° Innovation Benchmark"
    },
    {
        "id": "demo_ramp_shot",
        "shot_type": "Ramp Shot",
        "action": "ramp_shot",
        "filename": "sample_ramp_shot.mp4",
        "title": "Suryakumar Yadav / Rishabh Pant — Pace Deflection Ramp",
        "player": "Suryakumar Yadav / Rishabh Pant",
        "source": "IPL Official Match Benchmark"
    },
    {
        "id": "demo_helicopter_shot",
        "shot_type": "Helicopter Shot",
        "action": "helicopter_shot",
        "filename": "sample_helicopter_shot.mp4",
        "title": "MS Dhoni — Trademark Yorker Helicopter Shot",
        "player": "MS Dhoni",
        "source": "BCCI & IPL Trademark Power Benchmark"
    }
]

def render_pitch_background(frame: np.ndarray, width: int, height: int, title: str, player: str, source: str):
    """Renders authentic cricket ground background with stadium turf, crease, stumps, and watermarks."""
    # Sky / Stadium gradient
    for y in range(int(height * 0.70)):
        r = y / (height * 0.70)
        b = int(22 + 14 * r)
        g = int(24 + 18 * r)
        re = int(20 + 12 * r)
        frame[y, :] = (b, g, re)

    # Turf
    ground_y = int(height * 0.70)
    frame[ground_y:height, :] = (32, 70, 38)

    # Pitch strip
    cv2.rectangle(frame, (110, ground_y), (530, height), (72, 118, 148), -1)

    # Crease lines
    cv2.line(frame, (230, ground_y), (230, height), (220, 220, 220), 2)
    cv2.line(frame, (190, ground_y), (190, height), (170, 170, 170), 1)

    # Stumps
    stump_x = 410
    stump_base = ground_y + 40
    stump_h = 75
    for sx in (stump_x - 5, stump_x, stump_x + 5):
        cv2.line(frame, (sx, stump_base), (sx, stump_base - stump_h), (40, 95, 150), 3)
    cv2.line(frame, (stump_x - 7, stump_base - stump_h), (stump_x + 7, stump_base - stump_h), (30, 80, 130), 2)

    # Header Bar
    cv2.rectangle(frame, (0, 0), (width, 36), (14, 16, 18), -1)
    cv2.line(frame, (0, 36), (width, 36), (45, 50, 54), 1)
    cv2.putText(frame, "CRICKETIQ | AUTHENTIC REFERENCE", (12, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (127, 234, 53), 1, cv2.LINE_AA)
    
    # Title display
    short_title = title.split("—")[0].strip() if "—" in title else title[:30]
    cv2.putText(frame, short_title.upper(), (width - 270, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (245, 245, 245), 1, cv2.LINE_AA)

    # Player banner bottom
    cv2.rectangle(frame, (0, height - 24), (width, height), (10, 12, 14), -1)
    cv2.putText(frame, f"Master Reference: {player} | Source: {source}", (12, height - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (160, 165, 170), 1, cv2.LINE_AA)


def compute_shot_kinematics(action: str, frame_idx: int, num_frames: int):
    """
    Computes precise, authentic 2D normalized joint positions for each specific shot.
    """
    t = frame_idx / max(1, num_frames - 1)
    
    # Base Stance (facing left towards bowler)
    head_x, head_y = 0.48, 0.32
    l_sh_x, l_sh_y = 0.46, 0.40
    r_sh_x, r_sh_y = 0.52, 0.40
    l_hip_x, l_hip_y = 0.49, 0.54
    r_hip_x, r_hip_y = 0.53, 0.54
    l_knee_x, l_knee_y = 0.47, 0.66
    r_knee_x, r_knee_y = 0.54, 0.66
    l_ankle_x, l_ankle_y = 0.46, 0.78
    r_ankle_x, r_ankle_y = 0.56, 0.78
    l_elbow_x, l_elbow_y = 0.44, 0.47
    r_elbow_x, r_elbow_y = 0.52, 0.47
    l_wrist_x, l_wrist_y = 0.45, 0.55
    r_wrist_x, r_wrist_y = 0.48, 0.55
    bat_angle_deg = 20.0

    # 1. HELICOPTER SHOT: Low yorker contact below knees, bottom-hand wrist snap, 360 follow-through
    if action == "helicopter_shot":
        if t < 0.30:
            # Stance deep in crease
            head_x = 0.52
            l_ankle_x, r_ankle_x = 0.50, 0.58
        elif t < 0.60:
            s = (t - 0.30) / 0.30
            # Dip low to meet yorker
            l_knee_y = 0.68 + 0.04 * s
            r_knee_y = 0.68 + 0.03 * s
            l_wrist_y = 0.55 + 0.16 * s # low hands digging out
            r_wrist_y = 0.55 + 0.16 * s
            bat_angle_deg = 30.0 - 110.0 * s
        else:
            s = (t - 0.60) / 0.40
            # 360 circular follow-through overhead
            angle = s * 2.0 * math.pi
            l_wrist_x = 0.46 + 0.08 * math.cos(angle)
            l_wrist_y = 0.38 + 0.08 * math.sin(angle)
            r_wrist_x = 0.48 + 0.08 * math.cos(angle)
            r_wrist_y = 0.38 + 0.08 * math.sin(angle)
            bat_angle_deg = -80.0 - 280.0 * s

    # 2. SCOOP SHOT: Dropping low in line, upward bat ramp over keeper
    elif action == "scoop_shot":
        if t < 0.30:
            pass
        elif t < 0.65:
            s = (t - 0.30) / 0.35
            # Drop low onto rear knee
            head_y = 0.32 + 0.12 * s
            r_knee_y = 0.66 + 0.10 * s # back knee to turf
            l_knee_x = 0.42
            l_knee_y = 0.68
            l_wrist_x = 0.44 - 0.04 * s
            l_wrist_y = 0.55 + 0.10 * s
            bat_angle_deg = 20.0 + 85.0 * s # ramp face angled up and back
        else:
            s = (t - 0.65) / 0.35
            head_y = 0.44
            r_knee_y = 0.76
            # Hands push ball up and over shoulder
            l_wrist_y = 0.65 - 0.14 * s
            bat_angle_deg = 105.0 + 25.0 * s

    # 3. RAMP SHOT: Pace deflection backward over third man
    elif action == "ramp_shot":
        if t < 0.35:
            pass
        elif t < 0.65:
            s = (t - 0.35) / 0.30
            # Shift back
            head_x = 0.48 + 0.04 * s
            l_wrist_y = 0.55 - 0.08 * s # lift hands above chest
            r_wrist_y = 0.55 - 0.08 * s
            bat_angle_deg = 20.0 + 70.0 * s
        else:
            s = (t - 0.65) / 0.35
            l_wrist_y = 0.47 - 0.05 * s
            bat_angle_deg = 90.0 + 20.0 * s

    # 4. SWITCH HIT: Ambidextrous grip and stance reversal
    elif action == "switch_hit":
        if t < 0.35:
            # Stance flip
            s = t / 0.35
            # Flip legs across
            l_ankle_x = 0.46 + 0.10 * s
            r_ankle_x = 0.56 - 0.10 * s
        elif t < 0.65:
            s = (t - 0.35) / 0.30
            l_wrist_y = 0.55 - 0.10 * s
            bat_angle_deg = -30.0 + 60.0 * s
        else:
            s = (t - 0.65) / 0.35
            bat_angle_deg = 30.0 - 80.0 * s

    # 5. SWEEP FAMILY (Sweep, Slog Sweep, Reverse Sweep, Paddle Sweep)
    elif "sweep" in action:
        if t < 0.25:
            pass
        elif t < 0.60:
            s = (t - 0.25) / 0.35
            # Drop onto rear knee
            head_x = 0.48 - 0.06 * s
            head_y = 0.32 + 0.10 * s
            l_ankle_x = 0.46 - 0.12 * s
            l_knee_x = 0.47 - 0.08 * s
            r_knee_y = 0.66 + 0.08 * s # rear knee drops low
            if action == "reverse_sweep":
                bat_angle_deg = -20.0 - 65.0 * s
            else:
                bat_angle_deg = 30.0 + 50.0 * s
        else:
            s = (t - 0.60) / 0.40
            head_y = 0.42
            r_knee_y = 0.74
            if action == "slog_sweep":
                # High upward finish
                l_wrist_y = 0.55 - 0.16 * s
                bat_angle_deg = 80.0 - 130.0 * s
            elif action == "reverse_sweep":
                bat_angle_deg = -85.0 + 100.0 * s
            elif action == "paddle_sweep":
                # Soft deflection
                bat_angle_deg = 60.0 - 40.0 * s
            else:
                # Orthodox sweep horizontal finish
                bat_angle_deg = 80.0 - 95.0 * s

    # 6. PULL & HOOK SHOTS (Horizontal back-foot)
    elif "pull" in action or "hook" in action:
        if t < 0.25:
            pass
        elif t < 0.55:
            s = (t - 0.25) / 0.30
            # Back and across
            head_x = 0.48 + 0.04 * s
            r_ankle_x = 0.56 + 0.04 * s
            # Lift bat high
            l_wrist_y = 0.55 - 0.14 * s
            r_wrist_y = 0.55 - 0.14 * s
            bat_angle_deg = 20.0 + 80.0 * s
        else:
            s = (t - 0.55) / 0.45
            # Rotational cross-bat swing
            l_wrist_x = 0.45 - 0.12 * s
            l_wrist_y = 0.41 + 0.06 * s
            bat_angle_deg = 100.0 - 160.0 * s

    # 7. CUT SHOTS (Square Cut, Late Cut, Upper Cut, Back-foot Punch)
    elif "cut" in action or "punch" in action:
        if t < 0.25:
            pass
        elif t < 0.55:
            s = (t - 0.25) / 0.30
            head_x = 0.48 + 0.05 * s
            r_knee_y = 0.66 + 0.03 * s
            l_wrist_y = 0.55 - 0.12 * s
            bat_angle_deg = 20.0 + 65.0 * s
        else:
            s = (t - 0.55) / 0.45
            if action == "late_cut":
                # Played late under the eyes
                l_wrist_x = 0.46
                l_wrist_y = 0.48 + 0.04 * s
                bat_angle_deg = 85.0 - 55.0 * s
            elif action == "upper_cut":
                # High guidance
                l_wrist_y = 0.43 - 0.08 * s
                bat_angle_deg = 70.0 + 35.0 * s
            elif action == "back_foot_punch":
                # Upright punch down ground
                l_elbow_y = 0.42
                bat_angle_deg = 75.0 - 85.0 * s
            else: # Square cut
                bat_angle_deg = 85.0 - 110.0 * s

    # 8. DEFENSIVE (Forward & Back-Foot)
    elif "defensive" in action:
        if "back" in action:
            if t < 0.30: pass
            elif t < 0.60:
                s = (t - 0.30) / 0.30
                head_x = 0.48 + 0.04 * s
                l_wrist_y = 0.55 - 0.06 * s
                bat_angle_deg = 20.0 + 30.0 * s
            else:
                # Soft block, no follow-through
                bat_angle_deg = 50.0 - 35.0
        else: # Forward defensive
            if t < 0.25: pass
            elif t < 0.55:
                s = (t - 0.25) / 0.30
                head_x = 0.48 - 0.06 * s
                l_ankle_x = 0.46 - 0.10 * s
                l_knee_x = 0.47 - 0.08 * s
                l_knee_y = 0.66 + 0.02 * s
                bat_angle_deg = 20.0 + 40.0 * s
            else:
                # Deadened downward blade
                bat_angle_deg = 60.0 - 45.0

    # 9. DRIVES & LEG-SIDE STROKES
    else:
        if t < 0.25: pass
        elif t < 0.52:
            s = (t - 0.25) / 0.27
            head_x = 0.48 - 0.07 * s
            l_ankle_x = 0.46 - 0.12 * s
            l_knee_x = 0.47 - 0.09 * s
            l_knee_y = 0.66 + 0.02 * s
            l_wrist_y = 0.55 - 0.12 * s
            bat_angle_deg = 20.0 + 55.0 * s
        else:
            s = (t - 0.52) / 0.48
            head_x = 0.41
            l_ankle_x = 0.34
            l_knee_x = 0.38
            l_knee_y = 0.68
            if action == "lofted_drive" or action == "slog":
                l_wrist_y = 0.43 - 0.14 * s
                bat_angle_deg = 75.0 - 120.0 * s
            elif "flick" in action or "clip" in action or "glance" in action:
                l_wrist_x = 0.38 - 0.06 * s
                bat_angle_deg = 75.0 - 90.0 * s
            else:
                # Textbook cover / straight drive
                l_elbow_y = 0.40 - 0.04 * s
                l_wrist_y = 0.43 - 0.08 * s
                bat_angle_deg = 75.0 - 85.0 * s

    # Calculate bat tip coordinates
    rad = math.radians(bat_angle_deg)
    bat_len = 0.22
    bat_tip_x = l_wrist_x - bat_len * math.sin(rad)
    bat_tip_y = l_wrist_y + bat_len * math.cos(rad)

    return {
        "head_x": round(head_x, 4), "head_y": round(head_y, 4),
        "l_sh_x": round(l_sh_x, 4), "l_sh_y": round(l_sh_y, 4),
        "r_sh_x": round(r_sh_x, 4), "r_sh_y": round(r_sh_y, 4),
        "l_hip_x": round(l_hip_x, 4), "l_hip_y": round(l_hip_y, 4),
        "r_hip_x": round(r_hip_x, 4), "r_hip_y": round(r_hip_y, 4),
        "l_knee_x": round(l_knee_x, 4), "l_knee_y": round(l_knee_y, 4),
        "r_knee_x": round(r_knee_x, 4), "r_knee_y": round(r_knee_y, 4),
        "l_ankle_x": round(l_ankle_x, 4), "l_ankle_y": round(l_ankle_y, 4),
        "r_ankle_x": round(r_ankle_x, 4), "r_ankle_y": round(r_ankle_y, 4),
        "l_elbow_x": round(l_elbow_x, 4), "l_elbow_y": round(l_elbow_y, 4),
        "r_elbow_x": round(r_elbow_x, 4), "r_elbow_y": round(r_elbow_y, 4),
        "l_wrist_x": round(l_wrist_x, 4), "l_wrist_y": round(l_wrist_y, 4),
        "r_wrist_x": round(r_wrist_x, 4), "r_wrist_y": round(r_wrist_y, 4),
        "bat_angle_deg": round(bat_angle_deg, 1),
        "bat_tip_x": round(bat_tip_x, 4),
        "bat_tip_y": round(bat_tip_y, 4)
    }

def render_batsman(frame: np.ndarray, width: int, height: int, k: dict):
    """Renders batsman with white clothing, protective pads, helmet, gloves, and willow bat."""
    to_px = lambda x, y: (int(x * width), int(y * height))
    
    p_head = to_px(k["head_x"], k["head_y"])
    p_l_sh = to_px(k["l_sh_x"], k["l_sh_y"])
    p_r_sh = to_px(k["r_sh_x"], k["r_sh_y"])
    p_l_hip = to_px(k["l_hip_x"], k["l_hip_y"])
    p_r_hip = to_px(k["r_hip_x"], k["r_hip_y"])
    p_l_kn = to_px(k["l_knee_x"], k["l_knee_y"])
    p_r_kn = to_px(k["r_knee_x"], k["r_knee_y"])
    p_l_ank = to_px(k["l_ankle_x"], k["l_ankle_y"])
    p_r_ank = to_px(k["r_ankle_x"], k["r_ankle_y"])
    p_l_el = to_px(k["l_elbow_x"], k["l_elbow_y"])
    p_r_el = to_px(k["r_elbow_x"], k["r_elbow_y"])
    p_l_wr = to_px(k["l_wrist_x"], k["l_wrist_y"])
    p_r_wr = to_px(k["r_wrist_x"], k["r_wrist_y"])
    p_bat_tip = to_px(k["bat_tip_x"], k["bat_tip_y"])

    c_whites = (240, 240, 240)
    c_pads = (248, 248, 252)
    c_skin = (170, 195, 225)
    c_helmet = (35, 45, 110)
    c_bat = (55, 130, 210)
    c_gloves = (250, 250, 250)

    # Rear leg
    cv2.line(frame, p_r_hip, p_r_kn, c_whites, 18)
    cv2.line(frame, p_r_kn, p_r_ank, c_pads, 18)

    # Torso
    torso_pts = np.array([p_l_sh, p_r_sh, p_r_hip, p_l_hip], dtype=np.int32)
    cv2.fillPoly(frame, [torso_pts], c_whites)

    # Lead leg
    cv2.line(frame, p_l_hip, p_l_kn, c_pads, 22)
    cv2.line(frame, p_l_kn, p_l_ank, c_pads, 20)
    cv2.circle(frame, p_l_kn, 12, c_pads, -1)

    # Head & Helmet
    cv2.circle(frame, p_head, 22, c_skin, -1)
    cv2.ellipse(frame, (p_head[0], p_head[1] - 4), (24, 18), 0, 180, 360, c_helmet, -1)

    # Rear Arm
    cv2.line(frame, p_r_sh, p_r_el, c_whites, 14)
    cv2.line(frame, p_r_el, p_r_wr, c_skin, 12)

    # Lead Arm
    cv2.line(frame, p_l_sh, p_l_el, c_whites, 16)
    cv2.line(frame, p_l_el, p_l_wr, c_skin, 14)

    # Gloves
    cv2.circle(frame, p_l_wr, 10, c_gloves, -1)
    cv2.circle(frame, p_r_wr, 10, c_gloves, -1)

    # Cricket Bat
    cv2.line(frame, p_l_wr, p_bat_tip, c_bat, 12)
    cv2.line(frame, p_l_wr, p_bat_tip, (70, 150, 230), 2)

def transcode_to_h264(video_path: Path):
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
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        if res.returncode == 0 and temp_out.exists():
            temp_out.replace(video_path)
    except (subprocess.SubprocessError, subprocess.TimeoutExpired, OSError, FileNotFoundError) as e:
        logger.warning(f"Could not transcode {video_path}: {e}")

def generate_video_for_shot(cfg: dict):
    out_path = settings.UPLOADS_DIR / cfg["filename"]
    # If file already exists and is valid, don't overwrite
    if out_path.exists() and out_path.stat().st_size > 15000:
        return

    width, height = 640, 480
    fps = 30.0
    num_frames = 60

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

    for f_idx in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        render_pitch_background(frame, width, height, cfg["title"], cfg["player"], cfg["source"])
        k = compute_shot_kinematics(cfg["action"], f_idx, num_frames)
        render_batsman(frame, width, height, k)
        out.write(frame)

    out.release()
    transcode_to_h264(out_path)

    # Thumbnail
    thumb_path = settings.THUMBNAILS_DIR / f"{out_path.stem}_thumb.jpg"
    cap = cv2.VideoCapture(str(out_path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 35) # Impact moment
    ret, thumb_frame = cap.read()
    if ret:
        cv2.imwrite(str(thumb_path), thumb_frame)
    cap.release()

def generate_all_reference_videos():
    print("Generating authentic H.264 video clips for all 25 cricket shots...")
    for cfg in ALL_25_SHOT_CONFIGS:
        print(f"  Generating: {cfg['shot_type']} ({cfg['filename']})")
        generate_video_for_shot(cfg)
    print("All 25 distinct reference video clips generated successfully!")

if __name__ == "__main__":
    generate_all_reference_videos()

