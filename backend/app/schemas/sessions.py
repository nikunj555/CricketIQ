from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.app.schemas.analysis import MetricSummary

class SessionListItem(BaseModel):
    session_id: str
    video_filename: str
    shot_type: str
    category: Optional[str] = None
    handedness: str
    camera_angle: str
    duration_sec: float
    status: str
    created_at: str
    thumbnail_path: Optional[str] = None
    overall_technique_score: Optional[float] = None
    summary: Optional[MetricSummary] = None

class SessionListResponse(BaseModel):
    sessions: List[SessionListItem]
    total_count: int
    shot_types_summary: Dict[str, int]
    categories_summary: Optional[Dict[str, int]] = None
