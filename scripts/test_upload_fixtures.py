import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

FIXTURES = [
    ("Cover Drive", "backend/tests/fixtures/user_cover_drive.mp4"),
    ("Straight Drive", "backend/tests/fixtures/user_straight_drive.mp4"),
]

for name, path in FIXTURES:
    print(f"\n==========================================")
    print(f"Testing fixture: {name} ({path})")
    print(f"==========================================")
    if not os.path.exists(path):
        print(f"ERROR: Fixture file not found: {path}")
        continue

    start_t = time.time()
    with open(path, "rb") as f:
        response = client.post(
            "/api/video/upload",
            files={"file": (os.path.basename(path), f, "video/mp4")},
            data={"shot_type": "Auto-Detect"}
        )
    
    elapsed = time.time() - start_t
    print(f"Upload HTTP status: {response.status_code} in {elapsed:.2f}s")
    if response.status_code != 200:
        print("Upload failed:", response.text)
        continue
    
    data = response.json()
    session_id = data.get("session_id")
    print(f"Session ID: {session_id}")
    print(f"Initial upload response: {data}")

    # If processing happens in background task, poll status
    status = data.get("status")
    max_wait = 180
    waited = 0
    while status in ["queued", "processing", "uploaded"] and waited < max_wait:
        time.sleep(2)
        waited += 2
        st_res = client.get(f"/api/video/status/{session_id}")
        if st_res.status_code == 200:
            st_data = st_res.json()
            status = st_data.get("status")
            progress = st_data.get("progress")
            stage = st_data.get("current_stage")
            print(f"[{waited}s] status={status}, progress={progress}%, stage={stage}")
            if status in ["completed", "failed"]:
                break
        else:
            print(f"Status poll failed: {st_res.status_code} {st_res.text}")
            break

    # Get analysis result
    res = client.get(f"/api/analysis/{session_id}")
    print(f"Analysis HTTP status: {res.status_code}")
    if res.status_code == 200:
        res_data = res.json()
        shot_type = res_data.get("shot_type")
        confidence = res_data.get("confidence")
        top_candidates = res_data.get("top_candidates") or res_data.get("shot_classification", {}).get("top_candidates")
        striker = res_data.get("striker_track_id") or res_data.get("striker_details")
        frames_analyzed = res_data.get("total_frames") or res_data.get("frames_analyzed")
        processing_time = res_data.get("processing_time")
        
        pred_shot = res_data.get("predicted_shot_type") or res_data.get("shot_type")
        pred_conf = res_data.get("prediction_confidence") or res_data.get("confidence")
        print("\n--- RESULTS ---")
        print(f"Predicted Shot: {pred_shot}")
        print(f"Active Shot (used for technique): {shot_type}")
        print(f"Confidence: {pred_conf}")
        print(f"Top 3 Candidates: {top_candidates}")
        print(f"Striker: {striker}")
        print(f"Total Frames Analyzed: {frames_analyzed}")
    else:
        print(f"Analysis fetch error: {res.text}")
