from fastapi import APIRouter, HTTPException
from backend.app.schemas.evaluation import ModelEvaluationReport
from backend.app.services.evaluation_service import evaluation_service

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

@router.get("/report", response_model=ModelEvaluationReport)
def get_model_evaluation_report():
    report = evaluation_service.get_evaluation_report()
    if not report:
        raise HTTPException(
            status_code=404,
            detail="Evaluation report not found. Run model training script to generate experimental benchmarks."
        )
    return report
