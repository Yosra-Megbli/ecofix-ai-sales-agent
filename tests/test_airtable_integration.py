import pytest
import sys
import os
from unittest.mock import MagicMock, patch, ANY

# Add root folder to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.agent.graph import crm_sync_node
from backend.agent.state import GraphState

@patch("backend.agent.graph.AirtableClient")
def test_new_qualified_lead_creation(mock_client_class):
    # Setup mock client
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    # 1. Deduplication returns None (new lead)
    mock_client.find_by_field.return_value = None
    # 2. Lead creation returns new ID
    mock_client.create_record.return_value = {"id": "recNewLead123"}
    
    state = {
        "messages": [
            {"role": "user", "content": "Je veux changer de fournisseur"},
            {"role": "assistant", "content": "Parfait, nous créons votre fiche..."}
        ],
        "conversation_turn": 1,
        "lead_id": None,
        "lead_info": {
            "Nom": "Dupont",
            "Prenom": "Jean",
            "Telephone": "0488112233",
            "Email": "jean@example.com",
            "Eligible": True
        },
        "lead_score": 90,
        "qualification_status": "Qualified",
        "intent": "qualification",
        "conversation_stage": "Qualification",
        "customer_profile": None,
        "retrieved_sources": None
    }
    
    result = crm_sync_node(state)
    
    # Verify client calls
    mock_client.create_record.assert_any_call("Leads", {
        "Nom": "Dupont",
        "Prénom": "Jean",
        "Téléphone": "0488112233",
        "Email": "jean@example.com",
        "Éligible": True,
        "Statut": "Qualified",
        "Score IA": 90,
        "Prochaine action": "Envoyer étude comparative EDF"
    })
    mock_client.create_record.assert_any_call("Conversations", {
        "Lead": ["recNewLead123"],
        "Date": ANY,
        "Message client": "Je veux changer de fournisseur",
        "Réponse IA": "Parfait, nous créons votre fiche..."
    })
    
    assert result["lead_id"] == "recNewLead123"


@patch("backend.agent.graph.AirtableClient")
def test_existing_lead_update(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    state = {
        "messages": [
            {"role": "user", "content": "Voici mon adresse"},
            {"role": "assistant", "content": "Noté..."}
        ],
        "conversation_turn": 2,
        "lead_id": "recExistingLead456",
        "lead_info": {
            "Nom": "Dupont",
            "Prenom": "Jean",
            "Telephone": "0488112233",
            "Email": "jean@example.com",
            "Adresse": "Rue Royale 10",
            "Eligible": True
        },
        "lead_score": 95,
        "qualification_status": "Qualified",
        "intent": "qualification",
        "conversation_stage": "Qualification",
        "customer_profile": None,
        "retrieved_sources": None
    }
    
    result = crm_sync_node(state)
    
    # Verify update_record called instead of create_record for Leads
    mock_client.update_record.assert_called_with("Leads", "recExistingLead456", ANY)
    assert result["lead_id"] == "recExistingLead456"


@patch("backend.agent.graph.AirtableClient")
def test_duplicate_lead_matching(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    # find_by_field finds existing record by email
    mock_client.find_by_field.side_effect = lambda table, field, val: {"id": "recMatchedLead789"} if field == "Email" else None
    
    state = {
        "messages": [
            {"role": "user", "content": "mon email est jean@example.com"},
            {"role": "assistant", "content": "Merci"}
        ],
        "conversation_turn": 1,
        "lead_id": None,
        "lead_info": {
            "Email": "jean@example.com"
        },
        "lead_score": 10,
        "qualification_status": "Contacted",
        "intent": "qualification",
        "conversation_stage": "Qualification",
        "customer_profile": None,
        "retrieved_sources": None
    }
    
    result = crm_sync_node(state)
    
    # Verify update_record called with matched ID
    mock_client.update_record.assert_called_with("Leads", "recMatchedLead789", ANY)
    assert result["lead_id"] == "recMatchedLead789"


@patch("backend.agent.graph.AirtableClient")
def test_failed_airtable_connection(mock_client_class, capsys):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    # Simulate API connection error
    mock_client.find_by_field.side_effect = Exception("API Connection Timeout")
    
    state = {
        "messages": [
            {"role": "user", "content": "mon email est jean@example.com"},
            {"role": "assistant", "content": "Merci"}
        ],
        "conversation_turn": 1,
        "lead_id": None,
        "lead_info": {
            "Email": "jean@example.com"
        },
        "lead_score": 10,
        "qualification_status": "Contacted",
        "intent": "qualification",
        "conversation_stage": "Qualification",
        "customer_profile": None,
        "retrieved_sources": None
    }
    
    # Should not crash the execution flow (it prints/captures the warning and continues gracefully)
    result = crm_sync_node(state)
    
    assert result["lead_id"] is None
