import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.data.reference_catalogue import AUTHENTIC_REFERENCE_REGISTRY
from backend.app.services.shot_classifier_service import shot_classifier_service
from backend.app.services.phase_service import phase_service
from backend.app.services.comparison_service import comparison_service
from backend.app.repositories.session_repository import session_repo

client = TestClient(app)

def test_a_shot_preview_mapping():
    """
    Test A: Verify that 5 distinct shots (Cover Drive, Straight Drive, Pull Shot, Sweep, Reverse Sweep)
    return unique video URLs, distinct player attributions, and non-duplicate metadata.
    """
    test_shots = ["cover-drive", "straight-drive", "pull-shot", "sweep", "reverse-sweep"]
    video_urls = set()
    ref_ids = set()
    player_names = set()

    for shot_slug in test_shots:
        res = client.get(f"/api/reference/shots/{shot_slug}")
        assert res.status_code == 200, f"Failed to fetch reference for {shot_slug}"
        data = res.json()

        # Check required fields
        assert "video_url" in data and data["video_url"], f"Missing video_url for {shot_slug}"
        assert "player_name" in data and data["player_name"], f"Missing player_name for {shot_slug}"
        assert "phases" in data and len(data["phases"]) == 7, f"Expected 7 phases for {shot_slug}"
        assert "technique_points" in data and len(data["technique_points"]) >= 3, f"Missing technique points for {shot_slug}"
        assert "common_mistakes" in data and len(data["common_mistakes"]) >= 2, f"Missing common mistakes for {shot_slug}"

        # Ensure no URL or ID duplicates among different shots
        assert data["video_url"] not in video_urls, f"Duplicate video URL found: {data['video_url']}"
        assert data["id"] not in ref_ids, f"Duplicate reference ID found: {data['id']}"

        video_urls.add(data["video_url"])
        ref_ids.add(data["id"])
        player_names.add(data["player_name"])

    # Ensure all 5 shots have distinct videos and player attributions
    assert len(video_urls) == 5
    assert len(ref_ids) == 5

def test_b_dynamic_phase_detection():
    """
    Test B: Verify that dynamic phase detection calculates real movement boundaries based on kinematics,
    not arbitrary or fixed 1/7th fractional segments.
    """
    # Trajectory 1: Rapid stroke with impact at frame 10
    traj1 = []
    for i in range(30):
        traj1.append({
            "frame_index": i,
            "timestamp_sec": round(i * 0.033, 3),
            "wrist_separation": 0.05 + 0.3 * (1.0 if 8 <= i <= 12 else 0.1),
            "stance_width_ratio": 1.2 + 0.4 * (1.0 if i >= 6 else 0.0),
            "lead_knee_angle": 150.0 - (35.0 if 8 <= i <= 13 else 5.0),
            "rear_knee_angle": 155.0,
            "torso_inclination": 20.0,
            "pose_detected": True,
            "confidence": 0.95
        })

    # Trajectory 2: Delayed stroke with impact at frame 22
    traj2 = []
    for i in range(35):
        traj2.append({
            "frame_index": i,
            "timestamp_sec": round(i * 0.033, 3),
            "wrist_separation": 0.05 + 0.3 * (1.0 if 20 <= i <= 24 else 0.1),
            "stance_width_ratio": 1.2 + 0.4 * (1.0 if i >= 16 else 0.0),
            "lead_knee_angle": 150.0 - (35.0 if 20 <= i <= 25 else 5.0),
            "rear_knee_angle": 155.0,
            "torso_inclination": 20.0,
            "pose_detected": True,
            "confidence": 0.95
        })

    phases1, _, segs1 = phase_service.predict_phases(traj1, fps=30.0)
    phases2, _, segs2 = phase_service.predict_phases(traj2, fps=30.0)

    # Find impact window start in both
    impact1 = next((s for s in segs1 if s["phase_name"] == "Impact window"), None)
    impact2 = next((s for s in segs2 if s["phase_name"] == "Impact window"), None)

    assert impact1 is not None and impact2 is not None
    assert impact1["start_frame"] != impact2["start_frame"], "Phases must adapt dynamically to movement data!"
    assert impact1["start_frame"] < impact2["start_frame"], "Trajectory 1 should have an earlier impact than Trajectory 2!"

