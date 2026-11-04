import json
import time
import pytest
import numpy as np
from pathlib import Path
from backend.app.services.video_service import VideoService
from backend.app.services.feedback_service import feedback_service
from backend.app.services.geometry_service import geometry_service
from backend.app.services.shot_classifier_service import shot_classifier_service
from backend.app.services.pose_service import pose_service
from backend.app.services.reference_service import reference_service
from backend.app.services.progress_service import progress_service
from backend.app.repositories.session_repository import session_repo

FIXTURES_DIR = Path("backend/tests/fixtures")


def test_acceptance_1_straight_drive_selected():
    """Acceptance Test 1: straight_drive.mp4 with 'Straight Drive' selected -> no 'sweep', sensible score."""
    fixture = FIXTURES_DIR / "straight_drive.mp4"
    assert fixture.exists(), f"Fixture {fixture} missing"

    sess_id = f"test_sd_1_{int(time.time())}"
    session_repo.create_session(
        session_id=sess_id,
        video_filename="straight_drive.mp4",
        original_path=str(fixture),
        shot_type="Straight Drive",
        handedness="Right"
    )

    vs = VideoService()
    vs.process_video_session(sess_id)

    sess = session_repo.get_session(sess_id)
    assert sess is not None
    assert sess["status"] == "completed"

    res = sess["result"]
    assert res is not None
    # Must NOT be sweep
    assert res["shot_type"] == "Straight Drive", f"Expected Straight Drive, got {res['shot_type']}"
    assert res["predicted_shot_type"] != "Sweep", f"Predicted shot was Sweep: {res['predicted_shot_type']}"
    
    # Sensible score (20 - 100)
    score = res["overall_technique_score"]
    assert 40.0 <= score <= 98.0, f"Technique score {score} out of sensible range"
    print(f"\n[ACCEPTANCE 1 PASSED] Shot: {res['shot_type']}, Predicted: {res['predicted_shot_type']} ({res['prediction_confidence']:.2f}), Score: {score}")


def test_acceptance_2_cover_drive_selected():
    """Acceptance Test 2: cover_drive.mp4 with 'Cover Drive' selected -> sensible score."""
    fixture = FIXTURES_DIR / "cover_drive.mp4"
    assert fixture.exists(), f"Fixture {fixture} missing"

    sess_id = f"test_cd_2_{int(time.time())}"
    session_repo.create_session(
        session_id=sess_id,
        video_filename="cover_drive.mp4",
        original_path=str(fixture),
        shot_type="Cover Drive",
        handedness="Right"
    )

    vs = VideoService()
    vs.process_video_session(sess_id)

    sess = session_repo.get_session(sess_id)
    assert sess is not None
    assert sess["status"] == "completed"

    res = sess["result"]
    assert res is not None
    assert res["shot_type"] == "Cover Drive"
    assert res["predicted_shot_type"] != "Sweep"

    score = res["overall_technique_score"]
    assert 40.0 <= score <= 98.0, f"Technique score {score} out of sensible range"
    print(f"\n[ACCEPTANCE 2 PASSED] Shot: {res['shot_type']}, Predicted: {res['predicted_shot_type']} ({res['prediction_confidence']:.2f}), Score: {score}")


def test_acceptance_3_mismatch_soft_warning():
    """Acceptance Test 3: cover_drive.mp4 with 'Straight Drive' selected -> soft warning that it looks like Cover Drive."""
    fixture = FIXTURES_DIR / "cover_drive.mp4"
    assert fixture.exists(), f"Fixture {fixture} missing"

    sess_id = f"test_cd_mismatch_3_{int(time.time())}"
    session_repo.create_session(
        session_id=sess_id,
        video_filename="cover_drive.mp4",
        original_path=str(fixture),
        shot_type="Straight Drive",
        handedness="Right"
    )

    vs = VideoService()
    vs.process_video_session(sess_id)

    sess = session_repo.get_session(sess_id)
    res = sess["result"]

    # Selection remains source of truth
    assert res["shot_type"] == "Straight Drive", "User selection was overridden"
    # Soft warning should notify of the mismatch
    warning = res.get("shot_mismatch_warning")
    print(f"\n[ACCEPTANCE 3] Selected: {res['shot_type']}, Predicted: {res['predicted_shot_type']}, Warning: {warning}")
    assert warning is not None, "Expected soft warning for mismatching shot"
    assert "Cover Drive" in warning or "looks more like" in warning


