import torch
from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.services.pose_service import pose_service
from backend.app.services.phase_service import phase_service

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "models": {
            "pose_estimator": {
                "name": "MediaPipe Pose Landmarker Full",
                "loaded": pose_service.landmarker is not None,
                "asset_path": str(settings.MODEL_ASSET_PATH)
            },
            "phase_classifier": {
                "name": "BiLSTM Temporal Action Phase Classifier",
                "loaded": phase_service.model is not None,
                "asset_path": str(settings.PHASE_MODEL_PATH)
            }
        }
    }
