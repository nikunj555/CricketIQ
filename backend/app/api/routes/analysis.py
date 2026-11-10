from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.app.schemas.analysis import AnalysisResult
from backend.app.repositories.session_repository import session_repo
from backend.app.services.video_service import video_service

router = APIRouter(prefix="/analysis", tags=["Analysis"])

class ReanalyzeRequest(BaseModel):
    shot_type: str
    lang: Optional[str] = "en"

@router.get("/{session_id}", response_model=AnalysisResult)
def get_analysis_result(session_id: str):
    session = session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    if session["status"] == "failed":
        raise HTTPException(status_code=422, detail=f"Processing failed: {session.get('error', 'Unknown failure')}")

    if session["status"] != "completed" or not session.get("result"):
        raise HTTPException(status_code=202, detail="Analysis is still processing. Check status endpoint.")

    return session["result"]

@router.post("/{session_id}/reanalyze", response_model=AnalysisResult)
def reanalyze_shot_endpoint(session_id: str, payload: ReanalyzeRequest):
    updated = video_service.reanalyze_shot(session_id, payload.shot_type, lang=payload.lang or "en")
    if not updated:
        raise HTTPException(status_code=404, detail="Session not found or analysis incomplete.")
    return updated
