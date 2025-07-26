-- Notes and Annotations Schema
-- This schema supports comprehensive note-taking with PDF annotations, tags, and relationships

-- Note types enum
CREATE TYPE note_type_enum AS ENUM (
    'general',           -- General notes about the paper
    'annotation',        -- PDF annotation/highlight
    'quote',            -- Direct quote from paper
    'summary',          -- Summary of section/chapter
    'question',         -- Questions about content
    'insight',          -- Personal insights/thoughts
    'criticism',        -- Critical analysis
    'connection',       -- Connection to other papers/concepts
    'todo',             -- Action items
    'definition'        -- Definition of terms
);

-- Note priority enum
CREATE TYPE note_priority_enum AS ENUM (
    'low',
    'medium', 
    'high',
    'critical'
);

-- Notes table - Core note storage
CREATE TABLE IF NOT EXISTS notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    conversation_session_id UUID REFERENCES conversation_sessions(id) ON DELETE SET NULL,
    
    -- Core note content
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    note_type note_type_enum NOT NULL DEFAULT 'general',
    priority note_priority_enum DEFAULT 'medium',
    
    -- PDF annotation data (for annotations)
    page_number INTEGER, -- PDF page number
    x_position DECIMAL(10,4), -- X coordinate on page (0-1 scale)
    y_position DECIMAL(10,4), -- Y coordinate on page (0-1 scale)
    width DECIMAL(10,4), -- Width of annotation area
    height DECIMAL(10,4), -- Height of annotation area
    selected_text TEXT, -- Text selected in PDF
    annotation_color VARCHAR(7), -- Hex color for highlights
    
    -- Metadata
    tags TEXT[] DEFAULT '{}',
    is_public BOOLEAN DEFAULT FALSE, -- For sharing notes
    is_archived BOOLEAN DEFAULT FALSE,
    
    -- Relationships
    parent_note_id UUID REFERENCES notes(id) ON DELETE SET NULL, -- For hierarchical notes
    related_note_ids UUID[] DEFAULT '{}', -- Related notes
    
    -- Context and search
    context_section VARCHAR(255), -- Section of paper (e.g., "Introduction", "Methodology")
    search_vector tsvector, -- Full-text search vector
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Metadata
    metadata JSONB DEFAULT '{}' -- Store additional note metadata
);

-- Note tags table for better tag management
CREATE TABLE IF NOT EXISTS note_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    color VARCHAR(7) DEFAULT '#3B82F6', -- Default blue
    description TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Note relationships table for explicit note connections
CREATE TABLE IF NOT EXISTS note_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_note_id UUID NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    target_note_id UUID NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL, -- 'references', 'contradicts', 'supports', 'extends', etc.
    strength DECIMAL(3,2) DEFAULT 1.0, -- Relationship strength 0-1
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(source_note_id, target_note_id, relationship_type)
);

-- Note collections table for organizing notes
CREATE TABLE IF NOT EXISTS note_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#10B981', -- Default green
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Junction table for notes and collections
CREATE TABLE IF NOT EXISTS note_collection_members (
    note_id UUID NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    collection_id UUID NOT NULL REFERENCES note_collections(id) ON DELETE CASCADE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (note_id, collection_id)
);

-- Note templates table for reusable note structures
CREATE TABLE IF NOT EXISTS note_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_content TEXT NOT NULL, -- Template with placeholders
    note_type note_type_enum NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_notes_paper_id ON notes(paper_id);
