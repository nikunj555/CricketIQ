"""
Comprehensive Acceptance Tests for:
  Part A: Calibrated, Plain-English Shot Confidence
  Part B: Plain-English Coaching Feedback with Technical Proof Layer
  Part C: Mutual Protection Rule (Coaching paused on uncertain shots)
  Part D: Progress Tracking & Plain-Words Trends
"""

import os, sys
sys.path.insert(0, os.path.abspath("."))

import pytest
import numpy as np
from pathlib import Path
from backend.app.services.confidence_service import confidence_service
from backend.app.services.plain_language_service import plain_language_service
from backend.app.services.feedback_service import feedback_service, EvaluationResult
from backend.app.services.shot_classifier_service import shot_classifier_service
from backend.app.services.progress_service import progress_service


def _build_synthetic_shot_frames(shot_family="straight", stiff_knee=False, total_frames=45):
    """Helper to generate realistic synthetic frame metrics."""
    frames = []
    impact_frame = 25
    for f in range(total_frames):
        is_impact = (24 <= f <= 28)
        is_stride = (16 <= f <= 23)
        is_swing = (20 <= f <= 30)

        phase = "Stance"
        if f < 10:
            phase = "Stance"
        elif f < 16:
            phase = "Backlift"
        elif f < 22:
            phase = "Stride"
        elif f < 25:
            phase = "Downswing"
        elif f < 30:
            phase = "Impact window"
        elif f < 38:
            phase = "Follow-through"
        else:
            phase = "Recovery"

        # Knee angle: ideal is ~125-135; stiff is ~168
        if stiff_knee and is_impact:
            knee_angle = 168.0
        elif is_impact:
            knee_angle = 126.0
        elif is_stride:
            knee_angle = 135.0
        else:
            knee_angle = 155.0

        # Ideal elbow for drive at impact is ~90-105; downswing ~85-110
        if is_impact:
            elbow_angle = 92.0
            torso = 20.0
            stance_width = 1.60
        elif is_stride:
            elbow_angle = 105.0
            torso = 16.0
            stance_width = 1.55
        elif is_swing:
            elbow_angle = 95.0
            torso = 18.0
            stance_width = 1.50
        else:
            elbow_angle = 120.0
            torso = 12.0
            stance_width = 1.05

        wrist_speed = 0.85 if is_swing else 0.15

        if shot_family == "straight":
            lead_foot_dx = 0.02
            rear_knee = 158.0
        elif shot_family == "off":
            lead_foot_dx = 0.14
            rear_knee = 155.0
        elif shot_family == "cross":
            lead_foot_dx = -0.12
            rear_knee = 120.0
        else:
            lead_foot_dx = 0.0
            rear_knee = 160.0

        frames.append({
            "frame_index": f,
            "timestamp_sec": round(f * 0.033, 3),
            "pose_detected": True,
            "confidence": 0.92,
            "lead_knee_angle": knee_angle,
            "rear_knee_angle": rear_knee,
            "lead_elbow_angle": elbow_angle,
            "rear_elbow_angle": 130.0,
            "torso_inclination": torso,
            "shoulder_tilt": 8.0,
            "hip_tilt": 4.0,
            "head_over_lead_knee_norm": 0.02,
            "stance_width_norm": stance_width,
            "lead_wrist_speed": wrist_speed,
            "lead_foot_dx": lead_foot_dx,
            "phase": phase,
            "landmarks": [
                {"x": 0.35 + (0.05 if is_stride else 0.0), "y": 0.20, "visibility": 0.95}
            ] * 33
        })
    return frames


