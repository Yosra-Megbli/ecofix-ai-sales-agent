"""Tests unitaires pour backend/services/follow_up_classifier.py.

Couvre : Hot, Warm, Cold, None (pas assez de données), Rejected (bloque
même avec score élevé), et should_follow_up_now par catégorie.

Exécutable directement :
    python tests/test_follow_up_classifier.py

Ou via pytest :
    pytest tests/test_follow_up_classifier.py -v
"""

import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.follow_up_classifier import classify_lead, should_follow_up_now


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _hours_ago(h: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=h)).isoformat()

def _days_ago(d: int) -> str:
    return _hours_ago(d * 24)


# ---------------------------------------------------------------------------
# classify_lead — catégories positives
# ---------------------------------------------------------------------------

def test_classify_hot():
    lead = {"Score IA": 85, "Statut": "Contacted", "Email": "a@b.com"}
    assert classify_lead(lead) == "Hot", "Score 85 + Contacted → Hot"
    print("classify_lead Hot — OK")


def test_classify_hot_score_exactly_80():
    lead = {"Score IA": 80, "Statut": "New"}
    assert classify_lead(lead) == "Hot", "Score 80 → Hot (borne incluse)"
    print("classify_lead Hot (score=80) — OK")


def test_classify_hot_blocked_when_qualified():
    lead = {"Score IA": 90, "Statut": "Qualified"}
    # Qualified n'est pas Rejected, mais Hot ne doit pas s'appliquer
    assert classify_lead(lead) != "Hot", "Statut Qualified → pas Hot"
    print("classify_lead Hot bloqué si Qualified — OK")


def test_classify_warm():
    lead = {"Score IA": 65, "Statut": "Contacted", "Email": "a@b.com"}
    assert classify_lead(lead) == "Warm", "Score 65 → Warm"
    print("classify_lead Warm — OK")


def test_classify_warm_score_exactly_50():
    lead = {"Score IA": 50, "Statut": "New"}
    assert classify_lead(lead) == "Warm", "Score 50 → Warm (borne incluse)"
    print("classify_lead Warm (score=50) — OK")


def test_classify_cold_with_contact():
    lead = {"Score IA": 20, "Statut": "New", "Téléphone": "0488112233"}
    assert classify_lead(lead) == "Cold", "Score 20 + téléphone → Cold"
    print("classify_lead Cold — OK")


def test_classify_none_no_contact():
    lead = {"Score IA": 10, "Statut": "New"}
    assert classify_lead(lead) is None, "Score faible sans contact → None"
    print("classify_lead None (pas de contact) — OK")


def test_classify_none_no_score():
    lead = {"Statut": "New", "Email": "a@b.com"}
    assert classify_lead(lead) is None, "Score absent → None"
    print("classify_lead None (score absent) — OK")


# ---------------------------------------------------------------------------
# classify_lead — Rejected bloque tout, même score élevé
# ---------------------------------------------------------------------------

def test_classify_rejected_blocks_high_score():
    lead = {"Score IA": 95, "Statut": "Rejected", "Email": "a@b.com"}
    result = classify_lead(lead)
    assert result == "Rejected", f"Rejected doit bloquer score 95, got {result!r}"
    print("classify_lead Rejected bloque score élevé — OK")


def test_classify_rejected_blocks_zero_score():
    lead = {"Score IA": 0, "Statut": "Rejected"}
    assert classify_lead(lead) == "Rejected", "Rejected même avec score 0"
    print("classify_lead Rejected bloque score 0 — OK")


def test_classify_rejected_no_score():
    lead = {"Statut": "Rejected"}
    assert classify_lead(lead) == "Rejected", "Rejected sans score → Rejected"
    print("classify_lead Rejected sans score — OK")


# ---------------------------------------------------------------------------
# should_follow_up_now — Hot
# ---------------------------------------------------------------------------

def test_should_follow_up_hot_never_contacted():
    lead = {"Score IA": 85, "Statut": "New"}
    assert should_follow_up_now(lead, "Hot") is True, "Hot jamais contacté → True"
    print("should_follow_up_now Hot (jamais contacté) — OK")


def test_should_follow_up_hot_24h_elapsed():
    lead = {"Score IA": 85, "Statut": "New", "Dernier contact": _hours_ago(25)}
    assert should_follow_up_now(lead, "Hot") is True, "Hot 25h après → True"
    print("should_follow_up_now Hot (25h) — OK")


def test_should_follow_up_hot_too_soon():
    lead = {"Score IA": 85, "Statut": "New", "Dernier contact": _hours_ago(10)}
    assert should_follow_up_now(lead, "Hot") is False, "Hot 10h après → False"
    print("should_follow_up_now Hot (trop tôt) — OK")


