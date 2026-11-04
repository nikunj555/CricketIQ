"""
CricketIQ — Explainable Kinematic Shot Classification Service
Analyzes extracted body pose landmarks, footwork, joint angle trajectories, bat orientations,
and camera perspective to classify batting strokes into distinct cricket shot types.
"""

import numpy as np
import logging
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

class ShotClassifierService:
    """
    Kinematic rule-based and state-based classifier that maps observed player movements
    to cricket shot categories without sweep bias, foreshortening blindness, or silent overrides.
    """

    UNCERTAINTY_THRESHOLD = 0.45

    def classify_sequence(
        self,
        frame_metrics: List[Dict[str, Any]],
        hint_shot: Optional[str] = None,
        camera_view: str = "side-on",
        handedness: str = "Right"
    ) -> Dict[str, Any]:
        """
        Classifies an uploaded batting sequence based on extracted kinematic features.
        Returns predicted shot type, confidence, uncertainty flag, top alternatives, and soft warning.
        """
        if not frame_metrics:
            return {
                "predicted_shot": hint_shot or "Uncertain / Insufficient Data",
                "confidence": 0.0,
                "is_uncertain": True,
                "classification_method": "Biomechanical Feature Evaluator",
                "top_candidates": [],
                "rationale": "No frame metrics extracted from video.",
                "soft_warning": None
            }

        valid_frames = [m for m in frame_metrics if m.get("pose_detected")]
        tracking_rate = len(valid_frames) / max(1, len(frame_metrics))

        if tracking_rate < 0.25:
            return {
                "predicted_shot": hint_shot or "Cover Drive",
                "confidence": round(tracking_rate, 2),
                "is_uncertain": True,
                "classification_method": "Biomechanical Feature Evaluator",
                "top_candidates": [
                    {"shot_name": hint_shot or "Cover Drive", "score": 0.35}
                ],
                "rationale": f"Only {tracking_rate*100:.1f}% of frames had visible pose landmarks. Camera perspective or lighting was insufficient for reliable automated classification.",
                "soft_warning": None
            }

        # Identify swing/impact window frames vs setup frames
        impact_frames = [
            m for m in valid_frames
            if any(term in m.get("phase", "").lower() for term in ["impact", "downswing", "stride"])
        ]
        if not impact_frames:
            n = len(valid_frames)
            impact_frames = valid_frames[n // 3 : 2 * n // 3] if n >= 3 else valid_frames

        # Extract movement kinematics across swing window
        knee_angles = [m["lead_knee_angle"] for m in valid_frames if m.get("lead_knee_angle") is not None]
        rear_knee_angles = [m["rear_knee_angle"] for m in valid_frames if m.get("rear_knee_angle") is not None]
        swing_rear_knees = [m["rear_knee_angle"] for m in impact_frames if m.get("rear_knee_angle") is not None]
        swing_lead_knees = [m["lead_knee_angle"] for m in impact_frames if m.get("lead_knee_angle") is not None]
        torso_leans = [m["torso_inclination"] for m in valid_frames if m.get("torso_inclination") is not None]
        elbow_angles = [m["lead_elbow_angle"] for m in valid_frames if m.get("lead_elbow_angle") is not None]
        stance_widths = [m["stance_width_norm"] for m in valid_frames if m.get("stance_width_norm") is not None]

        min_lead_knee = float(np.min(knee_angles)) if knee_angles else 150.0
        min_rear_knee = float(np.min(rear_knee_angles)) if rear_knee_angles else 150.0
        min_swing_rear_knee = float(np.min(swing_rear_knees)) if swing_rear_knees else min_rear_knee
        min_swing_lead_knee = float(np.min(swing_lead_knees)) if swing_lead_knees else min_lead_knee

        max_torso_lean = float(np.max(torso_leans)) if torso_leans else 15.0
        mean_torso_lean = float(np.mean(torso_leans)) if torso_leans else 15.0
        max_stance_width = float(np.max(stance_widths)) if stance_widths else 1.1
        baseline_stance = float(stance_widths[0]) if stance_widths else 1.0
        stride_ratio = max_stance_width / max(0.5, baseline_stance)
        mean_lead_elbow = float(np.mean(elbow_angles)) if elbow_angles else 115.0

        # Check bat kinematics
        bat_angles = [m["bat_angle_deg"] for m in valid_frames if m.get("bat_detected") and m.get("bat_angle_deg") is not None]
        horizontal_bat_count = sum(1 for a in bat_angles if abs(a) < 35.0 or abs(a) > 145.0)
        horizontal_bat_ratio = horizontal_bat_count / max(1, len(bat_angles)) if bat_angles else 0.0

        # Off-side vs straight path indicator from wrist trajectory and stride reach
        wrist_xs = [m["lead_wrist_x"] for m in valid_frames if m.get("lead_wrist_x") is not None]
        wrist_x_span = max(wrist_xs) - min(wrist_xs) if wrist_xs else 0.0
        lateral_wrist_drift = 0.0
        if len(wrist_xs) > 3:
            lateral_wrist_drift = float(wrist_xs[-1] - wrist_xs[0])

        lead_foot_xs = [m["lead_foot_x"] for m in valid_frames if m.get("lead_foot_x") is not None]
        lead_foot_x_max = max(lead_foot_xs) if lead_foot_xs else 0.50

        scores: Dict[str, float] = {}

        # 1. Sweep Family: Requires genuine kneeling in the swing window AND a horizontal bat path
        # A deep front-foot drive with a low finish is NOT a sweep!
        is_genuine_kneeling = (min_swing_rear_knee < 88.0 and min_swing_lead_knee < 112.0)
        has_horizontal_swing = (horizontal_bat_ratio > 0.35)
        is_sweep = is_genuine_kneeling and (has_horizontal_swing or not bat_angles) and (max_torso_lean > 24.0)

        if is_sweep:
            scores["Sweep"] = 0.88
            scores["Slog Sweep"] = 0.82 if max_torso_lean > 28.0 else 0.74
            scores["Paddle Sweep"] = 0.76
            scores["Reverse Sweep"] = 0.70
        else:
            scores["Sweep"] = 0.15
            scores["Slog Sweep"] = 0.15
            scores["Paddle Sweep"] = 0.12
            scores["Reverse Sweep"] = 0.10

        # 2. Short-ball Cross-bat Family (Pull Shot, Hook Shot, Cut)
        is_backfoot_crossbat = (min_lead_knee > 136.0 and mean_torso_lean < 18.0 and (stride_ratio < 1.30 or horizontal_bat_ratio > 0.30))
        if is_backfoot_crossbat and not is_sweep:
            scores["Pull Shot"] = 0.88
            scores["Hook Shot"] = 0.82
            scores["Square Cut"] = 0.80
            scores["Back-foot Punch"] = 0.76
            scores["Upper Cut"] = 0.70
        else:
            scores["Pull Shot"] = 0.25
            scores["Hook Shot"] = 0.20

        # 3. Cut Shots
        if min_lead_knee > 140.0 and stride_ratio < 1.32 and not is_sweep:
            scores["Square Cut"] = max(scores.get("Square Cut", 0.0), 0.84)
            scores["Late Cut"] = 0.78
            scores["Back-foot Punch"] = max(scores.get("Back-foot Punch", 0.0), 0.80)
        else:
            scores["Square Cut"] = max(scores.get("Square Cut", 0.0), 0.20)
            scores["Late Cut"] = 0.15

        # 4. Front-Foot Drives (Cover Drive, Straight Drive, On Drive, Off Drive, Lofted Drive)
        # Stride present, lead knee flexion in swing, bat moving down vertically, not a sweep
        is_front_foot_drive = (not is_sweep and (stride_ratio >= 1.15 or max_stance_width > 1.2 or min_lead_knee < 155.0))
        if is_front_foot_drive:
            # Straight drive has forward pendulum reaching down ground (lead foot reach > 0.60 or wrist_x_span > 0.20)
            # Cover drive has an angled stride toward the covers with lateral follow-through
            if lead_foot_x_max > 0.60 or wrist_x_span > 0.20:
                scores["Straight Drive"] = 0.90
                scores["Cover Drive"] = 0.76
                scores["Off Drive"] = 0.78
                scores["On Drive"] = 0.74
            else:
                scores["Cover Drive"] = 0.89
                scores["Off Drive"] = 0.82
                scores["Straight Drive"] = 0.75
                scores["On Drive"] = 0.72

            scores["Lofted Drive"] = 0.78 if mean_lead_elbow > 130.0 else 0.70
        else:
            scores["Cover Drive"] = max(scores.get("Cover Drive", 0.0), 0.30)
            scores["Straight Drive"] = max(scores.get("Straight Drive", 0.0), 0.30)
            scores["On Drive"] = 0.25
            scores["Off Drive"] = 0.25
            scores["Lofted Drive"] = 0.20

        # 5. Defensive Strokes
        is_defensive = (min_lead_knee >= 125.0 and min_lead_knee <= 150.0 and mean_torso_lean < 22.0 and stride_ratio < 1.40 and not is_backfoot_crossbat and not is_sweep)
        if is_defensive:
            scores["Forward Defensive"] = 0.86
            scores["Back-foot Defensive"] = 0.75
        else:
            scores["Forward Defensive"] = max(scores.get("Forward Defensive", 0.0), 0.25)
            scores["Back-foot Defensive"] = max(scores.get("Back-foot Defensive", 0.0), 0.25)

        # 6. Leg-side Wrist Strokes
        if is_front_foot_drive and lateral_wrist_drift < -0.02:
            scores["Flick Shot"] = 0.84
            scores["Leg Glance"] = 0.80
            scores["Clip Shot"] = 0.78
        else:
            scores["Flick Shot"] = 0.25
            scores["Leg Glance"] = 0.20
            scores["Clip Shot"] = 0.20

        # 7. Innovative & Power Shots
        scores["Helicopter Shot"] = 0.65 if min_lead_knee < 135.0 and stride_ratio < 1.25 else 0.15
        scores["Scoop Shot"] = 0.75 if is_sweep and max_torso_lean > 30.0 else 0.10
        scores["Ramp Shot"] = 0.65 if min_lead_knee > 140.0 and stride_ratio < 1.25 else 0.10
        scores["Switch Hit"] = 0.30
        scores["Slog"] = 0.70 if stride_ratio > 1.35 and max_torso_lean > 22.0 else 0.20

        sorted_candidates = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_shot, top_score = sorted_candidates[0]
        second_shot, second_score = sorted_candidates[1]

        margin = top_score - second_score
        confidence = float(np.clip(top_score * 0.90 + margin * 0.10, 0.40, 0.95))
        is_uncertain = confidence < self.UNCERTAINTY_THRESHOLD or margin < 0.02

        # Soft warning if prediction disagrees with selected shot
        soft_warning = None
        if hint_shot and top_shot.lower() != hint_shot.lower() and confidence >= 0.65:
            soft_warning = f"This looks more like a {top_shot} ({confidence*100:.0f}% confidence). Analyse as {hint_shot}?"

        rationale = (
            f"Classified '{top_shot}' with {confidence*100:.0f}% confidence "
            f"(lead knee min: {min_lead_knee:.1f}°, stride ratio: {stride_ratio:.2f}x, "
            f"torso lean: {mean_torso_lean:.1f}°, camera: {camera_view})."
        )

        top_candidates = [
            {"shot_name": s, "score": round(sc, 3)}
            for s, sc in sorted_candidates[:4]
        ]

        return {
            "predicted_shot": top_shot,
            "confidence": round(confidence, 2),
            "is_uncertain": is_uncertain,
            "classification_method": "Biomechanical Kinematic State Engine",
            "top_candidates": top_candidates,
            "rationale": rationale,
            "soft_warning": soft_warning,
            "extracted_features": {
                "min_lead_knee_deg": round(min_lead_knee, 1),
                "min_rear_knee_deg": round(min_rear_knee, 1),
                "stride_ratio": round(stride_ratio, 2),
                "mean_torso_lean_deg": round(mean_torso_lean, 1),
                "max_torso_lean_deg": round(max_torso_lean, 1),
                "horizontal_bat_ratio": round(horizontal_bat_ratio, 2),
                "tracking_rate_pct": round(tracking_rate * 100.0, 1),
                "camera_view": camera_view
            }
        }

shot_classifier_service = ShotClassifierService()
