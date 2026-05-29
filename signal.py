#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小布交易信号系统 v1.0
基于用户回测验证的 N字启动 + 惠天模式 筛选逻辑
"""

import sys, os, json, requests
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(__file__))
from db import *

sys.stdout.reconfigure(encoding='utf-8')

# ========== 配置 ==========
BBI_PERIODS = [3, 6, 12, 24]
VOL_MA_PERIOD = 5
ZT_LOOKBACK_DAYS = 7  # 查询最近几天内的涨停记录
MIN_AMPLITUDE = 4.0   # 最低振幅 %

HEADERS = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn'}

# ========== 数据获取 ==========

def sina_code(code):
    """代码转新浪格式"""
    if code.startswith(('6','5','688')):
        return f"sh{code}"
    elif code.startswith(('83','87','92')):
        return f"bj{code}"
    return f"sz{code}"

def get_hist_kline(code, days=30):
    """获取历史K线数据（新浪，最近days天）"""
    try:
        # 新浪日K线接口
        sc = sina_code(code)
        url = f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={sc}&scale=240&ma=no&datalen={days}'
        r = requests.get(url, headers=HEADERS, timeout=10, proxies={'http':None,'https':None})
        data = r.json()
        if not data:
            return None
        
        klines = []
        for item in data:
            klines.append({
                'date': item.get('day', ''),
                'open': float(item.get('open', 0)),
                'high': float(item.get('high', 0)),
                'low': float(item.get('low', 0)),
                'close': float(item.get('close', 0)),
                'volume': float(item.get('volume', 0)),
            })
        return klines
    except Exception as e:
        return None

def get_realtime(code):
    """获取实时行情（新浪）"""
    from trade import get_price
    return get_price(sina_code(code))
    try:
        r = requests.get(url, headers=HEADERS, timeout=8, proxies={'http':None,'https':None})
        r.encoding = 'gb18030'
        parts = r.text.split('~')
        if len(parts) >= 34:
            return {
                'name': parts[1],
                'price': float(parts[3]),
                'yclose': float(parts[4]),
                'open': float(parts[5]),
                'high': float(parts[33]) if parts[33] else 0,
                'low': float(parts[34]) if parts[34] else 0,
                'change_pct': float(parts[32]),
                'volume': int(parts[6]) if parts[6] else 0,
            }
    except:
        pass
    return None

# ========== 技术指标 ==========

def calc_ma(klines, period):
    """计算MA均线"""
    closes = [k['close'] for k in klines]
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period

def calc_bbi(klines):
    """计算BBI = (MA3 + MA6 + MA12 + MA24) / 4"""
    ma3 = calc_ma(klines, 3)
    ma6 = calc_ma(klines, 6)
    ma12 = calc_ma(klines, 12)
    ma24 = calc_ma(klines, 24)
    if None in (ma3, ma6, ma12, ma24):
        return None
    return (ma3 + ma6 + ma12 + ma24) / 4

def calc_avg_volume(klines, period):
    """计算平均成交量"""
    if len(klines) < period:
        return None
    return sum(k['volume'] for k in klines[-period:]) / period

def check_recent_zt(code, lookback_days=7):
    """检查最近几天是否涨停过（从limitup_data.json）"""
    try:
        with open(os.path.join(os.path.dirname(__file__), 'limitup_data.json'), 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 只检查当前最新的涨停数据
        for s in data.get('stocks', []):
            if s['code'] == code:
                return True, data.get('date', '')
    except:
        pass
    return False, ''

# ========== 信号生成 ==========

def generate_signal(code, name):
    """对单个标的生成交易信号"""
    signal = {
        'code': code,
        'name': name,
        'action': '观望',
        'reason': [],
        'score': 0,
        'detail': {},
    }
    
    # 1. 获取数据
    klines = get_hist_kline(code, 30)
    rt = get_realtime(code)
    
    if not klines or len(klines) < 24:
        signal['reason'].append('数据不足（<24个交易日）')
        return signal
    
    if not rt:
        signal['reason'].append('实时行情获取失败')
        return signal
    
    current_price = rt['price']
    signal['detail']['现价'] = round(current_price, 2)
    signal['detail']['涨幅'] = f"{rt['change']:+.2f}%"
    signal['detail']['昨收'] = round(rt['yclose'], 2)
    signal['detail']['量'] = f"{rt['volume']//10000}万"
    
    # 2. 计算BBI
    bbi = calc_bbi(klines)
    if bbi is None:
        signal['reason'].append('BBI计算失败')
        return signal
    signal['detail']['BBI'] = round(bbi, 2)
    
    # 3. 判断BBI位置（买点核心条件1）
    below_bbi = current_price < bbi
    signal['detail']['距BBI'] = f"{((current_price - bbi) / bbi * 100):+.2f}%"
    if below_bbi:
        signal['score'] += 3
        signal['reason'].append(f"✅ BBI下方 (现价{current_price}<BBI{bbi:.2f})")
    else:
        signal['reason'].append(f"⚠️ BBI上方 (现价{current_price}>BBI{bbi:.2f})")
    
    # 4. 成交量萎缩判断（买点核心条件2）
    recent_vol = klines[-1]['volume']
    avg_vol = calc_avg_volume(klines, VOL_MA_PERIOD)
    if avg_vol and avg_vol > 0:
        vol_ratio = recent_vol / avg_vol
        signal['detail']['今日量/5日均量'] = f"{vol_ratio:.2f}"
        if vol_ratio < 0.7:
            signal['score'] += 3
            signal['reason'].append(f"✅ 缩量(量比{vol_ratio:.2f}<0.7)")
        elif vol_ratio < 1.0:
            signal['score'] += 1
            signal['reason'].append(f"⚪ 量能适中(量比{vol_ratio:.2f})")
        else:
            signal['reason'].append(f"❌ 放量(量比{vol_ratio:.2f}>1)")
    
    # 5. 振幅判断（活跃度）
    if klines:
        recent_high = max(k['high'] for k in klines[-5:])
        recent_low = min(k['low'] for k in klines[-5:])
        amp = round((recent_high - recent_low) / recent_low * 100, 2)
        signal['detail']['5日振幅'] = f"{amp}%"
        if amp >= MIN_AMPLITUDE:
            signal['score'] += 2
            signal['reason'].append(f"✅ 活跃(5日振幅{amp}%)")
        else:
            signal['reason'].append(f"⚪ 振幅{amp}%")
    
    # 6. 前期涨停判断
    has_zt, zt_date = check_recent_zt(code)
    signal['detail']['近期涨停'] = f"{zt_date}" if has_zt else '无'
    if has_zt:
        signal['score'] += 2
        signal['reason'].append(f"✅ 近期涨停({zt_date})")
    else:
        signal['reason'].append('❌ 近期无涨停')
    
    # 7. 最终判定
    if signal['score'] >= 7:
        signal['action'] = '🟢 买入'
    elif signal['score'] >= 5:
        signal['action'] = '🟡 观察'
    elif signal['score'] >= 3:
        signal['action'] = '⚪ 关注'
    else:
        signal['action'] = '🔴 放弃'
    
    return signal


def run_scan():
    """扫描观察池所有标的"""
    watchlist = watch_list()
    if not watchlist:
        print("观察池为空，请先加入股票")
        return
    
    print("=" * 60)
    print(f"🐻 小布交易信号系统 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   策略: N字启动 + 惠天模式(缩量回调BBI+前期涨停)")
    print(f"   扫描: {len(watchlist)}只")
    print("=" * 60)
    print()
    
    results = []
    for w in watchlist:
        signal = generate_signal(w['code'], w['name'])
        results.append(signal)
    
    # 按分值排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # 输出买入信号
    buys = [r for r in results if r['action'] == '🟢 买入']
    watches = [r for r in results if r['action'] in ('🟡 观察', '⚪ 关注')]
    discards = [r for r in results if r['action'] == '🔴 放弃']
    
    if buys:
        print("⭐⭐⭐ 买入信号 ⭐⭐⭐")
        print("-" * 60)
        for s in buys:
            detail = ' | '.join([f"{k}:{v}" for k, v in s['detail'].items()])
            print(f"\n{s['action']} {s['name']}({s['code']})  评分:{s['score']}")
            print(f"   {detail}")
            for r in s['reason']:
                print(f"   {r}")
        print()
    
    if watches:
        print("📊 观察中")
        print("-" * 60)
        for s in watches:
            print(f"  {s['action']} {s['name']}({s['code']})  评分:{s['score']}  {s['detail'].get('现价','')}  BBI:{s['detail'].get('BBI','')}")
    
    if discards:
        print()
        print("❌ 暂不关注")
        print("-" * 60)
        for s in discards:
            print(f"  {s['action']} {s['name']}({s['code']})  {' | '.join(s['reason'][:2])}")
    
    print()
    print("=" * 60)
    print(f"扫描完成 | 买入:{len(buys)} 观察:{len(watches)} 放弃:{len(discards)}")


def signal_for_web():
    """供Web调用的信号数据"""
    results = []
    watchlist = watch_list()
    for w in watchlist:
        signal = generate_signal(w['code'], w['name'])
        results.append(signal)
    results.sort(key=lambda x: x['score'], reverse=True)
    return results


if __name__ == '__main__':
    run_scan()
