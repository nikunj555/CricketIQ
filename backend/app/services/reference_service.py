import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from backend.app.core.config import BASE_DIR

logger = logging.getLogger(__name__)

class ReferenceService:
    """
    Authoritative reference data service loading standardized biomechanical
    tolerances and coaching cues for cricket batting strokes.
    """

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = Path(data_path or (BASE_DIR / "app" / "data" / "reference_shots.json"))
        self._data: Dict[str, Any] = {}
        self._alias_map: Dict[str, str] = {}
        self._load_data()

    def _load_data(self):
        if not self.data_path.exists():
            logger.warning(f"Reference shots file not found at {self.data_path}")
            return
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)

            # Build canonical alias lookup map
            for canonical_name, shot in self._data.items():
                self._alias_map[canonical_name.lower()] = canonical_name
                slug = shot.get("slug")
                if slug:
                    self._alias_map[slug.lower()] = canonical_name
                    self._alias_map[slug.replace("-", " ").lower()] = canonical_name

            # Special convenience aliases
            self._alias_map["pull"] = "Pull Shot"
            self._alias_map["sweep shot"] = "Sweep"
            self._alias_map["defensive"] = "Forward Defensive"
            self._alias_map["front foot defensive"] = "Forward Defensive"

            logger.info(f"Loaded {len(self._data)} shots from {self.data_path}")
        except Exception as e:
            logger.error(f"Failed to load reference shots from {self.data_path}: {e}")

    def canonicalize_shot_name(self, shot_name_or_slug: str) -> str:
        """Resolve any shot name, slug, or alias to canonical catalogue name."""
        if not shot_name_or_slug:
            return "Cover Drive"
        key = shot_name_or_slug.strip().lower()
        return self._alias_map.get(key, shot_name_or_slug.strip())

    def get_shot_reference(self, shot_name_or_slug: str) -> Optional[Dict[str, Any]]:
        canonical = self.canonicalize_shot_name(shot_name_or_slug)
        return self._data.get(canonical)

    def is_shot_analysis_available(self, shot_name_or_slug: str) -> bool:
        shot = self.get_shot_reference(shot_name_or_slug)
        if not shot:
            return False
        return shot.get("analysis_status") == "available"

    def get_phase_ideal_range(
        self,
        shot_name_or_slug: str,
        phase_name: str,
        metric_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves ideal tolerance range {min, max, ideal, unit} for a given shot, phase, and metric.
        Phase names can be loosely matched (e.g. 'Impact window' -> 'impact').
        """
        shot = self.get_shot_reference(shot_name_or_slug)
        if not shot or shot.get("analysis_status") != "available":
            return None

        # Normalize phase key
        p_key = phase_name.strip().lower()
        if "impact" in p_key or "contact" in p_key:
            phase_id = "impact"
        elif "downswing" in p_key or "execution" in p_key:
            phase_id = "downswing"
        elif "stride" in p_key:
            phase_id = "stride"
        elif "backlift" in p_key:
            phase_id = "backlift"
        elif "follow" in p_key:
            phase_id = "follow_through"
        elif "recovery" in p_key or "finish" in p_key:
            phase_id = "recovery"
        elif "stance" in p_key or "setup" in p_key:
            phase_id = "stance"
        else:
            phase_id = p_key.replace(" ", "_")

        phases = shot.get("phases", {})
        phase_data = phases.get(phase_id)
        if not phase_data:
            return None

        return phase_data.get(metric_key)

    def get_common_errors(self, shot_name_or_slug: str) -> List[Dict[str, str]]:
        shot = self.get_shot_reference(shot_name_or_slug)
        if not shot:
            return []
        return shot.get("common_errors", [])

    def get_drills(self, shot_name_or_slug: str) -> List[Dict[str, str]]:
        shot = self.get_shot_reference(shot_name_or_slug)
        if not shot:
            return []
        return shot.get("drills", [])

reference_service = ReferenceService()
