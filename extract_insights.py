#!/usr/bin/env python3
"""
CLI tool for extracting insights from papers using configurable rubrics.
Usage:
  python extract_insights.py --paper-id <id>     # Extract insights from specific paper
  python extract_insights.py --all-classified    # Extract from all classified papers
  python extract_insights.py --list-rubrics      # List available rubrics
  python extract_insights.py --test-extraction   # Test extraction with sample data
"""

import asyncio
import argparse
import sys
from pathlib import Path
from uuid import UUID

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.services.insight_extraction_service import InsightExtractionService
from src.services.rubric_loader import RubricLoader
from src.database.paper_repository import PaperRepository
from src.database.insight_repository import InsightRepository
from src.models.enums import AnalysisStatus

async def extract_insights_from_paper(paper_id: str):
    """Extract insights from a specific paper."""
    try:
        uuid_id = UUID(paper_id)
        print(f"🔍 Extracting insights from paper: {paper_id}")
        
        service = InsightExtractionService()
        insights = await service.extract_insights_from_paper(uuid_id)
        
        if not insights:
            print("❌ No insights extracted or paper not found")
            return
        
        print(f"\n📊 Extracted {len(insights)} insights:")
        print("-" * 80)
        
        for i, insight in enumerate(insights, 1):
            print(f"\n{i}. {insight.title}")
            print(f"   Type: {insight.insight_type.value.replace('_', ' ').title()}")
            print(f"   Confidence: {insight.confidence:.1%}")
            print(f"   Description: {insight.description}")
            
            # Show key content fields
            if insight.content:
                print("   Key Content:")
                for key, value in list(insight.content.items())[:3]:  # Show first 3 fields
                    if isinstance(value, list):
                        print(f"     {key}: {len(value)} items")
                    elif isinstance(value, str) and len(value) > 100:
                        print(f"     {key}: {value[:100]}...")
                    else:
                        print(f"     {key}: {value}")
        
        # Save insights to database
        print(f"\n💾 Saving insights to database...")
        insight_repo = InsightRepository()
        saved_insights = []
        for insight in insights:
            try:
                saved_insight = await insight_repo.create(insight)
                saved_insights.append(saved_insight)
            except Exception as e:
                print(f"   ⚠️  Failed to save insight: {e}")
        
        print(f"   Saved {len(saved_insights)} insights to database")
        
        # Create tags from insights
        print(f"\n🏷️  Creating tags from insights...")
        tags = await service.create_tags_from_insights(insights)
        
        if tags:
            print(f"   Created {len(tags)} tags:")
            for tag in tags:
                print(f"     - {tag.name} ({tag.category.value})")
        else:
            print("   No tags created")
            
    except ValueError:
        print("❌ Invalid paper ID format. Please provide a valid UUID.")
    except Exception as e:
        print(f"❌ Error: {e}")

async def extract_from_all_classified():
    """Extract insights from all classified papers."""
    print("🔍 Finding classified papers...")
    
    repo = PaperRepository()
    service = InsightExtractionService()
    
    # Get completed papers
    completed_papers = await repo.get_by_status(AnalysisStatus.COMPLETED)
    
    if not completed_papers:
        print("❌ No classified papers found")
        return
    
    print(f"📚 Found {len(completed_papers)} classified papers")
    
    total_insights = 0
    total_tags = 0
    for i, paper in enumerate(completed_papers, 1):
        print(f"\n📄 {i}/{len(completed_papers)}: {paper.title[:60]}...")
        
        insights = await service.extract_insights_from_paper(paper.id)
        total_insights += len(insights)
        
        print(f"   Extracted {len(insights)} insights")
        
        if insights:
            for insight in insights:
                print(f"     - {insight.title} (confidence: {insight.confidence:.1%})")
            
            # Create tags from insights
            print(f"   🏷️  Creating tags from insights...")
            tags = await service.create_tags_from_insights(insights)
            total_tags += len(tags)
            
            if tags:
                print(f"   Created {len(tags)} tags:")
                for tag in tags:
                    print(f"     - {tag.name} ({tag.category.value})")
            else:
                print("   No tags created")
    
    print(f"\n📊 Total: {total_insights} insights extracted from {len(completed_papers)} papers")
    print(f"🏷️  Total: {total_tags} tags created")

