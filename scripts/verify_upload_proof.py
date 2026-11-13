import sys
import time
import httpx
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000/api"

def test_file_upload(file_path: Path, shot_type: str = "Auto-Detect"):
    print(f"\n--- Testing upload for: {file_path.name} ({file_path.stat().st_size / 1024:.1f} KB) ---")
    start_t0 = time.time()
    
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f.read(), "video/mp4")}
        data = {
            "shot_type": shot_type,
            "handedness": "Right",
            "camera_angle": "Side View"
        }
        with httpx.Client(timeout=60.0) as client:
            res = client.post(f"{BASE_URL}/video/upload", files=files, data=data)
    
    upload_duration = time.time() - start_t0
    print(f"POST /api/video/upload status: {res.status_code} in {upload_duration:.2f}s")
    if res.status_code != 200:
        print("Upload Error:", res.text)
        return False
    
    res_data = res.json()
    session_id = res_data["session_id"]
    print(f"Session ID: {session_id} | Message: {res_data.get('message')}")
    
    # Poll status
    poll_start = time.time()
    last_step = ""
    with httpx.Client(timeout=10.0) as client:
        while True:
            status_res = client.get(f"{BASE_URL}/video/status/{session_id}")
            assert status_res.status_code == 200, f"Status check failed: {status_res.text}"
            status_data = status_res.json()
            current_step = status_data.get("current_step", "")
            progress = status_data.get("progress", 0.0)
            status = status_data.get("status", "")
            
            if current_step != last_step or status in ("completed", "failed"):
                print(f"  [{progress:5.1f}%] {status.upper()}: {current_step}")
                last_step = current_step
                
            if status == "completed":
                print(f"  Success! Total background analysis time: {time.time() - poll_start:.2f}s")
                result = status_data.get("result")
                if result:
                    print(f"  Detected Shot: {result.get('shot_type')} (Confidence: {result.get('prediction_confidence', 0.0):.2f})")
                    print(f"  Overall Score: {result.get('overall_technique_score')}")
                    print(f"  Phases Detected: {len(result.get('phases', []))}")
                    print(f"  Analyzed Frames: {result.get('analyzed_frames')}")
                else:
                    sess_res = client.get(f"{BASE_URL}/sessions/{session_id}")
                    print("  Session record fetched:", sess_res.json().get("shot_type"))
                return True
            elif status == "failed":
                print(f"  Analysis FAILED: {status_data.get('error')}")
                return False
                
            time.sleep(0.5)

if __name__ == "__main__":
    success_1 = test_file_upload(Path("backend/tests/fixtures/user_cover_drive.mp4"), "Cover Drive")
    success_2 = test_file_upload(Path("backend/tests/fixtures/user_straight_drive.mp4"), "Straight Drive")
    
    # Test longer recording clip
    user_clips = list(Path("C:/Users/Nikunj katta/.gemini/antigravity/brain/a3eae03c-b07a-4063-86e2-41c2d15368c1/.user_uploaded").glob("*.mp4"))
    success_3 = True
    if user_clips:
        long_clip = user_clips[0]
        success_3 = test_file_upload(long_clip, "Auto-Detect")
        
    print("\n===============================")
    print(f"user_cover_drive: {'PASS' if success_1 else 'FAIL'}")
    print(f"user_straight_drive: {'PASS' if success_2 else 'FAIL'}")
    print(f"long_clip: {'PASS' if success_3 else 'FAIL'}")
    print("===============================")
    
    if not (success_1 and success_2 and success_3):
        sys.exit(1)
