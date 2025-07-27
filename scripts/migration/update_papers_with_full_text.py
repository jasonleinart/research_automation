#!/usr/bin/env python3
"""
Script to update existing papers with full text PDFs.
This script will re-ingest papers from ArXiv URLs and update existing records
instead of creating duplicates.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.services.arxiv_client import ArxivClient
from src.services.pdf_processor import PDFProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def update_paper_with_full_text(paper, arxiv_client, pdf_processor, paper_repo):
    """Update a single paper with full text."""
    try:
        print(f"📄 Processing: {paper.title}")
        print(f"   ArXiv ID: {paper.arxiv_id}")
        
        # Download PDF and extract text
        print("   Downloading PDF...")
        pdf_content = await arxiv_client.download_pdf(paper.arxiv_id)
        
        if not pdf_content:
            print("   ❌ Failed to download PDF")
            return False
        
        # Save PDF temporarily for text extraction
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(pdf_content)
            temp_path = temp_file.name
        
        try:
            # Extract text from PDF
            print("   Extracting text...")
            full_text = pdf_processor.extract_text(temp_path)
            
            if not full_text:
                print("   ❌ Failed to extract text from PDF")
                return False
            
            # Update the paper with full text
            paper.full_text = full_text
            updated_paper = await paper_repo.update_paper(paper)
            
            print(f"   ✅ Successfully updated with {len(full_text)} characters of full text")
            return True
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def main():
    """Main function to update all papers without full text."""
    try:
        # Initialize database
        await db_manager.initialize()
        
        # Initialize services
        paper_repo = PaperRepository()
        arxiv_client = ArxivClient()
        pdf_processor = PDFProcessor()
        
        # Get all papers
        papers = await paper_repo.list_all()
        
        # Filter papers without full text
        papers_without_full_text = [p for p in papers if not p.full_text and p.arxiv_id]
        
        print(f"📊 Found {len(papers)} total papers")
        print(f"📄 Found {len(papers_without_full_text)} papers without full text")
        print()
        
        if not papers_without_full_text:
            print("✅ All papers already have full text!")
            return
        
        # Update each paper
        success_count = 0
        for paper in papers_without_full_text:
            success = await update_paper_with_full_text(paper, arxiv_client, pdf_processor, paper_repo)
            if success:
                success_count += 1
            print()  # Add spacing between papers
        
        print(f"📊 Summary:")
        print(f"   Total papers processed: {len(papers_without_full_text)}")
        print(f"   Successfully updated: {success_count}")
        print(f"   Failed: {len(papers_without_full_text) - success_count}")
        
        if success_count > 0:
            print(f"\n✅ Updated {success_count} papers with full text!")
        else:
            print(f"\n❌ No papers were successfully updated.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main()) 