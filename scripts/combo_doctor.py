# -*- coding: utf-8 -*-
"""
麦当劳套餐营养体检 + 替换处方

输入：官方套餐（主食固定，小食 / 饮料可在官方替换项中选择）
输出：① 默认组合的营养画像与超标项  ② 官方可选范围内的最优替换方案

目标依据：《中国居民膳食指南(2022)》三餐分配
    早餐 25–30% ｜ 午餐 30–40% ｜ 晚餐 30–35%
蛋白质参考「每餐 20–30 g」的均匀分配原则，不按能量比例缩放。
"""
import sys, csv, json, itertools
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
CSV = BASE / 'data' / 'nutrition.csv'
MODEL = BASE / 'data' / 'menu_model.json'

DIMS = ['kcal', 'protein', 'fat', 'carb', 'sodium', 'calcium']
CN = {'kcal': '能量', 'protein': '蛋白', 'fat': '脂肪',
      'carb': '碳水', 'sodium': '钠', 'calcium': '钙'}
UNIT = {'kcal': 'kcal', 'protein': 'g', 'fat': 'g',
        'carb': 'g', 'sodium': 'mg', 'calcium': 'mg'}

DAILY = {
    'male':   {'kcal': 2250, 'sodium': 2000, 'calcium': 800},
    'female': {'kcal': 1800, 'sodium': 2000, 'calcium': 800},
}

# 三餐占全天能量的比例（中国居民膳食指南 2022）
MEAL_RATIO = {
    'breakfast': (0.25, 0.30),
    'lunch':     (0.30, 0.40),
    'dinner':    (0.30, 0.35),
    'regular':   (0.30, 0.40),   # 正餐菜单（午餐口径）
}


