import math
import numpy as np
from typing import Optional, Tuple, Dict, Any, List

try:
    from scipy.signal import savgol_filter
    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False

class GeometryService:
    """
    Biomechanical vector geometry and kinematic metric calculations
    from 2D/3D human pose landmarks.
    
    Coordinate System Conventions:
    - Standard normalized camera coordinates: x in [0, 1] (left to right), y in [0, 1] (top to bottom).
    - Image-plane vertical axis: Vector (0, -1) points upward toward the sky.
    - Image-plane horizontal axis: Vector (1, 0) points to the right.
    
    Biomechanical Limitations:
    - All measurements are monocular 2D image-plane projections unless explicitly calibrated.
    - True 3D joint rotations outside the sagittal/frontal projection planes suffer from foreshortening.
    """
    
    # Key MediaPipe landmark indices
    NOSE = 0
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32

    MIN_VISIBILITY_THRESHOLD = 0.40

    @staticmethod
    def calculate_angle_2d(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> Optional[float]:
        """
        Calculate angle at p2 formed by lines (p1-p2) and (p3-p2) in degrees [0, 180].
        Returns None if any vector is degenerate (zero length).
        """
        if p1 is None or p2 is None or p3 is None:
            return None
            
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]], dtype=float)
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]], dtype=float)
        
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 < 1e-6 or norm2 < 1e-6:
            return None
            
        cosine = np.dot(v1, v2) / (norm1 * norm2)
        cosine = np.clip(cosine, -1.0, 1.0)
        angle_rad = np.arccos(cosine)
        return float(np.degrees(angle_rad))

    @staticmethod
    def calculate_angle_3d(p1: Tuple[float, float, float], p2: Tuple[float, float, float], p3: Tuple[float, float, float]) -> Optional[float]:
        """
        Calculate 3D joint angle at p2 formed by vectors (p1-p2) and (p3-p2) in degrees [0, 180].
        Incorporates MediaPipe estimated depth coordinates to alleviate 2D camera perspective foreshortening.
        """
        if p1 is None or p2 is None or p3 is None:
            return None
            
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1], p1[2] - p2[2]], dtype=float)
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1], p3[2] - p2[2]], dtype=float)
        
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 < 1e-6 or norm2 < 1e-6:
            return None
            
        cosine = np.dot(v1, v2) / (norm1 * norm2)
        cosine = np.clip(cosine, -1.0, 1.0)
        return float(np.degrees(np.arccos(cosine)))

    @staticmethod
    def calculate_inclination_from_vertical(p_base: Tuple[float, float], p_top: Tuple[float, float]) -> Optional[float]:
        """
        Calculate the angle in degrees between the line (p_base -> p_top) and the upward vertical axis (0, -1).
        0° means perfectly vertical upright.
        Positive angle indicates deviation/tilt from vertical.
        """
        if p_base is None or p_top is None:
            return None
            
        # Direction vector from base (e.g. hip) to top (e.g. shoulder)
        dx = p_top[0] - p_base[0]
        dy = p_top[1] - p_base[1]
        
        # Upward vertical vector in image coordinates: (0, -1)
        # Length of vector
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return None
            
        # Dot product with (0, -1) = -dy
        cos_angle = -dy / length
        cos_angle = max(-1.0, min(1.0, cos_angle))
        return float(math.degrees(math.acos(cos_angle)))

    @staticmethod
    def calculate_tilt_from_horizontal(p1: Tuple[float, float], p2: Tuple[float, float]) -> Optional[float]:
        """
        Calculate the absolute tilt angle in degrees relative to the horizontal axis (1, 0).
        0° means perfectly horizontal.
        """
        if p1 is None or p2 is None:
            return None
            
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return None
            
        angle_rad = math.atan2(abs(dy), abs(dx))
        return float(math.degrees(angle_rad))

    @staticmethod
    def calculate_extension_ratio(
        p_shoulder: Optional[Tuple[float, float]],
        p_elbow: Optional[Tuple[float, float]],
        p_wrist: Optional[Tuple[float, float]]
    ) -> Optional[float]:
        """
        Calculate arm extension ratio in [0.0, 1.0].
        Ratio = distance(shoulder, wrist) / (length(upper_arm) + length(forearm)).
        1.0 = fully extended straight arm, ~0.7 = 90 degree flexion.
        """
        if p_shoulder is None or p_elbow is None or p_wrist is None:
            return None
        upper_len = math.hypot(p_elbow[0] - p_shoulder[0], p_elbow[1] - p_shoulder[1])
        fore_len = math.hypot(p_wrist[0] - p_elbow[0], p_wrist[1] - p_elbow[1])
        total_arm = upper_len + fore_len
        if total_arm < 1e-5:
            return None
        span = math.hypot(p_wrist[0] - p_shoulder[0], p_wrist[1] - p_shoulder[1])
        return float(min(1.0, max(0.0, span / total_arm)))

    CAMERA_VIEW_METRIC_VALIDITY = {
        "side-on": {
            "lead_knee_flexion": "MEASURED",
            "rear_knee_flexion": "MEASURED",
            "lead_elbow_flexion": "MEASURED",
            "torso_inclination": "MEASURED",
            "head_over_knee": "MEASURED",
            "stance_width": "MEASURED",
            "lateral_balance": "UNAVAILABLE",
            "shoulder_alignment": "ESTIMATED",
        },
        "front-on": {
            "lead_knee_flexion": "UNAVAILABLE",  # Sagittal knee flexion foreshortened in frontal plane
            "rear_knee_flexion": "UNAVAILABLE",
            "lead_elbow_flexion": "MEASURED",
            "torso_inclination": "ESTIMATED",
            "head_over_knee": "MEASURED",
            "stance_width": "MEASURED",
            "lateral_balance": "MEASURED",
            "shoulder_alignment": "MEASURED",
        },
        "oblique": {
            "lead_knee_flexion": "ESTIMATED",   # 3D world reconstructed
            "rear_knee_flexion": "ESTIMATED",
            "lead_elbow_flexion": "MEASURED",
            "torso_inclination": "MEASURED",
            "head_over_knee": "MEASURED",
            "stance_width": "MEASURED",
            "lateral_balance": "ESTIMATED",
            "shoulder_alignment": "MEASURED",
        }
    }

    @classmethod
    def estimate_camera_view(cls, landmarks_frames: List[List[Any]]) -> Dict[str, Any]:
        """
        Estimates camera perspective (side-on, front-on, oblique) from body landmark proportions.
        Calculates ratio of projected shoulder width to torso length in stance / early frames.
        """
        if not landmarks_frames:
            return {"detected_view": "side-on", "confidence": 0.50, "ratio": 0.35}

        valid_ratios = []
        for lms in landmarks_frames[:60]:
            if not lms or len(lms) < 25:
                continue
            ls = lms[cls.LEFT_SHOULDER]
            rs = lms[cls.RIGHT_SHOULDER]
            lh = lms[cls.LEFT_HIP]
            ls_x = getattr(ls, 'x', 0) if not isinstance(ls, dict) else ls.get('x', 0)
            ls_y = getattr(ls, 'y', 0) if not isinstance(ls, dict) else ls.get('y', 0)
            rs_x = getattr(rs, 'x', 0) if not isinstance(rs, dict) else rs.get('x', 0)
            lh_x = getattr(lh, 'x', 0) if not isinstance(lh, dict) else lh.get('x', 0)
            lh_y = getattr(lh, 'y', 0) if not isinstance(lh, dict) else lh.get('y', 0)
            sh_w = abs(ls_x - rs_x)
            torso_h = math.hypot(ls_x - lh_x, ls_y - lh_y)
            if torso_h > 0.05:
                valid_ratios.append(sh_w / torso_h)

        if not valid_ratios:
            return {"detected_view": "side-on", "confidence": 0.50, "ratio": 0.35}

        median_ratio = float(np.median(valid_ratios))
        if median_ratio < 0.44:
            detected = "side-on"
            conf = min(0.95, 0.65 + (0.44 - median_ratio) * 1.5)
        elif median_ratio > 0.65:
            detected = "front-on"
            conf = min(0.95, 0.65 + (median_ratio - 0.65) * 1.5)
        else:
            detected = "oblique"
            conf = 0.80

        return {
            "detected_view": detected,
            "confidence": round(conf, 2),
            "ratio": round(median_ratio, 3)
        }

    @classmethod
    def get_recommended_camera_angle(cls, shot_name: str) -> str:
        shot_lower = (shot_name or "").lower()
        if any(w in shot_lower for w in ["drive", "defensive", "punch"]):
            return "Side View (side-on) provides the most reliable biomechanical capture for stride length and front knee flexion."
        elif any(w in shot_lower for w in ["pull", "hook", "cut"]):
            return "Side View or 45° Oblique View captures back-foot movement and horizontal bat extension cleanly."
        elif "sweep" in shot_lower:
            return "Side View captures knee drop depth and torso inclination during the sweep."
        return "Side View at waist height (~1.2m) delivers the highest accuracy for cricket stroke analysis."

    @classmethod
    def mirror_landmarks_for_left_hand(cls, landmarks: List[Any], is_world: bool = False) -> List[Any]:
        """
        Mirror 33 BlazePose landmarks horizontally (x -> 1.0 - x for 2D, x -> -x for world)
        and swap left/right joint pairs so a left-handed batsman is mapped into canonical
        right-handed coordinate space for comparison against reference tolerances.
        """
        if not landmarks or len(landmarks) < 33:
            return landmarks

        # Pairwise left/right swaps for MediaPipe Pose
        swap_map = {
            1: 4, 2: 5, 3: 6, 7: 8, 9: 10,  # eyes/ears/mouth
            11: 12, 13: 14, 15: 16, 17: 18, 19: 20, 21: 22,  # shoulders/arms/hands
            23: 24, 25: 26, 27: 28, 29: 30, 31: 32  # hips/legs/feet
        }
        full_map = {i: i for i in range(len(landmarks))}
        for l, r in swap_map.items():
            full_map[l] = r
            full_map[r] = l

        mirrored = [None] * len(landmarks)
        for orig_idx, target_idx in full_map.items():
            if orig_idx < len(landmarks) and target_idx < len(landmarks):
                lm = landmarks[orig_idx]
                if isinstance(lm, dict):
                    copied = dict(lm)
                    if "x" in copied and copied["x"] is not None:
                        copied["x"] = -copied["x"] if is_world else (1.0 - copied["x"])
                    mirrored[target_idx] = copied
                else:
                    class MirroredLM:
                        def __init__(self, x, y, z, v):
                            self.x = x
                            self.y = y
                            self.z = z
                            self.visibility = v
                    lx = getattr(lm, "x", 0.0)
                    ly = getattr(lm, "y", 0.0)
                    lz = getattr(lm, "z", 0.0)
                    lv = getattr(lm, "visibility", 1.0)
                    new_x = -lx if is_world else (1.0 - lx)
                    mirrored[target_idx] = MirroredLM(new_x, ly, lz, lv)
        return mirrored

    @classmethod
    def extract_frame_metrics(
        cls,
        landmarks: List[Any],
        handedness: str = "Right",
        world_landmarks: Optional[List[Any]] = None,
        camera_view: str = "side-on"
    ) -> Dict[str, Any]:
        """
        Extract complete biomechanical metrics from a single frame's landmarks.
        landmarks: list of landmark objects with x, y, z, visibility (or dicts)
        handedness: 'Right' or 'Left'
        world_landmarks: optional MediaPipe 3D world landmarks
        camera_view: 'side-on', 'front-on', 'oblique'
        """
        is_left_handed = str(handedness).strip().lower() == "left"
        if is_left_handed and landmarks and len(landmarks) >= 33:
            landmarks = cls.mirror_landmarks_for_left_hand(landmarks, is_world=False)
            handedness = "Right"
        if is_left_handed and world_landmarks and len(world_landmarks) >= 33:
            world_landmarks = cls.mirror_landmarks_for_left_hand(world_landmarks, is_world=True)
        empty_metrics = {
            "pose_detected": False,
            "confidence": 0.0,
            "lead_knee_angle": None,
            "rear_knee_angle": None,
            "left_knee_angle": None,
            "right_knee_angle": None,
            "torso_inclination": None,
            "shoulder_tilt": None,
            "hip_tilt": None,
            "head_x": None,
            "head_y": None,
            "head_displacement": None,
            "stance_width_norm": None,
            "lead_elbow_angle": None,
            "rear_elbow_angle": None,
            "left_elbow_angle": None,
            "right_elbow_angle": None,
            "lead_arm_extension": None,
            "rear_arm_extension": None,
            "lead_wrist_x": None,
            "lead_wrist_y": None,
            "rear_wrist_x": None,
            "rear_wrist_y": None,
            "wrist_separation_norm": None,
            "hands_to_torso_dist_norm": None,
            "hands_height_ratio": None,
            "lead_foot_x": None,
            "lead_foot_y": None,
            "rear_foot_x": None,
            "rear_foot_y": None,
            "head_over_lead_knee_norm": None,
            "shoulder_hip_separation_deg": None,
            "weight_distribution_proxy": None,
            "front_foot_stride_ratio": None,
        }
        if not landmarks or len(landmarks) < 33:
            return empty_metrics

        def get_point(idx: int) -> Optional[Tuple[float, float]]:
            lm = landmarks[idx]
            vis = getattr(lm, 'visibility', None)
            if vis is None and isinstance(lm, dict):
                vis = lm.get('visibility', 1.0)
            if vis is not None and vis < cls.MIN_VISIBILITY_THRESHOLD:
                return None
            x = getattr(lm, 'x', None)
            y = getattr(lm, 'y', None)
            if x is None and isinstance(lm, dict):
                x, y = lm.get('x'), lm.get('y')
            if x is None or y is None:
                return None
            return (float(x), float(y))

        # Anatomical Points
        p_l_shoulder = get_point(cls.LEFT_SHOULDER)
        p_r_shoulder = get_point(cls.RIGHT_SHOULDER)
        p_l_elbow = get_point(cls.LEFT_ELBOW)
        p_r_elbow = get_point(cls.RIGHT_ELBOW)
        p_l_wrist = get_point(cls.LEFT_WRIST)
        p_r_wrist = get_point(cls.RIGHT_WRIST)
        p_l_hip = get_point(cls.LEFT_HIP)
        p_r_hip = get_point(cls.RIGHT_HIP)
        p_l_knee = get_point(cls.LEFT_KNEE)
        p_r_knee = get_point(cls.RIGHT_KNEE)
        p_l_ankle = get_point(cls.LEFT_ANKLE)
        p_r_ankle = get_point(cls.RIGHT_ANKLE)
        p_l_toe = get_point(cls.LEFT_FOOT_INDEX)
        p_r_toe = get_point(cls.RIGHT_FOOT_INDEX)
        p_nose = get_point(cls.NOSE)

        # Confidence calculation
        visibilities = [
            getattr(lm, 'visibility', 0.5) if not isinstance(lm, dict) else lm.get('visibility', 0.5)
            for lm in landmarks
        ]
        mean_conf = float(np.mean(visibilities)) if visibilities else 0.0

        # Handedness dynamic landmark assignment:
        # Right-handed batsman: Lead (front facing bowler) = LEFT, Rear (back facing stumps) = RIGHT
        # Left-handed batsman: Lead = RIGHT, Rear = LEFT
        if handedness.lower() == "left":
            p_lead_shoulder, p_lead_elbow, p_lead_wrist = p_r_shoulder, p_r_elbow, p_r_wrist
            p_rear_shoulder, p_rear_elbow, p_rear_wrist = p_l_shoulder, p_l_elbow, p_l_wrist
            p_lead_hip, p_lead_knee, p_lead_ankle, p_lead_toe = p_r_hip, p_r_knee, p_r_ankle, p_r_toe
            p_rear_hip, p_rear_knee, p_rear_ankle, p_rear_toe = p_l_hip, p_l_knee, p_l_ankle, p_l_toe
        else:
            p_lead_shoulder, p_lead_elbow, p_lead_wrist = p_l_shoulder, p_l_elbow, p_l_wrist
            p_rear_shoulder, p_rear_elbow, p_rear_wrist = p_r_shoulder, p_r_elbow, p_r_wrist
            p_lead_hip, p_lead_knee, p_lead_ankle, p_lead_toe = p_l_hip, p_l_knee, p_l_ankle, p_l_toe
            p_rear_hip, p_rear_knee, p_rear_ankle, p_rear_toe = p_r_hip, p_r_knee, p_r_ankle, p_r_toe

        # Knee Flexion (Interior angle: ~180° = straight leg, 110-140° = bent knee during stride/drive)
        lead_knee_angle = cls.calculate_angle_2d(p_lead_hip, p_lead_knee, p_lead_ankle)
        rear_knee_angle = cls.calculate_angle_2d(p_rear_hip, p_rear_knee, p_rear_ankle)
        left_knee_angle = cls.calculate_angle_2d(p_l_hip, p_l_knee, p_l_ankle)
        right_knee_angle = cls.calculate_angle_2d(p_r_hip, p_r_knee, p_r_ankle)

        # Elbow Flexion (~180° = straight arm, ~90° = cocked elbow in backswing)
        lead_elbow_angle = cls.calculate_angle_2d(p_lead_shoulder, p_lead_elbow, p_lead_wrist)
        rear_elbow_angle = cls.calculate_angle_2d(p_rear_shoulder, p_rear_elbow, p_rear_wrist)
        left_elbow_angle = cls.calculate_angle_2d(p_l_shoulder, p_l_elbow, p_l_wrist)
        right_elbow_angle = cls.calculate_angle_2d(p_r_shoulder, p_r_elbow, p_r_wrist)

        # Compute 3D joint angles from MediaPipe WORLD landmarks if available
        def get_world_point(idx: int) -> Optional[Tuple[float, float, float]]:
            if not world_landmarks or idx >= len(world_landmarks):
                return None
            lm = world_landmarks[idx]
            vis = getattr(lm, 'visibility', None)
            if vis is None and isinstance(lm, dict):
                vis = lm.get('visibility', 1.0)
            if vis is not None and vis < cls.MIN_VISIBILITY_THRESHOLD:
                return None
            x = getattr(lm, 'x', None) if not isinstance(lm, dict) else lm.get('x')
            y = getattr(lm, 'y', None) if not isinstance(lm, dict) else lm.get('y')
            z = getattr(lm, 'z', None) if not isinstance(lm, dict) else lm.get('z')
            if x is None or y is None or z is None:
                return None
            return (float(x), float(y), float(z))

        if world_landmarks and len(world_landmarks) >= 33:
            w_lead_hip = get_world_point(cls.LEFT_HIP)
            w_lead_knee = get_world_point(cls.LEFT_KNEE)
            w_lead_ankle = get_world_point(cls.LEFT_ANKLE)
            w_lead_knee_angle = cls.calculate_angle_3d(w_lead_hip, w_lead_knee, w_lead_ankle)
            if w_lead_knee_angle is not None:
                lead_knee_angle = round(w_lead_knee_angle, 1)

            w_rear_hip = get_world_point(cls.RIGHT_HIP)
            w_rear_knee = get_world_point(cls.RIGHT_KNEE)
            w_rear_ankle = get_world_point(cls.RIGHT_ANKLE)
            w_rear_knee_angle = cls.calculate_angle_3d(w_rear_hip, w_rear_knee, w_rear_ankle)
            if w_rear_knee_angle is not None:
                rear_knee_angle = round(w_rear_knee_angle, 1)

            w_lead_sh = get_world_point(cls.LEFT_SHOULDER)
            w_lead_el = get_world_point(cls.LEFT_ELBOW)
            w_lead_wr = get_world_point(cls.LEFT_WRIST)
            w_lead_elbow_angle = cls.calculate_angle_3d(w_lead_sh, w_lead_el, w_lead_wr)
            if w_lead_elbow_angle is not None:
                lead_elbow_angle = round(w_lead_elbow_angle, 1)

            w_rear_sh = get_world_point(cls.RIGHT_SHOULDER)
            w_rear_el = get_world_point(cls.RIGHT_ELBOW)
            w_rear_wr = get_world_point(cls.RIGHT_WRIST)
            w_rear_elbow_angle = cls.calculate_angle_3d(w_rear_sh, w_rear_el, w_rear_wr)
            if w_rear_elbow_angle is not None:
                rear_elbow_angle = round(w_rear_elbow_angle, 1)

        # Arm Extensions [0.0 - 1.0]
        lead_arm_extension = cls.calculate_extension_ratio(p_lead_shoulder, p_lead_elbow, p_lead_wrist)
        rear_arm_extension = cls.calculate_extension_ratio(p_rear_shoulder, p_rear_elbow, p_rear_wrist)

        # Torso inclination & Height scale
        torso_inclination = None
        torso_height = None
        torso_center_x, torso_center_y = None, None
        if p_l_shoulder and p_r_shoulder and p_l_hip and p_r_hip:
            mid_shoulder = ((p_l_shoulder[0] + p_r_shoulder[0]) / 2.0, (p_l_shoulder[1] + p_r_shoulder[1]) / 2.0)
            mid_hip = ((p_l_hip[0] + p_r_hip[0]) / 2.0, (p_l_hip[1] + p_r_hip[1]) / 2.0)
            torso_inclination = cls.calculate_inclination_from_vertical(mid_hip, mid_shoulder)
            torso_height = math.hypot(mid_shoulder[0] - mid_hip[0], mid_shoulder[1] - mid_hip[1])
            torso_center_x = (mid_shoulder[0] + mid_hip[0]) / 2.0
            torso_center_y = (mid_shoulder[1] + mid_hip[1]) / 2.0
        elif p_lead_hip and (p_l_shoulder or p_r_shoulder):
            shoulder = p_l_shoulder or p_r_shoulder
            torso_inclination = cls.calculate_inclination_from_vertical(p_lead_hip, shoulder)
            torso_height = math.hypot(shoulder[0] - p_lead_hip[0], shoulder[1] - p_lead_hip[1])
            torso_center_x = (shoulder[0] + p_lead_hip[0]) / 2.0
            torso_center_y = (shoulder[1] + p_lead_hip[1]) / 2.0

        scale = torso_height if torso_height and torso_height > 0.05 else 0.3

        # Shoulder & Hip tilt relative to horizontal
        shoulder_tilt = cls.calculate_tilt_from_horizontal(p_l_shoulder, p_r_shoulder)
        hip_tilt = cls.calculate_tilt_from_horizontal(p_l_hip, p_r_hip)
        shoulder_hip_separation_deg = None
        if shoulder_tilt is not None and hip_tilt is not None:
            shoulder_hip_separation_deg = round(abs(shoulder_tilt - hip_tilt), 1)

        # Head position and displacement normalized by torso scale
        head_x, head_y = None, None
        head_disp_norm = None
        head_over_lead_knee_norm = None
        if p_nose:
            head_x, head_y = p_nose[0], p_nose[1]
            if p_l_hip and p_r_hip:
                pelvis_center_y = (p_l_hip[1] + p_r_hip[1]) / 2.0
                pelvis_center_x = (p_l_hip[0] + p_r_hip[0]) / 2.0
                dist_to_pelvis = math.hypot(head_x - pelvis_center_x, head_y - pelvis_center_y)
                head_disp_norm = dist_to_pelvis / scale
            if p_lead_knee:
                head_over_lead_knee_norm = (head_x - p_lead_knee[0]) / scale

        # Stance width and footwork
        stance_width_norm = None
        front_foot_stride_ratio = None
        weight_distribution_proxy = None
        if p_l_ankle and p_r_ankle:
            ankle_dist = math.hypot(p_l_ankle[0] - p_r_ankle[0], p_l_ankle[1] - p_r_ankle[1])
            stance_width_norm = float(ankle_dist / scale)
        if p_lead_ankle and p_rear_ankle:
            front_foot_stride_ratio = abs(p_lead_ankle[0] - p_rear_ankle[0]) / scale
            if torso_center_x is not None:
                base_span = p_lead_ankle[0] - p_rear_ankle[0]
                if abs(base_span) > 0.02:
                    raw_ratio = (torso_center_x - p_rear_ankle[0]) / base_span
                    weight_distribution_proxy = float(min(1.0, max(0.0, raw_ratio)))

        # Hand & Wrist relative kinematics
        wrist_separation_norm = None
        hands_to_torso_dist_norm = None
        hands_height_ratio = None
        if p_l_wrist and p_r_wrist:
            w_dist = math.hypot(p_l_wrist[0] - p_r_wrist[0], p_l_wrist[1] - p_r_wrist[1])
            wrist_separation_norm = w_dist / scale
            wrist_mid_x = (p_l_wrist[0] + p_r_wrist[0]) / 2.0
            wrist_mid_y = (p_l_wrist[1] + p_r_wrist[1]) / 2.0
            if torso_center_x is not None and torso_center_y is not None:
                hands_to_torso_dist_norm = math.hypot(wrist_mid_x - torso_center_x, wrist_mid_y - torso_center_y) / scale
            if p_l_hip and p_r_hip and p_l_shoulder and p_r_shoulder:
                hip_y = (p_l_hip[1] + p_r_hip[1]) / 2.0
                sh_y = (p_l_shoulder[1] + p_r_shoulder[1]) / 2.0
                if abs(hip_y - sh_y) > 0.02:
                    hands_height_ratio = (hip_y - wrist_mid_y) / (hip_y - sh_y)

        # Wrist coordinates
        lead_wrist_x = p_lead_wrist[0] if p_lead_wrist else None
        lead_wrist_y = p_lead_wrist[1] if p_lead_wrist else None
        rear_wrist_x = p_rear_wrist[0] if p_rear_wrist else None
        rear_wrist_y = p_rear_wrist[1] if p_rear_wrist else None

        # Foot coordinates (prefer toe, fallback to ankle)
        lead_foot_pt = p_lead_toe or p_lead_ankle
        rear_foot_pt = p_rear_toe or p_rear_ankle
        lead_foot_x = lead_foot_pt[0] if lead_foot_pt else None
        lead_foot_y = lead_foot_pt[1] if lead_foot_pt else None
        rear_foot_x = rear_foot_pt[0] if rear_foot_pt else None
        rear_foot_y = rear_foot_pt[1] if rear_foot_pt else None

        return {
            "pose_detected": True,
            "confidence": round(mean_conf, 3),
            "lead_knee_angle": round(lead_knee_angle, 1) if lead_knee_angle is not None else None,
            "rear_knee_angle": round(rear_knee_angle, 1) if rear_knee_angle is not None else None,
            "left_knee_angle": round(left_knee_angle, 1) if left_knee_angle is not None else None,
            "right_knee_angle": round(right_knee_angle, 1) if right_knee_angle is not None else None,
            "torso_inclination": round(torso_inclination, 1) if torso_inclination is not None else None,
            "shoulder_tilt": round(shoulder_tilt, 1) if shoulder_tilt is not None else None,
            "hip_tilt": round(hip_tilt, 1) if hip_tilt is not None else None,
            "head_x": round(head_x, 4) if head_x is not None else None,
            "head_y": round(head_y, 4) if head_y is not None else None,
            "head_displacement": round(head_disp_norm, 3) if head_disp_norm is not None else None,
            "stance_width_norm": round(stance_width_norm, 3) if stance_width_norm is not None else None,
            # Upper-body & arm extensions
            "lead_elbow_angle": round(lead_elbow_angle, 1) if lead_elbow_angle is not None else None,
            "rear_elbow_angle": round(rear_elbow_angle, 1) if rear_elbow_angle is not None else None,
            "left_elbow_angle": round(left_elbow_angle, 1) if left_elbow_angle is not None else None,
            "right_elbow_angle": round(right_elbow_angle, 1) if right_elbow_angle is not None else None,
            "lead_arm_extension": round(lead_arm_extension, 3) if lead_arm_extension is not None else None,
            "rear_arm_extension": round(rear_arm_extension, 3) if rear_arm_extension is not None else None,
            "lead_wrist_x": round(lead_wrist_x, 4) if lead_wrist_x is not None else None,
            "lead_wrist_y": round(lead_wrist_y, 4) if lead_wrist_y is not None else None,
            "rear_wrist_x": round(rear_wrist_x, 4) if rear_wrist_x is not None else None,
            "rear_wrist_y": round(rear_wrist_y, 4) if rear_wrist_y is not None else None,
            "wrist_separation_norm": round(wrist_separation_norm, 3) if wrist_separation_norm is not None else None,
            "hands_to_torso_dist_norm": round(hands_to_torso_dist_norm, 3) if hands_to_torso_dist_norm is not None else None,
            "hands_height_ratio": round(hands_height_ratio, 3) if hands_height_ratio is not None else None,
            # Footwork & Balance
            "lead_foot_x": round(lead_foot_x, 4) if lead_foot_x is not None else None,
            "lead_foot_y": round(lead_foot_y, 4) if lead_foot_y is not None else None,
            "rear_foot_x": round(rear_foot_x, 4) if rear_foot_x is not None else None,
            "rear_foot_y": round(rear_foot_y, 4) if rear_foot_y is not None else None,
            "head_over_lead_knee_norm": round(head_over_lead_knee_norm, 3) if head_over_lead_knee_norm is not None else None,
            "shoulder_hip_separation_deg": shoulder_hip_separation_deg,
            "weight_distribution_proxy": round(weight_distribution_proxy, 3) if weight_distribution_proxy is not None else None,
            "front_foot_stride_ratio": round(front_foot_stride_ratio, 3) if front_foot_stride_ratio is not None else None,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Temporal signal-processing helpers (operate on entire sequence, not single frames)
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def smooth_angle_sequence(
        angles: List[Optional[float]],
        window: int = 5,
        interpolate_dropouts: bool = False
    ) -> List[Optional[float]]:
        """
        Apply Savitzky-Golay smoothing (or a simple moving-average fallback) to an
        angle time series, preserving None entries and sequence length.

        Parameters
        ----------
        angles : list of float or None  — raw per-frame angles (degrees)
        window : int  — smoothing window length (must be odd, >= 3)

        Returns
        -------
        Smoothed list of the same length; None positions remain None.
        """
        if not angles:
            return angles

        valid_indices = [i for i, v in enumerate(angles) if v is not None]
        if len(valid_indices) < 3:
            return angles

        n = len(angles)
        filled = list(angles)
        is_short_dropout = [False] * n

        # 1. Identify contiguous None gaps; interpolate across short dropouts (< 5 frames)
        i = 0
        while i < n:
            if filled[i] is None:
                gap_start = i
                while i < n and filled[i] is None:
                    i += 1
                gap_end = i - 1
                gap_len = gap_end - gap_start + 1

                prev_idx = gap_start - 1
                next_idx = gap_end + 1
                if gap_len < 5 and prev_idx >= 0 and next_idx < n and filled[prev_idx] is not None and filled[next_idx] is not None:
                    v_prev = filled[prev_idx]
                    v_next = filled[next_idx]
                    for g in range(gap_start, gap_end + 1):
                        frac = (g - prev_idx) / float(next_idx - prev_idx)
                        filled[g] = float(v_prev + frac * (v_next - v_prev))
                        is_short_dropout[g] = True
            else:
                i += 1

        valid_indices = [idx for idx, v in enumerate(filled) if v is not None]
        if len(valid_indices) < 3:
            return angles

        # For remaining None entries (long dropouts >= 5 frames), fill locally for filter continuity
        filter_input = list(filled)
        for idx in range(n):
            if filter_input[idx] is None:
                prev = next((filter_input[j] for j in range(idx - 1, -1, -1) if filter_input[j] is not None), None)
                nxt = next((filter_input[j] for j in range(idx + 1, n) if filter_input[j] is not None), None)
                if prev is not None and nxt is not None:
                    filter_input[idx] = (prev + nxt) / 2.0
                elif prev is not None:
                    filter_input[idx] = prev
                elif nxt is not None:
                    filter_input[idx] = nxt
                else:
                    filter_input[idx] = 0.0

        arr = np.array(filter_input, dtype=float)
        w = min(window | 1, len(arr) if len(arr) % 2 == 1 else len(arr) - 1)
        w = max(3, w)

        if _SCIPY_AVAILABLE and len(arr) >= w:
            try:
                smoothed = savgol_filter(arr, window_length=w, polyorder=2)
            except Exception:
                smoothed = np.convolve(arr, np.ones(w) / w, mode="same")
        else:
            kernel = np.ones(w) / w
            smoothed = np.convolve(arr, kernel, mode="same")

        result: List[Optional[float]] = []
        for idx in range(n):
            # Retain value if it was originally measured or if dropout interpolation is explicitly requested
            if angles[idx] is not None or (interpolate_dropouts and is_short_dropout[idx]):
                result.append(round(float(smoothed[idx]), 2))
            else:
                result.append(None)
        return result

    @staticmethod
    def calculate_angular_velocity(
        angles: List[Optional[float]], fps: float
    ) -> List[Optional[float]]:
        """
        Compute frame-by-frame angular velocity (degrees/second) using central differences.
        Returns None for frames where the angle itself was unavailable.

        deg/sec = (angle[i+1] − angle[i−1]) / (2 / fps)
        """
        if fps <= 0:
            fps = 30.0
        dt = 1.0 / fps
        n = len(angles)
        velocities: List[Optional[float]] = [None] * n

        for i in range(n):
            # Central difference where neighbours are available
            prev = angles[i - 1] if i > 0 else None
            curr = angles[i]
            nxt = angles[i + 1] if i < n - 1 else None

            if curr is None:
                continue

            if prev is not None and nxt is not None:
                v = (nxt - prev) / (2.0 * dt)
            elif prev is not None:
                v = (curr - prev) / dt
            elif nxt is not None:
                v = (nxt - curr) / dt
            else:
                v = 0.0

            velocities[i] = round(float(v), 2)

        return velocities

    @staticmethod
    def calculate_angular_acceleration(
        angular_velocities: List[Optional[float]], fps: float
    ) -> List[Optional[float]]:
        """
        Compute frame-by-frame angular acceleration (degrees/second²) from a velocity series.
        Returns None where velocity was unavailable.
        """
        return GeometryService.calculate_angular_velocity(angular_velocities, fps)

    @classmethod
    def enrich_time_series_with_derivatives(
        cls,
        frame_metrics: List[Dict[str, Any]],
        fps: float = 30.0,
        smooth_window: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Post-processes an entire frame_metrics list (output of extract_frame_metrics calls) to:

        1. Smooth key angle trajectories using Savitzky-Golay / moving-average
        2. Add per-frame angular velocity fields (_velocity suffix, deg/s)
        3. Add per-frame angular acceleration fields (_acceleration suffix, deg/s²)

        This must be called AFTER all frames have been processed, not inline.

        Returns the same list mutated in-place (also returned for convenience).
        """
        if not frame_metrics:
            return frame_metrics

        ANGLE_KEYS = [
            "lead_knee_angle",
            "rear_knee_angle",
            "torso_inclination",
            "lead_elbow_angle",
            "rear_elbow_angle",
            "shoulder_tilt",
            "hip_tilt",
        ]

        for key in ANGLE_KEYS:
            raw = [m.get(key) for m in frame_metrics]

            # 1. Smooth
            smoothed = cls.smooth_angle_sequence(raw, window=smooth_window, interpolate_dropouts=True)

            # 2. Angular velocity
            velocities = cls.calculate_angular_velocity(smoothed, fps)

            # 3. Angular acceleration
            accelerations = cls.calculate_angular_acceleration(velocities, fps)

            vel_key = f"{key}_velocity"
            acc_key = f"{key}_acceleration"

            for i, m in enumerate(frame_metrics):
                if smoothed[i] is not None:
                    m[key] = smoothed[i]            # update with smoothed value
                m[vel_key] = velocities[i]
                m[acc_key] = accelerations[i]

        # Wrist speed: scalar magnitude of lead-wrist (x,y) velocity
        wrist_xs = [m.get("lead_wrist_x") for m in frame_metrics]
        wrist_ys = [m.get("lead_wrist_y") for m in frame_metrics]

        vx_list = cls.calculate_angular_velocity(wrist_xs, fps)  # reuse helper (works on any signal)
        vy_list = cls.calculate_angular_velocity(wrist_ys, fps)

        for i, m in enumerate(frame_metrics):
            vx = vx_list[i]
            vy = vy_list[i]
            if vx is not None and vy is not None:
                speed = round(math.hypot(vx, vy), 3)
                m["lead_wrist_speed"] = speed
                m["lead_wrist_speed_normalized"] = round(min(1.0, speed / 15.0), 3)
            else:
                m["lead_wrist_speed"] = None
                m["lead_wrist_speed_normalized"] = None

        return frame_metrics

    @staticmethod
    def compute_trajectory_consistency(
        angle_sequence: List[Optional[float]],
    ) -> Dict[str, Any]:
        """
        Compute consistency metrics for a single angle trajectory across the stroke cycle.
        Useful for comparing multiple attempts of the same shot type.

        Returns:
            mean, std, coefficient_of_variation, range, data_completeness_pct
        """
        valid = [v for v in angle_sequence if v is not None]
        n_total = len(angle_sequence)
        n_valid = len(valid)
        if n_valid == 0:
            return {
                "mean": None, "std": None, "cv": None,
                "range": None, "data_completeness_pct": 0.0
            }
        arr = np.array(valid, dtype=float)
        mean_v = float(np.mean(arr))
        std_v = float(np.std(arr))
        cv = round(std_v / abs(mean_v) * 100.0, 2) if abs(mean_v) > 1e-3 else None
        return {
            "mean": round(mean_v, 2),
            "std": round(std_v, 2),
            "cv": cv,
            "range": round(float(np.ptp(arr)), 2),
            "data_completeness_pct": round(n_valid / max(1, n_total) * 100.0, 1),
        }


geometry_service = GeometryService()
