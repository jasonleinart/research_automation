#!/usr/bin/env python3
"""
Simple script to check insights for the Group Recommender paper.
"""

import asyncio
import sys
sys.path.insert(0, "src")

from src.database.connection import db_manager
from src.database.insight_repository import InsightRepository

async def check_insights():
    """Check insights for the Group Recommender paper."""
    await db_manager.initialize()
    
    try:
        repo = InsightRepository()
        insights = await repo.get_by_paper_id('43bfc09d-d3d0-4f97-aa96-53006aa1f4a8')
        
        print(f"Found {len(insights)} insights for Group Recommender paper:")
        print()
        
        for insight in insights:
            print(f"🔍 {insight.insight_type.value.upper()}")
            print(f"   Title: {insight.title}")
            print(f"   Confidence: {insight.confidence:.1%}")
            print(f"   Method: {insight.extraction_method}")
            
            if insight.content:
                print(f"   Content preview: {str(insight.content)[:100]}...")
            print()
            
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_insights()) 