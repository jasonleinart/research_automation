#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database.connection import get_database_connection
from src.database.insight_repository import InsightRepository

async def check_insight_content():
    async with get_database_connection() as conn:
        insight_repo = InsightRepository(conn)
        
        # Get all insights for the paper
        insights = await insight_repo.get_insights_for_paper("43bfc09d-d3d0-4f97-aa96-53006aa1f4a8")
        
        print("=== INSIGHT CONTENT ANALYSIS ===\n")
        
        for insight in insights:
            print(f"Type: {insight.insight_type}")
            print(f"Confidence: {insight.confidence}")
            print(f"Content Type: {type(insight.content)}")
            print(f"Content Length: {len(str(insight.content))}")
            print(f"Content Preview: {str(insight.content)[:200]}...")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(check_insight_content()) 