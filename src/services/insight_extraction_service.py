"""
Service for extracting structured insights from papers using configurable rubrics.
"""

import json
import logging
import re
from typing import List, Optional, Dict, Any
from uuid import UUID
from dataclasses import dataclass, field

from .rubric_loader import RubricLoader, AnalysisRubric, ExtractionRule
from .llm_client import get_llm_client
from .tag_similarity_service import TagSimilarityService
from ..database.paper_repository import PaperRepository
from ..database.tag_repository import TagRepository, PaperTagRepository
from ..models.paper import Paper
from ..models.insight import Insight
from ..models.tag import Tag
from ..models.enums import PaperType, InsightType, TagCategory, TagSource, AnalysisStatus
from ..config import get_app_config

logger = logging.getLogger(__name__)


@dataclass
class ChainOfThoughtContext:
    """Context manager for tracking reasoning chain state across extraction steps."""
    paper: Paper
    reasoning_chain: List[Dict[str, Any]] = field(default_factory=list)
    extracted_elements: Dict[str, Any] = field(default_factory=dict)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    
    def add_reasoning_step(self, step_name: str, reasoning: str, output: Dict[str, Any], confidence: float):
        """Add a reasoning step to the chain."""
        step = {
            'step_name': step_name,
            'reasoning': reasoning,
            'output': output,
            'confidence': confidence
        }
        self.reasoning_chain.append(step)
        self.confidence_scores[step_name] = confidence
    
    def update_extracted_elements(self, key: str, value: Any):
        """Update extracted elements with new information."""
        self.extracted_elements[key] = value
    
    def get_previous_reasoning(self) -> str:
        """Get formatted previous reasoning for context in next steps."""
        if not self.reasoning_chain:
            return "No previous reasoning steps."
        
        reasoning_text = "Previous reasoning steps:\n"
        for i, step in enumerate(self.reasoning_chain, 1):
            reasoning_text += f"\nStep {i} ({step['step_name']}):\n"
            reasoning_text += f"Reasoning: {step['reasoning']}\n"
            reasoning_text += f"Key findings: {step['output']}\n"
            reasoning_text += f"Confidence: {step['confidence']:.2f}\n"
        
        return reasoning_text


