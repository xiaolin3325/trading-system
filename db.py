#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小布交易系统 - 数据库层 v1.0
SQLite本地存储，管理观察池、持仓、交易记录
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'trading.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表"""
    conn = get_conn()
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT,
            added_date TEXT DEFAULT (date('now', 'localtime')),
            reason TEXT,
            status TEXT DEFAULT 'active',
            UNIQUE(code)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT,
            type TEXT NOT NULL CHECK(type IN ('buy','sell')),
            shares INTEGER NOT NULL,
            price REAL NOT NULL,
            amount REAL,
            trade_date TEXT DEFAULT (date('now', 'localtime')),
            trade_time TEXT DEFAULT (time('now', 'localtime')),
            commission REAL DEFAULT 0,
            notes TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS holdings (
            code TEXT PRIMARY KEY,
            name TEXT,
            shares INTEGER NOT NULL DEFAULT 0,
            avg_cost REAL NOT NULL DEFAULT 0,
            total_cost REAL NOT NULL DEFAULT 0
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS capital (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK(type IN ('init','deposit','withdraw')),
            amount REAL NOT NULL,
            balance_after REAL,
            notes TEXT,
            record_date TEXT DEFAULT (date('now', 'localtime')),
            record_time TEXT DEFAULT (time('now', 'localtime'))
        )
    ''')
    
    conn.commit()
    conn.close()

def watch_add(code, name, reason=''):
    """加入观察池"""
    conn = get_conn()
    try:
        conn.execute('INSERT OR REPLACE INTO watchlist (code, name, reason, status) VALUES (?,?,?,?)',
                     (code, name, reason, 'active'))
        conn.commit()
        return f"✅ {name}({code}) 已加入观察池"
    except Exception as e:
        return f"❌ 加入失败: {e}"
    finally:
        conn.close()

def watch_remove(code):
    """从观察池移除"""
    conn = get_conn()
    conn.execute('UPDATE watchlist SET status="removed" WHERE code=?', (code,))
    conn.commit()
    conn.close()
    return f"✅ {code} 已从观察池移除"

def watch_list():
    """查看观察池"""
    conn = get_conn()
    rows = conn.execute('SELECT * FROM watchlist WHERE status="active" ORDER BY added_date DESC').fetchall()
    conn.close()
    return rows

def buy(code, name, shares, price, notes=''):
    """买入记录（自动扣减资金）"""
    conn = get_conn()
    conn.execute('BEGIN')
    try:
        amount = round(shares * price, 2)
        
        # 检查是否有资金管理，有的话自动扣款
        has_capital = conn.execute("SELECT COUNT(*) as c FROM capital WHERE type='init'").fetchone()['c'] > 0
        if has_capital:
            cur = get_current_balance(conn)
            if cur < amount:
                conn.rollback()
                return f"❌ 资金不足，可用余额 ¥{cur:.2f}，需要 ¥{amount:.2f}"
            new_balance = round(cur - amount, 2)
            conn.execute('INSERT INTO capital (type, amount, balance_after, notes) VALUES (?,?,?,?)',
                         ('withdraw', amount, new_balance, f'买入扣款: {name}({code})'))
        
        # 记录交易
        conn.execute(
            'INSERT INTO trades (code, name, type, shares, price, amount, notes) VALUES (?,?,?,?,?,?,?)',
            (code, name, 'buy', shares, price, amount, notes)
        )
        
        # 更新持仓
        existing = conn.execute('SELECT * FROM holdings WHERE code=?', (code,)).fetchone()
        if existing:
            old_shares = existing['shares']
            old_cost = existing['total_cost']
            new_shares = old_shares + shares
            new_cost = old_cost + amount
            avg = round(new_cost / new_shares, 3)
            conn.execute('UPDATE holdings SET shares=?, avg_cost=?, total_cost=?, name=? WHERE code=?',
                         (new_shares, avg, new_cost, name, code))
        else:
            conn.execute('INSERT INTO holdings (code, name, shares, avg_cost, total_cost) VALUES (?,?,?,?,?)',
                         (code, name, shares, round(price, 3), amount))
        
        # 自动从观察池移除
        conn.execute('UPDATE watchlist SET status="removed" WHERE code=? AND status="active"', (code,))
        
        conn.commit()
        if has_capital:
            return f"✅ 买入 {name}({code}) {shares}股 @ {price}，¥{amount:.2f} 已扣款，余额 ¥{new_balance:.2f}"
        return f"✅ 买入 {name}({code}) {shares}股 @ {price}，总成本 {amount:.2f}"
    except Exception as e:
        conn.rollback()
        return f"❌ 买入失败: {e}"
    finally:
        conn.close()

def sell(code, shares, notes='', price=None):
    """卖出记录（自动回款到资金池）"""
    conn = get_conn()
    conn.execute('BEGIN')
    try:
        holding = conn.execute('SELECT * FROM holdings WHERE code=?', (code,)).fetchone()
        if not holding:
            conn.rollback()
            return f"❌ 没有持仓 {code}"
        
        if shares > holding['shares']:
            conn.rollback()
            return f"❌ 持仓不足，当前 {holding['shares']}股"
        
        name = holding['name']
        sell_price = price if price else holding['avg_cost']
        sell_amount = round(sell_price * shares, 2)
        
        # 盈亏计算
        cost_amount = round(holding['avg_cost'] * shares, 2)
        pl = round(sell_amount - cost_amount, 2)
        pl_pct = round((sell_price - holding['avg_cost']) / holding['avg_cost'] * 100, 2)
        
        # 记录交易
        conn.execute(
            'INSERT INTO trades (code, name, type, shares, price, amount, notes) VALUES (?,?,?,?,?,?,?)',
            (code, name, 'sell', shares, sell_price, sell_amount, notes)
        )
        
        # 卖出回款自动入资金池
        has_capital = conn.execute("SELECT COUNT(*) as c FROM capital WHERE type='init'").fetchone()['c'] > 0
        if has_capital:
            cur = get_current_balance(conn)
            new_balance = round(cur + sell_amount, 2)
            conn.execute('INSERT INTO capital (type, amount, balance_after, notes) VALUES (?,?,?,?)',
                         ('deposit', sell_amount, new_balance, f'卖出回款: {name}({code})'))
        
        if shares == holding['shares']:
            conn.execute('DELETE FROM holdings WHERE code=?', (code,))
            pl_flag = f"盈亏:{pl:+.2f}({pl_pct:+.2f}%)"
            msg = f"🔴 清仓 {name}({code}) {shares}股 @ {sell_price}  {pl_flag}"
        else:
            new_shares = holding['shares'] - shares
            new_cost = holding['total_cost'] * (new_shares / holding['shares'])
            new_avg = round(new_cost / new_shares, 3) if new_shares > 0 else 0
            conn.execute('UPDATE holdings SET shares=?, total_cost=?, avg_cost=? WHERE code=?',
                         (new_shares, round(new_cost, 2), new_avg, code))
            pl_flag = f"盈亏:{pl:+.2f}({pl_pct:+.2f}%)"
            msg = f"🔻 减仓 {name}({code}) {shares}股 @ {sell_price}，剩余 {new_shares}股  {pl_flag}"
        
        if has_capital:
            msg += f" | 回款 ¥{sell_amount:.2f}，余额 ¥{new_balance:.2f}"
        
        conn.commit()
        return msg
    except Exception as e:
        conn.rollback()
        return f"❌ 卖出失败: {e}"
    finally:
        conn.close()

def get_holdings():
    """获取当前持仓"""
    conn = get_conn()
    rows = conn.execute('SELECT * FROM holdings WHERE shares > 0 ORDER BY total_cost DESC').fetchall()
    conn.close()
    return rows

def get_trades(limit=20):
    """获取最近交易记录"""
    conn = get_conn()
    rows = conn.execute('SELECT * FROM trades ORDER BY trade_date DESC, trade_time DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    return rows

def get_trade_summary():
    """获取交易统计"""
    conn = get_conn()
    trade_count = conn.execute('SELECT COUNT(*) as c FROM trades').fetchone()['c']
    buy_count = conn.execute('SELECT COUNT(*) as c FROM trades WHERE type="buy"').fetchone()['c']
    sell_count = conn.execute('SELECT COUNT(*) as c FROM trades WHERE type="sell"').fetchone()['c']
    total_buy = conn.execute('SELECT COALESCE(SUM(amount),0) as s FROM trades WHERE type="buy"').fetchone()['s']
    total_sell = conn.execute('SELECT COALESCE(SUM(amount),0) as s FROM trades WHERE type="sell"').fetchone()['s']
    conn.close()
    return {
        'trade_count': trade_count,
        'buy_count': buy_count,
        'sell_count': sell_count,
        'total_buy': total_buy,
        'total_sell': total_sell,
    }

# ========== 资金管理 ==========

def init_capital(amount):
    """设置初始资金（仅首次有效）"""
    conn = get_conn()
    try:
        existing = conn.execute("SELECT COUNT(*) as c FROM capital WHERE type='init'").fetchone()
        if existing and existing['c'] > 0:
            return "❌ 初始资金已设置，如需修改请用：重置资金 <金额>"
        conn.execute('INSERT INTO capital (type, amount, balance_after, notes) VALUES (?,?,?,?)',
                     ('init', amount, amount, '初始资金'))
        conn.commit()
        return f"✅ 初始资金设为 ¥{amount:.2f}"
    except Exception as e:
        return f"❌ 设置失败: {e}"
    finally:
        conn.close()

def reset_capital(amount):
    """重置初始资金（删除旧记录重新设置）"""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM capital WHERE type='init'")
        conn.execute('INSERT INTO capital (type, amount, balance_after, notes) VALUES (?,?,?,?)',
                     ('init', amount, amount, '初始资金（重置）'))
        conn.commit()
        return f"✅ 初始资金重置为 ¥{amount:.2f}"
    except Exception as e:
        return f"❌ 重置失败: {e}"
    finally:
        conn.close()

def deposit(amount, notes=''):
    """入金"""
    if amount <= 0:
        return "❌ 金额必须大于0"
    conn = get_conn()
    try:
        cur = get_current_balance(conn)
        new_balance = cur + amount
        label = notes or '入金'
        conn.execute('INSERT INTO capital (type, amount, balance_after, notes) VALUES (?,?,?,?)',
                     ('deposit', amount, round(new_balance, 2), label))
        conn.commit()
        return f"✅ 入金 ¥{amount:.2f}，当前资金余额 ¥{new_balance:.2f}"
    except Exception as e:
        return f"❌ 入金失败: {e}"
    finally:
        conn.close()

def withdraw(amount, notes=''):
    """出金"""
    if amount <= 0:
        return "❌ 金额必须大于0"
    conn = get_conn()
    try:
        cur = get_current_balance(conn)
        if cur < amount:
            return f"❌ 资金不足，当前余额 ¥{cur:.2f}"
        new_balance = cur - amount
        label = notes or '出金'
        conn.execute('INSERT INTO capital (type, amount, balance_after, notes) VALUES (?,?,?,?)',
                     ('withdraw', amount, round(new_balance, 2), label))
        conn.commit()
        return f"🔴 出金 ¥{amount:.2f}，当前资金余额 ¥{new_balance:.2f}"
    except Exception as e:
        return f"❌ 出金失败: {e}"
    finally:
        conn.close()

def get_current_balance(conn=None):
    """获取当前资金余额"""
    if conn is None:
        conn = get_conn()
        close_after = True
    else:
        close_after = False
    try:
        row = conn.execute("SELECT balance_after FROM capital ORDER BY id DESC LIMIT 1").fetchone()
        bal = row['balance_after'] if row else 0.0
        return bal
    finally:
        if close_after:
            conn.close()

def get_capital_summary():
    """获取资金概况"""
    conn = get_conn()
    try:
        init_row = conn.execute("SELECT amount FROM capital WHERE type='init' ORDER BY id ASC LIMIT 1").fetchone()
        init_amt = init_row['amount'] if init_row else 0.0
        
        total_deposit = conn.execute("SELECT COALESCE(SUM(amount),0) as s FROM capital WHERE type='deposit'").fetchone()['s']
        total_withdraw = conn.execute("SELECT COALESCE(SUM(amount),0) as s FROM capital WHERE type='withdraw'").fetchone()['s']
        
        current_balance = get_current_balance(conn)
        
        records = conn.execute("SELECT * FROM capital ORDER BY id DESC LIMIT 20").fetchall()
        
        return {
            'initial': init_amt,
            'total_deposit': total_deposit,
            'total_withdraw': total_withdraw,
            'net_input': init_amt + total_deposit - total_withdraw,
            'current_balance': current_balance,
            'records': [dict(r) for r in records]
        }
    finally:
        conn.close()

# 初始化
init_db()
