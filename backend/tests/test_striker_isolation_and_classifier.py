"""
Comprehensive Acceptance Tests for:
  (A) Bowler vs Striker Isolation & Multi-Person Tracking
  (B) Honest Hierarchical Shot Classifier & Discrepancy Reporting
"""

import os, sys
sys.path.insert(0, os.path.abspath("."))

import pytest
import numpy as np
from pathlib import Path
from backend.app.services.pose_service import MultiPersonTracker, PoseService
from backend.app.services.shot_classifier_service import shot_classifier_service

# ---------------------------------------------------------------------------
# FIX A: STRIKER ISOLATION TESTS
# ---------------------------------------------------------------------------

def test_striker_vs_bowler_classification():
    """
    Simulates two people across 60 frames:
      Track 0: Stationary batter holding bat pose at crease, then executing rotational swing.
      Track 1: Bowler running in with large hip translation and overhead bowling arm arc.
    Verifies that Track 0 is classified as 'striker' (locked) and Track 1 as 'bowler' (excluded).
    """
    tracker = MultiPersonTracker(max_disappeared=15)

    # Frame-by-frame simulation
    for f in range(60):
        # Person 0: Striker at crease (x~0.30, y~0.40)
        # Setup (f 0..25): hands together (lw ~ rw), minimal hip movement
        # Swing (f 26..45): peak wrist speed
        is_swing = (26 <= f <= 40)
        lw_x = 0.32 if not is_swing else 0.32 + (f - 26) * 0.015
        lw_y = 0.45 if not is_swing else 0.45 + (f - 26) * 0.018
        rw_x = 0.30 if not is_swing else 0.30 + (f - 26) * 0.014
        rw_y = 0.46 if not is_swing else 0.46 + (f - 26) * 0.017

        p0_lms = [
            {"x": 0.31, "y": 0.20, "visibility": 0.9}, # 0: nose
        ] + [{"x": 0.0, "y": 0.0, "visibility": 0.0}] * 10 + [
            {"x": 0.28, "y": 0.30, "visibility": 0.9}, # 11: left shoulder
            {"x": 0.34, "y": 0.30, "visibility": 0.9}, # 12: right shoulder
            {"x": 0.29, "y": 0.38, "visibility": 0.9}, # 13: left elbow
            {"x": 0.33, "y": 0.38, "visibility": 0.9}, # 14: right elbow
            {"x": lw_x, "y": lw_y, "visibility": 0.9}, # 15: left wrist
            {"x": rw_x, "y": rw_y, "visibility": 0.9}, # 16: right wrist
        ] + [{"x": 0.0, "y": 0.0, "visibility": 0.0}] * 6 + [
            {"x": 0.29, "y": 0.50, "visibility": 0.9}, # 23: left hip
            {"x": 0.33, "y": 0.50, "visibility": 0.9}, # 24: right hip
            {"x": 0.29, "y": 0.65, "visibility": 0.9}, # 25: left knee
            {"x": 0.33, "y": 0.65, "visibility": 0.9}, # 26: right knee
            {"x": 0.28, "y": 0.85, "visibility": 0.9}, # 27: left ankle
            {"x": 0.34, "y": 0.85, "visibility": 0.9}, # 28: right ankle
        ] + [{"x": 0.0, "y": 0.0, "visibility": 0.0}] * 4

        # Person 1: Bowler running in from far end
        # Translation: hip moves from x=0.85 down to x=0.55 (disp = 0.30)
        # Arm: overhead delivery arc (wrist y < head y) on frames 15..25
        b_x = 0.85 - (f * 0.005)
        b_y = 0.35 + (f * 0.002)
        overhead = (15 <= f <= 25)
        b_lw_y = 0.12 if overhead else b_y + 0.10

        p1_lms = [
            {"x": b_x, "y": b_y - 0.10, "visibility": 0.9}, # nose
        ] + [{"x": 0.0, "y": 0.0, "visibility": 0.0}] * 10 + [
            {"x": b_x - 0.03, "y": b_y - 0.05, "visibility": 0.9}, # 11
            {"x": b_x + 0.03, "y": b_y - 0.05, "visibility": 0.9}, # 12
            {"x": b_x - 0.04, "y": b_y, "visibility": 0.9},        # 13
            {"x": b_x + 0.04, "y": b_y, "visibility": 0.9},        # 14
            {"x": b_x - 0.03, "y": b_lw_y, "visibility": 0.9},     # 15
            {"x": b_x + 0.03, "y": b_y + 0.10, "visibility": 0.9},# 16
        ] + [{"x": 0.0, "y": 0.0, "visibility": 0.0}] * 6 + [
            {"x": b_x - 0.02, "y": b_y + 0.15, "visibility": 0.9}, # 23
            {"x": b_x + 0.02, "y": b_y + 0.15, "visibility": 0.9}, # 24
            {"x": b_x - 0.02, "y": b_y + 0.30, "visibility": 0.9}, # 25
            {"x": b_x + 0.02, "y": b_y + 0.30, "visibility": 0.9}, # 26
            {"x": b_x - 0.02, "y": b_y + 0.45, "visibility": 0.9}, # 27
            {"x": b_x + 0.02, "y": b_y + 0.45, "visibility": 0.9}, # 28
        ] + [{"x": 0.0, "y": 0.0, "visibility": 0.0}] * 4

        # Detections for frame f
        poses = [
            {"landmarks": p0_lms, "bbox": [0.26, 0.18, 0.36, 0.88], "world_landmarks": None},
            {"landmarks": p1_lms, "bbox": [b_x - 0.05, b_y - 0.12, b_x + 0.05, b_y + 0.50], "world_landmarks": None}
        ]
        tracker.update(poses, frame_idx=f)

    best_tid, classifications, needs_conf = tracker.classify_tracks(total_frames=60)

    assert best_tid == 0, f"Expected Track 0 (striker) to be selected, but got Track {best_tid}"
    assert classifications[0]["role"] == "striker"
    assert classifications[1]["role"] == "bowler", f"Expected Track 1 to be classified as bowler, got {classifications[1]['role']}"
    assert classifications[0]["striker_score"] > classifications[1]["striker_score"]
    assert "cue1_bat_pose_score" in classifications[0]["evidence"]
    assert "cue2_position_score" in classifications[0]["evidence"]
    assert "cue3_motion_score" in classifications[0]["evidence"]
    assert "cue4_temporal_score" in classifications[0]["evidence"]


