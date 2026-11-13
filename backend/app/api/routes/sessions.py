from pathlib import Path
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
from backend.app.schemas.sessions import SessionListResponse, SessionListItem
from backend.app.repositories.session_repository import session_repo
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])

class ConfirmShotRequest(BaseModel):
    confirmed_shot_type: str

@router.get("", response_model=SessionListResponse)
def list_sessions(
    limit: int = Query(50, ge=1, le=100),
    shot_type: Optional[str] = Query(None, description="Filter by shot type"),
    category: Optional[str] = Query(None, description="Filter by shot category")
):
    raw_list = session_repo.list_sessions(limit=limit, shot_type=shot_type, category=category)
    items = []
    shot_counts = {}
    category_counts = {}

    for s in raw_list:
        shot = s.get("shot_type") or "Unknown"
        cat = s.get("category") or "Other"
        shot_counts[shot] = shot_counts.get(shot, 0) + 1
        category_counts[cat] = category_counts.get(cat, 0) + 1

        summary = None
        if s.get("result") and s["result"].get("summary"):
            summary = s["result"]["summary"]

        items.append(SessionListItem(
            session_id=s["session_id"],
            video_filename=s["video_filename"],
            shot_type=shot,
            category=cat,
            handedness=s.get("handedness") or "Right",
            camera_angle=s.get("camera_angle") or "Side View",
            duration_sec=s.get("duration_sec") or 0.0,
            status=s.get("status") or "queued",
            created_at=s.get("created_at") or "",
            thumbnail_path=s.get("thumbnail_path"),
            summary=summary
        ))

    return SessionListResponse(
        sessions=items,
        total_count=len(items),
        shot_types_summary=shot_counts,
        categories_summary=category_counts
    )

@router.get("/{session_id}")
def get_session_detail(session_id: str):
    s = session_repo.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return s

@router.post("/{session_id}/confirm-shot")
def confirm_session_shot(session_id: str, payload: ConfirmShotRequest):
    """Allows user to confirm or manually change the detected batting shot type."""
    updated = session_repo.confirm_shot_type(session_id, payload.confirmed_shot_type)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return {
        "session_id": session_id,
        "confirmed_shot_type": payload.confirmed_shot_type,
        "message": f"Session shot type updated to '{payload.confirmed_shot_type}' successfully."
    }

@router.delete("/{session_id}")
def delete_session(session_id: str):
    s = session_repo.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    # Remove storage files if present
    if s.get("original_path"):
        try:
            Path(s["original_path"]).unlink(missing_ok=True)
        except OSError as file_err:
            logger.warning(f"Could not unlink original video file: {file_err}")

    annotated_file = settings.ANNOTATED_DIR / f"{session_id}_annotated.mp4"
    annotated_file.unlink(missing_ok=True)
    thumb_file = settings.THUMBNAILS_DIR / f"{session_id}_thumb.jpg"
    thumb_file.unlink(missing_ok=True)

    success = session_repo.delete_session(session_id)
    return {"session_id": session_id, "deleted": success, "message": "Session and media files deleted."}
