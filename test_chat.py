import requests
import json
import uuid

base_url = "http://127.0.0.1:8000"
session_id = str(uuid.uuid4())

print("=" * 60)
print("1️⃣ Starting chat session...")
print("=" * 60)

# Start session
try:
    r = requests.post(f"{base_url}/chat/start?session_id={session_id}", timeout=30)
    print(f"Status: {r.status_code}")
    response_data = r.json()
    print(f"Greeting: {response_data['response'][:100]}...")
    print(f"Session ID: {response_data['session_id']}")
    print(f"Turn: {response_data['turn']}")
except Exception as e:
    print(f"❌ Error starting chat: {e}")
    exit(1)

print("\n" + "=" * 60)
print("2️⃣ Sending a test message...")
print("=" * 60)

# Send a message
try:
    chat_request = {
        "message": "Bonjour, je suis intéressé par les solutions d'énergie renouvelable pour mon entreprise.",
        "session_id": session_id
    }
    
    r = requests.post(f"{base_url}/chat", json=chat_request, timeout=60)
    print(f"Status: {r.status_code}")
    
    if r.status_code == 200:
        response_data = r.json()
        print(f"✅ Response: {response_data['response'][:200]}...")
        print(f"Turn: {response_data['turn']}")
    else:
        print(f"❌ Error: {r.text}")
        
except Exception as e:
    print(f"❌ Error sending message: {e}")

print("\n" + "=" * 60)
print("3️⃣ Getting chat history...")
print("=" * 60)

try:
    r = requests.get(f"{base_url}/chat/history/{session_id}", timeout=30)
    print(f"Status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"Messages in session: {len(data['messages'])}")
        for i, msg in enumerate(data['messages']):
            print(f"  [{i+1}] {msg['role'].upper()}: {msg['content'][:80]}...")
    else:
        print(f"❌ Error: {r.text}")
        
except Exception as e:
    print(f"❌ Error getting history: {e}")

print("\n" + "=" * 60)
print("✅ Chat endpoint test complete!")
print("=" * 60)
