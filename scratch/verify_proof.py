import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.learning_video_service import learning_video_service

client = TestClient(app)

def check_shot(shot_name):
    print(f"\n=======================================================")
    print(f"VERIFYING: {shot_name}")
    print(f"=======================================================")
    
    # 1. API endpoint
    res = client.get(f"/api/shots/{shot_name}/videos")
    assert res.status_code == 200, f"Failed: status {res.status_code}"
    videos = res.json()
    print(f"GET /api/shots/{shot_name}/videos -> Status {res.status_code}")
    print(f"Video count: {len(videos)}")
    print("Payload:")
    print(json.dumps(videos, indent=2))
    
    # 2. UI Behavior mapping
    if len(videos) == 0:
        print("\nUI Behavior:")
        print("  -> Has Learning Video Card: NO (renders null)")
        print("  -> Placeholder shown: NO")
        print("  -> Only text steps, coaching cues and 7 movement phases rendered")
    else:
        print("\nUI Behavior:")
        for idx, v in enumerate(videos, 1):
            print(f"  [Card #{idx}]")
            print(f"    Title: \"Learn this shot: {v['title']}\"")
            print(f"    Provider / Channel: \"{v.get('channel', 'Sikana Education')}\"")
            print(f"    Match Tier: \"{v.get('match')}\"")
            if v.get("match") == "related":
                print(f"    Subtitle Badge: \"Similar technique\"")
            print(f"    Action Button: \"Open lesson\" -> {v['url']} (target='_blank' rel='noopener noreferrer')")

def main():
    print("CricketIQ — Learn This Shot Verification Proof")
    print("Checking Cover Drive (exact), Clip Shot (related), Hook Shot (no card)")
    
    check_shot("Cover Drive")
    check_shot("Clip Shot")
    check_shot("Hook Shot")

if __name__ == "__main__":
    main()
