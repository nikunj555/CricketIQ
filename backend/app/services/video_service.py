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

        if duration_sec < 0.8:
            warnings.append(
                f"Very short clip ({duration_sec:.2f}s). At least 0.8 s of footage (≈ 24 frames @ 30fps) "
                "is recommended to capture the full batting stroke cycle."
            )
        elif duration_sec > 120.0:
            warnings.append(
                f"Long clip ({duration_sec:.1f}s). Only the first {settings.MAX_FRAMES_TO_PROCESS} frames "
                "will be analysed. Trim the video to the relevant stroke sequence for best results."
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
        1. Read frames
        2. MediaPipe Pose Landmark extraction
        3. Geometric feature calculation
        4. Temporal Action Phase Recognition (BiLSTM / Heuristic)
        5. Skeleton-annotated video rendering
        6. Summary metric computation
        7. Evidence-based coaching feedback generation
        8. Database persistence
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
            # Propagate validation warnings to result metadata
            validation_warnings = val_info.get("warnings", [])

            # Frame sampling for performance
            sample_rate = 1
            if total_frames > 240:
                sample_rate = 2
            if total_frames > 500:
                sample_rate = 3

            cap = cv2.VideoCapture(str(input_path))
            annotated_filename = f"{session_id}_annotated.mp4"
            thumbnail_filename = f"{session_id}_thumb.jpg"
            annotated_path = settings.ANNOTATED_DIR / annotated_filename
            thumbnail_path = settings.THUMBNAILS_DIR / thumbnail_filename

            # Constrain frame dimensions to max 640 for lightweight memory footprint
            max_proc_dim = 640
            scale = 1.0
            if max(width, height) > max_proc_dim:
                scale = max_proc_dim / float(max(width, height))
            out_w = int(round(width * scale))
            out_h = int(round(height * scale))
            out_w = out_w if out_w % 2 == 0 else out_w - 1
            out_h = out_h if out_h % 2 == 0 else out_h - 1

            # Setup VideoWriter
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            effective_fps = max(10.0, fps / sample_rate)
            writer = cv2.VideoWriter(str(annotated_path), fourcc, effective_fps, (out_w, out_h))

            raw_frames = []
            extracted_landmarks = []
            frame_metrics: List[Dict[str, Any]] = []

            # Multi-person tracker for tracking striker without switching candidates
            tracker = MultiPersonTracker(max_disappeared=15)
            active_striker_id = striker_track_id

            # Check for ground-truth kinematic data (e.g. for reference clips and calibrated seed sessions)
            gt_file = input_path.parent / f"{input_path.stem}_groundtruth.json"
            groundtruth_data = None
            if gt_file.exists():
                try:
                    import json
                    with open(gt_file, "r") as f:
                        groundtruth_data = json.load(f)
                    logger.info(f"Loaded {len(groundtruth_data)} ground-truth frames for {input_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to load groundtruth file {gt_file.name}: {e}")

            session_repo.update_progress(session_id, "processing", 15.0, "Extracting pose landmarks...")

            frame_idx = 0
            analyzed_count = 0
            tracking_hits = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % sample_rate == 0:
                    analyzed_count += 1
                    if scale < 1.0:
                        frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA)
                    raw_frames.append(frame)
                    
                    # Multi-person MediaPipe pose extraction
                    multi_poses = pose_service.detect_frame_multi(frame)
                    current_tracks = tracker.update(multi_poses)

                    # Determine and lock the striker on frame 0 or initial frames
                    if active_striker_id is None and current_tracks:
                        if striker_tap_coords and len(striker_tap_coords) >= 2:
                            tx, ty = float(striker_tap_coords[0]), float(striker_tap_coords[1])
                            best_dist = 999.0
                            best_tid = None
                            for tid, tr in current_tracks.items():
                                bx1, by1, bx2, by2 = tr["bbox"]
                                if bx1 <= tx <= bx2 and by1 <= ty <= by2:
                                    best_tid = tid
                                    break
                                cx = (bx1 + bx2) / 2.0
                                cy = (by1 + by2) / 2.0
                                dist = math.hypot(cx - tx, cy - ty)
                                if dist < best_dist:
                                    best_dist = dist
                                    best_tid = tid
                            active_striker_id = best_tid
                        else:
                            # Default: pick track with highest kinetic motion or first track
                            active_striker_id = max(current_tracks.keys(), key=lambda t: current_tracks[t].get("wrist_motion_total", 0.0))

                    # Lock landmark extraction exclusively to active_striker_id
                    lms = None
                    world_lms = None
                    if active_striker_id is not None and active_striker_id in current_tracks and not current_tracks[active_striker_id].get("is_lost"):
                        lms = current_tracks[active_striker_id]["landmarks"]
                        world_lms = current_tracks[active_striker_id].get("world_landmarks")
                    elif current_tracks and len(current_tracks) == 1:
                        # Fallback for single track
                        single_tr = next(iter(current_tracks.values()))
                        lms = single_tr["landmarks"]
                        world_lms = single_tr.get("world_landmarks")

                    # If calibrated ground truth is available for this reference clip, prioritize calibrated landmarks
                    if groundtruth_data and frame_idx < len(groundtruth_data):
                        gt_lms = groundtruth_data[frame_idx].get("landmarks")
                        if gt_lms and len(gt_lms) >= 33:
                            lms = gt_lms
                        elif not lms or len(lms) < 33:
                            lms = gt_lms

                    extracted_landmarks.append(lms)
                    
                    # Kinematic calculation (passing 3D world landmarks)
                    m = geometry_service.extract_frame_metrics(lms, handedness=handedness, world_landmarks=world_lms)
                    m["frame_index"] = analyzed_count - 1
                    m["timestamp_sec"] = round(frame_idx / fps, 3)
                    if lms:
                        m["landmarks"] = [
                            {
                                "x": round(float(getattr(lm, "x", None) if not isinstance(lm, dict) else lm.get("x", 0.0)), 4),
                                "y": round(float(getattr(lm, "y", None) if not isinstance(lm, dict) else lm.get("y", 0.0)), 4),
                                "v": round(float(getattr(lm, "visibility", 1.0) if not isinstance(lm, dict) else lm.get("visibility", 1.0)), 3)
                            }
                            for lm in lms
                        ]
                    else:
                        m["landmarks"] = []
                    
                    if m["pose_detected"]:
                        tracking_hits += 1

                    # If groundtruth includes bat kinematics, update bat tracking
                    if groundtruth_data and frame_idx < len(groundtruth_data):
                        gt_frame = groundtruth_data[frame_idx]
                        if gt_frame.get("bat_angle_deg") is not None:
                            m["bat_detected"] = True
                            m["bat_angle_deg"] = gt_frame["bat_angle_deg"]
                            m["bat_tip_x"] = gt_frame.get("bat_tip_x")
                            m["bat_tip_y"] = gt_frame.get("bat_tip_y")
                            m["bat_speed_norm"] = 1.2

                    # Dedicated Hand Tracking
                    hands_info = hand_service.detect_hands(frame, handedness=handedness)
                    m["hand_tracking_detected"] = hands_info.get("hand_tracking_detected", False)
                    m["lead_hand_detected"] = hands_info.get("lead_hand_detected", False)
                    m["rear_hand_detected"] = hands_info.get("rear_hand_detected", False)
                    m["lead_hand_grip_closure"] = hands_info.get("lead_hand_grip_closure")
                    m["rear_hand_grip_closure"] = hands_info.get("rear_hand_grip_closure")
                    m["hand_landmarks"] = hands_info

                    # Modular Bat and Ball Tracking
                    wrist_pts = []
                    if m.get("lead_wrist_x") is not None and m.get("lead_wrist_y") is not None:
                        wrist_pts.append((m["lead_wrist_x"], m["lead_wrist_y"]))
                    if m.get("rear_wrist_x") is not None and m.get("rear_wrist_y") is not None:
                        wrist_pts.append((m["rear_wrist_x"], m["rear_wrist_y"]))

                    scale = m.get("head_displacement") or 0.3
                    bat_ball_info = bat_ball_service.detect_bat_and_ball(
                        frame,
                        wrist_pts=wrist_pts,
                        torso_scale=scale,
                        timestamp_sec=m["timestamp_sec"]
                    )
                    m["bat_detected"] = bat_ball_info.get("bat_detected", False)
                    m["bat_angle_deg"] = bat_ball_info.get("bat_angle_deg")
                    m["bat_tip_x"] = bat_ball_info.get("bat_tip_x")
                    m["bat_tip_y"] = bat_ball_info.get("bat_tip_y")
                    m["bat_speed_norm"] = bat_ball_info.get("bat_speed_norm")
                    m["ball_detected"] = bat_ball_info.get("ball_detected", False)
                    m["ball_x"] = bat_ball_info.get("ball_x")
                    m["ball_y"] = bat_ball_info.get("ball_y")
                    m["bat_ball_proximity"] = bat_ball_info.get("bat_ball_proximity")
                        
                    frame_metrics.append(m)

                    # Update progress every 20 frames
                    if analyzed_count % 15 == 0:
                        pct = 15.0 + min(50.0, (frame_idx / max(1, total_frames)) * 50.0)
                        session_repo.update_progress(
                            session_id, "processing", round(pct, 1),
                            f"Analyzing frame {analyzed_count} (pose tracking active)..."
                        )

                frame_idx += 1
                if analyzed_count >= settings.MAX_FRAMES_TO_PROCESS:
                    break

            cap.release()

            if analyzed_count == 0:
                session_repo.update_progress(session_id, "failed", 0.0, "No frames could be extracted from video.")
                writer.release()
                return

            # ── Post-Upload Validation: Pose Detection Quality Gate ────────────────
            detected_poses = sum(1 for f in frame_metrics if f.get("pose_detected"))
            detection_rate = detected_poses / float(analyzed_count)
            if detection_rate < 0.55:
                reject_reason = (
                    f"Video rejected: Player pose was detected in only {detection_rate * 100:.1f}% of frames "
                    f"(minimum required: 55.0%). Possible causes: camera is too far away, lighting is too dark, "
                    f"or the batter's full body (head to feet) was cut off by the camera frame."
                )
                session_repo.update_progress(session_id, "failed", 0.0, reject_reason)
                writer.release()
                return

            # ── Temporal Smoothing & Derivative Enrichment ─────────────────────────
            # Smooth pose trajectories and compute angular velocity + acceleration
            # for the ENTIRE sequence at once (after all frames have been extracted).
            session_repo.update_progress(session_id, "processing", 65.0, "Smoothing pose trajectories and computing angular derivatives...")
            frame_metrics = geometry_service.enrich_time_series_with_derivatives(
                frame_metrics, fps=effective_fps, smooth_window=5
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
            per_frame_phases, confidences, phase_segments = phase_service.predict_phases(frame_metrics, fps=effective_fps)

            for i in range(len(frame_metrics)):
                frame_metrics[i]["phase"] = per_frame_phases[i] if i < len(per_frame_phases) else "Unknown"
                frame_metrics[i]["phase_confidence"] = round(confidences[i], 3) if i < len(confidences) else 0.5

            # Shot Classification based on actual extracted kinematics
            session_repo.update_progress(session_id, "processing", 76.0, "Classifying batting shot from extracted kinematics...")
            classification_result = shot_classifier_service.classify_sequence(
                frame_metrics, hint_shot=shot_type, camera_view=detected_view, handedness=handedness
            )
            predicted_shot = classification_result.get("predicted_shot", shot_type)
            prediction_conf = float(classification_result.get("confidence", 0.75))

            # User-selected shot is always the source of truth; never silently override
            active_shot = shot_type

            # Soft warning if classifier top prediction disagrees with selection with strong confidence
            shot_mismatch_warning = None
            if predicted_shot.lower() != shot_type.lower() and prediction_conf >= 0.65:
                shot_mismatch_warning = f"This looks more like a {predicted_shot} ({int(prediction_conf * 100)}%). Analyse as {shot_type}?"

            # Render Annotated Frames & write to video (rendering ONLY the selected striker)
            session_repo.update_progress(session_id, "processing", 80.0, "Rendering skeleton overlay...")
            thumb_saved = False
            for i, frame in enumerate(raw_frames):
                phase_name = per_frame_phases[i] if i < len(per_frame_phases) else "Analyzing"
                lms = extracted_landmarks[i]
                annotated_frame = pose_service.draw_skeleton(frame, lms, handedness=handedness, phase_label=phase_name)
                
                # Draw hands overlay if detected
                m_curr = frame_metrics[i] if i < len(frame_metrics) else {}
                if m_curr.get("hand_landmarks"):
                    annotated_frame = hand_service.draw_hands(annotated_frame, m_curr["hand_landmarks"])

                # Draw bat and ball overlay if detected
                annotated_frame = bat_ball_service.draw_bat_and_ball(annotated_frame, m_curr)

                writer.write(annotated_frame)

                # Save thumbnail at impact or middle frame
                if not thumb_saved and (("impact" in phase_name.lower()) or (i == len(raw_frames) // 2)):
                    cv2.imwrite(str(thumbnail_path), annotated_frame)
                    thumb_saved = True

            writer.release()
            
            # Ensure web browser compatibility by transcoding annotated video to standard H.264
            self._ensure_browser_compatible_video(annotated_path)

            if not thumb_saved and raw_frames:
                cv2.imwrite(str(thumbnail_path), raw_frames[0])

            # Free frame memory immediately
            raw_frames.clear()
            gc.collect()

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
                "analyzed_frames": analyzed_count,
                "total_video_frames": total_frames,
                "hand_tracking_rate": round((hand_hits / max(1, analyzed_count)) * 100.0, 1),
                "bat_tracking_rate": round((bat_hits / max(1, analyzed_count)) * 100.0, 1),
                "ball_tracking_rate": round((ball_hits / max(1, analyzed_count)) * 100.0, 1)
            }

            # Evaluate technique against reference tolerances (with camera view validity)
            overall_score, top_mistakes, all_obs = feedback_service.evaluate_technique(
                frame_metrics, phase_segments, summary, shot_type=active_shot, camera_view=detected_view
            )
            summary["overall_technique_score"] = overall_score

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
                "sample_rate": sample_rate,
                "analyzed_frames": analyzed_count,
                "tracking_rate": f"{tracking_rate}%",
                "detected_camera_view": detected_view
            }

            result_dict = {
                "session_id": session_id,
                "video_filename": input_path.name,
                "annotated_video_path": f"/api/video/annotated/{annotated_filename}",
                "thumbnail_path": f"/api/video/thumbnail/{thumbnail_filename}",
                "shot_type": active_shot,
                "predicted_shot_type": predicted_shot,
                "prediction_confidence": prediction_conf,
                "shot_mismatch_warning": shot_mismatch_warning,
                "detected_camera_view": detected_view,
                "camera_view_warning": camera_view_warning,
                "striker_track_id": active_striker_id,
                "user_confirmed_shot_type": None,
                "shot_classification": classification_result,
                "handedness": handedness,
                "camera_angle": camera_angle,
                "fps": effective_fps,
                "duration_sec": round(analyzed_count / effective_fps, 2),
                "total_frames": total_frames,
                "analyzed_frames": analyzed_count,
                "sample_rate": sample_rate,
                "summary": summary,
                "phases": phase_segments,
                "time_series": frame_metrics,
                "metric_comparison_table": comparison_table,
                "overall_technique_score": overall_score,
                "top_mistakes": [m.model_dump() for m in top_mistakes],
                "coaching_feedback": [f.model_dump() for f in all_obs],
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
                total_frames=total_frames,
                analyzed_frames=analyzed_count,
                fps=effective_fps
            )
            logger.info(f"Session {session_id} processed successfully.")

        except Exception as e:
            if 'cap' in locals() and cap is not None and cap.isOpened():
                cap.release()
            logger.exception(f"Error processing session {session_id}: {e}")
            session_repo.update_progress(session_id, "failed", 0.0, "Processing failure", str(e))

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
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(temp_out)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
            if res.returncode == 0 and temp_out.exists():
                temp_out.replace(video_path)
                logger.info(f"Successfully transcoded {video_path.name} to standard browser H.264")
            elif temp_out.exists():
                temp_out.unlink()
        except Exception as e:
            logger.warning(f"Could not transcode {video_path} to H.264: {e}")

video_service = VideoService()
