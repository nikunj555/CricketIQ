export interface MetricSummary {
  overall_technique_score?: number | null;
  lead_knee_flexion_max?: number | null;
  lead_knee_flexion_at_impact?: number | null;
  lead_elbow_flexion_at_impact?: number | null;
  lead_arm_extension_at_impact?: number | null;
  head_over_knee_at_impact?: number | null;
  torso_lean_at_impact?: number | null;
  head_stability_index?: number | null;
  stance_width_ratio_max?: number | null;
  wrist_separation_mean?: number | null;
  weight_transfer_at_impact?: number | null;
  shoulder_hip_separation_max?: number | null;
  movement_smoothness?: number | null;
  tracking_success_rate: number;
  analyzed_frames: number;
  total_video_frames: number;
  hand_tracking_rate?: number | null;
  bat_tracking_rate?: number | null;
  ball_tracking_rate?: number | null;
}

export interface FrameMetric {
  frame_index: number;
  timestamp_sec: number;
  pose_detected: boolean;
  confidence: number;
  lead_knee_angle?: number | null;
  rear_knee_angle?: number | null;
  left_knee_angle?: number | null;
  right_knee_angle?: number | null;
  lead_elbow_angle?: number | null;
  rear_elbow_angle?: number | null;
  left_elbow_angle?: number | null;
  right_elbow_angle?: number | null;
  lead_arm_extension?: number | null;
  rear_arm_extension?: number | null;
  torso_inclination?: number | null;
  shoulder_tilt?: number | null;
  hip_tilt?: number | null;
  head_x?: number | null;
  head_y?: number | null;
  head_displacement?: number | null;
  stance_width_norm?: number | null;
  wrist_separation_norm?: number | null;
  hands_to_torso_dist_norm?: number | null;
  hands_height_ratio?: number | null;
  head_over_lead_knee_norm?: number | null;
  shoulder_hip_separation_deg?: number | null;
  weight_distribution_proxy?: number | null;
  front_foot_stride_ratio?: number | null;
  lead_wrist_x?: number | null;
  lead_wrist_y?: number | null;
  rear_wrist_x?: number | null;
  rear_wrist_y?: number | null;
  lead_foot_x?: number | null;
  lead_foot_y?: number | null;
  rear_foot_x?: number | null;
  rear_foot_y?: number | null;
  hand_tracking_detected?: boolean;
  lead_hand_detected?: boolean;
  rear_hand_detected?: boolean;
  lead_hand_grip_closure?: number | null;
  rear_hand_grip_closure?: number | null;
  bat_detected?: boolean;
  bat_angle_deg?: number | null;
  bat_tip_x?: number | null;
  bat_tip_y?: number | null;
  bat_speed_norm?: number | null;
  ball_detected?: boolean;
  ball_x?: number | null;
  ball_y?: number | null;
  bat_ball_proximity?: number | null;
  phase: string;
  phase_confidence?: number;
  landmarks?: { x: number; y: number; v?: number }[];
}

export interface PhaseSegment {
  phase_name: string;
  start_frame: number;
  end_frame: number;
  start_sec: number;
  end_sec: number;
  duration_sec?: number;
  confidence: number;
  detection_confidence?: number;
  supporting_evidence?: string[];
  key_frame: number;
  description: string;
}

export interface CoachingObservation {
  id: string;
  title: string;
  category: string;
  measurement: string;
  observed_value: string;
  reference_benchmark?: string | null;
  phase: string;
  timestamp_sec?: number | null;
  frame_index?: number | null;
  thumbnail_path?: string | null;
  severity: 'strength' | 'review' | 'consideration';
  why_it_matters: string;
  practical_drill: string;
  limitation: string;
  measurement_provenance?: 'MEASURED' | 'ESTIMATED' | 'MODEL_INFERRED' | 'UNAVAILABLE' | string;
  confidence?: number;
}

export interface MetricComparisonRow {
  phase: string;
  phase_label: string;
  metric: string;
  metric_name: string;
  yours?: number | null;
  yours_formatted: string;
  ideal_min: number;
  ideal_max: number;
  ideal_range: string;
  unit: string;
  verdict: 'OK' | 'Too Low' | 'Too High' | 'Unavailable' | 'Not Tracked' | string;
  status: 'ok' | 'low' | 'high' | 'unavailable' | string;
  validity: 'MEASURED' | 'ESTIMATED' | 'UNAVAILABLE' | string;
}

