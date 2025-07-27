#!/usr/bin/env python3
"""
Show tags generated for each paper.
"""

import asyncio
from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.database.tag_repository import TagRepository, PaperTagRepository

async def main():
    await db_manager.initialize()
    
    paper_repo = PaperRepository()
    tag_repo = TagRepository()
    paper_tag_repo = PaperTagRepository()
    
    print("🏷️  Paper Tags Overview\n")
    
    # Get all papers
    papers = await paper_repo.list_all()
    
    if not papers:
        print("No papers found in database.")
        return
    
    for paper in papers:
        print(f"📄 {paper.title[:60]}...")
        print(f"   Type: {paper.paper_type.value if paper.paper_type else 'Not classified'}")
        print(f"   ArXiv ID: {paper.arxiv_id or 'N/A'}")
        
        # Get tags for this paper
        paper_tags = await paper_tag_repo.get_paper_tags_with_details(paper.id)
        
        if paper_tags:
            print(f"   Tags ({len(paper_tags)}):")
            for pt in paper_tags:
                confidence_str = f" ({pt['confidence']:.1%})" if pt['confidence'] else ""
                source_str = f" [{pt['source']}]" if pt['source'] else ""
                print(f"     - {pt['name']} ({pt['category']}){confidence_str}{source_str}")
                if pt['description']:
                    print(f"       {pt['description'][:80]}...")
        else:
            print("   Tags: None")
        
        print()
    
    # Show tag statistics
    print("📊 Tag Usage Statistics:")
    tag_stats = await paper_tag_repo.get_tag_usage_stats()
    
    if tag_stats:
        print(f"   Total unique tags: {len(tag_stats)}")
        print(f"   Most used tags:")
        
        for stat in tag_stats[:10]:  # Top 10
            usage = stat['usage_count']
            avg_conf = stat['avg_confidence']
            conf_str = f" (avg: {avg_conf:.1%})" if avg_conf else ""
            print(f"     - {stat['name']} ({stat['category']}): {usage} papers{conf_str}")
    else:
        print("   No tag statistics available")
    
    # Show tag categories
    print("\n🗂️  Tags by Category:")
    from src.models.enums import TagCategory
    
    for category in TagCategory:
        category_tags = await tag_repo.get_by_category(category)
        if category_tags:
            print(f"   {category.value.replace('_', ' ').title()}: {len(category_tags)} tags")
            for tag in category_tags[:5]:  # Show first 5
                print(f"     - {tag.name}")
            if len(category_tags) > 5:
                print(f"     ... and {len(category_tags) - 5} more")

if __name__ == "__main__":
    asyncio.run(main())