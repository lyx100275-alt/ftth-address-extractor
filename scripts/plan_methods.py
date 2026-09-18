#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTTH 图纸画像（drawing_profile）生成器 —— Step 1a 探查的选法产物

职责：**只判定与选法，不测量任何业务字段**（户数、安装楼层、覆盖范围一律不碰）。

  1. 依据 methods/signals.json 的 12 个信号定义，逐项判定本图状态
     （present / absent / variant / unknown）并写 evidence；
  2. 按「子任务 → 候选方法」生成 candidates[]（role / method / requires / script / params）；
  3. 与本技能已沉淀的图纸档案（methods/*/manifest.json）逐份比对，给出最接近的一份
     —— 这是 measurement_methods.md §五.3「对比」的物化；
  4. 评估门禁：某子任务的全部候选前置信号均不成立时，记入 gate.unavailable_steps，
     由 parse / coverage 入口读取后决定是否 rc=2 退出（不再静默产出不可用结果）。
  5. 生成 **Step 1 → Step 2 交接契约 handoff**（两要素，**逐项申报制**）：
     ① 有没有分纤箱总图（提供编号 + 安装位置）
     ② 楼内系统图的分纤箱位置 / 覆盖范围 / 每层户数 各用什么方法统计。
     **"有没有"必须逐项如实回答**：有就说有（present + 证据），没有就说没有（absent + 证据）。
     图纸本来就可能只提供系统图、不提供总图 —— 那也**照样往下走**：
     absent 不阻塞，但必须给出**降级路径**（本图缺这一路，下游改用现有的什么来校验）。
     只有"未作答"（unknown = 判不了）才阻塞 → completeness.ok=false → 第二步入口 rc=2。
     本图未提供某命令所需数据时，该命令 rc=3（不适用，非错误）。

输出 schema 见 references/measurement_methods.md §4.2（kind: drawing_profile）。

通用性约束（硬要求）：
  · 不得出现任何项目名、小区名、楼号特例、固定米数/层数；
  · 连线图层关键词为通用启发式，且可由 --wire-keywords 覆盖；
  · 一切"图上有没有"都由本图实测得出，禁止套用前一幅图的经验值。

用法：
  python plan_methods.py --dxf 图纸.dxf --probe probe.json --out profile.json
  可选：--project-dir 项目目录（检测《楼宇信息采集表》）
        --text-layer / --text-type / --title-pattern / --fx-pattern / --wire-keywords
"""
import argparse
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

from ftth_common import (load_dxf, collect_texts, parse_bldg_nums_ex,
                          is_floor_text, setup_logger,
                          cluster_values_by_gap, measure_column_step,
                          home_box_kw, home_box_hit,
                          extract_geom, suggest_fx_symbol_layers,
                          filter_titleblock_units)

sys.stdout.reconfigure(encoding="utf-8")

# ============================================================
# 常量
# ============================================================

# 信号状态枚举 —— 前 3 个来自 methods/signals.json 的 status_values；
# unknown 为本脚本新增（探查未提供判据时**不许假装知道**，必须显式留白）。
# 新增枚举已同步登记进 methods/signals.json 与 SKILL.md 版本记录。
PRESENT, ABSENT, VARIANT, UNKNOWN = "present", "absent", "variant", "unknown"

# 通用正则：全部只描述「书写形态」，不含任何项目/小区特例
RE_HOUSEHOLD = re.compile(r"(?<![入])\s*(\d+)\s*户")            # X户（排除"入户"）
# 皮线米数标注：**字段序因图而异，不得只认一种写法**（2026-09-14 P0 修正）
#   原正则只认 `Xm*N`（米数在前），把 `2Px2芯x36m`（根数在前、带「芯」字、米数在后）
#   判为 absent —— 而后者是实测真实写法（柳辛庄 358 条）。后果：V 型计算被当成
#   「前置条件不成立」整条剔除、覆盖判定整步 skip，被迫退化到竖线法。
#   生产脚本 analyze_coverage_vshape.py 自 2026-09-13（P0-2）起已兼容多字段序，
#   画像检测器必须同步 —— 否则「引擎能跑、门禁不让进」。
RE_FIBER_LEN = re.compile(r"\d+(?:\.\d+)?\s*(?:[mM]|米)(?![a-zA-Z])")  # 含「数字+米数单位」即算
# 形态识别：只用于在 evidence 中回报命中的是哪种写法，便于人工核对（不参与判定）
RE_FIBER_LEN_FORMS = [
    ("米数*根数",       re.compile(r"^\d+(?:\.\d+)?\s*[mM]\s*[*×xX]\s*\d+$")),                      # 20m*2
    ("根数Px芯数x米数",  re.compile(r"^\d+\s*[Pp][xX]\s*\d+\s*芯\s*[xX*]\s*\d+(?:\.\d+)?\s*[mM]$")),  # 2Px2芯x36m
    ("芯数x米数",       re.compile(r"^\d+\s*芯\s*[xX*]\s*\d+(?:\.\d+)?\s*[mM]$")),                   # 2芯x36m
    ("纯米数",          re.compile(r"^\d+(?:\.\d+)?\s*[mM]$")),                                     # 36m
]
RE_COVER_ROW = re.compile(r"至\s*\d*\s*[#号]?\s*箱")             # 覆盖表行「…至NN#箱」
RE_LEVEL_HH = re.compile(r"\d+\s*层\s*/\s*\d+\s*户")             # 图签「N层/M户」
RE_UNIT = re.compile(r"\d+\s*单元")                              # 图签「N单元」
# 图签**分离标注**形态「NF」+「M户/层」（两个独立文字实体，同行相邻）。
# 生产脚本 read_titleblock_households.py 早有该 fallback（配对合成 N层/M户），
# 画像侧长期未同步 ⇒ 该类图纸的 titleblock_annotation 恒判 variant、图签这条
# **独立第二来源**永不启用（「镜像铁律」②：两侧写法兼容表必须一致）。
RE_HU_PER_FLOOR = re.compile(r"\d+\s*户\s*/\s*层")               # 图签「M户/层」
RE_FLOOR_COUNT = re.compile(r"\d+\s*[Ff]")                       # 图签「NF」层数
RE_BLDG_ONLY = re.compile(r"\d+\s*[#号]\s*楼")                    # 图签「N#楼」纯楼名（不含「…示意图」标题）
# 楼层刻度（floor_scale）：楼层标注须**全匹配**。实测宽松 search 会把光缆型号
# `GYTS-96B1` 里的 `B1` 当楼层；MTEXT 经 plain_text() 后仍保留分组花括号（如 `{-1F}`），
# 故判定前先剥花括号（见 _strip_group_braces）。
RE_FLOOR_LABEL = re.compile(r"^(-?\d+\s*[Ff]|[Bb]\s*\d+|[Bb][Ff]|[Ww][Ff])$")
# 普通地上层号 —— 一条 x 列内至少须有一个，否则该列不算可用楼层刻度列
# （排除 `B1`~`B24` 这类等距编号竖列，实测某图 `0` 图层存在）。
RE_FLOOR_PLAIN = re.compile(r"^\d+\s*[Ff]$")
# 箱体覆盖起止层直写（cover_range_annotation）：如「覆盖 -1F~9F」。
# 与覆盖表（`…至NN#箱`，RE_COVER_ROW）严格区分——后者给归属，不给覆盖楼层。
RE_COVER_RANGE = re.compile(
    r"(?:覆盖|范围)[^0-9]{0,8}-?\d+\s*[Ff层][^0-9]{0,8}[-~～至到][^0-9]{0,8}-?\d+\s*[Ff层]")
RE_BLDG_MARK = re.compile(r"[#号]\s*楼?|\d+\s*号楼")             # 楼栋标注特征
RE_TITLE_HINT = re.compile(r"楼|系统图|示意图|住宅|入户")        # 标题类文字的通用特征（不含平面图——2026-09-13 起不读平面图）
# 图纸类词：判「图纸标题」形态用——纯楼栋号罗列（对照表行 `1#楼，2#楼`）不含此类词，
# 不是图纸标题，不得作共享图纸证据（2026-09-16 立，实测对照表行误判 present）。
RE_DRAWING_TITLE = re.compile(r"系统图|示意图|布线图|平面图|竣工图|施工图")
RE_DEFAULT_FX = r"FX\s*\d+\s*#?"                                 # 分纤箱编号默认形态

# 连线图层关键词（通用启发式；实际图层名千变万化，命中清单会原样写进 evidence 供人工复核）
DEFAULT_WIRE_KEYWORDS = (
    r"通讯|通信|光纤|光缆|皮线|主干|ftth|弱电|电信|综合布线|"
    r"wire|cable|fiber|optic|telecom"
)

# 非连线类图层特征：标注/尺寸/文字/图案填充/设备符号 —— 这些层里的"线段"是标注线与
# 符号边框，不是电信连线。用于把「关键词命中」收敛为「连线层候选」。
RE_NON_WIRE_LAYER = re.compile(
    r"标注|尺寸|轴线|文字|图案|填充|符号|设备|家具|门窗|墙体|梁|柱|楼梯|索引|"
    r"dim|text|hatch|symbol|equip|furniture|wall|stair|axis|grid", re.I)

# 米数列判定用的建筑/制图图层黑名单（2026-09-15）：这些图层里的米数是建筑尺寸/
# 房间面积/集水坑深度等，不是皮线米数。词表只收明确建筑/制图语义的词，
# **不收 dim/text/文字 等泛词**——通讯专业的尺寸标注层可能叫 DIM-通讯，误杀会漏判真米数列。
RE_BLD_MEASURE_LAYER = re.compile(
    r"建筑|结构|房间|集水坑|车库|疏散|evac|图名|pub_text|房间名称|景观|幕墙|"
    r"总平面|平面图|立面|剖面|暖通|空调|给排水|消防|轴线", re.I)

# 机电专业黑名单（2026-09-13 P0-2）：这些层的线也"竖"，但不是电信连线。
# 关键词只含 wire/cable 等拉丁词时，层名大小写变体（如 wire-照明 小写）会命中关键词
# 误入候选——实测教训：某图 WIRE-照明/动力/安防/接地 全靠大写躲过小写关键词才没误抓。
# 命中后归入 exc（关键词命中但被排除），与 RE_NON_WIRE_LAYER 同等处置。
# 注意：「弱电」本身是电信连线的常用层名（弱电井/弱电系统图），**不在**黑名单；
# 但「弱电其他」（除电信外的杂项弱电，实测多为安防/监控走线）明确排除。
RE_MEP_LAYER = re.compile(
    r"弱电其他|安防|监控|报警|门禁|广播|照明|动力|接地|防雷|消防|暖通|空调|"
    r"给排水|强电|电力|电气|电梯|桥架|"
    r"lighting|power|fire|hvac|alarm|security|cabletray|lwire", re.I)
# 注：lwire 为某些图纸的机电走线层名前缀（实测出现于 LWIRE），属机电类排除；
# 不含「lwire」子串的电信层（如 RX-wire/WIRE-通讯）不受影响。

LINE_TYPES = ("LINE", "LWPOLYLINE", "POLYLINE")
DEFAULT_TEXT_TYPES = ("TEXT", "MTEXT")

# 判据是【是否随图纸坐标尺度变化】，不是【名字里带不带容差】（见 references/measurement_methods.md
# 「param_source 字段表」）。本技能**没有**不随尺度变化的算法常数：全部阈值（unit_cluster /
# unit_range / y_tol …）都由层高推导，随坐标尺度变化，各脚本按本图层高自适应；
# 量测失败时回退 ftth_common.py 的 DEFAULT_*，那是**本图量不出尺度时的兜底**，
# 不是可跨图沿用的常数（日志会显式标注）。
# 2026-09-16：原表收录 unit_cluster / unit_range / y_tol / install_tol 四个坐标尺度相关量，
# 却标注「与图纸无关，可沿用」，与该判据直接冲突；实测已有消费者据此跨图沿用 install_tol=5.0
#（该参数已随之废除）。现整表清空，只留本说明。
ALGO_DEFAULTS = {}


