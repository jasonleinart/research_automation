#!/usr/bin/env python3
"""
Test the enhanced chat UI with conversation history.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.services.conversation_service import ConversationService

async def create_test_conversations():
    """Create some test conversations for the UI."""
    await db_manager.initialize()
    
    paper_repo = PaperRepository()
    conversation_service = ConversationService()
    
    # Get test papers
    papers = await paper_repo.list_all()
    if len(papers) < 2:
        print("❌ Need at least 2 papers for testing")
        return
    
    print("🧪 Creating test conversations for UI...")
    
    # Create conversation 1
    paper1 = papers[0]
    session1 = await conversation_service.create_persistent_session(paper1.id)
    
    test_messages_1 = [
        "What is this paper about?",
        "Who are the authors?",
        "What are the main contributions?"
    ]
    
    print(f"📝 Creating conversation 1 with {paper1.title}")
    for msg in test_messages_1:
        await conversation_service.send_persistent_message(session1.session_id, msg)
    
    # Create conversation 2
    paper2 = papers[1]
    session2 = await conversation_service.create_persistent_session(paper2.id)
    
    test_messages_2 = [
        "Can you summarize this paper?",
        "What methodology was used?"
    ]
    
    print(f"📝 Creating conversation 2 with {paper2.title}")
    for msg in test_messages_2:
        await conversation_service.send_persistent_message(session2.session_id, msg)
    
    # List all conversations
    conversations = await conversation_service.list_conversations()
    print(f"\n✅ Created {len(conversations)} conversations:")
    
    for conv in conversations:
        print(f"   • {conv['conversation_title'] or 'Untitled'}")
        print(f"     Paper: {conv['paper_title']}")
        print(f"     Messages: {conv['message_count']}")
        print(f"     Last activity: {conv['last_activity']}")
        print()
    
    print("🎉 Test conversations created! You can now:")
    print("   1. Visit http://localhost:8001/chat")
    print("   2. See previous conversations in the sidebar")
    print("   3. Click on any conversation to resume it")
    print("   4. Start new conversations with the + button")

if __name__ == "__main__":
    asyncio.run(create_test_conversations())