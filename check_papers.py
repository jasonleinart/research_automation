#!/usr/bin/env python3
import asyncio
from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository

async def check_papers():
    await db_manager.initialize()
    repo = PaperRepository()
    
    papers = await repo.list_all(limit=5)
    print('Papers with full text:')
    for paper in papers:
        has_full_text = bool(paper.full_text)
        print(f'- {paper.title[:50]}... (has_full_text: {has_full_text})')
        if has_full_text:
            print(f'  ID: {paper.id}')
    
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_papers()) 