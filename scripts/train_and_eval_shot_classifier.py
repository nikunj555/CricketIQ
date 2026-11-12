"""
CricketIQ — Feature Extractor, Trainer & Held-out Evaluation
Trains a robust HistGradientBoostingClassifier on extracted kinematic features,
evaluates a held-out test split, prints confusion matrix and feature values,
and serializes the model to backend/app/models/assets/shot_classifier.joblib.
"""

import sys
import math
import logging
from pathlib import Path
import numpy as np
import joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import confusion_matrix, classification_report

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.reference_service import reference_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "stride_ratio",
    "min_lead_knee_p10",
    "min_rear_knee_p10",
    "rear_knee_ground_dist",
    "hip_drop_impact",
    "max_hip_drop",
    "bat_path_dx",
    "bat_path_dy",
    "bat_path_horizontal_ratio",
    "wrist_span_x_norm",
    "wrist_span_y_norm",
    "impact_bat_angle",
    "horizontal_bat_ratio",
    "hand_height_rel_hip",
    "impact_wrist_y_rel_shoulder",
    "mean_torso_lean",
    "torso_lean_impact",
    "head_over_lead_foot",
    "is_side_on"
]


def extract_features_from_frame_metrics(
    frame_metrics: list,
    camera_view: str = "side-on",
    handedness: str = "Right"
) -> tuple[dict, np.ndarray]:
    """
    Extracts physically sound biomechanical features separating cricket shots:
    - Swing window from wrist speed and acceleration
    - Landmark smoothing & low visibility masking
    - 10th-percentile angles (not single minimum)
    - Lengths normalized by standing leg length
    """
    valid_frames = [m for m in frame_metrics if m.get("pose_detected")]
    if not valid_frames:
        feat_dict = {k: 0.0 for k in FEATURE_NAMES}
        return feat_dict, np.zeros(len(FEATURE_NAMES), dtype=np.float32)

    is_left = handedness.strip().lower() == "left"
    is_side_on = 0.0 if any(v in camera_view.lower() for v in ["front", "behind", "pitch", "bowler"]) else 1.0

    # 1. Determine setup frames (standing posture at crease)
    n_total = len(valid_frames)
    setup_n = max(3, int(n_total * 0.20))
    setup_frames = valid_frames[:setup_n]

    standing_hip_ys = []
    standing_ank_ys = []
    torso_lens = []

    for f in setup_frames:
        lms = f.get("landmarks", [])
        if len(lms) >= 29:
            hy = (lms[23]["y"] + lms[24]["y"]) / 2.0
            ay = (lms[27]["y"] + lms[28]["y"]) / 2.0
            sy = (lms[11]["y"] + lms[12]["y"]) / 2.0
            standing_hip_ys.append(hy)
            standing_ank_ys.append(ay)
            td = abs(hy - sy)
            if 0.10 < td < 0.60:
                torso_lens.append(td)

    base_hip_y = float(np.mean(standing_hip_ys)) if standing_hip_ys else 0.55
    base_ank_y = float(np.mean(standing_ank_ys)) if standing_ank_ys else 0.85
    leg_len = max(0.18, abs(base_ank_y - base_hip_y))
    torso_len = max(0.12, float(np.mean(torso_lens)) if torso_lens else 0.28)

    # 2. Find Swing Window from wrist speed & acceleration
    wrist_speeds = []
    prev_wx, prev_wy = None, None
    for f in valid_frames:
        wx = f.get("lead_wrist_x") or f.get("bat_tip_x")
        wy = f.get("lead_wrist_y") or f.get("bat_tip_y")
        if wx is not None and wy is not None:
            if prev_wx is not None and prev_wy is not None:
                sp = math.sqrt((wx - prev_wx) ** 2 + (wy - prev_wy) ** 2)
            else:
                sp = 0.0
            prev_wx, prev_wy = wx, wy
        else:
            sp = f.get("lead_wrist_speed", 0.0) or 0.0
        wrist_speeds.append(sp)

    phase_swing_indices = [
        i for i, f in enumerate(valid_frames)
        if any(k in str(f.get("phase", "")).lower() for k in ("backlift", "stride", "downswing", "impact", "follow"))
    ]

    if len(phase_swing_indices) >= 5:
        start_idx = max(0, min(phase_swing_indices) - 2)
        end_idx = min(n_total - 1, max(phase_swing_indices) + 2)
    elif wrist_speeds and max(wrist_speeds) > 0.01:
        peak_idx = int(np.argmax(wrist_speeds))
        peak_val = wrist_speeds[peak_idx]
        thresh = peak_val * 0.22
        start_idx = peak_idx
        while start_idx > 0 and wrist_speeds[start_idx] >= thresh:
            start_idx -= 1
        end_idx = peak_idx
        while end_idx < n_total - 1 and wrist_speeds[end_idx] >= thresh:
            end_idx += 1
        start_idx = max(0, start_idx - 2)
        end_idx = min(n_total - 1, end_idx + 2)
    else:
        start_idx = 0
        end_idx = n_total - 1

    swing_frames = valid_frames[start_idx : end_idx + 1]
    if len(swing_frames) < 3:
        swing_frames = valid_frames

    # 3. Filter landmarks by visibility and smooth angles
    clean_lead_knees = []
    clean_rear_knees = []
    clean_hip_ys = []
    clean_torso_leans = []

    for f in swing_frames:
        lms = f.get("landmarks", [])
        lk = f.get("lead_knee_angle")
        rk = f.get("rear_knee_angle")
        if len(lms) >= 29:
            l_vis = lms[25].get("v", 1.0) * lms[27].get("v", 1.0)
            r_vis = lms[26].get("v", 1.0) * lms[28].get("v", 1.0)
            hip_vis = lms[23].get("v", 1.0) * lms[24].get("v", 1.0)
            if lk is not None and l_vis >= 0.25:
                clean_lead_knees.append(lk)
            if rk is not None and r_vis >= 0.25:
                clean_rear_knees.append(rk)
            if hip_vis >= 0.25:
                clean_hip_ys.append((lms[23]["y"] + lms[24]["y"]) / 2.0)
        else:
            if lk is not None:
                clean_lead_knees.append(lk)
            if rk is not None:
                clean_rear_knees.append(rk)

        tl = f.get("torso_inclination")
        if tl is not None:
            clean_torso_leans.append(tl)

    min_lead_knee_p10 = float(np.percentile(clean_lead_knees, 10)) if clean_lead_knees else 140.0
    min_rear_knee_p10 = float(np.percentile(clean_rear_knees, 10)) if clean_rear_knees else 145.0
    mean_torso_lean = float(np.mean(clean_torso_leans)) if clean_torso_leans else 18.0

    # 4. Impact frame metrics
    impact_frames = [f for f in swing_frames if "impact" in str(f.get("phase", "")).lower()]
    impact_f = impact_frames[len(impact_frames) // 2] if impact_frames else swing_frames[len(swing_frames) // 2]
    imp_lms = impact_f.get("landmarks", [])

    if len(imp_lms) >= 29:
        imp_hip_y = (imp_lms[23]["y"] + imp_lms[24]["y"]) / 2.0
        imp_sh_y = (imp_lms[11]["y"] + imp_lms[12]["y"]) / 2.0
        imp_r_knee_y = imp_lms[26]["y"]
        imp_r_ank_y = imp_lms[28]["y"]
        imp_l_ank_x = imp_lms[27]["x"]
        imp_head_x = imp_lms[0]["x"]
        imp_lw_x = imp_lms[15]["x"]
        imp_lw_y = imp_lms[15]["y"]
    else:
        imp_hip_y = base_hip_y
        imp_sh_y = base_hip_y - torso_len
        imp_r_knee_y = base_hip_y + 0.15
        imp_r_ank_y = base_ank_y
        imp_l_ank_x = 0.35
        imp_head_x = 0.35
        imp_lw_x = 0.35
        imp_lw_y = base_hip_y

    hip_drop_impact = (imp_hip_y - base_hip_y) / leg_len
    max_hip_y = max(clean_hip_ys) if clean_hip_ys else imp_hip_y
    max_hip_drop = (max_hip_y - base_hip_y) / leg_len
    rear_knee_ground_dist = (imp_r_ank_y - imp_r_knee_y) / leg_len
    hand_height_rel_hip = (imp_lw_y - imp_hip_y) / leg_len
    impact_wrist_y_rel_shoulder = (imp_lw_y - imp_sh_y) / torso_len
    torso_lean_impact = float(impact_f.get("torso_inclination") or mean_torso_lean)
    head_over_lead_foot = (imp_head_x - imp_l_ank_x) / leg_len
    if is_left:
        head_over_lead_foot = -head_over_lead_foot

    # 5. Stance & Stride Ratio
    stance_widths = [f["stance_width_norm"] for f in swing_frames if f.get("stance_width_norm") is not None]
    base_stances = [f["stance_width_norm"] for f in setup_frames if f.get("stance_width_norm") is not None]
    base_st = float(np.mean(base_stances)) if base_stances else 1.0
    max_st = float(np.max(stance_widths)) if stance_widths else base_st
    stride_ratio = max_st / max(0.40, base_st)

    # 6. Bat path dx, dy over swing
    wrist_xs, wrist_ys = [], []
    for f in swing_frames:
        wx = f.get("lead_wrist_x") or f.get("bat_tip_x")
        wy = f.get("lead_wrist_y") or f.get("bat_tip_y")
        if wx is not None and wy is not None:
            adj_x = (1.0 - wx) if is_left else wx
            wrist_xs.append(adj_x)
            wrist_ys.append(wy)

    if len(wrist_xs) >= 4:
        st_i = 0
        end_i = min(len(wrist_xs) - 1, int(len(wrist_xs) * 0.65))
        bat_path_dx = (wrist_xs[end_i] - wrist_xs[st_i]) / leg_len
        bat_path_dy = (wrist_ys[end_i] - wrist_ys[st_i]) / leg_len
        w_span_x = (max(wrist_xs) - min(wrist_xs)) / torso_len
        w_span_y = (max(wrist_ys) - min(wrist_ys)) / torso_len
    else:
        bat_path_dx = 0.0
        bat_path_dy = -0.5
        w_span_x = 0.3
        w_span_y = 0.5

    bat_path_horizontal_ratio = abs(bat_path_dx) / (abs(bat_path_dx) + abs(bat_path_dy) + 1e-4)

    # 7. Bat angles
    bat_angles = [f["bat_angle_deg"] for f in swing_frames if f.get("bat_detected") and f.get("bat_angle_deg") is not None]
    imp_angles = [f["bat_angle_deg"] for f in impact_frames if f.get("bat_angle_deg") is not None]
    impact_bat_angle = float(np.mean(imp_angles)) if imp_angles else (float(bat_angles[len(bat_angles)//2]) if bat_angles else 15.0)
    horiz_count = sum(1 for a in bat_angles if abs(a) >= 42.0)
    horizontal_bat_ratio = horiz_count / max(1, len(bat_angles)) if bat_angles else (1.0 if abs(impact_bat_angle) >= 42.0 else 0.0)

    feat_dict = {
        "stride_ratio": round(stride_ratio, 2),
        "min_lead_knee_p10": round(min_lead_knee_p10, 1),
        "min_rear_knee_p10": round(min_rear_knee_p10, 1),
        "rear_knee_ground_dist": round(rear_knee_ground_dist, 2),
        "hip_drop_impact": round(hip_drop_impact, 2),
        "max_hip_drop": round(max_hip_drop, 2),
        "bat_path_dx": round(bat_path_dx, 2),
        "bat_path_dy": round(bat_path_dy, 2),
        "bat_path_horizontal_ratio": round(bat_path_horizontal_ratio, 2),
        "wrist_span_x_norm": round(w_span_x, 2),
        "wrist_span_y_norm": round(w_span_y, 2),
        "impact_bat_angle": round(impact_bat_angle, 1),
        "horizontal_bat_ratio": round(horizontal_bat_ratio, 2),
        "hand_height_rel_hip": round(hand_height_rel_hip, 2),
        "impact_wrist_y_rel_shoulder": round(impact_wrist_y_rel_shoulder, 2),
        "mean_torso_lean": round(mean_torso_lean, 1),
        "torso_lean_impact": round(torso_lean_impact, 1),
        "head_over_lead_foot": round(head_over_lead_foot, 2),
        "is_side_on": float(is_side_on)
    }

    vec = np.array([feat_dict[k] for k in FEATURE_NAMES], dtype=np.float32)
    return feat_dict, vec


def synthesize_reference_sequence(shot_name: str, num_frames: int = 45) -> list[dict]:
    """Synthesizes a realistic sequence of frame metrics from reference_shots.json definition."""
    ref = reference_service.get_shot_reference(shot_name)
    if not ref:
        return []
    phases = ref["phases"]
    phase_keys = ["stance", "backlift", "stride", "downswing", "impact", "follow_through", "recovery"]

    keyframes = [phases[k]["keyframe_pose"] for k in phase_keys]
    weights = [max(0.05, float(kf.get("duration_weight", 0.14))) for kf in keyframes]
    total_w = sum(weights)
    frame_counts = [max(3, int(round((w / total_w) * num_frames))) for w in weights]

    frames = []
    f_acc = 0
    for p_idx, kf in enumerate(keyframes):
        n_p = frame_counts[p_idx]
        ph_name = phase_keys[p_idx]
        next_kf = keyframes[min(len(keyframes) - 1, p_idx + 1)]

        for i in range(n_p):
            t = i / float(n_p)
            cur_lk = kf.get("lead_knee_flex", 140.0) + t * (next_kf.get("lead_knee_flex", 140.0) - kf.get("lead_knee_flex", 140.0))
            cur_rk = kf.get("rear_knee_flex", 145.0) + t * (next_kf.get("rear_knee_flex", 145.0) - kf.get("rear_knee_flex", 145.0))
            cur_tl = kf.get("torso_lean", 18.0) + t * (next_kf.get("torso_lean", 18.0) - kf.get("torso_lean", 18.0))
            cur_ba = kf.get("bat_angle", 15.0) + t * (next_kf.get("bat_angle", 15.0) - kf.get("bat_angle", 15.0))
            cur_hx = kf.get("hands_x", 0.3) + t * (next_kf.get("hands_x", 0.3) - kf.get("hands_x", 0.3))
            cur_hy = kf.get("hands_y", 0.5) + t * (next_kf.get("hands_y", 0.5) - kf.get("hands_y", 0.5))
            cur_hip = kf.get("hip_y", 0.2) + t * (next_kf.get("hip_y", 0.2) - kf.get("hip_y", 0.2))
            st_w = 1.0 + abs(kf.get("lead_stride_x", 0.4) - kf.get("rear_foot_x", -0.1))

            # Synthesize 33 landmarks
            lms = [{"x": 0.35, "y": 0.20, "v": 0.95}] * 11
            # Shoulders (11, 12)
            lms.extend([{"x": 0.32, "y": 0.28, "v": 0.95}, {"x": 0.38, "y": 0.28, "v": 0.95}])
            # Elbows (13, 14)
            lms.extend([{"x": 0.33, "y": 0.38, "v": 0.95}, {"x": 0.37, "y": 0.38, "v": 0.95}])
            # Wrists (15, 16)
            lms.extend([{"x": cur_hx, "y": cur_hy, "v": 0.95}, {"x": cur_hx + 0.02, "y": cur_hy, "v": 0.95}])
            # Pinkies, index, thumb (17..22)
            lms.extend([{"x": cur_hx, "y": cur_hy, "v": 0.95}] * 6)
            # Hips (23, 24)
            lms.extend([{"x": 0.33, "y": 0.50 + cur_hip * 0.3, "v": 0.95}, {"x": 0.37, "y": 0.50 + cur_hip * 0.3, "v": 0.95}])
            # Knees (25, 26)
            lms.extend([{"x": 0.33, "y": 0.68 + cur_hip * 0.2, "v": 0.95}, {"x": 0.37, "y": 0.68 + cur_hip * 0.2, "v": 0.95}])
            # Ankles (27, 28)
            lms.extend([{"x": 0.32, "y": 0.85, "v": 0.95}, {"x": 0.38, "y": 0.85, "v": 0.95}])
            # Feet (29..32)
            lms.extend([{"x": 0.32, "y": 0.88, "v": 0.95}] * 4)

            frames.append({
                "pose_detected": True,
                "confidence": 0.92,
                "frame_index": f_acc,
                "timestamp_sec": f_acc / 30.0,
                "lead_knee_angle": cur_lk,
                "rear_knee_angle": cur_rk,
                "torso_inclination": cur_tl,
                "bat_angle_deg": cur_ba,
                "bat_detected": True,
                "lead_wrist_x": cur_hx,
                "lead_wrist_y": cur_hy,
                "lead_wrist_speed": 0.05 if "downswing" in ph_name or "impact" in ph_name else 0.01,
                "stance_width_norm": st_w,
                "phase": ph_name.capitalize(),
                "landmarks": lms
            })
            f_acc += 1

    return frames


def augment_frame_metrics(frames: list[dict], mirror: bool = False, speed_factor: float = 1.0, noise_std: float = 0.0) -> list[dict]:
    """Applies realistic augmentation: mirroring, temporal resampling, and landmark noise."""
    new_frames = []
    n = len(frames)
    new_len = max(15, int(n * speed_factor))

    for idx in range(new_len):
        src_i = min(n - 1, int(idx / speed_factor))
        f = dict(frames[src_i])
        f["frame_index"] = idx
        f["timestamp_sec"] = idx / 30.0

        if noise_std > 0.0:
            if f.get("lead_knee_angle") is not None:
                f["lead_knee_angle"] = float(f["lead_knee_angle"] + np.random.normal(0, noise_std * 35.0))
            if f.get("rear_knee_angle") is not None:
                f["rear_knee_angle"] = float(f["rear_knee_angle"] + np.random.normal(0, noise_std * 35.0))
            if f.get("torso_inclination") is not None:
                f["torso_inclination"] = float(f["torso_inclination"] + np.random.normal(0, noise_std * 10.0))

        if mirror:
            if f.get("lead_wrist_x") is not None:
                f["lead_wrist_x"] = 1.0 - f["lead_wrist_x"]
            if f.get("bat_angle_deg") is not None:
                f["bat_angle_deg"] = -f["bat_angle_deg"]
            if f.get("landmarks"):
                mirr_lms = []
                for lm in f["landmarks"]:
                    mirr_lms.append({
                        "x": 1.0 - lm["x"],
                        "y": lm["y"] + (np.random.normal(0, noise_std * 0.02) if noise_std > 0 else 0.0),
                        "v": lm.get("v", 1.0)
                    })
                f["landmarks"] = mirr_lms

        new_frames.append(f)
    return new_frames


def train_and_evaluate():
    logger.info("Building dataset from reference definitions and labeled videos...")
    
    classes = [
        "Cover Drive", "Straight Drive", "On Drive", "Off Drive", "Lofted Drive",
        "Forward Defensive", "Back-foot Defensive", "Back-foot Punch",
        "Square Cut", "Late Cut", "Upper Cut",
        "Pull Shot", "Hook Shot",
        "Flick Shot", "Leg Glance", "Clip Shot",
        "Sweep", "Slog Sweep", "Reverse Sweep", "Paddle Sweep",
        "Slog", "Switch Hit", "Scoop Shot", "Ramp Shot", "Helicopter Shot"
    ]
    class_to_idx = {c: i for i, c in enumerate(classes)}

    X_train, y_train, groups_train = [], [], []
    X_test, y_test, test_names = [], [], []

    # 1. Synthesize reference definitions with variations
    for c in classes:
        base_seq = synthesize_reference_sequence(c, num_frames=45)
        if not base_seq:
            continue
        
        _, vec = extract_features_from_frame_metrics(base_seq)
        X_train.append(vec)
        y_train.append(class_to_idx[c])
        groups_train.append(f"synth_{c}")

        # Augmentations: mirror, speed (0.85x, 1.15x), noise
        for mirror in [False, True]:
            for spd in [0.85, 1.15]:
                for noise in [0.01, 0.02]:
                    aug = augment_frame_metrics(base_seq, mirror=mirror, speed_factor=spd, noise_std=noise)
                    _, a_vec = extract_features_from_frame_metrics(aug, handedness="Left" if mirror else "Right")
                    X_train.append(a_vec)
                    y_train.append(class_to_idx[c])
                    groups_train.append(f"synth_{c}")

    # 2. Extract from labeled fixture videos
    from backend.app.repositories.session_repository import session_repo

    test_clips = [
        ("feat_test_user_cover_drive", "Cover Drive", "user_cover_drive.mp4"),
        ("feat_test_user_straight_drive", "Straight Drive", "user_straight_drive.mp4"),
        ("feat_test_pull_shot", "Pull Shot", "pull_shot.mp4"),
        ("feat_test_sample_sweep", "Sweep", "sample_sweep.mp4"),
        ("feat_test_sample_forward_defensive", "Forward Defensive", "sample_forward_defensive.mp4")
    ]

    for sid, shot_label, vname in test_clips:
        sess = session_repo.get_session(sid)
        if sess and sess.get("result"):
            fms = sess["result"]["time_series"]
            feat_dict, vec = extract_features_from_frame_metrics(fms)
            X_test.append(vec)
            y_test.append(class_to_idx[shot_label])
            test_names.append(f"{vname} ({shot_label})")
            print(f"\n--- Extracted Features for {vname} ({shot_label}) ---")
            for k in FEATURE_NAMES:
                print(f"  {k:28}: {feat_dict[k]}")

    X_train = np.array(X_train, dtype=np.float32)
    y_train = np.array(y_train, dtype=np.int64)

    logger.info(f"Training HistGradientBoostingClassifier on {len(X_train)} samples across {len(classes)} classes...")
    clf = HistGradientBoostingClassifier(
        max_iter=120,
        learning_rate=0.08,
        max_leaf_nodes=31,
        min_samples_leaf=3,
        random_state=42
    )
    clf.fit(X_train, y_train)

    # Save model asset
    out_dir = ROOT_DIR / "backend" / "app" / "models" / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / "shot_classifier.joblib"
    joblib.dump({"model": clf, "classes": classes, "feature_names": FEATURE_NAMES}, model_path)
    logger.info(f"Model successfully saved to {model_path}")

    # Evaluate on held-out test clips
    if X_test:
        X_test = np.array(X_test, dtype=np.float32)
        y_test = np.array(y_test, dtype=np.int64)
        preds = clf.predict(X_test)
        probs = clf.predict_proba(X_test)

        print("\n=======================================================")
        print(" HELD-OUT TEST EVALUATION ON REAL / FIXTURE CLIPS")
        print("=======================================================")
        for i, name in enumerate(test_names):
            true_label = classes[y_test[i]]
            pred_label = classes[preds[i]]
            top3_idx = np.argsort(probs[i])[::-1][:3]
            top3 = [(classes[idx], round(probs[i][idx], 3)) for idx in top3_idx]
            print(f"{name:40} -> Predicted: {pred_label:18} (True: {true_label}) | Top 3: {top3}")

        # Confusion Matrix
        print("\n--- Held-Out Confusion Matrix ---")
        unique_labels = sorted(list(set(y_test) | set(preds)))
        label_names = [classes[idx] for idx in unique_labels]
        cm = confusion_matrix(y_test, preds, labels=unique_labels)
        print("Classes:", label_names)
        print(cm)

    return clf


if __name__ == "__main__":
    train_and_evaluate()
