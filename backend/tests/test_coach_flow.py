"""Selected-shot-first coaching: feedback for every catalogue shot, and a cautious mismatch notice."""
from backend.app.core.config import settings
from backend.app.services.feedback_service import feedback_service
from backend.app.services.reference_service import reference_service
from backend.app.services.video_service import build_shot_mismatch_notice


def _notice(**kw):
    base = dict(selected_shot="Flick Shot", predicted_shot="Cover Drive", confidence=0.91,
                conf_code="very_sure", is_uncertain=False, auto_detect=False)
    base.update(kw)
    return build_shot_mismatch_notice(**base)


def test_notice_only_when_fairly_or_very_sure():
    assert "Cover Drive" in _notice()
    assert "Cover Drive" in _notice(conf_code="fairly_sure", confidence=0.775)
    assert _notice(conf_code="not_sure") is None
    assert _notice(is_uncertain=True) is None


def test_notice_never_for_unknown_sweep_same_or_auto():
    assert _notice(predicted_shot="No clear shot detected") is None
    assert _notice(predicted_shot="Paddle Sweep") is None
    assert _notice(predicted_shot="Reverse Sweep", selected_shot="Pull Shot") is None
    assert _notice(predicted_shot="flick shot") is None
    assert _notice(auto_detect=True) is None


def test_every_catalogue_shot_has_guidance():
    assert reference_service.get_guidance_level("Cover Drive") == "calibrated"
    assert reference_service.get_guidance_level("Flick Shot") == "baseline"
    assert reference_service.is_shot_analysis_available("Flick Shot")


def test_baseline_guidance_can_be_switched_off(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_BASELINE_GUIDANCE", False)
    assert reference_service.get_guidance_level("Flick Shot") == "none"
    assert not reference_service.is_shot_analysis_available("Flick Shot")
    assert reference_service.get_guidance_level("Cover Drive") == "calibrated"


def test_how_to_play_has_steps_for_selected_shot():
    guide = reference_service.get_how_to_play("Flick Shot")
    assert guide["shot"] == "Flick Shot"
    assert len(guide["phase_steps"]) >= 5
    assert guide["key_points"]


def test_flick_feedback_is_real_not_coming_soon():
    frames = []
    for i in range(40):
        phase = "Impact window" if 20 <= i <= 26 else ("Downswing" if i < 20 else "Follow-through")
        frames.append({
            "pose_detected": True, "frame_index": i, "timestamp_sec": i / 30.0, "phase": phase,
            "lead_knee_angle": 160.0, "rear_knee_angle": 165.0, "lead_elbow_angle": 150.0,
            "torso_inclination": 5.0, "confidence": 0.9,
        })
    summary = {"movement_smoothness": 80.0, "tracking_success_rate": 90.0}
    res = feedback_service.evaluate_technique(frames, [], summary, shot_type="Flick Shot", camera_view="side-on")
    ids = [o.id for o in res[2]]
    assert "obs_coming_soon" not in ids
