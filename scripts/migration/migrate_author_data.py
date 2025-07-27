#!/usr/bin/env python3
"""
Script to migrate author data from existing papers to the new relational tables.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.database.author_repository import AuthorRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def migrate_author_data():
    """Migrate author data from existing papers."""
    try:
        logger.info("Starting author data migration...")
        
        # Initialize database
        await db_manager.initialize()
        
        # Read and execute the migration file
        migration_file = Path(__file__).parent / "database" / "schema" / "07_migrate_authors.sql"
        
        logger.info("Migrating author data...")
        async with db_manager.get_connection() as conn:
            with open(migration_file, 'r') as f:
                migration_sql = f.read()
            await conn.execute(migration_sql)
            logger.info("✓ Author data migrated")
        
        # Verify migration
        author_repo = AuthorRepository()
        paper_repo = PaperRepository()
        
        # Check author count
        authors = await author_repo.list_all()
        logger.info(f"✓ Migrated {len(authors)} authors")
        
        # Check paper-author relationships
        papers = await paper_repo.list_all()
        total_relationships = 0
        for paper in papers:
            paper_authors = await author_repo.get_paper_authors(paper.id)
            total_relationships += len(paper_authors)
            logger.info(f"  Paper '{paper.title[:50]}...' has {len(paper_authors)} authors")
        
        logger.info(f"✓ Created {total_relationships} paper-author relationships")
        
        # Show some sample authors
        logger.info("\nSample authors:")
        for author in authors[:5]:
            logger.info(f"  - {author.name}")
        
        logger.info("\n✅ Author data migration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(migrate_author_data()) 