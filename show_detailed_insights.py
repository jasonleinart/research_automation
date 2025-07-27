#!/usr/bin/env python3
"""
Script to show detailed content of all insights for the Group Recommender paper.
"""

import asyncio
import sys
import json
sys.path.insert(0, "src")

from src.database.connection import db_manager
from src.database.insight_repository import InsightRepository

async def show_detailed_insights():
    """Show detailed content of all insights for the Group Recommender paper."""
    await db_manager.initialize()
    
    try:
        repo = InsightRepository()
        insights = await repo.get_by_paper_id('43bfc09d-d3d0-4f97-aa96-53006aa1f4a8')
        
        print(f"📄 Group Recommender Paper Insights")
        print(f"Found {len(insights)} insights:")
        print("=" * 80)
        
        for i, insight in enumerate(insights, 1):
            print(f"\n🔍 INSIGHT {i}: {insight.insight_type.value.upper()}")
            print(f"   Title: {insight.title}")
            print(f"   Confidence: {insight.confidence:.1%}")
            print(f"   Method: {insight.extraction_method}")
            print("-" * 60)
            
            if insight.content:
                # Parse content if it's a string
                if isinstance(insight.content, str):
                    try:
                        content = eval(insight.content)
                    except:
                        content = insight.content
                else:
                    content = insight.content
                
                # Display content structure
                if isinstance(content, dict):
                    for key, value in content.items():
                        print(f"   {key.upper()}:")
                        if isinstance(value, list):
                            for j, item in enumerate(value, 1):
                                if isinstance(item, dict):
                                    print(f"     {j}. {list(item.keys())}")
                                    for subkey, subvalue in item.items():
                                        if isinstance(subvalue, str) and len(subvalue) > 100:
                                            print(f"       {subkey}: {subvalue[:100]}...")
                                        else:
                                            print(f"       {subkey}: {subvalue}")
                                else:
                                    print(f"     {j}. {str(item)[:100]}...")
                        elif isinstance(value, str) and len(value) > 100:
                            print(f"     {value[:100]}...")
                        else:
                            print(f"     {value}")
                else:
                    print(f"   Content: {str(content)[:200]}...")
            else:
                print("   No content available")
            
            print()
            
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(show_detailed_insights()) 