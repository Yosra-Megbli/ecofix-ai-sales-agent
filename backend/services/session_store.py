"""Shared in-memory session store for all conversation channels (web, Telegram)."""

from typing import Dict, Any

# Global session registry: session_id -> state dict
# session_id format:
#   - web chat  : any string provided by the frontend
#   - Telegram  : "telegram:{chat_id}"
_sessions: Dict[str, Dict[str, Any]] = {}


def get_session(session_id: str) -> Dict[str, Any]:
    """Return existing session or create a fresh one."""
    if session_id not in _sessions:
        _sessions[session_id] = {
            "messages": [],
            "conversation_turn": 0,
            "lead_id": None,
            "lead_info": {},
        }
    return _sessions[session_id]


def set_session(session_id: str, state: Dict[str, Any]) -> None:
    """Overwrite the session state (used after graph.invoke returns a new state)."""
    _sessions[session_id] = state


def reset_session(session_id: str) -> Dict[str, Any]:
    """Reset a session to its initial state and return it."""
    _sessions[session_id] = {
        "messages": [],
        "conversation_turn": 0,
        "lead_id": None,
        "lead_info": {},
    }
    return _sessions[session_id]


def session_exists(session_id: str) -> bool:
    """Return True if the session already exists."""
    return session_id in _sessions
