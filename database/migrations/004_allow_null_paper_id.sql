-- Migration to allow NULL paper_id in conversation_sessions for general conversations
-- This enables conversations that are not tied to specific papers

-- Drop the NOT NULL constraint on paper_id
ALTER TABLE conversation_sessions ALTER COLUMN paper_id DROP NOT NULL;

-- Update the foreign key constraint to allow NULL
ALTER TABLE conversation_sessions DROP CONSTRAINT IF EXISTS conversation_sessions_paper_id_fkey;
ALTER TABLE conversation_sessions ADD CONSTRAINT conversation_sessions_paper_id_fkey 
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE;

-- Add a check constraint to ensure either paper_id is not null OR title is provided for general conversations
ALTER TABLE conversation_sessions ADD CONSTRAINT conversation_sessions_paper_or_title_check 
    CHECK (paper_id IS NOT NULL OR title IS NOT NULL);

-- Update the conversation_context table to also allow NULL paper_id
ALTER TABLE conversation_context ALTER COLUMN paper_id DROP NOT NULL;
ALTER TABLE conversation_context DROP CONSTRAINT IF EXISTS conversation_context_paper_id_fkey;
ALTER TABLE conversation_context ADD CONSTRAINT conversation_context_paper_id_fkey 
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE; 