import os
import time
import math
import base64
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
import cv2
import json
import urllib.request
import urllib.error

try:
    import requests
except ImportError:
    requests = None

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Valid classes trained on the Roboflow dataset
VALID_CLASSES = {"batter", "bowler", "non_striker", "bat", "ball", "stumps"}


@dataclass
class Detection:
    class_name: str
    confidence: float
    bbox: List[float]  # [xmin, ymin, xmax, ymax] normalized to [0.0, 1.0]
    bbox_px: List[int]  # [xmin, ymin, xmax, ymax] in integer frame pixels
    center: Tuple[float, float]  # (cx, cy) normalized
    center_px: Tuple[int, int]  # (cx, cy) in integer frame pixels
    width: float  # normalized width
    height: float  # normalized height
    class_id: Optional[int] = None
    detection_id: Optional[str] = None


@dataclass
class DetectionTrack:
    track_id: int
    class_name: str
    last_bbox: List[float]
    last_seen_frame: int
    history: Dict[int, List[float]] = field(default_factory=dict)  # frame_idx -> bbox
    bat_overlap_count: int = 0
    stumps_distance_sum: float = 0.0
    stumps_distance_samples: int = 0
    total_area_sum: float = 0.0
    total_frames: int = 0

    @property
    def avg_area(self) -> float:
        return self.total_area_sum / max(1, self.total_frames)

    @property
    def avg_stumps_distance(self) -> float:
        if self.stumps_distance_samples == 0:
            return 1.0
        return self.stumps_distance_sum / self.stumps_distance_samples


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