def _med(xs):
    """中位数（自带实现，不依赖外部私有函数）。"""
    xs = sorted(x for x in xs if x is not None)
    n = len(xs)
    if n == 0:
        return 0.0
    return float(xs[n // 2]) if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def _robust_span(vals, q_lo=0.02, q_hi=0.98):
    """稳健坐标跨度：按分位数截掉离群实体，返回 (lo, hi, hi-lo)。

    为什么不能直接用 max-min：图外孤立标注会把全图跨度撑大几个数量级
    （实测某图主体 x 跨度约 2.2e3，一条图外孤立文字把全图 x 跨度撑到 1.9e6），
    任何"占比"判据都会因此失效。
    """
    vs = sorted(v for v in vals if v is not None)
    n = len(vs)
    if n == 0:
        return 0.0, 0.0, 0.0
    lo = float(vs[min(n - 1, int(q_lo * n))])
    hi = float(vs[max(0, int(q_hi * n) - 1)])
    return lo, hi, hi - lo


def _row_pitch(floor_txt, texts):
    """估计本图行距：同列楼层标注的相邻 y 差中位数；量不出时退化为全图 y 相邻差中位数。

    行距是"同行判定"的尺子。与竖线法的层高自适应同源——从图纸自身量，不预设坐标值。
    """
    byx = {}
    for t in floor_txt:
        byx.setdefault(round(t.get("x", 0.0), 1), []).append(t.get("y", 0.0))
    diffs = []
    for ys in byx.values():
        ys = sorted(ys)
        diffs += [b - a for a, b in zip(ys, ys[1:]) if b - a > 0]
    if diffs:
        return _med(diffs)
    ys = sorted({t.get("y", 0.0) for t in texts})
    diffs = [b - a for a, b in zip(ys, ys[1:]) if b - a > 0]
    return _med(diffs) if diffs else 0.0


def _merge_intervals(ivs, gap=1.0):
    """合并重叠/相接的 y 区间，返回不连续段列表——用于判定竖干断口。"""
    if not ivs:
        return []
    ivs = sorted(ivs)
    out = [list(ivs[0])]
    for lo, hi in ivs[1:]:
        if lo <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


# ============================================================
# 采集层
# ============================================================

def wire_layer_candidates(line_cnt, wire_kw_re):
    """按通用关键词筛连线层候选，并剔除标注/设备/文字类图层。

    返回 (连线层候选: dict, 关键词命中但被排除的层: dict)。
    注意：本函数只做「图层名 + 线段数」层面筛选，**不代表该层线段真的构成电信主干/皮线连线**；
    连接性由 vertical_bus_traceable 进一步判断。候选与被排除层都写进 evidence 供人工复核。
    """
    inc, exc = {}, {}
    for ly, n in line_cnt.items():
        if not wire_kw_re.search(ly or ""):
            continue
        (exc if (RE_NON_WIRE_LAYER.search(ly or "") or RE_MEP_LAYER.search(ly or ""))
         else inc)[ly] = n
    return inc, exc


# 分纤箱在**图面上直写的名称**（与「编号」是两回事：编号可能只存在于配纤表/对照表里）
RE_FX_ANCHOR_KW = re.compile(
    r"分纤箱|分线箱|光缆交接箱|光交箱|光分纤箱|光纤分纤箱|配线箱|ODF")
# 2026-09-13：补「配线箱」——某图系统图箱标注写作『配线箱』（行业俗名），
# 词表不含时锚点全空、竖线法无法配对。「配线箱」与「配电箱」字符不重叠，无误抓风险。
# 注意：「光分路箱」**不得**入表——实测该词命中的全是 576 芯落地式光分路箱
# （ODF/光交设备，非 FTTH 楼内分纤箱），曾致锚点 23→26、覆盖率 100%→91%。

# 箱标注是**简称**（『分纤箱』『光缆分纤箱』），而说明性长句里也会出现同一个词 ——
# 实测某图 26 处含『分纤箱』字样的文字里有 4 处是『说明：…由电井分布分纤箱布放…』，
# 会把锚点数从 12 抬到 16、稀释覆盖率。故按「短 + 无句中标点 + 无说明性词头」过滤。
RE_FX_ANCHOR_NOISE = re.compile(r"[：:，,。;；、（）()【】\[\]]|说明|注[:：]|详见|参见|另见")
FX_ANCHOR_MAX_LEN = 12
FX_ANCHOR_X_TOL = 15.0   # 同一箱的多个文字实体 x 相近
FX_ANCHOR_Y_TOL = 30.0   # 约一个层高：低区/高区两箱 y 间距远大于此（实测差 240）
FX_UNIT_Y_GAP = 30.0     # 竖干切节的 y 断口阈值
FX_UNIT_Y_PAD = 120.0    # 锚点 y 到竖干节区间的允许距离


def _is_fx_anchor_text(s):
    """判断一段含『分纤箱』字样的文字是否为**箱标注简称**（而非说明性句子）。"""
    s = (s or "").strip()
    if not s or len(s) > FX_ANCHOR_MAX_LEN:
        return False
    return not RE_FX_ANCHOR_NOISE.search(s)


def _dedup_sorted_x(xs, tol=15.0):
    """把相近的 x 合并为一个位置（同一箱常有多个文字实体，x 相同或只差几个单位）。"""
    out = []
    for x in sorted(xs):
        if out and x - out[-1] <= tol:
            continue
        out.append(x)
    return out


def _cluster_anchor_points(pts, x_tol=None, y_tol=None):
    """把箱文字实体聚成**箱锚点** —— 二维 (x, y) 聚类。

    2026-09-13 二次实测教训：同一 x 位置的竖井里常上下叠着两个分纤箱（低区 5F +
    高区 13F），竖干也断成两节。只按 x 去重会把 21 个箱压成 12 个锚点，
    覆盖范围的低区/高区两段被糊成一段。故 x、y 都须聚类：x 容差内同桶，
    桶内 y 相近（≤ 约一个层高）才算同一箱。
    """
    if not pts:
        return []
    xt = FX_ANCHOR_X_TOL if x_tol is None else x_tol
    yt = FX_ANCHOR_Y_TOL if y_tol is None else y_tol

    def _flush(items, out):
        items = sorted(items, key=lambda p: p[1])
        groups = []
        for p in items:
            if groups and p[1] - groups[-1][-1][1] <= yt:
                groups[-1].append(p)
            else:
                groups.append([p])
        for g in groups:
            out.append((statistics.median(q[0] for q in g),
                        statistics.median(q[1] for q in g)))

    spts = sorted(pts)
    anchors = []
    bucket = [spts[0]]
    for p in spts[1:]:
        if p[0] - bucket[-1][0] <= xt:
            bucket.append(p)
        else:
            _flush(bucket, anchors)
            bucket = [p]
    _flush(bucket, anchors)
    return anchors


def pick_fx_anchors(texts, fx_re):
    """取分纤箱在**图面上的真实 x 位置**，作为竖线法 / 配对判据的锚点。

    优先级（2026-09-13 实测教训）：
      ① 图面上直写『分纤箱/分线箱』等字样的文字 —— 这是箱在图面上的真实位置；
         同一箱的多个文字实体按 x 相近合并；
      ② 仅当图上无此类字样时，退化为编号（fx_re）文字的 x。但编号可能只出现在
         **配纤表 / 对照表**里（实测某图：编号 x 跨度仅 246 单位、与楼栋/单元/楼层同行），
         此时其 x 是**表格坐标**而非图面箱位置 —— 必须显式告警，不得静默使用。

    实测对照（某图 23 个编号）：配纤表坐标 x≈24700~24950，图面真实箱 x≈25190~27000，
    相差 500+ 单位；用表格坐标去配图面竖线，覆盖率必然 0%。

    返回 (anchors: [(x, y), ...], source: str, warn: str|None)
    """
    kw_all = [t for t in texts if RE_FX_ANCHOR_KW.search(t.get("内容", ""))]
    kw = [t for t in kw_all if _is_fx_anchor_text(t.get("内容", ""))]
    ids = [t for t in texts if fx_re.search(t.get("内容", ""))]

    if kw:
        kw_note = (f"；已按『短简称』过滤掉 {len(kw_all) - len(kw)} 处说明性长句"
                   if len(kw) < len(kw_all) else "")
        # 『分纤箱』字样若落在编号（配纤表/对照表）的 x 跨度内，多半是表格表头，剔除
        tab_note = ""
        if ids:
            ixs = [t.get("x", 0.0) for t in ids]
            lo, hi = min(ixs), max(ixs)
            margin = max((hi - lo) * 0.05, 1.0)
            keep = [t for t in kw if not (lo - margin <= t.get("x", 0.0) <= hi + margin)]
            if keep and len(keep) < len(kw):
                tab_note = (f"；已剔除落在配纤表编号 x 跨度 [{lo:.0f},{hi:.0f}] 内的 "
                            f"{len(kw) - len(keep)} 处表头字样")
                kw = keep
        pts = [(float(t.get("x", 0.0)), float(t.get("y", 0.0))) for t in kw]
        anchors = _cluster_anchor_points(pts)
        layers = sorted({t.get("层", "") for t in kw if t.get("层")})
        src = (f"图面箱文字标注（{len(kw)} 处 → 二维聚类 {len(anchors)} 个箱锚点，"
               f"x 容差 {FX_ANCHOR_X_TOL:.0f} / y 容差 {FX_ANCHOR_Y_TOL:.0f}；"
               f"所在层：{'、'.join(layers[:5])}{'…' if len(layers) > 5 else ''}"
               f"{kw_note}{tab_note}）")
        return anchors, src, None

    if not ids:
        return [], "未找到分纤箱字样或编号文字", None
    pts = [(float(t.get("x", 0.0)), float(t.get("y", 0.0))) for t in ids]
    anchors = _cluster_anchor_points(pts)
    span = (max(a[0] for a in anchors) - min(a[0] for a in anchors)) if len(anchors) > 1 else 0.0
    src = f"编号文字（{len(ids)} 处 → 二维聚类 {len(anchors)} 个锚点，x 跨度 {span:.1f}）"
    warn = ("图上无『分纤箱/分线箱』字样，锚点退回编号文字坐标 —— 若该编号构成配纤表/对照表，"
            "其 x 是表格坐标而非图面箱位置，竖线配对结果须人工复核")
    return anchors, src, warn


def _cluster_segments(segs, x_tol=15.0):
    """按 x 中心把竖线段聚成簇（同一条竖干常由多段线拼成）。"""
    if not segs:
        return []
    ordered = sorted(segs, key=lambda s: s[0])
    clusters, cur = [], [ordered[0]]
    for s in ordered[1:]:
        if s[0] - cur[-1][0] <= x_tol:
            cur.append(s)
        else:
            clusters.append(cur)
            cur = [s]
    clusters.append(cur)
    return clusters


def _split_cluster_units(cluster, y_gap=None):
    """把一个竖线簇按 y 断口切成节 —— 每节是一个**独立的竖干单元**。

    2026-09-13 二次实测教训：同一 x 位置的竖井里常上下叠着**两个分纤箱**（低区 5F +
    高区 13F），竖干也因此断成上下两节。若按「簇」整体配对，一井两箱会被压成一个
    锚点（实测 21 个箱被 x 聚类压成 12 个）。节 = 配对的最小单元。
    返回 [(x, y_lo, y_hi, nseg), ...]，x 取簇内段 x 的中位数。
    """
    if not cluster:
        return []
    yg = FX_UNIT_Y_GAP if y_gap is None else y_gap
    xs = sorted(s[0] for s in cluster)
    cx = xs[len(xs) // 2]
    ivs = _merge_intervals([(s[1], s[2]) for s in cluster], gap=yg)
    seg_cnt = [0] * len(ivs)
    for s in cluster:
        best_k, best_ov = None, -1.0
        for k, (lo, hi) in enumerate(ivs):
            ov = min(s[2], hi) - max(s[1], lo)
            if ov > best_ov:
                best_ov, best_k = ov, k
        if best_k is not None and best_ov > 0:
            seg_cnt[best_k] += 1
    return [(cx, lo, hi, n) for (lo, hi), n in zip(ivs, seg_cnt)]


def _pair_anchors_to_clusters(clusters, fx_positions, x_tol=15.0,
                              y_gap=None, y_pad=None):
    """箱锚点 ↔ 竖干**节** 的一对一配对（二维：(x, y)），容忍文字↔图形的固有偏移。

    2026-09-13 二次实测教训：同一 x 位置的竖井里常上下叠两个箱（低区+高区），
    竖干断成两节 —— 配对单元必须是「节」而不是「簇」，锚点必须是 (x, y) 而不是 x。
    否则 21 个箱会被 12 个簇吞掉 9 个（每井两箱只报一箱）。

    做法：
      1) 每个簇按 y 断口切节（_split_cluster_units）；
      2) 用「最近节x − 锚点x」的带符号中位数估固有偏移 Δ（中位数抗离群）；
      3) 贪心指派：代价 = |节x − (锚x+Δ)|，须 ≤ tol，且锚 y 距节 y 区间 ≤ y_pad；
         一节可服务多个箱（同井低区/高区箱**共用同一根竖干**），但同节锚点两两
         y 间距须 ≥ 2×y_tol（不同楼层带才算不同箱）；
      4) 未配上的锚点若距最近节 x > 3×tol → 判「区域外锚点」剔除后重配
         （实测某图混入 x=27995 的另一地块箱标注，距主竖干群 900+ 单位）。

    返回 (pairs: [(锚下标, 节下标, x残差), ...], delta, tol,
          dropped: [(锚下标, 距最近节x距离), ...])
    """
    if not clusters or not fx_positions:
        return [], 0.0, x_tol, []
    yg = FX_UNIT_Y_GAP if y_gap is None else y_gap
    yp = FX_UNIT_Y_PAD if y_pad is None else y_pad
    units = []
    for c in clusters:
        units.extend(_split_cluster_units(c, yg))
    if not units:
        return [], 0.0, x_tol, []
    uxs = [u[0] for u in units]
    ax = [p[0] if isinstance(p, (tuple, list)) else p for p in fx_positions]
    ay = [p[1] if isinstance(p, (tuple, list)) else 0.0 for p in fx_positions]

    def _greedy(idx_list):
        signed = []
        for i in idx_list:
            j = min(range(len(uxs)), key=lambda k: abs(uxs[k] - ax[i]))
            signed.append(uxs[j] - ax[i])
        dlt = statistics.median(signed) if signed else 0.0
        xs_sorted = sorted(ax[i] for i in idx_list)
        gaps = [b - a for a, b in zip(xs_sorted, xs_sorted[1:]) if b - a > 0]
        t = max(x_tol, (statistics.median(gaps) / 2.0) if gaps else x_tol)
        cand = []
        for i in idx_list:
            for j, (ux, ulo, uhi, _n) in enumerate(units):
                dx = abs(ux - (ax[i] + dlt))
                if dx > t:
                    continue
                dy = max(ulo - ay[i], ay[i] - uhi, 0.0)
                if dy > yp:
                    continue
                cand.append((dx, dy, i, j))
        cand.sort()
        used_anchor, used_units, ps = set(), {}, []
        y_sep = 2.0 * FX_ANCHOR_Y_TOL
        for dx, dy, i, j in cand:
            if i in used_anchor:
                continue
            ys = used_units.get(j, [])
            if any(abs(ay[i] - v) < y_sep for v in ys):
                continue
            used_anchor.add(i)
            used_units.setdefault(j, []).append(ay[i])
            ps.append((i, j, dx))
        return ps, dlt, t

    all_idx = list(range(len(fx_positions)))
    pairs, delta, tol = _greedy(all_idx)
    if len(pairs) == len(all_idx):
        return pairs, delta, tol, []
    far_mult = 3.0
    keep, dropped = [], []
    paired_ids = {p[0] for p in pairs}
    for i in all_idx:
        dmin = min(abs(ux - ax[i]) for ux in uxs)
        if i not in paired_ids and dmin > far_mult * tol:
            dropped.append((i, dmin))
        else:
            keep.append(i)
    if dropped and keep:
        pairs2, delta2, tol2 = _greedy(keep)
        if len(pairs2) >= len(pairs):
            return pairs2, delta2, tol2, dropped
    return pairs, delta, tol, dropped


def collect_line_and_segments(msp, vert_dx):
    """一次遍历同时得到：线段图层分布 + 竖线段清单（补 Step 1a 第 5 项探查）。

    返回 (line_cnt: Counter, segs: [(x_center, y_lo, y_hi, layer), ...])
    竖线段定义：x 跨度 <= vert_dx 且 y 跨度 > x 跨度。
    """
    line_cnt = Counter()
    segs = []
    for e in msp:
        t = e.dxftype()
        if t not in LINE_TYPES:
            continue
        layer = e.dxf.layer or ""
        line_cnt[layer] += 1
        try:
            if t == "LINE":
                pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
            elif t == "LWPOLYLINE":
                pts = [(float(p[0]), float(p[1])) for p in e.get_points()]
            else:  # POLYLINE
                pts = [(float(p[0]), float(p[1])) for p in e.points()]
        except Exception:
            continue
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            dx, dy = abs(x2 - x1), abs(y2 - y1)
            if dx <= vert_dx and dy > dx:
                segs.append(((x1 + x2) / 2.0, min(y1, y2), max(y1, y2), layer))
    return line_cnt, segs


def load_suggested_from_probe(paths):
    """从 probe / config JSON 读回 suggested_params（命令行的补充来源）。

    2026-09-16 修复 P0-3：此前本脚本只用 --probe 的「全量文字样例」，
    suggested_params（含 text_layer / title_pattern 等 **probe 已探明** 的检测类参数）
    被整包丢弃，于是：
      · find_titles(texts, None) 掉进通用兜底（比实际标题写法宽，命中数偏多）；
      · 文字样例不按 text_layer 收窄（见 main 中收窄注释：会引入图签栏等非 FTTH 文字，
        实测可把稳健 x 跨度从约 2.2e3 撑到 142 万，图签栏被误判成「与编号同行」）。
    修法遵循技能契约「参数填充优先级：命令行 > config/probe 建议值 > 算法常数」，
    只回填**命令行未显式指定**的项（调用处在回填时判定），并在日志标注取值来源。
    多个来源按传入顺序先到先得 —— 调用方令 --config 先于 --probe。
    """
    merged = {}
    for p in paths:
        if not p:
            continue
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception:
            continue
        sp = d.get("suggested_params")
        if isinstance(sp, dict):
            for k, v in sp.items():
                if v not in (None, "", []):
                    merged.setdefault(k, v)
    return merged


def load_texts_from_probe(path):
    """复用 probe.json 的全量文字样例，避免二次提取。"""
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    texts = d.get("全量文字样例")
    return texts if isinstance(texts, list) and texts else None


def find_titles(texts, title_re=None, log=None):
    """找出楼栋标题类文字（锚点）。

    有 --title-pattern 时按其匹配；否则用通用兜底：
    能被楼栋号解析器识别、且含「楼/系统图/示意图/住宅」等标题特征。
    兜底正则**比探查枚举出的实际写法宽**（可能纳入非标题锚点，命中数偏多），
    故降级时显式告警，提醒按 Step 1a 枚举结果显式传入 --title-pattern。
    """
    if title_re:
        pat = re.compile(title_re)
        return [t for t in texts if pat.search(t.get("内容", ""))]
    if log:
        log.warning("未提供 --title-pattern，改用通用兜底识别标题锚点（结果可能偏宽）；"
                    "建议按 Step 1a 枚举出的实际标题写法显式传入")
    out = []
    for t in texts:
        s = t.get("内容", "")
        nums, _ = parse_bldg_nums_ex(s)
        if nums and RE_TITLE_HINT.search(s):
            out.append(t)
    return out


# ============================================================
# 信号判定（12 项，逐项返回 (status, evidence)）
# ============================================================

def judge_cluster_layout(texts, titles):
    """楼-簇独立组织：每楼全部信息聚成独立簇，簇间 x 间距大于簇内 x 跨度。"""
    if len(titles) < 2:
        return ABSENT, f"标题锚点仅 {len(titles)} 个，不构成可判定的多簇结构"
    xs = sorted(t.get("x", 0.0) for t in texts)
    anchors = sorted(t.get("x", 0.0) for t in titles)
    # gaps 长度恒为 len(anchors)-1，**不得过滤**（过滤会使索引与 anchors 错位）；
    # 仅用其中的正值做统计，x 重合的标题（gap=0）以默认半宽兜底。
    gaps = [anchors[i + 1] - anchors[i] for i in range(len(anchors) - 1)]
    pos_gaps = [g for g in gaps if g > 0]
    if not pos_gaps:
        return UNKNOWN, "相邻标题 x 间距全为 0（标题 x 重合），无法计算簇结构"
    default_half = _med(pos_gaps) / 2.0
    inner = []
    for i, a in enumerate(anchors):
        half_lo = gaps[i - 1] / 2.0 if (i > 0 and gaps[i - 1] > 0) else default_half
        half_hi = gaps[i] / 2.0 if (i < len(gaps) and gaps[i] > 0) else default_half
        band = [x for x in xs if (a - half_lo) <= x <= (a + half_hi)]
        if len(band) >= 2:
            inner.append(max(band) - min(band))
    if not inner:
        return UNKNOWN, "簇内文字样本不足，无法计算簇内跨度"
    med_gap, med_inner = _med(pos_gaps), _med(inner)
    ev = (f"标题 {len(anchors)} 个；相邻标题 x 间距中位数 {med_gap:.1f}，"
          f"簇内 x 跨度中位数 {med_inner:.1f}")
    if med_gap > med_inner:
        return PRESENT, ev + " → 簇间间距大于簇内跨度，簇结构成立"
    return ABSENT, ev + " → 簇间间距未超过簇内跨度，簇结构不成立"


def judge_shared_drawing(titles):
    """结构相同的多栋楼共享一张图纸：标题中含多个楼栋号。

    形态检验（2026-09-16 立，「信号判 present 须过形态检验」在本信号的落地）：
      ① 候选多栋文字须是**图纸标题**——含图纸类词（RE_DRAWING_TITLE）。纯楼栋号罗列
         （对照表/索引行，如 `1#楼，2#楼`）不是图纸标题，只记入 evidence 供人工核对，
         不作共享证据——实测某图 3 条对照表行在宽 title-pattern 下被误判 present、
         窄 pattern 下判 absent，同一图该信号随 pattern 宽窄摇摆（7/10 vs 3/10）；
      ② 分图区核对——候选所涉楼栋若在本图另有各自的**单栋图纸标题**，则每楼有独立
         图纸、不构成共享（多栋文字实为索引/对照表行）；部分覆盖时判 UNKNOWN 交人工。
    """
    multi, excluded, single_titles = [], [], {}
    for t in titles:
        s = t.get("内容", "")
        nums, amb = parse_bldg_nums_ex(s)
        if not nums:
            continue
        if len(nums) >= 2:
            if RE_DRAWING_TITLE.search(s):
                multi.append((s[:32], nums, amb))
            else:
                excluded.append((s[:32], nums))
        elif RE_DRAWING_TITLE.search(s):
            single_titles.setdefault(nums[0], s[:32])
    if not multi:
        ev = "所有标题均只含单个楼栋号，无多栋共享标题"
        if excluded:
            ev += ("；另有 %d 条多楼栋文字因非图纸标题形态被排除（对照表/索引行），"
                   "示例『%s』→ 楼栋号 %s" % (len(excluded), excluded[0][0], excluded[0][1]))
        return ABSENT, ev
    # ② 分图区核对：候选所涉楼栋另有独立图纸标题者不构成共享
    clear, partial, covered_all = [], [], []
    for txt, nums, amb in multi:
        covered = [n for n in nums if n in single_titles]
        if not covered:
            clear.append((txt, nums, amb))
        elif len(covered) < len(nums):
            partial.append((txt, nums, covered))
        else:
            covered_all.append((txt, nums))
    if clear:
        txt, nums, amb = clear[0]
        suffix = "；该标题含连字符写法，语义存疑须人工裁决" if amb else ""
        return PRESENT, (f"共 {len(clear)} 条共享标题，示例『{txt}』→ 楼栋号 {nums}{suffix}")
    if partial:
        txt, nums, covered = partial[0]
        return UNKNOWN, (f"多栋标题『{txt}』→ 楼栋号 {nums}，其中 {covered} 另有独立图纸标题、"
                         "其余没有——共享与独立并存，须人工裁决")
    txt, nums = covered_all[0]
    return ABSENT, (f"多栋标题『{txt}』→ 楼栋号 {nums}，但这些楼栋在本图均有各自的"
                    "单栋图纸标题——每楼独立图纸，不构成共享")


def judge_household_annotation(texts):
    """每层标注户数（'X户'）。"""
    hits = [t for t in texts if RE_HOUSEHOLD.search(t.get("内容", ""))]
    if hits:
        s = "｜".join(t.get("内容", "")[:12] for t in hits[:3])
        return PRESENT, f"命中 {len(hits)} 条『X户』层户数标注，样例：{s}"
    return ABSENT, "全量文字中无『X户』形式的层户数标注"


def collect_insert_idents(msp):
    """采集 INSERT 的（图层, 块名, 属性列表）——只取标识所需字段。

    为什么单列一个采集函数：家居配线箱图标在有些图上**不写字、只插块**，其标识藏在
    块名或块属性值里（实测块属性 `A=家居配线箱`、`$TEXT$=HDD`）。只靠文字实体判存在性
    会漏判，故信号判定必须同时看 INSERT。本函数**不取几何** —— 图标是否"贴皮线末端"
    属测量阶段判据，见 count_box_icons.py。
    """
    out = []
    for e in msp:
        if e.dxftype() != "INSERT":
            continue
        try:
            name = e.dxf.name or ""
            lay = e.dxf.layer or ""
            atts = [(a.dxf.tag or "", a.dxf.text or "") for a in e.attribs]
        except Exception:
            continue
        out.append((lay, name, atts))
    return out


# 家居配线箱的**文字实体**标识须是短标签（`家居配线箱` / `HDD`）——长句里出现关键词多为
# 路径/说明文字：实测某图『自地下车库引上至大堂弱电箱』命中「弱电箱」，而该图并无家居配线箱
# 图标。块名/属性值天然是短标签，不受此限。（依据 SKILL.md「信号判 present 须过形态检验」）
_HOME_BOX_TEXT_MAX = 12


def judge_box_icon_annotation(texts, inserts, has_wire_layer=False):
    """系统图内是否存在「家居配线箱」图标（每户一个）。**图标法的前置信号。**

    本阶段只回答"图上有没有这个东西"——判定只看**标识**（文字实体 / INSERT 块名 /
    块属性值），不断言几何：「贴皮线末端、每户一个」须配合皮线图元才能测，属测量阶段
    （count_box_icons.py）的职责，此处不越界。

    关键词表在 ftth_common（与 count_box_icons.py 共用同一份），纯 ASCII 缩写按词边界
    匹配，故 `HD` 不会误命中 `HDMI`/`CHD`。

    三态：
      · PRESENT —— 命中任一形式的**短标签**标识（图标标签天然极短：`家居配线箱` / `HDD`）；
      · VARIANT —— 无短标签，但命中长句疑似词 或 存在专用连线层：前者多为路径/说明文字
                   （实测某图『自地下车库引上至大堂弱电箱』命中「弱电箱」，而该图并无家居
                   配线箱图标），后者疑为"只画方块、什么字都不写"的画法。两种都须用
                   count_box_icons.py `--include-square` 现场确认"每户一个且贴末端"后才可采信
                   （VARIANT **不算前置成立**，选法不会自动切到图标法）；
      · ABSENT  —— 文字与 INSERT 中均无标识，须人工确认图上确实没有家居配线箱。
    """
    kw = home_box_kw()
    samples, seen, long_hits = [], set(), []
    for t in texts:
        c = (t.get("内容") or "").strip()
        if not c or not home_box_hit(c, kw):
            continue
        # 长句里的关键词不作存在性证据（见 _HOME_BOX_TEXT_MAX 的理由）。
        if len(c) > _HOME_BOX_TEXT_MAX:
            long_hits.append(c)
            continue
        if c not in seen:
            seen.add(c)
            samples.append(f"文字『{c}』")
    for lay, name, atts in inserts:
        # 块名 / 属性值天然是短标签，不受长度约束。
        if name and home_box_hit(name, kw) and name not in seen:
            seen.add(name)
            samples.append(f"块名『{name}』")
        for tag, val in atts:
            key = f"{tag}={val}"
            if val and home_box_hit(val, kw) and key not in seen:
                seen.add(key)
                samples.append(f"块属性 {key}")
    if samples:
        more = f"（共 {len(samples)} 种写法）" if len(samples) > 4 else ""
        return PRESENT, f"命中家居配线箱标识：{'；'.join(samples[:4])}{more}"
    if long_hits or has_wire_layer:
        why = []
        if long_hits:
            why.append("仅长句命中疑似词（疑为路径/说明文字，非图标标签）："
                       + "；".join(f"『{s[:28]}』" for s in long_hits[:2]))
        if has_wire_layer:
            why.append("存在专用连线层但无任何图标标签（疑『只画方块、不写文字』的画法）")
        return VARIANT, ("；".join(why) + " —— 须用 count_box_icons.py --include-square "
                         "现场确认『每户一个且贴皮线末端』后才可采信，确认前不得据此改用图标法")
    return ABSENT, ("文字与 INSERT 中均无家居配线箱标识（家居配线箱/HDD/HD/多媒体箱…），"
                    "且无专用连线层与疑似长句 —— 须人工确认图上确实没有家居配线箱图标")


def _fiber_len_columns(hits, min_n=3, even_lo=3.0):
    """米数列检验（**尺度无关**）：V 型计算消费的是**逐层一列**的皮线米数标注。

    三条判据，全部不依赖图纸坐标尺度（2026-09-15 通用化）：
      ① 同 x 聚簇 —— 按「间隙 > k×低分位间隙」自适应切分，不用绝对容差；
      ② 簇内 ≥ min_n 条；
      ③ 相邻 Δy 均匀 —— 每条间隔都落在 [med/even_lo, med×even_lo] 内，即「一层一条、
         等层距铺开」。说明长句/图例里堆叠的杂散标注即便条数够，也因间距不均被拒。

    为什么不能用「y 跨度 > 60」这类绝对阈值：那份 60 是按某张图（层高 30）标定的，
    换到层高 15600 的坐标系，任何真列都会被判为"堆在一起"，信号整体静默失效。
    """
    if not hits:
        return []
    by_x = {}
    for t in hits:
        by_x.setdefault(round(float(t.get("x", 0.0)), 4), []).append(t)
    cols = []
    for grp in cluster_values_by_gap(sorted(by_x)):
        v = [t for xk in grp for t in by_x[xk]]
        if len(v) < min_n:
            continue
        ys = sorted(float(t.get("y", 0.0)) for t in v)
        dys = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
        dys_p = [d for d in dys if d > 0]
        if not dys_p:
            continue                       # 全部重合，不成列
        med = statistics.median(dys_p) or min(dys_p)
        if all(med / even_lo <= d <= med * even_lo for d in dys_p):
            cols.append(v)
    return cols


def judge_fiber_length_vshape(texts):
    """皮线长度标注（V 型计算的前置信号）。**写法不固定，字段序因图而异**。

    已知形态：`20m*2`（米数在前）/ `2Px2芯x36m`（根数在前、带「芯」字、米数在后）/
    `2芯x36m` / `36m`。判据只看「含数字 + 米数单位」，**不假定字段序**。

    **判 PRESENT 必须过「米数列」形态检验**（2026-09-15 P0 修正）：
    命中须为短标注（长度 ≤24）、排除建筑/制图图层、且构成竖列（同 x 自适应聚簇
    ≥3 条且相邻 Δy 均匀）。教训：图例说明长句（如「光缆在分路箱成端10米，盘留5米…」）
    里的米数曾触发正则误判 PRESENT，导致覆盖方法错选 V 型计算，而全图并无任何米数列。
    """
    hits = [t for t in texts if RE_FIBER_LEN.search(t.get("内容", ""))]
    if hits:
        # 命中图层分布（打进证据串，供一眼识别是否为建筑/尺寸类图层污染）
        by_layer = {}
        for t in hits:
            by_layer[t.get("层", "?")] = by_layer.get(t.get("层", "?"), 0) + 1
        layer_str = "、".join(f"{k}({v})" for k, v in
                              sorted(by_layer.items(), key=lambda kv: -kv[1])[:5])
        forms = []
        for name, rex in RE_FIBER_LEN_FORMS:
            n = sum(1 for t in hits if rex.match(t.get("内容", "").strip()))
            if n:
                forms.append(f"{name} {n} 条")
        form_str = "、".join(forms) if forms else "未归类形态（见样例）"
        # 样例优先取「短标注」——图例说明长句（如「光缆在分路箱盘留10米…」）若排在
        # 首位，会让证据串首屏看起来像"说明文字也算米数"，误导 Agent 判读。
        _samp = ([t for t in hits if len(t.get("内容", "").strip()) <= 24] or hits)[:3]
        s = "｜".join(t.get("内容", "")[:20] for t in _samp)
        # 形态检验：短标注 + 排除建筑/制图图层 + 竖列
        short_all = [t for t in hits if len(t.get("内容", "").strip()) <= 24]
        short_hits = [t for t in short_all
                      if not RE_BLD_MEASURE_LAYER.search(t.get("层", ""))]
        bld_note = ""
        if len(short_all) > len(short_hits):
            bld_note = (f"；另有 {len(short_all) - len(short_hits)} 条短标注位于"
                        f"建筑/制图图层（如尺寸/房间/集水坑），已不计入米数列")
        cols = _fiber_len_columns(short_hits) if short_hits else []
        if cols:
            col_desc = "；".join(
                f"x≈{float(c[0].get('x', 0)):.0f} 共{len(c)}条" for c in cols[:3])
            return PRESENT, (f"命中 {len(hits)} 条皮线米数标注（{form_str}），"
                             f"图层分布：{layer_str}{bld_note}；其中 {len(short_hits)} 条短标注"
                             f"构成 {len(cols)} 个米数列（{col_desc}），样例：{s}；"
                             f"是否呈 V 形（谷底=安装层）由覆盖判定阶段验证")
        long_note = (f"；其中 {len(hits) - len(short_all)} 条为说明性长文字"
                     f"（长度>24，不成列）") if len(short_all) < len(hits) else ""
        return ABSENT, (f"命中 {len(hits)} 条含米数文字（{form_str}，图层分布：{layer_str}）"
                        f"{long_note}{bld_note}；可计入米数列的短标注不足，"
                        f"不构成逐层米数列（同x聚簇≥3条且逐条Δy均匀 = 一层一条铺开），"
                        f"V 型计算前置条件不成立；样例：{s}")
    # 判 absent 前**必须**先排除「正则漏写」：把全图含 m/米/芯 的短文字打出来作为反证材料。
    # 本次教训：`2Px2芯x36m` 因正则只认 `Xm*N` 被误判 absent，直接导致 V 型计算被剔除。
    suspects = [t.get("内容", "").strip() for t in texts
                if re.search(r"[mM米芯]", t.get("内容", ""))
                and len(t.get("内容", "").strip()) <= 24]
    hint = ("；**反证材料**（全图含 m/米/芯 的短文字，若其中有米数则说明是检测器漏写，"
            "须补正则后重判）：" + "｜".join(suspects[:5])) if suspects \
        else "；全图亦无含 m/米/芯 的短文字"
    return ABSENT, ("全量文字中无「数字+米数单位」形式的皮线长度标注，"
                    "V 型计算前置条件不成立" + hint)


def judge_coverage_table(texts):
    """覆盖表：标注皮线编号到分纤箱的映射（仅作线索，不作判据）。"""
    hits = [t for t in texts if RE_COVER_ROW.search(t.get("内容", ""))]
    if hits:
        return PRESENT, f"命中 {len(hits)} 条『至…箱』覆盖表行，样例：{hits[0].get('内容', '')[:28]}"
    return ABSENT, "无『至…箱』形式的覆盖表行"


def _strip_group_braces(s):
    """剥掉 MTEXT 残留的分组花括号。

    实测：`MText.plain_text()` 会剥掉 `\\W0.8;` 一类格式码，但**保留**包裹文字的花括号
    （原始内容 `{\\W0.7999999999999999;-1F}` → plain_text 后 `{-1F}`）。
    不剥这一层，`^-?\\d+F$` 之类全匹配判据永远不命中；改用宽松 search 又会被
    `GYTS-96B1` 这类光缆型号误命中。故：先剥花括号，再全匹配。
    """
    return (s or "").replace("{", "").replace("}", "").strip()


def judge_floor_scale(texts):
    """楼层刻度可建带：系统图内存在楼层标注（B1/1F/…/XF/WF），可按 y 排序建连续楼层带。

    这是**区间法的前置**，而区间法被三处共用：① 每层户数归属 ② 分纤箱安装楼层
    ③ 竖线法三步走第②③步（用区间法测断头所在层）；V 型计算的谷底定层同样走它。
    故本信号缺失 ⇒ 上述三法一律不可用，只剩纯文字直读（*读取标注*）。

    判据用「最长楼层刻度列」而非「图里有几个楼层标注」—— 后者会把"分散在多楼、
    每处都不成列"的情况误判为 present。
    """
    labs = []
    for t in texts:
        s = _strip_group_braces(t.get("内容"))
        if RE_FLOOR_LABEL.match(s):
            labs.append((float(t.get("x") or 0.0), float(t.get("y") or 0.0), s))
    if not labs:
        return ABSENT, "无全匹配的楼层标注（B1/1F/…/XF/WF），区间法无法建楼层带"
    labs.sort(key=lambda p: p[0])
    tol = max(2.0, (labs[-1][0] - labs[0][0]) * 0.002)
    cols, cur = [], [labs[0]]
    for p in labs[1:]:
        if p[0] - cur[-1][0] <= tol:
            cur.append(p)
        else:
            cols.append(cur)
            cur = [p]
    cols.append(cur)
    # 列内须含**普通地上层号**（1F/17F 等）才算可用楼层刻度列 —— 实测某图 `0` 图层存在
    # `B1`~`B24` 的等距编号竖列（同 x、间距恒定），只按 `[Bb]\d+` 计数会误判成 24 层刻度。
    cols = [c for c in cols if any(RE_FLOOR_PLAIN.match(p[2]) for p in c)]
    if not cols:
        return ABSENT, (f"楼层标注全匹配 {len(labs)} 条，但无任何 x 列含普通层号（1F/17F 等）"
                        f" —— 疑为同类编号竖列，不构成可用的楼层刻度")
    best = max(cols, key=lambda c: len({round(p[1], 3) for p in c}))
    n_best = len({round(p[1], 3) for p in best})
    n_y = len({round(p[1], 3) for p in labs})
    det = (f"楼层标注全匹配 {len(labs)} 条（去重 y {n_y} 个）；最长的楼层刻度列含 {n_best} 层"
           f"（x={best[0][0]:.1f}，样例 {'｜'.join(p[2] for p in best[:4])}）")
    if n_best >= 5:
        return PRESENT, det + " → 可按 y 排序建成连续楼层带，区间法前置成立"
    if n_best >= 3:
        return VARIANT, det + " → 楼层刻度列偏短（<5 层），能否建带须人工确认"
    return ABSENT, det + " → 无任何 x 列构成连续楼层刻度，区间法前置不成立"


def judge_cover_range_annotation(texts):
    """箱体覆盖起止层直写：图上直接写「覆盖 -1F~9F」这类区间 —— 属『读取标注』。

    与覆盖表严格区分：`coverage_table`（`…至NN#箱`）只给皮线→箱的归属映射，
    **不给出覆盖楼层区间**，不作覆盖判据；本信号是图上直写的覆盖楼层区间，可作判据。
    """
    hits = []
    for t in texts:
        s = _strip_group_braces(t.get("内容"))
        if RE_COVER_RANGE.search(s):
            hits.append(s)
    if hits:
        return PRESENT, (f"命中 {len(hits)} 条箱体覆盖起止层标注，样例："
                         f"{'｜'.join(hits[:3])} → 覆盖范围可直读（读取标注）")
    return ABSENT, "无『覆盖 N层~M层』形式的箱体覆盖区间标注，覆盖范围不能直读"


def inspect_overview_map(texts, fx_re, titles=None):
    """量测「分纤箱总图三要素」实况（编号 / 与楼栋·单元同行 / 与安装楼层同行）。

    为什么不能只看"编号 + 楼栋 + 单元同图"的数量共现：实测某图 17 条编号 x 跨度占图纸
    主体 75%（随楼分散）、x 与单元标注重合 94%、且**与『X户』『Xm*N』同行**——即编号嵌在
    各楼系统图的楼层表内部。同图当然同时有楼栋与单元标注，但那是每栋系统图各自带的，
    并非"集中总图"。按此数量共现判定会把"分散"误判成"集中"。

    故本函数改用**对照表形态**量测，一切以图纸自身的行距为尺：
      · 同行（|dy| ≤ 本图行距 且 |dx| ≤ 主体 x 跨度 15%）有楼栋或单元标注 → 构成
        「编号 → 楼栋/单元」对照表行；
      · 同行有『X户』或『Xm*N』 → 该编号处在楼层表内部（系统图特征）。
    两类比例都写进 evidence，供人工复核——本函数只量测，不下结论。
    """
    fx = [t for t in texts if fx_re.search(t.get("内容", ""))]
    bldg = [t for t in texts if RE_BLDG_MARK.search(t.get("内容", ""))
            and parse_bldg_nums_ex(t.get("内容", ""))[0]]
    unit = [t for t in texts if RE_UNIT.search(t.get("内容", ""))]
    floor_txt = [t for t in texts if is_floor_text(t.get("内容", ""))]
    hu = [t for t in texts if RE_HOUSEHOLD.search(t.get("内容", ""))]
    cable = [t for t in texts if RE_FIBER_LEN.search(t.get("内容", ""))]

    _, _, body_x = _robust_span([t.get("x", 0.0) for t in texts])
    fx_x = [t.get("x", 0.0) for t in fx]
    fx_y = [t.get("y", 0.0) for t in fx]
    x_span = (max(fx_x) - min(fx_x)) if fx else 0.0
    y_span = (max(fx_y) - min(fx_y)) if fx else 0.0
    conc = (x_span / body_x) if body_x else 0.0
    pitch = _row_pitch(floor_txt, texts)
    x_tol = 0.15 * body_x if body_x else 0.0

    def _same_row(f, o):
        return (abs(f.get("y", 0.0) - o.get("y", 0.0)) <= pitch
                and abs(f.get("x", 0.0) - o.get("x", 0.0)) <= x_tol)

    def _cnt(lst):
        return sum(1 for f in fx if any(_same_row(f, o) for o in lst))

    n = len(fx) or 1
    r_bldg, r_unit = _cnt(bldg), _cnt(unit)
    r_floor = _cnt(floor_txt)
    r_table = sum(1 for f in fx if any(_same_row(f, o) for o in hu + cable))
    r_map = sum(1 for f in fx if any(_same_row(f, o) for o in bldg + unit))

    det = (f"分纤箱编号 {len(fx)} 条（x 跨度 {x_span:.1f}｜y 跨度 {y_span:.1f}｜"
           f"占图纸主体 x 跨度 {conc:.0%}）；同行判据=本图行距 {pitch:.1f} 且 |dx| ≤ {x_tol:.0f}；"
           f"编号同行命中：楼栋 {r_bldg} / 单元 {r_unit} / 楼层 {r_floor} / "
           f"『X户』或『Xm*N』{r_table}（共 {len(fx)} 条编号）")
    return {
        "编号数": len(fx), "x跨度": x_span, "y跨度": y_span,
        "主体x跨度": body_x, "集中度": conc,
        "行距": pitch, "同行x容差": x_tol,
        "同行楼栋": r_bldg, "同行单元": r_unit, "同行楼层": r_floor,
        "同行楼层表": r_table, "同行对照表": r_map,
        "对照表率": r_map / n, "楼层表率": r_table / n,
        "楼栋标注数": len(bldg), "单元标注数": len(unit),
        "证据": det,
    }


def judge_fx_overview_map(st):
    """分纤箱总图判定：**对照表形态**才算总图；编号嵌在各楼系统图楼层表内的不算。

    实测教训：旧判据是「编号 + 楼栋 + 单元同图」的数量共现 → 对"编号随楼分散、嵌在
    各楼系统图表内"的图纸必然误判为 present，而该图恰恰**没有对照表可用**，
    下游只能退回几何归属（违反 SKILL.md 硬约束②的例外形态）。
    """
    if not st["编号数"]:
        return ABSENT, "全量文字中无分纤箱编号（FX 类）标注"
    det = st["证据"]
    if not st["楼栋标注数"] or not st["单元标注数"]:
        return VARIANT, det + " → 图上缺楼栋或单元标注，无法判断编号是否构成对照表，须人工复核"
    if st["楼层表率"] >= 0.6:
        return ABSENT, (det + f" → {st['楼层表率']:.0%} 的编号与『X户』/『Xm*N』同行，"
                               "属**嵌在各楼系统图楼层表内部**，不构成集中总图（无对照表可用）")
    if st["集中度"] > 0.5:
        return ABSENT, (det + f" → 编号 x 跨度占图纸主体 {st['集中度']:.0%}（>50%），"
                               "散布全图、不构成集中总图（实测：某图 252 条伪编号散布 54%）")
    if st["对照表率"] >= 0.6:
        return PRESENT, (det + f" → {st['对照表率']:.0%} 的编号与楼栋/单元标注同行，"
                               "构成『编号→楼栋/单元』对照表，总图成立")
    return VARIANT, (det + " → 同行特征既不明显属对照表、也不明显属楼层表，"
                           "是否构成总图须人工复核")


def _synth_level_hh_by_pairing(texts, y_tol=2.0):
    """把「NF」+「M户/层」分离标注按同行邻近配对，合成层户标注。

    与 read_titleblock_households.py 的 variant fallback **同一判据**（以 M户/层 为锚、
    每个只配 x 最近且未用过的 NF、y 容差 2.0），保证画像结论与生产脚本口径一致。
    返回合成条目列表（每项 = 该条 M户/层 的 text dict）。
    """
    hu = [t for t in texts if RE_HU_PER_FLOOR.fullmatch(t.get("内容", ""))]
    fl = [t for t in texts if RE_FLOOR_COUNT.fullmatch(t.get("内容", ""))]
    if not (hu and fl):
        return []
    used, out = set(), []
    for ht in hu:
        cands = [(ft, abs(ft.get("x", 0.0) - ht.get("x", 0.0)) + abs(ft.get("y", 0.0) - ht.get("y", 0.0)))
                 for ft in fl if id(ft) not in used
                 and abs(ft.get("y", 0.0) - ht.get("y", 0.0)) <= y_tol]
        if cands:
            cands.sort(key=lambda c: c[1])
            used.add(id(cands[0][0]))
            out.append(ht)
    return out


def judge_titleblock_annotation(texts):
    """图签（标题栏）层直写每栋入户规模：楼名 + 层户标注 + 'N单元'。

    层户标注兼容两种写法（写法兼容表与 read_titleblock_households.py 同步）：
      ① 合并形态「N层/M户」；
      ② 分离形态「NF」+「M户/层」同行 —— 配对后可合成「N层/M户」，故同样视为 present。

    `N单元` 计数只算**图签块内**的：系统图楼层列顶部也写 `N单元`（同图层同写法），
    混算会让「图签单元标注条数」虚高（实测 24 条里只有 12 条属图签），
    且与容差量测/配对侧的口径不一致 —— 两侧共用 ftth_common.filter_titleblock_units。
    """
    lv = [t for t in texts if RE_LEVEL_HH.search(t.get("内容", ""))]
    form = "『N层/M户』"
    if not lv:
        synth = _synth_level_hh_by_pairing(texts)
        if synth:
            lv, form = synth, "分离标注『NF』+『M户/层』（同行配对合成层户标注）"
    un_all = [t for t in texts if RE_UNIT.search(t.get("内容", ""))]
    bl = [t for t in texts if RE_BLDG_ONLY.fullmatch(t.get("内容", ""))]
    un_blk = un_all
    n_drop = 0
    if un_all and lv:
        _keep, _drop = filter_titleblock_units(
            [(t.get("x", 0.0), t.get("y", 0.0), t.get("内容", "")) for t in un_all],
            [(t.get("x", 0.0), t.get("y", 0.0), t.get("内容", "")) for t in bl],
            [(t.get("x", 0.0), t.get("y", 0.0), t.get("内容", "")) for t in lv])
        n_drop = len(_drop)
        _keys = {(round(x, 1), round(y, 1), s) for x, y, s in _keep}
        un_blk = [t for t in un_all
                  if (round(t.get("x", 0.0), 1), round(t.get("y", 0.0), 1), t.get("内容", "")) in _keys]
    _un_note = (f"、『N单元』{len(un_blk)} 条（图签块内；另有 {n_drop} 条同名标注离楼名/层户过远，"
                f"属系统图内的单元列头，已剔除）" if n_drop
                else f"、『N单元』{len(un_blk)} 条")
    if lv and un_blk:
        return PRESENT, (f"命中{form}{len(lv)} 条{_un_note}"
                         f"→ 图签直写入户规模成立；几何偏移须由 `read_titleblock_households.py --probe` 量测")
    if lv or un_all:
        return VARIANT, (f"仅命中部分要素：{form}{len(lv)} 条{_un_note}"
                         f"→ 是否构成成对标注须人工确认")
    return ABSENT, "图签层无『N层/M户』（含『NF』+『M户/层』分离形态）『N单元』成对标注"


def judge_dedicated_wire_layer(line_cnt, wire_kw_re, top_n=12):
    """专用电信连线图层：与建筑/暖通/监控等专业图线分离。

    本判定只做「图层名 + 线段数」层面的筛选；该层线段是否真的构成电信主干/皮线连线
    （连接分纤箱与楼层）由 vertical_bus_traceable 进一步验证 —— 故 evidence 中同时给出
    连线层候选与被排除的标注/设备类层，供人工复核。
    """
    if not line_cnt:
        return ABSENT, "图内无 LINE/LWPOLYLINE/POLYLINE 实体"
    inc, exc = wire_layer_candidates(line_cnt, wire_kw_re)
    top = "，".join(f"{ly}={n}" for ly, n in line_cnt.most_common(top_n))
    if inc:
        desc = "，".join(f"{ly}={n}" for ly, n in sorted(inc.items(), key=lambda kv: -kv[1]))
        extra = ("；另有关键词命中但属标注/设备/机电类的层（已排除）：" +
                 "，".join(f"{ly}={n}" for ly, n in sorted(exc.items(), key=lambda kv: -kv[1]))) if exc else ""
        return PRESENT, (f"存在电信连线图层候选（按线段数降序）：{desc}{extra}；"
                         f"全图线段图层 top{top_n}：{top}")
    return ABSENT, (f"无图层名含通信类关键词（{wire_kw_re.pattern}）且非标注/设备类的线段图层；"
                    f"全图线段图层 top{top_n}：{top}")


def judge_vertical_bus_traceable(segs, fx_positions, sig_wire_status,
                                 wire_layers=None, x_tol=15.0, min_cover=0.5):
    """竖干可追踪：连线层上存在竖向线段、可识别端点/断口，**且与分纤箱相连**。

    关键判据是「箱级覆盖率」而非「图里有没有竖线」—— 竖线法的测量对象是**每个分纤箱的竖干**，
    全图竖线再多，若与箱不相连也构不成覆盖判据。

    两处必须做对（2026-09-13 实测修正）：
      ① **segs 必须按连线层候选过滤**。segs 由 collect_line_and_segments 全图采集，
         每条竖线自带图层名（元组第 4 位）。不过滤的话，建筑轴网/墙体/楼梯/图框的竖线
         会一并计入（实测某图：全图竖线段 24285 条 / x 聚簇 127 个，布线层占比极小，
         覆盖率被稀释到 4%）。
      ② **锚点必须是图面箱位置**，不是配纤表里的编号坐标。实测某图配纤表编号
         x≈24700~24950 而图面箱在 x≈25190~27000，相差 500+ 单位 —— 拿表格坐标去配
         图面竖线，覆盖率必然 0%。锚点由 pick_fx_anchors 负责。

    断口**不作硬门槛**：竖线可能连续无断口（线型间隙与楼层分界无法用同一阈值区分，
    实测某图 12 个簇按 gap=1 会切出大量伪断口），此时改用簇的 y 上下端点配合区间法定层。
    判据只要求「箱锚点能配到竖干节」（二维 (x, y) 配对，一井两箱各自配各自的节）。

      覆盖率 = 0             → absent
      0 < 覆盖率 < min_cover → variant（仅少数箱可用，须人工确认）
      覆盖率 >= min_cover    → present
    """
    if sig_wire_status != PRESENT:
        return ABSENT, ("前置信号 dedicated_wire_layer 不成立 —— 竖干无法与建筑/专业线区分，"
                        "竖线法不可用")
    if not segs:
        return ABSENT, "连线图层内未发现竖线段（x 跨度≤阈值且 y 跨度更大），竖线法前置不成立"

    # ① 按连线层候选分组（segs 元组第 4 位为图层名）
    layer_note = ""
    if wire_layers:
        wl = set(wire_layers)
        kept = [s for s in segs if len(s) > 3 and s[3] in wl]
        if kept:
            layer_note = f"；已按连线层候选过滤 {len(segs)}→{len(kept)} 条（候选 {len(wl)} 层）"
            segs = kept
        else:
            layer_note = (f"；⚠ 连线层候选 {sorted(wl)[:6]} 内无竖线段，已回退全图判定，"
                          f"结果须人工复核")

    by_layer = {}
    for s in segs:
        if len(s) > 3:
            by_layer.setdefault(s[3], []).append(s)
    if not by_layer:
        return ABSENT, "竖线段元组缺少图层信息，无法按连线层分组；竖线法前置不成立"

    # ② 逐候选层试配：哪一层的竖线簇能对上最多箱锚点，就以哪层为主层
    #    （多候选层叠加会把别层（如系统图示意连线）的杂簇混进来，聚簇数虚高）
    per_layer = []
    for ly, ls in by_layer.items():
        cl = _cluster_segments(ls, x_tol)
        pairs, delta, tol, dropped = _pair_anchors_to_clusters(cl, fx_positions, x_tol)
        units = [u for c in cl for u in _split_cluster_units(c, FX_UNIT_Y_GAP)]
        per_layer.append({"层": ly, "竖线段": len(ls), "簇": cl, "节": units,
                          "配对": pairs, "偏移": delta, "容差": tol, "剔除": dropped})
    # 配对最多者优先；同分取簇更少者（更干净），再同则取线段更多者
    per_layer.sort(key=lambda d: (-len(d["配对"]), len(d["簇"]), -d["竖线段"]))
    best = per_layer[0]

    layer_summary = "，".join(
        f"{d['层']}={len(d['配对'])}/{len(fx_positions)}(簇{len(d['簇'])}/节{len(d['节'])})"
        for d in per_layer[:5])
    det = (f"竖线段 {len(segs)} 条 / 候选层 {len(by_layer)} 个｜各层配对：{layer_summary}"
           + layer_note)

    if not fx_positions:
        if best["簇"]:
            return VARIANT, det + "；但未取得分纤箱锚点，无法验证竖干是否与箱相连（可用性须人工确认）"
        return ABSENT, det + "；无竖线簇，覆盖分界无从判定"

    pairs = best["配对"]
    dropped = best.get("剔除", [])
    n_eff = len(fx_positions) - len(dropped)
    ratio = (len(pairs) / n_eff) if n_eff else 0.0
    delta = best["偏移"]

    # 逐箱竖干明细（竖干按 y 断口切节，节=独立配对单元；y 端点供第二步用区间法定层）
    detail = []
    for i, j, d in pairs:
        ux, ulo, uhi, unseg = best["节"][j]
        detail.append(f"锚({fx_positions[i][0]:.0f},{fx_positions[i][1]:.0f})→节y {ulo:.0f}~{uhi:.0f}({unseg}段)")
    drop_note = ""
    if dropped:
        ds = "、".join(f"({fx_positions[i][0]:.0f},{fx_positions[i][1]:.0f})距最近竖干{dd:.0f}"
                       for i, dd in dropped[:4])
        drop_note = f"；剔除区域外锚点 {len(dropped)} 个：{ds}" + ("…" if len(dropped) > 4 else "")
    shift_note = (f"；锚点↔节心固有偏移 {delta:+.1f}（超出 x_tol={x_tol:.0f}，已校正后配对）"
                  if abs(delta) > x_tol else f"；锚点↔节心偏移 {delta:+.1f}")
    det += (f"；主层 [{best['层']}]：箱锚点 {len(fx_positions)} 个（有效 {n_eff}），"
            f"配对 {len(pairs)} 节（覆盖率 {ratio:.0%}）{shift_note}{drop_note}"
            f"｜逐箱竖干：" + "、".join(detail[:12]) + ("…" if len(detail) > 12 else ""))

    if ratio == 0:
        return ABSENT, det + " → 竖干未与任何分纤箱相连，竖线法不可用"
    if ratio < min_cover:
        return VARIANT, det + f" → 覆盖率低于 {min_cover:.0%}，竖线法仅对少数箱可用，须人工确认"
    return PRESENT, det + " → 竖干与箱的连接覆盖率达标，竖线法可用"


def judge_intake_table(project_dir):
    """项目另附《楼宇信息采集表》（xls）：不在 DXF 内，须显式提供项目目录。

    排除规则（见下方常量）：本技能**自己的产物与归档副本**绝不算甲方采集表 ——
    采集表是随图纸提供的输入，本链路输出反过来当输入构成论证闭环。
    """
    if not project_dir:
        return UNKNOWN, ("未提供 --project-dir，无法检查项目是否附《楼宇信息采集表》；"
                         "若项目附有该表，请补充该参数后重跑本脚本")
    p = Path(project_dir)
    if not p.is_dir():
        return UNKNOWN, f"--project-dir 不存在或不是目录：{project_dir}"
    # 2026-09-13 P0-4：rglob("*") 会深入 run_YYYYMMDD/ 等本技能运行产物目录，
    # 把旧跑输出的表格（如 *_标准地址表.xlsx）误判成「项目另附的采集表」（variant 假阳性）。
    # 采集表是甲方随图纸提供的输入，只应存在于项目根目录（或明确的资料子目录），
    # 产物目录一律跳过；同时排除本技能已知输出文件名前缀，双保险。
    #
    # 2026-09-18 补（实测某项目）：原规则只跳过 `run_`/`_diag` 与写死的 `g_标准地址表` 前缀，
    #   而项目自带的归档目录（如 `_历史产物_归档\`）与项目名式产物（如 `<项目>标准地址表.xlsx`）
    #   都漏过 ⇒ 本技能**自己的产物**被当成「甲方采集表」列进 evidence。危害不止是假阳性：
    #   下游一旦真去读它，等于**用本链路的输出反过来当本链路的证据**（论证闭环、不可复现）。
    #   故改为按「归档/备份目录特征」+「本技能产物命名特征」判定，与项目名解耦。
    _SKIP_DIRS = ("run_", "_diag", ".workbuddy", "__pycache__", "backup", "_backup")
    _SKIP_DIR_KWS = ("归档", "备份", "历史产物", "archive", "bak", "_temp", ".temp", "out_", "_out")
    _SKIP_PREFIXES = ("g_标准地址表", "fx_map", "cov_full")
    _SKIP_NAME_KWS = ("标准地址表", "地址树", "地址簿", "batch_overview", "pipeline_timing")
    def _is_intake_candidate(f):
        if not f.is_file() or f.suffix.lower() not in (".xls", ".xlsx", ".csv"):
            return False
        parts = {seg.lower() for seg in f.relative_to(p).parts[:-1]}
        if any(d.startswith(_SKIP_DIRS) or d == _SKIP_DIRS for d in parts):
            return False
        if any(kw in d for d in parts for kw in _SKIP_DIR_KWS):
            return False
        n = f.name.lower()
        if any(n.startswith(pre) for pre in _SKIP_PREFIXES):
            return False
        if any(kw in f.stem for kw in _SKIP_NAME_KWS):
            return False
        return True
    sheets = [f for f in p.rglob("*") if _is_intake_candidate(f)]
    if not sheets:
        return ABSENT, f"项目目录下未发现表格文件（已扫描 {project_dir}，已排除 run_*/_diag 等产物目录）"
    # 2026-09-17：改为报**相对路径**（相对 project_dir），不再只报文件名。
    #   实测某项目根目录与 _历史产物_归档\ 各有一份同名 xlsx，只报文件名会打出
    #   两个完全相同的名字——看着像脚本重复枚举（歧义），实为两处各一份。
    #   带相对路径后一眼可辨，且比绝对路径短。
    _rel_names = []
    for _f in sheets[:5]:
        try:
            _rel_names.append(str(_f.relative_to(project_dir)))
        except Exception:
            _rel_names.append(_f.name)
    names = "、".join(_rel_names)
    more = f"（另有 {len(sheets) - 5} 个）" if len(sheets) > 5 else ""
    return VARIANT, (f"项目目录下发现 {len(sheets)} 个表格文件：{names}{more}；"
                     f"是否含『小区名称/楼宇名称/单元数/层数/每层住户数』列须人工确认")


# ============================================================
# 候选方法生成 / 档案对比 / 门禁
# ============================================================

def build_steps(sig, ctx):
    """按子任务生成候选方法列表。requires 引用信号名，可用性由 requires 是否成立决定。"""
    s = {k: v[0] for k, v in sig.items()}
    wire_suggest = ctx.get("wire_layer_suggest")
    return {
        "解析": {
            "楼栋分组": {
                "candidates": [
                    {"role": "primary", "method": "标题锚点+x中分",
                     "requires": ["cluster_layout"], "script": "parse_dxf_structured.py",
                     "params": {"title_pattern": "由探查枚举全部楼栋标题实际写法后确定"}},
                    {"role": "alternate", "method": "标题枚举+共享标题展开",
                     "requires": ["shared_drawing"], "script": "parse_dxf_structured.py",
                     "params": {"title_pattern": "同上；共享标题须按楼栋号逐一展开"}},
                ],
                "cross_check": "两种分组结果不一致时不得自动择一，列入待确认项交用户裁定",
            },
            "户数提取": {
                "candidates": [
                    {"role": "primary", "method": "读取标注（直读『X户』）",
                     "requires": ["household_annotation"], "script": "parse_dxf_structured.py",
                     "params": {"hu_pattern": "由探查采样后确定"}},
                    {"role": "alternate", "method": "读取标注（图签形态 N层/M户）+ 采集表三来源协议",
                     "requires": ["titleblock_annotation"], "script": "read_titleblock_households.py",
                     "params": {"geometric_tolerances": "由该脚本 --probe 量测，不设默认值"}},
                    # 2026-09-16：**图标法此前完全不在候选表里**（画像 household_annotation /
                    #   fiber_length_vshape 均 absent 的图上，实际走的就是"贴皮线末端的
                    #   家居配线箱图标计数"，而候选表只指到 count_households.py 皮线计数 ——
                    #   选法结论与实际执行脚本脱节，Agent 只能自己另找脚本）。
                    # 2026-09-16 用户裁决：**区间法计户数时，凡图上存在家居配线箱图标，
                    #   优先数图标、不得再数皮线**（图标每户一个、贴户端；皮线列会跨带串栋）。
                    #   故图标法排在皮线法**之前**，并挂 box_icon_annotation 前置信号。
                    # 2026-09-16 用户口径（第三轮）：**图标法是区间法的一种** —— 锚点取家居配线箱
                    #   图标；皮线法是同一区间法的另一个锚点，两者原理同为「锚点落楼层带」。
                    #   故图标法与皮线法**共享区间法公共前置 floor_scale**（无楼层刻度则建不成
                    #   楼层带）；图标法另需自己的锚点前置（dedicated_wire_layer +
                    #   box_icon_annotation，两者含义见 judge_box_icon_annotation 注释）。
                    #   实测依据：count_box_icons.py 的每列结果均带「刻度列x」、「合计 = 贴末端
                    #   图标数」、「逐层」按楼层带展开；无刻度列时其 `if sc` 分支使合计恒为 0
                    #   —— 该法产出**全部来自落楼层带**，故 floor_scale 是硬前置而非可选。
                    {"role": "alternate", "method": "图标法（贴皮线末端的家居配线箱图标计数）",
                     "requires": ["floor_scale", "dedicated_wire_layer", "box_icon_annotation"],
                     "script": "count_box_icons.py",
                     "params": {"wire_layer": "皮线图元图层（探查确定）",
                                "insert_blocks": "箱体块名；块含 attrib 时优先按属性值识别"
                                                 "（如 A=家居配线箱 / $TEXT$=HDD），比只按块名更稳",
                                "floor_layer": "楼层刻度列图层；刻度列配对偏移异常会自动告警",
                                "region_y": "系统图区 y 范围（默认由楼层刻度列界定）",
                                "*N": "乘数标注不得自行相乘，须列入待裁决项"}},
                    # 皮线计数：**仅当图标法不可用时**才可选（用户裁决 2026-09-16）。
                    #   注意「图标法不可用」≠「无图标标识」：图标法的 requires 是**三前置**
                    #   （区间法公共前置 floor_scale + 专用连线层 + 图标标识）。图上只有
                    #   图标标识、而无皮线图元时，
                    #   count_box_icons.py 会因"找不到任何皮线图元"硬失败 rc=2、产不出结果
                    #   （实测某类图纸即此形态），此时皮线法仍应回落 —— 本图若确无皮线图元，
                    #   皮线法自会报空，由 count_households.py 的出表守门拦下。
                    {"role": "alternate", "method": "区间法（皮线锚点落楼层带计数）",
                     "requires": ["floor_scale"], "script": "count_households.py",
                     "params": {"assign": "按楼层带归属（带由本图楼层刻度建成；不得用最近楼层线法）",
                                "前置否决": "**图标法可用时不得选本法**（box_icon_annotation 与 "
                                            "dedicated_wire_layer 同时成立 → 数图标，不数皮线）；"
                                            "图标法不可用时允许回落"}},
                ],
                "cross_check": ("**本子任务按候选顺序取首个可用者，非并跑**（2026-09-16 用户裁决）："
                                "①有『X户』标注或图签『N层/M户』→ 直读；②两者皆无 → 区间法，"
                                "其中图标法（**区间法公共前置 floor_scale** + 专用连线层 + "
                                "图标标识，三前置齐备）优先于皮线计数，"
                                "图标法不可用才回落皮线。划定实体口径后仍须与『X户』直读值（若有）"
                                "对账，不一致不得自动择一，交用户裁定"),
            },
            "覆盖判定": {
                "candidates": [
                    {"role": "primary", "method": "读取标注（图上直写箱体覆盖起止层）",
                     "requires": ["cover_range_annotation"], "script": "parse_dxf_structured.py",
                     "params": {"cover_range_pattern": "由探查采样后确定（形如『覆盖 -1F~9F』）"}},
                    {"role": "alternate", "method": "V型计算（皮线米数谷底→箱安装层）",
                     "requires": ["fiber_length_vshape", "floor_scale"],
                     "script": "analyze_coverage_vshape.py",
                     "params": {"cable_pattern": "由探查采样后确定",
                                "include_basement": "默认 False —— 覆盖范围每一项都必须来自米数列实际存在的行",
                                "floor_scale": "谷底定层须走区间法（floor_scale），不得按米数列排序硬切"}},
                    {"role": "alternate", "method": "竖线法（竖干断口 + 区间法定层·三步走）",
                     "requires": ["dedicated_wire_layer", "vertical_bus_traceable", "floor_scale"],
                     "script": "analyze_coverage.py",
                     "params": {"wire_layer": wire_suggest or "必须显式传入连线图层名（本图探查未给出候选）",
                                "floor_scale": "三步走第②③步用区间法测安装楼层与断头端点所在层"}},
                ],
                "cross_check": ("两者 requires 同时成立时必须并跑比对：覆盖楼层集合一致才通过；"
                                "不一致列入待确认。仅一个前置成立时用该法并在输出标注『无第二来源』"),
                "notes": ["方法按测量原理命名，禁止用小区名冠名",
                          "竖线法/V型计算只测覆盖楼层；区间法只测户数与安装楼层；不得混用",
                          "总图（fx_overview_map）只提供编号/归属/安装楼层，不含覆盖范围 —— 不能用于校验覆盖"],
            },
            "分纤箱提取": {
                "candidates": [
                    {"role": "primary", "method": "读取标注（总图对照表查表：编号→楼栋/单元/安装楼层）",
                     "requires": ["fx_overview_map"], "script": "extract_fx_map.py",
                     "params": {"fx_pattern": "由探查采样后确定",
                                "bldg_pattern": "由探查枚举实际写法后确定",
                                "proximity_tol": "由探查实测 FX 编号与最近楼栋标注距离后确定"}},
                    {"role": "alternate", "method": "区间法（编号文字/箱符号落楼层带定安装楼层）",
                     "requires": ["floor_scale"], "script": "analyze_coverage.py",
                     "params": {"fx_symbol_layer": ctx.get("fx_symbol_layer_suggest") or "探查未给出候选图层",
                                "fx_pattern": "由探查采样后确定",
                                "bldg_map": "本图无总图时留空，归属改用编号与楼栋/单元标注的坐标关联"}},
                ],
                "cross_check": "两条来源的归属 / 安装楼层不一致时不得自动择一，列入待确认项",
            },
        },
        "自检": {
            "checks": [
                "两类图纸交叉验证（总图（若有）/ 系统图，户数以系统图为准）",
                "安装楼层双来源校验（总图直写 vs 区间法，以总图为准并暴露冲突）",
                "楼层完整性（连续性 / 无混入）",
                "覆盖范围第二来源核对（两法前置都成立时必须双跑）",
                "户数守恒（源户数 vs 生成行数）",
                "矛盾检查",
            ]
        },
        "出表": {
            "method": "standard_assembly", "script": "gen_addressbook.py",
            "params": {"template": "assets/标准地址表模板.xlsx", "cover_rule": "floor100"},
            "output": "xlsx（每户一行，9 级地址 + 分纤箱编号）",
        },
    }


def load_signal_consequences(methods_dir):
    """读 methods/signals.json 的 consequence（信号状态 → 下游后果 + 既定处置）。

    单一真源纪律：consequence 只在 methods/signals.json 定义一处，本脚本只读不写副本。
    读不到时返回空 dict（**不阻塞**）：后果是"提效信息"，缺失不应让画像生成失败。
    """
    try:
        p = Path(methods_dir) / "signals.json"
        j = json.loads(p.read_text(encoding="utf-8-sig"))
        out = {}
        for k, v in (j.get("signals") or {}).items():
            c = v.get("consequence")
            if isinstance(c, dict):
                out[k] = c
        return out
    except Exception as e:                                               # noqa: BLE001
        print(f"[WARN] 读取 signals.json 的 consequence 失败（不影响画像其余部分）：{e}")
        return {}


# 信号**组合** → 下游必然出现的情况 + 既定处置。
#   与 consequence 的分工：consequence 是「单个信号某状态」的后果；
#   本表是「多个信号同时成立」才会出现的情况（组合条件无法由单信号表达）。
#   只写通用规则：不含项目名、楼号、坐标、个案数值。
SIGNAL_RISK_RULES = [
    {
        "id": "shared_system_drawing",
        "when": lambda s: s.get("shared_drawing") == PRESENT,
        "情况": "多栋共享同一系统图 —— 楼层刻度列 / 箱符号可能跨栋共用；"
                "逐层户数须按各楼标题邻域直读，不能用『一栋一列』去切",
        "信号依据": "shared_drawing = present",
        "处置": "走 assemble_households.py 的克隆留痕路径（一栋一份留痕）；coverage 显式注明"
                "『箱位跨栋共用』；**属图面固有形态，不得为『把结构搞清楚』自行重建图区、"
                "不得反复写探查脚本**；共用关系与配纤表/覆盖区间不一致时按 §5.3 第④类报人",
    },
    {
        "id": "no_floor_scale",
        "when": lambda s: s.get("floor_scale") == ABSENT,
        "情况": "无可用楼层刻度列 → 区间法前置不成立",
        "信号依据": "floor_scale = absent",
        "处置": "每层户数归属 / 箱安装层 / 竖线法定层三处同时退化，只剩纯文字直读；"
                "**不得强跑区间法**（归层恒为 0，会把空值当数据）",
    },
    {
        "id": "no_wire_layer",
        "when": lambda s: s.get("dedicated_wire_layer") == ABSENT,
        "情况": "无专用电信连线图层 → 竖线法不可用",
        "信号依据": "dedicated_wire_layer = absent",
        "处置": "改用文字类方法（V 型 / 直读）；**不得扫全图线段找主干**"
                "（会把建筑线、图框、家具线当成电信主干）",
    },
    {
        "id": "no_overview_map",
        "when": lambda s: s.get("fx_overview_map") == ABSENT,
        "情况": "无分纤箱总图（或非对照表形态）→ 箱编号缺独立对照来源",
        "信号依据": "fx_overview_map = absent",
        "处置": "箱信息只从各楼系统图取；箱—楼归属与安装层缺第二来源，"
                "结论须写明『未经交叉验证』，不得当作已印证上报",
    },
    {
        "id": "no_household_source",
        "when": lambda s: (s.get("household_annotation") == ABSENT
                           and s.get("box_icon_annotation") != PRESENT),
        "情况": "户数既无『X户』直读、又无可用图标法 → 户数来源不足",
        "信号依据": "household_annotation = absent 且 box_icon_annotation ≠ present",
        "处置": "户数只能靠皮线法推算；**任何户数结论必须写明取自哪种测量方法**；"
                "若皮线法前置亦不成立，按门禁 rc=2 报人，不得估算或沿用他图数值",
    },
    {
        "id": "variant_box_icon",
        "when": lambda s: s.get("box_icon_annotation") == VARIANT,
        "情况": "家居配线箱图标为 variant（有标识但几何判据不成立，疑『只画方块、不写字』画法）",
        "信号依据": "box_icon_annotation = variant",
        "处置": "**variant 不算前置成立**，选法不会自动切图标法；须现场确认画法后方可采信，"
                "不得按 present 处理",
    },
    {
        "id": "coverage_no_judge",
        "when": lambda s: (s.get("cover_range_annotation") == ABSENT
                           and s.get("fiber_length_vshape") == ABSENT
                           and s.get("vertical_bus_traceable") != PRESENT),
        "情况": "覆盖范围三条候选路径（直读标注 / V 型 / 竖线法）均不成立 → 覆盖无判据",
        "信号依据": "cover_range_annotation = absent 且 fiber_length_vshape = absent "
                    "且 vertical_bus_traceable ≠ present",
        "处置": "覆盖判定不可用，按门禁 rc=3 记『本图不提供该子任务』并声明降级路径；"
                "**不得用『户数×层数守恒』以外的自由推算填充覆盖值**",
    },
]


def forecast_risks(sig):
    """按 SIGNAL_RISK_RULES 给出本图下游**必然**出现的情况与既定处置。

    目的：把「本图形态 → 下游会发生什么」从每轮的临场推理，变成一次算清、随画像落盘。
    返回 list[dict]，每条含 情况 / 信号依据 / 处置。
    """
    st = {k: v[0] for k, v in sig.items()}
    out = []
    for r in SIGNAL_RISK_RULES:
        try:
            hit = bool(r["when"](st))
        except Exception:                                                # noqa: BLE001
            hit = False
        if hit:
            out.append({"id": r["id"], "情况": r["情况"],
                        "信号依据": r["信号依据"], "处置": r["处置"]})
    return out


def compare_archives(sig, methods_dir):
    """与已沉淀的图纸档案逐份比对，返回按一致率降序的结果（§五.3『对比』的物化）。"""
    results = []
    for mp in sorted(Path(methods_dir).glob("*/manifest.json")):
        try:
            arch = json.loads(mp.read_text(encoding="utf-8"))
        except Exception:
            continue
        a_sig = arch.get("signals") or {}
        common = sorted(set(a_sig) & set(sig))
        if not common:
            continue
        diff = [k for k in common if a_sig[k].get("status") != sig[k][0]]
        results.append({
            "档案": arch.get("name") or mp.parent.name,
            "目录": mp.parent.name,
            "比对信号数": len(common),
            "一致数": len(common) - len(diff),
            "一致率": round((len(common) - len(diff)) / len(common), 3),
            "差异项": diff,
        })
    results.sort(key=lambda r: (-r["一致率"], -r["一致数"], r["档案"]))
    return results


def evaluate_gate(steps, sig):
    """门禁：给出「子任务 → 本图能否跑」的判定，并区分**未作答**与**不适用**。

    二者性质完全不同，处置也不同：
      · 未作答（blocked）—— 候选前置信号里含 unknown（判不了）。属探查未完成，
        必须补探查后重跑 plan，第二步入口 rc=2 中止。
      · 不适用（skipped）—— 候选前置信号**全部明确 absent**（图上确实没有）。
        属"本图纸未提供这一路数据"，**不是缺陷**：放行降级，入口 rc=3 表示该命令不适用。
    """
    s = {k: v[0] for k, v in sig.items()}
    unavail = []
    for step_name, sub in (steps.get("解析") or {}).items():
        cands = sub.get("candidates") or []
        if not cands:
            continue

        def usable(c):
            return all(s.get(r, UNKNOWN) == PRESENT for r in c.get("requires", []))

        if any(usable(c) for c in cands):
            continue
        req_state = {}
        for c in cands:
            for r in c.get("requires", []):
                req_state[r] = s.get(r, UNKNOWN)
        # 信号都判出来了（absent/variant 都算判出）→ 本图不提供这一路 → 不适用；
        # 只要含 unknown（根本没判出来）→ 未作答，须补探查。
        nature = ("未作答" if any(v == UNKNOWN for v in req_state.values())
                  else "不适用")
        unavail.append({
            "子任务": step_name,
            "性质": nature,
            "原因": "全部候选的前置信号均不成立：" + "；".join(
                f"{c['method']} ← requires={c.get('requires', [])}" for c in cands),
            "候选信号实况": req_state,
            "处置": ("本图未提供该子任务所需数据（候选前置信号均不成立，且全部已判出）"
                     "→ 该步在本图不适用，跳过并声明降级路径，**不视为错误**；"
                     "若人工判定某候选其实可用，去掉 --profile 直跑并自行标注可用性"
                     if nature == "不适用" else
                     "存在 unknown 信号（探查未判定）→ 须补探查后重跑 plan"),
        })
    blocked = [u["子任务"] for u in unavail if u["性质"] == "未作答"]
    skipped = [u["子任务"] for u in unavail if u["性质"] == "不适用"]
    return {
        "status": "fail" if blocked else "pass",
        "blocked_steps": blocked,
        "skipped_steps": skipped,
        "unavailable_steps": [u["子任务"] for u in unavail],
        "details": unavail,
        "含义": ("fail = 存在**未作答**子任务（信号 unknown，判不了）→ 须补探查。"
                 "skipped_steps 非空**不算 fail**：这些子任务所需数据本图未提供"
                 "（候选前置信号已判出且均不成立），属合法缺席，"
                 "按申报降级处理（入口 rc=3 不适用）"),
    }


def summarize_profile_name(sig, archives):
    """由命中的信号组合推导形态名（不绑定项目/小区）。"""
    if archives and archives[0]["一致率"] >= 0.8:
        a = archives[0]
        return f"{a['档案']}（与已有档案一致率 {a['一致率']:.0%}）"
    traits = []
    for key, label in (
        ("cluster_layout", "楼-簇布局"), ("shared_drawing", "多栋共享图纸"),
        ("titleblock_annotation", "图签直写规模"), ("household_annotation", "有户数标注"),
        ("fiber_length_vshape", "有皮线米数"), ("dedicated_wire_layer", "有专用连线层"),
        ("box_icon_annotation", "有家居配线箱图标"),
        ("fx_overview_map", "含分纤箱总图"), ("coverage_table", "含覆盖表"),
    ):
        if sig.get(key, (None,))[0] in (PRESENT, VARIANT):
            traits.append(label)
    return ("未归类形态 · " + " + ".join(traits)) if traits else "未归类形态（信号全缺，须人工介入）"


# ============================================================
# Step 1 → Step 2 交接契约（两要素，逐项申报；absent 不阻塞）
# ============================================================

# 选定方法 → 方法池类别（回答"用什么方法统计"必须落到方法池命名上，不许自造方法名）
# 注：**图标法 = 区间法的锚点变体**——原理同为「锚点落楼层带」，只是锚点取家居配线箱图标
# （每户一个、贴皮线末端）而非皮线标注。故 `classify_method("图标法（…）")` 必须归到
# 「区间法」，与 SKILL.md 方法池表「区间法 → ①每层户数（皮线标注 / 家居配线箱图标 落在
# 哪条带）」的既有表述一致；否则选定方法会落到"其他"，下游「安装楼层随选定方法导出」
# 的分支判断随之失配。
_METHOD_POOL_RULES = (
    ("V型", "V型计算"), ("竖线", "竖线法"),
    ("区间", "区间法"), ("图标", "区间法"),
    ("总图对照表", "读取标注（对照表查表）"), ("编号文字", "读取标注 + 坐标关联"),
    ("读取标注", "读取标注"), ("标题", "读取标注 + 坐标分区"),
)


def classify_method(method):
    """把候选方法的自由描述归到方法池命名（读取标注 / 区间法 / 竖线法 / V型计算）。"""
    for kw, pool in _METHOD_POOL_RULES:
        if kw in (method or ""):
            return pool
    return "其他"


def _pick_method(steps, sig, sub):
    """取某子任务的**可用**候选（requires 全部成立），按列表顺序取首个为选定方法。"""
    s = {k: v[0] for k, v in sig.items()}
    cands = ((steps.get("解析") or {}).get(sub) or {}).get("candidates") or []
    usable = [c for c in cands
              if all(s.get(r, UNKNOWN) == PRESENT for r in c.get("requires", []))]
    if usable:
        ch = usable[0]
        return {
            "选定方法": ch["method"],
            "方法池类别": classify_method(ch["method"]),
            "脚本": ch.get("script"),
            "requires": ch.get("requires", []),
            "同可用备选": [{"方法": c["method"], "脚本": c.get("script")} for c in usable[1:]],
            "申报": "已选定",
            "待确认": False,
            "阻塞原因": None,
        }
    req_state = {}
    for c in cands:
        for r in c.get("requires", []):
            req_state[r] = s.get(r, UNKNOWN)
    # 无可用候选的性质：只要信号都**判出来了**（absent/variant 都算判出），
    # 就是"本图不提供这一路"→ 申报 absent（放行 + 降级）；只有 unknown（判不了）才算未作答。
    nature = "unknown" if any(v == UNKNOWN for v in req_state.values()) else "absent"
    return {
        "选定方法": None, "方法池类别": None, "脚本": None, "requires": [],
        "同可用备选": [], "待确认": True,
        "申报": nature,
        "候选信号实况": req_state,
        "阻塞原因": "；".join(
            f"{c['method']} ← requires={c.get('requires', [])}" for c in cands)
        or "该子任务无候选方法",
    }


def build_handoff(sig, steps, ov):
    """生成 Step 1 → Step 2 的交接契约 handoff（两要素，**逐项申报制**）。

    委托人裁定（2026-09-13，含当日语义修正；同日晚再裁定：**不再读取楼层平面图**，
    契约由三要素收缩为两要素，户数以系统图为准）：图纸向第二步（解析）传递的信息
    **至少**包含两项，两项都必须给出明确回答：
      ① 有没有分纤箱总图 —— 提供分纤箱编号与安装位置（楼栋/单元/安装楼层）
      ② 楼内系统图的分纤箱位置 / 覆盖范围 / 每层户数 —— 各用什么方法统计
         （读取标注 / 区间法 / 竖线法 / V型计算）。**② 是必备项**：
         系统图必须给出「分纤箱位置」与「每层户数」的方法，缺任一 ⇒ 不可解析；
         「覆盖范围」允许本图不提供（absent + 降级，不阻塞）

    **关键：这是"申报制"，不是"存在性检查"。** 有的图纸只提供系统图、不提供总图
    —— 这种情况**照样要能往下走**：
      · 有   → 报 present（附证据，指向能提对照表的脚本）；
      · 没有 → 报 absent（附证据，说明"图上确实没有"），并给出**降级路径**：
               本图缺这一路，下游改用现有的什么来校验（原则：以现有图纸为准）；
      · 只有 unknown（判不了 / 没判）才算"未作答"，才阻塞；
        variant（已判出但本路不可用，如竖线覆盖率不足）按"本图不提供"处理，同样放行。

    返回 completeness：
      · ok               = 未作答为空 且 不可解析为空
      · 未作答            → 状态 unknown，须补探查后重跑 plan（入口 rc=2）
      · 不可解析          → ② 三个子任务全部无候选，本图没有任何可解析依据（入口 rc=2）
      · 缺失项及降级路径   → absent 的项；**不阻塞**，入口会打印，下游据此降级
    """
    ov_status = (sig.get("fx_overview_map") or (UNKNOWN,))[0]

    # ---- ① 分纤箱总图 ----
    overview = {
        "要素": "有没有分纤箱总图（集中标注分纤箱编号 + 安装位置）",
        "状态": ov_status,
        "编号可读": bool(ov.get("编号数")),
        "编号数": ov.get("编号数", 0),
        "安装位置": {
            "编号同行的楼栋标注数": ov.get("同行楼栋", 0),
            "编号同行的单元标注数": ov.get("同行单元", 0),
            "编号同行的安装楼层标注数": ov.get("同行楼层", 0),
            "同行判据": f"|dy| ≤ 本图行距 {ov.get('行距', 0):.1f} 且 |dx| ≤ {ov.get('同行x容差', 0):.0f}",
        },
        "依据": ov.get("证据"),
        "下游": "extract_fx_map.py（提取 FX→楼栋/单元/安装楼层 对照表）→ analyze_coverage.py --bldg-map",
    }
    if ov_status not in (PRESENT,):
        overview["注意"] = ("无总图对照表 → 归属只能走几何/编号-符号配对，"
                            "此时 SKILL.md 硬约束②（禁用标题 x 区间硬切）无对照表可依，"
                            "必须把归属依据逐箱写出交人工复核")
        overview["降级"] = ("本图无对照表 → 箱的楼栋/单元/安装楼层归属改用"
                            "**编号与单元/楼栋标注的坐标关联**（逐箱写出依据），"
                            "并与系统图自身读数交叉；成果表归属列须注明"
                            "『依系统图坐标关联，无总图可查表』")

    # ---- ② 系统图选法（**必备项**：三项各用什么方法统计；只申报方法，不出结果）----
    fx_pick = _pick_method(steps, sig, "分纤箱提取")
    # 安装楼层的方法**随选定方法导出** —— 此前固定写「口径B（区间法）」，
    # 而候选池里根本没有区间法候选，契约与方法池自相矛盾（实测暴露）。
    _pool = fx_pick.get("方法池类别") or ""
    install_by = ("读取标注（编号旁直写安装楼层）" if "读取标注" in _pool
                  else "区间法（编号文字/箱符号落楼层带）" if "区间法" in _pool
                  else None)
    sys_methods = {
        "每层户数": _pick_method(steps, sig, "户数提取"),
        "分纤箱位置（安装楼层）": dict(fx_pick, **{"安装楼层方法": install_by}),
        "覆盖范围": _pick_method(steps, sig, "覆盖判定"),
    }

    # 子任务无候选时的降级路径（本图没有这一路 → 下游改用现有的什么来校验）
    _FALLBACK = {
        "每层户数": "本图无户数标注 → 户数不能从本图得出，须另取《楼宇信息采集表》"
                    "或由人工提供；成果表该列须注明来源不是本图",
        "分纤箱位置（安装楼层）": "本图无分纤箱编号可定位 → 箱的位置 / 安装楼层须由人工指定；"
                                  "成果表该列标注『本图未提供』",
        "覆盖范围": "本图既无『箱体覆盖起止层』直写（读取标注），也无皮线米数（V型计算）"
                    "或可追踪竖干（竖线法）→ 跳过覆盖校验，**以现有图纸为准**：用"
                    "「每层户数 × 层数 = 箱容量 × 箱数」守恒关系替代；成果表覆盖范围列"
                    "标注『本图未提供』。若人工判定某候选方法其实可用，"
                    "去掉 --profile 直跑并自行标注可用性",
    }
    for k, v in sys_methods.items():
        if v.get("选定方法"):
            v["申报"] = "present"
        elif v.get("申报") == "absent":
            v["降级"] = _FALLBACK.get(k, "本图未提供该子任务所需数据 → 该列留空并注明来源")
        # 申报 == "unknown" 保持原样 → 计入未作答

    unanswered, unparsable, gaps = [], [], []

    def _register(label, blk):
        st = blk.get("状态")
        if st == UNKNOWN:
            unanswered.append(f"{label}：状态 unknown（未作答 —— 探查没判出来）")
        elif st in (ABSENT, VARIANT):
            gaps.append({"要素": label, "状态": st,
                         "降级": blk.get("降级") or blk.get("注意")
                                 or "本图未提供该要素 → 下游改用现有图纸自身的信息校验"})

    _register("① 分纤箱总图", overview)
    # ② 是**必备项**：系统图必须能给出「分纤箱位置」与「每层户数」两项的测定方法，
    # 二者缺任一 ⇒ 本图没有可用的系统图 ⇒ 不可解析（入口 rc=2）。
    # 「覆盖范围」允许本图不提供 —— 如实申报 absent + 降级路径，不阻塞。
    _MANDATORY_SUB = ("分纤箱位置（安装楼层）", "每层户数")
    for k, v in sys_methods.items():
        if v.get("申报") == "unknown":
            unanswered.append(f"② 系统图选法·{k}：状态 unknown（{v.get('阻塞原因')}）")
        elif v.get("申报") == "absent":
            if k in _MANDATORY_SUB:
                unparsable.append(
                    f"② 系统图选法·{k}：无可用方法（候选前置信号实况 "
                    f"{v.get('候选信号实况') or '—'}）—— **系统图必备**，"
                    f"本图缺少该系统图能力，出不了地址表")
            else:
                gaps.append({"要素": f"② 系统图选法·{k}", "状态": "absent",
                             "降级": v.get("降级")})

    n_sel = sum(1 for v in sys_methods.values() if v.get("选定方法"))
    n_abs = sum(1 for v in sys_methods.values() if v.get("申报") == "absent")
    return {
        "contract": ("Step 1 → Step 2 的交接契约：下列两项必须**逐项申报** —— "
                     "有就报 present（附证据），没有就报 absent（附证据 + 降级路径）。"
                     "**①总图属可选**：absent 不阻塞（图纸本来就可能只给系统图）；"
                     "**②系统图属必备**：必须给出「分纤箱位置」「每层户数」两项的测定方法，"
                     "二者缺任一 ⇒ 不可解析 ⇒ rc=2（「覆盖范围」仍可 absent + 降级放行）。"
                     "只有 unknown（未作答）才 → completeness.ok=false → 第二步入口 rc=2。"
                     "absent 导致某命令在本图不适用时，该命令 rc=3（不适用，非错误）。"),
        "①分纤箱总图": overview,
        "②系统图选法": sys_methods,
        "completeness": {
            "ok": not (unanswered or unparsable),
            "已申报": [f"① 分纤箱总图={overview.get('状态')}",
                       f"② 系统图选法={n_sel}/{len(sys_methods)} 项已选定方法"
                       + (f"、{n_abs} 项申报 absent" if n_abs else "")],
            "未作答": unanswered,
            "不可解析": unparsable,
            "缺失项及降级路径": gaps,
            "说明": ("申报制：present / absent / variant 都是合法作答，absent 只意味着本图不提供"
                     "这一路，**不阻塞**；未作答（unknown）= 判不了，才须补探查。"
                     "缺失项的降级路径已逐条给出，下游按「以现有图纸为准」执行。"),
        },
    }


# ============================================================
# 主流程
# ============================================================

def main():
    ap = argparse.ArgumentParser(
        description="FTTH 图纸画像生成（Step 1a 探查的选法产物）")
    ap.add_argument("--dxf", required=True, help="输入 DXF 文件路径")
    ap.add_argument("--out", required=True, help="输出 profile.json 路径")
    ap.add_argument("--probe", default=None,
                    help="已生成的 probe.json（复用其文字样例 + suggested_params）")
    ap.add_argument("--config", default=None,
                    help="probe 输出的配置 JSON（suggested_params 来源之一）；"
                         "与 --probe 同给时 --config 优先")
    ap.add_argument("--project-dir", default=None, help="项目目录（检测《楼宇信息采集表》）")
    ap.add_argument("--text-layer", default=None, help="文字图层，逗号分隔；缺省不限图层")
    ap.add_argument("--text-type", default=None, help="文字实体类型，逗号分隔；缺省 TEXT,MTEXT")
    ap.add_argument("--title-pattern", default=None, help="楼栋标题正则")
    ap.add_argument("--fx-pattern", default=None, help="分纤箱编号正则（缺省 FX\\d+#?）")
    ap.add_argument("--wire-keywords", default=None, help="连线图层关键词正则（覆盖内置通用清单）")
    ap.add_argument("--vert-dx", type=float, default=3.0, help="竖线段 x 跨度阈值")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    log = setup_logger("plan_methods", args.verbose)
    methods_dir = Path(__file__).resolve().parent.parent / "methods"
    # 2026-09-17：后果台账（信号状态 → 下游后果 + 既定处置），单一真源在 methods/signals.json
    _conseq = load_signal_consequences(methods_dir)
    wire_kw_re = re.compile(args.wire_keywords or DEFAULT_WIRE_KEYWORDS)
    fx_re = re.compile(args.fx_pattern or RE_DEFAULT_FX)

    # ---- 0. 回填 probe/config 已探明的检测类参数（仅补命令行未指定的项）----
    #    2026-09-16 修复 P0-3，详见 load_suggested_from_probe 的说明。
    suggested = load_suggested_from_probe([args.config, args.probe])
    _filled = []
    for _k in ("text_layer", "text_type", "title_pattern", "fx_pattern"):
        if getattr(args, _k, None) in (None, "", []):
            _v = suggested.get(_k)
            if _v not in (None, "", []):
                setattr(args, _k, _v)
                _filled.append(_k)
    _param_src = ("--config" if args.config else ("--probe" if args.probe else None))
    if _filled:
        log.info("[param] 自 %s 的 suggested_params 回填命令行未指定的检测类参数：" % _param_src)
        for _k in _filled:
            log.info("        %-14s = %r" % (_k, getattr(args, _k)))
    else:
        log.info("[param] 无 suggested_params 可回填（命令行已给全，或来源未含建议值）")

    # ---- 1. 取文字：优先复用 probe.json / config.json，否则现场采集 ----
    _probe_like = args.probe or args.config
    texts = load_texts_from_probe(_probe_like) if _probe_like else None
    if texts:
        log.info(f"复用 probe.json 的文字样例：{len(texts)} 条")
        # 按 --text-layer 收窄：probe 的「全量文字样例」含全部图层（暖通/图签栏/机电…），
        # 不收窄会把非 FTTH 文字算进信号判定 —— 实测稳健 x 跨度被撑到 142 万（真实约 2.2e3），
        # 「同行 x 容差」随之放大到 21 万，图签栏标注被误判成"与编号同行"。
        if args.text_layer:
            want = {s.strip() for s in args.text_layer.split(",") if s.strip()}
            kept = [t for t in texts if (t.get("层") or "") in want]
            if kept:
                log.info(f"按 --text-layer 收窄文字样例：{len(texts)} → {len(kept)} 条"
                         f"（图层 {'、'.join(sorted(want))}）")
                texts = kept
            else:
                log.warning(f"--text-layer={args.text_layer} 在文字样例中无命中，未收窄")
    else:
        if _probe_like:
            log.warning(f"probe.json 未提供可用文字样例，改为现场采集：{_probe_like}")

    # ---- 2. 读 DXF：线段图层分布 + 竖线段（Step 1a 第 5 项，原 probe 缺此项）----
    log.info(f"读取 DXF：{args.dxf}")
    doc, msp = load_dxf(args.dxf, log)
    line_cnt, segs = collect_line_and_segments(msp, args.vert_dx)
    log.info(f"线段实体 {sum(line_cnt.values())} 条，分布于 {len(line_cnt)} 个图层；"
             f"竖线段 {len(segs)} 条")

    if texts is None:
        layers = [s.strip() for s in args.text_layer.split(",")] if args.text_layer else None
        types = [s.strip() for s in args.text_type.split(",")] if args.text_type else list(DEFAULT_TEXT_TYPES)
        texts = collect_texts(msp, layers, types)
        log.info(f"现场采集文字 {len(texts)} 条")

    # ---- 3. 逐信号判定 ----
    titles = find_titles(texts, args.title_pattern, log)

    # 分纤箱锚点：优先图面箱文字，退化才用编号（后者可能落在配纤表里）
    fx_positions, fx_anchor_src, fx_anchor_warn = pick_fx_anchors(texts, fx_re)
    if fx_anchor_warn:
        log.warning("[ANCHOR] " + fx_anchor_warn)
    log.info(f"[ANCHOR] 分纤箱锚点 {len(fx_positions)} 个 ← {fx_anchor_src}")

    # 连线层候选：供 dedicated_wire_layer 与 vertical_bus_traceable 共用（同一次筛选）
    wire_inc, wire_exc = wire_layer_candidates(line_cnt, wire_kw_re)

    sig = {}
    sig["cluster_layout"] = judge_cluster_layout(texts, titles)
    sig["shared_drawing"] = judge_shared_drawing(titles)
    sig["household_annotation"] = judge_household_annotation(texts)
    sig["fiber_length_vshape"] = judge_fiber_length_vshape(texts)
    sig["coverage_table"] = judge_coverage_table(texts)
    sig["floor_scale"] = judge_floor_scale(texts)
    sig["cover_range_annotation"] = judge_cover_range_annotation(texts)
    ov_stats = inspect_overview_map(texts, fx_re, titles)
    sig["fx_overview_map"] = judge_fx_overview_map(ov_stats)
    sig["titleblock_annotation"] = judge_titleblock_annotation(texts)
    sig["dedicated_wire_layer"] = judge_dedicated_wire_layer(line_cnt, wire_kw_re)
    # 家居配线箱图标（图标法前置）：文字 + INSERT 双路判定。
    # 此前该信号**只在 methods/signals.json 有定义、本脚本从未计算** —— 依赖它的候选
    # requires 恒为 unknown，"户数提取"永远选不到图标法（2026-09-16 接线补齐）。
    insert_idents = collect_insert_idents(msp)
    sig["box_icon_annotation"] = judge_box_icon_annotation(
        texts, insert_idents,
        has_wire_layer=(sig["dedicated_wire_layer"][0] == PRESENT))
    sig["vertical_bus_traceable"] = judge_vertical_bus_traceable(
        segs, fx_positions, sig["dedicated_wire_layer"][0],
        wire_layers=sorted(wire_inc, key=lambda ly: -line_cnt[ly]))
    sig["intake_table"] = judge_intake_table(args.project_dir)

    for k, (st, ev) in sig.items():
        log.info(f"[SIGNAL] {k} = {st} :: {ev}")
        # 2026-09-17：后果与处置随状态一并打印。此前只打「事实」不打「后果」，
        #   导致下游每换一次视角都要重新推演「这意味着什么」（实测重启式梳理占推理 26.3%）。
        _c = (_conseq.get(k) or {}).get(st)
        if _c:
            log.info(f"         └ 后果与处置：{_c}")

    # ---- 4. 候选 / 档案对比 / 门禁 ----
    # 连线图层建议值：关键词命中且非标注/设备类，按线段数降序（wire_inc 已在信号判定前算好）
    # 分纤箱图形符号层建议值（2026-09-16 新增，P0-2）：见 ftth_common.suggest_fx_symbol_layers。
    #   此前 `fx_symbol_layer_suggest` 在本文件**只被读取、从未被写入** → 候选方法里
    #   恒输出「探查未给出候选图层」，测量方无据可依只能猜图层名（实测猜成文字层 →
    #   箱位回退编号文字坐标 → 竖干配对率 0% → 覆盖全空，而脚本仍返回退出码 0）。
    fx_sym_cands = []
    try:
        _g = extract_geom(msp)
        fx_sym_cands = suggest_fx_symbol_layers(
            _g["polylines"], _g["texts"],
            fx_count=len([1 for t in texts if fx_re.search(t.get("内容", ""))]))
    except Exception as _e:                                              # noqa: BLE001
        log.warning("[SYM] 箱符号层候选打分失败（不影响其它信号）：%s" % _e)
    if fx_sym_cands:
        log.info("[SYM] 分纤箱符号层候选：%s"
                 % "，".join("%s=%.2f%s" % (c["层"], c["得分"], "(推荐)" if c["推荐"] else "")
                             for c in fx_sym_cands))
    else:
        log.info("[SYM] 无分纤箱符号层候选（本图箱体可能只写编号文字、无图形符号）")
    _fx_sym_pick = next((c["层"] for c in fx_sym_cands if c["推荐"]), None)
    ctx = {"wire_layer_suggest": ",".join(sorted(wire_inc, key=lambda ly: -line_cnt[ly])) if wire_inc else None,
           "fx_symbol_layer_suggest": _fx_sym_pick}

    steps = build_steps(sig, ctx)
    archives = compare_archives(sig, methods_dir)
    gate = evaluate_gate(steps, sig)
    # 2026-09-17：本图形态 → 下游必然出现的情况（一次算清，避免每轮重新推演）
    risk_fc = forecast_risks(sig)

    # Step 1 → Step 2 交接契约（两要素，逐项申报）——只有"未作答"才拖垮门禁
    handoff = build_handoff(sig, steps, ov_stats)
    if not handoff["completeness"]["ok"]:
        gate["status"] = "fail"
        gate["handoff_blocked"] = True
    gate["handoff_gaps"] = handoff["completeness"]["缺失项及降级路径"]

    # 未判定项：unknown 的信号一律显式列出，不许静默
    unresolved = [{"信号": k, "原因": v[1]} for k, v in sig.items() if v[0] == UNKNOWN]

    # ---- 5. 探查统计（补齐原 probe 缺的第 4/5/6 项）----
    xs = [t.get("x", 0.0) for t in texts] or [0.0]
    ys = [t.get("y", 0.0) for t in texts] or [0.0]
    text_layer_cnt = Counter(t.get("层", "") for t in texts)
    statistics = {
        "文字实体数": len(texts),
        "文字图层分布_top10": [{"层": k, "数": v} for k, v in text_layer_cnt.most_common(10)],
        "线段实体数": sum(line_cnt.values()),
        "线段图层分布_top15": [{"层": k, "数": v} for k, v in line_cnt.most_common(15)],
        "竖线段数": len(segs),
        "坐标范围": {"x": [round(min(xs), 2), round(max(xs), 2)],
                     "y": [round(min(ys), 2), round(max(ys), 2)]},
        "标题锚点数": len(titles),
        "分纤箱编号数": len([t for t in texts if fx_re.search(t.get("内容", ""))]),
        "分纤箱锚点数": len(fx_positions),
        "分纤箱锚点来源": fx_anchor_src,
    }

    # 2026-09-16（12坑复核·坑11）：透传 probe 顶层画像信号（只展示、不参与门禁）。
    #   否决「多地块未分带即 rc=2 中止」的硬门禁方案——地块标注探测存在误报率，
    #   硬中止会把可正常出表的图纸挡在门外；改以画像信号 + 日志提醒的申报制呈现，
    #   与 handoff 的「缺失项降级」哲学一致。
    probe_signals = {}
    if args.probe:
        try:
            with open(args.probe, "r", encoding="utf-8") as _f:
                _pj = json.load(_f)
            for _k in ("titleblock_layer_candidates", "plot_band_annotations",
                       "fx_location_annotation", "fx_symbol_layer_candidates"):
                if _pj.get(_k) is not None:
                    probe_signals[_k] = _pj[_k]
        except Exception:                                                # noqa: BLE001
            pass
    _pba = probe_signals.get("plot_band_annotations")
    if _pba:
        log.info("多地块信号：检出地块/分带标注 %s（%d 条）%s → "
                 "read_titleblock/coverage 建议按带（--band）分别运行"
                 % ("/".join(_pba.get("种类") or []), _pba.get("条数") or 0,
                    ("；" + _pba["缺号提醒"]) if _pba.get("缺号提醒") else ""))
    if str(probe_signals.get("fx_location_annotation") or "").startswith("present"):
        log.info("箱位直读标注信号 present → 建议 extract_fx_locations.py 提取后 "
                 "给 coverage-vshape 传 --fx-locations 做安装层交叉校验")
    if probe_signals.get("titleblock_layer_candidates"):
        log.info("图签候选图层：%s"
                 % (probe_signals["titleblock_layer_candidates"].get("候选图层"),))
    if probe_signals.get("fx_symbol_layer_candidates"):
        log.info("箱符号层候选（probe 画像）：%s"
                 % "，".join("%s=%.2f" % (c.get("层"), c.get("得分", 0.0))
                             for c in probe_signals["fx_symbol_layer_candidates"]))
        _pp = next((c.get("层") for c in probe_signals["fx_symbol_layer_candidates"]
                    if c.get("推荐")), None)
        if _pp and ctx.get("fx_symbol_layer_suggest") and _pp != ctx["fx_symbol_layer_suggest"]:
            log.warning("箱符号层推荐：probe=%s 与 plan=%s 不一致，以 plan 为准，但请人工复核"
                        % (_pp, ctx["fx_symbol_layer_suggest"]))

    profile = {
        "name": summarize_profile_name(sig, archives),
        "kind": "drawing_profile",
        "version": "2.0",
        "source_dxf": str(Path(args.dxf).resolve()),
        "source_probe": str(Path(args.probe).resolve()) if args.probe else None,
        "generated_by": "plan_methods.py",
        "description": ("【本图纸画像，由 Step 1a 探查产出】记录本图 12 个信号的实测状态与"
                        "选定的候选方法。方法按测量原理命名，不绑定任何项目或小区。"),
        "signals": {
            k: dict({"status": v[0], "evidence": v[1]},
                    **({"consequence": (_conseq.get(k) or {})[v[0]]}
                       if (_conseq.get(k) or {}).get(v[0]) else {}))
            for k, v in sig.items()},
        "handoff": handoff,
        "steps": steps,
        "archive_comparison": archives,
        "effective_layers": {
            "note": ("本图探查给出的可用图层。**机器可读**：值为纯层名，无候选时为 null。"
                     "与 param_source.must_probe 分开 —— 后者把「值」和「提示文案」混排，"
                     "机器无法区分，误当参数传会把整句中文送进脚本。"),
            "wire_layer": ctx["wire_layer_suggest"] or None,
            "wire_layer_source": ("dedicated_wire_layer 信号候选（按线段数降序）"
                                  if ctx["wire_layer_suggest"] else None),
            "fx_symbol_layer": ctx["fx_symbol_layer_suggest"] or None,
            "fx_symbol_layer_source": ("probe_signals.fx_symbol_layer_candidates 推荐项"
                                       if ctx["fx_symbol_layer_suggest"] else None),
        },
        "param_source": {
            "note": "本画像不提供任何检测类参数的默认值 —— 图层名、标题写法、编号格式每张图都不同。",
            "must_probe": {
                "text_layer": "含 FTTH 标注的文字图层（见 statistics.文字图层分布）",
                "text_type": "文字实体类型（TEXT / MTEXT）",
                "title_pattern": "楼栋标题正则（须枚举本图**图纸标题**的实际写法：楼栋号 + 系统图/布线图/示意图；楼栋号后可能是 楼/住宅/配套/商业 等；不得用 bldg_pattern 顶替）",
                "floor_pattern": "保持 None（内置统一解析，支持 3F/17F/-1F/B1/B2/WF）",
                "hu_pattern": "层户数标注正则（探查采样后确定）",
                "cable_pattern": "皮线米数标注正则（探查采样后确定）",
                "fx_pattern": "分纤箱编号正则（探查采样后确定）",
                "unit_pattern": "单元标注正则（探查采样后确定）",
                "wire_layer": ctx["wire_layer_suggest"] or "本图探查未给出连线图层候选，须人工指定",
                "fx_symbol_layer": ctx["fx_symbol_layer_suggest"] or "本图探查未给出图形符号层候选（箱体可能只写编号文字、无符号画法）",
                "proximity_tol": "须实测 FX 编号与最近楼栋标注的实际距离后确定，禁止沿用默认值",
            },
            "algorithm_defaults": dict(ALGO_DEFAULTS, note="本技能无不随图纸坐标尺度变化的算法常数：所有阈值均由本图层高自适应推导，量测失败时回退脚本内置默认值并告警，**不得跨图沿用**。判据见 references/measurement_methods.md「param_source 字段表」"),
        },
        "param_source_actual": {
            "note": ("本次 plan 实际生效的检测类参数与来源"
                     "（命令行显式 > probe/config 的 suggested_params > 内置兜底），供核对。"),
            "effective": {k: getattr(args, k, None)
                          for k in ("text_layer", "text_type", "title_pattern", "fx_pattern")},
            "filled_from_params_json": sorted(_filled),
            "params_json_path": _probe_like,
        },
        "gate": gate,
        "risk_forecast": risk_fc,
        "probe_signals": probe_signals,
        "unresolved": unresolved,
        "statistics": statistics,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"已写出图纸画像：{out}")

    # ---- 6. 控制台结论 ----
    log.info("")
    log.info("=" * 68)
    log.info(f"[画像] {profile['name']}")
    n_p = sum(1 for v in sig.values() if v[0] == PRESENT)
    n_a = sum(1 for v in sig.values() if v[0] == ABSENT)
    n_v = sum(1 for v in sig.values() if v[0] == VARIANT)
    n_u = sum(1 for v in sig.values() if v[0] == UNKNOWN)
    log.info(f"[信号] present={n_p} absent={n_a} variant={n_v} unknown={n_u}（共 {len(sig)} 项）")
    if archives:
        a = archives[0]
        log.info(f"[对比] 最接近的档案：{a['档案']}（一致率 {a['一致率']:.0%}，差异项 {a['差异项'] or '无'}）")
    else:
        log.info("[对比] methods/ 下无可比对档案 —— 属**新形态**，按 §五 走完整六步 SOP（需 ⑤沉淀）")
    log.info(f"[门禁] {gate['status'].upper()}｜不可用子任务：{gate['unavailable_steps'] or '无'}")
    for u in gate["details"]:
        log.info(f"       · {u['子任务']}：{u['原因']}")
    _ov = handoff["①分纤箱总图"]
    log.info(f"[交接] ①分纤箱总图={_ov['状态']}（编号 {_ov['编号数']} 条｜同行楼栋 "
             f"{_ov['安装位置']['编号同行的楼栋标注数']} / 单元 "
             f"{_ov['安装位置']['编号同行的单元标注数']} / 楼层 "
             f"{_ov['安装位置']['编号同行的安装楼层标注数']}）")
    log.info("[交接] ②系统图选法：" + "；".join(
        f"{k}→{v['选定方法'] or ('absent（本图未提供）' if v.get('申报') == 'absent' else '未作答')}"
        + (f"（安装楼层：{v['安装楼层方法']}）" if v.get("安装楼层方法") else "")
        for k, v in handoff["②系统图选法"].items()))
    _cp = handoff["completeness"]
    log.info(f"[申报] {'✔ 两项均已作答（' + '；'.join(_cp['已申报']) + '）' if _cp['ok'] else '✗ 未完成'}")
    for g in _cp["缺失项及降级路径"]:
        log.info(f"[降级] {g['要素']} = {g['状态']} → {g['降级']}")
    if _cp["未作答"]:
        log.info(f"[交接] ✗ 未作答（须补探查）：{_cp['未作答']}")
    if _cp["不可解析"]:
        log.info(f"[交接] ✗ 不可解析：{_cp['不可解析']}")
    if unresolved:
        log.info(f"[留白] {len(unresolved)} 项无法判定（已写入 unresolved，不得当作成立）："
                 f"{[u['信号'] for u in unresolved]}")
    if risk_fc:
        log.info(f"[预警] 本图形态已知会在下游出现 {len(risk_fc)} 处情况"
                 f"（**均属图面固有形态，按下列既定处置走即可，不必重新推导**）：")
        for _r in risk_fc:
            log.info(f"       · {_r['情况']}")
            log.info(f"         信号依据：{_r['信号依据']}")
            log.info(f"         既定处置：{_r['处置']}")
    log.info("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
