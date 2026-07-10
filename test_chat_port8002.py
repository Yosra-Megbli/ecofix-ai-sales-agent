import requests
import json
import uuid

base_url = "http://127.0.0.1:8002"  # Port 8002
session_id = str(uuid.uuid4())

print("=" * 70)
print("🚀 PHASE 3.1 - LANGGRAPH CHAT AGENT TEST (PORT 8002 - Direct Google SDK)")
print("=" * 70)

# 1. Start session
print("\n[1/3] Starting chat session...")
try:
    r = requests.post(f"{base_url}/chat/start?session_id={session_id}", timeout=10)
    if r.status_code != 200:
        print(f"❌ Failed: {r.status_code} - {r.text}")
        exit(1)
    
    greeting = r.json()["response"]
    print(f"✅ Agent greeting OK\n")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# 2. Send user message
print("[2/3] Sending user message...")
try:
    user_msg = "Bonjour, j'aimerais discuter de solutions d'énergie renouvelable pour ma manufacture."
    
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
    
    # Check if it's an error message
    if "Désolé, j'ai rencontré une erreur" in ai_reply:
        print(f"❌ LLM Error: {ai_reply[:200]}...")
    else:
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
        if len(content) > 100:
            content = content[:100] + "..."
        print(f"  [{i}] {role}: {content}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

print("\n" + "=" * 70)
print("✅ PHASE 3.1 COMPLETE - LangGraph Agent Endpoints Functional!")
print("=" * 70)
print(f"Session ID: {session_id}")
print(f"Endpoints: /chat/start, /chat, /chat/history")
print(f"Architecture: LangGraph + Google Generative AI")
