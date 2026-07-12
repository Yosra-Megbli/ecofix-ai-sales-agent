"""Script one-shot : envoie un message à tous les leads ayant un Telegram Chat ID.

Contrairement à run_follow_up.py, ce script ignore le timing (Dernier contact,
Nombre de tentatives) et envoie à tous les leads avec un Chat ID valide.

Usage :
    python scripts/broadcast_telegram.py           # envoi réel
    python scripts/broadcast_telegram.py --dry-run # affiche sans envoyer
"""

import sys
import os
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from backend.config import TELEGRAM_BOT_TOKEN
from backend.airtable_client import AirtableClient
from backend.integrations.telegram.client import TelegramClient
from backend.services.follow_up_classifier import classify_lead
from backend.services.follow_up_sender import render_template
from backend.agent.graph import calculate_lead_score

# Clé de template par catégorie (1re tentative)
_TEMPLATE_BY_CATEGORY = {
    "Hot":  "HOT_1",
    "Warm": "WARM_1",
    "Cold": "COLD_1",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Broadcast Telegram à tous les leads avec Chat ID.")
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

    # Filtrer uniquement les leads avec Telegram Chat ID
    targets = [r for r in records if r.get("fields", {}).get("Telegram Chat ID")]
    print(f"{len(records)} leads récupérés — {len(targets)} avec Telegram Chat ID.\n")

    client = TelegramClient(token=TELEGRAM_BOT_TOKEN)
    sent = skipped = errors = 0

    for record in targets:
        record_id = record["id"]
        fields = record.get("fields", {})
        prenom = fields.get("Prénom") or fields.get("Prenom") or "—"
        nom = fields.get("Nom") or "—"
        label = f"{prenom} {nom} ({record_id})"

        chat_id_raw = fields.get("Telegram Chat ID", "")
        try:
            chat_id = int(str(chat_id_raw).strip())
        except (ValueError, TypeError):
            print(f"  SKIP  {label} — Chat ID invalide : {chat_id_raw!r}")
            skipped += 1
            continue

        # Calcul score à la volée si absent
        if fields.get("Score IA") is None:
            fields["Score IA"] = calculate_lead_score(fields)

        category = classify_lead(fields)
        if category in (None, "Rejected"):
            print(f"  SKIP  {label} — catégorie : {category}")
            skipped += 1
            continue

        template_key = _TEMPLATE_BY_CATEGORY.get(category, "WARM_1")

        try:
            text = render_template(template_key, fields)
        except KeyError as exc:
            print(f"  SKIP  {label} — template introuvable : {exc}")
            skipped += 1
            continue

        print(f"  SEND  {label} — {category} ({template_key}) — chat_id={chat_id}")
        if dry_run:
            sent += 1
            continue

        try:
            client.send_message(chat_id=chat_id, text=text)
            # Mise à jour CRM
            attempts = int(fields.get("Nombre de tentatives", 0) or 0)
            try:
                airtable.update_record("Leads", record_id, {
                    "Nombre de tentatives": attempts + 1,
                    "Dernier contact": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                })
            except Exception as exc:
                print(f"    [WARN] CRM non mis à jour : {exc}")
            sent += 1
        except Exception as exc:
            print(f"  ERROR {label} — {exc}")
            errors += 1

    print(f"\nRésultat : {sent} envoyé(s), {skipped} ignoré(s), {errors} erreur(s).")


if __name__ == "__main__":
    main()
