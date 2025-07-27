#!/usr/bin/env python3
"""
Script to analyze a specific paper in detail.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.services.paper_classifier import PaperClassifier

async def analyze_paper_by_title(title_fragment: str):
    """Analyze a paper by searching for it by title fragment."""
    try:
        await db_manager.initialize()
        
        repo = PaperRepository()
        classifier = PaperClassifier()
        
        # Search for papers with title containing the fragment
        papers = await repo.search(title_fragment)
        
        if not papers:
            print(f"❌ No papers found containing: {title_fragment}")
            return
        
        # Take the first match
        paper = papers[0]
        
        print(f"📄 Analyzing: {paper.title}")
        print(f"   ArXiv ID: {paper.arxiv_id}")
        print(f"   Categories: {paper.categories}")
        print()
        
        # Show abstract
        if paper.abstract:
            print("📝 Abstract:")
            print(f"   {paper.abstract[:500]}...")
            print()
        
        # Get detailed classification
        classification = classifier.classify_paper(paper)
        
        print("🔍 Detailed Classification Analysis:")
        print(f"   Primary Type: {classification['paper_type'].value} ({classification['type_confidence']:.1%})")
        print(f"   Evidence: {classification['evidence_strength'].value} ({classification['evidence_confidence']:.1%})")
        print(f"   Applicability: {classification['practical_applicability'].value} ({classification['applicability_confidence']:.1%})")
        print(f"   Overall Confidence: {classification['overall_confidence']:.1%}")
        print()
        
        # Analyze text for multiple paper types
        print("🧪 Multi-Type Analysis:")
        text_content = classifier._prepare_text_for_analysis(paper)
        
        # Check scores for all paper types
        type_scores = {}
        for paper_type, rules in classifier.classification_rules['paper_types'].items():
            score = 0.0
            matches = []
            
            # Check title patterns
            for pattern in rules['title_patterns']:
                import re
                if re.search(pattern, text_content, re.IGNORECASE):
                    score += 2.0
                    matches.append(f"Title: {pattern}")
            
            # Check abstract patterns  
            for pattern in rules['abstract_patterns']:
                if re.search(pattern, text_content, re.IGNORECASE):
                    score += 1.5
                    matches.append(f"Abstract: {pattern}")
            
            # Check content indicators
            for indicator in rules['content_indicators']:
                count = len(re.findall(r'\b' + re.escape(indicator) + r'\b', text_content, re.IGNORECASE))
                if count > 0:
                    score += count * 0.5
                    matches.append(f"Content: '{indicator}' ({count}x)")
            
            if score > 0:
                type_scores[paper_type] = {'score': score, 'matches': matches}
        
        # Show top scoring types
        sorted_types = sorted(type_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        
        for i, (paper_type, data) in enumerate(sorted_types[:3]):
            print(f"   {i+1}. {paper_type.value.replace('_', ' ').title()}: {data['score']:.1f} points")
            for match in data['matches'][:3]:  # Show top 3 matches
                print(f"      - {match}")
            print()
        
        # Conclusion
        if len([t for t in sorted_types if t[1]['score'] > 3.0]) > 1:
            print("💡 Analysis: This paper shows strong signals for MULTIPLE types!")
            print("   Consider it a hybrid paper that could legitimately be classified as:")
            for paper_type, data in sorted_types:
                if data['score'] > 3.0:
                    print(f"   - {paper_type.value.replace('_', ' ').title()}")
        else:
            print("💡 Analysis: Clear single-type classification appears appropriate.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await db_manager.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        title_fragment = " ".join(sys.argv[1:])
    else:
        title_fragment = "Agentic Multimodal AI"
    
    asyncio.run(analyze_paper_by_title(title_fragment))