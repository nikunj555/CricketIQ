import os
import sys
import hashlib
import logging
import sqlite3
from pathlib import Path
from contextlib import asynccontextmanager

# Suppress harmless internal C++ logging from TFLite / MediaPipe
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("GLOG_minloglevel", "3")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from backend.app.core.config import settings
from backend.app.api.routes import health, video, analysis, comparison, sessions, evaluation, live, shots, reference, progress

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("cricketiq")

def _get_file_sha256(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()[:16]
    except OSError as hash_err:
        logger.warning(f"Could not calculate hash for {path}: {hash_err}")
        return "ERROR"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure storage subdirectories exist
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    settings.ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)
    settings.THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

    pose_hash = _get_file_sha256(settings.MODEL_ASSET_PATH)
    hand_hash = _get_file_sha256(settings.HAND_MODEL_PATH)
    phase_hash = _get_file_sha256(settings.PHASE_MODEL_PATH)
    
    # Database status
    db_status = "Connected" if settings.DB_PATH.exists() else "Initialized"
    session_count = 0
    try:
        from backend.app.repositories.session_repository import session_repo
        session_count = len(session_repo.list_sessions(limit=1000))
    except sqlite3.Error as db_err:
        logger.warning(f"Could not read session count on startup: {db_err}")

    frontend_dist = settings.BASE_DIR.parent / "frontend" / "dist"
    single_port_mode = "Single-Port SPA Mounted" if frontend_dist.exists() else "API Mode Only"

    banner = f"""
+========================================================================+
|                    CricketIQ Biomechanics Engine                       |
+========================================================================+
| Python Version       : {sys.version.split()[0]} ({sys.platform})
| API Prefix           : {settings.API_PREFIX}
| SQLite Database      : {db_status} ({settings.DB_PATH.name}) [{session_count} sessions]
| Pose Landmarker      : SHA256: {pose_hash}
| Hand Landmarker      : SHA256: {hand_hash}
| Phase BiLSTM         : SHA256: {phase_hash}
| Calibrated Shots     : 25 Master Reference Profiles
| Storage Base Dir     : {settings.STORAGE_DIR}
| Web Frontend         : {single_port_mode}
+========================================================================+
"""
    logger.info(banner)
    yield
    logger.info("CricketIQ Engine shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Explainable AI System for Cricket Batting Technique Assessment and Kinematic Video Analysis",
    lifespan=lifespan
)

# Gzip compression for large telemetry and landmark payloads
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(video.router, prefix=settings.API_PREFIX)
app.include_router(analysis.router, prefix=settings.API_PREFIX)
app.include_router(comparison.router, prefix=settings.API_PREFIX)
app.include_router(sessions.router, prefix=settings.API_PREFIX)
app.include_router(evaluation.router, prefix=settings.API_PREFIX)
app.include_router(live.router, prefix=settings.API_PREFIX)
app.include_router(shots.router, prefix=settings.API_PREFIX)
app.include_router(reference.router, prefix=settings.API_PREFIX)
app.include_router(progress.router, prefix=settings.API_PREFIX)

# Static media mounts for streaming
if settings.THUMBNAILS_DIR.exists():
    app.mount("/thumbnails", StaticFiles(directory=settings.THUMBNAILS_DIR), name="thumbnails")
if settings.STORAGE_DIR.exists():
    app.mount("/videos", StaticFiles(directory=settings.STORAGE_DIR), name="videos")

FRONTEND_DIST = settings.BASE_DIR.parent / "frontend" / "dist"

@app.get("/")
def root(request: Request):
    accept = request.headers.get("accept", "")
    # If client specifically requests HTML (e.g. browser navigation) and frontend is built, serve SPA
    if (FRONTEND_DIST / "index.html").exists() and "text/html" in accept and "application/json" not in accept:
        return FileResponse(FRONTEND_DIST / "index.html")
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "status": "operational"
    }

# SPA static asset mounting and client-side routing fallback
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Exclude reserved prefixes
        if (
            full_path.startswith("api")
            or full_path.startswith("docs")
            or full_path.startswith("redoc")
            or full_path.startswith("openapi.json")
            or full_path.startswith("thumbnails")
            or full_path.startswith("videos")
        ):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        target_file = FRONTEND_DIST / full_path
        if target_file.is_file():
            return FileResponse(target_file)
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse({"detail": "Not Found"}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
