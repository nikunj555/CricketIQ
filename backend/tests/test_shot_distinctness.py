"""
Test suite validating that all 25 catalogue cricket shots have distinct biomechanical
technique and correct bat grip geometry in reference_shots.json.
"""

import json
import math
from pathlib import Path
import pytest

REFERENCE_JSON_PATH = Path("backend/app/data/reference_shots.json")
FRONTEND_JSON_PATH = Path("frontend/src/data/reference_shots.json")

REQUIRED_PHASES = [
    "stance", "backlift", "stride", "downswing", "impact", "follow_through", "recovery"
]

REQUIRED_KEYFRAME_FIELDS = [
    "hip_x", "hip_y", "lead_stride_x", "lead_stride_dir_deg", "rear_foot_x",
    "rear_foot_mode", "lead_knee_flex", "rear_knee_flex", "lead_elbow_flex",
    "rear_elbow_flex", "pelvis_rotation_deg", "shoulder_rotation_deg",
    "head_offset_x", "hands_x", "hands_y", "bat_plane", "bat_angle",
    "bat_tip_x", "bat_tip_y", "wrist_cock_deg", "torso_lean", "shoulder_tilt",
    "duration_weight", "cue"
]


def load_reference_data():
    assert REFERENCE_JSON_PATH.exists(), f"{REFERENCE_JSON_PATH} missing"
    assert FRONTEND_JSON_PATH.exists(), f"{FRONTEND_JSON_PATH} missing"
    backend_data = json.loads(REFERENCE_JSON_PATH.read_text(encoding="utf-8"))
    frontend_data = json.loads(FRONTEND_JSON_PATH.read_text(encoding="utf-8"))
    assert len(backend_data) == 25, f"Backend expected 25 shots, found {len(backend_data)}"
    assert len(frontend_data) == 25, f"Frontend expected 25 shots, found {len(frontend_data)}"
    return backend_data


def get_pose_vector(keyframe_pose):
    return [
        float(keyframe_pose["hip_x"]),
        float(keyframe_pose["hip_y"]),
        float(keyframe_pose["lead_stride_x"]),
        float(keyframe_pose["lead_stride_dir_deg"]) / 90.0,
        float(keyframe_pose["rear_foot_x"]),
        float(keyframe_pose["lead_knee_flex"]) / 180.0,
        float(keyframe_pose["rear_knee_flex"]) / 180.0,
        float(keyframe_pose["lead_elbow_flex"]) / 180.0,
        float(keyframe_pose["rear_elbow_flex"]) / 180.0,
        float(keyframe_pose["pelvis_rotation_deg"]) / 90.0,
        float(keyframe_pose["shoulder_rotation_deg"]) / 90.0,
        float(keyframe_pose["head_offset_x"]),
        float(keyframe_pose["hands_x"]),
        float(keyframe_pose["hands_y"]),
        float(keyframe_pose["bat_angle"]) / 180.0,
        float(keyframe_pose["bat_tip_x"]),
        float(keyframe_pose["bat_tip_y"]),
        float(keyframe_pose["wrist_cock_deg"]) / 90.0,
        float(keyframe_pose["torso_lean"]) / 45.0,
        float(keyframe_pose["shoulder_tilt"]) / 45.0,
    ]


def euclidean_distance(v1, v2):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))


def test_all_25_shots_and_7_phases_exist_with_required_fields():
    """Assert 25 shots * 7 phases exist with all required fields in reference_shots.json."""
    data = load_reference_data()
    assert len(data) == 25

    for shot_name, shot in data.items():
        assert "phases" in shot, f"{shot_name} missing 'phases'"
        assert len(shot["phases"]) == 7, f"{shot_name} has {len(shot['phases'])} phases, expected 7"

        for p_name in REQUIRED_PHASES:
            assert p_name in shot["phases"], f"{shot_name} missing phase '{p_name}'"
            phase = shot["phases"][p_name]
            assert "keyframe_pose" in phase, f"{shot_name} phase '{p_name}' missing 'keyframe_pose'"
            kf = phase["keyframe_pose"]

            for field in REQUIRED_KEYFRAME_FIELDS:
                assert field in kf, f"{shot_name} phase '{p_name}' keyframe_pose missing '{field}'"


