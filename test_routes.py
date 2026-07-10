from backend.main import app

routes = [route.path for route in app.routes]
print("✅ FastAPI app imported")
print(f"Total routes: {len(routes)}")
chat_routes = [r for r in routes if "chat" in r]
print(f"Chat routes: {chat_routes}")
print("\nAll routes:")
for r in sorted(set(routes)):
    print(f"  {r}")
