"""Routes for chat/conversation endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services import conversation_service

router = APIRouter()


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    message: str
    session_id: str


class ChatResponse(BaseModel):
    """Response body for chat endpoint."""
    response: str
    session_id: str
    turn: int


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the AI agent and get a response.

    Maintains conversation history per session_id in memory.

    Args:
        request: ChatRequest with message and session_id

    Returns:
        ChatResponse with agent's reply
    """
    try:
        response_text, turn = conversation_service.send_message(
            request.session_id, request.message
        )
        return ChatResponse(response=response_text, session_id=request.session_id, turn=turn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat processing: {str(e)}")


@router.post("/start")
async def start_chat(session_id: str):
    """
    Start a new chat session with an initial greeting.

    Args:
        session_id: Unique session identifier

    Returns:
        ChatResponse with initial greeting
    """
    try:
        greeting, turn = conversation_service.start_session(session_id)
        return ChatResponse(response=greeting, session_id=session_id, turn=turn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting chat: {str(e)}")


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """
    Get conversation history for a session.

    Args:
        session_id: Session identifier

    Returns:
        Dict with messages, turn, lead_id, lead_info
    """
    try:
        return conversation_service.get_history(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
