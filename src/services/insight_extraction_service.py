"""
Service for extracting structured insights from papers using configurable rubrics.
"""

import json
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from .rubric_loader import RubricLoader, AnalysisRubric, ExtractionRule
from .llm_client import get_llm_client
from ..database.paper_repository import PaperRepository
from ..database.tag_repository import TagRepository, PaperTagRepository
from ..models.paper import Paper
from ..models.insight import Insight
from ..models.tag import Tag
from ..models.enums import PaperType, InsightType, TagCategory, TagSource, AnalysisStatus
from ..config import get_app_config

logger = logging.getLogger(__name__)


class InsightExtractionService:
    """Service for extracting structured insights from papers."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.rubric_loader = RubricLoader()
        
        # Use provided API key or get from config
        if not openai_api_key:
            config = get_app_config()
            openai_api_key = config.openai_api_key
        
        self.llm_client = get_llm_client(openai_api_key)
        self.paper_repo = PaperRepository()
        self.tag_repo = TagRepository()
        self.paper_tag_repo = PaperTagRepository()
    
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
            
            # Extract insights using each rule in the rubric
            insights = []
            for rule in rubric.extraction_rules:
                insight = await self._extract_insight_with_rule(paper, rule)
                if insight:
                    insights.append(insight)
            
            logger.info(f"Extracted {len(insights)} insights from paper: {paper.title}")
            return insights
            
        except Exception as e:
            logger.error(f"Failed to extract insights from paper {paper_id}: {e}")
            return []
    
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
    
    def _prepare_text_for_extraction(self, paper: Paper) -> str:
        """Prepare paper text for insight extraction."""
        text_parts = []
        
        # Title (important for context)
        if paper.title:
            text_parts.append(f"Title: {paper.title}")
        
        # Abstract (key insights often here)
        if paper.abstract:
            text_parts.append(f"Abstract: {paper.abstract}")
        
        # Categories (domain context)
        if paper.categories:
            text_parts.append(f"Categories: {', '.join(paper.categories)}")
        
        # Full text (if available, limit to reasonable size)
        if paper.full_text:
            # Use first 8000 characters to stay within LLM limits
            text_parts.append(f"Content: {paper.full_text[:8000]}")
        
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
            tag_name = content["name"].lower().replace(" ", "-")
            tag = await self._get_or_create_tag(tag_name, TagCategory.CONCEPT, 
                                              f"Framework: {content['name']}")
            if tag:
                tags.append(tag)
        
        # Create component tags
        if "components" in content:
            for component in content["components"][:3]:  # Limit to 3 components
                tag_name = component.lower().replace(" ", "-")[:50]  # Limit length
                tag = await self._get_or_create_tag(tag_name, TagCategory.METHODOLOGY,
                                                  f"Component: {component}")
                if tag:
                    tags.append(tag)
        
        return tags
    
    async def _create_concept_tags(self, insight: Insight) -> List[Tag]:
        """Create tags from concept insights."""
        tags = []
        content = insight.content
        
        # Create domain tag
        if "research_domain" in content and content["research_domain"]:
            domain_name = content["research_domain"].lower().replace(" ", "-")
            tag = await self._get_or_create_tag(domain_name, TagCategory.RESEARCH_DOMAIN,
                                              f"Research domain: {content['research_domain']}")
            if tag:
                tags.append(tag)
        
        # Create concept tags
        if "key_concepts" in content:
            for concept_data in content["key_concepts"][:5]:  # Limit to 5 concepts
                if isinstance(concept_data, dict) and "concept" in concept_data:
                    concept_name = concept_data["concept"].lower().replace(" ", "-")[:50]
                    tag = await self._get_or_create_tag(concept_name, TagCategory.CONCEPT,
                                                      concept_data.get("definition", ""))
                    if tag:
                        tags.append(tag)
        
        return tags
    
    async def _create_application_tags(self, insight: Insight) -> List[Tag]:
        """Create tags from application insights."""
        tags = []
        content = insight.content
        
        # Create domain tag
        if "problem_domain" in content and content["problem_domain"]:
            domain_name = content["problem_domain"].lower().replace(" ", "-")
            tag = await self._get_or_create_tag(domain_name, TagCategory.APPLICATION,
                                              f"Application domain: {content['problem_domain']}")
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
                tag = await self._get_or_create_tag(term, TagCategory.CONCEPT, 
                                                  f"Key concept: {term.replace('-', ' ').title()}")
                if tag:
                    tags.append(tag)
        
        return tags
    
    async def _create_methodology_tags(self, insight: Insight) -> List[Tag]:
        """Create tags from methodology insights."""
        tags = []
        content = insight.content
        
        # Create tags from methodology steps
        if "steps" in content and isinstance(content["steps"], list):
            for step_data in content["steps"][:2]:  # Limit to first 2 steps
                if isinstance(step_data, dict) and "step" in step_data:
                    step_name = step_data["step"].lower().replace(" ", "-")[:50]
                    tag = await self._get_or_create_tag(step_name, TagCategory.METHODOLOGY,
                                                      f"Methodology step: {step_data['step']}")
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
                    metric_name = metric_data["name"].lower().replace(" ", "-")[:50]
                    tag = await self._get_or_create_tag(metric_name, TagCategory.CONCEPT,
                                                      f"Performance metric: {metric_data['name']}")
                    if tag:
                        tags.append(tag)
        
        # Create tags from benchmarks
        if "benchmarks" in content and isinstance(content["benchmarks"], list):
            for benchmark_data in content["benchmarks"][:2]:  # Limit to first 2 benchmarks
                if isinstance(benchmark_data, dict) and "name" in benchmark_data:
                    benchmark_name = benchmark_data["name"].lower().replace(" ", "-")[:50]
                    tag = await self._get_or_create_tag(benchmark_name, TagCategory.APPLICATION,
                                                      f"Benchmark: {benchmark_data['name']}")
                    if tag:
                        tags.append(tag)
        
        return tags