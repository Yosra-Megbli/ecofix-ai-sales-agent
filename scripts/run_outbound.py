"""Script de premier contact outbound — envoie le 1er message aux leads New.

Récupère les leads Airtable avec Statut == "New" et Telegram Chat ID présent,
envoie le message WARM_1 et met à jour le CRM (Statut → Contacted).

Usage :
    python scripts/run_outbound.py                  # mode réel (50 leads max)
    python scripts/run_outbound.py --dry-run        # affiche sans envoyer
    python scripts/run_outbound.py --limit 20       # limite à 20 leads
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

from backend.services.outbound_service import run_outbound


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Envoie le premier contact Telegram aux leads New."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche les actions prévues sans envoyer ni modifier Airtable.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Nombre maximum de leads à traiter (défaut : 50).",
    )
    args = parser.parse_args()

    result = run_outbound(limit=args.limit, dry_run=args.dry_run)
    print(
        f"\nRésultat : {result['sent']} envoyé(s), "
        f"{result['skipped']} ignoré(s), "
        f"{result['errors']} erreur(s)."
    )


if __name__ == "__main__":
    main()
