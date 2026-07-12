"""Tests unitaires pour backend/services/enrichment_service.py.

Exécutable directement :
    python tests/test_enrichment_service.py
Ou via pytest :
    pytest tests/test_enrichment_service.py -v
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services import session_store
from backend.services.enrichment_service import (
    missing_fields,
    start_enrichment,
    handle_reply,
    _MSG_COMPLETE,
    _MSG_STOPPED,
)


def _clear():
    session_store._sessions.clear()


# ---------------------------------------------------------------------------
# missing_fields
# ---------------------------------------------------------------------------

def test_missing_fields_all_empty():
    fields = {}
    result = missing_fields(fields)
    assert "Prénom" in result
    assert "Email" in result
    assert len(result) == 9
    print("missing_fields — tous vides — OK")


def test_missing_fields_partial():
    fields = {"Prénom": "Jean", "Email": "jean@test.com"}
    result = missing_fields(fields)
    assert "Prénom" not in result
    assert "Email" not in result
    assert "Nom" in result
    print("missing_fields — partiel — OK")


def test_missing_fields_complete():
    fields = {
        "Prénom": "Jean", "Nom": "Dupont", "Téléphone": "0488",
        "Email": "a@b.com", "Adresse": "Rue 1", "Ville": "Namur",
        "Date de naissance": "01/01/1990", "Code EAN": "541234567890123456",
        "Désir de changement": "Oui",
    }
    assert missing_fields(fields) == []
    print("missing_fields — complet — OK")


# ---------------------------------------------------------------------------
# start_enrichment
# ---------------------------------------------------------------------------

def test_start_enrichment_sets_mode():
    _clear()
    msg = start_enrichment("telegram:111", "recABC", ["Prénom", "Email"])
    state = session_store.get_session("telegram:111")
    assert state["enrichment_mode"] is True
    assert state["enrichment_record_id"] == "recABC"
    assert state["enrichment_pending_fields"] == ["Prénom", "Email"]
    assert "Quel est votre prénom" in msg
    print("start_enrichment — mode active — OK")


def test_start_enrichment_empty_missing_returns_complete():
    _clear()
    msg = start_enrichment("telegram:222", "recDEF", [])
    assert _MSG_COMPLETE in msg
    print("start_enrichment — aucun champ manquant — OK")


# ---------------------------------------------------------------------------
# handle_reply — /stop
# ---------------------------------------------------------------------------

def test_handle_reply_stop_deactivates_mode():
    _clear()
    start_enrichment("telegram:333", "recGHI", ["Prénom", "Nom"])
    msg = handle_reply("telegram:333", "/stop")
    state = session_store.get_session("telegram:333")
    assert state["enrichment_mode"] is False
    assert msg == _MSG_STOPPED
    print("handle_reply /stop — mode désactivé — OK")


# ---------------------------------------------------------------------------
# handle_reply — flux normal
# ---------------------------------------------------------------------------

@patch("backend.services.enrichment_service.AirtableClient")
def test_handle_reply_saves_field_and_asks_next(mock_cls):
    _clear()
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    start_enrichment("telegram:444", "recJKL", ["Prénom", "Nom"])
    msg = handle_reply("telegram:444", "Marie")

    # Vérifie que Airtable a été appelé avec la bonne valeur
    mock_client.update_record.assert_called_once_with("Leads", "recJKL", {"Prénom": "Marie"})

    # Vérifie que la prochaine question est posée
    assert "nom de famille" in msg.lower()

    # Vérifie que pending a avancé
    state = session_store.get_session("telegram:444")
    assert state["enrichment_pending_fields"] == ["Nom"]
    print("handle_reply — sauvegarde + question suivante — OK")


@patch("backend.services.enrichment_service.AirtableClient")
def test_handle_reply_last_field_completes(mock_cls):
    _clear()
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    start_enrichment("telegram:555", "recMNO", ["Nom"])
    msg = handle_reply("telegram:555", "Dupont")

    assert msg == _MSG_COMPLETE
    state = session_store.get_session("telegram:555")
    assert state["enrichment_mode"] is False
    assert state["enrichment_pending_fields"] == []
    print("handle_reply — dernier champ -> complet — OK")


@patch("backend.services.enrichment_service.AirtableClient")
def test_handle_reply_airtable_error_returns_retry_message(mock_cls):
    _clear()
    mock_client = MagicMock()
    mock_client.update_record.side_effect = RuntimeError("Airtable down")
    mock_cls.return_value = mock_client

    start_enrichment("telegram:666", "recPQR", ["Email"])
    msg = handle_reply("telegram:666", "test@test.com")

    assert "erreur" in msg.lower()
    # Le champ ne doit pas avoir avancé
    state = session_store.get_session("telegram:666")
    assert "Email" in state["enrichment_pending_fields"]
    print("handle_reply — erreur Airtable -> message retry — OK")


# ---------------------------------------------------------------------------
# Point d'entrée direct
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_missing_fields_all_empty()
    test_missing_fields_partial()
    test_missing_fields_complete()
    test_start_enrichment_sets_mode()
    test_start_enrichment_empty_missing_returns_complete()
    test_handle_reply_stop_deactivates_mode()
    test_handle_reply_saves_field_and_asks_next()
    test_handle_reply_last_field_completes()
    test_handle_reply_airtable_error_returns_retry_message()
    print("\nAll enrichment_service tests PASSED successfully!")
