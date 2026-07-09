# Phase 1 — Choix techniques validés

## Décision 1 : Stratégie de dédoublonnage (Deduplication)

**Choix :** Dédoublonnage sur 3 clés primaires : **Email**, **Phone**, **EAN Code**

**Raison :** 
- Ces trois champs sont identifiants métier uniques pour un prospect (vente B2B)
- Si un nouveau lead correspond sur ANY de ces clés, il est traité comme doublon
- Minimise la fragmentation des données et les leads en double

**Implémentation :**
- Logique dans `backend/airtable_client.py` (méthode `create_lead()`)
- Script CSV `scripts/import_csv.py` valide avant import
- Tests de déduplication couverts dans `tests/test_airtable_client.py`

---

## Décision 2 : Gestion des noms de champs en français

**Choix :** Conserver tous les noms de champs Airtable en **français** (Nom, Prénom, Téléphone, Email, etc.)

**Raison :**
- Client français → UX naturelle en français
- Évite la confusion lors de mappings Excel/CSV
- Airtable supporte natalement l'UTF-8

**Implémentation :**
- Schémas Pydantic définissent les mappages (ex: `nom: str`, `prenom: str`)
- CSV import transforme les colonnes sources en noms français standard
- Test data utilise des valeurs françaises (Yosra, Sadia, etc.)

---

## Décision 3 : Résolution sys.path via conftest.py

**Choix :** Utiliser `conftest.py` à la racine du projet pour ajouter automatiquement le répertoire racine à `sys.path`

**Raison :**
- Pytest découvre et exécute `conftest.py` avant les tests
- Évite la modification de chaque fichier de test
- Standard industrie pour les projets Python (pytest best practice)
- Alternative `pytest.ini` avec `pythonpath = .` rejetée au profit de l'approche plus explicite

**Implémentation :**
```python
# conftest.py (racine du projet)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
```

**Résultat :** Tests s'exécutent sans erreur `ModuleNotFoundError: No module named 'backend'`

---

## Décision 4 : Validation et tests

**Choix :** TDD (Test-Driven Development) avec pytest, couverture minimale des fonctions critiques

**Implémentation :**
- Suite `tests/test_airtable_client.py` couvre : connexion, création de leads, déduplication
- Sample data CSV (`tests/sample_leads.csv`) permet tests reproducibles
- Tous les tests passent avec `pytest -q` (exit code 0)

---

## Statut Phase 1 : ✅ VALIDÉE ET COMPLÈTE

- Structure de fichiers ✅
- Connexion Airtable ✅
- Import CSV (3 leads créés) ✅
- Tests passés (0 failures) ✅
- Documentation des schémas ✅