export interface AnalysisResult {
  session_id: string;
  video_filename: string;
  annotated_video_path?: string | null;
  thumbnail_path?: string | null;
  shot_type: string;
  predicted_shot_type?: string | null;
  prediction_confidence?: number | null;
  shot_mismatch_warning?: string | null;
  detected_camera_view?: string | null;
  camera_view_warning?: string | null;
  striker_track_id?: number | null;
  metric_comparison_table?: MetricComparisonRow[];
  user_confirmed_shot_type?: string | null;
  shot_classification?: {
    predicted_shot: string;
    confidence: number;
    is_uncertain: boolean;
    classification_method: string;
    top_candidates: Array<{ shot_name: string; score: number }>;
    rationale: string;
    extracted_features?: Record<string, number>;
  } | null;
  handedness: string;
  camera_angle: string;
  overall_technique_score?: number | null;
  top_mistakes?: CoachingObservation[];
  fps: number;
  duration_sec: number;
  total_frames: number;
  analyzed_frames: number;
  sample_rate: number;
  summary: MetricSummary;
  phases: PhaseSegment[];
  time_series: FrameMetric[];
  coaching_feedback: CoachingObservation[];
  limitations: string[];
  model_metadata: {
    pose_estimator: string;
    phase_detector?: string;
    phase_classifier?: string;
    shot_classifier?: string;
    predicted_shot?: string;
    prediction_confidence?: string;
    sample_rate: number;
    analyzed_frames: number;
    tracking_rate: string;
  };
  created_at: string;
}

export interface CricketShot {
  id: string;
  slug: string;
  name: string;
  category: string;
  description: string;
  aliases: string[];
  tags: string[];
  difficulty: string;
  analysis_features: string[];
  reference_id?: string | null;
  reference_status: 'available' | 'unavailable';
  reference_title?: string | null;
  reference_player?: string | null;
  reference_source?: string | null;
  reference_video_url?: string | null;
  reference_thumbnail_url?: string | null;
  implementation_status: 'supported' | 'experimental' | 'in_development';
  technique_notes?: string | null;
}

export interface ReferenceDetail {
  id: string;
  shot_id: string;
  shot_name: string;
  player_name: string;
  source: string;
  source_url?: string | null;
  video_url: string;
  thumbnail_url?: string | null;
  camera_view: string;
  verification_status: string;
  description: string;
  stance_setup: string;
  footwork_weight_transfer: string;
  body_positioning: string;
  technique_points: string[];
  common_mistakes: string[];
  phases: Array<{
    phase_name: string;
    frame_window: string;
    description: string;
    lead_knee_target: string;
    key_cue: string;
  }>;
  key_metrics: Record<string, any>;
  is_custom_upload?: boolean;
}

export interface CategorySummary {
  name: string;
  count: number;
  shots: string[];
}

export interface ShotListResponse {
  total_count: number;
  categories: CategorySummary[];
  shots: CricketShot[];
}

export interface SessionListItem {
  session_id: string;
  video_filename: string;
  shot_type: string;
  category?: string | null;
  handedness: string;
  camera_angle: string;
  duration_sec: number;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  created_at: string;
  thumbnail_path?: string | null;
  overall_technique_score?: number | null;
  summary?: MetricSummary | null;
}

export interface SessionListResponse {
  sessions: SessionListItem[];
  total_count: number;
  shot_types_summary: Record<string, number>;
  categories_summary?: Record<string, number>;
}

export interface VideoProcessingStatus {
  session_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  current_step: string;
  error?: string | null;
}

export interface KeyMomentDifference {
  moment_name: string;
  phase: string;
  query_frame: number;
  ref_frame: number;
  query_timestamp: number;
  ref_timestamp: number;
  metric_name: string;
  query_value: number;
  ref_value: number;
  difference: number;
  unit: string;
  interpretation: string;
  is_notable: boolean;
}

export interface AlignedFramePair {
  query_frame: number;
  reference_frame: number;
  query_time_sec: number;
  reference_time_sec: number;
  query_knee_angle?: number | null;
  ref_knee_angle?: number | null;
  query_torso_lean?: number | null;
  ref_torso_lean?: number | null;
  query_head_y?: number | null;
  ref_head_y?: number | null;
  pose_distance: number;
}

