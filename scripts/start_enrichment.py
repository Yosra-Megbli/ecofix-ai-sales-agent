"""Script de démarrage de l'enrichissement des leads incomplets via Telegram.

Pour chaque lead ayant un Telegram Chat ID et des champs manquants,
envoie un message de bienvenue et active le mode enrichment dans la session.

Usage :
    python scripts/start_enrichment.py           # mode réel
    python scripts/start_enrichment.py --dry-run # affiche sans envoyer
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from backend.config import TELEGRAM_BOT_TOKEN
from backend.airtable_client import AirtableClient
from backend.integrations.telegram.client import TelegramClient
from backend.services import session_store
from backend.services.enrichment_service import missing_fields, start_enrichment


def main() -> None:
    parser = argparse.ArgumentParser(description="Démarre l'enrichissement des leads incomplets.")
    parser.add_argument("--dry-run", action="store_true", help="Affiche sans envoyer.")
    args = parser.parse_args()
    dry_run: bool = args.dry_run

    if dry_run:
        print("=== MODE DRY-RUN — aucun message ne sera envoyé ===\n")

    if not TELEGRAM_BOT_TOKEN:
        print("Erreur : TELEGRAM_BOT_TOKEN non configuré dans .env")
        sys.exit(1)

    try:
        airtable = AirtableClient()
    except ValueError as exc:
        print(f"Erreur Airtable : {exc}")
        sys.exit(1)

    try:
        records = airtable.list_records("Leads").get("records", [])
    except Exception as exc:
        print(f"Erreur récupération leads : {exc}")
        sys.exit(1)

    # Filtrer : Chat ID présent + au moins un champ manquant
    targets = []
    for record in records:
        fields = record.get("fields", {})
        chat_id_raw = str(fields.get("Telegram Chat ID") or "").strip()
        if not chat_id_raw:
            continue
        try:
            chat_id = int(chat_id_raw)
        except ValueError:
            continue
        missing = missing_fields(fields)
        if missing:
            targets.append((record["id"], chat_id, fields, missing))

    print(f"{len(records)} leads récupérés — {len(targets)} à enrichir.\n")

    if not targets:
        print("Aucun lead à enrichir.")
        return

    client = TelegramClient(token=TELEGRAM_BOT_TOKEN)
    sent = skipped = errors = 0

    for record_id, chat_id, fields, missing in targets:
        prenom = fields.get("Prénom") or fields.get("Prenom") or "—"
        nom = fields.get("Nom") or "—"
        label = f"{prenom} {nom} ({record_id})"
        print(f"  ENRICH  {label} — champs manquants : {', '.join(missing)}")

        if dry_run:
            sent += 1
            continue

        # Activer le mode enrichment dans la session
        session_id = f"telegram:{chat_id}"
        welcome_msg = start_enrichment(session_id, record_id, missing)

        try:
            client.send_message(chat_id=chat_id, text=welcome_msg)
            sent += 1
            print(f"          → Message envoyé à chat_id={chat_id}")
        except Exception as exc:
            print(f"  ERROR   {label} — {exc}")
            # Désactiver le mode enrichment si l'envoi échoue
            state = session_store.get_session(session_id)
            state["enrichment_mode"] = False
            session_store.set_session(session_id, state)
            errors += 1

    print(f"\nRésultat : {sent} démarré(s), {skipped} ignoré(s), {errors} erreur(s).")


if __name__ == "__main__":
    main()
