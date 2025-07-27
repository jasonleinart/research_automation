#!/usr/bin/env python3
"""
Test the cleaned up chat interface without confusing confidence displays.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.services.paper_qa_service import PaperQAService

async def test_clean_interface():
    """Test the cleaned up interface responses."""
    await db_manager.initialize()
    
    paper_repo = PaperRepository()
    qa_service = PaperQAService()
    
    # Get a test paper
    papers = await paper_repo.list_all()
    test_paper = None
    for paper in papers:
        if "Attention Is All You Need" in paper.title:
            test_paper = paper
            break
    
    if not test_paper:
        test_paper = papers[0]
    
    print("🎨 Testing Clean Chat Interface")
    print("=" * 50)
    print(f"📄 Paper: {test_paper.title}")
    
    test_questions = [
        "What is this paper about?",
        "What programming language was used?",  # Not in paper
        "What are the key innovations?",
        "How does the model perform?"
    ]
    
    for question in test_questions:
        print(f"\n🙋 User: {question}")
        
        qa_response = await qa_service.answer_question(test_paper.id, question)
        
        print(f"🤖 Assistant: {qa_response.answer}")
        
        # Show what the web interface will display
        metadata_display = []
        
        if qa_response.sources:
            metadata_display.append(f"📚 {', '.join(qa_response.sources)}")
        
        if qa_response.limitations:
            metadata_display.append(f"⚠️ {qa_response.limitations}")
        
        if not qa_response.grounded:
            metadata_display.append("ℹ️ Response may not be fully grounded in paper content")
        
        if metadata_display:
            print("   " + " | ".join(metadata_display))
        
        print()

if __name__ == "__main__":
    asyncio.run(test_clean_interface())