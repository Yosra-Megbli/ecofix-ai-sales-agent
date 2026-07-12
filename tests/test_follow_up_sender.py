"""Tests unitaires pour backend/services/follow_up_sender.py.

Tous les appels réseau (Telegram, Airtable) sont mockés.
Exécutable directement :
    python tests/test_follow_up_sender.py
Ou via pytest :
    pytest tests/test_follow_up_sender.py -v
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Réinitialise le cache de templates avant chaque test
import backend.services.follow_up_sender as sender_module


def _clear_cache():
    sender_module._templates_cache = None


# ---------------------------------------------------------------------------
# get_template / render_template
# ---------------------------------------------------------------------------

def test_get_template_hot_1():
    _clear_cache()
    text = sender_module.get_template("HOT_1")
    assert "{prenom}" in text, "HOT_1 doit contenir {prenom}"
    assert len(text) > 20, "HOT_1 ne doit pas être vide"
    print("get_template HOT_1 — OK")


def test_get_template_unknown_key_raises():
    _clear_cache()
    try:
        sender_module.get_template("INEXISTANT")
        assert False, "Doit lever KeyError"
    except KeyError:
        pass
    print("get_template clé inconnue → KeyError — OK")


def test_render_template_substitutes_variables():
    _clear_cache()
    lead = {"Prénom": "Yasmine", "Nom": "Dupont", "Fournisseur actuel": "Engie"}
    text = sender_module.render_template("HOT_1", lead)
    assert "Yasmine" in text, "Le prénom doit être substitué"
    assert "{prenom}" not in text, "La variable {prenom} ne doit plus apparaître"
    print("render_template substitution — OK")


def test_render_template_missing_prenom_uses_empty():
    _clear_cache()
    lead = {"Nom": "Dupont"}
    text = sender_module.render_template("WARM_1", lead)
    assert "{prenom}" not in text
    print("render_template prénom absent → chaîne vide — OK")


def test_render_template_missing_fournisseur_uses_default():
    _clear_cache()
    lead = {"Prénom": "Jean"}
    text = sender_module.render_template("COLD_1", lead)
    assert "votre fournisseur actuel" in text
    assert "{fournisseur}" not in text
    print("render_template fournisseur absent → valeur par défaut — OK")


# ---------------------------------------------------------------------------
# send_follow_up — cas d'erreur sans appel réseau
# ---------------------------------------------------------------------------

def test_send_follow_up_no_chat_id_returns_false():
    _clear_cache()
    lead = {"Prénom": "Jean", "Score IA": 85, "Statut": "Contacted"}
    result = sender_module.send_follow_up(lead, "Hot")
    assert result is False, "Sans Telegram Chat ID → False"
    print("send_follow_up sans Chat ID → False — OK")


def test_send_follow_up_invalid_chat_id_returns_false():
    _clear_cache()
    lead = {"Prénom": "Jean", "Telegram Chat ID": "abc_invalide"}
    result = sender_module.send_follow_up(lead, "Hot")
    assert result is False
    print("send_follow_up Chat ID invalide → False — OK")


def test_send_follow_up_unknown_category_returns_false():
    _clear_cache()
    lead = {"Prénom": "Jean", "Telegram Chat ID": "123456"}
    result = sender_module.send_follow_up(lead, "Unknown")
    assert result is False
    print("send_follow_up catégorie inconnue → False — OK")


@patch("backend.services.follow_up_sender.TELEGRAM_BOT_TOKEN", "fake-token")
@patch("backend.services.follow_up_sender.TelegramClient")
def test_send_follow_up_hot_calls_send_message(mock_client_cls):
    _clear_cache()
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    lead = {
        "Prénom": "Yasmine",
        "Nom": "Martin",
        "Telegram Chat ID": "8867809811",
        "Nombre de tentatives": 0,
        "Fournisseur actuel": "Engie",
    }
    result = sender_module.send_follow_up(lead, "Hot")

    assert result is True
    mock_client.send_message.assert_called_once()
    call_kwargs = mock_client.send_message.call_args
    assert call_kwargs[1]["chat_id"] == 8867809811 or call_kwargs[0][0] == 8867809811
    print("send_follow_up Hot → send_message appelé — OK")


@patch("backend.services.follow_up_sender.TELEGRAM_BOT_TOKEN", "fake-token")
@patch("backend.services.follow_up_sender.TelegramClient")
def test_send_follow_up_warm_second_attempt_uses_warm_2(mock_client_cls):
    _clear_cache()
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    lead = {
        "Prénom": "Luc",
        "Telegram Chat ID": "111222333",
        "Nombre de tentatives": 1,  # 2e tentative → WARM_2
    }
    sender_module.send_follow_up(lead, "Warm")

    sent_text = mock_client.send_message.call_args[1].get("text") or \
                mock_client.send_message.call_args[0][1]
    # WARM_2 parle du programme de parrainage
    assert "parrain" in sent_text.lower() or "5 €" in sent_text, \
        "La 2e tentative Warm doit utiliser WARM_2"
    print("send_follow_up Warm 2e tentative → WARM_2 — OK")


@patch("backend.services.follow_up_sender.TELEGRAM_BOT_TOKEN", "fake-token")
@patch("backend.services.follow_up_sender.TelegramClient")
def test_send_follow_up_telegram_error_returns_false(mock_client_cls):
    _clear_cache()
    mock_client = MagicMock()
    mock_client.send_message.side_effect = RuntimeError("Telegram API down")
    mock_client_cls.return_value = mock_client

    lead = {
        "Prénom": "Test",
        "Telegram Chat ID": "999",
        "Nombre de tentatives": 0,
    }
    result = sender_module.send_follow_up(lead, "Cold")
    assert result is False
    print("send_follow_up erreur Telegram → False — OK")


# ---------------------------------------------------------------------------
# Point d'entrée direct
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_get_template_hot_1()
    test_get_template_unknown_key_raises()
    test_render_template_substitutes_variables()
    test_render_template_missing_prenom_uses_empty()
    test_render_template_missing_fournisseur_uses_default()
    test_send_follow_up_no_chat_id_returns_false()
    test_send_follow_up_invalid_chat_id_returns_false()
    test_send_follow_up_unknown_category_returns_false()
    test_send_follow_up_hot_calls_send_message()
    test_send_follow_up_warm_second_attempt_uses_warm_2()
    test_send_follow_up_telegram_error_returns_false()
    print("\nAll follow_up_sender tests PASSED successfully!")