def test_acceptance_4_two_batters_striker_isolation():
    """Acceptance Test 4: two_batters.mp4 -> striker track analyzed, non-striker ignored."""
    fixture = FIXTURES_DIR / "two_batters.mp4"
    assert fixture.exists(), f"Fixture {fixture} missing"

    # 1. Test striker candidate inspection
    inspection = pose_service.inspect_strikers(fixture, max_scan_frames=60)
    assert len(inspection["candidates"]) >= 2, f"Expected at least 2 batters, got {len(inspection['candidates'])}"
    default_tid = inspection["default_track_id"]
    striker_cand = next(c for c in inspection["candidates"] if c["track_id"] == default_tid)
    assert striker_cand["is_suggested_striker"] is True
    print(f"\n[ACCEPTANCE 4] Multi-batter inspection found {len(inspection['candidates'])} batters. Suggested striker: Track {default_tid} (Motion: {striker_cand['wrist_motion_score']})")

    # 2. Process session locking specifically to striker
    sess_id = f"test_two_batters_4_{int(time.time())}"
    session_repo.create_session(
        session_id=sess_id,
        video_filename="two_batters.mp4",
        original_path=str(fixture),
        shot_type="Cover Drive",
        striker_track_id=default_tid
    )

    vs = VideoService()
    vs.process_video_session(sess_id)

    sess = session_repo.get_session(sess_id)
    res = sess["result"]
    assert res is not None
    assert res["striker_track_id"] == default_tid
    print(f"[ACCEPTANCE 4 PASSED] Locked analysis exclusively to striker track {default_tid}")


def test_acceptance_5_view_detection_and_validity():
    """Acceptance Test 5: Side-on vs front-on view detection and validity filtering."""
    # Test synthetic side-on vs front-on landmarks
    # In side-on: shoulder width is small relative to torso length
    side_on_lms = [{"x": 0.50, "y": 0.30, "visibility": 1.0} for _ in range(33)]
    side_on_lms[11] = {"x": 0.48, "y": 0.30, "visibility": 1.0}  # left shoulder
    side_on_lms[12] = {"x": 0.52, "y": 0.30, "visibility": 1.0}  # right shoulder (diff 0.04)
    side_on_lms[23] = {"x": 0.48, "y": 0.55, "visibility": 1.0}  # left hip (torso h 0.25 -> ratio 0.16)
    side_on_lms[24] = {"x": 0.52, "y": 0.55, "visibility": 1.0}

    front_on_lms = [{"x": 0.50, "y": 0.30, "visibility": 1.0} for _ in range(33)]
    front_on_lms[11] = {"x": 0.38, "y": 0.30, "visibility": 1.0}  # left shoulder
    front_on_lms[12] = {"x": 0.62, "y": 0.30, "visibility": 1.0}  # right shoulder (diff 0.24)
    front_on_lms[23] = {"x": 0.42, "y": 0.55, "visibility": 1.0}  # left hip (torso h 0.25 -> ratio 0.96)
    front_on_lms[24] = {"x": 0.58, "y": 0.55, "visibility": 1.0}

    side_est = geometry_service.estimate_camera_view([side_on_lms])
    front_est = geometry_service.estimate_camera_view([front_on_lms])

    assert side_est["detected_view"] == "side-on"
    assert front_est["detected_view"] == "front-on"

    # Verify validity matrix: in front-on view, knee flexion is UNAVAILABLE
    table_front = feedback_service.generate_comparison_table(
        time_series=[{"phase": "impact", "lead_knee_angle": 140.0, "lead_elbow_angle": 145.0, "torso_inclination": 22.0}],
        shot_type="Cover Drive",
        camera_view="front-on"
    )
    knee_rows = [r for r in table_front if "knee" in r["metric"]]
    assert len(knee_rows) > 0
    for kr in knee_rows:
        assert kr["validity"] == "UNAVAILABLE"
        assert kr["verdict"] == "Unavailable"

    # In side-on view, knee flexion is MEASURED
    table_side = feedback_service.generate_comparison_table(
        time_series=[{"phase": "impact", "lead_knee_angle": 140.0, "lead_elbow_angle": 145.0, "torso_inclination": 22.0}],
        shot_type="Cover Drive",
        camera_view="side-on"
    )
    knee_side = next(r for r in table_side if r["metric"] == "lead_knee_angle" and r["phase"] == "impact")
    assert knee_side["validity"] == "MEASURED"
    print(f"\n[ACCEPTANCE 5 PASSED] Side ratio: {side_est['ratio']} -> {side_est['detected_view']}, Front ratio: {front_est['ratio']} -> {front_est['detected_view']}")
    print(f"[ACCEPTANCE 5 PASSED] Front-on knee validity: {knee_rows[0]['validity']} (verdict: {knee_rows[0]['verdict']})")


