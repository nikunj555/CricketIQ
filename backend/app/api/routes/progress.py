"""
CricketIQ — Progress Tracking API Routes
Provides endpoints for querying user practice progression, consistency trends,
and per-shot biomechanical trajectories over time.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List, Optional
from backend.app.services.progress_service import progress_service

router = APIRouter(prefix="/progress", tags=["Progress & History"])


@router.get("/summary", summary="Get overall progress summary across all shot types")
def get_progress_summary(limit: int = Query(default=200, ge=1, le=1000)):
    """
    Returns aggregated progress metrics across all completed sessions in the database:
    - Session counts by shot type
    - Average key impact angles (lead knee, torso lean)
    - Tracking reliability statistics
    - Consistency metrics (coefficient of variation)
    """
    return progress_service.get_all_shots_summary(limit=limit)


@router.get("/shots", summary="List shot types with available session history")
def list_available_shot_types() -> List[str]:
    """
    Returns the distinct list of shot types that have at least one completed practice session.
    """
    return progress_service.get_available_shot_types_with_data()


@router.get("/shots/{shot_type}", summary="Get detailed progression trend for a specific shot")
def get_shot_progression(
    shot_type: str,
    limit: int = Query(default=50, ge=1, le=200)
):
    """
    Returns chronologically ordered kinematic points and per-metric statistical trends
    for the requested shot type.
    Includes trend direction ('improving', 'stable', 'needs_attention') and reliability flags.
    """
    trend = progress_service.get_shot_trend(shot_type=shot_type, limit=limit)
    if not trend:
        raise HTTPException(status_code=404, detail=f"No data available for shot type '{shot_type}'")
    return trend

