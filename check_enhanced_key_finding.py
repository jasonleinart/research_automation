#!/usr/bin/env python3
"""
Check the detailed content of the enhanced Key Finding.
"""

import asyncio
import sys
import ast
sys.path.insert(0, "src")

from src.database.connection import db_manager
from src.database.insight_repository import InsightRepository
from src.models.enums import InsightType as InsightTypeEnum

async def check_enhanced_key_finding():
    """Check the detailed content of the enhanced Key Finding."""
    await db_manager.initialize()
    
    try:
        # Get the Group Recommender paper ID
        paper_id = '43bfc09d-d3d0-4f97-aa96-53006aa1f4a8'
        
        insight_repo = InsightRepository()
        insights = await insight_repo.get_by_paper_id(paper_id)
        
        # Find the enhanced Key Finding
        enhanced_key_finding = None
        for insight in insights:
            if (insight.insight_type == InsightTypeEnum.KEY_FINDING and 
                insight.extraction_method == "enhanced_multi_step_chain_of_thought"):
                enhanced_key_finding = insight
                break
        
        if not enhanced_key_finding:
            print("❌ Enhanced Key Finding not found")
            return
        
        print("=" * 80)
        print("🔍 ENHANCED KEY FINDING DETAILED CONTENT")
        print("=" * 80)
        
        print(f"\n📋 Insight Details:")
        print(f"   ID: {enhanced_key_finding.id}")
        print(f"   Method: {enhanced_key_finding.extraction_method}")
        print(f"   Confidence: {enhanced_key_finding.confidence:.1%}")
        
        # Parse and display content
        try:
            content = ast.literal_eval(enhanced_key_finding.content) if isinstance(enhanced_key_finding.content, str) else enhanced_key_finding.content
            
            print(f"\n📄 FULL CONTENT:")
            for key, value in content.items():
                print(f"\n🔸 {key.upper()}:")
                print(f"   {value}")
                
                # Check for CHARM framework
                if 'charm' in str(value).lower():
                    print(f"   ✅ CHARM FRAMEWORK MENTIONED!")
                else:
                    print(f"   ❌ CHARM FRAMEWORK NOT MENTIONED")
                    
        except Exception as e:
            print(f"❌ Error parsing content: {e}")
            print(f"Raw content: {enhanced_key_finding.content}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_enhanced_key_finding()) 