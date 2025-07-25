#!/usr/bin/env python3
"""
Simple tool to list extracted insights.
"""

import asyncio
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.database.connection import db_manager
from src.database.insight_repository import InsightRepository
from src.database.paper_repository import PaperRepository

console = Console()


async def list_all_insights():
    """List all insights in a simple table format."""
    await db_manager.initialize()
    
    insight_repo = InsightRepository()
    paper_repo = PaperRepository()
    
    # Get insights with paper info
    insights_with_papers = await insight_repo.get_insights_with_papers()
    
    if not insights_with_papers:
        console.print("❌ No insights found.")
        return
    
    console.print(f"📚 [bold blue]Found {len(insights_with_papers)} insights[/bold blue]\n")
    
    # Create table
    table = Table()
    table.add_column("Paper", style="cyan", width=30)
    table.add_column("Type", style="green", width=12)
    table.add_column("Title", style="yellow", width=40)
    table.add_column("Confidence", justify="right", style="magenta", width=10)
    table.add_column("Content Preview", width=50)
    
    for item in insights_with_papers:
        insight = item["insight"]
        paper_info = item["paper"]
        
        # Truncate paper title
        paper_title = paper_info["title"][:27] + "..." if len(paper_info["title"]) > 30 else paper_info["title"]
        
        # Get content preview
        content_preview = ""
        if insight.content:
            # Extract key information from content
            key_items = []
            for key, value in insight.content.items():
                if isinstance(value, str) and len(value) > 5:
                    key_items.append(f"{key}: {value[:30]}...")
                elif isinstance(value, list) and value:
                    if isinstance(value[0], str):
                        key_items.append(f"{key}: {', '.join(value[:2])}")
                    elif isinstance(value[0], dict):
                        key_items.append(f"{key}: {len(value)} items")
                if len(key_items) >= 2:
                    break
            content_preview = "; ".join(key_items)
        
        # Confidence color
        conf_color = "green" if insight.confidence >= 0.8 else "yellow" if insight.confidence >= 0.6 else "red"
        confidence_str = f"[{conf_color}]{insight.confidence:.1%}[/{conf_color}]"
        
        table.add_row(
            paper_title,
            insight.insight_type.value,
            insight.title[:37] + "..." if len(insight.title) > 40 else insight.title,
            confidence_str,
            content_preview[:47] + "..." if len(content_preview) > 50 else content_preview
        )
    
    console.print(table)


async def show_insight_details(insight_id: str):
    """Show detailed information about a specific insight."""
    await db_manager.initialize()
    
    insight_repo = InsightRepository()
    paper_repo = PaperRepository()
    
    try:
        from uuid import UUID
        insight_uuid = UUID(insight_id)
        insight = await insight_repo.get_by_id(insight_uuid)
        
        if not insight:
            console.print(f"❌ Insight not found: {insight_id}")
            return
        
        paper = await paper_repo.get_by_id(insight.paper_id)
        
        # Display insight details
        console.print(f"🔍 [bold blue]Insight Details[/bold blue]\n")
        
        console.print(Panel(
            f"[bold]{insight.title}[/bold]\n"
            f"Type: {insight.insight_type.value}\n"
            f"Confidence: {insight.confidence:.1%}\n"
            f"Method: {insight.extraction_method}\n"
            f"Created: {insight.created_at}",
            title="Insight Information",
            border_style="blue"
        ))
        
        if paper:
            console.print(Panel(
                f"[bold]{paper.title}[/bold]\n"
                f"Type: {paper.paper_type.value if paper.paper_type else 'Unknown'}\n"
                f"ArXiv ID: {paper.arxiv_id or 'N/A'}",
                title="Source Paper",
                border_style="green"
            ))
        
        if insight.description:
            console.print(f"\n📝 [bold]Description:[/bold]\n{insight.description}")
        
        if insight.content:
            console.print(f"\n📋 [bold]Content:[/bold]")
            from rich.syntax import Syntax
            json_content = json.dumps(insight.content, indent=2)
            syntax = Syntax(json_content, "json", theme="monokai", line_numbers=True)
            console.print(syntax)
        
    except ValueError:
        console.print(f"❌ Invalid insight ID format: {insight_id}")
    except Exception as e:
        console.print(f"❌ Error: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="List extracted insights")
    parser.add_argument("--all", action="store_true", help="List all insights")
    parser.add_argument("--detail", help="Show detailed information for specific insight ID")
    
    args = parser.parse_args()
    
    if args.all:
        asyncio.run(list_all_insights())
    elif args.detail:
        asyncio.run(show_insight_details(args.detail))
    else:
        parser.print_help()