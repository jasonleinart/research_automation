"""
Main paper ingestion service that coordinates different input methods.
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from .arxiv_client import ArxivClient
from .pdf_processor import PDFProcessor
from .author_service import AuthorService
from ..database.paper_repository import PaperRepository
from ..models.paper import Paper

logger = logging.getLogger(__name__)


class PaperIngestionService:
    """Service for ingesting papers from various sources."""
    
    def __init__(self):
        self.arxiv_client = ArxivClient()
        self.pdf_processor = PDFProcessor()
        self.paper_repo = PaperRepository()
        self.author_service = AuthorService()
    
    async def ingest_from_arxiv_url(self, url: str) -> Optional[Paper]:
        """Ingest paper from ArXiv URL with full text extraction."""
        try:
            logger.info(f"Ingesting paper from ArXiv URL: {url}")
            
            # Extract ArXiv ID
            arxiv_id = self.arxiv_client.extract_arxiv_id(url)
            if not arxiv_id:
                logger.error(f"Could not extract ArXiv ID from URL: {url}")
                return None
            
            # Check if paper already exists
            existing_paper = await self.paper_repo.get_by_arxiv_id(arxiv_id)
            if existing_paper:
                logger.info(f"Paper already exists: {existing_paper.title}")
                return existing_paper
            
            # Fetch paper with full text from ArXiv
            paper = await self.arxiv_client.get_paper_from_url(url, include_full_text=True)
            if not paper:
                logger.error(f"Could not fetch paper from ArXiv")
                return None
            
            # Log content extraction results
            if paper.full_text:
                logger.info(f"Successfully extracted {len(paper.full_text)} characters of full text")
            else:
                logger.warning(f"No full text extracted - only metadata available")
            
            # Save paper to database
            saved_paper = await self.paper_repo.create(paper)
            
            # Handle authors if they exist
            if hasattr(paper, '_temp_author_names') and paper._temp_author_names:
                await self.author_service.assign_authors_to_paper(
                    paper_id=saved_paper.id,
                    author_names=paper._temp_author_names
                )
                logger.info(f"Assigned {len(paper._temp_author_names)} authors to paper")
            
            logger.info(f"Successfully ingested paper: {saved_paper.title}")
            return saved_paper
            
        except Exception as e:
            logger.error(f"Failed to ingest from ArXiv URL {url}: {e}")
            return None
    
    async def ingest_from_pdf(self, pdf_path: str, user_metadata: Optional[Dict[str, Any]] = None) -> Optional[Paper]:
        """Ingest paper from PDF file."""
        try:
            logger.info(f"Ingesting paper from PDF: {pdf_path}")
            
            # Validate PDF
            if not self.pdf_processor.validate_pdf(pdf_path):
                logger.error(f"Invalid PDF file: {pdf_path}")
                return None
            
            # Process PDF
            paper = self.pdf_processor.process_pdf(pdf_path, user_metadata)
            if not paper:
                logger.error(f"Could not process PDF: {pdf_path}")
                return None
            
            # Check for duplicates by title or ArXiv ID
            if paper.arxiv_id:
                existing_paper = await self.paper_repo.get_by_arxiv_id(paper.arxiv_id)
                if existing_paper:
                    logger.info(f"Paper already exists (ArXiv ID): {existing_paper.title}")
                    return existing_paper
            
            # Check by title similarity
            similar_papers = await self.paper_repo.find_similar_titles(paper.title, threshold=0.8)
            if similar_papers:
                logger.warning(f"Found {len(similar_papers)} similar papers by title")
                for similar in similar_papers:
                    logger.warning(f"  - {similar.title}")
                # For now, continue with ingestion, but flag this
            
            # Save paper to database
            saved_paper = await self.paper_repo.create(paper)
            
            # Handle authors if they exist
            if hasattr(paper, '_temp_author_names') and paper._temp_author_names:
                await self.author_service.assign_authors_to_paper(
                    paper_id=saved_paper.id,
                    author_names=paper._temp_author_names
                )
                logger.info(f"Assigned {len(paper._temp_author_names)} authors to paper")
            
            logger.info(f"Successfully ingested paper: {saved_paper.title}")
            return saved_paper
            
        except Exception as e:
            logger.error(f"Failed to ingest from PDF {pdf_path}: {e}")
            return None
    
    async def ingest_from_title(self, title: str, max_results: int = 5) -> List[Paper]:
        """Search and return potential papers by title."""
        try:
            logger.info(f"Searching for papers by title: {title}")
            
            # Search ArXiv
            search_results = await self.arxiv_client.search_papers(f'ti:"{title}"', max_results)
            
            papers = []
            for result in search_results:
                try:
                    paper = Paper(**result)
                    papers.append(paper)
                except Exception as e:
                    logger.warning(f"Could not create paper from search result: {e}")
            
            logger.info(f"Found {len(papers)} papers matching title")
            return papers
            
        except Exception as e:
            logger.error(f"Failed to search by title '{title}': {e}")
            return []
    
    async def ingest_selected_paper(self, paper: Paper) -> Optional[Paper]:
        """Ingest a paper that was selected from search results."""
        try:
            # Check if paper already exists
            if paper.arxiv_id:
                existing_paper = await self.paper_repo.get_by_arxiv_id(paper.arxiv_id)
                if existing_paper:
                    logger.info(f"Paper already exists: {existing_paper.title}")
                    return existing_paper
            
            # Save to database
            saved_paper = await self.paper_repo.create(paper)
            logger.info(f"Successfully ingested selected paper: {saved_paper.title}")
            return saved_paper
            
        except Exception as e:
            logger.error(f"Failed to ingest selected paper: {e}")
            return None
    
    async def ingest_from_doi(self, doi: str) -> Optional[Paper]:
        """Ingest paper from DOI (basic implementation)."""
        try:
            logger.info(f"Ingesting paper from DOI: {doi}")
            
            # For now, this is a placeholder
            # In a full implementation, you'd use CrossRef API or similar
            logger.warning("DOI ingestion not fully implemented yet")
            
            # Create a basic paper with DOI info
            paper = Paper(
                title=f"Paper with DOI: {doi}",
                abstract="DOI-based ingestion - metadata to be enhanced",
                ingestion_source="manual_doi"
            )
            
            saved_paper = await self.paper_repo.create(paper)
            logger.info(f"Created placeholder paper for DOI: {doi}")
            return saved_paper
            
        except Exception as e:
            logger.error(f"Failed to ingest from DOI {doi}: {e}")
            return None
    
    async def get_ingestion_stats(self) -> Dict[str, Any]:
        """Get statistics about ingested papers."""
        try:
            stats = await self.paper_repo.get_statistics()
            
            # Add source breakdown
            all_papers = await self.paper_repo.list_all()
            source_counts = {}
            for paper in all_papers:
                source = paper.ingestion_source or "unknown"
                source_counts[source] = source_counts.get(source, 0) + 1
            
            stats['ingestion_sources'] = source_counts
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get ingestion stats: {e}")
            return {}
    
    async def validate_ingestion(self, paper: Paper) -> List[str]:
        """Validate paper data and return list of issues."""
        issues = []
        
        if not paper.title or len(paper.title.strip()) < 5:
            issues.append("Title is missing or too short")
        
        if not paper.abstract or len(paper.abstract.strip()) < 20:
            issues.append("Abstract is missing or too short")
        
        if not paper.author_names:
            issues.append("No authors specified")
        
        if paper.arxiv_id:
            # Validate ArXiv ID format
            import re
            if not re.match(r'^\d{4}\.\d{4,5}(v\d+)?$', paper.arxiv_id):
                issues.append("Invalid ArXiv ID format")
        
        return issues