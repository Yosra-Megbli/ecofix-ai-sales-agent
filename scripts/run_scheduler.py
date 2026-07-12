"""Scheduler automatique — lance outbound + follow-up chaque jour.

Utilise APScheduler (BlockingScheduler) pour exécuter deux tâches :
  - 09:00 UTC : run_outbound()   → premier contact aux leads New
  - 09:30 UTC : run_follow_up()  → relances Hot/Warm/Cold

Usage :
    python scripts/run_scheduler.py              # démarre le scheduler
    python scripts/run_scheduler.py --once       # exécute une fois immédiatement et quitte
    python scripts/run_scheduler.py --dry-run    # exécute une fois en mode dry-run et quitte
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

from backend.services.outbound_service import run_outbound
from backend.services.follow_up_classifier import classify_lead, should_follow_up_now
from backend.services.follow_up_sender import send_follow_up
from backend.airtable_client import AirtableClient
from backend.agent.graph import calculate_lead_score
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Tâche follow-up (extraite de run_follow_up.py pour être appelable)
# ---------------------------------------------------------------------------

def _run_follow_up(dry_run: bool = False) -> dict:
    """Exécute la relance automatique sur tous les leads éligibles."""

    try:
        airtable = AirtableClient()
        records = airtable.list_records("Leads").get("records", [])
    except Exception as exc:
        logger.error("_run_follow_up : erreur Airtable — %s", exc)
        return {"sent": 0, "skipped": 0, "errors": 0}

    sent = skipped = errors = 0

    for record in records:
        record_id: str = record["id"]
        fields: dict = record.get("fields", {})

        if fields.get("Score IA") is None:
            fields["Score IA"] = calculate_lead_score(fields)

        category = classify_lead(fields)
        if category in (None, "Rejected"):
            skipped += 1
            continue

        if not should_follow_up_now(fields, category):
            skipped += 1
            continue

        if not fields.get("Telegram Chat ID"):
            skipped += 1
            continue

        attempts = int(fields.get("Nombre de tentatives", 0) or 0)
        logger.info(
            "SEND %s %s — %s — tentative %d",
            fields.get("Prénom", ""), fields.get("Nom", ""), category, attempts + 1,
        )

        if dry_run:
            sent += 1
            continue

        success = send_follow_up(fields, category)
        if success:
            now_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            try:
                airtable.update_record("Leads", record_id, {
                    "Nombre de tentatives": attempts + 1,
                    "Dernier contact": now_date,
                })
            except Exception as exc:
                logger.warning("CRM non mis à jour pour %s — %s", record_id, exc)
            sent += 1
        else:
            errors += 1

    logger.info(
        "follow_up terminé : %d envoyé(s), %d ignoré(s), %d erreur(s).",
        sent, skipped, errors,
    )
    return {"sent": sent, "skipped": skipped, "errors": errors}


# ---------------------------------------------------------------------------
# Jobs planifiés
# ---------------------------------------------------------------------------

def job_outbound() -> None:
    """Job 09:00 UTC — premier contact aux leads New."""
    logger.info("=== JOB OUTBOUND démarré ===")
    result = run_outbound(limit=100, dry_run=False)
    logger.info("=== JOB OUTBOUND terminé : %s ===", result)


def job_follow_up() -> None:
    """Job 09:30 UTC — relances Hot/Warm/Cold."""
    logger.info("=== JOB FOLLOW-UP démarré ===")
    result = _run_follow_up(dry_run=False)
    logger.info("=== JOB FOLLOW-UP terminé : %s ===", result)


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Scheduler automatique Ecofix.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Exécute outbound + follow-up une seule fois immédiatement et quitte.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Exécute une fois en mode dry-run (affiche sans envoyer) et quitte.",
    )
    args = parser.parse_args()

    # Mode one-shot (--once ou --dry-run)
    if args.once or args.dry_run:
        dry = args.dry_run
        logger.info("Mode one-shot (dry_run=%s)", dry)
        r1 = run_outbound(limit=100, dry_run=dry)
        r2 = _run_follow_up(dry_run=dry)
        print(f"\nOutbound  : {r1}")
        print(f"Follow-up : {r2}")
        return

    # Mode scheduler continu
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("APScheduler non installé. Lancez : pip install apscheduler==3.10.4")
        sys.exit(1)

    scheduler = BlockingScheduler(timezone="UTC")

    # Outbound : chaque jour à 09:00 UTC
    scheduler.add_job(
        job_outbound,
        CronTrigger(hour=9, minute=0),
        id="outbound",
        name="Premier contact leads New",
        replace_existing=True,
    )

    # Follow-up : chaque jour à 09:30 UTC
    scheduler.add_job(
        job_follow_up,
        CronTrigger(hour=9, minute=30),
        id="follow_up",
        name="Relances Hot/Warm/Cold",
        replace_existing=True,
    )

    logger.info("Scheduler démarré — jobs planifiés :")
    logger.info("  • Outbound  : chaque jour à 09:00 UTC")
    logger.info("  • Follow-up : chaque jour à 09:30 UTC")
    logger.info("  Ctrl+C pour arrêter.")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler arrêté par l'utilisateur.")


if __name__ == "__main__":
    main()
