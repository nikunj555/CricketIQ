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


def _calc_joint_angle(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
    """Calculates angle at joint p2 in degrees [0, 180]."""
    v1 = (p1[0] - p2[0], p1[1] - p2[1])
    v2 = (p3[0] - p2[0], p3[1] - p2[1])
    mag1 = math.hypot(v1[0], v1[1])
    mag2 = math.hypot(v2[0], v2[1])
    if mag1 * mag2 < 1e-6:
        return 180.0
    cos_ang = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (mag1 * mag2)))
    return float(math.degrees(math.acos(cos_ang)))


class MultiPersonTracker:
    """
    Robust per-person tracker using bounding box IoU and landmark continuity.
    Evaluates 6 biomechanical cues to isolate the striker from bowlers, non-strikers, and fielders:
      1. Bat in hand: Wrists coupled in classic batting grip; bat-shaped object anchored at wrists.
      2. Position: Crease end anchor (stationary pelvic base vs translating bowler).
      3. Motion signature: High rotational wrist swing velocity at impact, penalizing bowler overhead arm arc.
      4. Stance posture: Flexed knees, side-on torso alignment, hands low in front of hips.
      5. Ball contact / proximity: Proximity of wrists/bat to ball at trajectory contact frame.
      6. Size and framing: Foreground scale, central framing in broadcast or net footage.
    """
    def __init__(self, max_disappeared: int = 15):
        self.next_track_id = 0
        self.max_disappeared = max_disappeared
        self.tracks: Dict[int, Dict[str, Any]] = {}
        self.track_classifications: Dict[int, Dict[str, Any]] = {}

    def _extract_cues_snapshot(self, pose: Dict[str, Any], frame_idx: int) -> Dict[str, Any]:
        lms = pose.get("landmarks", [])
        lw = lms[15] if len(lms) > 15 else None
        rw = lms[16] if len(lms) > 16 else None
        lh = lms[23] if len(lms) > 23 else None
        rh = lms[24] if len(lms) > 24 else None
        ls = lms[11] if len(lms) > 11 else None
        rs = lms[12] if len(lms) > 12 else None
        lk = lms[25] if len(lms) > 25 else None
        rk = lms[26] if len(lms) > 26 else None
        la = lms[27] if len(lms) > 27 else None
        ra = lms[28] if len(lms) > 28 else None
        nose = lms[0] if len(lms) > 0 else None

        def _get_v(lm, attr, default=0.0):
            if lm is None:
                return default
            if isinstance(lm, dict):
                return lm.get(attr, default)
            return getattr(lm, attr, default)

        lw_x = _get_v(lw, 'x', 0.0)
        lw_y = _get_v(lw, 'y', 0.0)
        rw_x = _get_v(rw, 'x', 0.0)
        rw_y = _get_v(rw, 'y', 0.0)

        hip_x = (_get_v(lh, 'x', 0.5) + _get_v(rh, 'x', 0.5)) / 2.0 if lh and rh else 0.5
        hip_y = (_get_v(lh, 'y', 0.5) + _get_v(rh, 'y', 0.5)) / 2.0 if lh and rh else 0.5

        sh_x = (_get_v(ls, 'x', 0.5) + _get_v(rs, 'x', 0.5)) / 2.0 if ls and rs else 0.5
        sh_y = (_get_v(ls, 'y', 0.2) + _get_v(rs, 'y', 0.2)) / 2.0 if ls and rs else 0.2

        torso_len = max(0.1, math.hypot(sh_x - hip_x, sh_y - hip_y))
        wrist_dist = math.hypot(lw_x - rw_x, lw_y - rw_y)

        # Cue 1: Bat grip check - wrists together, in front of torso
        is_bat_grip = wrist_dist < max(0.08, torso_len * 0.28)
        hands_mid_y = (lw_y + rw_y) / 2.0
        is_in_front = (min(sh_y, hip_y) - 0.05) <= hands_mid_y <= (max(sh_y, hip_y) + 0.15)

        # Cue 3: Bowling overhead arc check - either wrist higher than nose/shoulder
        head_ref_y = _get_v(nose, 'y', sh_y) if nose else sh_y
        is_overhead = (lw_y < head_ref_y - 0.04) or (rw_y < head_ref_y - 0.04)

        # Cue 4: Stance knee angles & side-on ratio
        lk_ang = 180.0
        rk_ang = 180.0
        if lh and lk and la:
            lk_ang = _calc_joint_angle((_get_v(lh, 'x'), _get_v(lh, 'y')), (_get_v(lk, 'x'), _get_v(lk, 'y')), (_get_v(la, 'x'), _get_v(la, 'y')))
        if rh and rk and ra:
            rk_ang = _calc_joint_angle((_get_v(rh, 'x'), _get_v(rh, 'y')), (_get_v(rk, 'x'), _get_v(rk, 'y')), (_get_v(ra, 'x'), _get_v(ra, 'y')))
        has_bent_knees = (115.0 <= lk_ang <= 165.0) or (115.0 <= rk_ang <= 165.0)
        shoulder_width = math.hypot(_get_v(ls, 'x', 0.5) - _get_v(rs, 'x', 0.5), _get_v(ls, 'y', 0.2) - _get_v(rs, 'y', 0.2)) if ls and rs else 0.2
        is_side_on = (shoulder_width / torso_len) <= 0.88

        # Cue 6: Framing scale & centrality
        bbox = pose.get("bbox", [0.0, 0.0, 1.0, 1.0])
        box_w = max(0.01, bbox[2] - bbox[0])
        box_h = max(0.01, bbox[3] - bbox[1])
        box_area = box_w * box_h
        box_cx = (bbox[0] + bbox[2]) / 2.0
        centrality = max(0.0, 1.0 - abs(box_cx - 0.5) * 2.0)

        # Landmark visibility across primary keypoints
        key_indices = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
        vis_list = [_get_v(lms[idx], 'visibility', 1.0) for idx in key_indices if idx < len(lms) and lms[idx] is not None] if lms else []
        mean_vis = float(np.mean(vis_list)) if vis_list else 0.85

        return {
            "frame_idx": frame_idx,
            "bbox": bbox,
            "lw": (lw_x, lw_y),
            "rw": (rw_x, rw_y),
            "hip": (hip_x, hip_y),
            "shoulder": (sh_x, sh_y),
            "torso_len": torso_len,
            "wrist_dist": wrist_dist,
            "is_bat_grip": is_bat_grip,
            "is_in_front": is_in_front,
            "is_overhead": is_overhead,
            "lk_ang": lk_ang,
            "rk_ang": rk_ang,
            "has_bent_knees": has_bent_knees,
            "is_side_on": is_side_on,
            "box_height": box_h,
            "box_area": box_area,
            "centrality": centrality,
            "mean_vis": mean_vis
        }

    def update(self, detected_poses: List[Dict[str, Any]], frame_idx: int = 0) -> Dict[int, Dict[str, Any]]:
        """
        Updates tracks with detected poses in the current frame and records biomechanical cues.
        """
        if not self.tracks:
            for pose in detected_poses:
                tid = self.next_track_id
                self.next_track_id += 1
                cues = self._extract_cues_snapshot(pose, frame_idx)
                self.tracks[tid] = {
                    "track_id": tid,
                    "bbox": pose["bbox"],
                    "landmarks": pose["landmarks"],
                    "world_landmarks": pose.get("world_landmarks"),
                    "disappeared": 0,
                    "last_wrists": (cues["lw"], cues["rw"]),
                    "wrist_motion_total": 0.0,
                    "peak_wrist_vel": 0.0,
                    "history_frames": 1,
                    "is_lost": False,
                    "history": [cues],
                    "initial_hip": cues["hip"]
                }
            return self.tracks

        if not detected_poses:
            for tid, tr in list(self.tracks.items()):
                tr["disappeared"] += 1
                if tr["disappeared"] > self.max_disappeared:
                    tr["is_lost"] = True
            return self.tracks

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
                score = iou * 2.5 - dist
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
            cues = self._extract_cues_snapshot(pose, frame_idx)

            prev_lw, prev_rw = tr["last_wrists"]
            frame_disp = 0.0
            if prev_lw and cues["lw"]:
                frame_disp += math.hypot(cues["lw"][0] - prev_lw[0], cues["lw"][1] - prev_lw[1])
            if prev_rw and cues["rw"]:
                frame_disp += math.hypot(cues["rw"][0] - prev_rw[0], cues["rw"][1] - prev_rw[1])

            tr["bbox"] = pose["bbox"]
            tr["landmarks"] = pose["landmarks"]
            tr["world_landmarks"] = pose.get("world_landmarks")
            tr["disappeared"] = 0
            tr["is_lost"] = False
            tr["history_frames"] += 1
            tr["wrist_motion_total"] += frame_disp
            tr["peak_wrist_vel"] = max(tr["peak_wrist_vel"], frame_disp)
            tr["last_wrists"] = (cues["lw"], cues["rw"])
            cues["wrist_vel"] = frame_disp
            tr["history"].append(cues)

        for tid in unmatched_tracks:
            tr = self.tracks[tid]
            tr["disappeared"] += 1
            if tr["disappeared"] > self.max_disappeared:
                tr["is_lost"] = True

        for d_idx in unmatched_detections:
            tid = self.next_track_id
            self.next_track_id += 1
            pose = detected_poses[d_idx]
            cues = self._extract_cues_snapshot(pose, frame_idx)
            self.tracks[tid] = {
                "track_id": tid,
                "bbox": pose["bbox"],
                "landmarks": pose["landmarks"],
                "world_landmarks": pose.get("world_landmarks"),
                "disappeared": 0,
                "last_wrists": (cues["lw"], cues["rw"]),
                "wrist_motion_total": 0.0,
                "peak_wrist_vel": 0.0,
                "history_frames": 1,
                "is_lost": False,
                "history": [cues],
                "initial_hip": cues["hip"]
            }

        return self.tracks

    def classify_tracks(
        self,
        total_frames: int = 60,
        bat_ball_data: Optional[Dict[int, Any]] = None
    ) -> Tuple[int, Dict[int, Dict[str, Any]], bool, Optional[str]]:
        """
        Evaluates 6 biomechanical cues across all tracks to isolate the striker from bowlers and non-strikers:
          Cue 1: Bat in hand (wrists coupled in front of body, linear bat segment) [Weight 0.25]
          Cue 2: Position & Crease anchor (stationary pelvic station vs translating bowler) [Weight 0.20]
          Cue 3: Motion signature (high rotational wrist swing velocity at impact) [Weight 0.20]
          Cue 4: Batting stance posture (bent knees, side-on orientation, hands low) [Weight 0.15]
          Cue 5: Ball contact / proximity [Weight 0.10]
          Cue 6: Framing scale & centrality (foreground batter vs distant bowler) [Weight 0.10]
        Returns: (best_striker_track_id, track_classifications_dict, needs_user_confirmation, confirmation_message)
        """
        if not self.tracks:
            return 0, {}, False, None

        classifications: Dict[int, Dict[str, Any]] = {}
        setup_window_limit = max(10, min(45, int(total_frames * 0.45)))

        motion_vals = [tr.get("wrist_motion_total", 0.0) for tr in self.tracks.values()]
        max_total_wrist_motion = max(0.001, max(motion_vals)) if motion_vals else 0.001

        for tid, tr in self.tracks.items():
            hist = tr.get("history", [])
            if not hist or len(hist) < 3:
                classifications[tid] = {
                    "role": "other",
                    "striker_score": 0.05,
                    "confidence": 0.1,
                    "reason": "Insufficient track history (fewer than 3 frames)",
                    "evidence": {"reason": "Insufficient track history"}
                }
                continue

            init_hip = tr.get("initial_hip", hist[0]["hip"])
            setup_snapshots = [h for h in hist if h["frame_idx"] <= setup_window_limit]
            later_snapshots = [h for h in hist if h["frame_idx"] > setup_window_limit]

            # ----------------------------------------------------
            # Cue 0: Landmark Quality & Visibility Gate
            # ----------------------------------------------------
            vis_hist = [h.get("mean_vis", 0.85) for h in hist]
            track_mean_vis = float(np.mean(vis_hist)) if vis_hist else 0.85
            is_low_quality = track_mean_vis < 0.40
            quality_factor = 1.0 if not is_low_quality else max(0.15, track_mean_vis / 0.60)

            # Penalize transient tracks that persist for less than 15% of frames
            track_presence_ratio = len(hist) / max(1, total_frames)
            if track_presence_ratio < 0.15:
                quality_factor *= min(1.0, track_presence_ratio / 0.15)

            # ----------------------------------------------------
            # Cue 1: Bat in Hand (Weight: 0.25)
            # ----------------------------------------------------
            bat_grip_count = sum(1 for h in setup_snapshots if h.get("is_bat_grip") and h.get("is_in_front"))
            bat_grip_ratio = bat_grip_count / max(1, len(setup_snapshots))
            cue1_bat_pose_score = float(np.clip(bat_grip_ratio * 0.90 + (0.10 if bat_grip_ratio > 0.3 else 0.0), 0.0, 1.0))

            # ----------------------------------------------------
            # Cue 2: Position Stability at Crease End (Weight: 0.20)
            # ----------------------------------------------------
            all_hip_disps = [math.hypot(h["hip"][0] - init_hip[0], h["hip"][1] - init_hip[1]) for h in hist]
            max_total_hip_disp = max(all_hip_disps) if all_hip_disps else 0.0
            setup_hip_disps = [math.hypot(h["hip"][0] - init_hip[0], h["hip"][1] - init_hip[1]) for h in setup_snapshots]
            max_setup_hip_disp = max(setup_hip_disps) if setup_hip_disps else 0.0

            # Bowler has high run-up translation (>0.30); striker hip stride is bounded (~0.12-0.24)
            cue2_position_score = float(np.clip(1.0 - (max_total_hip_disp / 0.32), 0.0, 1.0))

            # ----------------------------------------------------
            # Cue 3: Motion Signature (Rotational Swing vs Run-up / Non-striker) (Weight: 0.20)
            # ----------------------------------------------------
            peak_wrist_vel = tr.get("peak_wrist_vel", 0.0)
            total_wrist_motion = tr.get("wrist_motion_total", 0.0)
            overhead_count = sum(1 for h in hist if h.get("is_overhead"))
            
            # Bowling arc requires overhead arm motion accompanied by translation (unlike batting high follow-through)
            has_bowling_runup = max_total_hip_disp > 0.25
            has_bowling_arc = overhead_count >= 2 and has_bowling_runup

            is_rotational_swing = (peak_wrist_vel > 0.038 or total_wrist_motion > 0.40) and (not has_bowling_arc) and (max_total_hip_disp < 0.28)
            is_bowler_runup = (has_bowling_arc and max_total_hip_disp > 0.18) or (max_total_hip_disp > 0.32 and not is_rotational_swing)
            is_still_non_striker = (peak_wrist_vel < 0.032) or (total_wrist_motion < 0.30 and peak_wrist_vel < 0.038 and max_total_hip_disp < 0.18)

            if is_rotational_swing:
                cue3_motion_score = 0.95
            elif is_bowler_runup:
                cue3_motion_score = 0.05
            elif is_still_non_striker:
                cue3_motion_score = 0.10
                cue1_bat_pose_score = min(cue1_bat_pose_score, 0.35)
            else:
                cue3_motion_score = 0.45

            # ----------------------------------------------------
            # Cue 4: Batting Stance Posture (Weight: 0.15)
            # ----------------------------------------------------
            bent_knee_count = sum(1 for h in setup_snapshots if h.get("has_bent_knees"))
            bent_knee_ratio = bent_knee_count / max(1, len(setup_snapshots))
            side_on_count = sum(1 for h in setup_snapshots if h.get("is_side_on"))
            side_on_ratio = side_on_count / max(1, len(setup_snapshots))
            stance_stability = max(0.0, 1.0 - (max_setup_hip_disp / 0.12))
            cue4_stance_score = float(np.clip(bent_knee_ratio * 0.40 + side_on_ratio * 0.30 + stance_stability * 0.30, 0.0, 1.0))

            # ----------------------------------------------------
            # Cue 5: Ball Contact / Proximity (Weight: 0.10)
            # ----------------------------------------------------
            cue5_ball_contact_score = 0.50
            if bat_ball_data:
                # Check if ball passes close to this track's wrists
                min_ball_dist = 999.0
                for f_idx, bb in bat_ball_data.items():
                    bx = bb.get("ball_x")
                    by = bb.get("ball_y")
                    if bx is not None and by is not None:
                        for h in hist:
                            if h["frame_idx"] == f_idx:
                                d1 = math.hypot(h["lw"][0] - bx, h["lw"][1] - by)
                                d2 = math.hypot(h["rw"][0] - bx, h["rw"][1] - by)
                                min_ball_dist = min(min_ball_dist, d1, d2)
                if min_ball_dist < 0.15:
                    cue5_ball_contact_score = 0.95
                elif min_ball_dist < 0.30:
                    cue5_ball_contact_score = 0.75
                elif min_ball_dist < 900.0:
                    cue5_ball_contact_score = 0.30

            # ----------------------------------------------------
            # Cue 6: Framing Scale & Centrality (Weight: 0.10)
            # ----------------------------------------------------
            box_heights = [h.get("box_height", 0.4) for h in hist]
            mean_box_height = float(np.mean(box_heights)) if box_heights else 0.4
            centrality_vals = [h.get("centrality", 0.5) for h in hist]
            mean_centrality = float(np.mean(centrality_vals)) if centrality_vals else 0.5
            cue6_framing_score = float(np.clip((mean_box_height / 0.45) * 0.60 + mean_centrality * 0.40, 0.0, 1.0))

            # Temporal order factor: swing energy ratio
            swing_energy_ratio = float(np.clip(total_wrist_motion / max_total_wrist_motion, 0.0, 1.0))

            # Weighted combination of all 6 cues
            raw_striker_score = (
                cue1_bat_pose_score * 0.25 +
                cue2_position_score * 0.20 +
                cue3_motion_score * 0.20 +
                cue4_stance_score * 0.15 +
                cue5_ball_contact_score * 0.10 +
                cue6_framing_score * 0.10
            )
            striker_score = float(np.clip(raw_striker_score * quality_factor, 0.0, 1.0))

            # Role classification & plain English rationale
            if is_low_quality:
                role = "low-confidence"
                striker_score = min(striker_score, 0.20)
                reason = "Excluded: Low landmark visibility or keypoints severely occluded."
            elif is_bowler_runup and not is_rotational_swing:
                role = "bowler"
                striker_score = min(striker_score, 0.20)
                reason = f"Excluded as Bowler: Run-up displacement ({max_total_hip_disp:.2f}) and overhead delivery arc detected."
            elif is_still_non_striker:
                role = "non-striker"
                striker_score = min(striker_score, 0.30)
                reason = f"Excluded as Non-Striker: Stationary positioning without batting stroke motion (peak wrist speed {peak_wrist_vel:.3f})."
            elif is_rotational_swing or striker_score >= 0.50:
                role = "striker"
                reason = f"Selected as Striker: Bat in hand ({cue1_bat_pose_score:.2f}), stationary crease position ({cue2_position_score:.2f}), rotational swing ({cue3_motion_score:.2f}), and batting stance posture."
            else:
                role = "other"
                reason = f"Excluded: Track does not exhibit primary batting striker characteristics."

            evidence = {
                "cue1_bat_in_hand": round(cue1_bat_pose_score, 2),
                "cue2_position_crease": round(cue2_position_score, 2),
                "cue3_motion_signature": round(cue3_motion_score, 2),
                "cue4_batting_stance": round(cue4_stance_score, 2),
                "cue5_ball_contact": round(cue5_ball_contact_score, 2),
                "cue6_framing_size": round(cue6_framing_score, 2),
                "swing_energy_ratio": round(swing_energy_ratio, 2),
                "mean_landmark_visibility": round(track_mean_vis, 2),
                "max_hip_disp": round(max_total_hip_disp, 3),
                "peak_wrist_vel": round(peak_wrist_vel, 3),
                "bat_grip_ratio": round(bat_grip_ratio, 2),
                "has_bowling_arc": has_bowling_arc,
                "role": role,
                "reason": reason,
                "bbox": tr.get("bbox")
            }

            classifications[tid] = {
                "role": role,
                "striker_score": round(striker_score, 3),
                "confidence": round(striker_score, 2),
                "reason": reason,
                "bbox": tr.get("bbox"),
                "evidence": evidence
            }

        # Select best striker track
        ranked = sorted(classifications.items(), key=lambda item: item[1]["striker_score"], reverse=True)
        best_tid, best_meta = ranked[0]
        second_score = ranked[1][1]["striker_score"] if len(ranked) > 1 else 0.0

        # Mark confirmed striker role on top candidate
        classifications[best_tid]["role"] = "striker"

        needs_confirmation = False
        confirmation_message = None
        if len(ranked) > 1:
            if best_meta["striker_score"] < 0.50 or abs(best_meta["striker_score"] - second_score) < 0.15:
                needs_confirmation = True
                confirmation_message = "Could not tell who the striker is. Please select the batter"

        self.track_classifications = classifications
        return best_tid, classifications, needs_confirmation, confirmation_message


