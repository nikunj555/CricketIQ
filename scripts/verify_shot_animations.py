"""
Verification script and test runner for shotAnimations.ts:
- Asserts that all 25 shots are present.
- Asserts that every shot has all 7 phases: stance, backlift, stride, downswing, impact, follow_through, recovery.
- Asserts that no two shots have identical impact keyframes.
- Asserts that provenance is explicitly marked 'authored baseline (tunable)'.
"""

import json
import re

ts_path = "frontend/src/data/shotAnimations.ts"
content = open(ts_path, "r", encoding="utf-8").read()

# Extract SHOT_ANIMATIONS JSON object
m = re.search(r"export const SHOT_ANIMATIONS:\s*Record<string,\s*ShotAnimationDefinition>\s*=\s*(\{.*?\});\s*\n\s*export function", content, re.DOTALL)
if not m:
    raise ValueError("Could not parse SHOT_ANIMATIONS from ts file")

data = json.loads(m.group(1))

print(f"Total shots parsed: {len(data)}")
assert len(data) == 25, f"Expected 25 shots, found {len(data)}"

phases = ["stance", "backlift", "stride", "downswing", "impact", "follow_through", "recovery"]

impact_poses = {}

for name, s in data.items():
    assert s["provenance"] == "authored baseline (tunable)", f"{name} provenance mismatch"
    assert "ballTrajectory" in s, f"{name} missing ballTrajectory"
    assert "swingPlane" in s, f"{name} missing swingPlane"
    assert len(s["commonMistakes"]) >= 3, f"{name} should have >= 3 mistakes"
    assert len(s["drills"]) >= 2, f"{name} should have >= 2 drills"

    for p in phases:
        assert p in s["phases"], f"{name} missing phase {p}"
        kf = s["phases"][p]
        assert "head" in kf, f"{name} phase {p} missing head"
        assert "torso" in kf, f"{name} phase {p} missing torso"
        assert "leadLeg" in kf, f"{name} phase {p} missing leadLeg"
        assert "rearLeg" in kf, f"{name} phase {p} missing rearLeg"
        assert "leadArm" in kf, f"{name} phase {p} missing leadArm"
        assert "rearArm" in kf, f"{name} phase {p} missing rearArm"
        assert "bat" in kf, f"{name} phase {p} missing bat"
        assert len(kf["techniquePoints"]) > 0, f"{name} phase {p} missing technique points"

    # Compare impact pose uniqueness
    imp = s["phases"]["impact"]
    # Form a fingerprint tuple
    fingerprint = (
        imp["torso"]["leanDeg"],
        imp["torso"]["sideLeanDeg"],
        imp["torso"]["rotationDeg"],
        imp["leadLeg"]["kneeAngleDeg"],
        imp["rearLeg"]["kneeAngleDeg"],
        imp["leadArm"]["elbowAngleDeg"],
        imp["bat"]["angleDeg"],
        imp["bat"]["swingPlane"],
        tuple(imp["bat"]["tipPos"]),
        tuple(imp["leadLeg"]["footPos"])
    )

    if fingerprint in impact_poses:
        other_name = impact_poses[fingerprint]
        raise AssertionError(f"Impact pose collision! Shot '{name}' is identical to '{other_name}'")
    impact_poses[fingerprint] = name

print("SUCCESS: All 25 shots verified! Distinct 3D keyframes, valid phases, and correct provenance.")
