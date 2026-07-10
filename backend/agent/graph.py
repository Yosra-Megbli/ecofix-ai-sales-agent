"""LangGraph agent graph definition."""

import os
import re
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from backend.agent.prompts import SYSTEM_PROMPT
from backend.agent.state import GraphState
from backend.airtable_client import AirtableClient
from backend.agent.rag import RagIndex

# Configure globally
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key, transport="rest")

# Reuse model and RAG index instances globally to allow HTTP connection pooling
_model_instance = None
_rag_index = None

def get_model():
    global _model_instance
    if _model_instance is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set in environment")
        _model_instance = genai.GenerativeModel(model_name="gemini-flash-latest")
    return _model_instance

def get_rag_index():
    global _rag_index
    if _rag_index is None:
        _rag_index = RagIndex()
        _rag_index.load_index()
    return _rag_index


class SimpleGeminiWrapper:
    def invoke(self, messages):
        # Convert LangChain messages to simple format
        text_messages = []
        for msg in messages:
            text_messages.append(f"{msg.type}: {msg.content}")
        
        prompt = "\n".join(text_messages)
        
        # Call Gemini API using global model
        model = get_model()
        response = model.generate_content(prompt)
        
        # Return LangChain-compatible response
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
    model = get_model()
    
    # Construct conversation transcript for LLM
    history_text = ""
    for msg in messages:
        role = "Prospect" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"
        
    prompt = f"""Tu es un extracteur d'informations de conversation. Analyse la conversation suivante entre l'Assistant et le Prospect.
Extrais uniquement les informations de contact et de qualification du prospect sous la forme d'un objet JSON plat.

Champs à extraire (si présents, sinon laisse la valeur null) :
- Nom : Le nom de famille du prospect.
- Prenom : Le prénom du prospect (ou prénom + nom s'il n'y a qu'un nom fourni).
- Telephone : Le numéro de téléphone du prospect.
- Email : L'adresse email du prospect.
- Adresse : L'adresse postale complète (ex: "13 rue de la Paix").
- Ville : La ville du prospect (ex: "Paris").
- Fournisseur : Le fournisseur d'électricité actuel (ex: "EDF", "Engie").
- Budget : Le budget électricité mentionné (ex: "1000" ou "1000 €/an").

Règles importantes :
- Ne devine aucune information. Si le prospect ne l'a pas donnée ou s'il a dit "je ne sais pas", laisse à null.
- Retourne UNIQUEMENT le code JSON brut, sans blocs de code markdown comme ```json, sans espaces superflus.

Conversation :
{history_text}
"""
    # Let exception propagate so process_message_node can handle the fallback
    response = model.generate_content(prompt)
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
        
    # 5. Budget extraction
    budget_match = re.search(r"\b(\d{3,5})\b", full_text)
    if budget_match:
        result["Budget"] = budget_match.group(1)
        
    # 6. Adresse/Ville extraction
    addr_match = re.search(r"(\d+\s+rue\s+[\w\s-]+|\d+\s+avenue\s+[\w\s-]+|\d+\s+boulevard\s+[\w\s-]+)", full_text, re.IGNORECASE)
    if addr_match:
        result["Adresse"] = addr_match.group(0).strip()
    if "paris" in full_text_lower:
        result["Ville"] = "Paris"
    elif "lyon" in full_text_lower:
        result["Ville"] = "Lyon"
    elif "marseille" in full_text_lower:
        result["Ville"] = "Marseille"
        
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



