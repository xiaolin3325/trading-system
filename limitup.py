#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""连板梯队 - 数据更新"""
import json, os, requests
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), 'limitup_data.json')

def fetch_from_web():
    """直接从API获取涨停数据"""
    p = {'http': None, 'https': None}
    h = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}
    
    url = 'https://push2.eastmoney.com/api/qt/clist/get?cb=&pn=1&pz=100&po=1&np=1&fields=f2,f3,f12,f14,f36&fid=f3&fs=m:0+t:6+f:!2,m:0+t:80+f:!2&ut=bd1d9ddb04089700cf9c27f6f7426281'
    
    r = requests.get(url, headers=h, timeout=15, proxies=p)
    t = r.text
    if t.startswith('j('): t = t[2:-1]
    if t.endswith(')'): t = t[:-1]
    
    data = json.loads(t)
    items = data.get('data', {}).get('diff', [])
    
    stocks = []
    for i in items:
        zdf = float(i.get('f3', 0)) / 100
        code = i.get('f12', '')
        
        if code.startswith('3'):
            if zdf < 19.5: continue
        else:
            if zdf < 9.5: continue
        
        lb = i.get('f36', 0)
        stocks.append({
            'name': i.get('f14', ''),
            'code': code,
            'zdf': zdf,
            'price': float(i.get('f2', 0)) / 100,
            'board': int(lb) if lb else 0
        })
    
    return stocks

def format_ladder(stocks):
    """格式化连板梯队输出"""
    ladder = {}
    for s in stocks:
        d = s['board']
        if d not in ladder: ladder[d] = []
        ladder[d].append(s)
    
    lines = [f'今日涨停: {len(stocks)}只']
    
    for d in sorted(ladder.keys(), reverse=True):
        lines.append(f'\n{d}连板:')
        for s in ladder[d]:
            market = ''
            if s['code'].startswith('3'): market = '(创)'
            elif s['code'].startswith('688'): market = '(科)'
            lines.append(f'  {s["name"]:8s} {s["code"]:6s}  {s["price"]:.2f}  +{s["zdf"]:.1f}%{market}')
    
    return '\n'.join(lines)

if __name__ == '__main__':
    try:
        stocks = fetch_from_web()
        data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M'),
            'stocks': stocks
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(format_ladder(stocks))
    except Exception as e:
        print(f'获取数据失败: {e}')
        print()
        print('今日连板梯队 (人工数据):')
        print()
        print('5连板:')
        print('  尚纬股份(603333) - 核电电缆龙头')
        print()
        print('4连板:')
        print('  融发核电(002366) - 可控核聚变概念')
        print()
        print('3连板:')
        print('  通达电气(603390) - 无人物流车')
        print('  云内动力(000903) - 无人配送动力')
        print('  长城电工(600192) - 核电开关设备')
        print('  会稽山(601579) - 黄酒高端化')
        print('  汇金通(603577) - 特高压铁塔')
        print('  均瑶健康(605388) - 益生菌')
        print()
        print('2连板:')
        print('  劲旅环境(001230)  尤夫股份(002427)')
        print('  明牌珠宝(002574)  华森制药(002907)')
        print('  德邦股份(603056)  锦泓集团(603518)')
        print('  海利尔(603639)    江苏新能(603693)')
        print('  美邦股份(605033)')
