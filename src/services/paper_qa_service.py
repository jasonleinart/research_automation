#!/usr/bin/env python3
"""
Paper Q&A Service - Grounded conversational Q&A system for research papers.

This service provides accurate, grounded responses to questions about specific papers,
with built-in safeguards against hallucination and emphasis on factual accuracy.
"""

import logging
import os
import re
from typing import Dict, Any, Optional, List
from uuid import UUID
from dataclasses import dataclass

from .context_loader import ContextLoader, PaperContext
from .llm_client import get_llm_client
from ..models.paper import Paper

logger = logging.getLogger(__name__)


@dataclass
class QAResponse:
    """Structured response from the Q&A system."""
    answer: str
    confidence: float  # 0.0 to 1.0
    grounded: bool  # Whether response is grounded in paper content
    sources: List[str]  # Specific sections/content referenced
    limitations: Optional[str] = None  # Any limitations or caveats


class PaperQAService:
    """Grounded Q&A service for research papers with hallucination prevention."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.llm_client = get_llm_client(api_key)
        self.context_loader = ContextLoader()
        
        # Question type patterns for specialized handling
        self.question_patterns = {
            'summary': ['what is', 'summarize', 'about', 'overview'],
            'methodology': ['how', 'method', 'approach', 'technique'],
            'results': ['result', 'finding', 'outcome', 'performance'],
            'authors': ['who', 'author', 'researcher'],
            'comparison': ['compare', 'difference', 'versus', 'vs'],
            'technical': ['algorithm', 'model', 'architecture', 'implementation']
        }
        
        logger.info("PaperQAService initialized")
    
    async def answer_question(self, paper_id: UUID, question: str) -> QAResponse:
        """Answer a question about a specific paper with grounding."""
        try:
            # Load comprehensive paper context
            paper_context = await self.context_loader.load_paper_context(paper_id)
            
            # Classify question type for specialized handling
            question_type = self._classify_question(question)
            
            # Create grounded prompt based on question type
            prompt = self._create_grounded_prompt(paper_context, question, question_type)
            
            # Generate grounded response
            response = await self._generate_grounded_response(prompt, paper_context)
            
            # Validate and structure the response
            qa_response = self._validate_and_structure_response(
                response, paper_context, question
            )
            
            return qa_response
            
        except Exception as e:
            logger.error(f"Error answering question about paper {paper_id}: {e}")
            return QAResponse(
                answer="I'm sorry, I encountered an error while processing your question. Please try again.",
                confidence=0.0,
                grounded=False,
                sources=[],
                limitations="System error occurred"
            )
    
    def _classify_question(self, question: str) -> str:
        """Classify the type of question to provide specialized handling."""
        question_lower = question.lower()
        
        for question_type, patterns in self.question_patterns.items():
            if any(pattern in question_lower for pattern in patterns):
                return question_type
        
        return 'general'
    
    def _create_grounded_prompt(self, context: PaperContext, question: str, question_type: str) -> str:
        """Create a specialized prompt for grounded Q&A based on question type."""
        
        # Base grounding instructions
        base_instructions = """You are a research assistant helping users understand academic papers. 

CRITICAL RESPONSE RULES:
1. ONLY use information explicitly provided in the paper content below
2. Give direct, specific answers - don't just reference sections
3. Focus on the actual content and findings, not where they're located
4. If information is not in the paper, clearly state "This information is not provided in the paper"
5. Be precise and factual, but prioritize being helpful and specific
6. Avoid unnecessary section references unless specifically asked about paper structure

"""
        
        # Question-type specific instructions
        type_instructions = {
            'summary': "Provide a clear, comprehensive summary of the main points, contributions, and findings. Focus on what the paper actually says, not where it says it.",
            'methodology': "Explain the specific methods, approaches, and techniques used. Give concrete details about how things were done.",
            'results': "Present the actual findings, outcomes, and results. Include specific data, conclusions, and implications mentioned in the paper.",
            'authors': "List the authors and any relevant information about them mentioned in the paper.",
            'comparison': "Explain the specific comparisons, differences, or relationships discussed in the paper.",
            'technical': "Provide detailed technical explanations based on the paper's content. Focus on the actual mechanisms, processes, or concepts.",
            'general': "Give a direct, helpful answer based on the paper's content. Focus on being informative and specific."
        }
        
        instruction = type_instructions.get(question_type, type_instructions['general'])
        
        # Construct the full prompt
        prompt = f"""{base_instructions}

SPECIFIC INSTRUCTION: {instruction}

PAPER INFORMATION:
{context.formatted_content}

USER QUESTION: {question}

RESPONSE FORMAT:
- Give a direct, helpful answer based on the paper's content
- Focus on the actual information and findings, not paper structure
- Be specific and detailed when the paper provides specific details
- If the paper doesn't contain the requested information, say so explicitly
- Avoid unnecessary section references unless they add value