def test_non_striker_exclusion():
    """
    Simulates a non-striker standing still at the non-striker crease.
    Verifies they are classified as non-striker and excluded from striker selection.
    """
    tracker = MultiPersonTracker(max_disappeared=15)
    for f in range(50):
        # Striker
        is_swing = (20 <= f <= 35)
        lw_x = 0.25 if not is_swing else 0.25 + (f - 20) * 0.015
        p0_lms = [{"x": 0.25, "y": 0.2, "visibility": 0.9}] * 15 + [
            {"x": lw_x, "y": 0.4, "visibility": 0.9},
            {"x": lw_x, "y": 0.4, "visibility": 0.9}
        ] + [{"x": 0.25, "y": 0.5, "visibility": 0.9}] * 16

        # Non-striker: completely still
        p1_lms = [{"x": 0.80, "y": 0.3, "visibility": 0.9}] * 33

        poses = [
            {"landmarks": p0_lms, "bbox": [0.20, 0.18, 0.30, 0.85]},
            {"landmarks": p1_lms, "bbox": [0.75, 0.25, 0.85, 0.85]}
        ]
        tracker.update(poses, frame_idx=f)

    best_tid, classifications, _ = tracker.classify_tracks(total_frames=50)
    assert best_tid == 0
    assert classifications[1]["role"] == "non-striker"
    assert classifications[0]["striker_score"] > 0.60


# ---------------------------------------------------------------------------
# FIX B: HONEST HIERARCHICAL SHOT CLASSIFIER TESTS
# ---------------------------------------------------------------------------

def test_leave_no_shot_attempted():
    """
    Simulates a clip where the batsman leaves the ball (no downward swing or follow-through).
    Verifies that the classifier honesty reports 'Leave / No Shot Attempted', NOT 'Cover Drive'.
    """
    frame_metrics = []
    for f in range(45):
        # Batter stands stationary with minimal movement
        frame_metrics.append({
            "pose_detected": True,
            "frame_index": f,
            "timestamp_sec": f / 30.0,
            "lead_knee_angle": 160.0,
            "rear_knee_angle": 162.0,
            "torso_inclination": 12.0,
            "stance_width_norm": 1.0,
            "lead_wrist_x": 0.35,
            "lead_wrist_y": 0.45,
            "lead_wrist_speed": 0.005,
            "landmarks": [
                {"x": 0.35, "y": 0.20}, # 0
            ] + [{"x": 0.0, "y": 0.0}] * 10 + [
                {"x": 0.33, "y": 0.28}, # 11
                {"x": 0.37, "y": 0.28}, # 12
            ] + [{"x": 0.0, "y": 0.0}] * 10 + [
                {"x": 0.33, "y": 0.55}, # 23
                {"x": 0.37, "y": 0.55}, # 24
            ]
        })

    res = shot_classifier_service.classify_sequence(frame_metrics, hint_shot="Cover Drive")
    assert res["predicted_shot"] == "Leave / No Shot Attempted", f"Got: {res['predicted_shot']}"
    assert res["predicted_shot"] != "Cover Drive"
    assert "Leave / No Shot" in res["family"]


