"""
Citation data models.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from .enums import CitationType, IngestionStatus


@dataclass
class Citation:
    """Citation relationship between papers in our system."""
    citing_paper_id: UUID
    cited_paper_id: UUID
    
    id: UUID = field(default_factory=uuid4)
    citation_context: Optional[str] = None
    citation_type: Optional[CitationType] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'citing_paper_id': self.citing_paper_id,
            'cited_paper_id': self.cited_paper_id,
            'citation_context': self.citation_context,
            'citation_type': self.citation_type.value if self.citation_type else None,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Citation':
        """Create Citation from dictionary."""
        citation_type = CitationType(data['citation_type']) if data.get('citation_type') else None
        
        return cls(
            id=data.get('id', uuid4()),
            citing_paper_id=data['citing_paper_id'],
            cited_paper_id=data['cited_paper_id'],
            citation_context=data.get('citation_context'),
            citation_type=citation_type,
            created_at=data.get('created_at')
        )


@dataclass
class ExternalCitation:
    """Citation to a paper not yet in our system."""
    citing_paper_id: UUID
    
    id: UUID = field(default_factory=uuid4)
    title: Optional[str] = None
    authors: Optional[str] = None
    publication_year: Optional[int] = None
    venue: Optional[str] = None
    external_citation_count: int = 0
    priority_score: Optional[float] = None
    ingestion_status: IngestionStatus = IngestionStatus.NOT_QUEUED
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate data after initialization."""
        if self.priority_score is not None:
            if not 0.0 <= self.priority_score <= 1.0:
                raise ValueError("priority_score must be between 0.0 and 1.0")
    
    @property
    def should_ingest(self) -> bool:
        """Check if this citation should be prioritized for ingestion."""
        return (
            self.priority_score is not None and 
            self.priority_score >= 0.7 and 
            self.ingestion_status == IngestionStatus.NOT_QUEUED
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'citing_paper_id': self.citing_paper_id,
            'title': self.title,
            'authors': self.authors,
            'publication_year': self.publication_year,
            'venue': self.venue,
            'external_citation_count': self.external_citation_count,
            'priority_score': self.priority_score,
            'ingestion_status': self.ingestion_status.value,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExternalCitation':
        """Create ExternalCitation from dictionary."""
        ingestion_status = IngestionStatus(data.get('ingestion_status', 'not_queued'))
        
        return cls(
            id=data.get('id', uuid4()),
            citing_paper_id=data['citing_paper_id'],
            title=data.get('title'),
            authors=data.get('authors'),
            publication_year=data.get('publication_year'),
            venue=data.get('venue'),
            external_citation_count=data.get('external_citation_count', 0),
            priority_score=data.get('priority_score'),
            ingestion_status=ingestion_status,
            created_at=data.get('created_at')
        )