def process_message_node(state: GraphState) -> Dict[str, Any]:
    """
    Node that processes user message, validates email, extracts lead info,
    and updates/saves lead and conversation in Airtable.
    """
    try:
        from concurrent.futures import ThreadPoolExecutor
        
        llm = get_llm()
        messages_list = state.get("messages", [])
        lead_id = state.get("lead_id")
        lead_info = state.get("lead_info", {})
        if lead_info is None:
            lead_info = {}
            
        # Get latest user message to query the RAG index
        user_messages = [m["content"] for m in messages_list if m["role"] == "user"]
        latest_user_message = user_messages[-1] if user_messages else ""
        
        # Query RAG
        rag_context = ""
        if latest_user_message:
            try:
                index = get_rag_index()
                chunks = index.retrieve(latest_user_message, top_n=2)
                if chunks:
                    rag_context = "\n\nInformations complémentaires issues de la base de connaissances :\n" + "\n---\n".join(chunks)
            except Exception as ex:
                print(f"[RAG] Error retrieving context: {ex}")
                
        # Build messages for LLM
        system_prompt_with_context = SYSTEM_PROMPT
        if rag_context:
            system_prompt_with_context += rag_context
            
        chat_messages = [SystemMessage(content=system_prompt_with_context)]
        for msg in messages_list:
            if msg["role"] == "user":
                chat_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                chat_messages.append(AIMessage(content=msg["content"]))
                
        # Add user message and temporary assistant response to messages for extraction
        temp_messages = messages_list.copy() if messages_list else []
        
        # Call LLM for assistant reply and perform extraction in parallel
        response_text = ""
        extracted = {}
        fallback_llm = False
        fallback_ext = False
        
        def run_llm():
            try:
                resp = llm.invoke(chat_messages)
                return resp.content, False
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower():
                    return get_mock_agent_response(messages_list), True
                raise e
                
        def run_extraction():
            try:
                return extract_lead_info_from_history(temp_messages), False
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower():
                    return extract_lead_info_fallback(temp_messages), True
                raise e
                
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_llm = executor.submit(run_llm)
            future_ext = executor.submit(run_extraction)
            
            try:
                response_text, fallback_llm = future_llm.result()
            except Exception as e:
                raise e
                
            try:
                extracted, fallback_ext = future_ext.result()
            except Exception as e:
                extracted = extract_lead_info_fallback(temp_messages)
                fallback_ext = True
                
        is_mock_fallback = fallback_llm or fallback_ext
        
        # Strict validation rules
        EMAIL_VALID_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
        PHONE_VALID_REGEX = re.compile(r"^\+?[\d\s-]{8,15}$")
        NAME_VALID_REGEX = re.compile(r"^[a-zA-ZÀ-ÿ\s'-]{2,}$")
        
        rejected_fields = []
        
        # 1. Email check
        extracted_email = extracted.get("Email")
        if extracted_email:
            extracted_email = str(extracted_email).strip()
            if not EMAIL_VALID_REGEX.match(extracted_email):
                rejected_fields.append("adresse e-mail")
                extracted["Email"] = None
                
        # 2. Telephone check
        extracted_phone = extracted.get("Telephone")
        if extracted_phone:
            extracted_phone = str(extracted_phone).strip()
            digits_only = re.sub(r"\D", "", extracted_phone)
            if not PHONE_VALID_REGEX.match(extracted_phone) or not (8 <= len(digits_only) <= 15):
                rejected_fields.append("numéro de téléphone")
                extracted["Telephone"] = None
                
        # 3. Nom check
        extracted_nom = extracted.get("Nom")
        if extracted_nom:
            extracted_nom = str(extracted_nom).strip()
            if not NAME_VALID_REGEX.match(extracted_nom) or extracted_nom.isdigit():
                rejected_fields.append("nom")
                extracted["Nom"] = None
                
        # 4. Prenom check
        extracted_prenom = extracted.get("Prenom")
        if extracted_prenom:
            extracted_prenom = str(extracted_prenom).strip()
            if not NAME_VALID_REGEX.match(extracted_prenom) or extracted_prenom.isdigit():
                rejected_fields.append("prénom")
                extracted["Prenom"] = None
                
        if rejected_fields:
            # Format rejected list into French
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
            
        # Merge valid extracted info into lead_info state
        for k, v in extracted.items():
            if v is not None:
                lead_info[k] = v
                
        # Intercept and validate required contact details before confirming or concluding
        has_email = bool(lead_info.get("Email"))
        has_phone = bool(lead_info.get("Telephone"))
        has_nom = bool(lead_info.get("Nom"))
        has_prenom = bool(lead_info.get("Prenom"))
        
        # Concluding keywords in the AI reply
        is_concluding = any(word in response_text.lower() for word in ["bientôt", "journée", "coordonnées", "préparons", "revoir", "semaine"])
        
        if not has_email or not has_phone or not has_nom or not has_prenom:
            # If the response is trying to conclude but we lack any mandatory fields, override it
            if is_concluding or (is_mock_fallback and len([m for m in messages_list if m["role"] == "user"]) >= 5):
                missing = []
                if not has_prenom:
                    missing.append("votre prénom")
                if not has_nom:
                    missing.append("votre nom")
                if not has_email:
                    missing.append("votre adresse e-mail")
                if not has_phone:
                    missing.append("votre numéro de téléphone")
                    
                # Format missing list into French
                if len(missing) == 1:
                    missing_str = missing[0]
                elif len(missing) == 2:
                    missing_str = f"{missing[0]} et {missing[1]}"
                else:
                    missing_str = ", ".join(missing[:-1]) + f" et {missing[-1]}"
                    
                response_text = (
                    f"J'ai bien noté ces informations, mais il me manque {missing_str} "
                    "pour finaliser votre dossier et vous envoyer l'étude. Pouvez-vous les indiquer ?"
                )
                    
        # Recheck constraints after interceptor
        has_email = bool(lead_info.get("Email"))
        has_phone = bool(lead_info.get("Telephone"))
        
        # Persist to Airtable if contact info is available and valid
        if (has_email or has_phone) and not rejected_fields:
            airtable_client = AirtableClient()
            
            # Map fields to French names in Airtable
            airtable_fields = {
                "Nom": lead_info.get("Nom"),
                "Prénom": lead_info.get("Prenom"),
                "Téléphone": lead_info.get("Telephone"),
                "Email": lead_info.get("Email"),
                "Adresse": lead_info.get("Adresse"),
                "Ville": lead_info.get("Ville"),
                "Fournisseur actuel": lead_info.get("Fournisseur"),
                "Statut": "Contacted",
            }
            # Clean None values
            airtable_fields = {k: v for k, v in airtable_fields.items() if v is not None}
            
            # Prochaine action summary
            provider = lead_info.get("Fournisseur") or "EDF"
            airtable_fields["Prochaine action"] = f"Envoyer étude comparative {provider}"
            
            # Create or update Lead
            if not lead_id:
                # Deduplication check
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
                
            # Log exchange in Conversations table
            date_str = datetime.utcnow().isoformat() + "Z"
            user_msgs = [m for m in messages_list if m["role"] == "user"]
            latest_user_message = user_msgs[-1]["content"] if user_msgs else ""
            
            conv_fields = {
                "Lead": [lead_id],
                "Date": date_str,
                "Message client": latest_user_message,
                "Réponse IA": response_text,
            }
            try:
                airtable_client.create_record("Conversations", conv_fields)
            except Exception as ex:
                print(f"Error logging conversation: {ex}")
                
        # Append final reply to history
        new_messages = messages_list.copy() if messages_list else []
        new_messages.append({"role": "assistant", "content": response_text})
        
        turn = state.get("conversation_turn", 0) + 1
        
        return {
            "messages": new_messages,
            "conversation_turn": turn,
            "lead_id": lead_id,
            "lead_info": lead_info,
        }
        
    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        new_messages = state.get("messages", []).copy() if state.get("messages") else []
        new_messages.append({"role": "assistant", "content": f"Désolé, j'ai rencontré une erreur. {error_msg}"})
        
        return {
            "messages": new_messages,
            "conversation_turn": state.get("conversation_turn", 0) + 1,
            "lead_id": state.get("lead_id"),
            "lead_info": state.get("lead_info"),
        }


def create_agent_graph():
    """Create the LangGraph graph for the agent."""
    from langgraph.graph import StateGraph, END
    
    graph_builder = StateGraph(GraphState)
    graph_builder.add_node("process_message", process_message_node)
    graph_builder.set_entry_point("process_message")
    graph_builder.add_edge("process_message", END)
    
    return graph_builder.compile()


# Global graph instance
agent_graph = None


def get_agent_graph():
    """Get or create the agent graph."""
    global agent_graph
    if agent_graph is None:
        agent_graph = create_agent_graph()
    return agent_graph

