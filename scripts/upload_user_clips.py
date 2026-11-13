import os
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.repositories.session_repository import session_repo

client = TestClient(app)

CLIPS_DIR = Path("storage/sample_videos")
clips = sorted(list(CLIPS_DIR.glob("Recording_*.mp4")))

print("=" * 70)
print(f"Ingesting & Analyzing {len(clips)} User Video Clips into CricketIQ")
print("=" * 70)

for idx, clip_path in enumerate(clips, 1):
    print(f"\n[{idx}/{len(clips)}] Processing {clip_path.name}...")
    start_time = time.time()
    
    with open(clip_path, "rb") as f:
        res = client.post(
            "/api/video/upload",
            files={"file": (clip_path.name, f, "video/mp4")},
            data={"shot_type": "Auto-Detect", "handedness": "Right", "camera_angle": "Side View"}
        )
    
    if res.status_code != 200:
        print(f"FAILED upload for {clip_path.name}: HTTP {res.status_code} - {res.text}")
        continue
    
    data = res.json()
    session_id = data.get("session_id")
    print(f"  Session Created: {session_id}")
    
    # Wait for processing to complete
    max_wait = 180
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(2)
        elapsed += 2
        st_res = client.get(f"/api/video/status/{session_id}")
        if st_res.status_code == 200:
            st = st_res.json()
            status = st.get("status")
            progress = st.get("progress", 0)
            step = st.get("current_step", "")
            print(f"  [{elapsed}s] Progress: {progress:.0f}% - {step}")
            if status == "completed":
                break
            elif status == "failed":
                print(f"  FAILED processing for {clip_path.name}: {st.get('error')}")
                break
        else:
            print(f"  Status query error: {st_res.status_code}")
            break
            
    # Fetch final analysis results
    an_res = client.get(f"/api/analysis/{session_id}")
    if an_res.status_code == 200:
        an = an_res.json()
        shot = an.get("shot_type")
        pred_shot = an.get("predicted_shot_type") or shot
        conf = an.get("prediction_confidence") or (an.get("shot_confidence", {}).get("calibrated_score", 0.0))
        score = an.get("overall_technique_score")
        frames = an.get("total_frames")
        top_cands = an.get("shot_classification", {}).get("top_candidates", [])
        top3_str = ", ".join([f"{c.get('shot_name')} ({c.get('confidence_pct')}%)" for c in top_cands[:3]])
        
        duration = time.time() - start_time
        print(f"  SUCCESS in {duration:.1f}s:")
        print(f"    Predicted Shot: {pred_shot} (Confidence: {conf*100:.0f}%)" if isinstance(conf, (int, float)) else f"    Predicted Shot: {pred_shot} (Confidence: {conf})")
        print(f"    Top 3 Candidates: {top3_str}")
        print(f"    Technique Score: {score}/100 | Frames Analyzed: {frames}")
        print(f"    Annotated Video: {an.get('annotated_video_path')}")
    else:
        print(f"  Could not retrieve analysis for {session_id}: HTTP {an_res.status_code}")

print("\n" + "=" * 70)
print("All clips processed and saved to CricketIQ session repository.")
print("=" * 70)
