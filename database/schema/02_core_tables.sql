-- Core papers table
CREATE TABLE papers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    arxiv_id VARCHAR(50) UNIQUE,
    title TEXT NOT NULL,
    abstract TEXT,
    authors JSONB, -- Array of author objects with names, affiliations
    publication_date DATE,
    categories JSONB, -- ArXiv categories
    pdf_url TEXT,
    full_text TEXT,
    citation_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Classification fields
    paper_type paper_type_enum,
    evidence_strength evidence_strength_enum,
    novelty_score DECIMAL(3,2), -- 0.00 to 1.00
    practical_applicability practical_applicability_enum,
    
    -- Analysis metadata
    analysis_status analysis_status_enum DEFAULT 'pending',
    analysis_confidence DECIMAL(3,2),
    extraction_version INTEGER DEFAULT 1,
    
    -- Content generation tracking
    content_generated BOOLEAN DEFAULT FALSE,
    content_approved BOOLEAN DEFAULT FALSE,
    
    -- Source tracking
    ingestion_source VARCHAR(50), -- 'manual_arxiv_url', 'manual_pdf_upload', etc.
    
    CONSTRAINT valid_novelty_score CHECK (novelty_score >= 0.00 AND novelty_score <= 1.00),
    CONSTRAINT valid_analysis_confidence CHECK (analysis_confidence >= 0.00 AND analysis_confidence <= 1.00)
);

-- Tags system
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    category tag_category_enum NOT NULL,
    description TEXT,
    parent_tag_id UUID REFERENCES tags(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Paper-tag relationships
CREATE TABLE paper_tags (
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    confidence DECIMAL(3,2), -- How confident we are in this tag
    source tag_source_enum, -- How this tag was assigned
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (paper_id, tag_id),
    CONSTRAINT valid_tag_confidence CHECK (confidence >= 0.00 AND confidence <= 1.00)
);

-- Extracted insights
CREATE TABLE insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    insight_type insight_type_enum NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    content JSONB, -- Structured content specific to insight type
    confidence DECIMAL(3,2),
    extraction_method VARCHAR(50), -- Which analysis method extracted this
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_insight_confidence CHECK (confidence >= 0.00 AND confidence <= 1.00)
);

-- Link insights to tags
CREATE TABLE insight_tags (
    insight_id UUID REFERENCES insights(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (insight_id, tag_id)
);