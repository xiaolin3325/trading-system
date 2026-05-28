#!/usr/bin/env python3
import json
fp = r'C:\Users\zxl\.openclaw\workspace\trading\limitup_data.json'
with open(fp, 'r', encoding='utf-8') as f:
    d = json.load(f)
print(f'日期: {d["date"]}')
print(f'时间: {d["time"]}')
print(f'股票数: {len(d["stocks"])}')
for s in d['stocks'][:3]:
    con = s['consecutive']
    b = s['boards']
    print(f'  {s["name"]:8s} {s["code"]}  {con}连板  20日{b}板')
