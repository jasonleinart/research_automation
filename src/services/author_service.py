"""
Service for managing authors and paper-author relationships.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from ..database.author_repository import AuthorRepository
from ..database.paper_repository import PaperRepository
from ..models.author import Author, PaperAuthor
from ..models.paper import Paper

logger = logging.getLogger(__name__)


class AuthorService:
    """Service for author operations."""
    
    def __init__(self):
        self.author_repo = AuthorRepository()
        self.paper_repo = PaperRepository()
    
    async def create_or_get_authors_from_names(self, author_names: List[str]) -> List[Author]:
        """Create or get authors from a list of names."""
        authors = []
        
        for name in author_names:
            if not name or not name.strip():
                continue
                
            # Clean up the name
            clean_name = name.strip()
            
            # Get or create author
            author = await self.author_repo.get_or_create(clean_name)
            authors.append(author)
        
        return authors
    
    async def assign_authors_to_paper(self, paper_id: UUID, author_names: List[str]) -> List[PaperAuthor]:
        """Assign authors to a paper in the correct order."""
        # First, remove any existing author relationships for this paper
        await self.author_repo.delete_paper_author_relationships(paper_id)
        
        # Create or get authors
        authors = await self.create_or_get_authors_from_names(author_names)
        
        # Create paper-author relationships
        paper_authors = []
        for order, author in enumerate(authors, 1):
            paper_author = await self.author_repo.create_paper_author_relationship(
                paper_id=paper_id,
                author_id=author.id,
                author_order=order
            )
            paper_authors.append(paper_author)
        
        logger.info(f"Assigned {len(authors)} authors to paper {paper_id}")
        return paper_authors
    
    async def get_paper_with_authors(self, paper_id: UUID) -> Optional[Paper]:
        """Get a paper with its authors loaded."""
        paper = await self.paper_repo.get_by_id(paper_id)
        if not paper:
            return None
        
        # Load authors
        authors = await self.author_repo.get_paper_authors(paper_id)
        
        # Set author properties on paper
        paper._authors = authors
        paper._author_names = [author.name for author in authors]
        
        return paper
    
    async def get_papers_with_authors(self, paper_ids: List[UUID]) -> List[Paper]:
        """Get multiple papers with their authors loaded."""
        papers = await self.paper_repo.get_by_ids(paper_ids)
        
        # Load authors for all papers
        for paper in papers:
            authors = await self.author_repo.get_paper_authors(paper.id)
            paper._authors = authors
            paper._author_names = [author.name for author in authors]
        
        return papers
    
    async def search_papers_by_author(self, author_name: str, limit: int = 50) -> List[Paper]:
        """Search papers by author name."""
        papers = await self.paper_repo.search_by_author(author_name, limit)
        
        # Load authors for all papers
        for paper in papers:
            authors = await self.author_repo.get_paper_authors(paper.id)
            paper._authors = authors
            paper._author_names = [author.name for author in authors]
        
        return papers
    
    async def get_author_collaboration_network(self, author_id: UUID) -> Dict[str, Any]:
        """Get collaboration network for an author."""
        # Get all papers by this author
        paper_ids = await self.author_repo.get_author_papers(author_id)
        
        # Get all co-authors
        collaborators = {}
        
        for paper_id in paper_ids:
            paper_authors = await self.author_repo.get_paper_authors(paper_id)
            
            for author in paper_authors:
                if author.id != author_id:  # Exclude the main author
                    if author.id not in collaborators:
                        collaborators[author.id] = {
                            'author': author,
                            'collaboration_count': 0,
                            'shared_papers': []
                        }
                    
                    collaborators[author.id]['collaboration_count'] += 1
                    collaborators[author.id]['shared_papers'].append(paper_id)
        
        return {
            'author_id': author_id,
            'total_papers': len(paper_ids),
            'collaborators': list(collaborators.values()),
            'total_collaborators': len(collaborators)
        }
    
    async def get_author_statistics(self) -> Dict[str, Any]:
        """Get comprehensive author statistics."""
        base_stats = await self.author_repo.get_author_statistics()
        prolific_authors = await self.author_repo.get_most_prolific_authors(10)
        
        return {
            **base_stats,
            'most_prolific_authors': prolific_authors
        }
    
    async def merge_duplicate_authors(self, primary_author_id: UUID, duplicate_author_ids: List[UUID]) -> Author:
        """Merge duplicate authors into a primary author."""
        primary_author = await self.author_repo.get_by_id(primary_author_id)
        if not primary_author:
            raise ValueError(f"Primary author {primary_author_id} not found")
        
        # Move all paper relationships to the primary author
        for duplicate_id in duplicate_author_ids:
            # Get papers for the duplicate author
            paper_ids = await self.author_repo.get_author_papers(duplicate_id)
            
            for paper_id in paper_ids:
                # Get the current relationship
                query = """
                    SELECT author_order FROM paper_authors 
                    WHERE paper_id = $1 AND author_id = $2
                """
                
                async with self.author_repo.db_manager.get_connection() as conn:
                    row = await conn.fetchrow(query, paper_id, duplicate_id)
                    if row:
                        # Delete the old relationship
                        await conn.execute(
                            "DELETE FROM paper_authors WHERE paper_id = $1 AND author_id = $2",
                            paper_id, duplicate_id
                        )
                        
                        # Create new relationship with primary author (if not exists)
                        try:
                            await self.author_repo.create_paper_author_relationship(
                                paper_id=paper_id,
                                author_id=primary_author_id,
                                author_order=row['author_order']
                            )
                        except Exception:
                            # Relationship might already exist, that's okay
                            pass
            
            # Delete the duplicate author
            async with self.author_repo.db_manager.get_connection() as conn:
                await conn.execute("DELETE FROM authors WHERE id = $1", duplicate_id)
        
        logger.info(f"Merged {len(duplicate_author_ids)} duplicate authors into {primary_author_id}")
        return primary_author
    
    async def update_author_info(self, author_id: UUID, name: Optional[str] = None, 
                               affiliation: Optional[str] = None, email: Optional[str] = None, 
                               orcid: Optional[str] = None) -> Author:
        """Update author information."""
        author = await self.author_repo.get_by_id(author_id)
        if not author:
            raise ValueError(f"Author {author_id} not found")
        
        # Update fields if provided
        if name is not None:
            author.name = name.strip()
        if affiliation is not None:
            author.affiliation = affiliation.strip() if affiliation else None
        if email is not None:
            author.email = email.strip() if email else None
        if orcid is not None:
            author.orcid = orcid.strip() if orcid else None
        
        # Update in database
        query = """
            UPDATE authors SET
                name = $2,
                affiliation = $3,
                email = $4,
                orcid = $5,
                updated_at = NOW()
            WHERE id = $1
            RETURNING *
        """
        
        async with self.author_repo.db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, author_id, author.name, 
                                    author.affiliation, author.email, author.orcid)
            return Author.from_dict(dict(row))