"""
Conversational research agent service for exploring papers through natural dialogue.
"""

import logging
import os
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from .llm_client import get_llm_client
from .context_loader import ContextLoader, PaperContext
from .paper_qa_service import PaperQAService, QAResponse
from ..database.paper_repository import PaperRepository
from ..database.conversation_repository import ConversationRepository
from ..database.note_repository import NoteRepository
from ..services.author_service import AuthorService
from ..models.paper import Paper
from ..models.conversation import ConversationSession, ConversationMessage
from ..models.note import Note
from ..models.enums import NoteType, NotePriority

logger = logging.getLogger(__name__)


class ConversationMessage:
    """Represents a single message in a conversation."""
    
    def __init__(self, role: str, content: str, timestamp: Optional[datetime] = None):
        self.role = role  # 'user' or 'assistant'
        self.content = content
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat()
        }


class ConversationContext:
    """Manages conversation context including current paper and related information."""
    
    def __init__(self):
        self.current_paper: Optional[Paper] = None
        self.related_papers: List[Paper] = []
        self.conversation_focus: Optional[str] = None
        self.user_interests: List[str] = []
    
    def set_current_paper(self, paper: Paper):
        """Set the current paper being discussed."""
        self.current_paper = paper
        logger.info(f"Conversation context set to paper: {paper.title}")
    
    def add_related_papers(self, papers: List[Paper]):
        """Add related papers to the context."""
        self.related_papers = papers
        logger.info(f"Added {len(papers)} related papers to context")
    
    def get_context_summary(self) -> str:
        """Get a summary of the current conversation context."""
        if not self.current_paper:
            return "No paper currently selected for discussion."
        
        summary = f"Current paper: {self.current_paper.title}\n"
        summary += f"Authors: {', '.join(self.current_paper.author_names)}\n"
        summary += f"Type: {self.current_paper.paper_type.value if self.current_paper.paper_type else 'Unknown'}\n"
        
        if self.related_papers:
            summary += f"\nRelated papers in database ({len(self.related_papers)}):\n"
            for paper in self.related_papers[:3]:  # Show first 3
                summary += f"- {paper.title}\n"
            if len(self.related_papers) > 3:
                summary += f"... and {len(self.related_papers) - 3} more\n"
        
        return summary


