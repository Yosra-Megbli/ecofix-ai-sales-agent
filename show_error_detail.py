import requests

# Récupérer la dernière session
session_id = "ebcb355c-5bbe-4d65-bd68-e7e6792fc64f"

r = requests.get(f"http://127.0.0.1:8002/chat/history/{session_id}", timeout=10)

if r.status_code == 200:
    data = r.json()
    messages = data["messages"]
    
    print("=" * 80)
    print("MESSAGE D'ERREUR COMPLET")
    print("=" * 80)
    
    # Afficher le 3ème message (l'erreur)
    error_msg = messages[2]['content']
    print(error_msg)
