"""Service d'enrichissement des leads via Telegram.

Gère le dialogue pas-à-pas pour collecter les champs manquants d'un lead
et les sauvegarder dans Airtable au fur et à mesure.

Fonctions publiques :
    missing_fields(airtable_fields)              -> list[str]
    start_enrichment(session_id, record_id, missing) -> str
    handle_reply(session_id, text)               -> str
"""

import logging
from typing import List, Optional

from backend.services import session_store
from backend.airtable_client import AirtableClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Définition des champs à collecter — ordre et libellés
# ---------------------------------------------------------------------------

# (clé Airtable, question posée à l'utilisateur)
_FIELD_QUESTIONS = [
    ("Prénom",             "Quel est votre prénom ?"),
    ("Nom",                "Quel est votre nom de famille ?"),
    ("Téléphone",          "Quel est votre numéro de téléphone ?"),
    ("Email",              "Quelle est votre adresse e-mail ?"),
    ("Adresse",            "Quelle est votre adresse postale complète ?"),
    ("Ville",              "Dans quelle ville habitez-vous ?"),
    ("Date de naissance",  "Quelle est votre date de naissance ? (format JJ/MM/AAAA)"),
    ("Code EAN",           "Quel est votre code EAN ? (18 chiffres commençant par 54)"),
    ("Désir de changement","Souhaitez-vous changer de fournisseur d'énergie ? (Oui / Non)"),
]

_QUESTIONS: dict = {k: q for k, q in _FIELD_QUESTIONS}
_FIELD_ORDER: List[str] = [k for k, _ in _FIELD_QUESTIONS]

# Message de fin
_MSG_COMPLETE = (
    "Merci ! 🎉 Votre dossier est maintenant complet. "
    "Un conseiller Ecofix va l'étudier et vous recontactera très prochainement."
)
_MSG_STOPPED = (
    "Enrichissement annulé. Vous pouvez reprendre la conversation normalement."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def missing_fields(airtable_fields: dict) -> List[str]:
    """Retourne la liste ordonnée des champs manquants pour ce lead.

    Args:
        airtable_fields: Dict des champs Airtable du lead.

    Returns:
        Liste des clés de champs vides ou absents, dans l'ordre de _FIELD_ORDER.
    """
    return [
        field for field in _FIELD_ORDER
        if not str(airtable_fields.get(field) or "").strip()
    ]


def _next_question(pending: List[str]) -> Optional[str]:
    """Retourne la question pour le prochain champ à collecter, ou None si terminé."""
    if not pending:
        return None
    return _QUESTIONS.get(pending[0], f"Veuillez renseigner : {pending[0]}")


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def start_enrichment(session_id: str, record_id: str, missing: List[str]) -> str:
    """Active le mode enrichment pour cette session et retourne le 1er message.

    Args:
        session_id: Identifiant de session Telegram (ex: 'telegram:123').
        record_id:  Identifiant Airtable du lead à enrichir.
        missing:    Liste ordonnée des champs manquants.

    Returns:
        Message de bienvenue + première question.
    """
    state = session_store.get_session(session_id)
    state["enrichment_mode"] = True
    state["enrichment_record_id"] = record_id
    state["enrichment_pending_fields"] = list(missing)
    session_store.set_session(session_id, state)

    intro = (
        "Bonjour ! Pour compléter votre dossier Ecofix, "
        "j'ai besoin de quelques informations supplémentaires. "
        "Vous pouvez taper /stop à tout moment pour annuler.\n\n"
    )
    first_question = _next_question(missing)
    return intro + first_question if first_question else _MSG_COMPLETE


def handle_reply(session_id: str, text: str) -> str:
    """Traite la réponse de l'utilisateur en mode enrichment.

    Sauvegarde la valeur dans Airtable, passe au champ suivant,
    et désactive le mode enrichment quand tous les champs sont collectés.

    Args:
        session_id: Identifiant de session Telegram.
        text:       Texte envoyé par l'utilisateur.

    Returns:
        Prochaine question, message de fin, ou message d'annulation.
    """
    # Commande d'annulation
    if text.strip().lower() == "/stop":
        state = session_store.get_session(session_id)
        state["enrichment_mode"] = False
        state["enrichment_pending_fields"] = []
        session_store.set_session(session_id, state)
        return _MSG_STOPPED

    state = session_store.get_session(session_id)
    pending: List[str] = state.get("enrichment_pending_fields", [])
    record_id: Optional[str] = state.get("enrichment_record_id")

    if not pending or not record_id:
        # Sécurité : plus rien à collecter
        state["enrichment_mode"] = False
        session_store.set_session(session_id, state)
        return _MSG_COMPLETE

    current_field = pending[0]
    value = text.strip()

    # Sauvegarde dans Airtable
    try:
        airtable = AirtableClient()
        airtable.update_record("Leads", record_id, {current_field: value})
        logger.info(
            "Enrichment [%s] — champ '%s' = '%s' sauvegardé.",
            session_id, current_field, value,
        )
    except Exception as exc:
        logger.error("Enrichment: erreur Airtable pour '%s' — %s", current_field, exc)
        return (
            f"Une erreur est survenue lors de la sauvegarde. "
            f"Pouvez-vous réessayer ? ({_QUESTIONS.get(current_field, current_field)})"
        )

    # Passer au champ suivant
    pending.pop(0)
    state["enrichment_pending_fields"] = pending
    session_store.set_session(session_id, state)

    if not pending:
        # Tous les champs collectés
        state["enrichment_mode"] = False
        session_store.set_session(session_id, state)
        return _MSG_COMPLETE

    return _next_question(pending)
