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
    """买入记录"""
    conn = get_conn()
    conn.execute('BEGIN')
    try:
        amount = round(shares * price, 2)
        
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
        return f"✅ 买入 {name}({code}) {shares}股 @ {price}，总成本 {amount:.2f}"
    except Exception as e:
        conn.rollback()
        return f"❌ 买入失败: {e}"
    finally:
        conn.close()

def sell(code, shares, notes=''):
    """卖出记录"""
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
        
        # 记录交易（卖价后面更新）
        conn.execute(
            'INSERT INTO trades (code, name, type, shares, price, amount, notes) VALUES (?,?,?,?,?,?,?)',
            (code, name, 'sell', shares, 0, 0, notes)
        )
        
        if shares == holding['shares']:
            conn.execute('DELETE FROM holdings WHERE code=?', (code,))
            msg = f"🔴 清仓 {name}({code}) {shares}股"
        else:
            new_shares = holding['shares'] - shares
            new_cost = holding['total_cost'] * (new_shares / holding['shares'])
            new_avg = round(new_cost / new_shares, 3) if new_shares > 0 else 0
            conn.execute('UPDATE holdings SET shares=?, total_cost=?, avg_cost=? WHERE code=?',
                         (new_shares, round(new_cost, 2), new_avg, code))
            msg = f"🔻 减仓 {name}({code}) {shares}股，剩余 {new_shares}股"
        
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

# 初始化
init_db()
