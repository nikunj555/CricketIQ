import cv2
import numpy as np
import math
from pathlib import Path
from backend.app.core.config import settings
from backend.app.repositories.session_repository import session_repo
from backend.app.services.video_service import video_service

def generate_cricket_clip(output_path: Path, num_frames: int = 60, fps: float = 30.0):
    """
    Renders an optical synthetic cricket batting clip with realistic human proportions
    that MediaPipe Pose can track.
    """
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    # Center coordinates
    cx, cy = 320, 240

    for i in range(num_frames):
        frame = np.full((height, width, 3), (30, 25, 20), dtype=np.uint8)
        
        # Draw cricket pitch ground
        cv2.rectangle(frame, (0, 380), (width, height), (35, 75, 45), -1)
        cv2.line(frame, (0, 380), (width, 380), (200, 200, 200), 2)
        # Crease line
        cv2.line(frame, (220, 380), (220, 480), (240, 240, 240), 3)

        t = i / max(1, num_frames - 1)
        
        # Kinematics of front foot drive
        head_x = int(cx - 30 * np.sin(np.pi * t))
        head_y = int(140 + 20 * np.sin(np.pi * t))
        
        torso_base_x = cx
        torso_base_y = 260
        
        # Shoulders
        sh_x, sh_y = head_x, head_y + 40
        # Hips
        hip_x, hip_y = torso_base_x, torso_base_y
        
        # Lead leg (front stride)
        lead_foot_x = int(cx - 90 * np.sin(np.pi * t * 0.9))
        lead_knee_x = int((hip_x + lead_foot_x) / 2 - 15)
        lead_knee_y = int(320 + 20 * np.sin(np.pi * t))
        
        # Rear leg
        rear_foot_x = cx + 70
        rear_knee_x = cx + 40
        rear_knee_y = 325

        # Colors
        skin = (180, 205, 235)
        whites = (230, 230, 230)
        pads = (245, 245, 245)
        bat_wood = (40, 110, 180)

        # Draw Head
        cv2.circle(frame, (head_x, head_y), 22, skin, -1)
        # Helmet
        cv2.ellipse(frame, (head_x, head_y - 4), (23, 18), 0, 180, 360, (120, 40, 20), -1)

        # Torso (Cricket jersey)
        cv2.line(frame, (sh_x, sh_y), (hip_x, hip_y), whites, 26)

        # Legs (White trousers + pads)
        # Rear leg
        cv2.line(frame, (hip_x + 10, hip_y), (rear_knee_x, rear_knee_y), pads, 16)
        cv2.line(frame, (rear_knee_x, rear_knee_y), (rear_foot_x, 380), pads, 14)
        
        # Lead leg
        cv2.line(frame, (hip_x - 10, hip_y), (lead_knee_x, lead_knee_y), pads, 18)
        cv2.line(frame, (lead_knee_x, lead_knee_y), (lead_foot_x, 380), pads, 16)

        # Bat swing
        bat_angle = -1.2 + 2.4 * t
        bat_tip_x = int(sh_x + 85 * np.cos(bat_angle))
        bat_tip_y = int(sh_y + 85 * np.sin(bat_angle))
        
        # Arms
        cv2.line(frame, (sh_x, sh_y), (sh_x - 20, sh_y + 40), whites, 10)
        cv2.line(frame, (sh_x - 20, sh_y + 40), (int((sh_x + bat_tip_x)/2), int((sh_y + bat_tip_y)/2)), skin, 8)

        # Bat blade
        cv2.line(frame, (sh_x - 15, sh_y + 35), (bat_tip_x, bat_tip_y), bat_wood, 10)

        out.write(frame)

    out.release()

    # Transcode to standard browser-compatible H.264
    try:
        import imageio_ffmpeg, subprocess
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        temp_out = output_path.with_name(f"temp_h264_{output_path.name}")
        cmd = [
            exe, "-y",
            "-i", str(output_path),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(temp_out)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and temp_out.exists():
            temp_out.replace(output_path)
    except (subprocess.SubprocessError, OSError, FileNotFoundError) as e:
        print(f"H.264 transcode notice: {e}")

def seed_demo_sessions():
    existing = session_repo.list_sessions(limit=5)
    if existing:
        print("Database already has sessions. Skipping demo seeding.")
        return

    sample_video_path = settings.UPLOADS_DIR / "sample_cover_drive.mp4"
    if not sample_video_path.exists():
        print("Generating realistic demo batting clip...")
        generate_cricket_clip(sample_video_path, num_frames=60, fps=30.0)

    demo_session_id = "demo_cd1"
    print(f"Creating seed session '{demo_session_id}'...")
    session_repo.create_session(
        session_id=demo_session_id,
        video_filename="sample_cover_drive.mp4",
        original_path=str(sample_video_path),
        shot_type="Cover Drive",
        handedness="Right",
        camera_angle="Side View"
    )

    print("Running video processing pipeline on demo session...")
    video_service.process_video_session(demo_session_id)
    print("Demo session seeded successfully.")

if __name__ == "__main__":
    seed_demo_sessions()
