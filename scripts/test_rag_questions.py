import requests
import uuid

base_url = "http://127.0.0.1:8000"

def test_question(question: str):
    session_id = str(uuid.uuid4())
    # Start session
    requests.post(f"{base_url}/chat/start?session_id={session_id}", timeout=10)
    
    # Send message
    payload = {
        "message": question,
        "session_id": session_id
    }
    r = requests.post(f"{base_url}/chat", json=payload, timeout=60)
    if r.status_code == 200:
        return r.json()["response"]
    else:
        return f"Error: {r.status_code} - {r.text}"

def main():
    questions = [
        "Quelles sont vos offres ?",
        "C'est quoi Friends with Benefits ?",
        "Est-ce que vous vendez des vélos électriques ?"
    ]
    
    for q in questions:
        print("=" * 80)
        print(f"QUESTION : {q}")
        print("=" * 80)
        response = test_question(q)
        print(f"RÉPONSE :\n{response}\n")

if __name__ == "__main__":
    main()
