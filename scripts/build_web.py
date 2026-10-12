# -*- coding: utf-8 -*-
"""
生成网页工作台：web/index.html

从 data/nutrition.csv 与 data/menu_model.json 生成单文件 HTML（零依赖、可离线打开、可部署 GitHub Pages）。
数据只读不写，重新运行即可刷新页面数据。
"""
import csv, json, sys, time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
CSV = BASE / 'data' / 'nutrition.csv'
MODEL = BASE / 'data' / 'menu_model.json'
OUT = BASE / 'docs' / 'index.html'   # GitHub Pages 支持以 /docs 作为发布源

DIMS = ['kcal', 'protein', 'fat', 'carb', 'sodium', 'calcium']

DAILY = {
    'male':   {'kcal': 2250, 'sodium': 2000, 'calcium': 800},
    'female': {'kcal': 1800, 'sodium': 2000, 'calcium': 800},
}
MEAL_RATIO = {
    'breakfast': [0.25, 0.30],   # 早餐 25–30%
    'lunch':     [0.30, 0.40],   # 午餐 30–40%
    'dinner':    [0.30, 0.35],   # 晚餐 30–35%
}


def build_targets():
    out = {}
    for sex, d in DAILY.items():
        out[sex] = {}
        for meal, (lo_r, hi_r) in MEAL_RATIO.items():
            out[sex][meal] = {
                'kcal':    [d['kcal'] * lo_r, d['kcal'] * hi_r],
                'protein': [20, 40],
                'fat':     [d['kcal'] * lo_r * 0.20 / 9, d['kcal'] * hi_r * 0.30 / 9],
                'carb':    [d['kcal'] * lo_r * 0.50 / 4, d['kcal'] * hi_r * 0.65 / 4],
                'sodium':  [0, d['sodium'] * hi_r * 0.85],
                'calcium': [d['calcium'] * lo_r * 0.9, 1500],   # 钙为「越多越好」，上限放宽
            }
    return out


TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>麦麦营养均衡助手 · 套餐体检台</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:#f6f4f1;color:#1c1c1c;line-height:1.6;padding-bottom:60px}
.wrap{max-width:900px;margin:0 auto;padding:0 20px}
header{background:#DA291C;color:#fff;padding:30px 0 26px}
h1{font-size:23px;font-weight:700;letter-spacing:.3px}
.sub{font-size:14px;opacity:.92;margin-top:8px}
.sub b{background:#FFC72C;color:#1c1c1c;padding:1px 7px;border-radius:5px;font-weight:600}
.timebar{margin-top:16px;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);border-radius:10px;padding:10px 14px;font-size:13px;display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.timebar .dot{width:7px;height:7px;border-radius:50%;background:#7CE38B;flex:none;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.timebar b{color:#FFC72C;font-weight:600}
.segrow{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}
.card{background:#fff;border-radius:14px;padding:22px;margin-top:18px;box-shadow:0 1px 3px rgba(0,0,0,.07)}
.card h2{font-size:15px;font-weight:600;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.card h2::before{content:"";width:4px;height:15px;background:#DA291C;border-radius:2px}
.cardhead{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.cardhead h2{margin-bottom:0}
.bestbtn{background:#FFC72C;border:0;color:#1c1c1c;font-weight:600;font-size:13px;padding:9px 18px;border-radius:9px;cursor:pointer;font-family:inherit;transition:background .15s,transform .1s}
.bestbtn:hover{background:#eab91f}
.bestbtn:active{transform:scale(.97)}
.ctrl{display:grid;gap:14px;margin-bottom:14px}
.fixed{padding:11px 12px;border:1px dashed #ddd;border-radius:9px;font-size:14px;color:#999;background:#fafaf8}
.fixed::after{content:" 固定";font-size:11px;color:#c4c4c4}
label{font-size:12px;color:#777;display:block;margin-bottom:6px}
select{width:100%;padding:10px 8px;border:1px solid #ddd;border-radius:9px;font-size:14px;background:#fff;cursor:pointer}
select:focus{outline:none;border-color:#DA291C}
.seg{display:inline-flex;background:#f0eeeb;border-radius:9px;padding:3px}
.seg button{border:0;background:transparent;padding:7px 18px;border-radius:7px;font-size:13px;cursor:pointer;color:#666;font-family:inherit}
.seg button.on{background:#fff;color:#DA291C;font-weight:600;box-shadow:0 1px 2px rgba(0,0,0,.08)}
.scorebox{display:flex;align-items:center;gap:22px;flex-wrap:wrap;margin-bottom:20px}
.score{font-size:46px;font-weight:700;line-height:1}
.score small{font-size:15px;font-weight:400;color:#999;margin-left:3px}
.verdict{font-size:14px;color:#555}
.pill{display:inline-block;padding:3px 11px;border-radius:20px;font-size:12.5px;margin:2px 5px 2px 0}
.pill.ok{background:#e6f4ea;color:#1e7e34}
.pill.bad{background:#fdecea;color:#c62828}
.pill.low{background:#fff4e5;color:#b26a00}
.row{display:grid;grid-template-columns:64px 1fr 130px;gap:12px;align-items:center;margin-bottom:13px}
.rname{font-size:13px;color:#555;text-align:right}
.rval{font-size:13px;font-weight:600}
.rval em{font-style:normal;font-size:11.5px;color:#999;font-weight:400;margin-left:4px}
.track{position:relative;height:17px;background:#f0f0f0;border-radius:9px;margin-top:5px}
.fill{position:absolute;left:0;top:0;height:100%;border-radius:9px;transition:width .35s ease,background .35s}
.range{position:absolute;top:0;height:100%;border-left:1.5px dashed #7fbf8a;border-right:1.5px dashed #7fbf8a;background:rgba(120,200,140,.16);z-index:2}
.tag{font-size:12px;text-align:left}
.tag.ok{color:#1e7e34}
.tag.bad{color:#c62828}
.tag.low{color:#b26a00}
.na-note{font-size:12.5px;color:#777;background:#faf8f5;border-left:3px solid #FFC72C;padding:9px 12px;border-radius:0 7px 7px 0;margin-top:6px}
.adv{background:#fafaf8;border-radius:10px;padding:12px 14px;margin-top:10px;border-left:3px solid #e0ddd8}
.adv-b{font-size:12.5px;color:#666;line-height:1.7;margin-top:7px;padding-left:11px;position:relative}
.adv-b::before{content:"";position:absolute;left:2px;top:8px;width:4px;height:4px;border-radius:50%;background:#ccc}
.adv-none{font-size:13px;color:#1e7e34;background:#f0f9f1;padding:12px 14px;border-radius:10px;margin-top:16px}
.adv-head{font-size:13px;font-weight:600;color:#444;margin:20px 0 2px;padding-top:16px;border-top:1px solid #f0f0f0}
.src{font-size:11.5px;color:#999;line-height:1.75;margin-top:16px;padding-top:13px;border-top:1px solid #f0f0f0}
.src b{color:#777;font-weight:600}
.rx{border:1px solid #eee;border-radius:11px;padding:14px;margin-bottom:11px;transition:.2s}
.rx:hover{border-color:#FFC72C;background:#fffdf7}
.rx .head{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}
.rx .name{font-size:14px;font-weight:600}
.rx .delta{font-size:12.5px;color:#1e7e34;font-weight:600}
.rx .meta{font-size:12.5px;color:#777}
.rx .meta span{margin-right:14px}
.rx.best{border-color:#DA291C;background:#fffaf9}
.rx.best .name::after{content:"推荐";font-size:11px;background:#DA291C;color:#fff;padding:1px 7px;border-radius:5px;margin-left:8px;font-weight:500;vertical-align:1px}
footer{font-size:12px;color:#999;text-align:center;margin-top:26px;line-height:1.9}
footer a{color:#DA291C;text-decoration:none}
@media(max-width:640px){
 .ctrl{grid-template-columns:1fr}
 .row{grid-template-columns:52px 1fr;gap:8px}
 .tag{grid-column:2}
 .score{font-size:38px}
}
</style>
</head>
<body>
<header>
  <div class="wrap">
    <h1>麦麦营养均衡助手</h1>
    <div class="sub">选一个官方套餐，看清这一餐的<b>六维营养</b>，再让它在官方替换项里帮你配到最优。<br>数据来自麦当劳官方 MCP，方案全部可在门店真实下单。</div>
    <div class="timebar">
      <span class="dot"></span>
      <span>当前 <b id="nowTime">--:--:--</b>（麦当劳 MCP 服务器时间）</span>
      <span>·</span>
      <span>识别为 <b id="nowMeal">--</b></span>
    </div>
  </div>
</header>

<div class="wrap">
  <div class="card">
    <div class="cardhead">
      <h2>选择套餐</h2>
      <button class="bestbtn" id="bestBtn">一键最优</button>
    </div>
    <div class="segrow">
      <div class="seg" id="sexSeg">
        <button data-sex="male" class="on">成年男性 2250 kcal</button>
        <button data-sex="female">成年女性 1800 kcal</button>
      </div>
      <div class="seg" id="mealSeg">
        <button data-meal="auto" class="on">按时间自动</button>
        <button data-meal="breakfast">早餐</button>
        <button data-meal="lunch">午餐</button>
        <button data-meal="dinner">晚餐</button>
      </div>
    </div>
    <div class="ctrl">
      <div><label>套餐</label><select id="comboSel"></select></div>
    </div>
    <div class="ctrl" id="pickers"></div>
    <div class="na-note" id="poolNote"></div>
  </div>

  <div class="card">
    <h2>营养体检</h2>
    <div class="scorebox">
      <div><div class="score" id="scoreNum">--<small>分</small></div></div>
      <div class="verdict" id="verdict">--</div>
    </div>
    <div id="bars"></div>
    <div id="advice"></div>
    <div class="src">
      <b>建议值依据</b>：《中国居民膳食营养素参考摄入量（2023版）》《中国居民膳食指南（2022）》——
      能量按餐次占比分配（早餐 25–30%／午餐 30–40%／晚餐 30–35%）；蛋白质按「每餐 20–30g」均匀分配；
      脂肪、碳水化合物按供能比（20–30%／50–65%）换算；钠按全天上限 2000mg、钙按全天推荐 800mg 分摊至本餐。
      <br>注：本页仅评估单餐，全日摄入仍需结合其他餐次统筹。
    </div>
  </div>

  <div class="card">
    <h2>替换处方（官方允许范围内）</h2>
    <div id="rx"></div>
  </div>

  <footer>
    数据来源：麦当劳官方 MCP（now-time-info / list-nutrition-foods / query-meals / query-meal-detail）<br>
    营养标准：《中国居民膳食营养素参考摄入量（2023版）》《中国居民膳食指南（2022）》<br>
    本页为参赛作品演示，非麦当劳官方产品；输出仅供参考，不构成营养或医疗建议。
  </footer>
</div>

<script>
const NUT = __NUT__;
const MODEL = __MODEL__;
const TARGETS = __TARGETS__;
const DIMS = ["kcal","protein","fat","carb","sodium","calcium"];
const CN = {kcal:"能量",protein:"蛋白",fat:"脂肪",carb:"碳水",sodium:"钠",calcium:"钙"};
const UNIT = {kcal:"kcal",protein:"g",fat:"g",carb:"g",sodium:"mg",calcium:"mg"};

const SERVER_TS = __SERVER_TS__, LOCAL_TS = __LOCAL_TS__;
const CLOCK_OFFSET = SERVER_TS - LOCAL_TS;   // 用麦当劳服务器时钟校正本地时钟

let sex = "male", cur = 0, segMode = "auto";
const $ = id => document.getElementById(id);

const MEAL_CN = {breakfast:"早餐", lunch:"午餐", dinner:"晚餐"};
function serverNow(){ return new Date(Date.now() + CLOCK_OFFSET); }
function detectMeal(d){
  const m = d.getHours() + d.getMinutes()/60;
  if (m >= 4 && m < 10.5) return "breakfast";   // 麦当劳早餐供应至 10:30
  if (m >= 10.5 && m < 15) return "lunch";
  return "dinner";
}
function activeMeal(){ return segMode === "auto" ? detectMeal(serverNow()) : segMode; }
function activeMenu(){ return activeMeal() === "breakfast" ? "breakfast" : "regular"; }

function key(name){
  const m = MODEL.name_map;
  if (name in m) return m[name];
  if (name === "鲜萃冰咖") return "小杯鲜萃咖啡";
  return name;
}
function vecOf(names){
  const v = [0,0,0,0,0,0];
  for (const n of names){
    const k = key(n);
    if (!NUT[k]) return null;
    for (let i=0;i<6;i++) v[i] += NUT[k][i];
  }
  return v;
}
function dimScore(val, lo, hi){
  if (val >= lo && val <= hi) return 1;
  const rel = val < lo ? (lo-val)/lo : (val-hi)/hi;
  return Math.max(0, 1 - rel/0.5);
}
function scoreOf(v, t){
  let s = 0;
  DIMS.forEach((d,i)=>{ s += dimScore(v[i], t[d][0], t[d][1]); });
  return s/6*100;
}
function statusOf(val, lo, hi){
  if (val < lo) return {k:"low", txt:"低 " + Math.round((lo-val)/lo*100) + "%"};
  if (val > hi) return {k:"bad", txt:"超 " + Math.round((val-hi)/hi*100) + "%"};
  return {k:"ok", txt:"达标"};
}
function fmtSeg(d, val, lo, hi){
  const dispHi = (lo > 0 && hi > lo*4) ? lo*3 : hi;
  const scale = Math.max(val, dispHi) * 1.2;
  const rl = lo/scale*100, rw = Math.max((dispHi-lo)/scale*100, 0.6);
  const fw = Math.min(val/scale*100, 100);
  const st = statusOf(val, lo, hi);
  const color = st.k==="ok" ? "#37a04a" : (st.k==="bad" ? "#DA291C" : "#e8952a");
  return '<div class="row">'
    + '<div class="rname">'+CN[d]+'</div>'
    + '<div><div class="rval">'+Math.round(val)+'<em>'+UNIT[d]+'</em>'
    + '<span style="font-size:11.5px;color:#aaa;font-weight:400;margin-left:8px">建议 '
    + Math.round(lo)+'–'+Math.round(hi)+'</span></div>'
    + '<div class="track"><div class="fill" style="width:'+fw+'%;background:'+color+'"></div>'
    + '<div class="range" style="left:'+rl+'%;width:'+rw+'%"></div></div></div>'
    + '<div class="tag '+st.k+'">'+st.txt+'</div>'
    + '</div>';
}

function mealOf(){ return activeMeal(); }

const TIPS = {
  kcal: {
    over: "把饮料换成小杯或无糖款，也可以把小食留到下一餐。",
    under: "加一份小食，或把饮料换成大杯。"
  },
  protein: {
    over: "单餐蛋白过多意义有限，主食可以留一半。",
    under: "再加一份含蛋白的主食（麦满分、鸡块、鸡排），或把饮料换成牛奶/豆浆。"
  },
  fat: {
    over: "避开炸物，把配餐换成玉米杯或苹果片。",
    under: "可适量增加，通常无需特别处理。"
  },
  carb: {
    over: "把含糖饮料换成无糖可乐或茶。",
    under: "加一份玉米杯，或把饮料换成含糖款。"
  },
  sodium: {
    over: "多喝水有助于钠的代谢；下一餐尽量清淡少盐，避开腌制品、加工肉、浓汤与蘸酱。",
    under: "这一餐整体偏清淡，正常吃即可。"
  },
  calcium: {
    over: "钙略高通常无需担心。",
    under: "把饮料换成纯牛奶、奶铁或豆浆，补钙效率最高。"
  }
};

function diffDesc(c, x){
  const parts = [];
  x.picks.forEach(p => {
    const sel = $("rd" + p.idx);
    if (sel && sel.value !== p.name) parts.push(c.rounds[p.idx].label + "「" + sel.value + "」→「" + p.name + "」");
  });
  return parts.length ? parts.join(" ｜ ") : "无需调整";
}

function buildAdvice(v, t, cands, c){
  const rows = [];
  DIMS.forEach((d, i) => {
    const lo = t[d][0], hi = t[d][1];
    const st = statusOf(v[i], lo, hi);
    if (st.k === "ok") return;
    const over = st.k === "bad";
    let inMeal = "";
    if (cands && cands.length){
      const dist = x => x < lo ? lo - x : (x > hi ? x - hi : 0);
      const best = cands.reduce((a, b) => dist(b.v[i]) < dist(a.v[i]) ? b : a);
      const curDist = dist(v[i]), newDist = dist(best.v[i]);
      const delta = best.v[i] - v[i];
      if (newDist < curDist - 0.5){
        inMeal = "本餐内：" + diffDesc(c, best) + "，"
               + CN[d] + (delta > 0 ? "可提升约 " : "可降低约 ") + Math.abs(Math.round(delta)) + " " + UNIT[d]
               + (newDist === 0 ? "，可回到建议范围。" : "，但仍未达标 —— 官方替换项已到极限。");
      } else {
        inMeal = "本餐内：官方替换项已无法改善这一项。";
      }
    }
    rows.push({d: CN[d], st: st, inMeal: inMeal, tip: TIPS[d][over ? "over" : "under"]});
  });
  return rows;
}

function buildPickers(){
  const c = MODEL.combos[cur];
  const box = $("pickers");
  box.innerHTML = "";
  box.style.gridTemplateColumns = "repeat(" + c.rounds.length + ",1fr)";
  c.rounds.forEach((r, idx) => {
    const wrap = document.createElement("div");
    const lab = document.createElement("label");
    lab.textContent = r.label + (r.pool ? "（官方可替换）" : "（固定）");
    wrap.appendChild(lab);
    if (r.pool){
      const sel = document.createElement("select");
      sel.id = "rd" + idx;
      MODEL.pools[r.pool].filter(([n]) => NUT[key(n)]).forEach(([n, d]) => {
        const o = document.createElement("option");
        o.value = n;
        o.textContent = n + (d ? (d > 0 ? "（+¥" + d + "）" : "（¥" + d + "）") : "");
        if (n === r.default) o.selected = true;
        sel.appendChild(o);
      });
      if (sel.options.length && sel.selectedIndex < 0) sel.selectedIndex = 0;
      sel.onchange = render;
      wrap.appendChild(sel);
    } else {
      const f = document.createElement("div");
      f.className = "fixed";
      f.textContent = r.name;
      wrap.appendChild(f);
    }
    box.appendChild(wrap);
  });

  const hidden = [];
  c.rounds.forEach(r => {
    if (!r.pool) return;
    MODEL.pools[r.pool].forEach(([n]) => { if (!NUT[key(n)]) hidden.push(n); });
  });
  const uniq = [...new Set(hidden)];
  $("poolNote").textContent = uniq.length
    ? "✓ 全部可选项均有官方营养数据（已自动隐藏 " + uniq.length + " 项营养表未收录的餐品：" + uniq.join("、") + "）"
    : "✓ 全部可选项均有官方营养数据";
}

function currentNames(){
  const c = MODEL.combos[cur];
  return c.rounds.map((r, idx) => r.pool ? (($("rd" + idx) && $("rd" + idx).value) || r.default) : r.name);
}

function enumerate(c){
  const poolRounds = c.rounds
    .map((r, idx) => r.pool ? { idx, opts: MODEL.pools[r.pool].filter(([n]) => NUT[key(n)]) } : null)
    .filter(Boolean);
  let acc = [[]];
  poolRounds.forEach(p => {
    const next = [];
    acc.forEach(prefix => {
      p.opts.forEach(([n, d]) => next.push(prefix.concat([{ idx: p.idx, name: n, diff: d }])));
    });
    acc = next;
  });
  return acc.map(picks => {
    const names = c.rounds.map((r, idx) => {
      if (!r.pool) return r.name;
      const p = picks.find(x => x.idx === idx);
      return p ? p.name : r.default;
    });
    const v = vecOf(names);
    const diff = picks.reduce((s, p) => s + p.diff, 0);
    return { names, picks, v, diff };
  }).filter(x => x.v);
}

function render(){
  const c = MODEL.combos[cur];
  if (!c) return;
  const t = TARGETS[sex][mealOf(c)];
  const names = currentNames();
  const v = vecOf(names);

  if (!v){
    $("scoreNum").innerHTML = "--<small>分</small>";
    $("verdict").textContent = "所选组合缺少营养数据，请换一个选项。";
    $("bars").innerHTML = "";
  } else {
    const sc = scoreOf(v, t);
    $("scoreNum").innerHTML = sc.toFixed(1) + "<small>分</small>";
    const bads = [];
    DIMS.forEach((d,i)=>{
      const st = statusOf(v[i], t[d][0], t[d][1]);
      if (st.k !== "ok") bads.push(CN[d] + st.txt);
    });
    $("verdict").innerHTML = bads.length
      ? bads.map(x=>'<span class="pill bad">'+x+'</span>').join("")
      : '<span class="pill ok">六维全部达标</span>';
    $("bars").innerHTML = DIMS.map((d,i)=>fmtSeg(d, v[i], t[d][0], t[d][1])).join("");
  }

  // 处方：枚举官方全部替换组合
  const mainRound = c.rounds.find(r => !r.pool);
  const mainName = mainRound ? mainRound.name : "";
  const mainV = NUT[key(mainName)] || null;
  const cands = enumerate(c);
  cands.forEach(x => { x.sc = scoreOf(x.v, t); });
  cands.sort((a,b)=> b.sc - a.sc || a.diff - b.diff);
  const curKey = JSON.stringify(names);
  const isCur = x => JSON.stringify(x.names) === curKey;
  const shown = cands.filter(x => !isCur(x)).slice(0,3);
  const naFloor = cands.length ? Math.min(...cands.map(x => x.v[4])) : null;
  let html = "";
  if (shown.length){
    html = shown.map((x,i)=> {
      const sts = DIMS.map((d,j)=>statusOf(x.v[j], t[d][0], t[d][1]))
                     .filter(s=>s.k!=="ok").map((s,j)=>s.txt).join("、");
      return '<div class="rx'+(i===0?' best':'')+'">'
        + '<div class="head"><div class="name">'+diffDesc(c, x)+'</div>'
        + '<div class="delta">'+x.sc.toFixed(1)+' 分</div></div>'
        + '<div class="meta"><span>差价 '+(x.diff?(x.diff>0?"+¥"+x.diff:"-¥"+Math.abs(x.diff)):"不变")+'</span>'
        + '<span>钠 '+Math.round(x.v[4])+'mg</span>'
        + '<span>能量 '+Math.round(x.v[0])+'kcal</span>'
        + '<span>'+(sts||"六维全部达标")+'</span></div></div>';
    }).join("");
  }
  if (naFloor !== null && naFloor > t.sodium[1]){
    html += '<div class="na-note"><b>⚠ 即使换遍官方全部可选项，钠仍然无法达标</b>'
      + '（理论最低 '+Math.round(naFloor)+'mg，本餐上限 '+Math.round(t.sodium[1])+'mg）。<br>'
      + (mainV ? '根因：主食「'+mainName+'」本身含钠 '+Math.round(mainV[4])+'mg，占了大头 —— ' : '')
      + '可替换项的空间已经用尽。要真正解决，只能更换主食或调整全天其他餐次。</div>';
  }
  $("rx").innerHTML = html;

  // —— 改善建议 ——
  const advBox = $("advice");
  if (!v){
    advBox.innerHTML = "";
  } else {
    const rows = buildAdvice(v, t, cands, c);
    advBox.innerHTML = rows.length
      ? '<div class="adv-head">改善建议</div>'
        + '<div style="font-size:12px;color:#aaa;margin-bottom:10px">逐项说明「本餐内怎么调」与「餐外怎么补」</div>'
        + rows.map(r =>
            '<div class="adv"><div><span class="pill ' + r.st.k + '">' + r.d + ' ' + r.st.txt + '</span></div>'
            + '<div class="adv-b">' + r.inMeal + '</div>'
            + '<div class="adv-b">' + r.tip + '</div></div>').join("")
      : '<div class="adv-none">✓ 六项全部落在建议范围内，这一餐不需要特别调整。</div>';
  }
}

function rebuildCombos(){
  const want = activeMenu();
  const list = MODEL.combos.filter(c => c.meal === want);
  const cs = $("comboSel");
  cs.innerHTML = "";
  list.forEach(c => {
    const i = MODEL.combos.indexOf(c);
    const o = document.createElement("option");
    o.value = i; o.textContent = c.name + "（¥" + c.price + "）";
    cs.appendChild(o);
  });
  cur = list.length ? MODEL.combos.indexOf(list[0]) : 0;
  buildPickers();
  render();
}

function tickClock(){
  const d = serverNow();
  const p = n => String(n).padStart(2, "0");
  $("nowTime").textContent = p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds());
  $("nowMeal").textContent = MEAL_CN[activeMeal()] + (segMode === "auto" ? "（自动判定）" : "（手动选择）");
}

function applyBest(){
  const b = $("bestBtn");
  const c = MODEL.combos[cur];
  if (!c) return;
  const t = TARGETS[sex][activeMeal()];
  const cands = enumerate(c);
  cands.forEach(x => { x.sc = scoreOf(x.v, t); });
  cands.sort((a, b) => b.sc - a.sc || a.diff - b.diff);
  if (!cands.length){
    b.textContent = "无可选组合";
    setTimeout(() => { b.textContent = "一键最优"; }, 1600);
    return;
  }
  const best = cands[0];
  if (JSON.stringify(best.names) === JSON.stringify(currentNames())){
    b.textContent = "当前已是最优";
  } else {
    best.picks.forEach(p => {
      const sel = $("rd" + p.idx);
      if (sel) sel.value = p.name;
    });
    render();
    b.textContent = "✓ 已应用最优（" + best.sc.toFixed(1) + " 分）";
  }
  setTimeout(() => { b.textContent = "一键最优"; }, 1800);
}

function init(){
  $("bestBtn").onclick = applyBest;
  $("comboSel").onchange = ()=>{ cur = +$("comboSel").value; buildPickers(); render(); };
  document.querySelectorAll("#sexSeg button").forEach(b=>{
    b.onclick = ()=>{
      document.querySelectorAll("#sexSeg button").forEach(x=>x.classList.remove("on"));
      b.classList.add("on");
      sex = b.dataset.sex;
      render();
    };
  });
  document.querySelectorAll("#mealSeg button").forEach(b=>{
    b.onclick = ()=>{
      document.querySelectorAll("#mealSeg button").forEach(x=>x.classList.remove("on"));
      b.classList.add("on");
      segMode = b.dataset.meal;
      rebuildCombos();
      tickClock();
    };
  });
  rebuildCombos();
  tickClock();
  setInterval(tickClock, 1000);
}
init();
</script>
</body>
</html>
'''


def main():
    nut = {}
    with open(CSV, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            nut[r['name']] = [float(r[k]) for k in DIMS]

    model = json.load(open(MODEL, encoding='utf-8'))
    targets = build_targets()

    # 服务器时间：由麦当劳 MCP「now-time-info」取得，写入 data/server_time.json
    # 网页据此按「麦当劳服务器时钟」判断当前餐段
    stamp = BASE / 'data' / 'server_time.json'
    if stamp.exists():
        st = json.load(open(stamp, encoding='utf-8'))
        server_ts, local_ts = st['server_ts'], st['local_ts']
    else:
        server_ts = local_ts = int(time.time() * 1000)

    html = (TEMPLATE
            .replace('__NUT__', json.dumps(nut, ensure_ascii=False, separators=(',', ':')))
            .replace('__MODEL__', json.dumps(model, ensure_ascii=False, separators=(',', ':')))
            .replace('__TARGETS__', json.dumps(targets, ensure_ascii=False, separators=(',', ':')))
            .replace('__SERVER_TS__', str(server_ts))
            .replace('__LOCAL_TS__', str(local_ts)))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding='utf-8')
    print(f'已生成：{OUT}')
    print(f'文件大小：{len(html.encode("utf-8")) / 1024:.1f} KB')
    print(f'营养条目：{len(nut)} 条 ｜ 套餐：{len(model["combos"])} 个')


if __name__ == '__main__':
    main()
