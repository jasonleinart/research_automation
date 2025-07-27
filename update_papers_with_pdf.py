#!/usr/bin/env python3
import asyncio
from src.database.connection import db_manager
from src.services.arxiv_client import ArxivClient

async def update_papers_with_pdf():
    await db_manager.initialize()
    arxiv_client = ArxivClient()
    
    # Get papers that don't have PDF content
    async with db_manager.get_connection() as conn:
        rows = await conn.fetch("""
            SELECT id, arxiv_id, title 
            FROM papers 
            WHERE arxiv_id IS NOT NULL 
            AND pdf_content IS NULL
            LIMIT 3
        """)
        
        if not rows:
            print("No papers found that need PDF content")
            return
        
        print(f"Found {len(rows)} papers to update with PDF content")
        
        for row in rows:
            paper_id = row['id']
            arxiv_id = row['arxiv_id']
            title = row['title']
            
            print(f"\nUpdating: {title[:50]}...")
            print(f"ArXiv ID: {arxiv_id}")
            
            try:
                # Download PDF content
                pdf_content = await arxiv_client.download_pdf(arxiv_id)
                
                if pdf_content:
                    # Update the paper with PDF content
                    await conn.execute("""
                        UPDATE papers 
                        SET pdf_content = $1, updated_at = NOW()
                        WHERE id = $2
                    """, pdf_content, paper_id)
                    
                    print(f"✅ Updated with PDF content ({len(pdf_content)} bytes)")
                else:
                    print("❌ Failed to download PDF")
                    
            except Exception as e:
                print(f"❌ Error updating paper: {e}")
    
    await db_manager.close()
    print("\nPDF update completed!")

if __name__ == "__main__":
    asyncio.run(update_papers_with_pdf()) 