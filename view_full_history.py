import requests

# Utiliser la dernière session du test
session_id = "05effd68-99e7-40b6-8bf2-936ee9aaa7fa"

r = requests.get(f"http://127.0.0.1:8002/chat/history/{session_id}", timeout=10)

if r.status_code == 200:
    data = r.json()
    messages = data["messages"]
    
    print("=" * 70)
    print("HISTORIQUE COMPLET DE LA SESSION")
    print("=" * 70)
    
    for i, msg in enumerate(messages, 1):
        print(f"\n[{i}] {msg['role'].upper()}:")
        print("-" * 70)
        print(msg['content'])
        print()
