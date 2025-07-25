#!/usr/bin/env python3
"""
CLI tool for classifying papers.
Usage:
  python classify_papers.py --all          # Classify all pending papers
  python classify_papers.py --paper-id <id>  # Classify specific paper
  python classify_papers.py --stats        # Show classification statistics
  python classify_papers.py --review       # Show papers needing review
"""

import asyncio
import argparse
import sys
from pathlib import Path
from uuid import UUID

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.services.classification_service import ClassificationService
from src.database.paper_repository import PaperRepository

async def classify_all_pending():
    """Classify all papers with pending status."""
    print("🔍 Finding papers with pending analysis...")
    
    service = ClassificationService()
    results = await service.classify_pending_papers()
    
    if not results:
        print("✅ No pending papers found or all classifications failed")
        return
    
    print(f"\n📊 Classification Results ({len(results)} papers):")
    print("-" * 80)
    
    for result in results:
        classification = result['classification']
        paper_title = result['paper_title'][:60] + "..." if len(result['paper_title']) > 60 else result['paper_title']
        
        print(f"📄 {paper_title}")
        print(f"   Type: {classification['paper_type'].value.replace('_', ' ').title()}")
        print(f"   Evidence: {classification['evidence_strength'].value.title()}")
        print(f"   Applicability: {classification['practical_applicability'].value.replace('_', ' ').title()}")
        print(f"   Confidence: {classification['overall_confidence']:.1%}")
        print(f"   Status: {result['status'].value.replace('_', ' ').title()}")
        print()

async def classify_specific_paper(paper_id: str):
    """Classify a specific paper by ID."""
    try:
        uuid_id = UUID(paper_id)
        print(f"🔍 Classifying paper: {paper_id}")
        
        service = ClassificationService()
        result = await service.classify_paper(uuid_id)
        
        if not result:
            print("❌ Failed to classify paper or paper not found")
            return
        
        classification = result['classification']
        
        print(f"\n📄 {result['paper_title']}")
        print(f"   Type: {classification['paper_type'].value.replace('_', ' ').title()}")
        print(f"   Evidence: {classification['evidence_strength'].value.title()}")
        print(f"   Applicability: {classification['practical_applicability'].value.replace('_', ' ').title()}")
        print(f"   Confidence: {classification['overall_confidence']:.1%}")
        print(f"   Status: {result['status'].value.replace('_', ' ').title()}")
        
        # Show explanation
        from src.services.paper_classifier import PaperClassifier
        classifier = PaperClassifier()
        explanation = classifier.get_classification_explanation(classification)
        print(f"\n💡 {explanation}")
        
    except ValueError:
        print("❌ Invalid paper ID format. Please provide a valid UUID.")

async def show_classification_stats():
    """Show classification statistics."""
    print("📊 Classification Statistics:")
    
    service = ClassificationService()
    stats = await service.get_classification_stats()
    
    print(f"\n📈 Overall Stats:")
    print(f"   Total papers: {stats.get('total_papers', 0)}")
    print(f"   Analyzed papers: {stats.get('analyzed_papers', 0)}")
    print(f"   Pending papers: {stats.get('pending_papers', 0)}")
    
    if 'paper_types' in stats and stats['paper_types']:
        print(f"\n📋 Paper Types:")
        for paper_type, count in stats['paper_types'].items():
            print(f"   {paper_type.replace('_', ' ').title()}: {count}")
    
    if 'evidence_strength' in stats and stats['evidence_strength']:
        print(f"\n🔬 Evidence Strength:")
        for evidence, count in stats['evidence_strength'].items():
            print(f"   {evidence.title()}: {count}")
    
    if 'practical_applicability' in stats and stats['practical_applicability']:
        print(f"\n🛠️  Practical Applicability:")
        for applicability, count in stats['practical_applicability'].items():
            print(f"   {applicability.replace('_', ' ').title()}: {count}")
    
    if 'confidence_distribution' in stats:
        print(f"\n🎯 Confidence Distribution:")
        conf_dist = stats['confidence_distribution']
        print(f"   High (≥80%): {conf_dist.get('high', 0)}")
        print(f"   Medium (50-79%): {conf_dist.get('medium', 0)}")
        print(f"   Low (<50%): {conf_dist.get('low', 0)}")
        print(f"   Unclassified: {conf_dist.get('none', 0)}")

async def show_papers_needing_review():
    """Show papers that need manual review."""
    print("👀 Papers Needing Manual Review:")
    
    service = ClassificationService()
    papers = await service.get_papers_needing_review()
    
    if not papers:
        print("✅ No papers currently need manual review")
        return
    
    print(f"\n📋 {len(papers)} papers need review:")
    print("-" * 80)
    
    for paper in papers:
        paper_title = paper.title[:60] + "..." if len(paper.title) > 60 else paper.title
        print(f"📄 {paper_title}")
        print(f"   ID: {paper.id}")
        if paper.paper_type:
            print(f"   Classified as: {paper.paper_type.value.replace('_', ' ').title()}")
        if paper.analysis_confidence:
            print(f"   Confidence: {paper.analysis_confidence:.1%}")
        print()

async def list_papers_for_classification():
    """List papers available for classification."""
    print("📚 Available Papers:")
    
    repo = PaperRepository()
    papers = await repo.list_all(limit=10)
    
    if not papers:
        print("No papers found in database")
        return
    
    print(f"\n📋 Showing first {len(papers)} papers:")
    print("-" * 80)
    
    for paper in papers:
        paper_title = paper.title[:50] + "..." if len(paper.title) > 50 else paper.title
        status = paper.analysis_status.value.replace('_', ' ').title()
        
        print(f"📄 {paper_title}")
        print(f"   ID: {paper.id}")
        print(f"   Status: {status}")
        if paper.paper_type:
            print(f"   Type: {paper.paper_type.value.replace('_', ' ').title()}")
        if paper.analysis_confidence:
            print(f"   Confidence: {paper.analysis_confidence:.1%}")
        print()

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Paper Classification Tool")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', action='store_true', help='Classify all pending papers')
    group.add_argument('--paper-id', help='Classify specific paper by ID')
    group.add_argument('--stats', action='store_true', help='Show classification statistics')
    group.add_argument('--review', action='store_true', help='Show papers needing manual review')
    group.add_argument('--list', action='store_true', help='List papers available for classification')
    
    args = parser.parse_args()
    
    try:
        # Initialize database
        await db_manager.initialize()
        
        if args.all:
            await classify_all_pending()
        elif args.paper_id:
            await classify_specific_paper(args.paper_id)
        elif args.stats:
            await show_classification_stats()
        elif args.review:
            await show_papers_needing_review()
        elif args.list:
            await list_papers_for_classification()
            
    except KeyboardInterrupt:
        print("\n👋 Classification cancelled!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())