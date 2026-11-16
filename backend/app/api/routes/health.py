import sys
import shutil
import sqlite3
import time
from pathlib import Path
from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.services.pose_service import pose_service
from backend.app.services.phase_service import phase_service
from backend.app.services.hand_service import hand_service
from backend.app.services.detector_service import detector_service
from backend.app.services.keepalive_service import keepalive_service

router = APIRouter(prefix="/health", tags=["Health"])


@router.api_route("", methods=["GET", "HEAD"])
@router.api_route("/", methods=["GET", "HEAD"])
def health_check():
    """Fast health check — no DB queries, no disk scans. Must respond in <50ms."""
    pose_loaded = pose_service.landmarker is not None
    pose_loading = getattr(pose_service, "is_loading", False)
    pose_error = getattr(pose_service, "init_error", None)

    hand_loaded = hand_service.landmarker is not None
    hand_loading = getattr(hand_service, "is_loading", False)

    phase_loaded = phase_service.model is not None

    is_warming_up = pose_loading or hand_loading

    # Check if an analysis job is currently running
    from backend.app.services.video_service import _processing_lock
    job_running = _processing_lock.locked()

    issues = []
    if is_warming_up:
        issues.append("AI models are warming up in background.")
    if not pose_loaded and not pose_loading:
        issues.append(f"MediaPipe Pose Landmarker not loaded ({pose_error or 'init failed'}).")
    if not phase_loaded:
        issues.append("Phase model not loaded (using kinematic fallback).")

    ready = pose_loaded

    if is_warming_up:
        status = "warming_up"
    elif ready and len(issues) == 0:
        status = "healthy"
    elif ready:
        status = "degraded"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "ready": ready,
        "job_running": job_running,
        "models": {
            "pose": {"loaded": pose_loaded, "loading": pose_loading, "error": pose_error},
            "pose_estimator": {"loaded": pose_loaded, "loading": pose_loading, "error": pose_error},
            "hand": {"loaded": hand_loaded, "loading": hand_loading},
            "hand_landmarker": {"loaded": hand_loaded, "loading": hand_loading},
            "phase": {"loaded": phase_loaded},
            "phase_classifier": {"loaded": phase_loaded},
        },
        "issues": issues,
    }


@router.api_route("/details", methods=["GET"])
def health_details():
    """Detailed diagnostics — DB queries, disk, memory. Not used for liveness checks."""
    # Database diagnostics
    db_connected = False
    db_writable = False
    session_count = 0
    try:
        from backend.app.repositories.session_repository import session_repo
        session_count = len(session_repo.list_sessions(limit=1000))
        db_connected = True
    except sqlite3.Error:
        db_connected = False

    try:
        with sqlite3.connect(settings.DB_PATH, timeout=2.0) as conn:
            conn.cursor().execute("PRAGMA quick_check(1)")
            db_writable = True
    except sqlite3.Error:
        db_writable = False

    # FFmpeg
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

    # Storage
    free_mb = 0.0
    try:
        usage = shutil.disk_usage(settings.STORAGE_DIR)
        free_mb = round(usage.free / (1024 * 1024), 2)
    except OSError:
        pass

    # Model states (full detail)
    pose_loaded = pose_service.landmarker is not None
    pose_loading = getattr(pose_service, "is_loading", False)
    pose_error = getattr(pose_service, "init_error", None)
    hand_loaded = hand_service.landmarker is not None
    hand_loading = getattr(hand_service, "is_loading", False)
    hand_error = getattr(hand_service, "init_error", None)
    phase_loaded = phase_service.model is not None
    phase_error = None if phase_loaded else "BiLSTM model not loaded (using kinematic fallback)"

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

    ready = pose_loaded and ffmpeg_available and db_connected and db_writable

    if is_warming_up:
        status = "warming_up"
    elif ready and len(issues) == 0:
        status = "healthy"
    elif ready:
        status = "degraded"
    else:
        status = "unhealthy"

    # Memory diagnostics
    memory_info = {}
    try:
        import psutil
        proc = psutil.Process()
        mem = proc.memory_info()
        memory_info = {
            "rss_mb": round(mem.rss / (1024 * 1024), 2),
            "percent": round(proc.memory_percent(), 2),
            "status": "healthy" if (mem.rss / (1024 * 1024)) < 400 else "warning"
        }
    except Exception:
        memory_info = {"status": "unavailable"}

    # Job status
    from backend.app.services.video_service import _processing_lock
    job_running = _processing_lock.locked()

    detector_info = detector_service.get_health_status()
    keepalive_info = keepalive_service.get_status()

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

    return {
        "status": status,
        "ready": ready,
        "job_running": job_running,
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "python_version": sys.version.split()[0],
        "models": {
            "pose": pose_model_info,
            "hand": hand_model_info,
            "phase": phase_model_info,
            "ffmpeg": ffmpeg_info,
            "detector": detector_info,
            "pose_estimator": pose_model_info,
            "hand_landmarker": hand_model_info,
            "phase_classifier": phase_model_info,
        },
        "detector": detector_info,
        "ffmpeg": ffmpeg_info,
        "memory": memory_info,
        "keepalive": keepalive_info,
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
