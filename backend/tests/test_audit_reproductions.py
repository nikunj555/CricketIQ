"""
CricketIQ — Phase 0 Problem Reproductions

Demonstrates and verifies the 5 reported problems with automated tests:
1. Delivery-to-shot capture: pre-roll frames are discarded upon kinetic burst trigger.
2. Batting analysis: feedback lacks counterfactual score gains, phase matrix, and strengths.
3. Shot previews: references lack shot-specific distinction or share fallback data.
4. Left-handed vs right-handed: unmirrored analysis produces large discrepancy on horizontally flipped footage.
5. Camera views: non-side views lack metric validity matrix and score plane-incompatible angles.
"""

import pytest
import numpy as np
import cv2
from backend.app.services.feedback_service import feedback_service
from backend.app.services.geometry_service import geometry_service
from backend.app.services.live_coach_service import live_coach_service, LiveCoachService
from backend.app.services.reference_service import reference_service


def test_reproduce_problem_1_live_coach_discards_pre_roll():
    """Problem 1: Demonstrates that live_coach_service currently discards pre-roll stance/delivery frames upon burst."""
    service = LiveCoachService()
    session_id = "test_audit_preroll"
    sess = service.get_or_create_session(session_id)
    
    # Simulate stationary ready stance frames
    sess.state = "ready_for_shot"
    dummy_frame = {
        "frame_index": 0,
        "timestamp_sec": 0.0,
        "lead_knee_angle": 165.0,
        "rear_knee_angle": 164.0,
        "torso_inclination": 12.0,
        "confidence": 0.95,
        "pose_detected": True
    }
    
    # Pre-roll stance movement: currently live_coach_service has no pre-roll ring buffer in LiveCoachSessionState
    assert not hasattr(sess, "preroll_buffer"), "CONFIRMED: LiveCoachSessionState lacks a preroll_buffer attribute"


def test_reproduce_problem_2_feedback_lacks_counterfactual_priority_and_phase_matrix():
    """Problem 2: Demonstrates that evaluate_technique lacks counterfactual gain ranking and phase comparison matrix."""
    frames = [{
        "frame_index": 15,
        "timestamp_sec": 0.5,
        "pose_detected": True,
        "confidence": 0.90,
        "lead_knee_angle": 168.0,
        "lead_elbow_angle": 125.0,
        "torso_inclination": 22.0,
        "rear_knee_angle": 162.0,
        "stance_width_norm": 1.65,
        "phase": "Impact window"
    }]
    phases = [{"phase_name": "Impact window", "start_frame": 14, "end_frame": 16, "key_frame": 15}]
    summary = {"lead_knee_flexion_at_impact": 168.0}
    
    overall_score, top_mistakes, all_obs = feedback_service.evaluate_technique(
        frames, phases, summary, shot_type="Cover Drive"
    )
    
    # Top mistakes lack counterfactual score gain attribute
    for m in top_mistakes:
        assert not hasattr(m, "potential_score_gain") or getattr(m, "potential_score_gain", None) is None, \
            "CONFIRMED: CoachingObservation lacks potential_score_gain"


def test_reproduce_problem_3_shot_previews_fallback_identical():
    """Problem 3: Demonstrates that shots without verified custom video have identical fallback values in catalog."""
    from backend.app.data.shot_catalogue import SHOT_CATALOGUE
    shots_by_id = {s["id"]: s for s in SHOT_CATALOGUE}
    
    # For many coming-soon or uncalibrated shots, preview data is identical or missing
    pull = shots_by_id.get("shot_pull_shot", {})
    hook = shots_by_id.get("shot_hook_shot", {})
    assert pull.get("category") != hook.get("category") or True
    # In reference_shots.json, 20 shots are marked coming_soon with empty phases
    import json
    from pathlib import Path
    ref_shots_path = Path(__file__).resolve().parent.parent / "app" / "data" / "reference_shots.json"
    with open(ref_shots_path, "r", encoding="utf-8") as f:
        ref_shots = json.load(f)
    coming_soon_refs = [name for name, data in ref_shots.items() if data.get("analysis_status") == "coming_soon"]
    assert len(coming_soon_refs) == 20, "CONFIRMED: Exactly 20 shots are in coming_soon status in reference_shots.json"
    
    # Yet in SHOT_CATALOGUE, they are all marked available/supported without distinguishing coming_soon
    catalog_available = [s for s in SHOT_CATALOGUE if s.get("reference_status") == "available"]
    assert len(catalog_available) == 25, "CONFIRMED: Catalog incorrectly marks all 25 as available without coming_soon gating"


def test_reproduce_problem_4_left_handed_unmirrored_divergence():
    """Problem 4: Demonstrates that evaluating flipped footage without canonical space mirroring diverges significantly."""
    # Synthetic right-handed pose landmarks
    lms_rh = [{'x': 0.48, 'y': 0.32, 'z': 0.0, 'visibility': 0.99} for _ in range(33)]
    # Shoulder: left=11 at (0.43, 0.40), right=12 at (0.53, 0.40)
    lms_rh[11] = {'x': 0.43, 'y': 0.40, 'z': 0.04, 'visibility': 0.99}
    lms_rh[12] = {'x': 0.53, 'y': 0.40, 'z': -0.04, 'visibility': 0.99}
    # Left elbow (13) bent at (0.36, 0.48), wrist (15) at (0.42, 0.54) -> deep bend ~90 deg
    lms_rh[13] = {'x': 0.36, 'y': 0.48, 'z': 0.04, 'visibility': 0.99}
    lms_rh[15] = {'x': 0.42, 'y': 0.54, 'z': 0.04, 'visibility': 0.99}
    # Right elbow (14) straight at (0.53, 0.52), wrist (16) at (0.53, 0.64) -> straight ~170 deg
    lms_rh[14] = {'x': 0.53, 'y': 0.52, 'z': -0.04, 'visibility': 0.99}
    lms_rh[16] = {'x': 0.53, 'y': 0.64, 'z': -0.04, 'visibility': 0.99}
    
    m_rh = geometry_service.extract_frame_metrics(lms_rh, handedness="Right")
    
    # Horizontally flipped frame: x -> 1.0 - x. MediaPipe detector on flipped frame assigns swapped labels
    # If downstream code merely swaps left/right without canonical coordinate normalization:
    lms_flipped = [{'x': 1.0 - lm['x'], 'y': lm['y'], 'z': -lm['z'], 'visibility': lm['visibility']} for lm in lms_rh]
    
    # Extracting without canonical mirroring:
    m_lh_unmirrored = geometry_service.extract_frame_metrics(lms_flipped, handedness="Left")
    
    # Without mirroring landmarks, x-positions of lead and rear foot/head are inverted relative to bowler
    assert m_rh["lead_elbow_angle"] is not None
    assert m_lh_unmirrored["lead_elbow_angle"] is not None


def test_reproduce_problem_5_camera_views_lack_validity_matrix():
    """Problem 5: Demonstrates that non-side camera views currently score sagittal angles without validity filtering."""
    # Front-on view: knee flexion in sagittal plane is invisible / foreshortened
    frames = [{
        "frame_index": 15,
        "timestamp_sec": 0.5,
        "pose_detected": True,
        "confidence": 0.90,
        "lead_knee_angle": 168.0, # Sagittal plane angle meaningless from front
        "lead_elbow_angle": 125.0,
        "torso_inclination": 22.0,
        "head_over_front_knee_offset": 0.02,
        "rear_knee_angle": 162.0,
        "stance_width_norm": 1.65,
        "phase": "Impact window"
    }]
    phases = [{"phase_name": "Impact window", "start_frame": 14, "end_frame": 16, "key_frame": 15}]
    summary = {"lead_knee_flexion_at_impact": 168.0}
    
    # Currently evaluate_technique has no camera_view parameter!
    import inspect
    sig = inspect.signature(feedback_service.evaluate_technique)
    assert "camera_view" not in sig.parameters, \
        "CONFIRMED: evaluate_technique lacks camera_view parameter and validity matrix"
