#!/usr/bin/env python3
"""
Author management utility.
"""

import asyncio
import click
from src.database.connection import db_manager
from src.services.author_service import AuthorService
from src.database.author_repository import AuthorRepository

@click.group()
def cli():
    """Author management commands."""
    pass

@cli.command()
@click.option('--limit', default=20, help='Number of authors to show')
async def list_authors(limit):
    """List all authors."""
    await db_manager.initialize()
    
    author_repo = AuthorRepository()
    authors = await author_repo.list_all()
    
    print(f"👥 Authors ({len(authors)} total):")
    print("-" * 80)
    
    for i, author in enumerate(authors[:limit], 1):
        affiliation = f" ({author.affiliation})" if author.affiliation else ""
        print(f"{i:3d}. {author.name}{affiliation}")
        if author.email:
            print(f"     📧 {author.email}")
        if author.orcid:
            print(f"     🔗 ORCID: {author.orcid}")
    
    if len(authors) > limit:
        print(f"\n... and {len(authors) - limit} more authors")

@cli.command('search')
@click.argument('author_name')
async def search_author(author_name):
    """Search for authors by name."""
    await db_manager.initialize()
    
    author_repo = AuthorRepository()
    authors = await author_repo.search_by_name(author_name)
    
    if not authors:
        print(f"❌ No authors found matching '{author_name}'")
        return
    
    print(f"🔍 Found {len(authors)} authors matching '{author_name}':")
    print("-" * 60)
    
    for author in authors:
        print(f"📝 {author.name}")
        if author.affiliation:
            print(f"   🏢 {author.affiliation}")
        if author.email:
            print(f"   📧 {author.email}")
        
        # Get papers by this author
        paper_ids = await author_repo.get_author_papers(author.id)
        print(f"   📄 {len(paper_ids)} papers")
        print()

@cli.command()
@click.argument('author_name')
async def author_papers(author_name):
    """Show papers by an author."""
    await db_manager.initialize()
    
    author_service = AuthorService()
    papers = await author_service.search_papers_by_author(author_name)
    
    if not papers:
        print(f"❌ No papers found for author '{author_name}'")
        return
    
    print(f"📚 Papers by '{author_name}' ({len(papers)} found):")
    print("-" * 80)
    
    for i, paper in enumerate(papers, 1):
        print(f"{i}. {paper.title}")
        print(f"   Authors: {', '.join(paper.author_names)}")
        if paper.publication_date:
            print(f"   Published: {paper.publication_date}")
        if paper.arxiv_id:
            print(f"   ArXiv: {paper.arxiv_id}")
        print()

@cli.command()
async def stats():
    """Show author statistics."""
    await db_manager.initialize()
    
    author_service = AuthorService()
    stats = await author_service.get_author_statistics()
    
    print("📊 Author System Statistics:")
    print("=" * 50)
    print(f"Total authors: {stats.get('total_authors', 0)}")
    print(f"Papers with authors: {stats.get('total_papers_with_authors', 0)}")
    print(f"Average authors per paper: {stats.get('avg_authors_per_paper', 0):.1f}")
    
    prolific = stats.get('most_prolific_authors', [])
    if prolific:
        print(f"\n🏆 Most Prolific Authors:")
        for author in prolific:
            print(f"   {author['name']}: {author['paper_count']} papers")

@cli.command()
@click.argument('paper_title')
async def paper_authors(paper_title):
    """Show authors for a specific paper."""
    await db_manager.initialize()
    
    from src.database.paper_repository import PaperRepository
    
    paper_repo = PaperRepository()
    author_service = AuthorService()
    
    # Search for paper by title
    papers = await paper_repo.search_by_title(paper_title)
    
    if not papers:
        print(f"❌ No papers found matching '{paper_title}'")
        return
    
    for paper in papers[:5]:  # Show first 5 matches
        print(f"📄 {paper.title}")
        
        # Get authors
        paper_with_authors = await author_service.get_paper_with_authors(paper.id)
        
        if paper_with_authors and paper_with_authors.authors:
            print(f"   👥 Authors ({len(paper_with_authors.authors)}):")
            for i, author in enumerate(paper_with_authors.authors, 1):
                affiliation = f" ({author.affiliation})" if author.affiliation else ""
                print(f"      {i}. {author.name}{affiliation}")
        else:
            print("   ❌ No authors found")
        print()

@cli.command()
@click.argument('author_id')
async def collaboration_network(author_id):
    """Show collaboration network for an author."""
    await db_manager.initialize()
    
    from uuid import UUID
    author_service = AuthorService()
    author_repo = AuthorRepository()
    
    try:
        author_uuid = UUID(author_id)
    except ValueError:
        print(f"❌ Invalid author ID format: {author_id}")
        return
    
    # Get author info
    author = await author_repo.get_by_id(author_uuid)
    if not author:
        print(f"❌ Author not found: {author_id}")
        return
    
    # Get collaboration network
    network = await author_service.get_author_collaboration_network(author_uuid)
    
    print(f"🤝 Collaboration Network for {author.name}")
    print("=" * 60)
    print(f"Total papers: {network['total_papers']}")
    print(f"Total collaborators: {network['total_collaborators']}")
    
    if network['collaborators']:
        print(f"\n👥 Top Collaborators:")
        # Sort by collaboration count
        sorted_collaborators = sorted(
            network['collaborators'], 
            key=lambda x: x['collaboration_count'], 
            reverse=True
        )
        
        for collab in sorted_collaborators[:10]:
            author_info = collab['author']
            count = collab['collaboration_count']
            print(f"   {author_info.name}: {count} papers together")

# Async wrapper for click commands
def async_command(f):
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

# Apply async wrapper to all commands
for command in [list_authors, search_author, author_papers, stats, paper_authors, collaboration_network]:
    command.callback = async_command(command.callback)

if __name__ == "__main__":
    cli()