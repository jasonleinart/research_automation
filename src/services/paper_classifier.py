"""
Paper classification service for determining paper types and attributes.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter

from ..models.paper import Paper
from ..models.enums import PaperType, EvidenceStrength, PracticalApplicability

logger = logging.getLogger(__name__)


class PaperClassifier:
    """Service for classifying papers by type and attributes."""
    
    def __init__(self):
        self.classification_rules = self._load_classification_rules()
    
    def _load_classification_rules(self) -> Dict[str, Any]:
        """Load classification rules and patterns."""
        return {
            'paper_types': {
                PaperType.CONCEPTUAL_FRAMEWORK: {
                    'title_patterns': [
                        r'\b(framework|architecture|model|approach|method)\b',
                        r'\b(introducing|proposing|novel|new)\b.*\b(framework|architecture|model)\b',
                        r'\b(design|development)\b.*\b(framework|system)\b'
                    ],
                    'abstract_patterns': [
                        r'\b(we propose|we introduce|we present)\b.*\b(framework|architecture|model|approach)\b',
                        r'\b(novel|new)\b.*\b(framework|architecture|model|method)\b',
                        r'\b(this paper (proposes|introduces|presents))\b',
                        r'\b(our (framework|approach|method|model))\b'
                    ],
                    'content_indicators': [
                        'framework', 'architecture', 'model', 'approach', 'methodology',
                        'design', 'propose', 'introduce', 'novel', 'new'
                    ],
                    'weight': 1.0
                },
                
                PaperType.SURVEY_REVIEW: {
                    'title_patterns': [
                        r'\b(survey|review|overview|comprehensive)\b',
                        r'\b(state.of.the.art|systematic review)\b',
                        r'\b(recent (advances|developments|progress))\b'
                    ],
                    'abstract_patterns': [
                        r'\b(this (survey|review|paper) (provides|presents|offers))\b',
                        r'\b(comprehensive (survey|review|overview))\b',
                        r'\b(we (survey|review|examine|analyze))\b.*\b(literature|field|domain)\b',
                        r'\b(state.of.the.art|recent (advances|developments|progress))\b'
                    ],
                    'content_indicators': [
                        'survey', 'review', 'overview', 'comprehensive', 'literature',
                        'state-of-the-art', 'recent advances', 'systematic'
                    ],
                    'weight': 1.0
                },
                
                PaperType.EMPIRICAL_STUDY: {
                    'title_patterns': [
                        r'\b(empirical|experimental|study|analysis|investigation)\b',
                        r'\b(evaluation|assessment|comparison)\b.*\b(study|analysis)\b'
                    ],
                    'abstract_patterns': [
                        r'\b(we (conduct|perform|carry out))\b.*\b(experiments|study|evaluation)\b',
                        r'\b(empirical (study|analysis|evaluation|investigation))\b',
                        r'\b(experimental (results|evaluation|study))\b',
                        r'\b(we (evaluate|analyze|investigate|examine))\b'
                    ],
                    'content_indicators': [
                        'empirical', 'experimental', 'experiments', 'evaluation',
                        'study', 'analysis', 'investigation', 'results'
                    ],
                    'weight': 1.0
                },
                
                PaperType.CASE_STUDY: {
                    'title_patterns': [
                        r'\b(case study|application|implementation)\b',
                        r'\b(applying|using)\b.*\b(to|for|in)\b',
                        r'\b(real.world|practical)\b.*\b(application|implementation)\b'
                    ],
                    'abstract_patterns': [
                        r'\b(case study|real.world application)\b',
                        r'\b(we (apply|implement|deploy))\b.*\b(to|for|in)\b',
                        r'\b(practical (application|implementation|deployment))\b',
                        r'\b(demonstrate|show|illustrate)\b.*\b(effectiveness|applicability)\b'
                    ],
                    'content_indicators': [
                        'case study', 'application', 'implementation', 'real-world',
                        'practical', 'demonstrate', 'deploy', 'apply'
                    ],
                    'weight': 1.0
                },
                
                PaperType.BENCHMARK_COMPARISON: {
                    'title_patterns': [
                        r'\b(benchmark|comparison|comparative|evaluation)\b',
                        r'\b(comparing|vs|versus)\b',
                        r'\b(performance (comparison|evaluation))\b'
                    ],
                    'abstract_patterns': [
                        r'\b(we (compare|benchmark|evaluate))\b.*\b(against|with|to)\b',
                        r'\b(comparative (study|analysis|evaluation))\b',
                        r'\b(benchmark|performance comparison)\b',
                        r'\b(extensive (comparison|evaluation|experiments))\b'
                    ],
                    'content_indicators': [
                        'benchmark', 'comparison', 'comparative', 'compare',
                        'versus', 'performance', 'evaluation', 'extensive'
                    ],
                    'weight': 1.0
                },
                
                PaperType.POSITION_PAPER: {
                    'title_patterns': [
                        r'\b(position|perspective|opinion|viewpoint)\b',
                        r'\b(towards|rethinking|reconsidering)\b',
                        r'\b(challenges|opportunities|future)\b.*\b(directions|research)\b'
                    ],
                    'abstract_patterns': [
                        r'\b(we (argue|believe|propose|suggest))\b.*\b(that|for)\b',
                        r'\b(this paper (argues|discusses|examines))\b',
                        r'\b(position|perspective|viewpoint)\b',
                        r'\b(challenges|opportunities|future directions)\b'
                    ],
                    'content_indicators': [
                        'position', 'perspective', 'argue', 'believe', 'challenges',
                        'opportunities', 'future', 'directions', 'rethinking'
                    ],
                    'weight': 1.0
                },
                
                PaperType.TUTORIAL_METHODOLOGY: {
                    'title_patterns': [
                        r'\b(tutorial|guide|how.to|methodology)\b',
                        r'\b(step.by.step|practical guide)\b',
                        r'\b(introduction to|primer)\b'
                    ],
                    'abstract_patterns': [
                        r'\b(this (tutorial|guide|paper) (provides|presents|offers))\b',
                        r'\b(step.by.step|practical guide|methodology)\b',
                        r'\b(we (provide|present|offer))\b.*\b(guide|tutorial|methodology)\b',
                        r'\b(introduction to|primer|how to)\b'
                    ],
                    'content_indicators': [
                        'tutorial', 'guide', 'methodology', 'step-by-step',
                        'practical', 'introduction', 'primer', 'how-to'
                    ],
                    'weight': 1.0
                }
            },
            
            'evidence_strength': {
                EvidenceStrength.EXPERIMENTAL: {
                    'patterns': [
                        r'\b(experiments|experimental|empirical)\b',
                        r'\b(results|evaluation|testing|validation)\b',
                        r'\b(dataset|data|benchmark)\b'
                    ],
                    'weight': 1.0
                },
                EvidenceStrength.THEORETICAL: {
                    'patterns': [
                        r'\b(theoretical|theory|mathematical|formal)\b',
                        r'\b(proof|theorem|analysis|derivation)\b',
                        r'\b(model|framework|formulation)\b'
                    ],
                    'weight': 1.0
                },
                EvidenceStrength.OBSERVATIONAL: {
                    'patterns': [
                        r'\b(observational|observation|study|analysis)\b',
                        r'\b(survey|investigation|examination)\b',
                        r'\b(trends|patterns|phenomena)\b'
                    ],
                    'weight': 1.0
                },
                EvidenceStrength.ANECDOTAL: {
                    'patterns': [
                        r'\b(anecdotal|preliminary|initial|exploratory)\b',
                        r'\b(case study|example|illustration)\b',
                        r'\b(discussion|opinion|perspective)\b'
                    ],
                    'weight': 1.0
                }
            },
            
            'practical_applicability': {
                PracticalApplicability.HIGH: {
                    'patterns': [
                        r'\b(practical|real.world|industry|production)\b',
                        r'\b(implementation|deployment|application)\b',
                        r'\b(scalable|efficient|effective)\b'
                    ],
                    'weight': 1.0
                },
                PracticalApplicability.MEDIUM: {
                    'patterns': [
                        r'\b(prototype|proof.of.concept|demonstration)\b',
                        r'\b(feasibility|potential|promising)\b',
                        r'\b(experimental|validation)\b'
                    ],
                    'weight': 1.0
                },
                PracticalApplicability.LOW: {
                    'patterns': [
                        r'\b(preliminary|initial|exploratory)\b',
                        r'\b(conceptual|abstract|theoretical)\b',
                        r'\b(future work|further research)\b'
                    ],
                    'weight': 1.0
                },
                PracticalApplicability.THEORETICAL_ONLY: {
                    'patterns': [
                        r'\b(theoretical|mathematical|formal)\b',
                        r'\b(analysis|proof|derivation)\b',
                        r'\b(abstract|conceptual)\b'
                    ],
                    'weight': 1.0
                }
            }
        }
    
    def classify_paper(self, paper: Paper) -> Dict[str, Any]:
        """Classify a paper and return classification results with confidence scores."""
        try:
            # Combine text for analysis
            text_content = self._prepare_text_for_analysis(paper)
            
            # Classify paper type
            paper_type, type_confidence = self._classify_paper_type(text_content)
            
            # Classify evidence strength
            evidence_strength, evidence_confidence = self._classify_evidence_strength(text_content)
            
            # Classify practical applicability
            applicability, applicability_confidence = self._classify_practical_applicability(text_content)
            
            # Calculate overall confidence
            overall_confidence = (type_confidence + evidence_confidence + applicability_confidence) / 3
            
            classification_result = {
                'paper_type': paper_type,
                'evidence_strength': evidence_strength,
                'practical_applicability': applicability,
                'type_confidence': type_confidence,
                'evidence_confidence': evidence_confidence,
                'applicability_confidence': applicability_confidence,
                'overall_confidence': overall_confidence,
                'classification_details': {
                    'text_length': len(text_content),
                    'has_abstract': bool(paper.abstract),
                    'arxiv_categories': paper.categories or []
                }
            }
            
            logger.info(f"Classified paper '{paper.title[:50]}...' as {paper_type} (confidence: {overall_confidence:.2f})")
            return classification_result
            
        except Exception as e:
            logger.error(f"Failed to classify paper '{paper.title}': {e}")
            return self._get_default_classification()
    
    def _prepare_text_for_analysis(self, paper: Paper) -> str:
        """Prepare text content for classification analysis."""
        text_parts = []
        
        # Title (weighted more heavily)
        if paper.title:
            text_parts.extend([paper.title] * 3)  # Triple weight for title
        
        # Abstract (weighted heavily)
        if paper.abstract:
            text_parts.extend([paper.abstract] * 2)  # Double weight for abstract
        
        # Categories as text
        if paper.categories:
            categories_text = " ".join(paper.categories)
            text_parts.append(categories_text)
        
        # Full text analysis (enhanced)
        if paper.full_text:
            full_text = paper.full_text.lower()
            
            # Use more comprehensive full text analysis
            # Include introduction, conclusion, and key sections
            sections_to_analyze = []
            
            # Introduction section (first 20% of text)
            intro_length = int(len(full_text) * 0.2)
            sections_to_analyze.append(full_text[:intro_length])
            
            # Conclusion section (last 15% of text)
            conclusion_length = int(len(full_text) * 0.15)
            sections_to_analyze.append(full_text[-conclusion_length:])
            
            # Middle sections (sample from 30-70% of text)
            middle_start = int(len(full_text) * 0.3)
            middle_end = int(len(full_text) * 0.7)
            middle_sample = full_text[middle_start:middle_end]
            
            # Sample from middle (every 10th character to get representative sample)
            middle_sample = middle_sample[::10]
            sections_to_analyze.append(middle_sample)
            
            # Add all sections to text parts
            for section in sections_to_analyze:
                text_parts.append(section)
        else:
            # If no full text, use more weight for title and abstract
            if paper.title:
                text_parts.extend([paper.title] * 2)  # Additional weight
            if paper.abstract:
                text_parts.extend([paper.abstract] * 1.5)  # Additional weight
        
        return " ".join(text_parts).lower()
    
    def _classify_paper_type(self, text: str) -> Tuple[PaperType, float]:
        """Classify paper type based on text content."""
        type_scores = {}
        
        for paper_type, rules in self.classification_rules['paper_types'].items():
            score = 0.0
            matches = 0
            detailed_matches = {
                'title_patterns': 0,
                'abstract_patterns': 0,
                'content_indicators': 0
            }
            
            # Check title patterns
            for pattern in rules['title_patterns']:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 3.0  # Increased weight for title patterns
                    matches += 1
                    detailed_matches['title_patterns'] += 1
            
            # Check abstract patterns
            for pattern in rules['abstract_patterns']:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 2.0  # Increased weight for abstract patterns
                    matches += 1
                    detailed_matches['abstract_patterns'] += 1
            
            # Check content indicators (enhanced for full text)
            for indicator in rules['content_indicators']:
                count = len(re.findall(r'\b' + re.escape(indicator) + r'\b', text, re.IGNORECASE))
                # Higher weight for content indicators when full text is available
                indicator_weight = 1.0 if len(text) > 10000 else 0.5  # Full text gets higher weight
                score += count * indicator_weight
                if count > 0:
                    matches += 1
                    detailed_matches['content_indicators'] += count
            
            # Bonus for having multiple types of matches
            if detailed_matches['title_patterns'] > 0 and detailed_matches['abstract_patterns'] > 0:
                score += 1.0  # Bonus for title + abstract match
            if detailed_matches['content_indicators'] > 5:
                score += 1.0  # Bonus for high content indicator frequency
            
            # Normalize score by number of rules
            total_rules = len(rules['title_patterns']) + len(rules['abstract_patterns']) + len(rules['content_indicators'])
            normalized_score = score / total_rules if total_rules > 0 else 0
            
            # Adjust confidence based on text length (full text analysis gets higher confidence)
            text_length_factor = min(len(text) / 5000, 1.5)  # Cap at 1.5x for very long texts
            adjusted_confidence = min(normalized_score * text_length_factor, 1.0)
            
            type_scores[paper_type] = {
                'score': normalized_score,
                'matches': matches,
                'confidence': adjusted_confidence,
                'detailed_matches': detailed_matches
            }
        
        # Find best match
        if not type_scores:
            return PaperType.EMPIRICAL_STUDY, 0.1  # Default fallback
        
        best_type = max(type_scores.keys(), key=lambda t: type_scores[t]['score'])
        confidence = type_scores[best_type]['confidence']
        
        # Minimum confidence threshold
        if confidence < 0.1:
            return PaperType.EMPIRICAL_STUDY, 0.1
        
        return best_type, confidence
    
    def _classify_evidence_strength(self, text: str) -> Tuple[EvidenceStrength, float]:
        """Classify evidence strength based on text content."""
        strength_scores = {}
        
        for strength, rules in self.classification_rules['evidence_strength'].items():
            score = 0.0
            
            for pattern in rules['patterns']:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches * rules['weight']
            
            strength_scores[strength] = score
        
        if not strength_scores or max(strength_scores.values()) == 0:
            return EvidenceStrength.THEORETICAL, 0.1
        
        best_strength = max(strength_scores.keys(), key=lambda s: strength_scores[s])
        max_score = strength_scores[best_strength]
        confidence = min(max_score / 5.0, 1.0)  # Normalize to 0-1
        
        return best_strength, max(confidence, 0.1)
    
    def _classify_practical_applicability(self, text: str) -> Tuple[PracticalApplicability, float]:
        """Classify practical applicability based on text content."""
        applicability_scores = {}
        
        for applicability, rules in self.classification_rules['practical_applicability'].items():
            score = 0.0
            
            for pattern in rules['patterns']:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches * rules['weight']
            
            applicability_scores[applicability] = score
        
        if not applicability_scores or max(applicability_scores.values()) == 0:
            return PracticalApplicability.MEDIUM, 0.1
        
        best_applicability = max(applicability_scores.keys(), key=lambda a: applicability_scores[a])
        max_score = applicability_scores[best_applicability]
        confidence = min(max_score / 3.0, 1.0)  # Normalize to 0-1
        
        return best_applicability, max(confidence, 0.1)
    
    def _get_default_classification(self) -> Dict[str, Any]:
        """Return default classification when analysis fails."""
        return {
            'paper_type': PaperType.EMPIRICAL_STUDY,
            'evidence_strength': EvidenceStrength.THEORETICAL,
            'practical_applicability': PracticalApplicability.MEDIUM,
            'type_confidence': 0.1,
            'evidence_confidence': 0.1,
            'applicability_confidence': 0.1,
            'overall_confidence': 0.1,
            'classification_details': {
                'text_length': 0,
                'has_abstract': False,
                'arxiv_categories': []
            }
        }
    
    def get_classification_explanation(self, classification: Dict[str, Any]) -> str:
        """Generate human-readable explanation of classification."""
        paper_type = classification['paper_type']
        confidence = classification['overall_confidence']
        
        explanation = f"Classified as {paper_type.value.replace('_', ' ').title()} "
        explanation += f"with {confidence:.1%} confidence.\n"
        
        if confidence > 0.8:
            explanation += "High confidence classification based on strong textual indicators."
        elif confidence > 0.5:
            explanation += "Medium confidence classification based on moderate textual indicators."
        else:
            explanation += "Low confidence classification - may need manual review."
        
        return explanation

    def get_detailed_classification_analysis(self, paper: Paper) -> Dict[str, Any]:
        """Get detailed classification analysis for debugging and understanding."""
        text = self._prepare_text_for_analysis(paper)
        type_scores = {}
        
        for paper_type, rules in self.classification_rules['paper_types'].items():
            score = 0.0
            matches = 0
            detailed_matches = {
                'title_patterns': [],
                'abstract_patterns': [],
                'content_indicators': {}
            }
            
            # Check title patterns
            for pattern in rules['title_patterns']:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 3.0
                    matches += 1
                    detailed_matches['title_patterns'].append(pattern)
            
            # Check abstract patterns
            for pattern in rules['abstract_patterns']:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 2.0
                    matches += 1
                    detailed_matches['abstract_patterns'].append(pattern)
            
            # Check content indicators
            for indicator in rules['content_indicators']:
                count = len(re.findall(r'\b' + re.escape(indicator) + r'\b', text, re.IGNORECASE))
                indicator_weight = 1.0 if len(text) > 10000 else 0.5
                score += count * indicator_weight
                if count > 0:
                    matches += 1
                    detailed_matches['content_indicators'][indicator] = count
            
            # Bonus calculations
            bonuses = []
            if detailed_matches['title_patterns'] and detailed_matches['abstract_patterns']:
                score += 1.0
                bonuses.append("Title + Abstract match")
            if sum(detailed_matches['content_indicators'].values()) > 5:
                score += 1.0
                bonuses.append("High content indicator frequency")
            
            # Normalize score
            total_rules = len(rules['title_patterns']) + len(rules['abstract_patterns']) + len(rules['content_indicators'])
            normalized_score = score / total_rules if total_rules > 0 else 0
            
            # Adjust confidence
            text_length_factor = min(len(text) / 5000, 1.5)
            adjusted_confidence = min(normalized_score * text_length_factor, 1.0)
            
            type_scores[paper_type] = {
                'score': normalized_score,
                'confidence': adjusted_confidence,
                'matches': matches,
                'detailed_matches': detailed_matches,
                'bonuses': bonuses,
                'text_length': len(text),
                'text_length_factor': text_length_factor
            }
        
        # Sort by confidence
        sorted_scores = sorted(type_scores.items(), key=lambda x: x[1]['confidence'], reverse=True)
        
        return {
            'paper_title': paper.title,
            'has_full_text': bool(paper.full_text),
            'text_length': len(text),
            'classification_scores': dict(sorted_scores),
            'recommended_type': sorted_scores[0][0] if sorted_scores else None,
            'recommended_confidence': sorted_scores[0][1]['confidence'] if sorted_scores else 0.0
        }