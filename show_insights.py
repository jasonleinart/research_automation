#!/usr/bin/env python3
"""
Show current insights and their structure for relationship analysis.
"""

import asyncio
import json
from src.database.insight_repository import InsightRepository

async def main():
    from src.database.connection import db_manager
    await db_manager.initialize()
    
    repo = InsightRepository()
    
    print("🔍 Current Insights and Their Structure:\n")
    
    # Get insights with paper information
    insights_with_papers = await repo.get_insights_with_papers()
    
    if not insights_with_papers:
        print("No insights found in database.")
        return
    
    for i, item in enumerate(insights_with_papers, 1):
        insight = item["insight"]
        paper = item["paper"]
        
        print(f"📄 {i}. {insight.title}")
        print(f"   Paper: {paper['title'][:60]}...")
        print(f"   Type: {insight.insight_type.value}")
        print(f"   Confidence: {insight.confidence:.1%}")
        print(f"   Content Structure:")
        
        if insight.content:
            for key, value in insight.content.items():
                if isinstance(value, list):
                    print(f"     - {key}: [{len(value)} items]")
                    if value and len(str(value[0])) < 100:
                        print(f"       Example: {value[0]}")
                elif isinstance(value, str):
                    preview = value[:80] + "..." if len(value) > 80 else value
                    print(f"     - {key}: \"{preview}\"")
                else:
                    print(f"     - {key}: {type(value).__name__}")
        
        print()
    
    # Show statistics
    stats = await repo.get_statistics()
    print("📊 Insight Statistics:")
    print(f"   Total insights: {stats.get('total_insights', 0)}")
    print(f"   Average confidence: {stats.get('avg_confidence', 0):.1%}")
    print(f"   Papers with insights: {stats.get('papers_with_insights', 0)}")
    
    print("\n📈 Type Distribution:")
    for insight_type, count in stats.get('type_distribution', {}).items():
        print(f"   - {insight_type}: {count}")

if __name__ == "__main__":
    asyncio.run(main())