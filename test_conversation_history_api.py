#!/usr/bin/env python3
"""
Test the conversation history API endpoint.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.database.connection import db_manager
from src.services.conversation_service import ConversationService

async def test_conversation_history_api():
    """Test the conversation history API endpoint."""
    await db_manager.initialize()
    
    conversation_service = ConversationService()
    
    print("🧪 Testing Conversation History API")
    print("=" * 50)
    
    # Get existing sessions
    sessions = await conversation_service.list_conversations(limit=5)
    
    if not sessions:
        print("❌ No sessions found")
        return
    
    print(f"📋 Found {len(sessions)} sessions")
    
    # Test each session's history
    for i, session_data in enumerate(sessions, 1):
        session_id = session_data['id']
        print(f"\n{i}️⃣ Testing session: {session_id}")
        print(f"   Paper: {session_data['paper_title']}")
        print(f"   Messages: {session_data['message_count']}")
        
        try:
            # Test getting conversation history
            history = await conversation_service.get_conversation_history(session_id)
            print(f"   ✅ Retrieved {len(history)} messages from history")
            
            # Show first few messages
            for j, msg in enumerate(history[:2], 1):
                role_emoji = "🙋" if msg.role == "user" else "🤖"
                print(f"      {role_emoji} {msg.role}: {msg.content[:50]}...")
                if msg.confidence:
                    print(f"         Confidence: {msg.confidence}")
                if msg.grounded:
                    print(f"         Grounded: ✅")
                    
        except Exception as e:
            print(f"   ❌ Error getting history: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n🎯 Conversation History API Testing Complete!")

if __name__ == "__main__":
    asyncio.run(test_conversation_history_api())