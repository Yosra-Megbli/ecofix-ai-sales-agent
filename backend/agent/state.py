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
    Date_de_naissance: Optional[str]
    Code_EAN: Optional[str]
    Desir_changement: Optional[str]
    Eligible: Optional[bool]


class GraphState(TypedDict):
    """State for the LangGraph agent."""
    messages: List[Dict[str, str]]  # List of {"role": "user|assistant", "content": str}
    conversation_turn: int
    lead_id: Optional[str]          # Airtable record ID of the Lead
    lead_info: LeadInfoDict         # Currently collected lead details
    intent: Optional[str]           # Detected intent of the user message
    conversation_stage: Optional[str] # Current stage of the sales pipeline
    customer_profile: Optional[Dict[str, Any]] # Extracted or enriched profile data
    retrieved_sources: Optional[List[str]] # Chunks retrieved from knowledge base
    lead_score: Optional[int]       # Score between 0 and 100
    qualification_status: Optional[str] # Status e.g. "Qualified", "Follow-up", "Rejected"
