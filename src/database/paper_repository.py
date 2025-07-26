"""
Paper repository for database operations.
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from .repository import SearchableRepository
from .connection import db_manager
from ..models.paper import Paper, Author
from ..models.enums import PaperType, AnalysisStatus


class PaperRepository(SearchableRepository[Paper]):
    """Repository for paper operations."""
    
    def __init__(self):
        super().__init__('papers')
    
    def _from_row(self, row: Dict[str, Any]) -> Paper:
        """Convert database row to Paper instance."""
        # Parse authors JSON
        authors = []
        if row.get('authors'):
            authors_data = row['authors'] if isinstance(row['authors'], list) else json.loads(row['authors'])
            authors = [Author(**author_data) for author_data in authors_data]
        
        # Parse categories JSON
        categories = row.get('categories', [])
        if isinstance(categories, str):
            categories = json.loads(categories)
        
        return Paper.from_dict({
            **row,
            'authors': authors,
            'categories': categories
        })
    
    def _to_row(self, paper: Paper) -> Dict[str, Any]:
        """Convert Paper instance to database row."""
        row_data = paper.to_dict()
        
        # Convert authors to JSON - handle empty list
        if row_data['authors']:
            row_data['authors'] = json.dumps(row_data['authors'])
        else:
            row_data['authors'] = None
        
        # Convert categories to JSON - handle empty list
        if row_data['categories']:
            row_data['categories'] = json.dumps(row_data['categories'])
        else:
            row_data['categories'] = None
        
        # Set timestamps
        now = datetime.now()
        if not row_data.get('created_at'):
            row_data['created_at'] = now
        row_data['updated_at'] = now
        
        # Remove None values that shouldn't be updated
        filtered_data = {}
        for key, value in row_data.items():
            if value is not None or key in ['authors', 'categories']:  # Allow explicit None for JSON fields
                filtered_data[key] = value
        
        return filtered_data
    
    async def get_by_arxiv_id(self, arxiv_id: str) -> Optional[Paper]:
        """Get paper by ArXiv ID."""
        query = "SELECT * FROM papers WHERE arxiv_id = $1"
        
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, arxiv_id)
            return self._from_row(dict(row)) if row else None
    
    async def get_by_ids(self, paper_ids: List[UUID]) -> List[Paper]:
        """Get multiple papers by their IDs."""
        if not paper_ids:
            return []
        
        # Build query with placeholders for each ID
        placeholders = ','.join([f'${i+1}' for i in range(len(paper_ids))])
        query = f"SELECT * FROM papers WHERE id IN ({placeholders})"
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, *paper_ids)
            return [self._from_row(dict(row)) for row in rows]
    
    async def get_by_title(self, title: str) -> Optional[Paper]:
        """Get paper by exact title match."""
        query = "SELECT * FROM papers WHERE title = $1"
        
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, title)
            return self._from_row(dict(row)) if row else None
    
    async def find_similar_titles(self, title: str, threshold: float = 0.7) -> List[Paper]:
        """Find papers with similar titles using fuzzy matching."""
        query = """
            SELECT *, similarity(title, $1) as sim_score
            FROM papers
            WHERE similarity(title, $1) > $2
            ORDER BY sim_score DESC
            LIMIT 10
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, title, threshold)
            return [self._from_row(dict(row)) for row in rows]
    
    async def get_by_status(self, status: AnalysisStatus, limit: Optional[int] = None) -> List[Paper]:
        """Get papers by analysis status."""
        query = "SELECT * FROM papers WHERE analysis_status = $1 ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, status.value)
            return [self._from_row(dict(row)) for row in rows]
    
    async def get_by_type(self, paper_type: PaperType, limit: Optional[int] = None) -> List[Paper]:
        """Get papers by type."""
        query = "SELECT * FROM papers WHERE paper_type = $1 ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, paper_type.value)
            return [self._from_row(dict(row)) for row in rows]
    
    async def get_pending_analysis(self, limit: Optional[int] = None) -> List[Paper]:
        """Get papers pending analysis."""
        return await self.get_by_status(AnalysisStatus.PENDING, limit=limit)
    
    async def get_recent_papers(self, days: int = 30, limit: Optional[int] = None) -> List[Paper]:
        """Get recent papers from the last N days."""
        query = f"""
            SELECT * FROM papers 
            WHERE created_at >= NOW() - INTERVAL '{days} days'
            ORDER BY created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query)
            return [self._from_row(dict(row)) for row in rows]

    async def count_papers(self) -> int:
        """Get total count of papers."""
        query = "SELECT COUNT(*) FROM papers"
        
        async with db_manager.get_connection() as conn:
            result = await conn.fetchval(query)
            return result or 0

    async def get_analysis_status_counts(self) -> Dict[str, int]:
        """Get count of papers by analysis status."""
        query = """
            SELECT analysis_status, COUNT(*) as count
            FROM papers
            GROUP BY analysis_status
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query)
            return {row['analysis_status']: row['count'] for row in rows}
    
    async def update_analysis_status(self, paper_id: UUID, status: AnalysisStatus, confidence: Optional[float] = None) -> Paper:
        """Update paper analysis status."""
        updates = {'analysis_status': status.value}
        if confidence is not None:
            updates['analysis_confidence'] = confidence
        
        query = """
            UPDATE papers
            SET analysis_status = $2, analysis_confidence = $3, updated_at = NOW()
            WHERE id = $1
            RETURNING *
        """
        
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, paper_id, status.value, confidence)
            if not row:
                raise ValueError(f"Paper with id {paper_id} not found")
            return self._from_row(dict(row))
    
    async def update_paper(self, paper: Paper) -> Paper:
        """Update a paper with better error handling."""
        query = """
            UPDATE papers SET
                title = $2,
                abstract = $3,
                authors = $4::jsonb,
                publication_date = $5,
                categories = $6::jsonb,
                pdf_url = $7,
                full_text = $8,
                citation_count = $9,
                paper_type = $10,
                evidence_strength = $11,
                novelty_score = $12,
                practical_applicability = $13,
                analysis_status = $14,
                analysis_confidence = $15,
                extraction_version = $16,
                content_generated = $17,
                content_approved = $18,
                ingestion_source = $19,
                updated_at = NOW()
            WHERE id = $1
            RETURNING *
        """
        
        # Prepare values
        authors_json = json.dumps([author.__dict__ for author in paper.authors]) if paper.authors else None
        categories_json = json.dumps(paper.categories) if paper.categories else None
        
        values = [
            paper.id,
            paper.title,
            paper.abstract,
            authors_json,
            paper.publication_date,
            categories_json,
            paper.pdf_url,
            paper.full_text,
            paper.citation_count,
            paper.paper_type.value if paper.paper_type else None,
            paper.evidence_strength.value if paper.evidence_strength else None,
            paper.novelty_score,
            paper.practical_applicability.value if paper.practical_applicability else None,
            paper.analysis_status.value,
            paper.analysis_confidence,
            paper.extraction_version,
            paper.content_generated,
            paper.content_approved,
            paper.ingestion_source
        ]
        
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, *values)
            if not row:
                raise ValueError(f"Paper with id {paper.id} not found")
            return self._from_row(dict(row))
    
    async def search_by_author(self, author_name: str, limit: int = 50) -> List[Paper]:
        """Search papers by author name."""
        query = """
            SELECT * FROM papers
            WHERE authors::text ILIKE $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, f'%{author_name}%', limit)
            return [self._from_row(dict(row)) for row in rows]
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get paper statistics."""
        query = """
            SELECT
                COUNT(*) as total_papers,
                COUNT(*) FILTER (WHERE analysis_status = 'completed') as analyzed_papers,
                COUNT(*) FILTER (WHERE analysis_status = 'pending') as pending_papers,
                COUNT(*) FILTER (WHERE content_generated = true) as content_generated,
                AVG(novelty_score) FILTER (WHERE novelty_score IS NOT NULL) as avg_novelty_score,
                AVG(analysis_confidence) FILTER (WHERE analysis_confidence IS NOT NULL) as avg_confidence
            FROM papers
        """
        
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(query)
            return dict(row) if row else {}