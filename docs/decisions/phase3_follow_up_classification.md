# Phase 3 — Classification des leads & liaison Telegram Chat ID

## Périmètre de cette phase

Phase 1 du système de relance :
- Lier chaque lead à son `chat_id` Telegram dans Airtable.
- Classifier automatiquement les leads en Hot / Warm / Cold / Rejected.

Hors scope (phases suivantes) :
- Templates de messages de relance.
- Script d'envoi en masse.
- Dashboard de suivi des relances.
- Human handoff.

---

## Décision 1 : Liaison Telegram Chat ID — approche non bloquante

**Choix :** Appel à `_sync_telegram_chat_id()` après chaque réponse envoyée
dans `bot.py`, en mode silencieux (try/except, jamais de crash de la boucle).

**Raison :**
- La conversation doit continuer même si Airtable est indisponible.
- La mise à jour est idempotente : si le champ est déjà correct, aucun appel PATCH.
- Réutilise `airtable_client.find_duplicate_lead()` (Email → Téléphone) — zéro
  duplication de la logique de recherche.

**Champ Airtable ajouté :**
- Table : `Leads`
- Nom : `Telegram Chat ID`
- Type : texte (string)
- Valeur : identifiant numérique Telegram sous forme de chaîne (ex: `"8867809811"`)

---

## Décision 2 : Classifier dans une couche service pure

**Choix :** `backend/services/follow_up_classifier.py` — fonctions pures sans
effet de bord, sans appel réseau, sans import de l'agent LangGraph.

**Raison :**
- Testable unitairement sans mock réseau.
- Réutilisable par n'importe quel futur scheduler ou endpoint.
- Les seuils de score (80 / 50) sont ceux de `lead_scoring.md` — pas de
  nouvelle règle inventée.

**Règles de classification (par priorité) :**

| Priorité | Catégorie | Condition |
|---|---|---|
| 1 | Rejected | Statut == "Rejected" (bloque tout) |
| 2 | Hot | Score IA >= 80 ET statut ∉ {Qualified, Sold} |
| 3 | Warm | 50 <= Score IA <= 79 |
| 4 | Cold | Score IA < 50 ET (Email ou Téléphone présent) |
| 5 | None | Pas assez de données |

---

## Décision 3 : Timing de relance (should_follow_up_now)

**Choix :** Délais codés comme constantes dans `follow_up_classifier.py`,
basés sur `follow_up_strategy.md`.

| Catégorie | Timing | Max tentatives |
|---|---|---|
| Hot | 24 h après dernier contact | illimité |
| Warm | J+3 (1re), J+7 (2e) | 2 |
| Cold | Immédiat (scheduler décide) | 2 |
| Rejected | Jamais | 0 |

**Champ Airtable ajouté :**
- Table : `Leads`
- Nom : `Nombre de tentatives`
- Type : number (entier)
- Valeur par défaut : 0

---

## Décision 4 : Comportement existant préservé

- `routes/chat.py` : **non modifié**.
- `integrations/telegram/bot.py` : seul ajout = appel non bloquant à
  `_sync_telegram_chat_id()` après `client.send_message()`. Le flux
  `/start` → `start_session` et message → `send_message` est identique.

---

## Statut Phase 3 : ✅ IMPLÉMENTÉE

- `backend/services/follow_up_classifier.py` ✅
- `backend/integrations/telegram/bot.py` (liaison Chat ID) ✅
- `tests/test_follow_up_classifier.py` (22 tests) ✅
- `docs/models.md` (2 nouveaux champs) ✅
- `docs/decisions/phase3_follow_up_classification.md` ✅

---

## Commande de test

```bash
cd c:\Users\megbl\Desktop\Yosra\v4
pytest tests/test_follow_up_classifier.py -v
```
