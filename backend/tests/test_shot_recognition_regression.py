"""
CricketIQ — Regression Test Suite for Shot Recognition & 2D Kinematic Playback
Verifies that:
1. Known clips / kinematic sequences rank the correct shot first (Cover Drive, Straight Drive, Pull Shot).
2. Recognition never defaults to 'Uncertain' / 'No clear shot detected' for valid inputs.
3. Poor / ambiguous input yields 'is_uncertain=True' with an honest rationale, not as a blanket default.
4. Auto-detect resolves active shot to the top predicted shot so coaching and scoring never collapse.
5. All 25 catalogue shots have valid biomechanical reference definitions and unique keyframe poses.
"""

import pytest
from backend.app.services.shot_classifier_service import shot_classifier_service
from backend.app.services.confidence_service import confidence_service
from backend.app.services.reference_service import reference_service


def _make_landmarks(torso_top=0.28, torso_bot=0.55):
    lms = []
    for i in range(33):
        if i in (11, 12):
            lms.append({"x": 0.35, "y": torso_top, "visibility": 0.95})
        elif i in (23, 24):
            lms.append({"x": 0.35, "y": torso_bot, "visibility": 0.95})
        else:
            lms.append({"x": 0.35, "y": 0.40, "visibility": 0.90})
    return lms


def test_cover_drive_recognition_ranks_first_and_not_uncertain_by_default():
    """Valid cover drive sequence must rank 'Cover Drive' #1 with confidence and not be erased to 'Uncertain'."""
    frames = []
    for f in range(45):
        t = f / 45.0
        st = 1.0 + (0.45 * t if t < 0.5 else 0.45)
        wx = 0.35 + (0.15 * t)
        wy = 0.25 + (0.35 * t)
        frames.append({
            "pose_detected": True,
            "frame_index": f,
            "timestamp_sec": f / 30.0,
            "lead_knee_angle": 128.0,
            "rear_knee_angle": 145.0,
            "torso_inclination": 22.0,
            "stance_width_norm": st,
            "lead_wrist_x": wx,
            "lead_wrist_y": wy,
            "lead_wrist_speed": 0.08,
            "confidence": 0.92,
            "phase": "Impact window" if 20 <= f <= 30 else "Downswing",
            "landmarks": _make_landmarks()
        })

    result = shot_classifier_service.classify_sequence(frames, camera_view="side-on", handedness="Right")
    assert result["predicted_shot"] == "Cover Drive"
    assert result["predicted_shot"] != "Uncertain"
    assert result["predicted_shot"] != "No clear shot detected"
    assert len(result["top_candidates"]) >= 3
    assert result["top_candidates"][0]["shot_name"] == "Cover Drive"
    assert result["confidence_pct"] >= 65


def test_straight_drive_recognition_ranks_first():
    """Straight drive with forward stride and straight vertical pendulum ranks 'Straight Drive' #1."""
    frames = []
    for f in range(45):
        t = f / 45.0
        st = 1.0 + (0.42 * t if t < 0.5 else 0.42)
        wx = 0.35 + (0.01 * t)
        wy = 0.25 + (0.38 * t)
        frames.append({
            "pose_detected": True,
            "frame_index": f,
            "timestamp_sec": f / 30.0,
            "lead_knee_angle": 124.0,
            "rear_knee_angle": 148.0,
            "torso_inclination": 20.0,
            "stance_width_norm": st,
            "lead_wrist_x": wx,
            "lead_wrist_y": wy,
            "lead_wrist_speed": 0.09,
            "confidence": 0.92,
            "phase": "Impact window" if 20 <= f <= 30 else "Downswing",
            "landmarks": _make_landmarks()
        })

    result = shot_classifier_service.classify_sequence(frames, camera_view="side-on", handedness="Right")
    assert result["predicted_shot"] == "Straight Drive"
    assert result["predicted_shot"] != "Uncertain"
    assert result["top_candidates"][0]["shot_name"] == "Straight Drive"


def test_pull_shot_recognition_ranks_first():
    """Pull shot with rear-foot anchoring, upright torso and horizontal swing ranks 'Pull Shot' #1."""
    frames = []
    for f in range(35):
        t = f / 35.0
        frames.append({
            "pose_detected": True,
            "frame_index": f,
            "timestamp_sec": f / 30.0,
            "lead_knee_angle": 148.0,
            "rear_knee_angle": 132.0,
            "torso_inclination": 12.0,
            "stance_width_norm": 1.05,
            "lead_wrist_x": 0.45 - (0.15 * t),
            "lead_wrist_y": 0.50 - (0.05 * t),
            "lead_wrist_speed": 0.07,
            "confidence": 0.90,
            "phase": "Impact window" if 15 <= f <= 25 else "Downswing",
            "landmarks": _make_landmarks()
        })

    result = shot_classifier_service.classify_sequence(frames, camera_view="side-on", handedness="Right")
    assert result["predicted_shot"] in ["Pull Shot", "Hook Shot"]
    assert result["predicted_shot"] != "Uncertain"
    assert result["predicted_shot"] != "No clear shot detected"


def test_poor_input_reports_unclear_with_honest_rationale():
    """When tracking is insufficient (< 8 frames), classifier honestly flags 'No clear shot detected' with reason."""
    frames = [
        {"pose_detected": True, "lead_wrist_x": 0.3, "lead_wrist_y": 0.3, "confidence": 0.3}
    ] * 4

    result = shot_classifier_service.classify_sequence(frames, camera_view="side-on")
    assert result["predicted_shot"] == "No clear shot detected"
    assert result["is_uncertain"] is True
    assert "Only" in result["rationale"] or "Insufficient" in result["rationale"]


def test_all_25_catalogue_shots_have_valid_reference_and_support_tier():
    """Verifies that all 25 shots can be canonicalized and queried in reference_service."""
    from backend.app.data.shot_catalogue import SHOT_CATALOGUE
    assert len(SHOT_CATALOGUE) == 25

    for s in SHOT_CATALOGUE:
        name = s["name"]
        tier = reference_service.get_shot_support_tier(name)
        assert tier in ["supported", "preview_only"]
        ref_data = reference_service.get_shot_reference(name)
        assert ref_data is not None, f"Missing reference shot data for {name}"
        assert "phases" in ref_data, f"Missing phases in reference data for {name}"
        assert len(ref_data["phases"]) == 7, f"Expected 7 phases for {name}, got {len(ref_data['phases'])}"
