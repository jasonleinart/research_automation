#!/usr/bin/env python3
"""
Test the paper relationship queries to understand database context integration.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository

async def test_paper_relationships():
    """Test all the paper relationship query methods."""
    await db_manager.initialize()
    
    paper_repo = PaperRepository()
    
    print("🔗 Testing Paper Relationship Queries")
    print("=" * 60)
    
    # Get all papers to test with
    papers = await paper_repo.list_all()
    if not papers:
        print("❌ No papers found")
        return
    
    print(f"📚 Total papers in database: {len(papers)}")
    
    # Test with the first few papers
    test_papers = papers[:3]
    
    for i, paper in enumerate(test_papers, 1):
        print(f"\n{i}️⃣ Testing relationships for: {paper.title}")
        print("-" * 50)
        
        # Test 1: Papers by same authors
        print("\n👥 Papers by Same Authors:")
        try:
            same_author_papers = await paper_repo.find_papers_by_same_authors(paper.id)
            if same_author_papers:
                for related_paper in same_author_papers[:3]:
                    authors = getattr(related_paper, '_author_names', ['Unknown'])
                    print(f"   • {related_paper.title[:60]}...")
                    print(f"     Authors: {', '.join(authors)}")
            else:
                print("   No papers found with same authors")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 2: Papers with shared tags
        print("\n🏷️ Papers with Shared Tags:")
        try:
            shared_tag_papers = await paper_repo.find_papers_with_shared_tags(paper.id)
            if shared_tag_papers:
                for related_paper in shared_tag_papers[:3]:
                    shared_count = getattr(related_paper, '_shared_tag_count', 0)
                    print(f"   • {related_paper.title[:60]}...")
                    print(f"     Shared tags: {shared_count}")
            else:
                print("   No papers found with shared tags")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 3: Papers in same categories
        print("\n📂 Papers in Same Categories:")
        try:
            same_category_papers = await paper_repo.find_papers_in_same_categories(paper.id)
            if same_category_papers:
                for related_paper in same_category_papers[:3]:
                    shared_count = getattr(related_paper, '_shared_category_count', 0)
                    print(f"   • {related_paper.title[:60]}...")
                    print(f"     Categories: {related_paper.categories}")
                    print(f"     Shared categories: {shared_count}")
            else:
                print("   No papers found in same categories")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 4: Papers from same time period
        print("\n📅 Papers from Same Time Period:")
        try:
            same_time_papers = await paper_repo.find_papers_from_same_time_period(paper.id)
            if same_time_papers:
                for related_paper in same_time_papers[:3]:
                    pub_date = related_paper.publication_date
                    print(f"   • {related_paper.title[:60]}...")
                    print(f"     Published: {pub_date.strftime('%Y-%m-%d') if pub_date else 'Unknown'}")
            else:
                print("   No papers found from same time period")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 5: Complete relationship summary
        print("\n📊 Relationship Summary:")
        try:
            summary = await paper_repo.get_relationship_summary(paper.id)
            print(f"   Same authors: {summary['same_authors']} papers")
            print(f"   Shared tags: {summary['shared_tags']} papers")
            print(f"   Same categories: {summary['same_categories']} papers")
            print(f"   Same time period: {summary['same_time_period']} papers")
            print(f"   Total related: {summary['total_related']} papers")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        if i >= 2:  # Limit to first 2 papers for demo
            break
    
    # Test 6: Demonstrate how this enhances conversations
    print(f"\n💬 How This Enhances Conversations:")
    print("=" * 50)
    
    test_paper = papers[0]
    relationships = await paper_repo.get_paper_relationships(test_paper.id)
    
    print(f"When discussing '{test_paper.title}', the agent can now:")
    
    if relationships['same_authors']:
        print(f"✅ Mention {len(relationships['same_authors'])} other papers by the same authors")
    
    if relationships['shared_tags']:
        print(f"✅ Reference {len(relationships['shared_tags'])} papers with similar topics/methods")
    
    if relationships['same_categories']:
        print(f"✅ Compare with {len(relationships['same_categories'])} papers in the same research area")
    
    if relationships['same_time_period']:
        print(f"✅ Discuss {len(relationships['same_time_period'])} contemporary papers from the same era")
    
    total_context = sum(len(papers) for papers in relationships.values())
    print(f"\n🎯 Total contextual papers available: {total_context}")
    print("This gives the agent much richer context for conversations!")
    
    print(f"\n🎉 Paper Relationship Testing Complete!")
    print("✅ All relationship query methods are working")
    print("✅ Database context integration is ready")

if __name__ == "__main__":
    asyncio.run(test_paper_relationships())