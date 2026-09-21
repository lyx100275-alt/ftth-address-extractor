#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
户数统计 —— 家居配线箱图标法（贴皮线末端）

测量原理
--------
FTTH 系统图里每一户的入户端都画一个「家居配线箱」图标（图纸上可能写成
家居配线箱 / 家庭信息箱 / 多媒体箱 / **HDD** / **HD** / **H.D.D**，
也可能**什么字都不写、只是一个方块**），
并且有且只有一条「皮线图元」从竖干引到该户：皮线一端贴着这个图标（户端），
另一端对着竖干/分纤箱侧。

> 图内文字**没有统一写法**，不得写死某一种：实测小区乙写 `HDD`、小区甲写 `HD`
> （块属性 `A=家居配线箱`、`$TEXT$=HD`）。故关键词把已知变体全部列出，
> 且对纯 ASCII 缩写改用**词边界**匹配（避免 `HD` 命中 `HDMI`/`CHD` 之类）。

于是判据可以完全不看文字：

    家居配线箱图标 ≡ 落在「皮线图元端点」固定小偏移之内的候选图标

实测（小区乙项目，331 户）该偏移恒定：4.04 / 4.03 / 4.13 / 4.37 四档，331/331 命中，
不随楼栋、楼层、单元变化 —— 这是"固定小偏移"，不是模糊特征。

识别流程
--------
1. **找皮线图元**：按图层名（`--wire-layer` 显式指定，或 `--wire-keys` 关键词命中，
   默认 wire / 皮线 / fiber / 光缆 / 光纤，排除 cabletray / 桥架）取 LINE 与
   LWPOLYLINE/POLYLINE，收集其**端点**（首顶点 + 末顶点）。
2. **找候选图标**：默认取全部 INSERT 块引用；`--insert-blocks` 可收窄；
   `--include-square` 追加"小闭合方块"（4 顶点闭合多段线，宽高在给定范围内）
   以覆盖"图上只画方块、不插块"的图纸。
3. **定容差（自适应，不硬编码）**：由图纸自身量测 —— 优先用关键词命中的候选
   到最近端点的距离分布定标（取 p25），无关键词命中时退化为"最低显著峰"；
   容差 = 基准 × 1.5，钳制在 [2, 30]。
4. **判定**：
   - **A 级**：贴末端 且 文本命中关键词（家居配线箱 / HDD / …）——可直接采信
   - **B 级**：贴末端 但无任何文字 ——"只是个方块"的情形，本法与皮线标注并跑互证
   - **C 级**：有文字但**不贴末端** —— 判为**非本图区**图标（典型：楼层平面图里
     一个户型一个的示意图标），默认**不计入户数**，但全部列出供人工核对
   - 其余（无文字、不贴末端）：丢弃
5. **归层**：楼层刻度列 + 区间法（`y_i <= y < y_{i+1}` 归第 i 层），与
   SKILL.md「区间法」口径完全一致；刻度列由图纸自身识别（同一 x 处成列的楼层标注）。

适用边界（与 SKILL.md 既有裁定一致）
------------------------------------
- 只用于**楼宇系统布线图**：图上有"皮线图元"（这正是本判据的作用对象）。
- **图标必须是「每户一个」——这是本法的前置条件（2026-09-14 小区甲实测新增）**：
  有些图纸把图标画成「**每单元每层一个**」（一层多户共用 1 个图标），
  此时本法读数只等于"层×单元"而不是户数，**绝不可直接当户数交付**。
  前置条件可由图纸自身判定（开跑后先看清）：
    ① 同一 x 列上相邻图标的 Δy 是否**恒等于一个层高**
       —— 恒等于 → 每层 1 个图标（层/单元级，须再乘每层户数）；
       —— 出现约半个层高 → 每层多图标（户级，可直接计数）。
    ② 图标总数 ≈ Σ(层数×单元数) → 每层每单元一个；
       图标总数 ≈ Σ(层数×单元数×每层户数) → 每户一个。
  小区甲 5-9 实测：15 列共 356 个图标，列内 Δy 全为 15600/17550（＝层高），
  无一处例外；而 Σ(层×单元)=624、总户数 1678 —— 即图标为「每单元每层一个」，
  **该图不适用本法**（如实申报，不得硬套）。
  本脚本会在报告里自动打印**每列的「列内 Δy 众数」**，用于判读"每层几个图标"。
  （"图标数 / Σ(层×单元)"须与图签读数对照，脚本不自行推断。）
- **楼层平面图**里的同类图标**不作为户数依据**（平面图一个户型只画一个图标 = 示意
  画法，且其周边没有系统图那种皮线图元）——这类图标在 C 级里被自动分离出来，不混入户数。
- 遇 `*N` 乘数标注（如 `*16`）**不得自行相乘**：按 SKILL.md 原则二（遇到不认识的
  标注主动询问用户）列入 `待裁决_乘数标注`，含义与落层口径由用户裁决后再改数。
- 户数结论须与皮线标注口径（`count_households.py`）或 `X户` 标注**并跑互证**；
  两者不一致即暂停交用户，不得自动择一。

退出码
------
  0 = 成功
  1 = 输入 / 文件错误
  2 = 门禁拦截：一个"贴末端"的候选都没有
      → 两种情形，脚本会打印诊断区分：
        ① 皮线图层没找对 → 用 `--wire-layer` 显式指定后重跑；
        ② 本图图标不是「每户一个」（如每单元每层一个的示意画法）→ 本法不适用，
           改走图签 / 楼宇采集表口径。空结果不得当成功消费。
