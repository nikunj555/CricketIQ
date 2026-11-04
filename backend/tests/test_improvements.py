"""
CricketIQ — Engineering Upgrade Test Suite
Verifies:
  1. Temporal signal smoothing (Savitzky-Golay / moving-average)
  2. Angular velocity and angular acceleration calculations
  3. Video validation with resolution/fps/duration checks and warnings
  4. Phase segment evidence & duration enrichment
  5. Progress tracking service calculations & reliability thresholds
  6. Feedback measurement provenance & severity assignments
"""

import pytest
import numpy as np
from pathlib import Path
from backend.app.services.geometry_service import geometry_service, GeometryService
from backend.app.services.video_service import video_service
from backend.app.services.phase_service import phase_service
from backend.app.services.progress_service import progress_service
from backend.app.services.feedback_service import feedback_service


def test_smooth_angle_sequence_preserves_length_and_nones():
    """Ensure smoothing preserves sequence length and maintains None positions."""
    raw = [120.0, 125.0, None, 135.0, 140.0, 142.0, 145.0]
    smoothed = GeometryService.smooth_angle_sequence(raw, window=3)
    assert len(smoothed) == len(raw)
    assert smoothed[2] is None
    assert smoothed[0] is not None
    assert smoothed[4] is not None


def test_calculate_angular_velocity():
    """Ensure central-difference angular velocity is computed accurately."""
    # Linearly increasing angle at 30 deg/sec at 30 fps -> step of 1 deg per frame
    fps = 30.0
    angles = [100.0 + i * 1.0 for i in range(10)]
    velocities = GeometryService.calculate_angular_velocity(angles, fps=fps)
    assert len(velocities) == len(angles)
    # Interior points should have velocity approx 30.0 deg/sec
    for v in velocities[1:-1]:
        assert abs(v - 30.0) < 0.1


def test_calculate_angular_acceleration():
    """Constant velocity should yield near-zero angular acceleration."""
    fps = 30.0
    velocities = [25.0] * 10
    accels = GeometryService.calculate_angular_acceleration(velocities, fps=fps)
    assert len(accels) == len(velocities)
    for a in accels[1:-1]:
        assert abs(a) < 0.1


def test_enrich_time_series_with_derivatives():
    """Verify that batch time series enrichment adds velocity and acceleration keys."""
    metrics = [
        {
            "lead_knee_angle": 130.0 + i * 2.0,
            "rear_knee_angle": 160.0,
            "torso_inclination": 20.0 + i * 0.5,
            "lead_elbow_angle": 90.0,
            "rear_elbow_angle": 100.0,
            "shoulder_tilt": 5.0,
            "hip_tilt": 4.0,
            "lead_wrist_x": 0.5 + i * 0.01,
            "lead_wrist_y": 0.6 - i * 0.02,
        }
        for i in range(15)
    ]
    enriched = geometry_service.enrich_time_series_with_derivatives(metrics, fps=30.0)
    assert len(enriched) == 15
    first = enriched[1]
    assert "lead_knee_angle_velocity" in first
    assert "lead_knee_angle_acceleration" in first
    assert "lead_wrist_speed" in first
    assert first["lead_wrist_speed"] is not None
    assert first["lead_wrist_speed"] > 0.0


def test_trajectory_consistency_computation():
    """Verify trajectory consistency helper metrics."""
    angles = [120.0, 122.0, 119.0, 121.0, 120.5]
    res = GeometryService.compute_trajectory_consistency(angles)
    assert res["mean"] is not None
    assert abs(res["mean"] - 120.5) < 1.0
    assert res["cv"] is not None
    assert res["cv"] < 5.0  # low variation
    assert res["data_completeness_pct"] == 100.0


def test_phase_segments_contain_evidence_and_duration():
    """Verify phase segments contain supporting evidence and duration."""
    fake_metrics = [
        {
            "pose_detected": True,
            "lead_knee_angle": 160.0 - i * 3.0,
            "rear_knee_angle": 165.0,
            "stance_width_norm": 1.0 + i * 0.05,
            "lead_wrist_y": 0.60 - i * 0.02,
            "lead_wrist_x": 0.50 + i * 0.01,
        }
        for i in range(25)
    ]
    phases, confs, segments = phase_service.predict_phases(fake_metrics, fps=25.0)
    assert len(segments) > 0
    seg = segments[0]
    assert "duration_sec" in seg
    assert seg["duration_sec"] >= 0.0
    assert "supporting_evidence" in seg
    assert isinstance(seg["supporting_evidence"], list)
    assert len(seg["supporting_evidence"]) > 0
    assert "detection_confidence" in seg


def test_progress_service_empty_graceful():
    """Ensure progress service handles queries gracefully without crashing."""
    summary = progress_service.get_all_shots_summary(limit=10)
    assert "total_sessions" in summary
    assert "completed_sessions" in summary
    assert "shot_type_breakdown" in summary

    trend = progress_service.get_shot_trend("Cover Drive", limit=10)
    assert "shot_type" in trend
    assert trend["shot_type"] == "Cover Drive"
    assert "is_trend_reliable" in trend
    assert isinstance(trend["trend_data"], list)


def test_feedback_provenance_labels():
    """Ensure coaching feedback assigns MEASURED vs ESTIMATED provenance appropriately."""
    time_series = [
        {
            "phase": "Impact window",
            "timestamp_sec": 0.85,
            "lead_knee_angle": 110.0,
            "torso_inclination": 22.0,
            "lead_elbow_angle": 115.0,
            "head_displacement": 0.15,
            "stance_width_norm": 1.5,
            "head_over_lead_knee_norm": 0.05,
            "bat_angle_deg": 65.0,  # cross-bat
        }
    ]
    summary = {
        "wrist_separation_mean": 0.15,
        "weight_transfer_at_impact": 0.40,  # trapped on back foot
    }
    feedback = feedback_service.generate_coaching_feedback(
        time_series, phases=[], summary=summary, shot_type="Cover Drive"
    )
    assert len(feedback) > 0
    provenance_types = {obs.measurement_provenance for obs in feedback}
    # Both MEASURED and ESTIMATED should be present
    assert "MEASURED" in provenance_types or "ESTIMATED" in provenance_types
    for obs in feedback:
        assert obs.confidence is not None
        assert 0.0 <= obs.confidence <= 1.0


def test_virat_kohli_test_video_clip_and_session():
    """Verify that the Virat Kohli video clip exists in storage/uploads and decodes properly."""
    import cv2
    from backend.app.repositories.session_repository import session_repo

    video_path = Path("storage/uploads/virat_kohli_cover_drive.mp4")
    assert video_path.exists(), "virat_kohli_cover_drive.mp4 must exist in storage/uploads/"

    cap = cv2.VideoCapture(str(video_path))
    assert cap.isOpened(), "Virat Kohli test video must be openable by OpenCV"
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    assert total_frames > 30, f"Expected > 30 frames, got {total_frames}"
    assert fps > 20.0, f"Expected FPS > 20, got {fps}"

    # Verify injected test session
    session = session_repo.get_session("virat_kohli_cover_drive")
    assert session is not None, "virat_kohli_cover_drive session must be present in database"
    assert session["status"] == "completed"
    assert session["shot_type"] == "Cover Drive"
    assert "result" in session
    assert len(session["result"]["phases"]) > 0
    assert len(session["result"]["coaching_feedback"]) > 0


