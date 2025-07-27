#!/usr/bin/env python3
"""
Script to view detailed information about specific insights.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.database.insight_repository import InsightRepository
from src.database.paper_repository import PaperRepository

async def view_insight_details(insight_id: str = None):
    """View detailed information about insights."""
    try:
        await db_manager.initialize()
        
        repo = InsightRepository()
        paper_repo = PaperRepository()
        
        if insight_id:
            # View specific insight
            insight = await repo.get_by_id(insight_id)
            if not insight:
                print(f"❌ Insight with ID {insight_id} not found")
                return
            
            paper = await paper_repo.get_by_id(insight.paper_id)
            
            print(f"🔍 Insight Details:")
            print(f"   ID: {insight.id}")
            print(f"   Type: {insight.insight_type.value}")
            print(f"   Title: {insight.title}")
            print(f"   Confidence: {insight.confidence:.1%}" if insight.confidence else "   Confidence: Not set")
            print(f"   Paper: {paper.title if paper else 'Unknown'}")
            print(f"   Description: {insight.description}")
            print()
            
            if insight.content:
                print("📋 Content:")
                for key, value in insight.content.items():
                    if isinstance(value, list):
                        print(f"   {key}: {len(value)} items")
                        for i, item in enumerate(value[:3]):  # Show first 3 items
                            print(f"     {i+1}. {str(item)[:100]}...")
                        if len(value) > 3:
                            print(f"     ... and {len(value) - 3} more items")
                    else:
                        print(f"   {key}: {str(value)[:200]}...")
            else:
                print("📋 Content: No structured content available")
                
        else:
            # List all insights with IDs
            insights_with_papers = await repo.get_insights_with_papers()
            
            print("📚 All Insights (with IDs):")
            print("-" * 80)
            
            for i, item in enumerate(insights_with_papers, 1):
                insight = item["insight"]
                paper = item["paper"]
                
                print(f"{i:2d}. ID: {insight.id}")
                print(f"    Type: {insight.insight_type.value}")
                print(f"    Title: {insight.title}")
                print(f"    Paper: {paper['title'][:60]}...")
                print(f"    Confidence: {insight.confidence:.1%}" if insight.confidence else "    Confidence: Not set")
                print()
            
            print("💡 To view details of a specific insight, run:")
            print("   python view_insight_details.py <insight_id>")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db_manager.close()

async def main():
    """Main function."""
    insight_id = sys.argv[1] if len(sys.argv) > 1 else None
    await view_insight_details(insight_id)

if __name__ == "__main__":
    asyncio.run(main()) 