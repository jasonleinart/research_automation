"""
Chat API endpoints for conversational paper exploration
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from uuid import UUID
import json
import logging

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.services.conversation_service import ConversationService
from src.services.paper_qa_service import PaperQAService, QAResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[str] = None
    confidence: Optional[float] = None
    grounded: Optional[bool] = None
    sources: Optional[List[str]] = None

class ChatRequest(BaseModel):
    message: str
    paper_id: Optional[str] = None  # Optional - allows general conversations
    session_id: Optional[str] = None
    conversation_type: Optional[str] = "general"  # "general" or "paper_specific"

class ChatResponse(BaseModel):
    response: str
    confidence: float
    grounded: bool
    sources: List[str]
    limitations: Optional[str] = None
    session_id: str

class PaperSummary(BaseModel):
    id: str
    title: str
    authors: List[str]
    paper_type: Optional[str]
    publication_date: Optional[str]
    categories: List[str]

class ChatSession(BaseModel):
    session_id: str
    paper_id: str
    paper_title: str
    message_count: int
    created_at: str
    last_activity: str

# Global services
conversation_service = ConversationService()
qa_service = PaperQAService()

@router.get("/papers", response_model=List[PaperSummary])
async def get_papers_for_chat():
    """Get list of papers available for chat."""
    try:
        await db_manager.initialize()
        paper_repo = PaperRepository()
        papers = await paper_repo.list_all()
        
        paper_summaries = []
        for paper in papers:
            # Get authors for each paper
            paper_with_authors = await paper_repo.get_paper_with_authors(paper.id)
            
            paper_summaries.append(PaperSummary(
                id=str(paper.id),
                title=paper.title,
                authors=paper_with_authors.author_names if hasattr(paper_with_authors, 'author_names') else [],
                paper_type=paper.paper_type.value if paper.paper_type else None,
                publication_date=paper.publication_date.isoformat() if paper.publication_date else None,
                categories=paper.categories or []
            ))
        
        return paper_summaries
        
    except Exception as e:
        logger.error(f"Error getting papers for chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to load papers")

@router.post("/message", response_model=ChatResponse)
async def send_chat_message(request: ChatRequest):
    """Send a message and get a response from the chat system."""
    try:
        await db_manager.initialize()
        
        # Always use general conversation with optional paper context
        if request.session_id:
            session_uuid = UUID(request.session_id)
            session = await conversation_service.get_persistent_session(session_uuid)
            if not session:
                # Create a general session (no paper_id)
                session = await conversation_service.create_general_session()
        else:
            session = await conversation_service.create_general_session()
        
        # Send message with optional paper context
        response_text = await conversation_service.send_general_message(
            session.session_id, request.message, 
            paper_id=UUID(request.paper_id) if request.paper_id else None
        )
        
        if not response_text:
            raise HTTPException(status_code=500, detail="Failed to process message")
        
        # Get the latest assistant message for metadata
        messages = await conversation_service.get_conversation_history(session.session_id)
        latest_assistant_msg = None
        for msg in reversed(messages):
            if msg.role == "assistant":
                latest_assistant_msg = msg
                break
        
        return ChatResponse(
            response=response_text,
            confidence=latest_assistant_msg.confidence if latest_assistant_msg else 0.5,
            grounded=latest_assistant_msg.grounded if latest_assistant_msg else False,
            sources=latest_assistant_msg.sources if latest_assistant_msg else [],
            limitations=latest_assistant_msg.limitations if latest_assistant_msg else None,
            session_id=str(session.session_id)
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {e}")
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")

@router.get("/sessions/{session_id}/history", response_model=List[ChatMessage])
async def get_chat_history(session_id: str):
    """Get chat history for a session."""
    try:
        await db_manager.initialize()
        session_uuid = UUID(session_id)
        
        messages = await conversation_service.get_conversation_history(session_uuid)
        
        chat_messages = []
        for msg in messages:
            chat_messages.append(ChatMessage(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp.isoformat(),
                confidence=msg.confidence,
                grounded=msg.grounded,
                sources=msg.sources
            ))
        
        return chat_messages
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chat history")

@router.get("/sessions", response_model=List[ChatSession])
async def get_chat_sessions():
    """Get list of chat sessions."""
    try:
        await db_manager.initialize()
        
        sessions_data = await conversation_service.list_conversations(limit=50)
        
        sessions = []
        for session_data in sessions_data:
            sessions.append(ChatSession(
                session_id=session_data['id'],
                paper_id=session_data['paper_id'],
                paper_title=session_data['paper_title'],
                message_count=session_data['message_count'],
                created_at=session_data['created_at'],
                last_activity=session_data['last_activity']
            ))
        
        return sessions
        
    except Exception as e:
        logger.error(f"Error getting chat sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sessions")

@router.get("/papers/{paper_id}/suggestions", response_model=List[str])
async def get_question_suggestions(paper_id: str):
    """Get suggested questions for a paper."""
    try:
        await db_manager.initialize()
        paper_repo = PaperRepository()
        paper_uuid = UUID(paper_id)
        
        paper = await paper_repo.get_by_id(paper_uuid)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        suggestions = qa_service.get_question_suggestions(paper)
        return suggestions
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid paper ID")
    except Exception as e:
        logger.error(f"Error getting question suggestions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get suggestions")

# WebSocket endpoint for real-time chat (optional enhancement)
@router.websocket("/ws/{paper_id}")
async def websocket_chat(websocket: WebSocket, paper_id: str):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()
    
    try:
        paper_uuid = UUID(paper_id)
        session = conversation_service.create_session()
        await conversation_service.set_paper_context(session.session_id, paper_uuid)
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            if user_message:
                # Get Q&A response
                qa_response = await qa_service.answer_question(paper_uuid, user_message)
                
                # Add to session
                session.add_message("user", user_message)
                session.add_message("assistant", qa_response.answer)
                
                # Send response back to client
                response_data = {
                    "type": "message",
                    "role": "assistant",
                    "content": qa_response.answer,
                    "confidence": qa_response.confidence,
                    "grounded": qa_response.grounded,
                    "sources": qa_response.sources,
                    "limitations": qa_response.limitations
                }
                
                await websocket.send_text(json.dumps(response_data))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for paper {paper_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

# Additional endpoints for conversation management

@router.delete("/sessions/{session_id}")
async def delete_conversation(session_id: str):
    """Delete a conversation session."""
    try:
        await db_manager.initialize()
        session_uuid = UUID(session_id)
        
        success = await conversation_service.delete_conversation(session_uuid)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": "Conversation deleted successfully"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")

@router.post("/sessions/{session_id}/archive")
async def archive_conversation(session_id: str):
    """Archive a conversation session."""
    try:
        await db_manager.initialize()
        session_uuid = UUID(session_id)
        success = await conversation_service.archive_session(session_uuid)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": "Conversation archived successfully"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    except Exception as e:
        logger.error(f"Error archiving conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to archive conversation")

@router.post("/notes")
async def create_note_from_chat(
    paper_id: str,
    title: str,
    content: str,
    note_type: str = "general",
    priority: str = "medium"
):
    """Create a note from the chat interface."""
    try:
        await db_manager.initialize()
        
        # Convert string UUID to UUID object
        paper_uuid = UUID(paper_id)
        
        # Import note repository
        from src.database.note_repository import NoteRepository
        note_repo = NoteRepository()
        
        # Create the note
        note_data = {
            "paper_id": paper_uuid,
            "title": title,
            "content": content,
            "note_type": note_type,
            "priority": priority,
            "tags": []
        }
        
        note = await note_repo.create(note_data)
        
        return {
            "id": str(note.id),
            "title": note.title,
            "content": note.content,
            "note_type": note.note_type.value if note.note_type else "general",
            "priority": note.priority.value if note.priority else "medium",
            "created_at": note.created_at.isoformat() if note.created_at else None
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid paper ID")
    except Exception as e:
        logger.error(f"Error creating note from chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to create note")

@router.get("/search")
async def search_conversations(
    q: str,
    paper_id: Optional[str] = None,
    limit: int = 20
):
    """Search conversations by content."""
    try:
        await db_manager.initialize()
        
        paper_uuid = UUID(paper_id) if paper_id else None
        results = await conversation_service.search_conversations(q, paper_uuid)
        
        return results
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid paper ID")
    except Exception as e:
        logger.error(f"Error searching conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to search conversations")