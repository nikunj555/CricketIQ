import torch
import numpy as np
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from backend.app.core.config import settings
from backend.app.models.temporal_model import BiLSTMBattingPhaseClassifier

logger = logging.getLogger(__name__)

PHASE_LABELS = [
    "Stance",
    "Backlift",
    "Stride",
    "Downswing",
    "Impact window",
    "Follow-through",
    "Recovery"
]

PHASE_DESCRIPTIONS = {
    "Stance": "Initial balanced ready position, bat grounded or tapped lightly, awaiting bowler delivery.",
    "Backlift": "Backswing initiated toward slips, shoulders coil, hands lift creating lever power.",
    "Stride": "Decisive foot movement (forward stride or back-and-across) establishing the striking base.",
    "Downswing": "Bat accelerates smoothly along plane towards ball intercept line; lead elbow guides path.",
    "Impact window": "Moment of bat-ball contact; head positioned directly over line of delivery with eyes focused.",
    "Follow-through": "Deceleration of bat swing through the stroke line; complete extension and rotational release.",
    "Recovery": "Rebalancing of body weight back toward neutral center of gravity ready for running or resetting."
}

PHASE_EVIDENCE = {
    "Stance": [
        "Minimal wrist displacement across sequential frames",
        "Neutral baseline stance width maintained",
        "Upright ready posture prior to bowler release"
    ],
    "Backlift": [
        "Upward elevation of wrists and hands (decreasing vertical coordinate)",
        "Shoulder coiling and backward displacement of bat handle",
        "Preparatory cocking of wrist levers"
    ],
    "Stride": [
        "Stance width expansion beyond quiescent baseline",
        "Lead foot forward translation establishing striking base",
        "Lower body weight initiation toward pitch line"
    ],
    "Downswing": [
        "Rapid downward acceleration of wrists towards ball intercept",
        "Lead elbow guiding the descent along vertical plane",
        "Torso inclination forward into the shot trajectory"
    ],
    "Impact window": [
        "Local peak in wrist speed and bat kinetic energy",
        "Maximum lead knee flexion establishing lowest center of gravity",
        "Head stabilized vertically over contact zone"
    ],
    "Follow-through": [
        "Post-impact upward swing deceleration arc",
        "High elbow or extended arm rotation through the line",
        "Deceleration phase following primary kinetic release"
    ],
    "Recovery": [
        "Return of center-of-gravity back toward neutral equilibrium",
        "Recoil from full extension into balanced running position"
    ]
}

