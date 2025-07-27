#!/usr/bin/env python3
import asyncio
from src.database.connection import db_manager
from src.services.paper_ingestion import PaperIngestionService

async def reingest_with_pdf():
    await db_manager.initialize()
    
    # Use the first paper as an example
    paper_id = "9f0ae9b7-7f3c-4c70-ad97-4e8989087ab9"
    
    # Get the paper to find its ArXiv ID
    async with db_manager.get_connection() as conn:
        row = await conn.fetchrow("SELECT arxiv_id, title FROM papers WHERE id = $1", paper_id)
        if not row:
            print("Paper not found")
            return
        
        arxiv_id = row['arxiv_id']
        title = row['title']
        
        if not arxiv_id:
            print("Paper doesn't have an ArXiv ID")
            return
        
        print(f"Re-ingesting paper: {title}")
        print(f"ArXiv ID: {arxiv_id}")
    
    # Re-ingest with PDF content
    ingestion_service = PaperIngestionService()
    arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
    
    try:
        paper = await ingestion_service.ingest_from_arxiv_url(arxiv_url)
        if paper and paper.pdf_content:
            print(f"✅ Successfully re-ingested with PDF content ({len(paper.pdf_content)} bytes)")
        else:
            print("❌ Failed to get PDF content")
    except Exception as e:
        print(f"❌ Error re-ingesting: {e}")
    
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(reingest_with_pdf()) 