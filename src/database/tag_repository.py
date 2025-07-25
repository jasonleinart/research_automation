"""
Tag repository for database operations.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from .repository import BaseRepository
from .connection import db_manager
from ..models.tag import Tag, PaperTag
from ..models.enums import TagCategory, TagSource


class TagRepository(BaseRepository[Tag]):
    """Repository for tag operations."""
    
    def __init__(self):
        super().__init__('tags')
    
    def _from_row(self, row: Dict[str, Any]) -> Tag:
        """Convert database row to Tag instance."""
        return Tag.from_dict(row)
    
    def _to_row(self, tag: Tag) -> Dict[str, Any]:
        """Convert Tag instance to database row."""
        row_data = tag.to_dict()
        
        # Set timestamp
        if not row_data.get('created_at'):
            row_data['created_at'] = datetime.now()
        
        return row_data
    
    async def get_by_name(self, name: str) -> Optional[Tag]:
        """Get tag by name."""
        query = "SELECT * FROM tags WHERE name = $1"
        
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, name)
            return self._from_row(dict(row)) if row else None
    
    async def get_by_category(self, category: TagCategory) -> List[Tag]:
        """Get tags by category."""
        query = "SELECT * FROM tags WHERE category = $1"
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, category.value)
            return [self._from_row(dict(row)) for row in rows]
    
    async def get_root_tags(self) -> List[Tag]:
        """Get root-level tags (no parent)."""
        query = "SELECT * FROM tags WHERE parent_tag_id IS NULL"
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query)
            return [self._from_row(dict(row)) for row in rows]
    
    async def get_children(self, parent_id: UUID) -> List[Tag]:
        """Get child tags of a parent."""
        query = "SELECT * FROM tags WHERE parent_tag_id = $1"
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, parent_id)
            return [self._from_row(dict(row)) for row in rows]
    
    async def get_tag_hierarchy(self, root_tag_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get hierarchical tag structure."""
        if root_tag_id:
            query = """
                WITH RECURSIVE tag_tree AS (
                    SELECT id, name, category, description, parent_tag_id, 0 as level
                    FROM tags WHERE id = $1
                    UNION ALL
                    SELECT t.id, t.name, t.category, t.description, t.parent_tag_id, tt.level + 1
                    FROM tags t
                    JOIN tag_tree tt ON t.parent_tag_id = tt.id
                )
                SELECT * FROM tag_tree ORDER BY level, name
            """
            
            async with db_manager.get_connection() as conn:
                rows = await conn.fetch(query, root_tag_id)
        else:
            # Get all tags
            query = "SELECT * FROM tags ORDER BY parent_tag_id NULLS FIRST, name"
            
            async with db_manager.get_connection() as conn:
                rows = await conn.fetch(query)
        
        # Build hierarchy
        tags_by_id = {row['id']: dict(row) for row in rows}
        hierarchy = {}
        
        for tag_data in tags_by_id.values():
            if tag_data['parent_tag_id'] is None:
                hierarchy[tag_data['id']] = {
                    'tag': tag_data,
                    'children': {}
                }
        
        # Add children
        for tag_data in tags_by_id.values():
            if tag_data['parent_tag_id'] and tag_data['parent_tag_id'] in hierarchy:
                parent = hierarchy[tag_data['parent_tag_id']]
                parent['children'][tag_data['id']] = {
                    'tag': tag_data,
                    'children': {}
                }
        
        return hierarchy


class PaperTagRepository(BaseRepository[PaperTag]):
    """Repository for paper-tag associations."""
    
    def __init__(self):
        super().__init__('paper_tags')
    
    def _from_row(self, row: Dict[str, Any]) -> PaperTag:
        """Convert database row to PaperTag instance."""
        return PaperTag.from_dict(row)
    
    def _to_row(self, paper_tag: PaperTag) -> Dict[str, Any]:
        """Convert PaperTag instance to database row."""
        row_data = paper_tag.to_dict()
        
        # Set timestamp
        if not row_data.get('created_at'):
            row_data['created_at'] = datetime.now()
        
        return row_data
    
    async def get_by_paper(self, paper_id: UUID) -> List[PaperTag]:
        """Get all tags for a paper."""
        query = "SELECT * FROM paper_tags WHERE paper_id = $1"
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, paper_id)
            return [self._from_row(dict(row)) for row in rows]
    
    async def get_by_tag(self, tag_id: UUID) -> List[PaperTag]:
        """Get all papers with a specific tag."""
        query = "SELECT * FROM paper_tags WHERE tag_id = $1"
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, tag_id)
            return [self._from_row(dict(row)) for row in rows]
    
    async def add_tag_to_paper(self, paper_id: UUID, tag_id: UUID, confidence: Optional[float] = None, source: TagSource = TagSource.AUTOMATIC) -> PaperTag:
        """Add a tag to a paper."""
        paper_tag = PaperTag(
            paper_id=paper_id,
            tag_id=tag_id,
            confidence=confidence,
            source=source
        )
        return await self.create(paper_tag)
    
    async def remove_tag_from_paper(self, paper_id: UUID, tag_id: UUID) -> bool:
        """Remove a tag from a paper."""
        query = "DELETE FROM paper_tags WHERE paper_id = $1 AND tag_id = $2"
        
        async with db_manager.get_connection() as conn:
            result = await conn.execute(query, paper_id, tag_id)
            return result.split()[-1] == '1'
    
    async def get_paper_tags_with_details(self, paper_id: UUID) -> List[Dict[str, Any]]:
        """Get paper tags with tag details."""
        query = """
            SELECT pt.*, t.name, t.category, t.description
            FROM paper_tags pt
            JOIN tags t ON pt.tag_id = t.id
            WHERE pt.paper_id = $1
            ORDER BY pt.confidence DESC NULLS LAST, t.name
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, paper_id)
            return [dict(row) for row in rows]
    
    async def get_tag_usage_stats(self) -> List[Dict[str, Any]]:
        """Get statistics on tag usage."""
        query = """
            SELECT 
                t.id,
                t.name,
                t.category,
                COUNT(pt.paper_id) as usage_count,
                AVG(pt.confidence) as avg_confidence
            FROM tags t
            LEFT JOIN paper_tags pt ON t.id = pt.tag_id
            GROUP BY t.id, t.name, t.category
            ORDER BY usage_count DESC, t.name
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]