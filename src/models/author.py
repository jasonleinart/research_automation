"""
Author data model for relational storage.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from dataclasses import dataclass, field


@dataclass
class Author:
    """Author information for relational storage."""
    name: str
    id: UUID = field(default_factory=uuid4)
    affiliation: Optional[str] = None
    email: Optional[str] = None
    orcid: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate data after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("Author name cannot be empty")
        
        # Clean up name
        self.name = self.name.strip()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'name': self.name,
            'affiliation': self.affiliation,
            'email': self.email,
            'orcid': self.orcid,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Author':
        """Create Author from dictionary."""
        return cls(
            id=data.get('id', uuid4()),
            name=data['name'],
            affiliation=data.get('affiliation'),
            email=data.get('email'),
            orcid=data.get('orcid'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )


@dataclass
class PaperAuthor:
    """Paper-Author relationship with ordering."""
    paper_id: UUID
    author_id: UUID
    author_order: int
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            'paper_id': self.paper_id,
            'author_id': self.author_id,
            'author_order': self.author_order,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PaperAuthor':
        """Create PaperAuthor from dictionary."""
        return cls(
            paper_id=data['paper_id'],
            author_id=data['author_id'],
            author_order=data['author_order'],
            created_at=data.get('created_at')
        ) 