async def list_available_rubrics():
    """List all available analysis rubrics."""
    print("📋 Available Analysis Rubrics:")
    
    loader = RubricLoader()
    rubric_ids = loader.list_available_rubrics()
    
    if not rubric_ids:
        print("❌ No rubrics found")
        return
    
    print(f"\n📚 Found {len(rubric_ids)} rubrics:")
    print("-" * 80)
    
    for rubric_id in rubric_ids:
        rubric = loader.load_rubric(rubric_id)
        if rubric:
            paper_types = ", ".join([pt.value.replace('_', ' ').title() for pt in rubric.paper_types])
            print(f"\n📄 {rubric.name} (v{rubric.version})")
            print(f"   ID: {rubric.id}")
            print(f"   Paper Types: {paper_types}")
            print(f"   Domains: {', '.join(rubric.domains)}")
            print(f"   Extraction Rules: {len(rubric.extraction_rules)}")
            if rubric.description:
                print(f"   Description: {rubric.description}")

async def test_extraction():
    """Test extraction system with sample data."""
    print("🧪 Testing insight extraction system...")
    
    repo = PaperRepository()
    service = InsightExtractionService()
    
    # Get a few papers for testing
    papers = await repo.list_all(limit=2)
    
    if not papers:
        print("❌ No papers found for testing")
        return
    
    print(f"📚 Testing with {len(papers)} papers:")
    
    for paper in papers:
        print(f"\n📄 Testing: {paper.title[:50]}...")
        print(f"   Type: {paper.paper_type.value if paper.paper_type else 'Not classified'}")
        
        if not paper.paper_type:
            print("   ⚠️  Paper not classified, skipping")
            continue
        
        # Test insight extraction
        insights = await service.extract_insights_from_paper(paper.id)
        
        print(f"   Extracted {len(insights)} insights:")
        for insight in insights:
            print(f"     - {insight.insight_type.value}: {insight.confidence:.1%} confidence")
        
        # Save insights to database
        if insights:
            insight_repo = InsightRepository()
            saved_insights = []
            for insight in insights:
                try:
                    saved_insight = await insight_repo.create(insight)
                    saved_insights.append(saved_insight)
                except Exception as e:
                    print(f"     ⚠️  Failed to save insight: {e}")
            
            print(f"   💾 Saved {len(saved_insights)} insights to database")
        
        # Test tag creation
        if insights:
            tags = await service.create_tags_from_insights(insights)
            print(f"   Created {len(tags)} tags:")
            for tag in tags[:3]:  # Show first 3 tags
                print(f"     - {tag.name} ({tag.category.value})")

async def show_extraction_stats():
    """Show statistics about insight extraction."""
    print("📊 Insight Extraction Statistics:")
    
    # This would require insight repository - for now show basic info
    repo = PaperRepository()
    stats = await repo.get_statistics()
    
    print(f"\n📈 Paper Status:")
    print(f"   Total papers: {stats.get('total_papers', 0)}")
    print(f"   Classified papers: {stats.get('analyzed_papers', 0)}")
    print(f"   Ready for extraction: {stats.get('analyzed_papers', 0)}")
    
    # Show rubric info
    loader = RubricLoader()
    rubrics = loader.list_available_rubrics()
    print(f"\n📋 Available rubrics: {len(rubrics)}")
    
    for rubric_id in rubrics:
        rubric = loader.load_rubric(rubric_id)
        if rubric:
            print(f"   - {rubric.name}: {len(rubric.extraction_rules)} rules")

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Insight Extraction Tool")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--paper-id', help='Extract insights from specific paper by ID')
    group.add_argument('--all-classified', action='store_true', help='Extract from all classified papers')
    group.add_argument('--list-rubrics', action='store_true', help='List available rubrics')
    group.add_argument('--test-extraction', action='store_true', help='Test extraction with sample data')
    group.add_argument('--stats', action='store_true', help='Show extraction statistics')
    
    args = parser.parse_args()
    
    try:
        # Initialize database
        await db_manager.initialize()
        
        if args.paper_id:
            await extract_insights_from_paper(args.paper_id)
        elif args.all_classified:
            await extract_from_all_classified()
        elif args.list_rubrics:
            await list_available_rubrics()
        elif args.test_extraction:
            await test_extraction()
        elif args.stats:
            await show_extraction_stats()
            
    except KeyboardInterrupt:
        print("\n👋 Extraction cancelled!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())