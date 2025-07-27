"""
PDF processing service for extracting text and metadata.
"""

import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import date

import PyPDF2
import pdfplumber

from ..models.paper import Paper
from ..models.author import Author

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Service for processing PDF files."""
    
    def __init__(self):
        self.max_text_length = 1_000_000  # 1MB text limit
    
    def extract_text_pypdf2(self, pdf_path: str) -> Optional[str]:
        """Extract text using PyPDF2 (faster but less accurate)."""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                
                return text.strip() if text.strip() else None
                
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed for {pdf_path}: {e}")
            return None
    
    def extract_text_pdfplumber(self, pdf_path: str) -> Optional[str]:
        """Extract text using pdfplumber (slower but more accurate)."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                return text.strip() if text.strip() else None
                
        except Exception as e:
            logger.error(f"pdfplumber extraction failed for {pdf_path}: {e}")
            return None
    
    def extract_text(self, pdf_path: str, method: str = "auto") -> Optional[str]:
        """Extract text from PDF using specified method."""
        if not Path(pdf_path).exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return None
        
        text = None
        
        if method == "auto":
            # Try pdfplumber first, fallback to PyPDF2
            text = self.extract_text_pdfplumber(pdf_path)
            if not text:
                logger.info("pdfplumber failed, trying PyPDF2...")
                text = self.extract_text_pypdf2(pdf_path)
        elif method == "pdfplumber":
            text = self.extract_text_pdfplumber(pdf_path)
        elif method == "pypdf2":
            text = self.extract_text_pypdf2(pdf_path)
        else:
            logger.error(f"Unknown extraction method: {method}")
            return None
        
        if text and len(text) > self.max_text_length:
            logger.warning(f"Text too long ({len(text)} chars), truncating...")
            text = text[:self.max_text_length]
        
        return text
    
    def extract_metadata_from_text(self, text: str) -> Dict[str, Any]:
        """Extract metadata from PDF text using patterns."""
        metadata = {}
        
        # Extract title (usually the first substantial line)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if lines:
            # Look for title in first few lines
            for line in lines[:5]:
                if len(line) > 10 and len(line) < 200:
                    # Skip lines that look like headers/footers
                    if not re.match(r'^(page|figure|table|\d+)', line.lower()):
                        metadata['title'] = line
                        break
        
        # Extract abstract
        abstract_patterns = [
            r'abstract\s*[:\-]?\s*(.*?)(?=\n\s*(?:keywords|introduction|1\.|i\.|background))',
            r'abstract\s*[:\-]?\s*(.*?)(?=\n\s*\n)',
        ]
        
        for pattern in abstract_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                # Clean up abstract
                abstract = re.sub(r'\s+', ' ', abstract)
                if len(abstract) > 50:  # Reasonable abstract length
                    metadata['abstract'] = abstract
                    break
        
        # Extract authors (look for patterns like "Author1, Author2")
        author_patterns = [
            r'(?:authors?|by)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)*)',
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)*)\s*$'
        ]
        
        for pattern in author_patterns:
            matches = re.findall(pattern, text[:2000], re.MULTILINE | re.IGNORECASE)
            if matches:
                author_text = matches[0]
                # Parse author names
                authors = []
                for name in author_text.split(','):
                    name = name.strip()
                    if name and len(name) > 2:
                        authors.append(Author(name=name))
                
                if authors:
                    metadata['authors'] = authors
                    break
        
        # Look for ArXiv ID in text
        arxiv_match = re.search(r'arxiv:(\d{4}\.\d{4,5}(?:v\d+)?)', text, re.IGNORECASE)
        if arxiv_match:
            metadata['arxiv_id'] = arxiv_match.group(1)
        
        return metadata
    
    def process_pdf(self, pdf_path: str, user_metadata: Optional[Dict[str, Any]] = None) -> Optional[Paper]:
        """Process PDF file and create Paper object."""
        try:
            # Extract text
            full_text = self.extract_text(pdf_path)
            if not full_text:
                logger.error(f"Could not extract text from PDF: {pdf_path}")
                return None
            
            # Extract metadata from text
            extracted_metadata = self.extract_metadata_from_text(full_text)
            
            # Merge with user-provided metadata (user data takes precedence)
            metadata = {
                'full_text': full_text,
                'ingestion_source': 'manual_pdf_upload',
                **extracted_metadata
            }
            
            if user_metadata:
                metadata.update(user_metadata)
            
            # Ensure we have at least a title
            if not metadata.get('title'):
                filename = Path(pdf_path).stem
                metadata['title'] = filename.replace('_', ' ').replace('-', ' ').title()
                logger.warning(f"No title found, using filename: {metadata['title']}")
            
            # Extract author names for separate processing
            author_names = [author.name for author in metadata.pop('authors', [])]
            
            # Create paper without authors (they'll be handled separately)
            paper = Paper(**metadata)
            
            # Store author names for later processing
            if author_names:
                paper._temp_author_names = author_names
            
            return paper
            
        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_path}: {e}")
            return None
    
    def validate_pdf(self, pdf_path: str) -> bool:
        """Validate that file is a readable PDF."""
        try:
            if not Path(pdf_path).exists():
                return False
            
            # Try to open with PyPDF2
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                # Check if we can read at least one page
                if len(reader.pages) > 0:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"PDF validation failed for {pdf_path}: {e}")
            return False