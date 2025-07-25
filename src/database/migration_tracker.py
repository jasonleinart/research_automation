"""
Migration tracking system for database schema evolution.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from .connection import db_manager

logger = logging.getLogger(__name__)


class MigrationTracker:
    """Tracks applied database migrations."""
    
    async def ensure_migration_table(self) -> None:
        """Create migration tracking table if it doesn't exist."""
        query = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT NOW(),
                checksum VARCHAR(64)
            );
        """
        
        async with db_manager.get_connection() as conn:
            await conn.execute(query)
            logger.info("Migration tracking table ensured")
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration filenames."""
        await self.ensure_migration_table()
        
        query = "SELECT filename FROM schema_migrations ORDER BY applied_at"
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query)
            return [row['filename'] for row in rows]
    
    async def mark_migration_applied(self, filename: str, checksum: str = None) -> None:
        """Mark a migration as applied."""
        query = """
            INSERT INTO schema_migrations (filename, checksum, applied_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (filename) DO NOTHING
        """
        
        async with db_manager.get_connection() as conn:
            await conn.execute(query, filename, checksum)
            logger.info(f"Marked migration as applied: {filename}")
    
    async def get_migration_info(self) -> List[Dict[str, Any]]:
        """Get detailed migration information."""
        await self.ensure_migration_table()
        
        query = """
            SELECT filename, applied_at, checksum
            FROM schema_migrations
            ORDER BY applied_at
        """
        
        async with db_manager.get_connection() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]


# Global migration tracker
migration_tracker = MigrationTracker()