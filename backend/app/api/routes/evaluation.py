from fastapi import APIRouter
from typing import Dict, Any
from backend.app.core.config import settings
from backend.app.services.evaluation_service import evaluation_service

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

@router.get("/report")
def get_model_evaluation_report() -> Dict[str, Any]:
    labeled_dir = settings.LABELED_FIXTURES_DIR
    clip_count = 0
    if labeled_dir.exists():
        clip_count = len(list(labeled_dir.glob("*/*.mp4")))

    # Minimum threshold required before claiming empirical cross-validation accuracy
    if clip_count < settings.MIN_CLIPS_FOR_SUPPORTED_SHOT:
        return {
            "has_empirical_data": False,
            "labeled_clips_count": clip_count,
            "min_required_per_shot": settings.MIN_CLIPS_FOR_SUPPORTED_SHOT,
            "message": f"Classifier evaluation requires at least {settings.MIN_CLIPS_FOR_SUPPORTED_SHOT} labelled clips per shot. Current labelled clips: {clip_count}. Run scripts/evaluate_classifier.py once data is added.",
            "report": None
        }

    report = evaluation_service.get_evaluation_report()
    if not report:
        return {
            "has_empirical_data": False,
            "labeled_clips_count": clip_count,
            "min_required_per_shot": settings.MIN_CLIPS_FOR_SUPPORTED_SHOT,
            "message": f"Classifier evaluation requires running scripts/evaluate_classifier.py. Current labelled clips: {clip_count}.",
            "report": None
        }

    data = report.model_dump() if hasattr(report, "model_dump") else report.dict()
    data["has_empirical_data"] = True
    data["benchmark_type"] = "synthetic_benchmark"
    data["benchmark_label"] = "Synthetic Benchmark (Calibrated Kinematic Sequences)"
    data["labeled_clips_count"] = clip_count
    data["min_required_per_shot"] = settings.MIN_CLIPS_FOR_SUPPORTED_SHOT
    return data
