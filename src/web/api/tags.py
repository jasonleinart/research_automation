"""
Tags API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from uuid import UUID

from src.database.connection import db_manager
from src.database.tag_repository import TagRepository, PaperTagRepository
from src.database.paper_repository import PaperRepository
from src.web.models.schemas import (
    TagListResponse, TagDetailResponse, TagSchema, PaperSchema
)

router = APIRouter()

@router.get("/", response_model=TagListResponse)
async def list_tags(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by tag category"),
    min_usage: Optional[str] = Query(None, description="Minimum usage count"),
    sort_by: Optional[str] = Query("name", description="Sort field")
):
    """List tags with pagination and filtering."""
    try:
        await db_manager.initialize()
        
        repo = TagRepository()
        paper_tag_repo = PaperTagRepository()
        
        # Get all tags
        tags = await repo.list_all()
        
        # Apply category filter
        if category and category.strip():
            tags = [t for t in tags if t.category.value == category]
        
        # Get usage statistics
        tag_stats = await paper_tag_repo.get_tag_usage_stats()
        usage_map = {stat['name']: stat['usage_count'] for stat in tag_stats}
        
        # Handle min_usage parameter
        min_usage_int = None
        if min_usage and min_usage.strip():
            try:
                min_usage_int = int(min_usage)
            except ValueError:
                pass  # Invalid number, ignore the filter
        
        # Apply usage filter
        if min_usage_int is not None:
            tags = [t for t in tags if usage_map.get(t.name, 0) >= min_usage_int]
        
        # Apply pagination
        offset = (page - 1) * per_page
        paginated_tags = tags[offset:offset + per_page]
        
        # Convert to schemas
        tag_schemas = []
        for tag in paginated_tags:
            # Get usage count for this tag
            usage_count = usage_map.get(tag.name, 0)
            
            tag_dict = {
                'id': tag.id,
                'name': tag.name,
                'category': tag.category,
                'description': tag.description,
                'parent_tag_id': tag.parent_tag_id,
                'usage_count': usage_count,
                'created_at': tag.created_at
            }
            tag_schemas.append(TagSchema.model_validate(tag_dict))
        
        total = len(tags)
        total_pages = (total + per_page - 1) // per_page
        
        return TagListResponse(
            tags=tag_schemas,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tags: {str(e)}")

@router.get("/{tag_id}", response_model=TagDetailResponse)
async def get_tag(tag_id: UUID):
    """Get detailed information about a specific tag."""
    try:
        await db_manager.initialize()
        
        repo = TagRepository()
        paper_tag_repo = PaperTagRepository()
        paper_repo = PaperRepository()
        
        # Get tag
        tag = await repo.get_by_id(tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        # Get usage statistics
        tag_stats = await paper_tag_repo.get_tag_usage_stats()
        usage_count = 0
        for stat in tag_stats:
            if stat['name'] == tag.name:
                usage_count = stat['usage_count']
                break
        
        # Get papers associated with this tag
        paper_tags = await paper_tag_repo.get_by_tag(tag_id)
        papers = []
        for paper_tag in paper_tags:
            paper = await paper_repo.get_by_id(paper_tag.paper_id)
            if paper:
                # Get authors from the new relational system
                authors = []
                if hasattr(paper, '_author_names') and paper._author_names:
                    for author_name in paper._author_names:
                        authors.append({'name': author_name})
                else:
                    # Fallback: try to get authors from the repository
                    try:
                        from src.database.author_repository import AuthorRepository
                        author_repo = AuthorRepository()
                        paper_authors = await author_repo.get_paper_authors(paper.id)
                        for author in paper_authors:
                            authors.append({'name': author.name})
                    except Exception as e:
                        # If we can't get authors, just continue
                        pass
                
                paper_dict = {
                    'id': paper.id,
                    'arxiv_id': paper.arxiv_id,
                    'title': paper.title,
                    'abstract': paper.abstract,
                    'authors': authors,
                    'publication_date': paper.publication_date,
                    'categories': paper.categories,
                    'paper_type': paper.paper_type,
                    'analysis_status': paper.analysis_status,
                    'created_at': paper.created_at,
                    'updated_at': paper.updated_at
                }
                papers.append(PaperSchema.model_validate(paper_dict))
        
        # Convert to schema
        tag_schema = TagSchema(
            id=tag.id,
            name=tag.name,
            category=tag.category,
            description=tag.description,
            usage_count=usage_count,
            created_at=tag.created_at
        )
        
        return TagDetailResponse(
            tag=tag_schema,
            papers=papers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tag: {str(e)}")

@router.get("/by-category/{category}", response_model=TagListResponse)
async def get_tags_by_category(
    category: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
):
    """Get tags by category."""
    try:
        await db_manager.initialize()
        
        repo = TagRepository()
        paper_tag_repo = PaperTagRepository()
        
        # Get tags by category
        tags = await repo.get_by_category(category)
        
        # Apply pagination
        offset = (page - 1) * per_page
        paginated_tags = tags[offset:offset + per_page]
        
        # Get usage statistics
        tag_stats = await paper_tag_repo.get_tag_usage_stats()
        usage_map = {stat['name']: stat['usage_count'] for stat in tag_stats}
        
        # Convert to schemas
        tag_schemas = []
        for tag in paginated_tags:
            usage_count = usage_map.get(tag.name, 0)
            tag_schema = TagSchema(
                id=tag.id,
                name=tag.name,
                category=tag.category,
                description=tag.description,
                usage_count=usage_count,
                created_at=tag.created_at
            )
            tag_schemas.append(tag_schema)
        
        total = len(tags)
        total_pages = (total + per_page - 1) // per_page
        
        return TagListResponse(
            tags=tag_schemas,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tags by category: {str(e)}")

@router.get("/stats/overview")
async def get_tag_stats():
    """Get tag statistics."""
    try:
        await db_manager.initialize()
        
        repo = TagRepository()
        paper_tag_repo = PaperTagRepository()
        
        # Get all tags
        tags = await repo.list_all()
        
        # Get usage statistics
        tag_stats = await paper_tag_repo.get_tag_usage_stats()
        
        # Calculate statistics
        total_tags = len(tags)
        tags_by_category = {}
        total_usage = 0
        
        for tag in tags:
            category = tag.category.value
            if category not in tags_by_category:
                tags_by_category[category] = 0
            tags_by_category[category] += 1
        
        for stat in tag_stats:
            total_usage += stat['usage_count']
        
        avg_usage = total_usage / total_tags if total_tags > 0 else 0
        
        return {
            "success": True,
            "stats": {
                "total_tags": total_tags,
                "total_usage": total_usage,
                "avg_usage": avg_usage,
                "tags_by_category": tags_by_category,
                "most_used_tags": sorted(tag_stats, key=lambda x: x['usage_count'], reverse=True)[:10]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tag stats: {str(e)}")

@router.get("/cloud/data")
async def get_tag_cloud_data():
    """Get tag cloud data for visualization."""
    try:
        await db_manager.initialize()
        
        paper_tag_repo = PaperTagRepository()
        
        # Get usage statistics
        tag_stats = await paper_tag_repo.get_tag_usage_stats()
        
        # Format for tag cloud
        cloud_data = []
        for stat in tag_stats:
            cloud_data.append({
                "text": stat['name'],
                "value": stat['usage_count'],
                "category": stat['category']
            })
        
        return {
            "success": True,
            "data": cloud_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tag cloud data: {str(e)}") 