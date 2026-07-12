"""Service de gestion des campagnes Ecofix.

Responsabilités :
- Calculer les statistiques d'une campagne depuis Airtable (leads, contacts,
  qualifiés, convertis, taux de conversion).
- Lister toutes les campagnes avec leur statut.
- Créer une nouvelle campagne dans Airtable.

Fonctions publiques :
    get_campaign_stats(campaign_name)   -> dict
    list_campaigns()                    -> list[dict]
    create_campaign(fields)             -> dict
"""

import logging
from typing import Any, Dict, List, Optional

from backend.airtable_client import AirtableClient

logger = logging.getLogger(__name__)

# Statuts considérés comme "contactés"
_CONTACTED_STATUSES = {"Contacted", "Replied", "Qualified", "Appointment", "Contract Sent", "Sold"}
# Statuts considérés comme "qualifiés"
_QUALIFIED_STATUSES = {"Qualified", "Appointment", "Contract Sent", "Sold"}
# Statut converti
_CONVERTED_STATUSES = {"Sold"}


# ---------------------------------------------------------------------------
# Statistiques d'une campagne
# ---------------------------------------------------------------------------

def get_campaign_stats(campaign_name: Optional[str] = None) -> Dict[str, Any]:
    """Calcule les statistiques de leads depuis Airtable.

    Si campaign_name est fourni, filtre les leads par ce nom de campagne
    (champ "Campagne" dans Airtable). Sinon, calcule sur tous les leads.

    Args:
        campaign_name: Nom de la campagne à filtrer (optionnel).

    Returns:
        Dict avec les métriques :
        {
            "campaign": str,
            "total_leads": int,
            "contacted": int,
            "qualified": int,
            "converted": int,
            "contact_rate": float,      # contacted / total * 100
            "qualification_rate": float, # qualified / contacted * 100
            "conversion_rate": float,    # converted / qualified * 100
        }
    """
    try:
        airtable = AirtableClient()

        params: Dict[str, Any] = {}
        if campaign_name:
            params["filterByFormula"] = f'{{Campagne}} = "{campaign_name}"'

        data = airtable.list_records("Leads", params=params if params else None)
        records = data.get("records", [])
    except Exception as exc:
        logger.error("get_campaign_stats : erreur Airtable — %s", exc)
        return {}

    total = len(records)
    contacted = 0
    qualified = 0
    converted = 0

    for record in records:
        statut = record.get("fields", {}).get("Statut", "New")
        if statut in _CONTACTED_STATUSES:
            contacted += 1
        if statut in _QUALIFIED_STATUSES:
            qualified += 1
        if statut in _CONVERTED_STATUSES:
            converted += 1

    contact_rate = round(contacted / total * 100, 1) if total else 0.0
    qualification_rate = round(qualified / contacted * 100, 1) if contacted else 0.0
    conversion_rate = round(converted / qualified * 100, 1) if qualified else 0.0

    stats = {
        "campaign": campaign_name or "Toutes campagnes",
        "total_leads": total,
        "contacted": contacted,
        "qualified": qualified,
        "converted": converted,
        "contact_rate": contact_rate,
        "qualification_rate": qualification_rate,
        "conversion_rate": conversion_rate,
    }

    logger.info(
        "Stats [%s] : %d leads, %d contactés (%.1f%%), %d qualifiés, %d convertis.",
        stats["campaign"], total, contacted, contact_rate, qualified, converted,
    )
    return stats


# ---------------------------------------------------------------------------
# Liste des campagnes
# ---------------------------------------------------------------------------

def list_campaigns() -> List[Dict[str, Any]]:
    """Retourne toutes les campagnes depuis la table Campaigns d'Airtable.

    Returns:
        Liste de dicts {id, name, lead_count, start_date, end_date, status}.
    """
    try:
        airtable = AirtableClient()
        data = airtable.list_records("Campaigns")
        records = data.get("records", [])
    except Exception as exc:
        logger.error("list_campaigns : erreur Airtable — %s", exc)
        return []

    campaigns = []
    for record in records:
        fields = record.get("fields", {})
        campaigns.append({
            "id": record["id"],
            "name": fields.get("Nom campagne", ""),
            "lead_count": fields.get("Nombre prospects", 0),
            "start_date": fields.get("Début"),
            "end_date": fields.get("Fin"),
            "status": fields.get("Statut", "Planifiée"),
            "description": fields.get("Description", ""),
            "responsable": fields.get("Responsable campagne", ""),
        })

    logger.info("list_campaigns : %d campagne(s) trouvée(s).", len(campaigns))
    return campaigns


# ---------------------------------------------------------------------------
# Création d'une campagne
# ---------------------------------------------------------------------------

def create_campaign(
    name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    lead_count: int = 0,
    description: Optional[str] = None,
    responsable: Optional[str] = None,
) -> Dict[str, Any]:
    """Crée une nouvelle campagne dans Airtable.

    Args:
        name:         Nom de la campagne (ex: "Belgique Juillet 2026").
        start_date:   Date de début ISO (ex: "2026-07-01").
        end_date:     Date de fin ISO (ex: "2026-07-31").
        lead_count:   Nombre de prospects prévus.
        description:  Description libre de la campagne.
        responsable:  Nom du responsable campagne.

    Returns:
        Record Airtable créé, ou dict vide en cas d'erreur.
    """
    fields: Dict[str, Any] = {
        "Nom campagne": name,
        "Statut": "Planifiée",
        "Nombre prospects": lead_count,
    }
    if start_date:
        fields["Début"] = start_date
    if end_date:
        fields["Fin"] = end_date
    if description:
        fields["Description"] = description
    # Responsable campagne est un champ Collaborateur (User) Airtable —
    # ne peut pas être écrit via l'API sans un user ID valide ("usr...")

    try:
        airtable = AirtableClient()
        record = airtable.create_record("Campaigns", fields)
        logger.info("Campagne créée : %s (id=%s).", name, record.get("id"))
        return record
    except Exception as exc:
        logger.error("create_campaign : erreur Airtable — %s", exc)
        return {}
