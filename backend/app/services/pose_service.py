import cv2
import numpy as np
import logging
import math
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


def compute_bbox_from_landmarks(landmarks: List[Any], margin: float = 0.04) -> List[float]:
    """Computes normalized [xmin, ymin, xmax, ymax] from visible landmarks."""
    xs = []
    ys = []
    for lm in landmarks:
        vis = getattr(lm, 'visibility', None)
        if vis is None and isinstance(lm, dict):
            vis = lm.get('visibility', 1.0)
        if vis is None or vis >= 0.30:
            x = getattr(lm, 'x', None) if not isinstance(lm, dict) else lm.get('x')
            y = getattr(lm, 'y', None) if not isinstance(lm, dict) else lm.get('y')
            if x is not None and y is not None:
                xs.append(x)
                ys.append(y)
    if not xs or not ys:
        return [0.0, 0.0, 1.0, 1.0]
    xmin = max(0.0, min(xs) - margin)
    ymin = max(0.0, min(ys) - margin)
    xmax = min(1.0, max(xs) + margin)
    ymax = min(1.0, max(ys) + margin)
    return [round(xmin, 4), round(ymin, 4), round(xmax, 4), round(ymax, 4)]


def calculate_iou(box1: List[float], box2: List[float]) -> float:
    """Calculates Intersection-over-Union between two [xmin, ymin, xmax, ymax] boxes."""
    x_left = max(box1[0], box2[0])
    y_top = max(box1[1], box2[1])
    x_right = min(box1[2], box2[2])
    y_bottom = min(box1[3], box2[3])

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    intersection = (x_right - x_left) * (y_bottom - y_top)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection
    return float(intersection / union) if union > 1e-6 else 0.0