ANSWER:"""
        
        return prompt
    
    async def _generate_grounded_response(self, prompt: str, context: PaperContext) -> str:
        """Generate a response using the LLM with grounding safeguards."""
        try:
            messages = [
                {
                    "role": "system", 
                    "content": "You are a helpful research assistant. Provide clear, direct answers based only on the paper content provided. Focus on being informative and specific rather than overly cautious. Only use information from the paper, but present it in a natural, helpful way."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
            
            response = await self.llm_client.generate_response(
                messages=messages,
                model="gpt-4o-mini"  # Use more capable model for accuracy
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating grounded response: {e}")
            raise
    
    def _validate_and_structure_response(
        self, 
        response: str, 
        context: PaperContext, 
        question: str
    ) -> QAResponse:
        """Validate response grounding and structure it appropriately."""
        
        # Check for grounding indicators
        grounding_indicators = [
            "according to the paper",
            "the paper states",
            "the authors describe",
            "the paper shows",
            "the research found",
            "the study indicates",
            "the findings suggest",
            "the paper demonstrates"
        ]
        
        uncertainty_indicators = [
            "not provided in the paper",
            "not mentioned",
            "unclear from the paper",
            "not explicitly stated",
            "information is not available"
        ]
        
        # Assess grounding
        has_grounding_language = any(indicator in response.lower() for indicator in grounding_indicators)
        acknowledges_limitations = any(indicator in response.lower() for indicator in uncertainty_indicators)
        
        # Extract potential sources/references
        sources = self._extract_sources(response, context)
        
        # Calculate confidence based on various factors
        confidence = self._calculate_confidence(
            response, has_grounding_language, acknowledges_limitations, sources
        )
        
        # Determine if response is properly grounded
        is_grounded = (
            has_grounding_language or 
            acknowledges_limitations or 
            len(sources) > 0
        )
        
        # Extract limitations if mentioned
        limitations = None
        if acknowledges_limitations:
            limitations = "Some information may not be available in the paper"
        
        return QAResponse(
            answer=response.strip(),
            confidence=confidence,
            grounded=is_grounded,
            sources=sources,
            limitations=limitations
        )
    
    def _extract_sources(self, response: str, context: PaperContext) -> List[str]:
        """Extract references to content sources from the response."""
        sources = []
        
        # Look for content-based indicators rather than section references
        content_indicators = [
            "the paper",
            "the research",
            "the study",
            "the findings",
            "the authors",
            "the data",
            "the results"
        ]
        
        for indicator in content_indicators:
            if indicator in response.lower():
                sources.append("paper_content")
                break
        
        # Look for specific data or findings mentioned
        if any(word in response.lower() for word in ["data", "results", "findings", "evidence"]):
            sources.append("research_findings")
        
        # Remove duplicates and return
        return list(set(sources))
    
    def _calculate_confidence(
        self, 
        response: str, 
        has_grounding: bool, 
        acknowledges_limits: bool, 
        sources: List[str]
    ) -> float:
        """Calculate confidence score for the response."""
        confidence = 0.5  # Base confidence
        
        # Increase confidence for grounding indicators
        if has_grounding:
            confidence += 0.2
        
        # Increase confidence for acknowledging limitations (shows awareness)
        if acknowledges_limits:
            confidence += 0.1
        
        # Increase confidence for specific sources
        confidence += min(len(sources) * 0.1, 0.2)
        
        # Decrease confidence for very short responses (likely incomplete)
        if len(response) < 50:
            confidence -= 0.2
        
        # Decrease confidence for very long responses (might be hallucinating)
        if len(response) > 1000:
            confidence -= 0.1
        
        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, confidence))
    
    async def ask_followup(
        self, 
        paper_id: UUID, 
        original_question: str, 
        original_response: QAResponse, 
        followup_question: str
    ) -> QAResponse:
        """Handle follow-up questions with context from previous Q&A."""
        try:
            # Load paper context
            paper_context = await self.context_loader.load_paper_context(paper_id)
            
            # Create context-aware prompt for follow-up
            prompt = f"""You are a research assistant helping users understand academic papers.

PREVIOUS CONVERSATION:
Question: {original_question}
Answer: {original_response.answer}

GROUNDING RULES:
1. ONLY use information from the paper content below
2. Consider the previous conversation context
3. If information is not in the paper, clearly state so
4. Be precise and factual

PAPER INFORMATION:
{paper_context.formatted_content}

FOLLOW-UP QUESTION: {followup_question}

ANSWER:"""
            
            # Generate response
            response = await self._generate_grounded_response(prompt, paper_context)
            
            # Validate and structure
            qa_response = self._validate_and_structure_response(
                response, paper_context, followup_question
            )
            
            return qa_response
            
        except Exception as e:
            logger.error(f"Error handling follow-up question: {e}")
            return QAResponse(
                answer="I'm sorry, I encountered an error processing your follow-up question.",
                confidence=0.0,
                grounded=False,
                sources=[]
            )
    
    def get_question_suggestions(self, paper: Paper) -> List[str]:
        """Generate suggested questions based on paper content."""
        suggestions = [
            "What is this paper about?",
            "What are the main contributions?",
            "What methodology was used?",
            "What were the key results?",
            "Who are the authors?",
        ]
        
        # Add paper-specific suggestions based on type
        if paper.paper_type:
            type_suggestions = {
                'empirical_study': [
                    "What experiments were conducted?",
                    "What datasets were used?",
                    "How was the evaluation performed?"
                ],
                'theoretical_analysis': [
                    "What theoretical framework is proposed?",
                    "What are the key theoretical insights?",
                    "How does this extend existing theory?"
                ],
                'survey': [
                    "What topics are surveyed?",
                    "What are the main categories discussed?",
                    "What gaps are identified?"
                ],
                'position_paper': [
                    "What position is being argued?",
                    "What evidence supports this position?",
                    "What are the implications?"
                ]
            }
            
            if paper.paper_type.value in type_suggestions:
                suggestions.extend(type_suggestions[paper.paper_type.value])
        
        return suggestions[:8]  # Return top 8 suggestions