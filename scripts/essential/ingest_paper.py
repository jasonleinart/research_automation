#!/usr/bin/env python3
"""
Simple CLI script for manual paper ingestion.
Usage:
  python ingest_paper.py --arxiv-url "https://arxiv.org/abs/2301.12345"
  python ingest_paper.py --pdf "path/to/paper.pdf"
  python ingest_paper.py --title "Attention Is All You Need"
  python ingest_paper.py --stats
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.services.paper_ingestion import PaperIngestionService
from src.models.paper import Author

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def ingest_from_arxiv_url(url: str):
    """Ingest paper from ArXiv URL."""
    print(f"🔍 Fetching paper from ArXiv URL: {url}")
    
    service = PaperIngestionService()
    paper = await service.ingest_from_arxiv_url(url)
    
    if paper:
        print(f"✅ Successfully ingested: {paper.title}")
        print(f"   ArXiv ID: {paper.arxiv_id}")
        print(f"   Authors: {', '.join(paper.author_names)}")
        if paper.categories:
            print(f"   Categories: {', '.join(paper.categories)}")
        return True
    else:
        print("❌ Failed to ingest paper")
        return False


async def ingest_from_pdf(pdf_path: str, title: str = None, authors: str = None):
    """Ingest paper from PDF file."""
    print(f"📄 Processing PDF: {pdf_path}")
    
    # Prepare metadata
    user_metadata = {}
    if title:
        user_metadata['title'] = title
        print(f"   Using title: {title}")
    
    if authors:
        author_list = [Author(name=name.strip()) for name in authors.split(',')]
        user_metadata['authors'] = author_list
        print(f"   Using authors: {authors}")
    
    service = PaperIngestionService()
    paper = await service.ingest_from_pdf(pdf_path, user_metadata)
    
    if paper:
        print(f"✅ Successfully ingested: {paper.title}")
        print(f"   Authors: {', '.join(paper.author_names)}")
        if paper.arxiv_id:
            print(f"   ArXiv ID: {paper.arxiv_id}")
        return True
    else:
        print("❌ Failed to process PDF")
        return False


async def search_by_title(title: str):
    """Search for papers by title."""
    print(f"🔍 Searching for papers with title: {title}")
    
    service = PaperIngestionService()
    papers = await service.ingest_from_title(title)
    
    if not papers:
        print("❌ No papers found")
        return False
    
    print(f"📚 Found {len(papers)} papers:")
    for i, paper in enumerate(papers, 1):
        print(f"\n{i}. {paper.title}")
        print(f"   Authors: {', '.join(paper.author_names)}")
        if paper.arxiv_id:
            print(f"   ArXiv ID: {paper.arxiv_id}")
        if paper.publication_date:
            print(f"   Published: {paper.publication_date}")
    
    # Simple selection
    try:
        choice = input(f"\nSelect paper to ingest (1-{len(papers)}) or press Enter to skip: ").strip()
        if choice:
            index = int(choice) - 1
            if 0 <= index < len(papers):
                selected_paper = papers[index]
                
                # Confirm and ingest
                print(f"\nSelected: {selected_paper.title}")
                confirm = input("Ingest this paper? (y/N): ").strip().lower()
                
                if confirm == 'y':
                    ingested_paper = await service.ingest_selected_paper(selected_paper)
                    if ingested_paper:
                        print("✅ Paper ingested successfully!")
                        return True
                    else:
                        print("❌ Failed to ingest paper")
                        return False
    except (ValueError, IndexError):
        print("Invalid selection")
    
    return False


async def show_stats():
    """Show ingestion statistics."""
    print("📊 Ingestion Statistics:")
    
    service = PaperIngestionService()
    stats = await service.get_ingestion_stats()
    
    print(f"   Total papers: {stats.get('total_papers', 0)}")
    print(f"   Analyzed papers: {stats.get('analyzed_papers', 0)}")
    print(f"   Pending analysis: {stats.get('pending_papers', 0)}")
    
    if 'ingestion_sources' in stats:
        print("\n   By source:")
        for source, count in stats['ingestion_sources'].items():
            print(f"     {source}: {count}")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="ArXiv Paper Ingestion Tool")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--arxiv-url', help='ArXiv URL to ingest')
    group.add_argument('--pdf', help='PDF file path to ingest')
    group.add_argument('--title', help='Search by paper title')
    group.add_argument('--stats', action='store_true', help='Show statistics')
    
    # Optional arguments for PDF ingestion
    parser.add_argument('--pdf-title', help='Override title for PDF ingestion')
    parser.add_argument('--pdf-authors', help='Comma-separated authors for PDF ingestion')
    
    args = parser.parse_args()
    
    try:
        # Initialize database
        await db_manager.initialize()
        
        success = False
        
        if args.arxiv_url:
            success = await ingest_from_arxiv_url(args.arxiv_url)
        elif args.pdf:
            success = await ingest_from_pdf(args.pdf, args.pdf_title, args.pdf_authors)
        elif args.title:
            success = await search_by_title(args.title)
        elif args.stats:
            await show_stats()
            success = True
        
        if not success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())