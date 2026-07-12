"""LangGraph agent graph definition."""

import os
import re
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from backend.agent.prompts import SYSTEM_PROMPT
from backend.agent.state import GraphState
from backend.airtable_client import AirtableClient
from backend.agent.rag import RagIndex

# Reuse client and RAG index instances globally
_client_instance = None
_rag_index = None

def get_model():
    """Returns the genai client (kept for compatibility with callers)."""
    return get_client()

def get_client():
    global _client_instance
    if _client_instance is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set in environment")
        _client_instance = genai.Client(api_key=api_key)
    return _client_instance

def get_rag_index():
    global _rag_index
    if _rag_index is None:
        _rag_index = RagIndex()
        _rag_index.load_index()
    return _rag_index


class SimpleGeminiWrapper:
    def invoke(self, messages):
        client = get_client()

        system_text = ""
        history = []
        pending_user = None

        for msg in messages:
            if msg.type == "system":
                system_text = msg.content
            elif msg.type == "human":
                pending_user = msg.content
            elif msg.type == "ai" and pending_user is not None:
                history.append(types.Content(role="user", parts=[types.Part(text=pending_user)]))
                history.append(types.Content(role="model", parts=[types.Part(text=msg.content)]))
                pending_user = None

        config = types.GenerateContentConfig(
            system_instruction=system_text,
        )
        history.append(types.Content(role="user", parts=[types.Part(text=pending_user or "")]))
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=history,
            config=config,
        )
        return AIMessage(content=response.text)

_llm_instance = None

def get_llm():
    """Get LangChain LLM instance for Google Gemini."""
    global _llm_instance
    if _llm_instance is None:
        # Check API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set in environment")
        _llm_instance = SimpleGeminiWrapper()
    return _llm_instance


