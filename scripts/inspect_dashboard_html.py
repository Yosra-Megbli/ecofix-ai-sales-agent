import requests
import re

def main():
    url = "http://127.0.0.1:8000/dashboard"
    try:
        r = requests.get(url, timeout=5)
        print("Status Code:", r.status_code)
        
        links = re.findall(r'<link\s+[^>]*href=["\']([^"\']+)["\'][^>]*>', r.text, re.IGNORECASE)
        print("\nLink tags hrefs:")
        for link in links:
            print(f"  {link}")
            
        scripts = re.findall(r'<script\s+[^>]*src=["\']([^"\']+)["\'][^>]*>', r.text, re.IGNORECASE)
        print("\nScript tags srcs:")
        for script in scripts:
            print(f"  {script}")
            
    except Exception as e:
        print("Error fetching dashboard HTML:", e)

if __name__ == "__main__":
    main()
