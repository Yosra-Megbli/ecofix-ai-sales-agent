import requests
import json

def main():
    url = "http://127.0.0.1:8000/dashboard/stats"
    try:
        r = requests.get(url, timeout=10)
        print("Status Code:", r.status_code)
        if r.status_code == 200:
            print("\nStatistics from Backend:")
            print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        else:
            print("Error response:", r.text)
    except Exception as e:
        print("Failed to query dashboard endpoint:", e)

if __name__ == "__main__":
    main()
