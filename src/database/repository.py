"""
Base repository pattern for database operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TypeVar, Generic
from uuid import UUID

from .connection import db_manager

T = TypeVar('T')


class BaseRepository(Generic[T], ABC):
    """Base repository with common CRUD operations."""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
    
    @abstractmethod
    def _from_row(self, row: Dict[str, Any]) -> T:
        """Convert database row to model instance."""
        pass
    
    @abstractmethod
    def _to_row(self, instance: T) -> Dict[str, Any]:
        """Convert model instance to database row."""
        pass
    
    async def create(self, instance: T) -> T:
        """Create a new record."""
        row_data = self._to_row(instance)
        
        # Build INSERT query
        columns = list(row_data.keys())
        placeholders = [f'${i+1}' for i in range(len(columns))]
        values = list(row_data.values())
        
        query = f"""
            INSERT INTO {self.table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """
        
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, *values)
            return self._from_row(dict(row))
    
    async def get_by_id(self, id: UUID) -> Optional[T]:
        """Get record by ID."""
        query = f"SELECT * FROM {self.table_name} WHERE id = $1"
        
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, id)
            return self._from_row(dict(row)) if row else None
    
    async def update(self, instance: T) -> T:
        """Update an existing record."""
        row_data = self._to_row(instance)
        
        # Filter out None values and id for the update
        update_data = {k: v for k, v in row_data.items() if k != 'id' and v is not None}
        
        if not update_data:
            # If no data to update, just return the instance
            return instance
        
        # Build UPDATE query with explicit type casting for problematic fields
        set_clauses = []
        values = [row_data['id']]
        
        for i, (col, val) in enumerate(update_data.items(), 1):
            if col in ['authors', 'categories']:
                # Handle JSON fields explicitly
                set_clauses.append(f"{col} = ${i+1}::jsonb")
            else:
                set_clauses.append(f"{col} = ${i+1}")
            values.append(val)
        
        # Add updated_at if not already in the data
        if 'updated_at' not in update_data:
            set_clauses.append(f"updated_at = NOW()")
        
        query = f"""
            UPDATE {self.table_name}
            SET {', '.join(set_clauses)}
            WHERE id = $1
            RETURNING *
        """
        
        async with db_manager.get_connection() as conn:
            row = await conn.fetchrow(query, *values)
            if not row:
                raise ValueError(f"Record with id {row_data['id']} not found")
            return self._from_row(dict(row))
    
    async def delete(self, id: UUID) -> bool:
        """Delete record by ID."""
        query = f"DELETE FROM {self.table_name} WHERE id = $1"
        
        async with db_manager.get_connection() as conn:
            result = await conn.execute(query, id)
            return result.split()[-1] == '1'  # Check if one row was deleted
    
    async def list_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """List all records with optional pagination."""
        query = f"SELECT * FROM {self.table_name} ORDER BY created_at DESC"
        
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query)
            return [self._from_row(dict(row)) for row in rows]
    
    async def count(self) -> int:
        """Count total records."""
        query = f"SELECT COUNT(*) FROM {self.table_name}"
        
        async with db_manager.get_connection() as conn:
            return await conn.fetchval(query)
    
    async def exists(self, id: UUID) -> bool:
        """Check if record exists."""
        query = f"SELECT EXISTS(SELECT 1 FROM {self.table_name} WHERE id = $1)"
        
        async with db_manager.get_connection() as conn:
            return await conn.fetchval(query, id)


class SearchableRepository(BaseRepository[T]):
    """Repository with search capabilities."""
    
    async def search(self, query: str, limit: int = 50) -> List[T]:
        """Full-text search across searchable fields."""
        # This is a basic implementation - can be enhanced with specific search logic
        search_query = f"""
            SELECT * FROM {self.table_name}
            WHERE to_tsvector('english', title || ' ' || COALESCE(abstract, '')) @@ plainto_tsquery('english', $1)
            ORDER BY ts_rank(to_tsvector('english', title || ' ' || COALESCE(abstract, '')), plainto_tsquery('english', $1)) DESC
            LIMIT $2
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(search_query, query, limit)
            return [self._from_row(dict(row)) for row in rows]
    
    async def filter_by(self, filters: Dict[str, Any], limit: Optional[int] = None) -> List[T]:
        """Filter records by field values."""
        if not filters:
            return await self.list_all(limit=limit)
        
        where_clauses = []
        values = []
        
        for i, (field, value) in enumerate(filters.items(), 1):
            if value is None:
                where_clauses.append(f"{field} IS NULL")
            elif isinstance(value, list):
                placeholders = [f'${len(values) + j + 1}' for j in range(len(value))]
                where_clauses.append(f"{field} = ANY(ARRAY[{', '.join(placeholders)}])")
                values.extend(value)
            else:
                where_clauses.append(f"{field} = ${len(values) + 1}")
                values.append(value)
        
        query = f"""
            SELECT * FROM {self.table_name}
            WHERE {' AND '.join(where_clauses)}
            ORDER BY created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query, *values)
            return [self._from_row(dict(row)) for row in rows]