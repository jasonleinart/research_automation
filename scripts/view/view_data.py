#!/usr/bin/env python3
"""
Simple script to view stored papers and tags.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.database.tag_repository import TagRepository, PaperTagRepository

async def view_stored_data():
    """View all stored papers and tags."""
    try:
        await db_manager.initialize()
        
        paper_repo = PaperRepository()
        tag_repo = TagRepository()
        paper_tag_repo = PaperTagRepository()
        
        print("=== STORED PAPERS ===")
        papers = await paper_repo.list_all()
        for paper in papers:
            print(f"📄 {paper.title}")
            print(f"   ArXiv ID: {paper.arxiv_id}")
            print(f"   Publication Date: {paper.publication_date}")
            print(f"   Abstract: {paper.abstract[:100]}..." if paper.abstract else "   Abstract: None")
            print(f"   Type: {paper.paper_type}")
            print(f"   Authors: {', '.join(paper.author_names)}")
            print(f"   Categories: {paper.categories}")
            print(f"   Novelty Score: {paper.novelty_score}")
            print(f"   Analysis Status: {paper.analysis_status}")
            print(f"   Created: {paper.created_at}")
            print(f"   Updated: {paper.updated_at}")
            print()
        
        print("=== STORED TAGS ===")
        tags = await tag_repo.list_all()
        for tag in tags:
            print(f"🏷️  {tag.name} ({tag.category.value})")
            if tag.description:
                print(f"   Description: {tag.description}")
        print()
        
        print("=== PAPER-TAG ASSOCIATIONS ===")
        for paper in papers:
            paper_tags = await paper_tag_repo.get_paper_tags_with_details(paper.id)
            if paper_tags:
                print(f"📄 {paper.title}:")
                for tag_info in paper_tags:
                    print(f"   🏷️  {tag_info['name']} (confidence: {tag_info['confidence']})")
                print()
        
        # Show statistics
        stats = await paper_repo.get_statistics()
        print("=== STATISTICS ===")
        print(f"Total papers: {stats['total_papers']}")
        print(f"Analyzed papers: {stats['analyzed_papers']}")
        print(f"Pending papers: {stats['pending_papers']}")
        print(f"Average novelty score: {stats['avg_novelty_score']}")
        
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(view_stored_data())