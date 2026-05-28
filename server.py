#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小布交易系统 - Web服务器 v1.0
Flask REST API + 静态文件服务
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from flask import Flask, jsonify, request, send_from_directory
from db import *
import requests

app = Flask(__name__, static_folder='.', static_url_path='')
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn'}

def sina_symbol(code):
    parts = code.split('.')
    if len(parts) == 2:
        m = {'SZ':'sz','SH':'sh','BJ':'bj'}
        return f"{m.get(parts[1],'sz')}{parts[0]}"
    if code.startswith(('6','688')): return f"sh{code}"
    if code.startswith(('83','87','92')): return f"bj{code}"
    return f"sz{code}"

def fetch_price(symbol):
    url = f'https://hq.sinajs.cn/list={symbol}'
    r = requests.get(url, headers=HEADERS, timeout=10, proxies={'http':None,'https':None})
    r.encoding = 'gb18030'
    d = r.text.split('"')[1].split(',')
    return {'name': d[0], 'price': float(d[3]), 'high': float(d[4]), 'low': float(d[5]),
            'open': float(d[1]), 'yclose': float(d[2]),
            'change': round((float(d[3])-float(d[2]))/float(d[2])*100, 2),
            'volume': int(d[8])}

# ========== API ==========

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/holdings')
def api_holdings():
    rows = get_holdings()
    result = []
    total_cost = total_market = total_pl = 0
    for r in rows:
        try:
            rt = fetch_price(sina_symbol(r['code']))
            cur = rt['price']
            mv = round(cur * r['shares'], 2)
            pl = round((cur - r['avg_cost']) * r['shares'], 2)
            pp = round((cur - r['avg_cost']) / r['avg_cost'] * 100, 2)
            total_cost += r['total_cost']
            total_market += mv
            total_pl += pl
            result.append({
                'code': r['code'], 'name': r['name'],
                'shares': r['shares'], 'cost': r['avg_cost'],
                'total_cost': r['total_cost'],
                'price': cur, 'market_value': mv,
                'pl': pl, 'pl_pct': pp,
                'change': rt['change'], 'yclose': rt['yclose']
            })
        except:
            result.append({
                'code': r['code'], 'name': r['name'],
                'shares': r['shares'], 'cost': r['avg_cost'],
                'total_cost': r['total_cost'],
                'price': 0, 'market_value': 0,
                'pl': 0, 'pl_pct': 0, 'change': 0, 'yclose': 0
            })
    return jsonify({'holdings': result, 'summary': {
        'total_cost': round(total_cost, 2), 'total_market': round(total_market, 2),
        'total_pl': round(total_pl, 2),
        'total_pl_pct': round(total_pl/total_cost*100, 2) if total_cost else 0
    }})

@app.route('/api/watchlist')
def api_watchlist():
    rows = watch_list()
    result = []
    for r in rows:
        try:
            rt = fetch_price(sina_symbol(r['code']))
            result.append({'code': r['code'], 'name': r['name'],
                          'price': rt['price'], 'change': rt['change'],
                          'reason': r['reason'], 'added_date': r['added_date']})
        except:
            result.append({'code': r['code'], 'name': r['name'],
                          'price': 0, 'change': 0,
                          'reason': r['reason'], 'added_date': r['added_date']})
    return jsonify(result)

@app.route('/api/watch/add', methods=['POST'])
def api_watch_add():
    data = request.json
    code = data.get('code', '').strip()
    reason = data.get('reason', '')
    try:
        rt = fetch_price(sina_symbol(code))
        name = rt['name']
    except:
        name = code
    msg = watch_add(code, name, reason)
    return jsonify({'msg': msg})

@app.route('/api/watch/remove', methods=['POST'])
def api_watch_remove():
    data = request.json
    msg = watch_remove(data.get('code', ''))
    return jsonify({'msg': msg})

@app.route('/api/trade/buy', methods=['POST'])
def api_buy():
    data = request.json
    code = data.get('code', '').strip()
    try:
        shares = int(data.get('shares', 0))
        price = float(data.get('price', 0))
    except:
        return jsonify({'msg': '❌ 股数和价格格式错误'})
    notes = data.get('notes', '')
    try:
        rt = fetch_price(sina_symbol(code))
        name = rt['name']
    except:
        name = code
    msg = buy(code, name, shares, price, notes)
    return jsonify({'msg': msg})

@app.route('/api/trade/sell', methods=['POST'])
def api_sell():
    data = request.json
    code = data.get('code', '').strip()
    try:
        shares = int(data.get('shares', 0))
    except:
        return jsonify({'msg': '❌ 股数格式错误'})
    notes = data.get('notes', '')
    msg = sell(code, shares, notes)
    return jsonify({'msg': msg})

@app.route('/api/trades')
def api_trades():
    rows = get_trades(50)
    result = []
    for r in rows:
        result.append(dict(r))
    return jsonify(result)

@app.route('/api/summary')
def api_summary():
    return jsonify(get_trade_summary())

@app.route('/api/ladder')
def api_ladder():
    import subprocess, json
    sp = os.path.dirname(__file__)
    fp = os.path.join(sp, 'limitup_data.json')
    try:
        r = subprocess.run([sys.executable, os.path.join(sp, 'limitup.py')], capture_output=True, text=True, timeout=20)
    except:
        pass
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except:
        return jsonify({'date': '2026-05-28', 'time': '收盘', 'stocks': [
            {'name':'尚纬股份','code':'603333','price':9.05,'zdf':10.0,'board':5},
            {'name':'融发核电','code':'002366','price':7.04,'zdf':10.0,'board':4},
            {'name':'通达电气','code':'603390','price':13.36,'zdf':10.0,'board':3},
            {'name':'云内动力','code':'000903','price':1.76,'zdf':10.0,'board':3},
            {'name':'长城电工','code':'600192','price':0,'zdf':10.0,'board':3},
            {'name':'会稽山','code':'601579','price':0,'zdf':10.0,'board':3},
            {'name':'汇金通','code':'603577','price':0,'zdf':10.0,'board':3},
            {'name':'均瑶健康','code':'605388','price':0,'zdf':10.0,'board':3},
        ]})

@app.route('/api/search', methods=['POST'])
def api_search():
    """搜索股票代码获取实时行情"""
    data = request.json
    code = data.get('code', '').strip()
    try:
        rt = fetch_price(sina_symbol(code))
        return jsonify(rt)
    except:
        return jsonify({'error': '未找到该股票'})

if __name__ == '__main__':
    import socket
    port = 18989
    print(f"\n  🐻 小布交易系统 Web界面")
    print(f"  ─────────────────────────────")
    print(f"  打开浏览器访问:")
    print(f"  👉 http://localhost:{port}")
    print(f"  👉 http://127.0.0.1:{port}")
    print(f"  ─────────────────────────────")
    print(f"  Ctrl+C 停止服务\n")
    app.run(host='127.0.0.1', port=port, debug=False)
