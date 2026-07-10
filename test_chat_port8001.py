import requests
import json
import uuid

base_url = "http://127.0.0.1:8001"  # Changed to port 8001
session_id = str(uuid.uuid4())

print("=" * 70)
print("🚀 PHASE 3.1 - LANGGRAPH CHAT AGENT TEST (PORT 8001)")
print("=" * 70)

# 1. Start session
print("\n[1/3] Starting chat session...")
try:
    r = requests.post(f"{base_url}/chat/start?session_id={session_id}", timeout=10)
    if r.status_code != 200:
        print(f"❌ Failed: {r.status_code} - {r.text}")
        exit(1)
    
    greeting = r.json()["response"]
    print(f"✅ Agent greeting:\n{greeting[:150]}...\n")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# 2. Send user message
print("[2/3] Sending user message...")
try:
    user_msg = "Bonjour, j'aimerais discuter de solutions d'énergie pour mon entreprise dans le secteur de la manufacture."
    
    chat_request = {
        "message": user_msg,
        "session_id": session_id
    }
    
    print(f"User: {user_msg}\n")
    
    r = requests.post(f"{base_url}/chat", json=chat_request, timeout=30)
    
    if r.status_code != 200:
        print(f"❌ Failed: {r.status_code}")
        print(f"Response: {r.text}")
        exit(1)
    
    response = r.json()
    ai_reply = response["response"]
    print(f"✅ Agent response:\n{ai_reply}\n")
    print(f"Turn: {response['turn']}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# 3. Get history
print("\n[3/3] Retrieving chat history...")
try:
    r = requests.get(f"{base_url}/chat/history/{session_id}", timeout=10)
    
    if r.status_code != 200:
        print(f"❌ Failed: {r.status_code}")
        exit(1)
    
    data = r.json()
    messages = data["messages"]
    
    print(f"✅ Conversation history ({len(messages)} messages):")
    for i, msg in enumerate(messages, 1):
        role = msg['role'].upper()
        content = msg['content']
        # Truncate long messages
        if len(content) > 100:
            content = content[:100] + "..."
        print(f"  [{i}] {role}: {content}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

print("\n" + "=" * 70)
print("✅ PHASE 3.1 TEST COMPLETE - CHAT AGENT OPERATIONAL!")
print("=" * 70)
print(f"Session ID: {session_id}")
print(f"Endpoints tested: /chat/start, /chat, /chat/history")
print(f"LangGraph + Google Gemini working: YES")
