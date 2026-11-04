from pydantic import BaseModel
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from backend.app.schemas.comparison import ComparisonResult, ReferenceShotMeta
from backend.app.services.comparison_service import comparison_service
from backend.app.repositories.session_repository import session_repo

router = APIRouter(prefix="/comparison", tags=["Comparison"])

class CompareRequest(BaseModel):
    session_id: str
    reference_id: Optional[str] = None
    target_session_id: Optional[str] = None

@router.get("/references", response_model=List[ReferenceShotMeta])
def list_reference_benchmarks():
    return comparison_service.list_reference_shots()

@router.post("/compare", response_model=ComparisonResult)
def compare_sessions(payload: CompareRequest):
    query_session = session_repo.get_session(payload.session_id)
    if not query_session:
        raise HTTPException(status_code=404, detail=f"Query session '{payload.session_id}' not found.")

    if query_session["status"] != "completed" or not query_session.get("result"):
        raise HTTPException(status_code=400, detail="Query session analysis has not completed yet.")

    # Target session comparison (Attempt vs Attempt)
    if payload.target_session_id:
        target_session = session_repo.get_session(payload.target_session_id)
        if not target_session:
            raise HTTPException(status_code=404, detail=f"Target session '{payload.target_session_id}' not found.")
        if target_session["status"] != "completed" or not target_session.get("result"):
            raise HTTPException(status_code=400, detail="Target session analysis has not completed yet.")

        # Adapt target session as reference
        target_result = target_session["result"]
        custom_ref = {
            "id": target_session["session_id"],
            "title": f"Practice Attempt ({target_session.get('video_filename')})",
            "shot_type": target_session.get("shot_type", "Cover Drive"),
            "data": {
                "time_series": target_result.get("time_series", [])
            }
        }
        # Run comparison with custom reference
        res = comparison_service.compare_session_with_reference(
            query_session_data=query_session,
            reference_id=None,
            custom_reference=custom_ref
        )
        # Override title to reflect session comparison
        res.reference_id = target_session["session_id"]
        res.reference_title = f"Previous Attempt: {target_session.get('video_filename')}"
        return res

    # Comparison against benchmark reference
    return comparison_service.compare_session_with_reference(
        query_session_data=query_session,
        reference_id=payload.reference_id
    )
