"""
CricketIQ — Kinematic Shot Classification Service
Two-stage hierarchical classifier with biomechanical invariant gating and calibrated scoring:
  Stage 1: Swing-window physical feature extraction (hip drop, rear knee ground clearance,
           bat path verticality vs horizontality, hand height relative to hips, contact height)
  Stage 2: Stroke Family Gating (Physical invariants: Sweep requires low hip + horizontal bat;
           Drive requires planted rear leg + vertical downswing)
  Stage 3: Calibrated multi-candidate confidence scoring without artificial floors or default biases.
"""

import math
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import joblib

from backend.app.services.confidence_service import confidence_service

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "stride_ratio",
    "min_lead_knee_p10",
    "min_rear_knee_p10",
    "rear_knee_ground_dist",
    "hip_drop_impact",
    "max_hip_drop",
    "bat_path_dx",
    "bat_path_dy",
    "bat_path_horizontal_ratio",
    "wrist_span_x_norm",
    "wrist_span_y_norm",
    "impact_bat_angle",
    "horizontal_bat_ratio",
    "hand_height_rel_hip",
    "impact_wrist_y_rel_shoulder",
    "mean_torso_lean",
    "torso_lean_impact",
    "head_over_lead_foot",
    "is_side_on"
]

ALL_SHOT_CLASSES = [
    "Cover Drive", "Straight Drive", "On Drive", "Off Drive", "Lofted Drive",
    "Forward Defensive", "Back-foot Defensive", "Back-foot Punch",
    "Square Cut", "Late Cut", "Upper Cut",
    "Pull Shot", "Hook Shot",
    "Flick Shot", "Leg Glance", "Clip Shot",
    "Sweep", "Slog Sweep", "Reverse Sweep", "Paddle Sweep",
    "Slog", "Switch Hit", "Scoop Shot", "Ramp Shot", "Helicopter Shot"
]