def load_nutrition():
    data = {}
    with open(CSV, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            data[r['name']] = tuple(float(r[k]) for k in DIMS)
    return data


def load_model():
    with open(MODEL, encoding='utf-8') as f:
        return json.load(f)


APPROX = {'鲜萃冰咖': '小杯鲜萃咖啡'}   # 菜单在售但营养表缺失时的近似替代


def norm(name, name_map):
    """把菜单售卖名转换为营养表名称；返回 None 表示无营养数据"""
    if name in name_map:
        return name_map[name]
    if name in APPROX:
        return APPROX[name]
    return name


def meal_target(sex, meal):
    d = DAILY[sex]
    lo_r, hi_r = MEAL_RATIO[meal]
    return {
        'kcal':    (d['kcal'] * lo_r, d['kcal'] * hi_r),
        'protein': (20, 40),                                  # 每餐 20–30g，上限放宽
        'fat':     (d['kcal'] * lo_r * 0.20 / 9, d['kcal'] * hi_r * 0.30 / 9),
        'carb':    (d['kcal'] * lo_r * 0.50 / 4, d['kcal'] * hi_r * 0.65 / 4),
        'sodium':  (0, d['sodium'] * hi_r * 0.85),            # 上限按该餐占比
        'calcium': (d['calcium'] * lo_r * 0.9, 1500),
    }


def dim_score(v, lo, hi):
    if lo <= v <= hi:
        return 1.0
    rel = (lo - v) / lo if v < lo else (v - hi) / hi
    return max(0.0, 1.0 - rel / 0.5)


def score(v, tgt):
    ds = [dim_score(v[i], *tgt[k]) for i, k in enumerate(DIMS)]
    return sum(ds) / len(ds) * 100, ds


def verdict(v, tgt):
    bad = []
    for i, k in enumerate(DIMS):
        lo, hi = tgt[k]
        if v[i] > hi:
            bad.append(f'{CN[k]}超{(v[i] - hi) / hi * 100:.0f}%')
        elif v[i] < lo:
            bad.append(f'{CN[k]}低{(lo - v[i]) / lo * 100:.0f}%')
    return '、'.join(bad) if bad else '六维全部达标'


def fmt(v):
    return ' | '.join(f'{CN[k]} {v[i]:.0f}{UNIT[k]}' for i, k in enumerate(DIMS))


def run(combo, nut, model, sex='male'):
    name_map = model['name_map']
    rounds = combo['rounds']
    tgt = meal_target(sex, combo['meal'])
    fixed = {i: r['name'] for i, r in enumerate(rounds) if 'name' in r}
    pools = [(i, r) for i, r in enumerate(rounds) if 'pool' in r]

    print('=' * 88)
    print(f"【{combo['name']}】¥{combo['price']}  ·  共 {len(rounds)} 轮")
    print(f"   建议值（{sex} · {combo['meal']}）：" +
          ' | '.join(f'{CN[k]} {tgt[k][0]:.0f}–{tgt[k][1]:.0f}' for k in DIMS))

    def value_of(picks):
        vec = [0.0] * len(DIMS)
        for i in range(len(rounds)):
            nm = fixed[i] if i in fixed else picks.get(i)
            k = norm(nm, name_map) if nm else None
            if k is None or k not in nut:
                return None
            for j in range(len(DIMS)):
                vec[j] += nut[k][j]
        return vec

    dflt = {}
    for i, r in pools:
        avail = [n for n, _ in model['pools'][r['pool']] if norm(n, name_map) in nut]
        dflt[i] = r['default'] if norm(r['default'], name_map) in nut else (avail[0] if avail else None)
    dv = value_of(dflt)
    if dv is None:
        print('   !! 默认组合缺营养数据，跳过')
        return
    d_score, _ = score(dv, tgt)
    desc = ' + '.join(rounds[i]['name'] if i in fixed else dflt[i] for i in range(len(rounds)))
    print(f"\n   ▸ 默认：{desc}")
    print(f"     {fmt(dv)}")
    print(f"     体检结论：{verdict(dv, tgt)}   ｜ 得分 {d_score:.1f}/100")

    na_parts = {}
    for i in range(len(rounds)):
        nm = fixed[i] if i in fixed else dflt[i]
        k = norm(nm, name_map)
        if k and k in nut:
            na_parts[rounds[i]['label']] = nut[k][4]
    if na_parts:
        detail = ' + '.join(f'{k} {v:.0f}' for k, v in na_parts.items())
        print(f'     钠来源：{detail} = {sum(na_parts.values()):.0f}mg' +
              (f'（上限 {tgt["sodium"][1]:.0f}mg）' if sum(na_parts.values()) > tgt['sodium'][1] else ''))

    # ---- 枚举官方全部替换组合（支持任意轮数）----
    opt_lists, total = [], 1
    for i, r in pools:
        opts = [(i, n, d) for n, d in model['pools'][r['pool']] if norm(n, name_map) in nut]
        opt_lists.append(opts)
        total *= len(opts)

    cands = []
    for combo_picks in itertools.product(*opt_lists):
        picks = dict(dflt)
        diff = 0.0
        for i, n, d in combo_picks:
            picks[i] = n
            diff += d
        v = value_of(picks)
        if v is None:
            continue
        sc, _ = score(v, tgt)
        cands.append((sc, diff, picks, v))
    cands.sort(key=lambda x: (-x[0], x[1]))

    print(f"\n   ▸ 处方（在官方 {total} 种替换组合中求解）")
    shown = 0
    for sc, diff, picks, v in cands:
        if all(picks[i] == dflt[i] for i in dflt):
            continue
        shown += 1
        if shown > 3:
            break
        changes = ' ｜ '.join(rounds[i]['label'] + '「' + dflt[i] + '」→「' + picks[i] + '」'
                             for i in dflt if picks[i] != dflt[i])
        d_txt = f'{"+" if diff >= 0 else "-"}¥{abs(diff):.1f}' if diff else '不加价'
        print(f'     {shown}) {changes}')
        print(f'        {fmt(v)}')
        print(f'        得分 {sc:.1f}（{sc - d_score:+.1f}）｜ 差价 {d_txt} ｜ {verdict(v, tgt)}')

    if cands:
        na_min = min(c[3][4] for c in cands)
        if cands[0][3][4] > tgt['sodium'][1]:
            main_name = next(iter(fixed.values()), '')
            mk = norm(main_name, name_map)
            main_na = nut[mk][4] if mk in nut else 0
            print(f'\n     ⚠ 穷尽官方全部替换项后，钠仍无法达标（理论最低 {na_min:.0f}mg，上限 {tgt["sodium"][1]:.0f}mg）')
            print(f'       根因：主食「{main_name}」自身含钠 {main_na:.0f}mg，占了大头；'
                  f'可替换项的空间已用尽。要真正解决，只能更换主食（如麦香鱼 556mg、吉士汉堡包 492mg）。')
    print()


if __name__ == '__main__':
    nut = load_nutrition()
    model = load_model()
    sex = sys.argv[1] if len(sys.argv) > 1 else 'male'
    print(f'\n>>> 体检对象：{sex}（{DAILY[sex]["kcal"]} kcal/天）\n')
    for combo in model['combos']:
        run(combo, nut, model, sex)