class MultiPersonTracker:
    """
    Robust per-person tracker using bounding box IoU and landmark continuity.
    Calculates kinetic wrist/bat displacement to identify the striker and prevents track jumping.
    """
    def __init__(self, max_disappeared: int = 10):
        self.next_track_id = 0
        self.max_disappeared = max_disappeared
        # track_id -> dict state
        self.tracks: Dict[int, Dict[str, Any]] = {}

    def update(self, detected_poses: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """
        Updates tracks with detected poses in the current frame.
        detected_poses: list of {"landmarks": ..., "world_landmarks": ..., "bbox": ...}
        Returns active tracks dictionary for this frame.
        """
        # If no tracks exist yet, initialize tracks for all detected poses
        if not self.tracks:
            for pose in detected_poses:
                tid = self.next_track_id
                self.next_track_id += 1
                lw = pose["landmarks"][15] if len(pose["landmarks"]) > 15 else None
                rw = pose["landmarks"][16] if len(pose["landmarks"]) > 16 else None
                lw_pt = (getattr(lw, 'x', 0.0), getattr(lw, 'y', 0.0)) if lw else None
                rw_pt = (getattr(rw, 'x', 0.0), getattr(rw, 'y', 0.0)) if rw else None
                self.tracks[tid] = {
                    "track_id": tid,
                    "bbox": pose["bbox"],
                    "landmarks": pose["landmarks"],
                    "world_landmarks": pose.get("world_landmarks"),
                    "disappeared": 0,
                    "last_wrists": (lw_pt, rw_pt),
                    "wrist_motion_total": 0.0,
                    "peak_wrist_vel": 0.0,
                    "history_frames": 1,
                    "is_lost": False
                }
            return self.tracks

        if not detected_poses:
            for tid, tr in list(self.tracks.items()):
                tr["disappeared"] += 1
                if tr["disappeared"] > self.max_disappeared:
                    tr["is_lost"] = True
            return self.tracks

        # Compute cost matrix between active tracks and detections
        track_ids = list(self.tracks.keys())
        matches = []
        unmatched_detections = set(range(len(detected_poses)))
        unmatched_tracks = set(track_ids)

        for tid in track_ids:
            tr = self.tracks[tid]
            b1 = tr["bbox"]
            c1 = ((b1[0] + b1[2]) / 2.0, (b1[1] + b1[3]) / 2.0)
            best_det_idx = None
            best_score = -999.0

            for d_idx in unmatched_detections:
                b2 = detected_poses[d_idx]["bbox"]
                c2 = ((b2[0] + b2[2]) / 2.0, (b2[1] + b2[3]) / 2.0)
                iou = calculate_iou(b1, b2)
                dist = math.hypot(c1[0] - c2[0], c1[1] - c2[1])
                # Combined score: IoU heavily rewarded, distance penalized
                score = iou * 2.0 - dist
                if (iou > 0.10 or dist < 0.28) and score > best_score:
                    best_score = score
                    best_det_idx = d_idx

            if best_det_idx is not None and best_det_idx in unmatched_detections:
                matches.append((tid, best_det_idx))
                unmatched_detections.remove(best_det_idx)
                unmatched_tracks.remove(tid)

        # Update matched tracks
        for tid, d_idx in matches:
            pose = detected_poses[d_idx]
            tr = self.tracks[tid]
            tr["bbox"] = pose["bbox"]
            tr["landmarks"] = pose["landmarks"]
            tr["world_landmarks"] = pose.get("world_landmarks")
            tr["disappeared"] = 0
            tr["is_lost"] = False
            tr["history_frames"] += 1

            # Accumulate wrist kinetic motion
            lw = pose["landmarks"][15] if len(pose["landmarks"]) > 15 else None
            rw = pose["landmarks"][16] if len(pose["landmarks"]) > 16 else None
            curr_lw = (getattr(lw, 'x', 0.0), getattr(lw, 'y', 0.0)) if lw else None
            curr_rw = (getattr(rw, 'x', 0.0), getattr(rw, 'y', 0.0)) if rw else None

            prev_lw, prev_rw = tr["last_wrists"]
            frame_disp = 0.0
            if curr_lw and prev_lw:
                frame_disp += math.hypot(curr_lw[0] - prev_lw[0], curr_lw[1] - prev_lw[1])
            if curr_rw and prev_rw:
                frame_disp += math.hypot(curr_rw[0] - prev_rw[0], curr_rw[1] - prev_rw[1])

            tr["wrist_motion_total"] += frame_disp
            tr["peak_wrist_vel"] = max(tr["peak_wrist_vel"], frame_disp)
            tr["last_wrists"] = (curr_lw, curr_rw)

        # Unmatched existing tracks
        for tid in unmatched_tracks:
            tr = self.tracks[tid]
            tr["disappeared"] += 1
            if tr["disappeared"] > self.max_disappeared:
                tr["is_lost"] = True

        # Unmatched new detections (add as new tracks)
        for d_idx in unmatched_detections:
            tid = self.next_track_id
            self.next_track_id += 1
            pose = detected_poses[d_idx]
            lw = pose["landmarks"][15] if len(pose["landmarks"]) > 15 else None
            rw = pose["landmarks"][16] if len(pose["landmarks"]) > 16 else None
            lw_pt = (getattr(lw, 'x', 0.0), getattr(lw, 'y', 0.0)) if lw else None
            rw_pt = (getattr(rw, 'x', 0.0), getattr(rw, 'y', 0.0)) if rw else None
            self.tracks[tid] = {
                "track_id": tid,
                "bbox": pose["bbox"],
                "landmarks": pose["landmarks"],
                "world_landmarks": pose.get("world_landmarks"),
                "disappeared": 0,
                "last_wrists": (lw_pt, rw_pt),
                "wrist_motion_total": 0.0,
                "peak_wrist_vel": 0.0,
                "history_frames": 1,
                "is_lost": False
            }

        return self.tracks


class PoseService:
    def __init__(self, model_asset_path: Optional[Path] = None):
        self.model_asset_path = str(model_asset_path or settings.MODEL_ASSET_PATH)
        self.landmarker = None
        self._init_landmarker()

    def _init_landmarker(self):
        try:
            import mediapipe as mp
            from mediapipe.tasks.python import vision, BaseOptions

            if not Path(self.model_asset_path).exists():
                logger.warning(f"PoseLandmarker asset not found at {self.model_asset_path}. Pose estimation disabled until asset downloaded.")
                return

            # Support multi-pose detection (up to 4 persons simultaneously)
            options = vision.PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=self.model_asset_path),
                running_mode=vision.RunningMode.IMAGE,
                num_poses=4,
                min_pose_detection_confidence=0.35,
                min_pose_presence_confidence=0.35,
                min_tracking_confidence=0.35
            )
            self.landmarker = vision.PoseLandmarker.create_from_options(options)
            logger.info("MediaPipe Multi-PoseLandmarker (num_poses=4) initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize PoseLandmarker: {e}")
            self.landmarker = None

    def detect_frame_multi(self, bgr_frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Runs multi-person pose detection on a single BGR frame.
        Returns a list of detected person dictionaries with landmarks, world_landmarks, and bbox.
        """
        if self.landmarker is None or bgr_frame is None:
            return []

        try:
            import mediapipe as mp
            h, w = bgr_frame.shape[:2]
            proc_frame = bgr_frame
            if max(h, w) > 960:
                s = 960.0 / max(h, w)
                proc_frame = cv2.resize(bgr_frame, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
            rgb_frame = np.ascontiguousarray(cv2.cvtColor(proc_frame, cv2.COLOR_BGR2RGB))
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection_result = self.landmarker.detect(mp_image)

            if not detection_result or not detection_result.pose_landmarks:
                return []

            results = []
            world_lms_list = detection_result.pose_world_landmarks or []

            for idx, lms in enumerate(detection_result.pose_landmarks):
                world_lms = world_lms_list[idx] if idx < len(world_lms_list) else None
                bbox = compute_bbox_from_landmarks(lms)
                results.append({
                    "landmarks": lms,
                    "world_landmarks": world_lms,
                    "bbox": bbox
                })

            return results
        except Exception as e:
            logger.warning(f"Multi-pose detection frame error: {e}")
            return []

    def detect_frame(self, bgr_frame: np.ndarray) -> Optional[List[Any]]:
        """
        Backward-compatible single-pose detector.
        Returns landmarks of the primary detected person.
        """
        multi = self.detect_frame_multi(bgr_frame)
        if multi:
            return multi[0]["landmarks"]
        return None

    def inspect_strikers(self, video_path: Path, max_scan_frames: int = 90) -> Dict[str, Any]:
        """
        Scans initial frames of a video to detect candidate batters,
        computes kinetic wrist motion across the initial window,
        and identifies the suggested striker with candidate bounding boxes on frame 0.
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return {"candidates": [], "default_track_id": 0, "total_persons": 0}

        try:
            ret, frame0 = cap.read()
            if not ret or frame0 is None:
                return {"candidates": [], "default_track_id": 0, "total_persons": 0}

            h, w = frame0.shape[:2]
            tracker = MultiPersonTracker(max_disappeared=10)

            # Detect poses in frame 0
            poses0 = self.detect_frame_multi(frame0)
            tracker.update(poses0)

            # Scan up to max_scan_frames to measure wrist kinetic motion
            frame_idx = 1
            while frame_idx < max_scan_frames:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break
                poses = self.detect_frame_multi(frame)
                tracker.update(poses)
                frame_idx += 1
        finally:
            cap.release()

        # Build candidate summaries across all observed tracks in the initial window
        all_track_ids = list(tracker.tracks.keys())
        candidates = []
        best_tid = all_track_ids[0] if all_track_ids else 0
        best_motion = -1.0

        for tid in all_track_ids:
            tr = tracker.tracks.get(tid, {})
            motion = tr.get("wrist_motion_total", 0.0) + tr.get("peak_wrist_vel", 0.0) * 2.0
            if motion > best_motion:
                best_motion = motion
                best_tid = tid

        for tid in all_track_ids:
            tr = tracker.tracks.get(tid, {})
            bbox = tr.get("bbox", [0.0, 0.0, 1.0, 1.0])
            is_default = (tid == best_tid)
            candidates.append({
                "track_id": tid,
                "bbox": bbox,
                "is_default": is_default,
                "is_suggested_striker": is_default,
                "role": "Suggested Striker (Peak Motion)" if is_default else "Other Person / Non-Striker",
                "wrist_motion_score": round(tr.get("wrist_motion_total", 0.0), 3)
            })

        return {
            "candidates": candidates,
            "default_track_id": best_tid,
            "total_persons": len(candidates),
            "frame_width": w,
            "frame_height": h
        }

    def draw_skeleton(
        self,
        bgr_frame: np.ndarray,
        landmarks: Optional[List[Any]],
        handedness: str = "Right",
        phase_label: str = "Analyzing"
    ) -> np.ndarray:
        """
        Render clean cricket-analytics skeleton overlay on the frame.
        Renders ONLY the active striker's skeleton.
        """
        annotated = bgr_frame
        h, w = annotated.shape[:2]

        if not landmarks or len(landmarks) < 33:
            cv2.putText(
                annotated,
                "Pose tracking: Striker occluded / low visibility",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 165, 255),
                2,
                cv2.LINE_AA
            )
            return annotated

        connections = [
            (0, 11), (0, 12),
            (11, 12), (11, 23), (12, 24), (23, 24),
            (11, 13), (13, 15),
            (12, 14), (14, 16),
            (23, 25), (25, 27), (27, 31),
            (24, 26), (26, 28), (28, 32)
        ]

        def get_coords(idx: int):
            lm = landmarks[idx]
            vis = getattr(lm, 'visibility', 1.0)
            if vis is not None and vis < 0.30:
                return None
            x = getattr(lm, 'x', None)
            y = getattr(lm, 'y', None)
            if x is None and isinstance(lm, dict):
                x, y = lm.get('x'), lm.get('y')
            if x is None or y is None:
                return None
            return (int(x * w), int(y * h))

        for (idx1, idx2) in connections:
            pt1 = get_coords(idx1)
            pt2 = get_coords(idx2)
            if pt1 and pt2:
                if idx1 in (23, 25, 27, 31) and idx2 in (23, 25, 27, 31):
                    color = (0, 230, 100) if handedness.lower() != "left" else (0, 160, 255)
                elif idx1 in (24, 26, 28, 32) and idx2 in (24, 26, 28, 32):
                    color = (0, 160, 255) if handedness.lower() != "left" else (0, 230, 100)
                elif idx1 in (11, 12, 23, 24) and idx2 in (11, 12, 23, 24):
                    color = (255, 220, 50)
                else:
                    color = (255, 150, 0)

                cv2.line(annotated, pt1, pt2, color, 3, cv2.LINE_AA)

        key_indices = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 31, 32]
        for idx in key_indices:
            pt = get_coords(idx)
            if pt:
                cv2.circle(annotated, pt, 5, (255, 255, 255), -1, cv2.LINE_AA)
                cv2.circle(annotated, pt, 3, (15, 23, 42), -1, cv2.LINE_AA)

        # Draw Top HUD Banner
        overlay = annotated.copy()
        cv2.rectangle(overlay, (10, 10), (340, 65), (15, 23, 42), -1)
        cv2.addWeighted(overlay, 0.75, annotated, 0.25, 0, annotated)

        cv2.putText(
            annotated,
            f"CricketIQ | Striker Track Locked",
            (20, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.50,
            (56, 189, 248),
            2,
            cv2.LINE_AA
        )
        cv2.putText(
            annotated,
            f"Phase: {phase_label} | Handedness: {handedness}",
            (20, 54),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (148, 163, 184),
            1,
            cv2.LINE_AA
        )

        return annotated


pose_service = PoseService()
