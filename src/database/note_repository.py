"""
Repository for note-related database operations.
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from .connection import db_manager
from ..models.note import Note, NoteTag, NoteRelationship, NoteCollection, NoteTemplate
from ..models.enums import NoteType, NotePriority


class NoteRepository:
    """Repository for note operations."""
    
    def __init__(self):
        pass

    def _from_row(self, row: Dict[str, Any]) -> Note:
        """Convert database row to Note instance."""
        # Parse arrays and JSON fields
        tags = row.get('tags', [])
        if isinstance(tags, str):
            tags = json.loads(tags) if tags else []
        
        related_note_ids = row.get('related_note_ids', [])
        if isinstance(related_note_ids, str):
            related_note_ids = json.loads(related_note_ids) if related_note_ids else []
        
        metadata = row.get('metadata', {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata) if metadata else {}
        
        return Note.from_dict({
            **row,
            'tags': tags,
            'related_note_ids': related_note_ids,
            'metadata': metadata
        })

    async def create_note(self, note: Note) -> Note:
        """Create a new note."""
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow("""
                INSERT INTO notes (
                    id, paper_id, conversation_session_id, title, content,
                    note_type, priority, page_number, x_position, y_position,
                    width, height, selected_text, annotation_color, tags,
                    is_public, is_archived, parent_note_id, related_note_ids,
                    context_section, created_at, updated_at, metadata
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                    $16, $17, $18, $19, $20, $21, $22, $23
                ) RETURNING *
            """, note.id, note.paper_id, note.conversation_session_id, note.title, note.content,
                note.note_type.value, note.priority.value, note.page_number, note.x_position, note.y_position,
                note.width, note.height, note.selected_text, note.annotation_color, note.tags,
                note.is_public, note.is_archived, note.parent_note_id, note.related_note_ids,
                note.context_section, note.created_at, note.updated_at, json.dumps(note.metadata))
            return self._from_row(dict(row))

    async def get_note(self, note_id: UUID) -> Optional[Note]:
        """Get a note by ID."""
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow("SELECT * FROM notes WHERE id = $1", note_id)
            return self._from_row(dict(row)) if row else None

    async def update_note(self, note: Note) -> Note:
        """Update an existing note."""
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow("""
                UPDATE notes SET
                    title = $2, content = $3, note_type = $4, priority = $5,
                    page_number = $6, x_position = $7, y_position = $8, width = $9, height = $10,
                    selected_text = $11, annotation_color = $12, tags = $13, is_public = $14,
                    is_archived = $15, parent_note_id = $16, related_note_ids = $17,
                    context_section = $18, updated_at = $19, metadata = $20
                WHERE id = $1 RETURNING *
            """, note.id, note.title, note.content, note.note_type.value, note.priority.value,
                note.page_number, note.x_position, note.y_position, note.width, note.height,
                note.selected_text, note.annotation_color, note.tags, note.is_public,
                note.is_archived, note.parent_note_id, note.related_note_ids,
                note.context_section, datetime.now(), json.dumps(note.metadata))
            return self._from_row(dict(row))

    async def delete_note(self, note_id: UUID) -> bool:
        """Delete a note."""
        async with db_manager.get_connection() as conn:
            result = await conn.execute("DELETE FROM notes WHERE id = $1", note_id)
            return result == "DELETE 1"

    async def get_notes_by_paper(self, paper_id: UUID, limit: Optional[int] = None) -> List[Note]:
        """Get all notes for a specific paper."""
        query = "SELECT * FROM notes WHERE paper_id = $1 ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, paper_id)
            return [self._from_row(dict(row)) for row in rows]

    async def get_notes_by_page(self, paper_id: UUID, page_number: int) -> List[Note]:
        """Get all notes for a specific page of a paper."""
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT * FROM notes 
                WHERE paper_id = $1 AND page_number = $2 
                ORDER BY y_position, x_position
            """, paper_id, page_number)
            return [self._from_row(dict(row)) for row in rows]

    async def search_notes(self, query: str, paper_id: Optional[UUID] = None, limit: int = 50) -> List[Note]:
        """Search notes using full-text search."""
        search_query = f"SELECT *, ts_rank(search_vector, plainto_tsquery('english', $1)) as rank FROM notes WHERE search_vector @@ plainto_tsquery('english', $1)"
        params = [query]
        
        if paper_id:
            search_query += " AND paper_id = $2"
            params.append(paper_id)
        
        search_query += " ORDER BY rank DESC LIMIT $3"
        params.append(limit)
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(search_query, *params)
            return [self._from_row(dict(row)) for row in rows]

    async def get_notes_by_conversation(self, conversation_session_id: UUID) -> List[Note]:
        """Get all notes from a specific conversation session."""
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT * FROM notes 
                WHERE conversation_session_id = $1 
                ORDER BY created_at DESC
            """, conversation_session_id)
            return [self._from_row(dict(row)) for row in rows]

    async def get_notes_by_tag(self, tag: str, paper_id: Optional[UUID] = None) -> List[Note]:
        """Get all notes with a specific tag."""
        query = "SELECT * FROM notes WHERE $1 = ANY(tags)"
        params = [tag]
        
        if paper_id:
            query += " AND paper_id = $2"
            params.append(paper_id)
        
        query += " ORDER BY created_at DESC"
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, *params)
            return [self._from_row(dict(row)) for row in rows]

    async def create_tag(self, tag: NoteTag) -> NoteTag:
        """Create a new tag."""
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow("""
                INSERT INTO note_tags (name, color, description, usage_count)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (name) DO UPDATE SET
                    color = EXCLUDED.color,
                    description = EXCLUDED.description,
                    usage_count = note_tags.usage_count + 1
                RETURNING *
            """, tag.name, tag.color, tag.description, tag.usage_count)
            return NoteTag.from_dict(dict(row))

    async def get_all_tags(self) -> List[NoteTag]:
        """Get all tags."""
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch("SELECT * FROM note_tags ORDER BY usage_count DESC")
            return [NoteTag.from_dict(dict(row)) for row in rows]

    async def get_popular_tags(self, limit: int = 10) -> List[NoteTag]:
        """Get the most popular tags."""
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT * FROM note_tags 
                ORDER BY usage_count DESC 
                LIMIT $1
            """, limit)
            return [NoteTag.from_dict(dict(row)) for row in rows]

    async def create_relationship(self, relationship: NoteRelationship) -> NoteRelationship:
        """Create a relationship between two notes."""
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow("""
                INSERT INTO note_relationships (source_note_id, target_note_id, relationship_type, strength)
                VALUES ($1, $2, $3, $4)
                RETURNING *
            """, relationship.source_note_id, relationship.target_note_id, 
                relationship.relationship_type, relationship.strength)
            return NoteRelationship.from_dict(dict(row))

    async def get_note_relationships(self, note_id: UUID) -> List[NoteRelationship]:
        """Get all relationships for a note."""
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT * FROM note_relationships 
                WHERE source_note_id = $1 OR target_note_id = $1
                ORDER BY strength DESC
            """, note_id)
            return [NoteRelationship.from_dict(dict(row)) for row in rows]

    async def delete_relationship(self, relationship_id: UUID) -> bool:
        """Delete a relationship."""
        async with db_manager.get_connection() as conn:
            result = await conn.execute("DELETE FROM note_relationships WHERE id = $1", relationship_id)
            return result == "DELETE 1"

    async def create_collection(self, collection: NoteCollection) -> NoteCollection:
        """Create a new collection."""
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow("""
                INSERT INTO note_collections (name, description, color, is_public)
                VALUES ($1, $2, $3, $4)
                RETURNING *
            """, collection.name, collection.description, collection.color, collection.is_public)
            return NoteCollection.from_dict(dict(row))

    async def get_collection(self, collection_id: UUID) -> Optional[NoteCollection]:
        """Get a collection by ID."""
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow("SELECT * FROM note_collections WHERE id = $1", collection_id)
            return NoteCollection.from_dict(dict(row)) if row else None

    async def get_all_collections(self) -> List[NoteCollection]:
        """Get all collections."""
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch("SELECT * FROM note_collections ORDER BY name")
            return [NoteCollection.from_dict(dict(row)) for row in rows]

    async def add_note_to_collection(self, note_id: UUID, collection_id: UUID) -> bool:
        """Add a note to a collection."""
        async with db_manager.get_connection() as conn:
            try:
                await conn.execute("""
                    INSERT INTO note_collection_members (note_id, collection_id)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                """, note_id, collection_id)
                return True
            except Exception:
                return False

    async def remove_note_from_collection(self, note_id: UUID, collection_id: UUID) -> bool:
        """Remove a note from a collection."""
        async with db_manager.get_connection() as conn:
            result = await conn.execute("""
                DELETE FROM note_collection_members 
                WHERE note_id = $1 AND collection_id = $2
            """, note_id, collection_id)
            return result == "DELETE 1"

    async def get_notes_in_collection(self, collection_id: UUID) -> List[Note]:
        """Get all notes in a collection."""
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT n.* FROM notes n
                JOIN note_collection_members ncm ON n.id = ncm.note_id
                WHERE ncm.collection_id = $1
                ORDER BY n.created_at DESC
            """, collection_id)
            return [self._from_row(dict(row)) for row in rows]

    async def get_templates(self, note_type: Optional[NoteType] = None) -> List[NoteTemplate]:
        """Get note templates, optionally filtered by type."""
        query = "SELECT * FROM note_templates"
        params = []
        
        if note_type:
            query += " WHERE note_type = $1"
            params.append(note_type.value)
        
        query += " ORDER BY is_default DESC, name"
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, *params)
            return [NoteTemplate.from_dict(dict(row)) for row in rows]

    async def get_default_template(self, note_type: NoteType) -> Optional[NoteTemplate]:
        """Get the default template for a note type."""
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM note_templates 
                WHERE note_type = $1 AND is_default = true
                LIMIT 1
            """, note_type.value)
            return NoteTemplate.from_dict(dict(row)) if row else None

    async def get_note_statistics(self, paper_id: UUID) -> Dict[str, Any]:
        """Get statistics for notes on a specific paper."""
        async with db_manager.get_connection() as conn:
            result = await conn.fetchval("""
                SELECT get_note_statistics($1)
            """, paper_id)
            return json.loads(result) if result else {}

    async def get_related_notes(self, note_id: UUID, limit: int = 10) -> List[Tuple[Note, float]]:
        """Get notes related to a specific note using content similarity."""
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT n.*, ts_rank(n.search_vector, 
                    (SELECT search_vector FROM notes WHERE id = $1)) as similarity
                FROM notes n
                WHERE n.id != $1 
                AND n.search_vector IS NOT NULL
                AND ts_rank(n.search_vector, 
                    (SELECT search_vector FROM notes WHERE id = $1)) > 0.1
                ORDER BY similarity DESC
                LIMIT $2
            """, note_id, limit)
            return [(self._from_row(dict(row)), row['similarity']) for row in rows] 