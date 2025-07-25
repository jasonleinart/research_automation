#!/usr/bin/env python3
"""
Test script for paper ingestion services.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.services.arxiv_client import ArxivClient
from src.services.paper_ingestion import PaperIngestionService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_arxiv_client():
    """Test ArXiv client functionality."""
    print("🧪 Testing ArXiv client...")
    
    client = ArxivClient()
    
    # Test ArXiv ID extraction
    test_urls = [
        "https://arxiv.org/abs/2106.09685",
        "https://arxiv.org/pdf/2106.09685.pdf",
        "2106.09685"
    ]
    
    for url in test_urls:
        arxiv_id = client.extract_arxiv_id(url)
        print(f"  {url} → {arxiv_id}")
    
    # Test metadata fetching
    print("\n📄 Testing metadata fetching...")
    metadata = await client.get_paper_metadata("2106.09685")
    
    if metadata:
        print(f"  Title: {metadata['title']}")
        print(f"  Authors: {len(metadata['authors'])} authors")
        print(f"  Categories: {metadata['categories']}")
        print("  ✅ Metadata fetch successful")
    else:
        print("  ❌ Metadata fetch failed")
    
    return metadata is not None

async def test_paper_search():
    """Test paper search functionality."""
    print("\n🔍 Testing paper search...")
    
    client = ArxivClient()
    papers = await client.search_papers("transformer attention", max_results=3)
    
    print(f"  Found {len(papers)} papers")
    for i, paper in enumerate(papers, 1):
        print(f"  {i}. {paper['title'][:60]}...")
    
    return len(papers) > 0

async def test_ingestion_service():
    """Test the full ingestion service."""
    print("\n🔧 Testing ingestion service...")
    
    service = PaperIngestionService()
    
    # Test stats
    stats = await service.get_ingestion_stats()
    print(f"  Current papers in database: {stats.get('total_papers', 0)}")
    
    # Test title search
    papers = await service.ingest_from_title("LoRA")
    print(f"  Found {len(papers)} papers for 'LoRA' search")
    
    return True

async def main():
    """Run all tests."""
    try:
        print("🚀 Starting ingestion service tests...\n")
        
        # Initialize database
        await db_manager.initialize()
        
        # Run tests
        test_results = []
        
        test_results.append(await test_arxiv_client())
        test_results.append(await test_paper_search())
        test_results.append(await test_ingestion_service())
        
        # Summary
        passed = sum(test_results)
        total = len(test_results)
        
        print(f"\n📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("✅ All tests passed! Ingestion system is ready.")
        else:
            print("❌ Some tests failed. Check the logs above.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        sys.exit(1)
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())