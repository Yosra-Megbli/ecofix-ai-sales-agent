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
from backend.services import session_store
from backend.services import enrichment_service
from backend.airtable_client import AirtableClient

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


def _sync_telegram_chat_id(chat_id: int, session_id: str) -> None:
    """Met à jour le champ 'Telegram Chat ID' du lead dans Airtable si nécessaire.

    Recherche le lead via email ou téléphone déjà collectés dans la session
    en mémoire. Si un record est trouvé et que son 'Telegram Chat ID' est
    absent ou différent, il est mis à jour. Silencieux en cas d'erreur.

    Args:
        chat_id:    Identifiant Telegram de l'utilisateur.
        session_id: Identifiant de session en mémoire (ex: 'telegram:123').
    """
    try:
        if not session_store.session_exists(session_id):
            return

        state = session_store.get_session(session_id)
        lead_info = state.get("lead_info") or {}
        email = lead_info.get("Email")
        phone = lead_info.get("Telephone")

        if not email and not phone:
            return  # Pas encore assez d'infos pour retrouver le lead

        airtable = AirtableClient()
        record = airtable.find_duplicate_lead(
            table_name="Leads",
            email=email,
            phone=phone,
        )
        if not record:
            return

        record_id = record["id"]
        existing_chat_id = str(record.get("fields", {}).get("Telegram Chat ID", "") or "")
        new_chat_id = str(chat_id)

        if existing_chat_id != new_chat_id:
            airtable.update_record("Leads", record_id, {"Telegram Chat ID": new_chat_id})
            logger.info("Telegram Chat ID mis à jour pour le lead %s → %s", record_id, new_chat_id)

    except Exception as exc:
        logger.warning("_sync_telegram_chat_id: erreur non bloquante — %s", exc)


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

        # Mode enrichment : collecte des champs manquants
        state = session_store.get_session(session_id)
        if state.get("enrichment_mode") and text != "/start":
            reply = enrichment_service.handle_reply(session_id, text)
        elif text == "/start":
            reply, _ = conversation_service.start_session(session_id)
        else:
            reply, _ = conversation_service.send_message(session_id, text)

        client.send_message(chat_id, reply)

        # Tente de lier le chat_id au lead Airtable (non bloquant)
        _sync_telegram_chat_id(chat_id, session_id)

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
