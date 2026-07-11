"""Shared conversation service used by all channels (web chat, Telegram, …).

This module is the single place that:
- creates / resets sessions via session_store
- calls the LangGraph agent graph
- returns the assistant reply and updated turn counter

Neither routes/chat.py nor the Telegram bot should duplicate this logic.
"""

from typing import Dict, Any, Tuple

from backend.agent.graph import get_agent_graph
from backend.agent.prompts import INITIAL_GREETING
from backend.services import session_store


def start_session(session_id: str) -> Tuple[str, int]:
    """
    Reset (or create) a session and return the initial greeting.

    Args:
        session_id: Unique session identifier.

    Returns:
        Tuple of (greeting_text, turn_number).
    """
    state = session_store.reset_session(session_id)
    state["messages"].append({"role": "assistant", "content": INITIAL_GREETING})
    state["conversation_turn"] = 1
    session_store.set_session(session_id, state)
    return INITIAL_GREETING, 1


def send_message(session_id: str, user_message: str) -> Tuple[str, int]:
    """
    Append a user message to the session, run the agent graph, and return
    the assistant reply.

    Args:
        session_id:    Unique session identifier (created on first call if absent).
        user_message:  Raw text sent by the user.

    Returns:
        Tuple of (assistant_reply_text, turn_number).

    Raises:
        ValueError: If the graph produces no assistant message.
    """
    state = session_store.get_session(session_id)

    # Append user turn
    state["messages"].append({"role": "user", "content": user_message})

    # Run the LangGraph agent
    graph = get_agent_graph()
    result = graph.invoke(state)

    # Persist updated state
    state["messages"] = result.get("messages", state["messages"])
    state["conversation_turn"] = result.get("conversation_turn", state["conversation_turn"])
    state["lead_id"] = result.get("lead_id", state.get("lead_id"))
    state["lead_info"] = result.get("lead_info", state.get("lead_info"))
    session_store.set_session(session_id, state)

    # Extract last assistant reply
    assistant_messages = [m["content"] for m in state["messages"] if m["role"] == "assistant"]
    if not assistant_messages:
        raise ValueError("No assistant response generated")

    return assistant_messages[-1], state["conversation_turn"]


def get_history(session_id: str) -> Dict[str, Any]:
    """
    Return the full session state for a given session_id.

    Args:
        session_id: Unique session identifier.

    Returns:
        Dict with messages, turn, lead_id, lead_info.

    Raises:
        KeyError: If the session does not exist.
    """
    if not session_store.session_exists(session_id):
        raise KeyError(f"Session {session_id} not found")

    state = session_store.get_session(session_id)
    return {
        "session_id": session_id,
        "messages": state.get("messages", []),
        "turn": state.get("conversation_turn", 0),
        "lead_id": state.get("lead_id"),
        "lead_info": state.get("lead_info"),
    }
