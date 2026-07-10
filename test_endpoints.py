import requests
import json

r = requests.get("http://127.0.0.1:8000/openapi.json")
if r.status_code == 200:
    spec = r.json()
    paths = list(spec.get("paths", {}).keys())
    print("Available endpoints:")
    for path in sorted(paths):
        print(f"  {path}")
else:
    print(f"Error: {r.status_code}")
