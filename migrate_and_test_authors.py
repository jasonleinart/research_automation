#!/usr/bin/env python3
"""
Migrate author system and test functionality.
"""

import asyncio
from src.database.connection import db_manager
from src.services.author_service import AuthorService
from src.database.paper_repository import PaperRepository

async def run_migration():
    """Run the author system migration."""
    await db_manager.initialize()
    
    print("🔄 Running author system migration...")
    
    # Read and execute migration
    with open('database/migrations/001_cleanup_authors.sql', 'r') as f:
        migration_sql = f.read()
    
    async with db_manager.get_connection() as conn:
        await conn.execute(migration_sql)
    
    print("✅ Migration completed successfully")

async def test_author_system():
    """Test the author system functionality."""
    await db_manager.initialize()
    
    author_service = AuthorService()
    paper_repo = PaperRepository()
    
    print("\n🧪 Testing author system...")
    
    # Get a sample paper
    papers = await paper_repo.list_all()
    if not papers:
        print("❌ No papers found for testing")
        return
    
    sample_paper = papers[0]
    print(f"📄 Testing with paper: {sample_paper.title[:50]}...")
    
    # Test getting paper with authors
    paper_with_authors = await author_service.get_paper_with_authors(sample_paper.id)
    
    if paper_with_authors:
        print(f"✅ Paper loaded with {len(paper_with_authors.author_names)} authors:")
        for i, author_name in enumerate(paper_with_authors.author_names, 1):
            print(f"   {i}. {author_name}")
    else:
        print("❌ Failed to load paper with authors")
    
    # Test author statistics
    stats = await author_service.get_author_statistics()
    print(f"\n📊 Author Statistics:")
    print(f"   Total authors: {stats.get('total_authors', 0)}")
    print(f"   Papers with authors: {stats.get('total_papers_with_authors', 0)}")
    print(f"   Avg authors per paper: {stats.get('avg_authors_per_paper', 0):.1f}")
    
    # Test most prolific authors
    prolific = stats.get('most_prolific_authors', [])
    if prolific:
        print(f"\n🏆 Most Prolific Authors:")
        for author in prolific[:5]:
            print(f"   - {author['name']}: {author['paper_count']} papers")

async def main():
    try:
        await run_migration()
        await test_author_system()
        print("\n🎉 Author system migration and testing completed successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())