#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""连板梯队 v2 - 20日内滚动
consecutive: 当前连续涨停天数
boards: 20日内涨停总次数
span_days: 20日内从首次涨停到现在的交易日跨度
"""

import json, os
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), 'limitup_data.json')

# 每日收盘后更新此数据
# 更新指南:
# 1. 查今天涨停板
# 2. 算每只: 当前连续几板? 20日内总共几板?
# 3. 填入下方

STOCKS = [
    # ===== 龙头高标 (非连续) =====
    {"name": "永安药业", "code": "002365", "price": 11.77, "zdf": 0.0,
     "consecutive": 0, "boards": 7, "span_days": 11,
     "tag": "牛磺酸龙头"},
     
    {"name": "滨海能源", "code": "000695", "price": 15.36, "zdf": 0.0,
     "consecutive": 0, "boards": 6, "span_days": 8,
     "tag": "核电"},
    
    # ===== 连板梯队 =====
    {"name": "尚纬股份", "code": "603333", "price": 9.05, "zdf": 10.0,
     "consecutive": 5, "boards": 5, "span_days": 5,
     "tag": "核电电缆"},
     
    {"name": "融发核电", "code": "002366", "price": 7.04, "zdf": 10.0,
     "consecutive": 4, "boards": 4, "span_days": 4,
     "tag": "可控核聚变"},
    
    {"name": "通达电气", "code": "603390", "price": 13.36, "zdf": 10.0,
     "consecutive": 3, "boards": 3, "span_days": 3,
     "tag": "无人物流车"},
    {"name": "云内动力", "code": "000903", "price": 1.76, "zdf": 10.0,
     "consecutive": 3, "boards": 3, "span_days": 3,
     "tag": "无人配送动力"},
    {"name": "长城电工", "code": "600192", "price": 8.50, "zdf": 10.0,
     "consecutive": 3, "boards": 3, "span_days": 3,
     "tag": "核电开关设备"},
    {"name": "会稽山",   "code": "601579", "price": 12.50, "zdf": 10.0,
     "consecutive": 3, "boards": 3, "span_days": 3,
     "tag": "黄酒高端化"},
    {"name": "汇金通",   "code": "603577", "price": 9.80, "zdf": 10.0,
     "consecutive": 3, "boards": 3, "span_days": 3,
     "tag": "特高压铁塔"},
    {"name": "均瑶健康", "code": "605388", "price": 15.20, "zdf": 10.0,
     "consecutive": 3, "boards": 3, "span_days": 3,
     "tag": "益生菌"},
    
    # ===== 2连板 =====
    {"name": "劲旅环境", "code": "001230", "price": 22.00, "zdf": 10.0,
     "consecutive": 2, "boards": 2, "span_days": 2, "tag": "氢能环卫"},
    {"name": "尤夫股份", "code": "002427", "price": 6.50, "zdf": 10.0,
     "consecutive": 2, "boards": 2, "span_days": 2, "tag": "超高分子量纤维"},
    {"name": "明牌珠宝", "code": "002574", "price": 8.20, "zdf": 10.0,
     "consecutive": 2, "boards": 2, "span_days": 2, "tag": "黄金IP"},
    {"name": "华森制药", "code": "002907", "price": 18.50, "zdf": 10.0,
     "consecutive": 2, "boards": 2, "span_days": 2, "tag": "中药创新药"},
    {"name": "德邦股份", "code": "603056", "price": 14.30, "zdf": 10.0,
     "consecutive": 2, "boards": 2, "span_days": 2, "tag": "京东物流整合"},
    {"name": "锦泓集团", "code": "603518", "price": 11.00, "zdf": 10.0,
     "consecutive": 2, "boards": 2, "span_days": 2, "tag": "IP联名"},
    {"name": "海利尔",   "code": "603639", "price": 20.50, "zdf": 10.0,
     "consecutive": 2, "boards": 2, "span_days": 2, "tag": "绿色农药"},
    {"name": "江苏新能", "code": "603693", "price": 12.80, "zdf": 10.0,
     "consecutive": 2, "boards": 2, "span_days": 2, "tag": "资产注入"},
    {"name": "美邦股份", "code": "605033", "price": 16.00, "zdf": 10.0,
     "consecutive": 2, "boards": 2, "span_days": 2, "tag": "水溶肥"},
    
    # ===== 首板 =====
    {"name": "中核科技", "code": "000777", "price": 18.53, "zdf": 10.0,
     "consecutive": 1, "boards": 1, "span_days": 0, "tag": "核电跟风"},
    {"name": "大唐发电", "code": "601991", "price": 8.00, "zdf": 10.0,
     "consecutive": 1, "boards": 1, "span_days": 0, "tag": "电力+AI"},
    {"name": "杭电股份", "code": "603618", "price": 38.83, "zdf": 10.0,
     "consecutive": 0, "boards": 4, "span_days": 16, "tag": "通信电子"},
    {"name": "昆工科技", "code": "920152", "price": 19.55, "zdf": 20.0,
     "consecutive": 1, "boards": 1, "span_days": 0, "tag": "北交所"},
]

def valid(s):
    c = s['code']
    if c.startswith('688'): return False
    if c.startswith(('83','87','92','4')): return False
    return True

def sort_key(s):
    con = s.get('consecutive', 0)
    boards = s.get('boards', 0)
    return (con, boards)

def generate():
    stocks = [s for s in STOCKS if valid(s)]
    stocks.sort(key=sort_key, reverse=True)
    return {"date": "2026-05-28", "time": "20日滚动", "stocks": stocks}

def format_output(stocks):
    non_c = [s for s in stocks if s['consecutive'] == 0 and s['boards'] > 1]
    consec = [s for s in stocks if s['consecutive'] >= 2]
    first = [s for s in stocks if s['consecutive'] == 1]
    
    lines = [f'涨停总数: {len(stocks)}只 (20日窗口)']
    
    if non_c:
        lines.append(f'\n🔥 几天几板 (非连续):')
        for s in sorted(non_c, key=lambda x: x['boards'], reverse=True):
            lines.append(f'  {s["name"]:8s} {s["code"]:6s}  {s["span_days"]}天{s["boards"]}板  {s["price"]:.2f}  {s["tag"]}')
    
    ladder = {}
    for s in consec:
        c = s['consecutive']
        if c not in ladder: ladder[c] = []
        ladder[c].append(s)
    for c in sorted(ladder.keys(), reverse=True):
        lines.append(f'\n{c}连板:')
        for s in sorted(ladder[c], key=lambda x: x['boards'], reverse=True):
            m = ''
            if s['boards'] > s['consecutive']:
                m = f' (20日{s["boards"]}板)'
            lines.append(f'  {s["name"]:8s} {s["code"]:6s}  {s["price"]:.2f}  +{s["zdf"]:.0f}%{m}  {s["tag"]}')
    
    if first:
        lines.append(f'\n首板:')
        for s in sorted(first, key=lambda x: x.get('price', 0)):
            lines.append(f'  {s["name"]:8s} {s["code"]:6s}  {s["price"]:.2f}  +{s["zdf"]:.0f}%  {s["tag"]}')
    
    return '\n'.join(lines)

if __name__ == '__main__':
    data = generate()
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(format_output(data['stocks']))
