"""Script de relance automatique — Phase 4.

Récupère tous les leads depuis Airtable, classifie chacun (Hot/Warm/Cold),
vérifie si une relance est due, envoie le message Telegram et met à jour
les champs CRM (Nombre de tentatives, Dernier contact).

Usage :
    python scripts/run_follow_up.py           # mode réel
    python scripts/run_follow_up.py --dry-run # affiche sans envoyer
"""

import sys
import os
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from backend.airtable_client import AirtableClient
from backend.services.follow_up_classifier import classify_lead, should_follow_up_now
from backend.services.follow_up_sender import send_follow_up
from backend.agent.graph import calculate_lead_score


def _increment_attempts(client: AirtableClient, record_id: str, current: int) -> None:
    """Incrémente Nombre de tentatives et met à jour Dernier contact."""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    # Essai avec date+heure, fallback sur date seule si le champ Airtable est de type Date
    try:
        client.update_record("Leads", record_id, {
            "Nombre de tentatives": current + 1,
            "Dernier contact": now_iso,
        })
    except Exception:
        try:
            client.update_record("Leads", record_id, {
                "Nombre de tentatives": current + 1,
                "Dernier contact": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            })
        except Exception as exc:
            print(f"  [WARN] Impossible de mettre à jour le lead {record_id} : {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Envoi des relances Telegram aux leads Ecofix.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche les relances prévues sans les envoyer ni modifier Airtable.",
    )
    args = parser.parse_args()
    dry_run: bool = args.dry_run

    if dry_run:
        print("=== MODE DRY-RUN — aucun message ne sera envoyé ===\n")

    try:
        airtable = AirtableClient()
    except ValueError as exc:
        print(f"Erreur de configuration Airtable : {exc}")
        sys.exit(1)

    # Récupère tous les leads (pagination automatique via offset si nécessaire)
    try:
        data = airtable.list_records("Leads")
        records = data.get("records", [])
    except Exception as exc:
        print(f"Erreur lors de la récupération des leads : {exc}")
        sys.exit(1)

    print(f"{len(records)} lead(s) récupéré(s) depuis Airtable.\n")

    sent = 0
    skipped = 0
    errors = 0

    for record in records:
        record_id: str = record["id"]
        fields: dict = record.get("fields", {})
        prenom = fields.get("Prénom") or fields.get("Prenom") or "—"
        nom = fields.get("Nom") or "—"
        label = f"{prenom} {nom} ({record_id})"

        # Si Score IA absent (leads importés CSV sans passer par le graphe),
        # on le calcule à la volée avec les règles déterministes de graph.py.
        if fields.get("Score IA") is None:
            fields["Score IA"] = calculate_lead_score(fields)

        category = classify_lead(fields)
        if category is None or category == "Rejected":
            print(f"  SKIP  {label} — catégorie : {category}")
            skipped += 1
            continue

        if not should_follow_up_now(fields, category):
            print(f"  WAIT  {label} — {category} — pas encore le moment")
            skipped += 1
            continue

        chat_id = fields.get("Telegram Chat ID")
        if not chat_id:
            print(f"  SKIP  {label} — {category} — pas de Telegram Chat ID")
            skipped += 1
            continue

        attempts = int(fields.get("Nombre de tentatives", 0) or 0)
        print(f"  SEND  {label} — {category} — tentative {attempts + 1}")

        if dry_run:
            sent += 1
            continue

        success = send_follow_up(fields, category)
        if success:
            _increment_attempts(airtable, record_id, attempts)
            sent += 1
        else:
            print(f"         → Échec d'envoi pour {label}")
            errors += 1

    print(f"\nRésultat : {sent} envoyé(s), {skipped} ignoré(s), {errors} erreur(s).")


if __name__ == "__main__":
    main()
