import pytest
import numpy as np
from backend.app.services.hand_service import hand_service

def test_hand_service_initialization():
    assert hand_service is not None

def test_detect_hands_blank_frame():
    # Blank frame should safely return without crashing
    blank = np.zeros((240, 320, 3), dtype=np.uint8)
    res = hand_service.detect_hands(blank)
    assert isinstance(res, dict)
    assert res["hand_tracking_detected"] is False
    assert res["num_hands"] == 0
    assert "reliability_note" in res

def test_detect_hands_none_frame():
    res = hand_service.detect_hands(None)
    assert res["hand_tracking_detected"] is False

def test_draw_hands_safety():
    blank = np.zeros((240, 320, 3), dtype=np.uint8)
    empty_data = {"hand_tracking_detected": False}
    out = hand_service.draw_hands(blank, empty_data)
    assert out.shape == blank.shape
