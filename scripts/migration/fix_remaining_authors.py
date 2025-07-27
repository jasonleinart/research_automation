#!/usr/bin/env python3
"""
Script to fix the remaining problematic author names.
"""

import asyncio
import logging
import re
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.database.author_repository import AuthorRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fix_author_name(name: str) -> str:
    """Fix author name by extracting from the original JSONB data."""
    if not name or name == "Author(name=\\":
        return ""
    
    # Try to extract from the original pattern
    # Look for patterns like: Author(name='Author(name="Author(name='...', ...)', ...)
    pattern = r"Author\(name=['\"]([^'\"]+)['\"]"
    matches = re.findall(pattern, name)
    
    if matches:
        # Get the last match and clean it
        clean_name = matches[-1]
        # Remove any remaining Author(...) wrappers
        clean_name = re.sub(r"Author\([^)]*\)", "", clean_name)
        clean_name = clean_name.strip()
        return clean_name
    
    return ""


async def fix_remaining_authors():
    """Fix the remaining problematic author names."""
    try:
        logger.info("Starting to fix remaining problematic authors...")
        
        # Initialize database
        await db_manager.initialize()
        
        # Get the original author data from papers to see what these should be
        async with db_manager.get_connection() as conn:
            # Get papers with their original authors JSONB
            rows = await conn.fetch("SELECT id, title, authors FROM papers WHERE authors IS NOT NULL")
            
            # Create a mapping of problematic author names to their correct names
            author_mapping = {}
            
            for row in rows:
                paper_id = row['id']
                title = row['title']
                authors_json = row['authors']
                
                if authors_json:
                    for i, author_data in enumerate(authors_json):
                        # Convert to string and try to extract clean name
                        author_str = str(author_data)
                        clean_name = fix_author_name(author_str)
                        
                        if clean_name and clean_name != "Author(name=\\":
                            # Store the mapping
                            author_mapping["Author(name=\\"] = clean_name
                            logger.info(f"Found mapping: 'Author(name=\\' -> '{clean_name}' from paper '{title[:50]}...'")
                            break
        
        # Now update the problematic authors in the database
        author_repo = AuthorRepository()
        authors = await author_repo.list_all()
        
        fixed_count = 0
        for author in authors:
            if author.name == "Author(name=\\":
                # Find the correct name from our mapping
                correct_name = author_mapping.get("Author(name=\\")
                if correct_name:
                    logger.info(f"Fixing author: '{author.name}' -> '{correct_name}'")
                    
                    async with db_manager.get_connection() as conn:
                        await conn.execute(
                            "UPDATE authors SET name = $1, updated_at = NOW() WHERE id = $2",
                            correct_name, author.id
                        )
                    fixed_count += 1
                else:
                    logger.warning(f"Could not find correct name for author ID {author.id}")
        
        logger.info(f"✓ Fixed {fixed_count} author names")
        
        # Show final sample
        logger.info("\nFinal sample of authors:")
        authors = await author_repo.list_all()
        for author in authors[:10]:
            logger.info(f"  - {author.name}")
        
        logger.info("\n✅ Author name fixing completed!")
        
    except Exception as e:
        logger.error(f"❌ Fixing failed: {e}")
        raise
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(fix_remaining_authors()) 