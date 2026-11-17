import sys
import os
import json
import uuid
import shutil
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.core.config import settings
from backend.app.repositories.session_repository import session_repo
from backend.app.services.video_service import video_service

def run_test(label: str, video_path: Path, selected_shot: str, handedness: str = "Right", camera_angle: str = "Side View"):
    print(f"\n==================================================")
    print(f"RUNNING {label}: Video={video_path.name}, Selected Shot='{selected_shot}'")
    print(f"==================================================")
    
    assert video_path.exists(), f"Video file not found: {video_path}"
    
    # Copy to a session file in storage/uploads to mimic real upload
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    upload_dest = settings.UPLOADS_DIR / f"{session_id}_{video_path.name}"
    shutil.copy(video_path, upload_dest)
    
    session_repo.create_session(
        session_id=session_id,
        video_filename=video_path.name,
        original_path=str(upload_dest),
        shot_type=selected_shot,
        handedness=handedness,
        camera_angle=camera_angle
    )
    
    print(f"Starting processing for session {session_id}...")
    video_service.process_video_session(session_id)
    
    sess = session_repo.get_session(session_id)
    assert sess is not None, "Session not found after processing"
    status = sess.get("status")
    print(f"Session Status: {status}, Progress: {sess.get('progress')}")
    if status == "failed":
        print(f"ERROR: {sess.get('error')}")
        return False, sess
    
    result_raw = sess.get("result_json")
    if not result_raw:
        print("ERROR: result_json is empty")
        return False, sess
        
    res = json.loads(result_raw)
    
    print("\n--- EXTRACTED RESULTS ---")
    print(f"Selected Shot (Technique Coach Target): {res.get('shot_type')}")
    print(f"Guidance Level: {res.get('guidance_level')}")
    print(f"Guidance Note: {res.get('guidance_note')}")
    print(f"How To Play Steps Count: {len(res.get('how_to_play', {}).get('phase_steps', []))}")
    print(f"How To Play Key Points: {len(res.get('how_to_play', {}).get('key_points', []))}")
    print(f"Shot Check Status: {res.get('shot_check_status')}")
    print(f"Shot Check Message: {res.get('shot_check_message')}")
    print(f"Predicted Shot Check: {res.get('predicted_shot_type')} (conf: {res.get('prediction_confidence'):.2f})")
    print(f"Shot Mismatch Warning: {res.get('shot_mismatch_warning')}")
    print(f"Overall Technique Score: {res.get('overall_score')}")
    print(f"Phase Scores: {res.get('phase_scores')}")
    
    key_faults = res.get("key_faults", [])
    print(f"Key Faults ({len(key_faults)}):")
    for idx, f in enumerate(key_faults[:3], 1):
        print(f"  {idx}. {f.get('fault')} (Severity: {f.get('severity')}) - {f.get('drill')}")
        
    top_fix = res.get("top_fix")
    if top_fix:
        print(f"Top Fix: {top_fix.get('title')}: {top_fix.get('description')}")
    else:
        print("Top Fix: None")
        
    # Invariants to verify
    assert res.get("shot_type") == selected_shot, f"Selected shot mismatch: expected {selected_shot}, got {res.get('shot_type')}"
    assert "how_to_play" in res and len(res["how_to_play"].get("phase_steps", [])) >= 5, "how_to_play steps missing"
    assert "guidance_level" in res, "guidance_level missing"
    assert "shot_check_status" in res, "shot_check_status missing"
    assert "phase_scores" in res, "phase_scores missing"
    
    return True, res

def main():
    runs = [
        ("Run 1", Path("backend/tests/fixtures/user_cover_drive.mp4"), "Cover Drive"),
        ("Run 2", Path("backend/tests/fixtures/user_straight_drive.mp4"), "Straight Drive"),
        ("Run 3", Path("storage/uploads/sample_flick_shot.mp4"), "Flick Shot"),
        ("Run 4", Path("storage/uploads/sample_flick_shot.mp4"), "Cover Drive"),
    ]
    
    all_ok = True
    summary_results = []
    for label, vpath, shot in runs:
        ok, res = run_test(label, vpath, shot)
        if not ok:
            all_ok = False
        summary_results.append((label, shot, res))
        
    print("\n==================================================")
    print(f"ALL 4 RUNS COMPLETED. All OK: {all_ok}")
    print("==================================================")

if __name__ == "__main__":
    main()