export interface ComparisonResult {
  query_session_id: string;
  reference_id: string;
  reference_title: string;
  shot_type: string;
  alignment_method: string;
  normalized_similarity_score: number;
  raw_dtw_distance: number;
  warping_path_length: number;
  key_differences: KeyMomentDifference[];
  aligned_time_series: AlignedFramePair[];
  compatibility_warning?: string | null;
  methodology_note: string;
}

export interface ReferenceShotMeta {
  id: string;
  title: string;
  shot_type: string;
  handedness: string;
  camera_angle: string;
  description: string;
  source_label: string;
  total_frames: number;
  fps: number;
  key_metrics: Record<string, number>;
}

export interface ClassPerformance {
  class_name: string;
  precision: number;
  recall: number;
  f1_score: number;
  support: number;
}

export interface ModelEvaluationReport {
  model_name: string;
  architecture: string;
  dataset_name: string;
  split_strategy: string;
  total_test_sequences: number;
  total_test_frames: number;
  accuracy: number;
  macro_precision: number;
  macro_recall: number;
  macro_f1: number;
  weighted_f1: number;
  per_class_metrics: ClassPerformance[];
  confusion_matrix: number[][];
  classes: string[];
  training_loss_history: number[];
  val_loss_history: number[];
  baseline_comparison: {
    baseline_model: string;
    baseline_accuracy: number;
    baseline_macro_f1: number;
    deep_learning_accuracy: number;
    deep_learning_macro_f1: number;
    accuracy_improvement: number;
    f1_improvement: number;
  };
  feature_importance: Record<string, number>;
  inference_latency_ms: number;
  evaluated_at: string;
  limitations: string[];
}

/* =========================================================================
   Live Batting Coach Types
   ========================================================================= */

export interface LivePlayerPresence {
  detected: boolean;
  confidence: number;
  visibility_score: number;
  message: string;
}

export interface LivePoseState {
  state: string; // "waiting_for_player" | "ready_for_shot" | "shot_in_progress" | "shot_completed" | "cooldown"
  state_description: string;
  presence: LivePlayerPresence;
  current_lead_knee?: number | null;
  current_rear_knee?: number | null;
  current_torso_lean?: number | null;
  current_head_disp?: number | null;
  current_lead_elbow?: number | null;
  current_lead_arm_ext?: number | null;
  current_head_over_knee?: number | null;
  current_weight_dist?: number | null;
  current_bat_angle?: number | null;
  bat_detected?: boolean;
  bat_angle_deg?: number | null;
  grip_closure?: number | null;
  hand_tracking_active?: boolean;
  bat_tracking_active?: boolean;
  landmarks_normalized?: Array<{ x: number; y: number; z: number; v: number }>;
  frame_timestamp_ms: number;
  latency_ms: number;
}

export interface LiveAttemptFeedback {
  attempt_id: string;
  session_id: string;
  shot_type: string;
  shot_confidence: number;
  main_observation: string;
  evidence: string;
  observed_metric_name: string;
  observed_value: string;
  benchmark_value: string;
  why_it_matters: string;
  next_action_drill: string;
  confidence_score: number;
  processing_latency_ms: number;
  impact_lead_knee?: number | null;
  impact_torso_lean?: number | null;
  head_stability?: number | null;
  impact_lead_elbow?: number | null;
  impact_arm_extension?: number | null;
  head_over_knee_alignment?: string | null;
  head_over_knee_offset?: number | null;
  hand_grip_analysis?: string | null;
  grip_closure?: number | null;
  bat_angle_at_impact?: number | null;
  bat_angle_impact?: number | null;
  weight_distribution?: number | null;
  previous_attempt_comparison?: string | null;
  full_session_id: string;
  created_at: string;
}

export interface LiveFrameRequest {
  image_base64: string;
  timestamp_ms: number;
  handedness?: string;
  shot_hint?: string;
  session_id?: string;
  manual_trigger?: string | null;
}

export interface LiveAttemptPayload {
  session_id: string;
  attempt_index: number;
  shot_type?: string;
  handedness?: string;
  camera_angle?: string;
  frames: FrameMetric[];
  video_base64?: string | null;
}

export type NavTab =
  | 'dashboard'
  | 'live'
  | 'library'
  | 'workspace'
  | 'upload'
  | 'biomechanics'
  | 'phases'
  | 'comparison'
  | 'progress'
  | 'evaluation'
  | 'about';

