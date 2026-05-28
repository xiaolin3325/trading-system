#!/usr/bin/env python3
"""Debug: 检查永安药业K线数据"""
import requests, json

h = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn'}
p = {'http': None, 'https': None}

r = requests.get('https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData',
    params={'symbol':'sz002365','scale':240,'datalen':25}, headers=h, timeout=10, proxies=p)
data = r.json()
print(f'永安药业 K线: {len(data)}条')
for k in data[-10:]:
    c = float(k['close'])
    o = float(k['open'])
    chg = (c - o) / o * 100
    zdf = (c - float(data[data.index(k)-1]['close'])) / float(data[data.index(k)-1]['close']) * 100 if data.index(k) > 0 else 0
    print(f'  {k["day"]:20s}  O:{o:.2f} C:{c:.2f} 日内:{chg:+.1f}%  昨收比:{zdf:+.1f}%')
