from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class CricketShot(BaseModel):
    id: str
    slug: str
    name: str
    category: str
    description: str
    aliases: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    difficulty: str
    analysis_features: List[str] = Field(default_factory=list)
    reference_id: Optional[str] = None
    reference_status: str  # "available" | "unavailable"
    reference_title: Optional[str] = None
    reference_player: Optional[str] = None
    reference_source: Optional[str] = None
    reference_video_url: Optional[str] = None
    reference_thumbnail_url: Optional[str] = None
    implementation_status: str  # "supported" | "experimental" | "in_development"
    support_tier: Optional[str] = "preview_only"  # "supported" | "preview_only"
    analysis_status: Optional[str] = "available"  # "available" | "preview_only" | "coming_soon"
    status_message: Optional[str] = None
    technique_notes: Optional[str] = None

class CategorySummary(BaseModel):
    name: str
    count: int
    shots: List[str]

class ShotListResponse(BaseModel):
    total_count: int
    categories: List[CategorySummary]
    shots: List[CricketShot]