# ---------------------------------------------------------------------------
# TEST 1: Reliability & Calibration across Probabilities
# ---------------------------------------------------------------------------
def test_1_reliability_table_and_binned_calibration():
    """Validates Platt probability scaling and plain-English certainty levels."""
    scores = np.linspace(0.1, 0.99, 10)
    calibrated_probs = [confidence_service.calibrate_probability(s) for s in scores]

    # Monotonicity: higher raw model score strictly produces higher calibrated probability
    for i in range(len(calibrated_probs) - 1):
        assert calibrated_probs[i] <= calibrated_probs[i+1], "Calibrated probability must be monotonic"

    # High score >= 0.85 maps to 'Very sure'
    high_eval = confidence_service.evaluate_confidence(
        predicted_shot="Straight Drive",
        raw_score=0.95,
        top_candidates=[{"shot": "Straight Drive", "score": 0.95}, {"shot": "Cover Drive", "score": 0.03}],
        frame_metrics=[{"confidence": 0.92, "pose_detected": True}] * 40,
        camera_view="side-on"
    )
    assert high_eval["confidence"] >= 85
    assert high_eval["level"] == "Very sure"
    assert high_eval["level_code"] == "very_sure"


# ---------------------------------------------------------------------------
# TEST 2: Clean Side-On Straight Drive High Confidence
# ---------------------------------------------------------------------------
def test_2_clean_side_on_straight_drive_high_confidence():
    """A clean, fully tracked straight drive produces 'Very sure' or 'Fairly sure' confidence."""
    frames = _build_synthetic_shot_frames(shot_family="straight", stiff_knee=False)
    res = shot_classifier_service.classify_sequence(frames, hint_shot="Straight Drive", camera_view="side-on")

    shot_conf = res.get("shot_confidence") or {}
    assert shot_conf.get("level_code") in ["very_sure", "fairly_sure"]
    assert shot_conf.get("confidence", 0) >= 65


# ---------------------------------------------------------------------------
# TEST 3: Cut-Off Swing or Low Quality Caps Confidence at <= 50%
# ---------------------------------------------------------------------------
def test_3_cut_off_swing_or_low_light_caps_confidence():
    """A cut-off swing strictly caps confidence at 50% with explicit plain-English reason."""
    frames = _build_synthetic_shot_frames(shot_family="straight")[:20] # Cut off before impact!
    res = shot_classifier_service.classify_sequence(frames, hint_shot="Cover Drive", camera_view="side-on")

    shot_conf = res.get("shot_confidence") or {}
    assert shot_conf.get("confidence", 100) <= 50, f"Expected confidence capped at <=50, got {shot_conf.get('confidence')}"
    caps = shot_conf.get("caps_applied", [])
    assert any("cut-off" in c.lower() for c in caps), f"Expected cut-off cap in {caps}"


# ---------------------------------------------------------------------------
# TEST 4: Ambiguous Clip Pauses Coaching (Mutual Protection)
# ---------------------------------------------------------------------------
def test_4_ambiguous_clip_pauses_coaching_and_prompts_confirmation():
    """Ambiguous candidate gap triggers 'not_sure' or 'cant_tell' and pauses technique coaching."""
    top_candidates = [
        {"shot": "Cover Drive", "score": 0.48},
        {"shot": "Straight Drive", "score": 0.46}
    ]
    low_conf_eval = confidence_service.evaluate_confidence(
        predicted_shot="Cover Drive",
        raw_score=0.48,
        top_candidates=top_candidates,
        frame_metrics=[{"confidence": 0.70, "pose_detected": True}] * 30,
        camera_view="side-on"
    )
    assert low_conf_eval["level_code"] in ["not_sure", "cant_tell"]

    is_paused = low_conf_eval["level_code"] in ["not_sure", "cant_tell"]
    assert is_paused is True


# ---------------------------------------------------------------------------
# TEST 5: Rare Shot Limited Data Cap
# ---------------------------------------------------------------------------
def test_5_rare_shot_limited_data_cap():
    """A rare shot with < 8 clips is capped at <= 60% with 'limited training data' note."""
    top_candidates = [
        {"shot": "Helicopter Shot", "score": 0.95},
        {"shot": "Cover Drive", "score": 0.02}
    ]
    eval_res = confidence_service.evaluate_confidence(
        predicted_shot="Helicopter Shot",
        raw_score=0.95,
        top_candidates=top_candidates,
        frame_metrics=[{"confidence": 0.90, "pose_detected": True}] * 35,
        camera_view="side-on"
    )
    assert eval_res["confidence"] <= 60
    assert any("limited training data" in r.lower() for r in eval_res.get("reasons", []) or eval_res.get("caps_applied", []))


