#!/usr/bin/env python3
"""
Database setup script for ArXiv Content Automation System.
This script initializes the database and runs all migrations.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.database.migrations import migration_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def setup_database():
    """Set up the database with all required schema."""
    try:
        logger.info("Starting database setup...")
        
        # Initialize database connection
        await db_manager.initialize()
        
        # Check connection
        if not await db_manager.check_connection():
            logger.error("Database connection failed")
            return False
        
        logger.info("Database connection successful")
        
        # Run migrations
        await migration_manager.run_migrations()
        
        logger.info("Database setup completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return False
    finally:
        await db_manager.close()

async def main():
    """Main setup function."""
    success = await setup_database()
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())