def test_straight_drive_vs_cover_drive_honest_separation():
    """
    Tests distinction between Straight Drive and Cover Drive:
      Straight drive has vertical downswing along pitch (dY <= -1.10L, vertical span > 1.40L).
      Cover drive has angled off-side stride and lateral downswing path.
    """
    # 1. Straight Drive Sequence
    straight_frames = []
    for f in range(50):
        t = f / 50.0
        # Stride expansion
        st = 0.8 + (0.5 * t if t < 0.5 else 0.5)
        # Vertical pendulum downswing and upward follow-through
        wy = 0.55 - 0.35 * t
        straight_frames.append({
            "pose_detected": True,
            "frame_index": f,
            "timestamp_sec": f / 30.0,
            "lead_knee_angle": 135.0,
            "rear_knee_angle": 140.0,
            "torso_inclination": 18.0,
            "stance_width_norm": st,
            "lead_wrist_x": 0.35, # no lateral off-side drift
            "lead_wrist_y": wy,
            "lead_wrist_speed": 0.05,
            "landmarks": [
                {"x": 0.35, "y": 0.20},
            ] + [{"x": 0.0, "y": 0.0}] * 10 + [
                {"x": 0.32, "y": 0.28},
                {"x": 0.38, "y": 0.28},
            ] + [{"x": 0.0, "y": 0.0}] * 10 + [
                {"x": 0.32, "y": 0.56},
                {"x": 0.38, "y": 0.56},
            ]
        })

    res_straight = shot_classifier_service.classify_sequence(straight_frames, hint_shot="Cover Drive")
    if res_straight["predicted_shot"] == "Uncertain":
        assert res_straight["is_uncertain"] is True
        assert res_straight["top_candidates"][0]["shot_name"] == "Straight Drive"
    else:
        assert res_straight["predicted_shot"] == "Straight Drive", f"Expected Straight Drive, got {res_straight['predicted_shot']}"
        assert res_straight["soft_warning"] == "You selected Cover Drive, but this looks like a Straight Drive."

    # 2. Cover Drive Sequence (with lateral off-side drift)
    cover_frames = []
    for f in range(50):
        t = f / 50.0
        st = 0.8 + (0.5 * t if t < 0.5 else 0.5)
        # Angled stride and lateral drift to off-side
        wx = 0.35 + (0.12 * t)
        wy = 0.25 + (0.28 * t)
        cover_frames.append({
            "pose_detected": True,
            "frame_index": f,
            "timestamp_sec": f / 30.0,
            "lead_knee_angle": 130.0,
            "rear_knee_angle": 142.0,
            "torso_inclination": 22.0,
            "stance_width_norm": st,
            "lead_wrist_x": wx,
            "lead_wrist_y": wy,
            "lead_wrist_speed": 0.06,
            "landmarks": [
                {"x": 0.35, "y": 0.20},
            ] + [{"x": 0.0, "y": 0.0}] * 10 + [
                {"x": 0.32, "y": 0.28},
                {"x": 0.38, "y": 0.28},
            ] + [{"x": 0.0, "y": 0.0}] * 10 + [
                {"x": 0.32, "y": 0.56},
                {"x": 0.38, "y": 0.56},
            ]
        })

    res_cover = shot_classifier_service.classify_sequence(cover_frames, hint_shot="Cover Drive")
    if res_cover["predicted_shot"] == "Uncertain":
        assert res_cover["is_uncertain"] is True
        assert res_cover["top_candidates"][0]["shot_name"] == "Cover Drive"
    else:
        assert res_cover["predicted_shot"] == "Cover Drive"
        assert res_cover["soft_warning"] is None