CREATE INDEX IF NOT EXISTS idx_notes_conversation_session_id ON notes(conversation_session_id);
CREATE INDEX IF NOT EXISTS idx_notes_note_type ON notes(note_type);
CREATE INDEX IF NOT EXISTS idx_notes_priority ON notes(priority);
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notes_updated_at ON notes(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_notes_page_number ON notes(paper_id, page_number);
CREATE INDEX IF NOT EXISTS idx_notes_parent_id ON notes(parent_note_id);
CREATE INDEX IF NOT EXISTS idx_notes_archived ON notes(is_archived);
CREATE INDEX IF NOT EXISTS idx_notes_public ON notes(is_public);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_notes_search_vector ON notes USING GIN(search_vector);

-- Tag indexes
CREATE INDEX IF NOT EXISTS idx_notes_tags ON notes USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_note_tags_name ON note_tags(name);
CREATE INDEX IF NOT EXISTS idx_note_tags_usage ON note_tags(usage_count DESC);

-- Relationship indexes
CREATE INDEX IF NOT EXISTS idx_note_relationships_source ON note_relationships(source_note_id);
CREATE INDEX IF NOT EXISTS idx_note_relationships_target ON note_relationships(target_note_id);
CREATE INDEX IF NOT EXISTS idx_note_relationships_type ON note_relationships(relationship_type);

-- Collection indexes
CREATE INDEX IF NOT EXISTS idx_note_collections_name ON note_collections(name);
CREATE INDEX IF NOT EXISTS idx_note_collection_members_note ON note_collection_members(note_id);
CREATE INDEX IF NOT EXISTS idx_note_collection_members_collection ON note_collection_members(collection_id);

-- Template indexes
CREATE INDEX IF NOT EXISTS idx_note_templates_name ON note_templates(name);
CREATE INDEX IF NOT EXISTS idx_note_templates_type ON note_templates(note_type);
CREATE INDEX IF NOT EXISTS idx_note_templates_default ON note_templates(is_default);

-- Function to update note search vector
CREATE OR REPLACE FUNCTION update_note_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.content, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.selected_text, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.context_section, '')), 'D');
    
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update search vector
DROP TRIGGER IF EXISTS trigger_update_note_search_vector ON notes;
CREATE TRIGGER trigger_update_note_search_vector
    BEFORE INSERT OR UPDATE ON notes
    FOR EACH ROW
    EXECUTE FUNCTION update_note_search_vector();

-- Function to update tag usage count
CREATE OR REPLACE FUNCTION update_tag_usage_count()
RETURNS TRIGGER AS $$
BEGIN
    -- Update usage count for all tags in the note
    IF TG_OP = 'INSERT' THEN
        UPDATE note_tags 
        SET usage_count = usage_count + 1, updated_at = CURRENT_TIMESTAMP
        WHERE name = ANY(NEW.tags);
    ELSIF TG_OP = 'UPDATE' THEN
        -- Remove count from old tags
        UPDATE note_tags 
        SET usage_count = usage_count - 1, updated_at = CURRENT_TIMESTAMP
        WHERE name = ANY(OLD.tags);
        -- Add count to new tags
        UPDATE note_tags 
        SET usage_count = usage_count + 1, updated_at = CURRENT_TIMESTAMP
        WHERE name = ANY(NEW.tags);
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE note_tags 
        SET usage_count = usage_count - 1, updated_at = CURRENT_TIMESTAMP
        WHERE name = ANY(OLD.tags);
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update tag usage counts
DROP TRIGGER IF EXISTS trigger_update_tag_usage_count ON notes;
CREATE TRIGGER trigger_update_tag_usage_count
    AFTER INSERT OR UPDATE OR DELETE ON notes
    FOR EACH ROW
    EXECUTE FUNCTION update_tag_usage_count();

-- Function to get note statistics
CREATE OR REPLACE FUNCTION get_note_statistics(paper_uuid UUID)
RETURNS JSON AS $$
DECLARE
    stats JSON;
