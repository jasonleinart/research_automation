#!/usr/bin/env python3
import asyncio
from src.database.connection import db_manager

async def check_pdf_papers():
    await db_manager.initialize()
    async with db_manager.get_connection() as conn:
        rows = await conn.fetch("""
            SELECT id, title, pdf_content IS NOT NULL as has_pdf 
            FROM papers 
            WHERE pdf_content IS NOT NULL 
            LIMIT 5
        """)
        
        print('Papers with PDF content:')
        for row in rows:
            print(f'- {row["title"][:50]}... (ID: {row["id"]})')
    
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_pdf_papers()) 