import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from backend.app.schemas.evaluation import ModelEvaluationReport

logger = logging.getLogger(__name__)

class EvaluationService:
    def __init__(self, report_path: Optional[Path] = None):
        self.report_path = Path(report_path or "backend/app/data/evaluation_data/evaluation_report.json")

    def get_evaluation_report(self) -> Optional[ModelEvaluationReport]:
        if not self.report_path.exists():
            return None
        try:
            with open(self.report_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ModelEvaluationReport(**data)
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.exception(f"Failed to load evaluation report from {self.report_path}: {e}")
            return None

evaluation_service = EvaluationService()
