#!/usr/bin/env python3
"""
Show tags generated for each paper.
"""

import asyncio
from typing import Dict, List, Any
from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.database.tag_repository import TagRepository, PaperTagRepository
from src.models.enums import TagCategory

async def main():
    await db_manager.initialize()
    
    paper_repo = PaperRepository()
    tag_repo = TagRepository()
    paper_tag_repo = PaperTagRepository()
    
    print("🏷️  Paper Tags Analysis\n")
    
    # Get all papers
    papers = await paper_repo.list_all()
    
    if not papers:
        print("No papers found in database.")
        return
    
    # Show tags for each paper
    for i, paper in enumerate(papers, 1):
        print(f"📄 {i}. {paper.title[:60]}...")
        print(f"   Paper Type: {paper.paper_type.value if paper.paper_type else 'Not classified'}")
        print(f"   ArXiv ID: {paper.arxiv_id or 'N/A'}")
        
        # Get tags for this paper
        paper_tags = await paper_tag_repo.get_paper_tags_with_details(paper.id)
        
        if paper_tags:
            print(f"   Tags ({len(paper_tags)}):")
            
            # Group tags by category
            tags_by_category = {}
            for tag_data in paper_tags:
                category = tag_data['category']
                if category not in tags_by_category:
                    tags_by_category[category] = []
                tags_by_category[category].append(tag_data)
            
            # Display tags by category
            for category, tags in tags_by_category.items():
                print(f"     {category.upper()}:")
                for tag_data in tags:
                    confidence_str = f" ({tag_data['confidence']:.1%})" if tag_data['confidence'] else ""
                    source_str = f" [{tag_data['source']}]" if tag_data['source'] else ""
                    print(f"       - {tag_data['name']}{confidence_str}{source_str}")
                    if tag_data['description']:
                        desc_preview = tag_data['description'][:60] + "..." if len(tag_data['description']) > 60 else tag_data['description']
                        print(f"         \"{desc_preview}\"")
        else:
            print("   Tags: None")
        
        print()
    
    # Show overall tag statistics
    print("📊 Tag Statistics:")
    
    # Get all tags
    all_tags = await tag_repo.list_all()
    print(f"   Total unique tags: {len(all_tags)}")
    
    # Count tags by category
    category_counts = {}
    for tag in all_tags:
        category = tag.category.value
        category_counts[category] = category_counts.get(category, 0) + 1
    
    print("   Tags by category:")
    for category, count in sorted(category_counts.items()):
        print(f"     - {category}: {count}")
    
    # Show most used tags
    print("\n🔥 Most Used Tags:")
    tag_usage = {}
    
    for paper in papers:
        paper_tags = await paper_tag_repo.get_paper_tags_with_details(paper.id)
        for tag_data in paper_tags:
            tag_name = tag_data['name']
            tag_usage[tag_name] = tag_usage.get(tag_name, 0) + 1
    
    # Sort by usage
    sorted_tags = sorted(tag_usage.items(), key=lambda x: x[1], reverse=True)
    
    for tag_name, count in sorted_tags[:10]:  # Top 10
        print(f"   - {tag_name}: {count} paper(s)")
    
    # Show tag coverage
    papers_with_tags = 0
    for paper in papers:
        paper_tags = await paper_tag_repo.get_paper_tags_with_details(paper.id)
        if paper_tags:
            papers_with_tags += 1
    
    coverage = (papers_with_tags / len(papers)) * 100 if papers else 0
    
    print(f"\n📈 Tag Coverage: {papers_with_tags}/{len(papers)} papers ({coverage:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main())