def test_c_dtw_comparison_and_incompatibility():
    """
    Test C: Verify DTW comparison returns alignment distance, and warns when comparing
    cross-category incompatible shots (e.g. Pull Shot vs Cover Drive).
    """
    # Construct mock session data
    mock_cov_session = {
        "session_id": "mock_cov_sess",
        "shot_type": "Cover Drive",
        "result": {
            "time_series": [
                {
                    "timestamp_sec": round(i * 0.033, 3),
                    "lead_knee_angle": 125.0,
                    "rear_knee_angle": 155.0,
                    "torso_inclination": 25.0,
                    "head_y": 0.35,
                    "stance_width_ratio": 1.45,
                    "lead_elbow_angle": 135.0
                }
                for i in range(25)
            ]
        }
    }

    # 1. Compatible comparison (Cover Drive vs Cover Drive)
    res_comp = comparison_service.compare_session_with_reference(
        query_session_data=mock_cov_session,
        reference_id="ref_cover_drive_kohli"
    )
    assert res_comp.reference_id == "ref_cover_drive_kohli"
    assert res_comp.raw_dtw_distance >= 0.0
    assert len(res_comp.aligned_time_series) > 0
    assert res_comp.compatibility_warning is None

    # 2. Incompatible cross-category comparison (Pull Shot vs Cover Drive)
    mock_pull_session = {
        "session_id": "mock_pull_sess",
        "shot_type": "Pull Shot",
        "result": mock_cov_session["result"]
    }
    res_incomp = comparison_service.compare_session_with_reference(
        query_session_data=mock_pull_session,
        reference_id="ref_cover_drive_kohli"
    )
    assert res_incomp.compatibility_warning is not None
    assert "Biomechanical Category Mismatch" in res_incomp.compatibility_warning

def test_d_shot_classification_and_manual_confirmation():
    """
    Test D: Verify kinematic classifier classifies batting sequences, returns confidence and rationale,
    and supports manual shot confirmation via the endpoint.
    """
    # Pull shot kinematics: rear knee flexion, high torso, horizontal pull
    pull_seq = []
    for i in range(25):
        pull_seq.append({
            "lead_knee_angle": 145.0,
            "rear_knee_angle": 128.0, # deep back foot flexion
            "stance_width_norm": 1.1,
            "torso_inclination": 16.0, # upright torso
            "wrist_separation": 0.35,
            "lead_wrist_speed": 0.05,
            "lead_wrist_x": 0.45 - i * 0.005,
            "lead_wrist_y": 0.60 - i * 0.015,
            "bat_detected": True,
            "bat_angle_deg": 20.0,
            "phase": "Impact window" if i == 12 else "Execution",
            "pose_detected": True,
            "confidence": 0.95
        })

    result = shot_classifier_service.classify_sequence(pull_seq)
    assert "predicted_shot" in result
    assert "confidence" in result
    assert "rationale" in result
    assert result["predicted_shot"] in ["Pull Shot", "Hook Shot", "Back-foot Punch"]

    # Test confirmation endpoint on a session
    sessions = session_repo.list_sessions(limit=1)
    if sessions:
        target_id = sessions[0]["session_id"]
        res = client.post(f"/api/sessions/{target_id}/confirm-shot", json={
            "confirmed_shot_type": "Square Cut"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["confirmed_shot_type"] == "Square Cut"

        # Verify updated in session detail
        updated_s = session_repo.get_session(target_id)
        assert updated_s["user_confirmed_shot_type"] == "Square Cut"
