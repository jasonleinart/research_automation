"""
Conversation Repository for persistent conversation storage and retrieval.
"""

import json
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from .connection import db_manager
from ..models.conversation import ConversationSession, ConversationMessage

logger = logging.getLogger(__name__)


class ConversationRepository:
    """Repository for managing conversation persistence."""
    
    async def create_session(self, paper_id: Optional[UUID], title: Optional[str] = None) -> ConversationSession:
        """Create a new conversation session."""
        query = """
            INSERT INTO conversation_sessions (paper_id, title)
            VALUES ($1, $2)
            RETURNING id, paper_id, title, created_at, updated_at, last_activity, message_count, is_archived
        """
        
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, paper_id, title)
            
            session = ConversationSession(
                session_id=row['id'],
                paper_id=row['paper_id'],
                title=row['title'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                last_activity=row['last_activity'],
                message_count=row['message_count'],
                is_archived=row['is_archived']
            )
            
            if paper_id:
                logger.info(f"Created conversation session {session.session_id} for paper {paper_id}")
            else:
                logger.info(f"Created general conversation session {session.session_id}")
            return session
    
    async def get_session(self, session_id: UUID) -> Optional[ConversationSession]:
        """Get a conversation session by ID."""
        query = """
            SELECT id, paper_id, title, created_at, updated_at, last_activity, 
                   message_count, is_archived, metadata
            FROM conversation_sessions
            WHERE id = $1
        """
        
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, session_id)
            
            if not row:
                return None
            
            return ConversationSession(
                session_id=row['id'],
                paper_id=row['paper_id'],
                title=row['title'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                last_activity=row['last_activity'],
                message_count=row['message_count'],
                is_archived=row['is_archived'],
                metadata=row['metadata'] or {}
            )
    
    async def add_message(
        self, 
        session_id: UUID, 
        role: str, 
        content: str,
        confidence: Optional[float] = None,
        grounded: Optional[bool] = None,
        sources: Optional[List[str]] = None,
        limitations: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationMessage:
        """Add a message to a conversation session."""
        query = """
            INSERT INTO conversation_messages 
            (session_id, role, content, confidence, grounded, sources, limitations, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, session_id, role, content, created_at, confidence, grounded, sources, limitations, metadata
        """
        
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(
                query, 
                session_id, 
                role, 
                content, 
                confidence, 
                grounded, 
                sources or [], 
                limitations,
                json.dumps(metadata or {})
            )
            
            message = ConversationMessage(
                id=row['id'],
                session_id=row['session_id'],
                role=row['role'],
                content=row['content'],
                timestamp=row['created_at'],
                confidence=row['confidence'],
                grounded=row['grounded'],
                sources=row['sources'] or [],
                limitations=row['limitations'],
                metadata=row['metadata'] or {}
            )
            
            logger.debug(f"Added {role} message to session {session_id}")
            return message
    
    async def get_messages(self, session_id: UUID, limit: Optional[int] = None) -> List[ConversationMessage]:
        """Get messages for a conversation session."""
        query = """
            SELECT id, session_id, role, content, created_at, confidence, grounded, sources, limitations, metadata
            FROM conversation_messages
            WHERE session_id = $1
            ORDER BY created_at ASC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, session_id)
            
            messages = []
            for row in rows:
                messages.append(ConversationMessage(
                    id=row['id'],
                    session_id=row['session_id'],
                    role=row['role'],
                    content=row['content'],
                    timestamp=row['created_at'],
                    confidence=row['confidence'],
                    grounded=row['grounded'],
                    sources=row['sources'] or [],
                    limitations=row['limitations'],
                    metadata=row['metadata'] or {}
                ))
            
            return messages
    
    async def get_recent_messages(self, session_id: UUID, limit: int = 10) -> List[ConversationMessage]:
        """Get recent messages for a conversation session."""
        query = """
            SELECT id, session_id, role, content, created_at, confidence, grounded, sources, limitations, metadata
            FROM conversation_messages
            WHERE session_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, session_id, limit)
            
            messages = []
            for row in reversed(rows):  # Reverse to get chronological order
                messages.append(ConversationMessage(
                    id=row['id'],
                    session_id=row['session_id'],
                    role=row['role'],
                    content=row['content'],
                    timestamp=row['created_at'],
                    confidence=row['confidence'],
                    grounded=row['grounded'],
                    sources=row['sources'] or [],
                    limitations=row['limitations'],
                    metadata=row['metadata'] or {}
                ))
            
            return messages
    
    async def list_sessions(
        self, 
        paper_id: Optional[UUID] = None, 
        limit: int = 50,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """List conversation sessions with summary information."""
        query = """
            SELECT * FROM conversation_summaries
            WHERE ($1::UUID IS NULL OR paper_id = $1)
            AND ($2 OR NOT is_archived)
            ORDER BY last_activity DESC
            LIMIT $3
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, paper_id, include_archived, limit)
            
            sessions = []
            for row in rows:
                sessions.append({
                    'id': str(row['id']),
                    'paper_id': str(row['paper_id']),
                    'paper_title': row['paper_title'],
                    'author_names': row['author_names'],
                    'conversation_title': row['conversation_title'],
                    'created_at': row['created_at'].isoformat(),
                    'updated_at': row['updated_at'].isoformat(),
                    'last_activity': row['last_activity'].isoformat(),
                    'message_count': row['message_count'],
                    'is_archived': row['is_archived'],
                    'first_message': row['first_message'],
                    'last_message_at': row['last_message_at'].isoformat() if row['last_message_at'] else None
                })
            
            return sessions
    
    async def update_session_title(self, session_id: UUID, title: str) -> bool:
        """Update the title of a conversation session."""
        query = """
            UPDATE conversation_sessions
            SET title = $1, updated_at = CURRENT_TIMESTAMP
            WHERE id = $2
        """
        
        async with db_manager.get_connection() as conn:
            result = await conn.execute(query, title, session_id)
            return result == "UPDATE 1"
    
    async def auto_generate_title(self, session_id: UUID) -> Optional[str]:
        """Auto-generate a title for a conversation session based on first message."""
        query = "SELECT generate_conversation_title($1)"
        
        async with db_manager.get_connection() as conn:
            result = await conn.fetchval(query, session_id)
            
            if result:
                await self.update_session_title(session_id, result)
                return result
            
            return None
    
    async def archive_session(self, session_id: UUID) -> bool:
        """Archive a conversation session."""
        query = """
            UPDATE conversation_sessions
            SET is_archived = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """
        
        async with db_manager.get_connection() as conn:
            result = await conn.execute(query, session_id)
            return result == "UPDATE 1"
    
    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a conversation session and all its messages."""
        query = "DELETE FROM conversation_sessions WHERE id = $1"
        
        async with db_manager.get_connection() as conn:
            result = await conn.execute(query, session_id)
            return result == "DELETE 1"
    
    async def search_conversations(
        self, 
        query: str, 
        paper_id: Optional[UUID] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search conversations by content."""
        search_query = """
            SELECT DISTINCT cs.*, p.title as paper_title
            FROM conversation_sessions cs
            JOIN papers p ON cs.paper_id = p.id
            JOIN conversation_messages cm ON cs.id = cm.session_id
            WHERE cm.content ILIKE $1
            AND ($2::UUID IS NULL OR cs.paper_id = $2)
            AND NOT cs.is_archived
            ORDER BY cs.last_activity DESC
            LIMIT $3
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(search_query, f'%{query}%', paper_id, limit)
            
            results = []
            for row in rows:
                results.append({
                    'id': str(row['id']),
                    'paper_id': str(row['paper_id']),
                    'paper_title': row['paper_title'],
                    'conversation_title': row['title'],
                    'created_at': row['created_at'].isoformat(),
                    'last_activity': row['last_activity'].isoformat(),
                    'message_count': row['message_count']
                })
            
            return results
    
    async def get_conversation_stats(self) -> Dict[str, Any]:
        """Get statistics about conversations."""
        query = """
            SELECT 
                COUNT(*) as total_sessions,
                COUNT(*) FILTER (WHERE NOT is_archived) as active_sessions,
                COUNT(*) FILTER (WHERE is_archived) as archived_sessions,
                AVG(message_count) as avg_messages_per_session,
                COUNT(DISTINCT paper_id) as papers_with_conversations,
                (SELECT COUNT(*) FROM conversation_messages) as total_messages
            FROM conversation_sessions
        """
        
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(query)
            
            return {
                'total_sessions': row['total_sessions'],
                'active_sessions': row['active_sessions'],
                'archived_sessions': row['archived_sessions'],
                'avg_messages_per_session': float(row['avg_messages_per_session']) if row['avg_messages_per_session'] else 0,
                'papers_with_conversations': row['papers_with_conversations'],
                'total_messages': row['total_messages']
            }