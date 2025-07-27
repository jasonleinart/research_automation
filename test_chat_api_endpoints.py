#!/usr/bin/env python3
"""
Test the chat API endpoints to identify issues.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.database.connection import db_manager
from src.web.api.chat import get_papers_for_chat, get_chat_sessions

async def test_chat_api_endpoints():
    """Test the chat API endpoints that might be failing."""
    await db_manager.initialize()
    
    print("🧪 Testing Chat API Endpoints")
    print("=" * 50)
    
    # Test 1: Get papers for chat
    print("\n1️⃣ Testing get_papers_for_chat...")
    try:
        papers = await get_papers_for_chat()
        print(f"✅ Successfully got {len(papers)} papers")
        if papers:
            print(f"   First paper: {papers[0].title}")
    except Exception as e:
        print(f"❌ Error getting papers: {e}")
        return
    
    # Test 2: Get chat sessions
    print("\n2️⃣ Testing get_chat_sessions...")
    try:
        sessions = await get_chat_sessions()
        print(f"✅ Successfully got {len(sessions)} sessions")
        
        if sessions:
            for i, session in enumerate(sessions[:3], 1):
                print(f"   Session {i}:")
                print(f"      ID: {session.session_id}")
                print(f"      Paper: {session.paper_title}")
                print(f"      Messages: {session.message_count}")
                print(f"      Created: {session.created_at}")
        else:
            print("   No sessions found")
            
    except Exception as e:
        print(f"❌ Error getting sessions: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎯 API Endpoint Testing Complete!")

if __name__ == "__main__":
    asyncio.run(test_chat_api_endpoints())