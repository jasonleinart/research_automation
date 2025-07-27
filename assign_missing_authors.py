#!/usr/bin/env python3
"""
Assign authors to papers that are missing them by fetching from ArXiv.
"""

import asyncio
from src.database.connection import db_manager
from src.services.author_service import AuthorService
from src.services.arxiv_client import ArxivClient
from src.database.paper_repository import PaperRepository

async def assign_authors_from_arxiv():
    """Fetch and assign authors from ArXiv for papers missing them."""
    await db_manager.initialize()
    
    author_service = AuthorService()
    paper_repo = PaperRepository()
    arxiv_client = ArxivClient()
    
    # Papers that need authors (from our analysis)
    papers_needing_authors = [
        "2504.17248v1",  # How Jungian Cognitive Functions...
        "2506.08872v1",  # Your Brain on ChatGPT...
        "2401.02777v2"   # From LLM to Conversational Agent...
    ]
    
    print("🔍 Fetching author information from ArXiv...\n")
    
    for arxiv_id in papers_needing_authors:
        print(f"📄 Processing {arxiv_id}...")
        
        # Find the paper in our database
        papers = await paper_repo.list_all()
        paper = None
        for p in papers:
            if p.arxiv_id == arxiv_id:
                paper = p
                break
        
        if not paper:
            print(f"   ❌ Paper not found in database: {arxiv_id}")
            continue
        
        print(f"   📝 Title: {paper.title[:60]}...")
        
        # Fetch paper info from ArXiv
        try:
            arxiv_data = await arxiv_client.get_paper_metadata(arxiv_id.replace('v1', '').replace('v2', ''))
            
            if not arxiv_data or 'authors' not in arxiv_data:
                print(f"   ❌ Could not fetch author data from ArXiv")
                continue
            
            # Extract author names
            author_names = [author.name for author in arxiv_data['authors']]
            
            if not author_names:
                print(f"   ❌ No authors found in ArXiv data")
                continue
            
            print(f"   👥 Found {len(author_names)} authors:")
            for i, name in enumerate(author_names, 1):
                print(f"      {i}. {name}")
            
            # Assign authors to paper
            paper_authors = await author_service.assign_authors_to_paper(
                paper_id=paper.id,
                author_names=author_names
            )
            
            print(f"   ✅ Successfully assigned {len(paper_authors)} authors")
            
        except Exception as e:
            print(f"   ❌ Error processing {arxiv_id}: {e}")
        
        print()
    
    print("🎉 Author assignment complete!")

async def verify_assignments():
    """Verify that all papers now have authors."""
    await db_manager.initialize()
    
    author_service = AuthorService()
    paper_repo = PaperRepository()
    
    papers = await paper_repo.list_all()
    
    print("🔍 Verifying author assignments...\n")
    
    papers_without_authors = 0
    
    for paper in papers:
        paper_with_authors = await author_service.get_paper_with_authors(paper.id)
        
        if not paper_with_authors.author_names:
            papers_without_authors += 1
            print(f"❌ Still missing authors: {paper.title[:60]}...")
        else:
            print(f"✅ {len(paper_with_authors.author_names)} authors: {paper.title[:60]}...")
    
    print(f"\n📊 Final Status:")
    print(f"   Total papers: {len(papers)}")
    print(f"   Papers with authors: {len(papers) - papers_without_authors}")
    print(f"   Papers without authors: {papers_without_authors}")
    
    if papers_without_authors == 0:
        print("🎉 All papers now have authors assigned!")

async def main():
    try:
        await assign_authors_from_arxiv()
        print("\n" + "="*60 + "\n")
        await verify_assignments()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())