#!/usr/bin/env python3
"""
Test the new context loader functionality.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.services.context_loader import ContextLoader
from src.services.conversation_service import ConversationService

async def test_context_loader():
    """Test the new context loader functionality."""
    await db_manager.initialize()
    
    paper_repo = PaperRepository()
    context_loader = ContextLoader()
    conversation_service = ConversationService()
    
    # Get the Attention paper
    papers = await paper_repo.list_all()
    attention_paper = None
    for paper in papers:
        if "Attention Is All You Need" in paper.title:
            attention_paper = paper
            break
    
    if not attention_paper:
        print("❌ Attention paper not found")
        return
    
    print(f"📄 Testing context loader with: {attention_paper.title}")
    
    # Test the context loader
    print("\\n🔄 Loading paper context...")
    paper_context = await context_loader.load_paper_context(attention_paper.id)
    
    print(f"\\n📊 Context Summary:")
    print(context_loader.get_context_summary(paper_context))
    
    print(f"\\n📝 Formatted Content Preview (first 500 chars):")
    print(paper_context.formatted_content[:500] + "..." if len(paper_context.formatted_content) > 500 else paper_context.formatted_content)
    
    # Test the enhanced chat functionality
    print("\\n💬 Testing enhanced chat functionality:")
    test_questions = [
        "What is this paper about?",
        "What are the key innovations?",
        "How does this relate to other papers in my database?"
    ]
    
    for question in test_questions:
        print(f"\\n❓ Question: {question}")
        try:
            response = await conversation_service.chat(attention_paper.id, question)
            print(f"🤖 Response: {response[:300]}..." if len(response) > 300 else f"🤖 Response: {response}")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_context_loader())