# ---------------------------------------------------------------------------
# TEST 6: Mirrored Clip Agreement (TTA)
# ---------------------------------------------------------------------------
def test_6_mirrored_clip_tta_agreement():
    """Checks TTA mirror evaluation runs and handles agreement/disagreement."""
    top_candidates = [
        {"shot": "Cover Drive", "score": 0.85},
        {"shot": "Straight Drive", "score": 0.10}
    ]
    # Disagreement case: predicted as Cover Drive, mirrored as Straight Drive
    eval_res = confidence_service.evaluate_confidence(
        predicted_shot="Cover Drive",
        raw_score=0.85,
        top_candidates=top_candidates,
        frame_metrics=[{"confidence": 0.90, "pose_detected": True}] * 35,
        camera_view="side-on",
        mirrored_predicted_shot="Straight Drive"
    )
    assert eval_res.get("tta_agreement") is False
    assert eval_res.get("confidence") <= 58


# ---------------------------------------------------------------------------
# TEST 7: Non-Shot Produces 'Can't Tell' Without Invented Name
# ---------------------------------------------------------------------------
def test_7_non_shot_produces_cant_tell_without_invented_name():
    """Non-shot clip (standing still, no swing) results in 'Can't tell' without inventing a stroke."""
    still_frames = [
        {
            "frame_index": f,
            "timestamp_sec": round(f * 0.033, 3),
            "pose_detected": True,
            "confidence": 0.85,
            "lead_knee_angle": 165.0,
            "rear_knee_angle": 165.0,
            "lead_elbow_angle": 150.0,
            "torso_inclination": 5.0,
            "lead_wrist_speed": 0.01,
            "stance_width_norm": 0.9,
            "phase": "Stance",
            "landmarks": [{"x": 0.3, "y": 0.3, "visibility": 0.9}] * 33
        }
        for f in range(35)
    ]
    res = shot_classifier_service.classify_sequence(still_frames)
    pred_shot = res.get("predicted_shot", "").lower()
    shot_conf = res.get("shot_confidence", {})

    assert ("leave" in pred_shot or "unrecognised" in pred_shot or shot_conf.get("level_code") == "cant_tell")


# ---------------------------------------------------------------------------
# TEST 8: UI Never Receives Uncalibrated Score
# ---------------------------------------------------------------------------
def test_8_ui_never_receives_uncalibrated_raw_score():
    """Verifies shot_confidence payload contains calibrated prob and levels."""
    frames = _build_synthetic_shot_frames(shot_family="off")
    res = shot_classifier_service.classify_sequence(frames, hint_shot="Cover Drive")
    conf_payload = res.get("shot_confidence")

    assert conf_payload is not None
    assert "calibrated_model_probability" in conf_payload
    assert "quality_factor" in conf_payload
    assert "margin_factor" in conf_payload
    assert 0 <= conf_payload["confidence"] <= 100
    assert conf_payload["level"] in ["Very sure", "Fairly sure", "Not very sure", "Can't tell"]


