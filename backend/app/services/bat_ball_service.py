import cv2
import math
import logging
import numpy as np
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class BatBallService:
    """
    Modular Computer Vision Engine for Cricket Bat and Ball Detection & Trajectory Tracking.
    Operates modularly: if bat or ball are not detectable or occluded, safely flags them as
    untracked rather than fabricating synthetic telemetry.
    """

    def __init__(self):
        self.prev_bat_tip = None
        self.prev_bat_angle = None
        self.prev_timestamp = None

    def reset(self):
        self.prev_bat_tip = None
        self.prev_bat_angle = None
        self.prev_timestamp = None

    def detect_bat_and_ball(
        self,
        bgr_frame: np.ndarray,
        wrist_pts: Optional[List[Tuple[float, float]]] = None,
        torso_scale: float = 0.3,
        timestamp_sec: float = 0.0
    ) -> Dict[str, Any]:
        """
        Analyzes a single frame for cricket bat orientation and ball trajectory.
        wrist_pts: optional list of [(lead_wrist_x, lead_wrist_y), (rear_wrist_x, rear_wrist_y)] in [0, 1] coords.
        torso_scale: anthropometric scale for normalization.
        """
        fallback: Dict[str, Any] = {
            "bat_detected": False,
            "bat_confidence": 0.0,
            "bat_angle_deg": None,
            "bat_tip_x": None,
            "bat_tip_y": None,
            "bat_handle_x": None,
            "bat_handle_y": None,
            "bat_speed_norm": None,
            "ball_detected": False,
            "ball_confidence": 0.0,
            "ball_x": None,
            "ball_y": None,
            "ball_speed_proxy": None,
            "bat_ball_proximity": None,
            "contact_window_estimated": False,
            "tracking_note": "No bat or ball detected in frame."
        }

        if bgr_frame is None:
            return fallback

        h, w = bgr_frame.shape[:2]
        dt = (timestamp_sec - self.prev_timestamp) if (self.prev_timestamp is not None and timestamp_sec > self.prev_timestamp) else 0.033

        # -------------------------------------------------------------
        # 1. Bat Detection: Linear Segment Anchored near Wrists
        # -------------------------------------------------------------
        bat_detected = False
        bat_conf = 0.0
        bat_angle_deg = None
        bat_tip = None
        bat_handle = None
        bat_speed_norm = None

        if wrist_pts and any(pt is not None for pt in wrist_pts):
            valid_wrists = [pt for pt in wrist_pts if pt is not None]
            wx = float(np.mean([pt[0] for pt in valid_wrists])) * w
            wy = float(np.mean([pt[1] for pt in valid_wrists])) * h

            # Crop Region of Interest (ROI) around wrists extending downward/outward
            roi_radius = int(min(h, w) * 0.45)
            x1 = max(0, int(wx - roi_radius))
            y1 = max(0, int(wy - roi_radius * 0.3))
            x2 = min(w, int(wx + roi_radius))
            y2 = min(h, int(wy + roi_radius * 1.5))

            if (x2 - x1) > 20 and (y2 - y1) > 20:
                roi = bgr_frame[y1:y2, x1:x2]
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                blurred = cv2.GaussianBlur(gray_roi, (5, 5), 0)
                edges = cv2.Canny(blurred, 40, 120)

                # Hough Line Transform to detect primary linear blade edges
                lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=35, minLineLength=int(roi_radius * 0.3), maxLineGap=15)
                
                if lines is not None and len(lines) > 0:
                    best_line = None
                    max_len = 0.0
                    for l in lines:
                        coords = l[0] if len(l.shape) > 1 else l
                        lx1, ly1, lx2, ly2 = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])
                        line_len = math.hypot(lx2 - lx1, ly2 - ly1)
                        if line_len > max_len:
                            max_len = line_len
                            best_line = (lx1 + x1, ly1 + y1, lx2 + x1, ly2 + y1)

                    if best_line and max_len > (roi_radius * 0.3):
                        bx1, by1, bx2, by2 = best_line
                        # Determine handle (closer to wrist) and tip (further from wrist)
                        d1 = math.hypot(bx1 - wx, by1 - wy)
                        d2 = math.hypot(bx2 - wx, by2 - wy)
                        if d1 < d2:
                            handle_pt = (bx1, by1)
                            tip_pt = (bx2, by2)
                        else:
                            handle_pt = (bx2, by2)
                            tip_pt = (bx1, by1)

                        bat_handle = (round(handle_pt[0] / w, 4), round(handle_pt[1] / h, 4))
                        bat_tip = (round(tip_pt[0] / w, 4), round(tip_pt[1] / h, 4))

                        # Bat angle relative to vertical (0, -1)
                        dx = bat_tip[0] - bat_handle[0]
                        dy = bat_tip[1] - bat_handle[1]
                        angle_rad = math.atan2(dx, -dy) # 0 = pointing straight down, 180 = pointing straight up
                        bat_angle_deg = round(math.degrees(angle_rad), 1)

                        # Calculate tip speed
                        if self.prev_bat_tip and dt > 1e-4:
                            tip_disp = math.hypot(bat_tip[0] - self.prev_bat_tip[0], bat_tip[1] - self.prev_bat_tip[1])
                            bat_speed_norm = round(float((tip_disp / dt) / max(0.1, torso_scale)), 2)

                        bat_detected = True
                        bat_conf = round(min(0.92, 0.40 + (max_len / roi_radius) * 0.5), 2)
                        self.prev_bat_tip = bat_tip
                        self.prev_bat_angle = bat_angle_deg

        # -------------------------------------------------------------
        # 2. Ball Detection: Spherical Motion & Color in Delivery Corridor
        # -------------------------------------------------------------
        ball_detected = False
        ball_conf = 0.0
        ball_pt = None
        bat_ball_prox = None
        contact_window = False

        gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
        blurred_full = cv2.GaussianBlur(gray, (7, 7), 1.5)
        
        # Hough Circles for spherical cricket ball candidate (downscaled for efficiency & stability)
        circles = None
        try:
            max_dim = 640
            scale_f = 1.0
            if max(h, w) > max_dim:
                scale_f = max_dim / float(max(h, w))
                small_blurred = cv2.resize(blurred_full, (int(w * scale_f), int(h * scale_f)))
            else:
                small_blurred = blurred_full

            sh, sw = small_blurred.shape[:2]
            c_det = cv2.HoughCircles(
                small_blurred,
                cv2.HOUGH_GRADIENT,
                dp=1.2,
                minDist=max(15, int(40 * scale_f)),
                param1=80,
                param2=28,
                minRadius=max(3, int(min(sh, sw) * 0.012)),
                maxRadius=max(10, int(min(sh, sw) * 0.05))
            )
            if c_det is not None and len(c_det) > 0:
                circles = c_det / scale_f
        except (cv2.error, ValueError) as e:
            logger.debug(f"Ball HoughCircles search skipped: {e}")
            circles = None

        if circles is not None and len(circles) > 0:
            circles = np.uint16(np.around(circles))
            # Pick circle closest to batting zone or wrist zone
            best_c = None
            min_dist = float('inf')
            ref_x, ref_y = (w * 0.5, h * 0.5)
            if bat_tip:
                ref_x, ref_y = bat_tip[0] * w, bat_tip[1] * h

            for c in circles[0, :]:
                cx, cy, cr = c[0], c[1], c[2]
                dist = math.hypot(cx - ref_x, cy - ref_y)
                if dist < min_dist:
                    min_dist = dist
                    best_c = (cx, cy, cr)

            if best_c:
                cx, cy, cr = best_c
                ball_pt = (round(cx / w, 4), round(cy / h, 4))
                ball_detected = True
                ball_conf = 0.75

                if bat_tip:
                    bat_ball_prox = round(math.hypot(ball_pt[0] - bat_tip[0], ball_pt[1] - bat_tip[1]) / max(0.1, torso_scale), 3)
                    # Contact window if ball is within 0.35 torso lengths from bat blade
                    if bat_ball_prox < 0.35:
                        contact_window = True

        self.prev_timestamp = timestamp_sec

        note = []
        if bat_detected:
            note.append(f"Bat tracked (angle: {bat_angle_deg}°)")
        else:
            note.append("Bat not detected / occluded")
        if ball_detected:
            note.append(f"Ball detected (prox: {bat_ball_prox})")
        else:
            note.append("Ball motion blur / untracked")

        return {
            "bat_detected": bat_detected,
            "bat_confidence": bat_conf,
            "bat_angle_deg": bat_angle_deg,
            "bat_tip_x": bat_tip[0] if bat_tip else None,
            "bat_tip_y": bat_tip[1] if bat_tip else None,
            "bat_handle_x": bat_handle[0] if bat_handle else None,
            "bat_handle_y": bat_handle[1] if bat_handle else None,
            "bat_speed_norm": bat_speed_norm,
            "ball_detected": ball_detected,
            "ball_confidence": ball_conf,
            "ball_x": ball_pt[0] if ball_pt else None,
            "ball_y": ball_pt[1] if ball_pt else None,
            "ball_speed_proxy": None,
            "bat_ball_proximity": bat_ball_prox,
            "contact_window_estimated": contact_window,
            "tracking_note": " • ".join(note)
        }

    def draw_bat_and_ball(self, bgr_frame: np.ndarray, tracking_data: Dict[str, Any]) -> np.ndarray:
        """
        Renders HUD overlays for bat axis and ball circle.
        """
        canvas = bgr_frame
        h, w = canvas.shape[:2]

        if tracking_data.get("bat_detected"):
            bx1 = tracking_data.get("bat_handle_x")
            by1 = tracking_data.get("bat_handle_y")
            bx2 = tracking_data.get("bat_tip_x")
            by2 = tracking_data.get("bat_tip_y")
            if bx1 is not None and by1 is not None and bx2 is not None and by2 is not None:
                p1 = (int(bx1 * w), int(by1 * h))
                p2 = (int(bx2 * w), int(by2 * h))
                # Glowing bat spine
                cv2.line(canvas, p1, p2, (0, 180, 255), 4, cv2.LINE_AA)
                cv2.circle(canvas, p2, 6, (0, 230, 255), -1, cv2.LINE_AA)
                ang = tracking_data.get("bat_angle_deg")
                cv2.putText(canvas, f"Bat: {ang}°", (p2[0] + 8, p2[1] - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 230, 255), 1, cv2.LINE_AA)

        if tracking_data.get("ball_detected"):
            bx = tracking_data.get("ball_x")
            by = tracking_data.get("ball_y")
            if bx is not None and by is not None:
                center = (int(bx * w), int(by * h))
                cv2.circle(canvas, center, 8, (0, 60, 255), 2, cv2.LINE_AA)
                cv2.circle(canvas, center, 3, (0, 60, 255), -1, cv2.LINE_AA)
                cv2.putText(canvas, "Ball", (center[0] + 10, center[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 60, 255), 1, cv2.LINE_AA)

        return canvas

bat_ball_service = BatBallService()
