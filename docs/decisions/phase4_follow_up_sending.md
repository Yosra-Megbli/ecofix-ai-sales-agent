# Phase 4 — Envoi automatique des relances Telegram

## Périmètre de cette phase

- Templates de messages de relance (Markdown, modifiables sans code).
- Service d'envoi `follow_up_sender.py` (lecture template + substitution + Telegram).
- Script `run_follow_up.py` (récupère leads Airtable, classifie, envoie, met à jour CRM).

Hors scope (phases suivantes) :
- Scheduler automatique (cron / Celery).
- Dashboard de suivi des relances.
- Personnalisation LLM (Gemini) des messages — prévu en V2.
- Human handoff.

---

## Décision 1 : Templates en Markdown, pas en Python

**Choix :** `docs/knowledge_base/follow_up_templates.md` avec sections `## CLE`.

**Raison :**
- Modifiable par Ecofix sans toucher au code.
- Parsé une seule fois puis mis en cache mémoire (`_templates_cache`).
- Format lisible par un humain et versionnable dans Git.

**Clés définies :**

| Clé | Catégorie | Tentative |
|---|---|---|
| HOT_1 | Hot | 1re (et unique) |
| WARM_1 | Warm | 1re |
| WARM_2 | Warm | 2e |
| COLD_1 | Cold | 1re |
| COLD_2 | Cold | 2e (dernière) |

---

## Décision 2 : Pas de RAG dans les relances (MVP)

**Choix :** Templates statiques avec variables `{prenom}`, `{nom}`, `{fournisseur}`.

**Raison :**
- Sécurité : pas de risque d'hallucination Gemini sur des informations commerciales.
- Testabilité : comportement 100% déterministe.
- Conformité : messages validés par Ecofix avant déploiement.

**V2 prévu :** Gemini lira l'historique de conversation pour personnaliser le message
(ex: "vous aviez comparé Ecofix Motion avec votre offre Engie...").

---

## Décision 3 : Mise à jour CRM après chaque envoi

**Champs mis à jour par `run_follow_up.py` après un envoi réussi :**
- `Nombre de tentatives` : incrémenté de 1.
- `Dernier contact` : mis à jour à l'heure UTC courante.

**Raison :** `should_follow_up_now()` s'appuie sur ces deux champs pour calculer
si une nouvelle relance est due — ils doivent rester synchronisés.

---

## Décision 4 : Mode --dry-run dans le script

**Choix :** Flag `--dry-run` qui affiche les relances prévues sans envoyer ni modifier Airtable.

**Raison :** Permet de valider la logique de classification avant le premier vrai envoi.

---

## Statut Phase 4 : ✅ IMPLÉMENTÉE

- `docs/knowledge_base/follow_up_templates.md` ✅
- `backend/services/follow_up_sender.py` ✅
- `scripts/run_follow_up.py` ✅
- `tests/test_follow_up_sender.py` (11 tests) ✅
- `docs/decisions/phase4_follow_up_sending.md` ✅

---

## Commandes

### Tester sans envoyer
```bash
cd c:\Users\megbl\Desktop\Yosra\v4
python scripts/run_follow_up.py --dry-run
```

### Envoyer les relances réelles
```bash
python scripts/run_follow_up.py
```

### Lancer les tests unitaires
```bash
pytest tests/test_follow_up_sender.py -v
```
