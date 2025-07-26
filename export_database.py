#!/usr/bin/env python3
"""
Export database contents to CSV files for easy viewing and analysis.
"""
import asyncio
import csv
import json
from pathlib import Path
from datetime import datetime
from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.database.insight_repository import InsightRepository
from src.database.tag_repository import TagRepository, PaperTagRepository

async def export_papers():
    """Export papers to CSV."""
    paper_repo = PaperRepository()
    papers = await paper_repo.list_all()
    
    filename = f"papers_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'id', 'arxiv_id', 'title', 'abstract', 'authors', 'publication_date',
            'categories', 'paper_type', 'evidence_strength', 'novelty_score',
            'practical_applicability', 'analysis_status', 'analysis_confidence',
            'extraction_version', 'content_generated', 'content_approved',
            'ingestion_source', 'created_at', 'updated_at'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for paper in papers:
            row = {
                'id': str(paper.id),
                'arxiv_id': paper.arxiv_id,
                'title': paper.title,
                'abstract': paper.abstract,
                'authors': '; '.join([author.name for author in paper.authors]),
                'publication_date': paper.publication_date.isoformat() if paper.publication_date else '',
                'categories': '; '.join(paper.categories),
                'paper_type': paper.paper_type.value if paper.paper_type else '',
                'evidence_strength': paper.evidence_strength.value if paper.evidence_strength else '',
                'novelty_score': paper.novelty_score,
                'practical_applicability': paper.practical_applicability.value if paper.practical_applicability else '',
                'analysis_status': paper.analysis_status.value,
                'analysis_confidence': paper.analysis_confidence,
                'extraction_version': paper.extraction_version,
                'content_generated': paper.content_generated,
                'content_approved': paper.content_approved,
                'ingestion_source': paper.ingestion_source,
                'created_at': paper.created_at.isoformat() if paper.created_at else '',
                'updated_at': paper.updated_at.isoformat() if paper.updated_at else ''
            }
            writer.writerow(row)
    
    print(f"✅ Papers exported to: {filename}")
    return filename

async def export_insights():
    """Export insights to CSV."""
    insight_repo = InsightRepository()
    paper_repo = PaperRepository()
    insights = await insight_repo.list_all()
    
    filename = f"insights_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'id', 'paper_id', 'paper_title', 'paper_arxiv_id', 'insight_type', 
            'title', 'description', 'confidence', 'extraction_method', 'created_at',
            'content_fields', 'content_json'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for insight in insights:
            # Get paper info
            paper = await paper_repo.get_by_id(insight.paper_id)
            
            # Flatten content for easier viewing
            content_fields = []
            if insight.content:
                content_fields = list(insight.content.keys())
            
            row = {
                'id': str(insight.id),
                'paper_id': str(insight.paper_id),
                'paper_title': paper.title if paper else 'Unknown',
                'paper_arxiv_id': paper.arxiv_id if paper else '',
                'insight_type': insight.insight_type.value,
                'title': insight.title,
                'description': insight.description,
                'confidence': insight.confidence,
                'extraction_method': insight.extraction_method,
                'created_at': insight.created_at.isoformat() if insight.created_at else '',
                'content_fields': '; '.join(content_fields),
                'content_json': json.dumps(insight.content, indent=2) if insight.content else ''
            }
            writer.writerow(row)
    
    print(f"✅ Insights exported to: {filename}")
    return filename

async def export_detailed_insights():
    """Export insights with detailed content breakdown."""
    insight_repo = InsightRepository()
    paper_repo = PaperRepository()
    insights = await insight_repo.list_all()
    
    filename = f"insights_detailed_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'id', 'paper_title', 'paper_arxiv_id', 'insight_type', 'title', 
            'description', 'confidence', 'extraction_method', 'created_at'
        ]
        
        # Add dynamic content fields based on what's in the database
        content_fields = set()
        for insight in insights:
            if insight.content:
                content_fields.update(insight.content.keys())
        
        fieldnames.extend(sorted(content_fields))
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for insight in insights:
            # Get paper info
            paper = await paper_repo.get_by_id(insight.paper_id)
            
            row = {
                'id': str(insight.id),
                'paper_title': paper.title if paper else 'Unknown',
                'paper_arxiv_id': paper.arxiv_id if paper else '',
                'insight_type': insight.insight_type.value,
                'title': insight.title,
                'description': insight.description,
                'confidence': insight.confidence,
                'extraction_method': insight.extraction_method,
                'created_at': insight.created_at.isoformat() if insight.created_at else '',
            }
            
            # Add content fields
            if insight.content:
                for field in content_fields:
                    row[field] = insight.content.get(field, '')
            
            writer.writerow(row)
    
    print(f"✅ Detailed insights exported to: {filename}")
    return filename

