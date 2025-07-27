#!/usr/bin/env python3
"""
Script to clean up author names by extracting the actual names from nested structures.
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


def extract_clean_name(nested_name: str) -> str:
    """Extract clean author name from nested Author structure."""
    if not nested_name:
        return ""
    
    # Pattern to match the innermost name: Author(name='...', ...)
    # Handle multiple levels of nesting
    pattern = r"Author\(name=['\"]([^'\"]+)['\"]"
    
    # Find all matches
    matches = re.findall(pattern, nested_name)
    
    if matches:
        # Return the last (innermost) match
        clean_name = matches[-1]
        # Clean up any remaining quotes or special characters
        clean_name = clean_name.strip()
        return clean_name
    
    # If no pattern match, try to extract from the string directly
    # Remove any remaining Author(...) wrappers
    clean_name = re.sub(r"Author\([^)]*\)", "", nested_name)
    clean_name = re.sub(r'[{"}\[\]]', "", clean_name)  # Remove JSON artifacts
    clean_name = re.sub(r"'name':\s*'([^']*)'", r"\1", clean_name)  # Extract name from dict format
    clean_name = clean_name.strip()
    
    return clean_name


async def clean_author_names():
    """Clean up author names in the database."""
    try:
        logger.info("Starting author name cleanup...")
        
        # Initialize database
        await db_manager.initialize()
        
        author_repo = AuthorRepository()
        authors = await author_repo.list_all()
        
        logger.info(f"Found {len(authors)} authors to clean")
        
        # Clean each author name
        cleaned_count = 0
        for author in authors:
            original_name = author.name
            clean_name = extract_clean_name(original_name)
            
            if clean_name and clean_name != original_name:
                logger.info(f"Cleaning: '{original_name[:50]}...' -> '{clean_name}'")
                
                # Update the author name in the database
                async with db_manager.get_connection() as conn:
                    await conn.execute(
                        "UPDATE authors SET name = $1, updated_at = NOW() WHERE id = $2",
                        clean_name, author.id
                    )
                cleaned_count += 1
        
        logger.info(f"✓ Cleaned {cleaned_count} author names")
        
        # Show some sample cleaned authors
        logger.info("\nSample cleaned authors:")
        authors = await author_repo.list_all()
        for author in authors[:10]:
            logger.info(f"  - {author.name}")
        
        logger.info("\n✅ Author name cleanup completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        raise
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(clean_author_names()) 