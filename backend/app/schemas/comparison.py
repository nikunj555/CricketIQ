from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.app.schemas.analysis import FrameMetric

class AlignedFramePair(BaseModel):
    query_frame: int
    reference_frame: int
    query_time_sec: float
    reference_time_sec: float
    query_knee_angle: Optional[float] = None
    ref_knee_angle: Optional[float] = None
    query_torso_lean: Optional[float] = None
    ref_torso_lean: Optional[float] = None
    query_head_y: Optional[float] = None
    ref_head_y: Optional[float] = None
    pose_distance: float

class KeyMomentDifference(BaseModel):
    moment_name: str
    phase: str
    query_frame: int
    ref_frame: int
    query_timestamp: float
    ref_timestamp: float
    metric_name: str
    query_value: float
    ref_value: float
    difference: float
    unit: str
    interpretation: str
    is_notable: bool

class ComparisonResult(BaseModel):
    query_session_id: str
    reference_id: str
    reference_title: str
    shot_type: str
    alignment_method: str  # "DTW (Dynamic Time Warping)"
    normalized_similarity_score: float  # 0 to 100 scale (pose kinematic similarity, NOT cricket skill)
    raw_dtw_distance: float
    warping_path_length: int
    key_differences: List[KeyMomentDifference]
    aligned_time_series: List[AlignedFramePair]
    compatibility_warning: Optional[str] = None
    methodology_note: str

class ReferenceShotMeta(BaseModel):
    id: str
    title: str
    shot_type: str
    handedness: str
    camera_angle: str
    description: str
    source_label: str
    total_frames: int
    fps: float
    key_metrics: Dict[str, float]
