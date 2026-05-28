#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""连板自动扫描 v3 - 从K线数据自动算连板"""
import requests, json, os
from datetime import datetime

HEADERS = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn'}
P = {'http': None, 'https': None}
DATA_FILE = os.path.join(os.path.dirname(__file__), 'limitup_data.json')

# 候选池 (只放确实有可能涨停的)
POOL = [
    "002365.SZ", # 永安药业
    "000695.SZ", # 滨海能源
    "603333.SH", # 尚纬股份
    "002366.SZ", # 融发核电
    "603390.SH", # 通达电气
    "000903.SZ", # 云内动力
    "600192.SH", # 长城电工
    "603577.SH", # 汇金通
    "605388.SH", # 均瑶健康
    "001230.SZ", # 劲旅环境
    "002427.SZ", # 尤夫股份
    "002574.SZ", # 明牌珠宝
    "002907.SZ", # 华森制药
    "603056.SH", # 德邦股份
    "603518.SH", # 锦泓集团
    "603639.SH", # 海利尔
    "603693.SH", # 江苏新能
    "605033.SH", # 美邦股份
    "000777.SZ", # 中核科技
    "601991.SH", # 大唐发电
    "603618.SH", # 杭电股份
    "600875.SH", # 东方电气
    "601985.SH", # 中国核电
    "603045.SH", # 福达合金
    "600130.SH", # 波导股份
    "601579.SH", # 会稽山
    "600537.SH", # 亿晶光电(ST)
]

def to_sina(code):
    p = code.split('.')
    m = {'SZ':'sz','SH':'sh','BJ':'bj'}
    return f"{m.get(p[1],'sz')}{p[0]}"

def to_code(code):
    # 002365.SZ -> 002365
    return code.split('.')[0]

def get_name(code):
    try:
        r = requests.get(f'https://hq.sinajs.cn/list={to_sina(code)}', headers=HEADERS, timeout=5, proxies=P)
        r.encoding = 'gb18030'
        return r.text.split('"')[1].split(',')[0]
    except:
        return ''

def get_klines(code, days=25):
    symbol = to_sina(code)
    url = 'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
    r = requests.get(url, params={'symbol':symbol,'scale':240,'datalen':days}, headers=HEADERS, timeout=10, proxies=P)
    return r.json()

def is_limitup(zdf, code):
    if code.startswith('3'): return zdf >= 19.0
    return zdf >= 9.0  # 留点容差

def scan():
    results = []
    for code in POOL:
        name = ''
        try:
            klines = get_klines(code, 25)
            if not klines or len(klines) < 5:
                continue
            
            name = get_name(code)
            if 'ST' in name.upper() or '退' in name:
                print(f'  ST跳过 {name} {code}')
                continue
            
            # 解析K线
            data = klines[-22:]  # 留点余量
            closes = [float(k['close']) for k in data]
            
            # 每天涨跌幅
            zdfs = [0]  # 第一天没有
            for i in range(1, len(data)):
                zdf = (closes[i] - closes[i-1]) / closes[i-1] * 100
                zdfs.append(round(zdf, 1))
            
            # 涨停标记
            is_lb = [is_limitup(zdfs[i], code) for i in range(len(data))]
            
            # 当前连板 (从今天往左数)
            current = 0
            for i in range(len(data)-1, 0, -1):
                if is_lb[i]:
                    current += 1
                else:
                    break
            
            # 20日内总板数
            boards_20 = sum(1 for i in range(max(1, len(data)-20), len(data)) if is_lb[i])
            
            # 20日内跨度 (从第一次涨停到现在)
            span = 0
            first_lb = -1
            for i in range(max(1, len(data)-20), len(data)):
                if is_lb[i]:
                    if first_lb == -1:
                        first_lb = i
                    span = len(data) - 1 - first_lb
            
            today_zdf = zdfs[-1] if len(zdfs) > 1 else 0
            today_close = closes[-1]
            
            results.append({
                'name': name,
                'code': to_code(code),
                'price': round(today_close, 2),
                'zdf': today_zdf,
                'consecutive': current,
                'boards': boards_20,
                'span_days': max(span, 0),
                'tag': ''
            })
        except Exception as e:
            if not name:
                name = code
            pass
    
    # 有涨停记录的才保留
    results = [r for r in results if r['boards'] > 0]
    results.sort(key=lambda x: (x['consecutive'], x['boards']), reverse=True)
    
    return {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': '20日自动',
        'stocks': results
    }

if __name__ == '__main__':
    print('连板自动扫描 v3 - 正在获取数据...')
    data = scan()
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    stocks = data['stocks']
    print(f'\n扫描完成: {len(stocks)}只有涨停记录')
    
    non_c = [s for s in stocks if s['consecutive'] == 0 and s['boards'] > 1]
    consec = [s for s in stocks if s['consecutive'] >= 2]
    first = [s for s in stocks if s['consecutive'] == 1]
    
    if non_c:
        print(f'\n几天几板 (今天未涨停):')
        for s in sorted(non_c, key=lambda x: x['boards'], reverse=True):
            print(f'  {s["name"]:8s} {s["code"]:6s}  {s["span_days"]}天{s["boards"]}板  {s["price"]:.2f}  {s["zdf"]:+.1f}%')
    
    ladder = {}
    for s in consec:
        c = s['consecutive']
        ladder.setdefault(c, []).append(s)
    for c in sorted(ladder.keys(), reverse=True):
        print(f'\n{c}连板:')
        for s in ladder[c]:
            print(f'  {s["name"]:8s} {s["code"]:6s}  {s["price"]:.2f}  +{s["zdf"]:.0f}%')
    
    if first:
        print(f'\n首板:')
        for s in first:
            print(f'  {s["name"]:8s} {s["code"]:6s}  {s["price"]:.2f}  +{s["zdf"]:.0f}%')
    print()
