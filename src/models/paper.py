"""
Paper data model.
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from .enums import (
    PaperType, EvidenceStrength, PracticalApplicability, AnalysisStatus
)


@dataclass
class Author:
    """Author information."""
    name: str
    affiliation: Optional[str] = None
    email: Optional[str] = None


@dataclass
class Paper:
    """Core paper model."""
    # Required fields
    title: str
    
    # Optional metadata
    id: UUID = field(default_factory=uuid4)
    arxiv_id: Optional[str] = None
    abstract: Optional[str] = None
    authors: List[Author] = field(default_factory=list)
    publication_date: Optional[date] = None
    categories: List[str] = field(default_factory=list)
    pdf_url: Optional[str] = None
    full_text: Optional[str] = None
    citation_count: int = 0
    
    # Classification fields
    paper_type: Optional[PaperType] = None
    evidence_strength: Optional[EvidenceStrength] = None
    novelty_score: Optional[float] = None
    practical_applicability: Optional[PracticalApplicability] = None
    
    # Analysis metadata
    analysis_status: AnalysisStatus = AnalysisStatus.PENDING
    analysis_confidence: Optional[float] = None
    extraction_version: int = 1
    
    # Content generation tracking
    content_generated: bool = False
    content_approved: bool = False
    
    # Source tracking
    ingestion_source: Optional[str] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate data after initialization."""
        if self.novelty_score is not None:
            if not 0.0 <= self.novelty_score <= 1.0:
                raise ValueError("novelty_score must be between 0.0 and 1.0")
        
        if self.analysis_confidence is not None:
            if not 0.0 <= self.analysis_confidence <= 1.0:
                raise ValueError("analysis_confidence must be between 0.0 and 1.0")
    
    @property
    def author_names(self) -> List[str]:
        """Get list of author names."""
        return [author.name for author in self.authors]
    
    @property
    def is_analyzed(self) -> bool:
        """Check if paper has been analyzed."""
        return self.analysis_status == AnalysisStatus.COMPLETED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'arxiv_id': self.arxiv_id,
            'title': self.title,
            'abstract': self.abstract,
            'authors': [
                {
                    'name': author.name,
                    'affiliation': author.affiliation,
                    'email': author.email
                }
                for author in self.authors
            ],
            'publication_date': self.publication_date,
            'categories': self.categories,
            'pdf_url': self.pdf_url,
            'full_text': self.full_text,
            'citation_count': self.citation_count,
            'paper_type': self.paper_type.value if self.paper_type else None,
            'evidence_strength': self.evidence_strength.value if self.evidence_strength else None,
            'novelty_score': self.novelty_score,
            'practical_applicability': self.practical_applicability.value if self.practical_applicability else None,
            'analysis_status': self.analysis_status.value,
            'analysis_confidence': self.analysis_confidence,
            'extraction_version': self.extraction_version,
            'content_generated': self.content_generated,
            'content_approved': self.content_approved,
            'ingestion_source': self.ingestion_source,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Paper':
        """Create Paper from dictionary."""
        # Convert authors from dict to Author objects
        authors = []
        if data.get('authors'):
            for author_data in data['authors']:
                if isinstance(author_data, dict):
                    authors.append(Author(**author_data))
                else:
                    # Handle case where author is just a string
                    authors.append(Author(name=str(author_data)))
        
        # Convert enum strings back to enums
        paper_type = PaperType(data['paper_type']) if data.get('paper_type') else None
        evidence_strength = EvidenceStrength(data['evidence_strength']) if data.get('evidence_strength') else None
        practical_applicability = PracticalApplicability(data['practical_applicability']) if data.get('practical_applicability') else None
        analysis_status = AnalysisStatus(data.get('analysis_status', 'pending'))
        
        return cls(
            id=data.get('id', uuid4()),
            arxiv_id=data.get('arxiv_id'),
            title=data['title'],
            abstract=data.get('abstract'),
            authors=authors,
            publication_date=data.get('publication_date'),
            categories=data.get('categories', []),
            pdf_url=data.get('pdf_url'),
            full_text=data.get('full_text'),
            citation_count=data.get('citation_count', 0),
            paper_type=paper_type,
            evidence_strength=evidence_strength,
            novelty_score=data.get('novelty_score'),
            practical_applicability=practical_applicability,
            analysis_status=analysis_status,
            analysis_confidence=data.get('analysis_confidence'),
            extraction_version=data.get('extraction_version', 1),
            content_generated=data.get('content_generated', False),
            content_approved=data.get('content_approved', False),
            ingestion_source=data.get('ingestion_source'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )