# -*- coding: utf-8 -*-
"""
麦当劳「营养均衡」栏目 —— 早餐组合搜索（第一版）

组合结构（按用户设定）：
    1 份饮料 + 1–3 份「主食 / 配餐」（其中至少 1 份主食），总件数 2–4 样

目标依据：《中国居民膳食营养素参考摄入量(2023版)》+《中国居民膳食指南(2022)》
          成年轻体力活动  男 2250 kcal / 女 1800 kcal，按「日推荐量 ÷ 3」分配
"""
import sys, csv, itertools
from pathlib import Path
from statistics import median

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
CSV = BASE / 'data' / 'nutrition.csv'

DIMS = ['kcal', 'protein', 'fat', 'carb', 'sodium', 'calcium']
CN = {'kcal': '能量', 'protein': '蛋白', 'fat': '脂肪',
      'carb': '碳水', 'sodium': '钠', 'calcium': '钙'}
UNIT = {'kcal': 'kcal', 'protein': 'g', 'fat': 'g',
        'carb': 'g', 'sodium': 'mg', 'calcium': 'mg'}

# ---------- 早餐品类池（按麦当劳早餐在售品类划分）----------
PRIMARY = [            # 早餐主食：麦满分 / 炒双蛋堡 / 营养卷 / 粥
    '猪柳麦满分', '猪柳蛋麦满分', '烟肉蛋麦满分', '火腿扒麦满分', '大脆鸡扒麦满分',
    '原味板烧鸡腿麦满分', '双层原味板烧鸡腿麦满分', '双层猪柳蛋麦满分', '双层火腿扒麦满分',
    '猪柳炒双蛋堡', '原味板烧鸡腿炒双蛋堡',
    '火腿扒早安营养卷', '图林根香肠早安营养卷',
    '皮蛋鸡肉粥', '雪菜脆笋鸡肉粥',
]
SIDE = [               # 早餐配餐：薯饼 / 油条 / 香肠 / 玉米杯 / 苹果片
    '脆薯饼', '脆香油条', '德式图林根香肠', '大杯玉米杯', '小杯玉米杯', '苹果片',
]
DRINK = [              # 早餐饮料：牛奶 / 咖啡 / 豆浆 / 茶 / 热饮（均为早餐在售热饮）
    '热牛奶小杯', '热牛奶中杯', '热牛奶大杯',
    '热奶铁小杯', '热奶铁中杯', '热奶铁大杯',
    '热燕麦奶铁小杯', '热燕麦奶铁中杯', '热燕麦奶铁大杯',
    '热浓浓抹茶牛奶中杯', '热浓浓抹茶牛奶大杯',
    '热浓浓黑巧中杯', '热浓浓黑巧大杯',
    '热浓浓燕麦黑巧中杯', '热浓浓燕麦黑巧大杯',
    '热朱古力', '热焦糖玛奇朵', '卡布奇诺中杯', '卡布奇诺大杯',
    '热美式小杯', '热美式中杯', '热美式大杯',
    '小杯鲜萃咖啡', '大杯鲜萃咖啡', '浓缩咖啡',
    '优品豆浆小杯', '优品豆浆大杯',
    '锡兰红茶', '川宁伯爵红茶',
    '纯牛奶(盒装)', '100%苹果汁', '纯悦',
]

DAILY = {
    'male':   {'kcal': 2250, 'protein': 65, 'fat_ratio': (0.20, 0.30),
               'carb_ratio': (0.50, 0.65), 'sodium': 2000, 'calcium': 800},
    'female': {'kcal': 1800, 'protein': 55, 'fat_ratio': (0.20, 0.30),
               'carb_ratio': (0.50, 0.65), 'sodium': 2000, 'calcium': 800},
}


def meal_target(sex, r_lo=1 / 3, r_hi=1 / 3, sodium_cap=None):
    """r_lo/r_hi = 该餐占『日推荐量』的比例（早餐约 0.25–0.30；均分则 1/3）
    sodium_cap：若给定，覆盖钠上限（用于测试放宽钠约束）"""
    d = DAILY[sex]
    return {
        'kcal':    (d['kcal'] * r_lo * 0.9, d['kcal'] * r_hi * 1.1),
        'protein': (d['protein'] * r_lo * 0.9, 40),
        'fat':     (d['kcal'] * r_lo * d['fat_ratio'][0] / 9,
                    d['kcal'] * r_hi * d['fat_ratio'][1] / 9),
        'carb':    (d['kcal'] * r_lo * d['carb_ratio'][0] / 4,
                    d['kcal'] * r_hi * d['carb_ratio'][1] / 4),
        'sodium':  (0, sodium_cap if sodium_cap else d['sodium'] * r_hi),
        'calcium': (d['calcium'] * r_lo * 0.9, 1500),
    }


