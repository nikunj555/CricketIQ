import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from backend.app.schemas.analysis import CoachingObservation
from backend.app.services.reference_service import reference_service

logger = logging.getLogger(__name__)

# Phase importance weights for overall technique scoring
PHASE_WEIGHTS = {
    "impact": 0.45,       # Impact is the single most critical moment
    "downswing": 0.20,    # Swing path into the ball
    "stride": 0.15,       # Base setup and weight transfer foundation
    "backlift": 0.10,     # Pre-swing setup and bat position
    "follow_through": 0.10 # Balance and deceleration
}

# Metric importance multipliers within phases
METRIC_WEIGHTS = {
    "lead_knee_angle": 1.25,
    "lead_elbow_angle": 1.15,
    "torso_lean": 1.0,
    "head_over_front_knee_offset": 1.0,
    "rear_knee_angle": 0.85,
    "stance_width_ratio": 0.80,
    "shoulder_tilt": 0.75
}

# Mapping of phase names to canonical keys in reference_shots.json
PHASE_CANONICAL_MAP = {
    "stance": "stance",
    "backlift": "backlift",
    "stride": "stride",
    "downswing": "downswing",
    "downswing / execution": "downswing",
    "impact": "impact",
    "impact window": "impact",
    "follow_through": "follow_through",
    "follow through": "follow_through",
    "follow-through": "follow_through",
    "recovery": "recovery",
    "finish": "recovery"
}

# Metric extraction mapping: reference metric key -> frame_metric key
METRIC_KEY_MAP = {
    "lead_knee_angle": "lead_knee_angle",
    "rear_knee_angle": "rear_knee_angle",
    "lead_elbow_angle": "lead_elbow_angle",
    "torso_lean": "torso_inclination",
    "head_over_front_knee_offset": "head_over_lead_knee_norm",
    "shoulder_tilt": "shoulder_tilt",
    "stance_width_ratio": "stance_width_norm"
}


