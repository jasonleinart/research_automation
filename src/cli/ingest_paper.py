"""
CLI interface for manual paper ingestion.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.connection import db_manager
from src.services.paper_ingestion import PaperIngestionService
from src.models.paper import Author

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PaperIngestionCLI:
    """CLI for paper ingestion operations."""
    
    def __init__(self):
        self.ingestion_service = PaperIngestionService()
    
    async def ingest_from_arxiv_url(self, url: str) -> bool:
        """Ingest paper from ArXiv URL."""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Fetching paper from ArXiv...", total=None)
                
                paper = await self.ingestion_service.ingest_from_arxiv_url(url)
                
                if paper:
                    progress.update(task, description="✓ Paper ingested successfully!")
                    self.display_paper_info(paper)
                    return True
                else:
                    progress.update(task, description="✗ Failed to ingest paper")
                    console.print("[red]Failed to ingest paper from ArXiv URL[/red]")
                    return False
                    
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return False
    
    async def ingest_from_pdf(self, pdf_path: str, title: Optional[str] = None, authors: Optional[str] = None) -> bool:
        """Ingest paper from PDF file."""
        try:
            # Prepare user metadata
            user_metadata = {}
            if title:
                user_metadata['title'] = title
            if authors:
                author_list = [Author(name=name.strip()) for name in authors.split(',')]
                user_metadata['authors'] = author_list
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Processing PDF...", total=None)
                
                paper = await self.ingestion_service.ingest_from_pdf(pdf_path, user_metadata)
                
                if paper:
                    progress.update(task, description="✓ Paper ingested successfully!")
                    self.display_paper_info(paper)
                    return True
                else:
                    progress.update(task, description="✗ Failed to process PDF")
                    console.print("[red]Failed to process PDF file[/red]")
                    return False
                    
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return False
    
    async def search_and_ingest_by_title(self, title: str) -> bool:
        """Search for papers by title and allow user to select one."""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Searching ArXiv...", total=None)
                
                papers = await self.ingestion_service.ingest_from_title(title)
                
                if not papers:
                    progress.update(task, description="✗ No papers found")
                    console.print("[yellow]No papers found matching that title[/yellow]")
                    return False
                
                progress.update(task, description=f"✓ Found {len(papers)} papers")
            
            # Display search results
            console.print(f"\n[bold]Found {len(papers)} papers:[/bold]")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim", width=3)
            table.add_column("Title", style="cyan")
            table.add_column("Authors", style="green")
            table.add_column("ArXiv ID", style="yellow")
            
            for i, paper in enumerate(papers, 1):
                authors_str = ", ".join(paper.author_names[:2])
                if len(paper.author_names) > 2:
                    authors_str += f" (+{len(paper.author_names) - 2} more)"
                
                table.add_row(
                    str(i),
                    paper.title[:60] + "..." if len(paper.title) > 60 else paper.title,
                    authors_str,
                    paper.arxiv_id or "N/A"
                )
            
            console.print(table)
            
            # Let user select a paper
            while True:
                choice = Prompt.ask(
                    "\nSelect a paper to ingest (1-{}) or 'q' to quit".format(len(papers)),
                    default="q"
                )
                
                if choice.lower() == 'q':
                    return False
                
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(papers):
                        selected_paper = papers[index]
                        
                        # Show detailed info and confirm
                        console.print(f"\n[bold]Selected paper:[/bold]")
                        self.display_paper_info(selected_paper, detailed=True)
                        
                        if Confirm.ask("Ingest this paper?"):
                            ingested_paper = await self.ingestion_service.ingest_selected_paper(selected_paper)
                            if ingested_paper:
                                console.print("[green]✓ Paper ingested successfully![/green]")
                                return True
                            else:
                                console.print("[red]✗ Failed to ingest paper[/red]")
                                return False
                        else:
                            continue
                    else:
                        console.print("[red]Invalid selection[/red]")
                except ValueError:
                    console.print("[red]Please enter a valid number[/red]")
                    
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return False
    
    def display_paper_info(self, paper, detailed: bool = False):
        """Display paper information in a formatted way."""
        console.print(f"\n[bold cyan]Title:[/bold cyan] {paper.title}")
        
        if paper.author_names:
            authors_str = ", ".join(paper.author_names)
            console.print(f"[bold green]Authors:[/bold green] {authors_str}")
        
        if paper.arxiv_id:
            console.print(f"[bold yellow]ArXiv ID:[/bold yellow] {paper.arxiv_id}")
        
        if paper.publication_date:
            console.print(f"[bold blue]Published:[/bold blue] {paper.publication_date}")
        
        if paper.categories:
            console.print(f"[bold magenta]Categories:[/bold magenta] {', '.join(paper.categories)}")
        
        if detailed and paper.abstract:
            abstract = paper.abstract[:300] + "..." if len(paper.abstract) > 300 else paper.abstract
            console.print(f"[bold white]Abstract:[/bold white] {abstract}")
    
    async def show_stats(self):
        """Show ingestion statistics."""
        try:
            stats = await self.ingestion_service.get_ingestion_stats()
            
            console.print("\n[bold]Ingestion Statistics:[/bold]")
            console.print(f"Total papers: {stats.get('total_papers', 0)}")
            console.print(f"Analyzed papers: {stats.get('analyzed_papers', 0)}")
            console.print(f"Pending analysis: {stats.get('pending_papers', 0)}")
            
            if 'ingestion_sources' in stats:
                console.print("\n[bold]By source:[/bold]")
                for source, count in stats['ingestion_sources'].items():
                    console.print(f"  {source}: {count}")
                    
        except Exception as e:
            console.print(f"[red]Error getting stats: {e}[/red]")


@click.group()
def cli():
    """ArXiv Paper Ingestion CLI"""
    pass


@cli.command()
@click.argument('url')
async def arxiv_url(url: str):
    """Ingest paper from ArXiv URL."""
    await db_manager.initialize()
    try:
        cli_tool = PaperIngestionCLI()
        success = await cli_tool.ingest_from_arxiv_url(url)
        sys.exit(0 if success else 1)
    finally:
        await db_manager.close()


@cli.command()
@click.argument('pdf_path')
@click.option('--title', help='Override paper title')
@click.option('--authors', help='Comma-separated list of authors')
async def pdf(pdf_path: str, title: Optional[str], authors: Optional[str]):
    """Ingest paper from PDF file."""
    await db_manager.initialize()
    try:
        cli_tool = PaperIngestionCLI()
        success = await cli_tool.ingest_from_pdf(pdf_path, title, authors)
        sys.exit(0 if success else 1)
    finally:
        await db_manager.close()


@cli.command()
@click.argument('title')
async def search(title: str):
    """Search and ingest paper by title."""
    await db_manager.initialize()
    try:
        cli_tool = PaperIngestionCLI()
        success = await cli_tool.search_and_ingest_by_title(title)
        sys.exit(0 if success else 1)
    finally:
        await db_manager.close()


@cli.command()
async def stats():
    """Show ingestion statistics."""
    await db_manager.initialize()
    try:
        cli_tool = PaperIngestionCLI()
        await cli_tool.show_stats()
    finally:
        await db_manager.close()


def main():
    """Main entry point that handles async commands."""
    import inspect
    
    # Get the command from click context
    ctx = click.get_current_context()
    command = ctx.info_name
    
    # Find the corresponding async function
    for name, func in cli.commands.items():
        if name == command and inspect.iscoroutinefunction(func.callback):
            # Run the async function
            asyncio.run(func.callback(*ctx.params.values()))
            return
    
    # If not async, run normally
    cli()


if __name__ == "__main__":
    main()