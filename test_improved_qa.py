#!/usr/bin/env python3
"""
Test the improved Q&A system with better response quality.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.services.paper_qa_service import PaperQAService

async def test_improved_qa():
    """Test the improved Q&A system."""
    await db_manager.initialize()
    
    paper_repo = PaperRepository()
    qa_service = PaperQAService()
    
    # Get papers
    papers = await paper_repo.list_all()
    
    # Find a paper to test with
    test_paper = None
    for paper in papers:
        if "Attention Is All You Need" in paper.title:
            test_paper = paper
            break
    
    if not test_paper:
        test_paper = papers[0]
    
    print(f"🧪 Testing Improved Q&A with: {test_paper.title}")
    print("=" * 60)
    
    # Test questions that should get specific, direct answers
    test_questions = [
        "Why are INTJ likely to succeed?",  # Your example question
        "What specific advantages does the Transformer have over RNNs?",
        "What were the exact BLEU scores achieved?",
        "How does multi-head attention work?",
        "What problem does this paper solve?",
        "What makes this approach different from previous methods?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n🙋 Question {i}: {question}")
        print("-" * 40)
        
        try:
            qa_response = await qa_service.answer_question(test_paper.id, question)
            
            print(f"🤖 Answer: {qa_response.answer}")
            print(f"📊 Confidence: {qa_response.confidence:.2f}")
            print(f"🔗 Grounded: {'✅' if qa_response.grounded else '❌'}")
            
            if qa_response.sources:
                print(f"📚 Sources: {', '.join(qa_response.sources)}")
            
            if qa_response.limitations:
                print(f"⚠️ Limitations: {qa_response.limitations}")
                
            # Analyze response quality
            response_text = qa_response.answer.lower()
            section_refs = sum(1 for ref in ["section", "introduction", "abstract", "see "] if ref in response_text)
            
            if section_refs > 2:
                print("⚠️ Response Quality: Too many section references")
            elif len(qa_response.answer) < 100:
                print("⚠️ Response Quality: Response might be too brief")
            elif "specifically" in response_text or "because" in response_text:
                print("✅ Response Quality: Good specificity")
            else:
                print("ℹ️ Response Quality: Standard response")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n🎯 Testing Complete!")
    print("Key improvements:")
    print("• Less section referencing")
    print("• More direct, specific answers")
    print("• Focus on actual content over structure")

if __name__ == "__main__":
    asyncio.run(test_improved_qa())