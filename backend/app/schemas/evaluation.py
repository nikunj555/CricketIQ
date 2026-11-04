from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ClassPerformance(BaseModel):
    class_name: str
    precision: float
    recall: float
    f1_score: float
    support: int

class ModelEvaluationReport(BaseModel):
    model_name: str
    architecture: str
    dataset_name: str
    split_strategy: str
    total_test_sequences: int
    total_test_frames: int
    accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    weighted_f1: float
    per_class_metrics: List[ClassPerformance]
    confusion_matrix: List[List[int]]
    classes: List[str]
    training_loss_history: List[float]
    val_loss_history: List[float]
    baseline_comparison: Dict[str, Any]
    feature_importance: Dict[str, float]
    inference_latency_ms: float
    evaluated_at: str
    limitations: List[str]