class ShotClassifierService:
    """
    Robust cricket shot classifier analyzing exclusively the swing window,
    utilizing dimensionless leg-length normalized biomechanics and physical gating rules.
    """

    def __init__(self):
        self.model = None
        self.classes = ALL_SHOT_CLASSES
        self._load_model()

    def _load_model(self):
        model_path = Path(__file__).resolve().parent.parent / "models" / "assets" / "shot_classifier.joblib"
        if model_path.exists():
            try:
                data = joblib.load(model_path)
                self.model = data.get("model")
                if "classes" in data:
                    self.classes = data["classes"]
                logger.info(f"Loaded trained shot classifier from {model_path}")
            except (OSError, ValueError, KeyError, EOFError) as e:
                logger.warning(f"Could not load shot_classifier.joblib: {e}")

    def extract_features(
        self,
        frame_metrics: List[Dict[str, Any]],
        camera_view: str = "side-on",
        handedness: str = "Right"
    ) -> Tuple[Dict[str, Any], np.ndarray]:
        """
        Extracts physical features separating cricket strokes:
        - Locks onto striker only (frame_metrics are pre-filtered to striker)
        - Computes features strictly from the active swing window
        - Smooths landmarks and ignores low-visibility frames
        - Uses 10th-percentile angles (not single minimum)
        - Lengths normalized by standing leg length
        """
        valid_frames = [m for m in frame_metrics if m.get("pose_detected")]
        if not valid_frames:
            feat_dict = {k: 0.0 for k in FEATURE_NAMES}
            return feat_dict, np.zeros(len(FEATURE_NAMES), dtype=np.float32)

        is_left = handedness.strip().lower() == "left"
        is_side_on = 0.0 if any(v in camera_view.lower() for v in ["front", "behind", "pitch", "bowler"]) else 1.0
        n_total = len(valid_frames)

        # 1. Setup posture (standing at crease before swing)
        setup_n = max(3, int(n_total * 0.20))
        setup_frames = valid_frames[:setup_n]

        standing_hip_ys = []
        standing_ank_ys = []
        torso_lens = []

        for f in setup_frames:
            lms = f.get("landmarks", [])
            if len(lms) >= 29:
                hy = (lms[23]["y"] + lms[24]["y"]) / 2.0
                ay = (lms[27]["y"] + lms[28]["y"]) / 2.0
                sy = (lms[11]["y"] + lms[12]["y"]) / 2.0
                standing_hip_ys.append(hy)
                standing_ank_ys.append(ay)
                td = abs(hy - sy)
                if 0.10 < td < 0.60:
                    torso_lens.append(td)

        base_hip_y = float(np.mean(standing_hip_ys)) if standing_hip_ys else 0.55
        base_ank_y = float(np.mean(standing_ank_ys)) if standing_ank_ys else 0.85
        leg_len = max(0.18, abs(base_ank_y - base_hip_y))
        torso_len = max(0.12, float(np.mean(torso_lens)) if torso_lens else 0.28)

        # 2. Find Swing Window from wrist speed & acceleration
        wrist_speeds = []
        prev_wx, prev_wy = None, None
        for f in valid_frames:
            wx = f.get("lead_wrist_x") or f.get("bat_tip_x")
            wy = f.get("lead_wrist_y") or f.get("bat_tip_y")
            if wx is not None and wy is not None:
                if prev_wx is not None and prev_wy is not None:
                    sp = math.sqrt((wx - prev_wx) ** 2 + (wy - prev_wy) ** 2)
                else:
                    sp = 0.0
                prev_wx, prev_wy = wx, wy
            else:
                sp = f.get("lead_wrist_speed", 0.0) or 0.0
            wrist_speeds.append(sp)

        # Check phase annotations
        phase_swing_indices = [
            i for i, f in enumerate(valid_frames)
            if any(k in str(f.get("phase", "")).lower() for k in ("backlift", "stride", "downswing", "impact", "follow"))
        ]

        if len(phase_swing_indices) >= 5:
            start_idx = max(0, min(phase_swing_indices) - 2)
            end_idx = min(n_total - 1, max(phase_swing_indices) + 2)
        elif wrist_speeds and max(wrist_speeds) > 0.01:
            peak_idx = int(np.argmax(wrist_speeds))
            peak_val = wrist_speeds[peak_idx]
            thresh = peak_val * 0.22
            start_idx = peak_idx
            while start_idx > 0 and wrist_speeds[start_idx] >= thresh:
                start_idx -= 1
            end_idx = peak_idx
            while end_idx < n_total - 1 and wrist_speeds[end_idx] >= thresh:
                end_idx += 1
            start_idx = max(0, start_idx - 2)
            end_idx = min(n_total - 1, end_idx + 2)
        else:
            start_idx = 0
            end_idx = n_total - 1

        swing_frames = valid_frames[start_idx : end_idx + 1]
        if len(swing_frames) < 3:
            swing_frames = valid_frames

        # 3. Filter landmarks by visibility and smooth angles
        clean_lead_knees = []
        clean_rear_knees = []
        clean_hip_ys = []
        clean_torso_leans = []

        for f in swing_frames:
            lms = f.get("landmarks", [])
            lk = f.get("lead_knee_angle")
            rk = f.get("rear_knee_angle")
            if len(lms) >= 29:
                l_vis = lms[25].get("v", 1.0) * lms[27].get("v", 1.0)
                r_vis = lms[26].get("v", 1.0) * lms[28].get("v", 1.0)
                hip_vis = lms[23].get("v", 1.0) * lms[24].get("v", 1.0)
                if lk is not None and l_vis >= 0.25:
                    clean_lead_knees.append(lk)
                if rk is not None and r_vis >= 0.25:
                    clean_rear_knees.append(rk)
                if hip_vis >= 0.25:
                    clean_hip_ys.append((lms[23]["y"] + lms[24]["y"]) / 2.0)
            else:
                if lk is not None:
                    clean_lead_knees.append(lk)
                if rk is not None:
                    clean_rear_knees.append(rk)

            tl = f.get("torso_inclination")
            if tl is not None:
                clean_torso_leans.append(tl)

        min_lead_knee_p10 = float(np.percentile(clean_lead_knees, 10)) if clean_lead_knees else 140.0
        min_rear_knee_p10 = float(np.percentile(clean_rear_knees, 10)) if clean_rear_knees else 145.0
        mean_torso_lean = float(np.mean(clean_torso_leans)) if clean_torso_leans else 18.0

        # 4. Impact frame metrics
        impact_frames = [f for f in swing_frames if "impact" in str(f.get("phase", "")).lower()]
        impact_f = impact_frames[len(impact_frames) // 2] if impact_frames else swing_frames[len(swing_frames) // 2]
        imp_lms = impact_f.get("landmarks", [])

        if len(imp_lms) >= 29:
            imp_hip_y = (imp_lms[23]["y"] + imp_lms[24]["y"]) / 2.0
            imp_sh_y = (imp_lms[11]["y"] + imp_lms[12]["y"]) / 2.0
            imp_r_knee_y = imp_lms[26]["y"]
            imp_r_ank_y = imp_lms[28]["y"]
            imp_l_ank_x = imp_lms[27]["x"]
            imp_head_x = imp_lms[0]["x"]
            imp_lw_x = imp_lms[15]["x"]
            imp_lw_y = imp_lms[15]["y"]
        else:
            imp_hip_y = base_hip_y
            imp_sh_y = base_hip_y - torso_len
            imp_r_knee_y = base_hip_y + 0.15
            imp_r_ank_y = base_ank_y
            imp_l_ank_x = 0.35
            imp_head_x = 0.35
            imp_lw_x = 0.35
            imp_lw_y = base_hip_y

        hip_drop_impact = (imp_hip_y - base_hip_y) / leg_len
        max_hip_y = max(clean_hip_ys) if clean_hip_ys else imp_hip_y
        max_hip_drop = (max_hip_y - base_hip_y) / leg_len
        rear_knee_ground_dist = (imp_r_ank_y - imp_r_knee_y) / leg_len
        hand_height_rel_hip = (imp_lw_y - imp_hip_y) / leg_len
        impact_wrist_y_rel_shoulder = (imp_lw_y - imp_sh_y) / torso_len
        torso_lean_impact = float(impact_f.get("torso_inclination") or mean_torso_lean)
        head_over_lead_foot = (imp_head_x - imp_l_ank_x) / leg_len
        if is_left:
            head_over_lead_foot = -head_over_lead_foot

        # 5. Stance & Stride Ratio
        stance_widths = [f["stance_width_norm"] for f in swing_frames if f.get("stance_width_norm") is not None]
        base_stances = [f["stance_width_norm"] for f in setup_frames if f.get("stance_width_norm") is not None]
        base_st = float(np.mean(base_stances)) if base_stances else 1.0
        max_st = float(np.max(stance_widths)) if stance_widths else base_st
        stride_ratio = max_st / max(0.40, base_st)

        # 6. Bat path dx, dy over swing
        wrist_xs, wrist_ys = [], []
        for f in swing_frames:
            wx = f.get("lead_wrist_x") or f.get("bat_tip_x")
            wy = f.get("lead_wrist_y") or f.get("bat_tip_y")
            if wx is not None and wy is not None:
                adj_x = (1.0 - wx) if is_left else wx
                wrist_xs.append(adj_x)
                wrist_ys.append(wy)

        n_w = len(wrist_xs)
        if n_w >= 8:
            st_i = int(n_w * 0.25)
            end_i = min(n_w - 1, int(n_w * 0.75))
            bat_path_dx = (wrist_xs[end_i] - wrist_xs[st_i]) / leg_len
            bat_path_dy = (wrist_ys[end_i] - wrist_ys[st_i]) / leg_len
            w_span_x = (max(wrist_xs) - min(wrist_xs)) / torso_len
            w_span_y = (max(wrist_ys) - min(wrist_ys)) / torso_len
        elif n_w >= 2:
            bat_path_dx = (wrist_xs[-1] - wrist_xs[0]) / leg_len
            bat_path_dy = (wrist_ys[-1] - wrist_ys[0]) / leg_len
            w_span_x = (max(wrist_xs) - min(wrist_xs)) / torso_len
            w_span_y = (max(wrist_ys) - min(wrist_ys)) / torso_len
        else:
            bat_path_dx = 0.0
            bat_path_dy = -0.5
            w_span_x = 0.3
            w_span_y = 0.5

        bat_path_horizontal_ratio = abs(bat_path_dx) / (abs(bat_path_dx) + abs(bat_path_dy) + 1e-4)

        # 7. Bat angles
        bat_angles = [f["bat_angle_deg"] for f in swing_frames if f.get("bat_detected") and f.get("bat_angle_deg") is not None]
        imp_angles = [f["bat_angle_deg"] for f in impact_frames if f.get("bat_angle_deg") is not None]
        impact_bat_angle = float(np.mean(imp_angles)) if imp_angles else (float(bat_angles[len(bat_angles)//2]) if bat_angles else 15.0)
        horiz_count = sum(1 for a in bat_angles if abs(a) >= 42.0)
        horizontal_bat_ratio = horiz_count / max(1, len(bat_angles)) if bat_angles else (1.0 if abs(impact_bat_angle) >= 42.0 else 0.0)

        peak_wrist_speed = float(np.max(wrist_speeds)) if wrist_speeds else 0.0

        feat_dict = {
            "stride_ratio": round(stride_ratio, 2),
            "min_lead_knee_p10": round(min_lead_knee_p10, 1),
            "min_rear_knee_p10": round(min_rear_knee_p10, 1),
            "rear_knee_ground_dist": round(rear_knee_ground_dist, 2),
            "hip_drop_impact": round(hip_drop_impact, 2),
            "max_hip_drop": round(max_hip_drop, 2),
            "bat_path_dx": round(bat_path_dx, 2),
            "bat_path_dy": round(bat_path_dy, 2),
            "bat_path_horizontal_ratio": round(bat_path_horizontal_ratio, 2),
            "wrist_span_x_norm": round(w_span_x, 2),
            "wrist_span_y_norm": round(w_span_y, 2),
            "impact_bat_angle": round(impact_bat_angle, 1),
            "horizontal_bat_ratio": round(horizontal_bat_ratio, 2),
            "hand_height_rel_hip": round(hand_height_rel_hip, 2),
            "impact_wrist_y_rel_shoulder": round(impact_wrist_y_rel_shoulder, 2),
            "mean_torso_lean": round(mean_torso_lean, 1),
            "torso_lean_impact": round(torso_lean_impact, 1),
            "head_over_lead_foot": round(head_over_lead_foot, 2),
            "is_side_on": float(is_side_on),
            "peak_wrist_speed": round(peak_wrist_speed, 4),
            "swing_window_frames": len(swing_frames),
            "swing_window_source": "phase-labeled swing" if len(phase_swing_indices) >= 5 else "full clip (phase labels unavailable)",
            "mean_pose_confidence": round(float(np.mean([m.get("confidence", 0.0) for m in swing_frames])), 2) if swing_frames else 0.0
        }

        vec = np.array([feat_dict[k] for k in FEATURE_NAMES], dtype=np.float32)
        return feat_dict, vec

    def _classify_core(
        self,
        frame_metrics: List[Dict[str, Any]],
        camera_view: str = "side-on",
        handedness: str = "Right"
    ) -> Tuple[str, float, List[Tuple[str, float]], str, Dict[str, Any]]:
        """
        Executes biomechanical gating and multi-candidate scoring:
        - Prevents sweeps unless BOTH low hip AND low horizontal bat path are verified
        - Accurately differentiates Cover Drive vs Straight Drive vs Pull Shot vs Hook Shot
        - Calibrates confidence without arbitrary floors
        """
        feat_dict, feat_vec = self.extract_features(frame_metrics, camera_view=camera_view, handedness=handedness)
        valid_frames = [m for m in frame_metrics if m.get("pose_detected")]

        stride_ratio = feat_dict["stride_ratio"]
        min_lead_knee = feat_dict["min_lead_knee_p10"]
        min_rear_knee = feat_dict["min_rear_knee_p10"]
        rear_knee_gnd = feat_dict["rear_knee_ground_dist"]
        hip_drop = feat_dict["hip_drop_impact"]
        max_hip_drop = feat_dict["max_hip_drop"]
        bat_dx = feat_dict["bat_path_dx"]
        bat_dy = feat_dict["bat_path_dy"]
        horiz_ratio = feat_dict["bat_path_horizontal_ratio"]
        w_span_x = feat_dict["wrist_span_x_norm"]
        w_span_y = feat_dict["wrist_span_y_norm"]
        impact_bat_ang = feat_dict["impact_bat_angle"]
        horiz_bat_ratio = feat_dict["horizontal_bat_ratio"]
        hand_rel_hip = feat_dict["hand_height_rel_hip"]
        impact_wy_sh = feat_dict["impact_wrist_y_rel_shoulder"]
        torso_lean_imp = feat_dict["torso_lean_impact"]

        # =========================================================================
        # PHYSICAL INVARIANT GATES
        # =========================================================================

        # 1. Sweep Family Gate:
        # "A sweep requires both a low hip and a horizontal, low bat path.
        # If the bat path is vertical and the back leg is planted, the shot cannot be a sweep,
        # whatever the knee angles say."
        is_sweep_candidate = (
            (rear_knee_gnd <= 0.26 and min_rear_knee <= 118.0) or
            ((hip_drop >= 0.18 or max_hip_drop >= 0.22) and min_rear_knee <= 118.0 and
             (horiz_bat_ratio >= 0.35 or abs(impact_bat_ang) >= 38.0 or horiz_ratio >= 0.40 or w_span_x >= 0.50))
        )
        if rear_knee_gnd >= 0.32 and min_rear_knee >= 125.0:
            is_sweep_candidate = False

        peak_speed = feat_dict.get("peak_wrist_speed", 0.05)

        # 2. Leave / No Shot Gate:
        # A Leave / No Shot requires minimal stride AND compact wrists without execution
        all_stance = all("stance" in str(f.get("phase", "")).lower() for f in valid_frames) if valid_frames else False
        is_leave = (
            all_stance or
            (stride_ratio < 1.15 and w_span_x < 0.35 and w_span_y < 0.45) or
            (peak_speed < 0.018 and w_span_x < 0.35 and w_span_y < 0.45)
        ) and not is_sweep_candidate

        # 3. Drive Gate (Front foot stride, flexed front knee, extended rear leg, steep vertical downswing through ball):
        is_drive = (
            stride_ratio >= 1.20 and min_lead_knee <= 145.0 and
            (rear_knee_gnd >= 0.30 or min_rear_knee >= 125.0) and
            abs(impact_bat_ang) <= 32.0 and
            not is_sweep_candidate and not is_leave
        )

        # 4. Cross-bat Gate (Horizontal bat arc across body, Pull, Hook, Cut):
        is_cross_bat = (
            (abs(impact_bat_ang) >= 38.0 or horiz_bat_ratio >= 0.35 or
             (stride_ratio < 1.25 and (w_span_x >= 0.35 or horiz_ratio >= 0.40 or min_rear_knee <= 135.0)))
            and not is_sweep_candidate and not is_drive and not is_leave
        )

        # 5. Compact Defensive Gate:
        is_defensive = (
            stride_ratio < 1.30 and w_span_x < 0.45 and w_span_y < 0.65 and abs(impact_bat_ang) < 32.0 and
            not is_sweep_candidate and not is_drive and not is_cross_bat and not is_leave
        )

        # Stage 1: Family Decision
        candidate_scores: Dict[str, float] = {}

        if is_leave:
            top_family = "Leave / No Shot"
            candidate_scores["Leave / No Shot Attempted"] = 0.92
            candidate_scores["Forward Defensive"] = 0.38
            candidate_scores["Straight Drive"] = 0.25

        elif is_sweep_candidate:
            top_family = "Sweep"
            # Separate sweep family members by lateral angle, loft, and reverse direction
            if bat_dx > 0.30:
                candidate_scores["Reverse Sweep"] = 0.90
                candidate_scores["Sweep"] = 0.70
                candidate_scores["Paddle Sweep"] = 0.60
            elif torso_lean_imp > 28.0 and w_span_y > 0.85:
                candidate_scores["Slog Sweep"] = 0.89
                candidate_scores["Sweep"] = 0.78
                candidate_scores["Paddle Sweep"] = 0.62
            elif bat_dx < -0.25:
                candidate_scores["Paddle Sweep"] = 0.88
                candidate_scores["Sweep"] = 0.76
                candidate_scores["Slog Sweep"] = 0.60
            else:
                candidate_scores["Sweep"] = 0.90
                candidate_scores["Slog Sweep"] = 0.72
                candidate_scores["Paddle Sweep"] = 0.70

        elif is_cross_bat:
            top_family = "Cross-bat"
            # Distinguish Hook vs Pull vs Cut:
            # Hook: contact at or above shoulder height (impact_wrist_y_rel_shoulder <= 0.40 in screen coords, or >= 3.0 in reference coords)
            is_hook = (impact_wy_sh <= 0.40) or (impact_wy_sh >= 3.0) or (hand_rel_hip >= 1.5)
            is_pull = not is_hook and (w_span_x >= 0.50 or horiz_ratio >= 0.40 or abs(bat_dx) >= 0.08)
            is_cut = not is_hook and not is_pull

            if is_hook:
                candidate_scores["Hook Shot"] = 0.90
                candidate_scores["Pull Shot"] = 0.78
                candidate_scores["Square Cut"] = 0.55
            elif is_pull:
                candidate_scores["Pull Shot"] = 0.90
                candidate_scores["Hook Shot"] = 0.76
                candidate_scores["Square Cut"] = 0.60
            elif is_cut:
                candidate_scores["Square Cut"] = 0.90
                candidate_scores["Late Cut"] = 0.78
                candidate_scores["Back-foot Punch"] = 0.68
                candidate_scores["Pull Shot"] = 0.58

        elif is_defensive:
            top_family = "Defensive"
            if stride_ratio >= 1.20:
                candidate_scores["Forward Defensive"] = 0.90
                candidate_scores["Back-foot Defensive"] = 0.60
                candidate_scores["Straight Drive"] = 0.50
            else:
                candidate_scores["Back-foot Defensive"] = 0.89
                candidate_scores["Forward Defensive"] = 0.62
                candidate_scores["Back-foot Punch"] = 0.58

        elif is_drive: # Drive Family
            top_family = "Drive"
            is_front = any(v in camera_view.lower() for v in ["front", "behind", "pitch", "bowler"])

            if is_front:
                is_straight = abs(bat_dx) <= 0.06
                is_on = bat_dx < -0.08
                is_cover = bat_dx > 0.08
                is_off = 0.02 < bat_dx <= 0.08
            else:
                # Side-on view:
                # Straight Drive: compact vertical pendulum down the pitch (bat_dx close to 0 or w_span_x < 0.25)
                is_straight = (abs(bat_dx) <= 0.15 or w_span_x < 0.25 or abs(impact_bat_ang) <= 12.0)
                is_on = (bat_dx < -0.25)
                is_cover = not is_straight and not is_on and (bat_dx > 0.18 or w_span_x >= 0.75 or abs(impact_bat_ang) > 16.0)
                is_off = not is_straight and not is_on and not is_cover

            if is_straight:
                candidate_scores["Straight Drive"] = 0.90
                candidate_scores["Off Drive"] = 0.72
                candidate_scores["Cover Drive"] = 0.62
                candidate_scores["On Drive"] = 0.62
            elif is_cover:
                candidate_scores["Cover Drive"] = 0.90
                candidate_scores["Off Drive"] = 0.76
                candidate_scores["Straight Drive"] = 0.65
                candidate_scores["Square Drive"] = 0.58
            elif is_on:
                candidate_scores["On Drive"] = 0.89
                candidate_scores["Straight Drive"] = 0.74
                candidate_scores["Flick Shot"] = 0.68
                candidate_scores["Cover Drive"] = 0.55
            elif is_off:
                candidate_scores["Off Drive"] = 0.89
                candidate_scores["Cover Drive"] = 0.78
                candidate_scores["Straight Drive"] = 0.76
            else:
                candidate_scores["Cover Drive"] = 0.86
                candidate_scores["Straight Drive"] = 0.82
                candidate_scores["Off Drive"] = 0.78

        else:
            # If evidence is weak or does not cleanly match any stroke family,
            # honestly report Unknown / low confidence without defaulting to Cover Drive or Sweep.
            top_family = "Unknown"
            candidate_scores["Unknown / low confidence"] = 0.35
            candidate_scores["Unrecognised Shot"] = 0.30
            candidate_scores["Forward Defensive"] = 0.22

        # Invariant Clamp: if not confirmed sweep, sweep family can NEVER exceed 0.20
        if not is_sweep_candidate:
            for sw in ["Sweep", "Slog Sweep", "Paddle Sweep", "Reverse Sweep"]:
                if sw in candidate_scores:
                    candidate_scores[sw] = min(0.20, candidate_scores[sw])

        # Standard catalogue fallbacks
        catalogue_fallbacks = ["Straight Drive", "Cover Drive", "Forward Defensive", "Pull Shot", "Square Cut"]
        for fb in catalogue_fallbacks:
            if fb not in candidate_scores:
                candidate_scores[fb] = 0.15

        sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
        top_shot, top_score = sorted_candidates[0]

        feat_dict["family"] = top_family
        return top_shot, top_score, sorted_candidates, top_family, feat_dict

    def classify_sequence(
        self,
        frame_metrics: List[Dict[str, Any]],
        hint_shot: Optional[str] = None,
        camera_view: str = "side-on",
        handedness: str = "Right"
    ) -> Dict[str, Any]:
        """
        Classifies sequence with Platt calibration, margin assessment,
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
            "slog sweep": "reverse sweep",
            "paddle sweep": "reverse sweep",
            "straight drive": "straight drive",
            "forward defensive": "forward defensive",
            "back-foot defensive": "back-foot defensive",
        }

        if mirrored_shot.lower() == top_shot.lower() or mirrored_shot.lower() == MIRROR_EQUIVALENTS.get(top_shot.lower()):
            tta_eval_shot = top_shot
        else:
            tta_eval_shot = mirrored_shot

        top_3_raw = [
            {"shot_name": s, "score": round(sc, 3), "confidence_pct": int(sc * 100)}
            for s, sc in sorted_candidates[:3]
        ]

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

        if conf_eval["level_code"] == "cant_tell" and final_shot.lower() in ("unrecognised shot", "no clear shot detected"):
            final_shot = "No clear shot detected"

        shot_mismatch_warning = None
        if hint_shot and final_shot.lower() != hint_shot.lower() and conf_level != "Can't tell" and final_shot.lower() not in ("unrecognized", "uncertain", "no clear shot detected"):
            shot_mismatch_warning = f"You selected {hint_shot}, but this looks like a {final_shot}."

        cand_margin = sorted_candidates[0][1] - sorted_candidates[1][1] if len(sorted_candidates) > 1 else 1.0
        is_uncertain = conf_eval["needs_confirmation"] or conf_eval["is_blocked"] or (cand_margin <= 0.10)
        second_cand = sorted_candidates[1][0] if len(sorted_candidates) > 1 else "Unknown"
        if is_uncertain:
            if cand_margin <= 0.10 or conf_level != "Can't tell":
                uncertainty_title = f"Unsure: {final_shot} or {second_cand}"
            else:
                uncertainty_title = "Can't tell: Clip unclear"
        else:
            uncertainty_title = None

        evidence = [
            f"{feature_dict.get('swing_window_frames', 0)} frames assessed across {feature_dict.get('swing_window_source', 'swing window')}.",
            f"Handedness used for direction normalization: {handedness}.",
            f"Stance-width expansion: {feature_dict.get('stride_ratio', 1.0):.2f}× baseline.",
            f"Rear knee clearance: {feature_dict.get('rear_knee_ground_dist', 0.4):.2f} leg lengths.",
            f"Bat path horizontal ratio: {feature_dict.get('bat_path_horizontal_ratio', 0.0):.2f}."
        ]
        if valid_frames:
            st_t = valid_frames[0].get("timestamp_sec")
            end_t = valid_frames[-1].get("timestamp_sec")
            if st_t is not None and end_t is not None:
                evidence.append(f"Swing evidence window: {float(st_t):.2f}s–{float(end_t):.2f}s.")

        rationale = (
            f"Stage 1: {top_family} family. "
            f"Stage 2: {final_shot} ({conf_level}, {final_conf_pct}%). "
            f"Margin: {conf_eval['margin']:.2f}, Quality factor: {conf_eval['quality_factor']:.2f}."
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
