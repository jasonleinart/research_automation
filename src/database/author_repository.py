"""
Repository for author-related database operations.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from ..database.connection import db_manager
from ..models.author import Author, PaperAuthor

logger = logging.getLogger(__name__)


class AuthorRepository:
    """Repository for author operations."""
    
    def __init__(self):
        self.db_manager = db_manager
    
    async def create(self, author: Author) -> Author:
        """Create a new author."""
        query = """
            INSERT INTO authors (id, name, affiliation, email, orcid, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """
        
        async with self.db_manager.get_connection() as conn:
            row = await conn.fetchrow(
                query,
                author.id,
                author.name,
                author.affiliation,
                author.email,
                author.orcid,
                author.created_at,
                author.updated_at
            )
            return Author.from_dict(dict(row))
    
    async def get_by_id(self, author_id: UUID) -> Optional[Author]:
        """Get author by ID."""
        query = "SELECT * FROM authors WHERE id = $1"
        
        async with self.db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, author_id)
            return Author.from_dict(dict(row)) if row else None
    
    async def get_by_name(self, name: str) -> Optional[Author]:
        """Get author by name."""
        query = "SELECT * FROM authors WHERE name = $1"
        
        async with self.db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, name)
            return Author.from_dict(dict(row)) if row else None
    
    async def get_or_create(self, name: str, affiliation: Optional[str] = None, 
                           email: Optional[str] = None, orcid: Optional[str] = None) -> Author:
        """Get existing author or create new one."""
        # Try to find existing author
        existing = await self.get_by_name(name)
        if existing:
            return existing
        
        # Create new author
        author = Author(
            name=name,
            affiliation=affiliation,
            email=email,
            orcid=orcid
        )
        return await self.create(author)
    
    async def get_by_ids(self, author_ids: List[UUID]) -> List[Author]:
        """Get multiple authors by their IDs."""
        if not author_ids:
            return []
        
        placeholders = ','.join([f'${i+1}' for i in range(len(author_ids))])
        query = f"SELECT * FROM authors WHERE id IN ({placeholders})"
        
        async with self.db_manager.get_connection() as conn:
            rows = await conn.fetch(query, *author_ids)
            return [Author.from_dict(dict(row)) for row in rows]
    
    async def list_all(self) -> List[Author]:
        """Get all authors."""
        query = "SELECT * FROM authors ORDER BY name"
        
        async with self.db_manager.get_connection() as conn:
            rows = await conn.fetch(query)
            return [Author.from_dict(dict(row)) for row in rows]
    
    async def search_by_name(self, name_pattern: str) -> List[Author]:
        """Search authors by name pattern."""
        query = "SELECT * FROM authors WHERE name ILIKE $1 ORDER BY name"
        
        async with self.db_manager.get_connection() as conn:
            rows = await conn.fetch(query, f'%{name_pattern}%')
            return [Author.from_dict(dict(row)) for row in rows]
    
    async def get_paper_authors(self, paper_id: UUID) -> List[Author]:
        """Get all authors for a specific paper."""
        query = """
            SELECT a.* 
            FROM authors a
            JOIN paper_authors pa ON a.id = pa.author_id
            WHERE pa.paper_id = $1
            ORDER BY pa.author_order
        """
        
        async with self.db_manager.get_connection() as conn:
            rows = await conn.fetch(query, paper_id)
            return [Author.from_dict(dict(row)) for row in rows]
    
    async def get_author_papers(self, author_id: UUID) -> List[UUID]:
        """Get all paper IDs for a specific author."""
        query = """
            SELECT paper_id 
            FROM paper_authors 
            WHERE author_id = $1
            ORDER BY created_at
        """
        
        async with self.db_manager.get_connection() as conn:
            rows = await conn.fetch(query, author_id)
            return [row['paper_id'] for row in rows]
    
    async def create_paper_author_relationship(self, paper_id: UUID, author_id: UUID, 
                                             author_order: int) -> PaperAuthor:
        """Create a paper-author relationship."""
        query = """
            INSERT INTO paper_authors (paper_id, author_id, author_order, created_at)
            VALUES ($1, $2, $3, NOW())
            RETURNING *
        """
        
        async with self.db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, paper_id, author_id, author_order)
            return PaperAuthor.from_dict(dict(row))
    
    async def delete_paper_author_relationships(self, paper_id: UUID):
        """Delete all author relationships for a paper."""
        query = "DELETE FROM paper_authors WHERE paper_id = $1"
        
        async with self.db_manager.get_connection() as conn:
            await conn.execute(query, paper_id)
    
    async def get_author_statistics(self) -> Dict[str, Any]:
        """Get author statistics."""
        query = """
            SELECT 
                COUNT(DISTINCT a.id) as total_authors,
                COUNT(DISTINCT pa.paper_id) as total_papers_with_authors,
                AVG(authors_per_paper.author_count) as avg_authors_per_paper
            FROM authors a
            LEFT JOIN paper_authors pa ON a.id = pa.author_id
            LEFT JOIN (
                SELECT paper_id, COUNT(*) as author_count
                FROM paper_authors
                GROUP BY paper_id
            ) authors_per_paper ON pa.paper_id = authors_per_paper.paper_id
        """
        
        async with self.db_manager.get_connection() as conn:
            row = await conn.fetchrow(query)
            return dict(row) if row else {}
    
    async def get_most_prolific_authors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get authors with the most papers."""
        query = """
            SELECT 
                a.id,
                a.name,
                COUNT(pa.paper_id) as paper_count
            FROM authors a
            JOIN paper_authors pa ON a.id = pa.author_id
            GROUP BY a.id, a.name
            ORDER BY paper_count DESC
            LIMIT $1
        """
        
        async with self.db_manager.get_connection() as conn:
            rows = await conn.fetch(query, limit)
            return [dict(row) for row in rows] 