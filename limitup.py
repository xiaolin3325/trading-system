#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""连板自动扫描 v5 - akshare数据源"""
import json, os
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), 'limitup_data.json')

def scan():
    import akshare as ak
    import pandas as pd
    
    # 获取涨停板数据
    df = ak.stock_zt_pool_em(date='20260528')
    print(f'涨停总数: {len(df)}只\n')
    
    # 字段说明: 代码,名称,涨跌幅,最新价,连板数,涨停统计,封板时间...
    result = []
    for _, row in df.iterrows():
        code = str(row['代码'])
        name = row['名称']
        zdf = round(float(row['涨跌幅']), 1)
        price = round(float(row['最新价']), 2)
        lb = int(row['连板数']) if pd.notna(row['连板数']) else 0
        zt_stats = str(row.get('涨停统计', '')) if pd.notna(row.get('涨停统计', '')) else ''
        
        # 解析涨停统计: "5天5板" -> 天数5板数5
        days = 0
        boards = 0
        if zt_stats and '天' in zt_stats and '板' in zt_stats:
            parts = zt_stats.replace('板', '').split('天')
            if len(parts) == 2:
                days = int(parts[0]) if parts[0].isdigit() else 0
                boards = int(parts[1]) if parts[1].isdigit() else 0
        
        # 如果没有涨停统计，用连板数
        if boards == 0:
            boards = lb
            days = lb
        
        result.append({
            'name': name,
            'code': code,
            'price': price,
            'zdf': zdf,
            'consecutive': lb,     # 当前连板数（连板字段）
            'boards': boards,      # 总板数
            'span_days': days,     # 区间天数
            'tag': ''
        })
    
    return result

def format_output(stocks):
    non_c = [s for s in stocks if s['consecutive'] == 0 and s['boards'] > 1]
    consec = [s for s in stocks if s['consecutive'] >= 2]
    first = [s for s in stocks if s['consecutive'] == 1]
    
    lines = [f'涨停总数: {len(stocks)}只']
    
    if non_c:
        lines.append(f'\n几天几板 (今天未涨停):')
        for s in sorted(non_c, key=lambda x: x['boards'], reverse=True)[:10]:
            lines.append(f'  {s["name"]:8s} {s["code"]:6s}  {s["span_days"]}天{s["boards"]}板  {s["price"]:.2f}  +{s["zdf"]:.1f}%')
    
    ladder = {}
    for s in consec:
        c = s['consecutive']
        ladder.setdefault(c, []).append(s)
    for c in sorted(ladder.keys(), reverse=True):
        lines.append(f'\n{c}连板:')
        tag = ' (连板中)' if s['boards'] == s['consecutive'] else ''
        for s in ladder[c]:
            lines.append(f'  {s["name"]:8s} {s["code"]:6s}  {s["price"]:.2f}  +{s["zdf"]:.0f}%')
    
    if first:
        lines.append(f'\n首板({len(first)}只):')
        for s in first[:15]:
            lines.append(f'  {s["name"]:8s} {s["code"]:6s}  {s["price"]:.2f}  +{s["zdf"]:.0f}%')
        if len(first) > 15:
            lines.append(f'  ...还有{len(first)-15}只')
    
    return '\n'.join(lines)

def count_by_concept(stocks):
    """统计概念分布"""
    import akshare as ak
    try:
        df = ak.stock_board_concept_name_em()
        # 取当天涨停的概念股
        conc = {}
        for s in stocks:
            code = s['code']
            for _, board in df.iterrows():
                if board['板块名称'] in ['核电','新能源','军工','芯片','AI','机器人','低空经济']:
                    pass  # 简化处理
        return conc
    except:
        return {}

if __name__ == '__main__':
    stocks = scan()
    data = {'date': datetime.now().strftime('%Y-%m-%d'), 'time': '收盘', 'stocks': stocks}
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(format_output(stocks))
