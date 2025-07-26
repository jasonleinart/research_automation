"""
Note data model for research paper annotations and notes.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any, Set
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum

from .enums import NoteType, NotePriority


@dataclass
class Note:
    """Core note model for research paper annotations and notes."""
    
    # Required fields
    title: str
    content: str
    paper_id: UUID
    
    # Optional fields
    id: UUID = field(default_factory=uuid4)
    conversation_session_id: Optional[UUID] = None
    note_type: NoteType = NoteType.GENERAL
    priority: NotePriority = NotePriority.MEDIUM
    
    # PDF annotation data
    page_number: Optional[int] = None
    x_position: Optional[Decimal] = None
    y_position: Optional[Decimal] = None
    width: Optional[Decimal] = None
    height: Optional[Decimal] = None
    selected_text: Optional[str] = None
    annotation_color: Optional[str] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    is_public: bool = False
    is_archived: bool = False
    
    # Relationships
    parent_note_id: Optional[UUID] = None
    related_note_ids: List[UUID] = field(default_factory=list)
    
    # Context
    context_section: Optional[str] = None
    
    # Search vector (populated by database trigger)
    search_vector: Optional[str] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Computed properties (populated by repository)
    _paper_title: Optional[str] = None
    _parent_note: Optional['Note'] = None
    _child_notes: List['Note'] = field(default_factory=list)
    _related_notes: List['Note'] = field(default_factory=list)
    _collections: List['NoteCollection'] = field(default_factory=list)
    _relationships: List['NoteRelationship'] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate data after initialization."""
        if self.annotation_color and not self._is_valid_color(self.annotation_color):
            raise ValueError("annotation_color must be a valid hex color (e.g., '#FF0000')")
        
        if self.x_position is not None and not (0 <= self.x_position <= 1):
            raise ValueError("x_position must be between 0 and 1")
        
        if self.y_position is not None and not (0 <= self.y_position <= 1):
            raise ValueError("y_position must be between 0 and 1")
        
        if self.width is not None and self.width <= 0:
            raise ValueError("width must be positive")
        
        if self.height is not None and self.height <= 0:
            raise ValueError("height must be positive")
    
    @staticmethod
    def _is_valid_color(color: str) -> bool:
        """Check if color is a valid hex color."""
        import re
        return bool(re.match(r'^#[0-9A-Fa-f]{6}$', color))
    
    @property
    def paper_title(self) -> Optional[str]:
        """Get paper title."""
        return self._paper_title
    
    @property
    def parent_note(self) -> Optional['Note']:
        """Get parent note."""
        return self._parent_note
    
    @property
    def child_notes(self) -> List['Note']:
        """Get child notes."""
        return self._child_notes
    
    @property
    def related_notes(self) -> List['Note']:
        """Get related notes."""
        return self._related_notes
    
    @property
    def collections(self) -> List['NoteCollection']:
        """Get collections this note belongs to."""
        return self._collections
    
    @property
    def relationships(self) -> List['NoteRelationship']:
        """Get relationships for this note."""
        return self._relationships
    
    @property
    def is_annotation(self) -> bool:
        """Check if this is a PDF annotation."""
        return self.note_type == NoteType.ANNOTATION
    
    @property
    def has_pdf_coordinates(self) -> bool:
        """Check if note has PDF coordinates."""
        return all([
            self.page_number is not None,
            self.x_position is not None,
            self.y_position is not None
        ])
    
    @property
    def tag_set(self) -> Set[str]:
        """Get tags as a set for efficient operations."""
        return set(self.tags)
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the note."""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the note."""
        if tag in self.tags:
            self.tags.remove(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Check if note has a specific tag."""
        return tag in self.tags
    
    def add_related_note(self, note_id: UUID) -> None:
        """Add a related note ID."""
        if note_id not in self.related_note_ids:
            self.related_note_ids.append(note_id)
    
    def remove_related_note(self, note_id: UUID) -> None:
        """Remove a related note ID."""
        if note_id in self.related_note_ids:
            self.related_note_ids.remove(note_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'paper_id': self.paper_id,
            'conversation_session_id': self.conversation_session_id,
            'title': self.title,
            'content': self.content,
            'note_type': self.note_type.value,
            'priority': self.priority.value,
            'page_number': self.page_number,
            'x_position': self.x_position,
            'y_position': self.y_position,
            'width': self.width,
            'height': self.height,
            'selected_text': self.selected_text,
            'annotation_color': self.annotation_color,
            'tags': self.tags,
            'is_public': self.is_public,
            'is_archived': self.is_archived,
            'parent_note_id': self.parent_note_id,
            'related_note_ids': self.related_note_ids,
            'context_section': self.context_section,
            'search_vector': self.search_vector,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Note':
        """Create Note from dictionary."""
        # Convert enum strings back to enums
        note_type = NoteType(data['note_type']) if data.get('note_type') else NoteType.GENERAL
        priority = NotePriority(data['priority']) if data.get('priority') else NotePriority.MEDIUM
        
        return cls(
            id=data.get('id', uuid4()),
            paper_id=data['paper_id'],
            conversation_session_id=data.get('conversation_session_id'),
            title=data['title'],
            content=data['content'],
            note_type=note_type,
            priority=priority,
            page_number=data.get('page_number'),
            x_position=data.get('x_position'),
            y_position=data.get('y_position'),
            width=data.get('width'),
            height=data.get('height'),
            selected_text=data.get('selected_text'),
            annotation_color=data.get('annotation_color'),
            tags=data.get('tags', []),
            is_public=data.get('is_public', False),
            is_archived=data.get('is_archived', False),
            parent_note_id=data.get('parent_note_id'),
            related_note_ids=data.get('related_note_ids', []),
            context_section=data.get('context_section'),
            search_vector=data.get('search_vector'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            metadata=data.get('metadata', {})
        )


@dataclass
class NoteTag:
    """Note tag model."""
    name: str
    id: UUID = field(default_factory=uuid4)
    color: str = '#3B82F6'  # Default blue
    description: Optional[str] = None
    usage_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate data after initialization."""
        if not Note._is_valid_color(self.color):
            raise ValueError("color must be a valid hex color")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'description': self.description,
            'usage_count': self.usage_count,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NoteTag':
        """Create NoteTag from dictionary."""
        return cls(
            id=data.get('id', uuid4()),
            name=data['name'],
            color=data.get('color', '#3B82F6'),
            description=data.get('description'),
            usage_count=data.get('usage_count', 0),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )


@dataclass
class NoteRelationship:
    """Note relationship model."""
    source_note_id: UUID
    target_note_id: UUID
    relationship_type: str
    id: UUID = field(default_factory=uuid4)
    strength: Decimal = Decimal('1.0')
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate data after initialization."""
        if not (0 <= self.strength <= 1):
            raise ValueError("strength must be between 0 and 1")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'source_note_id': self.source_note_id,
            'target_note_id': self.target_note_id,
            'relationship_type': self.relationship_type,
            'strength': self.strength,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NoteRelationship':
        """Create NoteRelationship from dictionary."""
        return cls(
            id=data.get('id', uuid4()),
            source_note_id=data['source_note_id'],
            target_note_id=data['target_note_id'],
            relationship_type=data['relationship_type'],
            strength=Decimal(str(data.get('strength', '1.0'))),
            created_at=data.get('created_at')
        )


@dataclass
class NoteCollection:
    """Note collection model for organizing notes."""
    name: str
    id: UUID = field(default_factory=uuid4)
    description: Optional[str] = None
    color: str = '#10B981'  # Default green
    is_public: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Computed properties
    _notes: List[Note] = field(default_factory=list)
    _note_count: int = 0
    
    def __post_init__(self):
        """Validate data after initialization."""
        if not Note._is_valid_color(self.color):
            raise ValueError("color must be a valid hex color")
    
    @property
    def notes(self) -> List[Note]:
        """Get notes in this collection."""
        return self._notes
    
    @property
    def note_count(self) -> int:
        """Get number of notes in this collection."""
        return self._note_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'is_public': self.is_public,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NoteCollection':
        """Create NoteCollection from dictionary."""
        return cls(
            id=data.get('id', uuid4()),
            name=data['name'],
            description=data.get('description'),
            color=data.get('color', '#10B981'),
            is_public=data.get('is_public', False),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )


@dataclass
class NoteTemplate:
    """Note template model for reusable note structures."""
    name: str
    template_content: str
    note_type: NoteType
    id: UUID = field(default_factory=uuid4)
    description: Optional[str] = None
    is_default: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'template_content': self.template_content,
            'note_type': self.note_type.value,
            'is_default': self.is_default,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NoteTemplate':
        """Create NoteTemplate from dictionary."""
        note_type = NoteType(data['note_type']) if data.get('note_type') else NoteType.GENERAL
        
        return cls(
            id=data.get('id', uuid4()),
            name=data['name'],
            description=data.get('description'),
            template_content=data['template_content'],
            note_type=note_type,
            is_default=data.get('is_default', False),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        ) 