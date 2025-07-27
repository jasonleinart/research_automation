#!/usr/bin/env python3
"""
Script to show the full parsed content of position-specific insights.
"""

import asyncio
import sys
import json
import ast
sys.path.insert(0, "src")

from src.database.connection import db_manager
from src.database.insight_repository import InsightRepository

async def show_full_content():
    """Show the full parsed content of position-specific insights."""
    await db_manager.initialize()
    
    try:
        repo = InsightRepository()
        insights = await repo.get_by_paper_id('43bfc09d-d3d0-4f97-aa96-53006aa1f4a8')
        
        print(f"📄 Group Recommender Paper - Full Content Analysis")
        print(f"Found {len(insights)} insights:")
        print("=" * 80)
        
        for i, insight in enumerate(insights, 1):
            print(f"\n🔍 INSIGHT {i}: {insight.insight_type.value.upper()}")
            print(f"   Title: {insight.title}")
            print(f"   Confidence: {insight.confidence:.1%}")
            print(f"   Method: {insight.extraction_method}")
            print("-" * 60)
            
            # Try to parse the content
            try:
                if isinstance(insight.content, str):
                    # Try to evaluate as Python literal
                    parsed_content = ast.literal_eval(insight.content)
                else:
                    parsed_content = insight.content
                
                print("📋 FULL CONTENT:")
                print(json.dumps(parsed_content, indent=2, ensure_ascii=False))
                
            except (ValueError, SyntaxError) as e:
                print(f"❌ Could not parse content: {e}")
                print(f"Raw content: {insight.content[:500]}...")
            
            print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(show_full_content()) 