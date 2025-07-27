-- Migration: Add PDF binary storage to papers table
-- This allows storing actual PDF files for proper viewing

-- Add PDF content column for binary storage
ALTER TABLE papers ADD COLUMN pdf_content BYTEA;

-- Add index for PDF content queries
CREATE INDEX idx_papers_pdf_content ON papers(pdf_content) WHERE pdf_content IS NOT NULL;

-- Add constraint to ensure PDF content is valid when present
ALTER TABLE papers ADD CONSTRAINT check_pdf_content_valid 
    CHECK (pdf_content IS NULL OR octet_length(pdf_content) > 0);

-- Update the updated_at trigger to handle PDF content changes
CREATE OR REPLACE FUNCTION update_papers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if it exists
DROP TRIGGER IF EXISTS update_papers_updated_at_trigger ON papers;

-- Create trigger for updated_at
CREATE TRIGGER update_papers_updated_at_trigger
    BEFORE UPDATE ON papers
    FOR EACH ROW
    EXECUTE FUNCTION update_papers_updated_at(); 