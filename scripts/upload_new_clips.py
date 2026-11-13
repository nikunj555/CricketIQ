import os
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

CLIPS_DIR = Path("storage/sample_videos")
new_clips = [
    "Recording_2026-11-12_114751.mp4",
    "Recording_2026-11-12_114916.mp4",
    "Recording_2026-11-12_115126.mp4",
    "Recording_2026-11-12_115241.mp4",
    "Recording_2026-11-12_115353.mp4",
    "Recording_2026-11-12_115621.mp4",
    "Recording_2026-11-12_115712.mp4",
    "Recording_2026-11-12_115857.mp4",
    "Recording_2026-11-12_115951.mp4",
    "Recording_2026-11-12_120108.mp4",
    "Recording_2026-11-12_120159.mp4"
]

print("=" * 70)
print(f"Ingesting & Analyzing {len(new_clips)} New User Video Clips into CricketIQ")
print("=" * 70)

results = []

for idx, name in enumerate(new_clips, 1):
    clip_path = CLIPS_DIR / name
    if not clip_path.exists():
        print(f"[{idx}/{len(new_clips)}] Missing {name}")
        continue
        
    print(f"\n[{idx}/{len(new_clips)}] Processing {name}...")
    start_time = time.time()
    
    with open(clip_path, "rb") as f:
        res = client.post(
            "/api/video/upload",
            files={"file": (name, f, "video/mp4")},
            data={"shot_type": "Auto-Detect", "handedness": "Right", "camera_angle": "Side View"}
        )
    
    if res.status_code != 200:
        print(f"  FAILED upload for {name}: HTTP {res.status_code} - {res.text}")
        results.append({"name": name, "status": "upload_failed", "error": res.text})
        continue
    
    data = res.json()
    session_id = data.get("session_id")
    print(f"  Session Created: {session_id}")
    
    # Wait for processing to complete
    max_wait = 180
    elapsed = 0
    final_status = None
    while elapsed < max_wait:
        time.sleep(2)
        elapsed += 2
        st_res = client.get(f"/api/video/status/{session_id}")
        if st_res.status_code == 200:
            st = st_res.json()
            final_status = st.get("status")
            progress = st.get("progress", 0)
            step = st.get("current_step", "")
            if final_status == "completed":
                print(f"  [{elapsed}s] Completed: 100%")
                break
            elif final_status == "failed":
                print(f"  [{elapsed}s] FAILED processing: {st.get('error')}")
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
        annotated_path = an.get("annotated_video_path")
        top_cands = an.get("shot_classification", {}).get("top_candidates", [])
        top3_str = ", ".join([f"{c.get('shot_name')} ({c.get('confidence_pct')}%)" for c in top_cands[:3]])
        
        duration = time.time() - start_time
        conf_str = f"{conf*100:.0f}%" if isinstance(conf, (int, float)) else str(conf)
        score_str = f"{score:.1f}/100" if isinstance(score, (int, float)) else "N/A"
        
        print(f"  SUCCESS in {duration:.1f}s:")
        print(f"    Predicted Shot: {pred_shot} (Confidence: {conf_str})")
        print(f"    Top 3 Candidates: {top3_str}")
        print(f"    Technique Score: {score_str} | Frames: {frames}")
        print(f"    Annotated Video: {annotated_path}")
        
        results.append({
            "name": name,
            "session_id": session_id,
            "status": "completed",
            "shot": pred_shot,
            "confidence": conf_str,
            "score": score_str,
            "frames": frames,
            "annotated_path": annotated_path,
            "duration": f"{duration:.1f}s"
        })
    else:
        results.append({
            "name": name,
            "session_id": session_id,
            "status": final_status or "analysis_fetch_failed",
            "error": f"HTTP {an_res.status_code}"
        })

print("\n" + "=" * 70)
print("BATCH PROCESSING COMPLETE - SUMMARY TABLE:")
print("=" * 70)
for r in results:
    if r["status"] == "completed":
        print(f"{r['name']} -> {r['shot']} ({r['confidence']}) | Score: {r['score']} | Session: {r['session_id']}")
    else:
        print(f"{r['name']} -> FAILED: {r.get('error', r['status'])} | Session: {r.get('session_id')}")
print("=" * 70)
