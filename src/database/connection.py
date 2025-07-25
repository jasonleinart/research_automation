import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
from asyncpg import Connection, Pool

from src.config import get_database_config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and connection pooling."""
    
    def __init__(self):
        self.config = get_database_config()
        self._pool: Optional[Pool] = None
    
    async def initialize(self) -> None:
        """Initialize the database connection pool."""
        try:
            self._pool = await asyncpg.create_pool(
                self.config.connection_string,
                min_size=2,
                max_size=10,
                command_timeout=60,
                server_settings={
                    'application_name': 'arxiv_automation',
                }
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close(self) -> None:
        """Close the database connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("Database connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Connection, None]:
        """Get a database connection from the pool."""
        if not self._pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self._pool.acquire() as connection:
            yield connection
    
    async def execute_schema_file(self, file_path: str) -> None:
        """Execute a SQL schema file."""
        try:
            with open(file_path, 'r') as f:
                sql = f.read()
            
            async with self.get_connection() as conn:
                await conn.execute(sql)
                logger.info(f"Executed schema file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to execute schema file {file_path}: {e}")
            raise
    
    async def check_connection(self) -> bool:
        """Check if database connection is working."""
        try:
            async with self.get_connection() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False

# Global database manager instance
db_manager = DatabaseManager()