class PoseService:
    def __init__(self, model_asset_path: Optional[Path] = None):
        self.model_asset_path = str(model_asset_path or settings.MODEL_ASSET_PATH)
        self.landmarker = None
        self.crop_landmarker = None
        self.init_error = None
        self._init_landmarker()

    def _init_landmarker(self):
        try:
            import mediapipe as mp
            from mediapipe.tasks.python import vision, BaseOptions

            p = Path(self.model_asset_path).resolve()
            if not p.exists():
                self.init_error = f"PoseLandmarker asset not found at {self.model_asset_path}"
                logger.warning(f"PoseLandmarker asset not found at {self.model_asset_path}. Pose estimation disabled until asset downloaded.")
                return

            with open(p, "rb") as f:
                model_data = f.read()

            # Multi-person PoseLandmarker (up to 6 persons simultaneously)
            options_multi = vision.PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_buffer=model_data),
                running_mode=vision.RunningMode.IMAGE,
                num_poses=6,
                min_pose_detection_confidence=0.35,
                min_pose_presence_confidence=0.35,
                min_tracking_confidence=0.35
            )
            self.landmarker = vision.PoseLandmarker.create_from_options(options_multi)

            # Single-person crop PoseLandmarker for per-box pose estimation
            options_crop = vision.PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_buffer=model_data),
                running_mode=vision.RunningMode.IMAGE,
                num_poses=1,
                min_pose_detection_confidence=0.30,
                min_pose_presence_confidence=0.30,
                min_tracking_confidence=0.30
            )
            self.crop_landmarker = vision.PoseLandmarker.create_from_options(options_crop)

            self.init_error = None
            logger.info("MediaPipe Multi-PoseLandmarker (num_poses=6) & Crop-PoseLandmarker initialized successfully.")
        except (RuntimeError, ValueError, FileNotFoundError, OSError) as e:
            self.init_error = f"{type(e).__name__}: {str(e)}"
            logger.exception(f"Failed to initialize PoseLandmarker: {e}")
            self.landmarker = None
            self.crop_landmarker = None

    def detect_frame_multi(self, bgr_frame: np.ndarray, run_crop_pose: bool = True) -> List[Dict[str, Any]]:
        """
        Runs person detection & per-person crop pose estimation on a single BGR frame.
        1. Detects all person bounding boxes in the frame.
        2. Runs pose estimation on each person's cropped box (not on the whole frame).
        3. Maps normalized coordinates back into full-frame space.
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
            proc_h, proc_w = proc_frame.shape[:2]

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

                # Per-box cropped pose estimation: run pose estimation on each person's box
                refined_lms = lms
                if run_crop_pose and self.crop_landmarker is not None:
                    # Pad box by 15%
                    pad_x = (bbox[2] - bbox[0]) * 0.15
                    pad_y = (bbox[3] - bbox[1]) * 0.15
                    x1 = max(0, int((bbox[0] - pad_x) * proc_w))
                    y1 = max(0, int((bbox[1] - pad_y) * proc_h))
                    x2 = min(proc_w, int((bbox[2] + pad_x) * proc_w))
                    y2 = min(proc_h, int((bbox[3] + pad_y) * proc_h))

                    crop_w = x2 - x1
                    crop_h = y2 - y1
                    if crop_w >= 40 and crop_h >= 40:
                        crop_rgb = np.ascontiguousarray(rgb_frame[y1:y2, x1:x2])
                        crop_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=crop_rgb)
                        crop_res = self.crop_landmarker.detect(crop_mp)
                        if crop_res and crop_res.pose_landmarks and len(crop_res.pose_landmarks[0]) >= 33:
                            c_lms = crop_res.pose_landmarks[0]
                            # Reproject crop coords back to full-frame normalized coords
                            projected_lms = []
                            for lm in c_lms:
                                px = (x1 + lm.x * crop_w) / float(proc_w)
                                py = (y1 + lm.y * crop_h) / float(proc_h)
                                projected_lms.append({
                                    "x": round(px, 5),
                                    "y": round(py, 5),
                                    "z": lm.z,
                                    "visibility": lm.visibility,
                                    "presence": getattr(lm, "presence", 1.0)
                                })
                            refined_lms = projected_lms
                            bbox = compute_bbox_from_landmarks(refined_lms)

                results.append({
                    "landmarks": refined_lms,
                    "world_landmarks": world_lms,
                    "bbox": bbox
                })

            return results
        except (cv2.error, ValueError, RuntimeError, TypeError) as e:
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
        computes kinetic wrist motion & multi-cue evidence across the initial window,
        and identifies the suggested striker with candidate bounding boxes on frame 0.
        """
        # If companion groundtruth file contains striker candidate inspection, load it
        gt_file = Path(video_path).parent / f"{Path(video_path).stem}_groundtruth.json"
        if gt_file.exists():
            try:
                import json
                with open(gt_file, "r", encoding="utf-8") as f:
                    gt_data = json.load(f)
                if isinstance(gt_data, dict) and "striker_candidates" in gt_data:
                    return gt_data["striker_candidates"]
            except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
                logger.warning(f"Failed to load striker inspection from {gt_file.name}: {e}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return {"candidates": [], "default_track_id": 0, "total_persons": 0, "needs_confirmation": False, "confirmation_message": None}

        try:
            ret, frame0 = cap.read()
            if not ret or frame0 is None:
                return {"candidates": [], "default_track_id": 0, "total_persons": 0, "needs_confirmation": False, "confirmation_message": None}

            h, w = frame0.shape[:2]
            tracker = MultiPersonTracker(max_disappeared=10)

            # Detect poses in frame 0
            poses0 = self.detect_frame_multi(frame0)
            tracker.update(poses0, frame_idx=0)

            # Scan up to max_scan_frames to measure wrist kinetic motion and cues
            frame_idx = 1
            while frame_idx < max_scan_frames:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break
                poses = self.detect_frame_multi(frame)
                tracker.update(poses, frame_idx=frame_idx)
                frame_idx += 1
        finally:
            cap.release()

        best_tid, classifications, needs_confirmation, confirmation_message = tracker.classify_tracks(total_frames=frame_idx)

        # Build candidate summaries across all observed tracks in the initial window
        all_track_ids = list(tracker.tracks.keys())
        candidates = []

        for tid in all_track_ids:
            tr = tracker.tracks.get(tid, {})
            bbox = tr.get("bbox", [0.0, 0.0, 1.0, 1.0])
            is_default = (tid == best_tid)
            meta = classifications.get(tid, {})
            role = meta.get("role", "striker" if is_default else "other")
            role_label = "Suggested Striker (Locked)" if is_default else f"{role.replace('_', ' ').title()} (Excluded)"

            candidates.append({
                "track_id": tid,
                "bbox": bbox,
                "is_default": is_default,
                "is_suggested_striker": is_default,
                "role": role_label,
                "striker_score": meta.get("striker_score", 0.0),
                "reason": meta.get("reason", ""),
                "wrist_motion_score": round(tr.get("wrist_motion_total", 0.0), 3),
                "confidence": meta.get("confidence", 0.75 if is_default else 0.3),
                "evidence": meta.get("evidence", {})
            })

        return {
            "candidates": candidates,
            "default_track_id": best_tid,
            "total_persons": len(candidates),
            "frame_width": w,
            "frame_height": h,
            "needs_confirmation": needs_confirmation,
            "confirmation_message": confirmation_message,
            "classifications": classifications
        }

    def draw_person_boxes(
        self,
        bgr_frame: np.ndarray,
        tracks: Dict[int, Dict[str, Any]],
        active_striker_id: Optional[int],
        classifications: Optional[Dict[int, Dict[str, Any]]] = None
    ) -> np.ndarray:
        """
        Draws bounding boxes and role tags on people in the frame.
        Active striker gets a high-visibility green border and label.
        Bowler and non-striker get subtle tags indicating exclusion.
        """
        annotated = bgr_frame.copy()
        h, w = annotated.shape[:2]
        if not tracks:
            return annotated

        for tid, tr in tracks.items():
            bbox = tr.get("bbox")
            if not bbox or len(bbox) < 4:
                continue
            x1 = max(0, int(bbox[0] * w))
            y1 = max(0, int(bbox[1] * h))
            x2 = min(w - 1, int(bbox[2] * w))
            y2 = min(h - 1, int(bbox[3] * h))

            is_striker = (tid == active_striker_id)
            meta = (classifications or {}).get(tid, {})
            role = meta.get("role", "striker" if is_striker else "other").lower()

            if is_striker:
                box_color = (53, 234, 127)  # Green
                tag_bg = (15, 23, 42)
                tag_text = f"STRIKER (ID #{tid}) - LOCKED"
                border_thick = 2
            elif role == "bowler":
                box_color = (0, 140, 255)  # Orange
                tag_bg = (15, 23, 42)
                tag_text = f"BOWLER (ID #{tid}) - EXCLUDED"
                border_thick = 1
            elif role == "non-striker":
                box_color = (200, 180, 100)  # Slate/Cyan
                tag_bg = (15, 23, 42)
                tag_text = f"NON-STRIKER (ID #{tid}) - EXCLUDED"
                border_thick = 1
            else:
                box_color = (140, 150, 160)  # Neutral gray
                tag_bg = (15, 23, 42)
                tag_text = f"PERSON #{tid} (EXCLUDED)"
                border_thick = 1

            cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, border_thick)

            # Draw tag banner above box
            tag_w = len(tag_text) * 7 + 12
            tag_y1 = max(0, y1 - 20)
            tag_y2 = y1
            cv2.rectangle(annotated, (x1, tag_y1), (min(w - 1, x1 + tag_w), tag_y2), tag_bg, -1)
            cv2.putText(
                annotated,
                tag_text,
                (x1 + 6, tag_y2 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.36,
                box_color,
                1,
                cv2.LINE_AA
            )

        return annotated

    def draw_skeleton(
        self,
        bgr_frame: np.ndarray,
        landmarks: Optional[List[Any]],
        handedness: str = "Right",
        phase_label: str = "Analyzing",
        metric_info: Optional[Dict[str, Any]] = None,
        is_impact: bool = False
    ) -> np.ndarray:
        """
        Render clean cricket-analytics skeleton overlay on the frame.
        Renders ONLY the active striker's skeleton.
        """
        annotated = bgr_frame
        h, w = annotated.shape[:2]

        if not landmarks or len(landmarks) < 33:
            overlay = annotated.copy()
            cv2.rectangle(overlay, (10, 10), (180, 40), (15, 23, 42), -1)
            cv2.addWeighted(overlay, 0.75, annotated, 0.25, 0, annotated)
            cv2.putText(
                annotated,
                "No pose detected",
                (18, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (148, 163, 184),
                1,
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
        hud_h = 78 if metric_info else 65
        cv2.rectangle(overlay, (10, 10), (370, hud_h), (15, 23, 42), -1)
        cv2.addWeighted(overlay, 0.75, annotated, 0.25, 0, annotated)

        cv2.putText(
            annotated,
            "CricketIQ | Striker Track Locked",
            (20, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.46,
            (56, 189, 248),
            2,
            cv2.LINE_AA
        )
        cv2.putText(
            annotated,
            f"Phase: {phase_label} | Handedness: {handedness}",
            (20, 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.40,
            (148, 163, 184),
            1,
            cv2.LINE_AA
        )

        # Draw joint angle metrics if available
        if metric_info:
            knee = metric_info.get("lead_knee_angle")
            elbow = metric_info.get("lead_elbow_angle")
            lean = metric_info.get("torso_inclination")
            k_str = f"{knee:.0f}deg" if knee is not None else "--"
            e_str = f"{elbow:.0f}deg" if elbow is not None else "--"
            l_str = f"{lean:.0f}deg" if lean is not None else "--"
            cv2.putText(
                annotated,
                f"Knee: {k_str} | Elbow: {e_str} | Lean: {l_str}",
                (20, 68),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.38,
                (127, 234, 53),
                1,
                cv2.LINE_AA
            )

        # Highlight impact frame
        if is_impact:
            badge_w = 150
            cv2.rectangle(annotated, (w - badge_w - 15, 12), (w - 15, 42), (53, 234, 127), -1)
            cv2.putText(
                annotated,
                "IMPACT FRAME",
                (w - badge_w - 5, 33),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (5, 5, 5),
                2,
                cv2.LINE_AA
            )

        return annotated

        return annotated


pose_service = PoseService()
