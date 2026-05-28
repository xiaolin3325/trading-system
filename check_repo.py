#!/usr/bin/env python3
import requests, json
r = requests.get('https://api.github.com/repos/xiaolin3325/trading-system')
d = r.json()
if 'message' in d:
    print(f'Error: {d["message"]}')
else:
    print(f'OK: {d["full_name"]} - {d["html_url"]}')
