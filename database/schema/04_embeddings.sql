-- Vector embeddings for papers
CREATE TABLE paper_embeddings (
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    embedding_type embedding_type_enum,
    embedding VECTOR(1536), -- Assuming OpenAI embeddings
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (paper_id, embedding_type)
);

-- Vector embeddings for insights
CREATE TABLE insight_embeddings (
    insight_id UUID REFERENCES insights(id) ON DELETE CASCADE,
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (insight_id)
);