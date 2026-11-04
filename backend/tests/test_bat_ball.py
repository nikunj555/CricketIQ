import pytest
import numpy as np
from backend.app.services.bat_ball_service import bat_ball_service

def test_bat_ball_service_init():
    assert bat_ball_service is not None

def test_detect_blank_frame():
    blank = np.zeros((240, 320, 3), dtype=np.uint8)
    res = bat_ball_service.detect_bat_and_ball(blank, wrist_pts=None)
    assert res["bat_detected"] is False
    assert res["ball_detected"] is False
    assert res["bat_angle_deg"] is None
    assert res["bat_speed_norm"] is None

def test_detect_with_synthetic_bat_line():
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    # Draw clear bat line from (150, 150) to (180, 260)
    import cv2
    cv2.line(img, (150, 150), (180, 260), (220, 180, 140), 10)
    wrist_pts = [(150 / 300, 150 / 300)]
    res = bat_ball_service.detect_bat_and_ball(img, wrist_pts=wrist_pts)
    assert res["bat_detected"] is True
    assert res["bat_angle_deg"] is not None
    assert res["bat_tip_y"] is not None

def test_draw_bat_and_ball():
    blank = np.zeros((200, 200, 3), dtype=np.uint8)
    dummy_data = {
        "bat_detected": True,
        "bat_handle_x": 0.4,
        "bat_handle_y": 0.4,
        "bat_tip_x": 0.5,
        "bat_tip_y": 0.8,
        "bat_angle_deg": 35.0,
        "ball_detected": True,
        "ball_x": 0.6,
        "ball_y": 0.5
    }
    out = bat_ball_service.draw_bat_and_ball(blank, dummy_data)
    assert out.shape == blank.shape
