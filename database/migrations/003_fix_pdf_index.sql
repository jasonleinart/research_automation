-- Migration: Remove PDF content index to fix large file storage issue
-- The index on BYTEA column is causing issues with large PDF files

-- Drop the problematic index
DROP INDEX IF EXISTS idx_papers_pdf_content;

-- Add a comment explaining why we don't index PDF content
COMMENT ON COLUMN papers.pdf_content IS 'PDF binary content - not indexed due to size constraints'; 