# Phase 2 — Intégration Telegram (Bot polling)

## Décision 1 : Mode polling (pas de webhook)

**Choix :** Long polling via `getUpdates` avec offset

**Raison :**
- Pas d'URL publique requise → fonctionne en local depuis un téléphone
- Aucune configuration DNS/ngrok/reverse-proxy nécessaire
- Suffisant pour les tests et la démo client

**Implémentation :**
- `backend/integrations/telegram/bot.py` → boucle `run_polling()`
- Timeout long-poll : 30 secondes (configurable dans `TelegramClient`)

---

## Décision 2 : Client HTTP minimal (requests, pas python-telegram-bot)

**Choix :** Client maison dans `backend/integrations/telegram/client.py` utilisant `requests`

**Raison :**
- `requests` est déjà une dépendance du projet (utilisé par `airtable_client.py`)
- Zéro nouvelle dépendance lourde
- Seules 3 méthodes API sont nécessaires : `getUpdates`, `sendMessage`, `sendChatAction`
- `python-telegram-bot` (20+) introduit `asyncio` et des abstractions incompatibles
  avec le reste du code synchrone du projet

---

## Décision 3 : Couche service partagée

**Choix :** Extraire la logique de session dans `backend/services/`

**Raison :**
- Évite toute duplication entre `routes/chat.py` et le bot Telegram
- `session_store.py` : dict global partagé entre tous les canaux
- `conversation_service.py` : unique point d'appel au graphe LangGraph

**Fichiers créés :**
```
backend/services/__init__.py
backend/services/session_store.py
backend/services/conversation_service.py
```

---

## Décision 4 : Isolation des sessions par canal

**Choix :** Préfixe `telegram:{chat_id}` pour les sessions Telegram

**Raison :**
- Un `chat_id` Telegram numérique (ex: `123456`) ne peut pas entrer en collision
  avec un `session_id` web (UUID ou string arbitraire) grâce au préfixe
- Traçabilité : on sait d'où vient chaque session en regardant son ID

---

## Décision 5 : Retry/backoff dans la boucle de polling

**Choix :** Liste de délais croissants `[2, 5, 10, 30, 60]` secondes

**Raison :**
- Évite de spammer l'API Telegram en cas de panne réseau
- La boucle ne crashe jamais sur une erreur réseau transitoire
- `KeyboardInterrupt` (Ctrl+C) arrête proprement le processus

---

## Statut Phase 2 : ✅ IMPLÉMENTÉE

- Couche service partagée ✅
- Client Telegram HTTP minimal ✅
- Boucle de polling avec retry/backoff ✅
- `routes/chat.py` refactorisé (zéro duplication) ✅
- Tests unitaires `tests/test_conversation_service.py` ✅
- `TELEGRAM_BOT_TOKEN` dans `config.py` ✅

---

## Comment lancer

### 1. Obtenir le token Telegram
1. Ouvre Telegram et cherche **@BotFather**
2. Envoie `/newbot` et suis les instructions
3. Copie le token fourni (format : `123456789:ABCdef...`)

### 2. Ajouter le token dans `.env`
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
```

### 3. Lancer le serveur FastAPI
```bash
cd c:\Users\megbl\Desktop\Yosra\v4
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Lancer le bot Telegram (terminal séparé)
```bash
cd c:\Users\megbl\Desktop\Yosra\v4
python -m backend.integrations.telegram.bot
```

### 5. Lancer les tests
```bash
cd c:\Users\megbl\Desktop\Yosra\v4
pytest tests/test_conversation_service.py -v
```
