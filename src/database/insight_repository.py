"""
Repository for managing insights in the database.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from .repository import BaseRepository
from .connection import db_manager
from ..models.insight import Insight
from ..models.enums import InsightType

logger = logging.getLogger(__name__)


class InsightRepository(BaseRepository[Insight]):
    """Repository for insight database operations."""
    
    def __init__(self):
        super().__init__("insights")
    
    async def get_by_paper_id(self, paper_id: UUID) -> List[Insight]:
        """Get all insights for a specific paper."""
        try:
            query = """
                SELECT id, paper_id, insight_type, title, description, content, 
                       confidence, extraction_method, created_at
                FROM insights 
                WHERE paper_id = $1
                ORDER BY created_at DESC
            """
            
            async with db_manager.get_connection() as conn:
                rows = await conn.fetch(query, paper_id)
            return [self._row_to_model(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get insights for paper {paper_id}: {e}")
            return []
    
    async def get_by_insight_type(self, insight_type: InsightType) -> List[Insight]:
        """Get all insights of a specific type."""
        try:
            query = """
                SELECT id, paper_id, insight_type, title, description, content, 
                       confidence, extraction_method, created_at
                FROM insights 
                WHERE insight_type = $1
                ORDER BY confidence DESC, created_at DESC
            """
            
            async with db_manager.get_connection() as conn:
                rows = await conn.fetch(query, insight_type.value)
            return [self._row_to_model(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get insights by type {insight_type}: {e}")
            return []
    
    async def get_high_confidence_insights(self, min_confidence: float = 0.8) -> List[Insight]:
        """Get insights with confidence above threshold."""
        try:
            query = """
                SELECT id, paper_id, insight_type, title, description, content, 
                       confidence, extraction_method, created_at
                FROM insights 
                WHERE confidence >= $1
                ORDER BY confidence DESC, created_at DESC
            """
            
            async with db_manager.get_connection() as conn:
                rows = await conn.fetch(query, min_confidence)
            return [self._row_to_model(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get high confidence insights: {e}")
            return []
    
    async def get_insights_with_papers(self) -> List[Dict[str, Any]]:
        """Get insights joined with paper information."""
        try:
            query = """
                SELECT 
                    i.id, i.paper_id, i.insight_type, i.title, i.description, 
                    i.content, i.confidence, i.extraction_method, 
                    i.created_at,
                    p.title as paper_title, p.paper_type, p.authors, p.arxiv_id
                FROM insights i
                JOIN papers p ON i.paper_id = p.id
                ORDER BY i.confidence DESC, i.created_at DESC
            """
            
            async with db_manager.get_connection() as conn:
                rows = await conn.fetch(query)
            results = []
            
            for row in rows:
                insight = self._row_to_model(row)
                paper_info = {
                    "title": row["paper_title"],
                    "paper_type": row["paper_type"],
                    "authors": row["authors"],
                    "arxiv_id": row["arxiv_id"]
                }
                
                results.append({
                    "insight": insight,
                    "paper": paper_info
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get insights with papers: {e}")
            return []
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get insight statistics."""
        try:
            stats_query = """
                SELECT 
                    COUNT(*) as total_insights,
                    AVG(confidence) as avg_confidence,
                    COUNT(DISTINCT paper_id) as papers_with_insights,
                    COUNT(DISTINCT insight_type) as unique_types
                FROM insights
            """
            
            type_query = """
                SELECT insight_type, COUNT(*) as count
                FROM insights
                GROUP BY insight_type
                ORDER BY count DESC
            """
            
            confidence_query = """
                SELECT 
                    COUNT(CASE WHEN confidence >= 0.8 THEN 1 END) as high_confidence,
                    COUNT(CASE WHEN confidence >= 0.6 AND confidence < 0.8 THEN 1 END) as medium_confidence,
                    COUNT(CASE WHEN confidence < 0.6 THEN 1 END) as low_confidence
                FROM insights
            """
            
            async with db_manager.get_connection() as conn:
                stats_row = await conn.fetchrow(stats_query)
                type_rows = await conn.fetch(type_query)
                confidence_row = await conn.fetchrow(confidence_query)
            
            return {
                "total_insights": stats_row["total_insights"],
                "avg_confidence": float(stats_row["avg_confidence"]) if stats_row["avg_confidence"] else 0,
                "papers_with_insights": stats_row["papers_with_insights"],
                "unique_types": stats_row["unique_types"],
                "type_distribution": {row["insight_type"]: row["count"] for row in type_rows},
                "confidence_distribution": {
                    "high": confidence_row["high_confidence"],
                    "medium": confidence_row["medium_confidence"],
                    "low": confidence_row["low_confidence"]
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get insight statistics: {e}")
            return {}
    
    def _from_row(self, row) -> Insight:
        """Convert database row to Insight model."""
        # Parse JSON content
        content = {}
        if row["content"]:
            try:
                content = json.loads(row["content"]) if isinstance(row["content"], str) else row["content"]
            except json.JSONDecodeError:
                content = {}
        
        return Insight(
            id=row["id"],
            paper_id=row["paper_id"],
            insight_type=InsightType(row["insight_type"]),
            title=row["title"],
            description=row["description"],
            content=content,
            confidence=float(row["confidence"]),
            extraction_method=row["extraction_method"],
            created_at=row["created_at"]
        )
    
    def _to_row(self, insight: Insight) -> Dict[str, Any]:
        """Convert Insight model to dictionary for database operations."""
        return {
            "id": insight.id,
            "paper_id": insight.paper_id,
            "insight_type": insight.insight_type.value,
            "title": insight.title,
            "description": insight.description,
            "content": json.dumps(insight.content) if insight.content else None,
            "confidence": insight.confidence,
            "extraction_method": insight.extraction_method,
            "created_at": insight.created_at or datetime.now()
        }
    
    def _row_to_model(self, row) -> Insight:
        """Convert database row to Insight model."""
        return self._from_row(row)
    
    def _model_to_dict(self, insight: Insight) -> Dict[str, Any]:
        """Convert Insight model to dictionary for database operations."""
        return self._to_row(insight)