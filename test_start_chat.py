import requests
import json
import uuid

base_url = "http://127.0.0.1:8000"
session_id = str(uuid.uuid4())

print(f"Testing with session_id: {session_id}\n")

print("=" * 60)
print("Testing /chat/start endpoint...")
print("=" * 60)

url = f"{base_url}/chat/start?session_id={session_id}"
print(f"URL: {url}\n")

try:
    r = requests.post(url, timeout=10)
    print(f"Status: {r.status_code}")
    print(f"Response text: {r.text}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"✅ Success!")
        print(f"Response: {data['response'][:150]}...\n")
    else:
        print(f"❌ Failed with status {r.status_code}")
        
except Exception as e:
    print(f"❌ Exception: {e}")
