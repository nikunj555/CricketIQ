import sys
import shutil
import sqlite3
from pathlib import Path
from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.services.pose_service import pose_service
from backend.app.services.phase_service import phase_service
from backend.app.services.hand_service import hand_service
from backend.app.repositories.session_repository import session_repo

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
def health_check():
    # Lazy/optional torch import
    device = "cpu"
    torch_available = False
    try:
        import torch
        torch_available = True
        device = "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        pass

    # Database diagnostics: connected & writable
    db_connected = False
    db_writable = False
    session_count = 0
    try:
        session_count = len(session_repo.list_sessions(limit=1000))
        db_connected = True
    except sqlite3.Error:
        db_connected = False

    try:
        with sqlite3.connect(settings.DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA quick_check")
            cursor.execute("BEGIN IMMEDIATE")
            conn.rollback()
            db_writable = True
    except sqlite3.Error:
        db_writable = False

    # FFmpeg diagnostics: check system PATH and bundled imageio-ffmpeg binary
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        try:
            import imageio_ffmpeg
            candidate = imageio_ffmpeg.get_ffmpeg_exe()
            if candidate and Path(candidate).exists():
                ffmpeg_path = candidate
        except (ImportError, OSError):
            ffmpeg_path = None
    ffmpeg_available = ffmpeg_path is not None

    # Storage diagnostics
    free_mb = 0.0
    try:
        usage = shutil.disk_usage(settings.STORAGE_DIR)
        free_mb = round(usage.free / (1024 * 1024), 2)
    except OSError:
        pass

    # Calibrated shot catalogue count
    calibrated_shot_count = 25
    try:
        from backend.app.data.shot_catalogue import SHOT_CATALOGUE
        calibrated_shot_count = len(SHOT_CATALOGUE)
    except ImportError:
        pass

    pose_loaded = pose_service.landmarker is not None
    phase_loaded = phase_service.model is not None
    hand_loaded = hand_service.landmarker is not None

    # Check overall system health
    issues = []
    if not pose_loaded:
        issues.append(f"MediaPipe Pose Landmarker is not loaded ({getattr(pose_service, 'init_error', 'initialization failed')}).")
    if not phase_loaded:
        issues.append("BiLSTM Temporal Action Phase model not loaded (falling back to kinematic rule-based phase detector).")
    if not hand_loaded:
        issues.append("MediaPipe Hand Landmarker model is not loaded.")
    if not ffmpeg_available:
        issues.append("FFmpeg executable not found (required for browser-compatible video transcoding).")
    if not db_connected:
        issues.append("SQLite database connection failed.")
    elif not db_writable:
        issues.append("SQLite database is read-only or locked.")

    status = "healthy" if len(issues) == 0 else "degraded"

    return {
        "status": status,
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "python_version": sys.version.split()[0],
        "device": device,
        "torch_available": torch_available,
        "ffmpeg": {
            "available": ffmpeg_available,
            "path": ffmpeg_path,
        },
        "database": {
            "connected": db_connected,
            "writable": db_writable,
            "path": str(settings.DB_PATH),
            "session_count": session_count,
        },
        "storage": {
            "base_dir": str(settings.STORAGE_DIR),
            "free_space_mb": free_mb,
            "uploads_exists": settings.UPLOADS_DIR.exists(),
            "annotated_exists": settings.ANNOTATED_DIR.exists(),
            "thumbnails_exists": settings.THUMBNAILS_DIR.exists(),
        },
        "calibrated_shots_count": calibrated_shot_count,
        "issues": issues,
        "models": {
            "pose_estimator": {
                "name": "MediaPipe Pose Landmarker Full",
                "loaded": pose_loaded,
                "asset_path": str(settings.MODEL_ASSET_PATH),
                "asset_exists": settings.MODEL_ASSET_PATH.exists(),
                "error": getattr(pose_service, "init_error", None),
            },
            "phase_classifier": {
                "name": "BiLSTM Temporal Action Phase Classifier",
                "loaded": phase_loaded,
                "asset_path": str(settings.PHASE_MODEL_PATH),
                "asset_exists": settings.PHASE_MODEL_PATH.exists(),
            },
            "hand_landmarker": {
                "name": "MediaPipe Hand Landmarker",
                "loaded": hand_loaded,
                "asset_path": str(settings.HAND_MODEL_PATH),
                "asset_exists": settings.HAND_MODEL_PATH.exists(),
            }
        }
    }
