"""
Papers API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, Response
from fastapi.responses import StreamingResponse
import logging
from uuid import UUID
import io

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.database.insight_repository import InsightRepository
from src.database.tag_repository import PaperTagRepository, TagRepository
from src.database.note_repository import NoteRepository
from src.web.models.schemas import (
    PaperListResponse, PaperDetailResponse, PaperSchema, AuthorSchema, InsightSchema, TagSchema
)

router = APIRouter()
logger = logging.getLogger(__name__)

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
        
        # Load authors for these papers
        paper_ids = [paper.id for paper in papers]
        papers_with_authors = await repo.get_papers_with_authors(paper_ids)
        
        # Get total count for pagination
        total = len(papers)  # This is simplified - in production you'd want a proper count query
        
        # Convert to schemas
        paper_schemas = []
        insight_repo = InsightRepository()
        paper_tag_repo = PaperTagRepository()
        
        for paper in papers_with_authors:
            # Get authors from the new relational system
            authors = []
            if hasattr(paper, '_author_names') and paper._author_names:
                for author_name in paper._author_names:
                    authors.append(AuthorSchema(name=author_name))
            else:
                # Fallback: try to get authors from the repository
                try:
                    from src.database.author_repository import AuthorRepository
                    author_repo = AuthorRepository()
                    paper_authors = await author_repo.get_paper_authors(paper.id)
                    for author in paper_authors:
                        authors.append(AuthorSchema(name=author.name))
                except Exception as e:
                    # If we can't get authors, just continue
                    pass
            
            # Get insight count for this paper
            insights = await insight_repo.get_by_paper_id(paper.id)
            insight_count = len(insights)
            
            # Get tags count for this paper
            paper_tags = await paper_tag_repo.get_by_paper(paper.id)
            tags_count = len(paper_tags)
            
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
                has_full_text=bool(paper.full_text),  # Check if full text exists
                created_at=paper.created_at,
                updated_at=paper.updated_at
            )
            
            # Add computed fields to the schema
            paper_dict = paper_schema.model_dump()
            paper_dict['insight_count'] = insight_count
            paper_dict['tags_count'] = tags_count
            
            paper_schemas.append(paper_dict)
        
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
        if hasattr(paper, '_author_names') and paper._author_names:
            for author_name in paper._author_names:
                authors.append(AuthorSchema(name=author_name))
        else:
            # Fallback: try to get authors from the repository
            try:
                from src.database.author_repository import AuthorRepository
                author_repo = AuthorRepository()
                paper_authors = await author_repo.get_paper_authors(paper.id)
                for author in paper_authors:
                    authors.append(AuthorSchema(name=author.name))
            except Exception as e:
                # If we can't get authors, just continue
                pass
        
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
            has_full_text=bool(paper.full_text),  # Check if full text exists
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
            # Check title and abstract
            if (q.lower() in paper.title.lower() or 
                q.lower() in paper.abstract.lower()):
                papers.append(paper)
                continue
            
            # Check authors if available
            if hasattr(paper, '_author_names') and paper._author_names:
                if any(q.lower() in author_name.lower() for author_name in paper._author_names):
                    papers.append(paper)
                    continue
        
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
                analysis_status=paper.analysis_status,
                has_full_text=bool(paper.full_text),  # Check if full text exists
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

@router.get("/{paper_id}/pdf")
async def get_paper_pdf(paper_id: UUID):
    """Serve PDF file for a paper."""
    try:
        await db_manager.initialize()
        async with db_manager.get_connection() as conn:
            # Get paper with PDF content
            row = await conn.fetchrow("""
                SELECT title, full_text, pdf_content 
                FROM papers 
                WHERE id = $1
            """, paper_id)
            
            if not row:
                raise HTTPException(status_code=404, detail="Paper not found")
            
            # If we have PDF content, serve it as PDF
            if row['pdf_content']:
                return Response(
                    content=row['pdf_content'],
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename=\"{row['title'][:50]}.pdf\""}
                )
            
            # Otherwise, serve full text as plain text
            if row['full_text']:
                return Response(
                    content=row['full_text'],
                    media_type="text/plain",
                    headers={"Content-Disposition": f"inline; filename=\"{row['title'][:50]}.txt\""}
                )
            
            raise HTTPException(status_code=404, detail="No PDF or full text available")
            
    except Exception as e:
        logger.error(f"Error serving PDF for paper {paper_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{paper_id}/notes")
async def get_paper_notes(paper_id: UUID):
    """Get all notes for a paper."""
    try:
        await db_manager.initialize()
        repo = NoteRepository()
        
        notes = await repo.get_notes_by_paper(paper_id)
        return {"notes": [note.to_dict() for note in notes]}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching notes: {str(e)}")

@router.post("/{paper_id}/notes")
async def create_paper_note(paper_id: UUID, note_data: dict):
    """Create a new note for a paper."""
    try:
        await db_manager.initialize()
        repo = NoteRepository()
        
        from src.models.note import Note
        from src.models.enums import NoteType, NotePriority
        
        note = Note(
            title=note_data.get("title", "Untitled Note"),
            content=note_data.get("content", ""),
            paper_id=paper_id,
            note_type=NoteType(note_data.get("note_type", "general")),
            priority=NotePriority(note_data.get("priority", "medium")),
            page_number=note_data.get("page_number"),
            x_position=note_data.get("x_position"),
            y_position=note_data.get("y_position"),
            width=note_data.get("width"),
            height=note_data.get("height"),
            selected_text=note_data.get("selected_text"),
            annotation_color=note_data.get("annotation_color"),
            tags=note_data.get("tags", []),
            context_section=note_data.get("context_section")
        )
        
        created_note = await repo.create_note(note)
        return created_note.to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating note: {str(e)}") 