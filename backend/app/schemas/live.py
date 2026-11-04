from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from backend.app.schemas.analysis import MetricSummary, PhaseSegment, CoachingObservation, FrameMetric

class LivePlayerPresence(BaseModel):
    detected: bool
    confidence: float
    visibility_score: float
    message: str
    is_ready_to_record: bool = True
    blocked_reason: Optional[str] = None

class LivePoseState(BaseModel):
    state: str  # "waiting_for_player", "ready_for_shot", "shot_in_progress", "shot_completed", "analyzing", "cooldown"
    state_description: str
    presence: LivePlayerPresence
    current_lead_knee: Optional[float] = None
    current_rear_knee: Optional[float] = None
    current_torso_lean: Optional[float] = None
    current_head_disp: Optional[float] = None
    current_lead_elbow: Optional[float] = None
    current_lead_arm_ext: Optional[float] = None
    current_head_over_knee: Optional[float] = None
    current_weight_dist: Optional[float] = None
    current_bat_angle: Optional[float] = None
    hand_tracking_active: bool = False
    bat_tracking_active: bool = False
    landmarks_normalized: Optional[List[Dict[str, float]]] = None
    frame_timestamp_ms: float
    latency_ms: float

class LiveAttemptFeedback(BaseModel):
    attempt_id: str
    session_id: str
    shot_type: str
    shot_confidence: float
    main_observation: str
    evidence: str
    observed_metric_name: str
    observed_value: str
    benchmark_value: str
    why_it_matters: str
    next_action_drill: str
    confidence_score: float
    processing_latency_ms: float
    impact_lead_knee: Optional[float] = None
    impact_torso_lean: Optional[float] = None
    head_stability: Optional[float] = None
    impact_lead_elbow: Optional[float] = None
    impact_arm_extension: Optional[float] = None
    head_over_knee_alignment: Optional[str] = None
    hand_grip_analysis: Optional[str] = None
    bat_angle_at_impact: Optional[float] = None
    previous_attempt_comparison: Optional[str] = None
    full_session_id: str
    created_at: str

class LiveFrameRequest(BaseModel):
    image_base64: str
    timestamp_ms: float
    handedness: str = "Right"
    shot_hint: Optional[str] = "Cover Drive"
    session_id: Optional[str] = None
    manual_trigger: Optional[str] = None  # "start", "finish", null

class LiveAttemptPayload(BaseModel):
    session_id: str
    attempt_index: int
    shot_type: str = "Cover Drive"
    handedness: str = "Right"
    camera_angle: str = "Side View"
    frames: List[FrameMetric]
    video_base64: Optional[str] = None  # Optional client-recorded webm/mp4 clip
    recorded_duration_sec: float = 0.0

class LiveSessionSummary(BaseModel):
    session_id: str
    total_attempts: int
    successful_analyses: int
    shot_distribution: Dict[str, int]
    recent_attempts: List[LiveAttemptFeedback]
