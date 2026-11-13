import time
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from starlette.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

print("=== 1. HEALTH ROUTE VERIFICATION ===")
health_res = client.get("/api/health")
print(f"Status Code: {health_res.status_code}")
print("Response JSON:")
print(json.dumps(health_res.json(), indent=2))

print("\n=== 2. FIXTURE UPLOAD: user_cover_drive.mp4 ===")
with open("backend/tests/fixtures/user_cover_drive.mp4", "rb") as f:
    upload_res1 = client.post(
        "/api/video/upload",
        files={"file": ("user_cover_drive.mp4", f, "video/mp4")},
        data={"shot_type": "Cover Drive"}
    )
print(f"Upload Status Code: {upload_res1.status_code}")
data1 = upload_res1.json()
print("Upload Response:", json.dumps(data1, indent=2))
sid1 = data1["session_id"]

for _ in range(60):
    st = client.get(f"/api/video/status/{sid1}").json()
    if st["status"] in ("completed", "failed"):
        print(f"Session {sid1} result -> Status: {st['status']}, Progress: {st['progress']}%, Step: {st['current_step']}")
        break
    time.sleep(0.5)

analysis1 = client.get(f"/api/analysis/{sid1}").json()
print(f"Analysis {sid1}: Shot = {analysis1.get('shot_type')}, Score = {analysis1.get('overall_technique_score')}/100, Conf = {analysis1.get('shot_confidence', {}).get('confidence')}%, Annotated Video = {analysis1.get('annotated_video_url')}")

print("\n=== 3. FIXTURE UPLOAD: user_straight_drive.mp4 ===")
with open("backend/tests/fixtures/user_straight_drive.mp4", "rb") as f:
    upload_res2 = client.post(
        "/api/video/upload",
        files={"file": ("user_straight_drive.mp4", f, "video/mp4")},
        data={"shot_type": "Straight Drive"}
    )
print(f"Upload Status Code: {upload_res2.status_code}")
data2 = upload_res2.json()
print("Upload Response:", json.dumps(data2, indent=2))
sid2 = data2["session_id"]

for _ in range(60):
    st = client.get(f"/api/video/status/{sid2}").json()
    if st["status"] in ("completed", "failed"):
        print(f"Session {sid2} result -> Status: {st['status']}, Progress: {st['progress']}%, Step: {st['current_step']}")
        break
    time.sleep(0.5)

analysis2 = client.get(f"/api/analysis/{sid2}").json()
print(f"Analysis {sid2}: Shot = {analysis2.get('shot_type')}, Score = {analysis2.get('overall_technique_score')}/100, Conf = {analysis2.get('shot_confidence', {}).get('confidence')}%, Annotated Video = {analysis2.get('annotated_video_url')}")
