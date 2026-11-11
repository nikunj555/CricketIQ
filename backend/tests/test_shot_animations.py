"""
Test suite validating shot animation data integrity:
- All 25 cricket shots are present
- Each shot has all 7 phases
- No two shots share identical impact keyframes
- Provenance is explicitly 'authored baseline (tunable)'
"""

import json
import re
from pathlib import Path

def test_all_25_shots_have_distinct_phases_and_correct_provenance():
    ts_file = Path("frontend/src/data/shotAnimations.ts")
    json_file = Path("frontend/src/data/shotAnimations.json")
    assert ts_file.exists(), "frontend/src/data/shotAnimations.ts does not exist"

    if json_file.exists():
        data = json.loads(json_file.read_text(encoding="utf-8"))
    else:
        content = ts_file.read_text(encoding="utf-8")
        m = re.search(r"export const SHOT_ANIMATIONS:\s*Record<string,\s*ShotAnimationDefinition>\s*=\s*(\{.*?\});\s*\n\s*export function", content, re.DOTALL)
        assert m is not None, "Failed to parse SHOT_ANIMATIONS from ts file"
        data = json.loads(m.group(1))
    assert len(data) == 25, f"Expected 25 shots, but found {len(data)}"

    required_phases = ["stance", "backlift", "stride", "downswing", "impact", "follow_through", "recovery"]
    seen_fingerprints = {}

    for shot_name, shot in data.items():
        assert shot["provenance"] == "authored baseline (tunable)", f"{shot_name} provenance must be 'authored baseline (tunable)'"
        assert "ballTrajectory" in shot, f"{shot_name} missing ballTrajectory"
        assert "swingPlane" in shot, f"{shot_name} missing swingPlane"
        assert len(shot["commonMistakes"]) >= 3, f"{shot_name} missing mistakes"
        assert len(shot["drills"]) >= 2, f"{shot_name} missing drills"

        for p in required_phases:
            assert p in shot["phases"], f"{shot_name} is missing phase {p}"
            phase = shot["phases"][p]
            assert "head" in phase
            assert "torso" in phase
            assert "leadLeg" in phase
            assert "rearLeg" in phase
            assert "leadArm" in phase
            assert "rearArm" in phase
            assert "bat" in phase
            assert len(phase["techniquePoints"]) > 0

        # Verify impact pose uniqueness across all 25 shots
        imp = shot["phases"]["impact"]
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

        assert fingerprint not in seen_fingerprints, f"Duplicate impact keyframe detected between '{shot_name}' and '{seen_fingerprints.get(fingerprint)}'"
        seen_fingerprints[fingerprint] = shot_name
