from fastapi import APIRouter, HTTPException
from backend.app.schemas.analysis import AnalysisResult
from backend.app.repositories.session_repository import session_repo

router = APIRouter(prefix="/analysis", tags=["Analysis"])

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
