"""
CricketIQ — End-to-End Upload & Analysis Smoke Test
Tests uploading a video fixture, processing the video session,
and verifying that the result contains:
  - predicted shot
  - calibrated confidence
  - stroke phases
  - actionable coaching feedback & top mistakes
  - top 3 candidate shots
"""

import sys
import time
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure repo root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from backend.app.repositories.session_repository import session_repo
from backend.app.services.video_service import video_service


def run_smoke_test(fixture_path: Path):
    print(f"\n=======================================================")
    print(f"Running CricketIQ Smoke Test on: {fixture_path.name}")
    print(f"=======================================================")

    assert fixture_path.exists(), f"Fixture file not found: {fixture_path}"

    client = TestClient(app)

    # 1. Health check
    print("\n[Step 1] Checking backend health...")
    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200, f"Health check failed: {health_resp.text}"
    health_data = health_resp.json()
    print(f"  Backend Status: {health_data.get('status')}")
    print(f"  Pose Estimator Loaded: {health_data.get('models', {}).get('pose_estimator', {}).get('loaded')}")
    print(f"  Phase Classifier Loaded: {health_data.get('models', {}).get('phase_classifier', {}).get('loaded')}")

    # 2. Upload video
    print(f"\n[Step 2] Uploading {fixture_path.name} to /api/video/upload...")
    with open(fixture_path, "rb") as f:
        upload_resp = client.post(
            "/api/video/upload",
            files={"file": (fixture_path.name, f, "video/mp4")},
            data={
                "shot_type": "Cover Drive",
                "handedness": "Right",
                "camera_angle": "Side View"
            }
        )

    assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
    upload_data = upload_resp.json()
    session_id = upload_data["session_id"]
    print(f"  Upload Success! Session ID: {session_id}")

    # 3. Process video session
    print("\n[Step 3] Processing session end-to-end...")
    video_service.process_video_session(session_id)

    # 4. Fetch analysis result
    print("\n[Step 4] Fetching analysis result from /api/analysis/{session_id}...")
    analysis_resp = client.get(f"/api/analysis/{session_id}")
    assert analysis_resp.status_code == 200, f"Analysis retrieval failed: {analysis_resp.text}"
    result = analysis_resp.json()

    # 5. Verify core required fields
    print("\n[Step 5] Validating required response fields...")
    
    # Check shot & confidence
    shot_cls = result.get("shot_classification") or {}
    pred_shot = result.get("predicted_shot_type") or shot_cls.get("predicted_shot")
    conf_pct = result.get("prediction_confidence")
    if conf_pct is not None and conf_pct <= 1.0:
        conf_pct = int(round(conf_pct * 100))
    elif conf_pct is None:
        conf_pct = shot_cls.get("confidence_pct", 0)

    print(f"  Predicted Shot: {pred_shot}")
    print(f"  Confidence: {conf_pct}% ({shot_cls.get('confidence_level', 'N/A')})")
    assert pred_shot, "predicted_shot_type must not be empty"
    assert conf_pct is not None and conf_pct > 0, "confidence must be > 0"

    # Check top 3 candidates
    top3 = shot_cls.get("top_candidates") or []
    print(f"  Top Candidates: {[(c.get('shot_name'), c.get('confidence_pct')) for c in top3]}")
    assert len(top3) >= 1, "top_candidates must not be empty"

    # Check phases
    phases = result.get("phases") or []
    print(f"  Recognized Phases: {len(phases)} phases")
    for ph in phases:
        print(f"    - {ph.get('name')}: frames {ph.get('start_frame')}–{ph.get('end_frame')} ({ph.get('duration_sec', 0):.2f}s)")
    assert len(phases) > 0, "phases must contain recognized temporal stroke segments"

    # Check coaching feedback & top mistakes
    top_mistakes = result.get("top_mistakes") or []
    print(f"  Coaching Observations / Mistakes: {len(top_mistakes)} items")
    for idx, m in enumerate(top_mistakes[:3], 1):
        print(f"    {idx}. {m.get('title')}: observed {m.get('observed_value')} (ideal: {m.get('reference_benchmark')})")
        print(f"       Drill: {m.get('practical_drill')}")
    assert len(top_mistakes) > 0, "top_mistakes must contain actionable feedback"

    # Check overall technique score
    score = result.get("overall_technique_score")
    print(f"  Overall Technique Score: {score}/100")
    assert score is not None and 0.0 <= score <= 100.0, "overall_technique_score must be between 0 and 100"

    print("\n=======================================================")
    print(" SMOKE TEST PASSED: All required fields present and valid.")
    print("=======================================================\n")
    return True


if __name__ == "__main__":
    fixtures = [
        ROOT_DIR / "backend" / "tests" / "fixtures" / "user_cover_drive.mp4",
        ROOT_DIR / "backend" / "tests" / "fixtures" / "user_straight_drive.mp4"
    ]
    
    # Test first available fixture
    test_fixture = None
    for f in fixtures:
        if f.exists():
            test_fixture = f
            break
            
    if not test_fixture:
        print("ERROR: No test fixture found in backend/tests/fixtures/")
        sys.exit(1)

    try:
        run_smoke_test(test_fixture)
    except Exception as e:
        print(f"\nSMOKE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
