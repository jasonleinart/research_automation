#!/usr/bin/env python3
"""
Show the actual raw content of the enhanced Key Finding.
"""

import asyncio
import sys
import ast
sys.path.insert(0, "src")

from src.database.connection import db_manager
from src.database.insight_repository import InsightRepository
from src.models.enums import InsightType as InsightTypeEnum

async def show_actual_results():
    """Show the actual raw content of the enhanced Key Finding."""
    await db_manager.initialize()
    
    try:
        # Get the Group Recommender paper ID
        paper_id = '43bfc09d-d3d0-4f97-aa96-53006aa1f4a8'
        
        insight_repo = InsightRepository()
        insights = await insight_repo.get_by_paper_id(paper_id)
        
        # Find the enhanced Key Finding (most recent one)
        key_findings = [i for i in insights if i.insight_type == InsightTypeEnum.KEY_FINDING]
        if len(key_findings) >= 2:
            enhanced_key_finding = key_findings[-1]  # Most recent
            original_key_finding = key_findings[-2]  # Second most recent
            
            print("=" * 80)
            print("ACTUAL ENHANCED KEY FINDING CONTENT:")
            print("=" * 80)
            
            # Parse the content
            try:
                content = ast.literal_eval(enhanced_key_finding.content)
                for key, value in content.items():
                    print(f"\n{key.upper()}:")
                    print(f"{value}")
                    print("-" * 40)
            except:
                print("RAW CONTENT:")
                print(enhanced_key_finding.content)
            
            print("\n" + "=" * 80)
            print("ACTUAL ORIGINAL KEY FINDING CONTENT:")
            print("=" * 80)
            
            try:
                content = ast.literal_eval(original_key_finding.content)
                for key, value in content.items():
                    print(f"\n{key.upper()}:")
                    print(f"{value}")
                    print("-" * 40)
            except:
                print("RAW CONTENT:")
                print(original_key_finding.content)
                
        else:
            print("Not enough Key Finding insights found")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(show_actual_results()) 