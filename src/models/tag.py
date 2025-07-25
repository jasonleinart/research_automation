"""
Tag data model.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from .enums import TagCategory, TagSource


@dataclass
class Tag:
    """Tag model for organizing papers and insights."""
    name: str
    category: TagCategory
    
    id: UUID = field(default_factory=uuid4)
    description: Optional[str] = None
    parent_tag_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate data after initialization."""
        if not self.name.strip():
            raise ValueError("Tag name cannot be empty")
    
    @property
    def is_root_tag(self) -> bool:
        """Check if this is a root-level tag."""
        return self.parent_tag_id is None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category.value,
            'description': self.description,
            'parent_tag_id': self.parent_tag_id,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tag':
        """Create Tag from dictionary."""
        return cls(
            id=data.get('id', uuid4()),
            name=data['name'],
            category=TagCategory(data['category']),
            description=data.get('description'),
            parent_tag_id=data.get('parent_tag_id'),
            created_at=data.get('created_at')
        )


@dataclass
class PaperTag:
    """Association between papers and tags."""
    paper_id: UUID
    tag_id: UUID
    confidence: Optional[float] = None
    source: TagSource = TagSource.AUTOMATIC
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate data after initialization."""
        if self.confidence is not None:
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError("confidence must be between 0.0 and 1.0")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'paper_id': self.paper_id,
            'tag_id': self.tag_id,
            'confidence': self.confidence,
            'source': self.source.value,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaperTag':
        """Create PaperTag from dictionary."""
        return cls(
            paper_id=data['paper_id'],
            tag_id=data['tag_id'],
            confidence=data.get('confidence'),
            source=TagSource(data.get('source', 'automatic')),
            created_at=data.get('created_at')
        )