#!/usr/bin/env python3
"""
Context Loader Service for Conversational Agent

This service handles loading and formatting paper content for LLM consumption,
including context window management for long papers.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from dataclasses import dataclass

from src.models.paper import Paper
from src.database.paper_repository import PaperRepository
from src.database.tag_repository import PaperTagRepository

logger = logging.getLogger(__name__)


@dataclass
class ContextChunk:
    """Represents a chunk of paper content for context loading."""
    content: str
    chunk_type: str  # 'abstract', 'introduction', 'body', 'conclusion', 'references'
    start_position: int
    end_position: int
    priority: int  # Higher priority chunks are included first


@dataclass
class PaperContext:
    """Complete context information for a paper."""
    paper: Paper
    formatted_content: str
    related_papers: List[Paper]
    tags: List[Dict[str, Any]]
    chunks: List[ContextChunk]
    total_tokens: int


class ContextLoader:
    """Service for loading and formatting paper content for conversations."""
    
    def __init__(self, max_context_tokens: int = 8000):
        self.paper_repo = PaperRepository()
        self.tag_repo = PaperTagRepository()
        self.max_context_tokens = max_context_tokens
        
    async def load_paper_context(self, paper_id: UUID, include_related: bool = True) -> PaperContext:
        """Load comprehensive context for a paper with token management."""
        paper = await self.paper_repo.get_by_id(paper_id)
        if not paper:
            raise ValueError(f"Paper with ID {paper_id} not found")
        
        # Get paper with authors
        paper_with_authors = await self.paper_repo.get_paper_with_authors(paper_id)
        
        # Load related papers if requested
        related_papers = []
        if include_related:
            related_papers = await self._load_related_papers(paper)
        
        # Load tags
        tags = await self._load_paper_tags(paper_id)
        
        # Create content chunks
        chunks = self._create_content_chunks(paper)
        
        # Format content within token limits
        formatted_content = await self._format_paper_content(
            paper_with_authors, related_papers, tags, chunks
        )
        
        # Estimate token count (rough approximation: 1 token ≈ 4 characters)
        total_tokens = len(formatted_content) // 4
        
        return PaperContext(
            paper=paper_with_authors,
            formatted_content=formatted_content,
            related_papers=related_papers,
            tags=tags,
            chunks=chunks,
            total_tokens=total_tokens
        )
    
    def _create_content_chunks(self, paper: Paper) -> List[ContextChunk]:
        """Break paper content into prioritized chunks."""
        chunks = []
        
        # Abstract (highest priority)
        if paper.abstract:
            chunks.append(ContextChunk(
                content=paper.abstract,
                chunk_type='abstract',
                start_position=0,
                end_position=len(paper.abstract),
                priority=10
            ))
        
        if not paper.full_text:
            return chunks
        
        # Split full text into sections
        text = paper.full_text
        sections = self._identify_sections(text)
        
        for section_name, start_pos, end_pos, priority in sections:
            content = text[start_pos:end_pos]
            chunks.append(ContextChunk(
                content=content,
                chunk_type=section_name,
                start_position=start_pos,
                end_position=end_pos,
                priority=priority
            ))
        
        # Sort by priority (highest first)
        chunks.sort(key=lambda x: x.priority, reverse=True)
        return chunks
    
    def _identify_sections(self, text: str) -> List[tuple]:
        """Identify sections in paper text with priorities."""
        sections = []
        text_lower = text.lower()
        
        # Common section patterns with priorities
        section_patterns = [
            ('introduction', 8),
            ('abstract', 10),
            ('conclusion', 7),
            ('results', 6),
            ('discussion', 6),
            ('methodology', 5),
            ('method', 5),
            ('related work', 4),
            ('background', 4),
            ('references', 2),
            ('acknowledgments', 1)
        ]
        
        for section_name, priority in section_patterns:
            # Look for section headers
            patterns = [
                f"\n{section_name}\n",
                f"\n{section_name.title()}\n",
                f"\n{section_name.upper()}\n",
                f"\n{section_name.capitalize()}\n"
            ]
            
            for pattern in patterns:
                start_pos = text_lower.find(pattern.lower())
                if start_pos != -1:
                    # Find end of section (next section or end of text)
                    end_pos = len(text)
                    for next_section, _ in section_patterns:
                        if next_section != section_name:
                            next_patterns = [
                                f"\n{next_section}\n",
                                f"\n{next_section.title()}\n",
                                f"\n{next_section.upper()}\n"
                            ]
                            for next_pattern in next_patterns:
                                next_pos = text_lower.find(next_pattern.lower(), start_pos + len(pattern))
                                if next_pos != -1 and next_pos < end_pos:
                                    end_pos = next_pos
                    
                    sections.append((section_name, start_pos, end_pos, priority))
                    break
        
        # If no sections found, treat entire text as body
        if not sections and text:
            sections.append(('body', 0, len(text), 5))
        
        return sections
    
    async def _format_paper_content(
        self, 
        paper: Paper, 
        related_papers: List[Paper], 
        tags: List[Dict[str, Any]], 
        chunks: List[ContextChunk]
    ) -> str:
        """Format paper content for LLM consumption within token limits."""
        
        # Start with essential metadata
        content_parts = [
            f"Title: {paper.title}",
            f"Authors: {', '.join(paper.author_names) if hasattr(paper, 'author_names') and paper.author_names else 'Unknown'}",
            f"Paper Type: {paper.paper_type.value if paper.paper_type else 'Unknown'}",
            f"Publication Date: {paper.publication_date or 'Unknown'}",
            f"Categories: {', '.join(paper.categories) if paper.categories else 'None'}",
            f"ArXiv ID: {paper.arxiv_id or 'N/A'}"
        ]
        
        # Add tags if available
        if tags:
            tag_info = []
            for tag in tags[:10]:  # Limit to first 10 tags
                tag_info.append(f"{tag['name']} ({tag['category']})")
            content_parts.append(f"Tags: {', '.join(tag_info)}")
        
        # Add related papers context
        if related_papers:
            related_info = []
            for paper in related_papers[:5]:  # Limit to 5 related papers
                related_info.append(f"- {paper.title[:80]}...")
            content_parts.append(f"Related Papers:\\n" + "\\n".join(related_info))
        
        # Calculate tokens used so far
        current_content = "\\n\\n".join(content_parts)
        tokens_used = len(current_content) // 4
        
        # Add content chunks within token limit
        remaining_tokens = self.max_context_tokens - tokens_used - 100  # Buffer
        
        for chunk in chunks:
            chunk_tokens = len(chunk.content) // 4
            if tokens_used + chunk_tokens > self.max_context_tokens:
                # Truncate chunk to fit
                available_chars = (remaining_tokens * 4) - 100
                if available_chars > 200:  # Only include if meaningful content fits
                    truncated_content = chunk.content[:available_chars] + "... [truncated]"
                    content_parts.append(f"{chunk.chunk_type.title()}: {truncated_content}")
                break
            else:
                content_parts.append(f"{chunk.chunk_type.title()}: {chunk.content}")
                tokens_used += chunk_tokens
                remaining_tokens -= chunk_tokens
        
        return "\\n\\n".join(content_parts)
    
    async def _load_related_papers(self, paper: Paper) -> List[Paper]:
        """Load papers related to the current paper."""
        related_papers = []
        
        # Find papers by same authors (limit to prevent context overflow)
        if hasattr(paper, 'author_names') and paper.author_names:
            for author_name in paper.author_names[:2]:  # Check first 2 authors
                author_papers = await self.paper_repo.search_by_author(author_name, limit=2)
                for author_paper in author_papers:
                    if author_paper.id != paper.id and author_paper not in related_papers:
                        related_papers.append(author_paper)
                        if len(related_papers) >= 3:  # Limit total related papers
                            break
                if len(related_papers) >= 3:
                    break
        
        # Find papers in same categories
        if paper.categories and len(related_papers) < 3:
            for category in paper.categories[:2]:  # Check first 2 categories
                category_papers = await self.paper_repo.search_by_category(category, limit=2)
                for category_paper in category_papers:
                    if (category_paper.id != paper.id and 
                        category_paper not in related_papers and 
                        len(related_papers) < 3):
                        related_papers.append(category_paper)
        
        return related_papers[:3]  # Maximum 3 related papers
    
    async def _load_paper_tags(self, paper_id: UUID) -> List[Dict[str, Any]]:
        """Load tags associated with the paper."""
        try:
            paper_tags = await self.tag_repo.get_paper_tags_with_details(paper_id)
            return paper_tags[:10] if paper_tags else []  # Limit to 10 tags
        except Exception as e:
            logger.warning(f"Could not load tags for paper {paper_id}: {e}")
            return []
    
    def get_context_summary(self, context: PaperContext) -> str:
        """Get a brief summary of the loaded context."""
        summary_parts = [
            f"Paper: {context.paper.title}",
            f"Content chunks: {len(context.chunks)}",
            f"Related papers: {len(context.related_papers)}",
            f"Tags: {len(context.tags)}",
            f"Estimated tokens: {context.total_tokens}"
        ]
        
        if context.chunks:
            chunk_types = [chunk.chunk_type for chunk in context.chunks]
            summary_parts.append(f"Sections included: {', '.join(set(chunk_types))}")
        
        return "\\n".join(summary_parts)