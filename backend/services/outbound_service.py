"""Service d'envoi du premier contact Telegram vers les leads entrants.

Responsabilités :
- Sélectionner les leads Airtable avec Statut == "New" ET Telegram Chat ID présent.
- Envoyer le message d'accueil OUTBOUND_1 (premier contact).
- Mettre à jour le CRM : Statut → "Contacted", Dernier contact, Nombre de tentatives.

Fonctions publiques :
    select_outbound_leads(limit)          -> list[dict]
    send_first_contact(lead_fields)       -> bool
    run_outbound(limit, dry_run)          -> dict
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.config import TELEGRAM_BOT_TOKEN
from backend.airtable_client import AirtableClient
from backend.integrations.telegram.client import TelegramClient
from backend.services.follow_up_sender import render_template

logger = logging.getLogger(__name__)

# Clé du template utilisé pour le premier contact (défini dans follow_up_templates.md)
_FIRST_CONTACT_TEMPLATE_KEY = "WARM_1"

# Statut Airtable des leads jamais contactés
_STATUS_NEW = "New"
_STATUS_CONTACTED = "Contacted"


# ---------------------------------------------------------------------------
# Sélection des leads
# ---------------------------------------------------------------------------

def select_outbound_leads(limit: int = 50) -> List[Dict[str, Any]]:
    """Retourne les leads Airtable éligibles au premier contact Telegram.

    Critères :
    - Statut == "New"
    - Telegram Chat ID présent et non vide

    Args:
        limit: Nombre maximum de leads à retourner.

    Returns:
        Liste de records Airtable (chaque record = {"id": ..., "fields": {...}}).
    """
    try:
        airtable = AirtableClient()
        formula = f'AND({{Statut}} = "{_STATUS_NEW}", {{Telegram Chat ID}} != "")'
        params = {"filterByFormula": formula, "maxRecords": limit}
        data = airtable.list_records("Leads", params=params)
        records = data.get("records", [])
        logger.info("select_outbound_leads : %d lead(s) éligible(s) trouvé(s).", len(records))
        return records
    except Exception as exc:
        logger.error("select_outbound_leads : erreur Airtable — %s", exc)
        return []


# ---------------------------------------------------------------------------
# Envoi du premier contact
# ---------------------------------------------------------------------------

def send_first_contact(lead_fields: Dict[str, Any]) -> bool:
    """Envoie le message de premier contact au lead via Telegram.

    Args:
        lead_fields: Dict des champs Airtable du lead.

    Returns:
        True si le message a été envoyé avec succès, False sinon.
    """
    chat_id_raw = lead_fields.get("Telegram Chat ID")
    if not chat_id_raw:
        logger.warning(
            "send_first_contact: lead '%s %s' sans Telegram Chat ID — ignoré.",
            lead_fields.get("Prénom", ""),
            lead_fields.get("Nom", ""),
        )
        return False

    try:
        chat_id = int(str(chat_id_raw).strip())
    except (ValueError, TypeError):
        logger.warning("send_first_contact: Chat ID invalide : %r", chat_id_raw)
        return False

    if not TELEGRAM_BOT_TOKEN:
        logger.error("send_first_contact: TELEGRAM_BOT_TOKEN non configuré.")
        return False

    try:
        text = render_template(_FIRST_CONTACT_TEMPLATE_KEY, lead_fields)
    except KeyError as exc:
        logger.error("send_first_contact: template introuvable — %s", exc)
        return False

    try:
        client = TelegramClient(token=TELEGRAM_BOT_TOKEN)
        client.send_message(chat_id=chat_id, text=text)
        logger.info(
            "Premier contact envoyé à chat_id=%s (%s %s).",
            chat_id,
            lead_fields.get("Prénom", ""),
            lead_fields.get("Nom", ""),
        )
        return True
    except Exception as exc:
        logger.error("send_first_contact: échec Telegram — %s", exc)
        return False


# ---------------------------------------------------------------------------
# Mise à jour CRM après envoi
# ---------------------------------------------------------------------------

def _mark_as_contacted(airtable: AirtableClient, record_id: str) -> None:
    """Met à jour le lead dans Airtable après le premier contact réussi.

    Champs mis à jour :
    - Statut            → "Contacted"
    - Dernier contact   → date UTC courante
    - Nombre de tentatives → 1

    Args:
        airtable:  Instance AirtableClient.
        record_id: Identifiant Airtable du lead.
    """
    now_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        airtable.update_record("Leads", record_id, {
            "Statut": _STATUS_CONTACTED,
            "Dernier contact": now_date,
            "Nombre de tentatives": 1,
        })
        logger.info("CRM mis à jour pour le lead %s → Contacted.", record_id)
    except Exception as exc:
        logger.warning("_mark_as_contacted: impossible de mettre à jour %s — %s", record_id, exc)


# ---------------------------------------------------------------------------
# Orchestrateur principal
# ---------------------------------------------------------------------------

def run_outbound(limit: int = 50, dry_run: bool = False) -> Dict[str, int]:
    """Sélectionne les leads New, envoie le premier contact et met à jour le CRM.

    Args:
        limit:   Nombre maximum de leads à traiter en une exécution.
        dry_run: Si True, affiche les actions prévues sans envoyer ni modifier Airtable.

    Returns:
        Dict avec les compteurs : {"sent": int, "skipped": int, "errors": int}.
    """
    if dry_run:
        logger.info("=== MODE DRY-RUN — aucun message ne sera envoyé ===")

    records = select_outbound_leads(limit=limit)
    if not records:
        logger.info("run_outbound : aucun lead à contacter.")
        return {"sent": 0, "skipped": 0, "errors": 0}

    try:
        airtable = AirtableClient()
    except ValueError as exc:
        logger.error("run_outbound : configuration Airtable invalide — %s", exc)
        return {"sent": 0, "skipped": 0, "errors": 0}

    sent = skipped = errors = 0

    for record in records:
        record_id: str = record["id"]
        fields: Dict[str, Any] = record.get("fields", {})
        prenom = fields.get("Prénom") or fields.get("Prenom") or "—"
        nom = fields.get("Nom") or "—"
        label = f"{prenom} {nom} ({record_id})"

        if not fields.get("Telegram Chat ID"):
            logger.debug("SKIP %s — pas de Telegram Chat ID", label)
            skipped += 1
            continue

        logger.info("SEND %s — premier contact outbound", label)

        if dry_run:
            sent += 1
            continue

        success = send_first_contact(fields)
        if success:
            _mark_as_contacted(airtable, record_id)
            sent += 1
        else:
            errors += 1

    logger.info(
        "run_outbound terminé : %d envoyé(s), %d ignoré(s), %d erreur(s).",
        sent, skipped, errors,
    )
    return {"sent": sent, "skipped": skipped, "errors": errors}
