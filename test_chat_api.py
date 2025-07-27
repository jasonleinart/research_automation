#!/usr/bin/env python3
"""
Test the chat API endpoints directly.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.database.connection import db_manager
from src.web.api.chat import get_papers_for_chat, send_chat_message, get_question_suggestions, ChatRequest

async def test_chat_api():
    """Test the chat API functionality."""
    await db_manager.initialize()
    
    print("🧪 Testing Chat API Endpoints")
    print("=" * 50)
    
    # Test 1: Get papers for chat
    print("\n📚 Testing get_papers_for_chat...")
    try:
        papers = await get_papers_for_chat()
        print(f"✅ Found {len(papers)} papers available for chat")
        if papers:
            print(f"   First paper: {papers[0].title}")
            test_paper = papers[0]
        else:
            print("❌ No papers found")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Test 2: Get question suggestions
    print(f"\n💡 Testing question suggestions for paper: {test_paper.title[:50]}...")
    try:
        suggestions = await get_question_suggestions(test_paper.id)
        print(f"✅ Got {len(suggestions)} suggestions:")
        for i, suggestion in enumerate(suggestions[:3], 1):
            print(f"   {i}. {suggestion}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Send chat message
    print(f"\n💬 Testing chat message...")
    try:
        request = ChatRequest(
            paper_id=test_paper.id,
            message="What is this paper about?"
        )
        response = await send_chat_message(request)
        print(f"✅ Got response:")
        print(f"   Response: {response.response[:200]}...")
        print(f"   Confidence: {response.confidence:.2f}")
        print(f"   Grounded: {response.grounded}")
        print(f"   Sources: {response.sources}")
        print(f"   Session ID: {response.session_id}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n🎉 Chat API testing complete!")

if __name__ == "__main__":
    asyncio.run(test_chat_api())