"""
Pydantic schemas for API requests and responses
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

from src.models.enums import PaperType, AnalysisStatus, InsightType, TagCategory, EvidenceStrength, PracticalApplicability

# Base schemas
class BaseResponse(BaseModel):
    """Base response model."""
    success: bool = True
    message: Optional[str] = None

# Paper schemas
class AuthorSchema(BaseModel):
    """Author information."""
    name: str
    affiliation: Optional[str] = None

class PaperSchema(BaseModel):
    """Paper information."""
    id: UUID
    arxiv_id: str
    title: str
    abstract: str
    authors: List[AuthorSchema]
    publication_date: Optional[datetime]
    categories: List[str]
    paper_type: PaperType
    analysis_status: AnalysisStatus
    created_at: datetime
    updated_at: datetime

# Insight schemas
class InsightSchema(BaseModel):
    """Insight information."""
    id: UUID
    paper_id: UUID
    insight_type: InsightType
    title: str
    description: Optional[str] = None
    content: str
    confidence: Optional[float] = None
    extraction_method: Optional[str] = None
    created_at: Optional[datetime] = None
    # Paper information for display
    paper_title: Optional[str] = None
    paper_arxiv_id: Optional[str] = None

# Tag schemas
class TagSchema(BaseModel):
    """Tag information."""
    id: UUID
    name: str
    description: Optional[str] = None
    category: TagCategory
    usage_count: int = 0
    created_at: datetime

# Dashboard schemas
class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_papers: int
    total_insights: int
    total_tags: int
    completed_analyses: int
    manual_review_analyses: int
    failed_analyses: int
    analysis_status_counts: Dict[str, int] = Field(default_factory=dict)
    insights_by_type: Dict[str, int] = Field(default_factory=dict)
    top_tags: List[TagSchema]
    recent_papers: List[PaperSchema]
    recent_insights: List[InsightSchema]

class DashboardResponse(BaseModel):
    """Dashboard response."""
    stats: DashboardStats

# List response schemas
class PaperListResponse(BaseModel):
    """Papers list response."""
    papers: List[PaperSchema]
    total: int
    page: int
    per_page: int
    total_pages: int

class PaperDetailResponse(BaseModel):
    """Paper detail response."""
    paper: PaperSchema
    insights: List[InsightSchema]
    tags: List[TagSchema]

class InsightListResponse(BaseModel):
    """Insights list response."""
    insights: List[InsightSchema]
    total: int
    page: int
    per_page: int
    total_pages: int

class InsightDetailResponse(BaseModel):
    """Insight detail response."""
    insight: InsightSchema
    paper: PaperSchema

class TagListResponse(BaseModel):
    """Tags list response."""
    tags: List[TagSchema]
    total: int
    page: int
    per_page: int
    total_pages: int

class TagDetailResponse(BaseModel):
    """Tag detail response."""
    tag: TagSchema
    papers: List[PaperSchema]

# Search schemas
class SearchRequest(BaseModel):
    """Search request."""
    query: str
    filters: Optional[Dict[str, Any]] = None
    page: int = 1
    per_page: int = 20

class SearchResponse(BaseResponse):
    """Search response."""
    papers: List[PaperSchema]
    insights: List[InsightSchema]
    tags: List[TagSchema]
    total_results: int
    page: int
    per_page: int 