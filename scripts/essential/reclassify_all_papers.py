#!/usr/bin/env python3
"""
Script to reclassify all papers with enhanced full text analysis.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, "src")

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.services.classification_service import ClassificationService
from src.models.enums import AnalysisStatus

async def reclassify_all_papers():
    """Reclassify all papers with enhanced full text analysis."""
    
    await db_manager.initialize()
    repo = PaperRepository()
    classification_service = ClassificationService()
    
    try:
        # Get all papers
        all_papers = await repo.list_all()
        
        if not all_papers:
            print("❌ No papers found in database")
            return
        
        print(f"📄 Found {len(all_papers)} papers to reclassify")
        print("=" * 60)
        
        # Track results
        results = {
            'total': len(all_papers),
            'completed': 0,
            'manual_review': 0,
            'failed': 0,
            'improvements': 0,
            'no_change': 0,
            'worse': 0
        }
        
        for i, paper in enumerate(all_papers, 1):
            print(f"\n[{i}/{len(all_papers)}] Reclassifying: {paper.title[:60]}...")
            
            # Store original classification for comparison
            original_type = paper.paper_type
            original_confidence = paper.analysis_confidence
            
            # Reclassify
            result = await classification_service.classify_paper(paper.paper_id)
            
            if result:
                new_paper = result['updated_paper']
                new_type = new_paper.paper_type
                new_confidence = new_paper.analysis_confidence
                new_status = new_paper.analysis_status
                
                # Track status
                if new_status == AnalysisStatus.COMPLETED:
                    results['completed'] += 1
                elif new_status == AnalysisStatus.MANUAL_REVIEW:
                    results['manual_review'] += 1
                else:
                    results['failed'] += 1
                
                # Compare confidence
                if original_confidence and new_confidence:
                    confidence_change = float(new_confidence) - float(original_confidence)
                    if confidence_change > 0.1:  # 10% improvement
                        results['improvements'] += 1
                        print(f"  ✅ Improved: {original_confidence:.1f}% → {new_confidence:.1f}% (+{confidence_change:.1f}%)")
                    elif confidence_change < -0.1:
                        results['worse'] += 1
                        print(f"  ⚠️  Decreased: {original_confidence:.1f}% → {new_confidence:.1f}% ({confidence_change:.1f}%)")
                    else:
                        results['no_change'] += 1
                        print(f"  ➡️  Similar: {original_confidence:.1f}% → {new_confidence:.1f}%")
                else:
                    results['improvements'] += 1
                    print(f"  ✅ New classification: {new_confidence:.1f}%")
                
                # Show type change
                if original_type != new_type:
                    print(f"  🔄 Type change: {original_type.value} → {new_type.value}")
                else:
                    print(f"  📊 Type unchanged: {new_type.value}")
                
                print(f"  📈 Status: {new_status.value}")
                
            else:
                results['failed'] += 1
                print(f"  ❌ Failed to reclassify")
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 RECLASSIFICATION SUMMARY")
        print("=" * 60)
        print(f"Total papers: {results['total']}")
        print(f"✅ Completed: {results['completed']} ({results['completed']/results['total']*100:.1f}%)")
        print(f"🔍 Manual Review: {results['manual_review']} ({results['manual_review']/results['total']*100:.1f}%)")
        print(f"❌ Failed: {results['failed']} ({results['failed']/results['total']*100:.1f}%)")
        print()
        print(f"📈 Improvements: {results['improvements']} ({results['improvements']/results['total']*100:.1f}%)")
        print(f"➡️  No change: {results['no_change']} ({results['no_change']/results['total']*100:.1f}%)")
        print(f"⚠️  Decreased: {results['worse']} ({results['worse']/results['total']*100:.1f}%)")
        
        if results['improvements'] > results['total'] * 0.5:
            print("\n🎉 Excellent! Most papers showed improvement with full text analysis!")
        elif results['improvements'] > results['total'] * 0.3:
            print("\n📈 Good! Many papers showed improvement with full text analysis.")
        else:
            print("\n🤔 Mixed results. Some papers may need manual review.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(reclassify_all_papers()) 