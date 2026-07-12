"""Service d'envoi des messages de relance Telegram.

Lit les templates depuis docs/knowledge_base/follow_up_templates.md,
substitue les variables dynamiques ({prenom}, {nom}, {fournisseur}),
et envoie via TelegramClient.

Fonctions publiques :
    get_template(key)                        -> str
    render_template(key, lead_fields)        -> str
    send_follow_up(lead_fields, category)    -> bool
"""

import os
import re
import logging
from typing import Optional, Dict, Any

from backend.config import TELEGRAM_BOT_TOKEN
from backend.integrations.telegram.client import TelegramClient

logger = logging.getLogger(__name__)

# Chemin vers le fichier de templates (relatif à la racine du projet)
_TEMPLATES_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "docs", "knowledge_base", "follow_up_templates.md"
)

# Clé de template par catégorie et numéro de tentative (0-indexé)
_TEMPLATE_KEYS: Dict[str, list] = {
    "Hot":  ["HOT_1"],
    "Warm": ["WARM_1", "WARM_2"],
    "Cold": ["COLD_1", "COLD_2"],
}

# Cache en mémoire pour éviter de relire le fichier à chaque appel
_templates_cache: Optional[Dict[str, str]] = None


# ---------------------------------------------------------------------------
# Lecture et parsing des templates
# ---------------------------------------------------------------------------

def _load_templates() -> Dict[str, str]:
    """Parse follow_up_templates.md et retourne un dict {clé: texte}.

    Les sections sont délimitées par `## CLE` (niveau 2).
    Le séparateur `---` entre sections est ignoré.
    """
    global _templates_cache
    if _templates_cache is not None:
        return _templates_cache

    path = os.path.abspath(_TEMPLATES_PATH)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Templates introuvables : {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Découpe sur les titres ## NOM (en majuscules, sans espace interne)
    sections = re.split(r"\n## ([A-Z0-9_]+)\n", content)
    # sections[0] = en-tête du fichier (ignoré)
    # sections[1], sections[2], sections[3], sections[4], ...
    # → paires (clé, texte)

    result: Dict[str, str] = {}
    it = iter(sections[1:])
    for key, text in zip(it, it):
        # Supprimer les séparateurs --- et les espaces superflus
        cleaned = re.sub(r"\n---\s*$", "", text.strip())
        result[key.strip()] = cleaned.strip()

    _templates_cache = result
    return result


def get_template(key: str) -> str:
    """Retourne le texte brut d'un template par sa clé (ex: 'HOT_1').

    Args:
        key: Clé du template (HOT_1, WARM_1, WARM_2, COLD_1, COLD_2).

    Returns:
        Texte brut avec variables non substituées.

    Raises:
        KeyError: Si la clé n'existe pas dans le fichier de templates.
    """
    templates = _load_templates()
    if key not in templates:
        raise KeyError(f"Template '{key}' introuvable dans follow_up_templates.md")
    return templates[key]


def render_template(key: str, lead_fields: Dict[str, Any]) -> str:
    """Retourne le texte du template avec les variables substituées.

    Variables supportées :
        {prenom}      → champ "Prénom" du lead (défaut : "")
        {nom}         → champ "Nom" du lead (défaut : "")
        {fournisseur} → champ "Fournisseur actuel" du lead (défaut : "votre fournisseur actuel")

    Args:
        key:         Clé du template.
        lead_fields: Dict des champs Airtable du lead.

    Returns:
        Texte prêt à envoyer.
    """
    text = get_template(key)
    prenom = (lead_fields.get("Prénom") or lead_fields.get("Prenom") or "").strip()
    nom = (lead_fields.get("Nom") or "").strip()
    fournisseur = (lead_fields.get("Fournisseur actuel") or "votre fournisseur actuel").strip()

    return (
        text
        .replace("{prenom}", prenom)
        .replace("{nom}", nom)
        .replace("{fournisseur}", fournisseur)
    )


# ---------------------------------------------------------------------------
# Envoi
# ---------------------------------------------------------------------------

def send_follow_up(lead_fields: Dict[str, Any], category: str) -> bool:
    """Envoie le message de relance approprié au lead via Telegram.

    Choisit la clé de template selon la catégorie et le nombre de tentatives
    déjà effectuées (champ "Nombre de tentatives").

    Args:
        lead_fields: Dict des champs Airtable du lead.
        category:    "Hot" | "Warm" | "Cold" (Rejected/None ne doivent pas arriver ici).

    Returns:
        True si le message a été envoyé avec succès, False sinon.
    """
    chat_id_raw = lead_fields.get("Telegram Chat ID")
    if not chat_id_raw:
        logger.warning(
            "send_follow_up: lead '%s %s' n'a pas de Telegram Chat ID — ignoré.",
            lead_fields.get("Prénom", ""),
            lead_fields.get("Nom", ""),
        )
        return False

    try:
        chat_id = int(str(chat_id_raw).strip())
    except (ValueError, TypeError):
        logger.warning("send_follow_up: Telegram Chat ID invalide : %r", chat_id_raw)
        return False

    keys = _TEMPLATE_KEYS.get(category, [])
    if not keys:
        logger.warning("send_follow_up: catégorie inconnue '%s'", category)
        return False

    try:
        attempts = int(lead_fields.get("Nombre de tentatives", 0) or 0)
    except (ValueError, TypeError):
        attempts = 0

    key_index = min(attempts, len(keys) - 1)
    template_key = keys[key_index]

    try:
        text = render_template(template_key, lead_fields)
    except KeyError as exc:
        logger.error("send_follow_up: %s", exc)
        return False

    if not TELEGRAM_BOT_TOKEN:
        logger.error("send_follow_up: TELEGRAM_BOT_TOKEN non configuré.")
        return False

    try:
        client = TelegramClient(token=TELEGRAM_BOT_TOKEN)
        client.send_message(chat_id=chat_id, text=text)
        logger.info(
            "Relance %s envoyée à chat_id=%s (tentative %d).",
            template_key, chat_id, attempts + 1,
        )
        return True
    except Exception as exc:
        logger.error("send_follow_up: échec envoi Telegram — %s", exc)
        return False
