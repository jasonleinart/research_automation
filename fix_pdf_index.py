#!/usr/bin/env python3
import asyncio
from src.database.connection import db_manager

async def fix_pdf_index():
    await db_manager.initialize()
    async with db_manager.get_connection() as conn:
        await conn.execute('DROP INDEX IF EXISTS idx_papers_pdf_content;')
        print('Fixed PDF index issue')
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(fix_pdf_index()) 