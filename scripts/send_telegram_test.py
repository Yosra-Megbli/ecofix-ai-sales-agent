"""Script ponctuel pour envoyer un message Telegram via TelegramClient.

Usage :
    python scripts/send_telegram_test.py <chat_id> [message]

Exemples :
    python scripts/send_telegram_test.py 8867809811
    python scripts/send_telegram_test.py 8867809811 "Bonjour depuis Ecofix !"
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

DEFAULT_MESSAGE = (
    "Bonjour ! Ceci est un message envoyé automatiquement par l'agent Ecofix, "
    "sans que vous ayez besoin d'écrire en premier."
)


def main():
    if len(sys.argv) < 2:
        print("Usage : python scripts/send_telegram_test.py <chat_id> [message]")
        sys.exit(1)

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print(
            "Erreur : TELEGRAM_BOT_TOKEN n'est pas configuré.\n"
            "Ajoutez la ligne suivante dans votre fichier .env :\n"
            "  TELEGRAM_BOT_TOKEN=<votre_token_botfather>"
        )
        sys.exit(1)

    try:
        chat_id = int(sys.argv[1])
    except ValueError:
        print(f"Erreur : chat_id doit être un entier, reçu : {sys.argv[1]!r}")
        sys.exit(1)

    text = sys.argv[2] if len(sys.argv) >= 3 else DEFAULT_MESSAGE

    from backend.integrations.telegram.client import TelegramClient

    client = TelegramClient(token=token)

    try:
        result = client.send_message(chat_id=chat_id, text=text)
        message_id = result.get("message_id", "?")
        print(f"Message envoyé avec succès. (message_id={message_id})")
    except Exception as e:
        print(f"Échec de l'envoi : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
