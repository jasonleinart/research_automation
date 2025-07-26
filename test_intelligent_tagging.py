#!/usr/bin/env python3
"""
Test script for the new intelligent tagging system with vector embeddings and LLM enhancement.
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.services.insight_extraction_service import InsightExtractionService
from src.services.tag_similarity_service import TagSimilarityService
from src.database.paper_repository import PaperRepository
from src.models.enums import AnalysisStatus, TagCategory

async def test_tag_similarity_service():
    """Test the tag similarity service functionality."""
    print("🧪 Testing Tag Similarity Service...")
    
    service = TagSimilarityService()
    
    # Test cases for different categories
    test_cases = [
        ("attention mechanism", TagCategory.CONCEPT),
        ("neural networks", TagCategory.CONCEPT),
        ("machine learning", TagCategory.CONCEPT),
        ("data preprocessing", TagCategory.METHODOLOGY),
        ("text classification", TagCategory.APPLICATION),
        ("transformer architecture", TagCategory.CONCEPT),
    ]
    
    for term, category in test_cases:
        print(f"\n🔍 Testing: '{term}' ({category.value})")
        
        # Test finding similar tags
        similar_tags = await service.find_similar_tags(term, category, limit=3)
        print(f"   Similar tags found: {len(similar_tags)}")
        for tag, similarity in similar_tags:
            print(f"     - {tag.name}: {similarity:.3f}")
        
        # Test LLM generalization
        suggested = await service.suggest_generalized_tag(term, category)
        print(f"   LLM suggestion: {suggested}")

async def test_intelligent_tag_creation():
    """Test the intelligent tag creation process."""
    print("\n🧪 Testing Intelligent Tag Creation...")
    
    service = InsightExtractionService()
    
    # Test cases with various terms that should be generalized
    test_terms = [
        ("attention-is-all-you-need-framework", TagCategory.CONCEPT),
        ("step-1-tokenization-process", TagCategory.METHODOLOGY),
        ("bert-transformer-model", TagCategory.CONCEPT),
        ("deep-neural-network-architecture", TagCategory.CONCEPT),
        ("natural-language-processing-pipeline", TagCategory.METHODOLOGY),
        ("sentiment-analysis-application", TagCategory.APPLICATION),
    ]
    
    for term, category in test_terms:
        print(f"\n🏷️  Testing tag creation: '{term}' ({category.value})")
        
        tag = await service._process_and_create_tag(term, category)
        if tag:
            print(f"   ✅ Created tag: {tag.name} ({tag.category.value})")
            print(f"   Description: {tag.description}")
        else:
            print(f"   ❌ Failed to create tag")

async def test_with_real_papers():
    """Test the intelligent tagging with real papers in the database."""
    print("\n🧪 Testing with Real Papers...")
    
    paper_repo = PaperRepository()
    service = InsightExtractionService()
    
    # Get papers that have insights but might need better tags
    papers = await paper_repo.get_by_status(AnalysisStatus.COMPLETED, limit=2)
    
    if not papers:
        print("❌ No completed papers found for testing")
        return
    
    for paper in papers:
        print(f"\n📄 Testing paper: {paper.title[:60]}...")
        
        # Extract insights
        insights = await service.extract_insights_from_paper(paper.id)
        print(f"   Extracted {len(insights)} insights")
        
        if insights:
            # Create tags using the new intelligent system
            tags = await service.create_tags_from_insights(insights)
            print(f"   Created {len(tags)} intelligent tags:")
            for tag in tags:
                print(f"     - {tag.name} ({tag.category.value})")

async def test_embedding_generation():
    """Test embedding generation for tags."""
    print("\n🧪 Testing Embedding Generation...")
    
    service = TagSimilarityService()
    
    # Test embedding generation
    test_texts = [
        "transformer architecture",
        "attention mechanism", 
        "neural networks",
        "machine learning",
        "deep learning"
    ]
    
    for text in test_texts:
        embedding = await service._get_embedding(text)
        if embedding:
            print(f"   ✅ Generated embedding for '{text}' ({len(embedding)} dimensions)")
        else:
            print(f"   ❌ Failed to generate embedding for '{text}'")

async def main():
    """Main test function."""
    print("🚀 Testing Intelligent Tagging System with Vector Embeddings and LLM Enhancement")
    print("=" * 80)
    
    try:
        await db_manager.initialize()
        
        # Run tests
        await test_embedding_generation()
        await test_tag_similarity_service()
        await test_intelligent_tag_creation()
        await test_with_real_papers()
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 