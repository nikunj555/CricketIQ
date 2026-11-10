from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from backend.app.schemas.shots import ShotListResponse, CricketShot, CategorySummary
from backend.app.data.shot_catalogue import (
    SHOT_CATALOGUE,
    CRICKET_SHOT_CATEGORIES,
    get_shot_by_id_or_slug
)
from backend.app.services.reference_service import reference_service

router = APIRouter(prefix="/shots", tags=["Shot Library"])

def _enrich_shot_data(s: dict) -> dict:
    shot_copy = dict(s)
    tier = reference_service.get_shot_support_tier(shot_copy.get("name", ""))
    shot_copy["support_tier"] = tier
    if tier == "supported":
        shot_copy["analysis_status"] = "available"
        shot_copy["status_message"] = f"Empirically validated reference active for {shot_copy.get('name')}."
    else:
        shot_copy["analysis_status"] = "preview_only"
        shot_copy["status_message"] = "Preview only: analysis coming soon"
    return shot_copy

@router.get("", response_model=ShotListResponse)
def list_shots(
    category: Optional[str] = Query(None, description="Filter by category name"),
    search: Optional[str] = Query(None, description="Search query matching name, alias, tags, or description"),
    reference_only: bool = Query(False, description="Filter to only shots with registered reference benchmarks")
):
    filtered = [_enrich_shot_data(s) for s in SHOT_CATALOGUE]

    if category and category.lower() != "all" and category.lower() != "all shots":
        cat_lower = category.lower()
        filtered = [s for s in filtered if s["category"].lower() == cat_lower]

    if reference_only:
        filtered = [s for s in filtered if s["reference_status"] == "available"]

    if search:
        q = search.lower().strip()
        matched = []
        for s in filtered:
            in_name = q in s["name"].lower()
            in_category = q in s["category"].lower()
            in_desc = q in s["description"].lower()
            in_aliases = any(q in a.lower() for a in s.get("aliases", []))
            in_tags = any(q in t.lower() for t in s.get("tags", []))
            if in_name or in_category or in_desc or in_aliases or in_tags:
                matched.append(s)
        filtered = matched

    # Compute category summaries
    category_map = {c: [] for c in CRICKET_SHOT_CATEGORIES}
    for s in SHOT_CATALOGUE:
        if s["category"] in category_map:
            category_map[s["category"]].append(s["name"])

    category_summaries = [
        CategorySummary(name=c, count=len(category_map[c]), shots=category_map[c])
        for c in CRICKET_SHOT_CATEGORIES
    ]

    return ShotListResponse(
        total_count=len(filtered),
        categories=category_summaries,
        shots=[CricketShot(**s) for s in filtered]
    )

@router.get("/{id_or_slug}", response_model=CricketShot)
def get_shot(id_or_slug: str):
    shot = get_shot_by_id_or_slug(id_or_slug)
    if not shot:
        raise HTTPException(status_code=404, detail=f"Cricket shot '{id_or_slug}' not found in catalogue.")
    return CricketShot(**_enrich_shot_data(shot))
