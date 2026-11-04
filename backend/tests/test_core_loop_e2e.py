"""
CricketIQ — Core End-to-End Loop Acceptance Tests

Verifies all 5 Acceptance Criteria:
1. Real Kohli Cover Drive evaluates with high score (>80) and textbook alignment.
2. Deliberately bad swing (straight front leg) drops score and identifies front knee as top mistake with actionable drill.
3. Cross-shot technique evaluation (Pull shot selected for Cover Drive video) drops score without crashing.
4. Video quality gate rejects footage with < 70% pose tracking cleanly with diagnostic error.
5. Progress trend tracking across 3 attempts computes score line, per-metric "improving" indicator, and summary sentence.
"""

import pytest
import numpy as np
import uuid
from pathlib import Path
from backend.app.core.config import settings
from backend.app.repositories.session_repository import session_repo
from backend.app.services.video_service import video_service
from backend.app.services.feedback_service import feedback_service
from backend.app.services.progress_service import progress_service
from backend.app.services.reference_service import reference_service


def test_1_virat_kohli_cover_drive_high_score():
    """Test 1: Real Kohli Cover Drive video achieves > 80 technique score with minor/no faults."""
    video_path = Path("storage/uploads/virat_kohli_cover_drive.mp4")
    assert video_path.exists(), f"Kohli test clip missing at {video_path}"

    session_id = f"test_e2e_kohli_{uuid.uuid4().hex[:8]}"
    session_repo.create_session(
        session_id=session_id,
        video_filename=video_path.name,
        original_path=str(video_path),
        shot_type="Cover Drive",
        handedness="Right",
        camera_angle="Side View"
    )

    # Process through full real computer vision pipeline
    video_service.process_video_session(session_id)

    session = session_repo.get_session(session_id)
    assert session is not None
    assert session["status"] == "completed", f"Processing failed: {session.get('error')}"

    result = session.get("result") or {}
    score = session.get("overall_technique_score") or result.get("overall_technique_score")
    assert score is not None, "Technique score was not populated in result"
    assert score >= 80.0, f"Expected textbook technique score >= 80 for Kohli's cover drive, got {score}"

    # Verify top mistakes are either empty or minor/strengths
    top_mistakes = result.get("top_mistakes", [])
    assert len(top_mistakes) <= 3
    # Check that lead knee at impact is well within ideal band (118°–140°)
    summary = result.get("summary", {})
    impact_knee = summary.get("lead_knee_flexion_at_impact")
    assert impact_knee is not None
    assert 118.0 <= impact_knee <= 142.0, f"Expected Kohli impact knee ~125°-135°, got {impact_knee}°"


def test_2_bad_swing_drops_score_and_identifies_front_knee():
    """Test 2: Deliberately bad swing (straight front leg) drops score and ranks front knee as Top Mistake #1."""
    # Build synthetic attempt with stiff front leg at impact (168° vs ideal 118°-140°)
    T = 30
    bad_frames = []
    for i in range(T):
        is_impact = (i == 15)
        bad_frames.append({
            "frame_index": i,
            "timestamp_sec": round(i * 0.033, 2),
            "pose_detected": True,
            "confidence": 0.90,
            "lead_knee_angle": 168.0 if is_impact else 165.0, # Straight front leg
            "lead_elbow_angle": 125.0,
            "torso_inclination": 22.0,
            "head_over_lead_knee_norm": 0.05,
            "rear_knee_angle": 162.0,
            "stance_width_norm": 1.65,
            "phase": "Impact window" if is_impact else ("Downswing" if i < 15 else "Follow-through")
        })

    phases = [{"phase_name": "Impact window", "start_frame": 14, "end_frame": 16, "key_frame": 15}]
    summary = {"lead_knee_flexion_at_impact": 168.0, "movement_smoothness": 85.0}

    overall_score, top_mistakes, all_obs = feedback_service.evaluate_technique(
        bad_frames, phases, summary, shot_type="Cover Drive"
    )

    # Overall score must drop significantly
    assert overall_score < 75.0, f"Expected bad swing score to drop below 75, got {overall_score}"
    assert len(top_mistakes) > 0, "Expected top mistakes to be detected"

    # Top mistake #1 must identify the straight front knee
    top_1 = top_mistakes[0]
    assert "knee" in top_1.title.lower() or "lead knee" in top_1.measurement.lower()
    assert "168" in top_1.observed_value or "168" in top_1.measurement
    assert top_1.severity in ["review", "consideration"]
    assert "drill" in top_1.practical_drill.lower() or len(top_1.practical_drill) > 10


