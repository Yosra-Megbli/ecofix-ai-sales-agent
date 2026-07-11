from backend.agent.graph import check_eligibility, calculate_lead_score
from backend.agent.state import GraphState

def test_eligibility_checks():
    print("Running check_eligibility tests...")
    
    # 1. Brussels check (ineligible)
    state1 = {
        "Ville": "Bruxelles",
        "Adresse": "Rue Royale 10",
        "Date_de_naissance": "15/08/1990",
        "Code_EAN": "541234567890123456",
        "Desir_changement": "Oui"
    }
    assert check_eligibility(state1) is False, "Failed Brussels check"
    print("Ineligibility for Brussels verified.")
    
    # 2. Underage check (ineligible)
    state2 = {
        "Ville": "Namur",
        "Adresse": "Rue de l'Ange 5",
        "Date_de_naissance": "15/08/2015", # Underage
        "Code_EAN": "541234567890123456",
        "Desir_changement": "Oui"
    }
    assert check_eligibility(state2) is False, "Failed underage check"
    print("Ineligibility for underage verified.")
    
    # 3. Invalid EAN check (ineligible)
    state3 = {
        "Ville": "Namur",
        "Adresse": "Rue de l'Ange 5",
        "Date_de_naissance": "15/08/1990",
        "Code_EAN": "123456789", # Short and doesn't start with 54
        "Desir_changement": "Oui"
    }
    assert check_eligibility(state3) is False, "Failed invalid EAN check"
    print("Ineligibility for invalid EAN verified.")

    # 4. Partial data (None)
    state4 = {
        "Ville": "Namur",
        "Adresse": "Rue de l'Ange 5",
        "Date_de_naissance": "15/08/1990",
        "Code_EAN": None, # Missing EAN
        "Desir_changement": "Oui"
    }
    assert check_eligibility(state4) is None, "Failed partial data check"
    print("Partial data returns None as expected.")

    # 5. Fully eligible
    state5 = {
        "Ville": "Namur",
        "Adresse": "Rue de l'Ange 5",
        "Date_de_naissance": "15/08/1990",
        "Code_EAN": "541234567890123456",
        "Desir_changement": "Oui"
    }
    assert check_eligibility(state5) is True, "Failed eligible check"
    print("Fully eligible lead verified.")

def test_scoring_calculations():
    print("\nRunning calculate_lead_score tests...")
    
    # 1. Full lead (100 score)
    lead_full = {
        "Prenom": "John",
        "Nom": "Doe",
        "Telephone": "0488112233",
        "Email": "john@example.com",
        "Adresse": "Rue de l'Ange 5",
        "Fournisseur": "Engie",
        "Type_energie": "Les deux",
        "Code_EAN": "541234567890123456",
        "Desir_changement": "Oui",
        "Ville": "Namur",
        "Date_de_naissance": "15/08/1990"
    }
    score = calculate_lead_score(lead_full)
    assert score == 100, f"Expected 100, got {score}"
    print("Lead with all data scored 100/100 successfully.")
    
    # 2. Basic contact details only
    lead_contact = {
        "Prenom": "John",       # +5
        "Nom": "Doe",           # +5
        "Telephone": "0488112233", # +15
        "Email": "john@example.com", # +10
        "Adresse": None
    }
    score = calculate_lead_score(lead_contact)
    assert score == 35, f"Expected 35, got {score}"
    print("Lead with contact details scored 35/100 successfully.")
    
    # 3. Ineligible lead (Brussels) gets malus
    lead_ineligible = {
        "Prenom": "John",
        "Nom": "Doe",
        "Telephone": "0488112233",
        "Email": "john@example.com",
        "Ville": "Bruxelles" # Brussels (ineligible) -> -50 malus
    }
    score = calculate_lead_score(lead_ineligible)
    # Score details: 5 (Prenom) + 5 (Nom) + 15 (Phone) + 10 (Email) + 10 (City fallback) = 45.
    # Malus: -50 -> -5 -> Capped at 0
    assert score == 0, f"Expected 0, got {score}"
    print("Ineligible lead gets malus and scores 0/100 successfully.")

def test_graph_flow():
    print("\nRunning test_graph_flow...")
    from backend.agent.graph import get_agent_graph
    
    graph = get_agent_graph()
    
    state = {
        "messages": [{"role": "user", "content": "Bonjour ! Je m'appelle Jean Dupont."}],
        "conversation_turn": 0,
        "lead_id": None,
        "lead_info": {
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
        },
        "intent": None,
        "conversation_stage": None,
        "customer_profile": None,
        "retrieved_sources": None,
        "lead_score": None,
        "qualification_status": None
    }
    
    result = graph.invoke(state)
    print("Graph executed successfully.")
    print("Detected Intent:", result.get("intent"))
    print("Conversation Stage:", result.get("conversation_stage"))
    print("Qualification Status:", result.get("qualification_status"))
    print("AI Response:", result.get("messages")[-1]["content"] if result.get("messages") else "")
    
    # Assertions to verify the new keys were populated
    assert result.get("intent") in ["greeting", "qualification", "faq"], f"Expected valid intent, got {result.get('intent')}"
    assert result.get("conversation_stage") == "Qualification", f"Expected stage 'Qualification', got {result.get('conversation_stage')}"
    assert result.get("qualification_status") == "Contacted", f"Expected status 'Contacted', got {result.get('qualification_status')}"

if __name__ == "__main__":
    test_eligibility_checks()
    test_scoring_calculations()
    test_graph_flow()
    print("\nAll local tests PASSED successfully!")