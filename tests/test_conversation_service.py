"""Unit tests for backend/services/conversation_service.py and session_store.py.

All external calls (LangGraph graph, Telegram HTTP) are mocked so these tests
run fully offline, in the same style as tests/test_eligibility_local.py.
"""

import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services import session_store, conversation_service
from backend.agent.prompts import INITIAL_GREETING


# ---------------------------------------------------------------------------
# session_store tests
# ---------------------------------------------------------------------------

def test_get_session_creates_fresh_state():
    session_store._sessions.clear()
    state = session_store.get_session("test-001")
    assert state["messages"] == []
    assert state["conversation_turn"] == 0
    assert state["lead_id"] is None
    assert state["lead_info"] == {}
    print("get_session creates fresh state — OK")


def test_get_session_returns_existing():
    session_store._sessions.clear()
    session_store.get_session("test-002")
    session_store._sessions["test-002"]["conversation_turn"] = 5
    state = session_store.get_session("test-002")
    assert state["conversation_turn"] == 5
    print("get_session returns existing state — OK")


def test_reset_session_clears_state():
    session_store._sessions.clear()
    state = session_store.get_session("test-003")
    state["conversation_turn"] = 10
    state["lead_id"] = "recABC"
    session_store.reset_session("test-003")
    fresh = session_store.get_session("test-003")
    assert fresh["conversation_turn"] == 0
    assert fresh["lead_id"] is None
    print("reset_session clears state — OK")


def test_session_exists():
    session_store._sessions.clear()
    assert session_store.session_exists("ghost") is False
    session_store.get_session("ghost")
    assert session_store.session_exists("ghost") is True
    print("session_exists works correctly — OK")


# ---------------------------------------------------------------------------
# conversation_service tests
# ---------------------------------------------------------------------------

def test_start_session_returns_greeting():
    session_store._sessions.clear()
    greeting, turn = conversation_service.start_session("web-001")
    assert greeting == INITIAL_GREETING
    assert turn == 1
    state = session_store.get_session("web-001")
    assert state["messages"][-1]["content"] == INITIAL_GREETING
    print("start_session returns greeting and stores it — OK")


@patch("backend.services.conversation_service.get_agent_graph")
def test_send_message_calls_graph_and_returns_reply(mock_get_graph):
    session_store._sessions.clear()

    # Build a fake graph that appends an assistant message
    fake_graph = MagicMock()
    fake_graph.invoke.return_value = {
        "messages": [
            {"role": "user", "content": "Bonjour"},
            {"role": "assistant", "content": "Bonjour ! Comment puis-je vous aider ?"},
        ],
        "conversation_turn": 1,
        "lead_id": None,
        "lead_info": {},
    }
    mock_get_graph.return_value = fake_graph

    reply, turn = conversation_service.send_message("web-002", "Bonjour")

    assert reply == "Bonjour ! Comment puis-je vous aider ?"
    assert turn == 1
    fake_graph.invoke.assert_called_once()
    print("send_message calls graph and returns assistant reply — OK")


@patch("backend.services.conversation_service.get_agent_graph")
def test_send_message_raises_if_no_assistant_reply(mock_get_graph):
    session_store._sessions.clear()

    fake_graph = MagicMock()
    fake_graph.invoke.return_value = {
        "messages": [{"role": "user", "content": "test"}],
        "conversation_turn": 1,
        "lead_id": None,
        "lead_info": {},
    }
    mock_get_graph.return_value = fake_graph

    try:
        conversation_service.send_message("web-003", "test")
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "No assistant response" in str(e)
    print("send_message raises ValueError when no assistant reply — OK")


def test_get_history_raises_for_unknown_session():
    session_store._sessions.clear()
    try:
        conversation_service.get_history("nonexistent")
        assert False, "Expected KeyError"
    except KeyError:
        pass
    print("get_history raises KeyError for unknown session — OK")


def test_get_history_returns_correct_data():
    session_store._sessions.clear()
    conversation_service.start_session("web-004")
    history = conversation_service.get_history("web-004")
    assert history["session_id"] == "web-004"
    assert len(history["messages"]) == 1
    assert history["turn"] == 1
    print("get_history returns correct session data — OK")


# ---------------------------------------------------------------------------
# Telegram session_id isolation test
# ---------------------------------------------------------------------------

def test_telegram_session_id_does_not_collide_with_web():
    session_store._sessions.clear()
    conversation_service.start_session("abc123")          # web session
    conversation_service.start_session("telegram:abc123") # telegram session

    web_state = session_store.get_session("abc123")
    tg_state = session_store.get_session("telegram:abc123")

    # They must be independent objects
    assert web_state is not tg_state
    print("Telegram and web sessions are isolated — OK")


if __name__ == "__main__":
    test_get_session_creates_fresh_state()
    test_get_session_returns_existing()
    test_reset_session_clears_state()
    test_session_exists()
    test_start_session_returns_greeting()
    test_send_message_calls_graph_and_returns_reply()
    test_send_message_raises_if_no_assistant_reply()
    test_get_history_raises_for_unknown_session()
    test_get_history_returns_correct_data()
    test_telegram_session_id_does_not_collide_with_web()
    print("\nAll conversation_service tests PASSED successfully!")