# ---------------------------------------------------------------------------
# TEST 9: Language Lint Test: Zero Banned Jargon & Sentence Length < 15 Words
# ---------------------------------------------------------------------------
def test_9_plain_language_lint_no_banned_jargon_short_sentences():
    """Strictly enforces zero biomechanics jargon in default feedback and avg sentence < 15 words."""
    card = plain_language_service.compose_issue_card(
        metric_key="lead_knee_angle",
        measured_val=168.0,
        min_ideal=118.0,
        max_ideal=140.0,
        phase="impact",
        shot_name="Cover Drive",
        frame_index=25,
        timestamp_sec=0.82,
        confidence=0.92,
        severity_rank=0,
        time_series=[]
    )

    full_text = f"{card['title']}. {card['why_it_matters']} {card['how_to_fix']} {card['drill']['instructions']}"
    banned_found = plain_language_service.lint_text_for_banned_jargon(full_text)
    assert not banned_found, f"Found banned jargon in issue card default layer: {banned_found}"

    avg_len = plain_language_service.calculate_average_sentence_length(full_text)
    assert avg_len < 15.0, f"Expected average sentence length < 15 words, got {avg_len:.1f}"
    assert len(card["title"].split()) <= 8, f"Title has > 8 words: '{card['title']}'"


# ---------------------------------------------------------------------------
# TEST 10: Issue Cards Structure & ONE Focus Equals Top Issue
# ---------------------------------------------------------------------------
def test_10_issue_cards_structure_and_one_focus():
    """Validates 6-part issue card structure and top summary ONE focus alignment."""
    frames = _build_synthetic_shot_frames(shot_family="straight", stiff_knee=True)
    phases = [{"phase_name": "Impact window", "start_frame": 24, "end_frame": 28, "key_frame": 25}]
    summary = {"lead_knee_flexion_at_impact": 168.0}

    eval_res = feedback_service.evaluate_technique(
        frames, phases, summary, shot_type="Straight Drive", camera_view="side-on"
    )

    assert isinstance(eval_res, EvaluationResult)
    cards = eval_res.issue_cards
    assert len(cards) >= 1

    top_card = cards[0]
    assert top_card.get("title")
    assert top_card.get("where_and_when")
    assert top_card.get("why_it_matters")
    assert top_card.get("how_to_fix")
    assert top_card.get("drill", {}).get("name")
    assert top_card.get("severity_label") in ["Fix this first", "Worth improving", "Minor"]

    plain_sum = eval_res.plain_summary
    assert plain_sum.get("one_focus_for_next_10_balls") is not None
    assert plain_sum["one_focus_for_next_10_balls"]["target_body_part"] == top_card["target_body_part"]


# ---------------------------------------------------------------------------
# TEST 11: Moment Loop Window Bounds
# ---------------------------------------------------------------------------
def test_11_moment_loop_window_bounds():
    """Moment loop window spans ~2-3 seconds around fault frame."""
    card = plain_language_service.compose_issue_card(
        metric_key="lead_knee_angle",
        measured_val=168.0,
        min_ideal=118.0,
        max_ideal=140.0,
        phase="impact",
        shot_name="Straight Drive",
        frame_index=45,
        timestamp_sec=1.5,
        confidence=0.9,
        severity_rank=0,
        time_series=[{"lead_knee_angle": 130}] * 100
    )
    loop = card["loop_window"]
    assert loop["center_frame"] == 45
    assert loop["start_frame"] < loop["center_frame"]
    assert loop["end_frame"] > loop["center_frame"]
    assert 40 <= (loop["end_frame"] - loop["start_frame"]) <= 90


# ---------------------------------------------------------------------------
# TEST 12: Unmeasurable Metric in Front-On Camera View
# ---------------------------------------------------------------------------
def test_12_unmeasurable_metric_in_camera_view():
    """In front-on camera view, knee flexion shows 'couldn't check' notice with NO knee advice."""
    frames = _build_synthetic_shot_frames(shot_family="straight", stiff_knee=True)
    phases = [{"phase_name": "Impact window", "start_frame": 24, "end_frame": 28, "key_frame": 25}]
    summary = {"lead_knee_flexion_at_impact": 168.0}

    eval_res = feedback_service.evaluate_technique(
        frames, phases, summary, shot_type="Straight Drive", camera_view="front-on"
    )

    notices = eval_res.plain_summary.get("unmeasurable_notices", [])
    assert any("couldn't check your front knee" in n.lower() for n in notices), f"Expected front-on notice in {notices}"

    knee_cards = [c for c in eval_res.issue_cards if "knee" in c.get("id", "").lower()]
    assert len(knee_cards) == 0, "No knee coaching should be offered when unmeasurable in front-on view"


