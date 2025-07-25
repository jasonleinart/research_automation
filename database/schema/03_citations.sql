-- Citations between papers in our system
CREATE TABLE citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    citing_paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    cited_paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    citation_context TEXT, -- Surrounding text where citation appears
    citation_type citation_type_enum,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(citing_paper_id, cited_paper_id)
);

-- External citations (papers not in our system yet)
CREATE TABLE external_citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    citing_paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    title TEXT,
    authors TEXT,
    publication_year INTEGER,
    venue TEXT,
    external_citation_count INTEGER, -- How many times this external paper is cited
    priority_score DECIMAL(3,2), -- Priority for backfill ingestion
    ingestion_status ingestion_status_enum DEFAULT 'not_queued',
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_priority_score CHECK (priority_score >= 0.00 AND priority_score <= 1.00)
);