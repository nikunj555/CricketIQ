import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.app.data.shot_catalogue import get_shot_by_id_or_slug, SHOT_CATALOGUE

logger = logging.getLogger(__name__)

class LearningVideoService:
    def __init__(self, data_path: Optional[Path] = None):
        if data_path is None:
            data_path = Path(__file__).resolve().parent.parent / "data" / "shot_videos.json"
        self.data_path = data_path
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
        self._load_data()

    def _load_data(self):
        if not self.data_path.exists():
            logger.warning(f"shot_videos.json not found at {self.data_path}")
            return
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self._cache = raw.get("videos", {})
        except Exception as e:
            logger.error(f"Failed to load shot_videos.json: {e}")
            self._cache = {}

    def get_videos_for_shot(self, shot_identifier: str) -> List[Dict[str, Any]]:
        """
        Resolves shot by canonical name, slug, or ID, and returns the curated
        learning video lessons list from shot_videos.json.
        """
        if not shot_identifier:
            return []
            
        # Try direct match
        if shot_identifier in self._cache:
            return list(self._cache[shot_identifier])
            
        # Try resolving via catalogue slug / ID / alias
        shot = get_shot_by_id_or_slug(shot_identifier)
        if shot and shot.get("name") in self._cache:
            return list(self._cache[shot["name"]])
            
        # Case-insensitive search across cache keys
        s_lower = shot_identifier.strip().lower()
        for k, v in self._cache.items():
            if k.lower() == s_lower:
                return list(v)
                
        return []

    def get_all_videos(self) -> Dict[str, List[Dict[str, Any]]]:
        return dict(self._cache)

learning_video_service = LearningVideoService()
