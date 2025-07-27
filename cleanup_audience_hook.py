#!/usr/bin/env python3
"""
Clean up Key Finding insights that contain audience_hook field.
"""

import asyncio
import sys
import ast
sys.path.insert(0, "src")

from src.database.connection import db_manager
from src.database.insight_repository import InsightRepository
from src.models.enums import InsightType as InsightTypeEnum

async def cleanup_audience_hook():
    """Delete Key Finding insights that contain audience_hook field."""
    await db_manager.initialize()
    
    try:
        insight_repo = InsightRepository()
        
        # Get all Key Finding insights
        all_insights = await insight_repo.list_all()
        key_findings = [i for i in all_insights if i.insight_type == InsightTypeEnum.KEY_FINDING]
        
        print(f"Found {len(key_findings)} Key Finding insights")
        
        deleted_count = 0
        for insight in key_findings:
            try:
                # Parse the content - handle both string and dict formats
                if isinstance(insight.content, str):
                    content = ast.literal_eval(insight.content)
                else:
                    content = insight.content
                
                # Check if audience_hook exists in the content
                if 'audience_hook' in content:
                    print(f"Deleting Key Finding with audience_hook for paper: {insight.paper_id}")
                    print(f"  Content keys: {list(content.keys())}")
                    
                    await insight_repo.delete(insight.id)
                    deleted_count += 1
                    
            except Exception as e:
                print(f"Error processing insight {insight.id}: {e}")
                # Try to check if it's a string that contains audience_hook
                if isinstance(insight.content, str) and 'audience_hook' in insight.content:
                    print(f"  Found audience_hook in string content, deleting...")
                    await insight_repo.delete(insight.id)
                    deleted_count += 1
        
        print(f"\nDeleted {deleted_count} Key Finding insights with audience_hook")
        
        # Show remaining Key Findings
        remaining_insights = await insight_repo.list_all()
        remaining_key_findings = [i for i in remaining_insights if i.insight_type == InsightTypeEnum.KEY_FINDING]
        
        print(f"\nRemaining Key Finding insights: {len(remaining_key_findings)}")
        for insight in remaining_key_findings:
            try:
                content = ast.literal_eval(insight.content)
                print(f"  Paper {insight.paper_id}: {list(content.keys())}")
            except:
                print(f"  Paper {insight.paper_id}: [error parsing content]")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(cleanup_audience_hook()) 