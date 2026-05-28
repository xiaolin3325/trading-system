#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""连板梯队 - 含首板 + 几天几板显示"""
import json, os

DATA_FILE = os.path.join(os.path.dirname(__file__), 'limitup_data.json')

# 今日连板数据 (手动更新)
# consecutive: 连续涨停天数
# days: 区间天数 (用于"几天几板"显示, 不连续时使用)
# boards: 区间内涨停次数 (用于"几天几板"显示)

STOCKS = [
    # === 高标龙头 ===
    {"name": "永安药业", "code": "002365", "price": 11.77, "zdf": 10.0, "consecutive": 0, "days": 11, "boards": 7, "tag": "牛磺酸龙头"},
    {"name": "滨海能源", "code": "000695", "price": 15.36, "zdf": 10.0, "consecutive": 0, "days": 8, "boards": 6, "tag": "核电"},
    
    # === 连板梯队 ===
    {"name": "尚纬股份", "code": "603333", "price": 9.05, "zdf": 10.0, "consecutive": 5, "tag": "核电电缆"},
    {"name": "融发核电", "code": "002366", "price": 7.04, "zdf": 10.0, "consecutive": 4, "tag": "可控核聚变"},
    
    {"name": "通达电气", "code": "603390", "price": 13.36, "zdf": 10.0, "consecutive": 3, "tag": "无人物流车"},
    {"name": "云内动力", "code": "000903", "price": 1.76, "zdf": 10.0, "consecutive": 3, "tag": "无人配送动力"},
    {"name": "长城电工", "code": "600192", "price": 8.50, "zdf": 10.0, "consecutive": 3, "tag": "核电开关设备"},
    {"name": "会稽山",   "code": "601579", "price": 12.50, "zdf": 10.0, "consecutive": 3, "tag": "黄酒高端化"},
    {"name": "汇金通",   "code": "603577", "price": 9.80, "zdf": 10.0, "consecutive": 3, "tag": "特高压铁塔"},
    {"name": "均瑶健康", "code": "605388", "price": 15.20, "zdf": 10.0, "consecutive": 3, "tag": "益生菌"},
    
    {"name": "劲旅环境", "code": "001230", "price": 22.00, "zdf": 10.0, "consecutive": 2, "tag": "氢能环卫"},
    {"name": "尤夫股份", "code": "002427", "price": 6.50, "zdf": 10.0, "consecutive": 2, "tag": "超高分子量纤维"},
    {"name": "明牌珠宝", "code": "002574", "price": 8.20, "zdf": 10.0, "consecutive": 2, "tag": "黄金IP"},
    {"name": "华森制药", "code": "002907", "price": 18.50, "zdf": 10.0, "consecutive": 2, "tag": "中药创新药"},
    {"name": "德邦股份", "code": "603056", "price": 14.30, "zdf": 10.0, "consecutive": 2, "tag": "京东物流整合"},
    {"name": "锦泓集团", "code": "603518", "price": 11.00, "zdf": 10.0, "consecutive": 2, "tag": "IP联名"},
    {"name": "海利尔",   "code": "603639", "price": 20.50, "zdf": 10.0, "consecutive": 2, "tag": "绿色农药"},
    {"name": "江苏新能", "code": "603693", "price": 12.80, "zdf": 10.0, "consecutive": 2, "tag": "资产注入"},
    {"name": "美邦股份", "code": "605033", "price": 16.00, "zdf": 10.0, "consecutive": 2, "tag": "水溶肥"},
    
    # === 首板 (今日首次涨停) ===
    # 从涨停分析数据看今日57股涨停，连板17只，首板约40只
    # 选取有板块效应的代表
    {"name": "中核科技", "code": "000777", "price": 18.53, "zdf": 10.0, "consecutive": 1, "tag": "核电跟风"},
    {"name": "大唐发电", "code": "601991", "price": 8.00, "zdf": 10.0, "consecutive": 1, "tag": "电力+AI"},
    {"name": "杭电股份", "code": "603618", "price": 38.83, "zdf": 10.0, "consecutive": 1, "tag": "通信电子"},
    {"name": "昆工科技", "code": "920152", "price": 19.55, "zdf": 20.0, "consecutive": 1, "tag": "北交所"},
    {"name": "戈碧迦",   "code": "920438", "price": 73.90, "zdf": 20.0, "consecutive": 1, "tag": "北交所光学玻璃"},
]

# 股票筛选（排除ST、科创、北交）
def valid_stock(s):
    c = s['code']
    if c.startswith('688'): return False  # 科创
    if c.startswith(('83','87','92','4')): return False  # 北交
    return True

def generate_data():
    stocks = [s for s in STOCKS if valid_stock(s)]
    return {
        "date": "2026-05-28",
        "time": "收盘",
        "stocks": stocks
    }

# 连板排序key
def sort_key(s):
    con = s.get('consecutive', 0)
    if con > 0: return (con, 1000)  # 连续连板排前面
    days = s.get('days', 0)
    boards = s.get('boards', 0)
    return (0, boards)  # 非连续按总板数排

def format_ladder(stocks):
    # 连板梯队
    ladder = {}
    non_consecutive = []
    for s in stocks:
        con = s.get('consecutive', 0)
        if con >= 2:
            if con not in ladder: ladder[con] = []
            ladder[con].append(s)
        elif con == 1:
            if 1 not in ladder: ladder[1] = []
            ladder[1].append(s)
        else:
            non_consecutive.append(s)
    
    lines = [f'今日涨停总数: {len(stocks)}只']
    
    # 非连续 (几天几板)
    if non_consecutive:
        lines.append(f'\n🔥 非连续 (几天几板):')
        for s in sorted(non_consecutive, key=lambda x: x.get('boards',0), reverse=True):
            ds = s.get('days',0)
            bs = s.get('boards',0)
            lines.append(f'  {s["name"]:8s} {s["code"]:6s}  {ds}天{bs}板  {s["price"]:.2f}  {s["tag"]}')
    
    # 连板梯队
    for d in sorted(ladder.keys(), reverse=True):
        label = '首板' if d == 1 else f'{d}连板'
        lines.append(f'\n{label}:')
        for s in ladder[d]:
            lines.append(f'  {s["name"]:8s} {s["code"]:6s}  {s["price"]:.2f}  +{s["zdf"]:.0f}%  {s["tag"]}')
    
    return '\n'.join(lines)

if __name__ == '__main__':
    data = generate_data()
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(format_ladder(data['stocks']))
