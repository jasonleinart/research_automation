"""
Dashboard API endpoints
"""

from fastapi import APIRouter, HTTPException

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.database.insight_repository import InsightRepository
from src.database.tag_repository import TagRepository, PaperTagRepository
from src.web.models.schemas import DashboardResponse, DashboardStats, PaperSchema, InsightSchema, TagSchema

router = APIRouter()

@router.get("/overview", response_model=DashboardResponse)
async def get_dashboard_overview():
    """Get comprehensive dashboard overview."""
    try:
        await db_manager.initialize()

        paper_repo = PaperRepository()
        insight_repo = InsightRepository()
        tag_repo = TagRepository()
        paper_tag_repo = PaperTagRepository()

        # Get basic counts
        papers_count = await paper_repo.count_papers()
        insights_count = await insight_repo.count_insights()
        tags_count = await tag_repo.count_tags()

        # Get analysis status counts
        analysis_status_counts = await paper_repo.get_analysis_status_counts()
        completed_analyses = analysis_status_counts.get("completed", 0)
        manual_review_analyses = analysis_status_counts.get("manual_review", 0)
        failed_analyses = analysis_status_counts.get("failed", 0)

        # Get top tags by usage
        top_tags = await tag_repo.get_top_tags(limit=5)
        top_tags_schemas = []
        for tag in top_tags:
            # Convert Tag object to dict for schema validation
            tag_dict = {
                'id': tag.id,
                'name': tag.name,
                'category': tag.category,
                'description': tag.description,
                'parent_tag_id': tag.parent_tag_id,
                'usage_count': getattr(tag, 'usage_count', 0),  # Get usage_count if available
                'created_at': tag.created_at
            }
            top_tags_schemas.append(TagSchema.model_validate(tag_dict))

        # Get recent papers
        recent_papers = await paper_repo.get_recent_papers(limit=5)
        recent_papers_schemas = []
        for paper in recent_papers:
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
                    
                    authors.append({'name': author_name})
            
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
            recent_papers_schemas.append(PaperSchema.model_validate(paper_dict))

        # Get recent insights
        recent_insights = await insight_repo.get_recent_insights(limit=5)
        recent_insights_schemas = []
        for insight in recent_insights:
            # Convert content dict to string if needed
            content_str = insight.content
            if isinstance(content_str, dict):
                content_str = str(content_str)
            elif content_str is None:
                content_str = ""
            
            insight_dict = {
                'id': insight.id,
                'paper_id': insight.paper_id,
                'insight_type': insight.insight_type,
                'title': insight.title,
                'description': insight.description,
                'confidence': insight.confidence,
                'extraction_method': insight.extraction_method,
                'content': content_str,
                'created_at': insight.created_at
            }
            recent_insights_schemas.append(InsightSchema.model_validate(insight_dict))

        # Get papers by status for chart
        papers_by_status = analysis_status_counts

        # Get insights by type for chart
        insights_by_type = await insight_repo.get_insights_by_type()

        stats = DashboardStats(
            total_papers=papers_count,
            total_insights=insights_count,
            total_tags=tags_count,
            completed_analyses=completed_analyses,
            manual_review_analyses=manual_review_analyses,
            failed_analyses=failed_analyses,
            analysis_status_counts=analysis_status_counts,
            insights_by_type=insights_by_type,
            top_tags=top_tags_schemas,
            recent_papers=recent_papers_schemas,
            recent_insights=recent_insights_schemas
        )

        return DashboardResponse(stats=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard overview: {e}")

@router.get("/stats/summary")
async def get_dashboard_summary():
    """Get quick summary statistics."""
    try:
        await db_manager.initialize()

        paper_repo = PaperRepository()
        insight_repo = InsightRepository()
        tag_repo = TagRepository()

        # Get basic counts
        papers = await paper_repo.list_all()
        insights = await insight_repo.list_all()
        tags = await tag_repo.list_all()

        # Calculate key metrics
        total_papers = len(papers)
        total_insights = len(insights)
        total_tags = len(tags)

        # Papers by analysis status
        completed_papers = len([p for p in papers if p.analysis_status.value == "completed"])
        pending_papers = len([p for p in papers if p.analysis_status.value == "pending"])

        # Insights by confidence
        high_confidence = len([i for i in insights if i.confidence and i.confidence >= 0.8])
        medium_confidence = len([i for i in insights if i.confidence and 0.6 <= i.confidence < 0.8])
        low_confidence = len([i for i in insights if i.confidence and i.confidence < 0.6])

        # Average insights per paper
        avg_insights_per_paper = total_insights / total_papers if total_papers > 0 else 0

        return {
            "success": True,
            "summary": {
                "papers": {
                    "total": total_papers,
                    "completed": completed_papers,
                    "pending": pending_papers,
                    "completion_rate": (completed_papers / total_papers * 100) if total_papers > 0 else 0
                },
                "insights": {
                    "total": total_insights,
                    "high_confidence": high_confidence,
                    "medium_confidence": medium_confidence,
                    "low_confidence": low_confidence,
                    "avg_per_paper": avg_insights_per_paper
                },
                "tags": {
                    "total": total_tags
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching summary: {str(e)}")

@router.get("/activity/recent")
async def get_recent_activity():
    """Get recent activity in the system."""
    try:
        await db_manager.initialize()

        paper_repo = PaperRepository()
        insight_repo = InsightRepository()

        # Get recent papers
        papers = await paper_repo.list_all()
        recent_papers = sorted(papers, key=lambda p: p.created_at, reverse=True)[:10]

        # Get recent insights
        insights = await insight_repo.list_all()
        recent_insights = sorted(insights, key=lambda i: i.created_at, reverse=True)[:10]

        # Format activity
        activity = []

        for paper in recent_papers:
            activity.append({
                "type": "paper_added",
                "id": str(paper.id),
                "title": paper.title,
                "timestamp": paper.created_at,
                "status": paper.analysis_status.value
            })

        for insight in recent_insights:
            activity.append({
                "type": "insight_extracted",
                "id": str(insight.id),
                "title": insight.title,
                "timestamp": insight.created_at,
                "confidence": insight.confidence
            })

        # Sort by timestamp
        activity.sort(key=lambda x: x["timestamp"], reverse=True)

        return {
            "success": True,
            "activity": activity[:20]  # Return top 20 most recent activities
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recent activity: {str(e)}")

@router.get("/trends/insights")
async def get_insight_trends():
    """Get insight extraction trends."""
    try:
        await db_manager.initialize()

        insight_repo = InsightRepository()
        insights = await insight_repo.list_all()

        # Group insights by month
        trends = {}
        for insight in insights:
            month_key = insight.created_at.strftime("%Y-%m")
            if month_key not in trends:
                trends[month_key] = {
                    "total": 0,
                    "by_type": {},
                    "avg_confidence": 0.0,
                    "confidences": []
                }

            trends[month_key]["total"] += 1

            insight_type = insight.insight_type.value
            trends[month_key]["by_type"][insight_type] = trends[month_key]["by_type"].get(insight_type, 0) + 1

            if insight.confidence:
                trends[month_key]["confidences"].append(insight.confidence)

        # Calculate average confidence for each month
        for month_data in trends.values():
            if month_data["confidences"]:
                month_data["avg_confidence"] = sum(month_data["confidences"]) / len(month_data["confidences"])
            del month_data["confidences"]  # Remove raw data

        return {
            "success": True,
            "trends": trends
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching insight trends: {str(e)}") 