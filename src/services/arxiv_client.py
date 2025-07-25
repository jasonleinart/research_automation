"""
ArXiv API client for fetching paper metadata and PDFs.
"""

import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qs

import httpx
import xml.etree.ElementTree as ET

from ..models.paper import Paper, Author

logger = logging.getLogger(__name__)


class ArxivClient:
    """Client for interacting with ArXiv API."""
    
    def __init__(self):
        self.base_url = "https://export.arxiv.org/api/query"  # Use HTTPS
        self.pdf_base_url = "https://arxiv.org/pdf"
        self.abs_base_url = "https://arxiv.org/abs"
    
    def extract_arxiv_id(self, url_or_id: str) -> Optional[str]:
        """Extract ArXiv ID from URL or return ID if already clean."""
        # Handle direct ArXiv ID
        if re.match(r'^\d{4}\.\d{4,5}(v\d+)?$', url_or_id):
            return url_or_id
        
        # Handle ArXiv URLs
        patterns = [
            r'arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)',
            r'arxiv\.org/pdf/(\d{4}\.\d{4,5}(?:v\d+)?)',
            r'arxiv\.org/(?:abs|pdf)/([a-z-]+/\d{7}(?:v\d+)?)',  # Old format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)
        
        return None
    
    async def get_paper_metadata(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """Fetch paper metadata from ArXiv API."""
        try:
            params = {
                'id_list': arxiv_id,
                'max_results': 1
            }
            
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                
                # Parse XML response
                root = ET.fromstring(response.content)
                
                # Find the entry
                entry = root.find('{http://www.w3.org/2005/Atom}entry')
                if entry is None:
                    logger.warning(f"No entry found for ArXiv ID: {arxiv_id}")
                    return None
                
                return self._parse_entry(entry)
                
        except Exception as e:
            logger.error(f"Failed to fetch metadata for {arxiv_id}: {e}")
            return None
    
    def _parse_entry(self, entry: ET.Element) -> Dict[str, Any]:
        """Parse ArXiv API entry XML into structured data."""
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
        
        # Extract basic fields
        title = entry.find('atom:title', ns)
        title_text = title.text.strip().replace('\n', ' ') if title is not None else ""
        
        summary = entry.find('atom:summary', ns)
        abstract_text = summary.text.strip().replace('\n', ' ') if summary is not None else ""
        
        # Extract ArXiv ID from the ID field
        id_elem = entry.find('atom:id', ns)
        arxiv_url = id_elem.text if id_elem is not None else ""
        arxiv_id = self.extract_arxiv_id(arxiv_url)
        
        # Extract publication date
        published = entry.find('atom:published', ns)
        pub_date = None
        if published is not None:
            try:
                pub_date = datetime.fromisoformat(published.text.replace('Z', '+00:00')).date()
            except ValueError:
                logger.warning(f"Could not parse publication date: {published.text}")
        
        # Extract authors
        authors = []
        for author_elem in entry.findall('atom:author', ns):
            name_elem = author_elem.find('atom:name', ns)
            if name_elem is not None:
                authors.append(Author(name=name_elem.text.strip()))
        
        # Extract categories
        categories = []
        for category_elem in entry.findall('atom:category', ns):
            term = category_elem.get('term')
            if term:
                categories.append(term)
        
        # Build PDF URL
        pdf_url = f"{self.pdf_base_url}/{arxiv_id}.pdf" if arxiv_id else None
        
        return {
            'arxiv_id': arxiv_id,
            'title': title_text,
            'abstract': abstract_text,
            'authors': authors,
            'publication_date': pub_date,
            'categories': categories,
            'pdf_url': pdf_url,
            'ingestion_source': 'arxiv_api'
        }
    
    async def download_pdf(self, arxiv_id: str, save_path: Optional[str] = None) -> Optional[bytes]:
        """Download PDF content for a paper."""
        try:
            pdf_url = f"{self.pdf_base_url}/{arxiv_id}.pdf"
            
            async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
                response = await client.get(pdf_url)
                response.raise_for_status()
                
                if save_path:
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"PDF saved to: {save_path}")
                
                return response.content
                
        except Exception as e:
            logger.error(f"Failed to download PDF for {arxiv_id}: {e}")
            return None
    
    async def search_papers(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search ArXiv papers by query."""
        try:
            params = {
                'search_query': query,
                'max_results': max_results,
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                
                # Parse XML response
                root = ET.fromstring(response.content)
                
                papers = []
                for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                    paper_data = self._parse_entry(entry)
                    papers.append(paper_data)
                
                return papers
                
        except Exception as e:
            logger.error(f"Failed to search papers: {e}")
            return []
    
    async def get_paper_from_url(self, url: str) -> Optional[Paper]:
        """Get paper from ArXiv URL."""
        arxiv_id = self.extract_arxiv_id(url)
        if not arxiv_id:
            logger.error(f"Could not extract ArXiv ID from URL: {url}")
            return None
        
        metadata = await self.get_paper_metadata(arxiv_id)
        if not metadata:
            return None
        
        return Paper(**metadata)