def test_left_handed_mirroring_invariance():
    """
    Verifies that a left-handed batter's kinematics are mirrored into the canonical frame,
    producing identical classification to the right-handed counterpart.
    """
    rh_frames = []
    lh_frames = []
    for f in range(50):
        t = f / 50.0
        # Off-side drift: for RH, moves +X (towards covers)
        wx_rh = 0.35 + 0.12 * t
        # For LH, mirrored: moves -X (towards off-side on the opposite side)
        wx_lh = 0.65 - 0.12 * t
        wy = 0.25 + 0.28 * t

        base_frame = {
            "pose_detected": True,
            "frame_index": f,
            "timestamp_sec": f / 30.0,
            "lead_knee_angle": 130.0,
            "rear_knee_angle": 142.0,
            "torso_inclination": 22.0,
            "stance_width_norm": 1.4,
            "lead_wrist_y": wy,
            "lead_wrist_speed": 0.06,
            "landmarks": [
                {"x": 0.5, "y": 0.20},
            ] + [{"x": 0.0, "y": 0.0}] * 10 + [
                {"x": 0.46, "y": 0.28},
                {"x": 0.54, "y": 0.28},
            ] + [{"x": 0.0, "y": 0.0}] * 10 + [
                {"x": 0.46, "y": 0.56},
                {"x": 0.54, "y": 0.56},
            ]
        }

        m_rh = dict(base_frame)
        m_rh["lead_wrist_x"] = wx_rh
        rh_frames.append(m_rh)

        m_lh = dict(base_frame)
        m_lh["lead_wrist_x"] = wx_lh
        lh_frames.append(m_lh)

    res_rh = shot_classifier_service.classify_sequence(rh_frames, handedness="Right")
    res_lh = shot_classifier_service.classify_sequence(lh_frames, handedness="Left")

    assert res_rh["predicted_shot"] == res_lh["predicted_shot"]
    assert res_rh["family"] == res_lh["family"]


def test_uncertainty_reporting_when_margin_is_narrow():
    """
    Verifies that when top-2 candidates are within margin <= 0.10,
    is_uncertain is set to True, and uncertainty_label reports 'Unsure: [A] or [B]'.
    """
    # Create ambiguous sequence
    frames = []
    for f in range(40):
        frames.append({
            "pose_detected": True,
            "frame_index": f,
            "timestamp_sec": f / 30.0,
            "lead_knee_angle": 138.0,
            "rear_knee_angle": 140.0,
            "torso_inclination": 18.0,
            "stance_width_norm": 1.26, # right between defensive and drive
            "lead_wrist_x": 0.35,
            "lead_wrist_y": 0.30 + (f * 0.005),
            "lead_wrist_speed": 0.025,
            "landmarks": [
                {"x": 0.35, "y": 0.20},
            ] + [{"x": 0.0, "y": 0.0}] * 10 + [
                {"x": 0.32, "y": 0.28},
                {"x": 0.38, "y": 0.28},
            ] + [{"x": 0.0, "y": 0.0}] * 10 + [
                {"x": 0.32, "y": 0.56},
                {"x": 0.38, "y": 0.56},
            ]
        })

    res = shot_classifier_service.classify_sequence(frames)
    top_cands = res["top_candidates"]
    if len(top_cands) >= 2 and (top_cands[0]["score"] - top_cands[1]["score"] <= 0.10):
        assert res["is_uncertain"] is True
        assert "Unsure:" in res["uncertainty_label"]

if __name__ == "__main__":
    print("Running test_striker_vs_bowler_classification()...")
    test_striker_vs_bowler_classification()
    print("PASS: test_striker_vs_bowler_classification")

    print("Running test_non_striker_exclusion()...")
    test_non_striker_exclusion()
    print("PASS: test_non_striker_exclusion")

    print("Running test_leave_no_shot_attempted()...")
    test_leave_no_shot_attempted()
    print("PASS: test_leave_no_shot_attempted")

    print("Running test_straight_drive_vs_cover_drive_honest_separation()...")
    test_straight_drive_vs_cover_drive_honest_separation()
    print("PASS: test_straight_drive_vs_cover_drive_honest_separation")

    print("Running test_left_handed_mirroring_invariance()...")
    test_left_handed_mirroring_invariance()
    print("PASS: test_left_handed_mirroring_invariance")

    print("Running test_uncertainty_reporting_when_margin_is_narrow()...")
    test_uncertainty_reporting_when_margin_is_narrow()
    print("PASS: test_uncertainty_reporting_when_margin_is_narrow")

    print("\nALL ACCEPTANCE TESTS PASSED SUCCESSFULLY!")
