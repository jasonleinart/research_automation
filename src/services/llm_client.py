"""
LLM client for insight extraction using OpenAI API.
"""

import json
import logging
from typing import Dict, Any, Optional, List
import asyncio

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class MockLLMClient:
    """Mock LLM client for testing without API keys."""
    
    def __init__(self):
        self.model = "gpt-4"
        self.max_tokens = 2000
        self.temperature = 0.1
    
    async def extract_insights(self, prompt: str, text: str, expected_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Mock insight extraction that returns structured data based on text analysis."""
        try:
            # Simulate processing delay
            await asyncio.sleep(0.1)
            
            # Mock extraction based on text content and expected structure
            result = self._mock_extraction(text, expected_structure)
            
            logger.info(f"Mock LLM extraction completed with {len(result)} fields")
            return result
            
        except Exception as e:
            logger.error(f"Mock LLM extraction failed: {e}")
            return {}
    
    def _mock_extraction(self, text: str, expected_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock structured data based on text analysis."""
        text_lower = text.lower()
        result = {}
        
        for field, field_type in expected_structure.items():
            if field_type == "string":
                result[field] = self._extract_string_field(field, text_lower)
            elif isinstance(field_type, list) and field_type == ["string"]:
                result[field] = self._extract_string_list_field(field, text_lower)
            elif isinstance(field_type, list) and isinstance(field_type[0], dict):
                result[field] = self._extract_object_list_field(field, text_lower, field_type[0])
            else:
                result[field] = f"Mock {field} extracted from text"
        
        return result
    
    def _extract_string_field(self, field: str, text: str) -> str:
        """Extract a string field based on field name and text content."""
        field_lower = field.lower()
        
        # Framework name extraction
        if "name" in field_lower:
            if "transformer" in text:
                return "Transformer Architecture"
            elif "bert" in text:
                return "BERT Model"
            elif "framework" in text:
                return "Novel AI Framework"
            else:
                return "Extracted Framework Name"
        
        # Core concept extraction
        elif "concept" in field_lower or "approach" in field_lower:
            if "attention" in text:
                return "Attention-based mechanism for sequence processing"
            elif "multimodal" in text:
                return "Multimodal AI integration approach"
            else:
                return "Core technical concept extracted from paper"
        
        # Architecture extraction
        elif "architecture" in field_lower:
            return "Layered neural network architecture with attention mechanisms"
        
        # Problem domain extraction
        elif "problem" in field_lower or "domain" in field_lower:
            if "nlp" in text or "language" in text:
                return "Natural Language Processing"
            elif "vision" in text or "image" in text:
                return "Computer Vision"
            else:
                return "Machine Learning Applications"
        
        # Default extraction
        else:
            return f"Mock {field} content based on text analysis"
    
    def _extract_string_list_field(self, field: str, text: str) -> List[str]:
        """Extract a list of strings based on field name and text content."""
        field_lower = field.lower()
        
        if "component" in field_lower:
            return [
                "Encoder module with self-attention",
                "Decoder module with cross-attention", 
                "Position encoding mechanism",
                "Multi-head attention layers"
            ]
        elif "innovation" in field_lower:
            return [
                "Elimination of recurrent connections",
                "Parallelizable attention computation",
                "Improved long-range dependency modeling"
            ]
        elif "trend" in field_lower:
            return [
                "Increased model scale and parameters",
                "Multi-modal integration approaches",
                "Efficient training methodologies"
            ]
        elif "gap" in field_lower:
            return [
                "Limited interpretability of attention patterns",
                "Computational efficiency at scale",
                "Robustness to adversarial inputs"
            ]
        elif "outcome" in field_lower or "result" in field_lower:
            return [
                "Improved performance on benchmark tasks",
                "Successful deployment in production environment",
                "Positive user feedback and adoption"
            ]
        else:
            return [f"Mock {field} item 1", f"Mock {field} item 2", f"Mock {field} item 3"]
    
    def _extract_object_list_field(self, field: str, text: str, obj_structure: Dict[str, str]) -> List[Dict[str, str]]:
        """Extract a list of objects based on field name and structure."""
        if "metric" in field.lower():
            return [
                {"name": "BLEU Score", "value": "34.2", "unit": "points"},
                {"name": "Accuracy", "value": "92.5", "unit": "percent"},
                {"name": "F1 Score", "value": "0.89", "unit": "ratio"}
            ]
        elif "concept" in field.lower():
            return [
                {"concept": "Attention Mechanism", "definition": "Method for focusing on relevant parts of input"},
                {"concept": "Self-Attention", "definition": "Attention applied within a single sequence"},
                {"concept": "Multi-Head Attention", "definition": "Parallel attention computations with different learned projections"}
            ]
        elif "step" in field.lower():
            return [
                {"step": "Input Processing", "description": "Tokenize and embed input sequences"},
                {"step": "Attention Computation", "description": "Calculate attention weights and apply to values"},
                {"step": "Output Generation", "description": "Generate final predictions from attended representations"}
            ]
        else:
            return [{"field": f"Mock {field} object", "value": "extracted content"}]


class OpenAILLMClient:
    """Real OpenAI LLM client (requires API key)."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.model = "gpt-4o-mini"  # More cost-effective model
        self.max_tokens = 2000
        self.temperature = 0.1
        
        if not api_key or not OPENAI_AVAILABLE:
            if not api_key:
                logger.warning("No OpenAI API key provided, using mock client")
            else:
                logger.warning("OpenAI package not available, using mock client")
            self._use_mock = True
            self._mock_client = MockLLMClient()
        else:
            self._use_mock = False
            self.client = openai.OpenAI(api_key=api_key)
    
    async def extract_insights(self, prompt: str, text: str, expected_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Extract insights using OpenAI API or mock client."""
        if self._use_mock:
            return await self._mock_client.extract_insights(prompt, text, expected_structure)
        
        try:
            # Create the full prompt with structure requirements
            full_prompt = f"""
{prompt}

Please analyze the following research paper content and extract information according to the specified structure.

IMPORTANT: Return ONLY a valid JSON object that matches this exact structure:
{json.dumps(expected_structure, indent=2)}

Research Paper Content:
{text}

Return only the JSON object, no additional text or explanation.
"""
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a research paper analysis expert. Extract structured information from academic papers and return only valid JSON."},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            content = response.choices[0].message.content
            result = json.loads(content)
            
            logger.info(f"OpenAI extraction completed with {len(result)} fields")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {e}")
            logger.info("Falling back to mock extraction")
            return await self._mock_client.extract_insights(prompt, text, expected_structure)
        except Exception as e:
            logger.error(f"OpenAI extraction failed: {e}")
            logger.info("Falling back to mock extraction")
            return await self._mock_client.extract_insights(prompt, text, expected_structure)


def get_llm_client(api_key: Optional[str] = None) -> OpenAILLMClient:
    """Get LLM client instance."""
    return OpenAILLMClient(api_key)