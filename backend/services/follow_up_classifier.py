"""Classification automatique des leads pour la stratégie de relance.

Règles fidèles à docs/knowledge_base/follow_up_strategy.md et
docs/knowledge_base/lead_scoring.md.

Fonctions publiques :
    classify_lead(lead_fields)         -> "Hot" | "Warm" | "Cold" | "Rejected" | None
    should_follow_up_now(lead_fields, category) -> bool
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Constantes de timing (fidèles à follow_up_strategy.md)
# ---------------------------------------------------------------------------

_HOT_DELAY_HOURS: int = 24          # relance Hot : dans les 24 h
_WARM_DELAYS_DAYS: list = [3, 7]    # relance Warm : J+3 puis J+7
_COLD_MAX_ATTEMPTS: int = 2         # Cold : 2 tentatives max puis stop


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _parse_last_contact(lead_fields: dict) -> Optional[datetime]:
    """Retourne la date du dernier contact en UTC, ou None si absente/invalide."""
    raw = lead_fields.get("Dernier contact")
    if not raw:
        return None
    try:
        # Airtable renvoie ISO 8601 avec ou sans 'Z'
        raw = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(raw).astimezone(timezone.utc)
    except (ValueError, AttributeError):
        return None


def _hours_since_last_contact(lead_fields: dict) -> Optional[float]:
    """Retourne le nombre d'heures écoulées depuis le dernier contact, ou None."""
    last = _parse_last_contact(lead_fields)
    if last is None:
        return None
    return (datetime.now(timezone.utc) - last).total_seconds() / 3600


def _attempts(lead_fields: dict) -> int:
    """Retourne le nombre de tentatives de relance (0 si champ absent)."""
    try:
        return int(lead_fields.get("Nombre de tentatives", 0) or 0)
    except (ValueError, TypeError):
        return 0


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def classify_lead(lead_fields: dict) -> Optional[str]:
    """Classifie un lead selon sa catégorie de relance.

    Priorités (dans l'ordre) :
    1. Rejected  — Statut == "Rejected", bloque toute autre catégorie.
    2. Hot       — Score IA >= 80 ET statut pas encore Qualified/Sold.
    3. Warm      — Score IA entre 50 et 79.
    4. Cold      — Score IA < 50 ET au moins un moyen de contact présent.
    5. None      — Pas assez de données pour classer.

    Args:
        lead_fields: Dict des champs Airtable du lead (tel que retourné par
                     airtable_client.get_record ou list_records).

    Returns:
        "Hot" | "Warm" | "Cold" | "Rejected" | None
    """
    statut: str = (lead_fields.get("Statut") or "").strip()
    score_raw = lead_fields.get("Score IA")

    # 1. Rejected — priorité absolue
    if statut == "Rejected":
        return "Rejected"

    # Score manquant → impossible de classer
    if score_raw is None:
        return None

    try:
        score = int(score_raw)
    except (ValueError, TypeError):
        return None

    # 2. Hot
    if score >= 80 and statut not in ("Qualified", "Sold"):
        return "Hot"

    # 3. Warm
    if 50 <= score <= 79:
        return "Warm"

    # 4. Cold — uniquement si au moins un moyen de contact
    has_contact = bool(lead_fields.get("Email") or lead_fields.get("Téléphone"))
    if score < 50 and has_contact:
        return "Cold"

    # 5. Pas assez de données
    return None


def should_follow_up_now(lead_fields: dict, category: Optional[str]) -> bool:
    """Détermine si une relance doit être envoyée maintenant pour ce lead.

    Règles par catégorie :
    - Hot      : True si >= 24 h depuis le dernier contact (ou jamais contacté).
    - Warm     : True si >= 3 j (1re tentative) ou >= 7 j (2e tentative).
                 False au-delà de 2 tentatives.
    - Cold     : True pour les 2 premières tentatives (sans contrainte de délai
                 strict — le délai est géré par le scheduler externe).
                 False dès que Nombre de tentatives >= 2.
    - Rejected : Toujours False.
    - None     : Toujours False.

    Args:
        lead_fields: Dict des champs Airtable du lead.
        category:    Résultat de classify_lead().

    Returns:
        True si une relance est appropriée maintenant, False sinon.
    """
    if category in (None, "Rejected"):
        return False

    attempts = _attempts(lead_fields)
    hours_elapsed = _hours_since_last_contact(lead_fields)

    if category == "Hot":
        # Jamais contacté → relancer immédiatement
        if hours_elapsed is None:
            return True
        return hours_elapsed >= _HOT_DELAY_HOURS

    if category == "Warm":
        if attempts >= len(_WARM_DELAYS_DAYS):
            return False  # 2 tentatives Warm épuisées
        if hours_elapsed is None:
            return True
        required_days = _WARM_DELAYS_DAYS[attempts]
        return hours_elapsed >= required_days * 24

    if category == "Cold":
        if attempts >= _COLD_MAX_ATTEMPTS:
            return False  # quota Cold épuisé
        return True  # le scheduler décide du moment exact

    return False
