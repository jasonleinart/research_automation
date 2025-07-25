#!/usr/bin/env python3
"""
Review and evaluate extracted insights from papers.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.database.insight_repository import InsightRepository
from src.models.paper import Paper
from src.models.insight import Insight
from src.models.enums import InsightType, PaperType
from src.services.insight_extraction_service import InsightExtractionService

console = Console()
logging.basicConfig(level=logging.WARNING)  # Reduce noise


class InsightReviewer:
    """Tool for reviewing and evaluating extracted insights."""
    
    def __init__(self):
        self.paper_repo = PaperRepository()
        self.insight_repo = InsightRepository()
        self.extraction_service = InsightExtractionService()
    
    async def review_all_insights(self):
        """Review all extracted insights with detailed analysis."""
        console.print("🔍 [bold blue]Reviewing All Extracted Insights[/bold blue]\n")
        
        # Get all papers with insights
        papers_with_insights = await self._get_papers_with_insights()
        
        if not papers_with_insights:
            console.print("❌ No papers with extracted insights found.")
            return
        
        console.print(f"📚 Found {len(papers_with_insights)} papers with insights\n")
        
        for i, paper in enumerate(papers_with_insights, 1):
            await self._review_paper_insights(paper, i, len(papers_with_insights))
            
            if i < len(papers_with_insights):
                if not Confirm.ask("\n➡️  Continue to next paper?", default=True):
                    break
    
    async def review_paper_insights(self, paper_id: str):
        """Review insights for a specific paper."""
        try:
            paper_uuid = UUID(paper_id)
            paper = await self.paper_repo.get_by_id(paper_uuid)
            
            if not paper:
                console.print(f"❌ Paper not found: {paper_id}")
                return
            
            await self._review_paper_insights(paper, 1, 1)
            
        except ValueError:
            console.print(f"❌ Invalid paper ID format: {paper_id}")
    
    async def compare_insights_to_source(self, paper_id: str):
        """Compare extracted insights to source paper content."""
        try:
            paper_uuid = UUID(paper_id)
            paper = await self.paper_repo.get_by_id(paper_uuid)
            
            if not paper:
                console.print(f"❌ Paper not found: {paper_id}")
                return
            
            insights = await self.insight_repo.get_by_paper_id(paper_uuid)
            
            if not insights:
                console.print(f"❌ No insights found for paper: {paper.title}")
                return
            
            await self._compare_insights_to_source(paper, insights)
            
        except ValueError:
            console.print(f"❌ Invalid paper ID format: {paper_id}")
    
    async def evaluate_extraction_quality(self):
        """Evaluate overall extraction quality with metrics."""
        console.print("📊 [bold blue]Extraction Quality Evaluation[/bold blue]\n")
        
        # Get all papers and insights
        papers_with_insights = await self._get_papers_with_insights()
        all_insights = []
        
        for paper in papers_with_insights:
            insights = await self.insight_repo.get_by_paper_id(paper.id)
            all_insights.extend(insights)
        
        if not all_insights:
            console.print("❌ No insights found for evaluation.")
            return
        
        # Calculate quality metrics
        metrics = await self._calculate_quality_metrics(papers_with_insights, all_insights)
        
        # Display metrics
        await self._display_quality_metrics(metrics)
    
    async def _get_papers_with_insights(self) -> List[Paper]:
        """Get all papers that have extracted insights."""
        # Get all papers
        all_papers = await self.paper_repo.list_all()
        papers_with_insights = []
        
        for paper in all_papers:
            insights = await self.insight_repo.get_by_paper_id(paper.id)
            if insights:
                papers_with_insights.append(paper)
        
        return papers_with_insights
    
    async def _review_paper_insights(self, paper: Paper, current: int, total: int):
        """Review insights for a single paper."""
        # Header
        console.print(f"📄 [bold cyan]Paper {current}/{total}[/bold cyan]")
        console.print(Panel(
            f"[bold]{paper.title}[/bold]\n"
            f"Type: {paper.paper_type.value if paper.paper_type else 'Unknown'}\n"
            f"Authors: {', '.join([author.name for author in paper.authors]) if paper.authors else 'Unknown'}\n"
            f"ArXiv ID: {paper.arxiv_id or 'N/A'}",
            title="Paper Information",
            border_style="cyan"
        ))
        
        # Get insights
        insights = await self.insight_repo.get_by_paper_id(paper.id)
        
        if not insights:
            console.print("❌ No insights found for this paper.\n")
            return
        
        console.print(f"🔍 Found {len(insights)} extracted insights:\n")
        
        # Review each insight
        for i, insight in enumerate(insights, 1):
            await self._review_single_insight(insight, i, paper)
        
        # Summary
        avg_confidence = sum(insight.confidence for insight in insights) / len(insights)
        console.print(f"\n📊 [bold]Summary:[/bold]")
        console.print(f"   • Total insights: {len(insights)}")
        console.print(f"   • Average confidence: {avg_confidence:.1%}")
        console.print(f"   • Insight types: {', '.join(set(i.insight_type.value for i in insights))}")
    
    async def _review_single_insight(self, insight: Insight, index: int, paper: Paper):
        """Review a single insight in detail."""
        # Insight header
        confidence_color = "green" if insight.confidence >= 0.8 else "yellow" if insight.confidence >= 0.6 else "red"
        
        console.print(f"🔸 [bold]Insight {index}: {insight.title}[/bold]")
        console.print(f"   Type: {insight.insight_type.value}")
        console.print(f"   Confidence: [{confidence_color}]{insight.confidence:.1%}[/{confidence_color}]")
        console.print(f"   Method: {insight.extraction_method}")
        
        if insight.description:
            console.print(f"   Description: {insight.description}")
        
        # Show content in a formatted way
        if insight.content:
            console.print("\n   📋 [bold]Extracted Content:[/bold]")
            formatted_content = self._format_insight_content(insight.content)
            console.print(Panel(formatted_content, border_style="blue", padding=(0, 1)))
        
        # Interactive review option
        if Confirm.ask("   🔍 Review this insight in detail?", default=False):
            await self._detailed_insight_review(insight, paper)
        
        console.print()  # Add spacing
    
    def _format_insight_content(self, content: Dict[str, Any]) -> str:
        """Format insight content for display."""
        formatted_lines = []
        
        for key, value in content.items():
            if isinstance(value, list):
                if value and isinstance(value[0], dict):
                    # List of objects
                    formatted_lines.append(f"[bold cyan]{key}:[/bold cyan]")
                    for i, item in enumerate(value[:3], 1):  # Show first 3 items
                        if isinstance(item, dict):
                            item_str = ", ".join(f"{k}: {v}" for k, v in item.items())
                            formatted_lines.append(f"   {i}. {item_str}")
                        else:
                            formatted_lines.append(f"   {i}. {item}")
                    if len(value) > 3:
                        formatted_lines.append(f"   ... and {len(value) - 3} more items")
                else:
                    # List of strings
                    formatted_lines.append(f"[bold cyan]{key}:[/bold cyan] {', '.join(str(v) for v in value[:5])}")
                    if len(value) > 5:
                        formatted_lines.append(f"   ... and {len(value) - 5} more items")
            else:
                # Simple value
                formatted_lines.append(f"[bold cyan]{key}:[/bold cyan] {value}")
        
        return "\n".join(formatted_lines)
    
    async def _detailed_insight_review(self, insight: Insight, paper: Paper):
        """Provide detailed review of a single insight."""
        console.print(f"\n🔍 [bold]Detailed Review: {insight.title}[/bold]")
        
        # Show full JSON content
        console.print("\n📋 [bold]Full Content (JSON):[/bold]")
        json_content = json.dumps(insight.content, indent=2)
        syntax = Syntax(json_content, "json", theme="monokai", line_numbers=True)
        console.print(syntax)
        
        # Show relevant paper excerpts if available
        if paper.abstract:
            console.print(f"\n📄 [bold]Paper Abstract:[/bold]")
            console.print(Panel(paper.abstract[:500] + "..." if len(paper.abstract) > 500 else paper.abstract, 
                               border_style="green"))
        
        # Quality assessment prompts
        console.print(f"\n🎯 [bold]Quality Assessment:[/bold]")
        
        accuracy = Prompt.ask(
            "Rate accuracy (1-5, where 5 is highly accurate)",
            choices=["1", "2", "3", "4", "5"],
            default="3"
        )
        
        completeness = Prompt.ask(
            "Rate completeness (1-5, where 5 is very complete)",
            choices=["1", "2", "3", "4", "5"],
            default="3"
        )
        
        relevance = Prompt.ask(
            "Rate relevance (1-5, where 5 is highly relevant)",
            choices=["1", "2", "3", "4", "5"],
            default="3"
        )
        
        # Store feedback (could be saved to database in future)
        feedback = {
            "insight_id": str(insight.id),
            "accuracy": int(accuracy),
            "completeness": int(completeness),
            "relevance": int(relevance),
            "overall": (int(accuracy) + int(completeness) + int(relevance)) / 3
        }
        
        console.print(f"✅ Feedback recorded: Overall score {feedback['overall']:.1f}/5")
    
    async def _compare_insights_to_source(self, paper: Paper, insights: List[Insight]):
        """Compare extracted insights to source paper content."""
        console.print(f"🔍 [bold]Comparing Insights to Source: {paper.title}[/bold]\n")
        
        # Show paper content sections
        console.print("📄 [bold]Source Paper Content:[/bold]")
        
        if paper.abstract:
            console.print(Panel(
                paper.abstract,
                title="Abstract",
                border_style="green"
            ))
        
        if paper.full_text:
            # Show first 1000 characters of full text
            preview = paper.full_text[:1000] + "..." if len(paper.full_text) > 1000 else paper.full_text
            console.print(Panel(
                preview,
                title="Content Preview",
                border_style="blue"
            ))
        
        console.print(f"\n🔍 [bold]Extracted Insights ({len(insights)}):[/bold]\n")
        
        # Show each insight with comparison
        for i, insight in enumerate(insights, 1):
            console.print(f"🔸 [bold]Insight {i}: {insight.title}[/bold]")
            console.print(f"   Confidence: {insight.confidence:.1%}")
            
            # Show key extracted points
            if insight.content:
                key_points = self._extract_key_points(insight.content)
                if key_points:
                    console.print("   Key Points:")
                    for point in key_points[:3]:
                        console.print(f"   • {point}")
            
            # Ask for validation
            if Confirm.ask(f"   ✅ Does this insight accurately reflect the paper content?", default=True):
                console.print("   ✅ [green]Validated as accurate[/green]")
            else:
                console.print("   ❌ [red]Marked as inaccurate[/red]")
                issue = Prompt.ask("   What's the issue? (missing/incorrect/irrelevant)", default="incorrect")
                console.print(f"   📝 Issue noted: {issue}")
            
            console.print()
    
    def _extract_key_points(self, content: Dict[str, Any]) -> List[str]:
        """Extract key points from insight content for comparison."""
        key_points = []
        
        # Extract meaningful strings from the content
        for key, value in content.items():
            if isinstance(value, str) and len(value) > 10:
                key_points.append(f"{key}: {value[:100]}...")
            elif isinstance(value, list) and value:
                if isinstance(value[0], str):
                    key_points.append(f"{key}: {', '.join(value[:2])}")
                elif isinstance(value[0], dict):
                    # Extract from first object
                    first_obj = value[0]
                    obj_summary = ", ".join(f"{k}: {v}" for k, v in list(first_obj.items())[:2])
                    key_points.append(f"{key}: {obj_summary}")
        
        return key_points
    
    async def _calculate_quality_metrics(self, papers: List[Paper], insights: List[Insight]) -> Dict[str, Any]:
        """Calculate quality metrics for extracted insights."""
        metrics = {
            "total_papers": len(papers),
            "total_insights": len(insights),
            "insights_per_paper": len(insights) / len(papers) if papers else 0,
            "confidence_distribution": {},
            "insight_type_distribution": {},
            "paper_type_coverage": {},
            "average_confidence": sum(i.confidence for i in insights) / len(insights) if insights else 0
        }
        
        # Confidence distribution
        confidence_ranges = {"high (80%+)": 0, "medium (60-80%)": 0, "low (<60%)": 0}
        for insight in insights:
            if insight.confidence >= 0.8:
                confidence_ranges["high (80%+)"] += 1
            elif insight.confidence >= 0.6:
                confidence_ranges["medium (60-80%)"] += 1
            else:
                confidence_ranges["low (<60%)"] += 1
        
        metrics["confidence_distribution"] = confidence_ranges
        
        # Insight type distribution
        type_counts = {}
        for insight in insights:
            type_name = insight.insight_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        metrics["insight_type_distribution"] = type_counts
        
        # Paper type coverage
        paper_type_insights = {}
        for paper in papers:
            paper_type = paper.paper_type.value if paper.paper_type else "unknown"
            paper_insights = [i for i in insights if i.paper_id == paper.id]
            paper_type_insights[paper_type] = {
                "papers": paper_type_insights.get(paper_type, {}).get("papers", 0) + 1,
                "insights": len(paper_insights),
                "avg_confidence": sum(i.confidence for i in paper_insights) / len(paper_insights) if paper_insights else 0
            }
        
        metrics["paper_type_coverage"] = paper_type_insights
        
        return metrics
    
    async def _display_quality_metrics(self, metrics: Dict[str, Any]):
        """Display quality metrics in a formatted way."""
        # Overview
        console.print(Panel(
            f"📊 Total Papers: {metrics['total_papers']}\n"
            f"🔍 Total Insights: {metrics['total_insights']}\n"
            f"📈 Insights per Paper: {metrics['insights_per_paper']:.1f}\n"
            f"🎯 Average Confidence: {metrics['average_confidence']:.1%}",
            title="Overview",
            border_style="cyan"
        ))
        
        # Confidence distribution
        console.print("\n📊 [bold]Confidence Distribution:[/bold]")
        conf_table = Table()
        conf_table.add_column("Confidence Range", style="cyan")
        conf_table.add_column("Count", justify="right")
        conf_table.add_column("Percentage", justify="right")
        
        total_insights = metrics['total_insights']
        for range_name, count in metrics['confidence_distribution'].items():
            percentage = (count / total_insights * 100) if total_insights > 0 else 0
            conf_table.add_row(range_name, str(count), f"{percentage:.1f}%")
        
        console.print(conf_table)
        
        # Insight type distribution
        console.print("\n🔍 [bold]Insight Type Distribution:[/bold]")
        type_table = Table()
        type_table.add_column("Insight Type", style="green")
        type_table.add_column("Count", justify="right")
        type_table.add_column("Percentage", justify="right")
        
        for insight_type, count in metrics['insight_type_distribution'].items():
            percentage = (count / total_insights * 100) if total_insights > 0 else 0
            type_table.add_row(insight_type, str(count), f"{percentage:.1f}%")
        
        console.print(type_table)
        
        # Paper type coverage
        console.print("\n📚 [bold]Paper Type Coverage:[/bold]")
        coverage_table = Table()
        coverage_table.add_column("Paper Type", style="magenta")
        coverage_table.add_column("Papers", justify="right")
        coverage_table.add_column("Insights", justify="right")
        coverage_table.add_column("Avg Confidence", justify="right")
        
        for paper_type, data in metrics['paper_type_coverage'].items():
            coverage_table.add_row(
                paper_type,
                str(data['papers']),
                str(data['insights']),
                f"{data['avg_confidence']:.1%}"
            )
        
        console.print(coverage_table)


async def main():
    """Main function to run the insight reviewer."""
    parser = argparse.ArgumentParser(description="Review and evaluate extracted insights")
    parser.add_argument("--all", action="store_true", help="Review all extracted insights")
    parser.add_argument("--paper-id", help="Review insights for specific paper ID")
    parser.add_argument("--compare", help="Compare insights to source for specific paper ID")
    parser.add_argument("--quality", action="store_true", help="Evaluate overall extraction quality")
    
    args = parser.parse_args()
    
    # Initialize database connection
    await db_manager.initialize()
    
    reviewer = InsightReviewer()
    
    try:
        if args.all:
            await reviewer.review_all_insights()
        elif args.paper_id:
            await reviewer.review_paper_insights(args.paper_id)
        elif args.compare:
            await reviewer.compare_insights_to_source(args.compare)
        elif args.quality:
            await reviewer.evaluate_extraction_quality()
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        console.print("\n👋 Review session ended.")
    except Exception as e:
        console.print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())