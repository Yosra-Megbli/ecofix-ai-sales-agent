"""Routes for chat/conversation endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from backend.agent.graph import get_agent_graph
from backend.agent.prompts import INITIAL_GREETING

router = APIRouter()

# In-memory session storage (session_id -> {messages, turn})
sessions: Dict[str, Dict] = {}


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
        session_id = request.session_id
        user_message = request.message
        
        # Get or create session
        if session_id not in sessions:
            sessions[session_id] = {
                "messages": [],
                "conversation_turn": 0,
            }
        
        state = sessions[session_id]
        
        # Add user message to history
        state["messages"].append({"role": "user", "content": user_message})
        
        # Process through agent graph
        graph = get_agent_graph()
        result = graph.invoke(state)
        
        # Update state with result
        state["messages"] = result.get("messages", state["messages"])
        state["conversation_turn"] = result.get("conversation_turn", state["conversation_turn"])
        
        # Get last assistant message (the response)
        assistant_messages = [m["content"] for m in state["messages"] if m["role"] == "assistant"]
        if not assistant_messages:
            raise ValueError("No assistant response generated")
        
        response_text = assistant_messages[-1]
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            turn=state["conversation_turn"],
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in chat processing: {str(e)}"
        )


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
        # Create or reset session
        sessions[session_id] = {
            "messages": [],
            "conversation_turn": 0,
        }
        
        state = sessions[session_id]
        
        # Add greeting message
        state["messages"].append({"role": "assistant", "content": INITIAL_GREETING})
        state["conversation_turn"] = 1
        
        return ChatResponse(
            response=INITIAL_GREETING,
            session_id=session_id,
            turn=1,
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error starting chat: {str(e)}"
        )


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """
    Get conversation history for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        List of messages (user/assistant pairs)
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    state = sessions[session_id]
    messages = state.get("messages", [])
    
    return {
        "session_id": session_id,
        "messages": messages,
        "turn": state.get("conversation_turn", 0),
    }

