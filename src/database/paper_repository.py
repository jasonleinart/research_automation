"""
Paper repository for database operations.
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from .repository import SearchableRepository
from .connection import db_manager
from ..models.paper import Paper
from ..models.author import Author
from .author_repository import AuthorRepository, Author
from ..models.enums import PaperType, AnalysisStatus, EvidenceStrength, PracticalApplicability


class PaperRepository(SearchableRepository[Paper]):
    """Repository for paper operations."""
    
    def __init__(self):
        super().__init__('papers')
        self.author_repo = AuthorRepository()
    
    def _from_row(self, row: Dict[str, Any]) -> Paper:
        """Convert database row to Paper instance."""
        # Parse categories JSON
        categories = row.get('categories', [])
        if isinstance(categories, str):
            categories = json.loads(categories)
        
        paper = Paper.from_dict({
            **row,
            'categories': categories
        })
        
        # Note: Authors will be loaded separately via get_paper_authors method
        return paper
    
    def _to_row(self, paper: Paper) -> Dict[str, Any]:
        """Convert Paper instance to database row."""
        row_data = paper.to_dict()
        
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
            if value is not None or key in ['categories']:  # Allow explicit None for JSON fields
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
                publication_date = $4,
                categories = $5::jsonb,
                pdf_url = $6,
                full_text = $7,
                citation_count = $8,
                paper_type = $9,
                evidence_strength = $10,
                novelty_score = $11,
                practical_applicability = $12,
                analysis_status = $13,
                analysis_confidence = $14,
                extraction_version = $15,
                content_generated = $16,
                content_approved = $17,
                ingestion_source = $18,
                updated_at = NOW()
            WHERE id = $1
            RETURNING *
        """
        
        # Prepare values - authors are now stored in separate table
        # Handle categories like _to_row method
        if paper.categories:
            categories_json = json.dumps(paper.categories)
        else:
            categories_json = None
        
        values = [
            paper.id,
            paper.title,
            paper.abstract,
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
    
    async def update_classification(self, paper_id: UUID, paper_type: PaperType, evidence_strength: EvidenceStrength, 
                                   practical_applicability: PracticalApplicability, analysis_status: AnalysisStatus, 
                                   analysis_confidence: float) -> Paper:
        """Update paper classification fields only."""
        query = """
            UPDATE papers
            SET paper_type = $2, 
                evidence_strength = $3, 
                practical_applicability = $4, 
                analysis_status = $5, 
                analysis_confidence = $6, 
                updated_at = NOW()
            WHERE id = $1
            RETURNING *
        """
        
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, paper_id, paper_type.value, evidence_strength.value, 
                                    practical_applicability.value, analysis_status.value, analysis_confidence)
            if not row:
                raise ValueError(f"Paper with id {paper_id} not found")
            return self._from_row(dict(row))
    
    async def get_paper_with_authors(self, paper_id: UUID) -> Optional[Paper]:
        """Get paper with authors loaded."""
        paper = await self.get_by_id(paper_id)
        if paper:
            authors = await self.author_repo.get_paper_authors(paper_id)
            paper._authors = authors
            paper._author_names = [author.name for author in authors]
        return paper
    
    async def get_papers_with_authors(self, paper_ids: List[UUID]) -> List[Paper]:
        """Get multiple papers with authors loaded."""
        papers = await self.get_by_ids(paper_ids)
        
        # Load authors for all papers
        for paper in papers:
            authors = await self.author_repo.get_paper_authors(paper.id)
            paper._authors = authors
            paper._author_names = [author.name for author in authors]
        
        return papers
    
    async def search_by_author(self, author_name: str, limit: int = 50) -> List[Paper]:
        """Search papers by author name using the new relational system."""
        query = """
            SELECT DISTINCT p.*
            FROM papers p
            JOIN paper_authors pa ON p.id = pa.paper_id
            JOIN authors a ON pa.author_id = a.id
            WHERE a.name ILIKE $1
            ORDER BY p.created_at DESC
            LIMIT $2
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, f'%{author_name}%', limit)
            papers = [self._from_row(dict(row)) for row in rows]
            
            # Load authors for all papers
            return papers
    
    async def search_by_category(self, category: str, limit: int = 50) -> List[Paper]:
        """Search papers by category."""
        query = """
            SELECT * FROM papers 
            WHERE categories::text ILIKE $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, f'%{category}%', limit)
            return [self._from_row(dict(row)) for row in rows]
    
    async def get_by_paper_type(self, paper_type, limit: int = 50) -> List[Paper]:
        """Get papers by paper type."""
        query = """
            SELECT * FROM papers 
            WHERE paper_type = $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, paper_type.value if hasattr(paper_type, 'value') else str(paper_type), limit)
            return [self._from_row(dict(row)) for row in rows]
    
    # === RELATIONSHIP QUERY METHODS ===
    
    async def find_papers_by_same_authors(self, paper_id: UUID, limit: int = 10) -> List[Paper]:
        """Find papers that share authors with the given paper."""
        query = """
            WITH target_paper_authors AS (
                SELECT jsonb_array_elements_text(
                    CASE 
                        WHEN jsonb_typeof(authors) = 'array' THEN authors
                        ELSE '[]'::jsonb
                    END
                ) as author_name
                FROM papers 
                WHERE id = $1
            )
            SELECT DISTINCT p.*, 
                   (SELECT COUNT(*) FROM target_paper_authors tpa 
                    WHERE tpa.author_name = ANY(
                        SELECT jsonb_array_elements_text(
                            CASE 
                                WHEN jsonb_typeof(p.authors) = 'array' THEN p.authors
                                ELSE '[]'::jsonb
                            END
                        )
                    )) as shared_author_count
            FROM papers p
            WHERE p.id != $1
            AND EXISTS (
                SELECT 1 FROM target_paper_authors tpa
                WHERE tpa.author_name = ANY(
                    SELECT jsonb_array_elements_text(
                        CASE 
                            WHEN jsonb_typeof(p.authors) = 'array' THEN p.authors
                            ELSE '[]'::jsonb
                        END
                    )
                )
            )
            ORDER BY shared_author_count DESC, p.created_at DESC
            LIMIT $2
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, paper_id, limit)
            papers = [self._from_row(dict(row)) for row in rows]
            
            # Add shared author count as metadata
            for i, row in enumerate(rows):
                papers[i]._shared_author_count = row['shared_author_count']
            
            return papers
    
    async def find_papers_with_shared_tags(self, paper_id: UUID, limit: int = 10) -> List[Paper]:
        """Find papers that share tags with the given paper."""
        query = """
            WITH paper_tags AS (
                SELECT tag_id 
                FROM paper_tags 
                WHERE paper_id = $1
            )
            SELECT DISTINCT p.*, COUNT(pt.tag_id) as shared_tag_count
            FROM papers p
            JOIN paper_tags pt ON p.id = pt.paper_id
            WHERE pt.tag_id IN (SELECT tag_id FROM paper_tags)
            AND p.id != $1
            GROUP BY p.id
            ORDER BY shared_tag_count DESC, p.created_at DESC
            LIMIT $2
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, paper_id, limit)
            papers = [self._from_row(dict(row)) for row in rows]
            
            # Add shared tag count as metadata
            for i, row in enumerate(rows):
                papers[i]._shared_tag_count = row['shared_tag_count']
            
            return papers
    
    async def find_papers_in_same_categories(self, paper_id: UUID, limit: int = 10) -> List[Paper]:
        """Find papers in the same categories as the given paper."""
        query = """
            WITH target_paper_categories AS (
                SELECT jsonb_array_elements_text(
                    CASE 
                        WHEN jsonb_typeof(categories) = 'array' THEN categories
                        ELSE '[]'::jsonb
                    END
                ) as category
                FROM papers 
                WHERE id = $1
            )
            SELECT DISTINCT p.*, 
                   (SELECT COUNT(*) FROM target_paper_categories tpc 
                    WHERE tpc.category = ANY(
                        SELECT jsonb_array_elements_text(
                            CASE 
                                WHEN jsonb_typeof(p.categories) = 'array' THEN p.categories
                                ELSE '[]'::jsonb
                            END
                        )
                    )) as shared_category_count
            FROM papers p
            WHERE p.id != $1
            AND EXISTS (
                SELECT 1 FROM target_paper_categories tpc
                WHERE tpc.category = ANY(
                    SELECT jsonb_array_elements_text(
                        CASE 
                            WHEN jsonb_typeof(p.categories) = 'array' THEN p.categories
                            ELSE '[]'::jsonb
                        END
                    )
                )
            )
            ORDER BY shared_category_count DESC, p.created_at DESC
            LIMIT $2
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, paper_id, limit)
            papers = [self._from_row(dict(row)) for row in rows]
            
            # Add shared category count as metadata
            for i, row in enumerate(rows):
                papers[i]._shared_category_count = row['shared_category_count'] or 0
            
            return papers
    
    async def find_papers_from_same_time_period(
        self, 
        paper_id: UUID, 
        days_range: int = 365, 
        limit: int = 10
    ) -> List[Paper]:
        """Find papers published within the same time period."""
        query = """
            WITH target_paper AS (
                SELECT publication_date 
                FROM papers 
                WHERE id = $1
            )
            SELECT p.*
            FROM papers p, target_paper tp
            WHERE p.id != $1
            AND p.publication_date IS NOT NULL
            AND tp.publication_date IS NOT NULL
            AND ABS(EXTRACT(EPOCH FROM (p.publication_date - tp.publication_date))) <= $2 * 86400
            ORDER BY ABS(EXTRACT(EPOCH FROM (p.publication_date - tp.publication_date))), p.created_at DESC
            LIMIT $3
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, paper_id, days_range, limit)
            papers = [self._from_row(dict(row)) for row in rows]
            
            return papers
    
    async def get_paper_relationships(self, paper_id: UUID) -> Dict[str, List[Paper]]:
        """Get all types of related papers for a given paper."""
        relationships = {}
        
        # Get papers by same authors
        relationships['same_authors'] = await self.find_papers_by_same_authors(paper_id, limit=5)
        
        # Get papers with shared tags
        relationships['shared_tags'] = await self.find_papers_with_shared_tags(paper_id, limit=5)
        
        # Get papers in same categories
        relationships['same_categories'] = await self.find_papers_in_same_categories(paper_id, limit=5)
        
        # Get papers from same time period (within 1 year)
        relationships['same_time_period'] = await self.find_papers_from_same_time_period(paper_id, days_range=365, limit=5)
        
        return relationships
    
    async def get_relationship_summary(self, paper_id: UUID) -> Dict[str, int]:
        """Get a summary count of relationships for a paper."""
        relationships = await self.get_paper_relationships(paper_id)
        
        return {
            'same_authors': len(relationships['same_authors']),
            'shared_tags': len(relationships['shared_tags']),
            'same_categories': len(relationships['same_categories']),
            'same_time_period': len(relationships['same_time_period']),
            'total_related': sum(len(papers) for papers in relationships.values())
        }
    
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
    
    async def get_paper_type_counts(self) -> Dict[str, int]:
        """Get count of papers by type."""
        query = """
            SELECT 
                paper_type,
                COUNT(*) as count
            FROM papers 
            WHERE paper_type IS NOT NULL
            GROUP BY paper_type
            ORDER BY count DESC
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query)
            return {row['paper_type']: row['count'] for row in rows}