# Data models for papers, insights, tags, and citations

from .enums import *
from .paper import Paper
from .author import Author, PaperAuthor
from .tag import Tag, PaperTag
from .insight import Insight, InsightTag
from .citation import Citation, ExternalCitation
from .note import Note, NoteTag, NoteRelationship, NoteCollection, NoteTemplate

__all__ = [
    # Enums
    'PaperType', 'EvidenceStrength', 'PracticalApplicability', 'AnalysisStatus',
    'TagCategory', 'TagSource', 'CitationType', 'IngestionStatus', 
    'InsightType', 'EmbeddingType', 'NoteType', 'NotePriority',
    
    # Models
    'Paper', 'Author', 'PaperAuthor',
    'Tag', 'PaperTag',
    'Insight', 'InsightTag',
    'Citation', 'ExternalCitation',
    'Note', 'NoteTag', 'NoteRelationship', 'NoteCollection', 'NoteTemplate'
]