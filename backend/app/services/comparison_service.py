import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from backend.app.data.reference_catalogue import AUTHENTIC_REFERENCE_REGISTRY, get_reference_for_shot, get_reference_by_id
from backend.app.services.dtw_service import dtw_service
from backend.app.schemas.comparison import ComparisonResult, KeyMomentDifference, AlignedFramePair, ReferenceShotMeta
from backend.app.data.shot_catalogue import resolve_shot_category

class ComparisonService:
    def list_reference_shots(self) -> List[ReferenceShotMeta]:
        """Returns metadata for all available reference benchmarks."""
        results = []
        for ref in AUTHENTIC_REFERENCE_REGISTRY:
            results.append(ReferenceShotMeta(
                id=ref["id"],
                title=f"{ref['shot_name']} — {ref['player_name']} ({ref['source'].split('/')[0].strip()})",
                shot_type=ref["shot_name"],
                handedness="Right",
                camera_angle=ref.get("camera_view", "Side View"),
                description=ref["description"],
                source_label=ref["source"],
                total_frames=ref.get("total_frames", 60),
                fps=ref.get("fps", 30.0),
                key_metrics=ref.get("key_metrics", {})
            ))
        return results

    def get_reference_by_id(self, ref_id: str) -> Optional[Dict[str, Any]]:
        for ref in AUTHENTIC_REFERENCE_REGISTRY:
            if ref["id"] == ref_id or (ref_id == "ref_cover_drive_kohli" and ref["id"] == "ref_cover_drive_master"):
                return {**ref, "id": ref_id}
        return None

    def find_best_reference_for_shot(self, shot_type: str) -> Optional[Dict[str, Any]]:
        """Finds matching reference for a shot type if one exists."""
        ref = get_reference_for_shot(shot_type)
        if ref:
            return ref

        shot_lower = shot_type.lower()
        for r in AUTHENTIC_REFERENCE_REGISTRY:
            if r["shot_name"].lower() in shot_lower or shot_lower in r["shot_name"].lower():
                return r
        return None

    def _extract_comparison_matrix(self, time_series: List[Dict[str, Any]]) -> np.ndarray:
        """Extracts normalized 5D kinematic matrix for DTW alignment."""
        T = len(time_series)
        mat = np.zeros((T, 5), dtype=np.float64)
        for i, f in enumerate(time_series):
            mat[i, 0] = (f.get("lead_knee_angle") or 160.0) / 180.0
            mat[i, 1] = (f.get("rear_knee_angle") or 165.0) / 180.0
            mat[i, 2] = (f.get("torso_inclination") or 15.0) / 90.0
            mat[i, 3] = min(3.0, (f.get("stance_width_norm") or 1.2)) / 3.0
            mat[i, 4] = f.get("head_y") if f.get("head_y") is not None else 0.3
        return mat

    def compare_session_with_reference(
        self,
        query_session_data: Dict[str, Any],
        reference_id: Optional[str] = None,
        custom_reference: Optional[Dict[str, Any]] = None
    ) -> ComparisonResult:
        query_result = query_session_data.get("result") or {}
        query_time_series = query_result.get("time_series", [])
        shot_type = query_session_data.get("user_confirmed_shot_type") or query_session_data.get("predicted_shot_type") or query_session_data.get("shot_type") or "Cover Drive"
        session_id = query_session_data.get("session_id", "unknown")

        if custom_reference:
            reference = custom_reference
        elif reference_id and reference_id != "none":
            reference = self.get_reference_by_id(reference_id)
            if not reference:
                reference = self.find_best_reference_for_shot(shot_type)
        else:
            reference = self.find_best_reference_for_shot(shot_type)

        if not reference:
            return ComparisonResult(
                query_session_id=session_id,
                reference_id="none",
                reference_title="No Benchmark Registered",
                shot_type=shot_type,
                alignment_method="DTW (Dynamic Time Warping)",
                normalized_similarity_score=0.0,
                raw_dtw_distance=0.0,
                warping_path_length=0,
                key_differences=[],
                aligned_time_series=[],
                compatibility_warning=f"No verified textbook benchmark is currently registered in the catalogue for '{shot_type}'. CricketIQ strictly refuses to compare unrelated shots against arbitrary templates to avoid deceptive technique scores. You can compare this attempt against another practice session of '{shot_type}'.",
                methodology_note="Benchmarked reference comparison requires verified kinematic footage for the specific shot family."
            )

        ref_time_series = reference.get("data", {}).get("time_series", [])

        # If query has no time series, return safe fallback
        if not query_time_series or not ref_time_series:
            return ComparisonResult(
                query_session_id=session_id,
                reference_id=reference.get("id", "ref_custom"),
                reference_title=reference.get("title", reference.get("shot_name", "Reference")),
                shot_type=shot_type,
                alignment_method="DTW (Dynamic Time Warping)",
                normalized_similarity_score=0.0,
                raw_dtw_distance=999.0,
                warping_path_length=0,
                key_differences=[],
                aligned_time_series=[],
                compatibility_warning="Session contains insufficient extracted pose landmarks for temporal alignment.",
                methodology_note="Pose sequences could not be aligned due to missing landmarks."
            )

        # Extract normalized kinematic matrices
        seq_query = self._extract_comparison_matrix(query_time_series)
        seq_ref = self._extract_comparison_matrix(ref_time_series)

        # Execute Dynamic Time Warping
        dtw_dist, warping_path, sim_score = dtw_service.compute_dtw(seq_query, seq_ref)

        # Construct aligned frame pairs along the warping path (sampled to max 80 points)
        step = max(1, len(warping_path) // 60)
        sampled_path = warping_path[::step]
        aligned_pairs: List[AlignedFramePair] = []

        for q_idx, r_idx in sampled_path:
            q_frame = query_time_series[q_idx]
            r_frame = ref_time_series[r_idx]
            dist = float(np.linalg.norm(seq_query[q_idx] - seq_ref[r_idx]))

            aligned_pairs.append(AlignedFramePair(
                query_frame=q_idx,
                reference_frame=r_idx,
                query_time_sec=q_frame.get("timestamp_sec", 0.0),
                reference_time_sec=r_frame.get("timestamp_sec", 0.0),
                query_knee_angle=q_frame.get("lead_knee_angle"),
                ref_knee_angle=r_frame.get("lead_knee_angle"),
                query_torso_lean=q_frame.get("torso_inclination"),
                ref_torso_lean=r_frame.get("torso_inclination"),
                query_head_y=q_frame.get("head_y"),
                ref_head_y=r_frame.get("head_y"),
                pose_distance=round(dist, 3)
            ))

        # Check compatibility warning
        ref_shot = reference.get("shot_name") or reference.get("shot_type") or "Standard"
        query_cat = resolve_shot_category(shot_type)
        ref_cat = resolve_shot_category(ref_shot)

        compatibility_warning = None
        if query_cat != ref_cat and shot_type.lower() != "unknown":
            compatibility_warning = (
                f"Biomechanical Category Mismatch: You are comparing '{shot_type}' ({query_cat}) against '{ref_shot}' ({ref_cat}). "
                "These belong to fundamentally distinct movement families (e.g. front-foot vertical drive vs back-foot horizontal cross-bat). "
                "DTW aligns the temporal curves, but differences reflect distinct stroke mechanics rather than execution errors."
            )

        # Extract Key Moment Differences at Impact
        key_differences = self._identify_key_differences(
            query_time_series, ref_time_series, warping_path
        )

        methodology_note = (
            "Dynamic Time Warping (DTW) aligns multivariate body-scale normalized joint coordinates and angles across varying tempos. "
            "Similarity reflects kinematic trajectory alignment, not subjective cricketing style or outcome."
        )

        ref_title = reference.get("title") or f"{reference.get('player_name', '')} {ref_shot}".strip()

        return ComparisonResult(
            query_session_id=session_id,
            reference_id=reference.get("id", "ref_custom"),
            reference_title=ref_title,
            shot_type=shot_type,
            alignment_method="DTW (Dynamic Time Warping)",
            normalized_similarity_score=sim_score,
            raw_dtw_distance=dtw_dist,
            warping_path_length=len(warping_path),
            key_differences=key_differences,
            aligned_time_series=aligned_pairs,
            compatibility_warning=compatibility_warning,
            methodology_note=methodology_note
        )

    def _identify_key_differences(
        self,
        q_series: List[Dict[str, Any]],
        r_series: List[Dict[str, Any]],
        warping_path: List[Tuple[int, int]]
    ) -> List[KeyMomentDifference]:
        diffs = []
        path_len = len(warping_path)
        if path_len == 0:
            return diffs

        # Find pair at approximate impact (~68% through sequence or impact phase)
        impact_candidates = [
            (q, r) for q, r in warping_path
            if "impact" in q_series[q].get("phase", "").lower()
        ]
        if impact_candidates:
            q_imp_idx, r_imp_idx = impact_candidates[len(impact_candidates) // 2]
        else:
            impact_idx = int(path_len * 0.68)
            q_imp_idx, r_imp_idx = warping_path[impact_idx]

        q_imp = q_series[q_imp_idx]
        r_imp = r_series[r_imp_idx]

        # 1. Lead knee flexion at impact
        q_knee = q_imp.get("lead_knee_angle")
        r_knee = r_imp.get("lead_knee_angle")
        if q_knee is not None and r_knee is not None:
            diff = round(q_knee - r_knee, 1)
            interp = (
                f"Front leg is {abs(diff):.1f}° straighter than reference ({q_knee:.1f}° vs {r_knee:.1f}°); bending the lead knee lowers the center of gravity and stabilizes the base."
                if diff > 10.0 else
                f"Front knee flexes {abs(diff):.1f}° deeper than reference ({q_knee:.1f}° vs {r_knee:.1f}°), providing an exaggerated low center of gravity."
                if diff < -10.0 else
                f"Lead knee flexion ({q_knee:.1f}°) closely matches benchmark reference ({r_knee:.1f}°)."
            )
            diffs.append(KeyMomentDifference(
                moment_name="Lead Knee Flexion at Impact",
                phase="Impact window",
                query_frame=q_imp_idx,
                ref_frame=r_imp_idx,
                query_timestamp=q_imp.get("timestamp_sec", 0.0),
                ref_timestamp=r_imp.get("timestamp_sec", 0.0),
                metric_name="Lead Knee Angle",
                query_value=round(q_knee, 1),
                ref_value=round(r_knee, 1),
                difference=diff,
                unit="degrees",
                interpretation=interp,
                is_notable=abs(diff) >= 8.0
            ))

        # 2. Torso inclination at impact
        q_torso = q_imp.get("torso_inclination")
        r_torso = r_imp.get("torso_inclination")
        if q_torso is not None and r_torso is not None:
            diff = round(q_torso - r_torso, 1)
            interp = (
                f"Torso leans {abs(diff):.1f}° further forward than reference ({q_torso:.1f}° vs {r_torso:.1f}°)."
                if diff > 8.0 else
                f"Torso is {abs(diff):.1f}° more upright than reference ({q_torso:.1f}° vs {r_torso:.1f}°)."
                if diff < -8.0 else
                f"Torso inclination ({q_torso:.1f}°) matches benchmark standard ({r_torso:.1f}°)."
            )
            diffs.append(KeyMomentDifference(
                moment_name="Torso Inclination at Impact",
                phase="Impact window",
                query_frame=q_imp_idx,
                ref_frame=r_imp_idx,
                query_timestamp=q_imp.get("timestamp_sec", 0.0),
                ref_timestamp=r_imp.get("timestamp_sec", 0.0),
                metric_name="Torso Lean",
                query_value=round(q_torso, 1),
                ref_value=round(r_torso, 1),
                difference=diff,
                unit="degrees",
                interpretation=interp,
                is_notable=abs(diff) >= 6.0
            ))

        # 3. Lead elbow elevation at impact
        q_elbow = q_imp.get("lead_elbow_angle")
        r_elbow = r_imp.get("lead_elbow_angle")
        if q_elbow is not None and r_elbow is not None:
            diff = round(q_elbow - r_elbow, 1)
            interp = (
                f"Lead elbow is extended wider by {abs(diff):.1f}° compared to benchmark ({q_elbow:.1f}° vs {r_elbow:.1f}°)."
                if diff > 15.0 else
                f"Lead elbow is held more compact by {abs(diff):.1f}° ({q_elbow:.1f}° vs {r_elbow:.1f}°)."
                if diff < -15.0 else
                f"Lead elbow elevation ({q_elbow:.1f}°) corresponds well to reference ({r_elbow:.1f}°)."
            )
            diffs.append(KeyMomentDifference(
                moment_name="Lead Elbow Elevation at Impact",
                phase="Impact window",
                query_frame=q_imp_idx,
                ref_frame=r_imp_idx,
                query_timestamp=q_imp.get("timestamp_sec", 0.0),
                ref_timestamp=r_imp.get("timestamp_sec", 0.0),
                metric_name="Lead Elbow Angle",
                query_value=round(q_elbow, 1),
                ref_value=round(r_elbow, 1),
                difference=diff,
                unit="degrees",
                interpretation=interp,
                is_notable=abs(diff) >= 12.0
            ))

        return diffs

comparison_service = ComparisonService()
