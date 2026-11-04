import pytest
import numpy as np
import cv2
import base64
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.live_coach_service import live_coach_service

client = TestClient(app)

def make_dummy_frame_b64(width=320, height=240):
    img = np.zeros((height, width, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode('utf-8')

def test_process_live_frame_no_player():
    b64 = make_dummy_frame_b64()
    resp = client.post("/api/live/process-frame", json={
        "image_base64": b64,
        "timestamp_ms": 100.0,
        "session_id": "test_live_session_1",
        "handedness": "Right",
        "shot_hint": "Cover Drive"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "waiting_for_player"
    assert data["presence"]["detected"] is False
    assert data["latency_ms"] >= 0.0

def test_manual_trigger_flow():
    b64 = make_dummy_frame_b64()
    
    # 1. Manual start
    resp_start = client.post("/api/live/process-frame", json={
        "image_base64": b64,
        "timestamp_ms": 200.0,
        "session_id": "test_live_manual",
        "manual_trigger": "start"
    })
    assert resp_start.status_code == 200
    assert resp_start.json()["state"] == "shot_in_progress"

    # 2. Manual finish
    resp_finish = client.post("/api/live/process-frame", json={
        "image_base64": b64,
        "timestamp_ms": 1200.0,
        "session_id": "test_live_manual",
        "manual_trigger": "finish"
    })
    assert resp_finish.status_code == 200

def test_analyze_attempt_endpoint():
    dummy_frames = [
        {
            "frame_index": i,
            "timestamp_sec": round(i * 0.05, 2),
            "pose_detected": True,
            "confidence": 0.95,
            "lead_knee_angle": 130.0 - 15.0 * np.sin(np.pi * (i / 20.0)),
            "rear_knee_angle": 160.0,
            "torso_inclination": 22.0,
            "head_displacement": 0.20,
            "stance_width_norm": 1.45,
            "phase": "Impact / Contact Window" if i == 12 else "Downswing / Execution"
        }
        for i in range(25)
    ]

    payload = {
        "session_id": "test_live_attempt_session",
        "attempt_index": 1,
        "shot_type": "Cover Drive",
        "handedness": "Right",
        "camera_angle": "Side View",
        "frames": dummy_frames
    }

    resp = client.post("/api/live/analyze-attempt", json=payload)
    assert resp.status_code == 200
    feedback = resp.json()
    assert feedback["shot_type"] == "Cover Drive"
    assert "observation" in feedback["main_observation"].lower() or "lead knee" in feedback["main_observation"].lower() or "balanced" in feedback["main_observation"].lower()
    assert feedback["impact_lead_knee"] is not None
    assert feedback["confidence_score"] > 0.8
    assert feedback["processing_latency_ms"] >= 0.0

    # Test retrieval of session attempts
    attempts_resp = client.get("/api/live/session/test_live_attempt_session/attempts")
    assert attempts_resp.status_code == 200
    attempts_list = attempts_resp.json()
    assert len(attempts_list) >= 1
