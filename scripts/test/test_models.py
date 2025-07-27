#!/usr/bin/env python3
"""
Test script to verify data models and repository operations.
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import date

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.database.tag_repository import TagRepository, PaperTagRepository
from src.models.paper import Paper, Author
from src.models.tag import Tag
from src.models.enums import PaperType, TagCategory, TagSource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_models_and_repositories():
    """Test basic model and repository operations."""
    try:
        logger.info("Testing data models and repositories...")
        
        # Initialize database connection
        await db_manager.initialize()
        
        # Initialize repositories
        paper_repo = PaperRepository()
        tag_repo = TagRepository()
        paper_tag_repo = PaperTagRepository()
        
        # Test 1: Create or get a sample paper
        logger.info("Creating/getting sample paper...")
        
        # First check if paper already exists
        existing_paper = await paper_repo.get_by_arxiv_id("1706.03762")
        
        if existing_paper:
            logger.info(f"✓ Found existing paper: {existing_paper.title} (ID: {existing_paper.id})")
            saved_paper = existing_paper
        else:
            # Create new paper
            sample_paper = Paper(
                title="Attention Is All You Need",
                abstract="We propose a new simple network architecture, the Transformer, based solely on attention mechanisms.",
                authors=[
                    Author(name="Ashish Vaswani", affiliation="Google Brain"),
                    Author(name="Noam Shazeer", affiliation="Google Brain")
                ],
                publication_date=date(2017, 6, 12),
                categories=["cs.CL", "cs.AI"],
                arxiv_id="1706.03762",
                paper_type=PaperType.CONCEPTUAL_FRAMEWORK,
                ingestion_source="manual_test"
            )
            
            saved_paper = await paper_repo.create(sample_paper)
            logger.info(f"✓ Created paper: {saved_paper.title} (ID: {saved_paper.id})")
        
        # Test 2: Create or get sample tags
        logger.info("Creating/getting sample tags...")
        
        # Check if tags already exist
        existing_ml_tag = await tag_repo.get_by_name("machine-learning")
        existing_transformer_tag = await tag_repo.get_by_name("transformer")
        
        if existing_ml_tag:
            logger.info(f"✓ Found existing ML tag: {existing_ml_tag.name}")
            saved_ml_tag = existing_ml_tag
        else:
            ml_tag = Tag(
                name="machine-learning",
                category=TagCategory.RESEARCH_DOMAIN,
                description="Machine learning research"
            )
            saved_ml_tag = await tag_repo.create(ml_tag)
            logger.info(f"✓ Created ML tag: {saved_ml_tag.name}")
        
        if existing_transformer_tag:
            logger.info(f"✓ Found existing transformer tag: {existing_transformer_tag.name}")
            saved_transformer_tag = existing_transformer_tag
        else:
            transformer_tag = Tag(
                name="transformer",
                category=TagCategory.CONCEPT,
                description="Transformer architecture"
            )
            saved_transformer_tag = await tag_repo.create(transformer_tag)
            logger.info(f"✓ Created transformer tag: {saved_transformer_tag.name}")
        
        # Test 3: Associate tags with paper (if not already associated)
        logger.info("Associating tags with paper...")
        
        # Check existing associations
        existing_tags = await paper_tag_repo.get_by_paper(saved_paper.id)
        existing_tag_ids = {pt.tag_id for pt in existing_tags}
        
        if saved_ml_tag.id not in existing_tag_ids:
            await paper_tag_repo.add_tag_to_paper(
                saved_paper.id, 
                saved_ml_tag.id, 
                confidence=0.95, 
                source=TagSource.MANUAL
            )
            logger.info("✓ Associated ML tag with paper")
        else:
            logger.info("✓ ML tag already associated with paper")
        
        if saved_transformer_tag.id not in existing_tag_ids:
            await paper_tag_repo.add_tag_to_paper(
                saved_paper.id, 
                saved_transformer_tag.id, 
                confidence=0.98, 
                source=TagSource.MANUAL
            )
            logger.info("✓ Associated transformer tag with paper")
        else:
            logger.info("✓ Transformer tag already associated with paper")
        
        # Test 4: Query operations
        logger.info("Testing query operations...")
        
        # Get paper by ArXiv ID
        found_paper = await paper_repo.get_by_arxiv_id("1706.03762")
        if found_paper:
            logger.info(f"✓ Found paper by ArXiv ID: {found_paper.title}")
        
        # Get paper tags
        paper_tags = await paper_tag_repo.get_paper_tags_with_details(saved_paper.id)
        logger.info(f"✓ Found {len(paper_tags)} tags for paper")
        for tag_info in paper_tags:
            logger.info(f"  - {tag_info['name']} ({tag_info['category']}) - confidence: {tag_info['confidence']}")
        
        # Search papers
        search_results = await paper_repo.search("attention transformer")
        logger.info(f"✓ Search found {len(search_results)} papers")
        
        # Get statistics
        stats = await paper_repo.get_statistics()
        logger.info(f"✓ Paper statistics: {stats}")
        
        # Test 5: Update operations
        logger.info("Testing update operations...")
        saved_paper.novelty_score = 0.95
        updated_paper = await paper_repo.update_paper(saved_paper)
        logger.info(f"✓ Updated paper novelty score: {updated_paper.novelty_score}")
        
        logger.info("All tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await db_manager.close()

async def main():
    """Main test function."""
    success = await test_models_and_repositories()
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())