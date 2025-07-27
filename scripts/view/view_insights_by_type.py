#!/usr/bin/env python3
"""
Script to view insights organized by type across all papers.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.database.insight_repository import InsightRepository
from src.models.enums import InsightType

async def view_insights_by_type(insight_type: str = None):
    """View insights organized by type."""
    try:
        await db_manager.initialize()
        
        repo = InsightRepository()
        
        # Get all insight types
        insight_types = [e.value for e in InsightType]
        
        # Filter by specified type if provided
        if insight_type:
            insight_type = insight_type.lower().replace(' ', '_')
            if insight_type not in insight_types:
                print(f"❌ Invalid insight type: {insight_type}")
                print(f"   Available types: {', '.join(insight_types)}")
                return
            insight_types = [insight_type]
        
        for insight_type_name in insight_types:
            print(f"🔍 {insight_type_name.replace('_', ' ').title()} Insights:")
            print("=" * 60)
            
            # Get insights of this type
            insights = await repo.get_by_insight_type(InsightType(insight_type_name))
            
            if not insights:
                print("   No insights found.")
                print()
                continue
            
            # Group by paper
            insights_by_paper = {}
            for insight in insights:
                # Get paper info for this insight
                paper_info = await get_paper_info(insight.paper_id)
                paper_title = paper_info.get("title", "Unknown Paper")
                
                if paper_title not in insights_by_paper:
                    insights_by_paper[paper_title] = []
                insights_by_paper[paper_title].append(insight)
            
            # Display insights by paper
            for paper_title, paper_insights in insights_by_paper.items():
                print(f"   📄 {paper_title}")
                
                for i, insight in enumerate(paper_insights, 1):
                    confidence_str = f" ({insight.confidence:.1%})" if insight.confidence else ""
                    print(f"     {i}. {insight.title}{confidence_str}")
                    
                    # Show key content based on insight type
                    if insight.content:
                        if insight_type_name == "key_finding":
                            significance = insight.content.get("significance", "")
                            if significance:
                                print(f"        Significance: {significance[:200]}...")
                        elif insight_type_name == "framework":
                            name = insight.content.get("name", "")
                            core_concept = insight.content.get("core_concept", "")
                            if name:
                                print(f"        Name: {name}")
                            if core_concept:
                                print(f"        Core Concept: {core_concept[:200]}...")
                        elif insight_type_name == "data_point":
                            metrics = insight.content.get("metrics", [])
                            if metrics:
                                print(f"        Metrics: {len(metrics)} data points")
                                for metric in metrics[:3]:  # Show first 3 metrics
                                    if isinstance(metric, dict):
                                        name = metric.get("name", "Unknown")
                                        value = metric.get("value", "N/A")
                                        print(f"          - {name}: {value}")
                        elif insight_type_name == "methodology":
                            steps = insight.content.get("steps", [])
                            if steps:
                                print(f"        Steps: {len(steps)} steps")
                                for step in steps[:3]:  # Show first 3 steps
                                    if isinstance(step, dict):
                                        step_name = step.get("name", "Unknown step")
                                        print(f"          - {step_name}")
                    
                    print()
                
                print()
            
            print("-" * 80)
            print()
        
        # Show overall statistics
        stats = await repo.get_statistics()
        if stats:
            print(f"📊 Overall Statistics:")
            print(f"   Total insights: {stats.get('total_insights', 0)}")
            print(f"   Average confidence: {stats.get('avg_confidence', 0):.1%}")
            print(f"   Papers with insights: {stats.get('papers_with_insights', 0)}")
            print(f"   Unique insight types: {stats.get('unique_types', 0)}")
            
            type_dist = stats.get('type_distribution', {})
            if type_dist:
                print(f"   Type distribution:")
                for insight_type, count in sorted(type_dist.items()):
                    print(f"     - {insight_type.replace('_', ' ').title()}: {count}")
            
            confidence_dist = stats.get('confidence_distribution', {})
            if confidence_dist:
                print(f"   Confidence distribution:")
                print(f"     - High (≥80%): {confidence_dist.get('high', 0)}")
                print(f"     - Medium (60-80%): {confidence_dist.get('medium', 0)}")
                print(f"     - Low (<60%): {confidence_dist.get('low', 0)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db_manager.close()

async def get_paper_info(paper_id):
    """Get basic paper information."""
    try:
        from src.database.paper_repository import PaperRepository
        repo = PaperRepository()
        paper = await repo.get_by_id(paper_id)
        if paper:
            return {
                "title": paper.title,
                "arxiv_id": paper.arxiv_id,
                "paper_type": paper.paper_type.value if paper.paper_type else None
            }
    except:
        pass
    return {"title": "Unknown Paper"}

async def main():
    """Main function."""
    insight_type = sys.argv[1] if len(sys.argv) > 1 else None
    await view_insights_by_type(insight_type)

if __name__ == "__main__":
    asyncio.run(main()) 