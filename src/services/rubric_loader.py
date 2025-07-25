"""
Rubric configuration loader for analysis templates.
"""

import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..models.enums import PaperType, InsightType

logger = logging.getLogger(__name__)


@dataclass
class ExtractionRule:
    """Configuration for a single insight extraction rule."""
    insight_type: InsightType
    prompt: str
    expected_structure: Dict[str, Any]
    confidence_calculation: Dict[str, Any]
    validation_rules: List[str]
    minimum_confidence: float = 0.5


@dataclass
class AnalysisRubric:
    """Complete analysis rubric configuration."""
    id: str
    name: str
    version: str
    paper_types: List[PaperType]
    domains: List[str]
    extraction_rules: List[ExtractionRule]
    quality_thresholds: Dict[str, float]
    created_at: Optional[str] = None
    description: Optional[str] = None


class RubricLoader:
    """Loads and manages analysis rubric configurations."""
    
    def __init__(self, rubrics_dir: str = "rubrics"):
        self.rubrics_dir = Path(rubrics_dir)
        self.rubrics_dir.mkdir(exist_ok=True)
        self._loaded_rubrics: Dict[str, AnalysisRubric] = {}
        self._create_default_rubrics()
    
    def _create_default_rubrics(self):
        """Create default rubric configurations if they don't exist."""
        default_rubrics = [
            self._create_framework_rubric(),
            self._create_survey_rubric(),
            self._create_empirical_rubric(),
            self._create_case_study_rubric(),
            self._create_benchmark_rubric(),
            self._create_tutorial_rubric()
        ]
        
        for rubric in default_rubrics:
            rubric_file = self.rubrics_dir / f"{rubric.id}.yaml"
            if not rubric_file.exists():
                self.save_rubric(rubric)
                logger.info(f"Created default rubric: {rubric.name}")
    
    def _create_framework_rubric(self) -> AnalysisRubric:
        """Create default rubric for framework papers."""
        return AnalysisRubric(
            id="framework_default",
            name="Conceptual Framework Analysis",
            version="1.0",
            paper_types=[PaperType.CONCEPTUAL_FRAMEWORK],
            domains=["machine-learning", "natural-language-processing", "computer-vision"],
            extraction_rules=[
                ExtractionRule(
                    insight_type=InsightType.FRAMEWORK,
                    prompt="""
                    Identify the main framework or methodology introduced in this paper.
                    Extract the following information:
                    - Framework name and core concept
                    - Key components and their relationships
                    - Novel innovations compared to existing approaches
                    - Technical architecture or design principles
                    
                    Focus on the technical contribution and architectural details.
                    """,
                    expected_structure={
                        "name": "string",
                        "core_concept": "string", 
                        "components": ["string"],
                        "innovations": ["string"],
                        "architecture": "string",
                        "comparison_to_existing": "string"
                    },
                    confidence_calculation={
                        "method": "keyword_density",
                        "required_keywords": ["framework", "architecture", "component", "design"],
                        "min_keyword_count": 3
                    },
                    validation_rules=[
                        "name must not be empty",
                        "components must have at least 2 items",
                        "innovations must have at least 1 item"
                    ],
                    minimum_confidence=0.6
                ),
                ExtractionRule(
                    insight_type=InsightType.METHODOLOGY,
                    prompt="""
                    Describe the step-by-step methodology or process outlined in this framework.
                    Extract:
                    - Implementation steps or workflow
                    - Input requirements and data formats
                    - Output specifications
                    - Validation or evaluation approach
                    
                    Focus on actionable implementation details.
                    """,
                    expected_structure={
                        "steps": [{"step": "string", "description": "string"}],
                        "inputs": ["string"],
                        "outputs": ["string"],
                        "validation_approach": "string"
                    },
                    confidence_calculation={
                        "method": "structure_completeness",
                        "required_fields": ["steps", "inputs", "outputs"],
                        "min_completeness": 0.7
                    },
                    validation_rules=[
                        "steps must have at least 3 items",
                        "inputs must not be empty",
                        "outputs must not be empty"
                    ],
                    minimum_confidence=0.5
                ),
                ExtractionRule(
                    insight_type=InsightType.KEY_FINDING,
                    prompt="""
                    Extract the key finding and main contribution of this framework paper for content generation.
                    Focus on what makes this significant and attention-worthy:
                    - The breakthrough or innovation that changes how we think
                    - Why this matters to practitioners and researchers
                    - The "aha moment" or surprising insight
                    - Practical impact and real-world implications
                    - What problem this solves that people care about
                    
                    Write for an intelligent but non-expert audience. Make it compelling and clear.
                    """,
                    expected_structure={
                        "main_contribution": "string",
                        "significance": "string",
                        "practical_impact": "string",
                        "surprising_insight": "string",
                        "problem_solved": "string",
                        "audience_hook": "string",
                        "field_advancement": "string"
                    },
                    confidence_calculation={
                        "method": "content_completeness",
                        "required_fields": ["main_contribution", "significance", "practical_impact"],
                        "min_completeness": 0.7
                    },
                    validation_rules=[
                        "main_contribution must not be empty",
                        "significance must not be empty",
                        "practical_impact must not be empty"
                    ],
                    minimum_confidence=0.6
                )
            ],
            quality_thresholds={
                "auto_approve": 0.8,
                "manual_review": 0.6,
                "auto_reject": 0.3
            },
            description="Extracts framework components, innovations, and implementation methodology"
        )
    
    def _create_survey_rubric(self) -> AnalysisRubric:
        """Create default rubric for survey papers."""
        return AnalysisRubric(
            id="survey_default",
            name="Survey Paper Analysis",
            version="1.0",
            paper_types=[PaperType.SURVEY_REVIEW, PaperType.POSITION_PAPER],
            domains=["general"],
            extraction_rules=[
                ExtractionRule(
                    insight_type=InsightType.CONCEPT,
                    prompt="""
                    Identify the key concepts, trends, and research areas covered in this survey.
                    Extract:
                    - Main research domain and scope
                    - Key concepts and terminology definitions
                    - Major research trends identified
                    - Gaps in current research
                    - Future research directions
                    
                    Focus on the comprehensive coverage and synthesis of the field.
                    """,
                    expected_structure={
                        "research_domain": "string",
                        "scope": "string",
                        "key_concepts": [{"concept": "string", "definition": "string"}],
                        "research_trends": ["string"],
                        "research_gaps": ["string"],
                        "future_directions": ["string"]
                    },
                    confidence_calculation={
                        "method": "coverage_analysis",
                        "required_elements": ["research_domain", "key_concepts", "research_trends"],
                        "min_coverage": 0.8
                    },
                    validation_rules=[
                        "research_domain must not be empty",
                        "key_concepts must have at least 2 items",
                        "research_trends must have at least 1 items"
                    ],
                    minimum_confidence=0.7
                ),
                ExtractionRule(
                    insight_type=InsightType.KEY_FINDING,
                    prompt="""
                    Extract the key finding and main insights from this survey paper for content generation.
                    Focus on what makes this survey valuable and attention-worthy:
                    - The most important synthesis or meta-insight across the field
                    - Surprising patterns or trends discovered in the literature
                    - Critical gaps that practitioners should know about
                    - The "state of the field" summary that matters most
                    - Future opportunities that excite researchers and practitioners
                    
                    Write for an intelligent audience who wants to understand the field landscape.
                    """,
                    expected_structure={
                        "main_contribution": "string",
                        "significance": "string",
                        "practical_impact": "string",
                        "surprising_insight": "string",
                        "problem_solved": "string",
                        "audience_hook": "string",
                        "field_advancement": "string"
                    },
                    confidence_calculation={
                        "method": "content_completeness",
                        "required_fields": ["main_contribution", "significance", "practical_impact"],
                        "min_completeness": 0.7
                    },
                    validation_rules=[
                        "main_contribution must not be empty",
                        "significance must not be empty",
                        "practical_impact must not be empty"
                    ],
                    minimum_confidence=0.6
                )
            ],
            quality_thresholds={
                "auto_approve": 0.85,
                "manual_review": 0.65,
                "auto_reject": 0.4
            },
            description="Extracts comprehensive coverage analysis and research synthesis"
        )
    
    def _create_empirical_rubric(self) -> AnalysisRubric:
        """Create default rubric for empirical study papers."""
        return AnalysisRubric(
            id="empirical_default",
            name="Empirical Study Analysis",
            version="1.0",
            paper_types=[PaperType.EMPIRICAL_STUDY, PaperType.BENCHMARK_COMPARISON],
            domains=["general"],
            extraction_rules=[
                ExtractionRule(
                    insight_type=InsightType.DATA_POINT,
                    prompt="""
                    Extract quantitative results, performance metrics, and statistical findings.
                    Extract:
                    - Performance metrics and their values
                    - Experimental results and comparisons
                    - Statistical significance indicators
                    - Dataset information and sizes
                    - Baseline comparisons
                    
                    Focus on concrete, measurable outcomes and data points.
                    """,
                    expected_structure={
                        "metrics": [{"name": "string", "value": "string", "unit": "string"}],
                        "results": [{"experiment": "string", "outcome": "string"}],
                        "statistical_significance": "string",
                        "datasets": [{"name": "string", "size": "string", "description": "string"}],
                        "baseline_comparisons": [{"baseline": "string", "improvement": "string"}]
                    },
                    confidence_calculation={
                        "method": "data_density",
                        "required_metrics": 3,
                        "required_results": 2
                    },
                    validation_rules=[
                        "metrics must have at least 1 items",
                        "results must have at least 1 item"
                    ],
                    minimum_confidence=0.6
                ),
                ExtractionRule(
                    insight_type=InsightType.KEY_FINDING,
                    prompt="""
                    Extract the key finding and main results from this empirical study for content generation.
                    Focus on what makes this research significant and attention-worthy:
                    - The most important experimental result or discovery
                    - What this proves or disproves that matters to the field
                    - Surprising or counterintuitive findings
                    - Practical implications for practitioners
                    - How this changes what we thought we knew
                    
                    Write for an audience interested in evidence-based insights and practical applications.
                    """,
                    expected_structure={
                        "main_contribution": "string",
                        "significance": "string",
                        "practical_impact": "string",
                        "surprising_insight": "string",
                        "problem_solved": "string",
                        "audience_hook": "string",
                        "field_advancement": "string"
                    },
                    confidence_calculation={
                        "method": "content_completeness",
                        "required_fields": ["main_contribution", "significance", "practical_impact"],
                        "min_completeness": 0.7
                    },
                    validation_rules=[
                        "main_contribution must not be empty",
                        "significance must not be empty",
                        "practical_impact must not be empty"
                    ],
                    minimum_confidence=0.6
                )
            ],
            quality_thresholds={
                "auto_approve": 0.8,
                "manual_review": 0.6,
                "auto_reject": 0.3
            },
            description="Extracts experimental results, metrics, and statistical findings"
        )
    
    def _create_case_study_rubric(self) -> AnalysisRubric:
        """Create default rubric for case study papers."""
        return AnalysisRubric(
            id="case_study_default",
            name="Case Study Analysis",
            version="1.0",
            paper_types=[PaperType.CASE_STUDY],
            domains=["general"],
            extraction_rules=[
                ExtractionRule(
                    insight_type=InsightType.APPLICATION,
                    prompt="""
                    Identify the specific application or use case being demonstrated.
                    Extract:
                    - Problem domain and specific challenge addressed
                    - Solution approach and implementation details
                    - Real-world deployment context
                    - Practical outcomes and lessons learned
                    - Scalability and generalizability insights
                    
                    Focus on practical implementation and real-world applicability.
                    """,
                    expected_structure={
                        "problem_domain": "string",
                        "specific_challenge": "string",
                        "solution_approach": "string",
                        "implementation_details": ["string"],
                        "deployment_context": "string",
                        "outcomes": ["string"],
                        "lessons_learned": ["string"],
                        "scalability_insights": "string"
                    },
                    confidence_calculation={
                        "method": "application_completeness",
                        "required_fields": ["problem_domain", "solution_approach", "outcomes"],
                        "min_completeness": 0.75
                    },
                    validation_rules=[
                        "problem_domain must not be empty",
                        "solution_approach must not be empty",
                        "outcomes must have at least 2 items"
                    ],
                    minimum_confidence=0.6
                ),
                ExtractionRule(
                    insight_type=InsightType.KEY_FINDING,
                    prompt="""
                    Extract the key finding and main lessons from this case study for content generation.
                    Focus on what makes this case study valuable and attention-worthy:
                    - The most important lesson learned from this real-world application
                    - What worked (or didn't work) that others should know about
                    - Surprising challenges or unexpected successes
                    - Practical insights that practitioners can apply immediately
                    - How this changes best practices or conventional wisdom
                    
                    Write for practitioners who want actionable insights from real-world implementations.
                    """,
                    expected_structure={
                        "main_contribution": "string",
                        "significance": "string",
                        "practical_impact": "string",
                        "surprising_insight": "string",
                        "problem_solved": "string",
                        "audience_hook": "string",
                        "field_advancement": "string"
                    },
                    confidence_calculation={
                        "method": "content_completeness",
                        "required_fields": ["main_contribution", "significance", "practical_impact"],
                        "min_completeness": 0.7
                    },
                    validation_rules=[
                        "main_contribution must not be empty",
                        "significance must not be empty",
                        "practical_impact must not be empty"
                    ],
                    minimum_confidence=0.6
                )
            ],
            quality_thresholds={
                "auto_approve": 0.8,
                "manual_review": 0.6,
                "auto_reject": 0.3
            },
            description="Extracts practical applications, implementations, and real-world outcomes"
        )
    
    def _create_benchmark_rubric(self) -> AnalysisRubric:
        """Create default rubric for benchmark comparison papers."""
        return AnalysisRubric(
            id="benchmark_default",
            name="Benchmark Comparison Analysis",
            version="1.0",
            paper_types=[PaperType.BENCHMARK_COMPARISON],
            domains=["general"],
            extraction_rules=[
                ExtractionRule(
                    insight_type=InsightType.DATA_POINT,
                    prompt="""
                    Extract benchmark results, performance comparisons, and evaluation metrics.
                    Extract:
                    - Benchmark datasets and their characteristics
                    - Performance metrics and comparative results
                    - Baseline methods and their performance
                    - Statistical analysis and significance testing
                    - Key findings from the comparison
                    
                    Focus on quantitative comparisons and performance analysis.
                    """,
                    expected_structure={
                        "benchmarks": [{"name": "string", "description": "string", "size": "string"}],
                        "metrics": [{"name": "string", "value": "string", "unit": "string"}],
                        "baselines": [{"method": "string", "performance": "string"}],
                        "comparisons": [{"method_a": "string", "method_b": "string", "result": "string"}],
                        "statistical_analysis": "string",
                        "key_findings": ["string"]
                    },
                    confidence_calculation={
                        "method": "benchmark_completeness",
                        "required_fields": ["benchmarks", "metrics", "comparisons"],
                        "min_completeness": 0.6
                    },
                    validation_rules=[
                        "benchmarks must have at least 1 items",
                        "metrics must have at least 1 items",
                        "comparisons must have at least 1 items"
                    ],
                    minimum_confidence=0.5
                ),
                ExtractionRule(
                    insight_type=InsightType.KEY_FINDING,
                    prompt="""
                    Extract the key finding and main insights from this benchmark comparison for content generation.
                    Focus on what makes this comparison significant and attention-worthy:
                    - The most important performance insight or ranking result
                    - Which method won and why it matters
                    - Surprising performance differences or unexpected results
                    - Practical implications for choosing between methods
                    - What this settles or reveals about the state of the field
                    
                    Write for practitioners who need to make informed decisions about methods and tools.
                    """,
                    expected_structure={
                        "main_contribution": "string",
                        "significance": "string",
                        "practical_impact": "string",
                        "surprising_insight": "string",
                        "problem_solved": "string",
                        "audience_hook": "string",
                        "field_advancement": "string"
                    },
                    confidence_calculation={
                        "method": "content_completeness",
                        "required_fields": ["main_contribution", "significance", "practical_impact"],
                        "min_completeness": 0.7
                    },
                    validation_rules=[
                        "main_contribution must not be empty",
                        "significance must not be empty",
                        "practical_impact must not be empty"
                    ],
                    minimum_confidence=0.6
                )
            ],
            quality_thresholds={
                "auto_approve": 0.75,
                "manual_review": 0.5,
                "auto_reject": 0.3
            },
            description="Extracts benchmark results, performance comparisons, and evaluation metrics"
        )
    
    def _create_tutorial_rubric(self) -> AnalysisRubric:
        """Create default rubric for tutorial/methodology papers."""
        return AnalysisRubric(
            id="tutorial_default",
            name="Tutorial Methodology Analysis",
            version="1.0",
            paper_types=[PaperType.TUTORIAL_METHODOLOGY],
            domains=["general"],
            extraction_rules=[
                ExtractionRule(
                    insight_type=InsightType.METHODOLOGY,
                    prompt="""
                    Extract the tutorial content, step-by-step methodology, and learning objectives.
                    Extract:
                    - Learning objectives and target audience
                    - Step-by-step methodology or tutorial steps
                    - Prerequisites and required knowledge
                    - Practical examples and use cases
                    - Tools and resources mentioned
                    - Expected outcomes and skills gained
                    
                    Focus on educational content and practical implementation guidance.
                    """,
                    expected_structure={
                        "learning_objectives": ["string"],
                        "target_audience": "string",
                        "methodology_steps": [{"step": "string", "description": "string", "example": "string"}],
                        "prerequisites": ["string"],
                        "tools_resources": ["string"],
                        "use_cases": ["string"],
                        "expected_outcomes": ["string"]
                    },
                    confidence_calculation={
                        "method": "tutorial_completeness",
                        "required_fields": ["learning_objectives", "methodology_steps", "expected_outcomes"],
                        "min_completeness": 0.7
                    },
                    validation_rules=[
                        "learning_objectives must have at least 1 items",
                        "methodology_steps must have at least 2 items",
                        "expected_outcomes must have at least 1 items"
                    ],
                    minimum_confidence=0.6
                ),
                ExtractionRule(
                    insight_type=InsightType.KEY_FINDING,
                    prompt="""
                    Extract the key finding and main value from this tutorial/methodology paper for content generation.
                    Focus on what makes this tutorial significant and attention-worthy:
                    - The most important skill or capability this teaches
                    - Why this approach is better than existing methods
                    - What practical problem this solves for practitioners
                    - The "aha moment" or key insight that makes this valuable
                    - How this empowers people to do something they couldn't before
                    
                    Write for learners and practitioners who want to improve their skills and capabilities.
                    """,
                    expected_structure={
                        "main_contribution": "string",
                        "significance": "string",
                        "practical_impact": "string",
                        "surprising_insight": "string",
                        "problem_solved": "string",
                        "audience_hook": "string",
                        "field_advancement": "string"
                    },
                    confidence_calculation={
                        "method": "content_completeness",
                        "required_fields": ["main_contribution", "significance", "practical_impact"],
                        "min_completeness": 0.7
                    },
                    validation_rules=[
                        "main_contribution must not be empty",
                        "significance must not be empty",
                        "practical_impact must not be empty"
                    ],
                    minimum_confidence=0.6
                )
            ],
            quality_thresholds={
                "auto_approve": 0.8,
                "manual_review": 0.6,
                "auto_reject": 0.4
            },
            description="Extracts tutorial methodology, learning objectives, and practical guidance"
        )
    
    def load_rubric(self, rubric_id: str) -> Optional[AnalysisRubric]:
        """Load a rubric by ID."""
        if rubric_id in self._loaded_rubrics:
            return self._loaded_rubrics[rubric_id]
        
        rubric_file = self.rubrics_dir / f"{rubric_id}.yaml"
        if not rubric_file.exists():
            logger.error(f"Rubric file not found: {rubric_file}")
            return None
        
        try:
            with open(rubric_file, 'r') as f:
                data = yaml.safe_load(f)
            
            rubric = self._parse_rubric_data(data)
            self._loaded_rubrics[rubric_id] = rubric
            logger.info(f"Loaded rubric: {rubric.name}")
            return rubric
            
        except Exception as e:
            logger.error(f"Failed to load rubric {rubric_id}: {e}")
            return None
    
    def save_rubric(self, rubric: AnalysisRubric) -> bool:
        """Save a rubric to file."""
        try:
            rubric_file = self.rubrics_dir / f"{rubric.id}.yaml"
            data = self._rubric_to_dict(rubric)
            
            with open(rubric_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, indent=2)
            
            self._loaded_rubrics[rubric.id] = rubric
            logger.info(f"Saved rubric: {rubric.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save rubric {rubric.id}: {e}")
            return False
    
    def list_available_rubrics(self) -> List[str]:
        """List all available rubric IDs."""
        rubric_files = list(self.rubrics_dir.glob("*.yaml"))
        return [f.stem for f in rubric_files]
    
    def get_rubric_for_paper_type(self, paper_type: PaperType) -> Optional[AnalysisRubric]:
        """Get the best rubric for a given paper type."""
        available_rubrics = self.list_available_rubrics()
        
        for rubric_id in available_rubrics:
            rubric = self.load_rubric(rubric_id)
            if rubric and paper_type in rubric.paper_types:
                return rubric
        
        # Fallback to general rubric
        return self.load_rubric("empirical_default")
    
    def _parse_rubric_data(self, data: Dict[str, Any]) -> AnalysisRubric:
        """Parse rubric data from dictionary."""
        extraction_rules = []
        for rule_data in data.get('extraction_rules', []):
            rule = ExtractionRule(
                insight_type=InsightType(rule_data['insight_type']),
                prompt=rule_data['prompt'],
                expected_structure=rule_data['expected_structure'],
                confidence_calculation=rule_data['confidence_calculation'],
                validation_rules=rule_data['validation_rules'],
                minimum_confidence=rule_data.get('minimum_confidence', 0.5)
            )
            extraction_rules.append(rule)
        
        return AnalysisRubric(
            id=data['id'],
            name=data['name'],
            version=data['version'],
            paper_types=[PaperType(pt) for pt in data['paper_types']],
            domains=data['domains'],
            extraction_rules=extraction_rules,
            quality_thresholds=data['quality_thresholds'],
            created_at=data.get('created_at'),
            description=data.get('description')
        )
    
    def _rubric_to_dict(self, rubric: AnalysisRubric) -> Dict[str, Any]:
        """Convert rubric to dictionary for serialization."""
        return {
            'id': rubric.id,
            'name': rubric.name,
            'version': rubric.version,
            'paper_types': [pt.value for pt in rubric.paper_types],
            'domains': rubric.domains,
            'extraction_rules': [
                {
                    'insight_type': rule.insight_type.value,
                    'prompt': rule.prompt,
                    'expected_structure': rule.expected_structure,
                    'confidence_calculation': rule.confidence_calculation,
                    'validation_rules': rule.validation_rules,
                    'minimum_confidence': rule.minimum_confidence
                }
                for rule in rubric.extraction_rules
            ],
            'quality_thresholds': rubric.quality_thresholds,
            'created_at': rubric.created_at,
            'description': rubric.description
        }