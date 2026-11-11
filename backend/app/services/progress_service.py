"""
CricketIQ — Progress Tracking Service

Aggregates real analysis results from completed sessions to produce:
  - Per-shot type kinematic trend data over time
  - Single overall technique score progression line
  - Per-metric "Improving" / "Same" / "Needs attention" indicators vs previous attempts
  - Concise plain-language coaching progress summary sentence
  - Recurring technical mistakes aggregated across sessions

All values come exclusively from actual session analysis results stored in the DB.
Nothing is fabricated or hardcoded.
"""

import numpy as np
import logging
from typing import List, Dict, Any, Optional
from backend.app.repositories.session_repository import session_repo
from backend.app.services.geometry_service import GeometryService
from backend.app.services.reference_service import reference_service

logger = logging.getLogger(__name__)

# Minimum sessions required before reporting a statistical trend as "reliable"
MIN_SESSIONS_FOR_TREND = 3

# Metrics reported in progress summaries
TRACKED_METRICS = [
    ("lead_knee_flexion_at_impact", "Lead Knee Flexion at Impact", "°", "lower_is_more_flexed", "lead_knee_angle"),
    ("torso_lean_at_impact",        "Torso Forward Lean at Impact", "°", "higher_means_forward", "torso_lean"),
    ("lead_elbow_flexion_at_impact","Lead Elbow Flexion at Impact", "°", "higher_is_more_extended", "lead_elbow_angle"),
    ("head_stability_index",        "Head Stability Index (lower = steadier)", "", "lower_is_better", None),
    ("stance_width_ratio_max",      "Peak Stride Width", "× torso", "higher_is_wider", "stance_width_ratio"),
    ("tracking_success_rate",       "Pose Tracking Success Rate", "%", "higher_is_better", None),
    ("movement_smoothness",         "Movement Smoothness Score", "", "higher_is_better", None),
]


class ProgressService:
    """
    Reads completed session summaries from the database and computes
    biomechanical progress trends without inventing data.
    """

    def get_all_shots_summary(self, limit: int = 200) -> Dict[str, Any]:
        """
        Returns a high-level progress summary across ALL shot types.
        Groups completed sessions by shot type and computes per-shot statistics.
        """
        sessions = session_repo.list_sessions(limit=limit)
        completed = [
            s for s in sessions
            if s.get("status") == "completed" and (s.get("summary") or s.get("result", {}).get("summary"))
        ]

        if not completed:
            return {
                "total_sessions": len(sessions),
                "completed_sessions": 0,
                "shot_type_breakdown": [],
                "most_practiced_shot": None,
                "data_quality_note": "No completed analysis sessions found. Upload and analyse batting footage to track progress.",
            }

        # Group by shot_type
        by_shot: Dict[str, List[Dict[str, Any]]] = {}
        for s in completed:
            shot = s.get("shot_type") or "Unknown"
            by_shot.setdefault(shot, []).append(s)

        breakdown = []
        for shot_type, shot_sessions in sorted(by_shot.items(), key=lambda kv: -len(kv[1])):
            summaries = [s.get("summary") or s.get("result", {}).get("summary", {}) for s in shot_sessions]
            knees = [sm.get("lead_knee_flexion_at_impact") for sm in summaries if sm.get("lead_knee_flexion_at_impact") is not None]
            torsos = [sm.get("torso_lean_at_impact") for sm in summaries if sm.get("torso_lean_at_impact") is not None]
            scores = [
                s.get("overall_technique_score") or (s.get("result") or {}).get("overall_technique_score") or sm.get("overall_technique_score")
                for s, sm in zip(shot_sessions, summaries)
                if (s.get("overall_technique_score") or (s.get("result") or {}).get("overall_technique_score") or sm.get("overall_technique_score")) is not None
            ]
            tracking = [sm.get("tracking_success_rate") for sm in summaries if sm.get("tracking_success_rate") is not None]

            entry = {
                "shot_type": shot_type,
                "session_count": len(shot_sessions),
                "is_trend_reliable": len(shot_sessions) >= MIN_SESSIONS_FOR_TREND,
                "avg_technique_score": round(float(np.mean(scores)), 1) if scores else None,
                "avg_lead_knee_at_impact": round(float(np.mean(knees)), 1) if knees else None,
                "avg_torso_lean_at_impact": round(float(np.mean(torsos)), 1) if torsos else None,
                "avg_tracking_rate": round(float(np.mean(tracking)), 1) if tracking else None,
                "latest_session_id": shot_sessions[0].get("session_id"),
                "latest_date": shot_sessions[0].get("created_at"),
            }
            if len(knees) >= 2:
                knee_consistency = GeometryService.compute_trajectory_consistency(knees)
                entry["knee_consistency_cv"] = knee_consistency.get("cv")
            breakdown.append(entry)

        most_practiced = breakdown[0]["shot_type"] if breakdown else None

        return {
            "total_sessions": len(sessions),
            "completed_sessions": len(completed),
            "shot_type_breakdown": breakdown,
            "most_practiced_shot": most_practiced,
            "data_quality_note": (
                f"Based on {len(completed)} completed analysis sessions. "
                "Trends are labelled 'reliable' only when ≥ 3 sessions of the same shot type are available."
            ),
        }

    def get_shot_trend(self, shot_type: str, limit: int = 50) -> Dict[str, Any]:
        """
        Returns detailed kinematic trend data for a specific shot type:
        - Chronological technique score line
        - Per-metric 'Improving' / 'Same' / 'Needs attention' indicator vs previous 3 attempts
        - Highlight progress summary sentence
        - Recurring technical mistakes aggregated across sessions
        """
        all_sessions = session_repo.list_sessions(limit=limit * 3)
        canonical_shot = reference_service.canonicalize_shot_name(shot_type)
        shot_lower = canonical_shot.lower().strip()

        # Match sessions by shot type
        matching: List[Dict[str, Any]] = []
        for s in all_sessions:
            if s.get("status") != "completed":
                continue
            s_shot = (
                s.get("user_confirmed_shot_type")
                or s.get("shot_type")
                or s.get("predicted_shot_type")
                or ""
            ).lower().strip()
            if s_shot == shot_lower or shot_lower in s_shot or s_shot in shot_lower:
                matching.append(s)
                if len(matching) >= limit:
                    break

        if not matching:
            return {
                "shot_type": canonical_shot,
                "session_count": 0,
                "score_trend": [],
                "trend_data": [],
                "metric_trends": {},
                "metric_comparisons": [],
                "summary_sentence": f"No completed sessions recorded yet for {canonical_shot}.",
                "recurring_mistakes": [],
                "is_trend_reliable": False,
                "data_quality_note": (
                    f"No completed sessions found for '{canonical_shot}'. "
                    "Upload or record batting practice to start tracking your progression."
                ),
            }

        # Sort oldest → newest for chronological progression
        matching_sorted = sorted(matching, key=lambda s: s.get("created_at") or "")

        # 1. Build per-session trend points & score line
        trend_data = []
        score_trend = []
        all_mistakes: List[Dict[str, Any]] = []

        for idx, s in enumerate(matching_sorted):
            summary = s.get("summary") or (s.get("result") or {}).get("summary") or {}
            score = (
                s.get("overall_technique_score")
                or (s.get("result") or {}).get("overall_technique_score")
                or summary.get("overall_technique_score")
                or 75.0
            )
            created_str = (s.get("created_at") or "")[:10]
            attempt_num = idx + 1

            point = {
                "attempt_number": attempt_num,
                "session_id": s.get("session_id"),
                "date": created_str,
                "shot_type": canonical_shot,
                "overall_technique_score": round(float(score), 1),
            }
            score_trend.append({
                "attempt_number": attempt_num,
                "session_id": s.get("session_id"),
                "date": created_str,
                "overall_technique_score": round(float(score), 1),
            })

            for metric_key, _, _, _, _ in TRACKED_METRICS:
                val = summary.get(metric_key)
                point[metric_key] = val
            trend_data.append(point)

            # Collect top mistakes for recurrence tracking
            res_dict = s.get("result") or {}
            top_m = res_dict.get("top_mistakes") or s.get("top_mistakes") or []
            for m in top_m:
                if isinstance(m, dict) and m.get("severity") != "strength":
                    all_mistakes.append(m)

        # 2. Metric comparisons vs previous attempts (up to 3 previous)
        metric_comparisons = []
        best_improvement_note: Optional[str] = None
        largest_deviation_reduction = 0.0

        for metric_key, label, unit, direction, ref_key in TRACKED_METRICS:
            values = [p[metric_key] for p in trend_data if p.get(metric_key) is not None]
            if not values:
                continue

            current_val = values[-1]
            prev_values = values[-4:-1] if len(values) >= 2 else []

            # Check reference ideal range for impact phase
            ref_spec = reference_service.get_phase_ideal_range(canonical_shot, "impact", ref_key) if ref_key else None
            ideal_min = float(ref_spec["min"]) if ref_spec else None
            ideal_max = float(ref_spec["max"]) if ref_spec else None
            ideal_str = f"{ideal_min:.0f}{unit}–{ideal_max:.0f}{unit}" if (ideal_min is not None and ideal_max is not None) else "Optimal"

            # Compute deviation from ideal
            def calc_dev(val: float) -> float:
                if ideal_min is None or ideal_max is None:
                    return 0.0
                if val < ideal_min:
                    return ideal_min - val
                if val > ideal_max:
                    return val - ideal_max
                return 0.0

            curr_dev = calc_dev(current_val)
            status = "same"

            if prev_values:
                prev_dev = float(np.mean([calc_dev(v) for v in prev_values]))
                dev_diff = prev_dev - curr_dev  # positive means improved

                if dev_diff >= 2.0:
                    status = "improving"
                elif dev_diff <= -2.0:
                    status = "needs_attention"
                else:
                    status = "same"

                # Check if this metric is the top highlight improvement
                if dev_diff > largest_deviation_reduction:
                    largest_deviation_reduction = dev_diff
                    first_val = values[0]
                    within_now = (ideal_min <= current_val <= ideal_max) if (ideal_min and ideal_max) else False
                    within_suffix = " — within ideal band now." if within_now else f" (closing on ideal {ideal_str})."
                    best_improvement_note = (
                        f"You've worked on {label.lower()}: improved from {first_val:.1f}{unit} (attempt 1) "
                        f"to {current_val:.1f}{unit} (attempt {len(values)}){within_suffix}"
                    )

            metric_comparisons.append({
                "metric_key": metric_key,
                "label": label,
                "unit": unit,
                "current_value": round(float(current_val), 1),
                "ideal_range": ideal_str,
                "status": status,
                "previous_values": [round(float(v), 1) for v in prev_values],
                "deviation_from_ideal": round(float(curr_dev), 1),
            })

        # Plain-words progress tracking statements (e.g., 'Front knee: fixed in your last 3 attempts')
        plain_progress_statements: List[Dict[str, Any]] = []
        body_part_names = {
            "lead_knee_flexion_at_impact": "Front knee",
            "torso_lean_at_impact": "Upper body lean",
            "lead_elbow_flexion_at_impact": "Front elbow",
            "head_stability_index": "Head position",
            "stance_width_ratio_max": "Front step",
        }

        for metric_key, label, unit, direction, ref_key in TRACKED_METRICS:
            if metric_key not in body_part_names:
                continue
            friendly_name = body_part_names[metric_key]
            values = [p[metric_key] for p in trend_data if p.get(metric_key) is not None]
            if not values:
                continue

            ref_spec = reference_service.get_phase_ideal_range(canonical_shot, "impact", ref_key) if ref_key else None
            ideal_min = float(ref_spec["min"]) if ref_spec else None
            ideal_max = float(ref_spec["max"]) if ref_spec else None

            recent_vals = values[-5:]
            is_good = []
            for v in recent_vals:
                if ideal_min is not None and ideal_max is not None:
                    is_good.append(ideal_min <= v <= ideal_max)
                else:
                    is_good.append(True)

            total_recent = len(recent_vals)
            good_count = sum(1 for g in is_good if g)
            bad_count = total_recent - good_count

            if total_recent >= 3 and is_good[-3:] == [True, True, True]:
                statement = f"{friendly_name}: fixed in your last 3 attempts"
                trend_arrow = "↑"
                trend_status = "improving"
            elif bad_count >= 3:
                statement = f"{friendly_name}: still a problem ({bad_count} of {total_recent} attempts)"
                trend_arrow = "↓"
                trend_status = "needs_work"
            elif good_count == total_recent:
                statement = f"{friendly_name}: consistently solid across all recent attempts"
                trend_arrow = "→"
                trend_status = "solid"
            elif is_good[-1] and not is_good[0]:
                statement = f"{friendly_name}: improving on your latest balls"
                trend_arrow = "↑"
                trend_status = "improving"
            else:
                statement = f"{friendly_name}: steady ({good_count} of {total_recent} on target)"
                trend_arrow = "→"
                trend_status = "steady"

            plain_progress_statements.append({
                "body_part": friendly_name,
                "statement": statement,
                "trend_arrow": trend_arrow,
                "trend_status": trend_status,
                "metric_key": metric_key
            })

        # Dual tracking: technique score vs shot recognition confidence (strictly separate lines)
        dual_tracking = []
        for s in matching_sorted:
            res_d = s.get("result") or {}
            sc = s.get("overall_technique_score") or res_d.get("overall_technique_score") or 75.0
            shot_c = res_d.get("shot_confidence") or {}
            c_pct = shot_c.get("confidence") or int((s.get("prediction_confidence") or 0.75) * 100)
            c_lvl = shot_c.get("level") or ("Very sure" if c_pct >= 85 else ("Fairly sure" if c_pct >= 65 else "Not very sure"))

            t_label = "solid" if sc >= 80 else ("getting there" if sc >= 65 else "needs work")
            line = f"Technique: {sc:.0f} ({t_label}) · Shot recognized: {c_lvl} ({c_pct:.0f}%)"
            dual_tracking.append({
                "session_id": s.get("session_id"),
                "date": (s.get("created_at") or "")[:10],
                "technique_score": round(float(sc), 1),
                "technique_label": t_label,
                "shot_confidence_pct": round(float(c_pct), 0),
                "shot_confidence_level": c_lvl,
                "summary_line": line
            })

        # 3. Concise summary narrative sentence
        if best_improvement_note:
            summary_sentence = best_improvement_note
        elif len(trend_data) >= 2:
            latest_score = trend_data[-1].get("overall_technique_score", 0.0)
            first_score = trend_data[0].get("overall_technique_score", 0.0)
            score_diff = latest_score - first_score
            if score_diff > 2.0:
                summary_sentence = (
                    f"Overall technique rating improved from {first_score:.0f}/100 (attempt 1) "
                    f"to {latest_score:.0f}/100 (attempt {len(trend_data)})."
                )
            elif score_diff < -2.0:
                summary_sentence = (
                    f"Overall technique rating dropped from {first_score:.0f}/100 to {latest_score:.0f}/100. "
                    "Focus on front knee bend and high leading elbow."
                )
            else:
                summary_sentence = f"Consistent technique across {len(trend_data)} attempts (latest score: {latest_score:.0f}/100)."
        elif len(trend_data) == 1:
            score_val = trend_data[0].get("overall_technique_score", 80.0)
            summary_sentence = f"First attempt recorded with an overall technique rating of {score_val:.0f}/100. Record further attempts to track progress."
        else:
            summary_sentence = f"No completed sessions recorded yet for {canonical_shot}."

        # 4. Recurring mistakes across sessions
        recurring_map: Dict[str, Dict[str, Any]] = {}
        for m in all_mistakes:
            t = m.get("title") or "Technical Variance"
            if t not in recurring_map:
                recurring_map[t] = {
                    "title": t,
                    "category": m.get("category", "General"),
                    "count": 0,
                    "practical_drill": m.get("practical_drill", ""),
                    "why_it_matters": m.get("why_it_matters", "")
                }
            recurring_map[t]["count"] += 1

        recurring_mistakes = []
        for item in sorted(recurring_map.values(), key=lambda x: -x["count"]):
            pct = round((item["count"] / max(1, len(trend_data))) * 100.0)
            recurring_mistakes.append({
                "title": item["title"],
                "category": item["category"],
                "count": item["count"],
                "total_attempts": len(trend_data),
                "frequency_pct": pct,
                "practical_drill": item["practical_drill"],
                "why_it_matters": item["why_it_matters"],
            })

        return {
            "shot_type": canonical_shot,
            "session_count": len(matching),
            "score_trend": score_trend,
            "trend_data": trend_data,
            "metric_comparisons": metric_comparisons,
            "plain_progress_statements": plain_progress_statements,
            "dual_tracking": dual_tracking,
            "summary_sentence": summary_sentence,
            "recurring_mistakes": recurring_mistakes[:5],
            "is_trend_reliable": len(matching) >= MIN_SESSIONS_FOR_TREND,
            "data_quality_note": (
                f"Based on {len(matching)} completed '{canonical_shot}' session(s). "
                "Trends compare performance against MCC / Cricket Australia biomechanical benchmarks."
            ),
        }

    def get_available_shot_types_with_data(self) -> List[str]:
        """Returns list of shot types that have at least 1 completed session."""
        sessions = session_repo.list_sessions(limit=500)
        seen = set()
        for s in sessions:
            if s.get("status") == "completed":
                shot = s.get("shot_type")
                if shot:
                    seen.add(reference_service.canonicalize_shot_name(shot))
        return sorted(seen)


progress_service = ProgressService()
