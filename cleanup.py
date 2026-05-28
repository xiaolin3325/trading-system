import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from db import *

# 移除ST股
code = '600537'
watch_remove(code)
print(f'已移除 {code}（ST股）')

# 显示当前观察池
print(f'\n当前观察池 ({len(watch_list())}只):')
for w in watch_list():
    print(f'  {w["name"]} ({w["code"]}) - {w["reason"]}')
