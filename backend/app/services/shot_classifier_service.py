"""
CricketIQ — Explainable Hierarchical Kinematic Shot Classification Service
Two-stage classification engine with calibrated confidence scoring:
  Stage 1: Stroke Family (Drive, Defensive, Cross-bat, Leg-side, Sweep, Innovative, Leave / No Shot)
  Stage 2: Shot within Family (using view-aware, handedness-normalized biomechanical kinematics)
  Stage 3: Calibrated Confidence Assessment via ConfidenceService
"""

import math
import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from backend.app.services.confidence_service import confidence_service

logger = logging.getLogger(__name__)

class ShotClassifierService:
    """
    Two-stage hierarchical classifier that categorizes cricket shots without sweep bias,
    blanket drive defaults, or hidden overrides, calibrated via Platt scaling and quality factor.
    """

    CONFIDENCE_THRESHOLD = 0.55
    MARGIN_THRESHOLD = 0.10

    def _classify_core(
        self,
        frame_metrics: List[Dict[str, Any]],
        camera_view: str = "side-on",
        handedness: str = "Right"
    ) -> Tuple[str, float, List[Tuple[str, float]], str, Dict[str, Any]]:
        """Core feature extraction and two-stage classification."""
        valid_frames = [m for m in frame_metrics if m.get("pose_detected")]
        swing_frames = [
            m for m in valid_frames
            if any(k in str(m.get("phase", "")).lower() for k in
                   ("backlift", "stride", "downswing", "impact", "follow"))
        ]
        use_swing_window = len(swing_frames) >= max(5, int(len(valid_frames) * 0.2))
        analysis_frames = swing_frames if use_swing_window else valid_frames
        is_left_handed = handedness.lower().strip() == "left"

        # Calculate average torso length for spatial scale invariance
        torso_lens = []
        for m in analysis_frames:
            lms = m.get("landmarks")
            if lms and len(lms) >= 25:
                def _get_y(lm):
                    return lm.get("y", 0.0) if isinstance(lm, dict) else getattr(lm, "y", 0.0)
                sh_y = (_get_y(lms[11]) + _get_y(lms[12])) / 2.0
                hp_y = (_get_y(lms[23]) + _get_y(lms[24])) / 2.0
                t_dist = abs(hp_y - sh_y)
                if 0.10 < t_dist < 0.60:
                    torso_lens.append(t_dist)

        torso_len = float(np.mean(torso_lens)) if torso_lens else 0.28
        torso_len = max(0.12, torso_len)

        # Extract kinematic arrays
        lead_knees = [m["lead_knee_angle"] for m in analysis_frames if m.get("lead_knee_angle") is not None]
        rear_knees = [m["rear_knee_angle"] for m in analysis_frames if m.get("rear_knee_angle") is not None]
        torso_leans = [m["torso_inclination"] for m in analysis_frames if m.get("torso_inclination") is not None]
        stance_widths = [m["stance_width_norm"] for m in analysis_frames if m.get("stance_width_norm") is not None]
        wrist_speeds = [m.get("lead_wrist_speed", 0.0) or m.get("bat_speed_norm", 0.0) or 0.0 for m in analysis_frames]

        wrist_xs = []
        wrist_ys = []
        hip_ys = []
        sh_ys = []
        for m in analysis_frames:
            wx = m.get("lead_wrist_x") if m.get("lead_wrist_x") is not None else m.get("bat_tip_x")
            wy = m.get("lead_wrist_y") if m.get("lead_wrist_y") is not None else m.get("bat_tip_y")
            if wx is not None and wy is not None:
                adj_x = (1.0 - wx) if is_left_handed else wx
                wrist_xs.append(adj_x)
                wrist_ys.append(wy)
            lms = m.get("landmarks")
            if lms and len(lms) >= 25:
                def _gy(lm):
                    return lm.get("y", 0.0) if isinstance(lm, dict) else getattr(lm, "y", 0.0)
                hip_ys.append((_gy(lms[23]) + _gy(lms[24])) / 2.0)
                sh_ys.append((_gy(lms[11]) + _gy(lms[12])) / 2.0)

        mean_shoulder_y = float(np.mean(sh_ys)) if sh_ys else 0.35
        min_wrist_y = float(np.min(wrist_ys)) if wrist_ys else 0.40

        # Basic kinematic metrics
        min_lead_knee = float(np.min(lead_knees)) if lead_knees else 145.0
        min_rear_knee = float(np.min(rear_knees)) if rear_knees else 145.0
        mean_torso_lean = float(np.mean(torso_leans)) if torso_leans else 16.0
        max_torso_lean = float(np.max(torso_leans)) if torso_leans else 20.0
        peak_wrist_speed = float(np.max(wrist_speeds)) if wrist_speeds else 0.0

        # Normalized wrist spans
        if wrist_xs and wrist_ys:
            w_span_x = (max(wrist_xs) - min(wrist_xs)) / torso_len
            w_span_y = (max(wrist_ys) - min(wrist_ys)) / torso_len
        else:
            w_span_x = 0.5
            w_span_y = 0.5

        # Stride expansion ratio
        setup_stances = stance_widths[:max(5, len(stance_widths) // 4)]
        base_stance = float(np.mean(setup_stances)) if setup_stances else 1.0
        max_stance = float(np.max(stance_widths)) if stance_widths else 1.0
        stride_ratio = max_stance / max(0.40, base_stance)

        # Pelvis height drop
        setup_hips = hip_ys[:max(5, len(hip_ys) // 4)]
        base_hip = float(np.mean(setup_hips)) if setup_hips else 0.55
        max_hip = float(np.max(hip_ys)) if hip_ys else base_hip
        pelvis_drop = (max_hip - base_hip) / torso_len

        # Wrist trajectory through swing
        n_w = len(wrist_xs)
        if n_w >= 8:
            start_i = int(n_w * 0.25)
            end_i = min(n_w - 1, int(n_w * 0.75))
            dx = (wrist_xs[end_i] - wrist_xs[start_i]) / torso_len
            dy = (wrist_ys[end_i] - wrist_ys[start_i]) / torso_len
        else:
            dx = 0.0
            dy = -0.5

        # Bat orientations (in cricket, 0 deg is pointing down/vertical, 90 deg is horizontal)
        bat_angles = [m["bat_angle_deg"] for m in analysis_frames if m.get("bat_detected") and m.get("bat_angle_deg") is not None]
        horizontal_bat_count = sum(1 for a in bat_angles if 45.0 <= abs(a) <= 135.0)
        horizontal_bat_ratio = horizontal_bat_count / max(1, len(bat_angles)) if bat_angles else 0.0

        impact_frames = [m for m in analysis_frames if "impact" in str(m.get("phase", "")).lower()]
        impact_bat_angles = [m["bat_angle_deg"] for m in impact_frames if m.get("bat_angle_deg") is not None]
        impact_bat_angle = float(np.mean(impact_bat_angles)) if impact_bat_angles else (bat_angles[len(bat_angles)//2] if bat_angles else 25.0)

        impact_wrist_ys = [
            m.get("lead_wrist_y") if m.get("lead_wrist_y") is not None else m.get("bat_tip_y")
            for m in impact_frames
            if (m.get("lead_wrist_y") is not None or m.get("bat_tip_y") is not None)
        ]
        impact_wrist_y = float(np.mean(impact_wrist_ys)) if impact_wrist_ys else min_wrist_y

        # Stage 1: Family Decision
        family_scores: Dict[str, float] = {
            "Leave / No Shot": 0.05,
            "Defensive": 0.10,
            "Sweep": 0.10,
            "Cross-bat": 0.10,
            "Drive": 0.10,
            "Leg-side": 0.08,
            "Innovative": 0.05
        }

        horizontal_sweep_path = horizontal_bat_ratio > 0.25 or (w_span_x >= 0.40 and abs(dx) > 0.15) or abs(impact_bat_angle) > 35.0
        is_kneeling = (
            min_rear_knee < 128.0 and (pelvis_drop >= 0.08 or min_rear_knee < 112.0)
        )
        if is_kneeling:
            family_scores["Sweep"] = 0.95

        is_leave = (
            (w_span_x < 0.35 and w_span_y < 0.40 and peak_wrist_speed < 0.028) or
            (peak_wrist_speed < 0.020 and stride_ratio < 1.15)
        ) and not is_kneeling
        if is_leave:
            family_scores["Leave / No Shot"] = 0.94

        is_compact_swing = (stride_ratio < 1.25 and w_span_y < 0.70 and peak_wrist_speed < 0.038) or (
            stride_ratio >= 1.20 and peak_wrist_speed < 0.040 and abs(impact_bat_angle) < 32.0 and dy > -0.55
        )
        if is_compact_swing and not is_kneeling and not is_leave:
            family_scores["Defensive"] = 0.90

        # Cross-bat: back-foot transfer (stride_ratio < 1.25, tall lead knee, upright torso) or horizontal bat at impact
        is_cross_bat = (
            (stride_ratio < 1.25 and (min_lead_knee > 142.0 or abs(impact_bat_angle) >= 35.0))
            and not is_kneeling and not is_compact_swing
        )
        if is_cross_bat:
            family_scores["Cross-bat"] = 0.92

        # Drive: front-foot stride (stride_ratio >= 1.20), flexed lead knee, steep vertical bat at impact
        is_drive = (stride_ratio >= 1.20 and min_lead_knee <= 142.0 and not is_kneeling and not is_compact_swing and not is_cross_bat)
        if is_drive:
            family_scores["Drive"] = 0.92

        if dx < -0.30 and stride_ratio > 1.15 and not is_kneeling and not is_cross_bat:
            family_scores["Leg-side"] = 0.85

        top_family = max(family_scores.keys(), key=lambda k: family_scores[k])

        # Stage 2: Specific Shot Classification within Family
        candidate_scores: Dict[str, float] = {}

        if top_family == "Leave / No Shot":
            candidate_scores["Leave / No Shot Attempted"] = 0.92
            candidate_scores["Forward Defensive"] = 0.40
            candidate_scores["Unrecognised Shot"] = 0.35

        elif top_family == "Sweep":
            if dx > 0.35:
                candidate_scores["Reverse Sweep"] = 0.90
                candidate_scores["Sweep"] = 0.72
                candidate_scores["Paddle Sweep"] = 0.65
            elif max_torso_lean > 26.0 and w_span_y > 0.90:
                candidate_scores["Slog Sweep"] = 0.89
                candidate_scores["Sweep"] = 0.80
                candidate_scores["Paddle Sweep"] = 0.68
            elif dx < -0.25:
                candidate_scores["Paddle Sweep"] = 0.88
                candidate_scores["Sweep"] = 0.78
                candidate_scores["Slog Sweep"] = 0.60
            else:
                candidate_scores["Sweep"] = 0.90
                candidate_scores["Slog Sweep"] = 0.74
                candidate_scores["Paddle Sweep"] = 0.72

        elif top_family == "Defensive":
            if stride_ratio >= 1.20:
                candidate_scores["Forward Defensive"] = 0.90
                candidate_scores["Back-foot Defensive"] = 0.62
                candidate_scores["Straight Drive"] = 0.52
            else:
                candidate_scores["Back-foot Defensive"] = 0.89
                candidate_scores["Forward Defensive"] = 0.64
                candidate_scores["Back-foot Punch"] = 0.55

        elif top_family == "Cross-bat":
            is_high_hook = (impact_wrist_y <= mean_shoulder_y + 0.05)
            has_bat = len(bat_angles) > 0
            is_punch = (has_bat and horizontal_bat_ratio < 0.20 and abs(impact_bat_angle) < 40.0) or (not has_bat and w_span_x < 0.20 and dy > 0.30)
            is_late_cut = (has_bat and dx <= 0.05 and abs(impact_bat_angle) > 35.0 and dy > 0.10)
            is_side_on = not any(v in camera_view.lower() for v in ["front", "behind", "pitch", "bowler"])

            is_pull_or_hook = (
                (is_side_on and (dx >= 0.45 or dx <= -0.25 or (abs(dx) >= 0.25 and dy <= 0.10))) or
                (not is_side_on and dx < -0.15)
            )

            if is_punch:
                candidate_scores["Back-foot Punch"] = 0.90
                candidate_scores["Square Cut"] = 0.72
                candidate_scores["Pull Shot"] = 0.65
            elif is_late_cut:
                candidate_scores["Late Cut"] = 0.89
                candidate_scores["Square Cut"] = 0.76
                candidate_scores["Back-foot Punch"] = 0.68
            elif is_pull_or_hook:
                # In horizontal cross-bat swing across to on-side, pull/hook dominates
                if is_high_hook:
                    candidate_scores["Hook Shot"] = 0.90
                    candidate_scores["Pull Shot"] = 0.78
                    candidate_scores["Square Cut"] = 0.58
                else:
                    candidate_scores["Pull Shot"] = 0.90
                    candidate_scores["Hook Shot"] = 0.76
                    candidate_scores["Square Cut"] = 0.62
            else:
                candidate_scores["Square Cut"] = 0.90
                candidate_scores["Late Cut"] = 0.76
                candidate_scores["Back-foot Punch"] = 0.70
                candidate_scores["Pull Shot"] = 0.60

        elif top_family == "Leg-side":
            if dx < -0.40:
                candidate_scores["Flick Shot"] = 0.88
                candidate_scores["Leg Glance"] = 0.80
                candidate_scores["On Drive"] = 0.70
            else:
                candidate_scores["Leg Glance"] = 0.86
                candidate_scores["Flick Shot"] = 0.80
                candidate_scores["On Drive"] = 0.72

        else: # Drive Family
            is_front_or_behind = any(v in camera_view.lower() for v in ["front", "behind", "pitch", "bowler"])
            if is_front_or_behind:
                is_straight = abs(dx) <= 0.05
                is_on_drive = dx < -0.08
                is_cover = dx > 0.08
                is_off_drive = 0.02 < dx <= 0.08
            else:
                # Side-on view:
                # Straight Drive: compact vertical pendulum down pitch (abs(impact_bat_angle) <= 18.0 or dx <= 0.75)
                is_straight = (abs(impact_bat_angle) <= 18.0 and dx <= 0.75) or (w_span_x < 0.25)
                is_on_drive = (dx < -0.25 and dy > -0.70)
                is_cover = not is_straight and not is_on_drive and (dx > 0.75 or abs(impact_bat_angle) > 18.0)
                is_off_drive = not is_straight and not is_on_drive and not is_cover

            if is_straight:
                candidate_scores["Straight Drive"] = 0.90
                candidate_scores["Off Drive"] = 0.74
                candidate_scores["Cover Drive"] = 0.65
                candidate_scores["On Drive"] = 0.65
            elif is_on_drive:
                candidate_scores["On Drive"] = 0.89
                candidate_scores["Straight Drive"] = 0.76
                candidate_scores["Flick Shot"] = 0.70
                candidate_scores["Cover Drive"] = 0.58
            elif is_off_drive:
                candidate_scores["Off Drive"] = 0.89
                candidate_scores["Cover Drive"] = 0.80
                candidate_scores["Straight Drive"] = 0.78
            elif is_cover:
                candidate_scores["Cover Drive"] = 0.89
                candidate_scores["Off Drive"] = 0.78
                candidate_scores["Straight Drive"] = 0.68
                candidate_scores["Square Drive"] = 0.62
            else:
                candidate_scores["Cover Drive"] = 0.86
                candidate_scores["Straight Drive"] = 0.82
                candidate_scores["Off Drive"] = 0.78

        catalogue_fallbacks = ["Straight Drive", "Cover Drive", "Forward Defensive", "Pull Shot", "Square Cut"]
        for fb in catalogue_fallbacks:
            if fb not in candidate_scores:
                candidate_scores[fb] = 0.20

        sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
        top_shot, top_score = sorted_candidates[0]

        feature_dict = {
            "family": top_family,
            "stride_ratio": round(stride_ratio, 2),
            "wrist_span_x_norm": round(w_span_x, 2),
            "wrist_span_y_norm": round(w_span_y, 2),
            "wrist_dy_norm": round(dy, 2),
            "wrist_dx_norm": round(dx, 2),
            "min_lead_knee_deg": round(min_lead_knee, 1),
            "min_rear_knee_deg": round(min_rear_knee, 1),
            "mean_torso_lean_deg": round(mean_torso_lean, 1),
            "pelvis_drop_norm": round(pelvis_drop, 2),
            "horizontal_bat_ratio": round(horizontal_bat_ratio, 2),
            "torso_length": round(torso_len, 3),
            "camera_view": camera_view,
            "handedness": handedness,
            "swing_window_frames": len(analysis_frames),
            "swing_window_source": "phase-labeled swing" if use_swing_window else "full clip (phase labels unavailable)",
            "wrist_or_bat_motion_frames": sum(1 for m in analysis_frames if m.get("lead_wrist_speed") is not None or m.get("bat_speed_norm") is not None),
            "mean_pose_confidence": round(float(np.mean([m.get("confidence", 0.0) for m in analysis_frames])), 2) if analysis_frames else 0.0
        }

        return top_shot, top_score, sorted_candidates, top_family, feature_dict

    def classify_sequence(
        self,
        frame_metrics: List[Dict[str, Any]],
        hint_shot: Optional[str] = None,
        camera_view: str = "side-on",
        handedness: str = "Right"
    ) -> Dict[str, Any]:
        """
        Classifies batting sequence with Platt calibration, margin assessment,
        quality gate capping, TTA agreement, and plain-English certainty.
        """
        if not frame_metrics:
            return self._build_uncertain_response(
                shot_name="Leave / No Shot Attempted",
                conf=0.10,
                rationale="No kinematic frame data extracted from clip.",
                hint_shot=hint_shot
            )

        valid_frames = [m for m in frame_metrics if m.get("pose_detected")]
        tracking_rate = len(valid_frames) / max(1, len(frame_metrics))

        if tracking_rate < 0.20:
            return self._build_uncertain_response(
                shot_name="Unrecognised Shot",
                conf=round(tracking_rate, 2),
                rationale=f"Insufficient tracking: pose detected in only {tracking_rate*100:.1f}% of frames.",
                hint_shot=hint_shot
            )

        if len(valid_frames) < 8:
            return self._build_uncertain_response(
                shot_name="No clear shot detected",
                conf=min(0.35, tracking_rate),
                rationale=f"Only {len(valid_frames)} pose-tracked frames are available; the swing and follow-through cannot be assessed reliably.",
                hint_shot=hint_shot
            )

        stroke_evidence_frames = [
            m for m in valid_frames
            if (m.get("lead_wrist_speed") is not None or m.get("bat_speed_norm") is not None
                or (m.get("lead_wrist_x") is not None and m.get("lead_wrist_y") is not None)
                or (m.get("bat_tip_x") is not None and m.get("bat_tip_y") is not None))
        ]
        if len(stroke_evidence_frames) < 5:
            return self._build_uncertain_response(
                shot_name="No clear shot detected",
                conf=round(tracking_rate * len(stroke_evidence_frames) / max(1, len(valid_frames)), 2),
                rationale="Too few visible wrist or bat measurements to confirm a batting swing.",
                hint_shot=hint_shot
            )

        # 1. Primary Classification
        top_shot, top_score, sorted_candidates, top_family, feature_dict = self._classify_core(
            frame_metrics, camera_view=camera_view, handedness=handedness
        )

        # 2. Test-Time Augmentation (TTA) check on horizontally mirrored sequence
        mirrored_handedness = "Left" if handedness.lower() == "right" else "Right"
        mirrored_shot, _, _, _, _ = self._classify_core(
            frame_metrics, camera_view=camera_view, handedness=mirrored_handedness
        )

        # Complementary mirror counterparts in cricket:
        # e.g. A right-hander's Cover Drive (off-side) mirrors naturally to an On Drive (leg-side).
        MIRROR_EQUIVALENTS = {
            "cover drive": "on drive",
            "on drive": "cover drive",
            "off drive": "on drive",
            "square cut": "pull shot",
            "pull shot": "square cut",
            "hook shot": "square cut",
            "late cut": "leg glance",
            "leg glance": "late cut",
            "flick shot": "off drive",
            "sweep": "reverse sweep",
            "reverse sweep": "sweep",
            "straight drive": "straight drive",
            "forward defensive": "forward defensive",
            "back-foot defensive": "back-foot defensive",
        }

        # If mirrored shot matches directly or matches expected mirror counterpart, treat as agreed
        if mirrored_shot.lower() == top_shot.lower() or mirrored_shot.lower() == MIRROR_EQUIVALENTS.get(top_shot.lower()):
            tta_eval_shot = top_shot
        else:
            tta_eval_shot = mirrored_shot

        top_3_raw = [
            {"shot_name": s, "score": round(sc, 3), "confidence_pct": int(sc * 100)}
            for s, sc in sorted_candidates[:3]
        ]

        evidence_frames = [m for m in valid_frames if any(k in str(m.get("phase", "")).lower() for k in
                           ("backlift", "stride", "downswing", "impact", "follow"))] or valid_frames
        evidence = [
            f"{feature_dict['swing_window_frames']} frames assessed across {feature_dict['swing_window_source']}.",
            f"Handedness used for direction normalization: {handedness}.",
            f"Stance-width expansion: {feature_dict['stride_ratio']:.2f}× baseline.",
        ]
        if feature_dict.get("wrist_span_x_norm") is not None:
            evidence.append(f"Normalized lateral wrist path: {feature_dict['wrist_dx_norm']:.2f} torso lengths.")
        if feature_dict.get("mean_pose_confidence") is not None:
            evidence.append(f"Mean pose confidence: {feature_dict['mean_pose_confidence']:.0%}.")
        if evidence_frames:
            start_t = evidence_frames[0].get("timestamp_sec")
            end_t = evidence_frames[-1].get("timestamp_sec")
            if start_t is not None and end_t is not None:
                evidence.append(f"Swing evidence window: {float(start_t):.2f}s–{float(end_t):.2f}s.")

        # 3. Apply Confidence Service Calibration
        conf_eval = confidence_service.evaluate_confidence(
            predicted_shot=top_shot,
            raw_score=top_score,
            top_candidates=top_3_raw,
            frame_metrics=frame_metrics,
            camera_view=camera_view,
            mirrored_predicted_shot=tta_eval_shot
        )

        final_shot = conf_eval["shot"]
        final_conf_ratio = conf_eval["confidence_ratio"]
        final_conf_pct = conf_eval["confidence"]
        conf_level = conf_eval["level"]

        # Only label as "No clear shot detected" when clip is truly unrecognised
        if conf_eval["level_code"] == "cant_tell" and final_shot.lower() in ("unrecognised shot", "no clear shot detected"):
            final_shot = "No clear shot detected"

        # Mismatch warning
        shot_mismatch_warning = None
        if hint_shot and final_shot.lower() != hint_shot.lower() and conf_level != "Can't tell" and final_shot.lower() not in ("unrecognized", "uncertain", "no clear shot detected"):
            shot_mismatch_warning = f"You selected {hint_shot}, but this looks like a {final_shot}."

        is_uncertain = conf_eval["needs_confirmation"] or conf_eval["is_blocked"]
        if is_uncertain:
            second_cand = sorted_candidates[1][0] if len(sorted_candidates) > 1 else "Unknown"
            uncertainty_title = f"Unsure: {final_shot} or {second_cand}" if conf_level != "Can't tell" else "Can't tell: Clip unclear"
        else:
            uncertainty_title = None

        rationale = (
            f"Stage 1: {top_family} family. "
            f"Stage 2: {final_shot} ({conf_level}, {final_conf_pct}%). "
            f"Margin: {conf_eval['margin']:.2f}, Quality factor: {conf_eval['quality_factor']:.2f}. "
            f"Caps applied: {', '.join(conf_eval['caps_applied']) if conf_eval['caps_applied'] else 'None'}."
        )

        return {
            "predicted_shot": final_shot,
            "confidence": final_conf_ratio,
            "confidence_pct": final_conf_pct,
            "confidence_level": conf_level,
            "confidence_level_code": conf_eval["level_code"],
            "confidence_level_color": conf_eval["level_color"],
            "display_label": conf_eval["display_label"],
            "shot_confidence": conf_eval,
            "is_uncertain": is_uncertain,
            "uncertainty_label": uncertainty_title,
            "family": top_family,
            "classification_method": "Calibrated Two-Stage Biomechanical Classifier",
            "top_candidates": conf_eval["top3"],
            "evidence": evidence,
            "rationale": rationale,
            "soft_warning": shot_mismatch_warning,
            "shot_mismatch_warning": shot_mismatch_warning,
            "extracted_features": feature_dict
        }

    def _build_uncertain_response(
        self,
        shot_name: str,
        conf: float,
        rationale: str,
        hint_shot: Optional[str] = None
    ) -> Dict[str, Any]:
        conf_eval = confidence_service.evaluate_confidence(
            predicted_shot=shot_name,
            raw_score=conf,
            top_candidates=[{"shot_name": shot_name, "score": conf}],
            frame_metrics=[]
        )
        return {
            "predicted_shot": shot_name,
            "confidence": conf_eval["confidence_ratio"],
            "confidence_pct": conf_eval["confidence"],
            "confidence_level": conf_eval["level"],
            "confidence_level_code": conf_eval["level_code"],
            "confidence_level_color": conf_eval["level_color"],
            "display_label": conf_eval["display_label"],
            "shot_confidence": conf_eval,
            "is_uncertain": True,
            "uncertainty_label": f"Unsure: {shot_name}",
            "family": "Unknown",
            "classification_method": "Calibrated Two-Stage Biomechanical Classifier",
            "top_candidates": conf_eval["top3"],
            "rationale": rationale,
            "soft_warning": None,
            "shot_mismatch_warning": None,
            "extracted_features": {}
        }


shot_classifier_service = ShotClassifierService()