"""
import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
from ftth_common import (
    measure_column_step,
    HOME_BOX_STRONG_KEYS, HOME_BOX_WEAK_KEYS,
    kw_split_ascii, kw_hit,
    protect_out_path, auto_scaled,
)

import ezdxf
import os

sys.stdout.reconfigure(encoding="utf-8")

# 内置统一楼层解析（与 ftth.py / count_households.py 一致：支持 3F / -1F / B1 / WF）
FLOOR_RE = re.compile(r"^(B\d+|WF|W\d+F|F\d+|夹层|屋面|屋顶层|-?\d+F)$")

# 家居配线箱关键词（强 = 明确指向户内配线箱；弱 = 行业缩写，可能被别的设备复用）。
# **唯一真源在 ftth_common**：本脚本与 plan_methods.py（信号判定）共用同一份，不得各留副本。
# 缩写**不写死某一种写法**：同一设备的图内文字随画图人而变 —— 实测一张图写 `HDD`、
# 另一张写 `HD`（块属性 A=家居配线箱、$TEXT$=HD）。故已知变体全列，且纯 ASCII 缩写
# 按**词边界**匹配（`HD` 绝不能当子串匹配，否则会命中 `HDMI` / `CHD` / `SHD` 之类无关文字）。
STRONG_KEYS = HOME_BOX_STRONG_KEYS
WEAK_KEYS = HOME_BOX_WEAK_KEYS

DEFAULT_WIRE_KEYS = ("wire", "皮线", "fiber", "光缆", "光纤")
DEFAULT_WIRE_EXCLUDE = ("cabletray", "cable_tray", "桥架", "槽", "支架")
# 乘数标注：*16 / * 16 / x16
MULT_RE = re.compile(r"^[\*xX]\s*(\d{1,3})$")


def log(*a):
    print(*a)


# ---------------------------------------------------------------- 关键词匹配
# 关键词命中工具的唯一真源在 ftth_common（与 plan_methods.py 共用同一份实现），此处仅留别名。
_kw_split = kw_split_ascii
key_hit = kw_hit


def dy_mode(ys):
    """一段（同一 x 带、同一 y 连续段）内相邻图标的 Δy 众数 + 占比。

    用于判读「每层几个图标」：Δy 恒等于一个层高 → 每层 1 个（层/单元级）；
    出现约半个层高 → 每层多图标（户级）。返回 (众数, 占比) 或 (None, 0)。
    """
    ys = sorted(ys)
    if len(ys) < 2:
        return None, 0.0
    dys = [round(ys[i + 1] - ys[i], 1) for i in range(len(ys) - 1)]
    dys = [d for d in dys if d > 0]
    if not dys:
        return None, 0.0
    mode, n = Counter(dys).most_common(1)[0]
    return mode, n / len(dys)


# ---------------------------------------------------------------- 网格索引
class Grid:
    """按格子分桶的最近点查询（候选数量 × 端点数可达千万级，必须走索引）。"""

    def __init__(self, pts, cell=40.0):
        self.cell = cell
        self.pts = pts
        self.g = defaultdict(list)
        for i, (x, y) in enumerate(pts):
            self.g[(int(math.floor(x / cell)), int(math.floor(y / cell)))].append(i)

    def nearest(self, x, y, radius):
        """返回半径内的最近点 (idx, dist)；半径内无点返回 (-1, None)。"""
        c = self.cell
        r = int(math.ceil(radius / c))
        cx, cy = int(math.floor(x / c)), int(math.floor(y / c))
        best, bd = -1, None
        for gx in range(cx - r, cx + r + 1):
            for gy in range(cy - r, cy + r + 1):
                for i in self.g.get((gx, gy), ()):
                    px, py = self.pts[i]
                    d = math.hypot(px - x, py - y)
                    if bd is None or d < bd:
                        bd, best = d, i
        if bd is not None and bd <= radius:
            return best, bd
        return -1, None


# ---------------------------------------------------------------- 采集
def collect(dxf_path, wire_layers, wire_keys, wire_exclude, insert_blocks):
    # 走 ftth_common.load_dxf 的磁盘缓存。本函数需要**多段线整组顶点**与 **INSERT 属性**，
    # 这两样几何缓存(<DXF>.geom.json)不承载，故此处用 pkl 缓存而非 load_geom。
    from ftth_common import load_dxf
    doc, msp = load_dxf(dxf_path)

    wl = {l.strip() for l in (wire_layers or []) if l.strip()}
    kl = [k.strip().lower() for k in (wire_keys or []) if k.strip()]
    el = [k.strip().lower() for k in (wire_exclude or []) if k.strip()]
    bl = {b.strip() for b in (insert_blocks or []) if b.strip()}

    def is_wire(layer):
        l = (layer or "").lower()
        if wl:
            return layer in wl
        if any(k in l for k in el):
            return False
        return any(k in l for k in kl)

    wires, polys, inserts, texts = [], [], [], []
    for e in msp:
        t = e.dxftype()
        lay = e.dxf.layer
        if t == "LINE":
            pts = [(float(e.dxf.start[0]), float(e.dxf.start[1])),
                   (float(e.dxf.end[0]), float(e.dxf.end[1]))]
            polys.append((lay, pts, False))
        elif t in ("LWPOLYLINE", "POLYLINE"):
            try:
                if t == "LWPOLYLINE":
                    pts = [(float(p[0]), float(p[1])) for p in e.get_points()]
                    closed = bool(e.closed)
                else:
                    pts = [(float(v.dxf.location[0]), float(v.dxf.location[1]))
                           for v in e.vertices]
                    closed = bool(e.is_closed)
            except Exception:
                continue
            if len(pts) >= 2:
                polys.append((lay, pts, closed))
        elif t == "INSERT":
            if bl and e.dxf.name not in bl:
                continue
            atts = [(a.dxf.tag or "", a.dxf.text or "") for a in e.attribs]
            inserts.append({
                "块名": e.dxf.name, "图层": lay,
                "x": round(e.dxf.insert.x, 4), "y": round(e.dxf.insert.y, 4),
                "属性": atts,
            })
        elif t in ("TEXT", "MTEXT"):
            s = e.dxf.text if t == "TEXT" else e.text
            if s:
                texts.append((lay, s.replace("\n", " ").strip(),
                              float(e.dxf.insert[0]), float(e.dxf.insert[1])))

    for lay, pts, closed in polys:
        if is_wire(lay):
            wires.append({"图层": lay, "首": (round(pts[0][0], 4), round(pts[0][1], 4)),
                          "末": (round(pts[-1][0], 4), round(pts[-1][1], 4)),
                          "顶点数": len(pts)})
    return {"wires": wires, "polys": polys, "inserts": inserts, "texts": texts,
            "wire_layers_used": sorted({w["图层"] for w in wires})}


# ---------------------------------------------------------------- 楼层刻度
def floor_scales(texts, floor_layer=None, min_floors=3):
    """识别楼层刻度列：同一 x（容差 0.2）上成列的楼层标注。

    不写死图层：优先用 `--floor-layer`；否则**逐图层试成列**，取"有效刻度列最多"
    的图层（平面图里零散的楼层文字成不了列，自然落选）。
    返回 (scales, 图层名)。
    """
    cand = defaultdict(list)
    for lay, s, x, y in texts:
        if floor_layer and lay != floor_layer:
            continue
        if FLOOR_RE.match(s):
            cand[lay].append((x, y, s))
    if not cand:
        return [], None

    best_layer, best_scales, best_key = None, [], (-1, -1)
    for lay, rows in cand.items():
        sc = _scales_from_rows(rows, min_floors)
        key = (len(sc), len(rows))
        if key > best_key:
            best_layer, best_scales, best_key = lay, sc, key
    return best_scales, best_layer


def _scales_from_rows(rows, min_floors=3):
    """把某图层的楼层文字按 x 聚成刻度列。"""
    gx = defaultdict(list)
    for x, y, s in rows:
        gx[round(x, 1)].append((y, s))
    scales = []
    for x in sorted(gx):
        v = sorted(gx[x])
        if len(v) < min_floors:
            continue
        scales.append({"x": x, "ys": [p[0] for p in v], "names": [p[1] for p in v],
                       "y0": v[0][0], "y1": v[-1][0]})
    # 合并相邻近的刻度列（同一列的 x 可能因圆整差 0.1~0.3）。
    # 2026-09-19（实测某图）：**必须同时要求 y 区间重叠**。图上「上下两个图区的
    #   刻度列」x 可能几乎相同（实测仅差 0.7），只按 x 合并会把标注少的那条吞掉，
    #   该图区此后**再无可用刻度列** —— 其图标列被迫配到邻图区的列，且因为 y 范围
    #   不覆盖而**整列未归属**（实测丢 8 户，且 rc 仍为 0，属静默错）。
    #   判据：同 x 候选若楼层 y 区间不重叠 = 两个图区的独立列，各自保留。
    merged = []
    for s in sorted(scales, key=lambda z: z["x"]):
        if merged and s["x"] - merged[-1]["x"] <= 1.0:
            _m = merged[-1]
            _ov = min(s["y1"], _m["y1"]) - max(s["y0"], _m["y0"])
            if _ov <= 0:
                merged.append(s)
            elif len(s["names"]) > len(_m["names"]):
                merged[-1] = s
        else:
            merged.append(s)
    return merged


def band_of(sc, y):
    for i in range(len(sc["ys"]) - 1):
        if sc["ys"][i] <= y < sc["ys"][i + 1]:
            return sc["names"][i]
    return None


def _pitch_of(scales):
    """由楼层刻度列估计**层高**（本图坐标尺度的锚）。
    各刻度列内相邻层 y 差取全局中位数；刻度列缺失返回 None。
    用途：凡语义为『约 N 个层高 / 行距 / 图标尺寸』的阈值都必须由它推导，
    不得写死绝对坐标值——图纸坐标系尺度因项目而异（同为层高的 y 差可差两个数量级）。
    """
    gaps = []
    for s in scales:
        ys = sorted(set(s["ys"]))
        gaps += [b - a for a, b in zip(ys, ys[1:]) if b - a > 0]
    if not gaps:
        return None
    gaps.sort()
    return gaps[len(gaps) // 2]


# ---------------------------------------------------------------- 尺度自适应默认值
# 通用化判据（见 SKILL.md）：**凡是随图纸坐标尺度变化的几何阈值，都必须是无量纲比值
# × 图纸自身尺度**；写成绝对数值（80 / 150 / 40）就只对标定它的那一张图成立。
AUTO_RATIOS = {
    # 名称            比值        语义
    "search_radius": 8 / 3,      # 最近端点搜索半径 ≈ 2.67 层高（须大于贴合容差）
    "region_pad":    5.0,        # 图区 y 余量 = 上下各留 5 个层高
    "col_x_tol":     1 / 30,     # 同一物理列的 x 抖动 ≈ 1/30 层高
    "col_gap":       4 / 3,      # y 断口阈值 ≈ 一个层高（留 33% 余量）
    "square_min":    1 / 15,     # 方块候选最小边（滤掉碎屑图元）
    "square_max":    2.0,        # 方块候选最大边 ≈ 2 层高（滤掉大轮廓/机架）
    "grid_cell":     4 / 3,      # 空间索引格边长 ≈ 1.33 层高
    "tol_bucket":    1 / 60,     # 距离直方图桶宽 ≈ 层高/60
    "tol_scan_max":  20 / 3,     # 距离直方图扫描上限 ≈ 6.67 层高
    "tol_cap":       1.0,        # 贴合容差上限 = 一个层高
}
# 图纸量不出层高时的兜底（无楼层刻度列 / 极简图）。仅供无法定标时使用，
# 且日志会显式标注"未定标"，避免被当成"已按图纸刻度校准"。
AUTO_FALLBACK = {"search_radius": 80.0, "region_pad": 150.0, "col_x_tol": 1.0,
                 "col_gap": 40.0, "square_min": 2.0, "square_max": 60.0,
                 "grid_cell": 40.0, "tol_bucket": 0.5, "tol_scan_max": 200.0,
                 "tol_cap": 30.0}


# auto_scaled 已上收 ftth_common（2026-09-19 八十九）：与 analyze_coverage.py 原先各存一份
# 逐字相同的实现。比率表仍用本模块的 AUTO_RATIOS / AUTO_FALLBACK，调用处关键字传入。


# ---------------------------------------------------------------- 容差自适应
def estimate_tol(dists, ratio=0.04, min_peak=3, bucket=0.5, scan_max=200.0,
                 tol_cap=30.0):
    """由图纸自身量测贴合容差 —— 在距离直方图里找**最低的显著峰**。

    「贴皮线末端」的图标会在某个固定小距离上堆成一个尖峰（实测某图 4.0 处 331 个），
    而不贴的图标距离是散开的。故取"从头开始第一个 count 达标的桶"作基准，
    容差 = 基准 × 1.5，钳制在 [bucket, tol_cap]。

    传入的建议是**关键词命中的种子候选**的距离（高置信）；无种子时退化用全部候选，
    此时把 min_peak 抬高，避免把噪声当峰。

    scan_max / tol_cap 由调用方按图纸层高自适应传入（大尺度坐标系下贴合距离
    会同比例放大，固定 200/30 会让定标静默失败）。

    返回 (tol, 依据说明)；无法定标返回 (None, 原因)。
    """
    ds = sorted(d for d in dists if d is not None and d <= scan_max)
    if not ds:
        return None, "无候选或全部候选都超出扫描范围"
    hist = Counter(round(d / bucket) * bucket for d in ds)
    need = max(min_peak, int(len(ds) * ratio))
    for k in sorted(hist):
        if hist[k] >= need:
            base = k if k > 0 else bucket
            tol = max(bucket, min(base * 1.5, tol_cap))
            return tol, ("最低显著峰 %.1f（count=%d，阈值=%d，N=%d）→ 容差 = 峰×1.5 = %.2f"
                         % (k, hist[k], need, len(ds), tol))
    return None, "距离直方图无显著峰（N=%d，阈值=%d）" % (len(ds), need)


# ---------------------------------------------------------------- 门禁诊断
def diagnose_no_bond(cands, search_radius):
    """打印「候选与皮线不相邻」的诊断（2026-09-14 小区甲实测新增，两个门禁共用）。

    本法的判据是**几何**（图标贴皮线末端）。当图上有图标、也有关键词命中，
    但两者就是不相邻时，必须能区分两种根因，否则会误判成"参数没调对"而反复空跑：
      ① 皮线图层没找对（换 --wire-layer 即可解决）；
      ② 本图图标根本不是「每户一个」，而是「每单元每层一个」的示意画法
         （小区甲即此类：图标配 `x2`/`x3` 乘数标注，且图上无皮线图元）。
    """
    kw = [c for c in cands if (c["强命中"] or c["弱命中"] or c["块名命中"])]
    if not kw:
        log("[诊断] 全图没有任何候选命中关键词（家居配线箱 / HD / HDD / …）——")
        log("[诊断] 先确认图标的图内文字是什么，或用 --strong-keys / --weak-keys 补关键词。")
        return
    ds = sorted(c["d"] for c in kw if c["d"] is not None)
    log("[诊断] 图上确有 %d 个候选命中关键词（家居配线箱 / HD / HDD / …）。" % len(kw))
    if ds:
        log("[诊断] 它们到最近皮线端点的距离：最小 %.1f，中位数 %.1f"
            % (ds[0], ds[len(ds) // 2]))
        log("[诊断] → 关键词与皮线**都找到了，但两者不相邻**。")
    else:
        log("[诊断] 它们在搜索半径 %.0f 内**没有任何皮线端点**"
            % search_radius)
        log("[诊断] → 本图多半**根本没有入户皮线图元**。")
    log("[诊断] 两种可能，必须判清后再决定口径（不得硬凑）：")
    log("        ① 皮线图层没找对 —— 用 --wire-layer 显式指定后重跑；")
    log("        ② 本图图标是「每单元每层一个」的**示意画法**（常配 `x2`/`x3` 乘数标注")
    log("           表明该点代表几户）→ 不是「每户一个」，**本法不适用**，应改走图签")
    log("           （`read_titleblock_households.py`）/楼宇采集表口径，如实申报。")
    log("           判据：同一 x 列内相邻图标的 Δy 是否恒等于一个层高；")
    log("                 图标总数是否 ≈ Σ(层数×单元数) 而非 Σ(层数×单元数×每层户数)。")


# ---------------------------------------------------------------- 主流程
def _nearest(seq, val, key):
    """返回 (最近元素, 距离)；seq 为空时返回 (None, None)。"""
    best, bd = None, None
    for it in seq:
        d = abs(key(it) - val)
        if bd is None or d < bd:
            best, bd = it, d
    return best, bd


def mode_base(dxs):
    """主偏移 = **最大显著簇**的中心（簇 = 相邻值相对差 ≤10%；显著 = 成员 ≥2）。

    为什么不用中位数：本法的合法偏移是「本栋刻度列 → 本栋第 k 个图标列」的距离
    = k × 单元间距，天然是一条**离散的整数谱**。中位数隐含「全体列偏移同分布」
    假设，当某图「第 2 单元列」占多数时中位数会落到 2× 间距上，合法的 1× 列
    反被判异常（反之亦然）；取"最小簇"又会被少数真错配值凑成的小簇带偏。
    取**最大簇** = 出现次数最多的那个 k，是本形态下唯一稳定的基准。
    """
    if not dxs:
        return None
    s = sorted(dxs)
    clusters = [[s[0]]]
    for v in s[1:]:
        if abs(v - clusters[-1][-1]) <= 0.10 * clusters[-1][-1]:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    sig = [c for c in clusters if len(c) >= 2]
    big = max(sig if sig else clusters, key=len)
    return sum(big) / len(big)


def period_dev(dx, base):
    """dx 相对 base 的**整数倍偏离率**。返回 (k, dev)。

    dx ≥ base：按 dx ≈ k·base 取最近整数 k；dx < base：按 base ≈ k·dx。
    dev = 相对偏差（0 表示恰为整数倍）。合法配对恒为整数倍；偏离整数谱
    ⇒ 配到了别栋/别图区的刻度列。
    """
    if not base or not dx or dx <= 0:
        return None, None
    if dx >= base:
        k = max(1, int(round(dx / base)))
        return k, abs(dx - k * base) / (k * base)
    k = max(1, int(round(base / dx)))
    return k, abs(base - k * dx) / (k * dx)


def parse_col_scale_map(spec, scales, col_list, tol, log):
    """解析 --col-scale-map "列x=刻度列x;列x=刻度列x;..."，返回 {列x(1位小数): 刻度列对象}。

    为什么需要它：pick_scale 用「y 覆盖 + x 最近」自动挑刻度列，遇到**一条刻度列服务
    多个图标列**的图纸会整列错位，而且**零告警**（y 覆盖判据看不出这种错）。人工核对
    出正确归属后，必须有一条通道把裁决喂回脚本，而不是每次自造一批脚本重算。

    容错与底线：两侧 x 都按最近匹配（人工从 JSON 抄来的值常有零点几的误差），但
    **匹配不上就报错并列全部候选**——静默忽略会让调用方误以为映射已生效。
    """
    m = {}
    for part in re.split(r"[;,]", spec or ""):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            log("[错误] --col-scale-map 片段 %r 缺少 '='，正确格式：列x=刻度列x" % part)
            sys.exit(2)
        a, b = part.split("=", 1)
        try:
            ax, bx = float(a), float(b)
        except ValueError:
            log("[错误] --col-scale-map 片段 %r 的 x 值不是数字" % part)
            sys.exit(2)
        col, dcol = _nearest(col_list, ax, lambda c: c["列x"])
        sc, dsc = _nearest(scales, bx, lambda s: s["x"])
        if col is None or dcol is None or dcol > tol:
            log("[错误] --col-scale-map：图上没有 x≈%.1f 的图标列（最近差 %.1f > 容差 %.1f）"
                % (ax, dcol if dcol is not None else -1, tol))
            log("       现有图标列 x：%s" % ", ".join("%.1f" % c["列x"] for c in col_list))
            sys.exit(2)
        if sc is None or dsc is None or dsc > tol:
            log("[错误] --col-scale-map：图上没有 x≈%.1f 的刻度列（最近差 %.1f > 容差 %.1f）"
                % (bx, dsc if dsc is not None else -1, tol))
            log("       现有刻度列 x：%s" % ", ".join("%.1f" % s["x"] for s in scales))
            sys.exit(2)
        m[round(col["列x"], 1)] = sc
    return m


def main():
    ap = argparse.ArgumentParser(description="家居配线箱图标法（贴皮线末端）户数统计")
    ap.add_argument("dxf", help="输入 DXF 路径")
    ap.add_argument("out", nargs="?", help="输出 JSON 路径")
    # 皮线图元
    ap.add_argument("--wire-layer", default=None, help="皮线/连线图层名，逗号分隔（显式指定，优先）")
    ap.add_argument("--wire-keys", default=None, help="皮线图层关键词，逗号分隔（默认 %s）"
                                                   % ",".join(DEFAULT_WIRE_KEYS))
    ap.add_argument("--wire-exclude", default=None, help="排除的图层关键词，逗号分隔（默认 %s）"
                                                        % ",".join(DEFAULT_WIRE_EXCLUDE))
    # 候选图标
    ap.add_argument("--insert-blocks", default=None, help="限定 INSERT 块名，逗号分隔（默认全部）")
    ap.add_argument("--include-square", action="store_true",
                    help="追加『小闭合方块』为候选（覆盖「只画方块不插块」的图纸）")
    ap.add_argument("--square-min", type=float, default=0.0,
                    help="方块最小边（0=按 %g 倍层高自适应）" % AUTO_RATIOS["square_min"])
    ap.add_argument("--square-max", type=float, default=0.0,
                    help="方块最大边（0=按 %g 倍层高自适应）" % AUTO_RATIOS["square_max"])
    # 容差
    ap.add_argument("--tol", type=float, default=None, help="贴合容差（默认自适应量测）")
    ap.add_argument("--search-radius", type=float, default=0.0,
                    help="最近端点搜索半径（0=按 %g 倍层高自适应，须大于容差）"
                         % AUTO_RATIOS["search_radius"])
    # 关键词
    ap.add_argument("--strong-keys", default=None, help="强关键词，逗号分隔")
    ap.add_argument("--weak-keys", default=None, help="弱关键词，逗号分隔")
    # 归层
    ap.add_argument("--floor-layer", default=None, help="楼层标注图层（默认自动识别）")
    ap.add_argument("--scale-max-dx", type=float, default=None,
                    help="图标列到刻度列的最大 x 距离（默认自适应 p90×1.3）")
    ap.add_argument("--scale-period-tol", dest="scale_period_tol", type=float, default=0.07,
                    help="刻度列**配对偏移异常**判据（0=关闭）：某列偏移与主偏移（最大簇中心）"
                         "不成整数倍、且相对偏离 > 本值时标记异常。合法偏移 = k × 单元间距，"
                         "天然呈整数谱；偏离即说明配到了别栋/别图区的刻度列。")
    ap.add_argument("--scale-outlier-ratio", type=float, default=None,
                    help="[已弃用] 旧判据（偏移 > 中位数 × 本值）。中位数隐含「全体列偏移"
                         "同分布」假设，在「一条刻度列服务本栋多个图标列」形态下会同时"
                         "误报与漏报；**传了也不参与判定**，仅为兼容旧命令行保留。")
    ap.add_argument("--region-y", default=None,
                    help="显式限定图区 y 范围 min,max（默认由楼层刻度列界定）")
    ap.add_argument("--region-pad", type=float, default=0.0,
                    help="图区 y 方向余量（0=按 %g 倍层高自适应）" % AUTO_RATIOS["region_pad"])
    ap.add_argument("--col-x-tol", type=float, default=0.0,
                    help="同一物理列的 x 聚类容差（0=按 %g 倍层高自适应；"
                         "块对齐差异会让 x 抖动）" % AUTO_RATIOS["col_x_tol"])
    ap.add_argument("--col-gap", type=float, default=0.0,
                    help="同一 x 带上不同图区的 y 断口阈值（0=按 %g 倍层高自适应，"
                         "约一个层高）" % AUTO_RATIOS["col_gap"])
    ap.add_argument("--col-scale-map", dest="col_scale_map", default=None,
                    help="显式指定「图标列 x → 刻度列 x」，格式 \"列x=刻度列x;...\"（分号或逗号分隔）。"
                         "用于『一条刻度列服务多个图标列』的图纸——该形态下几何最近配对"
                         "会把整列配到邻栋/邻图区且零告警。")
    ap.add_argument("--force", action="store_true",
                    help="允许覆盖已存在的输出产物（默认改道 <原名>_patched.json，写保护）")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    wire_keys = args.wire_keys.split(",") if args.wire_keys else list(DEFAULT_WIRE_KEYS)
    wire_excl = args.wire_exclude.split(",") if args.wire_exclude else list(DEFAULT_WIRE_EXCLUDE)
    wire_layers = args.wire_layer.split(",") if args.wire_layer else None
    strong = tuple(args.strong_keys.split(",")) if args.strong_keys else STRONG_KEYS
    weak = tuple(args.weak_keys.split(",")) if args.weak_keys else WEAK_KEYS
    # 强/弱关键词各拆成「中文子串」+「ASCII 缩写词边界」两路
    strong_sub, strong_pat = _kw_split(strong)
    weak_sub, weak_pat = _kw_split(weak)

    try:
        data = collect(args.dxf, wire_layers, wire_keys, wire_excl,
                       args.insert_blocks.split(",") if args.insert_blocks else None)
    except Exception as e:
        log("[ERROR] 读取 DXF 失败：%s" % e)
        sys.exit(1)

    wires, polys, inserts, texts = (data["wires"], data["polys"],
                                    data["inserts"], data["texts"])
    log("=" * 74)
    log("家居配线箱图标法（贴皮线末端） —— 户数统计")
    log("=" * 74)
    log("皮线图元 = %d（顶点数>2 的折线按整条计）｜图层 = %s"
        % (len(wires), data["wire_layers_used"]))
    log("候选 INSERT = %d ｜ 全图多段线 = %d ｜ 全图文字 = %d"
        % (len(inserts), len(polys), len(texts)))

    if not wires:
        log("")
        log("!" * 74)
        log("[门禁] 已中止：没找到任何『皮线图元』—— 层名关键词 %s 无一命中。" % wire_keys)
        log("[门禁] 处置：用 --wire-layer 显式指定连线图层名后重跑（空结果不得当成功消费）。")
        log("!" * 74)
        sys.exit(2)

    # ---- 楼层刻度列（提前算：既用于归层，也用于界定系统图区） ----
    scales, floor_layer = floor_scales(texts, args.floor_layer)
    log("楼层刻度列 = %d 个（图层 = %s）" % (len(scales), floor_layer))

    # ---- 图纸尺度锚：层高（此后所有几何阈值的单位） ----
    # 阈值写成绝对数值（80/150/40）只对标定它的那张图成立，故统一按层高倍数还原。
    step, step_why = measure_column_step([s["ys"] for s in scales]) if scales \
        else (None, "无楼层刻度列")
    _AUTO_KEYS = ("search_radius", "region_pad", "col_x_tol", "col_gap",
                  "square_min", "square_max")
    if step:
        for _k in _AUTO_KEYS:
            if not getattr(args, _k, None) or getattr(args, _k) <= 0:
                setattr(args, _k, auto_scaled(step, _k, ratios=AUTO_RATIOS, fallback=AUTO_FALLBACK))
        log("图纸尺度锚：层高 = %.6g（%s）→ 阈值按层高倍数还原：%s"
            % (step, step_why, "、".join("%s=%.6g" % (k, getattr(args, k))
                                         for k in _AUTO_KEYS)))
    else:
        for _k in _AUTO_KEYS:
            if not getattr(args, _k, None) or getattr(args, _k) <= 0:
                setattr(args, _k, AUTO_FALLBACK[_k])
        log("图纸尺度锚：**未定标**（%s）→ 阈值取兜底值（%s），结果须人工复核"
            % (step_why, "、".join("%s=%.6g" % (k, AUTO_FALLBACK[k])
                                   for k in _AUTO_KEYS)))

    if args.region_y:
        ry0, ry1 = [float(v) for v in args.region_y.split(",")]
        region_why = "命令行显式指定"
    elif scales:
        ry0 = min(s["y0"] for s in scales) - args.region_pad
        ry1 = max(s["y1"] for s in scales) + args.region_pad
        region_why = "由楼层刻度列 y 范围 ± %.0f 界定" % args.region_pad
    else:
        ry0 = ry1 = None
        region_why = "无楼层刻度列，未做图区过滤（须自行确认候选图区）"
    log("图区 y 范围 = %s（%s）"
        % (("[%.1f, %.1f]" % (ry0, ry1)) if ry0 is not None else "未限定", region_why))

    def in_region(y):
        return True if ry0 is None else (ry0 <= y <= ry1)

    # ---- 皮线端点（只取图区内的：平面图的线管走线不属系统图皮线） ----
    ends_all = []
    for w in wires:
        ends_all.append(w["首"])
        ends_all.append(w["末"])
    ends_region = [p for p in ends_all if in_region(p[1])]
    end_uq = sorted(set(ends_region))
    log("皮线端点 = %d（全图去重 %d；图区内去重 %d）"
        % (len(ends_all), len(set(ends_all)), len(end_uq)))

    if not end_uq:
        log("")
        log("!" * 74)
        log("[门禁] 已中止：图区内没有任何皮线端点 → 图区范围或皮线图层判定有误。")
        log("[门禁] 处置：用 --wire-layer / --region-y 修正后重跑。")
        log("!" * 74)
        sys.exit(2)

    # ---- 候选图标 ----
    cands = []
    for it in inserts:
        attrs = " ".join(t for _, t in it["属性"])
        cands.append({"来源": "INSERT", "块名": it["块名"], "图层": it["图层"],
                      "x": it["x"], "y": it["y"], "文本": attrs})
    if args.include_square:
        n_sq = 0
        for lay, pts, closed in polys:
            if not closed or len(pts) != 4:
                continue
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            w, h = max(xs) - min(xs), max(ys) - min(ys)
            if not (args.square_min <= w <= args.square_max
                    and args.square_min <= h <= args.square_max):
                continue
            if w < 1e-9 or h < 1e-9 or max(w / h, h / w) > 3.0:
                continue
            cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
            cands.append({"来源": "SQUARE", "块名": "", "图层": lay,
                          "x": round(cx, 4), "y": round(cy, 4), "文本": ""})
            n_sq += 1
        log("追加小闭合方块候选 = %d" % n_sq)

    # ---- 每个候选到最近皮线端点的距离 ----
    g = Grid(end_uq, cell=auto_scaled(step, "grid_cell", ratios=AUTO_RATIOS, fallback=AUTO_FALLBACK))
    for c in cands:
        idx, d = g.nearest(c["x"], c["y"], args.search_radius)
        c["端点"] = list(end_uq[idx]) if idx >= 0 else None
        c["d"] = round(d, 3) if d is not None else None
        c["在图区"] = in_region(c["y"])
        c["强命中"] = key_hit(c["文本"], strong_sub, strong_pat)
        c["弱命中"] = key_hit(c["文本"], weak_sub, weak_pat)
        c["块名命中"] = (key_hit(c["块名"], strong_sub, strong_pat)
                      or key_hit(c["块名"], weak_sub, weak_pat))

    # ---- 容差（自适应量测） ----
    seed_d = [c["d"] for c in cands
              if (c["强命中"] or c["弱命中"] or c["块名命中"])
              and c["d"] is not None and c["在图区"]]
    all_d = [c["d"] for c in cands if c["d"] is not None]
    if args.tol is not None:
        tol, tol_why = args.tol, "命令行显式指定"
    elif len(seed_d) >= 3:
        tol, tol_why = estimate_tol(
            seed_d, bucket=auto_scaled(step, "tol_bucket", ratios=AUTO_RATIOS, fallback=AUTO_FALLBACK),
            scan_max=auto_scaled(step, "tol_scan_max", ratios=AUTO_RATIOS, fallback=AUTO_FALLBACK),
            tol_cap=auto_scaled(step, "tol_cap", ratios=AUTO_RATIOS, fallback=AUTO_FALLBACK))
        tol_why = "种子候选（关键词命中，n=%d）" % len(seed_d) + tol_why
    else:
        tol, tol_why = estimate_tol(
            all_d, ratio=0.05, min_peak=5,
            bucket=auto_scaled(step, "tol_bucket", ratios=AUTO_RATIOS, fallback=AUTO_FALLBACK),
            scan_max=auto_scaled(step, "tol_scan_max", ratios=AUTO_RATIOS, fallback=AUTO_FALLBACK),
            tol_cap=auto_scaled(step, "tol_cap", ratios=AUTO_RATIOS, fallback=AUTO_FALLBACK))
        tol_why = "全部候选（无关键词种子）" + (tol_why or "")
    if tol is None:
        log("")
        log("!" * 74)
        log("[门禁] 已中止：无法从图纸自身量测贴合容差（%s）。" % tol_why)
        diagnose_no_bond(cands, args.search_radius)
        log("[门禁] 处置：用 --tol / --wire-layer 修正后重跑；空结果不得当成功消费。")
        log("!" * 74)
        sys.exit(2)
    log("贴合容差 = %.2f（%s）｜种子候选 = %d"
        % (tol, tol_why, len(seed_d)))

    # ---- 判定分级 ----
    for c in cands:
        near = c["d"] is not None and c["d"] <= tol
        txt = c["强命中"] or c["弱命中"] or c["块名命中"]
        c["贴末端"] = near
        c["有文本"] = txt
        if near and c["在图区"] and txt:
            c["级别"] = "A"
        elif near and c["在图区"] and not txt:
            c["级别"] = "B"
        elif txt:
            c["级别"] = "C"
        else:
            c["级别"] = "-"

    lv = Counter(c["级别"] for c in cands)
    log("分级：A（图区内+贴末端+文字）= %d ｜ B（图区内+贴末端无文字）= %d ｜ "
        "C（有文字但未计入：不在图区或不贴末端）= %d ｜ 丢弃 = %d"
        % (lv.get("A", 0), lv.get("B", 0), lv.get("C", 0), lv.get("-", 0)))

    hit = [c for c in cands if c["贴末端"] and c["在图区"]]
    if not hit:
        log("")
        log("!" * 74)
        log("[门禁] 已中止：一个『贴皮线末端』的候选都没有。")
        diagnose_no_bond(cands, args.search_radius)
        log("[门禁] 处置：用 --wire-layer / --region-y 修正后重跑；空结果不得当成功消费。")
        log("!" * 74)
        sys.exit(2)

    # ---- 同一端点被多个候选共用：告警 ----
    per_end = defaultdict(list)
    for c in hit:
        per_end[tuple(c["端点"])].append(c)
    dup_end = {k: v for k, v in per_end.items() if len(v) > 1}

    # ---- 归层：物理列 = 先按 x 聚类，再按 y 断口切 run ----
    # 同一物理列的图标 x 会有 0.1~0.5 的抖动（块对齐方式不同），必须按容差聚合；
    # 共享图纸的上下两行图区在同一 x 带上各有一列，必须靠 y 断口分开。
    groups = []
    for c in sorted(hit, key=lambda z: (z["x"], z["y"])):
        if groups and c["x"] - groups[-1]["xs"][-1] <= args.col_x_tol:
            groups[-1]["xs"].append(c["x"])
            groups[-1]["items"].append(c)
        else:
            groups.append({"xs": [c["x"]], "items": [c]})
    col_list = []
    for gp in groups:
        v = sorted(gp["items"], key=lambda z: z["y"])
        runs, cur = [], [v[0]]
        for c in v[1:]:
            if c["y"] - cur[-1]["y"] <= args.col_gap:
                cur.append(c)
            else:
                runs.append(cur)
                cur = [c]
        runs.append(cur)
        for run in runs:
            xs_r = [c["x"] for c in run]
            mode, share = dy_mode([c["y"] for c in run])
            col_list.append({"列x": round(sum(xs_r) / len(xs_r), 1),
                             "x范围": [min(xs_r), max(xs_r)], "图标": run,
                             "Δy众数": mode, "Δy占比": round(share, 3)})
    col_list.sort(key=lambda z: z["列x"])
    log("物理列 = %d 个（x 聚类容差 %.1f，y 断口 %.0f）"
        % (len(col_list), args.col_x_tol, args.col_gap))

    # ---- 显式「图标列 → 刻度列」映射（2026-09-18 落地，复盘建议 1）----
    col_scale_map = {}
    if getattr(args, "col_scale_map", None):
        _tol = max(5.0, args.col_x_tol or 0.0)
        col_scale_map = parse_col_scale_map(args.col_scale_map, scales, col_list, _tol, log)
        log("显式列→刻度列映射 = %d 条（优先于几何最近配对，x 匹配容差 %.1f）"
            % (len(col_scale_map), _tol))
        for _k in sorted(col_scale_map):
            log("    列 x=%-11.1f  ->  刻度列 x=%.1f" % (_k, col_scale_map[_k]["x"]))

    def pick_scale(x, y0, y1, _fb=None):
        """挑刻度列：优先① 人工显式映射（--col-scale-map）；否则② y 范围完全覆盖；
        再③ y 重叠最大的那批；同批里取 x 最近。全程只看 y 覆盖是否够、不看偏移大小
        （区间法只用 y）——这正是它在「共用刻度列」图纸上会静默错配的根源。
        2026-09-20：无完全覆盖列而走 ③/兜底时，若传入 _fb 列表则记入
        (列x, y0, y1)，由调用方统一打印——只加可见性，不改挑列结果
        （真错配仍由偏移异常/共用刻度列两门禁 + 人工 --col-scale-map 裁决）。"""
        if col_scale_map:
            _sc = col_scale_map.get(round(x, 1))
            if _sc is not None:
                return _sc, abs(_sc["x"] - x)
            # 映射未覆盖的列：仍走自动配对（映射允许只覆盖一部分列）
        cov = [s for s in scales if s["y0"] <= y0 + 1 and s["y1"] >= y1 - 1]
        if not cov:
            if _fb is not None:
                _fb.append((x, y0, y1))
            ov = [s for s in scales if min(y1, s["y1"]) - max(y0, s["y0"]) > 0]
            if ov:
                best = max(ov, key=lambda s: min(y1, s["y1"]) - max(y0, s["y0"]))
                top = min(y1, best["y1"]) - max(y0, best["y0"])
                cov = [s for s in ov
                       if min(y1, s["y1"]) - max(y0, s["y0"]) >= top * 0.9]
            else:
                cov = list(scales)
        if not cov:
            return None, None
        sc = min(cov, key=lambda s: abs(s["x"] - x))
        return sc, abs(sc["x"] - x)

    dxs = []
    for col in col_list:
        ys = [c["y"] for c in col["图标"]]
        _, dx = pick_scale(col["列x"], min(ys), max(ys))
        if dx is not None:
            dxs.append(dx)
    max_dx = args.scale_max_dx
    if max_dx is None:
        if dxs:
            dxs_s = sorted(dxs)
            max_dx = max(10.0, min(dxs_s[int(len(dxs_s) * 0.9)] * 1.3, 400.0))
        else:
            max_dx = 1e9

    # 刻度列**偏移异常**检测（2026-09-16 立，2026-09-19 判据重做）：
    #   根因：pick_scale 只按「y 覆盖是否够 + 同批里 x 最近」挑刻度列，**不看偏移大小**
    #   （见其 docstring）。当本楼栋的刻度列不在候选批里时，它会安静地配到
    #   **相邻楼栋/图区**的刻度列上，B1/1F 归属整体错位，而全程**零告警**。
    #   旧判据（偏移 > 中位数 × ratio）隐含「全体列偏移同分布」假设，在「一条刻度列
    #   服务本栋多个图标列」形态下偏移天然呈 k 的**整数谱**（1×/2×/3× 单元间距），
    #   中位数只落在其中一档 ⇒ **别的档全部误报，而真错配偏离谱线却不报**
    #   （实测同一图既淹真阳性又放真阴性）。改法：以**最大簇中心**为主偏移，
    #   偏移与之不成整数倍且偏离超容差者标为异常，JSON 与控制台显式列出。
    #   **仍不静默改结果**——归层是否重算交人工裁决（遵循「不自行择一」原则）。
    dx_main = mode_base(dxs)
    if dx_main and args.scale_period_tol:
        log("刻度列偏移：主偏移（最大簇中心）= %.1f，整数倍容差 = %.0f%%"
            % (dx_main, args.scale_period_tol * 100))

    results = []
    _fb_cols = []  # 2026-09-20：走 ③/兜底（无 y 完全覆盖刻度列）的列，见 pick_scale
    for col in col_list:
        x = col["列x"]
        ys = [c["y"] for c in col["图标"]]
        y0, y1 = min(ys), max(ys)
        sc, dx = pick_scale(x, y0, y1, _fb=_fb_cols)
        if sc is not None and dx > max_dx:
            sc = None
        _out_why = None
        if sc is not None and dx is not None and dx_main and args.scale_period_tol:
            _pk, _pdev = period_dev(dx, dx_main)
            if _pdev is not None and _pdev > args.scale_period_tol:
                _out_why = ("偏移 %.1f 与主偏移 %.1f 不成整数倍（最近 %d×，偏离 %.0f%% > "
                            "%.0f%% 容差）——疑似本楼栋刻度列缺失、配到了相邻楼栋/图区的"
                            "刻度列，该列归层结果不可信"
                            % (dx, dx_main, _pk, _pdev * 100, args.scale_period_tol * 100))
        per, un = Counter(), []
        if sc:
            for c in col["图标"]:
                b = band_of(sc, c["y"])
                if b is None:
                    un.append(c["y"])
                else:
                    per[b] += 1
        else:
            # 无刻度列：本列图标**全部**计为未归属，不得静默消失。
            # 原实现 sc 为 None 时既不进 per、也不进 un —— 图标凭空消失，表现为
            # 「归层合计 0 且 未归属 0 且 rc=0」，下游会把 0 户当成功结果消费。
            un = [c["y"] for c in col["图标"]]
        ordered = ([[sc["names"][i], per.get(sc["names"][i], 0)]
                    for i in range(len(sc["names"]))] if sc else [])
        lvc = Counter(c["级别"] for c in col["图标"])
        results.append({
            "列x": x, "x范围": col["x范围"], "图标数": len(col["图标"]),
            "y范围": [round(y0, 2), round(y1, 2)],
            "刻度列x": sc["x"] if sc else None,
            "刻度偏移": round(dx, 2) if dx is not None else None,
            "刻度偏移异常": bool(_out_why),
            "偏移异常说明": _out_why,
            "列内Δy众数": col["Δy众数"], "列内Δy众数占比": col["Δy占比"],
            "级别": dict(lvc), "逐层": ordered,
            "合计": sum(per.values()) if sc else 0, "未归属y": un,
            "证据": [{"级别": c["级别"], "x": c["x"], "y": c["y"], "d": c["d"],
                      "端点": c["端点"], "块名": c["块名"],
                      "文本": c["文本"][:60]} for c in col["图标"]],
        })

    total = sum(r["合计"] for r in results)
    unassigned = sum(len(r["未归属y"]) for r in results)
    scale_outliers = [{"列x": r["列x"], "刻度偏移": r["刻度偏移"], "说明": r["偏移异常说明"]}
                      for r in results if r["刻度偏移异常"]]

    # ---- 多列共用同一刻度列检测（2026-09-18 落地，复盘建议 2）----
    # 「一条刻度列服务多个图标列」是本法的已知失效形态：pick_scale 按几何最近配对，
    # 该形态下会把整列配到邻栋/邻图区，而旧版**零告警**（偏移异常检测也未必触发）。
    # 这里只报事实 + 给可复制的纠正命令，**不自行改结果**（是否真错配由人工裁决）。
    _shared = {}
    for r in results:
        if r["刻度列x"] is not None:
            _shared.setdefault(r["刻度列x"], []).append(r["列x"])
    shared_scale = {k: v for k, v in _shared.items() if len(v) > 1}

    # ---- 乘数标注 ----
    mults = []
    for lay, s, x, y in texts:
        m = MULT_RE.match(s)
        if m:
            mults.append({"标注": s, "图层": lay, "x": round(x, 2), "y": round(y, 2)})

    # ---- 报告 ----
    log("")
    log("-" * 74)
    log("逐列结果（区间法归层）")
    log("-" * 74)
    for r in results:
        fl = "  ".join("%s:%d" % (a, b) for a, b in r["逐层"] if b)
        log("列 x=%-11.1f 图标=%-3d y[%.1f,%.1f] 刻度列x=%s(偏移%s) 级别=%s"
            % (r["列x"], r["图标数"], r["y范围"][0], r["y范围"][1],
               r["刻度列x"], r["刻度偏移"], r["级别"]))
        log("    逐层: %s   [合计 %d]   列内Δy众数=%s(占比%.0f%%)"
            % (fl or "（未归层）", r["合计"],
               "—" if r["列内Δy众数"] is None
               else "%.1f" % r["列内Δy众数"], r["列内Δy众数占比"] * 100))
        if r["未归属y"]:
            log("    ⚠ 未归属 y=%s（落在最低楼层线以下或刻度缺失）" % r["未归属y"])

    log("")
    log("=" * 74)
    log("贴皮线末端图标总数 = %d  →  归层后户数合计 = %d" % (len(hit), total))
    log("=" * 74)

    if scale_outliers:
        log("")
        log("!" * 74)
        log("! 刻度列配对**偏移异常** = %d 列（主偏移 %.1f · 整数倍容差 %.0f%%）"
            % (len(scale_outliers), dx_main or 0, (args.scale_period_tol or 0) * 100))
        for _o in scale_outliers:
            log("!   列 x=%-11.1f 偏移=%-8s %s" % (_o["列x"], _o["刻度偏移"], _o["说明"]))
        log("!  → 这些列的归层结果**不可信**（可能整体错位到邻栋/邻图区）。")
        log("!    请核对刻度列归属后重跑，或显式用 --scale-max-dx 收紧上限。")
        log("!" * 74)

    if shared_scale and not col_scale_map:
        log("")
        log("!" * 74)
        log("! 多个图标列**共用同一条刻度列** = %d 组" % len(shared_scale))
        for _k, _v in sorted(shared_scale.items()):
            log("!   刻度列 x=%-11.1f ← 图标列 %s" % (_k, ", ".join("%.1f" % z for z in _v)))
        log("!  → 本图疑似『一条刻度列服务多个图标列』，几何最近配对在此形态下不可靠")
        log("!    （可能整列错位到邻栋/邻图区，而偏移异常检测未必触发）。")
        log("!    处置：人工核对归属后显式指定，例如：")
        log("!       --col-scale-map \"%s\""
            % ";".join("%.1f=%.1f" % (_v[0], _k) for _k, _v in sorted(shared_scale.items())))
        log("!" * 74)

    if _fb_cols:
        # 2026-09-20：兜底挑列只看重叠/距离、不看方向，共用刻度列图纸上此处
        # 最易静默错配。只报事实不改结果（是否真错配由人工裁决）。
        log("")
        log("!" * 74)
        log("! %d 列**没有 y 完全覆盖的刻度列**，已走重叠最大/全候选兜底（结果未改，只提示）"
            % len(_fb_cols))
        for _fx, _fy0, _fy1 in _fb_cols:
            _r = next((r for r in results if r["列x"] == _fx), None)
            log("!   列 x=%-11.1f y[%.1f,%.1f] → 刻度列x=%s（请人工核对归属，必要时 --col-scale-map 显式指定）"
                % (_fx, _fy0, _fy1, _r["刻度列x"] if _r else "?"))
        log("!  → 兜底挑列不看方向，错配时偏移异常门禁未必触发，须人工看一眼。")
        log("!" * 74)

    if dup_end:
        log("")
        log("⚠ 同一皮线端点被多个候选共用（%d 处）——须人工复核是否为重复绘制：" % len(dup_end))
        for k, v in list(dup_end.items())[:10]:
            log("    端点 (%.2f,%.2f) ← %d 个候选：%s"
                % (k[0], k[1], len(v), [ (c["块名"], c["x"], c["y"]) for c in v[:4] ]))

    excl = [c for c in cands if c["级别"] == "C"]
    if excl:
        log("")
        log("以下 %d 个候选带关键词但**未被计入**（不贴皮线末端，或不在系统图区）" % len(excl))
        log("（典型为楼层平面图里「一个户型一个」的示意图标；如其中有系统图图标被漏，请人工指出）：")
        bx = Counter((round(c["x"] / 500) * 500, round(c["y"] / 500) * 500) for c in excl)
        for k, n in bx.most_common(8):
            log("    区域 x≈%d y≈%d ：%d 个" % (k[0], k[1], n))

    if mults:
        log("")
        log("⚠ 图上存在 *N 乘数标注 %d 处 —— 按 SKILL.md 原则二**不得自行相乘**，" % len(mults))
        log("  其含义与落层口径须交用户裁决后再改数：")
        for m in mults[:20]:
            log("    %-6s (%.1f, %.1f)  图层=%s" % (m["标注"], m["x"], m["y"], m["图层"]))

    out = {
        "口径": "家居配线箱图标法（贴皮线末端）",
        "输入": args.dxf,
        "参数": {
            "皮线图层": data["wire_layers_used"],
            "图区y": [round(ry0, 2), round(ry1, 2)] if ry0 is not None else None,
            "图区依据": region_why,
            "贴合容差": round(tol, 3), "容差依据": tol_why,
            "搜索半径": args.search_radius,
            "强关键词": list(strong), "弱关键词": list(weak),
            "含小方块候选": bool(args.include_square),
            "刻度max_dx": round(max_dx, 2) if max_dx < 1e8 else None,
            "刻度偏移主偏移": round(dx_main, 2) if dx_main else None,
            "主偏移定义": "最大簇中心（合法偏移 = k × 单元间距，天然呈整数谱）",
            "整数倍容差": args.scale_period_tol,
            "显式列刻度映射": {("%.1f" % k): v["x"] for k, v in sorted(col_scale_map.items())},
        },
        "皮线图元数": len(wires), "皮线端点数": len(end_uq),
        "候选数": len(cands), "分级统计": {k: lv.get(k, 0) for k in ("A", "B", "C", "-")},
        "贴末端图标数": len(hit),
        "归层后总户数": total,
        "未归属图标数": unassigned,
        # 2026-09-16（P0-1）：刻度列配对偏移异常清单。非空即表示**本列归层不可信**，
        # 须人工核对刻度列归属后重跑（不得当成"已完成的户数"直接消费）。
        "刻度偏移异常列": scale_outliers,
        # 2026-09-18（建议 2）：共用同一刻度列的图标列分组。非空即提示本图可能是
        # 「一条刻度列服务多个图标列」形态，几何配对结果须人工核对后再消费。
        "共用刻度列组": [{"刻度列x": k, "图标列x": v} for k, v in sorted(shared_scale.items())],
        "列": results,
        "同一端点多候选": [{"端点": list(k), "候选数": len(v),
                          "候选": [{"块名": c["块名"], "x": c["x"], "y": c["y"]} for c in v]}
                         for k, v in dup_end.items()],
        "排除_非末端同类图标": [{"区域": {"x": round(c["x"] / 500) * 500,
                                    "y": round(c["y"] / 500) * 500},
                             "x": c["x"], "y": c["y"], "块名": c["块名"],
                             "文本": c["文本"][:60]} for c in excl],
        "待裁决_乘数标注": mults,
        "说明": ("1 个贴皮线末端的家居配线箱图标 = 1 户；判定依据为几何贴合"
                 "（恒定小偏移），不依赖块名，也不要求图上写 HDD 字样。"
                 "户数须与皮线标注口径或『X户』标注并跑互证；不一致即交用户裁决。"),
    }
    # ---- 门禁：贴末端图标 > 0 但归层后合计 = 0 ----
    # 常见成因：本图不是「每户一个箱」，而是「每层一个箱 + xN 乘数标注」形态 ——
    # 图标数 = 层数 × 单元数，本身**不等于户数**，归层必然得 0。
    # 原实现会 rc=0 写出「归层后总户数 = 0」，下游把 0 户当成功结果消费。
    # 判据与既有「空结果不得当成功消费」一致：非空却归层为 0，同样是空结果。
    if hit and total == 0:
        _ns = sum(1 for r in results if r["刻度列x"] is None)
        log("")
        log("!" * 74)
        log("[门禁] 已中止：贴皮线末端图标 %d 个，但**归层后户数合计 = 0**。" % len(hit))
        log("[门禁] 原因：%d/%d 列的楼层刻度列未配对。" % (_ns, len(results)))
        log("[门禁] 常见成因：本图不是「每户一个箱」，而是「每层一个箱 + xN 乘数标注」，")
        log("[门禁]          图标数 = 层数×单元数，本身不等于户数 —— 本法不适用于该形态。")
        log("[门禁] 处置：① 用 --floor-layer 显式指定楼层标注图层后重跑；")
        log("[门禁]       ② 确无逐层楼层标注时，改走图签参数法（read_titleblock_households.py）")
        log("[门禁]          或按乘数标注口径人工裁决后再出表。")
        log("!" * 74)
        sys.exit(2)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        log("")
        log("已写出 %s" % args.out)

    if unassigned:
        log("⚠ 有 %d 个图标未能归层，已计入待确认" % unassigned)
    sys.exit(0)


if __name__ == "__main__":
    main()
