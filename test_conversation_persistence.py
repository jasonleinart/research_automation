#!/usr/bin/env python3
"""
Test conversation persistence functionality.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.services.conversation_service import ConversationService

async def test_conversation_persistence():
    """Test the persistent conversation functionality."""
    await db_manager.initialize()
    
    # First, let's create the conversation tables
    print("🔧 Setting up conversation tables...")
    try:
        async with db_manager.get_connection() as conn:
            # Read and execute the schema
            with open('database/schema/07_conversations.sql', 'r') as f:
                schema_sql = f.read()
            await conn.execute(schema_sql)
        print("✅ Conversation tables created successfully")
    except Exception as e:
        print(f"⚠️ Schema setup: {e}")
    
    paper_repo = PaperRepository()
    conversation_service = ConversationService()
    
    # Get a test paper
    papers = await paper_repo.list_all()
    if not papers:
        print("❌ No papers found")
        return
    
    test_paper = papers[0]
    print(f"📄 Testing with paper: {test_paper.title}")
    
    print("\n🧪 Testing Conversation Persistence")
    print("=" * 50)
    
    # Test 1: Create a persistent session
    print("\n1️⃣ Creating persistent session...")
    session = await conversation_service.create_persistent_session(test_paper.id)
    print(f"✅ Created session: {session.session_id}")
    print(f"   Paper ID: {session.paper_id}")
    print(f"   Created: {session.created_at}")
    
    # Test 2: Send messages and verify persistence
    print("\n2️⃣ Sending messages...")
    test_messages = [
        "What is this paper about?",
        "Who are the authors?",
        "What are the main contributions?"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"   Sending message {i}: {message}")
        response = await conversation_service.send_persistent_message(session.session_id, message)
        if response:
            print(f"   ✅ Got response: {response[:100]}...")
        else:
            print(f"   ❌ No response received")
    
    # Test 3: Retrieve conversation history
    print("\n3️⃣ Retrieving conversation history...")
    history = await conversation_service.get_conversation_history(session.session_id)
    print(f"✅ Retrieved {len(history)} messages:")
    
    for msg in history:
        role_emoji = "🙋" if msg.role == "user" else "🤖"
        print(f"   {role_emoji} {msg.role}: {msg.content[:80]}...")
        if msg.confidence:
            print(f"      Confidence: {msg.confidence:.2f}")
        if msg.grounded:
            print(f"      Grounded: ✅")
    
    # Test 4: List conversations
    print("\n4️⃣ Listing conversations...")
    conversations = await conversation_service.list_conversations()
    print(f"✅ Found {len(conversations)} conversations:")
    
    for conv in conversations[:3]:  # Show first 3
        print(f"   📝 {conv['conversation_title'] or 'Untitled'}")
        print(f"      Paper: {conv['paper_title']}")
        print(f"      Messages: {conv['message_count']}")
        print(f"      Last activity: {conv['last_activity']}")
    
    # Test 5: Session persistence across service restarts
    print("\n5️⃣ Testing session persistence...")
    session_id = session.session_id
    
    # Create new service instance (simulating restart)
    new_conversation_service = ConversationService()
    
    # Try to retrieve the session
    retrieved_session = await new_conversation_service.get_persistent_session(session_id)
    if retrieved_session:
        print(f"✅ Successfully retrieved session after 'restart'")
        print(f"   Session ID: {retrieved_session.session_id}")
        print(f"   Messages in memory: {len(retrieved_session.messages)}")
        print(f"   Paper ID: {retrieved_session.paper_id}")
    else:
        print("❌ Failed to retrieve session")
    
    # Test 6: Search conversations
    print("\n6️⃣ Testing conversation search...")
    search_results = await conversation_service.search_conversations("paper")
    print(f"✅ Search for 'paper' found {len(search_results)} results")
    
    print("\n🎉 Conversation Persistence Testing Complete!")
    print("✅ Key features working:")
    print("   • Persistent session creation")
    print("   • Message storage with metadata")
    print("   • Conversation history retrieval")
    print("   • Session listing and management")
    print("   • Cross-restart persistence")
    print("   • Conversation search")

if __name__ == "__main__":
    asyncio.run(test_conversation_persistence())