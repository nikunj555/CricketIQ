import sys
import shutil
import sqlite3
from pathlib import Path
from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.services.pose_service import pose_service
from backend.app.services.phase_service import phase_service
from backend.app.services.hand_service import hand_service
from backend.app.services.detector_service import detector_service
from backend.app.repositories.session_repository import session_repo

router = APIRouter(prefix="/health", tags=["Health"])

@router.api_route("", methods=["GET", "HEAD"])
@router.api_route("/", methods=["GET", "HEAD"])
def health_check():
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
        with sqlite3.connect(settings.DB_PATH, timeout=2.0) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA quick_check(1)")
            db_writable = True
    except sqlite3.Error:
        db_writable = False

    # FFmpeg diagnostics
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

    # Model states
    pose_loaded = pose_service.landmarker is not None
    pose_loading = getattr(pose_service, "is_loading", False)
    pose_error = getattr(pose_service, "init_error", None)

    hand_loaded = hand_service.landmarker is not None
    hand_loading = getattr(hand_service, "is_loading", False)
    hand_error = getattr(hand_service, "init_error", None)

    phase_loaded = phase_service.model is not None
    phase_error = None if phase_loaded else "BiLSTM model not loaded (using kinematic fallback)"

    # Status evaluation
    is_warming_up = pose_loading or hand_loading
    
    issues = []
    if is_warming_up:
        issues.append("AI models are warming up in background.")
    if not pose_loaded and not pose_loading:
        issues.append(f"MediaPipe Pose Landmarker is not loaded ({pose_error or 'initialization failed'}).")
    if not phase_loaded:
        issues.append("BiLSTM Temporal Action Phase model not loaded (falling back to kinematic rule-based phase detector).")
    if not hand_loaded and not hand_loading and settings.ENABLE_HAND_LANDMARKER:
        issues.append(f"MediaPipe Hand Landmarker is not loaded ({hand_error or 'initialization failed'}).")
    if not ffmpeg_available:
        issues.append("FFmpeg executable not found (required for browser-compatible video transcoding).")
    if not db_connected:
        issues.append("SQLite database connection failed.")
    elif not db_writable:
        issues.append("SQLite database is read-only or locked.")

    # ready condition: pose loaded, phase loaded or rule fallback ready, ffmpeg ready, db working
    ready = pose_loaded and ffmpeg_available and db_connected and db_writable

    if is_warming_up:
        status = "warming_up"
    elif ready and len(issues) == 0:
        status = "healthy"
    elif ready:
        status = "degraded"
    else:
        status = "unhealthy"

    pose_model_info = {
        "name": "MediaPipe Pose Landmarker Full",
        "loaded": pose_loaded,
        "loading": pose_loading,
        "asset_path": str(settings.MODEL_ASSET_PATH),
        "asset_exists": settings.MODEL_ASSET_PATH.exists(),
        "error": pose_error,
    }

    hand_model_info = {
        "name": "MediaPipe Hand Landmarker",
        "loaded": hand_loaded,
        "loading": hand_loading,
        "asset_path": str(settings.HAND_MODEL_PATH),
        "asset_exists": settings.HAND_MODEL_PATH.exists(),
        "error": hand_error,
    }

    phase_model_info = {
        "name": "BiLSTM Batting Phase Classifier (NumPy)",
        "loaded": phase_loaded,
        "asset_path": str(getattr(phase_service, "npz_path", settings.PHASE_MODEL_PATH)),
        "asset_exists": getattr(phase_service, "npz_path", settings.PHASE_MODEL_PATH).exists(),
        "error": phase_error,
    }

    ffmpeg_info = {
        "available": ffmpeg_available,
        "path": ffmpeg_path,
        "error": None if ffmpeg_available else "FFmpeg binary not found",
    }

    detector_info = detector_service.get_health_status()

    return {
        "status": status,
        "ready": ready,
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "python_version": sys.version.split()[0],
        "models": {
            "pose": pose_model_info,
            "hand": hand_model_info,
            "phase": phase_model_info,
            "ffmpeg": ffmpeg_info,
            "detector": detector_info,
            # Backward compatibility aliases
            "pose_estimator": pose_model_info,
            "hand_landmarker": hand_model_info,
            "phase_classifier": phase_model_info,
        },
        "detector": detector_info,
        "ffmpeg": ffmpeg_info,
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
        "issues": issues,
    }
