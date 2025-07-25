"""
Enum definitions matching the database schema.
"""

from enum import Enum


class PaperType(str, Enum):
    """Types of research papers."""
    CONCEPTUAL_FRAMEWORK = "conceptual_framework"
    SURVEY_REVIEW = "survey_review"
    EMPIRICAL_STUDY = "empirical_study"
    CASE_STUDY = "case_study"
    BENCHMARK_COMPARISON = "benchmark_comparison"
    POSITION_PAPER = "position_paper"
    TUTORIAL_METHODOLOGY = "tutorial_methodology"


class EvidenceStrength(str, Enum):
    """Strength of evidence in the paper."""
    EXPERIMENTAL = "experimental"
    THEORETICAL = "theoretical"
    OBSERVATIONAL = "observational"
    ANECDOTAL = "anecdotal"


class PracticalApplicability(str, Enum):
    """How practically applicable the research is."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    THEORETICAL_ONLY = "theoretical_only"


class AnalysisStatus(str, Enum):
    """Status of paper analysis."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    MANUAL_REVIEW = "manual_review"


class TagCategory(str, Enum):
    """Categories for tags."""
    RESEARCH_DOMAIN = "research_domain"
    CONCEPT = "concept"
    METHODOLOGY = "methodology"
    APPLICATION = "application"
    INNOVATION_MARKER = "innovation_marker"


class TagSource(str, Enum):
    """How a tag was assigned."""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    USER_OVERRIDE = "user_override"


class CitationType(str, Enum):
    """Types of citation relationships."""
    BUILDS_UPON = "builds_upon"
    CONTRADICTS = "contradicts"
    EXTENDS = "extends"
    APPLIES = "applies"
    SURVEYS = "surveys"
    COMPARES = "compares"


class IngestionStatus(str, Enum):
    """Status of paper ingestion."""
    NOT_QUEUED = "not_queued"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class InsightType(str, Enum):
    """Types of insights extracted from papers."""
    FRAMEWORK = "framework"
    CONCEPT = "concept"
    DATA_POINT = "data_point"
    METHODOLOGY = "methodology"
    LIMITATION = "limitation"
    APPLICATION = "application"
    FUTURE_WORK = "future_work"
    KEY_FINDING = "key_finding"


class EmbeddingType(str, Enum):
    """Types of embeddings."""
    TITLE_ABSTRACT = "title_abstract"
    FULL_TEXT = "full_text"
    INSIGHTS_SUMMARY = "insights_summary"