#!/usr/bin/env python3
"""
Test script to check rubric loading for position papers.
"""

import sys
sys.path.insert(0, "src")

from src.services.rubric_loader import RubricLoader
from src.services.insight_extraction_service import InsightExtractionService
from src.models.enums import PaperType
from src.models.paper import Paper

def test_rubric_loading():
    """Test if position paper rubric is loaded correctly."""
    
    loader = RubricLoader()
    
    print("Available rubrics:")
    available = loader.list_available_rubrics()
    for rubric_id in available:
        print(f"  - {rubric_id}")
    
    print(f"\nLooking for rubric for paper type: {PaperType.POSITION_PAPER.value}")
    
    # Test the rubric loader directly
    rubric = loader.get_rubric_for_paper_type(PaperType.POSITION_PAPER)
    
    print(f"\n--- Rubric Loader Result ---")
    if rubric:
        print(f"✅ Found rubric: {rubric.name}")
        print(f"   ID: {rubric.id}")
        print(f"   Version: {rubric.version}")
        print(f"   Paper types: {[pt.value for pt in rubric.paper_types]}")
        print(f"   Extraction rules: {len(rubric.extraction_rules)}")
        
        for i, rule in enumerate(rubric.extraction_rules, 1):
            print(f"   Rule {i}: {rule.insight_type.value}")
            print(f"     Min confidence: {rule.minimum_confidence}")
    else:
        print("❌ No rubric found for position papers")
    
    # Test the insight extraction service method
    print(f"\n--- Insight Extraction Service Result ---")
    insight_service = InsightExtractionService()
    
    # Create a mock paper for testing
    mock_paper = Paper(
        title="Test Position Paper",
        abstract="Test abstract",
        paper_type=PaperType.POSITION_PAPER
    )
    
    rubric = insight_service._get_rubric_for_paper(mock_paper)
    
    if rubric:
        print(f"✅ Found rubric: {rubric.name}")
        print(f"   ID: {rubric.id}")
        print(f"   Version: {rubric.version}")
        print(f"   Paper types: {[pt.value for pt in rubric.paper_types]}")
        print(f"   Extraction rules: {len(rubric.extraction_rules)}")
        
        for i, rule in enumerate(rubric.extraction_rules, 1):
            print(f"   Rule {i}: {rule.insight_type.value}")
            print(f"     Min confidence: {rule.minimum_confidence}")
    else:
        print("❌ No rubric found for position papers")
        
        # Try loading the position paper rubric directly
        print("\nTrying to load position_paper_default directly...")
        direct_rubric = loader.load_rubric("position_paper_default")
        if direct_rubric:
            print(f"✅ Direct load successful: {direct_rubric.name}")
            print(f"   ID: {direct_rubric.id}")
            print(f"   Version: {direct_rubric.version}")
            print(f"   Paper types: {[pt.value for pt in direct_rubric.paper_types]}")
            print(f"   Extraction rules: {len(direct_rubric.extraction_rules)}")
            
            for i, rule in enumerate(direct_rubric.extraction_rules, 1):
                print(f"   Rule {i}: {rule.insight_type.value}")
                print(f"     Min confidence: {rule.minimum_confidence}")
        else:
            print("❌ Direct load failed")

if __name__ == "__main__":
    test_rubric_loading() 