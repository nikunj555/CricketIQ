import re
from backend.app.utils.update_catalogue_videos import SHOT_VIDEO_MAP

def update_file(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    for s_id, (v_name, t_name) in SHOT_VIDEO_MAP.items():
        if "reference_catalogue" in path:
            pattern = rf'("shot_id":\s*"{s_id}",.*?"video_url":\s*")[^"]*(".*?"thumbnail_url":\s*")[^"]*(")'
            content = re.sub(pattern, rf'\g<1>/api/video/original/{v_name}\g<2>/api/video/thumbnail/{t_name}\g<3>', content, flags=re.DOTALL)
        else: # shot_catalogue
            pattern = rf'("id":\s*"{s_id}",.*?"reference_video_url":\s*")[^"]*(".*?"reference_thumbnail_url":\s*")[^"]*(")'
            content = re.sub(pattern, rf'\g<1>/api/video/original/{v_name}\g<2>/api/video/thumbnail/{t_name}\g<3>', content, flags=re.DOTALL)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated {path}")

if __name__ == "__main__":
    update_file('e:/CricketIQ/backend/app/data/reference_catalogue.py')
    update_file('e:/CricketIQ/backend/app/data/shot_catalogue.py')
    
    # Also re-sync the sqlite database reference_videos table
    from backend.app.repositories.session_repository import session_repo
    from backend.app.data.reference_catalogue import AUTHENTIC_REFERENCE_REGISTRY
    for ref in AUTHENTIC_REFERENCE_REGISTRY:
        s_id = ref["shot_id"]
        if s_id in SHOT_VIDEO_MAP:
            v_name, t_name = SHOT_VIDEO_MAP[s_id]
            ref["video_url"] = f"/api/video/original/{v_name}"
            ref["thumbnail_url"] = f"/api/video/thumbnail/{t_name}"
        session_repo.save_reference(ref)
    print("Synchronized SQLite reference_videos table with 25 distinct reference videos!")

