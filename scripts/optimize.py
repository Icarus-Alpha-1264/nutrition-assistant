# -*- coding: utf-8 -*-
"""
麦当劳餐品营养均衡搭配 —— 组合搜索

目标依据：《中国居民膳食营养素参考摄入量(2023版)》+《中国居民膳食指南(2022)》
成人(18-49岁) 轻体力活动：男性 2250 kcal/天，女性 1800 kcal/天
按用户要求：一餐目标 = 日推荐量 / 3

搜索 1–3 件餐品的所有组合，找出最接近「一餐目标」的搭配。
"""
import sys, csv, itertools
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
CSV = BASE / 'data' / 'nutrition.csv'

DIMS = ['kcal', 'protein', 'fat', 'carb', 'sodium', 'calcium']
CN = {'kcal': '能量kcal', 'protein': '蛋白质g', 'fat': '脂肪g',
      'carb': '碳水g', 'sodium': '钠mg', 'calcium': '钙mg'}

# ---- 每日推荐量（成人轻体力活动，男性 2250 kcal / 女性 1800 kcal）----
DAILY = {
    'male':   {'kcal': 2250, 'protein': 65, 'fat_ratio': (0.20, 0.30),
               'carb_ratio': (0.50, 0.65), 'sodium': 2000, 'calcium': 800},
    'female': {'kcal': 1800, 'protein': 55, 'fat_ratio': (0.20, 0.30),
               'carb_ratio': (0.50, 0.65), 'sodium': 2000, 'calcium': 800},
}


def meal_target(sex):
    """把日推荐量换算成『一餐』目标（区间）"""
    d = DAILY[sex]
    kcal = d['kcal'] / 3
    fat_lo = d['kcal'] * d['fat_ratio'][0] / 9 / 3
    fat_hi = d['kcal'] * d['fat_ratio'][1] / 9 / 3
    carb_lo = d['kcal'] * d['carb_ratio'][0] / 4 / 3
    carb_hi = d['kcal'] * d['carb_ratio'][1] / 4 / 3
    return {
        'kcal':    (kcal * 0.9, kcal * 1.1),      # 能量 ±10%
        'protein': (d['protein'] / 3 * 0.9, 40),  # 下限 90%，上限宽松
        'fat':     (fat_lo, fat_hi),
        'carb':    (carb_lo, carb_hi),
        'sodium':  (0, d['sodium'] / 3),          # 上限硬约束
        'calcium': (d['calcium'] / 3 * 0.9, 1500),# 下限 90%
    }


def penalty(sumv, tgt):
    """各维度相对偏离之和：区间内=0，区间外按相对距离计罚"""
    total = 0.0
    for i, k in enumerate(DIMS):
        lo, hi = tgt[k]
        v = sumv[i]
        if v < lo:
            total += (lo - v) / lo if lo > 0 else 0
        elif v > hi:
            total += (v - hi) / hi if hi > 0 else 0
    return total


def load():
    items = []
    with open(CSV, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            vals = tuple(float(r[k]) for k in DIMS)
            items.append((r['name'], vals))
    return items


def search(items, tgt, k):
    results = []
    for combo in itertools.combinations(items, k):
        s = [sum(c[1][i] for c in combo) for i in range(len(DIMS))]
        results.append((penalty(s, tgt), combo, s))
    return results


def fmt(s):
    return ' | '.join(f'{CN[k]} {v:.1f}' for k, v in zip(DIMS, s))


def show(sex):
    tgt = meal_target(sex)
    items = load()
    print('=' * 78)
    print(f'【{sex}】一餐目标（日推荐量 ÷ 3）')
    for k in DIMS:
        lo, hi = tgt[k]
        hi_s = f'{hi:.0f}' if hi < 9000 else '不限'
        print(f'   {CN[k]:<10} {lo:.1f} – {hi_s}')
    print()

    all_res = []
    for k in (1, 2, 3):
        all_res += search(items, tgt, k)
    all_res.sort(key=lambda x: x[0])

    # 完全达标（6 维全部落在区间内）
    perfect = [r for r in all_res if r[0] == 0]
    print(f'>>> 6 维全部达标的组合数：{len(perfect)}')
    cnt = {}
    for r in all_res:
        n_ok = sum(1 for i, k in enumerate(DIMS)
                   if tgt[k][0] <= r[2][i] <= tgt[k][1])
        cnt[n_ok] = cnt.get(n_ok, 0) + 1
    for n in sorted(cnt, reverse=True):
        print(f'    达标 {n} 维的组合数：{cnt[n]}')
    print()

    if perfect:
        print(f'>>> 完全达标组合（前 10 个）：')
        for _, combo, s in perfect[:10]:
            print('  * ' + ' + '.join(c[0] for c in combo))
            print('      ' + fmt(s))
        print()

    print('>>> 最接近的组合 Top 15：')
    for rank, (p, combo, s) in enumerate(all_res[:15], 1):
        n_ok = sum(1 for i, k in enumerate(DIMS) if tgt[k][0] <= s[i] <= tgt[k][1])
        print(f'{rank:>2}. 偏离 {p:.3f} | 达标 {n_ok}/6 | ' + ' + '.join(c[0] for c in combo))
        print(f'    {fmt(s)}')
    print()


if __name__ == '__main__':
    show('male')
    show('female')
