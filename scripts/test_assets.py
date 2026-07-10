import requests

def test_url(url):
    try:
        r = requests.get(url, timeout=5)
        print(f"URL: {url}")
        print(f"  Status: {r.status_code}")
        print(f"  Content-Type: {r.headers.get('Content-Type')}")
        print(f"  Body (first 150 chars): {repr(r.text[:150])}")
        print("-" * 50)
    except Exception as e:
        print(f"URL: {url} failed: {e}")
        print("-" * 50)

def main():
    base = "http://127.0.0.1:8000"
    test_url(f"{base}/dashboard")
    test_url(f"{base}/chat-ui/style.css")
    test_url(f"{base}/chat-ui/dashboard.js")
    test_url(f"{base}/style.css")
    test_url(f"{base}/dashboard.js")

if __name__ == "__main__":
    main()
