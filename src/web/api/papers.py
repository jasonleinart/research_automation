"""
Papers API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from uuid import UUID

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.database.insight_repository import InsightRepository
from src.database.tag_repository import PaperTagRepository, TagRepository
from src.web.models.schemas import (
    PaperListResponse, PaperDetailResponse, PaperSchema, AuthorSchema, InsightSchema, TagSchema
)

router = APIRouter()

@router.get("/", response_model=PaperListResponse)
async def list_papers(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in title and abstract"),
    paper_type: Optional[str] = Query(None, description="Filter by paper type"),
    status: Optional[str] = Query(None, description="Filter by analysis status")
):
    """List papers with pagination and filtering."""
    try:
        await db_manager.initialize()
        
        repo = PaperRepository()
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get papers with filters
        papers = await repo.list_all(limit=per_page, offset=offset)
        
        # Apply search filter if provided
        if search:
            papers = [p for p in papers if search.lower() in p.title.lower() or search.lower() in p.abstract.lower()]
        
        # Apply type filter if provided
        if paper_type:
            papers = [p for p in papers if p.paper_type and p.paper_type.value == paper_type]
        
        # Apply status filter if provided
        if status:
            papers = [p for p in papers if p.analysis_status.value == status]
        
        # Get total count for pagination
        total = len(papers)  # This is simplified - in production you'd want a proper count query
        
        # Convert to schemas
        paper_schemas = []
        for paper in papers:
            # Handle authors properly
            authors = []
            if paper.authors:
                for author in paper.authors:
                    # Simple approach: just use the string representation
                    author_name = str(author)
                    # Clean up common patterns
                    if "Author(name=" in author_name:
                        # Try to extract just the name part
                        if "name='" in author_name:
                            parts = author_name.split("name='")
                            if len(parts) > 1:
                                name_part = parts[1]
                                if "'" in name_part:
                                    author_name = name_part.split("'")[0]
                                else:
                                    author_name = "Unknown Author"
                            else:
                                author_name = "Unknown Author"
                        else:
                            author_name = "Unknown Author"
                    elif hasattr(author, 'name'):
                        author_name = author.name
                    elif isinstance(author, dict):
                        author_name = author.get('name', 'Unknown')
                    
                    authors.append(AuthorSchema(name=author_name))
            
            paper_schema = PaperSchema(
                id=paper.id,
                arxiv_id=paper.arxiv_id,
                title=paper.title,
                abstract=paper.abstract,
                authors=authors,
                publication_date=paper.publication_date,
                categories=paper.categories,
                paper_type=paper.paper_type,
                analysis_status=paper.analysis_status,
                created_at=paper.created_at,
                updated_at=paper.updated_at
            )
            paper_schemas.append(paper_schema)
        
        total_pages = (total + per_page - 1) // per_page
        
        return PaperListResponse(
            papers=paper_schemas,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching papers: {str(e)}")

@router.get("/{paper_id}", response_model=PaperDetailResponse)
async def get_paper(paper_id: UUID):
    """Get detailed information about a specific paper."""
    try:
        await db_manager.initialize()
        
        repo = PaperRepository()
        insight_repo = InsightRepository()
        paper_tag_repo = PaperTagRepository()
        
        # Get paper
        paper = await repo.get_by_id(paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        # Get insights
        insights = await insight_repo.get_by_paper_id(paper_id)
        
        # Get tags
        paper_tags = await paper_tag_repo.get_by_paper(paper_id)
        tag_repo = TagRepository()
        tags = []
        for paper_tag in paper_tags:
            tag = await tag_repo.get_by_id(paper_tag.tag_id)
            if tag:
                tags.append(tag)
        
        # Convert to schema
        authors = []
        if paper.authors:
            for author in paper.authors:
                if hasattr(author, 'name'):
                    authors.append(AuthorSchema(name=author.name))
                elif isinstance(author, dict):
                    authors.append(AuthorSchema(name=author.get('name', 'Unknown')))
                else:
                    authors.append(AuthorSchema(name=str(author)))
        
        paper_schema = PaperSchema(
            id=paper.id,
            arxiv_id=paper.arxiv_id,
            title=paper.title,
            abstract=paper.abstract,
            authors=authors,
            publication_date=paper.publication_date,
            categories=paper.categories,
            paper_type=paper.paper_type,
            analysis_status=paper.analysis_status,
            created_at=paper.created_at,
            updated_at=paper.updated_at
        )
        
        # Convert insights to schemas
        insight_schemas = []
        for insight in insights:
            content_str = insight.content
            if isinstance(content_str, dict):
                content_str = str(content_str)
            elif content_str is None:
                content_str = ""
            
            insight_schema = InsightSchema(
                id=insight.id,
                paper_id=insight.paper_id,
                insight_type=insight.insight_type,
                title=insight.title,
                description=insight.description,
                confidence=insight.confidence,
                extraction_method=insight.extraction_method,
                content=content_str,
                created_at=insight.created_at
            )
            insight_schemas.append(insight_schema)
        
        # Convert tags to schemas
        tag_schemas = []
        for tag in tags:
            tag_schema = TagSchema(
                id=tag.id,
                name=tag.name,
                category=tag.category,
                description=tag.description,
                usage_count=0,  # We could calculate this if needed
                created_at=tag.created_at
            )
            tag_schemas.append(tag_schema)
        
        return PaperDetailResponse(
            paper=paper_schema,
            insights=insight_schemas,
            tags=tag_schemas
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching paper: {str(e)}")

@router.get("/search", response_model=PaperListResponse)
async def search_papers(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
):
    """Search papers by title and abstract."""
    try:
        await db_manager.initialize()
        
        repo = PaperRepository()
        
        # Get all papers (simplified - in production you'd want proper search)
        all_papers = await repo.list_all()
        
        # Filter by search query
        papers = []
        for paper in all_papers:
            if (q.lower() in paper.title.lower() or 
                q.lower() in paper.abstract.lower() or
                any(q.lower() in author.name.lower() for author in paper.authors)):
                papers.append(paper)
        
        # Apply pagination
        offset = (page - 1) * per_page
        paginated_papers = papers[offset:offset + per_page]
        
        # Convert to schemas
        paper_schemas = []
        for paper in paginated_papers:
            authors = [AuthorSchema(name=author.name) for author in paper.authors]
            paper_schema = PaperSchema(
                id=paper.id,
                arxiv_id=paper.arxiv_id,
                title=paper.title,
                abstract=paper.abstract,
                authors=authors,
                publication_date=paper.publication_date,
                categories=paper.categories,
                paper_type=paper.paper_type,
                evidence_strength=paper.evidence_strength,
                novelty_score=paper.novelty_score,
                practical_applicability=paper.practical_applicability,
                analysis_status=paper.analysis_status,
                analysis_confidence=paper.analysis_confidence,
                created_at=paper.created_at,
                updated_at=paper.updated_at
            )
            paper_schemas.append(paper_schema)
        
        total = len(papers)
        total_pages = (total + per_page - 1) // per_page
        
        return PaperListResponse(
            papers=paper_schemas,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching papers: {str(e)}")

@router.get("/stats/overview")
async def get_paper_stats():
    """Get paper statistics."""
    try:
        await db_manager.initialize()
        
        repo = PaperRepository()
        stats = await repo.get_statistics()
        
        return {
            "success": True,
            "stats": {
                "total_papers": stats.get("total_papers", 0),
                "analyzed_papers": stats.get("analyzed_papers", 0),
                "pending_papers": stats.get("pending_papers", 0),
                "papers_by_type": stats.get("papers_by_type", {}),
                "papers_by_status": stats.get("papers_by_status", {})
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching paper stats: {str(e)}") 