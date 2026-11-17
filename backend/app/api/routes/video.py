import uuid
import shutil
import base64
import sqlite3
import logging
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
from backend.app.services.detector_service import detector_service, Detection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video", tags=["Video"])

@router.post("/inspect-strikers", response_model=StrikerInspectionResponse)
async def inspect_strikers_endpoint(
    file: UploadFile = File(...)
):
    """
    Fast inspection of video frame 0 (and scrub frames) to detect all person bounding boxes,
    measure striker confidence, and suggest default striker.
    Supports two-pass Roboflow detection for small/distant batters and MediaPipe fallback.
    """
    pose_service.ensure_loaded()
    if pose_service.landmarker is None:
        raise HTTPException(
            status_code=503,
            detail=f"Pose estimation AI engine is unavailable on the server ({pose_service.init_error or 'PoseLandmarker not loaded'}). Ensure runtime dependencies are installed."
        )

    temp_id = str(uuid.uuid4())[:8]
    temp_path = settings.UPLOADS_DIR / f"temp_inspect_{temp_id}_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract frames 0, 5, 10, 15, 20 for scrubbing & preview
        cap = cv2.VideoCapture(str(temp_path))
        scrub_indices = [0, 5, 10, 15, 20]
        scrub_frames_data = []
        frame0 = None
        orig_h, orig_w = 480, 640

        for idx in range(25):
            ret, fr = cap.read()
            if not ret or fr is None:
                break
            if idx == 0:
                frame0 = fr.copy()
                orig_h, orig_w = frame0.shape[:2]
            if idx in scrub_indices:
                disp_fr = fr
                if disp_fr.shape[1] > 1280:
                    sc = 1280.0 / disp_fr.shape[1]
                    disp_fr = cv2.resize(disp_fr, (1280, int(disp_fr.shape[0] * sc)))
                s_ok, s_enc = cv2.imencode(".jpg", disp_fr, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if s_ok:
                    b64_str = base64.b64encode(s_enc).decode('utf-8')
                    scrub_frames_data.append({
                        "frame_idx": idx,
                        "data_url": f"data:image/jpeg;base64,{b64_str}"
                    })
        cap.release()

        frame0_raw_b64 = None
        frame0_b64 = None
        if scrub_frames_data:
            frame0_b64 = scrub_frames_data[0]["data_url"]
            frame0_raw_b64 = frame0_b64.replace("data:image/jpeg;base64,", "")

        # Determine detection path: Roboflow or Fallback
        candidates = []
        detection_source = "mediapipe_fallback"
        detector_status = "active"
        detector_reason = None
        calls_used = 0
        camera_view = "side_on"
        camera_warning = None
        needs_conf = False
        conf_msg = None
        default_tid = 0

        # Try Roboflow two-pass detection if configured
        rf_success = False
        if detector_service.is_configured() and frame0 is not None:
            call_counter = {"count": 0}
            rf_dets, rf_stat, calls_used = detector_service.detect_frame_two_pass(frame0, call_counter=call_counter)
            if rf_stat == "ok" and rf_dets:
                detection_source = "roboflow"
                detector_status = "active"
                camera_view, camera_warning = detector_service.estimate_camera_view(rf_dets, (orig_h, orig_w))

                rf_tracks = detector_service.track_detections({0: rf_dets})
                rf_tid, rf_select_status, rf_details = detector_service.select_striker(rf_tracks, {0: rf_dets})

                # Build candidate objects from detector tracks
                for tid, tr in rf_tracks.items():
                    bx = tr.last_bbox
                    box_h_px = int(round((bx[3] - bx[1]) * orig_h))
                    is_small = box_h_px < 120
                    is_def = (tid == rf_tid) if rf_tid is not None else (tr.class_name == "batter")
                    is_striker = is_def and (tr.class_name == "batter")

                    role_name = (
                        "Suggested Striker (Locked)" if is_striker
                        else ("Batter Candidate" if tr.class_name == "batter" else f"{tr.class_name.replace('_', ' ').title()} (Excluded)")
                    )

                    candidates.append(StrikerCandidate(
                        track_id=tid,
                        bbox=bx,
                        is_default=is_striker,
                        role=role_name,
                        class_name=tr.class_name,
                        striker_score=round(tr.bat_overlap_count * 15.0 + max(0.0, 1.0 - tr.avg_stumps_distance) * 10.0 + 0.2, 2),
                        reason=f"Roboflow {tr.class_name} detection (score: {round(tr.bat_overlap_count * 15.0 + max(0.0, 1.0 - tr.avg_stumps_distance) * 10.0 + 0.2, 2)})",
                        box_height_px=box_h_px,
                        is_small_target=is_small,
                        wrist_motion_score=0.0,
                        confidence=0.85 if is_striker else 0.50
                    ))

                if rf_select_status == "striker_unclear":
                    needs_conf = True
                    conf_msg = rf_details.get("reason", "Could not tell who the striker is. Please tap the batter.")
                    default_tid = rf_details.get("candidates", [{}])[0].get("track_id", 0) if rf_details.get("candidates") else 0
                elif rf_tid is not None:
                    default_tid = rf_tid
                    needs_conf = False
                rf_success = len(candidates) > 0

            if not rf_success:
                detector_reason = detector_service.last_call_error or f"Roboflow API returned status: {rf_stat}"
                detector_status = f"degraded: detector unavailable ({detector_reason})"
                logger.info(f"Roboflow detector fell back: {detector_reason}")
        else:
            reason = "ROBOFLOW_API_KEY missing" if not settings.ROBOFLOW_API_KEY else "ROBOFLOW_MODEL_ID missing"
            detector_status = f"degraded: detector unavailable ({reason})"
            detector_reason = reason
            logger.info(f"Detector unconfigured ({reason}), using MediaPipe fallback.")

        # Fallback to MediaPipe pose inspection if Roboflow returned no person candidates
        if not rf_success:
            detection_source = "mediapipe_fallback"
            inspect_data = pose_service.inspect_strikers(temp_path, max_scan_frames=60)
            candidates = [
                StrikerCandidate(
                    track_id=c["track_id"],
                    bbox=c["bbox"],
                    is_default=c["is_default"],
                    role=c["role"],
                    class_name=c.get("class_name", "person"),
                    striker_score=c.get("striker_score"),
                    reason=c.get("reason"),
                    box_height_px=c.get("box_height_px"),
                    is_small_target=c.get("is_small_target", False),
                    wrist_motion_score=c["wrist_motion_score"],
                    confidence=c.get("confidence"),
                    evidence=c.get("evidence")
                )
                for c in inspect_data.get("candidates", [])
            ]
            default_tid = inspect_data.get("default_track_id", 0)
            needs_conf = inspect_data.get("needs_confirmation", False)
            conf_msg = inspect_data.get("confirmation_message")
            if inspect_data.get("camera_warning"):
                camera_warning = inspect_data.get("camera_warning")

        logger.info(f"Inspect Strikers Complete: source={detection_source}, status={detector_status}, candidates={len(candidates)}, needs_conf={needs_conf}")

        return StrikerInspectionResponse(
            candidates=candidates,
            default_track_id=default_tid,
            total_persons=len(candidates),
            frame_width=orig_w,
            frame_height=orig_h,
            frame0_thumbnail_base64=frame0_raw_b64,
            frame_0_data_url=frame0_b64,
            needs_confirmation=needs_conf,
            confirmation_message=conf_msg,
            detection_source=detection_source,
            detector_status=detector_status,
            detector_reason=detector_reason,
            roboflow_calls_used=calls_used,
            camera_view=camera_view,
            camera_warning=camera_warning,
            scrub_frames=scrub_frames_data
        )
    finally:
        temp_path.unlink(missing_ok=True)

@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    shot_type: str = Form("Auto-Detect"),
    handedness: str = Form("Right"),
    camera_angle: str = Form("Side View"),
    striker_track_id: Optional[str] = Form(None),
    striker_tap_coords: Optional[str] = Form(None),
    manual_crop_box: Optional[str] = Form(None)
):
    # Safely parse striker_track_id (preventing 422 if client sends 'undefined', 'null', or empty string)
    parsed_striker_track_id: Optional[int] = None
    if striker_track_id is not None:
        clean_track = str(striker_track_id).strip()
        if clean_track and clean_track.lower() not in ("none", "null", "undefined", ""):
            try:
                parsed_striker_track_id = int(clean_track)
            except (ValueError, TypeError):
                parsed_striker_track_id = None

    # Fail fast if server AI engine is not ready
    pose_service.ensure_loaded()
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
    except (OSError, IOError) as e:
        logger.exception(f"Failed to save uploaded video {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded video to storage: {str(e)}")

    # Initial video validation check
    val = video_service.validate_video_file(saved_path)
    if not val["valid"]:
        saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=val["error"])

    # Register in repository
    try:
        session_repo.create_session(
            session_id=session_id,
            video_filename=file.filename,
            original_path=str(saved_path),
            shot_type=shot_type,
            handedness=handedness,
            camera_angle=camera_angle,
            striker_track_id=parsed_striker_track_id,
            striker_tap_coords=striker_tap_coords,
            manual_crop_box=manual_crop_box
        )
    except sqlite3.Error as db_err:
        logger.exception(f"Database error registering session {session_id}: {db_err}")
        saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Database error registering video session: {str(db_err)}")

    # Queue background processing
    background_tasks.add_task(video_service.process_video_session, session_id)

    return VideoUploadResponse(
        session_id=session_id,
        filename=file.filename,
        shot_type=shot_type,
        handedness=handedness,
        camera_angle=camera_angle,
        striker_track_id=parsed_striker_track_id,
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
        error=session["error"],
        result=session.get("result") if session.get("status") == "completed" else None
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

@router.post("/debug")
async def debug_video_endpoint(
    file: UploadFile = File(...)
):
    """
    Diagnostic debug endpoint reporting frames read, frame size, rotation metadata applied,
    person boxes found per sampled frame, pose estimation results per frame, and failing stage.
    """
    temp_id = str(uuid.uuid4())[:8]
    temp_path = settings.UPLOADS_DIR / f"temp_debug_{temp_id}_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        report = video_service.debug_video_pipeline(temp_path)
        return report
    finally:
        temp_path.unlink(missing_ok=True)

@router.get("/debug/{session_id}")
async def debug_session_endpoint(session_id: str):
    """
    Diagnostic debug endpoint for an existing session by ID.
    """
    session = session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    orig_path = Path(session.get("original_path", ""))
    if not orig_path.exists():
        raise HTTPException(status_code=404, detail="Original video file not found on disk")
    report = video_service.debug_video_pipeline(orig_path)
    report["session_id"] = session_id
    report["session_status"] = session.get("status")
    report["session_error"] = session.get("error")
    return report
