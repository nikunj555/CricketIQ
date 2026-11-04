import os
from pathlib import Path

# Prevent WinError 1450 memory paging exhaustion on Windows
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR.parent

class Settings:
    PROJECT_NAME: str = "CricketIQ — Explainable AI Cricket Batting Technique Analyzer"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # Storage directories
    STORAGE_DIR: Path = ROOT_DIR / "storage"
    UPLOADS_DIR: Path = STORAGE_DIR / "uploads"
    ANNOTATED_DIR: Path = STORAGE_DIR / "annotated"
    THUMBNAILS_DIR: Path = STORAGE_DIR / "thumbnails"
    DB_PATH: Path = STORAGE_DIR / "cricketiq.db"
    
    # Model assets
    MODEL_ASSET_PATH: Path = BASE_DIR / "app" / "models" / "assets" / "pose_landmarker_full.task"
    HAND_MODEL_PATH: Path = BASE_DIR / "app" / "models" / "assets" / "hand_landmarker.task"
    PHASE_MODEL_PATH: Path = BASE_DIR / "app" / "models" / "assets" / "phase_bilstm.pt"
    
    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 150
    ALLOWED_EXTENSIONS: set = {".mp4", ".mov", ".avi", ".webm", ".mkv", ".m4v"}
    MAX_FRAMES_TO_PROCESS: int = 300  # Cap processing to ~10s @ 30fps for responsive performance
    DEFAULT_SAMPLE_RATE: int = 1       # 1 = every frame, 2 = every 2nd frame
    
    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ]

settings = Settings()

# Ensure storage directories exist
os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
os.makedirs(settings.ANNOTATED_DIR, exist_ok=True)
os.makedirs(settings.THUMBNAILS_DIR, exist_ok=True)
