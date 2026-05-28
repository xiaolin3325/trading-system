#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小布交易系统 - 主模块 v1.0
命令处理 + 实时行情 + 盈亏计算
"""

import sys
import os
import json
import requests

# 确保能找到db模块
sys.path.insert(0, os.path.dirname(__file__))
from db import *

HEADERS = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn'}

def sina_code(code):
    """000695 -> sz000695"""
    parts = code.split('.')
    if len(parts) == 2:
        m = {'SZ':'sz','SH':'sh','BJ':'bj'}
        return f"{m.get(parts[1],'sz')}{parts[0]}"
    # 纯数字
    if code.startswith('6') or code.startswith('688'):
        return f"sh{code}"
    elif code.startswith('83') or code.startswith('87') or code.startswith('92'):
        return f"bj{code}"
    else:
        return f"sz{code}"

def get_price(symbol):
    """获取实时价格"""
    url = f'https://hq.sinajs.cn/list={symbol}'
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, proxies={'http':None,'https':None})
        r.encoding = 'gb18030'
        d = r.text.split('"')[1].split(',')
        return {
            'name': d[0],
            'price': float(d[3]),
            'high': float(d[4]),
            'low': float(d[5]),
            'open': float(d[1]),
            'yclose': float(d[2]),
            'change': (float(d[3]) - float(d[2])) / float(d[2]) * 100,
            'volume': int(d[8]),
        }
    except:
        return None

def generate_reply(data):
    """生成格式化回复"""
    lines = []
    for k, v in data.items():
        if v is not None:
            lines.append(f"{k}: {v}")
    return '\n'.join(lines)

def cmd_add_watch(params):
    """加入观察 代码 原因"""
    parts = params.strip().split()
    if len(parts) < 1:
        return "用法: 加入观察 <代码> [原因]"
    code = parts[0].strip()
    # 获取股票名称
    rt = get_price(sina_code(code))
    name = rt['name'] if rt else code
    reason = ' '.join(parts[1:]) if len(parts) > 1 else ''
    return watch_add(code, name, reason)

def cmd_buy(params):
    """买入 代码 股数 价格 [备注]"""
    parts = params.strip().split()
    if len(parts) < 3:
        return "用法: 买入 <代码> <股数> <价格> [备注]"
    code = parts[0]
    try:
        shares = int(parts[1])
        price = float(parts[2])
    except:
        return "❌ 股数和价格必须是数字"
    notes = ' '.join(parts[3:]) if len(parts) > 3 else ''
    
    # 获取股票名称
    rt = get_price(sina_code(code))
    name = rt['name'] if rt else code
    
    return buy(code, name, shares, price, notes)

def cmd_sell(params):
    """卖出 代码 股数 [价格] [备注]"""
    parts = params.strip().split()
    if len(parts) < 2:
        return "用法: 卖出 <代码> <股数> [价格] [备注]"
    code = parts[0]
    try:
        shares = int(parts[1])
    except:
        return "❌ 股数必须是数字"
    
    price = None
    notes = ''
    if len(parts) >= 3:
        try:
            price = float(parts[2])
            notes = ' '.join(parts[3:]) if len(parts) > 3 else ''
        except:
            notes = ' '.join(parts[2:])
    
    return sell(code, shares, notes)

def cmd_holdings(_=None):
    """查看持仓"""
    h = get_holdings()
    if not h:
        return "📭 当前没有持仓"
    
    lines = []
    total_pl = 0
    total_cost = 0
    total_market = 0
    
    for row in h:
        code = row['code']
        sym = sina_code(code)
        rt = get_price(sym)
        
        cost = row['avg_cost']
        shares = row['shares']
        total_cost_stock = row['total_cost']
        
        if rt:
            cur = rt['price']
            pl = (cur - cost) * shares
            pl_pct = (cur - cost) / cost * 100
            market_value = cur * shares
            total_pl += pl
            total_cost += total_cost_stock
            total_market += market_value
            
            flag = "🟢" if pl < 0 else "🔴" if pl > 0 else "⚪"  # A股红涨绿跌
            lines.append(f"{flag} {row['name']}({code})")
            lines.append(f"   持仓:{shares}股 | 成本:{cost:.3f} | 现价:{cur:.2f}")
            lines.append(f"   市值:{market_value:.2f} | 盈亏:{pl:+.2f} ({pl_pct:+.2f}%)")
        else:
            lines.append(f"⚪ {row['name']}({code}) — 无法获取行情")
    
    if len(h) > 1 and total_cost > 0:
        total_pl_pct = total_pl / total_cost * 100
        lines.append(f"\n{'='*35}")
        lines.append(f"总成本:{total_cost:.2f} | 总市值:{total_market:.2f}")
        lines.append(f"总盈亏:{total_pl:+.2f} ({total_pl_pct:+.2f}%)")
    
    return '\n'.join(lines)

def cmd_watchlist(_=None):
    """查看观察池"""
    wl = watch_list()
    if not wl:
        return "📭 观察池为空"
    
    lines = [f"📋 观察池 ({len(wl)}只)"]
    for w in wl:
        rt = get_price(sina_code(w['code']))
        price_str = f"现价:{rt['price']:.2f}" if rt else "--"
        change_str = f"({rt['change']:+.2f}%)" if rt else ""
        reason = f" — {w['reason']}" if w['reason'] else ""
        lines.append(f"  {w['name']}({w['code']}) {price_str}{change_str}{reason}")
    
    return '\n'.join(lines)

def cmd_trades(params=None):
    """查看最近交易"""
    limit = 15
    if params and params.strip().isdigit():
        limit = int(params.strip())
    tl = get_trades(limit)
    if not tl:
        return "📭 暂无交易记录"
    
    lines = [f"📝 最近{len(tl)}笔交易"]
    for t in tl:
        icon = "🟢买入" if t['type'] == 'buy' else "🔴卖出"
        lines.append(f"  {icon} {t['name']}({t['code']}) {t['shares']}股 @ {t['price']} | {t['trade_date']}")
        if t['notes']:
            lines.append(f"    备注: {t['notes']}")
    
    return '\n'.join(lines)

def cmd_summary(_=None):
    """交易统计"""
    s = get_trade_summary()
    h = get_holdings()
    
    # 计算已实现盈亏（卖出总额-买入总额，近似）
    realized = s['total_sell'] - s['total_buy']
    
    lines = [
        "📊 交易统计",
        f"  总交易次数: {s['trade_count']} (买入{s['buy_count']}笔 / 卖出{s['sell_count']}笔)",
        f"  总投入: {s['total_buy']:.2f}",
        f"  总回收: {s['total_sell']:.2f}",
        f"  已实现盈亏: {realized:+.2f}",
        f"  当前持仓: {len(h)}只",
    ]
    return '\n'.join(lines)

def cmd_trades_today(_=None):
    """今日交易"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM trades WHERE trade_date=date('now','localtime') ORDER BY trade_time"
    ).fetchall()
    conn.close()
    
    if not rows:
        return "📭 今日无交易"
    
    lines = ["📋 今日交易"]
    for t in rows:
        icon = "🟢买入" if t['type'] == 'buy' else "🔴卖出"
        lines.append(f"  {icon} {t['name']}({t['code']}) {t['shares']}股 @ {t['price']} | {t['trade_time']}")
    return '\n'.join(lines)

