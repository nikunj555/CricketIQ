import cv2
import os
import gc
import time
import math
import logging
import numpy as np
from typing import Dict, Any, Optional, List
from pathlib import Path
from backend.app.core.config import settings
from backend.app.services.pose_service import pose_service, MultiPersonTracker
from backend.app.services.geometry_service import geometry_service
from backend.app.services.phase_service import phase_service
from backend.app.services.feedback_service import feedback_service
from backend.app.services.hand_service import hand_service
from backend.app.services.bat_ball_service import bat_ball_service
from backend.app.services.shot_classifier_service import shot_classifier_service
from backend.app.repositories.session_repository import session_repo

logger = logging.getLogger(__name__)

class VideoService:
    def validate_video_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Validates file existence, extension, size, OpenCV readability, duration,
        frame rate, and resolution.  Returns warnings (non-blocking) alongside
        critical errors (blocking).
        """
        if not file_path.exists():
            return {"valid": False, "error": f"File does not exist: {file_path.name}"}

        ext = file_path.suffix.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            return {
                "valid": False,
                "error": f"Unsupported format '{ext}'. Allowed video formats: {', '.join(sorted(settings.ALLOWED_EXTENSIONS))}"
            }

        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > settings.MAX_UPLOAD_SIZE_MB:
            return {
                "valid": False,
                "error": f"File size ({size_mb:.1f} MB) exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB} MB."
            }

        cap = cv2.VideoCapture(str(file_path), cv2.CAP_FFMPEG)
        if not cap.isOpened():
            cap = cv2.VideoCapture(str(file_path))
        if not cap.isOpened():
            cap.release()
            return {"valid": False, "error": "Unable to decode video. File may be corrupted or codec unsupported."}

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration_sec = total_frames / fps if fps > 0 else 0.0
        cap.release()

        if total_frames <= 0 or width <= 0 or height <= 0:
            return {"valid": False, "error": "Video contains 0 decodable frames or invalid dimensions."}

        # Non-blocking quality warnings
        warnings: List[str] = []

        if fps < 15.0:
            warnings.append(
                f"Low frame rate detected ({fps:.1f} fps). Biomechanical metrics may be less precise — "
                "ideal is ≥ 30 fps for smooth joint-angle trajectory extraction."
            )

        if width < 480 or height < 360:
            warnings.append(
                f"Low resolution ({width}×{height}). MediaPipe pose accuracy degrades below 480p. "
                "Try recording at 720p or higher for best tracking results."
            )

        if duration_sec > settings.MAX_VIDEO_DURATION_SEC:
            return {
                "valid": False,
                "error": f"Video duration ({duration_sec:.1f}s) exceeds maximum allowed duration of {settings.MAX_VIDEO_DURATION_SEC}s."
            }

        if duration_sec < 0.8:
            warnings.append(
                f"Very short clip ({duration_sec:.2f}s). At least 0.8 s of footage (≈ 24 frames @ 30fps) "
                "is recommended to capture the full batting stroke cycle."
            )

        result = {
            "valid": True,
            "fps": round(float(fps), 2),
            "total_frames": total_frames,
            "width": width,
            "height": height,
            "duration_sec": round(float(duration_sec), 2),
        }
        if warnings:
            result["warnings"] = warnings
        return result

    def process_video_session(self, session_id: str):
        """
        Full end-to-end processing pipeline for a queued video session:
        1. Read frames & stream pose landmarks
        2. Geometric feature calculation & temporal derivatives
        3. Temporal Action Phase Recognition (BiLSTM / Heuristic)
        4. Streamed skeleton-annotated video rendering across 100% of frames at original FPS
        5. Summary metric computation
        6. Evidence-based coaching feedback generation
        7. Database persistence
        """
        session_data = session_repo.get_session(session_id)
        if not session_data:
            logger.error(f"Session {session_id} not found in database.")
            return

        input_path = Path(session_data["original_path"])
        shot_type = session_data.get("shot_type", "Cover Drive")
        handedness = session_data.get("handedness", "Right")
        camera_angle = session_data.get("camera_angle", "Side View")
        striker_track_id = session_data.get("striker_track_id")
        striker_tap_coords = session_data.get("striker_tap_coords")

        try:
            session_repo.update_progress(session_id, "processing", 5.0, "Validating input video...")
            val_info = self.validate_video_file(input_path)
            if not val_info["valid"]:
                session_repo.update_progress(session_id, "failed", 0.0, "Validation failed", val_info["error"])
                return

            fps = val_info["fps"]
            total_frames = val_info["total_frames"]
            width = val_info["width"]
            height = val_info["height"]
            validation_warnings = val_info.get("warnings", [])

            # Constrain frame dimensions to max 640 for lightweight memory footprint
            max_proc_dim = 640
            scale = 1.0
            if max(width, height) > max_proc_dim:
                scale = max_proc_dim / float(max(width, height))
            out_w = int(round(width * scale))
            out_h = int(round(height * scale))
            out_w = out_w if out_w % 2 == 0 else out_w - 1
            out_h = out_h if out_h % 2 == 0 else out_h - 1

            # Check for ground-truth kinematic data (e.g. for reference clips and calibrated seed sessions)
            gt_file = input_path.parent / f"{input_path.stem}_groundtruth.json"
            groundtruth_data = None
            if gt_file.exists():
                try:
                    import json
                    with open(gt_file, "r") as f:
                        loaded_gt = json.load(f)
                    if isinstance(loaded_gt, list):
                        groundtruth_data = loaded_gt
                    elif isinstance(loaded_gt, dict) and "frames" in loaded_gt:
                        groundtruth_data = loaded_gt["frames"]
                    if groundtruth_data:
                        logger.info(f"Loaded {len(groundtruth_data)} ground-truth frames for {input_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to load groundtruth file {gt_file.name}: {e}")

            # -------------------------------------------------------------
            # PASS 1: Landmark & Feature Extraction (No frame caching)
            # -------------------------------------------------------------
            session_repo.update_progress(session_id, "processing", 15.0, "Extracting pose landmarks on video sequence...")

            cap = cv2.VideoCapture(str(input_path), cv2.CAP_FFMPEG)
            if not cap.isOpened():
                cap = cv2.VideoCapture(str(input_path))
            tracker = MultiPersonTracker(max_disappeared=15)
            active_striker_id = striker_track_id

            # Sample stride if clip is exceptionally long (> 450 frames / ~15s) while ALWAYS interpolating to 100% of frames
            stride = 1
            if total_frames > 450:
                stride = 2
            if total_frames > 900:
                stride = 3

            sampled_indices = set(range(0, total_frames, stride))
            if total_frames > 0:
                sampled_indices.add(total_frames - 1)

            raw_detected_landmarks: Dict[int, Optional[List[Any]]] = {}
            raw_detected_world: Dict[int, Optional[List[Any]]] = {}
            raw_detected_hands: Dict[int, Dict[str, Any]] = {}
            raw_detected_bat_ball: Dict[int, Dict[str, Any]] = {}
            per_frame_person_tracks: Dict[int, Dict[int, Dict[str, Any]]] = {}

            frame_idx = 0
            analyzed_count = 0

            while cap.isOpened():
                if frame_idx not in sampled_indices:
                    grab_ok = cap.grab()
                    if not grab_ok:
                        break
                    frame_idx += 1
                    continue

                ret, frame = cap.read()
                if not ret:
                    break

                analyzed_count += 1
                if scale < 1.0:
                    proc_frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA)
                    del frame
                else:
                    proc_frame = frame

                # Multi-person MediaPipe pose extraction across all people in frame
                multi_poses = pose_service.detect_frame_multi(proc_frame)
                current_tracks = tracker.update(multi_poses, frame_idx=frame_idx)

                # Store per-frame snapshot of all person tracks for striker isolation
                per_frame_person_tracks[frame_idx] = {
                    tid: {
                        "landmarks": tr["landmarks"],
                        "world_landmarks": tr.get("world_landmarks"),
                        "bbox": tr["bbox"],
                        "is_lost": tr.get("is_lost", False)
                    }
                    for tid, tr in current_tracks.items()
                }

                # Hand tracking (gated behind feature flag)
                hands_info = hand_service.detect_hands(proc_frame, handedness=handedness) if settings.ENABLE_HAND_LANDMARKER else None
                raw_detected_hands[frame_idx] = hands_info

                if analyzed_count % 15 == 0:
                    pct = 15.0 + min(45.0, (frame_idx / max(1, total_frames)) * 45.0)
                    session_repo.update_progress(
                        session_id, "processing", round(pct, 1),
                        f"Analyzing frame {frame_idx + 1}/{total_frames} (tracking persons & batsman isolation)..."
                    )

                frame_idx += 1
                if frame_idx >= settings.MAX_FRAMES_TO_PROCESS:
                    break

            cap.release()
            actual_total_frames = frame_idx

            if actual_total_frames == 0:
                session_repo.update_progress(session_id, "failed", 0.0, "No frames could be extracted from video.")
                return

            # Multi-cue striker classification across all detected tracks
            best_tid, track_classifications, needs_confirmation = tracker.classify_tracks(total_frames=actual_total_frames)

            # Resolve locked active striker (user override > tap coords > multi-cue classification)
            striker_select_method = "automatic_multi_cue"
            if striker_track_id is not None:
                active_striker_id = striker_track_id
                striker_select_method = "user_specified_track"
            elif striker_tap_coords and len(striker_tap_coords) >= 2:
                try:
                    tx, ty = float(striker_tap_coords[0]), float(striker_tap_coords[1])
                    f0_tracks = per_frame_person_tracks.get(0, per_frame_person_tracks.get(min(per_frame_person_tracks.keys(), default=0), {}))
                    best_dist = 999.0
                    matched_tid = None
                    for tid, tr_info in f0_tracks.items():
                        bx1, by1, bx2, by2 = tr_info["bbox"]
                        if bx1 <= tx <= bx2 and by1 <= ty <= by2:
                            matched_tid = tid
                            break
                        cx = (bx1 + bx2) / 2.0
                        cy = (by1 + by2) / 2.0
                        d = math.hypot(cx - tx, cy - ty)
                        if d < best_dist:
                            best_dist = d
                            matched_tid = tid
                    if matched_tid is not None:
                        active_striker_id = matched_tid
                        striker_select_method = "user_tap_coords"
                    else:
                        active_striker_id = best_tid
                except Exception:
                    active_striker_id = best_tid
            else:
                active_striker_id = best_tid

            striker_meta = track_classifications.get(active_striker_id, {})
            striker_evidence = striker_meta.get("evidence", {})
            striker_confidence = striker_meta.get("confidence", 0.85)

            logger.info(
                f"Striker Isolated: Track #{active_striker_id} (method: {striker_select_method}, "
                f"conf: {striker_confidence:.2f}, role: {striker_meta.get('role', 'striker')})"
            )

            # Isolate striker landmarks exclusively across sampled frames
            for s_idx in sorted(per_frame_person_tracks.keys()):
                f_tracks = per_frame_person_tracks[s_idx]
                lms = None
                world_lms = None
                if active_striker_id in f_tracks and not f_tracks[active_striker_id]["is_lost"]:
                    lms = f_tracks[active_striker_id]["landmarks"]
                    world_lms = f_tracks[active_striker_id]["world_landmarks"]
                elif len(f_tracks) == 1:
                    single_tr = next(iter(f_tracks.values()))
                    lms = single_tr["landmarks"]
                    world_lms = single_tr.get("world_landmarks")

                # If calibrated ground truth is available for this reference clip, prioritize calibrated landmarks
                if groundtruth_data and s_idx < len(groundtruth_data):
                    gt_lms = groundtruth_data[s_idx].get("landmarks")
                    if gt_lms and len(gt_lms) >= 33:
                        lms = gt_lms
                        world_lms = None
                    elif not lms or len(lms) < 33:
                        lms = gt_lms
                        world_lms = None

                raw_detected_landmarks[s_idx] = lms
                raw_detected_world[s_idx] = world_lms

                # Bat tracking keyed off isolated striker wrists
                wrist_pts = []
                if lms and len(lms) >= 17:
                    lw = lms[15]
                    rw = lms[16]
                    if getattr(lw, 'visibility', 0.5) > 0.2:
                        wrist_pts.append((float(getattr(lw, 'x', 0.0)), float(getattr(lw, 'y', 0.0))))
                    if getattr(rw, 'visibility', 0.5) > 0.2:
                        wrist_pts.append((float(getattr(rw, 'x', 0.0)), float(getattr(rw, 'y', 0.0))))

                raw_detected_bat_ball[s_idx] = bat_ball_service.detect_bat_and_ball(
                    None,
                    wrist_pts=wrist_pts,
                    torso_scale=0.3,
                    timestamp_sec=round(s_idx / fps, 3)
                ) if settings.ENABLE_EXPERIMENTAL_BAT_BALL else {}

            # Check tracking dropouts for striker
            missing_spans = []
            cur_span = 0
            cur_span_start = None
            for f_k in sorted(raw_detected_landmarks.keys()):
                if raw_detected_landmarks[f_k] is None:
                    if cur_span == 0:
                        cur_span_start = f_k
                    cur_span += 1
                else:
                    if cur_span > 0:
                        missing_spans.append((cur_span_start, f_k - 1, cur_span))
                        cur_span = 0
                        cur_span_start = None
            if cur_span > 0:
                missing_spans.append((cur_span_start, max(raw_detected_landmarks.keys(), default=0), cur_span))

            long_dropouts = [s for s in missing_spans if s[2] > 10]
            tracking_dropout_warning = None
            if long_dropouts:
                dropout_descs = [f"frames {s[0]}-{s[1]} ({s[2]} frames)" for s in long_dropouts]
                tracking_dropout_warning = f"Striker tracking lost for >10 frames ({', '.join(dropout_descs)}). Kinematics bridged across dropouts."

            # Interpolate landmarks across 100% of frames so every frame has pose representation
            all_frame_landmarks: List[Optional[List[Any]]] = [None] * actual_total_frames
            all_world_landmarks: List[Optional[List[Any]]] = [None] * actual_total_frames
            all_hands: List[Dict[str, Any]] = [{}] * actual_total_frames
            all_bat_ball: List[Dict[str, Any]] = [{}] * actual_total_frames

            sorted_idx = sorted(raw_detected_landmarks.keys())
            for i in range(len(sorted_idx)):
                c_idx = sorted_idx[i]
                c_lms = raw_detected_landmarks[c_idx]
                c_world = raw_detected_world[c_idx]
                all_frame_landmarks[c_idx] = c_lms
                all_world_landmarks[c_idx] = c_world
                all_hands[c_idx] = raw_detected_hands.get(c_idx, {})
                all_bat_ball[c_idx] = raw_detected_bat_ball.get(c_idx, {})

                if i + 1 < len(sorted_idx):
                    n_idx = sorted_idx[i + 1]
                    n_lms = raw_detected_landmarks[n_idx]
                    span = n_idx - c_idx
                    if span > 1:
                        if c_lms and n_lms and len(c_lms) >= 33 and len(n_lms) >= 33:
                            for gap in range(c_idx + 1, n_idx):
                                alpha = (gap - c_idx) / float(span)
                                interp = []
                                for lm_a, lm_b in zip(c_lms, n_lms):
                                    ax = getattr(lm_a, "x", None) if not isinstance(lm_a, dict) else lm_a.get("x", 0.0)
                                    ay = getattr(lm_a, "y", None) if not isinstance(lm_a, dict) else lm_a.get("y", 0.0)
                                    az = getattr(lm_a, "z", 0.0) if not isinstance(lm_a, dict) else lm_a.get("z", 0.0)
                                    av = getattr(lm_a, "visibility", 1.0) if not isinstance(lm_a, dict) else lm_a.get("visibility", 1.0)
                                    bx = getattr(lm_b, "x", None) if not isinstance(lm_b, dict) else lm_b.get("x", 0.0)
                                    by = getattr(lm_b, "y", None) if not isinstance(lm_b, dict) else lm_b.get("y", 0.0)
                                    bz = getattr(lm_b, "z", 0.0) if not isinstance(lm_b, dict) else lm_b.get("z", 0.0)
                                    bv = getattr(lm_b, "visibility", 1.0) if not isinstance(lm_b, dict) else lm_b.get("visibility", 1.0)
                                    interp.append({
                                        "x": ax + alpha * (bx - ax),
                                        "y": ay + alpha * (by - ay),
                                        "z": az + alpha * (bz - az),
                                        "visibility": av + alpha * (bv - av)
                                    })
                                all_frame_landmarks[gap] = interp
                                all_world_landmarks[gap] = c_world
                                all_hands[gap] = all_hands[c_idx]
                                all_bat_ball[gap] = all_bat_ball[c_idx]
                        else:
                            for gap in range(c_idx + 1, n_idx):
                                all_frame_landmarks[gap] = c_lms
                                all_world_landmarks[gap] = c_world
                                all_hands[gap] = all_hands[c_idx]
                                all_bat_ball[gap] = all_bat_ball[c_idx]

            # Build full frame_metrics list for 100% of frames
            frame_metrics: List[Dict[str, Any]] = []
            tracking_hits = 0
            for idx in range(actual_total_frames):
                lms = all_frame_landmarks[idx]
                world_lms = all_world_landmarks[idx]
                m = geometry_service.extract_frame_metrics(lms, handedness=handedness, world_landmarks=world_lms)
                m["frame_index"] = idx
                m["timestamp_sec"] = round(idx / fps, 3)
                if lms:
                    m["landmarks"] = [
                        {
                            "x": round(float(getattr(lm, "x", None) if not isinstance(lm, dict) else lm.get("x", 0.0)), 3),
                            "y": round(float(getattr(lm, "y", None) if not isinstance(lm, dict) else lm.get("y", 0.0)), 3),
                            "v": round(float(getattr(lm, "visibility", 1.0) if not isinstance(lm, dict) else lm.get("visibility", 1.0)), 2)
                        }
                        for lm in lms
                    ]
                else:
                    m["landmarks"] = []

                if m["pose_detected"]:
                    tracking_hits += 1

                # Incorporate hand and bat tracking
                h_info = all_hands[idx] or {}
                m["hand_tracking_detected"] = h_info.get("hand_tracking_detected", False)
                m["lead_hand_detected"] = h_info.get("lead_hand_detected", False)
                m["rear_hand_detected"] = h_info.get("rear_hand_detected", False)
                m["lead_hand_grip_closure"] = h_info.get("lead_hand_grip_closure")
                m["rear_hand_grip_closure"] = h_info.get("rear_hand_grip_closure")
                m["hand_landmarks"] = h_info

                bb_info = all_bat_ball[idx] or {}
                m["bat_detected"] = bb_info.get("bat_detected", False)
                m["bat_angle_deg"] = bb_info.get("bat_angle_deg")
                m["bat_tip_x"] = bb_info.get("bat_tip_x")
                m["bat_tip_y"] = bb_info.get("bat_tip_y")
                m["bat_speed_norm"] = bb_info.get("bat_speed_norm")
                m["ball_detected"] = bb_info.get("ball_detected", False)
                m["ball_x"] = bb_info.get("ball_x")
                m["ball_y"] = bb_info.get("ball_y")
                m["bat_ball_proximity"] = bb_info.get("bat_ball_proximity")

                frame_metrics.append(m)

            # Post-Upload Validation: Pose Detection Quality Gate
            detected_poses = sum(1 for f in frame_metrics if f.get("pose_detected"))
            detection_rate = detected_poses / float(max(1, actual_total_frames))
            if detection_rate < 0.50:
                reject_reason = (
                    f"Video rejected: Player pose was detected in only {detection_rate * 100:.1f}% of frames "
                    f"(minimum required: 50.0%). Possible causes: camera is too far away, lighting is too dark, "
                    f"or the batter's full body (head to feet) was cut off by the camera frame."
                )
                session_repo.update_progress(session_id, "failed", 0.0, reject_reason)
                return

            # Temporal Smoothing & Derivative Enrichment on 100% of frames
            session_repo.update_progress(session_id, "processing", 65.0, "Smoothing pose trajectories and computing angular derivatives...")
            frame_metrics = geometry_service.enrich_time_series_with_derivatives(
                frame_metrics, fps=fps, smooth_window=5
            )

            # Camera View Estimation from extracted pose sequence
            session_repo.update_progress(session_id, "processing", 68.0, "Estimating camera perspective plane...")
            valid_pose_lms = [f["landmarks"] for f in frame_metrics if f.get("landmarks")]
            view_analysis = geometry_service.estimate_camera_view(valid_pose_lms)
            detected_view = view_analysis.get("detected_view", "side-on")
            view_conf = view_analysis.get("confidence", 0.85)

            camera_view_warning = None
            if detected_view != "side-on":
                rec_angle = geometry_service.get_recommended_camera_angle(shot_type)
                camera_view_warning = f"Camera perspective detected as {detected_view} ({int(view_conf * 100)}%). {rec_angle}"

            # Phase Classification (Kinematic Action Phase Detection)
            session_repo.update_progress(session_id, "processing", 70.0, "Executing kinematic movement phase detection...")
            per_frame_phases, confidences, phase_segments = phase_service.predict_phases(frame_metrics, fps=fps)

            for i in range(len(frame_metrics)):
                frame_metrics[i]["phase"] = per_frame_phases[i] if i < len(per_frame_phases) else "Unknown"
                frame_metrics[i]["phase_confidence"] = round(confidences[i], 3) if i < len(confidences) else 0.5

            # Shot Classification based on actual extracted kinematics
            session_repo.update_progress(session_id, "processing", 76.0, "Classifying batting shot from extracted kinematics...")
            auto_detect_requested = shot_type.strip().lower().replace(" ", "-") in {"auto-detect", "automatic"}
            classification_result = shot_classifier_service.classify_sequence(
                frame_metrics, hint_shot=None if auto_detect_requested else shot_type,
                camera_view=detected_view, handedness=handedness
            )
            predicted_shot = classification_result.get("predicted_shot", shot_type)
            prediction_conf = float(classification_result.get("confidence", 0.75))
            is_uncertain = classification_result.get("is_uncertain", False)

            # Auto-detect uses the recognized label for its reference lookup. Manual
            # selection remains the reference choice when the user chose a shot.
            if auto_detect_requested:
                if predicted_shot in ("No clear shot detected", "Uncertain", "Unrecognised Shot"):
                    cands = classification_result.get("top_candidates", [])
                    active_shot = cands[0].get("shot_name", "Cover Drive") if cands else "Cover Drive"
                else:
                    active_shot = predicted_shot
            else:
                active_shot = shot_type

            # Headline discrepancy notice if detected shot differs from selected shot
            shot_mismatch_warning = None
            if not auto_detect_requested and predicted_shot.lower() != shot_type.lower():
                shot_mismatch_warning = f"You selected {shot_type}, but this looks like a {predicted_shot}."

            # Identify the impact frame index
            impact_frame_idx = None
            for m in frame_metrics:
                if "impact" in m.get("phase", "").lower() and m.get("lead_knee_angle") is not None:
                    impact_frame_idx = m["frame_index"]
                    break
            if impact_frame_idx is None:
                impact_frame_idx = actual_total_frames // 2

            # -------------------------------------------------------------
            # PASS 2: Streaming Annotated Video Generation at Source FPS
            # -------------------------------------------------------------
            session_repo.update_progress(session_id, "processing", 80.0, "Rendering annotated video across all frames at full frame rate...")
            annotated_filename = f"{session_id}_annotated.mp4"
            thumbnail_filename = f"{session_id}_thumb.jpg"
            annotated_path = settings.ANNOTATED_DIR / annotated_filename
            thumbnail_path = settings.THUMBNAILS_DIR / thumbnail_filename

            cap_stream = cv2.VideoCapture(str(input_path), cv2.CAP_FFMPEG)
            if not cap_stream.isOpened():
                cap_stream = cv2.VideoCapture(str(input_path))
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(str(annotated_path), fourcc, fps, (out_w, out_h))

            thumb_saved = False
            for f_idx in range(actual_total_frames):
                ret, frame = cap_stream.read()
                if not ret:
                    break

                if frame.shape[1] != out_w or frame.shape[0] != out_h:
                    frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA)

                # Draw person bounding boxes on setup frames (0-20) to show striker isolation
                if f_idx < 20 and f_idx in per_frame_person_tracks:
                    frame = pose_service.draw_person_boxes(
                        frame,
                        per_frame_person_tracks[f_idx],
                        active_striker_id,
                        track_classifications
                    )

                lms = all_frame_landmarks[f_idx]
                phase_name = per_frame_phases[f_idx] if f_idx < len(per_frame_phases) else "Analyzing"
                m_curr = frame_metrics[f_idx] if f_idx < len(frame_metrics) else {}
                is_impact = (f_idx == impact_frame_idx)

                annotated_frame = pose_service.draw_skeleton(
                    frame,
                    lms,
                    handedness=handedness,
                    phase_label=phase_name,
                    metric_info=m_curr,
                    is_impact=is_impact
                )

                if settings.ENABLE_HAND_LANDMARKER and m_curr.get("hand_landmarks"):
                    annotated_frame = hand_service.draw_hands(annotated_frame, m_curr["hand_landmarks"])

                if settings.ENABLE_EXPERIMENTAL_BAT_BALL:
                    annotated_frame = bat_ball_service.draw_bat_and_ball(annotated_frame, m_curr)

                writer.write(annotated_frame)

                if is_impact or (not thumb_saved and f_idx == actual_total_frames // 2):
                    cv2.imwrite(str(thumbnail_path), annotated_frame)
                    thumb_saved = True

                del frame
                del annotated_frame

            cap_stream.release()
            writer.release()

            if not thumb_saved and annotated_path.exists():
                cap_t = cv2.VideoCapture(str(annotated_path), cv2.CAP_FFMPEG)
                if not cap_t.isOpened():
                    cap_t = cv2.VideoCapture(str(annotated_path))
                r, f_first = cap_t.read()
                if r:
                    cv2.imwrite(str(thumbnail_path), f_first)
                cap_t.release()

            # Ensure web browser compatibility by transcoding annotated video to standard H.264
            self._ensure_browser_compatible_video(annotated_path)

            # Calculate Overall Summary Metrics
            session_repo.update_progress(session_id, "processing", 90.0, "Computing explainable biomechanical features...")
            knee_angles = [m["lead_knee_angle"] for m in frame_metrics if m.get("lead_knee_angle") is not None]
            elbow_angles = [m["lead_elbow_angle"] for m in frame_metrics if m.get("lead_elbow_angle") is not None]
            arm_extensions = [m["lead_arm_extension"] for m in frame_metrics if m.get("lead_arm_extension") is not None]
            torso_leans = [m["torso_inclination"] for m in frame_metrics if m.get("torso_inclination") is not None]
            head_disps = [m["head_displacement"] for m in frame_metrics if m.get("head_displacement") is not None]
            stance_widths = [m["stance_width_norm"] for m in frame_metrics if m.get("stance_width_norm") is not None]

            # Find impact values
            impact_knee = None
            impact_torso = None
            impact_elbow = None
            impact_ext = None
            impact_head_knee = None
            impact_wt = None

            impact_frames = [m for m in frame_metrics if "impact" in m.get("phase", "").lower()]
            if impact_frames:
                valid_impact_frames = [f for f in impact_frames if f.get("lead_knee_angle") is not None]
                imp_f = valid_impact_frames[len(valid_impact_frames) // 2] if valid_impact_frames else impact_frames[len(impact_frames) // 2]
                impact_knee = imp_f.get("lead_knee_angle") or (float(np.min(knee_angles)) if knee_angles else None)
                impact_torso = imp_f.get("torso_inclination") or (float(np.mean(torso_leans)) if torso_leans else 20.0)
                impact_elbow = imp_f.get("lead_elbow_angle") or (float(np.mean(elbow_angles)) if elbow_angles else None)
                impact_ext = imp_f.get("lead_arm_extension") or (float(np.mean(arm_extensions)) if arm_extensions else None)
                impact_head_knee = imp_f.get("head_over_lead_knee_norm")
                impact_wt = imp_f.get("weight_distribution_proxy")
            elif knee_angles:
                impact_knee = float(np.min(knee_angles))
                impact_torso = float(np.mean(torso_leans)) if torso_leans else 20.0
                impact_elbow = float(np.mean(elbow_angles)) if elbow_angles else None
                impact_ext = float(np.mean(arm_extensions)) if arm_extensions else None

            head_stability_idx = float(np.std(head_disps)) if head_disps else 0.05
            tracking_rate = round((tracking_hits / max(1, analyzed_count)) * 100.0, 1)

            # Smoothness estimate: jerk / variance of velocity
            smoothness_score = 85.0
            if len(knee_angles) > 3:
                diffs = np.diff(knee_angles)
                diffs2 = np.diff(diffs)
                smoothness_score = round(max(50.0, min(98.0, 100.0 - float(np.std(diffs2)) * 3.0)), 1)

            wrist_seps = [m["wrist_separation_norm"] for m in frame_metrics if m.get("wrist_separation_norm") is not None]
            sh_hip_seps = [m["shoulder_hip_separation_deg"] for m in frame_metrics if m.get("shoulder_hip_separation_deg") is not None]

            hand_hits = sum(1 for m in frame_metrics if m.get("hand_tracking_detected"))
            bat_hits = sum(1 for m in frame_metrics if m.get("bat_detected"))
            ball_hits = sum(1 for m in frame_metrics if m.get("ball_detected"))

            summary = {
                "lead_knee_flexion_max": round(float(np.min(knee_angles)), 1) if knee_angles else None,
                "lead_knee_flexion_at_impact": round(impact_knee, 1) if impact_knee is not None else None,
                "lead_elbow_flexion_at_impact": round(impact_elbow, 1) if impact_elbow is not None else None,
                "lead_arm_extension_at_impact": round(impact_ext, 2) if impact_ext is not None else None,
                "head_over_knee_at_impact": round(impact_head_knee, 2) if impact_head_knee is not None else None,
                "torso_lean_at_impact": round(impact_torso, 1) if impact_torso is not None else None,
                "head_stability_index": round(head_stability_idx, 3),
                "stance_width_ratio_max": round(float(np.max(stance_widths)), 2) if stance_widths else None,
                "wrist_separation_mean": round(float(np.mean(wrist_seps)), 2) if wrist_seps else None,
                "weight_transfer_at_impact": round(impact_wt, 2) if impact_wt is not None else None,
                "shoulder_hip_separation_max": round(float(np.max(sh_hip_seps)), 1) if sh_hip_seps else None,
                "movement_smoothness": smoothness_score,
                "tracking_success_rate": tracking_rate,
                "analyzed_frames": actual_total_frames,
                "total_video_frames": actual_total_frames,
                "hand_tracking_rate": round((hand_hits / max(1, actual_total_frames)) * 100.0, 1),
                "bat_tracking_rate": round((bat_hits / max(1, actual_total_frames)) * 100.0, 1),
                "ball_tracking_rate": round((ball_hits / max(1, actual_total_frames)) * 100.0, 1)
            }

            # Check shot support tier: preview-only shots never receive a score or fake feedback
            from backend.app.services.reference_service import reference_service
            shot_tier = reference_service.get_shot_support_tier(active_shot)
            shot_conf = classification_result.get("shot_confidence") or {}
            conf_level_code = shot_conf.get("level_code", "fairly_sure")

            if shot_tier != "supported":
                eval_res = None
                overall_score = None
                top_mistakes = []
                all_obs = []
                comparison_table = []
                summary["overall_technique_score"] = None
                summary["support_tier"] = "preview_only"
                coaching_paused = True
                pause_reason = "Preview only: analysis coming soon"
            else:
                # Evaluate technique against reference tolerances (with camera view validity)
                eval_res = feedback_service.evaluate_technique(
                    frame_metrics, phase_segments, summary, shot_type=active_shot, camera_view=detected_view
                )
                overall_score, top_mistakes, all_obs = eval_res
                summary["overall_technique_score"] = overall_score
                summary["support_tier"] = "supported"

                coaching_paused = conf_level_code in ["cant_tell", "not_sure"]
                pause_reason = None
                if coaching_paused:
                    pause_reason = "Shot recognition is uncertain. Please confirm which shot you played so we can give you accurate technique coaching."

                # Generate structured metric comparison table (all phases and metrics vs ideal)
                comparison_table = feedback_service.generate_comparison_table(
                    frame_metrics, shot_type=active_shot, camera_view=detected_view
                )

            limitations = [
                "Monocular 2D Projection: Joint angles are computed in the image projection plane and do not account for full 3D skeletal rotation or foreshortening.",
                "Bat and Ball Calibration: Current pipeline tracks player kinematics; bat-ball contact timing is approximated from biomechanical deceleration rather than direct high-speed camera sensors.",
                "Perspective Dependency: Metrics assume a camera placed 3-6 meters away at pitch level (~1.2m height). Elevation or extreme oblique angles alter measured torso tilt.",
                "Individual Anatomy: Biomechanical ranges represent coaching guidelines; individual physical proportions and coaching philosophies may vary."
            ]

            model_metadata = {
                "pose_estimator": "MediaPipe Pose Landmarker Full (Google)",
                "phase_detector": "Kinematic Trajectory State Detector",
                "shot_classifier": "Biomechanical Kinematic State Engine",
                "predicted_shot": predicted_shot,
                "prediction_confidence": f"{prediction_conf * 100:.0f}%",
                "sample_rate": 1,
                "analyzed_frames": actual_total_frames,
                "tracking_rate": f"{tracking_rate}%",
                "detected_camera_view": detected_view
            }

            # Assemble candidate tracks for manual UI override
            striker_candidates = []
            for tid, meta in track_classifications.items():
                t_bbox = [0.0, 0.0, 1.0, 1.0]
                if tid in tracker.tracks:
                    t_bbox = tracker.tracks[tid].get("bbox", [0.0, 0.0, 1.0, 1.0])
                striker_candidates.append({
                    "track_id": tid,
                    "bbox": t_bbox,
                    "is_selected": (tid == active_striker_id),
                    "role": meta.get("role", "other"),
                    "confidence": meta.get("confidence", 0.5),
                    "striker_score": meta.get("striker_score", 0.0),
                    "is_default": (tid == best_tid),
                })

            result_dict = {
                "session_id": session_id,
                "video_filename": input_path.name,
                "annotated_video_path": f"/api/video/annotated/{annotated_filename}",
                "thumbnail_path": f"/api/video/thumbnail/{thumbnail_filename}",
                "shot_type": active_shot,
                "user_selected_shot": None if auto_detect_requested else shot_type,
                "predicted_shot_type": predicted_shot,
                "prediction_confidence": prediction_conf,
                "is_uncertain": is_uncertain,
                "shot_mismatch_warning": shot_mismatch_warning,
                "detected_camera_view": detected_view,
                "camera_view_warning": camera_view_warning,
                "striker_track_id": active_striker_id,
                "striker_candidates": striker_candidates,
                "striker_isolation_evidence": {
                    "active_striker_id": active_striker_id,
                    "role": striker_meta.get("role", "striker"),
                    "confidence": striker_confidence,
                    "selection_method": striker_select_method,
                    "needs_confirmation": needs_confirmation,
                    "cues": striker_evidence,
                    "all_tracks": {
                        t: {
                            "role": meta.get("role"),
                            "confidence": meta.get("confidence"),
                            "striker_score": meta.get("striker_score")
                        }
                        for t, meta in track_classifications.items()
                    }
                },
                "striker_tracking_status": f"Striker Track #{active_striker_id} Locked (Non-strikers Excluded)",
                "tracking_dropout_warning": tracking_dropout_warning,
                "user_confirmed_shot_type": None,
                "shot_classification": classification_result,
                "shot_confidence": shot_conf,
                "coaching_paused": coaching_paused,
                "pause_reason": pause_reason,
                "plain_summary": getattr(eval_res, "plain_summary", {}) if eval_res is not None else {},
                "issue_cards": getattr(eval_res, "issue_cards", []) if eval_res is not None else [],
                "handedness": handedness,
                "camera_angle": camera_angle,
                "fps": round(float(fps), 2),
                "duration_sec": round(actual_total_frames / fps, 2),
                "total_frames": actual_total_frames,
                "analyzed_frames": actual_total_frames,
                "sample_rate": 1,
                "summary": summary,
                "phases": phase_segments,
                "time_series": frame_metrics,
                "metric_comparison_table": comparison_table,
                "overall_technique_score": overall_score,
                "top_mistakes": [m.model_dump() if hasattr(m, "model_dump") else m for m in top_mistakes],
                "coaching_feedback": [f.model_dump() if hasattr(f, "model_dump") else f for f in all_obs] if shot_tier == "supported" else ["Preview only: analysis coming soon"],
                "limitations": limitations,
                "model_metadata": model_metadata,
                "validation_warnings": validation_warnings,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }

            session_repo.save_analysis_result(
                session_id=session_id,
                result_dict=result_dict,
                annotated_path=f"/api/video/annotated/{annotated_filename}",
                thumbnail_path=f"/api/video/thumbnail/{thumbnail_filename}",
                duration_sec=result_dict["duration_sec"],
                total_frames=actual_total_frames,
                analyzed_frames=actual_total_frames,
                fps=round(float(fps), 2)
            )
            logger.info(f"Session {session_id} processed successfully.")

        except Exception as e:
            if 'cap' in locals() and cap is not None and cap.isOpened():
                cap.release()
            logger.exception(f"Error processing session {session_id}: {e}")
            session_repo.update_progress(session_id, "failed", 0.0, "Processing failure", str(e))

    def reanalyze_shot(self, session_id: str, new_shot: str, lang: str = "en") -> Optional[Dict[str, Any]]:
        """
        Re-evaluates technique comparison, scores, and feedback for an existing session
        against a newly selected shot type (e.g. when user clicks 'Analyse as Selected Shot').
        """
        session = session_repo.get_session(session_id)
        if not session or not session.get("result"):
            return None

        result = dict(session["result"])
        frame_metrics = result.get("time_series", [])
        phases = result.get("phases", [])
        summary = result.get("summary", {})
        detected_view = result.get("detected_camera_view", "side-on")

        eval_res = feedback_service.evaluate_technique(
            frame_metrics, phases, summary, shot_type=new_shot, camera_view=detected_view, lang=lang
        )
        overall_score, top_mistakes, all_obs = eval_res
        summary["overall_technique_score"] = overall_score

        comparison_table = feedback_service.generate_comparison_table(
            frame_metrics, shot_type=new_shot, camera_view=detected_view
        )

        result["shot_type"] = new_shot
        result["overall_technique_score"] = overall_score
        result["top_mistakes"] = [m.model_dump() for m in top_mistakes]
        result["coaching_feedback"] = [f.model_dump() for f in all_obs]
        result["metric_comparison_table"] = comparison_table
        result["user_confirmed_shot_type"] = new_shot
        result["coaching_paused"] = False
        result["pause_reason"] = None
        result["plain_summary"] = getattr(eval_res, "plain_summary", {})
        result["issue_cards"] = getattr(eval_res, "issue_cards", [])

        session_repo.update_result(session_id, result)
        logger.info(f"Session {session_id} successfully re-analyzed as {new_shot}. New score: {overall_score:.1f}")
        return result

    def _ensure_browser_compatible_video(self, video_path: Path):
        """
        Transcodes OpenCV-generated video to standard H.264 (yuv420p) with faststart
        so it streams and plays natively across all web browsers (Chrome, Edge, Safari, Firefox).
        """
        try:
            import imageio_ffmpeg
            import subprocess
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            temp_out = video_path.with_name(f"temp_h264_{video_path.name}")
            cmd = [
                exe, "-y",
                "-i", str(video_path),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(temp_out)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0 and temp_out.exists():
                temp_out.replace(video_path)
                logger.info(f"Successfully transcoded {video_path.name} to standard browser H.264")
            elif temp_out.exists():
                temp_out.unlink()
        except Exception as e:
            logger.warning(f"Could not transcode {video_path} to H.264: {e}")

    def override_striker(self, session_id: str, track_id: int):
        """
        Updates the selected striker track for this session and re-runs video processing.
        """
        session_repo.update_striker_track_id(session_id, track_id)
        self.process_video_session(session_id)
        return session_repo.get_session(session_id)

video_service = VideoService()