def load():
    data = {}
    with open(CSV, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            data[r['name']] = tuple(float(r[k]) for k in DIMS)
    return data


def check(data):
    bad = [n for n in PRIMARY + SIDE + DRINK if n not in data]
    if bad:
        print('!! 以下名称在 nutrition.csv 中找不到，请核对：')
        for n in bad:
            print('   -', n)
        sys.exit(1)


def penalty(v, tgt):
    total = 0.0
    for i, k in enumerate(DIMS):
        lo, hi = tgt[k]
        if v[i] < lo:
            total += (lo - v[i]) / lo if lo > 0 else 0
        elif v[i] > hi:
            total += (v[i] - hi) / hi if hi > 0 else 0
    return total


def dim_score(v, lo, hi):
    """单维度得分：区间内 1.0；区间外按相对偏离线性衰减，偏离 50% 归零"""
    if lo <= v <= hi:
        return 1.0
    if v < lo:
        rel = (lo - v) / lo if lo > 0 else 1.0
    else:
        rel = (v - hi) / hi if hi > 0 else 0.0
    return max(0.0, 1.0 - rel / 0.5)


def score(v, tgt):
    """返回 (总分 0–100, 各维度得分列表)"""
    ds = [dim_score(v[i], *tgt[k]) for i, k in enumerate(DIMS)]
    return sum(ds) / len(ds) * 100, ds


def base_of(name):
    """归一化基础品类名，用于避免「两杯玉米杯」这类重复搭配"""
    for s in ('大杯', '中杯', '小杯'):
        name = name.replace(s, '')
    return name


def build_combos():
    combos = []
    for d in DRINK:
        for np_ in (1, 2):
            for ps in itertools.combinations(PRIMARY, np_):
                for ns in (0, 1, 2):
                    if np_ + ns > 3:
                        continue
                    for ss in itertools.combinations(SIDE, ns):
                        names = [d] + list(ps) + list(ss)
                        if not (2 <= len(names) <= 4):
                            continue
                        bases = [base_of(n) for n in names]
                        if len(set(bases)) != len(bases):
                            continue
                        combos.append(names)
    return combos


def gap_text(v, tgt):
    out = []
    for i, k in enumerate(DIMS):
        lo, hi = tgt[k]
        if v[i] < lo:
            out.append(f'{CN[k]}差{lo - v[i]:.0f}')
        elif v[i] > hi:
            out.append(f'{CN[k]}超{v[i] - hi:.0f}')
    return '、'.join(out) if out else '全达标'


def run(sex, combos, data, label, r_lo=1 / 3, r_hi=1 / 3, topn=12, sodium_cap=None):
    tgt = meal_target(sex, r_lo, r_hi, sodium_cap)
    print('=' * 84)
    print(f'【{sex}】营养均衡 · 早餐 —— {label}')
    print('   目标区间：' + ' | '.join(f'{CN[k]} {tgt[k][0]:.0f}–{tgt[k][1]:.0f}' for k in DIMS))
    print(f'   共枚举组合 {len(combos):,} 个')

    scored = []
    for names in combos:
        v = [sum(data[n][i] for n in names) for i in range(len(DIMS))]
        total, ds = score(v, tgt)
        scored.append((total, names, v, ds))
    scored.sort(key=lambda x: (-x[0], len(x[1])))

    bands = {'≥90优秀': 0, '80–90良好': 0, '70–80一般': 0, '<70': 0}
    for t, *_ in scored:
        if t >= 90:
            bands['≥90优秀'] += 1
        elif t >= 80:
            bands['80–90良好'] += 1
        elif t >= 70:
            bands['70–80一般'] += 1
        else:
            bands['<70'] += 1
    print('   评分分布：' + '  '.join(f'{k} {n}' for k, n in bands.items()))

    print(f'\n>>> 推荐早餐 Top {topn}')
    for rank, (t, names, v, ds) in enumerate(scored[:topn], 1):
        wi = min(range(len(DIMS)), key=lambda i: ds[i])
        weak = '六维全达标' if ds[wi] >= 1 else f'短板：{CN[DIMS[wi]]} {ds[wi] * 100:.0f}分'
        print(f'{rank:>2}. {t:5.1f} 分 | ' + ' + '.join(names))
        print('     ' + ' | '.join(f'{CN[k]} {v[i]:.0f}{UNIT[k]}' for i, k in enumerate(DIMS)))
        print(f'     {weak}')
    print()


if __name__ == '__main__':
    data = load()
    check(data)
    combos = build_combos()
    for sex in ('male', 'female'):
        run(sex, combos, data, '早餐占全天 25%–30%（《膳食指南》口径）', 0.25, 0.30)
