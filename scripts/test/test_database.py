#!/usr/bin/env python3
"""
Test script to verify database setup and basic operations.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_database():
    """Test basic database operations."""
    try:
        logger.info("Testing database connection...")
        
        # Initialize database connection
        await db_manager.initialize()
        
        # Test connection
        if not await db_manager.check_connection():
            logger.error("Database connection test failed")
            return False
        
        # Test basic queries
        async with db_manager.get_connection() as conn:
            # Test table existence
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            
            logger.info(f"Found {len(tables)} tables:")
            for table in tables:
                logger.info(f"  - {table['table_name']}")
            
            # Test enum types
            enums = await conn.fetch("""
                SELECT typname 
                FROM pg_type 
                WHERE typtype = 'e'
                ORDER BY typname;
            """)
            
            logger.info(f"Found {len(enums)} enum types:")
            for enum in enums:
                logger.info(f"  - {enum['typname']}")
            
            # Test pgvector extension
            extensions = await conn.fetch("""
                SELECT extname 
                FROM pg_extension 
                WHERE extname IN ('vector', 'uuid-ossp');
            """)
            
            logger.info(f"Found {len(extensions)} required extensions:")
            for ext in extensions:
                logger.info(f"  - {ext['extname']}")
        
        logger.info("Database test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        return False
    finally:
        await db_manager.close()

async def main():
    """Main test function."""
    success = await test_database()
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())