# ---------------------------------------------------------------------------
# should_follow_up_now — Warm
# ---------------------------------------------------------------------------

def test_should_follow_up_warm_first_attempt_after_3_days():
    lead = {
        "Score IA": 60,
        "Statut": "Contacted",
        "Dernier contact": _days_ago(4),
        "Nombre de tentatives": 0,
    }
    assert should_follow_up_now(lead, "Warm") is True, "Warm J+4, 0 tentatives → True"
    print("should_follow_up_now Warm (J+4, 0 tentatives) — OK")


def test_should_follow_up_warm_too_soon():
    lead = {
        "Score IA": 60,
        "Statut": "Contacted",
        "Dernier contact": _days_ago(1),
        "Nombre de tentatives": 0,
    }
    assert should_follow_up_now(lead, "Warm") is False, "Warm J+1, 0 tentatives → False"
    print("should_follow_up_now Warm (trop tôt) — OK")


def test_should_follow_up_warm_second_attempt_after_7_days():
    lead = {
        "Score IA": 60,
        "Statut": "Contacted",
        "Dernier contact": _days_ago(8),
        "Nombre de tentatives": 1,
    }
    assert should_follow_up_now(lead, "Warm") is True, "Warm J+8, 1 tentative → True"
    print("should_follow_up_now Warm (J+8, 1 tentative) — OK")


def test_should_follow_up_warm_exhausted():
    lead = {
        "Score IA": 60,
        "Statut": "Contacted",
        "Dernier contact": _days_ago(10),
        "Nombre de tentatives": 2,
    }
    assert should_follow_up_now(lead, "Warm") is False, "Warm 2 tentatives épuisées → False"
    print("should_follow_up_now Warm (épuisé) — OK")


# ---------------------------------------------------------------------------
# should_follow_up_now — Cold
# ---------------------------------------------------------------------------

def test_should_follow_up_cold_first_attempt():
    lead = {"Score IA": 20, "Téléphone": "0488", "Nombre de tentatives": 0}
    assert should_follow_up_now(lead, "Cold") is True, "Cold 0 tentatives → True"
    print("should_follow_up_now Cold (1re tentative) — OK")


def test_should_follow_up_cold_second_attempt():
    lead = {"Score IA": 20, "Téléphone": "0488", "Nombre de tentatives": 1}
    assert should_follow_up_now(lead, "Cold") is True, "Cold 1 tentative → True"
    print("should_follow_up_now Cold (2e tentative) — OK")


def test_should_follow_up_cold_exhausted():
    lead = {"Score IA": 20, "Téléphone": "0488", "Nombre de tentatives": 2}
    assert should_follow_up_now(lead, "Cold") is False, "Cold 2 tentatives → False"
    print("should_follow_up_now Cold (épuisé) — OK")


# ---------------------------------------------------------------------------
# should_follow_up_now — Rejected / None
# ---------------------------------------------------------------------------

def test_should_follow_up_rejected_always_false():
    lead = {"Score IA": 95, "Statut": "Rejected", "Email": "a@b.com"}
    assert should_follow_up_now(lead, "Rejected") is False, "Rejected → toujours False"
    print("should_follow_up_now Rejected — OK")


def test_should_follow_up_none_always_false():
    lead = {"Score IA": 10, "Statut": "New"}
    assert should_follow_up_now(lead, None) is False, "None → toujours False"
    print("should_follow_up_now None — OK")


# ---------------------------------------------------------------------------
# Point d'entrée direct
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_classify_hot()
    test_classify_hot_score_exactly_80()
    test_classify_hot_blocked_when_qualified()
    test_classify_warm()
    test_classify_warm_score_exactly_50()
    test_classify_cold_with_contact()
    test_classify_none_no_contact()
    test_classify_none_no_score()
    test_classify_rejected_blocks_high_score()
    test_classify_rejected_blocks_zero_score()
    test_classify_rejected_no_score()
    test_should_follow_up_hot_never_contacted()
    test_should_follow_up_hot_24h_elapsed()
    test_should_follow_up_hot_too_soon()
    test_should_follow_up_warm_first_attempt_after_3_days()
    test_should_follow_up_warm_too_soon()
    test_should_follow_up_warm_second_attempt_after_7_days()
    test_should_follow_up_warm_exhausted()
    test_should_follow_up_cold_first_attempt()
    test_should_follow_up_cold_second_attempt()
    test_should_follow_up_cold_exhausted()
    test_should_follow_up_rejected_always_false()
    test_should_follow_up_none_always_false()
    print("\nAll follow_up_classifier tests PASSED successfully!")
