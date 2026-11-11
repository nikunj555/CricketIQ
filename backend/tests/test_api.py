import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "CricketIQ" in data["project"]

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "models" in data
    assert data["models"]["pose_estimator"]["loaded"] is True
    assert data["models"]["phase_classifier"]["loaded"] is True

def test_list_references():
    response = client.get("/api/comparison/references")
    assert response.status_code == 200
    refs = response.json()
    assert len(refs) >= 4
    shot_types = [r["shot_type"] for r in refs]
    assert "Cover Drive" in shot_types
    assert "Pull Shot" in shot_types

def test_evaluation_report():
    response = client.get("/api/evaluation/report")
    assert response.status_code == 200
    rep = response.json()
    assert "has_empirical_data" in rep
    assert "min_required_per_shot" in rep
    if rep["has_empirical_data"]:
        assert "accuracy" in rep
        assert "macro_f1" in rep

def test_list_sessions():
    response = client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert "total_count" in data
