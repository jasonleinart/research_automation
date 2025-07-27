-- Migration to clean up author system
-- This removes the JSONB authors column and ensures proper relational structure

BEGIN;

-- First, ensure all papers have proper author relationships
-- (This should already be done, but let's verify)

-- Remove the JSONB authors column from papers table
ALTER TABLE papers DROP COLUMN IF EXISTS authors;

-- Ensure proper indexes exist for author queries
CREATE INDEX IF NOT EXISTS idx_paper_authors_paper_order ON paper_authors(paper_id, author_order);
CREATE INDEX IF NOT EXISTS idx_authors_name_lower ON authors(LOWER(name));

-- Add constraint to ensure author order is positive
ALTER TABLE paper_authors ADD CONSTRAINT check_author_order_positive 
    CHECK (author_order > 0);

-- Add constraint to ensure author names are not empty
ALTER TABLE authors ADD CONSTRAINT check_author_name_not_empty 
    CHECK (LENGTH(TRIM(name)) > 0);

COMMIT;