class DetectorService:
    """
    Roboflow Hosted Object Detection Service.
    Queries RF-DETR model for classes: batter, bowler, non_striker, bat, ball, stumps.
    - Encodes frames as JPEG (max 640px)
    - Timeout + 2 retries with exponential backoff
    - Call counting and hard quota cap per video
    - Graceful fallback when unavailable (never raises through upload)
    """

    def __init__(self):
        self.last_call_success: Optional[bool] = None
        self.last_call_error: Optional[str] = None
        self.last_call_timestamp: Optional[float] = None
        self.total_api_calls_session: int = 0

    def is_configured(self) -> bool:
        """Returns True if the Roboflow API key and Model ID are configured."""
        return bool(settings.ROBOFLOW_API_KEY and settings.ROBOFLOW_MODEL_ID)

    def get_health_status(self) -> Dict[str, Any]:
        """Returns detector health info for /api/health without leaking the API key."""
        configured = self.is_configured()
        return {
            "configured": configured,
            "model_id": settings.ROBOFLOW_MODEL_ID if configured else None,
            "base_url": settings.ROBOFLOW_BASE_URL if configured else None,
            "confidence_threshold": settings.ROBOFLOW_CONFIDENCE_THRESHOLD,
            "max_calls_per_video": settings.ROBOFLOW_MAX_CALLS_PER_VIDEO,
            "last_call_success": self.last_call_success,
            "last_call_error": self.last_call_error,
            "status": "ready" if (configured and (self.last_call_success is not False)) else ("degraded" if configured else "unconfigured")
        }

    def detect_frame(
        self,
        frame: np.ndarray,
        call_counter: Optional[Dict[str, int]] = None
    ) -> Tuple[List[Detection], str]:
        """
        Sends a single BGR frame to Roboflow hosted inference API.
        Returns (detections, status_code_string).
        status_code_string: "ok" | "unconfigured" | "quota_capped" | "network_error" | "auth_error" | "api_error"
        """
        if not self.is_configured():
            return [], "unconfigured"

        # Check call cap per video
        max_calls = settings.ROBOFLOW_MAX_CALLS_PER_VIDEO
        if call_counter is not None:
            current_calls = call_counter.get("count", 0)
            if current_calls >= max_calls:
                logger.warning(f"Roboflow call cap reached ({current_calls}/{max_calls} calls). Skipping API call.")
                return [], "quota_capped"

        # Downscale frame to max 640px wide if necessary
        h, w = frame.shape[:2]
        proc_frame = frame
        if max(h, w) > 640:
            scale = 640.0 / max(h, w)
            proc_frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        # Encode to JPEG
        success, buffer = cv2.imencode(".jpg", proc_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            logger.warning("Failed to encode frame as JPEG for Roboflow detector.")
            return [], "encode_error"

        img_b64 = base64.b64encode(buffer).decode("ascii")
        url = f"{settings.ROBOFLOW_BASE_URL}/{settings.ROBOFLOW_MODEL_ID}"
        headers = {
            "Authorization": f"Bearer {settings.ROBOFLOW_API_KEY}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Retry up to 2 times with backoff
        max_retries = 2
        last_err_msg = ""
        timeout_sec = settings.ROBOFLOW_TIMEOUT_SEC

        for attempt in range(max_retries + 1):
            if attempt > 0:
                backoff_time = 0.5 * (2 ** (attempt - 1))
                time.sleep(backoff_time)
                logger.info(f"Retrying Roboflow inference (attempt {attempt + 1}/{max_retries + 1})...")

            try:
                t0 = time.time()
                status_code = 0
                raw_data = {}
                resp_text = ""

                if requests is not None:
                    resp = requests.post(url, data=img_b64, headers=headers, timeout=timeout_sec)
                    status_code = resp.status_code
                    if status_code == 200:
                        raw_data = resp.json()
                    else:
                        resp_text = resp.text[:120]
                else:
                    req = urllib.request.Request(
                        url,
                        data=img_b64.encode("ascii"),
                        headers=headers,
                        method="POST"
                    )
                    try:
                        with urllib.request.urlopen(req, timeout=timeout_sec) as u_resp:
                            status_code = u_resp.status
                            raw_data = json.loads(u_resp.read().decode("utf-8"))
                    except urllib.error.HTTPError as h_err:
                        status_code = h_err.code
                        resp_text = h_err.read().decode("utf-8", errors="ignore")[:120]

                elapsed = time.time() - t0

                # Count this attempt
                if call_counter is not None:
                    call_counter["count"] = call_counter.get("count", 0) + 1
                self.total_api_calls_session += 1

                if status_code == 200:
                    self.last_call_success = True
                    self.last_call_error = None
                    self.last_call_timestamp = time.time()

                    detections = self._parse_predictions(raw_data.get("predictions", []), orig_w=w, orig_h=h)
                    logger.info(
                        f"Roboflow API call #{call_counter.get('count', 1) if call_counter else 1}: "
                        f"{len(detections)} objects detected in {elapsed * 1000:.1f}ms."
                    )
                    return detections, "ok"

                elif status_code in (401, 403):
                    last_err_msg = f"Unauthorized (HTTP {status_code}): Invalid ROBOFLOW_API_KEY."
                    logger.error(f"Roboflow detector auth error: {last_err_msg}")
                    self.last_call_success = False
                    self.last_call_error = "auth_error"
                    return [], "auth_error"

                elif status_code == 404:
                    last_err_msg = f"Model ID '{settings.ROBOFLOW_MODEL_ID}' not found on endpoint (HTTP 404)."
                    logger.error(f"Roboflow detector model error: {last_err_msg}")
                    self.last_call_success = False
                    self.last_call_error = "model_not_found"
                    return [], "model_not_found"

                elif status_code == 429:
                    last_err_msg = "Quota or rate limit exceeded (HTTP 429)."
                    logger.warning(f"Roboflow detector quota error: {last_err_msg}")
                    self.last_call_success = False
                    self.last_call_error = "quota_exceeded"
                    return [], "quota_exceeded"

                else:
                    last_err_msg = f"HTTP {status_code}: {resp_text}"
                    logger.warning(f"Roboflow API warning: {last_err_msg}")

            except (TimeoutError, urllib.error.URLError) as net_err:
                last_err_msg = f"Network/Connection error: {type(net_err).__name__}"
                logger.warning(f"Roboflow network error (attempt {attempt + 1}): {last_err_msg}")
            except Exception as ex:
                if requests is not None and isinstance(ex, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                    last_err_msg = f"Network/Connection error: {type(ex).__name__}"
                else:
                    last_err_msg = f"{type(ex).__name__}: {str(ex)}"
                logger.warning(f"Roboflow request exception (attempt {attempt + 1}): {last_err_msg}")

        self.last_call_success = False
        self.last_call_error = last_err_msg
        return [], "api_error"

    def _parse_predictions(
        self,
        predictions: List[Dict[str, Any]],
        orig_w: int,
        orig_h: int
    ) -> List[Detection]:
        """Parses raw Roboflow prediction dictionary into typed Detection dataclass."""
        detections: List[Detection] = []
        conf_thresh = settings.ROBOFLOW_CONFIDENCE_THRESHOLD

        for p in predictions:
            confidence = float(p.get("confidence", 0.0))
            if confidence < conf_thresh:
                continue

            raw_cls = str(p.get("class", "unknown")).lower().strip().replace(" ", "_").replace("-", "_")
            cx = float(p.get("x", 0.0))
            cy = float(p.get("y", 0.0))
            bw = float(p.get("width", 0.0))
            bh = float(p.get("height", 0.0))

            xmin_px = int(round(max(0, cx - bw / 2.0)))
            ymin_px = int(round(max(0, cy - bh / 2.0)))
            xmax_px = int(round(min(orig_w, cx + bw / 2.0)))
            ymax_px = int(round(min(orig_h, cy + bh / 2.0)))

            # Normalized coordinates [0.0, 1.0]
            xmin = round(max(0.0, min(1.0, xmin_px / orig_w)), 4)
            ymin = round(max(0.0, min(1.0, ymin_px / orig_h)), 4)
            xmax = round(max(0.0, min(1.0, xmax_px / orig_w)), 4)
            ymax = round(max(0.0, min(1.0, ymax_px / orig_h)), 4)

            norm_cx = round(cx / orig_w, 4)
            norm_cy = round(cy / orig_h, 4)
            norm_w = round(bw / orig_w, 4)
            norm_h = round(bh / orig_h, 4)

            detections.append(Detection(
                class_name=raw_cls,
                confidence=round(confidence, 4),
                bbox=[xmin, ymin, xmax, ymax],
                bbox_px=[xmin_px, ymin_px, xmax_px, ymax_px],
                center=(norm_cx, norm_cy),
                center_px=(int(round(cx)), int(round(cy))),
                width=norm_w,
                height=norm_h,
                class_id=p.get("class_id"),
                detection_id=p.get("detection_id")
            ))

        return detections

    def track_detections(
        self,
        per_frame_detections: Dict[int, List[Detection]],
        iou_threshold: float = 0.30
    ) -> Dict[int, DetectionTrack]:
        """
        Builds temporal person tracks across frames using IoU matching.
        Tracks are maintained for 'batter', 'bowler', and 'non_striker'.
        """
        tracks: Dict[int, DetectionTrack] = {}
        next_track_id = 0

        for f_idx in sorted(per_frame_detections.keys()):
            frame_dets = per_frame_detections[f_idx]
            person_dets = [d for d in frame_dets if d.class_name in ("batter", "bowler", "non_striker")]

            matched_track_ids = set()
            matched_det_indices = set()

            # Attempt IoU matching with active tracks seen recently (within last 15 frames)
            for d_idx, det in enumerate(person_dets):
                best_iou = 0.0
                best_tid = None
                for tid, tr in tracks.items():
                    if tid in matched_track_ids:
                        continue
                    if f_idx - tr.last_seen_frame > 15:
                        continue
                    iou = calculate_iou(det.bbox, tr.last_bbox)
                    if iou > best_iou:
                        best_iou = iou
                        best_tid = tid

                if best_iou >= iou_threshold and best_tid is not None:
                    tr = tracks[best_tid]
                    tr.last_bbox = det.bbox
                    tr.last_seen_frame = f_idx
                    tr.history[f_idx] = det.bbox
                    tr.total_frames += 1
                    area = (det.bbox[2] - det.bbox[0]) * (det.bbox[3] - det.bbox[1])
                    tr.total_area_sum += area
                    matched_track_ids.add(best_tid)
                    matched_det_indices.add(d_idx)

            # Create new tracks for unmatched person detections
            for d_idx, det in enumerate(person_dets):
                if d_idx not in matched_det_indices:
                    area = (det.bbox[2] - det.bbox[0]) * (det.bbox[3] - det.bbox[1])
                    tracks[next_track_id] = DetectionTrack(
                        track_id=next_track_id,
                        class_name=det.class_name,
                        last_bbox=det.bbox,
                        last_seen_frame=f_idx,
                        history={f_idx: det.bbox},
                        total_frames=1,
                        total_area_sum=area
                    )
                    next_track_id += 1

        return tracks

    def select_striker(
        self,
        tracks: Dict[int, DetectionTrack],
        per_frame_detections: Dict[int, List[Detection]],
        per_frame_landmarks: Optional[Dict[int, Any]] = None
    ) -> Tuple[Optional[int], str, Dict[str, Any]]:
        """
        Isolates the striker among tracked persons according to the strict criteria:
        1. MUST be of class 'batter'. (Never select bowler or non_striker).
        2. Track with most frames where a 'bat' box overlaps their wrist area (MediaPipe wrists).
        3. Break ties by larger average box area and closeness to 'stumps'.
        4. If two batter tracks score close together or 0 batter tracks detected:
           return (None, "striker_unclear", details).
        """
        # Step 1: Filter tracks strictly for class 'batter'
        batter_tracks = [tr for tr in tracks.values() if tr.class_name == "batter"]

        if not batter_tracks:
            return None, "striker_unclear", {
                "reason": "No 'batter' class tracks detected by object detector.",
                "candidate_count": 0,
                "candidates": []
            }

        # Step 2: Compute bat-wrist overlaps and stumps proximity across frames
        for f_idx, dets in per_frame_detections.items():
            bat_boxes = [d.bbox for d in dets if d.class_name == "bat"]
            stump_boxes = [d.bbox for d in dets if d.class_name == "stumps"]
            lms = (per_frame_landmarks or {}).get(f_idx)

            for tr in batter_tracks:
                if f_idx not in tr.history:
                    continue
                batter_box = tr.history[f_idx]

                # Stumps proximity
                if stump_boxes:
                    s_box = stump_boxes[0]
                    scx = (s_box[0] + s_box[2]) / 2.0
                    scy = (s_box[1] + s_box[3]) / 2.0
                    bcx = (batter_box[0] + batter_box[2]) / 2.0
                    bcy = (batter_box[1] + batter_box[3]) / 2.0
                    dist = math.hypot(scx - bcx, scy - bcy)
                    tr.stumps_distance_sum += dist
                    tr.stumps_distance_samples += 1

                # Bat overlap with wrist area
                if bat_boxes:
                    for bat_box in bat_boxes:
                        # Check if bat box intersects batter box
                        if calculate_iou(batter_box, bat_box) > 0.05:
                            # If landmarks are available, verify overlap with wrist area
                            if lms and len(lms) >= 17:
                                lw = lms[15]
                                rw = lms[16]
                                lwx = getattr(lw, "x", lw.get("x", 0.0) if isinstance(lw, dict) else 0.0)
                                lwy = getattr(lw, "y", lw.get("y", 0.0) if isinstance(lw, dict) else 0.0)
                                rwx = getattr(rw, "x", rw.get("x", 0.0) if isinstance(rw, dict) else 0.0)
                                rwy = getattr(rw, "y", rw.get("y", 0.0) if isinstance(rw, dict) else 0.0)

                                margin = 0.06
                                left_in_bat = (bat_box[0] - margin <= lwx <= bat_box[2] + margin and
                                               bat_box[1] - margin <= lwy <= bat_box[3] + margin)
                                right_in_bat = (bat_box[0] - margin <= rwx <= bat_box[2] + margin and
                                                bat_box[1] - margin <= rwy <= bat_box[3] + margin)

                                if left_in_bat or right_in_bat:
                                    tr.bat_overlap_count += 1
                                    break
                            else:
                                tr.bat_overlap_count += 1
                                break

        # Step 3: Score and rank candidate batters
        # Primary score: bat_overlap_count * 10.0 + total_frames * 0.1
        candidates = []
        for tr in batter_tracks:
            score = (
                (tr.bat_overlap_count * 10.0)
                + (tr.avg_area * 5.0)
                + ((1.0 - min(1.0, tr.avg_stumps_distance)) * 3.0)
                + (tr.total_frames * 0.2)
            )
            candidates.append({
                "track_id": tr.track_id,
                "class_name": tr.class_name,
                "score": round(score, 2),
                "bat_overlaps": tr.bat_overlap_count,
                "total_frames": tr.total_frames,
                "avg_area": round(tr.avg_area, 4),
                "avg_stumps_dist": round(tr.avg_stumps_distance, 3)
            })

        # Sort descending by score
        candidates.sort(key=lambda c: c["score"], reverse=True)

        # Step 4: Check for ambiguity / unclear striker
        if len(candidates) >= 2:
            top = candidates[0]
            second = candidates[1]
            score_diff = abs(top["score"] - second["score"])
            # If two batters are close (e.g. difference <= 2.0 and both have bat overlaps or both 0)
            if score_diff <= 2.0:
                logger.info(f"Striker selection unclear: Track #{top['track_id']} ({top['score']}) vs Track #{second['track_id']} ({second['score']}).")
                return None, "striker_unclear", {
                    "reason": f"Two batter candidates scored within close margin ({top['score']} vs {second['score']}).",
                    "candidate_count": len(candidates),
                    "candidates": candidates
                }

        best = candidates[0]
        logger.info(f"Striker locked: Track #{best['track_id']} (score: {best['score']}, bat_overlaps: {best['bat_overlaps']})")
        return best["track_id"], "locked", {
            "selected_track_id": best["track_id"],
            "score": best["score"],
            "frames_selected": best["total_frames"],
            "bat_overlaps": best["bat_overlaps"],
            "candidates": candidates
        }

    def draw_detections(
        self,
        bgr_frame: np.ndarray,
        detections: List[Detection],
        active_striker_id: Optional[int] = None
    ) -> np.ndarray:
        """
        Draws bounding boxes and labels for Roboflow detections on setup frames.
        Striker is highlighted in green, bowler in orange (excluded), non-striker in slate.
        Bat, ball, and stumps have distinct clear colors.
        """
        annotated = bgr_frame.copy()
        h, w = annotated.shape[:2]

        for det in detections:
            x1 = max(0, int(round(det.bbox[0] * w)))
            y1 = max(0, int(round(det.bbox[1] * h)))
            x2 = min(w - 1, int(round(det.bbox[2] * w)))
            y2 = min(h - 1, int(round(det.bbox[3] * h)))

            cls = det.class_name
            if cls == "batter":
                box_color = (53, 234, 127)  # Vibrant green
                tag_text = f"STRIKER (ID #{active_striker_id or 0}) - LOCKED"
                border_w = 2
            elif cls == "bowler":
                box_color = (0, 140, 255)  # Orange
                tag_text = "BOWLER - EXCLUDED"
                border_w = 1
            elif cls == "non_striker":
                box_color = (200, 180, 100)  # Slate
                tag_text = "NON-STRIKER - EXCLUDED"
                border_w = 1
            elif cls == "bat":
                box_color = (255, 230, 0)  # Cyan
                tag_text = f"BAT ({int(det.confidence * 100)}%)"
                border_w = 2
            elif cls == "ball":
                box_color = (0, 255, 255)  # Yellow
                tag_text = f"BALL ({int(det.confidence * 100)}%)"
                border_w = 1
            elif cls == "stumps":
                box_color = (255, 0, 255)  # Purple
                tag_text = f"STUMPS ({int(det.confidence * 100)}%)"
                border_w = 1
            else:
                box_color = (160, 160, 160)
                tag_text = cls.upper()
                border_w = 1

            cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, border_w)

            # Draw tag banner above box
            tag_w = len(tag_text) * 7 + 10
            tag_y1 = max(0, y1 - 18)
            cv2.rectangle(annotated, (x1, tag_y1), (min(w - 1, x1 + tag_w), y1), (15, 23, 42), -1)
            cv2.putText(annotated, tag_text, (x1 + 4, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, box_color, 1, cv2.LINE_AA)

        return annotated


# Singleton service instance
detector_service = DetectorService()