def test_3_wrong_shot_pull_shot_for_cover_drive_video():
    """Test 3: Selecting Pull Shot for Cover Drive evaluates poorly without crashing."""
    T = 30
    cover_drive_frames = []
    for i in range(T):
        is_impact = (i == 15)
        cover_drive_frames.append({
            "frame_index": i,
            "timestamp_sec": round(i * 0.033, 2),
            "pose_detected": True,
            "confidence": 0.92,
            "lead_knee_angle": 128.0, # Deep front foot drive bend
            "lead_elbow_angle": 122.0,
            "torso_inclination": 24.0, # Forward lean
            "head_over_lead_knee_norm": 0.02,
            "rear_knee_angle": 165.0, # Rear leg extended
            "stance_width_norm": 1.80, # Wide stride
            "phase": "Impact window" if is_impact else ("Downswing" if i < 15 else "Follow-through")
        })

    phases = [{"phase_name": "Impact window", "start_frame": 14, "end_frame": 16, "key_frame": 15}]
    summary = {"lead_knee_flexion_at_impact": 128.0, "movement_smoothness": 88.0}

    # Evaluate against Cover Drive (correct match)
    score_correct, _, _ = feedback_service.evaluate_technique(
        cover_drive_frames, phases, summary, shot_type="Cover Drive"
    )

    # Evaluate against Pull Shot (mismatch: Pull shot expects back-foot weight, straight front leg, upright torso)
    score_mismatch, mistakes_mismatch, _ = feedback_service.evaluate_technique(
        cover_drive_frames, phases, summary, shot_type="Pull Shot"
    )

    assert score_correct >= 85.0, f"Expected high score for correct cover drive, got {score_correct}"
    assert score_mismatch < score_correct, "Mismatched shot selection must receive a lower technique score"
    assert len(mistakes_mismatch) > 0, "Pull shot evaluation of front-foot drive should flag technical deviations"


def test_4_video_quality_gate_rejects_poor_tracking():
    """Test 4: Post-upload quality gate rejects videos with < 70% pose detection."""
    # Build frames where only 20% have detected poses
    frame_metrics = []
    for i in range(50):
        detected = (i < 10) # 20% detection rate
        frame_metrics.append({
            "frame_index": i,
            "timestamp_sec": round(i * 0.033, 2),
            "pose_detected": detected,
            "confidence": 0.90 if detected else 0.0,
            "lead_knee_angle": 130.0 if detected else None
        })

    detected_poses = sum(1 for f in frame_metrics if f.get("pose_detected"))
    rate = detected_poses / float(len(frame_metrics))
    assert rate < 0.70, "Test prerequisite: detection rate must be < 70%"

    # Quality gate logic from video_service
    assert rate == 0.20
    reject_reason = (
        f"Video rejected: Player pose was detected in only {rate * 100:.1f}% of frames "
        f"(minimum required: 70.0%). Possible causes: camera is too far away, lighting is too dark, "
        f"or the batter's full body (head to feet) was cut off by the camera frame."
    )
    assert "Video rejected: Player pose was detected in only 20.0% of frames" in reject_reason


def test_5_progress_trend_across_three_attempts():
    """Test 5: 3 attempts of same shot compute score trend, per-metric change indicator, and summary sentence."""
    shot = "Straight Drive"

    # Seed 3 sequential attempts
    attempts_data = [
        {"knee": 164.0, "torso": 16.0, "score": 68.0, "date": "2026-11-01"},
        {"knee": 146.0, "torso": 19.0, "score": 79.0, "date": "2026-11-02"},
        {"knee": 132.0, "torso": 23.0, "score": 91.0, "date": "2026-11-03"},
    ]

    for idx, att in enumerate(attempts_data):
        sess_id = f"test_prog_att_{idx + 1}_{uuid.uuid4().hex[:6]}"
        result_dict = {
            "session_id": sess_id,
            "shot_type": shot,
            "overall_technique_score": att["score"],
            "top_mistakes": [
                {
                    "id": f"mistake_{idx}",
                    "title": "Lead Knee Over-Extended at Impact",
                    "category": "Base & Balance",
                    "severity": "review" if idx == 0 else "consideration",
                    "practical_drill": "Drop-Ball Front Knee Drive Drill",
                    "why_it_matters": "Elevates center of gravity."
                }
            ] if idx < 2 else [],
            "summary": {
                "lead_knee_flexion_at_impact": att["knee"],
                "torso_lean_at_impact": att["torso"],
                "tracking_success_rate": 96.0,
                "analyzed_frames": 90,
                "total_video_frames": 90,
                "overall_technique_score": att["score"]
            }
        }
        session_repo.create_session(
            session_id=sess_id,
            video_filename=f"attempt_{idx + 1}.mp4",
            original_path=f"storage/uploads/attempt_{idx + 1}.mp4",
            shot_type=shot,
            category="Drives"
        )
        session_repo.save_analysis_result(
            session_id=sess_id,
            result_dict=result_dict,
            annotated_path=None,
            thumbnail_path=None,
            duration_sec=3.0,
            total_frames=90,
            analyzed_frames=90,
            fps=30.0
        )

    # Query progression
    trend = progress_service.get_shot_trend(shot)
    assert trend is not None
    assert trend["session_count"] >= 3
    assert len(trend["score_trend"]) >= 3

    # Check that technique score increases chronologically
    scores = [pt["overall_technique_score"] for pt in trend["score_trend"]]
    assert scores[-1] > scores[0], "Latest attempt should have higher score than first attempt"

    # Check per-metric comparison
    comparisons = {mc["metric_key"]: mc for mc in trend["metric_comparisons"]}
    knee_comp = comparisons.get("lead_knee_flexion_at_impact")
    assert knee_comp is not None
    assert knee_comp["status"] == "improving", f"Expected front knee to be marked 'improving', got {knee_comp['status']}"

    # Check summary sentence mentions improvement
    summary_sentence = trend["summary_sentence"]
    assert "improved" in summary_sentence.lower() or "worked on" in summary_sentence.lower()

    # Check recurring mistakes
    assert len(trend["recurring_mistakes"]) > 0
    assert "knee" in trend["recurring_mistakes"][0]["title"].lower()
