import json
from pathlib import Path
from typing import Optional, Dict, Any
from backend.app.schemas.evaluation import ModelEvaluationReport

class EvaluationService:
    def __init__(self, report_path: Optional[Path] = None):
        self.report_path = Path(report_path or "backend/app/data/evaluation_data/evaluation_report.json")

    def get_evaluation_report(self) -> Optional[ModelEvaluationReport]:
        if not self.report_path.exists():
            return None
        try:
            with open(self.report_path, "r") as f:
                data = json.load(f)
            return ModelEvaluationReport(**data)
        except Exception as e:
            return None

evaluation_service = EvaluationService()
