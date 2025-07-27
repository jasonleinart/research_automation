#!/usr/bin/env python3
"""
Test the dashboard functionality.
"""

import asyncio
import sys
import json
sys.path.insert(0, 'src')

from src.web.api.dashboard import get_dashboard_overview, get_dashboard_summary

async def test_dashboard_apis():
    """Test all dashboard API endpoints."""
    print("🧪 Testing Dashboard APIs")
    print("=" * 50)
    
    # Test overview endpoint
    try:
        print("📊 Testing dashboard overview...")
        result = await get_dashboard_overview()
        
        print(f"✅ Overview API working:")
        print(f"   Total papers: {result.stats.total_papers}")
        print(f"   Total insights: {result.stats.total_insights}")
        print(f"   Total tags: {result.stats.total_tags}")
        print(f"   Completed analyses: {result.stats.completed_analyses}")
        print(f"   Full text ratio: {result.stats.full_text_ratio:.1%}")
        
        # Test recent papers
        print(f"\n📄 Recent papers ({len(result.stats.recent_papers)}):")
        for i, paper in enumerate(result.stats.recent_papers[:3], 1):
            print(f"   {i}. {paper.title[:60]}...")
            print(f"      Authors: {len(paper.authors)} ({', '.join([a.name for a in paper.authors[:2]])}{'...' if len(paper.authors) > 2 else ''})")
            print(f"      Type: {paper.paper_type or 'Unknown'}")
            print(f"      Status: {paper.analysis_status}")
        
        # Test recent insights
        print(f"\n💡 Recent insights ({len(result.stats.recent_insights)}):")
        for i, insight in enumerate(result.stats.recent_insights[:3], 1):
            print(f"   {i}. {insight.title}")
            print(f"      Type: {insight.insight_type}")
            print(f"      Confidence: {insight.confidence:.1%}" if insight.confidence else "      Confidence: N/A")
        
        # Test paper type distribution
        print(f"\n📈 Paper type distribution:")
        for paper_type, count in result.stats.paper_type_counts.items():
            print(f"   {paper_type}: {count}")
        
        # Test top tags
        print(f"\n🏷️  Top tags ({len(result.stats.top_tags)}):")
        for tag in result.stats.top_tags:
            print(f"   {tag.name} ({tag.category}): {tag.usage_count} uses")
        
    except Exception as e:
        print(f"❌ Overview API error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test summary endpoint
    try:
        print(f"\n📋 Testing dashboard summary...")
        summary = await get_dashboard_summary()
        
        if summary.get('success'):
            s = summary['summary']
            print(f"✅ Summary API working:")
            print(f"   Papers: {s['papers']['total']} total, {s['papers']['completed']} completed ({s['papers']['completion_rate']:.1f}%)")
            print(f"   Insights: {s['insights']['total']} total, {s['insights']['high_confidence']} high confidence")
            print(f"   Tags: {s['tags']['total']} total")
        else:
            print(f"❌ Summary API returned error")
            
    except Exception as e:
        print(f"❌ Summary API error: {e}")
        import traceback
        traceback.print_exc()

async def test_data_integrity():
    """Test data integrity issues that might affect the dashboard."""
    print(f"\n🔍 Testing Data Integrity")
    print("=" * 50)
    
    from src.database.connection import db_manager
    from src.database.paper_repository import PaperRepository
    from src.services.author_service import AuthorService
    
    await db_manager.initialize()
    
    paper_repo = PaperRepository()
    author_service = AuthorService()
    
    # Check papers without types
    papers = await paper_repo.list_all()
    papers_without_type = [p for p in papers if not p.paper_type]
    
    if papers_without_type:
        print(f"⚠️  Found {len(papers_without_type)} papers without paper_type:")
        for paper in papers_without_type[:3]:
            print(f"   - {paper.title[:60]}...")
    else:
        print(f"✅ All papers have paper_type assigned")
    
    # Check papers without authors
    papers_without_authors = []
    for paper in papers:
        paper_with_authors = await author_service.get_paper_with_authors(paper.id)
        if not paper_with_authors.author_names:
            papers_without_authors.append(paper)
    
    if papers_without_authors:
        print(f"⚠️  Found {len(papers_without_authors)} papers without authors:")
        for paper in papers_without_authors[:3]:
            print(f"   - {paper.title[:60]}...")
    else:
        print(f"✅ All papers have authors assigned")
    
    # Check papers without abstracts
    papers_without_abstract = [p for p in papers if not p.abstract]
    
    if papers_without_abstract:
        print(f"⚠️  Found {len(papers_without_abstract)} papers without abstracts:")
        for paper in papers_without_abstract[:3]:
            print(f"   - {paper.title[:60]}...")
    else:
        print(f"✅ All papers have abstracts")

async def main():
    try:
        await test_dashboard_apis()
        await test_data_integrity()
        
        print(f"\n🎉 Dashboard testing completed!")
        print(f"\n💡 To start the dashboard server, run:")
        print(f"   python start_dashboard.py")
        print(f"\n🌐 Then visit: http://localhost:8000")
        
    except Exception as e:
        print(f"❌ Testing failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())