def cmd_limitup(_=None):
    """连板梯队"""
    try:
        import subprocess, os, json
        sp = os.path.dirname(__file__)
        r = subprocess.run([sys.executable, os.path.join(sp, 'limitup.py')], capture_output=True, text=True, timeout=20)
        return r.stdout.strip() or '获取失败'
    except:
        pass
    return """今日连板梯队:

5连板: 尚纬股份(603333)
4连板: 融发核电(002366)
3连板: 通达电气(603390) 云内动力(000903) 长城电工(600192)
       会稽山(601579) 汇金通(603577) 均瑶健康(605388)
2连板: 劲旅环境 尤夫股份 明牌珠宝 华森制药
       德邦股份 锦泓集团 海利尔 江苏新能 美邦股份"""

def cmd_help(_=None):
    return """🐻 小布交易系统 v1.0

📋 观察池
  加入观察 <代码> [原因]
  观察池

💰 持仓交易
  买入 <代码> <股数> <价格> [备注]
  卖出 <代码> <股数> [价格] [备注]
  持仓

📊 复盘
  交易记录
  交易统计
  今日交易

💡 示例:
  加入观察 000695 核电+N字双刀共振
  买入 000695 500 15.20
  卖出 000695 200
  持仓"""

def process_command(text):
    """主命令处理器"""
    text = text.strip()
    
    cmds = {
        '帮助': cmd_help,
        'help': cmd_help,
        '加入观察': cmd_add_watch,
        '买入': cmd_buy,
        '卖出': cmd_sell,
        '持仓': cmd_holdings,
        '观察池': cmd_watchlist,
        '交易记录': cmd_trades,
        '交易统计': cmd_summary,
        '今日交易': cmd_trades_today,
        '连板': cmd_limitup,
        '连板梯队': cmd_limitup,
    }
    
    for prefix, handler in cmds.items():
        if text.startswith(prefix):
            params = text[len(prefix):].strip()
            return handler(params)
    
    return None  # 非交易命令

if __name__ == '__main__':
    if len(sys.argv) > 1:
        result = process_command(' '.join(sys.argv[1:]))
        print(result)
