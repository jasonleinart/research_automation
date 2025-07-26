#!/usr/bin/env python3
"""
Script to clean up old insights that were created before the Chain-of-Thought approach.
This will remove all insights that don't use the 'chain_of_thought' extraction method.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Optional
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.connection import db_manager
from src.database.insight_repository import InsightRepository
from src.database.paper_repository import PaperRepository
from src.models.insight import Insight
from src.models.enums import InsightType

class InsightCleanupService:
    """Service to clean up old insights before CoT implementation."""
    
    def __init__(self):
        self.insight_repo = InsightRepository()
        self.paper_repo = PaperRepository()
    
    async def analyze_insights(self) -> Dict[str, any]:
        """Analyze which insights need to be removed."""
        print("🔍 Analyzing insights...")
        
        # Get all insights
        all_insights = await self.insight_repo.list_all()
        
        # Group by extraction method
        by_method = {}
        for insight in all_insights:
            method = insight.extraction_method or "unknown"
            if method not in by_method:
                by_method[method] = []
            by_method[method].append(insight)
        
        # Group by paper
        by_paper = {}
        for insight in all_insights:
            paper_id = str(insight.paper_id)
            if paper_id not in by_paper:
                by_paper[paper_id] = []
            by_paper[paper_id].append(insight)
        
        # Count by insight type
        by_type = {}
        for insight in all_insights:
            insight_type = insight.insight_type.value
            if insight_type not in by_type:
                by_type[insight_type] = []
            by_type[insight_type].append(insight)
        
        # Find non-CoT insights
        non_cot_insights = []
        for insight in all_insights:
            if insight.extraction_method != 'chain_of_thought':
                non_cot_insights.append(insight)
        
        return {
            'total_insights': len(all_insights),
            'by_method': {method: len(insights) for method, insights in by_method.items()},
            'by_paper': {paper_id: len(insights) for paper_id, insights in by_paper.items()},
            'by_type': {insight_type: len(insights) for insight_type, insights in by_type.items()},
            'non_cot_insights': non_cot_insights,
            'non_cot_count': len(non_cot_insights)
        }
    
    async def cleanup_old_insights(self, dry_run: bool = True) -> Dict[str, any]:
        """Clean up old insights that don't use CoT extraction."""
        print(f"🧹 Cleaning up old insights (dry_run: {dry_run})...")
        
        # Analyze current state
        analysis = await self.analyze_insights()
        
        print(f"\n📊 Current Insight Analysis:")
        print(f"   Total insights: {analysis['total_insights']}")
        print(f"   By extraction method: {analysis['by_method']}")
        print(f"   Non-CoT insights to remove: {analysis['non_cot_count']}")
        
        if dry_run:
            print(f"\n🔍 DRY RUN - No changes will be made")
            return {'removed': [], 'errors': []}
        
        # Perform cleanup
        removed_insights = []
        errors = []
        
        try:
            for insight in analysis['non_cot_insights']:
                try:
                    success = await self.insight_repo.delete(insight.id)
                    if success:
                        removed_insights.append(f"{insight.id} ({insight.insight_type.value})")
                        print(f"   ✅ Removed insight: {insight.id} ({insight.insight_type.value})")
                    else:
                        errors.append(f"Failed to remove insight: {insight.id}")
                        print(f"   ❌ Failed to remove insight: {insight.id}")
                except Exception as e:
                    errors.append(f"Error removing insight {insight.id}: {str(e)}")
                    print(f"   ❌ Error removing insight {insight.id}: {e}")
        
        except Exception as e:
            errors.append(str(e))
            print(f"❌ Error during cleanup: {e}")
        
        return {'removed': removed_insights, 'errors': errors}
    
    async def show_remaining_insights(self):
        """Show statistics about remaining insights after cleanup."""
        print("\n📈 Remaining Insight Statistics:")
        
        # Get all insights
        all_insights = await self.insight_repo.list_all()
        
        # Group by extraction method
        by_method = {}
        for insight in all_insights:
            method = insight.extraction_method or "unknown"
            if method not in by_method:
                by_method[method] = []
            by_method[method].append(insight)
        
        # Group by paper
        by_paper = {}
        for insight in all_insights:
            paper_id = str(insight.paper_id)
            if paper_id not in by_paper:
                by_paper[paper_id] = []
            by_paper[paper_id].append(insight)
            
        # Get paper titles
        paper_titles = {}
        for paper_id in by_paper:
            paper = await self.paper_repo.get_by_id(paper_id)
            if paper:
                paper_titles[paper_id] = paper.title
        
        print(f"   Total insights: {len(all_insights)}")
        print(f"   By extraction method: {', '.join([f'{method}: {len(insights)}' for method, insights in by_method.items()])}")
        print(f"   By paper:")
        for paper_id, insights in by_paper.items():
            title = paper_titles.get(paper_id, "Unknown")
            print(f"     - {title[:50]}... ({len(insights)} insights)")

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Old Insight Cleanup Tool")
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--cleanup', action='store_true', help='Perform the actual cleanup')
    parser.add_argument('--stats', action='store_true', help='Show insight statistics')
    
    args = parser.parse_args()
    
    if not any([args.dry_run, args.cleanup, args.stats]):
        print("Please specify an action: --dry-run, --cleanup, or --stats")
        return
    
    try:
        await db_manager.initialize()
        
        service = InsightCleanupService()
        
        if args.dry_run:
            await service.cleanup_old_insights(dry_run=True)
        
        elif args.cleanup:
            print("⚠️  WARNING: This will permanently delete all non-CoT insights!")
            response = input("Are you sure you want to proceed? (y/N): ")
            if response.lower() == 'y':
                changes = await service.cleanup_old_insights(dry_run=False)
                print(f"\n✅ Cleanup completed:")
                print(f"   Insights removed: {len(changes['removed'])}")
                if changes['errors']:
                    print(f"   Errors: {len(changes['errors'])}")
                
                await service.show_remaining_insights()
            else:
                print("Cleanup cancelled.")
        
        elif args.stats:
            await service.show_remaining_insights()
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 