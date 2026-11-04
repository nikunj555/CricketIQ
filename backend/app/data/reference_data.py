from typing import List, Dict, Any, Optional
from backend.app.data.reference_catalogue import (
    AUTHENTIC_REFERENCE_REGISTRY,
    generate_reference_kinematics,
    get_all_references,
    get_reference_for_shot,
    get_reference_by_id
)

# Maintain backward compatibility with existing imports
REFERENCE_SHOT_REGISTRY: List[Dict[str, Any]] = AUTHENTIC_REFERENCE_REGISTRY

def generate_synthetic_kinematic_sequence(
    shot_type: str,
    total_frames: int = 60,
    fps: float = 30.0
) -> Dict[str, Any]:
    return generate_reference_kinematics(shot_type, total_frames, fps)
