"""State definition for LangGraph agent."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ConversationMessage:
    """Represents a single message in the conversation."""
    role: str  # "user" or "assistant"
    content: str


@dataclass
class LeadInfo:
    """Information about the lead being qualified."""
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    interest_level: Optional[str] = None  # "high", "medium", "low", None
    energy_consumption: Optional[str] = None
    current_provider: Optional[str] = None


@dataclass
class AgentState:
    """State for the LangGraph agent."""
    session_id: str
    messages: List[ConversationMessage] = field(default_factory=list)
    lead_info: LeadInfo = field(default_factory=LeadInfo)
    conversation_turn: int = 0
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation history."""
        self.messages.append(ConversationMessage(role=role, content=content))
        
    def get_messages_dict(self) -> List[Dict[str, str]]:
        """Get messages in dict format for LLM."""
        return [{"role": m.role, "content": m.content} for m in self.messages]
