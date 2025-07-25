#!/usr/bin/env python3
"""
Debug tag creation by checking insights and their content.
"""

import asyncio
from src.database.connection import db_manager
from src.database.insight_repository import InsightRepository

async def main():
    await db_manager.initialize()
    
    repo = InsightRepository()
    insights_with_papers = await repo.get_insights_with_papers()
    
    print("🔍 Debugging Tag Creation\n")
    
    for item in insights_with_papers:
        insight = item["insight"]
        paper = item["paper"]
        
        print(f"📄 Paper: {paper['title'][:50]}...")
        print(f"   Insight Type: {insight.insight_type.value}")
        print(f"   Content Keys: {list(insight.content.keys()) if insight.content else 'None'}")
        
        # Check specific content that should generate tags
        if insight.insight_type.value == "key_finding":
            main_contrib = insight.content.get("main_contribution", "") if insight.content else ""
            print(f"   Main Contribution: {main_contrib[:100]}...")
        elif insight.insight_type.value == "framework":
            name = insight.content.get("name", "") if insight.content else ""
            components = insight.content.get("components", []) if insight.content else []
            print(f"   Framework Name: {name}")
            print(f"   Components: {components}")
        elif insight.insight_type.value == "concept":
            domain = insight.content.get("research_domain", "") if insight.content else ""
            concepts = insight.content.get("key_concepts", []) if insight.content else []
            print(f"   Research Domain: {domain}")
            print(f"   Key Concepts: {len(concepts)} items")
        
        print()

if __name__ == "__main__":
    asyncio.run(main())