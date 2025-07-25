#!/usr/bin/env python3
"""
Script to clean up test data and fix the Attention paper.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.services.paper_ingestion import PaperIngestionService

async def fix_attention_paper():
    """Fix the corrupted Attention Is All You Need paper."""
    try:
        await db_manager.initialize()
        
        repo = PaperRepository()
        ingestion_service = PaperIngestionService()
        
        # Find the corrupted paper
        attention_paper = await repo.get_by_arxiv_id("1706.03762")
        
        if attention_paper:
            print(f"📄 Found existing paper: {attention_paper.title}")
            print(f"   Current status: {attention_paper.analysis_status}")
            print(f"   Authors look corrupted: {len(attention_paper.authors)} authors")
            
            # Delete the corrupted entry
            deleted = await repo.delete(attention_paper.id)
            if deleted:
                print("🗑️  Deleted corrupted paper")
            else:
                print("❌ Failed to delete paper")
                return
        
        # Re-ingest the proper paper
        print("📥 Re-ingesting proper paper from ArXiv...")
        new_paper = await ingestion_service.ingest_from_arxiv_url("https://arxiv.org/abs/1706.03762")
        
        if new_paper:
            print(f"✅ Successfully re-ingested: {new_paper.title}")
            print(f"   ArXiv ID: {new_paper.arxiv_id}")
            print(f"   Authors: {', '.join(new_paper.author_names)}")
            print(f"   Categories: {new_paper.categories}")
        else:
            print("❌ Failed to re-ingest paper")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(fix_attention_paper())