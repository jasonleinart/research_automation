"""
Tag similarity service using vector embeddings for intelligent tag matching.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from src.services.llm_client import get_llm_client
from src.database.tag_repository import TagRepository
from src.models.tag import Tag, TagCategory

logger = logging.getLogger(__name__)


class TagSimilarityService:
    """Service for finding similar tags using vector embeddings."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        # Use provided API key or get from config
        if not openai_api_key:
            from src.config import get_app_config
            config = get_app_config()
            openai_api_key = config.openai_api_key
        
        self.llm_client = get_llm_client(openai_api_key)
        self.tag_repo = TagRepository()
        
        # Similarity threshold for tag matching
        self.similarity_threshold = 0.85
        
        # Cache for embeddings to avoid recomputation
        self._embedding_cache: Dict[str, List[float]] = {}
    
    async def find_similar_tags(self, term: str, category: TagCategory, 
                              limit: int = 5) -> List[Tuple[Tag, float]]:
        """Find similar existing tags for a given term."""
        try:
            # Get all existing tags in the same category
            existing_tags = await self.tag_repo.get_by_category(category)
            
            if not existing_tags:
                return []
            
            # Generate embedding for the input term
            term_embedding = await self._get_embedding(term)
            if not term_embedding:
                return []
            
            # Calculate similarities with existing tags
            similarities = []
            for tag in existing_tags:
                tag_embedding = await self._get_embedding(tag.name)
                if tag_embedding:
                    similarity = self._cosine_similarity(term_embedding, tag_embedding)
                    if similarity >= self.similarity_threshold:
                        similarities.append((tag, similarity))
            
            # Sort by similarity and return top matches
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar tags: {e}")
            return []
    
    async def suggest_generalized_tag(self, term: str, category: TagCategory) -> Optional[str]:
        """Suggest a generalized tag name using LLM."""
        try:
            # Get similar existing tags for context (but don't require them)
            similar_tags = await self.find_similar_tags(term, category, limit=3)
            
            # Create context for LLM
            similar_tag_names = [tag.name for tag, _ in similar_tags] if similar_tags else []
            
            prompt = f"""
You are a research paper tagging expert. Your job is to convert specific, paper-specific terms into generalized tags that can be reused across many different papers.

CRITICAL GUIDELINES:
1. ALWAYS generalize - never use paper-specific terms
2. Use lowercase with hyphens: "machine-learning", "neural-networks"
3. Use standard, widely-recognized terminology from the field
4. Keep it concise (2-3 words maximum)
5. The tag should be applicable to HUNDREDS of papers, not just this one
6. If the input is a specific action or analysis, convert it to a general methodology or concept
7. NEVER include specific paper details, model names, or dataset names
8. Focus on the BROADER concept or methodology

EXAMPLES OF GENERALIZATION:
- "Analyze the relationship between model size and dataset size" → "scaling-analysis"
- "Derive equations for overfitting" → "overfitting-analysis"
- "Train transformer model on large dataset" → "model-training"
- "Evaluate performance on benchmark tasks" → "benchmark-evaluation"
- "Implement attention mechanism" → "attention-mechanism"
- "Analyze the relationship between size dataset size" → "scaling-analysis"
- "Derive simple equations that relate overfitting to" → "overfitting-analysis"

Input term: "{term}"
Category: {category.value}
Similar existing tags: {', '.join(similar_tag_names) if similar_tag_names else 'None found'}

Convert the input term into a generalized tag that follows the guidelines above. Return only the tag name, no explanation.

Suggested tag:"""

            # Use LLM to suggest generalized tag
            response = await self.llm_client.extract_insights(
                prompt=prompt,
                text=term,
                expected_structure={"suggested_tag": "string"}
            )
            
            suggested_tag = response.get("suggested_tag", "").strip().lower()
            
            # Clean up the suggested tag
            if suggested_tag:
                # Replace spaces with hyphens
                suggested_tag = suggested_tag.replace(" ", "-")
                # Remove any special characters except hyphens
                suggested_tag = "".join(c for c in suggested_tag if c.isalnum() or c == "-")
                # Remove multiple consecutive hyphens
                while "--" in suggested_tag:
                    suggested_tag = suggested_tag.replace("--", "-")
                # Remove leading/trailing hyphens
                suggested_tag = suggested_tag.strip("-")
                
                return suggested_tag if suggested_tag else None
            
            return None
            
        except Exception as e:
            logger.error(f"Error suggesting generalized tag: {e}")
            return None
    
    async def validate_tag_similarity(self, new_tag_name: str, existing_tags: List[Tag]) -> Dict[str, Any]:
        """Validate if a new tag is too similar to existing tags."""
        try:
            results = {
                "is_too_similar": False,
                "similar_tags": [],
                "recommendation": "proceed"
            }
            
            if not existing_tags:
                return results
            
            # Generate embedding for new tag
            new_embedding = await self._get_embedding(new_tag_name)
            if not new_embedding:
                return results
            
            # Check similarity with existing tags
            similarities = []
            for tag in existing_tags:
                tag_embedding = await self._get_embedding(tag.name)
                if tag_embedding:
                    similarity = self._cosine_similarity(new_embedding, tag_embedding)
                    if similarity >= 0.9:  # Very high similarity threshold
                        similarities.append((tag, similarity))
            
            if similarities:
                results["is_too_similar"] = True
                results["similar_tags"] = similarities
                results["recommendation"] = "merge_or_reuse"
                
                # Suggest the most similar tag to reuse
                best_match = max(similarities, key=lambda x: x[1])
                results["suggested_reuse"] = best_match[0].name
            
            return results
            
        except Exception as e:
            logger.error(f"Error validating tag similarity: {e}")
            return {"is_too_similar": False, "similar_tags": [], "recommendation": "proceed"}
    
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text, using cache if available."""
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        
        try:
            embedding = await self.llm_client.get_embedding(text)
            if embedding:
                self._embedding_cache[text] = embedding
            return embedding
        except Exception as e:
            logger.error(f"Error getting embedding for '{text}': {e}")
            return None
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            if len(vec1) != len(vec2):
                return 0.0
            
            # Convert to numpy arrays
            v1 = np.array(vec1)
            v2 = np.array(vec2)
            
            # Calculate cosine similarity
            dot_product = np.dot(v1, v2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def clear_cache(self):
        """Clear the embedding cache."""
        self._embedding_cache.clear()
        logger.info("Tag similarity cache cleared") 