#!/usr/bin/env python3
import requests
p = {'http': None, 'https': None}
r = requests.get('https://raw.githubusercontent.com/xiaolin3325/trading-system/main/limitup_data.json', proxies=p)
d = r.json()
print(f'GitHub数据验证:')
print(f'时间: {d["time"]}')
print(f'股票数: {len(d["stocks"])}')
for s in d['stocks'][:3]:
    print(f'  {s["name"]} {s["code"]} {s["consecutive"]}连板 20日{s["boards"]}板')
