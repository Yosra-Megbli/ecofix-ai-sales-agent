"""Telegram bot polling loop for the Ecofix AI Sales Agent.

Run as a standalone process (independently of the FastAPI server):

    python -m backend.integrations.telegram.bot

The bot maps each Telegram chat_id to a deterministic session_id of the form
"telegram:{chat_id}" so it never collides with web-chat sessions.

Supported commands / messages:
  /start  — resets the session and sends the initial greeting
  <text>  — forwarded to conversation_service.send_message()
"""

import time
import logging
from typing import Optional

from backend.config import TELEGRAM_BOT_TOKEN
from backend.integrations.telegram.client import TelegramClient
from backend.services import conversation_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Seconds to wait before retrying after a network/API error
_RETRY_DELAYS = [2, 5, 10, 30, 60]


def _session_id(chat_id: int) -> str:
    """Build a deterministic session_id from a Telegram chat_id."""
    return f"telegram:{chat_id}"


def _handle_update(client: TelegramClient, update: dict) -> None:
    """
    Process a single Telegram update.

    Args:
        client: TelegramClient instance.
        update: Raw Update dict from the Telegram API.
    """
    message = update.get("message")
    if not message:
        return  # Ignore non-message updates (edited messages, etc.)

    chat_id: int = message["chat"]["id"]
    text: Optional[str] = message.get("text", "").strip()

    if not text:
        return  # Ignore stickers, photos, etc.

    session_id = _session_id(chat_id)

    try:
        client.send_chat_action(chat_id, "typing")

        if text == "/start":
            reply, _ = conversation_service.start_session(session_id)
        else:
            reply, _ = conversation_service.send_message(session_id, text)

        client.send_message(chat_id, reply)

    except Exception as e:
        logger.error("Error handling update for chat_id=%s: %s", chat_id, e)
        try:
            client.send_message(
                chat_id,
                "Une erreur est survenue. Veuillez réessayer dans quelques instants.",
            )
        except Exception:
            pass  # If we can't even send the error message, give up silently


def run_polling(client: TelegramClient) -> None:
    """
    Main long-polling loop. Runs indefinitely until interrupted (Ctrl+C).

    Implements exponential backoff on consecutive errors to avoid hammering
    the Telegram API when the network is unstable.

    Args:
        client: Configured TelegramClient instance.
    """
    logger.info("Telegram bot started — polling for updates…")
    offset: Optional[int] = None
    error_count = 0

    while True:
        try:
            updates = client.get_updates(offset=offset)
            error_count = 0  # reset on success

            for update in updates:
                update_id: int = update["update_id"]
                _handle_update(client, update)
                offset = update_id + 1  # acknowledge this update

        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break

        except Exception as e:
            delay = _RETRY_DELAYS[min(error_count, len(_RETRY_DELAYS) - 1)]
            logger.warning(
                "Polling error (attempt %d): %s — retrying in %ds",
                error_count + 1,
                e,
                delay,
            )
            error_count += 1
            time.sleep(delay)


def main() -> None:
    """Entry point: validate config, build client, start polling."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Add it to your .env file:\n  TELEGRAM_BOT_TOKEN=<your_token>"
        )

    client = TelegramClient(token=TELEGRAM_BOT_TOKEN)
    run_polling(client)


if __name__ == "__main__":
    main()
