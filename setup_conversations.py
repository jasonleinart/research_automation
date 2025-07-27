#!/usr/bin/env python3
"""
Setup conversation tables in the database.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.database.connection import db_manager

async def setup_conversation_tables():
    """Create conversation tables in the database."""
    await db_manager.initialize()
    
    print("🔧 Setting up conversation tables...")
    
    try:
        async with db_manager.get_connection() as conn:
            # Read and execute the schema
            with open('database/schema/07_conversations.sql', 'r') as f:
                schema_sql = f.read()
            
            # Execute the schema
            await conn.execute(schema_sql)
            
        print("✅ Conversation tables created successfully!")
        
        # Verify tables were created
        async with db_manager.get_connection() as conn:
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE 'conversation%'
                ORDER BY table_name
            """)
            
            print(f"📋 Created tables:")
            for table in tables:
                print(f"   • {table['table_name']}")
                
    except Exception as e:
        print(f"❌ Error setting up tables: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(setup_conversation_tables())