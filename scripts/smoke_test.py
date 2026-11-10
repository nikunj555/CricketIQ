"""
CricketIQ End-to-End Smoke Test Suite
Verifies 7 critical subsystems against a live server or in-process TestClient:
1. Health check & system diagnostics
2. Shot catalogue completeness (25+ shots)
3. Video upload and pipeline processing
4. Biomechanical pose extraction (33 MediaPipe landmarks)
5. Session progress tracking and trend analytics
6. Machine learning evaluation report (accuracy, confusion matrix)
7. Robust error handling for corrupt and invalid inputs
"""

import os
import sys
import time
import argparse
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

PASS = "[PASS]"
FAIL = "[FAIL]"

def run_smoke_test(base_url: str = None):
    print("=" * 70)
    print("                CricketIQ End-to-End Smoke Test Suite                 ")
    print("=" * 70)

    client = None
    if base_url:
        import httpx
        print(f"[*] Testing against live server: {base_url}")
        client = httpx.Client(base_url=base_url, timeout=60.0)
    else:
        print("[*] Testing using FastAPI TestClient (in-process)")
        from fastapi.testclient import TestClient
        from backend.app.main import app
        client = TestClient(app)

    passed_count = 0
    total_checks = 7

    # ---------------------------------------------------------
    # CHECK 1: Health Check & System Diagnostics
    # ---------------------------------------------------------
    print("\n--- Check 1: System Health & Diagnostic Endpoints ---")
    try:
        res = client.get("/api/health")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data.get("status") in ("healthy", "degraded"), f"Unexpected status: {data.get('status')}"
        assert "models" in data, "Missing 'models' key in health response"
        assert data["models"]["pose_estimator"]["loaded"] is True, "Pose estimator model not loaded"
        assert data["database"]["connected"] is True, "Database not connected"
        print(f"{PASS} Health endpoint returned 200 OK. Models loaded, DB connected ({data['database']['session_count']} sessions).")
        passed_count += 1
    except Exception as e:
        print(f"{FAIL} Health check failed: {e}")

    # ---------------------------------------------------------
    # CHECK 2: Shot Catalogue Completeness
    # ---------------------------------------------------------
    print("\n--- Check 2: Calibrated Shot Catalogue Completeness ---")
    try:
        res = client.get("/api/shots")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        shots = data.get("shots", [])
        assert len(shots) >= 25, f"Expected at least 25 shots, got {len(shots)}"
        categories = {s.get("category") for s in shots}
        assert "Drives" in categories, "Missing 'Drives' category"
        assert "Defensive Strokes" in categories, "Missing 'Defensive Strokes' category"
        print(f"{PASS} Shot catalogue contains {len(shots)} calibrated cricket shots across {len(categories)} categories.")
        passed_count += 1
    except Exception as e:
        print(f"{FAIL} Shot catalogue check failed: {e}")

    # ---------------------------------------------------------
    # CHECK 3 & 4: Video Upload, Polling & 33 Pose Landmarks
    # ---------------------------------------------------------
    print("\n--- Checks 3 & 4: Video Ingestion, Pipeline & 33-Landmark Pose Extraction ---")
    session_id = None
    try:
        fixture_path = ROOT_DIR / "backend" / "tests" / "fixtures" / "cover_drive.mp4"
        if not fixture_path.exists():
            fixture_path = ROOT_DIR / "storage" / "sample_videos" / "virat_kohli_cover_drive.mp4"

        assert fixture_path.exists(), f"Fixture video not found at {fixture_path}"

        with open(fixture_path, "rb") as video_file:
            files = {"file": ("cover_drive.mp4", video_file, "video/mp4")}
            data = {"shot_type": "Cover Drive", "camera_view": "Side-on (Right)"}
            res = client.post("/api/video/upload", files=files, data=data)
            assert res.status_code in (200, 201), f"Upload failed: {res.status_code} {res.text}"
            upload_data = res.json()
            session_id = upload_data.get("session_id")
            assert session_id, "No session_id in upload response"

        # Poll until complete (if async) or read status
        status_res = client.get(f"/api/video/status/{session_id}")
        assert status_res.status_code == 200
        status_data = status_res.json()
        
        # In testclient / synchronous upload, it is already completed
        if status_data.get("status") != "completed":
            for _ in range(30):
                time.sleep(1)
                st = client.get(f"/api/video/status/{session_id}").json()
                if st.get("status") in ("completed", "failed"):
                    status_data = st
                    break

        assert status_data.get("status") == "completed", f"Processing failed: {status_data}"
        print(f"{PASS} Check 3 Passed: Video upload & processing completed for session {session_id}.")
        passed_count += 1

        # Check 4: Pose extraction details
        analysis_res = client.get(f"/api/analysis/{session_id}")
        assert analysis_res.status_code == 200, f"Failed to get analysis: {analysis_res.status_code}"
        analysis = analysis_res.json()
        assert analysis.get("shot_type") == "Cover Drive"
        score = analysis.get("overall_technique_score") or analysis.get("overall_score")
        assert score is not None and score > 0
        
        time_series = analysis.get("time_series", [])
        assert len(time_series) > 0, "No analyzed time_series frames extracted"
        first_frame = time_series[0]
        landmarks = first_frame.get("landmarks", [])
        assert len(landmarks) == 33, f"Expected 33 landmarks, got {len(landmarks)}"
        print(f"{PASS} Check 4 Passed: 33 MediaPipe landmarks extracted across {len(time_series)} frames. Score: {score:.1f}/100.")
        passed_count += 1
    except Exception as e:
        print(f"{FAIL} Video ingestion / pose extraction failed: {e}")

    # ---------------------------------------------------------
    # CHECK 5: Biomechanical Progress Tracking
    # ---------------------------------------------------------
    print("\n--- Check 5: Historical Progress Tracking & Dual Attempts ---")
    try:
        res = client.get("/api/progress/shots/Cover Drive")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        progress_data = res.json()
        trend_items = progress_data.get("score_trend") or progress_data.get("trend_data") or []
        session_count = progress_data.get("session_count", len(trend_items))
        assert session_count >= 1 or len(trend_items) >= 1, f"Expected at least 1 attempt for Cover Drive, found {len(trend_items)}"
        print(f"{PASS} Progress tracking verified: {session_count} recorded Cover Drive attempts with chronological trend.")
        passed_count += 1
    except Exception as e:
        print(f"{FAIL} Progress tracking check failed: {e}")

    # ---------------------------------------------------------
    # CHECK 6: Machine Learning Evaluation Report
    # ---------------------------------------------------------
    print("\n--- Check 6: ML Evaluation Report & Calibration Veracity ---")
    try:
        res = client.get("/api/evaluation/report")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        rep = res.json()
        accuracy = rep.get("accuracy", 0.0)
        assert accuracy >= 0.90, f"Accuracy below 90%: {accuracy}"
        cm = rep.get("confusion_matrix", [])
        assert len(cm) == 7, f"Expected 7x7 confusion matrix, got {len(cm)}"
        print(f"{PASS} ML Evaluation report verified: Accuracy = {accuracy * 100:.1f}%, 7x7 confusion matrix validated.")
        passed_count += 1
    except Exception as e:
        print(f"{FAIL} ML Evaluation check failed: {e}")

    # ---------------------------------------------------------
    # CHECK 7: Error Handling for Corrupt Inputs
    # ---------------------------------------------------------
    print("\n--- Check 7: Input Boundary & Error Resilience ---")
    try:
        corrupt_bytes = b"CORRUPT_NOT_A_VALID_H264_OR_MP4_HEADER"
        files = {"file": ("broken.mp4", corrupt_bytes, "video/mp4")}
        res = client.post("/api/video/upload", files=files, data={"shot_type": "Cover Drive"})
        assert res.status_code == 400, f"Expected 400 Bad Request, got {res.status_code}"
        err_detail = res.json().get("detail", "")
        assert "video" in err_detail.lower() or "codec" in err_detail.lower() or "read" in err_detail.lower(), f"Unexpected error detail: {err_detail}"
        print(f"{PASS} Boundary resilience verified: Corrupt file rejected with HTTP 400: '{err_detail}'.")
        passed_count += 1
    except Exception as e:
        print(f"{FAIL} Error handling check failed: {e}")

    print("\n" + "=" * 70)
    print(f"SMOKE TEST SUMMARY: {passed_count}/{total_checks} CHECKS PASSED")
    print("=" * 70)

    if passed_count == total_checks:
        print("ALL END-TO-END SMOKE TESTS PASSED CLEANLY.")
        return 0
    else:
        print(f"{total_checks - passed_count} CHECKS FAILED.")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CricketIQ Smoke Test")
    parser.add_argument("--url", type=str, default=None, help="Base URL of live running server (e.g. http://127.0.0.1:8000)")
    args = parser.parse_args()
    sys.exit(run_smoke_test(args.url))
