from dotenv import load_dotenv
load_dotenv()

import os
import json
import urllib.request


def main():
    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')
    if not api_key or not base_id:
        print('Missing AIRTABLE_API_KEY or AIRTABLE_BASE_ID')
        return
    url = f'https://api.airtable.com/v0/{base_id}/Leads?maxRecords=1'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {api_key}'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
            print('OK', json.dumps(data.get('records', []), indent=2)[:1000])
    except Exception as e:
        print('ERROR', e)


if __name__ == '__main__':
    main()