def extract_lead_info_from_history(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Use Gemini to extract lead details from the conversation history."""
    client = get_client()

    history_text = ""
    for msg in messages:
        role = "Prospect" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"

    prompt = f"""Tu es un extracteur d'informations de conversation. Analyse la conversation suivante entre l'Assistant et le Prospect.
Extrais uniquement les informations de contact et de qualification du prospect sous la forme d'un objet JSON plat.

Champs à extraire (si présents, sinon laisse la valeur null) :
- Nom : Le nom de famille du prospect.
- Prenom : Le prénom du prospect.
- Telephone : Le numéro de téléphone du prospect.
- Email : L'adresse email du prospect.
- Adresse : L'adresse postale complète (ex: "13 rue de la Paix").
- Ville : La ville du prospect (ex: "Bruxelles", "Charleroi").
- Fournisseur : Le fournisseur d'énergie actuel (ex: "EDF", "Engie").
- Budget : Le budget électricité/énergie mentionné.
- Date_de_naissance : La date de naissance (ex: "15/08/1990").
- Code_EAN : Le code EAN du compteur d'énergie (18 chiffres commençant par 54).
- Desir_changement : Indique si le prospect veut changer de fournisseur d'énergie ("Oui", "Non", ou null).
- Type_energie : Le type d'énergie (ex: "Electricité", "Gaz", ou "Les deux").

Règles importantes :
- Ne devine aucune information. Si le prospect ne l'a pas donnée ou s'il a dit "je ne sais pas", laisse à null.
- Retourne UNIQUEMENT le code JSON brut, sans blocs de code markdown comme ```json, sans espaces superflus.

Conversation :
{history_text}
"""
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    text = response.text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```json") or lines[0].startswith("```"):
            text = "\n".join(lines[1:-1]).strip()
    
    return json.loads(text)


def extract_lead_info_fallback(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Fallback extraction using simple regex when Gemini API is rate-limited."""
    result = {
        "Nom": None,
        "Prenom": None,
        "Telephone": None,
        "Email": None,
        "Adresse": None,
        "Ville": None,
        "Fournisseur": None,
        "Budget": None,
        "Date_de_naissance": None,
        "Code_EAN": None,
        "Desir_changement": None,
        "Type_energie": None,
    }
    
    # Concatenate all user messages
    user_texts = [msg["content"] for msg in messages if msg["role"] == "user"]
    full_text = " ".join(user_texts)
    
    # 1. Email extraction
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", full_text)
    if email_match:
        result["Email"] = email_match.group(0)
        
    # 2. Phone extraction
    phone_match = re.search(r"(\+?\d[\d\s\.]{8,}\d)", full_text)
    if phone_match:
        raw_phone = phone_match.group(0)
        cleaned_phone = re.sub(r"[^\d+]", "", raw_phone)
        if len(cleaned_phone) >= 10:
            result["Telephone"] = cleaned_phone
            
    # 3. Nom/Prenom extraction
    name_match = re.search(r"(?:je m'appelle|mon nom est|je suis)\s+(\w+)\s+(\w+)", full_text, re.IGNORECASE)
    if name_match:
        result["Prenom"] = name_match.group(1).capitalize()
        result["Nom"] = name_match.group(2).capitalize()
    else:
        # Heuristic: if user is prompted for contact details (turn count >= 3)
        # and they enter exactly two alphabetic words, treat them as Prenom and Nom
        latest_user_msgs = [m["content"] for m in messages if m["role"] == "user"]
        if latest_user_msgs:
            last_msg = latest_user_msgs[-1].strip().strip(",").strip()
            words = last_msg.split()
            if len(words) == 2 and words[0].isalpha() and words[1].isalpha():
                result["Prenom"] = words[0].capitalize()
                result["Nom"] = words[1].capitalize()
        
    # 4. Fournisseur extraction
    full_text_lower = full_text.lower()
    if "edf" in full_text_lower:
        result["Fournisseur"] = "EDF"
    elif "engie" in full_text_lower:
        result["Fournisseur"] = "Engie"
    elif "total" in full_text_lower:
        result["Fournisseur"] = "TotalEnergies"
    elif "luminus" in full_text_lower:
        result["Fournisseur"] = "Luminus"
    elif "eneco" in full_text_lower:
        result["Fournisseur"] = "Eneco"
        
    # 5. Budget extraction
    budget_match = re.search(r"\b(\d{3,5})\b", full_text)
    if budget_match:
        result["Budget"] = budget_match.group(1)
        
    # 6. Adresse/Ville extraction
    addr_match = re.search(r"(\d+\s+rue\s+[\w\s-]+|\d+\s+avenue\s+[\w\s-]+|\d+\s+boulevard\s+[\w\s-]+)", full_text, re.IGNORECASE)
    if addr_match:
        result["Adresse"] = addr_match.group(0).strip()
    
    # Simple city match for Belgium
    cities = ["charleroi", "liège", "liege", "namur", "mons", "gand", "gent", "anvers", "antwerpen", "bruges", "brugge", "bruxelles", "brussels"]
    for city in cities:
        if city in full_text_lower:
            result["Ville"] = city.capitalize()
            break

    # 7. Code EAN extraction (18 digits starting with 54)
    ean_match = re.search(r"\b(54\d{16})\b", full_text)
    if ean_match:
        result["Code_EAN"] = ean_match.group(1)

    # 8. Date de naissance (DD-MM-YYYY or DD/MM/YYYY)
    dob_match = re.search(r"\b(\d{2}[-/. ]\d{2}[-/. ]\d{4})\b", full_text)
    if dob_match:
        result["Date_de_naissance"] = dob_match.group(1)

    # 9. Désir de changement
    if any(keyword in full_text_lower for keyword in ["change", "passer chez", "quitter", "rejoindre", "nouveau contrat", "souscrire"]):
        result["Desir_changement"] = "Oui"
    elif any(keyword in full_text_lower for keyword in ["pas intéressé", "pas intéresse", "ne veux pas", "ne souhaite pas", "rester", "garde mon"]):
        result["Desir_changement"] = "Non"
    elif any(keyword in full_text_lower for keyword in ["peut-être", "peut etre", "je réfléchis", "je reflechis", "pas sûr", "pas sur", "indécis"]):
        result["Desir_changement"] = "Indécis"

    # 10. Type d'énergie
    if "gaz" in full_text_lower and ("élec" in full_text_lower or "elec" in full_text_lower):
        result["Type_energie"] = "Les deux"
    elif "gaz" in full_text_lower:
        result["Type_energie"] = "Gaz"
    elif "élec" in full_text_lower or "elec" in full_text_lower:
        result["Type_energie"] = "Électricité"
        
    return result


def get_mock_agent_response(messages: List[Dict[str, str]]) -> str:
    """Mock conversation agent flow when Gemini API is rate-limited."""
    user_messages = [msg for msg in messages if msg["role"] == "user"]
    turn_count = len(user_messages)
    
    # Check if the user is asking a question about Ecofix offers or referral program
    if user_messages:
        last_msg_lower = user_messages[-1]["content"].lower()
        if "offre" in last_msg_lower or "propos" in last_msg_lower or "formule" in last_msg_lower:
            return (
                "Chez Ecofix Gas & Power, nous proposons deux formules principales pour l'électricité et le gaz :\n\n"
                "1. **Ecofix Flexy (Tarif Variable)** : Notre offre classique avec un prix réajusté chaque mois selon "
                "le marché, des frais de plateforme de 5,99 €/mois et un service client complet (téléphone et en ligne).\n"
                "2. **Ecofix Motion (Tarif Dynamique)** : Le prix est indexé en temps réel sur le marché (mis à jour "
                "toutes les 15 minutes). C'est parfait si vous pouvez décaler vos consommations (comme recharger votre voiture la nuit).\n\n"
                "Ces offres existent aussi en version 'Online' 100% digitale (sans support téléphonique) pour de plus grandes économies."
            )
        if "parrain" in last_msg_lower or "friends" in last_msg_lower or "benefit" in last_msg_lower:
            return (
                "Notre programme de parrainage **'Friends with Benefits'** est très simple : pour chaque ami parrainé "
                "qui souscrit un contrat actif chez Ecofix, vous bénéficiez d'une réduction récurrente de **5 € par mois** "
                "(60 €/an) sur votre facture. Cette réduction est cumulable, donc si vous parrainez 2 amis, "
                "vous économisez environ 120 € par an !"
            )
    
    if turn_count <= 1:
        return (
            "Enchanté ! C'est bien noté. Pour que je puisse vous orienter au mieux, "
            "s'agit-il plutôt d'un projet pour votre habitation personnelle (maison/appartement) "
            "ou pour des locaux professionnels (bâtiment, bureaux) ?"
        )
    elif turn_count == 2:
        return (
            "Très bien ! Quel est votre fournisseur d'électricité actuel (ex: EDF, Engie, TotalEnergies) "
            "et quel est le montant approximatif de votre facture annuelle (ex: 1000 €) ?"
        )
    elif turn_count == 3:
        return (
            "C'est bien noté ! Afin que nous puissions affiner notre proposition tarifaire selon votre région, "
            "quelle est votre adresse postale complète et votre ville ?"
        )
    elif turn_count == 4:
        return (
            "Merci ! Pour finaliser votre dossier et que je puisse vous envoyer votre étude comparative "
            "gratuite (et vous envoyer un SMS quand elle est prête), pourriez-vous me donner votre Nom, "
            "votre Prénom, votre adresse e-mail ainsi que votre numéro de téléphone ?"
        )
    else:
        return (
            "Parfait, j'ai bien noté toutes vos coordonnées ! Nous préparons votre étude comparative "
            "gratuite et nous vous l'enverrons sous 24 à 48 heures. Je vous souhaite une excellente journée ! 👋"
        )



def check_eligibility(lead_info: Dict[str, Any]) -> Optional[bool]:
    """
    Check if the lead meets Ecofix eligibility conditions:
    1. Ville / Adresse: Must not be in Brussels region (e.g. Bruxelles, Ixelles, Uccle, etc.).
       Must be in Wallonia or Flanders. If the city is filled, we can check.
    2. Date de naissance / Age: Must be >= 18.
    3. Code EAN: Must start with '54' and be 18 digits.
    4. Desir de changement: Should be positive/Yes (if provided).
    
    Returns True if fully eligible, False if ineligible, None if we don't have enough data yet.
    """
    # 1. Check Brussels region
    ville = lead_info.get("Ville")
    adresse = lead_info.get("Adresse")
    
    ineligible_cities = ["bruxelles", "brussels", "ixelles", "uccle", "evere", "anderlecht", "schaerbeek", "saint-gilles", "forest", "jette", "etterbeek", "woluwe"]
    
    if ville:
        v_lower = ville.lower()
        if any(c in v_lower for c in ineligible_cities):
            return False
            
    if adresse:
        a_lower = adresse.lower()
        if any(c in a_lower for c in ineligible_cities):
            return False
            
    # 2. Check Age
    dob = lead_info.get("Date_de_naissance")
    if dob:
        try:
            clean_dob = re.sub(r"[-. ]", "/", dob.strip())
            parts = clean_dob.split("/")
            if len(parts) == 3:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                birth_date = datetime(year, month, day)
                age = (datetime.utcnow() - birth_date).days / 365.25
                if age < 18:
                    return False
        except Exception:
            pass
            
    # 3. Check Code EAN
    ean = lead_info.get("Code_EAN")
    if ean:
        clean_ean = re.sub(r"\D", "", ean)
        if len(clean_ean) != 18 or not clean_ean.startswith("54"):
            return False

    # 4. Check desire to change
    desir = lead_info.get("Desir_changement")
    if desir and desir in ["Non"]:
        return False
        
    # Check if we have the critical data to declare them eligible
    has_location = bool(ville or adresse)
    has_dob = bool(dob)
    has_ean = bool(ean)
    has_desir = bool(desir)
    
    # If all mandatory fields for eligibility check are present, it's True
    if has_location and has_dob and has_ean and has_desir:
        return True
        
    return None


def calculate_lead_score(lead_info: Dict[str, Any]) -> int:
    """
    Calculate deterministic lead score (0-100) based on docs/knowledge_base/lead_scoring.md.
    """
    score = 0
    
    # 1. Customer Contact Information (Max 50 pts)
    if lead_info.get("Prenom"):
        score += 5
    if lead_info.get("Nom"):
        score += 5
    if lead_info.get("Telephone"):
        score += 15
    if lead_info.get("Email"):
        score += 10
    if lead_info.get("Adresse"):
        score += 15
    elif lead_info.get("Ville"):
        score += 10 # Fallback for city only
        
    # 2. Energy Information (Max 35 pts)
    if lead_info.get("Fournisseur"):
        score += 10 # Current supplier
    if lead_info.get("Type_energie"):
        score += 5  # Energy type
    if lead_info.get("Code_EAN"):
        score += 20 # EAN number
        
    # 3. Purchase Intent (Max 50 pts)
    desir = lead_info.get("Desir_changement")
    if desir == "Oui":
        score += 20
        score += 10
        
    # If EAN is provided, they request next step (implied, +10)
    if lead_info.get("Code_EAN"):
        score += 10
        
    # Negative signals (applied as malus)
    # Check if ineligible
    elig = check_eligibility(lead_info)
    if elig is False:
        score -= 50 # Fake/Invalid/Ineligible
        
    # Ensure score is within 0-100 bounds
    return max(0, min(100, score))


def detect_intent_fallback(message: str) -> str:
    """Fallback heuristic for intent classification."""
    msg_lower = message.lower()
    if any(word in msg_lower for word in ["bonjour", "salut", "hello", "hi"]):
        return "greeting"
    if any(word in msg_lower for word in ["cher", "coupure", "risqu", "peur", "doute", "engie", "luminus"]):
        return "objection"
    if any(word in msg_lower for word in ["combien", "tarif", "offre", "flexy", "motion", "dynamique", "variable"]):
        return "product_question"
    if any(word in msg_lower for word in ["changement", "changer", "résiliation", "resilier", "migrer", "transition"]):
        return "switching_question"
    if any(word in msg_lower for word in ["merci", "au revoir", "bye", "fin", "bonne journée"]):
        return "closing"
    if "@" in msg_lower or any(char.isdigit() for char in msg_lower):
        return "qualification"
    return "faq"


def intent_router_node(state: GraphState) -> Dict[str, Any]:
    """Classifies user intent based on the last message."""
    messages_list = state.get("messages", [])
    user_messages = [m["content"] for m in messages_list if m["role"] == "user"]
    if not user_messages:
        return {"intent": "greeting"}

    latest_message = user_messages[-1]

    prompt = f"""Tu es un classifieur d'intentions utilisateur. Analyse le message suivant du client et classe-le dans EXACTEMENT UNE des catégories suivantes :
- greeting : Si le client dit bonjour, salue, ou débute la conversation.
- product_question : Si le client pose une question sur les offres d'Ecofix (Flexy, Motion, tarifs, gaz, électricité).
- objection : Si le client exprime un doute, une plainte, ou une objection (trop cher, peur de coupure, fidélité à son fournisseur actuel).
- switching_question : Si le client pose une question sur le processus de changement de fournisseur (délais, résiliation, transition).
- faq : Si le client pose une question d'ordre général ou fréquemment posée.
- qualification : Si le client fournit ses informations (nom, prénom, e-mail, téléphone, adresse, date de naissance, EAN).
- follow_up : Si le client demande à être recontacté, à recevoir une étude ou demande un suivi.
- closing : Si le client termine la conversation (merci, au revoir, bonne journée).
- off_topic : Si le client parle de quelque chose de complètement sans rapport avec l'énergie ou Ecofix.

Message du client : "{latest_message}"

Retourne uniquement le mot-clé de la catégorie en minuscule (ex: "faq", "objection", "qualification"). Sans aucun autre texte.
"""
    try:
        client = get_client()
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        intent = response.text.strip().lower()
        intent = re.sub(r"[^a-z_]", "", intent)
        valid_intents = {
            "greeting", "product_question", "objection", "switching_question",
            "faq", "qualification", "follow_up", "closing", "off_topic"
        }
        if intent not in valid_intents:
            intent = detect_intent_fallback(latest_message)
    except Exception as e:
        print(f"[Intent Router] Error calling LLM: {e}")
        intent = detect_intent_fallback(latest_message)
        
    return {"intent": intent}


def route_by_intent(state: GraphState) -> str:
    """Routes to retrieval or direct generation based on intent."""
    intent = state.get("intent")
    rag_intents = {"product_question", "objection", "switching_question", "faq"}
    if intent in rag_intents:
        return "retrieve_knowledge"
    return "generate_response"


def retrieve_knowledge_node(state: GraphState) -> Dict[str, Any]:
    """Retrieves relevant knowledge chunks from RAG index."""
    messages_list = state.get("messages", [])
    user_messages = [m["content"] for m in messages_list if m["role"] == "user"]
    latest_user_message = user_messages[-1] if user_messages else ""
    
    retrieved_sources = []
    intent = state.get("intent")
    if latest_user_message:
        try:
            index = get_rag_index()
            rag_res = index.retrieve(latest_user_message, top_n=2)
            chunks = rag_res.get("chunks", [])
            max_score = rag_res.get("max_score", 0.0)
            
            is_question = "?" in latest_user_message or any(
                word in latest_user_message.lower() 
                for word in ["comment", "pourquoi", "qu'est", "est-ce", "vendez", "proposez", "tarif", "prix", "quel", "quelles", "combien"]
            )
            
            if max_score < 0.67 and is_question:
                return {"intent": "off_topic", "retrieved_sources": []}
            elif chunks and max_score >= 0.67:
                retrieved_sources = chunks
        except Exception as ex:
            print(f"[RAG] Error retrieving context in node: {ex}")
            
    return {"retrieved_sources": retrieved_sources, "intent": intent}


def generate_response_node(state: GraphState) -> Dict[str, Any]:
    """Generates assistant response using Gemini and extracts new lead info with validation."""
    messages_list = state.get("messages", [])
    lead_info = state.get("lead_info", {})
    if lead_info is None:
        lead_info = {}
    else:
        lead_info = lead_info.copy()

    intent = state.get("intent")
    retrieved_sources = state.get("retrieved_sources") or []

    # Si la conversation est déjà complétée, répondre poliment sans relancer le closing
    if state.get("conversation_completed"):
        _COMPLETED_REPLIES = [
            "Votre dossier est déjà complet. N'hésitez pas si vous avez d'autres questions ! 😊",
            "Tout est en ordre de notre côté. Un conseiller vous contactera très prochainement.",
            "Votre demande a bien été enregistrée. Avez-vous une question en attendant ?",
        ]
        turn = state.get("conversation_turn", 0)
        reply = _COMPLETED_REPLIES[turn % len(_COMPLETED_REPLIES)]
        new_messages = messages_list.copy()
        new_messages.append({"role": "assistant", "content": reply})
        return {"messages": new_messages, "lead_info": lead_info}

    response_text = ""
    
    if intent == "off_topic":
        response_text = "Je n'ai pas cette information précise, mais un de nos conseillers pourra vous répondre."
    else:
        score_ia = calculate_lead_score(lead_info)
        system_prompt_with_context = SYSTEM_PROMPT
        if retrieved_sources:
            system_prompt_with_context += "\n\nInformations complémentaires issues de la base de connaissances :\n" + "\n---\n".join(retrieved_sources)
            
        system_prompt_with_context += f"\n\n[CONTEXTE DU LEAD - SCORE IA ACTUEL : {score_ia}/100]"
        
        chat_messages = [SystemMessage(content=system_prompt_with_context)]
        for msg in messages_list:
            if msg["role"] == "user":
                chat_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                chat_messages.append(AIMessage(content=msg["content"]))
                
        try:
            llm = get_llm()
            res_msg = llm.invoke(chat_messages)
            response_text = res_msg.content
            print("[AGENT MODE] ✅ Gemini réel")
        except Exception as e:
            print(f"[AGENT MODE] ⚠️ MOCK activé — Gemini indisponible : {e}")
            response_text = get_mock_agent_response(messages_list)
            
    # Extract lead details
    try:
        extracted = extract_lead_info_from_history(messages_list)
        print("[EXTRACTION] ✅ Gemini réel")
    except Exception as e:
        print(f"[EXTRACTION] ⚠️ Fallback regex activé — {e}")
        extracted = extract_lead_info_fallback(messages_list)
    # Strict validation rules
    EMAIL_VALID_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    PHONE_VALID_REGEX = re.compile(r"^\+?[\d\s-]{8,15}$")
    NAME_VALID_REGEX = re.compile(r"^[a-zA-ZÀ-ÿ\s'-]{2,}$")
    
    rejected_fields = []
    
    extracted_email = extracted.get("Email")
    if extracted_email:
        extracted_email = str(extracted_email).strip()
        if not EMAIL_VALID_REGEX.match(extracted_email):
            rejected_fields.append("adresse e-mail")
            extracted["Email"] = None
            
    extracted_phone = extracted.get("Telephone")
    if extracted_phone:
        extracted_phone = str(extracted_phone).strip()
        digits_only = re.sub(r"\D", "", extracted_phone)
        if not PHONE_VALID_REGEX.match(extracted_phone) or not (8 <= len(digits_only) <= 15):
            rejected_fields.append("numéro de téléphone")
            extracted["Telephone"] = None
            
    extracted_nom = extracted.get("Nom")
    if extracted_nom:
        extracted_nom = str(extracted_nom).strip()
        if not NAME_VALID_REGEX.match(extracted_nom) or extracted_nom.isdigit():
            rejected_fields.append("nom")
            extracted["Nom"] = None
            
    extracted_prenom = extracted.get("Prenom")
    if extracted_prenom:
        extracted_prenom = str(extracted_prenom).strip()
        if not NAME_VALID_REGEX.match(extracted_prenom) or extracted_prenom.isdigit():
            rejected_fields.append("prénom")
            extracted["Prenom"] = None

    extracted_ean = extracted.get("Code_EAN")
    if extracted_ean:
        extracted_ean = str(extracted_ean).strip()
        digits_ean = re.sub(r"\D", "", extracted_ean)
        if len(digits_ean) != 18 or not digits_ean.startswith("54"):
            rejected_fields.append("code EAN (qui doit comporter 18 chiffres et commencer par 54)")
            extracted["Code_EAN"] = None

    extracted_dob = extracted.get("Date_de_naissance")
    if extracted_dob:
        extracted_dob = str(extracted_dob).strip()
        clean_dob = re.sub(r"[-. ]", "/", extracted_dob)
        parts = clean_dob.split("/")
        valid_dob = False
        if len(parts) == 3:
            try:
                d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                if 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= datetime.utcnow().year:
                    valid_dob = True
            except ValueError:
                pass
        if not valid_dob:
            rejected_fields.append("date de naissance (au format JJ/MM/AAAA)")
            extracted["Date_de_naissance"] = None
            
    if rejected_fields:
        if len(rejected_fields) == 1:
            rej_str = rejected_fields[0]
        elif len(rejected_fields) == 2:
            rej_str = f"{rejected_fields[0]} et {rejected_fields[1]}"
        else:
            rej_str = ", ".join(rejected_fields[:-1]) + f" et {rejected_fields[-1]}"
            
        response_text = (
            f"Certaines informations saisies ne semblent pas valides : {rej_str}. "
            "Pourriez-vous me les redonner correctement ?"
        )
        
    for k, v in extracted.items():
        if v is not None:
            lead_info[k] = v
            
    new_messages = messages_list.copy()
    new_messages.append({"role": "assistant", "content": response_text})
    
    return {
        "messages": new_messages,
        "lead_info": lead_info
    }


def existing_qualification_node(state: GraphState) -> Dict[str, Any]:
    """Applies eligibility checks, validation interceptor, and computes final score."""
    messages_list = state.get("messages", [])
    lead_info = state.get("lead_info", {})
    if lead_info is None:
        lead_info = {}
    else:
        lead_info = lead_info.copy()
        
    response_text = messages_list[-1]["content"] if messages_list else ""
    
    has_email = bool(lead_info.get("Email"))
    has_phone = bool(lead_info.get("Telephone"))
    has_nom = bool(lead_info.get("Nom"))
    has_prenom = bool(lead_info.get("Prenom"))
    has_location = bool(lead_info.get("Adresse") or lead_info.get("Ville"))
    has_dob = bool(lead_info.get("Date_de_naissance"))
    has_ean = bool(lead_info.get("Code_EAN"))
    has_desir = bool(lead_info.get("Desir_changement"))
    
    user_msgs = [m for m in messages_list if m["role"] == "user"]
    user_msgs_count = len(user_msgs)
    
    is_concluding = any(word in response_text.lower() for word in ["bientôt", "journée", "coordonnées", "préparons", "revoir", "semaine"])
    is_mock_fallback = response_text.startswith("C'est bien noté") or response_text.startswith("Merci !") or response_text.startswith("Parfait")
    
    if is_concluding or (is_mock_fallback and user_msgs_count >= 5):
        missing = []
        if not has_prenom:
            missing.append("votre prénom")
        if not has_nom:
            missing.append("votre nom")
        if not has_email:
            missing.append("votre adresse e-mail")
        if not has_phone:
            missing.append("votre numéro de téléphone")
        if not has_location:
            missing.append("votre adresse ou ville (Wallonie/Flandre)")
        if not has_dob:
            missing.append("votre date de naissance")
        if not has_ean:
            missing.append("votre code EAN (18 chiffres)")
        if not has_desir:
            missing.append("votre confirmation pour changer de fournisseur")
            
        if missing:
            if len(missing) == 1:
                missing_str = missing[0]
            elif len(missing) == 2:
                missing_str = f"{missing[0]} et {missing[1]}"
            else:
                missing_str = ", ".join(missing[:-1]) + f" et {missing[-1]}"
                
            response_text = (
                f"J'ai bien noté ces informations, mais il me manque {missing_str} "
                "pour finaliser votre dossier et évaluer votre éligibilité chez Ecofix. Pouvez-vous les indiquer ?"
            )

    elig = check_eligibility(lead_info)
    if elig is False:
        response_text = (
            "Nous vous remercions de votre intérêt pour Ecofix Gas & Power. Malheureusement, "
            "après vérification de vos informations, nous ne pouvons pas valider votre éligibilité. "
            "En effet, nous ne desservons pas la région de Bruxelles (nos offres sont réservées uniquement à la Flandre et à la Wallonie), "
            "nos offres sont réservées aux personnes majeures, et nécessitent un code EAN belge valide (commençant par 54). "
            "Nous vous remercions pour votre temps et vous souhaitons une très bonne continuation."
        )
        lead_info["Eligible"] = False
    elif elig is True:
        response_text = (
            "Parfait ! Vos informations ont été vérifiées et votre éligibilité est confirmée. "
            "Votre dossier est maintenant complet (Code EAN validé, région desservie). "
            "Nous avons créé votre fiche Lead dans notre CRM avec succès et le statut est marqué comme qualifié. "
            "Un de nos conseillers va préparer votre étude comparative et vous l'envoyer dans les plus brefs délais. "
            "Merci d'avoir choisi Ecofix Gas & Power, et à très bientôt !"
        )
        lead_info["Eligible"] = True
        
    score_ia = calculate_lead_score(lead_info)
    lead_info["Score_IA"] = score_ia
    
    conversation_stage = "Qualification"
    conversation_completed = False
    if elig is True:
        conversation_stage = "Qualified"
        qualification_status = "Qualified"
        conversation_completed = True
    elif elig is False:
        conversation_stage = "Rejected"
        qualification_status = "Rejected"
        conversation_completed = True
    else:
        qualification_status = "Contacted"
        
    new_messages = messages_list.copy()
    if new_messages and new_messages[-1]["role"] == "assistant":
        new_messages[-1]["content"] = response_text
        
    return {
        "messages": new_messages,
        "lead_info": lead_info,
        "lead_score": score_ia,
        "qualification_status": qualification_status,
        "conversation_stage": conversation_stage,
        "conversation_completed": conversation_completed
    }


def _generate_conversation_summary(messages_list: List[Dict[str, str]], lead_info: Dict[str, Any]) -> str:
    """Generate a short AI summary of the conversation for Airtable."""
    prenom = lead_info.get("Prenom") or ""
    nom = lead_info.get("Nom") or ""
    fournisseur = lead_info.get("Fournisseur") or ""
    ville = lead_info.get("Ville") or ""
    score = lead_info.get("Score_IA", 0)
    turn_count = sum(1 for m in messages_list if m["role"] == "user")
    parts = [f"Conversation de {turn_count} échange(s)."]
    if prenom or nom:
        parts.append(f"Prospect : {prenom} {nom}".strip())
    if fournisseur:
        parts.append(f"Fournisseur actuel : {fournisseur}.")
    if ville:
        parts.append(f"Ville : {ville}.")
    if score:
        parts.append(f"Score IA : {score}/100.")
    return " ".join(parts)


def crm_sync_node(state: GraphState) -> Dict[str, Any]:
    """Syncs lead details and conversation history to Airtable CRM."""
    messages_list = state.get("messages", [])
    lead_info = state.get("lead_info", {})
    if lead_info is None:
        lead_info = {}
    lead_id = state.get("lead_id")
    qualification_status = state.get("qualification_status") or "Contacted"
    score_ia = state.get("lead_score") or 0
    elig = lead_info.get("Eligible")
    intent = state.get("intent") or ""
    
    has_email = bool(lead_info.get("Email"))
    has_phone = bool(lead_info.get("Telephone"))
    
    email = lead_info.get("Email")
    phone = lead_info.get("Telephone")
    email_invalid = email and not re.match(r"[\w\.-]+@[\w\.-]+\.\w+", email)
    phone_invalid = phone and len(re.sub(r"[^\d+]", "", phone)) < 10
    
    if (has_email or has_phone) and not (email_invalid or phone_invalid):
        try:
            airtable_client = AirtableClient()
            
            airtable_fields = {
                "Nom": lead_info.get("Nom"),
                "Prénom": lead_info.get("Prenom"),
                "Téléphone": lead_info.get("Telephone"),
                "Email": lead_info.get("Email"),
                "Adresse": lead_info.get("Adresse"),
                "Ville": lead_info.get("Ville"),
                "Fournisseur actuel": lead_info.get("Fournisseur"),
                "Code EAN": lead_info.get("Code_EAN"),
                "Date de naissance": lead_info.get("Date_de_naissance"),
                "Désir de changement": lead_info.get("Desir_changement") if lead_info.get("Desir_changement") in ("Oui", "Non", "Indécis") else None,
                "Éligible": elig if elig is not None else False,
                "Statut": qualification_status,
                "Score IA": score_ia,
            }
            airtable_fields = {k: v for k, v in airtable_fields.items() if v is not None}
            
            provider = lead_info.get("Fournisseur") or "EDF"
            airtable_fields["Prochaine action"] = f"Envoyer étude comparative {provider}"
            
            if not lead_id:
                existing_record = None
                if lead_info.get("Email"):
                    existing_record = airtable_client.find_by_field("Leads", "Email", lead_info["Email"])
                if not existing_record and lead_info.get("Telephone"):
                    existing_record = airtable_client.find_by_field("Leads", "Téléphone", lead_info["Telephone"])
                    
                if existing_record:
                    lead_id = existing_record["id"]
                    airtable_client.update_record("Leads", lead_id, airtable_fields)
                else:
                    created_record = airtable_client.create_record("Leads", airtable_fields)
                    lead_id = created_record["id"]
            else:
                airtable_client.update_record("Leads", lead_id, airtable_fields)
                
            date_str = datetime.utcnow().isoformat() + "Z"
            user_msgs = [m for m in messages_list if m["role"] == "user"]
            latest_user_message = user_msgs[-1]["content"] if user_msgs else ""
            response_text = messages_list[-1]["content"] if messages_list else ""
            
            resume_ia = _generate_conversation_summary(messages_list, lead_info)
            conv_fields = {
                "Lead": [lead_id],
                "Date": date_str,
                "Message client": latest_user_message,
                "Réponse IA": response_text,
                "Intent détecté": intent,
                "Objection": latest_user_message if intent == "objection" else None,
                "Résumé IA": resume_ia,
            }
            conv_fields = {k: v for k, v in conv_fields.items() if v is not None}
            try:
                airtable_client.create_record("Conversations", conv_fields)
            except Exception as ex:
                print(f"Error logging conversation: {ex}")
        except Exception as e:
            print(f"[CRM Sync] Error communicating with Airtable: {e}")
            
    turn = state.get("conversation_turn", 0) + 1
    
    return {
        "conversation_turn": turn,
        "lead_id": lead_id,
        "lead_info": lead_info
    }


def create_agent_graph():
    """Create the LangGraph graph for the agent."""
    from langgraph.graph import StateGraph, END
    
    graph_builder = StateGraph(GraphState)
    
    # Add nodes
    graph_builder.add_node("intent_router", intent_router_node)
    graph_builder.add_node("retrieve_knowledge", retrieve_knowledge_node)
    graph_builder.add_node("generate_response", generate_response_node)
    graph_builder.add_node("existing_qualification", existing_qualification_node)
    graph_builder.add_node("crm_sync", crm_sync_node)
    
    # Define execution flow
    graph_builder.set_entry_point("intent_router")
    
    # Conditional edge from intent_router
    graph_builder.add_conditional_edges(
        "intent_router",
        route_by_intent,
        {
            "retrieve_knowledge": "retrieve_knowledge",
            "generate_response": "generate_response"
        }
    )
    
    # Edges
    graph_builder.add_edge("retrieve_knowledge", "generate_response")
    graph_builder.add_edge("generate_response", "existing_qualification")
    graph_builder.add_edge("existing_qualification", "crm_sync")
    graph_builder.add_edge("crm_sync", END)
    
    return graph_builder.compile()


# Global graph instance
agent_graph = None


def get_agent_graph():
    """Get or create the agent graph."""
    global agent_graph
    if agent_graph is None:
        agent_graph = create_agent_graph()
    return agent_graph