class InsightExtractionService:
    """Service for extracting structured insights from papers."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.rubric_loader = RubricLoader()
        
        # Use provided API key or get from config
        if not openai_api_key:
            config = get_app_config()
            openai_api_key = config.openai_api_key
        
        self.llm_client = get_llm_client(openai_api_key)
        self.tag_similarity_service = TagSimilarityService(openai_api_key)
        self.paper_repo = PaperRepository()
        self.tag_repo = TagRepository()
        self.paper_tag_repo = PaperTagRepository()
        
        # CoT configuration
        self.use_cot_extraction = True  # Feature flag for Chain-of-Thought extraction
    
    async def extract_insights_from_paper(self, paper_id: UUID) -> List[Insight]:
        """Extract insights from a paper using appropriate rubric."""
        try:
            # Get paper from database
            paper = await self.paper_repo.get_by_id(paper_id)
            if not paper:
                logger.error(f"Paper not found: {paper_id}")
                return []
            
            # Get appropriate rubric based on paper type
            rubric = self._get_rubric_for_paper(paper)
            if not rubric:
                logger.error(f"No suitable rubric found for paper type: {paper.paper_type}")
                return []
            
            logger.info(f"Using rubric '{rubric.name}' for paper: {paper.title}")
            
            # Use Chain-of-Thought extraction if enabled
            if self.use_cot_extraction:
                logger.info(f"Using Chain-of-Thought extraction for paper: {paper.title}")
                try:
                    insights = await self._extract_with_cot_chain(paper, rubric)
                    if insights:
                        logger.info(f"CoT extracted {len(insights)} insights from paper: {paper.title}")
                        return insights
                    else:
                        logger.warning(f"CoT extraction failed for paper: {paper.title}, falling back to legacy method")
                except Exception as e:
                    logger.error(f"CoT extraction error for paper {paper.title}: {e}, falling back to legacy method")
            
            # Legacy extraction method (fallback)
            logger.info(f"Using legacy extraction method for paper: {paper.title}")
            return await self._extract_with_legacy_method(paper, rubric)
            
        except Exception as e:
            logger.error(f"Failed to extract insights from paper {paper_id}: {e}")
            return []
    
    async def _extract_with_cot_chain(self, paper: Paper, rubric: AnalysisRubric) -> List[Insight]:
        """Extract insights using Chain-of-Thought multi-step reasoning."""
        logger.info(f"Starting CoT chain extraction for paper: {paper.title}")
        
        # Create CoT context
        context = ChainOfThoughtContext(paper=paper)
        
        # Execute the 5-step CoT chain
        try:
            # Step 1: Content Analysis
            await self._step_1_content_analysis(context)
            
            # Step 2: Research Identification
            await self._step_2_research_identification(context)
            
            # Step 3: Contribution Synthesis
            await self._step_3_contribution_synthesis(context)
            
            # Step 4: Practical Implications
            await self._step_4_practical_implications(context)
            
            # Step 5: Executive Summary/Key Finding
            insights = await self._step_5_executive_synthesis(context, rubric)
            
            logger.info(f"CoT chain completed successfully with {len(insights)} insights")
            return insights
            
        except Exception as e:
            logger.error(f"CoT chain extraction failed: {e}")
            return []
    
    async def _extract_with_legacy_method(self, paper: Paper, rubric: AnalysisRubric) -> List[Insight]:
        """Legacy extraction method (original single-shot approach)."""
        # Find the Key Finding rule as the primary synthesis rule
        key_finding_rule = None
        supporting_rules = []
        
        for rule in rubric.extraction_rules:
            if rule.insight_type == InsightType.KEY_FINDING:
                key_finding_rule = rule
            else:
                supporting_rules.append(rule)
        
        insights = []
        
        # Extract the primary Key Finding insight that synthesizes the entire paper
        if key_finding_rule:
            key_finding_insight = await self._extract_comprehensive_key_finding(
                paper, key_finding_rule, supporting_rules
            )
            if key_finding_insight:
                insights.append(key_finding_insight)
                logger.info(f"Created comprehensive Key Finding insight for paper: {paper.title}")
        
        # Only create supporting insights if they add significant value beyond the Key Finding
        for rule in supporting_rules:
            # Skip if this would create redundant information already covered in Key Finding
            if not self._would_add_unique_value(rule, insights):
                continue
                
            insight = await self._extract_insight_with_rule(paper, rule)
            if insight:
                insights.append(insight)
        
        return insights
    
    # Chain-of-Thought Step Methods
    
    async def _step_1_content_analysis(self, context: ChainOfThoughtContext):
        """Step 1: Analyze paper structure and establish foundational understanding."""
        logger.info("CoT Step 1: Content Analysis")
        
        # Prepare text for this step (no abstract, full text)
        text = self._prepare_text_for_extraction(context.paper)
        
        prompt = """
        Analyze the structure and content of this research paper to establish foundational understanding.
        
        Your task is to:
        1. Identify the paper's structure and main sections
        2. Determine the research domain and field
        3. Understand the paper's scope and complexity
        4. Identify key topics and themes
        
        Return a JSON object with this structure:
        {
            "paper_structure": "Description of paper organization and sections",
            "research_domain": "Primary research field/domain",
            "scope_and_complexity": "Assessment of paper scope and technical complexity",
            "key_topics": ["list", "of", "main", "topics"],
            "reasoning": "Your step-by-step reasoning for this analysis"
        }
        
        Focus on building a solid foundation for subsequent analysis steps.
        """
        
        try:
            result = await self.llm_client.extract_insights(
                prompt=prompt,
                text=text,
                expected_structure={
                    "paper_structure": "",
                    "research_domain": "",
                    "scope_and_complexity": "",
                    "key_topics": [],
                    "reasoning": ""
                }
            )
            
            confidence = 0.85  # Base confidence for structural analysis
            context.add_reasoning_step("content_analysis", result["reasoning"], result, confidence)
            context.update_extracted_elements("structure", result)
            
            logger.info(f"Step 1 completed - Domain: {result.get('research_domain', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"Step 1 failed: {e}")
            # Add empty step to maintain chain
            context.add_reasoning_step("content_analysis", f"Step failed: {e}", {}, 0.0)
    
    async def _step_2_research_identification(self, context: ChainOfThoughtContext):
        """Step 2: Identify core research elements and methodology."""
        logger.info("CoT Step 2: Research Identification")
        
        text = self._prepare_text_for_extraction(context.paper)
        previous_reasoning = context.get_previous_reasoning()
        
        prompt = f"""
        {previous_reasoning}
        
        Based on the previous analysis, now identify the core research elements of this paper.
        
        Your task is to:
        1. Extract the research problem statement
        2. Identify key hypotheses or research questions
        3. Detail the methodology and experimental approach
        4. Identify data sources and evaluation methods
        
        Return a JSON object with this structure:
        {{
            "research_problem": "Clear statement of the problem being addressed",
            "hypotheses_questions": ["list", "of", "key", "research", "questions"],
            "methodology": "Description of research methodology and approach",
            "data_sources": "Information about datasets, experiments, or evaluation",
            "reasoning": "Your step-by-step reasoning building on previous analysis"
        }}
        
        Build on the foundational understanding from Step 1.
        """
        
        try:
            result = await self.llm_client.extract_insights(
                prompt=prompt,
                text=text,
                expected_structure={
                    "research_problem": "",
                    "hypotheses_questions": [],
                    "methodology": "",
                    "data_sources": "",
                    "reasoning": ""
                }
            )
            
            confidence = 0.80  # Research identification confidence
            context.add_reasoning_step("research_identification", result["reasoning"], result, confidence)
            context.update_extracted_elements("methodology", result)
            
            logger.info(f"Step 2 completed - Problem: {result.get('research_problem', 'Unknown')[:100]}...")
            
        except Exception as e:
            logger.error(f"Step 2 failed: {e}")
            context.add_reasoning_step("research_identification", f"Step failed: {e}", {}, 0.0)
    
    async def _step_3_contribution_synthesis(self, context: ChainOfThoughtContext):
        """Step 3: Synthesize the paper's main contributions and findings."""
        logger.info("CoT Step 3: Contribution Synthesis")
        
        text = self._prepare_text_for_extraction(context.paper)
        previous_reasoning = context.get_previous_reasoning()
        
        prompt = f"""
        {previous_reasoning}
        
        Based on your understanding of the paper's structure and research elements, now synthesize the main contributions and findings.
        
        Your task is to:
        1. Identify the paper's main contributions and innovations
        2. Extract key findings and experimental results
        3. Identify novel approaches or techniques introduced
        4. Assess the significance of the work to the field
        
        Return a JSON object with this structure:
        {{
            "main_contributions": ["list", "of", "primary", "contributions"],
            "key_findings": ["specific", "findings", "and", "results"],
            "novel_approaches": ["new", "techniques", "or", "methods"],
            "significance": "Assessment of work's importance and impact",
            "reasoning": "Your step-by-step reasoning building on previous steps"
        }}
        
        Focus on what makes this work unique and valuable.
        """
        
        try:
            result = await self.llm_client.extract_insights(
                prompt=prompt,
                text=text,
                expected_structure={
                    "main_contributions": [],
                    "key_findings": [],
                    "novel_approaches": [],
                    "significance": "",
                    "reasoning": ""
                }
            )
            
            confidence = 0.85  # High confidence for contribution synthesis
            context.add_reasoning_step("contribution_synthesis", result["reasoning"], result, confidence)
            context.update_extracted_elements("contributions", result)
            
            logger.info(f"Step 3 completed - {len(result.get('main_contributions', []))} contributions identified")
            
        except Exception as e:
            logger.error(f"Step 3 failed: {e}")
            context.add_reasoning_step("contribution_synthesis", f"Step failed: {e}", {}, 0.0)
    
    async def _step_4_practical_implications(self, context: ChainOfThoughtContext):
        """Step 4: Extract practical applications and real-world implications."""
        logger.info("CoT Step 4: Practical Implications")
        
        text = self._prepare_text_for_extraction(context.paper)
        previous_reasoning = context.get_previous_reasoning()
        
        prompt = f"""
        {previous_reasoning}
        
        Based on your comprehensive understanding of this research, now identify the practical applications and real-world implications.
        
        Your task is to:
        1. Identify practical applications of this research
        2. Extract industry implications and use cases
        3. Detail implementation considerations
        4. Determine target audiences and stakeholders
        
        Return a JSON object with this structure:
        {{
            "practical_applications": ["specific", "real-world", "applications"],
            "industry_implications": "How this affects industry or practice",
            "implementation_considerations": "What's needed to apply this work",
            "target_audiences": ["who", "would", "benefit", "from", "this"],
            "reasoning": "Your step-by-step reasoning building on all previous analysis"
        }}
        
        Focus on translating research insights into actionable implications.
        """
        
        try:
            result = await self.llm_client.extract_insights(
                prompt=prompt,
                text=text,
                expected_structure={
                    "practical_applications": [],
                    "industry_implications": "",
                    "implementation_considerations": "",
                    "target_audiences": [],
                    "reasoning": ""
                }
            )
            
            confidence = 0.80  # Practical implications confidence
            context.add_reasoning_step("practical_implications", result["reasoning"], result, confidence)
            context.update_extracted_elements("applications", result)
            
            logger.info(f"Step 4 completed - {len(result.get('practical_applications', []))} applications identified")
            
        except Exception as e:
            logger.error(f"Step 4 failed: {e}")
            context.add_reasoning_step("practical_implications", f"Step failed: {e}", {}, 0.0)
    
    async def _step_5_executive_synthesis(self, context: ChainOfThoughtContext, rubric: AnalysisRubric) -> List[Insight]:
        """Step 5: Create comprehensive Key Finding by synthesizing all previous steps."""
        logger.info("CoT Step 5: Executive Synthesis")
        
        # Find the Key Finding rule from the rubric
        key_finding_rule = None
        for rule in rubric.extraction_rules:
            if rule.insight_type == InsightType.KEY_FINDING:
                key_finding_rule = rule
                break
        
        if not key_finding_rule:
            logger.warning("No Key Finding rule found in rubric")
            return []
        
        text = self._prepare_text_for_extraction(context.paper)
        previous_reasoning = context.get_previous_reasoning()
        
        prompt = f"""
        {previous_reasoning}
        
        Now synthesize ALL previous analysis into a comprehensive Key Finding that serves as an executive summary of this research paper.
        
        Your task is to create ONE comprehensive Key Finding that:
        1. Synthesizes insights from all previous steps
        2. Provides a complete overview for content generation
        3. Captures the essence of the research in a structured format
        4. Includes specific, actionable details from the full paper
        
        You MUST return a JSON object that EXACTLY matches this structure:
        {json.dumps(key_finding_rule.expected_structure, indent=2)}
        
        CRITICAL INSTRUCTIONS:
        - Extract highly specific, detailed, and actionable insights directly from the full text
        - Do NOT provide generic summaries or rephrased abstract content
        - Highlight unique contributions, specific methodologies, and concrete results
        - Include practical implications like specific platform integrations or system architectures
        - Focus on what makes this research valuable and how it can be applied
        - Use all the accumulated knowledge from previous reasoning steps
        
        Return only the JSON object with complete details in each field.
        """
        
        try:
            result = await self.llm_client.extract_insights(
                prompt=prompt,
                text=text,
                expected_structure=key_finding_rule.expected_structure
            )
            
            # Calculate confidence based on all previous steps
            step_confidences = list(context.confidence_scores.values())
            avg_confidence = sum(step_confidences) / len(step_confidences) if step_confidences else 0.5
            final_confidence = min(avg_confidence * 1.1, 1.0)  # Slight boost for synthesis
            
            # Create the Key Finding insight
            insight = Insight(
                paper_id=context.paper.id,
                insight_type=InsightType.KEY_FINDING,
                title=self._generate_cot_key_finding_title(context.paper, result),
                description=self._generate_cot_key_finding_description(context.paper, result),
                content=result,
                confidence=final_confidence,
                extraction_method="chain_of_thought"
            )
            
            logger.info(f"Step 5 completed - Key Finding synthesized with confidence: {final_confidence:.2f}")
            return [insight]
            
        except Exception as e:
            logger.error(f"Step 5 failed: {e}")
            return []
    
    def _generate_cot_key_finding_title(self, paper: Paper, content: Dict[str, Any]) -> str:
        """Generate title for CoT-extracted Key Finding."""
        if content.get("main_contribution"):
            return f"Key Finding: {content['main_contribution'][:80]}..."
        elif content.get("audience_hook"):
            return f"Key Finding: {content['audience_hook'][:80]}..."
        else:
            return f"Key Finding: {paper.title[:60]}..."
    
    def _generate_cot_key_finding_description(self, paper: Paper, content: Dict[str, Any]) -> str:
        """Generate description for CoT-extracted Key Finding."""
        parts = []
        if content.get("significance"):
            parts.append(f"Significance: {content['significance']}")
        if content.get("practical_impact"):
            parts.append(f"Impact: {content['practical_impact']}")
        
        return " | ".join(parts) if parts else f"Comprehensive analysis of {paper.title}"

    async def _extract_insight_with_rule(self, paper: Paper, rule: ExtractionRule) -> Optional[Insight]:
        """Extract a single insight using a specific extraction rule."""
        try:
            # Prepare text for extraction
            text_content = self._prepare_text_for_extraction(paper)
            
            # Use LLM to extract structured insight
            extracted_content = await self.llm_client.extract_insights(
                prompt=rule.prompt,
                text=text_content,
                expected_structure=rule.expected_structure
            )
            
            if not extracted_content:
                logger.warning(f"No content extracted for insight type: {rule.insight_type}")
                return None
            
            # Calculate confidence for this extraction
            confidence = self._calculate_extraction_confidence(
                extracted_content, 
                rule.confidence_calculation,
                text_content
            )
            
            # Validate extraction
            validation_errors = self._validate_extraction(extracted_content, rule.validation_rules)
            if validation_errors:
                logger.warning(f"Validation errors for {rule.insight_type}: {validation_errors}")
                confidence *= 0.7  # Reduce confidence for validation issues
            
            # Check minimum confidence threshold
            if confidence < rule.minimum_confidence:
                logger.info(f"Extraction confidence {confidence:.2f} below threshold {rule.minimum_confidence}")
                return None
            
            # Create insight object
            insight = Insight(
                paper_id=paper.id,
                insight_type=rule.insight_type,
                title=self._generate_insight_title(rule.insight_type, extracted_content),
                description=self._generate_insight_description(rule.insight_type, extracted_content),
                content=extracted_content,
                confidence=confidence,
                extraction_method=f"rubric_{rule.insight_type.value}"
            )
            
            logger.info(f"Extracted {rule.insight_type.value} insight with confidence {confidence:.2f}")
            return insight
            
        except Exception as e:
            logger.error(f"Failed to extract insight with rule {rule.insight_type}: {e}")
            return None

    async def _extract_comprehensive_key_finding(self, paper: Paper, key_finding_rule: ExtractionRule, 
                                                supporting_rules: List[ExtractionRule]) -> Optional[Insight]:
        """Extract a comprehensive Key Finding that synthesizes the entire paper."""
        try:
            # Prepare text for extraction
            text_content = self._prepare_text_for_extraction(paper)
            
            # Create an enhanced prompt that asks for comprehensive synthesis
            enhanced_prompt = self._create_comprehensive_key_finding_prompt(
                key_finding_rule.prompt, supporting_rules, paper
            )
            
            # Use LLM to extract structured insight
            extracted_content = await self.llm_client.extract_insights(
                prompt=enhanced_prompt,
                text=text_content,
                expected_structure=key_finding_rule.expected_structure
            )
            
            if not extracted_content:
                logger.warning(f"No content extracted for comprehensive Key Finding")
                return None
            
            # Calculate confidence for this extraction
            confidence = self._calculate_extraction_confidence(
                extracted_content, 
                key_finding_rule.confidence_calculation,
                text_content
            )
            
            # Validate extraction
            validation_errors = self._validate_extraction(extracted_content, key_finding_rule.validation_rules)
            if validation_errors:
                logger.warning(f"Validation errors for Key Finding: {validation_errors}")
                confidence *= 0.7  # Reduce confidence for validation issues
            
            # Check minimum confidence threshold
            if confidence < key_finding_rule.minimum_confidence:
                logger.info(f"Key Finding confidence {confidence:.2f} below threshold {key_finding_rule.minimum_confidence}")
                return None
            
            # Create insight object with a more descriptive title
            insight = Insight(
                paper_id=paper.id,
                insight_type=InsightType.KEY_FINDING,
                title=self._generate_comprehensive_key_finding_title(paper, extracted_content),
                description=self._generate_comprehensive_key_finding_description(paper, extracted_content),
                content=extracted_content,
                confidence=confidence,
                extraction_method=f"comprehensive_synthesis_{key_finding_rule.insight_type.value}"
            )
            
            logger.info(f"Extracted comprehensive Key Finding with confidence {confidence:.2f}")
            return insight
            
        except Exception as e:
            logger.error(f"Failed to extract comprehensive Key Finding: {e}")
            return None

    def _create_comprehensive_key_finding_prompt(self, base_prompt: str, supporting_rules: List[ExtractionRule], 
                                                paper: Paper) -> str:
        """Create an enhanced prompt for comprehensive Key Finding extraction."""
        enhanced_prompt = f"""
{base_prompt}

CRITICAL INSTRUCTIONS: You are extracting a SINGLE, COMPREHENSIVE Key Finding from the FULL TEXT of this research paper. 

Your task is to create ONE detailed Key Finding that captures the SPECIFIC contributions, findings, and implications from this paper. This is NOT a generic summary - it should contain paper-specific details, examples, and insights that demonstrate you have read and understood the full content.

IMPORTANT REQUIREMENTS:
1. Extract SPECIFIC details from the full text, not generic statements
2. Include concrete examples, case studies, or specific findings mentioned in the paper
3. Reference specific technologies, platforms, or applications discussed (e.g., Slack, team decision-making, specific algorithms)
4. Include quantitative results or metrics if mentioned in the paper
5. Capture the paper's unique perspective or novel approach
6. Explain the practical implementation or real-world application

For each field in the expected structure, provide DETAILED, PAPER-SPECIFIC content:
- audience_hook: What specific problem or opportunity does this address? Who specifically would care?
- field_advancement: What specific advancement does this make in the field? How does it differ from existing approaches?
- main_contribution: What is the paper's specific technical or conceptual contribution?
- practical_impact: What specific real-world impact could this have? On which industries or applications?
- problem_solved: What specific problem does this research solve? Include details about the problem context.
- significance: Why is this research significant? What broader implications does it have?
- surprising_insight: What surprising or counterintuitive finding does the paper reveal?

Paper Title: {paper.title}
Paper Type: {paper.paper_type.value if paper.paper_type else 'Unknown'}

Remember: This should be a detailed, paper-specific executive summary that someone could read to understand exactly what this research contributes and why it matters. Avoid generic statements - include specific details from the full text.
"""
        return enhanced_prompt

    def _would_add_unique_value(self, rule: ExtractionRule, existing_insights: List[Insight]) -> bool:
        """Check if a supporting rule would add unique value beyond existing insights."""
        # If we already have a comprehensive Key Finding, be more selective about additional insights
        has_key_finding = any(insight.insight_type == InsightType.KEY_FINDING for insight in existing_insights)
        
        if has_key_finding:
            # Only add supporting insights that provide specific technical details not covered in Key Finding
            if rule.insight_type in [InsightType.METHODOLOGY, InsightType.FRAMEWORK]:
                # These might add technical implementation details
                return True
            else:
                # Other types are likely redundant with comprehensive Key Finding
                return False
        
        return True

    def _generate_comprehensive_key_finding_title(self, paper: Paper, content: Dict[str, Any]) -> str:
        """Generate a descriptive title for the comprehensive Key Finding."""
        if content.get('main_contribution'):
            # Use the main contribution as the basis for the title
            contribution = content['main_contribution']
            if len(contribution) > 60:
                contribution = contribution[:57] + "..."
            return f"Key Finding: {contribution}"
        else:
            return f"Key Finding: {paper.title[:50]}..."

    def _generate_comprehensive_key_finding_description(self, paper: Paper, content: Dict[str, Any]) -> str:
        """Generate a description for the comprehensive Key Finding."""
        if content.get('significance'):
            return f"Comprehensive synthesis of {paper.title} highlighting its significance and impact."
        else:
            return f"Executive summary of the main findings and contributions from {paper.title}."
    
    def _prepare_text_for_extraction(self, paper: Paper) -> str:
        """Prepare paper text for insight extraction."""
        text_parts = []
        
        # Title (important for context)
        if paper.title:
            text_parts.append(f"Title: {paper.title}")
        
        # Categories (domain context)
        if paper.categories:
            text_parts.append(f"Categories: {', '.join(paper.categories)}")
        
        # Full text (no cutoff - use complete text for deep analysis)
        if paper.full_text:
            text_parts.append(f"Content: {paper.full_text}")
        
        return "\n\n".join(text_parts)
    
    def _calculate_extraction_confidence(self, content: Dict[str, Any], 
                                       confidence_config: Dict[str, Any], 
                                       source_text: str) -> float:
        """Calculate confidence score for extracted content."""
        try:
            method = confidence_config.get("method", "structure_completeness")
            
            if method == "keyword_density":
                return self._calculate_keyword_confidence(content, confidence_config, source_text)
            elif method == "structure_completeness":
                return self._calculate_structure_confidence(content, confidence_config)
            elif method == "coverage_analysis":
                return self._calculate_coverage_confidence(content, confidence_config)
            elif method == "data_density":
                return self._calculate_data_confidence(content, confidence_config)
            elif method == "application_completeness":
                return self._calculate_application_confidence(content, confidence_config)
            elif method == "benchmark_completeness":
                return self._calculate_benchmark_confidence(content, confidence_config)
            elif method == "tutorial_completeness":
                return self._calculate_tutorial_confidence(content, confidence_config)
            elif method == "content_completeness":
                return self._calculate_content_confidence(content, confidence_config)
            else:
                # Default: structure completeness
                return self._calculate_structure_confidence(content, confidence_config)
                
        except Exception as e:
            logger.error(f"Failed to calculate confidence: {e}")
            return 0.5  # Default medium confidence
    
    def _calculate_keyword_confidence(self, content: Dict[str, Any], 
                                    config: Dict[str, Any], 
                                    source_text: str) -> float:
        """Calculate confidence based on keyword density in source text."""
        required_keywords = config.get("required_keywords", [])
        min_keyword_count = config.get("min_keyword_count", 1)
        
        found_keywords = 0
        source_lower = source_text.lower()
        
        for keyword in required_keywords:
            if keyword.lower() in source_lower:
                found_keywords += 1
        
        keyword_ratio = found_keywords / len(required_keywords) if required_keywords else 0
        structure_score = len([v for v in content.values() if v]) / len(content) if content else 0
        
        return min((keyword_ratio + structure_score) / 2, 1.0)
    
    def _calculate_structure_confidence(self, content: Dict[str, Any], 
                                      config: Dict[str, Any]) -> float:
        """Calculate confidence based on structure completeness."""
        required_fields = config.get("required_fields", list(content.keys()))
        min_completeness = config.get("min_completeness", 0.5)
        
        filled_fields = 0
        for field in required_fields:
            if field in content and content[field]:
                if isinstance(content[field], list):
                    if len(content[field]) > 0:
                        filled_fields += 1
                elif isinstance(content[field], str):
                    if content[field].strip():
                        filled_fields += 1
                else:
                    filled_fields += 1
        
        completeness = filled_fields / len(required_fields) if required_fields else 0
        return min(completeness / min_completeness, 1.0)
    
    def _calculate_coverage_confidence(self, content: Dict[str, Any], 
                                     config: Dict[str, Any]) -> float:
        """Calculate confidence based on coverage analysis."""
        required_elements = config.get("required_elements", [])
        min_coverage = config.get("min_coverage", 0.7)
        
        covered_elements = 0
        for element in required_elements:
            if element in content and content[element]:
                covered_elements += 1
        
        coverage = covered_elements / len(required_elements) if required_elements else 0
        return min(coverage / min_coverage, 1.0)
    
    def _calculate_data_confidence(self, content: Dict[str, Any], 
                                 config: Dict[str, Any]) -> float:
        """Calculate confidence based on data density."""
        required_metrics = config.get("required_metrics", 1)
        required_results = config.get("required_results", 1)
        
        metrics_count = len(content.get("metrics", []))
        results_count = len(content.get("results", []))
        
        metrics_score = min(metrics_count / required_metrics, 1.0) if required_metrics > 0 else 1.0
        results_score = min(results_count / required_results, 1.0) if required_results > 0 else 1.0
        
        return (metrics_score + results_score) / 2
    
    def _calculate_application_confidence(self, content: Dict[str, Any], 
                                        config: Dict[str, Any]) -> float:
        """Calculate confidence based on application completeness."""
        required_fields = config.get("required_fields", [])
        min_completeness = config.get("min_completeness", 0.75)
        
        return self._calculate_structure_confidence(content, {
            "required_fields": required_fields,
            "min_completeness": min_completeness
        })
    
    def _calculate_benchmark_confidence(self, content: Dict[str, Any], 
                                      config: Dict[str, Any]) -> float:
        """Calculate confidence based on benchmark completeness."""
        required_fields = config.get("required_fields", [])
        min_completeness = config.get("min_completeness", 0.6)
        
        return self._calculate_structure_confidence(content, {
            "required_fields": required_fields,
            "min_completeness": min_completeness
        })
    
    def _calculate_tutorial_confidence(self, content: Dict[str, Any], 
                                     config: Dict[str, Any]) -> float:
        """Calculate confidence based on tutorial completeness."""
        required_fields = config.get("required_fields", [])
        min_completeness = config.get("min_completeness", 0.7)
        
        return self._calculate_structure_confidence(content, {
            "required_fields": required_fields,
            "min_completeness": min_completeness
        })
    
    def _calculate_content_confidence(self, content: Dict[str, Any], 
                                    config: Dict[str, Any]) -> float:
        """Calculate confidence based on content completeness for content generation."""
        required_fields = config.get("required_fields", [])
        min_completeness = config.get("min_completeness", 0.7)
        
        return self._calculate_structure_confidence(content, {
            "required_fields": required_fields,
            "min_completeness": min_completeness
        })
    
    def _validate_extraction(self, content: Dict[str, Any], 
                           validation_rules: List[str]) -> List[str]:
        """Validate extracted content against rules."""
        errors = []
        
        for rule in validation_rules:
            try:
                if "must not be empty" in rule:
                    field = rule.split()[0]
                    if field not in content or not content[field]:
                        errors.append(f"{field} is empty")
                
                elif "must have at least" in rule:
                    parts = rule.split()
                    field = parts[0]
                    # Find the number after "least"
                    least_index = parts.index("least")
                    min_count = int(parts[least_index + 1])
                    
                    if field not in content:
                        errors.append(f"{field} is missing")
                    elif isinstance(content[field], list):
                        if len(content[field]) < min_count:
                            errors.append(f"{field} has {len(content[field])} items, need {min_count}")
                    else:
                        errors.append(f"{field} is not a list")
                        
            except Exception as e:
                logger.warning(f"Failed to validate rule '{rule}': {e}")
        
        return errors
    
    def _generate_insight_title(self, insight_type: InsightType, content: Dict[str, Any]) -> str:
        """Generate a descriptive title for the insight."""
        if insight_type == InsightType.FRAMEWORK:
            name = content.get("name", "Framework")
            return f"Framework: {name}"
        elif insight_type == InsightType.METHODOLOGY:
            return "Implementation Methodology"
        elif insight_type == InsightType.CONCEPT:
            domain = content.get("research_domain", "Research")
            return f"Key Concepts in {domain}"
        elif insight_type == InsightType.DATA_POINT:
            metrics_count = len(content.get("metrics", []))
            return f"Experimental Results ({metrics_count} metrics)"
        elif insight_type == InsightType.APPLICATION:
            domain = content.get("problem_domain", "Application")
            return f"Application: {domain}"
        else:
            return f"{insight_type.value.replace('_', ' ').title()} Insight"
    
    def _generate_insight_description(self, insight_type: InsightType, content: Dict[str, Any]) -> str:
        """Generate a description for the insight."""
        if insight_type == InsightType.FRAMEWORK:
            concept = content.get("core_concept", "")
            return f"Framework analysis: {concept}"
        elif insight_type == InsightType.METHODOLOGY:
            steps_count = len(content.get("steps", []))
            return f"Implementation methodology with {steps_count} steps"
        elif insight_type == InsightType.CONCEPT:
            concepts_count = len(content.get("key_concepts", []))
            return f"Comprehensive analysis covering {concepts_count} key concepts"
        elif insight_type == InsightType.DATA_POINT:
            return "Quantitative results and performance metrics from experiments"
        elif insight_type == InsightType.APPLICATION:
            challenge = content.get("specific_challenge", "")
            return f"Real-world application addressing: {challenge}"
        else:
            return f"Structured {insight_type.value.replace('_', ' ')} extracted from paper"
    
    def _get_rubric_for_paper(self, paper: Paper) -> Optional[AnalysisRubric]:
        """Get the most appropriate rubric for a paper."""
        if paper.paper_type:
            rubric = self.rubric_loader.get_rubric_for_paper_type(paper.paper_type)
            if rubric:
                return rubric
            
            # Fallback logic for unsupported paper types
            if paper.paper_type in [PaperType.POSITION_PAPER, PaperType.SURVEY_REVIEW]:
                return self.rubric_loader.load_rubric("survey_default")
            elif paper.paper_type == PaperType.CONCEPTUAL_FRAMEWORK:
                return self.rubric_loader.load_rubric("framework_default")
            elif paper.paper_type == PaperType.CASE_STUDY:
                return self.rubric_loader.load_rubric("case_study_default")
            elif paper.paper_type == PaperType.EMPIRICAL_STUDY:
                return self.rubric_loader.load_rubric("empirical_default")
            elif paper.paper_type == PaperType.BENCHMARK_COMPARISON:
                return self.rubric_loader.load_rubric("benchmark_default")
            elif paper.paper_type == PaperType.TUTORIAL_METHODOLOGY:
                return self.rubric_loader.load_rubric("tutorial_default")
            else:
                # Default to empirical for unknown types
                return self.rubric_loader.load_rubric("empirical_default")
        else:
            # Default to empirical rubric if no type is set
            return self.rubric_loader.load_rubric("empirical_default")
    
    # Centralized tag processing methods following TAG_GUIDELINES.md
    async def _process_and_create_tag(self, term: str, category: TagCategory, 
                                    description: str = "") -> Optional[Tag]:
        """Centralized method to process and create tags following guidelines."""
        try:
            # Step 1: Clean the term
            cleaned_term = self._clean_tag_term(term)
            if not cleaned_term:
                return None
            
            # Step 2: Check for existing similar tags using vector similarity
            similar_tags = await self.tag_similarity_service.find_similar_tags(
                cleaned_term, category, limit=3
            )
            
            # If we find a highly similar tag, use it instead
            if similar_tags and similar_tags[0][1] >= 0.9:  # 90% similarity threshold
                best_match, similarity = similar_tags[0]
                logger.info(f"Found highly similar tag: '{cleaned_term}' -> '{best_match.name}' (similarity: {similarity:.3f})")
                return best_match
            
            # Step 3: Use LLM to suggest a generalized term
            suggested_term = await self.tag_similarity_service.suggest_generalized_tag(
                cleaned_term, category
            )
            
            if suggested_term:
                logger.info(f"LLM suggested generalization: '{cleaned_term}' -> '{suggested_term}'")
                generalized_term = suggested_term
            else:
                # If LLM fails, skip this tag rather than using manual fallback
                logger.warning(f"LLM failed to generalize '{cleaned_term}', skipping tag creation")
                return None
            
            if not generalized_term:
                return None
            
            # Step 4: Validate the term
            if not self._validate_tag_term(generalized_term, category):
                return None
            
            # Step 5: Generate description if not provided
            if not description:
                description = self._generate_tag_description(generalized_term, category)
            
            # Step 6: Get or create the tag
            return await self._get_or_create_tag(generalized_term, category, description)
            
        except Exception as e:
            logger.error(f"Failed to process and create tag '{term}': {e}")
            return None
    
    def _clean_tag_term(self, term: str) -> Optional[str]:
        """Clean tag term according to guidelines."""
        if not term or not isinstance(term, str):
            return None
        
        # Convert to lowercase and strip whitespace
        cleaned = term.lower().strip()
        
        # Remove paper-specific identifiers
        paper_specific_patterns = [
            r'\b(paper|study|research|work|approach|method|framework|model|system)\b',
            r'\b(step\s*\d+|phase\s*\d+|stage\s*\d+)\b',
            r'\b(version\s*\d+\.\d+)\b',
            r'\b(implementation|proposed|novel|new|improved|enhanced)\b'
        ]
        
        for pattern in paper_specific_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Replace special characters with hyphens
        cleaned = re.sub(r'[^\w\s-]', '-', cleaned)
        
        # Replace multiple spaces/hyphens with single hyphen
        cleaned = re.sub(r'[\s-]+', '-', cleaned)
        
        # Remove leading/trailing hyphens
        cleaned = cleaned.strip('-')
        
        # Limit length
        if len(cleaned) > 50:
            cleaned = cleaned[:50].rstrip('-')
        
        return cleaned if cleaned else None
    
    def _generalize_tag_term(self, term: str) -> Optional[str]:
        """Generalize tag term to be applicable across papers."""
        if not term:
            return None
        
        # Generalization mappings
        generalization_mappings = {
            # Technical concepts
            'attention-is-all-you-need': 'transformer-architecture',
            'bert': 'transformer-architecture',
            'gpt': 'transformer-architecture',
            'llama': 'transformer-architecture',
            'neural-network': 'neural-networks',
            'deep-learning': 'neural-networks',
            'machine-learning': 'ai-ml',
            'artificial-intelligence': 'ai-ml',
            'natural-language-processing': 'nlp',
            'computer-vision': 'computer-vision',
            'reinforcement-learning': 'reinforcement-learning',
            
            # Methodologies
            'supervised-learning': 'supervised-learning',
            'unsupervised-learning': 'unsupervised-learning',
            'semi-supervised-learning': 'semi-supervised-learning',
            'transfer-learning': 'transfer-learning',
            'fine-tuning': 'fine-tuning',
            'pre-training': 'pre-training',
            'data-preprocessing': 'data-preprocessing',
            'feature-engineering': 'feature-engineering',
            'model-evaluation': 'model-evaluation',
            'cross-validation': 'cross-validation',
            
            # Applications
            'text-classification': 'text-classification',
            'sentiment-analysis': 'sentiment-analysis',
            'named-entity-recognition': 'named-entity-recognition',
            'machine-translation': 'machine-translation',
            'question-answering': 'question-answering',
            'summarization': 'text-summarization',
            'recommendation-system': 'recommendation-systems',
            'anomaly-detection': 'anomaly-detection',
            'image-classification': 'image-classification',
            'object-detection': 'object-detection',
            
            # Research domains
            'computer-science': 'computer-science',
            'information-technology': 'information-technology',
            'data-science': 'data-science',
            'statistics': 'statistics',
            'mathematics': 'mathematics',
            'psychology': 'psychology',
            'linguistics': 'linguistics',
            'cognitive-science': 'cognitive-science',
            'robotics': 'robotics',
            'bioinformatics': 'bioinformatics',
            
            # New mappings based on test results
            'encoder-module-with-self-attention': 'attention-mechanism',
            'decoder-module-with-cross-attention': 'attention-mechanism',
            'position-encoding-mechanism': 'position-encoding',
            'attention-computation': 'attention-mechanism',
            'input-processing': 'data-preprocessing',
            'bleu-score': 'performance-metrics',
            'accuracy': 'performance-metrics',
            'self-attention': 'attention-mechanism',
            'multi-head-attention': 'attention-mechanism',
            
            # Specific methodology mappings
            'analyze-the-relationship-between-size-dataset-size': 'scaling-analysis',
            'derive-simple-equations-that-relate-overfitting-to': 'overfitting-analysis',
            'analyze-relationship': 'relationship-analysis',
            'derive-equations': 'mathematical-modeling',
            'model-size': 'model-scaling',
            'dataset-size': 'data-scaling',
            'compute-used': 'computational-resources',
            'overfitting': 'overfitting-analysis',
            'scaling-laws': 'scaling-analysis',
            'neural-language-models': 'language-models'
        }
        
        # Check for exact matches first
        if term in generalization_mappings:
            return generalization_mappings[term]
        
        # Check for partial matches
        for specific_term, generalized_term in generalization_mappings.items():
            if term in specific_term or specific_term in term:
                return generalized_term
        
        # If no mapping found, return the cleaned term
        return term
    
    def _validate_tag_term(self, term: str, category: TagCategory) -> bool:
        """Validate tag term according to guidelines."""
        if not term or len(term) < 2:
            return False
        
        # Avoid overly specific or technical terms
        avoided_terms = {
            'implementation', 'proposed', 'novel', 'new', 'improved', 'enhanced',
            'step', 'phase', 'stage', 'version', 'paper', 'study', 'research',
            'work', 'approach', 'method', 'framework', 'model', 'system',
            'algorithm', 'technique', 'procedure', 'process', 'strategy'
        }
        
        if term in avoided_terms:
            return False
        
        # Check category-specific rules
        if category == TagCategory.RESEARCH_DOMAIN:
            # Research domains should be broad academic fields
            valid_domains = {
                'computer-science', 'information-technology', 'data-science',
                'statistics', 'mathematics', 'psychology', 'linguistics',
                'cognitive-science', 'robotics', 'bioinformatics', 'physics',
                'chemistry', 'biology', 'engineering', 'economics'
            }
            return term in valid_domains
        
        elif category == TagCategory.CONCEPT:
            # Concepts should be fundamental ideas or theories
            return len(term) >= 3 and not term.isdigit()
        
        elif category == TagCategory.METHODOLOGY:
            # Methodologies should be systematic approaches
            return len(term) >= 4 and not term.isdigit()
        
        elif category == TagCategory.APPLICATION:
            # Applications should be use cases or domains
            return len(term) >= 3 and not term.isdigit()
        
        elif category == TagCategory.INNOVATION_MARKER:
            # Innovation markers should indicate significant contributions
            innovation_terms = {
                'breakthrough', 'pioneering', 'groundbreaking', 'revolutionary',
                'state-of-the-art', 'novel-approach', 'innovative-method'
            }
            return term in innovation_terms
        
        return True
    
    def _generate_tag_description(self, term: str, category: TagCategory) -> str:
        """Generate a description for a tag based on its category."""
        term_display = term.replace('-', ' ').title()
        
        descriptions = {
            TagCategory.RESEARCH_DOMAIN: f"Research domain: {term_display}",
            TagCategory.CONCEPT: f"Key concept: {term_display}",
            TagCategory.METHODOLOGY: f"Methodology: {term_display}",
            TagCategory.APPLICATION: f"Application domain: {term_display}",
            TagCategory.INNOVATION_MARKER: f"Innovation marker: {term_display}"
        }
        
        return descriptions.get(category, f"Tag: {term_display}")

    async def create_tags_from_insights(self, insights: List[Insight]) -> List[Tag]:
        """Create tags based on extracted insights and link them to papers."""
        tags = []
        
        for insight in insights:
            # Extract concepts for tagging
            insight_tags = []
            if insight.insight_type == InsightType.FRAMEWORK:
                insight_tags = await self._create_framework_tags(insight)
            elif insight.insight_type == InsightType.CONCEPT:
                insight_tags = await self._create_concept_tags(insight)
            elif insight.insight_type == InsightType.APPLICATION:
                insight_tags = await self._create_application_tags(insight)
            elif insight.insight_type == InsightType.KEY_FINDING:
                insight_tags = await self._create_key_finding_tags(insight)
            elif insight.insight_type == InsightType.METHODOLOGY:
                insight_tags = await self._create_methodology_tags(insight)
            elif insight.insight_type == InsightType.DATA_POINT:
                insight_tags = await self._create_data_point_tags(insight)
            
            # Link tags to the paper
            for tag in insight_tags:
                try:
                    await self.paper_tag_repo.add_tag_to_paper(
                        paper_id=insight.paper_id,
                        tag_id=tag.id,
                        confidence=0.8,  # Default confidence for auto-generated tags
                        source=TagSource.AUTOMATIC
                    )
                    tags.append(tag)
                except Exception as e:
                    # Skip if tag is already linked to paper
                    if "duplicate key" not in str(e).lower():
                        logger.warning(f"Failed to link tag {tag.name} to paper: {e}")
                    tags.append(tag)
        
        return tags
    
    async def _create_framework_tags(self, insight: Insight) -> List[Tag]:
        """Create tags from framework insights."""
        tags = []
        content = insight.content
        
        # Create framework name tag
        if "name" in content and content["name"]:
            tag = await self._process_and_create_tag(
                content["name"], 
                TagCategory.CONCEPT, 
                f"Framework: {content['name']}"
            )
            if tag:
                tags.append(tag)
        
        # Create component tags
        if "components" in content:
            for component in content["components"][:3]:  # Limit to 3 components
                tag = await self._process_and_create_tag(
                    component, 
                    TagCategory.METHODOLOGY,
                    f"Component: {component}"
                )
                if tag:
                    tags.append(tag)
        
        return tags
    
    async def _create_concept_tags(self, insight: Insight) -> List[Tag]:
        """Create tags from concept insights."""
        tags = []
        content = insight.content
        
        # Create domain tag
        if "research_domain" in content and content["research_domain"]:
            tag = await self._process_and_create_tag(
                content["research_domain"], 
                TagCategory.RESEARCH_DOMAIN,
                f"Research domain: {content['research_domain']}"
            )
            if tag:
                tags.append(tag)
        
        # Create concept tags
        if "key_concepts" in content:
            for concept_data in content["key_concepts"][:5]:  # Limit to 5 concepts
                if isinstance(concept_data, dict) and "concept" in concept_data:
                    tag = await self._process_and_create_tag(
                        concept_data["concept"], 
                        TagCategory.CONCEPT,
                        concept_data.get("definition", "")
                    )
                    if tag:
                        tags.append(tag)
        
        return tags
    
    async def _create_application_tags(self, insight: Insight) -> List[Tag]:
        """Create tags from application insights."""
        tags = []
        content = insight.content
        
        # Create domain tag
        if "problem_domain" in content and content["problem_domain"]:
            tag = await self._process_and_create_tag(
                content["problem_domain"], 
                TagCategory.APPLICATION,
                f"Application domain: {content['problem_domain']}"
            )
            if tag:
                tags.append(tag)
        
        return tags
    
    async def _get_or_create_tag(self, name: str, category: TagCategory, 
                               description: str) -> Optional[Tag]:
        """Get existing tag or create new one."""
        try:
            # Check if tag already exists
            existing_tag = await self.tag_repo.get_by_name(name)
            if existing_tag:
                return existing_tag
            
            # Create new tag
            new_tag = Tag(
                name=name,
                category=category,
                description=description
            )
            
            return await self.tag_repo.create(new_tag)
            
        except Exception as e:
            logger.error(f"Failed to get or create tag '{name}': {e}")
            return None
    
    async def _create_key_finding_tags(self, insight: Insight) -> List[Tag]:
        """Create tags from key finding insights."""
        tags = []
        content = insight.content
        
        # Create tag from main contribution
        if "main_contribution" in content and content["main_contribution"]:
            # Extract key terms from main contribution
            contribution = content["main_contribution"].lower()
            key_terms = []
            
            # Look for important technical terms
            if "transformer" in contribution:
                key_terms.append("transformer")
            if "attention" in contribution:
                key_terms.append("attention-mechanism")
            if "neural" in contribution:
                key_terms.append("neural-networks")
            if "benchmark" in contribution:
                key_terms.append("benchmarking")
            if "agent" in contribution:
                key_terms.append("ai-agents")
            
            for term in key_terms:
                tag = await self._process_and_create_tag(
                    term, 
                    TagCategory.CONCEPT, 
                    f"Key concept: {term.replace('-', ' ').title()}"
                )
                if tag:
                    tags.append(tag)
        
        return tags
    
    async def _create_methodology_tags(self, insight: Insight) -> List[Tag]:
        """Create tags from methodology insights using intelligent tagging."""
        tags = []
        content = insight.content
        
        # Create tags from methodology steps
        if "steps" in content and isinstance(content["steps"], list):
            for step_data in content["steps"][:2]:  # Limit to first 2 steps
                if isinstance(step_data, dict) and "step" in step_data:
                    # Pass the raw step description to the intelligent tagging system
                    # Let the LLM + vector similarity handle generalization
                    step_description = step_data["step"]
                    
                    tag = await self._process_and_create_tag(
                        step_description, 
                        TagCategory.METHODOLOGY,
                        f"Methodology step: {step_description}"
                    )
                    if tag:
                        tags.append(tag)
        
        return tags
    
    async def _create_data_point_tags(self, insight: Insight) -> List[Tag]:
        """Create tags from data point insights."""
        tags = []
        content = insight.content
        
        # Create tags from metrics
        if "metrics" in content and isinstance(content["metrics"], list):
            for metric_data in content["metrics"][:2]:  # Limit to first 2 metrics
                if isinstance(metric_data, dict) and "name" in metric_data:
                    tag = await self._process_and_create_tag(
                        metric_data["name"], 
                        TagCategory.CONCEPT,
                        f"Performance metric: {metric_data['name']}"
                    )
                    if tag:
                        tags.append(tag)
        
        # Create tags from benchmarks
        if "benchmarks" in content and isinstance(content["benchmarks"], list):
            for benchmark_data in content["benchmarks"][:2]:  # Limit to first 2 benchmarks
                if isinstance(benchmark_data, dict) and "name" in benchmark_data:
                    tag = await self._process_and_create_tag(
                        benchmark_data["name"], 
                        TagCategory.APPLICATION,
                        f"Benchmark: {benchmark_data['name']}"
                    )
                    if tag:
                        tags.append(tag)
        
        return tags