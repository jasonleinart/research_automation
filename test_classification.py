#!/usr/bin/env python3
"""
Test script for paper classification system.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.services.paper_classifier import PaperClassifier
from src.services.classification_service import ClassificationService
from src.database.paper_repository import PaperRepository
from src.models.paper import Paper, Author
from src.models.enums import PaperType, EvidenceStrength, PracticalApplicability

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_paper_classifier():
    """Test the paper classifier with sample papers."""
    print("🧪 Testing Paper Classifier...")
    
    classifier = PaperClassifier()
    
    # Test papers with different characteristics
    test_papers = [
        {
            'title': 'A Novel Framework for Deep Learning in Natural Language Processing',
            'abstract': 'We propose a new framework for deep learning that improves performance on NLP tasks. Our approach introduces novel architectural components and demonstrates effectiveness across multiple benchmarks.',
            'expected_type': PaperType.CONCEPTUAL_FRAMEWORK
        },
        {
            'title': 'A Comprehensive Survey of Transformer Architectures',
            'abstract': 'This survey provides a comprehensive overview of transformer architectures in deep learning. We review recent advances and analyze the state-of-the-art methods in the field.',
            'expected_type': PaperType.SURVEY_REVIEW
        },
        {
            'title': 'Empirical Analysis of BERT Performance on Question Answering',
            'abstract': 'We conduct extensive experiments to evaluate BERT performance on question answering tasks. Our empirical study includes evaluation on multiple datasets and analysis of results.',
            'expected_type': PaperType.EMPIRICAL_STUDY
        },
        {
            'title': 'Applying GPT-3 to Customer Service: A Case Study',
            'abstract': 'This paper presents a case study of applying GPT-3 to real-world customer service scenarios. We demonstrate the practical implementation and show effectiveness in production.',
            'expected_type': PaperType.CASE_STUDY
        }
    ]
    
    correct_classifications = 0
    
    for i, test_data in enumerate(test_papers, 1):
        paper = Paper(
            title=test_data['title'],
            abstract=test_data['abstract'],
            authors=[Author(name="Test Author")]
        )
        
        classification = classifier.classify_paper(paper)
        predicted_type = classification['paper_type']
        expected_type = test_data['expected_type']
        confidence = classification['overall_confidence']
        
        is_correct = predicted_type == expected_type
        if is_correct:
            correct_classifications += 1
        
        status = "✅" if is_correct else "❌"
        print(f"  {status} Test {i}: {predicted_type.value} (confidence: {confidence:.1%})")
        print(f"     Expected: {expected_type.value}")
        print(f"     Title: {test_data['title'][:50]}...")
        print()
    
    accuracy = correct_classifications / len(test_papers)
    print(f"📊 Classification Accuracy: {accuracy:.1%} ({correct_classifications}/{len(test_papers)})")
    
    return accuracy > 0.5  # At least 50% accuracy

async def test_classification_service():
    """Test the classification service with real papers from database."""
    print("\n🔧 Testing Classification Service...")
    
    service = ClassificationService()
    repo = PaperRepository()
    
    # Get a few papers from database
    papers = await repo.list_all(limit=3)
    
    if not papers:
        print("  ⚠️  No papers found in database for testing")
        return True
    
    print(f"  Found {len(papers)} papers to test classification")
    
    success_count = 0
    
    for paper in papers:
        print(f"\n  📄 Testing: {paper.title[:50]}...")
        
        result = await service.classify_paper(paper.id)
        
        if result:
            classification = result['classification']
            print(f"     Type: {classification['paper_type'].value}")
            print(f"     Evidence: {classification['evidence_strength'].value}")
            print(f"     Applicability: {classification['practical_applicability'].value}")
            print(f"     Confidence: {classification['overall_confidence']:.1%}")
            print(f"     Status: {result['status'].value}")
            success_count += 1
        else:
            print("     ❌ Classification failed")
    
    success_rate = success_count / len(papers)
    print(f"\n  📊 Service Success Rate: {success_rate:.1%} ({success_count}/{len(papers)})")
    
    return success_rate > 0.8  # At least 80% success rate

async def test_classification_stats():
    """Test classification statistics."""
    print("\n📈 Testing Classification Statistics...")
    
    service = ClassificationService()
    stats = await service.get_classification_stats()
    
    if not stats:
        print("  ❌ Failed to get classification stats")
        return False
    
    print(f"  ✅ Retrieved stats with {len(stats)} fields")
    
    required_fields = ['total_papers', 'analyzed_papers', 'pending_papers']
    for field in required_fields:
        if field in stats:
            print(f"     {field}: {stats[field]}")
        else:
            print(f"  ⚠️  Missing field: {field}")
    
    return all(field in stats for field in required_fields)

async def main():
    """Run all classification tests."""
    try:
        print("🚀 Starting classification system tests...\n")
        
        # Initialize database
        await db_manager.initialize()
        
        # Run tests
        test_results = []
        
        test_results.append(await test_paper_classifier())
        test_results.append(await test_classification_service())
        test_results.append(await test_classification_stats())
        
        # Summary
        passed = sum(test_results)
        total = len(test_results)
        
        print(f"\n📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("✅ All classification tests passed! System is ready.")
        else:
            print("❌ Some tests failed. Check the logs above.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        sys.exit(1)
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())