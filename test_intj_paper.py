#!/usr/bin/env python3
"""
Test the Q&A system with the actual INTJ/MBTI paper.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.services.paper_qa_service import PaperQAService
from src.services.context_loader import ContextLoader

async def test_intj_paper():
    """Test Q&A with the actual INTJ paper."""
    await db_manager.initialize()
    
    paper_repo = PaperRepository()
    qa_service = PaperQAService()
    context_loader = ContextLoader()
    
    # Find the INTJ paper
    papers = await paper_repo.list_all()
    intj_paper = None
    
    for paper in papers:
        if 'INTJ' in paper.title or 'MBTI' in paper.title or 'Jungian' in paper.title:
            intj_paper = paper
            break
    
    if not intj_paper:
        print("❌ INTJ/MBTI paper not found!")
        return
    
    print(f"📄 Found INTJ paper: {intj_paper.title}")
    print("=" * 60)
    
    # First, let's check what context is being loaded
    print("🔍 Loading paper context...")
    context = await context_loader.load_paper_context(intj_paper.id)
    
    print(f"📊 Context Summary:")
    print(f"   Total tokens: {context.total_tokens}")
    print(f"   Content chunks: {len(context.chunks)}")
    print(f"   Related papers: {len(context.related_papers)}")
    
    print(f"\n📝 Content Preview (first 800 chars):")
    print(context.formatted_content[:800] + "..." if len(context.formatted_content) > 800 else context.formatted_content)
    
    # Now test the INTJ question
    print(f"\n💬 Testing INTJ Questions:")
    print("-" * 40)
    
    intj_questions = [
        "Why are INTJ likely to succeed?",
        "What makes INTJ successful in computer careers?",
        "What are the characteristics of INTJ personality type?",
        "How do INTJ cognitive functions relate to career success?",
        "What does this paper say about INTJ in the computer industry?"
    ]
    
    for question in intj_questions:
        print(f"\n🙋 Question: {question}")
        
        try:
            qa_response = await qa_service.answer_question(intj_paper.id, question)
            
            print(f"🤖 Answer: {qa_response.answer}")
            print(f"📊 Confidence: {qa_response.confidence:.2f}")
            print(f"🔗 Grounded: {'✅' if qa_response.grounded else '❌'}")
            
            if qa_response.sources:
                print(f"📚 Sources: {', '.join(qa_response.sources)}")
            
            if qa_response.limitations:
                print(f"⚠️ Limitations: {qa_response.limitations}")
                
            # Check if response actually addresses the question
            if "not provided in the paper" in qa_response.answer.lower():
                print("🚨 WARNING: System says info not in paper - this might be a context loading issue!")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()

if __name__ == "__main__":
    asyncio.run(test_intj_paper())