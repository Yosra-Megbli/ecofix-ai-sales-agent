"""Minimal HTTP client for the Telegram Bot API.

Uses only `requests` (already a project dependency) — no extra library needed.
Covers the three methods required by the polling loop:
  - get_updates   : long-polling for new messages
  - send_message  : reply to a chat
  - send_chat_action : show "typing…" indicator
"""

import requests
from typing import Any, Dict, List, Optional

_BASE = "https://api.telegram.org/bot{token}/{method}"


class TelegramClient:
    """Thin wrapper around the Telegram Bot HTTP API."""

    def __init__(self, token: str, timeout: int = 30) -> None:
        """
        Args:
            token:   Bot token obtained from BotFather.
            timeout: HTTP read timeout in seconds (also used as long-poll window).
        """
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is empty — set it in .env")
        self._token = token
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _url(self, method: str) -> str:
        return _BASE.format(token=self._token, method=method)

    def _post(self, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST to the Telegram API and return the parsed JSON result."""
        resp = requests.post(
            self._url(method),
            json=payload,
            timeout=self._timeout + 5,  # slightly above the long-poll window
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API error on {method}: {data}")
        return data.get("result", {})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_updates(self, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch pending updates via long polling.

        Args:
            offset: Identifier of the first update to return (all previous
                    updates are confirmed as processed).

        Returns:
            List of Update objects (may be empty).
        """
        payload: Dict[str, Any] = {"timeout": self._timeout, "allowed_updates": ["message"]}
        if offset is not None:
            payload["offset"] = offset
        result = self._post("getUpdates", payload)
        # result is a list when ok=True for getUpdates
        return result if isinstance(result, list) else []

    def send_message(self, chat_id: int, text: str) -> Dict[str, Any]:
        """
        Send a text message to a chat.

        Args:
            chat_id: Telegram chat identifier.
            text:    Message text (plain text, max 4096 chars).

        Returns:
            Sent Message object.
        """
        # Telegram max message length is 4096 characters
        if len(text) > 4096:
            text = text[:4093] + "…"
        return self._post("sendMessage", {"chat_id": chat_id, "text": text})

    def send_chat_action(self, chat_id: int, action: str = "typing") -> None:
        """
        Send a chat action (e.g. "typing") to show activity to the user.

        Args:
            chat_id: Telegram chat identifier.
            action:  One of the Telegram ChatAction values (default: "typing").
        """
        try:
            self._post("sendChatAction", {"chat_id": chat_id, "action": action})
        except Exception:
            pass  # Non-critical — ignore failures silently