async def export_cot_insights():
    """Export only Chain of Thought insights with full details."""
    insight_repo = InsightRepository()
    paper_repo = PaperRepository()
    insights = await insight_repo.list_all()
    
    # Filter for CoT insights
    cot_insights = [i for i in insights if i.extraction_method == 'chain_of_thought']
    
    if not cot_insights:
        print("❌ No Chain of Thought insights found.")
        return None
    
    filename = f"cot_insights_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'paper_title', 'paper_arxiv_id', 'insight_type', 'title', 
            'confidence', 'created_at',
            'significance', 'audience_hook', 'problem_solved', 'practical_impact',
            'field_advancement', 'main_contribution', 'surprising_insight'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for insight in cot_insights:
            # Get paper info
            paper = await paper_repo.get_by_id(insight.paper_id)
            
            row = {
                'paper_title': paper.title if paper else 'Unknown',
                'paper_arxiv_id': paper.arxiv_id if paper else '',
                'insight_type': insight.insight_type.value,
                'title': insight.title,
                'confidence': insight.confidence,
                'created_at': insight.created_at.isoformat() if insight.created_at else '',
            }
            
            # Add CoT-specific content fields
            if insight.content:
                row['significance'] = insight.content.get('significance', '')
                row['audience_hook'] = insight.content.get('audience_hook', '')
                row['problem_solved'] = insight.content.get('problem_solved', '')
                row['practical_impact'] = insight.content.get('practical_impact', '')
                row['field_advancement'] = insight.content.get('field_advancement', '')
                row['main_contribution'] = insight.content.get('main_contribution', '')
                row['surprising_insight'] = insight.content.get('surprising_insight', '')
            
            writer.writerow(row)
    
    print(f"✅ CoT insights exported to: {filename}")
    return filename

async def export_stats():
    """Export database statistics."""
    paper_repo = PaperRepository()
    insight_repo = InsightRepository()
    
    papers = await paper_repo.list_all()
    insights = await insight_repo.list_all()
    
    filename = f"database_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Count by various categories
    stats = []
    
    # Paper stats
    stats.append(['Metric', 'Count'])
    stats.append(['Total Papers', len(papers)])
    stats.append(['Total Insights', len(insights)])
    
    # Analysis status
    status_counts = {}
    for paper in papers:
        status = paper.analysis_status.value
        status_counts[status] = status_counts.get(status, 0) + 1
    
    stats.append(['', ''])  # Empty row
    stats.append(['Analysis Status', 'Count'])
    for status, count in status_counts.items():
        stats.append([status.title(), count])
    
    # Paper types
    type_counts = {}
    for paper in papers:
        if paper.paper_type:
            ptype = paper.paper_type.value
            type_counts[ptype] = type_counts.get(ptype, 0) + 1
    
    stats.append(['', ''])  # Empty row
    stats.append(['Paper Type', 'Count'])
    for ptype, count in type_counts.items():
        stats.append([ptype.replace('_', ' ').title(), count])
    
    # Insight types
    insight_type_counts = {}
    for insight in insights:
        itype = insight.insight_type.value
        insight_type_counts[itype] = insight_type_counts.get(itype, 0) + 1
    
    stats.append(['', ''])  # Empty row
    stats.append(['Insight Type', 'Count'])
    for itype, count in insight_type_counts.items():
        stats.append([itype.replace('_', ' ').title(), count])
    
    # Extraction methods
    method_counts = {}
    for insight in insights:
        method = insight.extraction_method or 'unknown'
        method_counts[method] = method_counts.get(method, 0) + 1
    
    stats.append(['', ''])  # Empty row
    stats.append(['Extraction Method', 'Count'])
    for method, count in method_counts.items():
        stats.append([method.replace('_', ' ').title(), count])
    
    # Confidence distribution
    confidences = [i.confidence for i in insights if i.confidence]
    if confidences:
        avg_confidence = sum(confidences) / len(confidences)
        high_confidence = len([c for c in confidences if c >= 0.8])
        
        stats.append(['', ''])  # Empty row
        stats.append(['Confidence Stats', 'Value'])
        stats.append(['Average Confidence', f"{avg_confidence:.1%}"])
        stats.append(['High Confidence (≥80%)', f"{high_confidence}/{len(confidences)} ({high_confidence/len(confidences):.1%})"])
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(stats)
    
    print(f"✅ Database stats exported to: {filename}")
    return filename

async def main():
    """Main export function."""
    await db_manager.initialize()
    
    print("🔬 ArXiv Database Export Tool")
    print("=" * 50)
    
    try:
        # Export all data
        papers_file = await export_papers()
        insights_file = await export_insights()
        detailed_file = await export_detailed_insights()
        cot_file = await export_cot_insights()
        stats_file = await export_stats()
        
        print("\n🎉 Export Complete!")
        print("=" * 50)
        print("Files created:")
        print(f"📄 Papers: {papers_file}")
        print(f"💡 Insights: {insights_file}")
        print(f"🔍 Detailed Insights: {detailed_file}")
        if cot_file:
            print(f"🧠 CoT Insights: {cot_file}")
        print(f"📊 Statistics: {stats_file}")
        print("\nYou can now open these CSV files in:")
        print("• Excel")
        print("• Google Sheets")
        print("• Any spreadsheet application")
        print("• Airtable (import CSV)")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 