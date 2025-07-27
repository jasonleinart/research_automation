"""
Conversation data models for the research agent.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from .paper import Paper


@dataclass
class ConversationMessage:
    """A single message in a conversation."""
    role: str  # 'user', 'assistant', or 'system'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    confidence: Optional[float] = None
    grounded: Optional[bool] = None
    sources: Optional[List[str]] = None
    limitations: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': str(self.id) if self.id else None,
            'session_id': str(self.session_id) if self.session_id else None,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'confidence': self.confidence,
            'grounded': self.grounded,
            'sources': self.sources,
            'limitations': self.limitations,
            'metadata': self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """Create from dictionary."""
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            id=UUID(data['id']) if data.get('id') else None,
            session_id=UUID(data['session_id']) if data.get('session_id') else None,
            confidence=data.get('confidence'),
            grounded=data.get('grounded'),
            sources=data.get('sources'),
            limitations=data.get('limitations'),
            metadata=data.get('metadata')
        )


@dataclass
class ConversationSession:
    """A conversation session with a user."""
    session_id: UUID = field(default_factory=uuid4)
    paper_id: Optional[UUID] = None
    title: Optional[str] = None
    messages: List[ConversationMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    is_archived: bool = False
    metadata: Optional[Dict[str, Any]] = None
    
    # Legacy fields for compatibility
    user_id: Optional[str] = None
    current_paper_id: Optional[UUID] = None
    related_paper_ids: List[UUID] = field(default_factory=list)
    user_interests: List[str] = field(default_factory=list)
    is_active: bool = True
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        # Set current_paper_id for compatibility
        if self.paper_id and not self.current_paper_id:
            self.current_paper_id = self.paper_id
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> ConversationMessage:
        """Add a message to the conversation."""
        message = ConversationMessage(role=role, content=content, metadata=metadata)
        self.messages.append(message)
        self.updated_at = datetime.now()
        self.last_activity = datetime.now()
        self.message_count = len(self.messages)
        return message
    
    def add_message_to_memory(self, message: ConversationMessage):
        """Add a message to the in-memory message list."""
        self.messages.append(message)
        self.last_activity = datetime.now()
        self.message_count = len(self.messages)
    
    def get_recent_messages(self, limit: int = 10) -> List[ConversationMessage]:
        """Get recent messages for context."""
        return self.messages[-limit:] if self.messages else []
    
    def get_message_count(self) -> int:
        """Get total number of messages."""
        return len(self.messages)
    
    def set_current_paper(self, paper_id: UUID):
        """Set the current paper being discussed."""
        self.current_paper_id = paper_id
        self.paper_id = paper_id
        self.updated_at = datetime.now()
    
    def add_related_papers(self, paper_ids: List[UUID]):
        """Add related papers to the context."""
        self.related_paper_ids = paper_ids
        self.updated_at = datetime.now()
    
    def generate_title(self) -> str:
        """Generate a title for the conversation based on content."""
        if self.messages:
            # Use first user message as basis for title
            first_user_msg = next((msg for msg in self.messages if msg.role == 'user'), None)
            if first_user_msg:
                # Take first 50 characters and clean up
                title = first_user_msg.content[:50].strip()
                if len(first_user_msg.content) > 50:
                    title += "..."
                return title
        
        return f"Conversation {self.session_id.hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'session_id': str(self.session_id),
            'user_id': self.user_id,
            'title': self.title or self.generate_title(),
            'messages': [msg.to_dict() for msg in self.messages],
            'paper_id': str(self.paper_id) if self.paper_id else None,
            'current_paper_id': str(self.current_paper_id) if self.current_paper_id else None,
            'related_paper_ids': [str(pid) for pid in self.related_paper_ids],
            'user_interests': self.user_interests,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active,
            'message_count': self.get_message_count()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationSession':
        """Create from dictionary."""
        messages = [ConversationMessage.from_dict(msg_data) for msg_data in data.get('messages', [])]
        
        return cls(
            session_id=UUID(data['session_id']),
            user_id=data.get('user_id'),
            title=data.get('title'),
            messages=messages,
            current_paper_id=UUID(data['current_paper_id']) if data.get('current_paper_id') else None,
            related_paper_ids=[UUID(pid) for pid in data.get('related_paper_ids', [])],
            user_interests=data.get('user_interests', []),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            is_active=data.get('is_active', True)
        )


@dataclass
class UserInterest:
    """Tracks user interests and research preferences."""
    user_id: str
    topic: str
    interest_level: float  # 0.0 to 1.0
    papers_explored: List[UUID] = field(default_factory=list)
    questions_asked: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_paper_exploration(self, paper_id: UUID):
        """Record that user explored a paper on this topic."""
        if paper_id not in self.papers_explored:
            self.papers_explored.append(paper_id)
            self.updated_at = datetime.now()
    
    def add_question(self, question: str):
        """Record a question asked about this topic."""
        self.questions_asked.append(question)
        self.updated_at = datetime.now()
    
    def update_interest_level(self, new_level: float):
        """Update the interest level (0.0 to 1.0)."""
        self.interest_level = max(0.0, min(1.0, new_level))
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'user_id': self.user_id,
            'topic': self.topic,
            'interest_level': self.interest_level,
            'papers_explored': [str(pid) for pid in self.papers_explored],
            'questions_asked': self.questions_asked,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserInterest':
        """Create from dictionary."""
        return cls(
            user_id=data['user_id'],
            topic=data['topic'],
            interest_level=data['interest_level'],
            papers_explored=[UUID(pid) for pid in data.get('papers_explored', [])],
            questions_asked=data.get('questions_asked', []),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )