-- Performance indexes

-- Core search indexes
CREATE INDEX idx_papers_publication_date ON papers(publication_date DESC);
CREATE INDEX idx_papers_paper_type ON papers(paper_type);
CREATE INDEX idx_papers_novelty_score ON papers(novelty_score DESC);
CREATE INDEX idx_papers_analysis_status ON papers(analysis_status);
CREATE INDEX idx_papers_arxiv_id ON papers(arxiv_id);
CREATE INDEX idx_papers_title ON papers USING gin(to_tsvector('english', title));
CREATE INDEX idx_papers_abstract ON papers USING gin(to_tsvector('english', abstract));

-- Tag search indexes
CREATE INDEX idx_tags_category ON tags(category);
CREATE INDEX idx_tags_name ON tags(name);
CREATE INDEX idx_paper_tags_confidence ON paper_tags(confidence DESC);

-- Citation indexes
CREATE INDEX idx_citations_citing_paper ON citations(citing_paper_id);
CREATE INDEX idx_citations_cited_paper ON citations(cited_paper_id);
CREATE INDEX idx_external_citations_priority ON external_citations(priority_score DESC);

-- Insight indexes
CREATE INDEX idx_insights_paper_id ON insights(paper_id);
CREATE INDEX idx_insights_type ON insights(insight_type);
CREATE INDEX idx_insights_confidence ON insights(confidence DESC);

-- Vector similarity indexes (using pgvector)
CREATE INDEX idx_paper_embeddings_vector ON paper_embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_insight_embeddings_vector ON insight_embeddings USING ivfflat (embedding vector_cosine_ops);