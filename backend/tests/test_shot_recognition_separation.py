"""
Tests for Shot Recognition Separation:
  1. Straight Drive vs Cover Drive must not be confused.
  2. Pull Shot vs Hook Shot must not be confused.
  3. Weak evidence / low tracking returns unrecognised/uncertain without default floor.
  4. Top 3 candidate shots are always returned with calibrated confidences.
"""

import pytest
from pathlib import Path
from backend.app.services.video_service import VideoService
from backend.app.services.shot_classifier_service import shot_classifier_service
from backend.app.repositories.session_repository import session_repo


def test_straight_drive_and_cover_drive_separation():
    """Ensure Cover Drive and Straight Drive produce distinct, separated classifications."""
    vs = VideoService()

    # 1. Test Cover Drive
    cd_path = Path("backend/tests/fixtures/user_cover_drive.mp4")
    assert cd_path.exists(), "user_cover_drive.mp4 fixture missing"
    sid_cd = "test_sep_cover_drive"
    session_repo.create_session(sid_cd, video_filename="user_cover_drive.mp4", original_path=str(cd_path), shot_type="Cover Drive")
    vs.process_video_session(sid_cd)
    sess_cd = session_repo.get_session(sid_cd)
    res_cd = sess_cd.get("result", {})
    sc_cd = res_cd.get("shot_classification", {})

    assert sc_cd.get("predicted_shot") == "Cover Drive", f"Expected Cover Drive, got {sc_cd.get('predicted_shot')}"
    assert sc_cd.get("confidence_pct", 0) >= 65, "Expected confident prediction for benchmark cover drive"

    # 2. Test Straight Drive
    sd_path = Path("backend/tests/fixtures/user_straight_drive.mp4")
    assert sd_path.exists(), "user_straight_drive.mp4 fixture missing"
    sid_sd = "test_sep_straight_drive"
    session_repo.create_session(sid_sd, video_filename="user_straight_drive.mp4", original_path=str(sd_path), shot_type="Straight Drive")
    vs.process_video_session(sid_sd)
    sess_sd = session_repo.get_session(sid_sd)
    res_sd = sess_sd.get("result", {})
    sc_sd = res_sd.get("shot_classification", {})

    assert sc_sd.get("predicted_shot") == "Straight Drive", f"Expected Straight Drive, got {sc_sd.get('predicted_shot')}"
    assert sc_sd.get("confidence_pct", 0) >= 65, "Expected confident prediction for benchmark straight drive"

    # 3. Verify separation: top-1 predictions differ
    assert sc_cd.get("predicted_shot") != sc_sd.get("predicted_shot"), "Cover Drive and Straight Drive must not be confused!"


def test_pull_shot_and_hook_shot_separation():
    """Ensure Pull Shot and Hook Shot are properly distinguished by contact height and cross-bat kinematics."""
    vs = VideoService()

    pull_path = Path("backend/tests/fixtures/pull_shot.mp4")
    assert pull_path.exists(), "pull_shot.mp4 fixture missing"
    sid_pull = "test_sep_pull_shot"
    session_repo.create_session(sid_pull, video_filename="pull_shot.mp4", original_path=str(pull_path), shot_type="Pull Shot")
    vs.process_video_session(sid_pull)
    sess_pull = session_repo.get_session(sid_pull)
    res_pull = sess_pull.get("result", {})
    sc_pull = res_pull.get("shot_classification", {})

    assert sc_pull.get("predicted_shot") == "Pull Shot", f"Expected Pull Shot, got {sc_pull.get('predicted_shot')}"
    
    # Top 3 candidates must contain Hook Shot as secondary cross-bat candidate, but Pull Shot must rank first
    top_candidates = sc_pull.get("top_candidates", [])
    assert len(top_candidates) >= 2
    assert top_candidates[0]["shot_name"] == "Pull Shot"
    candidate_names = [c["shot_name"] for c in top_candidates]
    assert "Hook Shot" in candidate_names, "Hook Shot should be a close cross-bat alternative"


def test_weak_evidence_returns_uncertain_without_40_percent_floor():
    """Clips with insufficient evidence or low tracking rate must return uncertain without a fake 40% floor."""
    # 1. Empty frame sequence
    resp_empty = shot_classifier_service.classify_sequence([])
    assert resp_empty["is_uncertain"] is True
    assert resp_empty["confidence_pct"] <= 35

    # 2. Sequence with only 3 valid frames
    dummy_frames = [{"pose_detected": True, "confidence": 0.3} for _ in range(3)] + [{"pose_detected": False} for _ in range(20)]
    resp_weak = shot_classifier_service.classify_sequence(dummy_frames)
    assert resp_weak["is_uncertain"] is True
    assert resp_weak["confidence_pct"] < 40, "Weak evidence must not have a 40% confidence floor"
    assert "unrecognised" in resp_weak["predicted_shot"].lower() or "no clear" in resp_weak["predicted_shot"].lower()


def test_top_3_candidates_structure():
    """Ensure top 3 candidates are always provided with calibrated scores."""
    sd_path = Path("backend/tests/fixtures/user_straight_drive.mp4")
    sess_sd = session_repo.get_session("test_sep_straight_drive")
    if not sess_sd or not sess_sd.get("result"):
        vs = VideoService()
        session_repo.create_session("test_sep_straight_drive", video_filename="user_straight_drive.mp4", original_path=str(sd_path), shot_type="Straight Drive")
        vs.process_video_session("test_sep_straight_drive")
        sess_sd = session_repo.get_session("test_sep_straight_drive")

    res = sess_sd.get("result", {})
    sc = res.get("shot_classification", {})
    top3 = sc.get("top_candidates", [])

    assert len(top3) == 3, f"Expected exactly 3 candidates in top_candidates, got {len(top3)}"
    assert top3[0]["confidence_pct"] >= top3[1]["confidence_pct"] >= top3[2]["confidence_pct"], "Top candidates must be sorted descending"
    for cand in top3:
        assert "shot_name" in cand
        assert "confidence_pct" in cand
        assert 0 <= cand["confidence_pct"] <= 100
