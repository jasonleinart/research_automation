import os
import logging
from pathlib import Path
from typing import List

from src.database.connection import db_manager

logger = logging.getLogger(__name__)

class MigrationManager:
    """Manages database schema migrations."""
    
    def __init__(self, schema_dir: str = "database/schema"):
        self.schema_dir = Path(schema_dir)
    
    async def run_migrations(self) -> None:
        """Run all schema migrations in order."""
        if not self.schema_dir.exists():
            logger.error(f"Schema directory not found: {self.schema_dir}")
            raise FileNotFoundError(f"Schema directory not found: {self.schema_dir}")
        
        # Get all SQL files and sort them
        sql_files = sorted(self.schema_dir.glob("*.sql"))
        
        if not sql_files:
            logger.warning("No schema files found")
            return
        
        logger.info(f"Running {len(sql_files)} schema migrations")
        
        for sql_file in sql_files:
            try:
                await db_manager.execute_schema_file(str(sql_file))
                logger.info(f"✓ Applied migration: {sql_file.name}")
            except Exception as e:
                logger.error(f"✗ Failed migration: {sql_file.name} - {e}")
                raise
        
        logger.info("All migrations completed successfully")
    
    async def create_migration_table(self) -> None:
        """Create table to track applied migrations."""
        sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) NOT NULL UNIQUE,
            applied_at TIMESTAMP DEFAULT NOW()
        );
        """
        
        async with db_manager.get_connection() as conn:
            await conn.execute(sql)
            logger.info("Migration tracking table created")

# Global migration manager
migration_manager = MigrationManager()