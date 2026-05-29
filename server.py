#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小布交易系统 - Web服务器 v1.0
Flask REST API + 静态文件服务
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from flask import Flask, jsonify, request, send_from_directory, redirect, render_template_string
from db import *
import requests
import hashlib

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = 'xiaobu_trading_' + hashlib.md5(os.path.abspath(__file__).encode()).hexdigest()

# ========== 登录控制 ==========

LOGIN_PASSWORD = os.environ.get('TRADING_PWD', 'xbtrader')  # 默认密码 xbtrader

def is_logged_in():
    from flask import session
    return session.get('logged_in', False)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not is_logged_in():
            # API请求返回401，页面请求重定向到登录页
            if request.path.startswith('/api/'):
                return jsonify({'error': '未登录'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return wrapper

LOGIN_PAGE = '''\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>小布交易系统 - 登录</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0d1117;color:#c9d1d9;display:flex;justify-content:center;align-items:center;min-height:100vh}
.login-box{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:40px;width:360px;text-align:center}
.login-box h1{font-size:24px;margin-bottom:8px;color:#f0f6fc}
.login-box h1 span{color:#ff6b35}
.login-box .sub{font-size:13px;color:#8b949e;margin-bottom:24px}
.login-box input[type=password]{width:100%;padding:10px 14px;border-radius:8px;border:1px solid #30363d;background:#0d1117;color:#c9d1d9;font-size:15px;outline:none;transition:.2s}
.login-box input:focus{border-color:#1f6feb}
.login-box .btn{width:100%;margin-top:16px;padding:10px;border-radius:8px;border:none;background:#1f6feb;color:#fff;font-size:15px;cursor:pointer;transition:.2s}
.login-box .btn:hover{background:#388bfd}
.login-box .error{color:#f85149;font-size:13px;margin-top:12px}
</style>
</head>
<body>
<div class="login-box">
  <h1>🐻 <span>小布</span>交易系统</h1>
  <div class="sub">请输入密码</div>
  <form method="post" action="/login">
    <input type="password" name="password" placeholder="密码" autofocus>
    <button class="btn" type="submit">进入系统</button>
  </form>
  {% if error %}<div class="error">{{ error }}</div>{% endif %}
</div>
</body>
</html>\
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
    from flask import session
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        if pwd == LOGIN_PASSWORD:
            session['logged_in'] = True
            return redirect('/')
        return render_template_string(LOGIN_PAGE, error='密码错误')
    if is_logged_in():
        return redirect('/')
    return render_template_string(LOGIN_PAGE, error=None)

@app.route('/logout')
def logout():
    from flask import session
    session['logged_in'] = False
    return redirect('/login')

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
@login_required
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/holdings')
@login_required
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
@login_required
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
@login_required
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

@app.route('/api/watch/export')
@login_required
def api_watch_export():
    """导出观察池到通达信格式（.txt 纯代码列表）"""
    rows = watch_list()
    lines = []
    for r in rows:
        code = r['code']
        lines.append(code)
    text = '\n'.join(lines)
    from flask import Response
    return Response(
        text,
        mimetype='text/plain',
        headers={'Content-Disposition': 'attachment; filename=xiaobu_watchlist.txt'}
    )

@app.route('/api/watch/remove', methods=['POST'])
@login_required
def api_watch_remove():
    data = request.json
    msg = watch_remove(data.get('code', ''))
    return jsonify({'msg': msg})

@app.route('/api/trade/buy', methods=['POST'])
@login_required
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
@login_required
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
@login_required
def api_trades():
    rows = get_trades(50)
    result = []
    for r in rows:
        result.append(dict(r))
    return jsonify(result)

@app.route('/api/summary')
@login_required
def api_summary():
    return jsonify(get_trade_summary())

@app.route('/api/ladder')
@login_required
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
        return jsonify({'date': '2026-05-28', 'time': '收盘', 'stocks': []})

@app.route('/api/search', methods=['POST'])
@login_required
def api_search():
    """搜索股票代码获取实时行情"""
    data = request.json
    code = data.get('code', '').strip()
    try:
        rt = fetch_price(sina_symbol(code))
        return jsonify(rt)
    except:
        return jsonify({'error': '未找到该股票'})

# ========== 资金管理 API ==========

@app.route('/api/capital')
@login_required
def api_capital():
    return jsonify(get_capital_summary())

@app.route('/api/capital/init', methods=['POST'])
@login_required
def api_capital_init():
    data = request.json
    try:
        amount = float(data.get('amount', 0))
        return jsonify({'msg': init_capital(amount)})
    except:
        return jsonify({'msg': '❌ 金额格式错误'})

@app.route('/api/capital/deposit', methods=['POST'])
@login_required
def api_capital_deposit():
    data = request.json
    try:
        amount = float(data.get('amount', 0))
        notes = data.get('notes', '')
        return jsonify({'msg': deposit(amount, notes)})
    except:
        return jsonify({'msg': '❌ 金额格式错误'})

@app.route('/api/capital/withdraw', methods=['POST'])
@login_required
def api_capital_withdraw():
    data = request.json
    try:
        amount = float(data.get('amount', 0))
        notes = data.get('notes', '')
        return jsonify({'msg': withdraw(amount, notes)})
    except:
        return jsonify({'msg': '❌ 金额格式错误'})

@app.route('/api/capital/reset', methods=['POST'])
@login_required
def api_capital_reset():
    data = request.json
    try:
        amount = float(data.get('amount', 0))
        return jsonify({'msg': reset_capital(amount)})
    except:
        return jsonify({'msg': '❌ 金额格式错误'})

# ========== 交易信号 API ==========

@app.route('/api/signals')
@login_required
def api_signals():
    from signal import signal_for_web
    return jsonify(signal_for_web())

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
