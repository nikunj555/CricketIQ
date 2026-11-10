import os
from pathlib import Path

# Prevent WinError 1450 memory paging exhaustion on Windows
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR.parent

# Load local environment overrides if .env exists
try:
    from dotenv import load_dotenv
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

class Settings:
    ROOT_DIR: Path = ROOT_DIR
    BASE_DIR: Path = BASE_DIR
    PROJECT_NAME: str = "CricketIQ — Explainable AI Cricket Batting Technique Analyzer"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    
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
    
    # Feature flags & validation gates
    ENABLE_EXPERIMENTAL_BAT_BALL: bool = os.getenv("ENABLE_EXPERIMENTAL_BAT_BALL", "false").lower() == "true"
    ENABLE_HAND_LANDMARKER: bool = os.getenv("ENABLE_HAND_LANDMARKER", "false").lower() == "true"
    MIN_CLIPS_FOR_SUPPORTED_SHOT: int = int(os.getenv("MIN_CLIPS_FOR_SUPPORTED_SHOT", "8"))
    MIN_BATTERS_FOR_SUPPORTED_SHOT: int = int(os.getenv("MIN_BATTERS_FOR_SUPPORTED_SHOT", "2"))
    LABELED_FIXTURES_DIR: Path = BASE_DIR / "tests" / "fixtures" / "labeled"
    
    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "150"))
    ALLOWED_EXTENSIONS: set = {".mp4", ".mov", ".avi", ".webm", ".mkv", ".m4v"}
    MAX_FRAMES_TO_PROCESS: int = int(os.getenv("MAX_FRAMES_TO_PROCESS", "1800"))
    MAX_VIDEO_DURATION_SEC: float = float(os.getenv("MAX_VIDEO_DURATION_SEC", "60.0"))
    DEFAULT_SAMPLE_RATE: int = 1       # 1 = every frame
    
    # CORS
    CORS_ORIGINS: list = [
        origin.strip() for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,*"
        ).split(",") if origin.strip()
    ]

settings = Settings()

# Ensure storage directories exist
os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
os.makedirs(settings.ANNOTATED_DIR, exist_ok=True)
os.makedirs(settings.THUMBNAILS_DIR, exist_ok=True)
