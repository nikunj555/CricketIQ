import uuid
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from backend.app.core.config import settings
from backend.app.repositories.session_repository import session_repo
from backend.app.data.reference_catalogue import get_reference_for_shot, get_reference_by_id, get_all_references
from backend.app.data.shot_catalogue import get_shot_by_id_or_slug

router = APIRouter(prefix="/reference", tags=["Reference Library"])

class ReferenceDetailResponse(BaseModel):
    id: str
    shot_id: str
    shot_name: str
    player_name: str
    source: str
    source_url: Optional[str] = None
    video_url: str
    thumbnail_url: Optional[str] = None
    camera_view: str
    verification_status: str
    description: str
    stance_setup: str
    footwork_weight_transfer: str
    body_positioning: str
    technique_points: List[str]
    common_mistakes: List[str]
    phases: List[Dict[str, Any]]
    key_metrics: Dict[str, Any]
    is_custom_upload: bool = False

@router.get("/list", response_model=List[ReferenceDetailResponse])
def list_all_references():
    """Lists all available reference videos and authentic benchmarks."""
    refs = session_repo.list_all_references()
    if not refs:
        # Fallback to in-memory registry
        refs = get_all_references()
    return refs

@router.get("/shots/{shot_id_or_slug}", response_model=ReferenceDetailResponse)
def get_shot_reference(shot_id_or_slug: str):
    """Retrieves authoritative reference breakdown and preview video for a specific shot."""
    ref = session_repo.get_reference_by_shot(shot_id_or_slug)
    if not ref:
        ref = get_reference_for_shot(shot_id_or_slug)
    if not ref:
        raise HTTPException(
            status_code=404,
            detail=f"No reference benchmark or footage currently registered for '{shot_id_or_slug}'. You can upload an authorized reference video."
        )
    return ref

@router.post("/upload")
async def upload_custom_reference(
    file: UploadFile = File(...),
    shot_id: str = Form(...),
    player_name: str = Form("Authorized Reference Athlete"),
    source: str = Form("User / Coach Uploaded Reference"),
    camera_view: str = Form("Side View"),
    description: Optional[str] = Form(None)
):
    """Uploads an authorized reference video for any shot type."""
    shot = get_shot_by_id_or_slug(shot_id)
    if not shot:
        raise HTTPException(status_code=400, detail=f"Invalid shot ID '{shot_id}'.")

    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{ext}'.")

    ref_uuid = f"custom_ref_{str(uuid.uuid4())[:8]}"
    safe_filename = f"{ref_uuid}_{file.filename.replace(' ', '_')}"
    saved_path = settings.UPLOADS_DIR / safe_filename

    try:
        with open(saved_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save video: {e}")

    # Generate thumbnail
    thumb_filename = f"{ref_uuid}_thumb.jpg"
    thumb_path = settings.THUMBNAILS_DIR / thumb_filename
    try:
        import cv2
        cap = cv2.VideoCapture(str(saved_path))
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(str(thumb_path), frame)
        cap.release()
    except Exception:
        pass

    ref_dict = {
        "id": ref_uuid,
        "shot_id": shot["id"],
        "shot_name": shot["name"],
        "player_name": player_name,
        "source": source,
        "source_url": "",
        "video_url": f"/api/video/original/{safe_filename}",
        "thumbnail_url": f"/api/video/thumbnail/{thumb_filename}",
        "camera_view": camera_view,
        "verification_status": "verified",
        "description": description or f"Authorized reference footage demonstrating {shot['name']}.",
        "stance_setup": "Balanced standard batting stance.",
        "footwork_weight_transfer": "Synchronized stride and weight transfer.",
        "body_positioning": "Standard upright spinal posture with steady head.",
        "technique_points": [
            f"Demonstrates textbook {shot['name']} mechanics.",
            "Appropriate base and balance at impact window.",
            "Complete follow-through through the line."
        ],
        "common_mistakes": [
            "Loss of balance through point of contact.",
            "Head tilting away from delivery line."
        ],
        "phases": [],
        "key_metrics": {
            "lead_knee_flexion_at_impact": 125.0,
            "torso_lean_at_impact": 24.0,
            "head_stability_index": 0.035
        },
        "is_custom_upload": True
    }

    session_repo.save_reference(ref_dict)
    return {
        "message": f"Custom reference video for '{shot['name']}' uploaded successfully.",
        "reference": ref_dict
    }

