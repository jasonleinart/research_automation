"""
Insights API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from uuid import UUID

from src.database.connection import db_manager
from src.database.insight_repository import InsightRepository
from src.database.paper_repository import PaperRepository
from src.web.models.schemas import (
    InsightListResponse, InsightDetailResponse, InsightSchema
)

router = APIRouter()

@router.get("/", response_model=InsightListResponse)
async def list_insights(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    insight_type: Optional[str] = Query(None, description="Filter by insight type"),
    min_confidence: Optional[str] = Query(None, description="Minimum confidence score"),
    paper_id: Optional[UUID] = Query(None, description="Filter by paper ID"),
    sort_by: Optional[str] = Query("created_at", description="Sort field")
):
    """List insights with pagination and filtering."""
    try:
        await db_manager.initialize()
        
        repo = InsightRepository()
        
        # Get all insights (simplified - in production you'd want proper filtering)
        insights = await repo.list_all()
        
        # Apply filters
        if insight_type and insight_type.strip():
            insights = [i for i in insights if i.insight_type.value == insight_type]
        
        # Handle min_confidence parameter
        min_conf_float = None
        if min_confidence and min_confidence.strip():
            try:
                min_conf_float = float(min_confidence)
            except ValueError:
                pass  # Invalid number, ignore the filter
        
        if min_conf_float is not None:
            insights = [i for i in insights if i.confidence and i.confidence >= min_conf_float]
        
        if paper_id:
            insights = [i for i in insights if i.paper_id == paper_id]
        
        # Apply pagination
        offset = (page - 1) * per_page
        paginated_insights = insights[offset:offset + per_page]
        
        # Convert to schemas
        insight_schemas = []
        
        # Get paper information for all insights
        paper_repo = PaperRepository()
        paper_ids = list(set([insight.paper_id for insight in paginated_insights]))
        papers = await paper_repo.get_by_ids(paper_ids)
        papers_dict = {paper.id: paper for paper in papers}
        
        for insight in paginated_insights:
            # Convert content dict to string if needed
            content_str = insight.content
            if isinstance(content_str, dict):
                content_str = str(content_str)
            elif content_str is None:
                content_str = ""
            
            # Get paper information
            paper = papers_dict.get(insight.paper_id)
            paper_title = paper.title if paper else None
            paper_arxiv_id = paper.arxiv_id if paper else None
            
            insight_dict = {
                'id': insight.id,
                'paper_id': insight.paper_id,
                'insight_type': insight.insight_type,
                'title': insight.title,
                'description': insight.description,
                'confidence': insight.confidence,
                'extraction_method': insight.extraction_method,
                'content': content_str,
                'created_at': insight.created_at,
                'paper_title': paper_title,
                'paper_arxiv_id': paper_arxiv_id
            }
            insight_schemas.append(InsightSchema.model_validate(insight_dict))
        
        total = len(insights)
        total_pages = (total + per_page - 1) // per_page
        
        return InsightListResponse(
            insights=insight_schemas,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching insights: {str(e)}")

@router.get("/{insight_id}", response_model=InsightDetailResponse)
async def get_insight(insight_id: UUID):
    """Get detailed information about a specific insight."""
    try:
        await db_manager.initialize()
        
        repo = InsightRepository()
        paper_repo = PaperRepository()
        
        # Get insight
        insight = await repo.get_by_id(insight_id)
        if not insight:
            raise HTTPException(status_code=404, detail="Insight not found")
        
        # Get paper info
        paper = await paper_repo.get_by_id(insight.paper_id)
        paper_title = paper.title if paper else "Unknown"
        paper_arxiv_id = paper.arxiv_id if paper else ""
        
        # Convert to schema
        insight_schema = InsightSchema(
            id=insight.id,
            paper_id=insight.paper_id,
            insight_type=insight.insight_type,
            title=insight.title,
            description=insight.description,
            confidence=insight.confidence,
            extraction_method=insight.extraction_method,
            content=insight.content,
            created_at=insight.created_at
        )
        
        return InsightDetailResponse(
            insight=insight_schema,
            paper_title=paper_title,
            paper_arxiv_id=paper_arxiv_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching insight: {str(e)}")

@router.get("/by-paper/{paper_id}", response_model=InsightListResponse)
async def get_insights_by_paper(
    paper_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
):
    """Get insights for a specific paper."""
    try:
        await db_manager.initialize()
        
        repo = InsightRepository()
        
        # Get insights for paper
        insights = await repo.get_by_paper_id(paper_id)
        
        # Apply pagination
        offset = (page - 1) * per_page
        paginated_insights = insights[offset:offset + per_page]
        
        # Convert to schemas
        insight_schemas = []
        for insight in paginated_insights:
            insight_schema = InsightSchema(
                id=insight.id,
                paper_id=insight.paper_id,
                insight_type=insight.insight_type,
                title=insight.title,
                description=insight.description,
                confidence=insight.confidence,
                extraction_method=insight.extraction_method,
                content=insight.content,
                created_at=insight.created_at
            )
            insight_schemas.append(insight_schema)
        
        total = len(insights)
        total_pages = (total + per_page - 1) // per_page
        
        return InsightListResponse(
            insights=insight_schemas,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching paper insights: {str(e)}")

@router.get("/by-type/{insight_type}", response_model=InsightListResponse)
async def get_insights_by_type(
    insight_type: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
):
    """Get insights by type."""
    try:
        await db_manager.initialize()
        
        repo = InsightRepository()
        
        # Get insights by type
        insights = await repo.get_by_insight_type(insight_type)
        
        # Apply pagination
        offset = (page - 1) * per_page
        paginated_insights = insights[offset:offset + per_page]
        
        # Convert to schemas
        insight_schemas = []
        for insight in paginated_insights:
            insight_schema = InsightSchema(
                id=insight.id,
                paper_id=insight.paper_id,
                insight_type=insight.insight_type,
                title=insight.title,
                description=insight.description,
                confidence=insight.confidence,
                extraction_method=insight.extraction_method,
                content=insight.content,
                created_at=insight.created_at
            )
            insight_schemas.append(insight_schema)
        
        total = len(insights)
        total_pages = (total + per_page - 1) // per_page
        
        return InsightListResponse(
            insights=insight_schemas,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching insights by type: {str(e)}")

@router.get("/stats/overview")
async def get_insight_stats():
    """Get insight statistics."""
    try:
        await db_manager.initialize()
        
        repo = InsightRepository()
        stats = await repo.get_statistics()
        
        return {
            "success": True,
            "stats": {
                "total_insights": stats.get("total_insights", 0),
                "insights_by_type": stats.get("insights_by_type", {}),
                "avg_confidence": stats.get("avg_confidence", 0.0),
                "high_confidence_count": stats.get("high_confidence_count", 0),
                "extraction_methods": stats.get("extraction_methods", {})
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching insight stats: {str(e)}") 