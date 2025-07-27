#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository

async def test_pdf_endpoint():
    try:
        await db_manager.initialize()
        repo = PaperRepository()
        papers = await repo.list_all()
        
        if not papers:
            print("No papers found in database")
            return
        
        paper = papers[0]
        print(f"Testing PDF endpoint for paper: {paper.title}")
        print(f"Paper ID: {paper.id}")
        print(f"Has PDF content: {paper.pdf_content is not None}")
        print(f"Has full text: {paper.full_text is not None}")
        
        if paper.pdf_content:
            print(f"PDF content size: {len(paper.pdf_content)} bytes")
        elif paper.full_text:
            print(f"Full text length: {len(paper.full_text)} characters")
        else:
            print("No PDF content or full text available")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_pdf_endpoint()) 