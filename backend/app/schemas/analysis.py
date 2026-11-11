from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class LandmarkPoint(BaseModel):
    index: int
    name: str
    x: float
    y: float
    z: float
    visibility: float
    presence: float

class FrameMetric(BaseModel):
    frame_index: int
    timestamp_sec: float
    pose_detected: bool
    confidence: float
    lead_knee_angle: Optional[float] = None
    rear_knee_angle: Optional[float] = None
    torso_inclination: Optional[float] = None
    shoulder_tilt: Optional[float] = None
    hip_tilt: Optional[float] = None
    head_x: Optional[float] = None
    head_y: Optional[float] = None
    head_displacement: Optional[float] = None
    stance_width_norm: Optional[float] = None
    # Landmarks
    landmarks: Optional[List[Any]] = None
    # Upper-body & arm kinematics
    lead_elbow_angle: Optional[float] = None
    rear_elbow_angle: Optional[float] = None
    left_elbow_angle: Optional[float] = None
    right_elbow_angle: Optional[float] = None
    left_knee_angle: Optional[float] = None
    right_knee_angle: Optional[float] = None
    lead_arm_extension: Optional[float] = None
    rear_arm_extension: Optional[float] = None
    lead_wrist_x: Optional[float] = None
    lead_wrist_y: Optional[float] = None
    rear_wrist_x: Optional[float] = None
    rear_wrist_y: Optional[float] = None
    wrist_separation_norm: Optional[float] = None
    hands_to_torso_dist_norm: Optional[float] = None
    hands_height_ratio: Optional[float] = None
    # Footwork & balance kinematics
    lead_foot_x: Optional[float] = None
    lead_foot_y: Optional[float] = None
    rear_foot_x: Optional[float] = None
    rear_foot_y: Optional[float] = None
    head_over_lead_knee_norm: Optional[float] = None
    shoulder_hip_separation_deg: Optional[float] = None
    weight_distribution_proxy: Optional[float] = None
    front_foot_stride_ratio: Optional[float] = None
    # Dedicated Hand Tracking
    hand_tracking_detected: bool = False
    lead_hand_detected: bool = False
    rear_hand_detected: bool = False
    lead_hand_grip_closure: Optional[float] = None
    rear_hand_grip_closure: Optional[float] = None
    hand_landmarks: Optional[Dict[str, Any]] = None
    # Modular Bat and Ball Tracking
    bat_detected: bool = False
    bat_angle_deg: Optional[float] = None
    bat_tip_x: Optional[float] = None
    bat_tip_y: Optional[float] = None
    bat_speed_norm: Optional[float] = None
    ball_detected: bool = False
    ball_x: Optional[float] = None
    ball_y: Optional[float] = None
    bat_ball_proximity: Optional[float] = None
    phase: str = "Unknown"
    phase_confidence: float = 0.0
    landmarks: Optional[List[Dict[str, float]]] = None
    # Temporal derivatives & velocities
    lead_knee_angle_velocity: Optional[float] = None
    lead_knee_angle_acceleration: Optional[float] = None
    torso_inclination_velocity: Optional[float] = None
    lead_elbow_angle_velocity: Optional[float] = None
    lead_wrist_speed: Optional[float] = None
    lead_wrist_speed_normalized: Optional[float] = None

class PhaseSegment(BaseModel):
    phase_name: str
    start_frame: int
    end_frame: int
    start_sec: float
    end_sec: float
    duration_sec: float = 0.0
    confidence: float
    detection_confidence: float = 0.0
    supporting_evidence: List[str] = Field(default_factory=list)
    key_frame: int
    description: str

class CoachingObservation(BaseModel):
    id: str
    title: str
    category: str
    measurement: str
    observed_value: str
    reference_benchmark: Optional[str] = None
    phase: str
    timestamp_sec: Optional[float] = None
    frame_index: Optional[int] = None
    thumbnail_path: Optional[str] = None
    severity: str  # "strength", "review", "consideration"
    why_it_matters: str
    practical_drill: str
    limitation: str
    measurement_provenance: str = "MEASURED"  # "MEASURED", "ESTIMATED", "MODEL_INFERRED", "UNAVAILABLE"
    confidence: Optional[float] = 0.85

