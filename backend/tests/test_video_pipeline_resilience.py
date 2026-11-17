import pytest
import shutil
import subprocess
import imageio_ffmpeg
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.video_service import video_service
from backend.app.services.pose_service import pose_service

client = TestClient(app)


def test_rotated_clip_read_upright(tmp_path):
    """
    Test that phone rotation metadata (e.g. 90-degree gyro tag) is detected
    and normalized by ffmpeg with rotation applied.
    """
    ffmpeg_exe = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
    assert ffmpeg_exe, "ffmpeg must be available for video normalization tests"

    raw_path = tmp_path / "raw_base.mp4"
    rot_path = tmp_path / "rotated_video.mp4"

    # Create short 1-sec test video
    subprocess.run([
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1",
        "-c:v", "libx264",
        str(raw_path)
    ], check=True, capture_output=True)

    # Apply 90-degree display rotation tag
    subprocess.run([
        ffmpeg_exe, "-y",
        "-display_rotation:v", "90",
        "-i", str(raw_path),
        "-c", "copy",
        str(rot_path)
    ], check=True, capture_output=True)

    norm_path, meta = video_service.normalize_video_input(rot_path)
    assert meta["rotation"] == 90
    assert meta["rotation_applied"] is True
    assert norm_path.exists()
    assert norm_path.stat().st_size > 500


def test_hevc_mov_converted_and_analysed(tmp_path):
    """
    Test that unsupported/container formats (.mov, HEVC) are converted
    to standard constant-frame-rate H.264 MP4 and can be decoded and analyzed.
    """
    ffmpeg_exe = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
    assert ffmpeg_exe, "ffmpeg must be available for video normalization tests"

    # 1. Test .mov container
    mov_path = tmp_path / "recording.mov"
    subprocess.run([
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "color=c=green:s=320x240:d=1",
        "-c:v", "libx264",
        str(mov_path)
    ], check=True, capture_output=True)

    norm_mov, meta_mov = video_service.normalize_video_input(mov_path)
    assert norm_mov.suffix.lower() == ".mp4"
    assert norm_mov.exists()

    # 2. Test HEVC codec
    hevc_path = tmp_path / "hevc_clip.mp4"
    res = subprocess.run([
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "color=c=red:s=320x240:d=1",
        "-c:v", "libx265",
        str(hevc_path)
    ], capture_output=True)

    if res.returncode == 0:
        norm_hevc, meta_hevc = video_service.normalize_video_input(hevc_path)
        assert meta_hevc["codec_converted"] is True
        assert norm_hevc.exists()

    # Verify debug_video_pipeline successfully reads normalized output
    debug_res = video_service.debug_video_pipeline(norm_mov)
    assert debug_res["frames_read"] > 0
    assert debug_res["failing_stage"] != "video_decode"


def test_small_subject_crop_path_passes():
    """
    Test that distant batter footage runs through the crop path
    and achieves >= 30% pose detection rate without 0.0% quality gate rejection.
    """
    failing_clip = Path("storage/uploads/0f564027_Recording_2026-11-04_023233.mp4")
    if failing_clip.exists():
        res = video_service.debug_video_pipeline(failing_clip)
        assert res["frames_read"] > 0
        assert res["detection_rate"] >= 0.30
        assert res["failing_stage"] == "none"
        # Confirm crop path was utilized
        assert any(src == "crop" for src in res["pose_source_per_frame"].values())
    else:
        # Fallback to fixture
        fixture_clip = Path("backend/tests/fixtures/user_cover_drive.mp4")
        res = video_service.debug_video_pipeline(fixture_clip)
        assert res["frames_read"] > 0
        assert res["detection_rate"] >= 0.30
        assert res["failing_stage"] == "none"


def test_missing_landmarker_returns_503_not_zero_percent():
    """
    Test that when pose landmarker failed to initialize (e.g. libGLESv2 missing),
    the server returns 503 from /api/health/details and /api/video/upload,
    and NEVER scores the video as 0.0% user quality gate rejection.
    """
    pose_service.ensure_loaded()
    orig_landmarker = pose_service.landmarker
    orig_loading = pose_service.is_loading
    orig_error = pose_service.init_error

    try:
        pose_service.landmarker = None
        pose_service.is_loading = False
        pose_service.init_error = "OSError: libGLESv2.so.2: cannot open shared object file: No such file or directory"

        # 1. /api/health/details must return 503 Service Unavailable
        res_health = client.get("/api/health/details")
        assert res_health.status_code == 503
        data_health = res_health.json()
        assert data_health["ready"] is False
        assert "libGLESv2" in str(data_health["issues"])

        # 2. /api/video/upload must return 503 Service Unavailable
        files = {"file": ("test.mp4", b"\x00" * 1024, "video/mp4")}
        res_upload = client.post("/api/video/upload", files=files)
        assert res_upload.status_code == 503
        assert "Pose estimation AI engine is unavailable" in res_upload.json()["detail"]
        assert "0.0%" not in res_upload.text

        # 3. debug_video_pipeline must report failing_stage == "model_not_loaded"
        debug_res = video_service.debug_video_pipeline(Path("backend/tests/fixtures/user_cover_drive.mp4"))
        assert debug_res["pose_landmarker_loaded"] is False
        assert debug_res["failing_stage"] == "model_not_loaded"
        assert "libGLESv2" in str(debug_res["pose_landmarker_error"])

    finally:
        pose_service.landmarker = orig_landmarker
        pose_service.is_loading = orig_loading
        pose_service.init_error = orig_error