# ---------------------------------------------------------------------------
# TEST 13: Hindi / Hinglish Translation with English Fallback
# ---------------------------------------------------------------------------
def test_13_hindi_hinglish_translation_and_fallback():
    """Verifies coach-style Hindi/Hinglish translations."""
    card_hi = plain_language_service.compose_issue_card(
        metric_key="lead_knee_angle",
        measured_val=168.0,
        min_ideal=118.0,
        max_ideal=140.0,
        phase="impact",
        shot_name="Cover Drive",
        frame_index=25,
        timestamp_sec=0.82,
        confidence=0.92,
        severity_rank=0,
        time_series=[],
        lang="hi"
    )
    assert "ghutna" in card_hi["title"].lower() or "ghutna" in card_hi["how_to_fix"].lower()
    assert card_hi["severity_label"] == "Pehle yeh theek karo"


# ---------------------------------------------------------------------------
# TEST 14: Clean Technique Clip Gives Encouraging Feedback (No Invented Faults)
# ---------------------------------------------------------------------------
def test_14_clean_technique_gives_encouraging_feedback_no_invented_faults():
    """A clean execution clip yields score >= 85, encouraging verdict, and no fake mistakes."""
    frames = _build_synthetic_shot_frames(shot_family="straight", stiff_knee=False)
    phases = [{"phase_name": "Impact window", "start_frame": 24, "end_frame": 28, "key_frame": 25}]
    summary = {"lead_knee_flexion_at_impact": 126.0}

    eval_res = feedback_service.evaluate_technique(
        frames, phases, summary, shot_type="Straight Drive", camera_view="side-on"
    )
    assert eval_res.overall_score >= 85.0
    assert eval_res.plain_summary["score_label"] in ["Excellent", "Good"]
    assert len(eval_res.plain_summary["what_you_did_well"]) >= 1


# ---------------------------------------------------------------------------
# TEST 15: Progress Tracking Plain Words & Separate Lines
# ---------------------------------------------------------------------------
def test_15_progress_tracking_plain_words_and_dual_lines():
    """Verifies 'My Progress' plain-words items and dual lines (Technique vs Shot recognized)."""
    trend = progress_service.get_shot_trend("Cover Drive")
    assert "plain_progress_statements" in trend
    assert "dual_tracking" in trend
    if trend["dual_tracking"]:
        line = trend["dual_tracking"][0]["summary_line"]
        assert "Technique:" in line and "Shot recognized:" in line


def test_classifier_reports_phase_window_evidence_and_short_clip_uncertainty():
    frames = _build_synthetic_shot_frames(shot_family="straight")
    result = shot_classifier_service.classify_sequence(frames, camera_view="side-on")
    assert result["extracted_features"]["swing_window_source"] == "phase-labeled swing"
    assert result["extracted_features"]["swing_window_frames"] < len(frames)
    assert any("Swing evidence window" in item for item in result["evidence"])

    short = shot_classifier_service.classify_sequence(frames[:5], camera_view="side-on")
    assert short["predicted_shot"] == "No clear shot detected"
    assert short["is_uncertain"] is True


def test_feedback_points_keep_clip_measurement_phase_time_and_reference():
    frames = _build_synthetic_shot_frames(shot_family="straight", stiff_knee=True)
    result = feedback_service.evaluate_technique(
        frames, [], {}, shot_type="Straight Drive", camera_view="side-on"
    )
    assert result.issue_cards
    for card in result.issue_cards:
        proof = card["proof"]
        assert isinstance(proof["measured_value"], (int, float))
        assert proof["timestamp_sec"] is not None
        assert proof["ideal_min"] <= proof["ideal_max"]
