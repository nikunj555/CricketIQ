import sys
import shutil
import sqlite3
from pathlib import Path
from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.services.pose_service import pose_service
from backend.app.services.phase_service import phase_service
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

    # Database diagnostics
    db_ok = False
    session_count = 0
    try:
        session_count = len(session_repo.list_sessions(limit=1000))
        db_ok = True
    except Exception:
        pass

    # Storage diagnostics
    free_mb = 0.0
    try:
        usage = shutil.disk_usage(settings.STORAGE_DIR)
        free_mb = round(usage.free / (1024 * 1024), 2)
    except Exception:
        pass

    # Calibrated shot catalogue count
    calibrated_shot_count = 25
    try:
        from backend.app.data.shot_catalogue import SHOT_CATALOGUE
        calibrated_shot_count = len(SHOT_CATALOGUE)
    except Exception:
        pass

    return {
        "status": "healthy" if db_ok and pose_service.landmarker is not None else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "python_version": sys.version.split()[0],
        "device": device,
        "torch_available": torch_available,
        "database": {
            "connected": db_ok,
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
        "models": {
            "pose_estimator": {
                "name": "MediaPipe Pose Landmarker Full",
                "loaded": pose_service.landmarker is not None,
                "asset_path": str(settings.MODEL_ASSET_PATH),
                "asset_exists": settings.MODEL_ASSET_PATH.exists(),
                "error": getattr(pose_service, "init_error", None),
            },
            "phase_classifier": {
                "name": "BiLSTM Temporal Action Phase Classifier",
                "loaded": phase_service.model is not None,
                "asset_path": str(settings.PHASE_MODEL_PATH),
                "asset_exists": settings.PHASE_MODEL_PATH.exists(),
            },
            "hand_landmarker": {
                "name": "MediaPipe Hand Landmarker",
                "asset_path": str(settings.HAND_MODEL_PATH),
                "asset_exists": settings.HAND_MODEL_PATH.exists(),
            }
        }
    }