class ConversationSession:
    """Manages a conversation session with message history and context."""
    
    def __init__(self, session_id: Optional[UUID] = None):
        self.session_id = session_id or uuid4()
        self.messages: List[ConversationMessage] = []
        self.context = ConversationContext()
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
    
    def add_message(self, role: str, content: str) -> ConversationMessage:
        """Add a message to the conversation history."""
        message = ConversationMessage(role, content)
        self.messages.append(message)
        self.last_activity = datetime.now()
        return message
    
    def get_recent_messages(self, limit: int = 10) -> List[ConversationMessage]:
        """Get recent messages for context."""
        return self.messages[-limit:] if self.messages else []
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get full conversation history as dictionaries."""
        return [msg.to_dict() for msg in self.messages]


class ConversationService:
    """Main service for handling conversational interactions about research papers."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.llm_client = get_llm_client(api_key)
        self.paper_repo = PaperRepository()
        self.author_service = AuthorService()
        self.context_loader = ContextLoader()
        self.qa_service = PaperQAService(api_key)
        self.conversation_repo = ConversationRepository()
        self.active_sessions: Dict[UUID, ConversationSession] = {}
        
        logger.info("ConversationService initialized")
    
    def create_session(self) -> ConversationSession:
        """Create a new conversation session."""
        session = ConversationSession()
        self.active_sessions[session.session_id] = session
        logger.info(f"Created new conversation session: {session.session_id}")
        return session
    
    def get_session(self, session_id: UUID) -> Optional[ConversationSession]:
        """Get an existing conversation session."""
        return self.active_sessions.get(session_id)
    
    async def set_paper_context(self, session_id: UUID, paper_id: UUID) -> bool:
        """Set the current paper context for a conversation session."""
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return False
        
        try:
            # Load paper with authors
            paper = await self.author_service.get_paper_with_authors(paper_id)
            if not paper:
                logger.error(f"Paper not found: {paper_id}")
                return False
            
            # Set paper context
            session.context.set_current_paper(paper)
            
            # Load related papers
            related_papers = await self._get_related_papers(paper)
            session.context.add_related_papers(related_papers)
            
            # Add system message about paper context
            context_msg = f"Now discussing: {paper.title}"
            if paper.author_names:
                context_msg += f" by {', '.join(paper.author_names)}"
            session.add_message("system", context_msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set paper context: {e}")
            return False
    
    async def send_message(self, session_id: UUID, user_message: str) -> Optional[str]:
        """Process a user message and generate a response."""
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return None
        
        try:
            # Add user message to history
            session.add_message("user", user_message)
            
            # Generate response
            response = await self._generate_response(session, user_message)
            
            # Add assistant response to history
            session.add_message("assistant", response)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return "I'm sorry, I encountered an error processing your message. Please try again."
    
    async def _generate_response(self, session: ConversationSession, user_message: str) -> str:
        """Generate a response using the LLM with paper context."""
        try:
            # Build context for LLM
            context_parts = []
            
            # Add paper context if available
            if session.context.current_paper:
                paper = session.context.current_paper
                context_parts.append(f"CURRENT PAPER CONTEXT:")
                context_parts.append(f"Title: {paper.title}")
                context_parts.append(f"Authors: {', '.join(paper.author_names)}")
                context_parts.append(f"Type: {paper.paper_type.value if paper.paper_type else 'Unknown'}")
                
                if paper.abstract:
                    context_parts.append(f"Abstract: {paper.abstract}")
                
                # Add related papers context
                if session.context.related_papers:
                    context_parts.append(f"\nRELATED PAPERS IN DATABASE:")
                    for related_paper in session.context.related_papers[:5]:
                        context_parts.append(f"- {related_paper.title} ({related_paper.paper_type.value if related_paper.paper_type else 'Unknown'})")
            
            # Add conversation history for context
            recent_messages = session.get_recent_messages(6)  # Last 6 messages for context
            if len(recent_messages) > 1:  # More than just the current message
                context_parts.append(f"\nRECENT CONVERSATION:")
                for msg in recent_messages[:-1]:  # Exclude current message
                    context_parts.append(f"{msg.role.upper()}: {msg.content}")
            
            # Build the prompt
            system_prompt = """You are a knowledgeable research assistant helping a user explore and understand research papers. 

Your role is to:
- Answer questions about the current paper being discussed
- Explain concepts, methodologies, and findings clearly
- Make connections to related papers in the user's database
- Suggest areas for deeper exploration
- Maintain a conversational, helpful tone

Guidelines:
- Base your responses on the provided paper content and context
- If you don't know something specific about a paper, say so clearly
- Make connections to related papers when relevant
- Ask follow-up questions to guide deeper exploration
- Keep responses focused and conversational, not overly academic

Current context:
""" + "\n".join(context_parts)
            
            # Use the LLM to generate response
            # For now, use a simple prompt structure - we can enhance this later
            full_prompt = f"{system_prompt}\n\nUser question: {user_message}\n\nResponse:"
            
            # Use the existing LLM client (mock for now)
            response_data = await self.llm_client.extract_insights(
                prompt="Respond to the user's question about the research paper in a helpful, conversational way.",
                text=full_prompt,
                expected_structure={"response": "string"}
            )
            
            response = response_data.get("response", "I'm not sure how to respond to that. Could you rephrase your question?")
            
            # Fallback to a simple response if LLM fails
            if not response or len(response.strip()) < 10:
                response = self._generate_fallback_response(session, user_message)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return self._generate_fallback_response(session, user_message)
    
    def _generate_fallback_response(self, session: ConversationSession, user_message: str) -> str:
        """Generate a simple fallback response when LLM fails."""
        if not session.context.current_paper:
            return "I'd be happy to help you explore research papers! Please select a paper from your database to start our conversation."
        
        paper = session.context.current_paper
        
        # Simple keyword-based responses
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ['what', 'about', 'summary', 'summarize']):
            response = f"This paper is titled '{paper.title}'"
            if paper.author_names:
                response += f" by {', '.join(paper.author_names)}"
            if paper.abstract:
                response += f". Here's the abstract: {paper.abstract[:300]}..."
            return response
        
        elif any(word in message_lower for word in ['author', 'who', 'wrote']):
            if paper.author_names:
                return f"This paper was written by {', '.join(paper.author_names)}."
            else:
                return "I don't have author information for this paper."
        
        elif any(word in message_lower for word in ['type', 'kind', 'category']):
            paper_type = paper.paper_type.value if paper.paper_type else 'Unknown'
            return f"This is classified as a {paper_type} paper."
        
        elif any(word in message_lower for word in ['related', 'similar', 'connection']):
            if session.context.related_papers:
                related_titles = [p.title for p in session.context.related_papers[:3]]
                return f"I found {len(session.context.related_papers)} related papers in your database: {', '.join(related_titles)}"
            else:
                return "I didn't find any directly related papers in your database."
        
        else:
            return f"I'd be happy to help you explore '{paper.title}'. You can ask me about the authors, content, related papers, or any specific aspects you're curious about."
    
    async def _get_related_papers(self, paper: Paper) -> List[Paper]:
        """Find papers related to the current paper."""
        related_papers = []
        
        try:
            # Find papers by same authors
            if paper.author_names:
                for author_name in paper.author_names[:2]:  # Check first 2 authors
                    author_papers = await self.author_service.search_papers_by_author(author_name, limit=5)
                    for author_paper in author_papers:
                        if author_paper.id != paper.id and author_paper not in related_papers:
                            related_papers.append(author_paper)
            
            # Find papers with same type
            if paper.paper_type:
                type_papers = await self.paper_repo.get_by_paper_type(paper.paper_type, limit=5)
                for type_paper in type_papers:
                    if type_paper.id != paper.id and type_paper not in related_papers:
                        related_papers.append(type_paper)
            
            # Limit to most relevant
            return related_papers[:10]
            
        except Exception as e:
            logger.error(f"Failed to get related papers: {e}")
            return []
    
    def get_session_summary(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a summary of the conversation session."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        return {
            'session_id': str(session.session_id),
            'created_at': session.created_at.isoformat(),
            'last_activity': session.last_activity.isoformat(),
            'message_count': len(session.messages),
            'current_paper': session.context.current_paper.title if session.context.current_paper else None,
            'related_papers_count': len(session.context.related_papers)
        }
    
    async def chat(self, paper_id: UUID, message: str) -> str:
        """Simple chat method for direct paper conversation (used by CLI)."""
        try:
            # Use the grounded Q&A service for accurate responses
            qa_response = await self.qa_service.answer_question(paper_id, message)
            
            # Format response with any important limitations
            response = qa_response.answer
            
            # Add limitations if present
            if qa_response.limitations:
                response += f"\n\n⚠️ {qa_response.limitations}"
            
            return response
            
        except Exception as e:
            logger.error(f"Error in chat method: {e}")
            return f"I'm sorry, I encountered an error while processing your question about the paper. Please try again."
    
    async def chat_with_qa_details(self, paper_id: UUID, message: str) -> QAResponse:
        """Chat method that returns detailed Q&A response structure."""
        return await self.qa_service.answer_question(paper_id, message)
    
    async def create_persistent_session(self, paper_id: UUID, title: Optional[str] = None) -> ConversationSession:
        """Create a new persistent conversation session."""
        session = await self.conversation_repo.create_session(paper_id, title)
        
        # Load into memory for active use
        self.active_sessions[session.session_id] = session
        
        logger.info(f"Created persistent session {session.session_id} for paper {paper_id}")
        return session

    async def create_general_session(self, title: Optional[str] = None) -> ConversationSession:
        """Create a new persistent conversation session for general discussions (no paper context)."""
        session = await self.conversation_repo.create_session(None, title or "General Discussion")
        
        # Load into memory for active use
        self.active_sessions[session.session_id] = session
        
        logger.info(f"Created general session {session.session_id}")
        return session
    
    async def get_persistent_session(self, session_id: UUID) -> Optional[ConversationSession]:
        """Get a persistent conversation session."""
        # Check if already in memory
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # Load from database
        session = await self.conversation_repo.get_session(session_id)
        if session:
            # Load recent messages into memory
            messages = await self.conversation_repo.get_recent_messages(session_id, limit=50)
            session.messages = messages
            
            # Cache in memory
            self.active_sessions[session_id] = session
            
        return session
    
    async def send_persistent_message(self, session_id: UUID, user_message: str) -> Optional[str]:
        """Send a message in a persistent conversation."""
        session = await self.get_persistent_session(session_id)
        if not session:
            return None
        
        try:
            # Get Q&A response
            qa_response = await self.qa_service.answer_question(session.paper_id, user_message)
            
            # Save user message to database
            user_msg = await self.conversation_repo.add_message(
                session_id=session_id,
                role="user",
                content=user_message
            )
            
            # Save assistant response to database
            assistant_msg = await self.conversation_repo.add_message(
                session_id=session_id,
                role="assistant",
                content=qa_response.answer,
                confidence=qa_response.confidence,
                grounded=qa_response.grounded,
                sources=qa_response.sources,
                limitations=qa_response.limitations
            )
            
            # Add to memory
            session.add_message_to_memory(user_msg)
            session.add_message_to_memory(assistant_msg)
            
            # Auto-generate title if this is the first user message
            if session.message_count <= 2 and not session.title:
                await self.conversation_repo.auto_generate_title(session_id)
            
            return qa_response.answer
            
        except Exception as e:
            logger.error(f"Error in persistent conversation {session_id}: {e}")
            return "I'm sorry, I encountered an error processing your message. Please try again."

    async def send_general_message(self, session_id: UUID, user_message: str, paper_id: Optional[UUID] = None) -> Optional[str]:
        """Send a message in a general conversation (with optional paper context)."""
        try:
            logger.info(f"Starting general message processing for session {session_id}")
            
            session = await self.get_persistent_session(session_id)
            if not session:
                logger.error(f"Session not found: {session_id}")
                return None
            
            logger.info(f"Session found, building conversation context")
            
            # Use LLM client for general conversation
            llm_client = get_llm_client()  # This will use the API key from environment
            logger.info("LLM client created")
            
            # Build conversation context
            recent_messages = session.get_recent_messages(limit=10)
            conversation_history = []
            for msg in recent_messages:
                conversation_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Add current user message
            conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            logger.info(f"Built conversation history with {len(conversation_history)} messages")
            
            # Get paper context if available
            paper_context = ""
            if paper_id:
                try:
                    paper_repo = PaperRepository()
                    paper = await paper_repo.get_by_id(paper_id)
                    if paper:
                        # Include paper metadata and full text content
                        paper_context = f"\n\nCurrent paper context: You are viewing '{paper.title}' by {', '.join(paper.author_names) if paper.author_names else 'Unknown authors'}."
                        
                        # Add full text content if available
                        if paper.full_text:
                            # Give access to the complete paper content - no truncation
                            paper_context += f"\n\nComplete paper content:\n{paper.full_text}"
                            
                            # Log what content is being sent for debugging
                            logger.info(f"Paper content length: {len(paper.full_text)} characters")
                            logger.info(f"Content preview: {paper.full_text[:200]}...")
                            if "choice pattern" in paper.full_text.lower():
                                logger.info("Found 'choice pattern' in paper content")
                            else:
                                logger.warning("'choice pattern' NOT found in paper content")
                        
                        paper_context += "\n\nYour primary responsibility is to help the user understand this specific paper. When they ask questions, search through this paper's content first and provide detailed answers based on what the paper actually says. Only expand to broader discussions after thoroughly addressing the paper content."
                except Exception as e:
                    logger.warning(f"Could not load paper context: {e}")
            
            # Generate response using LLM
            system_prompt = f"""You are a research assistant focused on helping users understand and engage with the current paper. Your primary role is to answer questions based on the paper's content.

{paper_context}

**CRITICAL: ALWAYS FORMAT YOUR RESPONSES WITH CLEAR STRUCTURE**

**MANDATORY FORMATTING REQUIREMENTS:**
1. **Use bold headings** for main topics: **"Main Topic"**
2. **Use bullet points ONLY for main lists**: • Item 1 • Item 2 • Item 3
3. **Use regular paragraphs** for descriptions and explanations (no sub-bullets)
4. **Bold key terms** and concepts: **"Important Term"**
5. **Use quotes** for direct paper references: "exact quote from paper"
6. **Break up text** into clear sections with line breaks
7. **Keep it simple** - avoid nested lists and complex formatting

**Your approach:**
1. **ALWAYS start by answering the user's question based on the paper's content first**
2. **Quote specific sections and provide detailed explanations from the paper**
3. **Only after thoroughly addressing the paper content, you can expand to broader discussions if relevant**
4. **If the user asks about concepts not in the paper, acknowledge this and offer to discuss them separately**

**When the user asks about the paper:**
- Search through the paper content for relevant information
- Look for exact phrases and terms the user mentions
- **ALWAYS structure your response with:**
  - **Main heading** for the topic
  - **Bullet points** for main lists only (e.g., choice patterns)
  - **Regular paragraphs** for descriptions under each bullet point
  - **Bold text** for important concepts and terms
  - **Quotes** when directly referencing the paper
  - **Clear sections** separated by line breaks
- Provide specific quotes and page references when possible
- Explain concepts in detail using the paper's own language and examples
- Connect different parts of the paper to give comprehensive answers
- If you can't find specific information, say so clearly rather than making assumptions

**For broader discussions:**
- Only after addressing the paper content
- Clearly distinguish between paper content and your general knowledge
- Be conversational and engaging while maintaining academic rigor

**REMEMBER: Your response must be scannable and easy to read with clear structure!**

**NOTE CREATION CAPABILITY:**
If the user asks you to "add a note" or "create a note" about something, you should:
1. First provide your normal response about the topic
2. Then create a note with the key information from your response
3. Confirm that you've created the note

When creating notes, use clear, concise titles and include the most important information from your response."""
            
            # Prepare messages for the LLM
            llm_messages = [
                {"role": "system", "content": system_prompt},
                *conversation_history
            ]
            
            logger.info("Calling LLM client")
            assistant_response = await llm_client.generate_response(llm_messages)
            logger.info(f"LLM response received: {assistant_response[:100]}...")
            
            # Check if user wants a note created
            note_created = None
            if paper_id and any(phrase in user_message.lower() for phrase in ["add a note", "create a note", "save a note", "make a note"]):
                try:
                    # Extract a title from the user's request
                    title = "Note from conversation"
                    if "about" in user_message.lower():
                        # Try to extract topic after "about"
                        about_index = user_message.lower().find("about")
                        if about_index != -1:
                            title = user_message[about_index + 6:].strip().capitalize()
                    
                    # Create note with the assistant's response as content
                    note_created = await self.create_note_for_paper(
                        paper_id=paper_id,
                        title=title,
                        content=assistant_response,
                        session_id=session_id
                    )
                    
                    if note_created:
                        assistant_response += f"\n\n✅ **Note Created**: I've saved a note titled '{note_created['title']}' with the key information from our discussion."
                        logger.info(f"Note created successfully: {note_created['id']}")
                    else:
                        assistant_response += "\n\n❌ **Note Creation Failed**: I tried to create a note but encountered an error."
                        logger.error("Failed to create note")
                        
                except Exception as e:
                    logger.error(f"Error creating note: {e}")
                    assistant_response += "\n\n❌ **Note Creation Failed**: I encountered an error while trying to create the note."
            
            # Save user message to database
            user_msg = await self.conversation_repo.add_message(
                session_id=session_id,
                role="user",
                content=user_message
            )
            
            # Save assistant response to database
            assistant_msg = await self.conversation_repo.add_message(
                session_id=session_id,
                role="assistant",
                content=assistant_response,
                confidence=0.8,  # General confidence for general conversations
                grounded=False,  # Not grounded in specific paper content
                sources=[],
                limitations="This is a general conversation response, not specifically grounded in paper content."
            )
            
            # Add to memory
            session.add_message_to_memory(user_msg)
            session.add_message_to_memory(assistant_msg)
            
            # Auto-generate title if this is the first user message
            if session.message_count <= 2 and not session.title:
                await self.conversation_repo.auto_generate_title(session_id)
            
            return assistant_response
            
        except Exception as e:
            logger.error(f"Error in general conversation {session_id}: {e}")
            return "I'm sorry, I encountered an error processing your message. Please try again."
    
    async def list_conversations(
        self, 
        paper_id: Optional[UUID] = None, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List conversation sessions."""
        return await self.conversation_repo.list_sessions(paper_id, limit)
    
    async def get_conversation_history(self, session_id: UUID) -> List[ConversationMessage]:
        """Get full conversation history."""
        return await self.conversation_repo.get_messages(session_id)
    
    async def archive_conversation(self, session_id: UUID) -> bool:
        """Archive a conversation."""
        # Remove from active sessions
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        return await self.conversation_repo.archive_session(session_id)
    
    async def delete_conversation(self, session_id: UUID) -> bool:
        """Delete a conversation."""
        # Remove from active sessions
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        return await self.conversation_repo.delete_session(session_id)
    
    async def search_conversations(self, query: str, paper_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
        """Search conversations by content."""
        return await self.conversation_repo.search_conversations(query, paper_id)
    
    async def create_note_for_paper(self, paper_id: UUID, title: str, content: str, session_id: Optional[UUID] = None) -> Optional[Dict[str, Any]]:
        """Create a note for a paper."""
        try:
            note_repo = NoteRepository()
            
            note = Note(
                title=title,
                content=content,
                paper_id=paper_id,
                conversation_session_id=session_id,
                note_type=NoteType.GENERAL,
                priority=NotePriority.MEDIUM
            )
            
            created_note = await note_repo.create_note(note)
            logger.info(f"Created note '{title}' for paper {paper_id}")
            
            return {
                "id": str(created_note.id),
                "title": created_note.title,
                "content": created_note.content,
                "created_at": created_note.created_at.isoformat() if created_note.created_at else None
            }
            
        except Exception as e:
            logger.error(f"Error creating note: {e}")
            return None