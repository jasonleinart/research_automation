#!/usr/bin/env python3
"""
Script to view insights organized by paper.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.database.connection import db_manager
from src.database.insight_repository import InsightRepository
from src.database.paper_repository import PaperRepository
from src.models.enums import InsightType

async def view_paper_insights(paper_title_fragment: str = None):
    """View insights organized by paper."""
    try:
        await db_manager.initialize()
        
        insight_repo = InsightRepository()
        paper_repo = PaperRepository()
        
        # Get all insights with paper information
        insights_with_papers = await insight_repo.get_insights_with_papers()
        
        # Group insights by paper
        papers_with_insights = {}
        for item in insights_with_papers:
            insight = item["insight"]
            paper = item["paper"]
            
            # Use paper title as key since we don't have paper ID in the joined data
            paper_title = paper["title"]
            if paper_title not in papers_with_insights:
                papers_with_insights[paper_title] = {
                    "paper": paper,
                    "insights": []
                }
            papers_with_insights[paper_title]["insights"].append(insight)
        
        # Display insights by paper
        for paper_title, data in papers_with_insights.items():
            paper = data["paper"]
            insights = data["insights"]
            
            # Filter by title if specified
            if paper_title_fragment and paper_title_fragment.lower() not in paper["title"].lower():
                continue
            
            print(f"📄 Paper: {paper['title']}")
            print(f"   ArXiv ID: {paper.get('arxiv_id', 'N/A')}")
            print(f"   Type: {paper.get('paper_type', 'Not classified')}")
            print(f"   Authors: {paper.get('authors', 'N/A')}")
            print()
            
            # Group insights by type
            insights_by_type = {}
            for insight in insights:
                insight_type = insight.insight_type.value
                if insight_type not in insights_by_type:
                    insights_by_type[insight_type] = []
                insights_by_type[insight_type].append(insight)
            
            # Display insights by type
            for insight_type, type_insights in insights_by_type.items():
                print(f"   🔍 {insight_type.replace('_', ' ').title()} ({len(type_insights)}):")
                
                for i, insight in enumerate(type_insights, 1):
                    confidence_str = f" ({insight.confidence:.1%})" if insight.confidence else ""
                    print(f"     {i}. {insight.title}{confidence_str}")
                    
                    # Show key content for different insight types
                    if insight.content:
                        if insight_type == "key_finding":
                            significance = insight.content.get("significance", "")
                            if significance:
                                print(f"        Significance: {significance[:150]}...")
                        elif insight_type == "framework":
                            name = insight.content.get("name", "")
                            core_concept = insight.content.get("core_concept", "")
                            if name:
                                print(f"        Name: {name}")
                            if core_concept:
                                print(f"        Core Concept: {core_concept[:150]}...")
                        elif insight_type == "data_point":
                            metrics = insight.content.get("metrics", [])
                            if metrics:
                                print(f"        Metrics: {len(metrics)} data points")
                                for metric in metrics[:2]:  # Show first 2 metrics
                                    if isinstance(metric, dict):
                                        name = metric.get("name", "Unknown")
                                        value = metric.get("value", "N/A")
                                        print(f"          - {name}: {value}")
                        elif insight_type == "methodology":
                            steps = insight.content.get("steps", [])
                            if steps:
                                print(f"        Steps: {len(steps)} steps")
                                for step in steps[:2]:  # Show first 2 steps
                                    if isinstance(step, dict):
                                        step_name = step.get("name", "Unknown step")
                                        print(f"          - {step_name}")
                    
                    print()
            
            print("-" * 80)
            print()
        
        # Show summary statistics
        total_papers = len(papers_with_insights)
        total_insights = sum(len(data["insights"]) for data in papers_with_insights.values())
        
        print(f"📊 Summary:")
        print(f"   Total papers with insights: {total_papers}")
        print(f"   Total insights: {total_insights}")
        print(f"   Average insights per paper: {total_insights/total_papers:.1f}")
        
        # Show insight type distribution
        all_insights = [insight for data in papers_with_insights.values() for insight in data["insights"]]
        type_counts = {}
        for insight in all_insights:
            insight_type = insight.insight_type.value
            type_counts[insight_type] = type_counts.get(insight_type, 0) + 1
        
        print(f"   Insight types:")
        for insight_type, count in sorted(type_counts.items()):
            print(f"     - {insight_type.replace('_', ' ').title()}: {count}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db_manager.close()

async def main():
    """Main function."""
    paper_title_fragment = sys.argv[1] if len(sys.argv) > 1 else None
    await view_paper_insights(paper_title_fragment)

if __name__ == "__main__":
    asyncio.run(main()) 