"""State definition for LangGraph agent."""

from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict


class LeadInfoDict(TypedDict, total=False):
    """Structured collected details for a lead."""
    Nom: Optional[str]
    Prénom: Optional[str]
    Téléphone: Optional[str]
    Email: Optional[str]
    Adresse: Optional[str]
    Ville: Optional[str]
    Fournisseur_actuel: Optional[str]
    Budget: Optional[str]


class GraphState(TypedDict):
    """State for the LangGraph agent."""
    messages: List[Dict[str, str]]  # List of {"role": "user|assistant", "content": str}
    conversation_turn: int
    lead_id: Optional[str]          # Airtable record ID of the Lead
    lead_info: LeadInfoDict         # Currently collected lead details
