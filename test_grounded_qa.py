#!/usr/bin/env python3
"""
Test the grounded Q&A system functionality.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.services.paper_qa_service import PaperQAService
from src.services.conversation_service import ConversationService

async def test_grounded_qa():
    """Test the grounded Q&A system with various question types."""
    await db_manager.initialize()
    
    paper_repo = PaperRepository()
    qa_service = PaperQAService()
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
    
    print(f"📄 Testing grounded Q&A with: {attention_paper.title}")
    print("=" * 60)
    
    # Test different types of questions
    test_questions = [
        # Summary questions
        ("What is this paper about?", "summary"),
        ("Can you summarize the main contributions?", "summary"),
        
        # Methodology questions  
        ("How does the Transformer architecture work?", "methodology"),
        ("What approach did the authors use?", "methodology"),
        
        # Results questions
        ("What were the performance results?", "results"),
        ("How well did the model perform on translation tasks?", "results"),
        
        # Author questions
        ("Who wrote this paper?", "authors"),
        
        # Technical questions
        ("What is multi-head attention?", "technical"),
        ("How does positional encoding work?", "technical"),
        
        # Questions that might not be in the paper
        ("What programming language was used for implementation?", "not_in_paper"),
        ("What was the computational cost of training?", "maybe_not_in_paper"),
    ]
    
    for question, question_type in test_questions:
        print(f"\n🔍 Question Type: {question_type}")
        print(f"❓ Question: {question}")
        print("-" * 40)
        
        try:
            # Test detailed Q&A response
            qa_response = await qa_service.answer_question(attention_paper.id, question)
            
            print(f"🤖 Answer: {qa_response.answer}")
            print(f"📊 Confidence: {qa_response.confidence:.2f}")
            print(f"🔗 Grounded: {'✅' if qa_response.grounded else '❌'}")
            
            if qa_response.sources:
                print(f"📚 Sources: {', '.join(qa_response.sources)}")
            
            if qa_response.limitations:
                print(f"⚠️ Limitations: {qa_response.limitations}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
    
    # Test follow-up questions
    print("\n" + "=" * 60)
    print("🔄 Testing Follow-up Questions")
    print("=" * 60)
    
    # First question
    original_question = "What is the Transformer architecture?"
    print(f"❓ Original: {original_question}")
    
    original_response = await qa_service.answer_question(attention_paper.id, original_question)
    print(f"🤖 Answer: {original_response.answer[:200]}...")
    
    # Follow-up question
    followup_question = "How does it differ from RNNs?"
    print(f"\n❓ Follow-up: {followup_question}")
    
    followup_response = await qa_service.ask_followup(
        attention_paper.id, original_question, original_response, followup_question
    )
    print(f"🤖 Answer: {followup_response.answer}")
    print(f"📊 Confidence: {followup_response.confidence:.2f}")
    
    # Test question suggestions
    print("\n" + "=" * 60)
    print("💡 Question Suggestions")
    print("=" * 60)
    
    suggestions = qa_service.get_question_suggestions(attention_paper)
    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion}")
    
    # Test conversation service integration
    print("\n" + "=" * 60)
    print("🗣️ Testing Conversation Service Integration")
    print("=" * 60)
    
    test_chat_questions = [
        "What problem does this paper solve?",
        "What are the key innovations?",
        "How was the model evaluated?"
    ]
    
    for question in test_chat_questions:
        print(f"\n❓ Question: {question}")
        response = await conversation_service.chat(attention_paper.id, question)
        print(f"🤖 Response: {response[:300]}..." if len(response) > 300 else f"🤖 Response: {response}")

if __name__ == "__main__":
    asyncio.run(test_grounded_qa())