class FeedbackService:
    """
    Authoritative Biomechanical Coaching Feedback Engine.
    Evaluates measured player kinematics against standardized reference tolerances
    from reference_shots.json across stroke phases.
    """

    @staticmethod
    def _normalize_phase_name(phase_raw: str) -> str:
        p = (phase_raw or "").strip().lower()
        for k, v in PHASE_CANONICAL_MAP.items():
            if k in p:
                return v
        return "impact"

    @classmethod
    def evaluate_technique(
        cls,
        time_series: List[Dict[str, Any]],
        phases: List[Dict[str, Any]],
        summary: Dict[str, Any],
        shot_type: str = "Cover Drive",
        camera_view: str = "side-on"
    ) -> Tuple[float, List[CoachingObservation], List[CoachingObservation]]:
        """
        Compares measured values against reference_shots.json for the specified shot.
        
        Returns:
            overall_score: float (0 - 100)
            top_mistakes: List[CoachingObservation] (max 3 prioritized errors)
            all_observations: List[CoachingObservation] (full list including strengths)
        """
        canonical_shot = reference_service.canonicalize_shot_name(shot_type)
        is_available = reference_service.is_shot_analysis_available(canonical_shot)

        # Handle shots marked "coming soon"
        if not is_available:
            coming_soon_obs = CoachingObservation(
                id="obs_coming_soon",
                title=f"Analysis Calibration In Progress: {canonical_shot}",
                category="Reference Library",
                measurement=f"Shot: {canonical_shot}",
                observed_value="Biomechanical tolerances currently active for Cover Drive, Straight Drive, Pull Shot, Forward Defensive, Sweep",
                reference_benchmark="MCC / Cricket Australia Biomechanical Framework",
                phase="Impact",
                timestamp_sec=0.0,
                frame_index=0,
                severity="consideration",
                why_it_matters=f"CricketIQ enforces strict biomechanical reference integrity. Active analysis for {canonical_shot} is scheduled for an upcoming model calibration.",
                practical_drill="Select one of the 5 calibrated shots to receive full joint-angle deviation analysis.",
                limitation="Shot tolerances not yet published in reference_shots.json",
                measurement_provenance="UNAVAILABLE",
                confidence=1.0
            )
            # Default score based on movement smoothness and tracking success
            smoothness = float(summary.get("movement_smoothness") or 80.0)
            tracking = float(summary.get("tracking_success_rate") or 85.0)
            baseline_score = round(0.5 * smoothness + 0.5 * min(100.0, tracking), 1)
            return baseline_score, [coming_soon_obs], [coming_soon_obs]

        if not time_series:
            return 70.0, [], []

        shot_ref = reference_service.get_shot_reference(canonical_shot) or {}
        shot_drills = shot_ref.get("drills", [])
        shot_cues = shot_ref.get("coaching_cues", [])
        shot_errors = shot_ref.get("common_errors", [])

        # Default drills if reference list is short
        drill_primary = shot_drills[0]["description"] if shot_drills else "Practice shadow swings focusing on balanced head and knee alignment."
        drill_secondary = shot_drills[1]["description"] if len(shot_drills) > 1 else drill_primary

        # 1. Identify representative key frames for each stroke phase
        phase_frames: Dict[str, Dict[str, Any]] = {}
        for p_canon in ["impact", "downswing", "stride", "backlift", "follow_through"]:
            # Match frames assigned to this phase
            candidates = [
                f for f in time_series
                if cls._normalize_phase_name(f.get("phase", "")) == p_canon
            ]
            if candidates:
                if p_canon == "impact":
                    # Representative impact frame: lowest lead knee or highest wrist speed
                    valid_k = [c for c in candidates if c.get("lead_knee_angle") is not None]
                    rep = min(valid_k, key=lambda c: c["lead_knee_angle"]) if valid_k else candidates[len(candidates) // 2]
                elif p_canon == "stride":
                    # Representative stride frame: widest stance
                    valid_s = [c for c in candidates if c.get("stance_width_norm") is not None]
                    rep = max(valid_s, key=lambda c: c["stance_width_norm"]) if valid_s else candidates[len(candidates) // 2]
                else:
                    rep = candidates[len(candidates) // 2]
                phase_frames[p_canon] = rep

        # Fallback for impact frame if not directly matched in phase segments
        if "impact" not in phase_frames:
            imp_idx = int(len(time_series) * 0.55)
            phase_frames["impact"] = time_series[min(len(time_series) - 1, imp_idx)]

        # 2. Evaluate metrics across phases against reference_shots.json
        candidate_mistakes: List[Dict[str, Any]] = []
        strength_observations: List[CoachingObservation] = []
        total_penalty = 0.0

        # Define metrics to check per phase
        eval_plan = [
            ("impact", ["lead_knee_angle", "lead_elbow_angle", "torso_lean", "head_over_front_knee_offset", "rear_knee_angle", "stance_width_ratio"]),
            ("stride", ["stance_width_ratio", "lead_knee_angle"]),
            ("downswing", ["lead_elbow_angle", "torso_lean", "lead_knee_angle"]),
            ("backlift", ["lead_elbow_angle", "torso_lean"]),
            ("follow_through", ["lead_knee_angle", "torso_lean"])
        ]

        for phase_name, metric_keys in eval_plan:
            frame = phase_frames.get(phase_name)
            if not frame:
                continue

            phase_weight = PHASE_WEIGHTS.get(phase_name, 0.10)

            for metric_key in metric_keys:
                validity = "MEASURED"
                if camera_view == "front-on" and "knee" in metric_key:
                    validity = "UNAVAILABLE"
                elif camera_view == "oblique" and "knee" in metric_key:
                    validity = "ESTIMATED"

                # Exclude metrics that are unmeasurable in this view plane from penalties
                if validity == "UNAVAILABLE":
                    continue

                ref_spec = reference_service.get_phase_ideal_range(canonical_shot, phase_name, metric_key)
                if not ref_spec:
                    continue

                frame_field = METRIC_KEY_MAP.get(metric_key, metric_key)
                measured_val = frame.get(frame_field)
                if measured_val is None:
                    continue

                min_ideal = float(ref_spec.get("min", 0.0))
                max_ideal = float(ref_spec.get("max", 0.0))
                ideal_target = float(ref_spec.get("ideal", (min_ideal + max_ideal) / 2.0))
                unit = ref_spec.get("unit", "deg")
                unit_str = "°" if unit == "deg" else ("x torso" if unit == "torso_ratio" else "")

                tolerance_band = max(max_ideal - min_ideal, 4.0)

                # Check if within tolerance
                if min_ideal <= measured_val <= max_ideal:
                    # Within ideal range: Record as technical strength for key metrics
                    if metric_key in ["lead_knee_angle", "lead_elbow_angle"] and phase_name == "impact":
                        metric_label = "Lead Knee Flexion" if "knee" in metric_key else "High Lead Elbow"
                        strength_observations.append(CoachingObservation(
                            id=f"strength_{phase_name}_{metric_key}",
                            title=f"Optimal {metric_label} at Impact",
                            category="Base & Balance" if "knee" in metric_key else "Bat Swing & Arms",
                            measurement=f"{metric_label}: {measured_val:.1f}{unit_str}",
                            observed_value=f"{measured_val:.1f}{unit_str} (within ideal {min_ideal:.0f}°–{max_ideal:.0f}°)",
                            reference_benchmark=f"Benchmark: {min_ideal:.0f}°–{max_ideal:.0f}°",
                            phase="Impact",
                            timestamp_sec=frame.get("timestamp_sec", 0.0),
                            frame_index=frame.get("frame_index"),
                            severity="strength",
                            why_it_matters="Well-calibrated joint angle creates an efficient transfer of momentum through the stroke.",
                            practical_drill="Maintain current execution habit during match-simulation drills.",
                            limitation="Assumes standard camera perspective.",
                            measurement_provenance="MEASURED",
                            confidence=round(frame.get("confidence", 0.88), 2)
                        ))
                    continue

                # Metric deviated from tolerance
                if measured_val < min_ideal:
                    deviation = min_ideal - measured_val
                    direction = "under"
                else:
                    deviation = measured_val - max_ideal
                    direction = "over"

                normalized_dev = deviation / tolerance_band
                metric_weight = METRIC_WEIGHTS.get(metric_key, 1.0)
                severity_score = normalized_dev * phase_weight * metric_weight

                # Weighted penalty for overall score
                # Moderate error adds ~8-12 penalty; severe error adds ~18-26 penalty
                penalty = min(36.0, normalized_dev * 30.0 * phase_weight * metric_weight)
                total_penalty += penalty

                # Generate plain-language coaching statement, biomechanics explanation, and drill
                statement, why_it_matters, drill = cls._compose_coaching_narrative(
                    canonical_shot, phase_name, metric_key, measured_val, min_ideal, max_ideal, direction, unit_str,
                    shot_errors, shot_drills, drill_primary, drill_secondary
                )

                provenance = "MEASURED" if frame.get("confidence", 0.0) >= 0.60 else "ESTIMATED"

                candidate_mistakes.append({
                    "id": f"mistake_{phase_name}_{metric_key}",
                    "phase": phase_name.capitalize(),
                    "metric_key": metric_key,
                    "measured_val": measured_val,
                    "min_ideal": min_ideal,
                    "max_ideal": max_ideal,
                    "unit_str": unit_str,
                    "severity_score": severity_score,
                    "normalized_dev": normalized_dev,
                    "statement": statement,
                    "why_it_matters": why_it_matters,
                    "drill": drill,
                    "timestamp_sec": frame.get("timestamp_sec", 0.0),
                    "frame_index": frame.get("frame_index"),
                    "provenance": provenance,
                    "confidence": round(frame.get("confidence", 0.85), 2)
                })

        # 3. Overall Technique Score (0 - 100)
        # Deduct penalties; apply high floor/ceiling bounds
        overall_score = round(max(20.0, min(97.0, 97.0 - total_penalty)), 1)

        # 4. Rank errors by severity_score descending and pick TOP 3
        candidate_mistakes.sort(key=lambda m: m["severity_score"], reverse=True)

        # Filter duplicates: keep the highest-severity occurrence for each metric
        seen_metrics = set()
        top_mistake_candidates = []
        for m in candidate_mistakes:
            if m["metric_key"] not in seen_metrics:
                seen_metrics.add(m["metric_key"])
                top_mistake_candidates.append(m)
            if len(top_mistake_candidates) == 3:
                break

        top_mistakes: List[CoachingObservation] = []
        for idx, m in enumerate(top_mistake_candidates):
            title = cls._generate_mistake_title(m["phase"], m["metric_key"], m["measured_val"], m["min_ideal"], m["max_ideal"])
            category = cls._map_metric_to_category(m["metric_key"])
            severity_label = "review" if m["normalized_dev"] >= 0.5 else "consideration"
            val_format = f"{m['measured_val']:.1f}{m['unit_str']}" if m["unit_str"] == "°" else f"{m['measured_val']:.2f}{m['unit_str']}"
            ideal_format = f"{m['min_ideal']:.0f}°–{m['max_ideal']:.0f}°" if m["unit_str"] == "°" else f"{m['min_ideal']:.2f}–{m['max_ideal']:.2f}{m['unit_str']}"

            top_mistakes.append(CoachingObservation(
                id=f"top_mistake_{idx + 1}_{m['metric_key']}",
                title=title,
                category=category,
                measurement=f"{cls._format_metric_name(m['metric_key'])}: {val_format}",
                observed_value=f"{val_format} (ideal: {ideal_format})",
                reference_benchmark=f"Benchmark for {canonical_shot}: {ideal_format}",
                phase=m["phase"],
                timestamp_sec=m["timestamp_sec"],
                frame_index=m["frame_index"],
                severity=severity_label,
                why_it_matters=m["why_it_matters"],
                practical_drill=m["drill"],
                limitation="Measured relative to camera perspective plane.",
                measurement_provenance=m["provenance"],
                confidence=m["confidence"]
            ))

        # If no major mistakes detected (technique within tolerance on all parameters)
        if not top_mistakes:
            perfect_cue = shot_cues[0] if shot_cues else "Maintain current balanced head and high elbow alignment."
            top_mistakes.append(CoachingObservation(
                id="obs_solid_technique",
                title="Solid Execution — Balanced Observation Within Ideal Tolerances",
                category="Overall Technique",
                measurement="All measured joint kinematics align within standard coaching bounds",
                observed_value=f"Overall technique rating: {overall_score}/100",
                reference_benchmark=f"Standard {canonical_shot} tolerances met across all evaluated phases",
                phase="Impact",
                timestamp_sec=phase_frames.get("impact", {}).get("timestamp_sec", 0.0),
                frame_index=phase_frames.get("impact", {}).get("frame_index"),
                severity="strength",
                why_it_matters="Balanced alignment throughout the swing plane allows clean sweet-spot contact and maximum shot control.",
                practical_drill=f"Fine-tuning cue: {perfect_cue}",
                limitation="Assumes standard camera perspective.",
                measurement_provenance="MEASURED",
                confidence=0.92
            ))

        all_observations = top_mistakes + strength_observations
        return overall_score, top_mistakes, all_observations

    @classmethod
    def generate_coaching_feedback(
        cls,
        time_series: List[Dict[str, Any]],
        phases: List[Dict[str, Any]],
        summary: Dict[str, Any],
        shot_type: str = "Cover Drive"
    ) -> List[CoachingObservation]:
        """Backward-compatible entry point returning coaching observations list."""
        _, _, all_obs = cls.evaluate_technique(time_series, phases, summary, shot_type=shot_type)
        return all_obs

    @classmethod
    def generate_comparison_table(
        cls,
        time_series: List[Dict[str, Any]],
        shot_type: str = "Cover Drive",
        camera_view: str = "side-on"
    ) -> List[Dict[str, Any]]:
        """
        Generates a structured comparison table for each evaluated phase and metric
        contrasting the user's measured value against reference_shots.json benchmark ranges.
        
        Returns:
            List of dicts: [
                {
                    "phase": str,
                    "phase_label": str,
                    "metric": str,
                    "metric_name": str,
                    "yours": float | None,
                    "yours_formatted": str,
                    "ideal_min": float,
                    "ideal_max": float,
                    "ideal_range": str,
                    "unit": str,
                    "verdict": str ("OK" | "Too Low" | "Too High" | "Unavailable"),
                    "status": str ("ok" | "low" | "high" | "unavailable"),
                    "validity": str ("MEASURED" | "ESTIMATED" | "UNAVAILABLE")
                }, ...
            ]
        """
        canonical_shot = reference_service.canonicalize_shot_name(shot_type)
        shot_ref = reference_service.get_shot_reference(canonical_shot) or {}
        ref_phases = shot_ref.get("phases", {})
        
        phase_frames: Dict[str, Dict[str, Any]] = {}
        for p_canon in ["stance", "backlift", "stride", "downswing", "impact", "follow_through", "recovery"]:
            candidates = [
                f for f in time_series
                if cls._normalize_phase_name(f.get("phase", "")) == p_canon
            ]
            if candidates:
                if p_canon == "impact":
                    valid_k = [c for c in candidates if c.get("lead_knee_angle") is not None]
                    rep = min(valid_k, key=lambda c: c["lead_knee_angle"]) if valid_k else candidates[len(candidates) // 2]
                elif p_canon == "stride":
                    valid_s = [c for c in candidates if c.get("stance_width_norm") is not None]
                    rep = max(valid_s, key=lambda c: c["stance_width_norm"]) if valid_s else candidates[len(candidates) // 2]
                else:
                    rep = candidates[len(candidates) // 2]
                phase_frames[p_canon] = rep

        if "impact" not in phase_frames and time_series:
            imp_idx = int(len(time_series) * 0.55)
            phase_frames["impact"] = time_series[min(len(time_series) - 1, imp_idx)]

        table_rows: List[Dict[str, Any]] = []
        ordered_phases = ["stance", "backlift", "stride", "downswing", "impact", "follow_through", "recovery"]

        for phase_name in ordered_phases:
            phase_specs = ref_phases.get(phase_name, {})
            if not phase_specs:
                continue

            frame = phase_frames.get(phase_name)

            for metric_key, spec in phase_specs.items():
                if metric_key == "keyframe_pose" or not isinstance(spec, dict) or "min" not in spec:
                    continue
                min_ideal = float(spec.get("min", 0.0))
                max_ideal = float(spec.get("max", 0.0))
                unit = spec.get("unit", "deg")
                unit_str = "°" if unit == "deg" else ("x torso" if unit == "torso_ratio" else "")
                ideal_str = f"{min_ideal:.0f}° - {max_ideal:.0f}°" if unit == "deg" else f"{min_ideal:.2f} - {max_ideal:.2f}{unit_str}"

                validity = "MEASURED"
                if camera_view == "front-on" and "knee" in metric_key:
                    validity = "UNAVAILABLE"
                elif camera_view == "oblique" and "knee" in metric_key:
                    validity = "ESTIMATED"

                measured_val = None
                if frame:
                    frame_field = METRIC_KEY_MAP.get(metric_key, metric_key)
                    measured_val = frame.get(frame_field)

                if validity == "UNAVAILABLE" or measured_val is None:
                    verdict = "Unavailable" if validity == "UNAVAILABLE" else "Not Tracked"
                    status = "unavailable"
                    yours_formatted = "N/A"
                elif measured_val < min_ideal:
                    verdict = "Too Low"
                    status = "low"
                    yours_formatted = f"{measured_val:.1f}{unit_str}" if unit == "deg" else f"{measured_val:.2f}{unit_str}"
                elif measured_val > max_ideal:
                    verdict = "Too High"
                    status = "high"
                    yours_formatted = f"{measured_val:.1f}{unit_str}" if unit == "deg" else f"{measured_val:.2f}{unit_str}"
                else:
                    verdict = "OK"
                    status = "ok"
                    yours_formatted = f"{measured_val:.1f}{unit_str}" if unit == "deg" else f"{measured_val:.2f}{unit_str}"

                table_rows.append({
                    "phase": phase_name,
                    "phase_label": phase_name.replace("_", " ").title(),
                    "metric": metric_key,
                    "metric_name": cls._format_metric_name(metric_key),
                    "yours": round(float(measured_val), 1) if measured_val is not None else None,
                    "yours_formatted": yours_formatted,
                    "ideal_min": min_ideal,
                    "ideal_max": max_ideal,
                    "ideal_range": ideal_str,
                    "unit": unit_str,
                    "verdict": verdict,
                    "status": status,
                    "validity": validity
                })

        return table_rows

    @staticmethod
    def _format_metric_name(metric_key: str) -> str:
        names = {
            "lead_knee_angle": "Lead Knee Angle",
            "rear_knee_angle": "Rear Knee Angle",
            "lead_elbow_angle": "Lead Elbow Angle",
            "torso_lean": "Torso Forward Lean",
            "head_over_front_knee_offset": "Head-Over-Lead-Knee Offset",
            "shoulder_tilt": "Shoulder Tilt",
            "stance_width_ratio": "Stance Width Ratio"
        }
        return names.get(metric_key, metric_key.replace("_", " ").title())

    @staticmethod
    def _map_metric_to_category(metric_key: str) -> str:
        if "knee" in metric_key:
            return "Base & Balance"
        if "elbow" in metric_key:
            return "Bat Swing & Arms"
        if "torso" in metric_key or "shoulder" in metric_key:
            return "Posture & Body Line"
        if "head" in metric_key:
            return "Vision & Head Position"
        if "stance" in metric_key:
            return "Footwork & Base"
        return "Kinematics"

    @staticmethod
    def _generate_mistake_title(phase: str, metric_key: str, val: float, min_val: float, max_val: float) -> str:
        if metric_key == "lead_knee_angle":
            return f"Stiff Lead Knee at {phase}" if val > max_val else f"Over-Flexed Lead Knee at {phase}"
        if metric_key == "rear_knee_angle":
            return f"Collapsed Rear Knee at {phase}" if val < min_val else f"Rigid Rear Leg at {phase}"
        if metric_key == "lead_elbow_angle":
            return f"Collapsed Lead Elbow (Chicken Wing) at {phase}" if val < min_val else f"Over-Extended Lead Elbow at {phase}"
        if metric_key == "torso_lean":
            return f"Exaggerated Torso Forward Lean at {phase}" if val > max_val else f"Upright Torso Posture at {phase}"
        if metric_key == "head_over_front_knee_offset":
            return f"Head Falling Outside Front Knee at {phase}" if val > max_val else f"Head Hanging Back at {phase}"
        if metric_key == "stance_width_ratio":
            return f"Over-Striding Base at {phase}" if val > max_val else f"Restricted Stride Width at {phase}"
        return f"{metric_key.replace('_', ' ').title()} Variance at {phase}"

    @classmethod
    def _compose_coaching_narrative(
        cls,
        shot_type: str,
        phase: str,
        metric_key: str,
        val: float,
        min_v: float,
        max_v: float,
        direction: str,
        unit_str: str,
        common_errors: List[Dict[str, str]],
        drills: List[Dict[str, str]],
        drill_primary: str,
        drill_secondary: str
    ) -> Tuple[str, str, str]:
        """Constructs plain-language coaching feedback, biomechanical rationale, and actionable drill."""
        val_str = f"{val:.1f}{unit_str}" if unit_str == "°" else f"{val:.2f}{unit_str}"
        range_str = f"{min_v:.0f}°–{max_v:.0f}°" if unit_str == "°" else f"{min_v:.2f}–{max_v:.2f}{unit_str}"

        # Lead Knee Angle
        if metric_key == "lead_knee_angle":
            if direction == "over":
                stmt = (
                    f"Your front knee was {val_str} at {phase}; ideal for {shot_type} is {range_str}. "
                    "You're playing with a straight front leg, which pushes your weight back and makes you slice or hit in the air."
                )
                why = "A straight front leg raises your center of gravity, preventing your head from getting over the ball and reducing front-foot stability."
                drill = drills[0]["description"] if drills else drill_primary
            else:
                stmt = (
                    f"Your front knee collapsed to {val_str} at {phase}; ideal is {range_str}. "
                    "Over-bending your knee drops your head too low, making it difficult to adjust to late bounce or seam movement."
                )
                why = "Excessive knee bend locks your lower body in place and restricts full pendulum arm extension."
                drill = drills[0]["description"] if drills else drill_primary
            return stmt, why, drill

        # Lead Elbow Angle
        if metric_key == "lead_elbow_angle":
            if direction == "under":
                stmt = (
                    f"Your leading elbow dropped to {val_str} at {phase}; ideal is {range_str}. "
                    "A collapsed lead elbow forces the bat across the line and presents an angled face, risking an edge to slip cordon or gully."
                )
                why = "A dominant high leading elbow guides the bat down a straight vertical plane, presenting the full width of the blade."
                drill = drills[1]["description"] if len(drills) > 1 else drill_secondary
            else:
                stmt = (
                    f"Your lead elbow was locked out at {val_str} at {phase}; ideal is {range_str}. "
                    "Reaching with stiff arms disconnects your swing from your core rotation and reduces sweet-spot precision."
                )
                why = "A slightly relaxed lead elbow allows fine-tuning adjustments right up to the point of impact."
                drill = drills[1]["description"] if len(drills) > 1 else drill_secondary
            return stmt, why, drill

        # Torso Lean
        if metric_key == "torso_lean":
            if direction == "over":
                stmt = (
                    f"Your torso leaned forward at {val_str} at {phase}; ideal is {range_str}. "
                    "Over-leaning pulls your head and shoulders outside off-stump, making you fall over the crease and vulnerable to lbw."
                )
                why = "Spine alignment governs balance; leaning too far forward restricts hip rotation and compromises defensive stability."
                drill = drills[0]["description"] if drills else drill_primary
            else:
                stmt = (
                    f"Your torso remained upright at {val_str} at {phase}; ideal is {range_str}. "
                    "Staying too upright keeps your body mass back, preventing full momentum transfer into the stroke."
                )
                why = "Controlled forward torso tilt transfers body weight through the ball for power and ground control."
                drill = drills[0]["description"] if drills else drill_primary
            return stmt, why, drill

        # Head Over Front Knee
        if metric_key == "head_over_front_knee_offset":
            if direction == "over":
                stmt = (
                    f"Your head was offset by {val:+.2f} torso units outside your front knee; ideal is {range_str}. "
                    "Your head is falling across the off-side line, causing your eyes to tilt and misjudging the ball's line."
                )
                why = "Leading with the head into the line of the delivery ensures stereoscopic depth perception and balanced weight transfer."
                drill = drills[0]["description"] if drills else drill_primary
            else:
                stmt = (
                    f"Your head was hanging back {abs(val):.2f} torso units behind your front knee; ideal is {range_str}. "
                    "Hanging back forces you to reach with hands alone, losing power and balance."
                )
                why = "Getting your chin directly over your front knee at impact keeps the stroke along the ground."
                drill = drills[0]["description"] if drills else drill_primary
            return stmt, why, drill

        # Rear Knee Angle
        if metric_key == "rear_knee_angle":
            if direction == "under":
                stmt = f"Your rear knee collapsed to {val_str}; ideal is {range_str}. Collapsing the back leg drops your hips and saps stroke power."
                why = "A firm rear base provides a stable anchor for hip and torso rotation."
                drill = drills[1]["description"] if len(drills) > 1 else drill_secondary
            else:
                stmt = f"Your back leg was locked stiff at {val_str}; ideal is {range_str}. A rigid back leg restricts fluid weight transfer."
                why = "The rear foot should naturally pivot onto its toe as weight moves onto the front foot."
                drill = drills[1]["description"] if len(drills) > 1 else drill_secondary
            return stmt, why, drill

        # Stance Width Ratio
        if metric_key == "stance_width_ratio":
            if direction == "over":
                stmt = (
                    f"Your stride width was {val_str} at {phase}; ideal is {range_str}. "
                    "Over-striding locks your pelvis, preventing fluid core rotation and leaving you reaching with isolated hands."
                )
                why = "An excessive stride fixes the batter's weight onto the front heel and makes it impossible to adjust to variations in length."
                drill = drills[0]["description"] if drills else drill_primary
            else:
                stmt = (
                    f"Your stride width was only {val_str} at {phase}; ideal is {range_str}. "
                    "A short stride leaves you reaching short of the pitch of the ball, playing away from your body."
                )
                why = "A committed stride positions the front pad and eyes directly adjacent to the ball's bouncing point."
                drill = drills[0]["description"] if drills else drill_primary
            return stmt, why, drill

        # Generic fallback
        stmt = f"{cls._format_metric_name(metric_key)} was {val_str} at {phase}; benchmark range is {range_str}."
        why = "Consistent joint angles in this phase support balance and swing trajectory."
        drill = drill_primary
        return stmt, why, drill


feedback_service = FeedbackService()
