-- Create all enum types first

CREATE TYPE paper_type_enum AS ENUM (
    'conceptual_framework', 'survey_review', 'empirical_study', 
    'case_study', 'benchmark_comparison', 'position_paper', 'tutorial_methodology'
);

CREATE TYPE evidence_strength_enum AS ENUM (
    'experimental', 'theoretical', 'observational', 'anecdotal'
);

CREATE TYPE practical_applicability_enum AS ENUM (
    'high', 'medium', 'low', 'theoretical_only'
);

CREATE TYPE analysis_status_enum AS ENUM (
    'pending', 'in_progress', 'completed', 'failed', 'manual_review'
);

CREATE TYPE tag_category_enum AS ENUM (
    'research_domain', 'concept', 'methodology', 'application', 'innovation_marker'
);

CREATE TYPE tag_source_enum AS ENUM (
    'automatic', 'manual', 'user_override'
);

CREATE TYPE citation_type_enum AS ENUM (
    'builds_upon', 'contradicts', 'extends', 'applies', 'surveys', 'compares'
);

CREATE TYPE ingestion_status_enum AS ENUM (
    'not_queued', 'queued', 'in_progress', 'completed', 'failed'
);

CREATE TYPE insight_type_enum AS ENUM (
    'framework', 'concept', 'data_point', 'methodology', 'limitation', 
    'application', 'future_work', 'key_finding'
);

CREATE TYPE embedding_type_enum AS ENUM (
    'title_abstract', 'full_text', 'insights_summary'
);