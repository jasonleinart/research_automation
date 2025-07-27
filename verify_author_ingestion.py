#!/usr/bin/env python3
"""
Verify that the author ingestion system is working correctly.
"""

import asyncio
from src.database.connection import db_manager
from src.services.author_service import AuthorService
from src.database.paper_repository import PaperRepository

async def main():
    await db_manager.initialize()
    
    author_service = AuthorService()
    paper_repo = PaperRepository()
    
    print("🔍 Verifying Author Ingestion System")
    print("=" * 50)
    
    # Get all papers
    papers = await paper_repo.list_all()
    
    print(f"📚 Total papers in database: {len(papers)}")
    
    # Check each paper for authors
    papers_with_authors = 0
    total_authors = 0
    
    for paper in papers:
        paper_with_authors = await author_service.get_paper_with_authors(paper.id)
        
        if paper_with_authors and paper_with_authors.author_names:
            papers_with_authors += 1
            author_count = len(paper_with_authors.author_names)
            total_authors += author_count
            
            print(f"\n📄 {paper.title[:60]}...")
            print(f"   ArXiv ID: {paper.arxiv_id or 'N/A'}")
            print(f"   Authors ({author_count}):")
            for i, author_name in enumerate(paper_with_authors.author_names, 1):
                print(f"      {i}. {author_name}")
        else:
            print(f"\n❌ {paper.title[:60]}... - NO AUTHORS")
    
    print(f"\n📊 Summary:")
    print(f"   Papers with authors: {papers_with_authors}/{len(papers)}")
    print(f"   Total author assignments: {total_authors}")
    print(f"   Average authors per paper: {total_authors/len(papers):.1f}")
    
    # Get author statistics
    stats = await author_service.get_author_statistics()
    print(f"\n📈 Author System Statistics:")
    print(f"   Unique authors: {stats.get('total_authors', 0)}")
    print(f"   Papers with authors: {stats.get('total_papers_with_authors', 0)}")
    print(f"   Avg authors per paper: {stats.get('avg_authors_per_paper', 0):.1f}")
    
    # Show most prolific authors
    prolific = stats.get('most_prolific_authors', [])
    if prolific:
        print(f"\n🏆 Most Prolific Authors:")
        for author in prolific[:5]:
            print(f"   {author['name']}: {author['paper_count']} papers")
    
    # Test author search
    print(f"\n🔍 Testing author search functionality:")
    test_authors = ["Thompson", "Vaswani", "Khan"]
    
    for author_name in test_authors:
        author_papers = await author_service.search_papers_by_author(author_name)
        print(f"   '{author_name}': {len(author_papers)} papers found")
    
    print(f"\n✅ Author ingestion system verification complete!")
    
    if papers_with_authors == len(papers) and len(papers) > 0:
        print(f"🎉 SUCCESS: All {len(papers)} papers have authors properly assigned!")
    elif papers_with_authors > 0:
        print(f"⚠️  PARTIAL: {papers_with_authors}/{len(papers)} papers have authors")
    else:
        print(f"❌ FAILURE: No papers have authors assigned")

if __name__ == "__main__":
    asyncio.run(main())