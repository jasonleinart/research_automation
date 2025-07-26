# Database connection, migrations, and repository patterns

from .connection import db_manager
from .paper_repository import PaperRepository
from .insight_repository import InsightRepository
from .tag_repository import TagRepository
from .author_repository import AuthorRepository
from .conversation_repository import ConversationRepository
from .note_repository import NoteRepository

__all__ = [
    'db_manager',
    'PaperRepository',
    'InsightRepository',
    'TagRepository',
    'AuthorRepository',
    'ConversationRepository',
    'NoteRepository'
]