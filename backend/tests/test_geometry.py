import pytest
import math
from backend.app.services.geometry_service import geometry_service

def test_calculate_angle_2d_orthogonal():
    # 90 degree angle at origin: (0, 1) -> (0, 0) -> (1, 0)
    p1 = (0.0, 1.0)
    p2 = (0.0, 0.0)
    p3 = (1.0, 0.0)
    angle = geometry_service.calculate_angle_2d(p1, p2, p3)
    assert angle is not None
    assert math.isclose(angle, 90.0, abs_tol=1e-4)

def test_calculate_angle_2d_collinear():
    # 180 degree straight line (fully extended knee): (-1, 0) -> (0, 0) -> (1, 0)
    p1 = (-1.0, 0.0)
    p2 = (0.0, 0.0)
    p3 = (1.0, 0.0)
    angle = geometry_service.calculate_angle_2d(p1, p2, p3)
    assert angle is not None
    assert math.isclose(angle, 180.0, abs_tol=1e-4)

def test_calculate_angle_2d_zero_length():
    # Degenerate zero-length vector should return None safely without crashing
    p1 = (0.0, 0.0)
    p2 = (0.0, 0.0)
    p3 = (1.0, 1.0)
    angle = geometry_service.calculate_angle_2d(p1, p2, p3)
    assert angle is None

def test_calculate_angle_2d_none_handling():
    assert geometry_service.calculate_angle_2d(None, (0, 0), (1, 1)) is None

def test_calculate_inclination_from_vertical():
    # In image plane: (0, 0) is top-left, y increases downward.
    # Base at (0.5, 0.8), Top at (0.5, 0.2) -> Perfectly vertical upright
    p_base = (0.5, 0.8)
    p_top = (0.5, 0.2)
    incl = geometry_service.calculate_inclination_from_vertical(p_base, p_top)
    assert incl is not None
    assert math.isclose(incl, 0.0, abs_tol=1e-4)

    # 45 degree tilt forward (top at 0.8, 0.5)
    p_top_lean = (0.8, 0.5)
    # dx = 0.3, dy = -0.3 -> angle = 45 degrees
    incl_lean = geometry_service.calculate_inclination_from_vertical(p_base, p_top_lean)
    assert incl_lean is not None
    assert math.isclose(incl_lean, 45.0, abs_tol=1e-4)

def test_extract_frame_metrics_missing():
    # Empty or insufficient landmarks returns graceful fallback
    metrics = geometry_service.extract_frame_metrics([], handedness="Right")
    assert metrics["pose_detected"] is False
    assert metrics["confidence"] == 0.0
    assert metrics["lead_knee_angle"] is None
    assert metrics["lead_elbow_angle"] is None
    assert metrics["wrist_separation_norm"] is None

def test_calculate_extension_ratio():
    # Straight arm: shoulder=(0, 0), elbow=(0, 0.5), wrist=(0, 1.0) -> extension = 1.0
    ext_straight = geometry_service.calculate_extension_ratio((0, 0), (0, 0.5), (0, 1.0))
    assert ext_straight is not None
    assert math.isclose(ext_straight, 1.0, abs_tol=1e-3)

    # 90-degree bent arm: shoulder=(0, 0), elbow=(0, 1.0), wrist=(1.0, 1.0)
    # span = sqrt(2) ~= 1.414, arm_length = 1.0 + 1.0 = 2.0 -> ratio ~= 0.707
    ext_bent = geometry_service.calculate_extension_ratio((0, 0), (0, 1.0), (1.0, 1.0))
    assert ext_bent is not None
    assert math.isclose(ext_bent, math.sqrt(2) / 2.0, abs_tol=1e-3)

def test_extract_comprehensive_metrics():
    # Create synthetic 33-point pose
    landmarks = [{"x": 0.5, "y": 0.5, "visibility": 0.9} for _ in range(33)]
    # Shoulder midpoint
    landmarks[11] = {"x": 0.45, "y": 0.3, "visibility": 0.95} # Left shoulder
    landmarks[12] = {"x": 0.55, "y": 0.3, "visibility": 0.95} # Right shoulder
    # Elbows
    landmarks[13] = {"x": 0.40, "y": 0.45, "visibility": 0.95} # Left elbow
    landmarks[14] = {"x": 0.60, "y": 0.45, "visibility": 0.95} # Right elbow
    # Wrists close together in batting grip
    landmarks[15] = {"x": 0.48, "y": 0.55, "visibility": 0.95} # Left wrist
    landmarks[16] = {"x": 0.50, "y": 0.56, "visibility": 0.95} # Right wrist
    # Hips
    landmarks[23] = {"x": 0.46, "y": 0.6, "visibility": 0.95} # Left hip
    landmarks[24] = {"x": 0.54, "y": 0.6, "visibility": 0.95} # Right hip
    # Knees
    landmarks[25] = {"x": 0.40, "y": 0.75, "visibility": 0.95} # Left knee (lead for RH)
    landmarks[26] = {"x": 0.58, "y": 0.75, "visibility": 0.95} # Right knee
    # Ankles
    landmarks[27] = {"x": 0.38, "y": 0.9, "visibility": 0.95} # Left ankle
    landmarks[28] = {"x": 0.62, "y": 0.9, "visibility": 0.95} # Right ankle
    # Nose
    landmarks[0] = {"x": 0.48, "y": 0.2, "visibility": 0.95}

    metrics_rh = geometry_service.extract_frame_metrics(landmarks, handedness="Right")
    assert metrics_rh["pose_detected"] is True
    assert metrics_rh["lead_knee_angle"] is not None
    assert metrics_rh["lead_elbow_angle"] is not None
    assert metrics_rh["rear_elbow_angle"] is not None
    assert metrics_rh["wrist_separation_norm"] is not None
    assert metrics_rh["wrist_separation_norm"] < 0.2  # Wrists are closely paired
    assert metrics_rh["head_over_lead_knee_norm"] is not None
    assert metrics_rh["weight_distribution_proxy"] is not None
