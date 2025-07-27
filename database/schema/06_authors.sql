-- Authors table for proper relational storage
CREATE TABLE authors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    affiliation TEXT,
    email VARCHAR(255),
    orcid VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, email) -- Prevent exact duplicates
);

-- Junction table for paper-author relationships
CREATE TABLE paper_authors (
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    author_id UUID REFERENCES authors(id) ON DELETE CASCADE,
    author_order INTEGER NOT NULL, -- Maintain author order
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (paper_id, author_id, author_order)
);

-- Indexes for performance
CREATE INDEX idx_authors_name ON authors(name);
CREATE INDEX idx_paper_authors_paper_id ON paper_authors(paper_id);
CREATE INDEX idx_paper_authors_author_id ON paper_authors(author_id);
CREATE INDEX idx_paper_authors_order ON paper_authors(paper_id, author_order); 