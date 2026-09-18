#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTTH DXF 结构化解析脚本（通用版 v2）
从 DXF 文件中提取：楼栋、单元、分纤箱编号(FX)、楼层表(每层户数/皮线米数)、光缆型号。

用法：
    python parse_dxf_structured.py <输入DXF> [输出JSON] [选项]

示例：
    python parse_dxf_structured.py 图纸.dxf out.json
    python parse_dxf_structured.py 图纸.dxf --text-layer <探查图层> --text-type MTEXT,TEXT
    python parse_dxf_structured.py 图纸.dxf --probe        # 先探查图层/文字样例

关键参数（换新图纸前务必用 --probe 确认实际标注格式再传参）：
    --text-layer    文字所在图层，逗号分隔（必填，由探查提供）
    --title-pattern 楼栋标题正则，需含捕获组数字（必填，由探查枚举标题写法后提供）
    --floor-pattern 楼层标注正则（留空＝内置统一解析，支持 3F/17F/-1F/B1/B2/WF）
    --hu-pattern    每层户数正则（由探查采样后提供）
    --cable-pattern 皮线米数正则（由探查采样后提供）
    --fx-pattern    分纤箱编号正则（由探查采样后提供）
    --unit-pattern  单元标注正则（由探查采样后提供）

规则：
- 不硬编码项目特有参数；所有标注格式均可通过命令行覆盖。
- 换新图纸先跑 --probe 确认实际图层与标注格式，再按需传参。
- 同时支持 MTEXT 与 TEXT（默认都取）。
- 户数直读、布线、安装楼层（口径B y坐标关联），均禁止猜测。
"""
import argparse
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict, OrderedDict

sys.stdout.reconfigure(encoding="utf-8")

from ftth_common import (
    DEFAULT_UNIT_CLUSTER, DEFAULT_UNIT_RANGE, DEFAULT_Y_TOL,
    INF_COORD, NEG_INF_COORD,
    setup_logger, bldg_num, floor_num_or_zero, parse_floor_label,
    load_dxf, collect_texts, find_bldg_anchors, cluster_by_x, compute_bldg_ranges, match_y_to_floor,
    compute_bldg_ranges_banded, assign_by_xy, bldg_range_diagnostics, group_shared_ranges,
    column_consensus_y,
    MultiPlotDuplicateAnchorError,
    assign_floor_by_interval, clean_text, is_floor_text, require_params,
    floor_step_from_texts, set_expand_bldg_ranges,
    extract_geom, is_bldg_title_text, suggest_fx_symbol_layers,
    find_plot_band_anchors, derive_plot_bands, PLOT_BAND_WORDS,
    ensure_parent, write_json, sanitize_nonfinite,
)

log = setup_logger("parse_dxf")

# ---------- 参数 ----------
ap = argparse.ArgumentParser(description="FTTH DXF 结构化解析（通用版 v2）")
ap.add_argument("--expand-bldg-ranges", action="store_true",
                help="楼栋区间标题（如 `1-3号楼`）按**区间**语义展开为 1,2,3。\n"
                     "默认不展开（只取字面数字并 WARNING 待裁决）——连字符写法\n"
                     "既可能是并列也可能是区间，**须用户确认语义后**才可开启，\n"
                     "不得替用户静默选定语义。")
ap.add_argument("dxf", help="输入DXF文件路径")
ap.add_argument("out", nargs="?", default=None, help="输出JSON路径（默认DXF同目录 _解析结果.json）")
ap.add_argument("--title-band-tol", type=float, default=None,
                help="楼栋标题分带容差（y）。相邻锚点 y 相差不超过本值者视为同一带，"
                     "带内再按 x 中分；留空 → 按 2 倍层高自适应，层高不可得 → 单带。")
ap.add_argument("--legacy-bldg-assign", action="store_true",
                help="【仅对拍】强制旧的「纯 x 闭区间 + dict 序先到先得」楼栋归属（忽略 y）。"
                     "仅供 A/B 回归对拍，正式出表不得启用。")
ap.add_argument("--text-layer", default=None, help="文字所在图层，逗号分隔（必填，由探查提供）")
ap.add_argument("--text-type", default="MTEXT,TEXT", help="文字实体类型，逗号分隔（默认两者都取）")
ap.add_argument("--title-pattern", default=None, help="楼栋标题正则，含捕获组数字（必填，由探查提供）")
ap.add_argument("--floor-pattern", default=None, help="楼层标注正则。默认 None＝内置统一解析（支持 3F/17F/-1F/B1/B2/WF）")
ap.add_argument("--hu-pattern", default=None, help="每层户数正则，捕获组为户数（由探查采样后提供；留空＝不提取户数）")
ap.add_argument("--cable-pattern", default=None, help="皮线米数正则，组1米数/组2根数（由探查采样后提供；留空＝不提取皮线）")
ap.add_argument("--fx-pattern", default=None, help="分纤箱编号正则（由探查采样后提供；留空＝不提取分纤箱）")
ap.add_argument("--fx-map", dest="fx_map", default=None,
                help="总图 FX 对照表 JSON（extract_fx_map.py 产物，含「FX映射表」数组）。"
                     "只回填 parse 侧**缺失**的安装楼层，不覆盖已测出的值；"
                     "重号编号不回填、登记交人工。用于消除「未关联到楼层」类 FAIL")
ap.add_argument("--bldg-map", dest="bldg_map", default=None,
                help="总图 FX 对照表 JSON（同上，extract_fx_map.py 产物）。提供后箱的"
                     "**楼栋/单元归属以对照表为准**（SKILL.md 硬约束②：严禁用标题 x 中分"
                     "硬切）。总图对照表形态的图纸（编号集中在独立图区，x 不落在任何楼栋"
                     "标题区间内）不传它则逐栋 0 箱。只改归属，不改安装楼层")
ap.add_argument("--unit-pattern", default=None, help="单元标注正则，捕获组为单元号（由探查采样后提供；留空＝用分纤箱x聚类分单元）")
ap.add_argument("--cable-keywords", default=None, help="光缆识别关键词正则（由探查采样后提供；留空＝不提取光缆名）")
ap.add_argument("--unit-cluster", type=float, default=None, help="无单元标注时fx聚类阈值（None=按 1.0 倍层高自适应，层高由楼层标注实测）")
ap.add_argument("--unit-range", type=float, default=None, help="单元文字x归属半宽（None=按 4.0 倍层高自适应）")
ap.add_argument("--y-tol", type=float, default=None, help="户数/皮线与楼层y坐标匹配容差（None=按 1/15 倍层高自适应）")
ap.add_argument("--insert-blocks", default=None, help="INSERT块名列表，逗号分隔。指定后提取INSERT实体的ATTRIB属性（由探查枚举全部设备块名）")
ap.add_argument("--insert-attrib-tag", default=None, help="ATTRIB属性tag名，逗号分隔（由探查确定）")
ap.add_argument("--insert-attrib-val", default=None, help="ATTRIB属性值筛选正则（由探查确定，如 HDD/家居配线箱）")
ap.add_argument("--probe", action="store_true", help="探查模式：只打印图层/文字样例，不解析")
args = ap.parse_args()
# 楼栋区间标题语义（`1-3号楼` = 并列 还是 区间？）由用户裁定后经本开关启用，
# 不设默认开启——替用户静默选定语义会丢/多解楼栋。
set_expand_bldg_ranges(getattr(args, "expand_bldg_ranges", False))

DXF_PATH = args.dxf
OUT = args.out or (os.path.splitext(DXF_PATH)[0] + "_解析结果.json")

if not args.probe:
    require_params([
        ("--text-layer", args.text_layer, "含FTTH标注的文字图层（探查图层清单+采样后确定）"),
        ("--title-pattern", args.title_pattern, "楼栋标题正则，需含组1=楼栋号"),
    ], "parse_dxf_structured")

LAYERS = [x.strip() for x in (args.text_layer or "").split(",") if x.strip()]
TYPES = [x.strip().upper() for x in args.text_type.split(",") if x.strip()]
TITLE_RE = re.compile(args.title_pattern) if args.title_pattern else None
FLOOR_RE = re.compile(args.floor_pattern) if args.floor_pattern else None
HU_RE = re.compile(args.hu_pattern) if args.hu_pattern else None
CABLE_RE = re.compile(args.cable_pattern) if args.cable_pattern else None
CABLE_KW_RE = re.compile(args.cable_keywords) if args.cable_keywords else None
FX_RE = re.compile(args.fx_pattern) if args.fx_pattern else None
UNIT_RE = re.compile(args.unit_pattern) if args.unit_pattern else None

# ---------- 2026-09-17（R2 参数自检）：正则捕获组契约，编译后立刻校验 ----------
# 背景（2026-09-16 22:03 实测）：--cable-pattern 传入无捕获组的正则（如 "\d+Px\d+芯x\d+m"），
#   编译通过，直到解析期 m.group(1) 才以 IndexError 裸崩——崩点远离传参处，排查成本高。
#   需要几组不是拍脑袋的默认值，取自本脚本内各正则的实际用法（m.group(n) 的最大 n）：
#   TITLE_RE→find_bldg_anchors group(1)；HU_RE→787 group(1)；
#   CABLE_RE→792 group(1)(2)；UNIT_RE→717 group(1)。
#   校验失败立刻显式退出并给出正确形态示例，不再带病运行。通用判据，与具体项目无关。
for _arg, _pat, _rex, _need, _eg in (
    ("--title-pattern", args.title_pattern, TITLE_RE, 1, r'"(\d+)#楼"（组1=楼栋号）'),
    ("--hu-pattern", args.hu_pattern, HU_RE, 1, r'"(\d+)户"（组1=户数）'),
    ("--cable-pattern", args.cable_pattern, CABLE_RE, 2, r'"(\d+(?:\.\d+)?)m\*(\d+)芯"（组1=米数 组2=根数）'),
    ("--unit-pattern", args.unit_pattern, UNIT_RE, 1, r'"(\d+)单元"（组1=单元号）'),
):
    # 命名组的例外（2026-09-18）：皮线米数**字段序因图而异**，位置组无法表达
    # `2Px2芯x36m` 这种「米数在后」的写法。故约定命名组 `meters*` / `count*`，
    # 含 meters 命名组的 pattern 不再要求位置组数量 —— 否则只用「纯米数」形态的图
    # 会给出 1 组 pattern 被本条自检拦下（而该 pattern 恰恰是正确写法）。
    if _arg == "--cable-pattern" and _rex is not None and "?P<meters" in (_pat or ""):
        continue
    if _rex is not None and _rex.groups < _need:
        raise SystemExit(
            f"[参数自检] {_arg} 本脚本解析期需要至少 {_need} 个捕获组，"
            f"当前 pattern 只有 {_rex.groups} 个: {_pat!r}\n"
            f"  正确形态{_eg}\n"
            f"  （2026-09-16 实测：无捕获组编译通过、rc=0 假象，到解析期才 IndexError 裸崩）")


# ---------- 皮线米数标注：写法谱（2026-09-18）----------
# 与 plan_methods.RE_FIBER_LEN_FORMS 的形态表**必须一致**（镜像铁律②）：
#   画像侧认得出（fiber_length_vshape=present）、探测侧却给不出 --cable-pattern
#   ⇒ plan 选「V 型计算」、coverage 因缺 --cable-pattern 直接硬失败 rc=2。
#   实测某图 8 个分带全中（画像 present / cable_pattern=None），根因就是探测侧只认
#   `\d+m*\d+` 一种字段序。
# 命名约定（三处解析方共用，见 _cable_tuple 与 analyze_coverage_vshape.parse_cable）：
#   任何以 `meters` 开头的组 = 米数；以 `count` 开头的组 = 根数。字段序不同的形态
#   用**不同的组名**区分（同名组在正则里只能出现一次），取值时按前缀归并。
CABLE_FORM_RES = [
    # 根数Px芯数x米数（米数在后）—— 必须排在「米数*根数」之前判，否则窄形态会被误吞
    ("根数Px芯数x米数",
     re.compile(r"(?P<count_px>\d+)\s*[Pp][xX]\s*\d+\s*芯\s*[xX*]\s*(?P<meters_px>\d+(?:\.\d+)?)\s*[mM]")),
    ("米数*根数",
     re.compile(r"(?P<meters_m>\d+(?:\.\d+)?)\s*[mM]\s*[*×xX]\s*(?P<count_m>\d+)")),
    ("芯数x米数",
     re.compile(r"\d+\s*芯\s*[xX*]\s*(?P<meters_core>\d+(?:\.\d+)?)\s*[mM]")),
    ("纯米数",
     re.compile(r"(?P<meters_only>\d+(?:\.\d+)?)\s*[mM]")),
]


def _cable_pattern_for(forms):
    """按图上**实际出现**的形态拼装 --cable-pattern（全匹配、带命名组）。"""
    parts = [rex.pattern for name, rex in CABLE_FORM_RES if name in forms]
    if not parts:
        return None
    return r"^(?:" + "|".join(parts) + r")$"


def _cable_forms_in(sample_texts):
    """返回图上出现的形态名（按具体→宽泛顺序）。"""
    found = []
    for name, rex in CABLE_FORM_RES:
        if any(rex.fullmatch(s.strip()) for s in sample_texts):
            found.append(name)
    return found


def _cable_tuple(m):
    """从匹配对象取 (米数, 根数)。

    取值顺序：① 命名组（`meters*` / `count*` 前缀）；② 无命名组时回退旧契约
    （组1=米数、组2=根数）。根数缺省为 1（「纯米数」形态天然无根数）。
    """
    gd = m.groupdict()
    meters = None
    count = None
    for k, v in gd.items():
        if v is None:
            continue
        if k.startswith("meters") and meters is None:
            meters = v
        elif k.startswith("count") and count is None:
            count = v
    if meters is None and (m.re.groups or 0) >= 1:
        meters = m.group(1)
        if count is None and (m.re.groups or 0) >= 2:
            count = m.group(2)
    return meters, count


def _is_floor_text(s):
    """楼层标注判定：统一走 ftth_common.is_floor_text（支持 3F/17F/-1F/B1/B2/WF）。"""
    return is_floor_text(s, FLOOR_RE)

doc, msp = load_dxf(DXF_PATH, log)

# ---------- 探查模式 ----------
if args.probe:
    log.info("== 图层清单 ==")
    for lay in doc.layers:
        log.info(f"  {lay.dxf.name}")
    log.info("\n== 文字实体（按图层/类型统计） ==")
    cnt = Counter()
    for e in msp:
        if e.dxftype() in ("TEXT", "MTEXT"):
            cnt[(e.dxf.layer, e.dxftype())] += 1
    for (lay, typ), n in cnt.most_common():
        log.info(f"  {lay} {typ}: {n}")
    log.info(f"\n== 文字样例（前40条） ==")
    shown = 0
    for e in msp:
        if e.dxftype() not in ("TEXT", "MTEXT"):
            continue
        txt = e.plain_text().strip() if e.dxftype() == "MTEXT" else str(e.dxf.text).strip()
        if not txt:
            continue
        p = e.dxf.insert
        log.info(f"  [{e.dxf.layer}] {txt!r} @ ({p.x:.1f},{p.y:.1f})")
        shown += 1
        if shown >= 40:
            break
    # INSERT/ATTRIB 探查
    insert_blocks_seen = {}  # {块名: 数量}
    for e in msp:
        if e.dxftype() != "INSERT":
            continue
        bname = e.dxf.name
        insert_blocks_seen[bname] = insert_blocks_seen.get(bname, 0) + 1
    if insert_blocks_seen:
        log.info("\n== INSERT 块统计 ==")
        for bn, cnt in sorted(insert_blocks_seen.items(), key=lambda x: -x[1]):
            log.info(f"  {bn}: {cnt} 个")
            # 读取块定义中的 ATTDEF 和子实体
            try:
                block = doc.blocks.get(bname)
                if block:
                    attdefs = []
                    for sub in block:
                        if sub.dxftype() == "ATTDEF":
                            attdefs.append(f"tag={sub.dxf.tag} text={sub.dxf.text}")
                        elif sub.dxftype() in ("TEXT", "MTEXT"):
                            txt = sub.plain_text().strip() if sub.dxftype() == "MTEXT" else str(sub.dxf.text).strip()
                            if txt:
                                attdefs.append(f"{sub.dxftype()}={txt}")
                    if attdefs:
                        log.info(f"    块定义: {', '.join(attdefs)}")
            except Exception:
                pass
        # 统计 INSERT 实例的 ATTRIB 属性值
        log.info("\n== INSERT 实例 ATTRIB 属性样例（前20个） ==")
        shown = 0
        for e in msp:
            if e.dxftype() != "INSERT":
                continue
            if not e.has_attrib:
                continue
            p = e.dxf.insert
            attribs = []
            for attrib in e.attribs:
                attribs.append(f"{attrib.dxf.tag}={attrib.dxf.text}")
            if attribs:
                log.info(f"  [{e.dxf.name}] @ ({p.x:.1f},{p.y:.1f}) {', '.join(attribs)}")
                shown += 1
                if shown >= 20:
                    break
        log.info("\n  提示：若需在解析模式提取INSERT，用 --insert-blocks 指定块名，")
        log.info("  --insert-attrib-tag 指定属性tag，--insert-attrib-val 指定属性值筛选正则。")
    log.info("\n（提示：根据上面样例，用 --text-layer 指定含标注的图层；")
    log.info("  **楼栋标题**＝含『系统图/布线图/示意图』的图纸标题（如「1#住宅光纤入户系统图」），")
    log.info("  用 --title-pattern 指定，必须枚举本图**标题的实际写法**；")
    log.info("  标题里的楼栋号后不一定写『楼』（可能是 住宅/配套/商业 等）；")
    log.info("  **不要用 --bldg-pattern 的值顶替 --title-pattern** —— bldg-pattern 匹配的是")
    log.info("  总图对照表里的楼栋行，不是系统图标题；顶替后楼栋 x 范围会被切在对照表区，")
    log.info("  逐栋找不到箱符号（该情形已由 analyze_coverage 的同区护栏明确报出）；")
    log.info("  楼层/户数/皮线/分纤箱编号格式不同，分别用 --floor/--hu/--cable/--fx-pattern 指定。）")
    # 写入建议参数 JSON + 全量文字样例（供 --config 使用）
    if args.out:
        all_samples = []
        for e in msp:
            if e.dxftype() not in ("TEXT", "MTEXT"):
                continue
            txt = e.plain_text().strip() if e.dxftype() == "MTEXT" else str(e.dxf.text).strip()
            if not txt:
                continue
            p = e.dxf.insert
            all_samples.append({"层": e.dxf.layer, "类型": e.dxftype(), "内容": txt, "x": round(p.x, 2), "y": round(p.y, 2)})
        # 2026-09-12 修正（P0-1 / 通用性）：
        #   ① probe 必须真分析文字样例，而不是回显命令行默认值（旧实现回显 args.*，
        #      而现在 args.* 已无项目默认值 → 照文档用 config 必然拿到 None）。
        #   ② text_layer 候选不能"按文字条数取前N个"（会把暖通/消防/建筑等文字量大的
        #      无关图层混进来），也不能只取"文本最多的那一个"（FTTH 信息在各图纸上
        #      常常分散在多个图层：楼层刻度一个图层、编号/标题另一个图层——漏掉任一
        #      都会让后续步骤静默缺数据）。改为按【强特征标记】逐图层计数：
        #      只有真正含 楼层标注 / 楼栋标题 / 编号 / 皮线米数 / 户数 / 单元标记 的图层
        #      才进候选；这些标记在建筑/暖通/消防图层上几乎不会出现。
        #   ③ 推断不出的一律返回 None，交由使用者按探查输出人工确认，不猜。
        def _guess_params(samples):
            """从全量文字样例中推断参数候选；推断不出返回 None（不猜）。"""
            from collections import Counter as _C

            def _strong_marks(t):
                """返回该文字命中的强特征标记集合（用于判定它所在图层是否为 FTTH 图层）。"""
                m = set()
                if is_floor_text(t):
                    m.add("楼层")
                if is_bldg_title_text(t):
                    m.add("标题")   # 图纸类词 + 楼栋号，避免「防护分区抗爆单元示意图」这类无关标题
                    # 判据统一走 ftth_common.is_bldg_title_text：楼栋号后**不要求紧跟
                    # 『楼』**，`N#楼`/`N号楼`/`N#住宅`/`N#配套` 一并命中 —— 只认
                    # `数字+#+楼` 时，整类写作「N#住宅…系统图」的图纸标题标记全不命中
                    # → 标题图层不进 text_layer（2026-09-16 实测踩坑）
                    # 候选 → 采集不到标题 → 「标题锚点 0 个、楼栋分组不可用」。
                if re.search(r"[A-Za-z]{1,4}\s*\d+\s*[-_ ]?\s*FX\s*\d+|FX\s*\d+", t):
                    m.add("编号")
                    # `\bFX\d+` 对 `FL01FX01` 不命中（`1` 与 `F` 之间无词边界），
                    # 故前缀形态必须显式写出，否则整类带前缀编号的图层漏选。
                if re.search(r"\d+\s*m\s*[*×]\s*\d+", t):
                    m.add("米数")
                if re.fullmatch(r"\d+\s*户", t.strip()):
                    m.add("户数")
                if re.fullmatch(r"\d+\s*单元", t.strip()):
                    m.add("单元")
                if re.search(r"\d+芯|光分|分光器|光交", t):
                    m.add("芯数")
                return m

            layer_marks = {}          # 图层 -> Counter(标记 -> 条数)
            for s in samples:
                ms = _strong_marks(s["内容"])
                if ms:
                    c = layer_marks.setdefault(s["层"], _C())
                    for k in ms:
                        c[k] += 1
            if layer_marks:
                # 按"命中的强特征种类数"再按"命中总条数"排序；取前 8 个图层
                ranked = sorted(layer_marks.items(),
                                key=lambda kv: (len(kv[1]), sum(kv[1].values())),
                                reverse=True)[:8]
                suggested_text_layer = ",".join(lay for lay, _ in ranked)
                log.info("  [探查] FTTH 图层候选（图层: 强特征命中）:")
                for lay, c in ranked:
                    log.info("    %s: %s" % (lay, dict(c)))
            else:
                suggested_text_layer = None

            # 标题正则候选：含 系统图/布线图/示意图 且含楼栋号的标题。
            # 2026-09-15 修正：楼栋号写法必须**并列枚举** `N#楼` 与 `N号楼` —— 旧条件
            #   写死 `\d+#`，而真实图纸整类标题可能全写成「N号楼」（实测柳辛庄 15 条
            #   标题全是「N号楼/综合布线系统图」）→ title_pattern 推断为 None，
            #   整个标题体系未被识别，楼栋边界只能靠猜。
            # 2026-09-16 再修：**楼栋号后不要求紧跟『楼』**（判据统一到
            #   ftth_common.is_bldg_title_text）—— 实测某图整类标题写作
            #   「N#住宅光纤入户系统图」「N#配套光纤入户系统图」，数字后接 住宅/配套，
            #   旧判据整类失配 → 本项与下方「标题图层并入 text_layer」**同时**失效，
            #   且失败是静默的（只表现为 title_pattern: None）。
            title_texts = [s["内容"] for s in samples if is_bldg_title_text(s["内容"])]
            suggested_title = None
            if title_texts:
                _has_hash = any(re.search(r"\d+#", t) for t in title_texts)
                _has_hao = any(re.search(r"\d+\s*号楼", t) for t in title_texts)
                if _has_hash and _has_hao:
                    suggested_title = r"(\d+)(?:#|号楼).*(?:系统图|布线图|示意图)"
                elif _has_hash:
                    suggested_title = r"(\d+)#.*(?:系统图|布线图|示意图)"
                else:
                    suggested_title = r"(\d+)号楼.*(?:系统图|布线图|示意图)"

            # 标题图层**强制并入** text_layer（2026-09-15 铁律 5，双保险）：
            # 标题常在专用图层（如 `TEL_SYMB`），该图层不含楼层/芯数/单元等强特征关键词，
            # 整层可能不进候选；漏掉它的症状极具迷惑性——pattern 写对、门禁 PASS，
            # 却是「标题锚点 0 个 → 楼栋分组不可用」。故不依赖候选命中，直接并入。
            _title_layers = [s["层"] for s in samples if is_bldg_title_text(s["内容"])]
            if _title_layers:
                _cur = [x for x in (suggested_text_layer or "").split(",") if x]
                for _lay in dict.fromkeys(_title_layers):
                    if _lay not in _cur:
                        _cur.append(_lay)
                        log.info("  [探查] 标题图层 %r 已并入 text_layer（标题须可采集）" % _lay)
                suggested_text_layer = ",".join(_cur) if _cur else None

            # 编号正则候选：**必须保留完整编号（含前缀）**。
            # 2026-09-15 修正（P0）：只取尾段（如 `FX\d+`）会让跨地块/跨楼栋的同序号
            #   串号。实测柳辛庄：图上 4 个地块各有一整套 FX01~FX28（写作 `FL01FX01`
            #   ——前缀无分隔符），旧逻辑只认 `FL\d+-FX\d+`（**带连字符**）→ 不匹配 →
            #   退化为 `FX\d+#?` → **84 个箱被压成 28 个编号，56 个箱静默丢失**，
            #   且同序号箱互相覆盖归属。形态谱由「最完整」到「最简」依次尝试。
            fx_texts = [s["内容"] for s in samples if re.search(r"FX\s*\d+|FL\s*\d+", s["内容"])]
            suggested_fx = None
            fx_dup_note = None
            if fx_texts:
                if any(re.search(r"FL\d+\s*-\s*FX\d+", t) for t in fx_texts):
                    suggested_fx = r"FL\d+-FX\d+"
                elif any(re.search(r"[A-Za-z]{1,4}\d+\s*[-_ ]?\s*FX\d+", t) for t in fx_texts):
                    # 前缀无分隔（FL01FX01）：整体取，**禁止退化为 FX 尾段**
                    suggested_fx = r"[A-Za-z]{1,4}\d+FX\d+"
                elif any(re.search(r"FX\s*\d+\s*#?", t) for t in fx_texts):
                    suggested_fx = r"FX\d+#?"
                # 串号风险检测：同一 FX 尾号若对应多个前缀 → 必须用完整编号
                _tails = {}
                for t in fx_texts:
                    _m = re.search(r"([A-Za-z]{1,4}\d+)?\s*FX\s*(\d+)", t)
                    if _m and _m.group(1):
                        _tails.setdefault(_m.group(2), set()).add(_m.group(1))
                _dups = {k: v for k, v in _tails.items() if len(v) > 1}
                if _dups:
                    _ex = list(_dups.items())[0]
                    fx_dup_note = (
                        "**串号风险**：检出 %d 个 FX 尾号对应多个前缀（如 FX%s → %s）。"
                        "若 fx_pattern 只取尾段（FX\\d+），这些箱会被压成同一个编号并互相"
                        "覆盖归属，数量级静默丢失。本图已按完整编号给出建议 pattern。"
                        % (len(_dups), _ex[0], "/".join(sorted(_ex[1]))))
                    log.info("  [探查] " + fx_dup_note)

            suggested_hu = r"(\d+)户" if any(re.fullmatch(r"\d+\s*户", s["内容"].strip()) for s in samples) else None
            # 皮线米数：**写法谱**（2026-09-18）。旧实现只认 `\d+m*\d+` 一种字段序，
            #   实测某图标注写成 `2Px2芯x36m`（米数在后）→ 给出 None → 下游
            #   analyze_coverage_vshape 缺 --cable-pattern 硬失败 rc=2，而画像却申报
            #   fiber_length_vshape=present（两侧写法兼容表不一致，镜像铁律② 违规）。
            #   现按图面实际出现的形态拼装 pattern，并回报命中的形态便于人工核对。
            _cable_forms = _cable_forms_in([s["内容"] for s in samples])
            suggested_cable = _cable_pattern_for(_cable_forms)
            cable_forms_note = None
            if _cable_forms:
                log.info("  [探查] 皮线米数形态：%s → cable_pattern 覆盖 %d 种写法"
                         % ("、".join(_cable_forms), len(_cable_forms)))
            else:
                cable_forms_note = ("本图采样未发现米数标注（含 `Xm*N` / `NPxM芯xLm` / `X芯xLm` /"
                                    " `Xm` 四种已知写法）—— 需人工确认是否另有写法")
                log.info("  [探查] " + cable_forms_note)
            suggested_unit = r"(\d+)单元" if any(re.fullmatch(r"\d+\s*单元", s["内容"].strip()) for s in samples) else None

            # 楼栋标注正则候选（供 extract_fx_map / analyze_coverage 使用）：
            # 必须覆盖『N#配套楼』『N#商业楼』以及无『楼』字的写法
            suggested_bldg = None
            if any(re.search(r"\d+#", s["内容"]) and ("楼" in s["内容"] or "单元" in s["内容"]) for s in samples):
                suggested_bldg = r"(\d+)#(?:配套|商业|附属)?楼|(\d+)号楼"

            # FX 编号 ↔ 楼栋/单元标注 的实测邻近距离（供 extract_fx_map --proximity-tol）：
            # 文档要求"必须先测量实际距离，不得盲目沿用默认值"，这里直接量出来。
            suggested_proximity = None
            _fx_pts = [(s["x"], s["y"]) for s in samples if re.search(r"FX\s*\d+", s["内容"])]
            _bd_pts = [(s["x"], s["y"]) for s in samples
                       if re.search(r"\d+#.*楼|\d+号楼|\d+\s*单元", s["内容"])]
            if _fx_pts and _bd_pts:
                _ds = sorted(min(((x - bx) ** 2 + (y - by) ** 2) ** 0.5 for bx, by in _bd_pts)
                             for x, y in _fx_pts)
                _k = max(0, int(len(_ds) * 0.9) - 1)
                suggested_proximity = int(__import__("math").ceil(_ds[_k] / 10.0) * 10) + 10
                log.info("  [探查] FX↔楼栋标注实测距离：min=%.1f 中位=%.1f P90=%.1f → 建议 --proximity-tol %d"
                         % (_ds[0], _ds[len(_ds) // 2], _ds[_k], suggested_proximity))

            # ---------- 图签候选图层探测（2026-09-16，12坑复核·坑3）----------
            # 「N层/M户」「N单元」类图签标注常在独立图签层（不含 FTTH 强特征），
            # 不进 text_layer 候选 → 图签提取靠试错找层。此处按图层直接统计命中，
            # 输出为顶层信号 titleblock_layer_candidates（供 read_titleblock_households
            # 的 --floor-layer 参考；advisory，需人工确认）。
            _tb_marks = {}
            for s in samples:
                t = s["内容"].strip()
                _hit = []
                if re.fullmatch(r"\d+\s*层\s*/\s*\d+\s*户", t):
                    _hit.append("层户")
                if re.fullmatch(r"\d+\s*F", t):
                    _hit.append("NF")
                if re.fullmatch(r"\d+\s*户\s*/\s*层", t):
                    _hit.append("户/层")
                if re.fullmatch(r"\d+\s*单元", t):
                    _hit.append("单元")
                if _hit:
                    c = _tb_marks.setdefault(s["层"], _C())
                    for k in _hit:
                        c[k] += 1
            titleblock_layer_candidates = None
            if _tb_marks:
                _tb_ranked = sorted(
                    ((lay, c) for lay, c in _tb_marks.items()
                     if c.get("层户") or (c.get("NF") and c.get("户/层"))),
                    key=lambda kv: (kv[1].get("层户", 0) + kv[1].get("NF", 0),
                                    sum(kv[1].values())),
                    reverse=True)
                if _tb_ranked:
                    titleblock_layer_candidates = {
                        "候选图层": [lay for lay, _ in _tb_ranked[:4]],
                        "命中明细": {lay: dict(c) for lay, c in _tb_ranked[:4]},
                        "用途": "read_titleblock_households.py --floor-layer 候选（advisory）",
                    }
                    log.info("  [探查] 图签候选图层: %s"
                             % {lay: dict(c) for lay, c in _tb_ranked[:4]})

            # ---------- 地块/分带标注探测（2026-09-16 立；2026-09-18 改走共享实现）----------
            # 多地块混排竣工图常用短标注区分地块；**文件名不等于地块划分**——一张图
            # 内部可含多个独立地块、楼号各自从 1 起。输出**锚点候选 + 排除明细 +
            # 分带窗口**，供 `ftth.py split-band --auto` 直接切子图。
            # 2026-09-18 补：此前只输出「样例」且按 (编号,文字) 去重截断（同编号多位置
            #   时静默只剩 1 条），并且**算了不接线** —— 下游 split-band 只吃人工 --band，
            #   人被迫手搓 8 条 band spec。现在窗口由 derive_plot_bands 一次算齐，
            #   与 split-band 同源同算法（画像里看到的就是实际会切出来的）。
            _pb = derive_plot_bands(msp, samples)
            _pb_anchors = _pb["锚点"]
            _pb_excluded = _pb["锚点排除"]
            _pb_hits = _pb["命中"]
            plot_band_annotations = None
            if _pb_hits:
                _names = sorted({h["编号"] for h in _pb_hits if h.get("编号")},
                                key=lambda s: (len(s), s))
                _main_nums = set()
                for _nm in _names:
                    _mm = re.match(r"(\d+)", _nm)
                    if _mm:
                        _main_nums.add(int(_mm.group(1)))
                _gaps = [i for i in range(min(_main_nums), max(_main_nums) + 1)
                         if i not in _main_nums] if _main_nums else []
                plot_band_annotations = {
                    "词表": ("%s（内置通用词表；本图用词不同请人工补充）"
                           % "|".join(PLOT_BAND_WORDS)),
                    "种类": _names,
                    "条数": len(_pb_hits),
                    "缺号提醒": ("编号序列缺 %s——图纸可能只含部分地块或编号本就不连续，请人工确认"
                              % _gaps) if _gaps else None,
                    # 全量命中（**不再按 (编号,文字) 去重、不截断**）：去重会丢掉同编号的
                    # 其余位置，下游若据此算分带锚点会静默少切带。
                    "样例": _pb_hits,
                    "锚点候选": _pb_anchors,
                    "锚点排除": _pb_excluded,
                    "分带窗口": _pb["分带窗口"],
                    "分带切点": _pb["切点"],
                    "分带核对疑点": _pb["疑点"],
                    "分带错误": _pb["错误"],
                    "锚点去向": _pb["去向"] if _pb_anchors else
                             ("0 个严格形态锚点 —— 图上只有带附加字/合并形态的地块标注，"
                              "需人工指定分带边界（--band）" if _pb_hits else None),
                }
                log.info("  [探查] 地块/分带标注 %d 条（编号 %s）%s；严格锚点 %d 个，"
                         "分带窗口 %d 个%s"
                         % (len(_pb_hits), "/".join(_names),
                            ("，缺号 %s" % _gaps) if _gaps else "",
                            len(_pb_anchors), len(_pb["分带窗口"] or []),
                            ("，排除 %d 条（见画像的「锚点排除」）" % len(_pb_excluded))
                            if _pb_excluded else ""))
                if _pb["疑点"]:
                    log.warning("  [探查] 分带核对疑点 %d 条（不阻塞，须人工过目）：%s"
                                % (len(_pb["疑点"]), _pb["疑点"][0]))

            # ---------- 箱位直读标注信号（2026-09-16，12坑复核·坑9）----------
            # 「N号楼M单元K层」格式标注直接给出箱位（楼栋/单元/安装层），是最可靠的
            # 箱位第二来源；present 时下游应做安装层交叉校验（并列证据交人裁定，不自动择一）。
            _FXLOC_RE = re.compile(r"(\d+)\s*号楼\s*(\d+)\s*单元\s*(\d+)\s*层")
            _fxloc_n = sum(1 for s in samples if _FXLOC_RE.search(s["内容"]))
            fx_location_annotation = ("present(%d条)" % _fxloc_n) if _fxloc_n else "absent"
            if _fxloc_n:
                log.info("  [探查] 箱位直读标注「N号楼M单元K层」%d 条 → 建议做安装层交叉校验"
                         % _fxloc_n)

            return {
                "text_layer": suggested_text_layer,
                "text_type": ",".join(TYPES),
                "title_pattern": suggested_title,
                "floor_pattern": None,  # None=内置统一解析（支持 B1/WF）
                "hu_pattern": suggested_hu,
                "cable_pattern": suggested_cable,
                "cable_pattern_note": cable_forms_note,   # 非 None 表示采样未见已知写法，须人工确认
                "fx_pattern": suggested_fx,
                "fx_pattern_note": fx_dup_note,   # 非 None 表示检出串号风险，须保留完整编号
                "unit_pattern": suggested_unit,
                "bldg_pattern": suggested_bldg,
                "proximity_tol": suggested_proximity,
                "titleblock_layer_candidates": titleblock_layer_candidates,
                "plot_band_annotations": plot_band_annotations,
                "fx_location_annotation": fx_location_annotation,
            }

        suggested = _guess_params(all_samples)

        # ---- 分纤箱图形符号层候选（2026-09-16 新增，P0-2）----
        # 与 plan 同源打分（ftth_common.suggest_fx_symbol_layers）。此前该项在 plan
        # 的输出里**只有读、没有写**，恒为「探查未给出候选图层」，测量方只能猜图层名
        # （实测猜成文字层 → 箱位回退编号文字坐标 → 竖干配对率 0% → 覆盖全空）。
        fx_symbol_layer_candidates = []
        try:
            _g = extract_geom(msp)
            _fxp = suggested.get("fx_pattern")
            _fxr = re.compile(_fxp) if _fxp else re.compile(r"FX\d+")
            fx_symbol_layer_candidates = suggest_fx_symbol_layers(
                _g["polylines"], _g["texts"],
                fx_count=len([1 for _s in all_samples if _fxr.search(_s["内容"])]))
        except Exception as _e:                                          # noqa: BLE001
            log.warning("  [探查] 箱符号层候选打分失败（不影响其它项）：%s" % _e)
        if fx_symbol_layer_candidates:
            log.info("  [探查] 分纤箱图形符号层候选（按得分降序；箱体只写编号、不画符号的图本项为空）:")
            for _c in fx_symbol_layer_candidates:
                log.info("    %s 得分%.2f%s（闭合四点矩形%d｜尺寸一致性%.2f｜标题区重叠%.2f｜众数尺寸%s）"
                         % (_c["层"], _c["得分"], "【推荐】" if _c["推荐"] else "",
                            _c["闭合四点矩形"], _c["一致性"], _c["标题区重叠"], _c["众数尺寸"]))
        else:
            log.info("  [探查] 分纤箱图形符号层候选：无（本图箱体可能只写编号文字、无图形符号）")
        suggested["fx_symbol_layer_candidates"] = fx_symbol_layer_candidates or None
        if not suggested.get("title_pattern"):
            log.warning("  [探查] title_pattern 推断为空 —— 请按上面的「全量文字样例」人工枚举"
                        "**图纸标题**的实际写法（含楼栋号 + 系统图/布线图/示意图）；"
                        "**切勿用 bldg_pattern 的值顶替**（它匹配对照表楼栋行，不是标题）。")
        # 2026-09-16（12坑复核）：画像类信号提升到 probe JSON 顶层。
        #   它们不是任何子命令的命令行参数——留在 suggested_params 里会被
        #   ftth.py --config 的参数校验逐个 WARN 忽略，反而淹没有效告警。
        _profile_signals = {}
        for _k in ("titleblock_layer_candidates", "plot_band_annotations",
                   "fx_location_annotation", "fx_symbol_layer_candidates"):
            if _k in suggested:
                _profile_signals[_k] = suggested.pop(_k)
        # 2026-09-18 整改：推荐箱符号层**同时**以子命令参数名留在 suggested_params。
        #   上面 pop 的理由是「它们不是任何子命令的命令行参数」—— 与事实不符：
        #   coverage 有 --fx-symbol-layer。后果是 ftth.py 经 --config 无法下传，
        #   coverage 只能扫全图找符号层，实测某图直接 rc=3「找不到任何箱图形符号」。
        #   顶层候选列表（供人核对）与参数值（供机器消费）两者都要，缺一不可。
        _rec_sym = next((c.get("层") for c in (fx_symbol_layer_candidates or [])
                         if c.get("推荐")), None)
        if _rec_sym:
            suggested["fx_symbol_layer"] = _rec_sym
            log.info("  [探查] 推荐箱符号层已写入 suggested_params.fx_symbol_layer = %s"
                     % _rec_sym)

        log.info("\n== 建议参数（由文字样例推断；推断不出的为 null，需人工确认） ==")
        for _k, _v in suggested.items():
            log.info(f"  {_k}: {_v!r}")
        # 2026-09-16 修复 P0-1：写盘失败必须反映到退出码。
        #   原实现 except 只 WARNING，而末尾 sys.exit(0) 在 try/except 之外 ——
        #   于是「探查未产出配置」对外表现为 rc=0（成功），调用方判定成功并继续/反复重试。
        #   退出码 4 = 输出写盘失败，与 1（输入错误）/ 2（门禁中止）/ 3（不适用）区分。
        try:
            write_json(args.out, {"suggested_params": suggested, **_profile_signals,
                                  "全量文字样例": all_samples}, log=log)
            log.info(f"\n配置+全量文字样例({len(all_samples)}条)已写入: {args.out}")
        except OSError as e:
            log.error(f"无法写入探查结果 {args.out}: {e}")
            log.error("探查未产出可用配置 —— 不得按成功继续；请检查路径/权限后重试。")
            sys.exit(4)
    sys.exit(0)

# ---------- 文字收集 ----------
texts = collect_texts(msp, LAYERS, TYPES)

# ---------- INSERT/ATTRIB 收集 ----------
insert_items = []  # [{块名, x, y, 属性: {tag: val}, layer}]
if args.insert_blocks:
    INSERT_BLOCK_SET = set(b.strip() for b in args.insert_blocks.split(",") if b.strip())
    ATTRIB_TAGS = set(t.strip() for t in args.insert_attrib_tag.split(",") if t.strip())
    ATTRIB_VAL_RE = re.compile(args.insert_attrib_val)
    for e in msp:
        if e.dxftype() != "INSERT":
            continue
        if e.dxf.name not in INSERT_BLOCK_SET:
            continue
        if not e.has_attrib:
            continue
        p = e.dxf.insert
        attribs = {}
        for attrib in e.attribs:
            tag = attrib.dxf.tag
            val = attrib.dxf.text.strip()
            if tag in ATTRIB_TAGS:
                attribs[tag] = val
        # 筛选：至少一个属性值匹配 --insert-attrib-val 正则
        if ATTRIB_VAL_RE and not any(ATTRIB_VAL_RE.search(v) for v in attribs.values()):
            continue
        insert_items.append({
            "块名": e.dxf.name,
            "x": round(p.x, 2),
            "y": round(p.y, 2),
            "属性": attribs,
            "层": e.dxf.layer,
        })
    log.info(f"收集到 {len(insert_items)} 个匹配的 INSERT 实体")

# ---------- 楼栋锚点 ----------
# 多地块同名楼守卫：**rc=2（输入不足·须人工分带）**、点名根因与同名锚点位置、零产物
#   （--out 尚未写入）。
#   2026-09-18 实跑修正：原为 rc=3。rc=3 在 L1-C2 里的语义是「本图确实不提供该子任务
#   数据（absent）→ 跳过 + 降级路径，**不是错误**」；而本处是**本图有数据、只是缺分带
#   信息**，属 rc=2「有未作答项/必须修项 → 停」（C2 的 rc=2 适用范围本就写明含 `parse`
#   门禁）。给成 rc=3 会让 pipeline/调用方读成「不适用，非错误」而放行 —— 实测两张多地块
#   图都因此被读成「按画像降级路径继续」，实际链路已终止、下游从未运行。
try:
    bldg_anchors = find_bldg_anchors(texts, TITLE_RE, log)
except MultiPlotDuplicateAnchorError as _e:
    log.error(str(_e))
    sys.exit(2)

if not bldg_anchors:
    log.error("未匹配到楼栋标题，请检查 --title-pattern / --text-layer，或先运行 --probe")
    sys.exit(1)

anchor_xs = sorted([(k, v["x"]) for k, v in bldg_anchors.items()], key=lambda x: x[1])
anchor_y_map = {k: v.get("y", 0) for k, v in bldg_anchors.items()}
anchor_y_of = {k: v.get("y") for k, v in bldg_anchors.items()}

# ---------- 楼栋 x 范围：按 y 分带 + 带内 x 中分（2026-09-18 重做） ----------
# 旧实现是「全图统一 x 中分 + 纯 x 闭区间先到先得」，其成立前提为
# 「各锚点同处一个 y 行，且各栋 x 区间互不重叠」。实测两类图纸破此前提：
#   ① 共享锚点：一张系统图服务多栋（标题原文 `7#、8#、10#住宅光纤入户系统图`），
#      `_x_groups` 已并组共用同一区间 → 归属时先到先得者独吞，其余楼栋楼层表整片为空。
#   ② 上下分带：配套小图与住宅大图在 x 上重叠 → 分带后区间可重叠 → 实体归错楼或成孤儿。
# 分带容差口径与 count_households.py 一致：--title-band-tol 优先，否则取 2 倍层高；
# 层高不可得则退回单带（与改造前行为逐位一致）。
_step_b, _basis_b = floor_step_from_texts(texts, _is_floor_text)
_band_tol = args.title_band_tol or (2.0 * _step_b if _step_b else None)
if args.legacy_bldg_assign:
    _band_tol = None
    log.info("[对拍] --legacy-bldg-assign：强制单带 + 纯 x 先到先得（复现改造前行为）")
if _band_tol:
    log.info("楼栋标题分带容差 = %.4g（%s）"
             % (_band_tol, "--title-band-tol" if args.title_band_tol else "2 倍层高"))
else:
    log.warning("分带容差不可得（既未量出层高也未传 --title-band-tol）→ 退回单带 x 中分；"
                "若图上有配套楼/住宅楼上下分带，可能串带，请显式传 --title-band-tol")
bldg_ranges, _bldg_bands = compute_bldg_ranges_banded(
    [(k, v["x"], v.get("y")) for k, v in bldg_anchors.items()], band_tol=_band_tol, log=log)

# 单锚点带：带内只有一组锚点 x → 区间由 `_ranges_from_x_groups` 的 **±1000 绝对常量**兜底。
# 该常量与图纸比例无关（实测某图层高 6.5，±1000 相当于 153 倍层高）→ 命中必须显式告警
# 并落产物，不得静默。（本轮三个真机项目未命中：每个带内最少 2 组锚点。）
_SINGLE_ANCHOR_BANDS = []
for _i, _b in enumerate(_bldg_bands):
    _xs = sorted({round(float((bldg_anchors.get(_n) or {}).get("x")), 6)
                  for _n in _b.get("names") or [] if bldg_anchors.get(_n)})
    if len(_xs) <= 1:
        _SINGLE_ANCHOR_BANDS.append({"带": _i + 1, "y0": _b.get("y0"),
                                     "锚点x": _xs, "楼栋": _b.get("names")})
        log.warning("  [单锚点带] 带%d(y0=%s) 内只有一组锚点 x=%s → 区间按 ±1000 绝对兜底给出，"
                    "与图纸比例无关，须人工确认：%s"
                    % (_i + 1, _b.get("y0"), _xs, "、".join(_b.get("names") or [])))

log.info("\n楼栋x范围:")
for bldg, (xmin, xmax) in bldg_ranges.items():
    log.info(f"  {bldg}: x {xmin:.1f}~{xmax:.1f}")

# 共享区间（一张系统图服务多栋）：显式登记 —— 归属时按标题原文克隆，**不得**先到先得
_shared_groups = group_shared_ranges(bldg_ranges)
_shared_src = []
for _g in _shared_groups:
    log.info("  [共享区间] %s 共用 x %.1f~%.1f（宽 %.1f）：同区间实体按标题原文克隆给全部楼栋"
             % ("、".join(_g["names"]), _g["lo"], _g["hi"], _g["hi"] - _g["lo"]))
    # 共享组的**来源标题原文** —— 人工判「克隆是否成立」的唯一依据：
    #   同一标题展开多栋（如 `7#、8#、10#住宅光纤入户系统图`）→ 克隆成立；
    #   不同标题却落在同一 x 区间 → **疑假共享**，不得克隆，须报人。
    _titles = sorted({str((bldg_anchors.get(_n) or {}).get("内容") or "").strip()
                      for _n in _g["names"]})
    _g2 = dict(_g)
    _g2["源标题"] = _titles
    _g2["判据"] = "同一标题展开多栋" if len(_titles) == 1 else "不同标题同区间（疑假共享）"
    if len(_titles) != 1:
        log.warning("  [疑假共享] %s 落在同一 x 区间，但来源标题不止一种：%s —— 不得克隆，须人工裁决"
                    % ("、".join(_g["names"]), _titles))
    _shared_src.append(_g2)

# ---------- 楼栋区域边界重叠校验 ----------
# 混合布局图纸中不同 y 行的楼栋（如住宅楼 y 行与配套楼 y 行），虽然**同带内** x 范围
# 不相交，但跨带楼栋 x 范围可能紧邻、间距过小，导致实体按 x 归属时跨行混入邻楼。
# 检测方式：对每对不同 y 行的楼栋，若 x 范围间距 < 同行楼栋间距中位数的一半，告警。
import statistics as _stat
# 2026-09-18 统一口径：y 分行**只允许一份实现** —— 直接复用上面
# `compute_bldg_ranges_banded` 返回的 `_bldg_bands`（口径 = --title-band-tol 或 2×层高）。
# 旧实现此处又重算一遍且硬编码 `abs(y - yg) < 100`，与归属侧的分带容差是**两套口径**
# （同一维度两套口径必然漂移，且校验与归属会各说各话）。
_y_groups = {}
_band_of = {}
if len(_bldg_bands) > 1:
    for _i, _b in enumerate(_bldg_bands):
        _names_in = [n for n in (_b.get("names") or []) if n in bldg_ranges]
        if _names_in:
            _y_groups[_i] = _names_in
            for _n in _names_in:
                _band_of[_n] = _i
else:
    _k0 = (_bldg_bands[0].get("y0") if _bldg_bands else None)
    _y_groups[0 if _k0 is None else _k0] = list(bldg_ranges)
    for _n in bldg_ranges:
        _band_of[_n] = 0

if len(_y_groups) > 1:
    # 计算同行楼栋间距中位数
    same_row_gaps = []
    for yg, bldg_list in _y_groups.items():
        xs = sorted([bldg_ranges[b][0] for b in bldg_list])
        for i in range(1, len(xs)):
            same_row_gaps.append(xs[i] - xs[i-1])
    if same_row_gaps:
        median_gap = _stat.median(same_row_gaps)
        threshold = median_gap / 2
        overlap_found = False
        sorted_bldg_list = sorted(bldg_ranges.items(), key=lambda r: r[1][0])
        for i in range(len(sorted_bldg_list)):
            for j in range(i + 1, len(sorted_bldg_list)):
                n1, (x1lo, x1hi) = sorted_bldg_list[i]
                n2, (x2lo, x2hi) = sorted_bldg_list[j]
                y1 = anchor_y_map.get(n1, 0)
                y2 = anchor_y_map.get(n2, 0)
                if _band_of.get(n1) != _band_of.get(n2):
                    gap = x2lo - x1hi
                    if gap < threshold:
                        log.warning(
                            f"  [边界过近] {n1} [x={x1lo:.1f}~{x1hi:.1f},y={y1:.0f}] 与 "
                            f"{n2} [x={x2lo:.1f}~{x2hi:.1f},y={y2:.0f}] 不同行但 x 间距 "
                            f"{gap:.1f} < 阈值 {threshold:.1f}（同行间距中位数 {median_gap:.1f}）"
                            f"——按 x 归属可能把邻楼实体混入本楼，须按 x 列 + y 带双重维度精确归属"
                        )
                        overlap_found = True
        if overlap_found:
            log.warning("  [边界过近] 检测到跨行 x 间距过小，请在自检与出表时注意按 x 列精确拆分实体归属")

# ---------- 归属：带内 (x, y)，多候选显式处置（2026-09-18 重做） ----------
# 旧实现 `for bldg,(lo,hi) in bldg_ranges.items(): if lo<=x<=hi: break` 有三处问题：
#   · 不看 y —— 分带后不同带区间可重叠，先到先得必错；
#   · 闭区间 + break 依赖 dict 顺序 —— 边界上的点归谁取决于插入序，不可复现；
#   · 命中即 break —— 共享区间（多栋同区间）时独占，其余楼栋整片为空。
# 新实现：单候选 → 与旧行为逐位一致（零回归）；多候选 → 共享克隆 / y 就近 / 报裁决。
_ASSIGN_STAT = Counter()
_SHARE_CLONE = Counter()
_PENDING_ASSIGN = []

# ---------- 列共识 y（2026-09-18 新增） ----------
# 病灶（实测、坐标级）：跨带 x 重叠时**逐点**按 y 就近归属，会把同一条楼层刻度列在带分界
#   处拦腰拆开 —— 实测某图 x 完全相同的 12 个刻度（B1,1F..10F,WF，步长=层高）被判成
#   上半列归住宅、下半列归配套楼，下游表现为「住宅少 5 层、配套楼多 4 层」，且同 x 的
#   另两栋（共享该图的）整列落空。皮线标注列同样被拆成 10/10。
# 处置：同一 x（精确同值）的实体是一条「列」＝同一张系统图的同一根楼层轴，**不可按 y 拆**；
#   判带时用列的 y 中位代表该列。**只对「x 命中 >=2 个楼栋区间」的点启用**，其余点仍用
#   自身 y（故单候选点与改造前逐位一致）。
_COL_Y = column_consensus_y(list(texts) + list(insert_items))
_COL_USED = Counter()


def _hits_n(x):
    """x 命中的楼栋区间个数（用于判定是否需要列共识）。"""
    return sum(1 for (lo, hi) in bldg_ranges.values() if lo <= x <= hi)

def _assign(x, y, content, y_repr=None):
    """按 (x,y) 归属楼栋 → names 列表（长度>1 = 共享区间，须克隆给全部）。

    y_repr：该点所属**列**的代表 y（同 x 列的 y 中位）。仅当 x 命中 >=2 个楼栋区间时
    才用它替代自身 y —— 跨带重叠区逐点判 y 会把一条列拆给两栋（见上方「列共识 y」）。
    """
    if args.legacy_bldg_assign:            # 对拍：旧行为（纯 x + dict 序先到先得）
        for bldg, (xmin, xmax) in bldg_ranges.items():
            if xmin <= x <= xmax:
                _ASSIGN_STAT["legacy先到先得"] += 1
                return [bldg]
        _ASSIGN_STAT["legacy未命中"] += 1
        return []
    _yy = y
    if y_repr is not None and _hits_n(x) >= 2:
        _yy = y_repr                                  # 列共识：跨带重叠时按「列」判带
        _COL_USED[round(x, 6)] += 1
    _names, _reason = assign_by_xy(x, _yy, bldg_ranges, anchor_y_of)
    _ASSIGN_STAT[_reason.split("(")[0]] += 1
    if len(_names) > 1:
        _SHARE_CLONE[tuple(_names)] += 1
    elif (not _names) and _reason.startswith("重叠无y判据"):
        _PENDING_ASSIGN.append({"x": round(x, 2), "y": y, "列代表y": _yy,
                                "内容": content, "原因": _reason})
    return _names

# 为 INSERT 实体分配楼栋归属（须在 bldg_ranges 计算之后）
if insert_items:
    for ins in insert_items:
        _names = _assign(ins["x"], ins.get("y"), ins.get("块名"), _COL_Y.get(id(ins)))
        ins["楼"] = _names[0] if _names else None
        if len(_names) > 1:
            ins["楼_共享"] = _names

# 为每栋楼分配文字（共享区间 → 同一批文字克隆给组内每一栋，不再先到先得）
bldg_texts = defaultdict(list)
for t in texts:
    for _n in _assign(t["x"], t.get("y"), t.get("内容"), _COL_Y.get(id(t))):
        bldg_texts[_n].append(t)

# ---------- 区间自检：把「区间装不下自己的实体」显式报出（2026-09-18 新增） ----------
def _is_biz_text(c):
    """含业务特征的文字（楼层刻度 / 每层户数 / 皮线米数 / 分纤箱编号）。"""
    if not c:
        return False
    if _is_floor_text(c):
        return True
    if FX_RE and FX_RE.search(c):
        return True
    if HU_RE and HU_RE.fullmatch(clean_text(c)):
        return True
    if CABLE_RE and CABLE_RE.fullmatch(clean_text(c)):
        return True
    return False

_RANGE_DIAG = bldg_range_diagnostics(bldg_ranges, texts, featured=_is_biz_text,
                                     anchor_y_of=anchor_y_of)
_widths = [r["宽"] for r in _RANGE_DIAG["楼栋"]]
_med_w = _stat.median(_widths) if _widths else 0.0
_NARROW = []
if _med_w > 0:
    for _r in _RANGE_DIAG["楼栋"]:
        if _r["宽"] < _med_w / 3.0:
            _NARROW.append({"楼栋": _r["楼栋"], "宽": round(_r["宽"], 2),
                            "中位宽": round(_med_w, 2), "区间内条数": _r["条数"]})
            log.warning("  [区间过窄] %s 区间宽 %.1f，仅占中位宽 %.1f 的 %.0f%%（区间内 %d 条）"
                        "——疑锚点不居中或共享锚点未拆分，本栋实体可能被切在区间外"
                        % (_r["楼栋"], _r["宽"], _med_w, 100.0 * _r["宽"] / _med_w, _r["条数"]))
_BIZ_ORPHAN = [o for o in _RANGE_DIAG["孤儿"] if o["业务实体"]]
# 参考量：相邻锚点间距的中位数（仅登记进产物，不作判据）
_sorted_b = sorted(bldg_ranges, key=lambda k: bldg_ranges[k][0])
_gaps = [bldg_ranges[_sorted_b[i + 1]][0] - bldg_ranges[_sorted_b[i]][0]
         for i in range(len(_sorted_b) - 1)]
_med_gap = _stat.median(_gaps) if _gaps else 0.0
# 只把「贴边」的孤儿当可疑：距最近区间边界 < **该栋区间宽的 1/4**。
# 远离全部区间的（如图纸左侧总图区对照表、别带的箱清单）是独立图区，被排除本来
# 就是对的，不报 —— 实测某图总图区箱清单距首栋左界 83~167（约半个区间宽），
# 若用「锚点间距中位」当阈值会全部误报。
_wmap = {r["楼栋"]: r["宽"] for r in _RANGE_DIAG["楼栋"]}
_BIZ_ORPHAN_SUSPECT = [o for o in _BIZ_ORPHAN
                       if o["距边界"] is not None and _wmap.get(o["最近楼栋"], 0) > 0
                       and o["距边界"] < 0.25 * _wmap[o["最近楼栋"]]]
if _BIZ_ORPHAN_SUSPECT:
    log.warning("  [业务实体落空] %d 条含业务特征的文字紧贴区间边界却被排除"
                "（判据：距边界 < 本栋区间宽的 1/4）——须复核是否被边界切出：%s"
                % (len(_BIZ_ORPHAN_SUSPECT),
                   "；".join("%s@x%.1f(距%.1f)" % (o["内容"], o["x"], o["距边界"])
                             for o in _BIZ_ORPHAN_SUSPECT[:6])))
elif _BIZ_ORPHAN:
    log.info("  [业务实体落空] %d 条含业务特征的文字位于全部楼栋区间之外且远离边界"
             "（判据：距边界 >= 本栋区间宽的 1/4）→ 判为独立图区（总图/平面图/别带），已排除"
             % len(_BIZ_ORPHAN))

# ---------- 孤儿分类账（2026-09-18 新增） ----------
# 「未命中」常占全图文字 40%~60%（实测三项目 175~393 条/图），此前只有一个总数 ——
# 既看不出是「独立图区（图例/材料表/图框）」还是「被边界切出」，也无法核对与复现。
# 现按**机械判据**分类计数（只登记、不裁决），并把每类样本落产物：
#   ①贴边疑切出 —— 距最近区间边界 < τ（τ = 0.25×最近楼栋区间宽，与既有可疑口径同源）
#   ②跨带落空   —— x 落在**别带**的区间内（本带无区间覆盖）
#   ③带内缝隙   —— x 在本带包络内，但落在相邻区间之间
#   ④图区外     —— x 在本带包络（含 τ 余量）之外 → 独立图区，被排除本来就是对的
_band_env, _band_of_bldg = {}, {}
for _i, _b in enumerate(_bldg_bands):
    _rs = [bldg_ranges[_n] for _n in (_b.get("names") or []) if _n in bldg_ranges]
    if _rs:
        _band_env[_i] = (min(r[0] for r in _rs), max(r[1] for r in _rs))
    for _n in (_b.get("names") or []):
        _band_of_bldg[_n] = _i
_ORPHAN_CLS = Counter()
_ORPHAN_SAMPLE = defaultdict(list)
for _o in _RANGE_DIAG["孤儿"]:
    _x = _o.get("x") or 0.0
    _nb = _o.get("最近楼栋")
    _bw = _wmap.get(_nb, 0.0)
    _tau = 0.25 * _bw if _bw > 0 else 0.0
    _bi = _band_of_bldg.get(_nb)
    _env = _band_env.get(_bi) if _bi is not None else None
    if _tau > 0 and _o.get("距边界") is not None and _o["距边界"] < _tau:
        _cls = "①贴边疑切出"
    elif [n for n, (lo, hi) in bldg_ranges.items()
          if lo <= _x <= hi and _band_of_bldg.get(n) != _bi]:
        _cls = "②跨带落空"
    elif _env and (_env[0] <= _x <= _env[1]):
        _cls = "③带内缝隙"
    else:
        _cls = "④图区外(独立图区)"
    _ORPHAN_CLS[_cls] += 1
    if _o.get("业务实体"):
        _ORPHAN_CLS[_cls + "/含业务特征"] += 1
    if len(_ORPHAN_SAMPLE[_cls]) < 3:
        _ORPHAN_SAMPLE[_cls].append("%s@x%.1f" % (str(_o.get("内容"))[:16], _x))
log.info("  [孤儿分类账] 合计 %d 条：%s"
         % (len(_RANGE_DIAG["孤儿"]),
            " ｜ ".join("%s=%d" % (k, v) for k, v in sorted(_ORPHAN_CLS.items()))))

# ---------- 尺度锚：阈值按层高自适应（2026-09-15 通用化，须在 split_units 系列首次使用 args.* 前解析） ----------
# 比值的历史出处：层高 30 时 unit_cluster=30 / unit_range=120 / y_tol=2（原手调默认值）。
# 2026-09-16：install_tol 已整体废弃（比值／回退值／命令行参数／输出字段一并移除）。
#   安装楼层一律走纯区间法，与 analyze_coverage.py 的 f_install 口径统一。
#   原小容差闸门（1/6 倍层高）只覆盖楼层带下沿的一小段，而箱体落点不固定，
#   实测某图分纤箱到下方层线的距离普遍大于闸门值 → 安装楼层整列落空。
_TOL_RATIOS = {"unit_cluster": 1.0, "unit_range": 4.0,
               "y_tol": 1.0 / 15.0}
_TOL_FALLBACK = {"unit_cluster": DEFAULT_UNIT_CLUSTER, "unit_range": DEFAULT_UNIT_RANGE,
                 "y_tol": DEFAULT_Y_TOL}
_step, _basis = floor_step_from_texts(texts, _is_floor_text)
if _step:
    for _n, _r in _TOL_RATIOS.items():
        if not getattr(args, _n):        # None / 0 均视为自适应（与 analyze_coverage 的 0=auto 约定一致）
            setattr(args, _n, _r * _step)
    log.info("尺度锚：层高 %.4g（%s）→ unit_cluster=%.4g / unit_range=%.4g / y_tol=%.4g"
             % (_step, _basis, args.unit_cluster, args.unit_range, args.y_tol))
else:
    for _n, _d in _TOL_FALLBACK.items():
        if getattr(args, _n) is None:
            setattr(args, _n, _d)
    log.warning("尺度锚量测失败（%s）→ 回退绝对默认值 %s", _basis,
                {k: getattr(args, k) for k in _TOL_FALLBACK})

# ---------- 分单元（优先用单元标注锚点，其次 fx 聚类） ----------
def split_units_no_fx(bldg_text_list):
    """无 fx 文字时，全部文字归入'全部'单元。"""
    return {"全部": bldg_text_list}

def split_units_by_marker(bldg_text_list, unit_marks, bldg_name=None):
    """有单元标注时，以单元标注 x 为锚点中分。

    2026-09-12 修正（P0-2）：
      1. 单元名重名时报错退出，不再静默覆盖（旧实现 dict key 覆盖导致 1#楼只剩 2 个假单元）。
      2. 若 bldg_name 提供，校验单元标注与楼栋同号（如「2#楼」只认「2#楼N单元」），
         避免总图区的「N#楼M单元」被误归给不相关楼栋。
    """
    units = []
    seen_names = set()
    for t in sorted(unit_marks, key=lambda t: t["x"]):
        m = UNIT_RE.search(t["内容"])
        uname = m.group(1) + "单元" if m else t["内容"]
        # P0-2 修正③：重名单元报错，不静默覆盖
        if uname in seen_names:
            log.warning(f"  [重复单元] 单元名 {uname!r} 重复出现（来自 {t['内容']!r}），"
                        f"可能是总图区标注混入。仅保留首次出现。")
            continue
        seen_names.add(uname)
        units.append({"x": t["x"], "名": uname})
    result = {}
    unit_anchors = [(u["名"], u["x"]) for u in units]
    if not unit_anchors:
        return result
    unit_ranges = compute_bldg_ranges(unit_anchors)
    for u in units:
        xlo, xhi = unit_ranges[u["名"]]
        result[u["名"]] = [t for t in bldg_text_list if xlo <= t["x"] < xhi]
    return result

def split_units_by_fx_cluster(fx_texts, bldg_text_list):
    """无单元标注时，用 fx 聚类分单元。"""
    fx_clusters = cluster_by_x(fx_texts, args.unit_cluster)
    result = {}
    for i, c in enumerate(fx_clusters):
        cx = c["x"]
        if i == 0:
            xlo = cx - args.unit_range
        else:
            xlo = max((fx_clusters[i - 1]["x"] + cx) / 2, cx - args.unit_range)
        if i == len(fx_clusters) - 1:
            xhi = cx + args.unit_range
        else:
            xhi = min((cx + fx_clusters[i + 1]["x"]) / 2, cx + args.unit_range)
        uname = f"单元{i+1}"
        result[uname] = [t for t in bldg_text_list if xlo <= t["x"] < xhi]
    return result

def split_units(bldg):
    fx_texts = [t for t in bldg_texts[bldg] if FX_RE and FX_RE.search(t["内容"])]
    unit_marks = [t for t in bldg_texts[bldg] if UNIT_RE and UNIT_RE.search(t["内容"])]
    if not fx_texts:
        return split_units_no_fx(bldg_texts[bldg])
    if unit_marks:
        return split_units_by_marker(bldg_texts[bldg], unit_marks, bldg_name=bldg)
    return split_units_by_fx_cluster(fx_texts, bldg_texts[bldg])

# ---------- 楼层信息解析（正则全部参数化） ----------
def parse_floor_info(unit_texts):
    floor_marks = {}   # 楼层名(如"1F") -> y
    fx_list = []       # {编号, x, y}
    hu_count = {}      # y -> 户数
    cable_info = {}    # y -> (米数, 根数)
    cable_names = {}   # 文字 -> y
    others = []
    for t in unit_texts:
        txt = clean_text(t["内容"])
        y = t["y"]
        if _is_floor_text(txt):
            floor_marks[txt] = y
            continue
        if FX_RE is not None:
            m = FX_RE.search(txt)
            if m:
                # 2026-09-16：原实现只留 y（层位）、**丢掉 x** —— 分纤箱「安装位置」因此
                #   只剩楼层、没有平面位置，两个同层同单元的箱无法在几何上区分，也无法与
                #   台账/总图按平面位置对照。x 与编号同源同行文字，直接取用最稳。
                fx_list.append({"编号": m.group(0), "x": t["x"], "y": y})
                continue
        if HU_RE is not None:
            m = HU_RE.fullmatch(txt)
            if m:
                hu_count[y] = int(m.group(1))
                continue
        if CABLE_RE is not None:
            m = CABLE_RE.fullmatch(txt)
            if m:
                _mm, _cc = _cable_tuple(m)
                _bad = None
                if _mm is None:
                    _bad = "米数未捕获（pattern 缺 meters 命名组，也无位置组）"
                else:
                    try:
                        cable_info[y] = (int(round(float(_mm))),
                                         int(_cc) if _cc else 1)
                    except (TypeError, ValueError) as _e:
                        _bad = "捕获值无法转数值（米数=%r 根数=%r）：%s" % (_mm, _cc, _e)
                if _bad:
                    # 匹配上却解析不出 = pattern 与图面写法不合，必须可见（不静默吞掉）
                    log.warning("皮线米数标注 %r 解析失败：%s" % (txt, _bad))
                continue
        if TITLE_RE.search(txt):
            continue
        if CABLE_KW_RE is not None and CABLE_KW_RE.search(txt):
            # P1-14 修正：排除图框标题（含换行符或过长的文字）和已被 TITLE_RE 匹配的标题
            if '\n' in txt or len(txt) > 40:
                continue
            cable_names[txt] = y
            continue
        others.append((txt, y))
    return floor_marks, fx_list, hu_count, cable_info, cable_names, others

result = {
    "DXF文件": os.path.basename(DXF_PATH),
    "DXF版本": doc.dxfversion,
    "参数": {
        "text_layer": LAYERS,
        "text_type": TYPES,
        "title_pattern": args.title_pattern,
        "floor_pattern": args.floor_pattern or "内置统一解析（3F/17F/-1F/B1/B2/WF）",
        "hu_pattern": args.hu_pattern or "未提供（不提取户数）",
        "cable_pattern": args.cable_pattern or "未提供（不提取皮线）",
        "fx_pattern": args.fx_pattern or "未提供（不提取分纤箱）",
        "unit_pattern": args.unit_pattern or "未提供（用分纤箱x聚类分单元）",
        "unit_cluster": args.unit_cluster,
        "unit_range": args.unit_range,
        "y_tol": args.y_tol,
    },
    "楼栋": {},
    # 2026-09-18 新增：把边界与归属依据落进产物（此前只进 log，下游拿不到 ⇒ 无法守门）
    "楼栋边界": {
        "分带容差": _band_tol,
        "带": _bldg_bands,
        "区间": {_b: [round(_lo, 3), round(_hi, 3)] for _b, (_lo, _hi) in bldg_ranges.items()},
        "共享区间": _shared_src,
        "归属统计": dict(_ASSIGN_STAT),
        "共享克隆": {"、".join(_k): _v for _k, _v in _SHARE_CLONE.items()},
        # 列共识判带：跨带重叠时改用「同 x 列」的 y 中位判带（防一条列被拆给两栋）。
        # 只列参与的点数与列 x，供人工复核「这条列凭什么判给这个带」。
        "列共识判带": {"条数": sum(_COL_USED.values()),
                       "列数": len(_COL_USED),
                       "列x": [{"x": _k, "条数": _v}
                               for _k, _v in sorted(_COL_USED.items())[:50]]},
        "单锚点带": _SINGLE_ANCHOR_BANDS,
        # 2026-09-18：**截断必须带总数** —— 旧实现只存前 100 条且不记总数，下游看到 100 会
        #   当成全部（实测两处真值均 >=100，属「没核不得输出成通过」同族缺陷）。
        "待裁决归属": {"总数": len(_PENDING_ASSIGN), "展示": _PENDING_ASSIGN[:100]},
        "区间过窄": {"总数": len(_NARROW), "展示": _NARROW[:100]},
        "业务实体落空": {"总数": len(_BIZ_ORPHAN), "展示": _BIZ_ORPHAN[:100]},
        "业务实体落空_可疑": {"总数": len(_BIZ_ORPHAN_SUSPECT), "展示": _BIZ_ORPHAN_SUSPECT[:100]},
        "孤儿总数": len(_RANGE_DIAG["孤儿"]),
        "孤儿分类账": dict(sorted(_ORPHAN_CLS.items())),
        "孤儿分类样本": {k: v for k, v in sorted(_ORPHAN_SAMPLE.items())},
        "锚点间距中位": _med_gap,
        "自检": {"楼栋": _RANGE_DIAG["楼栋"], "异常": _RANGE_DIAG["异常"]},
    },
}

# ---------- --fx-map：总图对照表回填（2026-09-18 新增） ----------
# 动机：inspect 的 C2/C3/C6 会因 parse 侧「安装楼层=null」判 FAIL，而该 null 常源于
#   本单元图上确实无楼层线可归属（配套楼、地下室等），不是数据错误；总图对照表
#   （extract_fx_map，独立方法）里同一编号往往有楼层可查。
# 纪律：① 只补缺失，**绝不覆盖已测出的值**；② 重号不自行择一，登记交人工；
#       ③ 回填留来源标记，供 inspect 与人工追溯。
FX_MAP = {}          # 编号 -> [entry, ...]
FXMAP_FILLED = []    # 回填留痕
FXMAP_SKIP_DUP = []  # 重号未回填
_fxmap_meta = None
if args.fx_map:
    try:
        with open(args.fx_map, "r", encoding="utf-8") as _f:
            _raw = json.load(_f)
    except (IOError, json.JSONDecodeError) as e:
        log.error("无法读取 --fx-map %s: %s" % (args.fx_map, e))
        sys.exit(1)
    _entries = _raw.get("FX映射表") if isinstance(_raw, dict) else _raw
    if not isinstance(_entries, list):
        log.error("--fx-map 格式不对：顶层应含「FX映射表」数组（确认是 extract_fx_map.py 产物）")
        sys.exit(1)
    for _e in _entries:
        if isinstance(_e, dict) and _e.get("编号"):
            FX_MAP.setdefault(str(_e["编号"]).strip(), []).append(_e)
    _dups = sorted(k for k, v in FX_MAP.items() if len(v) > 1)
    _fxmap_meta = {"文件": os.path.basename(args.fx_map), "条目数": len(_entries),
                   "唯一编号": len(FX_MAP), "重号编号": _dups}
    log.info("已载入 --fx-map：%d 条目 / %d 唯一编号%s"
             % (len(_entries), len(FX_MAP),
                ("（重号 %d 个不回填：%s）" % (len(_dups), "、".join(_dups[:8]))) if _dups else ""))

# ---------- --bldg-map：按总图对照表定「箱的楼栋/单元归属」（2026-09-18 新增） ----------
# 动机：SKILL.md 硬约束② 明文「楼栋/单元归属**必须以图纸自带的分纤箱总图对照表为准**，
#   严禁用标题 x 区间硬切（系统图区常两行交错排布、纵向重叠横向错开，按标题 x 中分
#   **必然串行**）」。但此前只有 analyze_coverage.py 接了 --bldg-map，本脚本没有 ——
#   总图对照表形态的图纸（箱编号集中在独立图区，x 不落在任何楼栋标题区间内）逐栋 0 箱，
#   而 rc 仍为 0（静默丢数；下游不跑 inspect 不会察觉）。
# 纪律：① 只改「归属」，**不改「安装楼层」** —— 安装楼层仍走本脚本的区间法，与对照表的
#          分歧由 inspect 的 C3 双源交叉 + C7 报人处理，此处不择一；
#       ② 重号（同编号被对照表映射到多处）不自行择一，登记交人工；
#       ③ 每条改派留痕，可回原文坐标追溯。
BDG_MAP = {}          # 编号 -> [entry, ...]（extract_fx_map 的 FX映射表条目）
BDGMAP_MOVED = []     # 改派留痕（跨栋才记，同栋只并入单元）
BDGMAP_SKIP_DUP = []  # 重号未改派
BDGMAP_NAMEMISS = []  # 对照表单元名与 parse 原单元名并存登记
_bdgmap_meta = None
if args.bldg_map:
    try:
        with open(args.bldg_map, "r", encoding="utf-8") as _f:
            _raw2 = json.load(_f)
    except (IOError, json.JSONDecodeError) as e:
        log.error("无法读取 --bldg-map %s: %s" % (args.bldg_map, e))
        sys.exit(1)
    _entries2 = _raw2.get("FX映射表") if isinstance(_raw2, dict) else _raw2
    if not isinstance(_entries2, list):
        log.error("--bldg-map 格式不对：顶层应含「FX映射表」数组（确认是 extract_fx_map.py 产物）")
        sys.exit(1)
    for _e2 in _entries2:
        if isinstance(_e2, dict) and _e2.get("编号"):
            BDG_MAP.setdefault(str(_e2["编号"]).strip(), []).append(_e2)
    _dups2 = sorted(k for k, v in BDG_MAP.items() if len(v) > 1)
    _bdgmap_meta = {"文件": os.path.basename(args.bldg_map), "条目数": len(_entries2),
                    "唯一编号": len(BDG_MAP), "重号编号": _dups2}
    log.info("已载入 --bldg-map：%d 条目 / %d 唯一编号%s"
             % (len(_entries2), len(BDG_MAP),
                ("（重号 %d 个不改派：%s）" % (len(_dups2), "、".join(_dups2[:8]))) if _dups2 else ""))

# ---------- --bldg-map 改派：把 FX 文字挂到对照表给定的楼栋/单元 ----------
# 必须在楼栋循环之前完成。改派对象是**文字本身**：先在每栋文字里摘出有对照表映射的
# FX 文字，再按对照表楼栋/单元重新挂入（同栋同单元的也统一走这条通道，保证单元名
# 以对照表为准）。对照表没有的编号、重号、楼栋名不在本图锚点内的，一律**保持原
# 标题 x 硬切结果**并留痕，不猜、不静默择一。
def _norm_bldg(s):
    """楼栋名归一化：只做**等价写法折叠**，不做语义推断。

    现状：同一张图上楼栋名有两种写法并存 —— 系统图标题写 `1#楼`，
    箱表描述写 `1号楼1单元2层`。对照表条目若原样带 `号楼…单元…层` 后缀，
    用 `startswith` 去撞 `1#楼` 必然失败，条目**整批静默丢弃**（实测某图 22 条
    对照表一条未挂上，箱归属全空而 rc 仍 0）。
    折叠规则（都是同义替换，不改变任何数字）：
      · `#` / `＃` → `号`；· 去空白；· 去尾部 `单元/层` 等描述性后缀。
    不做的事：不把 `1号楼` 猜成别的楼号、不做模糊匹配 —— 匹配仍然要求前缀相等。
    """
    if not s:
        return ""
    t = re.sub(r"\s+", "", str(s))
    t = t.replace("＃", "号").replace("#", "号")
    # 去掉描述性后缀（单元号 / 层号 / 户数），保留楼栋本体
    t = re.sub(r"\d+\s*单元.*$", "", t)
    t = re.sub(r"\d+\s*层.*$", "", t)
    return t


def _resolve_bldg_name(name):
    """把对照表的「楼栋」值解析为本图锚点楼栋名（bldg_ranges 的键）。

    对照表由 extract_fx_map.py 产出，其「楼栋」字段取自最近楼栋标注，形态可为
    `3#楼` 或 `3#楼2单元`；而本脚本 bldg_ranges 的键是**不含单元**的楼栋名
    （如 `3#楼`）。不做这一步解析，含单元后缀的条目会被 `not in bldg_ranges`
    整批丢掉（2026-09-18 实测：23 条里只有 4#配套楼 / 11#配套楼两个无后缀的通过，
    箱数只从 0 涨到 2 而非 23）。

    2026-09-18 二次修正：仅做前缀匹配还不够 —— 另有 `1号楼…`（`号`）与锚点
    `1#楼`（`#`）**写法不同**的形态，实测某图 22 条对照表因此一条都挂不上。
    现改为先归一化（见 _norm_bldg）再匹配，等价写法折叠、数字一律不动。

    规则：归一化后精确命中优先；否则取「归一化后是它的前缀」的最长锚点名；
    都不命中返回 None（不猜），并由调用方**登记**而非静默丢弃。
    """
    if not name:
        return None
    if name in bldg_ranges:
        return name
    _n = _norm_bldg(name)
    if not _n:
        return None
    for _b in bldg_ranges:                      # 归一化后精确命中
        if _b != name and _norm_bldg(_b) == _n:
            return _b
    best = None
    for _b in bldg_ranges:
        _nb = _norm_bldg(_b)
        if _nb and _n.startswith(_nb) and (best is None or len(_nb) > len(_norm_bldg(best))):
            best = _b
    return best


BDGMAP_UNRESOLVED = []   # 对照表楼栋值无法解析到本图锚点 -> 登记（不静默丢弃）

# ---------- 分纤箱实例台账（2026-09-18 新增） ----------
# 动机：编号文字在图上出现 ≠ 分纤箱个数。实测某图同一编号被重复绘制 3 处
#   （同一图幅重复绘制 / 平面图箱符号与系统图箱表并列），原实现「一处文字 = 一个箱」
#   ⇒ 箱数虚高数倍、成品箱编号列重复。另：对照表未认领的编号文字，其 x 常落在所有
#   楼栋标题 x 区间之外 ⇒ 不进任何单元桶 ⇒ **静默消失**（图上确有文字、产物查无此箱）。
# 纪律：① 已归入某单元桶的**文字实例**按 (编号, x) 记账，用于事后找出未被收录的文字；
#       ② 文字不得丢 —— 未归属者收入「未归属分纤箱」显式容器 + 登记「需人工裁决」，
#          该容器不进成品（地址表只读「楼栋」），故未裁决值不污染成品。
_CONSUMED_FX = set()     # {(编号, round(x,2))} 已被某单元收录的编号文字实例
FX_DEDUP = []            # 同编号多实例收敛留痕
PENDING_NOTES = []       # parse 侧「需人工裁决」登记（透传进产物）
_FX_ENTRY = {}           # {(编号, round(x,2))} -> 该实例配对到的对照表条目（重号实例专用）
BDGMAP_DUP_MATCHED = []  # 重号按坐标配对成功的留痕
FX_DROPPED_DUP = []      # 重号编号中「与任何对照表实例都配不上坐标」的文字实例（不产出箱）


_FX_FORCE = {}          # 楼栋名 -> {对照表单元名: [text, ...]}
if BDG_MAP:
    # 改派必须从**全图 texts** 出发，不能从 bldg_texts 出发 —— bldg_texts 是「已按
    #   楼栋标题 x 区间切好」的结果，而本类图纸的箱编号恰好落在**所有楼栋区间之外**
    #   （汇总在独立的总图对照表区），压根不在 bldg_texts 里。从它里面找等于
    #   「在错误的地方找丢失的东西」，必然 0 命中（2026-09-18 实测踩中）。
    _owner = {}
    for _b0 in list(bldg_texts.keys()):
        for _t0 in bldg_texts[_b0]:
            _owner[id(_t0)] = _b0          # 记录原归属，用于留痕与移除
    _moved = 0
    _claimed = set()
    for _t in texts:
        _m = FX_RE.search(_t["内容"]) if FX_RE else None
        if not _m:
            continue
        _no = _m.group(0).strip()
        _cand = BDG_MAP.get(_no)
        if not _cand:
            continue                          # 对照表无此编号 -> 保持原归属
        if len(_cand) > 1:
            # 重号：同一编号在对照表里有多个实例（= 图上确有多个不同箱用了同一个号）。
            # 2026-09-18：原实现一律 continue（不择一交人工）—— 归属确实定不了，但**箱就
            #   此消失**（其实例 x 常落在所有楼栋区间之外），下游只看到「parse 漏收录」。
            # 现按**对照表条目自带坐标**与该编号文字实例做最近配对：条目坐标就是同一张图上
            #   该编号文字的位置，二者是**同一次测量的同一个点**，距离≈0 即同一实例 ——
            #   属「测量」而非「推理」（有客观判据，可复核）。配对成功则该实例按条目的
            #   楼栋/单元/楼层归属；配不上（超容差）仍不择一，交人工。
            _scored = []
            for _e in _cand:
                try:
                    _ex, _ey = float(_e.get("x")), float(_e.get("y"))
                except (TypeError, ValueError):
                    continue
                _scored.append((abs(_ex - _t["x"]) + abs(_ey - _t["y"]), _e))
            _ymatch_tol = max(1.0, 0.5 * float(_t.get("高") or 0.0))
            if not _scored or min(_scored, key=lambda z: z[0])[0] > _ymatch_tol:
                BDGMAP_SKIP_DUP.append(_no)   # 配不上 -> 不择一，登记
                continue
            _dist1, _pick1 = min(_scored, key=lambda z: z[0])
            _cand = [_pick1]
            BDGMAP_DUP_MATCHED.append(
                "%s@(%.1f,%.1f)：对照表 %d 个实例中按坐标配对到「%s/%s %s」（距离 %.2f）"
                % (_no, _t["x"], _t["y"], len(_scored),
                   _pick1.get("楼栋"), _pick1.get("单元"), _pick1.get("安装楼层"), _dist1))
        _tb0 = str(_cand[0].get("楼栋") or "").strip()
        _tb = _resolve_bldg_name(_tb0)
        if not _tb:
            # 对照表楼栋在本图锚点里找不到 -> 不猜；但**必须登记**。
            # 2026-09-18 实测：此处原先静默 continue，22 条对照表一条没挂上而日志
            # 只有「改派 0 个」，看不出是被丢掉还是本身为空 —— 静默丢数是缺陷。
            BDGMAP_UNRESOLVED.append("%s: 对照表楼栋=%r 未命中本图锚点（锚点：%s）"
                                     % (_no, _tb0, "/".join(sorted(bldg_ranges)[:8])))
            continue
        # 单元名取对照表的「单元」字段（如 `1#楼1单元`，与 coverage 侧同源）；
        # 缺该字段时退化为楼栋名，不自行编造单元号。
        _tu = str(_cand[0].get("单元") or "").strip() or _tb
        _FX_FORCE.setdefault(_tb, {}).setdefault(_tu, []).append(_t)
        # 配对到的对照表条目按文字实例记账（(编号, x) 为该实例的唯一键）——
        #   安装楼层须用**该实例自己**的条目，不能再用「编号→条目」查表（重号时查不出）。
        _FX_ENTRY[(_no, round(_t["x"], 2))] = _cand[0]
        _claimed.add(id(_t))
        _moved += 1
        _old = _owner.get(id(_t))
        if _old != _tb:
            # 「(不在任何楼栋x区间)」这一情形正是本类图纸的特征，留痕备查
            BDGMAP_MOVED.append("%s: %s -> %s/%s"
                                % (_no, _old or "(不在任何楼栋x区间)", _tb, _tu))
    if _claimed:                              # 从原楼栋摘除，避免重复计数
        for _b0 in list(bldg_texts.keys()):
            bldg_texts[_b0] = [_t0 for _t0 in bldg_texts[_b0]
                               if id(_t0) not in _claimed]
    log.info("--bldg-map 改派：%d 个 FX 文字按对照表归属（跨栋/跨区 %d 个）；重号未改派 %d 个"
             % (_moved, len(BDGMAP_MOVED), len(set(BDGMAP_SKIP_DUP))))
    if BDGMAP_UNRESOLVED:
        log.warning("--bldg-map 有 %d 个编号的对照表楼栋值解析不到本图锚点（这些箱保持原归属）：%s"
                    % (len(BDGMAP_UNRESOLVED), "；".join(BDGMAP_UNRESOLVED[:5])))
    _bdgmap_meta["改派条数"] = _moved
    _bdgmap_meta["跨栋改派"] = BDGMAP_MOVED
    _bdgmap_meta["重号未改派"] = sorted(set(BDGMAP_SKIP_DUP))
    _bdgmap_meta["楼栋值未解析"] = BDGMAP_UNRESOLVED

for bldg in sorted(bldg_ranges.keys(), key=lambda x: bldg_num(x)):
    titles = [t["内容"] for t in bldg_texts[bldg] if TITLE_RE.search(t["内容"])]
    units = split_units(bldg)
    # --bldg-map：把对照表认领的箱注入其单元，单元名以对照表为准。
    #   该楼对照表只有一个单元名时，parse 原划分（常是占位名「全部」）整体并入该名下
    #   —— 否则 parsed.json 的单元名与 coverage.json（走 bldg-map）对不上、无法 join。
    #   有多个单元名时保留 parse 原划分作**非箱文字容器**，另按要求新增单元，并登记
    #   「名称并存」交人工，不静默合并、不丢文字。
    _forced = _FX_FORCE.get(bldg) or {}
    if _forced:
        if len(_forced) == 1:
            _only = list(_forced.keys())[0]
            _merged = []
            for _u0, _tl0 in units.items():
                _merged.extend(_tl0)
            units = {_only: _merged}
        elif units:
            BDGMAP_NAMEMISS.append(
                "%s: 对照表单元 %s 与 parse 原单元 %s 并存（非箱文字仍在原单元）"
                % (bldg, "/".join(sorted(_forced)), "/".join(sorted(units.keys()))))
        for _u0, _tl0 in _forced.items():
            units[_u0] = list(units.get(_u0) or []) + list(_tl0)
    result["楼栋"][bldg] = {"标题": titles[0] if titles else "", "单元": {}}
    for uname, unit_texts in units.items():
        floor_marks, fx_list, hu_count, cable_info, cable_names, others = parse_floor_info(unit_texts)
        floor_table = {}
        # 楼层表按楼层数字排序（1F→2F→…→N F），便于阅读与后续处理
        # 准备楼层标注列表供二分查找（替代 O(N×M) 遍历）
        floor_items = [(fl, fy) for fl, fy in floor_marks.items()]
        for fl, fy in sorted(floor_marks.items(), key=lambda kv: floor_num_or_zero(kv[0], args.floor_pattern, use_fullmatch=True)):
            # 户数匹配：y 坐标最近（排序+二分，O(log N)）
            hu = None
            hu_items = list(hu_count.items())  # [(y, n), ...]
            best_hu, _ = match_y_to_floor(fy, hu_items, tol=args.y_tol, y_key=lambda it: it[0])
            if best_hu is not None:
                hu = best_hu[1]  # (y, n) 的 n
            # 皮线匹配：同理
            cable = None
            cable_items = list(cable_info.items())  # [(y, (m, count)), ...]
            best_cable, _ = match_y_to_floor(fy, cable_items, tol=args.y_tol, y_key=lambda it: it[0])
            if best_cable is not None:
                cable = best_cable[1]  # (y, (m, count)) 的 (m, count)
            floor_table[fl] = {
                "户数": hu,
                "布线": f"{cable[0]}m*{cable[1]}" if cable else None,
                "fl_num": floor_num_or_zero(fl, args.floor_pattern, use_fullmatch=True),
            }
        for fx in fx_list:
            # 2026-09-18：该文字实例已被本单元收录 —— 记账，供事后找出「图上确有编号
            #   文字、产物里查无此箱」的静默丢数（详见文件内「未归属分纤箱」一节）。
            _CONSUMED_FX.add((str(fx.get("编号", "")).strip(), round(fx.get("x", 0.0), 2)))
            # 安装楼层匹配：区间法（2026-09-12 P0-6 修正：从最近线法改为区间法）
            # 2026-09-16 P0：此处原先传 tol=install_tol（1/6 倍层高）作距离闸门。闸门在 bisect
            #   完成区间归属**之后**再二次否决，效果等价于「必须贴着下方层线才算」＝「最近楼层
            #   线法」，与 SKILL.md「禁止用最近楼层线法测分纤箱安装楼层」「安装楼层必须与户数
            #   同用区间法」两条明文冲突；且闸门只覆盖楼层带下沿一小段，实测某图分纤箱到下方
            #   层线的距离普遍大于闸门值，安装楼层整列落空而脚本仍 rc=0。
            #   现改 tol=None（纯区间法），与 analyze_coverage.py 的 f_install 口径统一；
            #   dist 仍返回，用于区分口径A（图上直写）/ 口径B（区间法）。
            fl_name, dist = assign_floor_by_interval(fx["y"], floor_items)
            # ---- 对照表认领的箱：安装楼层取图上直写口径A，区间法结果降级为参考留痕 ----
            # 本类图纸的箱编号写在**独立的总图对照表图区**，其 y 与楼栋系统图的楼层刻度
            #   不是同一坐标系；拿它的 y 去套系统图楼层带，得到的层号（实测出现过 WF /
            #   16F 等）不具物理意义。对照表给的是图纸上直写的安装楼层，属权威来源。
            # 判据（客观、可复核，故属「有判据自判」而非「猜」）：
            #   ① 该编号在总图对照表里有**唯一**映射；② 该映射带非空安装楼层。
            #   两条不同时成立则一切照旧 —— 不猜、不放宽。
            # 留证：区间法原值原样写入 区间法参考值/区间法参考误差 供审计，证据不丢；
            #   并保留 C3 双源交叉（parse 本分支值 vs coverage 独立方法）作第二来源。
            _bdg = BDG_MAP.get(str(fx.get("编号", "")).strip()) if BDG_MAP else None
            # 重号实例：优先用**该文字实例自己配对到的条目**（见上方按坐标配对），
            #   否则退回「编号唯一映射」。
            _ent1 = _FX_ENTRY.get((str(fx.get("编号", "")).strip(),
                                   round(fx.get("x", 0.0), 2)))
            if _ent1 is None and _bdg and len(_bdg) == 1:
                _ent1 = _bdg[0]
                _ent1_is_dup = False
            else:
                _ent1_is_dup = _ent1 is not None
            if _ent1 and _ent1.get("安装楼层"):
                fx["区间法参考值"] = fl_name
                # 非有限距离（本单元无可用楼层行时 assign_floor_by_interval 返回 inf）
                #   一律写 null：json.dump 会把 inf 写成非标准的 `Infinity`，
                #   严格 JSON 解析器（JS/Go/多数工具）会拒绝**整份**产物。
                fx["区间法参考误差"] = (round(dist, 2)
                                    if isinstance(dist, (int, float)) and math.isfinite(dist)
                                    else None)
                fx["安装楼层"] = _ent1["安装楼层"]
                fx["安装楼层口径"] = ("口径A′:对照表内该编号实例坐标配对（图上直写）"
                                    if _ent1_is_dup else "口径A:图上直写（总图对照表）")
                fx["安装楼层来源"] = "fxmap对照表"
                fx["安装楼层误差"] = 0.0
                # ---- 结果状态契约（v3.1 L1-C8）产出方落地 ----
                # 对照表实例坐标配对（唯一命中）+ 非空安装楼层 = 客观判据 ⇒ measured + settled
                fx["result_origin"] = "measured"
                fx["result_confirmation"] = "settled"
                fx["依据来源"] = ("E-DXF-TEXT:总图对照表（图上直写安装楼层，编号实例坐标配对）"
                                if _ent1_is_dup else
                                "E-DXF-TEXT:总图对照表（图上直写安装楼层，编号唯一映射）")
            else:
                # 2026-09-18（P0）：对照表内该编号有**多个**实例（重号）而本文字实例与任一
                #   实例都配不上坐标 ⇒ 归属无客观判据。此时**不得**退回「几何 x 区间 +
                #   区间法」定归属：硬约束② 明文禁止按标题 x 区间硬切，而且它会把同一个
                #   编号硬拆成另一个「箱」（实测某图因此凭空多出箱、并被 C9 判 pending）。
                #   处置：本实例不产出箱，交给下方「未配对编号实例 / 未归属分纤箱」显式登记。
                if _bdg and len(_bdg) > 1:
                    fx["_drop_reason"] = ("对照表内该编号有 %d 个实例（重号），本文字实例与"
                                          "任一实例坐标均不匹配 —— 归属无客观判据"
                                          % len(_bdg))
                    continue
                fx["安装楼层"] = fl_name
                if fl_name is None:
                    fx["安装楼层口径"] = "未关联到楼层"
                elif dist <= args.y_tol:
                    fx["安装楼层口径"] = "口径A:图上直写"
                else:
                    fx["安装楼层口径"] = "口径B:区间法"
                fx["安装楼层误差"] = round(dist, 2)
                # ---- 结果状态契约（v3.1 L1-C8）产出方落地 ----
                # 两个正交维度，只**登记**已定值、不改变任何归属结果与数值：
                #   origin：口径A（图上直写，dist ≤ 容差）= measured；口径B（区间法算出）= derived；
                #           关联不到楼层 = unresolved。
                #   confirmation：归属须有客观依据才可定案。依据 = ①对照表对该编号有**唯一**映射，
                #           或 ②编号文字落在他所属楼栋的 x 区间内（几何归属本身可用）。
                #           两者皆不成立 ⇒ 归属属「标题 x 区间硬切」（硬约束② 明文禁止）⇒ pending，
                #           由 inspect C9 拦下，不得进入成品。
                if fl_name is None:
                    fx["result_origin"] = "unresolved"
                elif dist <= args.y_tol:
                    fx["result_origin"] = "measured"
                else:
                    fx["result_origin"] = "derived"
                _bm_unique = bool(_bdg and len(_bdg) == 1)
                _br = bldg_ranges.get(bldg)
                _x_in_range = bool(_br and _br[0] <= fx.get("x", 0) <= _br[1])
                fx["result_confirmation"] = ("settled" if (_bm_unique or _x_in_range)
                                             else "pending")
                fx["依据来源"] = (
                    "E-DXF-TEXT:总图对照表（编号唯一映射，归属已定案）" if _bm_unique else
                    ("E-DXF-GEOM:系统图内几何归属（编号文字在本栋 x 区间内）" if _x_in_range else
                     "未对照总图、且编号文字不在本栋 x 区间内 —— 归属待裁决"))
            # --fx-map 回填：只在 parse 侧测不出（null）时补，绝不覆盖已测值
            if FX_MAP and fx.get("安装楼层") is None:
                _cand = FX_MAP.get(str(fx.get("编号", "")).strip())
                if _cand and len(_cand) == 1 and _cand[0].get("安装楼层"):
                    fx["安装楼层"] = _cand[0]["安装楼层"]
                    fx["安装楼层口径"] = "fx-map:总图对照表回填"
                    fx["安装楼层来源"] = "fx-map"
                    fx["result_origin"] = "measured"
                    fx["result_confirmation"] = "settled"
                    fx["依据来源"] = "E-DXF-TEXT:fx-map 总图对照表回填（编号唯一映射）"
                    FXMAP_FILLED.append("%s@%s/%s" % (fx["编号"], bldg, uname))
                elif _cand and len(_cand) > 1:
                    FXMAP_SKIP_DUP.append(str(fx.get("编号")))

        # 重号且未配对的实例：不产出箱（见上方 _drop_reason），此处摘除并留痕。
        _dropped_dup = [f for f in fx_list if f.get("_drop_reason")]
        if _dropped_dup:
            fx_list = [f for f in fx_list if not f.get("_drop_reason")]
            for _f in _dropped_dup:
                FX_DROPPED_DUP.append("%s@(%.1f,%.1f) %s" % (
                    _f.get("编号"), _f.get("x", 0.0), _f.get("y", 0.0), _f["_drop_reason"]))

        # ---------- 分纤箱按编号收敛（2026-09-18 新增） ----------
        # 判据（客观、可复核）：编号是分纤箱的唯一标识 ⇒ 同一编号在本单元的多次文字
        #   出现 = 同一个箱的多次绘制，不是多个箱。实测某图同一箱被计 3 次。
        # 纪律：① 仅当各实例给出**相同**安装楼层时收敛为一条，主记录保留，
        #          其余实例坐标写入「多处出现」证据（证据不丢，可回原坐标追溯）；
        #       ② 各实例安装楼层**不一致** ⇒ 不自行择一：全部信息保留、标 pending、
        #          登记「需人工裁决」（由 inspect C9 拦下，不得进入成品）。
        _grp = {}
        for _fx0 in fx_list:
            _grp.setdefault(str(_fx0.get("编号", "")).strip(), []).append(_fx0)

        def _fx_rank(_f):
            """主记录优先序：已定案 > measured > 误差小。"""
            _err = _f.get("安装楼层误差")
            return (0 if _f.get("result_confirmation") == "settled" else 1,
                    0 if _f.get("result_origin") == "measured" else 1,
                    _err if isinstance(_err, (int, float)) else INF_COORD)

        fx_deduped = []
        for _no0, _g0 in _grp.items():
            if len(_g0) == 1:
                fx_deduped.append(_g0[0])
                continue
            _floors0 = sorted({str(_f.get("安装楼层")) for _f in _g0})
            _best0 = sorted(_g0, key=_fx_rank)[0]
            _best0["多处出现"] = [{"x": round(_f.get("x", 0.0), 2),
                                   "y": round(_f.get("y", 0.0), 2),
                                   "层": _f.get("层"), "安装楼层": _f.get("安装楼层")}
                                  for _f in _g0 if _f is not _best0]
            _best0["多处出现说明"] = (
                "同编号在本单元出现 %d 处；编号唯一标识分纤箱，各处为同一箱的重复绘制，"
                "已按编号收敛为一条（坐标见「多处出现」）" % len(_g0))
            FX_DEDUP.append("%s@%s/%s：%d 处文字 → 1 箱" % (_no0, bldg, uname, len(_g0)))
            if len(_floors0) > 1:
                _best0["result_confirmation"] = "pending"
                _best0["多处出现说明"] += (
                    "；⚠ 各实例安装楼层不一致（%s）—— 未自行择一，须人工裁决"
                    % "/".join(_floors0))
                PENDING_NOTES.append({
                    "对象": "%s/%s 箱 %s" % (bldg, uname, _no0),
                    "事项": "同编号多处出现且安装楼层不一致",
                    "说明": "各实例安装楼层 = %s（各实例坐标见该箱的「多处出现」）"
                            "—— 不得自行择一，须人工裁决" % "/".join(_floors0)})
            fx_deduped.append(_best0)
        fx_list = fx_deduped

        result["楼栋"][bldg]["单元"][uname] = {
            "分纤箱": fx_list,
            "楼层表": floor_table,
            "光缆": list(cable_names.keys()),
        }
        # INSERT 实体归属当前单元（按 x 坐标判断）
        unit_inserts = []
        if insert_items:
            for ins in insert_items:
                if ins.get("楼") != bldg:
                    continue
                # 判断是否属于当前单元（uname 来自 units.items() 循环，必定在 units 中）
                # 与该单元的 fx 文字 x 范围比较
                unit_fx = [t for t in units[uname] if FX_RE and FX_RE.search(t["内容"])]
                if unit_fx:
                    fx_xs = [t["x"] for t in unit_fx]
                    unit_xmin = min(fx_xs) - args.unit_range
                    unit_xmax = max(fx_xs) + args.unit_range
                else:
                    # 无 fx 文字时用单元标注 x
                    unit_anchors = [t["x"] for t in bldg_texts[bldg] if UNIT_RE and UNIT_RE.search(t["内容"])]
                    if unit_anchors:
                        unit_xmin = min(unit_anchors) - args.unit_range
                        unit_xmax = max(unit_anchors) + args.unit_range
                    else:
                        unit_xmin, unit_xmax = NEG_INF_COORD, INF_COORD
                if not (unit_xmin <= ins["x"] <= unit_xmax):
                    continue
                unit_inserts.append(ins)
            if unit_inserts:
                # 按区间法归属楼层
                floor_items = [(fl, fy) for fl, fy in floor_marks.items()]
                if floor_items:
                    for ins in unit_inserts:
                        fl_name, _ = assign_floor_by_interval(ins["y"], floor_items)
                        ins["归属楼层"] = fl_name
                        ins["归属方法"] = "区间法" if fl_name else "区间法:低于最低楼层线"
                result["楼栋"][bldg]["单元"][uname]["INSERT"] = unit_inserts
        if others:
            result["楼栋"][bldg]["单元"][uname]["其它"] = others

# ---------- 未归属分纤箱：禁止静默丢文字（2026-09-18 新增） ----------
# 根因：箱编号文字的归属走「对照表认领 → 各楼栋单元桶」两条路。两条都不成立的文字
#   （对照表无此编号 / 编号重号未择一 / 对照表条目楼栋值为空）会留在原桶；而本类图纸
#   的箱编号恰好落在**所有楼栋标题 x 区间之外**（集中在独立总图/箱表区），于是
#   「留在原桶」＝「哪个桶都不是」＝ **静默消失**。实测某图上确有编号文字、parse 产物
#   里查无此箱（inspect C4 报「parse 漏收录」），下游不跑 inspect 根本察觉不到。
# 处置：**文字不得丢**。未归属的文字实例按编号归集、收入「未归属分纤箱」显式容器，
#   写明未归属原因与对照表候选，供人工一次裁决；同时登记进「需人工裁决」。
#   ⚠ 该容器**不进成品**（地址表只读「楼栋」），故未裁决值不会污染成品 —— 符合
#   「未裁决的值不得进入成品」；本项属「不进成品、可回滚 ⇒ 取安全侧＋标记、不阻塞」。
_un_group = {}
_UNPAIRED = {}   # 编号已归属、但图上仍有未配对的同号文字实例（重复绘制）—— 仅留证
_consumed_ids = {_no0 for (_no0, _x0) in _CONSUMED_FX}
for _t_u in texts:
    if FX_RE is None:
        break
    _m_u = FX_RE.search(_t_u["内容"])
    if not _m_u:
        continue
    _no_u = _m_u.group(0).strip()
    if (_no_u, round(_t_u["x"], 2)) in _CONSUMED_FX:
        continue
    if _no_u in _consumed_ids:
        # 该编号已有归属（其他地方配对成功）—— 本处只是同一编号的又一次绘制，
        #   不新增箱、也不算「未归属」；留证供人工核对是否存在真重号。
        _UNPAIRED.setdefault(_no_u, []).append(
            {"x": round(_t_u["x"], 2), "y": round(_t_u["y"], 2), "层": _t_u.get("层")})
        continue
    _g_u = _un_group.setdefault(_no_u, {"编号": _no_u, "出现位置": [],
                                        "未归属原因": "", "对照表候选": []})
    _g_u["出现位置"].append({"x": round(_t_u["x"], 2), "y": round(_t_u["y"], 2),
                             "层": _t_u.get("层")})
    if not _g_u["未归属原因"]:
        _cand_u = (BDG_MAP.get(_no_u) or []) if BDG_MAP else []
        if not _cand_u:
            _g_u["未归属原因"] = ("对照表无此编号，且其 x 不落在任何楼栋标题区间内"
                                  "（禁止按 x 区间硬切定归属）—— 归属无客观判据")
        elif len(_cand_u) > 1:
            _g_u["未归属原因"] = ("对照表内该编号有 %d 个实例（重号：同一编号标注多个"
                                  "不同箱位）—— 未自行择一，须人工裁决" % len(_cand_u))
        else:
            _g_u["未归属原因"] = ("对照表该条目的「楼栋」字段为空，无法解析到本图楼栋"
                                  "锚点（不猜）—— 归属无客观判据")
        _g_u["对照表候选"] = [{"楼栋": _e.get("楼栋"), "单元": _e.get("单元"),
                               "安装楼层": _e.get("安装楼层"),
                               "口径": _e.get("安装楼层口径"),
                               "箱表描述": _e.get("箱表描述")} for _e in _cand_u][:8]

# ---------- 静默丢数闸门（2026-09-18 新增） ----------
# parse 找不到箱时此前只把 分纤箱=[] 写出去、rc 仍为 0 —— 下游不跑 inspect 不会察觉。
# 总图对照表形态的图纸（箱编号在独立图区）必然触发该情形，故显式告警 + 落状态字段。
_n_fx_total = sum(len(_uv.get("分纤箱") or [])
                  for _bv in result["楼栋"].values()
                  for _uv in (_bv.get("单元") or {}).values())
if _n_fx_total == 0:
    log.warning("!! parse 侧箱数为 0 —— 箱编号可能集中在独立的总图对照表图区"
                "（x 不落在任何楼栋标题区间内）。若图纸申报有总图对照表，"
                "请传 --bldg-map（extract_fx_map.py 产物）按对照表定归属；"
                "否则 inspect 的 C0/C2/C3/C4/C6 会全部 FAIL。")
    result["分纤箱提取状态"] = "0箱｜须核：是否总图对照表形态（需 --bldg-map）"
else:
    result["分纤箱提取状态"] = "%d箱" % _n_fx_total

if _un_group:
    result["未归属分纤箱"] = list(_un_group.values())
    _n_un = len(_un_group)
    result["分纤箱提取状态"] += "｜另有 %d 个编号未归属（图上确有文字、归属无客观判据，" \
                               "不进成品，须人工裁决）" % _n_un
    for _g_u in _un_group.values():
        PENDING_NOTES.append({
            "对象": "未归属箱 %s" % _g_u["编号"],
            "事项": "编号文字存在但归属无法确定",
            "说明": "%s；出现位置 %s" % (
                _g_u["未归属原因"],
                "、".join("(%.1f,%.1f)" % (p["x"], p["y"]) for p in _g_u["出现位置"][:6]))})
    log.warning("!! parse 有 %d 个编号未归属（图上确有编号文字，但归属无客观判据）—— "
                "已收入产物「未归属分纤箱」、不进成品，须人工裁决：%s"
                % (_n_un, "、".join(sorted(_un_group)[:10])))

if FX_DEDUP:
    result["分纤箱收敛"] = {
        "说明": "同一编号在本单元多处文字出现（同一箱的重复绘制）——已按编号收敛为一条，"
                "各实例坐标留在该箱的「多处出现」证据里",
        "收敛条数": len(FX_DEDUP), "收敛清单": FX_DEDUP}
    log.info("分纤箱按编号收敛：%d 条（同编号多实例 → 单箱）" % len(FX_DEDUP))

if _UNPAIRED or FX_DROPPED_DUP:
    result["未配对编号实例"] = {
        "说明": "这些编号已定归属，但图上还有同号的其它文字实例未与本编号的对照表条目配对"
                "（同一编号的再次绘制，或图纸本身的重号）——不新增箱、不影响归属；"
                "留证供人工核对是否存在真重号",
        "条数": sum(len(v) for v in _UNPAIRED.values()) + len(FX_DROPPED_DUP),
        "明细": {k: v for k, v in _UNPAIRED.items()},
        "重号未配对实例": FX_DROPPED_DUP}
    log.info("未配对的同号文字实例：%d 个编号 / %d 处（含重号未配对 %d 处；已留证，不新增箱）"
             % (len(_UNPAIRED), sum(len(v) for v in _UNPAIRED.values()) + len(FX_DROPPED_DUP),
                len(FX_DROPPED_DUP)))

if PENDING_NOTES:
    result["需人工裁决"] = PENDING_NOTES
    log.warning("parse 侧需人工裁决 %d 项（明细见产物「需人工裁决」）" % len(PENDING_NOTES))
if _bdgmap_meta:
    _bdgmap_meta["单元名并存"] = BDGMAP_NAMEMISS
    _bdgmap_meta["重号按坐标配对"] = BDGMAP_DUP_MATCHED
    result["BDGMAP归属"] = _bdgmap_meta
    log.info("--bldg-map 归属结果：跨栋改派 %d；重号按坐标配对 %d；重号未配对 %d；单元名并存 %d"
             % (len(BDGMAP_MOVED), len(BDGMAP_DUP_MATCHED),
                len(set(BDGMAP_SKIP_DUP)), len(BDGMAP_NAMEMISS)))

# ---------- --fx-map 回填汇总（写入产物，供 inspect / 人工追溯） ----------
if _fxmap_meta:
    _fxmap_meta["回填条数"] = len(FXMAP_FILLED)
    _fxmap_meta["回填清单"] = FXMAP_FILLED
    _fxmap_meta["重号未回填"] = sorted(set(FXMAP_SKIP_DUP))
    result["FXMAP回填"] = _fxmap_meta
    log.info("--fx-map 回填安装楼层 %d 条；重号未回填 %d 条（交人工裁决）"
             % (len(FXMAP_FILLED), len(set(FXMAP_SKIP_DUP))))

# ---------- 产物 JSON 标准性闸门（2026-09-18 新增） ----------
# 非有限浮点（inf/nan）的清洗由 ftth_common.sanitize_nonfinite **单一实现**承担，
#   勿在此再写一份 —— 本轮实测解析产物曾把 inf 写成非标准的 `Infinity`，
#   严格解析器会拒绝整份产物。此处只负责把命中项登记进产物，不静默丢弃。
_NONFINITE = []
result = sanitize_nonfinite(result, _hits=_NONFINITE)
if _NONFINITE:
    result["非有限值清洗"] = {
        "说明": "以下字段原为非有限浮点（inf/nan），已写为 null —— 非标准 JSON 值会"
                "导致严格解析器拒绝整份产物；null 表示「本图未测得该量」，不得读作 0",
        "条数": len(_NONFINITE), "字段路径": _NONFINITE[:50]}
    log.warning("产物含非有限浮点 %d 处，已清洗为 null（详见产物「非有限值清洗」）"
                % len(_NONFINITE))

try:
    write_json(OUT, result, indent=2, log=log)
except IOError as e:
    log.error(f"无法写入输出文件: {OUT}\n{e}")
    sys.exit(1)

log.info(f"\n解析完成 → {OUT}")