class MetricSummary(BaseModel):
    overall_technique_score: Optional[float] = None  # 0 to 100
    lead_knee_flexion_max: Optional[float] = None
    lead_knee_flexion_at_impact: Optional[float] = None
    lead_elbow_flexion_at_impact: Optional[float] = None
    lead_arm_extension_at_impact: Optional[float] = None
    head_over_knee_at_impact: Optional[float] = None
    torso_lean_at_impact: Optional[float] = None
    head_stability_index: Optional[float] = None  # Lower is more stable
    stance_width_ratio_max: Optional[float] = None
    wrist_separation_mean: Optional[float] = None
    weight_transfer_at_impact: Optional[float] = None
    shoulder_hip_separation_max: Optional[float] = None
    movement_smoothness: Optional[float] = None
    tracking_success_rate: float = 0.0
    analyzed_frames: int = 0
    total_video_frames: int = 0
    hand_tracking_rate: Optional[float] = None
    bat_tracking_rate: Optional[float] = None
    ball_tracking_rate: Optional[float] = None

class AnalysisResult(BaseModel):
    session_id: str
    video_filename: str
    annotated_video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    shot_type: str
    predicted_shot_type: Optional[str] = None
    prediction_confidence: Optional[float] = None
    user_confirmed_shot_type: Optional[str] = None
    shot_classification: Optional[Dict[str, Any]] = None
    handedness: str = "Right-handed"
    camera_angle: str = "Side-on (Right)"
    detected_camera_view: Optional[str] = None
    camera_view_warning: Optional[str] = None
    shot_mismatch_warning: Optional[str] = None
    striker_track_id: Optional[int] = None
    striker_candidates: Optional[List[Dict[str, Any]]] = None
    striker_isolation_evidence: Optional[Dict[str, Any]] = None
    striker_tracking_status: Optional[str] = None
    tracking_dropout_warning: Optional[str] = None
    shot_confidence: Optional[Dict[str, Any]] = None
    coaching_paused: Optional[bool] = False
    pause_reason: Optional[str] = None
    plain_summary: Optional[Dict[str, Any]] = None
    issue_cards: Optional[List[Dict[str, Any]]] = None
    overall_technique_score: Optional[float] = None
    top_mistakes: List[Any] = Field(default_factory=list)
    fps: float = 30.0
    duration_sec: float = 0.0
    total_frames: int = 0
    analyzed_frames: int = 0
    sample_rate: int = 1
    summary: Optional[Any] = None
    phases: List[PhaseSegment] = Field(default_factory=list)
    time_series: List[FrameMetric] = Field(default_factory=list)
    coaching_feedback: List[Any] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    model_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None

class StrikerCandidate(BaseModel):
    track_id: int
    bbox: List[float]
    is_default: bool
    role: str
    wrist_motion_score: float
    confidence: Optional[float] = None
    evidence: Optional[Dict[str, Any]] = None

class StrikerInspectionResponse(BaseModel):
    candidates: List[StrikerCandidate]
    default_track_id: int
    total_persons: int
    frame_width: int
    frame_height: int
    frame_0_data_url: Optional[str] = None
    needs_confirmation: bool = False

class VideoUploadResponse(BaseModel):
    session_id: str
    filename: str
    shot_type: str
    handedness: str
    camera_angle: str
    striker_track_id: Optional[int] = None
    detected_camera_view: Optional[str] = None
    message: str
    video_url: str

class VideoProcessingStatus(BaseModel):
    session_id: str
    status: str  # "queued", "processing", "completed", "failed"
    progress: float  # 0 to 100
    current_step: str
    error: Optional[str] = None