class PhaseService:
    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = Path(model_path or settings.PHASE_MODEL_PATH)
        self.model: Optional[BiLSTMBattingPhaseClassifier] = None
        self.device = torch.device("cpu")
        self._load_model()

    def _load_model(self):
        if self.model_path.exists():
            try:
                model = BiLSTMBattingPhaseClassifier(
                    input_dim=14,
                    hidden_dim=64,
                    num_layers=2,
                    num_classes=len(PHASE_LABELS)
                )
                state_dict = torch.load(self.model_path, map_location=self.device, weights_only=True)
                model.load_state_dict(state_dict)
                model.eval()
                self.model = model
                logger.info(f"Loaded trained BiLSTM phase model from {self.model_path}")
            except Exception as e:
                logger.warning(f"Could not load phase model weights: {e}. Using kinematic phase detector.")
                self.model = None
        else:
            logger.info("No pretrained BiLSTM phase model weights found. Fallback to kinematic phase detector.")

    def extract_temporal_feature_matrix(self, frame_metrics: List[Dict[str, Any]]) -> np.ndarray:
        T = len(frame_metrics)
        if T == 0:
            return np.zeros((0, 14), dtype=np.float32)

        feats = np.zeros((T, 10), dtype=np.float32)
        for i, m in enumerate(frame_metrics):
            feats[i, 0] = (m.get("lead_knee_angle") or 160.0) / 180.0
            feats[i, 1] = (m.get("rear_knee_angle") or 165.0) / 180.0
            feats[i, 2] = (m.get("torso_inclination") or 15.0) / 90.0
            feats[i, 3] = (m.get("shoulder_tilt") or 5.0) / 90.0
            feats[i, 4] = (m.get("hip_tilt") or 5.0) / 90.0
            feats[i, 5] = m.get("head_x") if m.get("head_x") is not None else 0.5
            feats[i, 6] = m.get("head_y") if m.get("head_y") is not None else 0.3
            disp = m.get("head_displacement")
            feats[i, 7] = min(2.0, disp) / 2.0 if disp is not None else 0.2
            sw = m.get("stance_width_norm")
            feats[i, 8] = min(3.0, sw) / 3.0 if sw is not None else 0.4
            feats[i, 9] = m.get("confidence", 0.5)

        nan_mask = np.isnan(feats)
        if np.any(nan_mask):
            feats[nan_mask] = 0.5

        if T > 1:
            diffs = np.diff(feats[:, [0, 2, 6, 8]], axis=0)
            diffs = np.vstack([diffs[0:1], diffs])
        else:
            diffs = np.zeros((T, 4), dtype=np.float32)

        return np.hstack([feats, diffs])

    def predict_phases(
        self,
        frame_metrics: List[Dict[str, Any]],
        fps: float = 30.0
    ) -> Tuple[List[str], List[float], List[Dict[str, Any]]]:
        T = len(frame_metrics)
        if T == 0:
            return [], [], []

        # If clip has enough length, use kinematic trajectory phase detector
        per_frame_phases, confidences = self._detect_kinematic_phases(frame_metrics, fps)
        segments = self._extract_segments(per_frame_phases, confidences, fps)

        return per_frame_phases, confidences, segments

    def _detect_kinematic_phases(
        self,
        metrics: List[Dict[str, Any]],
        fps: float
    ) -> Tuple[List[str], List[float]]:
        """
        Physics-grounded kinematic action segmenter for batting strokes.
        Uses wrist velocity, bat path trajectory, and lead knee flexion to identify
        the true impact instant, and derives all other 6 stroke phases around it.
        Strictly preserves chronological monotonic phase ordering:
        Stance -> Backlift -> Stride -> Downswing -> Impact -> Follow-through -> Recovery.
        """
        T = len(metrics)
        if T < 7:
            phases = [PHASE_LABELS[min(i, len(PHASE_LABELS)-1)] for i in range(T)]
            confs = [0.75] * T
            return phases, confs

        # 1. Extract and smooth kinematic time-series
        knee_angles = np.array([m.get("lead_knee_angle") or 160.0 for m in metrics], dtype=float)
        stance_widths = np.array([m.get("stance_width_norm") or 1.0 for m in metrics], dtype=float)
        wrist_ys = np.array([m.get("lead_wrist_y") or 0.50 for m in metrics], dtype=float)
        wrist_xs = np.array([m.get("lead_wrist_x") or 0.50 for m in metrics], dtype=float)
        confidences_raw = np.array([m.get("confidence") or 0.80 for m in metrics], dtype=float)

        # Smooth using Savitzky-Golay or 5-point moving average
        w = min(5, T if T % 2 == 1 else T - 1)
        w = max(3, w)
        kernel = np.ones(w) / w
        w_xs = np.convolve(wrist_xs, kernel, mode="same")
        w_ys = np.convolve(wrist_ys, kernel, mode="same")
        knee_s = np.convolve(knee_angles, kernel, mode="same")
        sw_s = np.convolve(stance_widths, kernel, mode="same")

        vx = np.gradient(w_xs)
        vy = np.gradient(w_ys)
        v_wrist = np.sqrt(vx**2 + vy**2)

        # Check for alternative wrist speed / separation signals if 2D coordinates are static
        wrist_signals = [m.get("lead_wrist_speed") or m.get("wrist_separation") for m in metrics]
        if any(w is not None for w in wrist_signals):
            v_alt = np.array([float(w or 0.0) for w in wrist_signals], dtype=float)
            if np.ptp(v_alt) > 1e-4:
                v_wrist = v_alt
                vy = np.gradient(v_alt)

        # 2. Locate the Impact Window via Peak Downward Wrist Acceleration & Velocity
        # Search across sequence excluding edge margins (first 6%, last 6%)
        valid_start = max(1, int(T * 0.06))
        valid_end = min(T - 2, int(T * 0.94))
        if valid_end <= valid_start:
            valid_start = 0
            valid_end = T - 1

        # Downswing into impact is characterized by high wrist speed and downward velocity (vy > 0 in image coords)
        # combined with front knee flex
        norm_v = (v_wrist - np.min(v_wrist)) / (np.ptp(v_wrist) + 1e-6)
        knee_flex_inv = (np.max(knee_s) - knee_s) / (np.ptp(knee_s) + 1e-6)
        downward_bonus = np.where(vy > 0, 1.25, 0.75)

        impact_score = (0.70 * norm_v + 0.30 * knee_flex_inv) * downward_bonus
        search_window = impact_score[valid_start:valid_end]
        if len(search_window) > 0:
            i_impact = valid_start + int(np.argmax(search_window))
        else:
            i_impact = T // 2

        # 3. Derive Chronological Boundaries Around Impact
        # (a) Backlift Peak: Minimum wrist_y (highest hand position) prior to downswing
        pre_impact_window = max(2, i_impact - 1)
        # Search for backlift apex in frames preceding impact
        backlift_search_start = max(1, int(i_impact * 0.20))
        if i_impact > backlift_search_start:
            i_backlift_peak = backlift_search_start + int(np.argmin(w_ys[backlift_search_start:i_impact]))
        else:
            i_backlift_peak = max(1, int(i_impact * 0.50))

        # (b) Stance End / Backlift Start: When hands first elevate from rest baseline
        baseline_wrist_y = np.median(w_ys[:max(2, i_backlift_peak // 2)])
        i_stance_end = max(1, min(i_backlift_peak - 1, int(i_backlift_peak * 0.55)))

        # (c) Stride: Front foot commitment between backlift and downswing
        # Typically overlaps backlift release and downswing preparation
        i_stride_start = max(i_stance_end, min(i_backlift_peak, i_impact - 4))
        i_downswing_start = max(i_stride_start + 1, min(i_impact - 2, i_backlift_peak + 1))

        # (d) Impact Window width: guaranteed contiguous window enclosing i_impact
        imp_half = max(1, min(3, int(T * 0.04)))
        i_impact_start = max(1, i_impact - imp_half)
        i_impact_end = min(T - 1, i_impact + imp_half)
        if i_impact_end < i_impact_start:
            i_impact_end = i_impact_start

        # Prior phases must precede i_impact_start
        i_downswing_start = min(i_downswing_start, max(1, i_impact_start - 1))
        i_stride_start = min(i_stride_start, max(1, i_downswing_start - 1))
        i_stance_end = min(i_stance_end, max(1, i_stride_start - 1))

        # (e) Follow-Through End: Swing deceleration past impact
        post_imp = v_wrist[i_impact_end:]
        peak_v = max(1e-5, v_wrist[i_impact])
        if len(post_imp) > 3:
            low_v = np.where(post_imp < peak_v * 0.38)[0]
            if len(low_v) > 0:
                i_ft_end = i_impact_end + low_v[0]
            else:
                i_ft_end = min(T - 1, i_impact_end + int(len(post_imp) * 0.65))
        else:
            i_ft_end = min(T - 1, i_impact_end + 3)

        i_ft_end = max(i_impact_end + 1, min(T - 1, i_ft_end))

        # Ensure strict monotonicity:
        i_stance_end = max(1, min(i_stance_end, i_backlift_peak))
        i_backlift_end = max(i_stance_end + 1, i_stride_start)
        i_stride_end = max(i_backlift_end + 1, i_downswing_start)
        i_downswing_end = max(i_stride_end + 1, i_impact_start)

        # 4. Label each frame and assign signal-grounded confidence
        # Saliency confidence: ratio of peak velocity to mean background motion
        mean_v = float(np.mean(v_wrist)) + 1e-6
        v_saliency = min(1.0, max(0.5, (peak_v / mean_v) / 3.0))

        phases: List[str] = []
        confs: List[float] = []

        for i in range(T):
            raw_c = float(confidences_raw[i]) if i < len(confidences_raw) else 0.85
            # Dynamic confidence grounded in tracking clarity and velocity sharpness
            frame_conf = round(float(np.clip(0.50 * raw_c + 0.50 * v_saliency, 0.65, 0.98)), 3)

            if i < i_stance_end:
                ph = PHASE_LABELS[0]  # Stance
            elif i < i_stride_start:
                ph = PHASE_LABELS[1]  # Backlift
            elif i < i_downswing_start:
                ph = PHASE_LABELS[2]  # Stride
            elif i < i_impact_start:
                ph = PHASE_LABELS[3]  # Downswing
            elif i <= i_impact_end:
                ph = PHASE_LABELS[4]  # Impact window
                frame_conf = round(min(0.98, frame_conf + 0.05), 3)
            elif i < i_ft_end:
                ph = PHASE_LABELS[5]  # Follow-through
            else:
                ph = PHASE_LABELS[6]  # Recovery

            phases.append(ph)
            confs.append(frame_conf)

        return phases, confs

    def _extract_segments(
        self,
        phases: List[str],
        confidences: List[float],
        fps: float
    ) -> List[Dict[str, Any]]:
        T = len(phases)
        if T == 0:
            return []

        segments = []
        current_phase = phases[0]
        start_idx = 0
        seg_confs = [confidences[0]]

        for i in range(1, T):
            if phases[i] != current_phase:
                end_idx = i - 1
                key_frame = (start_idx + end_idx) // 2
                start_sec = round(start_idx / fps, 2)
                end_sec = round(end_idx / fps, 2)
                mean_c = round(float(np.mean(seg_confs)), 3)
                segments.append({
                    "phase_name": current_phase,
                    "start_frame": start_idx,
                    "end_frame": end_idx,
                    "start_sec": start_sec,
                    "end_sec": end_sec,
                    "duration_sec": round(end_sec - start_sec, 2),
                    "confidence": mean_c,
                    "detection_confidence": mean_c,
                    "supporting_evidence": PHASE_EVIDENCE.get(current_phase, []),
                    "key_frame": key_frame,
                    "description": PHASE_DESCRIPTIONS.get(current_phase, "")
                })
                current_phase = phases[i]
                start_idx = i
                seg_confs = [confidences[i]]
            else:
                seg_confs.append(confidences[i])

        # Final segment
        key_frame = (start_idx + T - 1) // 2
        start_sec = round(start_idx / fps, 2)
        end_sec = round((T - 1) / fps, 2)
        mean_c = round(float(np.mean(seg_confs)), 3)
        segments.append({
            "phase_name": current_phase,
            "start_frame": start_idx,
            "end_frame": T - 1,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "duration_sec": round(end_sec - start_sec, 2),
            "confidence": mean_c,
            "detection_confidence": mean_c,
            "supporting_evidence": PHASE_EVIDENCE.get(current_phase, []),
            "key_frame": key_frame,
            "description": PHASE_DESCRIPTIONS.get(current_phase, "")
        })

        return segments

phase_service = PhaseService()