def test_all_25_keyframe_sets_are_unique_and_pairwise_distinct():
    """Assert all 25 shots are distinct with pairwise distance >= 0.15 at impact and follow-through."""
    data = load_reference_data()
    shots = list(data.keys())

    # Build full sequence signatures
    signatures = set()
    for s_name, shot in data.items():
        sig = tuple(
            tuple(get_pose_vector(shot["phases"][p]["keyframe_pose"]))
            for p in REQUIRED_PHASES
        )
        signatures.add(sig)

    assert len(signatures) == 25, f"Distinctness count must be 25, got {len(signatures)}"

    # Check pairwise Euclidean distances between impact and follow-through poses
    min_impact_dist = 999.0
    closest_impact_pair = None
    min_ft_dist = 999.0
    closest_ft_pair = None

    for i in range(len(shots)):
        for j in range(i + 1, len(shots)):
            s1, s2 = shots[i], shots[j]
            v1_imp = get_pose_vector(data[s1]["phases"]["impact"]["keyframe_pose"])
            v2_imp = get_pose_vector(data[s2]["phases"]["impact"]["keyframe_pose"])
            d_imp = euclidean_distance(v1_imp, v2_imp)

            if d_imp < min_impact_dist:
                min_impact_dist = d_imp
                closest_impact_pair = (s1, s2)

            v1_ft = get_pose_vector(data[s1]["phases"]["follow_through"]["keyframe_pose"])
            v2_ft = get_pose_vector(data[s2]["phases"]["follow_through"]["keyframe_pose"])
            d_ft = euclidean_distance(v1_ft, v2_ft)

            if d_ft < min_ft_dist:
                min_ft_dist = d_ft
                closest_ft_pair = (s1, s2)

            assert d_imp >= 0.15, f"Impact poses too close for {s1} vs {s2}: dist={d_imp:.4f} < 0.15"

    # Verify Cover Drive vs Straight Drive explicitly
    cd_sd_imp_dist = euclidean_distance(
        get_pose_vector(data["Cover Drive"]["phases"]["impact"]["keyframe_pose"]),
        get_pose_vector(data["Straight Drive"]["phases"]["impact"]["keyframe_pose"]),
    )
    print(f"\n[+] Closest impact pair: {closest_impact_pair} with distance {min_impact_dist:.4f}")
    print(f"[+] Closest follow-through pair: {closest_ft_pair} with distance {min_ft_dist:.4f}")
    print(f"[+] Cover Drive vs Straight Drive impact distance: {cd_sd_imp_dist:.4f}")

    assert cd_sd_imp_dist >= 0.15, f"Cover Drive and Straight Drive must be distinct (got {cd_sd_imp_dist:.4f})"


def test_bat_to_hands_grip_geometry():
    """Assert handle-to-hands distance < handle-to-tip distance across all 25 shots and all phases."""
    data = load_reference_data()

    for shot_name, shot in data.items():
        for phase_name in REQUIRED_PHASES:
            kf = shot["phases"][phase_name]["keyframe_pose"]

            hands_x = float(kf["hands_x"])
            hands_y = float(kf["hands_y"])
            tip_x = float(kf["bat_tip_x"])
            tip_y = float(kf["bat_tip_y"])

            # Compute bat axis u from hands to tip
            dx = tip_x - hands_x
            dy = tip_y - hands_y
            bat_len = math.hypot(dx, dy)
            if bat_len < 0.05:
                rad = math.radians(float(kf["bat_angle"]))
                ux = math.sin(rad)
                uy = -math.cos(rad)
                bat_len = 0.92
            else:
                ux = dx / bat_len
                uy = dy / bat_len

            # Butt sits 5% above top hand along -u
            butt_x = hands_x - ux * (bat_len * 0.05)
            butt_y = hands_y - uy * (bat_len * 0.05)

            # Distances
            dist_top_hand_to_butt = math.hypot(hands_x - butt_x, hands_y - butt_y)
            dist_top_hand_to_tip = math.hypot(hands_x - tip_x, hands_y - tip_y)

            # Hands grip handle (top 30%), blade extends beyond
            assert dist_top_hand_to_butt < dist_top_hand_to_tip, (
                f"{shot_name} [{phase_name}]: top hand is closer to tip ({dist_top_hand_to_tip:.3f}) "
                f"than butt ({dist_top_hand_to_butt:.3f}) - bat held by blade!"
            )


def test_shot_direction_and_technique_characteristics():
    """
    Assert technique directions:
    - Straight Drive bat vector points towards bowler (within 10 deg of vertical / pitch line)
    - Cover Drive points off-side
    - Pull Shot horizontal across the body
    - Sweep low to the ground with kneeling rear leg
    """
    data = load_reference_data()

    # 1. Straight Drive
    sd_imp = data["Straight Drive"]["phases"]["impact"]["keyframe_pose"]
    assert abs(float(sd_imp["bat_angle"])) <= 10.0, (
        f"Straight Drive bat angle must be within 10 deg of vertical, got {sd_imp['bat_angle']}"
    )
    assert abs(float(sd_imp["lead_stride_dir_deg"])) <= 10.0, (
        f"Straight Drive stride must be down the ground, got {sd_imp['lead_stride_dir_deg']}"
    )

    # 2. Cover Drive
    cd_imp = data["Cover Drive"]["phases"]["impact"]["keyframe_pose"]
    assert float(cd_imp["lead_stride_dir_deg"]) >= 20.0, (
        f"Cover Drive front foot must point to off-side (>=20 deg), got {cd_imp['lead_stride_dir_deg']}"
    )
    assert float(cd_imp["bat_angle"]) >= 15.0, (
        f"Cover Drive bat must angle toward off-side, got {cd_imp['bat_angle']}"
    )

    # 3. Pull Shot
    pull_imp = data["Pull Shot"]["phases"]["impact"]["keyframe_pose"]
    assert pull_imp["bat_plane"] == "horizontal", "Pull Shot bat plane must be horizontal"
    assert abs(float(pull_imp["bat_angle"])) >= 70.0, (
        f"Pull Shot bat must be horizontal (>=70 deg), got {pull_imp['bat_angle']}"
    )
    assert pull_imp["rear_foot_mode"] == "back-and-across", "Pull Shot rear foot must be back-and-across"

    # 4. Sweep Shot
    sweep_imp = data["Sweep"]["phases"]["impact"]["keyframe_pose"]
    assert sweep_imp["rear_foot_mode"] == "kneeling", "Sweep rear foot must be kneeling"
    assert sweep_imp["bat_plane"] == "horizontal", "Sweep bat plane must be horizontal"
    assert float(sweep_imp["bat_tip_y"]) <= 0.30, (
        f"Sweep bat tip must be low to ground (<=0.30m), got {sweep_imp['bat_tip_y']}"
    )
