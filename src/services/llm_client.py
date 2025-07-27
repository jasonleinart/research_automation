"""
LLM client for insight extraction and embeddings using OpenAI API.
"""

import json
import logging
import numpy as np
import os
from typing import Dict, Any, Optional, List, Union
import asyncio

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


# MockLLMClient class completely removed - only real OpenAI LLM is used


class OpenAILLMClient:
    """Real OpenAI LLM client (requires API key)."""
    
    def __init__(self, api_key: Optional[str] = None):
        if not api_key:
            raise ValueError("OpenAI API key is required")
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package is not available")
        
        self.api_key = api_key
        self.model = "gpt-4o-mini"  # More cost-effective model
        self.max_tokens = 2000
        self.temperature = 0.1
        self.client = openai.OpenAI(api_key=api_key)
    
    async def extract_insights(self, prompt: str, text: str, expected_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Extract insights using OpenAI API."""
        try:
            # Create the full prompt with structure requirements
            full_prompt = f"""
{prompt}

Please analyze the following research paper content and extract information according to the specified structure.

CRITICAL: You MUST return a JSON object that EXACTLY matches this structure. Do not add, remove, or rename any fields:
{json.dumps(expected_structure, indent=2)}

Research Paper Content:
{text}

IMPORTANT RULES:
1. Return ONLY the JSON object, no additional text
2. Use EXACTLY the field names shown in the structure above
3. Do not create new fields or rename existing ones
4. If a field cannot be filled, use an empty string ""
5. Ensure all required fields are present

Return only the JSON object:
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
            
            # Validate that the response matches the expected structure
            self._validate_response_structure(result, expected_structure)
            
            logger.info(f"OpenAI extraction completed with {len(result)} fields")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {e}")
            raise
        except Exception as e:
            logger.error(f"OpenAI extraction failed: {e}")
            raise
    
    async def get_embedding(self, text: str, model: str = "text-embedding-3-small") -> List[float]:
        """Generate embeddings for text using OpenAI API."""
        try:
            response = self.client.embeddings.create(
                model=model,
                input=text
            )
            
            embedding = response.data[0].embedding
            logger.info(f"OpenAI embedding generated with {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise
    
    async def get_embeddings_batch(self, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        """Generate embeddings for multiple texts in batch."""
        try:
            response = self.client.embeddings.create(
                model=model,
                input=texts
            )
            
            embeddings = [data.embedding for data in response.data]
            logger.info(f"OpenAI batch embeddings generated for {len(texts)} texts")
            return embeddings
            
        except Exception as e:
            logger.error(f"OpenAI batch embedding generation failed: {e}")
            raise

    def _validate_response_structure(self, result: Dict[str, Any], expected_structure: Dict[str, Any]) -> None:
        """Validate that the LLM response matches the expected structure."""
        try:
            # Check that all expected fields are present
            for field_name, field_type in expected_structure.items():
                if field_name not in result:
                    logger.warning(f"Missing required field: {field_name}")
                    result[field_name] = ""  # Add missing field with empty string
                
                # Validate field type (basic validation)
                if isinstance(field_type, list):
                    if not isinstance(result[field_name], list):
                        logger.warning(f"Field {field_name} should be a list, got {type(result[field_name])}")
                        result[field_name] = []
                elif field_type == str:
                    if not isinstance(result[field_name], str):
                        logger.warning(f"Field {field_name} should be a string, got {type(result[field_name])}")
                        result[field_name] = str(result[field_name]) if result[field_name] is not None else ""
            
            # Remove any extra fields not in expected structure
            extra_fields = [field for field in result.keys() if field not in expected_structure]
            if extra_fields:
                logger.warning(f"Removing extra fields: {extra_fields}")
                for field in extra_fields:
                    del result[field]
                    
        except Exception as e:
            logger.error(f"Structure validation failed: {e}")
            raise
    
    async def generate_response(self, messages: List[Dict[str, str]], model: str = "gpt-4o-mini") -> str:
        """Generate a simple chat response using OpenAI API."""
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise


def get_llm_client(api_key: Optional[str] = None) -> OpenAILLMClient:
    """Get LLM client instance. Requires OpenAI API key."""
    if not api_key:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key is required for LLM client")
    return OpenAILLMClient(api_key)