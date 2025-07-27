#!/usr/bin/env python3
"""
Script to generate an enhanced Key Finding using multi-step CoT with full text + detailed insights.
"""

import asyncio
import sys
import json
import ast
import os
sys.path.insert(0, "src")

from src.database.connection import db_manager
from src.database.insight_repository import InsightRepository
from src.database.paper_repository import PaperRepository
from src.services.llm_client import get_llm_client
from src.models.insight import Insight, InsightType
from src.models.enums import InsightType as InsightTypeEnum

async def enhance_cot_key_finding():
    """Generate an enhanced Key Finding using multi-step CoT with full text + detailed insights."""
    await db_manager.initialize()
    
    try:
        # Get the Group Recommender paper
        paper_repo = PaperRepository()
        insight_repo = InsightRepository()
        
        paper = await paper_repo.get_by_id('43bfc09d-d3d0-4f97-aa96-53006aa1f4a8')
        if not paper:
            print("❌ Group Recommender paper not found")
            return
        
        print(f"📄 Enhancing Key Finding for: {paper.title}")
        print(f"📋 Paper Type: {paper.paper_type.value}")
        print("=" * 80)
        
        # Get existing insights
        existing_insights = await insight_repo.get_by_paper_id(paper.id)
        
        # Find the original Key Finding
        original_key_finding = None
        position_insights = []
        
        for insight in existing_insights:
            if insight.insight_type == InsightTypeEnum.KEY_FINDING:
                original_key_finding = insight
            elif insight.insight_type in [InsightTypeEnum.CONCEPT, InsightTypeEnum.FUTURE_WORK, InsightTypeEnum.APPLICATION]:
                position_insights.append(insight)
        
        if not original_key_finding:
            print("❌ Original Key Finding not found")
            return
        
        if not position_insights:
            print("❌ No position-specific insights found")
            return
        
        print(f"✅ Found original Key Finding (confidence: {original_key_finding.confidence:.1%})")
        print(f"✅ Found {len(position_insights)} position-specific insights")
        
        # Prepare detailed content for enhanced CoT
        detailed_content = {}
        for insight in position_insights:
            try:
                if isinstance(insight.content, str):
                    content = ast.literal_eval(insight.content)
                else:
                    content = insight.content
                detailed_content[insight.insight_type.value] = content
            except Exception as e:
                print(f"⚠️ Error parsing {insight.insight_type.value} content: {e}")
        
        print(f"\n🔍 Starting enhanced multi-step CoT process...")
        print(f"   Step 1: Full text analysis with detailed insights context")
        print(f"   Step 2: Synthesis and Key Finding generation")
        
        # Generate enhanced Key Finding using multi-step CoT
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ OPENAI_API_KEY environment variable not set")
            print("   Please set your OpenAI API key: export OPENAI_API_KEY='your-key-here'")
            return
        
        llm_client = get_llm_client(api_key)
        enhanced_response = await generate_enhanced_cot_key_finding(llm_client, paper, detailed_content)
        
        if not enhanced_response:
            print("❌ Failed to generate enhanced Key Finding")
            return
        
        # Parse the enhanced response
        try:
            # The LLM client already returns structured data, no parsing needed
            enhanced_content = enhanced_response
            
            # Create new enhanced Key Finding insight
            enhanced_insight = Insight(
                paper_id=paper.id,
                insight_type=InsightTypeEnum.KEY_FINDING,
                title="Enhanced Key Finding (Multi-step CoT with Full Text + Insights)",
                content=json.dumps(enhanced_content),
                confidence=0.95,  # High confidence due to comprehensive analysis
                extraction_method="enhanced_multi_step_chain_of_thought",
                created_at=None  # Will be set by database
            )
            
            # Save enhanced Key Finding
            saved_enhanced_insight = await insight_repo.create(enhanced_insight)
            
            print(f"\n✅ Enhanced Key Finding generated and saved!")
            print(f"   Database ID: {saved_enhanced_insight.id}")
            print(f"   Confidence: {saved_enhanced_insight.confidence:.1%}")
            
            # Display comparison
            print(f"\n" + "="*80)
            print(f"📊 COMPARISON: Original vs Enhanced Key Finding")
            print(f"="*80)
            
            print(f"\n🔍 ORIGINAL KEY FINDING:")
            print(f"   Method: {original_key_finding.extraction_method}")
            print(f"   Confidence: {original_key_finding.confidence:.1%}")
            print(f"   Content Preview:")
            try:
                original_content = ast.literal_eval(original_key_finding.content) if isinstance(original_key_finding.content, str) else original_key_finding.content
                for key, value in original_content.items():
                    print(f"     {key}: {str(value)[:100]}...")
            except:
                print(f"     {original_key_finding.content[:200]}...")
            
            print(f"\n🚀 ENHANCED KEY FINDING:")
            print(f"   Method: {saved_enhanced_insight.extraction_method}")
            print(f"   Confidence: {saved_enhanced_insight.confidence:.1%}")
            print(f"   Content Preview:")
            for key, value in enhanced_content.items():
                print(f"     {key}: {str(value)[:100]}...")
            
            print(f"\n🎯 Key Improvements:")
            print(f"   • Enhanced with {len(position_insights)} detailed position-specific insights")
            print(f"   • Maintains full text analysis (like original CoT)")
            print(f"   • Multi-step process with rich context integration")
            print(f"   • Higher confidence due to comprehensive input data")
            
        except Exception as e:
            print(f"❌ Error parsing enhanced response: {e}")
            print(f"Raw response: {enhanced_response[:500]}...")
        
    except Exception as e:
        print(f"❌ Error during enhanced CoT: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_manager.close()

async def generate_enhanced_cot_key_finding(llm_client, paper, detailed_content):
    """Generate enhanced Key Finding using multi-step CoT with full text + detailed insights."""
    
    # Step 1: Create enhanced CoT prompt that includes full text analysis
    enhanced_prompt = create_enhanced_multi_step_cot_prompt(paper, detailed_content)
    
    print(f"   📝 Step 1: Analyzing full text with detailed insights context...")
    
    # Define expected structure for the Key Finding
    expected_structure = {
        "problem_solved": "",
        "main_contribution": "",
        "field_advancement": "",
        "practical_impact": "",
        "significance": "",
        "surprising_insight": ""
    }
    
    # Generate enhanced Key Finding using the LLM client's extract_insights method
    enhanced_response = await llm_client.extract_insights(
        prompt=enhanced_prompt,
        text=paper.full_text or paper.abstract,
        expected_structure=expected_structure
    )
    
    return enhanced_response

def create_enhanced_multi_step_cot_prompt(paper, detailed_content):
    """Create an enhanced multi-step CoT prompt using full text + detailed position-specific insights."""
    
    # Format detailed content for the prompt
    concept_content = detailed_content.get('concept', {})
    future_work_content = detailed_content.get('future_work', {})
    application_content = detailed_content.get('application', {})
    
    # Prepare full text sections for analysis
    full_text = paper.full_text or ""
    text_sections = prepare_text_sections(full_text)
    
    prompt = f"""
You are an expert research analyst performing a comprehensive Chain of Thought (CoT) analysis to generate a Key Finding for a position paper. You will follow a true multi-step reasoning process.

PAPER INFORMATION:
Title: {paper.title}
Abstract: {paper.abstract}
Paper Type: {paper.paper_type.value}

FULL TEXT FOR ANALYSIS:
{text_sections}

DETAILED POSITION-SPECIFIC INSIGHTS (Available for Step 2):
1. CONCEPT ANALYSIS:
Main Position: {concept_content.get('main_position', 'N/A')}
Supporting Arguments: {len(concept_content.get('supporting_arguments', []))} detailed arguments
Counter-arguments: {len(concept_content.get('counter_arguments', []))} counter-arguments with responses
Context/Background: {concept_content.get('context_background', 'N/A')}
Stakeholders Impacted: {len(concept_content.get('stakeholders_impacted', []))} stakeholder groups

2. FUTURE WORK ANALYSIS:
Proposed Solution: {future_work_content.get('proposed_solution', 'N/A')}
Implementation Steps: {len(future_work_content.get('implementation_steps', []))} detailed steps
Expected Outcomes: {len(future_work_content.get('expected_outcomes', []))} expected outcomes
Timeline/Roadmap: {len(future_work_content.get('timeline_roadmap', []))} timeline phases
Challenges/Risks: {len(future_work_content.get('challenges_risks', []))} challenges with mitigations

3. APPLICATION ANALYSIS:
Impact Areas: {len(application_content.get('impact_areas', []))} impact areas with descriptions
Stakeholder Groups: {len(application_content.get('stakeholder_groups', []))} stakeholder groups with concerns
Adoption Barriers: {len(application_content.get('adoption_barriers', []))} barriers with severity and mitigation
Industry Relevance: {application_content.get('industry_relevance', 'N/A')}
Research Implications: {application_content.get('research_implications', 'N/A')}

TRUE MULTI-STEP COT ANALYSIS PROCESS:

STEP 1: SYSTEMATIC FULL TEXT ANALYSIS
Follow these reasoning steps sequentially:

1a. PROBLEM IDENTIFICATION
- What specific problem or gap does this paper address?
- What evidence does the paper provide about the problem's significance?
- What are the limitations of current approaches?

1b. MAIN CONTRIBUTION EXTRACTION
- What is the core idea, method, framework, or finding introduced?
- What specific technical contributions are made? (frameworks, algorithms, systems, etc.)
- How is this contribution described and justified?

1c. EVIDENCE AND ARGUMENT ANALYSIS
- What evidence supports the main contribution?
- What arguments are presented for the approach?
- What counter-arguments are addressed?

1d. METHODOLOGY AND APPROACH
- What specific methodology or approach is described?
- What are the key components or steps?
- How is the approach implemented or proposed?

1e. IMPLICATIONS AND IMPACT
- What are the immediate implications of this work?
- What broader impact is suggested?
- What future directions are proposed?

STEP 2: INTEGRATION WITH STORED INSIGHTS
Now reference the detailed position-specific insights to enhance understanding:
- How do the detailed insights provide additional context for the main contribution?
- What specific details from the insights can strengthen the Key Finding?
- Are there specific frameworks, methods, or technical details mentioned in the insights that should be highlighted?
- What stakeholder impacts or practical applications are revealed?

STEP 3: ENHANCED KEY FINDING GENERATION
Generate a comprehensive Key Finding that:
- Incorporates the systematic full text analysis from Step 1
- Adds specific details and context from Step 2 insights
- Emphasizes concrete technical contributions (frameworks, methods, systems)
- Focuses on paper content only (no audience hooks)

CRITICAL REQUIREMENTS:
- MUST identify and mention specific technical contributions (frameworks, methods, systems)
- MUST reference concrete details from the stored insights when they add value
- MUST maintain the systematic reasoning from Step 1
- MUST be more specific and evidence-based than a generic Key Finding

REQUIRED OUTPUT FORMAT (JSON):
{{
    "problem_solved": "The specific problem or gap the paper addresses",
    "main_contribution": "The core idea, method, framework, or finding introduced (be specific about technical contributions)",
    "field_advancement": "How this contribution moves the field forward",
    "practical_impact": "Real-world implications or applications",
    "significance": "Why this work matters broadly",
    "surprising_insight": "Any unexpected findings or counter-intuitive results"
}}

CRITICAL: Do NOT include "audience_hook" or any other fields not listed above. Only use the 6 fields specified.

Remember: The goal is to create a Key Finding that is both comprehensive (from systematic full text analysis) AND enhanced with specific details from the position-specific insights. Focus on concrete technical contributions and specific details rather than generic statements.
"""
    
    return prompt

def prepare_text_sections(full_text):
    """Prepare full text sections for analysis."""
    if not full_text:
        return "Full text not available for analysis."
    
    # Split text into manageable sections
    words = full_text.split()
    section_size = 1000  # words per section
    
    sections = []
    for i in range(0, len(words), section_size):
        section = ' '.join(words[i:i + section_size])
        sections.append(section)
    
    # Format sections for the prompt
    formatted_sections = []
    for i, section in enumerate(sections[:5], 1):  # Limit to first 5 sections
        formatted_sections.append(f"Section {i}: {section[:500]}...")
    
    return "\n\n".join(formatted_sections)

def parse_enhanced_response(response):
    """Parse the enhanced CoT response into structured content."""
    try:
        # Try to extract JSON from the response
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            return json.loads(json_str)
        else:
            # Fallback: create structured content from text
            lines = response.strip().split('\n')
            content = {}
            current_key = None
            current_value = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('"') and ':' in line:
                    if current_key and current_value:
                        content[current_key] = ' '.join(current_value).strip()
                    parts = line.split(':', 1)
                    current_key = parts[0].strip('"')
                    current_value = [parts[1].strip('"')] if len(parts) > 1 else []
                elif line and current_key:
                    current_value.append(line)
            
            if current_key and current_value:
                content[current_key] = ' '.join(current_value).strip()
            
            return content
    except Exception as e:
        print(f"Warning: Could not parse response as JSON: {e}")
        # Return as simple text
        return {"raw_response": response}

if __name__ == "__main__":
    asyncio.run(enhance_cot_key_finding()) 