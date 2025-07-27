-- Conversation persistence schema
-- This schema stores chat conversations, sessions, and messages for the conversational agent

-- Conversation sessions table
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    title VARCHAR(255), -- Optional title for the conversation
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    is_archived BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}' -- Store additional session metadata
);

-- Conversation messages table
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    confidence DECIMAL(3,2), -- For assistant messages, store confidence score
    grounded BOOLEAN, -- Whether the response was grounded
    sources TEXT[], -- Array of sources referenced
    limitations TEXT, -- Any limitations noted in the response
    metadata JSONB DEFAULT '{}' -- Store additional message metadata
);

-- Conversation context table (stores paper context and related info)
CREATE TABLE IF NOT EXISTS conversation_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    related_paper_ids UUID[], -- Array of related paper IDs
    user_interests TEXT[], -- Tracked user interests
    conversation_focus TEXT, -- Current focus of conversation
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_paper_id ON conversation_sessions(paper_id);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_created_at ON conversation_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_last_activity ON conversation_sessions(last_activity DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_archived ON conversation_sessions(is_archived);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_session_id ON conversation_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_created_at ON conversation_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_role ON conversation_messages(role);

CREATE INDEX IF NOT EXISTS idx_conversation_context_session_id ON conversation_context(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_context_paper_id ON conversation_context(paper_id);

-- Function to update session activity and message count
CREATE OR REPLACE FUNCTION update_session_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversation_sessions 
    SET 
        last_activity = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP,
        message_count = (
            SELECT COUNT(*) 
            FROM conversation_messages 
            WHERE session_id = NEW.session_id
        )
    WHERE id = NEW.session_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update session activity when messages are added
DROP TRIGGER IF EXISTS trigger_update_session_activity ON conversation_messages;
CREATE TRIGGER trigger_update_session_activity
    AFTER INSERT ON conversation_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_session_activity();

-- Function to generate conversation titles based on first user message
CREATE OR REPLACE FUNCTION generate_conversation_title(session_uuid UUID)
RETURNS TEXT AS $$
DECLARE
    first_message TEXT;
    paper_title TEXT;
    generated_title TEXT;
BEGIN
    -- Get the first user message
    SELECT content INTO first_message
    FROM conversation_messages
    WHERE session_id = session_uuid AND role = 'user'
    ORDER BY created_at ASC
    LIMIT 1;
    
    -- Get the paper title
    SELECT p.title INTO paper_title
    FROM conversation_sessions cs
    JOIN papers p ON cs.paper_id = p.id
    WHERE cs.id = session_uuid;
    
    -- Generate title based on first message and paper
    IF first_message IS NOT NULL THEN
        generated_title := CASE
            WHEN LENGTH(first_message) > 50 THEN LEFT(first_message, 47) || '...'
            ELSE first_message
        END;
    ELSE
        generated_title := 'Chat about ' || COALESCE(LEFT(paper_title, 30), 'Unknown Paper');
    END IF;
    
    RETURN generated_title;
END;
$$ LANGUAGE plpgsql;

-- View for conversation summaries with paper info
CREATE OR REPLACE VIEW conversation_summaries AS
SELECT 
    cs.id,
    cs.paper_id,
    p.title as paper_title,
    ARRAY[]::text[] as author_names,
    cs.title as conversation_title,
    cs.created_at,
    cs.updated_at,
    cs.last_activity,
    cs.message_count,
    cs.is_archived,
    -- Get first user message as preview
    (SELECT content FROM conversation_messages 
     WHERE session_id = cs.id AND role = 'user' 
     ORDER BY created_at ASC LIMIT 1) as first_message,
    -- Get last message timestamp
    (SELECT created_at FROM conversation_messages 
     WHERE session_id = cs.id 
     ORDER BY created_at DESC LIMIT 1) as last_message_at
FROM conversation_sessions cs
JOIN papers p ON cs.paper_id = p.id
ORDER BY cs.last_activity DESC;