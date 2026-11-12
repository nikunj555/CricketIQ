import uuid
import shutil
import base64
import cv2
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from backend.app.core.config import settings
from backend.app.schemas.analysis import VideoUploadResponse, VideoProcessingStatus, StrikerInspectionResponse, StrikerCandidate
from backend.app.repositories.session_repository import session_repo
from backend.app.services.video_service import video_service
from backend.app.services.pose_service import pose_service

router = APIRouter(prefix="/video", tags=["Video"])

@router.post("/inspect-strikers", response_model=StrikerInspectionResponse)
async def inspect_strikers_endpoint(
    file: UploadFile = File(...)
):
    """
    Fast inspection of video frame 0 to detect all person bounding boxes,
    measure initial wrist movement across the first frames, and suggest the default striker.
    Returns candidate boxes and a base64 JPEG thumbnail of frame 0.
    """
    temp_id = str(uuid.uuid4())[:8]
    temp_path = settings.UPLOADS_DIR / f"temp_inspect_{temp_id}_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        inspect_data = pose_service.inspect_strikers(temp_path, max_scan_frames=60)
        
        # Extract frame 0 image as base64 JPEG
        cap = cv2.VideoCapture(str(temp_path))
        ret, frame0 = cap.read()
        cap.release()
        frame0_raw_b64 = None
        frame0_b64 = None
        if ret and frame0 is not None:
            # Resize slightly if very high-res to keep response snappy
            h, w = frame0.shape[:2]
            if w > 1280:
                scale = 1280.0 / w
                frame0 = cv2.resize(frame0, (1280, int(h * scale)))
            success, enc = cv2.imencode(".jpg", frame0, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if success:
                raw_str = base64.b64encode(enc).decode('utf-8')
                frame0_raw_b64 = raw_str
                frame0_b64 = f"data:image/jpeg;base64,{raw_str}"

        candidates = [
            StrikerCandidate(
                track_id=c["track_id"],
                bbox=c["bbox"],
                is_default=c["is_default"],
                role=c["role"],
                wrist_motion_score=c["wrist_motion_score"],
                confidence=c.get("confidence"),
                evidence=c.get("evidence")
            )
            for c in inspect_data.get("candidates", [])
        ]

        needs_conf = inspect_data.get("needs_confirmation", False)
        conf_msg = "Could not tell who the striker is. Please select the batter" if needs_conf else None

        return StrikerInspectionResponse(
            candidates=candidates,
            default_track_id=inspect_data.get("default_track_id", 0),
            total_persons=inspect_data.get("total_persons", len(candidates)),
            frame_width=inspect_data.get("frame_width", 640),
            frame_height=inspect_data.get("frame_height", 480),
            frame0_thumbnail_base64=frame0_raw_b64,
            frame_0_data_url=frame0_b64,
            needs_confirmation=needs_conf,
            confirmation_message=conf_msg
        )
    finally:
        temp_path.unlink(missing_ok=True)

@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    shot_type: str = Form("Cover Drive"),
    handedness: str = Form("Right"),
    camera_angle: str = Form("Side View"),
    striker_track_id: Optional[int] = Form(None),
    striker_tap_coords: Optional[str] = Form(None)
):
    # Fail fast if server AI engine is not ready
    if pose_service.landmarker is None:
        raise HTTPException(
            status_code=503,
            detail=f"Pose estimation AI engine is unavailable on the server ({pose_service.init_error or 'PoseLandmarker not loaded'}). Ensure Docker runtime with OpenGL/libGLESv2 is deployed."
        )

    # Validate extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format '{file_ext}'. Allowed formats: {', '.join(sorted(settings.ALLOWED_EXTENSIONS))}"
        )

    session_id = str(uuid.uuid4())[:8]
    safe_filename = f"{session_id}_{file.filename.replace(' ', '_')}"
    saved_path = settings.UPLOADS_DIR / safe_filename

    # Stream write file to storage
    try:
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded video: {str(e)}")

    # Initial video validation check
    val = video_service.validate_video_file(saved_path)
    if not val["valid"]:
        saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=val["error"])

    # Register in repository
    session_repo.create_session(
        session_id=session_id,
        video_filename=file.filename,
        original_path=str(saved_path),
        shot_type=shot_type,
        handedness=handedness,
        camera_angle=camera_angle,
        striker_track_id=striker_track_id,
        striker_tap_coords=striker_tap_coords
    )

    # Queue background processing
    background_tasks.add_task(video_service.process_video_session, session_id)

    return VideoUploadResponse(
        session_id=session_id,
        filename=file.filename,
        shot_type=shot_type,
        handedness=handedness,
        camera_angle=camera_angle,
        striker_track_id=striker_track_id,
        message="Video uploaded successfully. Biomechanical analysis in progress.",
        video_url=f"/api/video/original/{safe_filename}"
    )

@router.get("/status/{session_id}", response_model=VideoProcessingStatus)
def get_processing_status(session_id: str):
    session = session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return VideoProcessingStatus(
        session_id=session_id,
        status=session["status"],
        progress=session["progress"],
        current_step=session["current_step"],
        error=session["error"]
    )

@router.post("/session/{session_id}/select-striker")
def select_striker_endpoint(
    session_id: str,
    track_id: int,
    background_tasks: BackgroundTasks
):
    """
    Overrides the striker track for an existing video session and triggers re-processing.
    """
    session = session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    session_repo.update_striker_track_id(session_id, track_id)
    background_tasks.add_task(video_service.process_video_session, session_id)
    return {
        "session_id": session_id,
        "striker_track_id": track_id,
        "message": f"Striker track locked to #{track_id}. Re-processing video session..."
    }

@router.get("/original/{filename}")
def get_original_video(filename: str):
    path = settings.UPLOADS_DIR / filename
    if not path.exists():
        matches = list(settings.UPLOADS_DIR.glob(f"*{filename}"))
        if matches:
            path = matches[0]
        elif filename.startswith("live_") or "live_practice" in filename:
            # Fallback to available sample video so player displays replay smoothly
            sample_candidates = list(settings.UPLOADS_DIR.glob("sample_*.mp4"))
            if sample_candidates:
                path = sample_candidates[0]
            else:
                raise HTTPException(status_code=404, detail="Original video not found.")
        else:
            raise HTTPException(status_code=404, detail="Original video not found.")
    return FileResponse(
        str(path),
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"}
    )

@router.get("/annotated/{filename}")
def get_annotated_video(filename: str):
    path = settings.ANNOTATED_DIR / filename
    if not path.exists():
        matches = list(settings.ANNOTATED_DIR.glob(f"*{filename}"))
        if matches:
            path = matches[0]
        else:
            raise HTTPException(status_code=404, detail="Annotated video not found.")
    return FileResponse(
        str(path),
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"}
    )

@router.get("/thumbnail/{filename}")
def get_thumbnail(filename: str):
    path = settings.THUMBNAILS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found.")
    return FileResponse(str(path), media_type="image/jpeg")
