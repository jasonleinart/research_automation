#!/usr/bin/env python3
"""
Script to extract position-specific insights from the Group Recommender paper.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, "src")

from src.database.connection import db_manager
from src.services.insight_extraction_service import InsightExtractionService
from src.database.paper_repository import PaperRepository
from src.models.enums import PaperType

async def extract_position_insights():
    """Extract position-specific insights from the Group Recommender paper."""
    
    await db_manager.initialize()
    
    try:
        # Get the Group Recommender paper
        paper_repo = PaperRepository()
        papers = await paper_repo.list_all()
        
        group_recommender_paper = None
        for paper in papers:
            if "Group Recommender" in paper.title:
                group_recommender_paper = paper
                break
        
        if not group_recommender_paper:
            print("❌ Group Recommender paper not found")
            return
        
        print(f"📄 Found paper: {group_recommender_paper.title}")
        print(f"📋 Paper Type: {group_recommender_paper.paper_type.value}")
        print(f"📊 Analysis Status: {group_recommender_paper.analysis_status.value}")
        print(f"🎯 Confidence: {group_recommender_paper.analysis_confidence*100:.1f}%")
        
        # Initialize insight extraction service
        insight_service = InsightExtractionService()
        
        print(f"\n🔍 Extracting position-specific insights...")
        
        # Extract insights using the position paper rubric
        insights = await insight_service.extract_insights_from_paper(group_recommender_paper.id)
        
        if not insights:
            print("❌ No insights extracted")
            return
        
        print(f"\n✅ Extracted {len(insights)} insights:")
        
        # Save insights to database
        from src.database.insight_repository import InsightRepository
        insight_repo = InsightRepository()
        
        saved_insights = []
        for insight in insights:
            try:
                saved_insight = await insight_repo.create(insight)
                saved_insights.append(saved_insight)
                print(f"💾 Saved {insight.insight_type.value} insight to database")
            except Exception as e:
                print(f"❌ Failed to save {insight.insight_type.value} insight: {e}")
        
        print(f"💾 Successfully saved {len(saved_insights)} insights to database")
        
        for i, insight in enumerate(insights, 1):
            print(f"\n--- Insight {i}: {insight.insight_type.value.upper()} ---")
            print(f"Title: {insight.title}")
            print(f"Confidence: {insight.confidence*100:.1f}%")
            print(f"Extraction Method: {insight.extraction_method}")
            
            # Parse and display content structure
            try:
                content = eval(insight.content) if isinstance(insight.content, str) else insight.content
                print("Content Structure:")
                for key, value in content.items():
                    if isinstance(value, list):
                        print(f"  {key}: {len(value)} items")
                        for j, item in enumerate(value[:3], 1):  # Show first 3 items
                            if isinstance(item, dict):
                                print(f"    {j}. {list(item.keys())}")
                            else:
                                print(f"    {j}. {str(item)[:100]}...")
                        if len(value) > 3:
                            print(f"    ... and {len(value) - 3} more")
                    else:
                        print(f"  {key}: {str(value)[:100]}...")
            except Exception as e:
                print(f"  Content: {insight.content[:200]}...")
                print(f"  (Error parsing content: {e})")
        
        # Create tags from insights
        print(f"\n🏷️ Creating tags from insights...")
        tags = await insight_service.create_tags_from_insights(insights)
        
        if tags:
            print(f"✅ Created {len(tags)} tags:")
            for tag in tags:
                print(f"  - {tag.name} ({tag.category.value})")
        
        print(f"\n🎉 Position paper insight extraction completed!")
        
    except Exception as e:
        print(f"❌ Error during insight extraction: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(extract_position_insights()) 