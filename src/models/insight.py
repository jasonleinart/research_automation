"""
Insight data model.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from .enums import InsightType


@dataclass
class Insight:
    """Extracted insight from a paper."""
    paper_id: UUID
    insight_type: InsightType
    title: str
    
    id: UUID = field(default_factory=uuid4)
    description: Optional[str] = None
    content: Dict[str, Any] = field(default_factory=dict)
    confidence: Optional[float] = None
    extraction_method: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate data after initialization."""
        if not self.title.strip():
            raise ValueError("Insight title cannot be empty")
        
        if self.confidence is not None:
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError("confidence must be between 0.0 and 1.0")
    
    @property
    def is_high_confidence(self) -> bool:
        """Check if this is a high-confidence insight."""
        return self.confidence is not None and self.confidence >= 0.8
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'paper_id': self.paper_id,
            'insight_type': self.insight_type.value,
            'title': self.title,
            'description': self.description,
            'content': self.content,
            'confidence': self.confidence,
            'extraction_method': self.extraction_method,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Insight':
        """Create Insight from dictionary."""
        return cls(
            id=data.get('id', uuid4()),
            paper_id=data['paper_id'],
            insight_type=InsightType(data['insight_type']),
            title=data['title'],
            description=data.get('description'),
            content=data.get('content', {}),
            confidence=data.get('confidence'),
            extraction_method=data.get('extraction_method'),
            created_at=data.get('created_at')
        )


@dataclass
class InsightTag:
    """Association between insights and tags."""
    insight_id: UUID
    tag_id: UUID
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'insight_id': self.insight_id,
            'tag_id': self.tag_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InsightTag':
        """Create InsightTag from dictionary."""
        return cls(
            insight_id=data['insight_id'],
            tag_id=data['tag_id']
        )