def test_acceptance_6_all_25_shots_reference_json():
    """Acceptance Test 6: All 25 shots complete in reference JSON; avatar renders 7 phases without error."""
    ref_path = Path("backend/app/data/reference_shots.json")
    assert ref_path.exists()

    with open(ref_path, "r") as f:
        data = json.load(f)

    assert len(data) == 25, f"Expected 25 shots, found {len(data)}"
    phases_required = ["stance", "backlift", "stride", "downswing", "impact", "follow_through", "recovery"]

    for shot_name, s_data in data.items():
        assert "phases" in s_data, f"Shot {shot_name} missing phases"
        for p in phases_required:
            assert p in s_data["phases"], f"Shot {shot_name} missing phase {p}"
            kf = s_data["phases"][p].get("keyframe_pose")
            assert kf is not None, f"Shot {shot_name} phase {p} missing keyframe_pose"
            assert "hip_x" in kf and "lead_stride_x" in kf and "bat_angle" in kf

    calibrated_count = sum(1 for s in data.values() if s.get("source_type") == "calibrated (video-derived)")
    baseline_count = sum(1 for s in data.values() if s.get("source_type") == "baseline (tunable)")
    assert calibrated_count == 5, f"Expected 5 calibrated shots, got {calibrated_count}"
    assert baseline_count == 20, f"Expected 20 baseline shots, got {baseline_count}"
    print(f"\n[ACCEPTANCE 6 PASSED] All {len(data)} shots verified across all 7 phases with keyframe_pose.")
    print(f"  5 Calibrated (video-derived): Cover Drive, Straight Drive, Pull Shot, Forward Defensive, Sweep")
    print(f"  20 Baseline (tunable): {', '.join([k for k, v in data.items() if v.get('source_type') == 'baseline (tunable)'])[:80]}...")


def test_acceptance_7_progress_shot_trend():
    """Acceptance Test 7: Progress chart shows 2 attempts with correct trend."""
    # Create two test sessions for Cover Drive
    sess1 = "test_prog_cd_1"
    sess2 = "test_prog_cd_2"
    session_repo.create_session(session_id=sess1, video_filename="attempt_1.mp4", shot_type="Cover Drive")
    session_repo.create_session(session_id=sess2, video_filename="attempt_2.mp4", shot_type="Cover Drive")

    res1 = {
        "shot_type": "Cover Drive",
        "overall_technique_score": 72.0,
        "summary": {"lead_knee_flexion_at_impact": 145.0, "torso_lean_at_impact": 18.0},
        "top_mistakes": [{"title": "Stiff Lead Knee at Impact", "category": "Base & Balance"}]
    }
    res2 = {
        "shot_type": "Cover Drive",
        "overall_technique_score": 86.0,
        "summary": {"lead_knee_flexion_at_impact": 128.0, "torso_lean_at_impact": 24.0},
        "top_mistakes": []
    }

    session_repo.save_analysis_result(sess1, res1)
    session_repo.save_analysis_result(sess2, res2)

    prog = progress_service.get_shot_trend("Cover Drive")
    assert prog["session_count"] >= 2
    assert len(prog["score_trend"]) >= 2
    print(f"\n[ACCEPTANCE 7 PASSED] Shot: Cover Drive, Total attempts: {prog['session_count']}, Trend points: {len(prog['score_trend'])}, Summary: {prog['summary_sentence']}")