BEGIN
    SELECT json_build_object(
        'total_notes', COUNT(*),
        'notes_by_type', json_object_agg(note_type, count) FILTER (WHERE note_type IS NOT NULL),
        'notes_by_priority', json_object_agg(priority, count) FILTER (WHERE priority IS NOT NULL),
        'most_used_tags', (
            SELECT json_agg(json_build_object('tag', tag, 'count', tag_count))
            FROM (
                SELECT unnest(tags) as tag, COUNT(*) as tag_count
                FROM notes 
                WHERE paper_id = paper_uuid AND tags IS NOT NULL
                GROUP BY tag
                ORDER BY tag_count DESC
                LIMIT 10
            ) tag_stats
        ),
        'recent_activity', (
            SELECT json_agg(json_build_object('date', date_trunc('day', created_at), 'count', count))
            FROM (
                SELECT date_trunc('day', created_at) as created_at, COUNT(*) as count
                FROM notes 
                WHERE paper_id = paper_uuid
                GROUP BY date_trunc('day', created_at)
                ORDER BY date_trunc('day', created_at) DESC
                LIMIT 30
            ) activity_stats
        )
    ) INTO stats
    FROM (
        SELECT 
            note_type,
            priority,
            COUNT(*) as count
        FROM notes 
        WHERE paper_id = paper_uuid
        GROUP BY note_type, priority
    ) type_priority_stats;
    
    -- Add pages_with_annotations separately
    SELECT json_build_object(
        'total_notes', (stats->>'total_notes')::int,
        'notes_by_type', stats->'notes_by_type',
        'notes_by_priority', stats->'notes_by_priority',
        'pages_with_annotations', COUNT(DISTINCT page_number) FILTER (WHERE page_number IS NOT NULL),
        'most_used_tags', stats->'most_used_tags',
        'recent_activity', stats->'recent_activity'
    ) INTO stats
    FROM notes 
    WHERE paper_id = paper_uuid;
    
    RETURN stats;
END;
$$ LANGUAGE plpgsql;

-- View for note summaries with paper info
CREATE OR REPLACE VIEW note_summaries AS
SELECT 
    n.id,
    n.paper_id,
    p.title as paper_title,
    n.title as note_title,
    n.content,
    n.note_type,
    n.priority,
    n.page_number,
    n.tags,
    n.created_at,
    n.updated_at,
    n.is_archived,
    n.is_public,
    -- Get related notes count
    (SELECT COUNT(*) FROM note_relationships WHERE source_note_id = n.id OR target_note_id = n.id) as relationship_count,
    -- Get collections count
    (SELECT COUNT(*) FROM note_collection_members WHERE note_id = n.id) as collection_count
FROM notes n
JOIN papers p ON n.paper_id = p.id
ORDER BY n.updated_at DESC;

-- Insert default note templates
INSERT INTO note_templates (name, description, template_content, note_type, is_default) VALUES
('Question Template', 'Template for asking questions about paper content', 
 'Question: [Your question here]\n\nContext: [Relevant section/page]\n\nThoughts: [Your initial thoughts]', 
 'question', true),
 
('Quote Template', 'Template for capturing important quotes', 
 'Quote: "[Exact quote from paper]"\n\nPage: [Page number]\n\nWhy Important: [Your reasoning]\n\nConnection: [How it relates to other concepts]', 
 'quote', true),
 
('Insight Template', 'Template for personal insights and thoughts', 
 'Insight: [Your key insight]\n\nEvidence: [Supporting evidence from paper]\n\nImplications: [What this means]\n\nQuestions: [Follow-up questions]', 
 'insight', true),
 
('Criticism Template', 'Template for critical analysis', 
 'Criticism: [What you disagree with or find problematic]\n\nReasoning: [Why you think this]\n\nAlternative: [What could be done differently]\n\nEvidence: [Supporting evidence]', 
 'criticism', true),
 
('Connection Template', 'Template for connecting ideas across papers', 
 'Connection: [What you''re connecting]\n\nPaper A: [First paper/concept]\n\nPaper B: [Second paper/concept]\n\nRelationship: [How they relate]\n\nInsight: [What this connection reveals]', 
 'connection', true),
 
('Todo Template', 'Template for action items', 
 'Action: [What needs to be done]\n\nPriority: [High/Medium/Low]\n\nDeadline: [When it needs to be done]\n\nNotes: [Additional context]', 
 'todo', true)
ON CONFLICT DO NOTHING; 