import cv2
import math
import logging
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class HandService:
    """
    Dedicated Hand & Finger Landmarker Service using Google MediaPipe HandLandmarker (21 keypoints per hand).
    Extracts individual finger joints, calculates grip closure score, hand orientation,
    and flags occlusion / low-resolution unreliability.
    """
    # 21 Hand Landmark Indices
    WRIST = 0
    THUMB_CMC = 1; THUMB_MCP = 2; THUMB_IP = 3; THUMB_TIP = 4
    INDEX_MCP = 5; INDEX_PIP = 6; INDEX_DIP = 7; INDEX_TIP = 8
    MIDDLE_MCP = 9; MIDDLE_PIP = 10; MIDDLE_DIP = 11; MIDDLE_TIP = 12
    RING_MCP = 13; RING_PIP = 14; RING_DIP = 15; RING_TIP = 16
    PINKY_MCP = 17; PINKY_PIP = 18; PINKY_DIP = 19; PINKY_TIP = 20

    FINGER_TIPS = [4, 8, 12, 16, 20]
    FINGER_MCPS = [2, 5, 9, 13, 17]

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or settings.HAND_MODEL_PATH
        self.landmarker = None
        self._init_landmarker()

    def _init_landmarker(self):
        if not self.model_path.exists():
            logger.warning(f"Hand landmarker asset not found at {self.model_path}. Hand tracking disabled.")
            return

        try:
            with open(self.model_path, "rb") as f:
                model_data = f.read()
            base_options = python.BaseOptions(model_asset_buffer=model_data)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=2,
                min_hand_detection_confidence=0.40,
                min_hand_presence_confidence=0.40,
                min_tracking_confidence=0.40
            )
            self.landmarker = vision.HandLandmarker.create_from_options(options)
            logger.info("MediaPipe HandLandmarker initialized successfully.")
        except (RuntimeError, ValueError, FileNotFoundError, OSError) as e:
            logger.exception(f"Failed to initialize MediaPipe HandLandmarker: {e}")
            self.landmarker = None

    def detect_hands(self, bgr_frame: np.ndarray, handedness: str = "Right") -> Dict[str, Any]:
        """
        Runs hand tracking on a BGR video frame.
        Returns detailed finger kinematics, grip closure, and reliability indicators.
        """
        fallback: Dict[str, Any] = {
            "hand_tracking_detected": False,
            "num_hands": 0,
            "lead_hand_detected": False,
            "rear_hand_detected": False,
            "lead_hand_grip_closure": None,
            "rear_hand_grip_closure": None,
            "lead_hand_orientation_deg": None,
            "rear_hand_orientation_deg": None,
            "hands_detail": [],
            "reliability_note": "Hand landmarker not active or no hands detected."
        }

        if self.landmarker is None or bgr_frame is None:
            return fallback

        try:
            h, w = bgr_frame.shape[:2]
            proc_frame = bgr_frame
            if max(h, w) > 960:
                s = 960.0 / max(h, w)
                proc_frame = cv2.resize(bgr_frame, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
            rgb_frame = np.ascontiguousarray(cv2.cvtColor(proc_frame, cv2.COLOR_BGR2RGB))
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection = self.landmarker.detect(mp_image)

            if not detection or not detection.hand_landmarks or len(detection.hand_landmarks) == 0:
                fallback["reliability_note"] = "No hands detected in frame (hands occluded or out of view)."
                return fallback

            hands_list = []
            for h_idx, lms in enumerate(detection.hand_landmarks):
                # Extract 21 points
                pts = [{"x": round(lm.x, 4), "y": round(lm.y, 4), "z": round(lm.z, 4)} for lm in lms]
                
                # Check resolution & overlapping
                w_pt = pts[self.WRIST]
                m_mcp = pts[self.MIDDLE_MCP]
                palm_length = math.hypot(m_mcp["x"] - w_pt["x"], m_mcp["y"] - w_pt["y"])
                
                # If palm is too tiny in the frame, resolution is insufficient for finger analysis
                is_reliable = True
                diag = "Valid grip detection"
                if palm_length < 0.025:
                    is_reliable = False
                    diag = "Hand resolution too small in frame for reliable individual finger tracking."
                
                # Calculate Grip Closure Score [0.0 - 1.0]
                # Ratio of distance from fingertips to wrist vs full extended finger length
                closures = []
                for tip_idx, mcp_idx in zip(self.FINGER_TIPS, self.FINGER_MCPS):
                    tip = pts[tip_idx]
                    mcp = pts[mcp_idx]
                    dist_to_wrist = math.hypot(tip["x"] - w_pt["x"], tip["y"] - w_pt["y"])
                    finger_span = math.hypot(tip["x"] - mcp["x"], tip["y"] - mcp["y"])
                    # Lower distance to wrist indicates curled finger (tight grip)
                    if palm_length > 1e-4:
                        curled_ratio = min(1.0, max(0.0, 1.0 - (dist_to_wrist / (palm_length * 1.8))))
                        closures.append(curled_ratio)
                
                grip_closure = float(np.mean(closures)) if closures else 0.5

                # Calculate Hand Orientation relative to vertical (0, -1)
                dx = m_mcp["x"] - w_pt["x"]
                dy = m_mcp["y"] - w_pt["y"]
                orient_angle = math.degrees(math.atan2(dx, -dy)) # 0 deg = pointing straight up

                # Check handedness label if available from MediaPipe
                hand_label = "Hand"
                if detection.handedness and h_idx < len(detection.handedness):
                    cat = detection.handedness[h_idx][0]
                    hand_label = cat.category_name # "Left" or "Right"

                hands_list.append({
                    "hand_index": h_idx,
                    "label": hand_label,
                    "palm_length_norm": round(palm_length, 4),
                    "grip_closure": round(grip_closure, 3),
                    "orientation_deg": round(orient_angle, 1),
                    "is_reliable": is_reliable,
                    "diagnostic": diag,
                    "landmarks": pts
                })

            lead_hand = hands_list[0] if hands_list else None
            rear_hand = hands_list[1] if len(hands_list) > 1 else None

            lead_closure = lead_hand["grip_closure"] if lead_hand else None
            rear_closure = rear_hand["grip_closure"] if rear_hand else None
            lead_orient = lead_hand["orientation_deg"] if lead_hand else None
            rear_orient = rear_hand["orientation_deg"] if rear_hand else None

            return {
                "hand_tracking_detected": True,
                "num_hands": len(hands_list),
                "lead_hand_detected": lead_hand is not None,
                "rear_hand_detected": rear_hand is not None,
                "lead_hand_grip_closure": lead_closure,
                "rear_hand_grip_closure": rear_closure,
                "lead_hand_orientation_deg": lead_orient,
                "rear_hand_orientation_deg": rear_orient,
                "hands_detail": hands_list,
                "reliability_note": "Hand landmarks extracted. Grip metrics indicative of visible 2D closure."
            }

        except (cv2.error, ValueError, RuntimeError, TypeError) as e:
            logger.exception(f"Hand detection error: {e}")
            fallback["reliability_note"] = f"Inference exception: {str(e)}"
            return fallback

    def draw_hands(self, bgr_frame: np.ndarray, hands_data: Dict[str, Any]) -> np.ndarray:
        """
        Renders clean 21-point hand skeletons on the frame.
        """
        if not hands_data.get("hand_tracking_detected") or not hands_data.get("hands_detail"):
            return bgr_frame

        canvas = bgr_frame
        h, w = canvas.shape[:2]

        connections = [
            (0, 1), (1, 2), (2, 3), (3, 4),       # Thumb
            (0, 5), (5, 6), (6, 7), (7, 8),       # Index
            (5, 9), (9, 10), (10, 11), (11, 12),  # Middle
            (9, 13), (13, 14), (14, 15), (15, 16),# Ring
            (13, 17), (17, 18), (18, 19), (19, 20),# Pinky
            (0, 17)                                # Palm base
        ]

        for hand in hands_data["hands_detail"]:
            pts = hand.get("landmarks", [])
            if len(pts) < 21:
                continue

            color = (0, 230, 100) if hand.get("is_reliable") else (180, 180, 180)
            for c1, c2 in connections:
                p1 = (int(pts[c1]["x"] * w), int(pts[c1]["y"] * h))
                p2 = (int(pts[c2]["x"] * w), int(pts[c2]["y"] * h))
                cv2.line(canvas, p1, p2, color, 1, cv2.LINE_AA)

            for p in pts:
                cx, cy = int(p["x"] * w), int(p["y"] * h)
                cv2.circle(canvas, (cx, cy), 2, (255, 255, 255), -1, cv2.LINE_AA)

        return canvas

hand_service = HandService()
