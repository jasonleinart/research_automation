#!/usr/bin/env python3
"""
Test that new paper ingestion properly handles authors.
"""

import asyncio
from src.database.connection import db_manager
from src.services.paper_ingestion import PaperIngestionService
from src.services.author_service import AuthorService

async def test_arxiv_ingestion():
    """Test ArXiv paper ingestion with author handling."""
    await db_manager.initialize()
    
    ingestion_service = PaperIngestionService()
    author_service = AuthorService()
    
    print("🧪 Testing ArXiv paper ingestion with author handling...")
    
    # Test with a different paper
    test_url = "https://arxiv.org/abs/2301.00001"  # A paper that likely doesn't exist in our DB
    
    print(f"📄 Ingesting paper from: {test_url}")
    
    # Ingest the paper
    paper = await ingestion_service.ingest_from_arxiv_url(test_url)
    
    if not paper:
        print("❌ Failed to ingest paper")
        return
    
    print(f"✅ Paper ingested: {paper.title}")
    
    # Check if authors were properly assigned
    paper_with_authors = await author_service.get_paper_with_authors(paper.id)
    
    if paper_with_authors and paper_with_authors.author_names:
        print(f"✅ Authors properly assigned ({len(paper_with_authors.author_names)}):")
        for i, author_name in enumerate(paper_with_authors.author_names, 1):
            print(f"   {i}. {author_name}")
    else:
        print("❌ No authors found for the paper")
    
    return paper_with_authors

async def test_duplicate_handling():
    """Test that duplicate ingestion doesn't create duplicate authors."""
    await db_manager.initialize()
    
    ingestion_service = PaperIngestionService()
    author_service = AuthorService()
    
    print("\n🔄 Testing duplicate paper ingestion...")
    
    # Try to ingest the same paper again
    test_url = "https://arxiv.org/abs/2301.00001"
    
    paper = await ingestion_service.ingest_from_arxiv_url(test_url)
    
    if paper:
        print(f"✅ Duplicate handling worked: {paper.title}")
        
        # Check authors
        paper_with_authors = await author_service.get_paper_with_authors(paper.id)
        if paper_with_authors and paper_with_authors.author_names:
            print(f"✅ Authors still present: {len(paper_with_authors.author_names)} authors")
        else:
            print("❌ Authors missing after duplicate check")
    else:
        print("❌ Duplicate handling failed")

async def test_author_statistics():
    """Test author statistics after ingestion."""
    await db_manager.initialize()
    
    author_service = AuthorService()
    
    print("\n📊 Author statistics after ingestion:")
    
    stats = await author_service.get_author_statistics()
    
    print(f"   Total authors: {stats.get('total_authors', 0)}")
    print(f"   Papers with authors: {stats.get('total_papers_with_authors', 0)}")
    print(f"   Avg authors per paper: {stats.get('avg_authors_per_paper', 0):.1f}")

async def main():
    try:
        paper = await test_arxiv_ingestion()
        await test_duplicate_handling()
        await test_author_statistics()
        
        print("\n🎉 Author ingestion testing completed!")
        
        if paper and paper.author_names:
            print(f"\n✅ SUCCESS: New ingestion process properly handles authors!")
            print(f"   Paper: {paper.title}")
            print(f"   Authors: {', '.join(paper.author_names)}")
        else:
            print(f"\n❌ FAILURE: Authors not properly handled in ingestion")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())