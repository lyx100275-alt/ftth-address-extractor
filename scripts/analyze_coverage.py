#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTTH 分纤箱覆盖范围分析脚本（通用版 v2，依据 coverage_rules.md 方法一"连线直读"）
通过追踪 DXF 中分纤箱位置的竖主干 + 皮线连接关系，输出"覆盖范围线索"供用户确认（非结论）。

用法：
    python analyze_coverage.py <输入DXF> [输出JSON] [选项]

选项（检测类参数必须由探查提供，脚本不设项目默认值）：
    --text-layer <探查图层>        文字图层（逗号分隔）
    --text-type MTEXT,TEXT       文字实体类型（逗号分隔，默认两者都取）
    --title-pattern "<探查标题正则>"  楼栋标题正则（含捕获组数字）
    --floor-pattern                 楼层标注正则（留空＝内置统一解析，支持 3F/17F/-1F/B1/B2/WF）
    --fx-pattern "<探查编号正则>"    分纤箱编号正则
    --unit-cluster 0             同一单元分纤箱x聚类阈值（0＝按 1 倍层高自适应）
    --vert-dx 0                  垂直线段判定：x跨度阈值（0＝按 1/10 倍层高自适应）
    --vert-dy 0                  垂直线段判定：y跨度阈值（0＝按 1/10 倍层高自适应）
    --fx-window 0                分纤箱x附近竖干搜索半宽（0＝按 1/2 倍层高自适应）
    --merge-tol 0                竖干拼接：端点相接容差（0＝按 1/15 倍层高自适应）
    --conn-tol 0                 皮线连接关系判定容差：端点距竖干/设备x距离（0＝按 1/10 倍层高自适应）

说明：
- 竖干 = 多条 LINE/LWPOLYLINE 首尾相接拼成的竖直线段（覆盖楼层判定依据）。
- 皮线判定按"连接关系"（一端在竖干x±容差、另一端在住户设备INSERT x±容差），不用dy阈值。
- 单元归属：提供 --bldg-map（分纤箱总图对照表）时按 FX 编号查表；未提供时回退"标题x中分"，
  该法在两行交错布局图纸上会串行，输出中标注为"不可靠"。（故本脚本无 --unit-pattern 参数）
- 输出"已分类皮线"与"未分类线段"两组清单。
- 有住户设备但无皮线连接 → 标记"异常"（非"0户"）。
- 所有覆盖范围结果均标注为"线索"，由用户裁决，绝不作为结论。
"""
import argparse
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

from ftth_common import (
    DEFAULT_UNIT_CLUSTER, DEFAULT_VERT_DX, DEFAULT_VERT_DY, DEFAULT_FX_WINDOW,
    DEFAULT_MERGE_TOL, DEFAULT_CONN_TOL,
    INF_COORD, NEG_INF_COORD,
    setup_logger, extract_bldg_name, bldg_num, floor_num_or_zero,
    parse_bldg_nums, parse_bldg_nums_ex, first_group,
    load_dxf, collect_texts, cluster_by_x, match_y_to_floor, assign_floor_by_interval,
    parse_floor_label, clean_text, is_floor_text, attrib_hit, require_params,
    cluster_values_by_gap, measure_column_step,
    RE_DRAWING_WORD,
)

log = setup_logger("analyze_coverage")


def judge_object_name(bldg, unit, box_id=None):
    r"""待确认清单里「对象」的统一命名口径（2026-09-18 立）。

    格式：`楼栋+单元`，再按需追加 `/<箱编号>`；**单元名自带同一楼号时不再重复加楼栋前缀**。
    为什么必须统一：实测某图同一对象在清单里出现两种写法（`4#楼4#配套楼/FX22#` 与
    `4#配套楼/FX22#`），人无法把它们对照到同一行 —— 清单的可读性直接归零。
    旧实现有两种成因：① 一处用 `unit.startswith(bldg)` 判断，遇到 `4#配套楼` 这类
    「含楼号但不以楼栋全名开头」的单元名判断失效、拼成双前缀；② 另一处无条件 `f"{b}{u}"`，
    遇到 `7#楼1单元` 直接拼成 `7#楼7#楼1单元`。
    判据用「同一楼号」而非「字符串前缀」：楼栋取 ``(数字+)#``（见下方正则），
    单元名同号即视为自带前缀。

    注：本 docstring 用 raw 字符串 —— 里面写了正则转义，非 raw 会触发 SyntaxWarning
    （Python 3.12+ 起非法转义告警、将来是错误）。
    """
    b = str(bldg or "").strip()
    u = str(unit or "").strip()
    m = re.match(r"(\d+)#", b)
    self_prefixed = bool(u) and (
        (bool(b) and u.startswith(b)) or
        (bool(m) and bool(re.match(r"^\s*%s#" % re.escape(m.group(1)), u)))
    )
    if self_prefixed:
        base = u
    elif b and u:
        base = b + u
    else:
        base = b or u
    return ("%s/%s" % (base, box_id)) if box_id else base

# ---------------------------------------------------------------- 尺度自适应默认值
# 通用化判据（见 SKILL.md）：**凡是随图纸坐标尺度变化的几何阈值，必须是无量纲比值
# × 图纸自身层高**；写成绝对数值（200 / 60 / 30）就只对标定它的那一张图成立。
AUTO_RATIOS = {
    # 名称                   比值     语义
    "bldg_pad":          20 / 3,     # 楼栋楼层线搜索范围 ≈ 6.67 层高
    "title_band_tol":    2.0,        # 标题分带容差 ≈ 2 层高
    "fx_symbol_cluster": 2 / 3,      # 箱内图元聚组半径 ≈ 2/3 层高
    "fx_symbol_max_size": 2.0,       # 箱体最大边长 ≈ 2 层高（滤掉大轮廓/机架）
    "total_pad":         5.0,        # 总图区排除半径 ≈ 5 层高
    "unit_cluster":      1.0,        # 同单元分纤箱 x 聚类 ≈ 1 层高
    "vert_dx":           0.1,        # 垂直线段 x 跨度阈值 ≈ 层高/10
    "vert_dy":           0.1,        # 垂直线段 y 跨度阈值 ≈ 层高/10
    "fx_window":         0.5,        # 竖干搜索半宽 ≈ 层高/2
    "merge_tol":         1 / 15,     # 竖干拼接端点相接容差 ≈ 层高/15
    "conn_tol":          0.1,        # 皮箱连接 x 容差 ≈ 层高/10
}
# 图纸量不出层高时的兜底（无楼层刻度列 / 极简图）。日志会显式标注"未定标"，
# 避免被误当成"已按本图刻度校准"。
AUTO_FALLBACK = {"bldg_pad": 200.0, "title_band_tol": 60.0, "fx_symbol_cluster": 20.0,
                 "fx_symbol_max_size": 60.0, "total_pad": 150.0, "unit_cluster": 30.0,
                 "vert_dx": 3.0, "vert_dy": 3.0, "fx_window": 15.0,
                 "merge_tol": 2.0, "conn_tol": 3.0}
AUTO_KEYS = tuple(AUTO_RATIOS)


def auto_scaled(step, name):
    """按图纸自身层高还原某个几何阈值的图纸单位值。"""
    v = AUTO_RATIOS[name] * step if step else AUTO_FALLBACK[name]
    return round(v, 6)


ap = argparse.ArgumentParser(description="FTTH 覆盖范围分析（输出线索，竖线法）")
ap.add_argument("dxf", help="输入DXF文件路径")
ap.add_argument("out", nargs="?", default=None, help="输出JSON路径（默认 _覆盖范围.json）")
ap.add_argument("--text-layer", default=None, help="文字图层，逗号分隔（必填，由探查提供）")
ap.add_argument("--text-type", default="MTEXT,TEXT", help="文字实体类型，逗号分隔（默认两者都取）")
ap.add_argument("--title-pattern", default=None, help="楼栋标题正则（含捕获组数字；必填，由探查枚举标题写法后提供）")
ap.add_argument("--floor-pattern", default=None, help="楼层标注正则（默认 None＝内置统一解析，支持 3F/17F/-1F/B1/B2/WF；仅当图纸用非标楼层写法时才显式指定）")
ap.add_argument("--fx-pattern", default=None, help="分纤箱编号正则（必填，由探查采样后提供）")
ap.add_argument("--unit-cluster", type=float, default=0.0, help="同一单元分纤箱x聚类阈值（0=按 %g 倍层高自适应）" % AUTO_RATIOS["unit_cluster"])
ap.add_argument("--vert-dx", type=float, default=0.0, help="垂直线段判定：x跨度阈值（0=按 %g 倍层高自适应）" % AUTO_RATIOS["vert_dx"])
ap.add_argument("--vert-dy", type=float, default=0.0, help="垂直线段判定：y跨度阈值（0=按 %g 倍层高自适应）" % AUTO_RATIOS["vert_dy"])
ap.add_argument("--fx-window", type=float, default=0.0, help="分纤箱x附近竖干搜索半宽（0=按 %g 倍层高自适应）" % AUTO_RATIOS["fx_window"])
ap.add_argument("--merge-tol", type=float, default=0.0, help="竖干拼接：端点相接容差（0=按 %g 倍层高自适应）" % AUTO_RATIOS["merge_tol"])
ap.add_argument("--conn-tol", type=float, default=0.0, help="皮箱连接判定：端点距竖干/设备x容差（0=按 %g 倍层高自适应）" % AUTO_RATIOS["conn_tol"])

# ---------- 数据来源过滤（2026-09-11 新增，对应 P0-3） ----------
ap.add_argument("--wire-layer", default=None,
                help="连线(LINE/LWPOLYLINE)所在图层名，逗号分隔（如 'RX-wire.通讯,WIRE-通讯'）。"
                     "强烈建议显式指定：不指定则扫描全图所有图层的线段，极易把建筑线/图框/家具图层的线段"
                     "当成电信主干（实测教训：绝大多数『竖干』其实来自建筑/图框等无关图层，真正的通信图层命中可能为 0 条）")
ap.add_argument("--insert-attrib-tag", default=None,
                help="设备块(INSERT)属性 tag，如 A / $TEXT$ / 名称")
ap.add_argument("--insert-attrib-val", default=None,
                help="设备块属性值关键词，逗号分隔，任一命中即算（如 'HDD,家居配线箱'）。"
                     "按属性值识别设备、不按块名——同一种设备在不同区域可能用完全不同的块名")
ap.add_argument("--bldg-map", default=None,
                help="分纤箱总图对照表 JSON（extract_fx_map.py 的输出）。"
                     "提供后，楼栋/单元归属改为按【FX编号】直接查表，不再用标题 x 中分硬切。"
                     "强烈建议提供：系统图区常为两行交错排布，x 中分必然串行")
ap.add_argument("--bldg-pad", type=float, default=0.0,
                help="用对照表归属时，楼栋楼层线搜索范围 = 该楼栋FX的x范围 ± 本值"
                     "（0=按 %g 倍层高自适应）" % AUTO_RATIOS["bldg_pad"])
ap.add_argument("--title-band-tol", type=float, default=0.0,
                help="系统图标题按 y 分带的容差：y 相差不超过本值的标题视为同一带"
                     "（0=按 %g 倍层高自适应）。"
                     "配套楼系统图常与住宅楼系统图上下分带，带内才做 x 中分，跨带不可混算"
                     % AUTO_RATIOS["title_band_tol"])
ap.add_argument("--fx-symbol-layer", default=None,
                help="分纤箱【图形符号】所在图层（如 'R-设备.通讯'）。"
                     "实测教训：系统图里分纤箱可能只有图形符号、没有编号文字（编号文字全部只在总图区对照表），"
                     "不提供本参数时脚本会把总图区的编号文字当成箱位置，导致每个箱都'附近找不到竖干'")
ap.add_argument("--fx-symbol-cluster", type=float, default=0.0,
                help="分纤箱符号内图元聚成一组的阈值（0=按 %g 倍层高自适应）"
                     % AUTO_RATIOS["fx_symbol_cluster"])
ap.add_argument("--fx-symbol-max-size", type=float, default=0.0,
                help="分纤箱符号（闭合多段线）最大边长，用于把箱体与同图层的大轮廓/机架"
                     "区分开（0=按 %g 倍层高自适应）" % AUTO_RATIOS["fx_symbol_max_size"])
ap.add_argument("--symbol-pair-tol", type=float, default=0.0,
                help="箱符号 ↔ 安装楼层线 的残差阈值（图纸单位）；0=自动取 0.6×楼层间距。"
                     "残差≤阈值判为可信，>3×阈值则该箱退回编号文字并标『需人工复核』")
ap.add_argument("--allow-low-pairing", action="store_true",
                help="逃生开关：箱符号配对率<30%%或图上全无符号时仍强行继续（2026-09-15 坑3："
                     "缺符号时箱位回退编号文字坐标，覆盖计算必然失真，默认按失败退出码3）")
ap.add_argument("--total-pad", type=float, default=0.0,
                help="总图区判据：与任一 FX 编号文字的 x 距离 ≤ 本值的文字视为『总图/拓扑区文字』，"
                     "不参与楼层刻度（总图里每个箱旁都写着一个安装楼层，混进刻度池会污染覆盖楼层）"
                     "（0=按 %g 倍层高自适应）" % AUTO_RATIOS["total_pad"])
ap.add_argument("--break-floor-tol", type=float, default=0.0,
                help="断口处楼层归属容差（图纸单位）；0=自动取 0.6×楼层间距。"
                     "楼层线落在断口内时，只要它距断口上方那段的下端不超过本值，就判归上方那段")
ap.add_argument("--max-break-span", type=float, default=0.0,
                help="断口跨度上限（图纸单位）；0=自动取 2×楼层间距。只有间距 ≤ 本值的两个相邻连续体"
                     "才算『同一根竖干被断开的上下段』；超过则视为跨图带/跨单元误并入，不进断口判定"
                     "（实测：真断口约 1.1 倍层高，跨图带伪断口约 3.6 倍层高）")

args = ap.parse_args()

DXF_PATH = args.dxf
OUT = args.out or (os.path.splitext(DXF_PATH)[0] + "_覆盖范围.json")

require_params([
    ("--text-layer", args.text_layer, "含FTTH标注的文字图层（探查图层清单+采样后确定）"),
    ("--fx-pattern", args.fx_pattern, "分纤箱编号正则"),
    ("--title-pattern 或 --bldg-map", args.title_pattern or args.bldg_map,
     "楼栋标题正则 / 分纤箱总图对照表（至少其一：前者用于定楼栋x范围，后者用于按编号归属）"),
], "analyze_coverage")

TEXT_LAYERS = [x.strip() for x in args.text_layer.split(",") if x.strip()]
TYPES = [x.strip().upper() for x in args.text_type.split(",") if x.strip()]
WIRE_LAYERS = [x.strip() for x in args.wire_layer.split(",") if x.strip()] if args.wire_layer else None
SYM_LAYERS = [x.strip() for x in args.fx_symbol_layer.split(",") if x.strip()] if args.fx_symbol_layer else []
FX_SYM_MAX = args.fx_symbol_max_size
INSERT_VAL_KEYS = [x.strip() for x in args.insert_attrib_val.split(",") if x.strip()] if args.insert_attrib_val else None
TITLE_RE = re.compile(args.title_pattern) if args.title_pattern else None
FLOOR_RE = re.compile(args.floor_pattern) if args.floor_pattern else None
FX_RE = re.compile(args.fx_pattern)

if WIRE_LAYERS is None:
    log.warning("未指定 --wire-layer：将扫描全图所有图层的 LINE/LWPOLYLINE。"
                "请核对输出 JSON 的『线段图层来源统计』，确认主干来自电信图层而非建筑/图框图层。")

doc, msp = load_dxf(DXF_PATH, log)

# ---------- 1. 提取文字 ----------
all_texts = collect_texts(msp, TEXT_LAYERS, TYPES)

# ---------- 2. 楼栋标题 → 楼栋 x 范围（中分） ----------
titles = [(t["x"], t["y"], t["内容"]) for t in all_texts if TITLE_RE and TITLE_RE.search(t["内容"])]
titles.sort(key=lambda t: t[0])
bldg_ranges = []
_amb_titles = []
for i, (x, y, text) in enumerate(titles):
    # 2026-09-13（P0-1）：楼号一律走 parse_bldg_nums，覆盖
    #   `N号楼` / `N#楼` / `N#、N#` / `N/M号楼`；禁止再内联楼号正则。
    _nums, _amb = parse_bldg_nums_ex(text)
    if _amb:
        _amb_titles.append(text)
    if not _nums:
        # 标题正则命中但统一解析器认不出（自定义写法）：回退 title_re 捕获组 1。
        # first_group 保证正则写成 `\d+号楼`（无捕获组）时也不崩。
        _g = first_group(TITLE_RE.search(text))
        if _g is not None and str(_g).strip().isdigit():
            _nums = [int(str(_g).strip())]
    if not _nums:
        continue
    bm_name = extract_bldg_name(text)
    xmin = NEG_INF_COORD if i == 0 else (titles[i - 1][0] + x) / 2
    xmax = INF_COORD if i == len(titles) - 1 else (x + titles[i + 1][0]) / 2
    for bnum in _nums:
        # 单楼号标题保留修饰词楼名；共享标题多楼号时修饰词归首号，其余用「N#楼」
        if bm_name and len(_nums) == 1:
            bldg_name = bm_name
        elif (bm_name and len(_nums) > 1 and bnum == _nums[0]
              and re.search(re.escape(str(bnum)) + r"[#号]", bm_name)):
            bldg_name = bm_name
        else:
            bldg_name = f"{bnum}#楼"
        bldg_ranges.append((bnum, xmin, xmax, bldg_name))
if _amb_titles:
    log.warning("以下标题含 `N-M号楼` 连字符写法，已按『N 号与 M 号』并列展开；"
                "若图纸实为区间（N 至 M 号），请人工更正后重跑：%s", "；".join(_amb_titles))
if not bldg_ranges and not args.bldg_map:
    log.error("未匹配到楼栋标题，请检查 --title-pattern / --text-layer（或改用 --bldg-map）")
    sys.exit(2)

# ---------- 2b. 分纤箱对照表 → 楼栋/单元归属（2026-09-11 新增，P0-6） ----------
# 为什么必须优先用对照表：
#   系统图区常为"两行交错排布"（上行配套楼、下行住宅楼），高层住宅图很高，
#   两行纵向重叠、横向错开 → 按标题 x 中分必然串行。
#   实测教训：中分法会把分属不同楼栋/单元的多个箱归成同一组，归属完全错。
#   FX 编号本身就是权威归属键，查表即可，无需任何几何推断。
FX_MAP = {}
if args.bldg_map:
    try:
        with open(args.bldg_map, "r", encoding="utf-8") as f:
            _bm = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        log.error(f"无法读取分纤箱对照表: {args.bldg_map}\n{e}")
        sys.exit(1)
    # 2026-09-15（P0-10 配套）：对照表的**重号**必须可见。
    #   本步按【编号】建键，同编号多实例会在此合并（后写覆盖前写）——旧实现无任何提示，
    #   箱位凭空消失。实测某图对照表 72 条、唯一编号 64（8 个编号各 2 次、指向不同楼栋），
    #   载入后只剩 64 条。故：表内条数 > 载入条数时**显式告警**并点名重号编号，
    #   交人工裁决（遵循原则二：不自行择一）。
    _n_tab = 0
    for _e in _bm.get("FX映射表", []):
        if _e.get("编号"):
            FX_MAP[_e["编号"]] = _e
            _n_tab += 1
    log.info(f"已载入分纤箱对照表：{len(FX_MAP)} 条")
    if _n_tab > len(FX_MAP):
        _dups = _bm.get("重号编号") or {}
        log.warning(
            "分纤箱对照表存在重号编号：表内 %d 条 → 按编号去重后 %d 条（%d 条被合并）。"
            "重号编号：%s。这些编号在图上指向多处，归属需人工裁决；"
            "本步结果对重号箱**不可用**，不得直接作为结论。"
            % (_n_tab, len(FX_MAP), _n_tab - len(FX_MAP),
               "、".join(sorted(_dups)) if _dups else "（对照表未提供『重号编号』字段）"))

fx_texts = [t for t in all_texts if FX_RE.search(t["内容"])]

# 编号文字坐标（箱定位的回退来源）
_text_pos = {}
FX_TEXT_XS = []
for _t in fx_texts:
    _m = FX_RE.search(_t["内容"])
    if _m:
        _text_pos.setdefault(_m.group(0), (_t["x"], _t["y"]))
        FX_TEXT_XS.append(_t["x"])

# ---- 图纸尺度锚：层高（此后所有几何阈值的单位） ----
# 注意：必须用**未经 total-pad 过滤**的原始楼层文字来量层高，否则就成了
# 「用 total_pad 算 step、又用 step 算 total_pad」的循环依赖。
_fl_rows = [(t["x"], t["y"]) for t in all_texts if is_floor_text(t["内容"], FLOOR_RE)]
_cols = []
for _grp in cluster_values_by_gap(sorted(x for x, _y in _fl_rows)):
    _sel = {round(v, 6) for v in _grp}
    _cols.append(sorted(y for x, y in _fl_rows if round(x, 6) in _sel))
DRAW_STEP, DRAW_STEP_WHY = measure_column_step(_cols)
if DRAW_STEP:
    for _k in AUTO_KEYS:
        if not getattr(args, _k, None) or getattr(args, _k) <= 0:
            setattr(args, _k, auto_scaled(DRAW_STEP, _k))
    log.info("图纸尺度锚：层高 = %.6g（%s）→ 阈值按层高倍数还原：%s",
             DRAW_STEP, DRAW_STEP_WHY,
             "、".join("%s=%.6g" % (k, getattr(args, k)) for k in AUTO_KEYS))
else:
    for _k in AUTO_KEYS:
        if not getattr(args, _k, None) or getattr(args, _k) <= 0:
            setattr(args, _k, AUTO_FALLBACK[_k])
    log.warning("图纸尺度锚：**未定标**（%s）→ 阈值取兜底值（%s），结果须人工复核",
                DRAW_STEP_WHY,
                "、".join("%s=%.6g" % (k, AUTO_FALLBACK[k]) for k in AUTO_KEYS))

# 归属作业表：[{楼栋, x_lo, x_hi, 单元:[{单元名, 箱:[{编号, 对照表安装楼层}]}]}]
bldg_jobs = []
if FX_MAP:
    belong_mode = "对照表按编号归属 + 系统图标题定x范围 + 图形符号定箱位"

    # ① 单元 → 箱清单（来自对照表；单元的权威来源是编号本身，不是几何）
    _units = {}
    _bad_unit = []
    for _fxid, _e in FX_MAP.items():
        _bl = (_e.get("楼栋") or "").strip()
        _u = (_e.get("单元") or "").strip() or _bl
        # 防御：单元号必须与楼栋号一致，否则以楼栋为准
        # （旧版对照表可能把配套楼的箱挂到邻近住宅楼的单元上）
        if _bl and _u and bldg_num(_u) != bldg_num(_bl):
            _bad_unit.append(f"{_fxid}: 单元「{_u}」≠ 楼栋「{_bl}」")
            _u = _bl
        if _u:
            _units.setdefault(_u, []).append(_fxid)
    if _bad_unit:
        log.warning("对照表『单元』与『楼栋』不同号，已按楼栋纠正：%s", "；".join(_bad_unit))

    def _unit_ord(name):
        m = re.findall(r"(\d+)", name)
        return (int(m[0]) if m else 0, int(m[1]) if len(m) > 1 else 0)

    # ② 系统图标题锚点：先按 y 分带（配套图与住宅图常上下两带），带内再按 x 中分
    #    —— 用系统图自己的标题定 x，而不是用总图区 FX 文字的 x（后者是拓扑图/表格位置，与主干无关）
    _bands = []
    _title_hits = []
    for _t in sorted(all_texts, key=lambda t: t["y"]):
        if not TITLE_RE or not TITLE_RE.search(_t["内容"]):
            continue
        _title_hits.append(_t["内容"])
        # 2026-09-13（P0-1）：原为硬编码 `re.findall(r"(\d+)#", ...)`，
        #   对图上 `N号楼`（如「1号楼综合布线系统图」「3/6号楼…」）一律返回空
        #   → 所有楼栋被静默跳过，脚本仍以 0 退出。
        _nums, _amb = parse_bldg_nums_ex(_t["内容"])
        if _amb:
            log.warning("  [注意] 标题 %r 含 `N-M号楼` 连字符写法，已按并列展开；"
                        "若实为区间请人工更正", _t["内容"])
        if not _nums:
            continue
        if _bands and abs(_t["y"] - _bands[-1]["y0"]) <= args.title_band_tol:
            _bands[-1]["items"].append((_t["x"], _nums))
        else:
            _bands.append({"y0": _t["y"], "items": [(_t["x"], _nums)]})

    # 标题池形态护栏（2026-09-16 新增，P1-2）：
    #   `--title-pattern` 的**匹配对象必须是图纸标题**（本技能普遍约定：含
    #   『系统图/布线图/示意图』）。实测踩坑：把「总图对照表里的楼栋行」正则误当标题
    #   正则传入时，匹配到的是一批对照表行文字，锚点 x 落对照表区，楼栋 x 带随之
    #   **整体平移**——各带宽度正常、并集甚至仍覆盖符号带，因此「并集是否重叠」这类
    #   判据抓不住它（该判据仍在下方保留，用于捕获另一类「标题在远端图区」的情形），
    #   要一路走到逐栋「本楼栋 x 范围内找不到任何箱图形符号」才失败，而那句错误信息
    #   把排错方向误导向「图层名不对」。此处按**匹配文字的形态**直接判定并点名真因。
    if TITLE_RE and _title_hits:
        if not any(RE_DRAWING_WORD.search(_c) for _c in _title_hits):
            _msg = ("--title-pattern 匹配到 %d 条文字，但没有一条含『系统图/布线图/示意图』"
                    "→ 该正则匹配的不是**光纤入户系统图标题**。实测两类常见误匹配："
                    "① 总图对照表里的楼栋行（如 `1#楼，2#楼`）；② 楼层平面图标题"
                    "（如 `1#楼楼层平面图`）——它们都会把楼栋 x 范围整体平移，箱符号必然对不上。"
                    "请让 --title-pattern 匹配系统图标题（形如 `(\\d+)#.*?(?:系统图|示意图)`），"
                    "**不要用 --bldg-pattern 的值顶替**。命中样例：%s"
                    % (len(_title_hits), "｜".join(_title_hits[:3])))
            if args.allow_low_pairing:
                log.warning("  [警告] 标题池形态存疑：" + _msg
                            + "（已加 --allow-low-pairing，继续执行，结果须人工复核）")
            else:
                log.error("  [失败] 标题池形态存疑：" + _msg
                          + " **本次未产出覆盖结果，已按失败退出（码 3）**")
                sys.exit(3)

    ranges = {}
    for _b in _bands:
        _items = sorted(_b["items"], key=lambda it: it[0])
        _xs = [it[0] for it in _items]
        for _i, (_x, _nums) in enumerate(_items):
            _lo = (_xs[_i - 1] + _x) / 2 if _i > 0 else _x - args.bldg_pad * 1.5
            _hi = (_x + _xs[_i + 1]) / 2 if _i + 1 < len(_xs) else _x + args.bldg_pad * 1.5
            for _n in _nums:
                if _n in ranges:
                    log.warning(f"  [注意] {_n}# 出现多个系统图标题锚点，取先出现的")
                    continue
                ranges[_n] = (_lo, _hi)
    if not ranges:
        # 2026-09-13（P0-3）：原为 log.warning 后继续执行 → 作业表为空仍返回退出码 0，
        #   调用方会把"整轮作废"当成"跑成功了"。现改为硬失败。
        log.error("对照表已载入，但按 --title-pattern 找不到任何系统图标题锚点，"
                  "无法确定楼栋 x 范围 —— **本次未产出任何楼栋，已按失败退出（码 2）**。"
                  "请依次核对：① --text-layer 是否覆盖标题所在图层；"
                  "② --title-pattern 是否与图上**图纸标题**写法一致（`N#楼`/`N号楼`/"
                  "`N#住宅`/`N#配套`/`N/M号楼` 等，且不得用 bldg_pattern 顶替）；"
                  "③ 标题是否在图框层而非标注层。")
        sys.exit(2)

    # ③ 楼栋号 → 单元清单
    _by_num = {}
    for _u, _ids in _units.items():
        for _bn in {bldg_num(FX_MAP[i].get("楼栋") or "") for i in _ids}:
            if _bn:
                _by_num.setdefault(_bn, {})[_u] = sorted(_ids)

    for _bn in sorted(_by_num):
        if _bn not in ranges:
            log.warning(f"  [注意] {_bn}# 在对照表里有箱，但找不到对应的系统图标题，跳过")
            continue
        _lo, _hi = ranges[_bn]
        _ul = _by_num[_bn]
        _unames = sorted(_ul, key=_unit_ord)
        _bname = f"{_bn}#楼"
        _job = {"楼栋": _bname, "x_lo": _lo, "x_hi": _hi, "单元": []}
        for _u in _unames:
            _job["单元"].append({
                "单元名": _u,
                "箱": [{"编号": _i, "对照表安装楼层": FX_MAP[_i].get("安装楼层")} for _i in _ul[_u]],
            })
        bldg_jobs.append(_job)
        log.info("  %s: %d 个单元 %s, x∈[%.0f,%.0f]", _bname, len(_unames),
                 [(u["单元名"], [b["编号"] for b in u["箱"]]) for u in _job["单元"]], _lo, _hi)
else:
    belong_mode = "标题x中分（不可靠，需人工复核）"
    log.warning("未提供 --bldg-map：楼栋归属回退为『标题 x 中分』。"
                "该法在两行交错布局的图纸上会串行，结果仅供线索。")
    _by_num = {}
    for bnum, xmin, xmax, bldg_name in bldg_ranges:
        _ids = [t["内容"] for t in fx_texts if xmin <= t["x"] <= xmax]
        _by_num.setdefault(bnum, []).append((bldg_name, xmin, xmax, _ids))
    for bnum in sorted(_by_num):
        for bldg_name, xmin, xmax, _ids in _by_num[bnum]:
            bldg_jobs.append({"楼栋": bldg_name, "x_lo": xmin, "x_hi": xmax,
                              "单元": [{"单元名": f"{bldg_name}单元1",
                                        "箱": [{"编号": i, "对照表安装楼层": None} for i in _ids]}]})

# ---------- 3. 楼栋内楼层文字 ----------
def _is_floor_text(s):
    """判断一段文字是否为楼层标注（统一走 ftth_common.is_floor_text）。

    支持 3F/17F/-1F/B1/B2/WF；显式传了 --floor-pattern 时额外兼容该正则。
    """
    return is_floor_text(s, FLOOR_RE)


def floors_in_range(xmin, xmax):
    """楼栋 x 范围内的楼层标注。

    2026-09-11 修正（P0-14）：排除「总图/拓扑图区」的楼层文字。
    总图区每个分纤箱都会挨着一个「安装楼层」文字（如 5F/13F/-1F），它们与系统图的
    楼层刻度完全无关；但楼栋 x 范围（由标题中点切分）常常会覆盖到总图区，
    于是这些拓扑标注就混进刻度池，导致覆盖楼层出现重复/张冠李戴的项。
    判据：某文字与任一 FX 编号文字的 x 距离 ≤ --total-pad，即视为总图区文字。
    """
    out = []
    for t in all_texts:
        if not (xmin <= t["x"] <= xmax) or not _is_floor_text(t["内容"]):
            continue
        if FX_TEXT_XS and min(abs(t["x"] - _fx) for _fx in FX_TEXT_XS) <= args.total_pad:
            continue
        out.append(t)
    return out


def y_to_floor_name(y, floors):
    """公共函数包装：楼层标注中找最近的 y 坐标。"""
    floor_items = [(f["内容"], f["y"]) for f in floors]
    return match_y_to_floor(y, floor_items)



# ---------- 4. 提取线段（LINE + LWPOLYLINE，按 --wire-layer 过滤） ----------
# 2026-09-11 修正（P0-3）：新增图层过滤与图层来源统计。
# 旧实现不过滤图层，会把建筑线/图框/家具/热水器等图层的线段一并当作"电信主干"参与覆盖计算。
ALL_LAYERS_STAT = {}     # 全图线段图层分布（不受过滤影响，用于诊断"主干取自哪个图层"）
seg_layer_stat = {}      # 实际参与分析的线段图层分布
segments = []
_skipped_symbols = 0     # 被识别为"箱图形符号"而排除的多段线数


def _wire_ok(layer):
    return (WIRE_LAYERS is None) or (layer in WIRE_LAYERS)


def _is_box_symbol_entity(e):
    """闭合小多段线 = 分纤箱图形符号，不是线缆，绝不能当主干线段参与覆盖计算。

    2026-09-11 新增（P0-13）：实测——箱符号是"宽而矮"的闭合矩形，其左右两条竖边
    恰好落在箱体 x 上，若把符号层放进 --wire-layer，这两条很矮的"竖干"会把箱的 y 直接
    包住，脚本就会认领这两条假主干，得出 y 区间只剩箱高、覆盖楼层全空的错误结论。
    """
    if not SYM_LAYERS or e.dxf.layer not in SYM_LAYERS:
        return False
    if e.dxftype() != "LWPOLYLINE" or not e.closed:
        return False
    try:
        pts = e.get_points()
        if not pts:
            return False
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (max(xs) - min(xs)) <= FX_SYM_MAX and (max(ys) - min(ys)) <= FX_SYM_MAX
    except Exception:
        return False


def _count(stat, key, n=1):
    stat[key] = stat.get(key, 0) + n


for e in msp:
    if _is_box_symbol_entity(e):
        _skipped_symbols += 1
        continue
    if e.dxftype() == "LINE":
        lay = e.dxf.layer
        _count(ALL_LAYERS_STAT, lay)
        if not _wire_ok(lay):
            continue
        _count(seg_layer_stat, lay)
        segments.append({
            "start": (e.dxf.start.x, e.dxf.start.y),
            "end": (e.dxf.end.x, e.dxf.end.y),
            "层": lay, "类型": "LINE",
        })
    elif e.dxftype() == "LWPOLYLINE":
        lay = e.dxf.layer
        # get_points() 默认返回 (x,y) 或更多元素；统一取前两个作为坐标
        pts = e.get_points()
        _count(ALL_LAYERS_STAT, lay, max(1, len(pts) - 1))
        if not _wire_ok(lay):
            continue
        _count(seg_layer_stat, lay, max(1, len(pts) - 1))
        for i in range(len(pts) - 1):
            p1, p2 = pts[i], pts[i + 1]
            segments.append({
                "start": (float(p1[0]), float(p1[1])),
                "end": (float(p2[0]), float(p2[1])),
                "层": lay, "类型": "LWPOLYLINE",
            })
        # 闭合多段线：追加闭合段（最后一点→第一点）
        if e.closed and len(pts) >= 2:
            p1, p2 = pts[-1], pts[0]
            segments.append({
                "start": (float(p1[0]), float(p1[1])),
                "end": (float(p2[0]), float(p2[1])),
                "层": lay, "类型": "LWPOLYLINE",
            })

if segments:
    top = sorted(seg_layer_stat.items(), key=lambda kv: -kv[1])[:8]
    log.info("线段图层来源（参与分析）: " + ", ".join(f"{k}={v}" for k, v in top))
    if _skipped_symbols:
        log.info("已排除分纤箱图形符号 %d 个（闭合小多段线，非线缆）", _skipped_symbols)
else:
    log.error("过滤后没有任何线段参与分析，请检查 --wire-layer 是否写错（见 JSON 的『线段图层来源统计』）")

# ---------- 5. 提取 INSERT（住户设备块，按属性值过滤） ----------
# 2026-09-11 修正（P0-3 / P0-9）：
#  · 新增 --insert-attrib-tag / --insert-attrib-val，按【属性值】识别设备、不按块名。
#    同一设备在不同图区可能用完全不同的块名（实测：不同图区各用一套 $equip$ 块名），
#    因此硬编码块名必然漏。
#  · 旧实现不筛选，把全部 INSERT 都当"住户设备"，设备数虚高、皮线匹配随之失真。
inserts = []
block_stat = {}


def _attrib_ok(e):
    """返回 (是否命中, 属性字典)

    按【属性值】识别设备（统一走 ftth_common.attrib_hit）。
    两个筛选条件都没提供时视为"不过滤"，全部 INSERT 命中。
    """
    vals = {}
    try:
        for a in e.attribs:
            vals[a.dxf.tag] = a.dxf.text or ""
    except Exception:
        vals = {}
    if args.insert_attrib_tag is None and INSERT_VAL_KEYS is None:
        return True, vals
    TAGS = [t.strip() for t in (args.insert_attrib_tag or "").split(",") if t.strip()]
    return attrib_hit(vals, TAGS, INSERT_VAL_KEYS), vals


for e in msp:
    if e.dxftype() != "INSERT":
        continue
    ok, vals = _attrib_ok(e)
    _count(block_stat, e.dxf.name)
    if not ok:
        continue
    inserts.append({
        "x": e.dxf.insert.x, "y": e.dxf.insert.y,
        "名": e.dxf.name, "层": e.dxf.layer,
        "属性": vals,
    })

if args.insert_attrib_tag or INSERT_VAL_KEYS:
    log.info(f"设备块筛选：命中 {len(inserts)} 个（tag={args.insert_attrib_tag or '任意'}, val={INSERT_VAL_KEYS or '任意'}）")
    if not inserts:
        top = sorted(block_stat.items(), key=lambda kv: -kv[1])[:8]
        log.error("没有任何 INSERT 命中筛选条件。全图块名分布: " + ", ".join(f"{k}×{v}" for k, v in top))


# ---------- 5b. 分纤箱图形符号（2026-09-11 新增，P0-10） ----------
# 很多图纸的系统图里，分纤箱**只画图形符号、不写编号文字**——编号只出现在总图对照表。
# 实测教训：全图的编号文字可能全部只落在总图/拓扑区，系统图区一个都没有。
# 若不区分，脚本会把总图区的编号文字当成箱位置 → 每个箱都"附近找不到竖干"。
fx_symbols = []
fx_symbol_src = None
if SYM_LAYERS:
    _sym_layers = SYM_LAYERS
    _rect, _axis, _other = [], [], []
    for _e in msp:
        if _e.dxf.layer not in _sym_layers:
            continue
        try:
            _tp = _e.dxftype()
            if _tp == "LWPOLYLINE":
                _p = _e.get_points()
                if not _p:
                    continue
                _xs = [q[0] for q in _p]
                _ys = [q[1] for q in _p]
                _w, _h = max(_xs) - min(_xs), max(_ys) - min(_ys)
                _rec = {"x": (min(_xs) + max(_xs)) / 2, "y": (min(_ys) + max(_ys)) / 2,
                        "宽": _w, "高": _h, "类型": _tp}
                if _e.closed and _w <= args.fx_symbol_max_size and _h <= args.fx_symbol_max_size:
                    _rect.append(_rec)
                else:
                    _other.append(_rec)
            elif _tp == "LINE":
                _sx, _sy = _e.dxf.start.x, _e.dxf.start.y
                _ex, _ey = _e.dxf.end.x, _e.dxf.end.y
                _ln = ((_ex - _sx) ** 2 + (_ey - _sy) ** 2) ** 0.5
                _rec = {"x": (_sx + _ex) / 2, "y": (_sy + _ey) / 2,
                        "宽": _ln, "高": 0.0, "类型": _tp}
                (_axis if _ln > args.conn_tol else _other).append(_rec)
            else:
                try:
                    _p0 = _e.dxf.insert
                    _other.append({"x": _p0.x, "y": _p0.y, "宽": 0.0, "高": 0.0, "类型": _tp})
                except Exception:
                    pass
        except Exception:
            continue
    # 判别顺序：闭合小矩形（唯一可靠特征）→ 有向线段 → 其他图元。
    # 实测：分纤箱符号 = 宽而矮的闭合 LWPOLYLINE（矩形）；同图层另有大量 len=0 的 LINE，
    # 是皮线锚点而非箱体——若把 len=0 线段当箱，一个单元会凭空多出十几个"箱"。
    if _rect:
        _raw, fx_symbol_src = _rect, "闭合多段线(尺寸≤%g)" % args.fx_symbol_max_size
    elif _axis:
        _raw, fx_symbol_src = _axis, "有向线段（未找到闭合多段线，退化为线段，需人工复核）"
    else:
        _raw, fx_symbol_src = _other, "其他图元（未找到闭合多段线/线段，需人工复核）"
    for _r in _raw:
        _hit = None
        for _c in fx_symbols:
            if abs(_c["x"] - _r["x"]) <= args.fx_symbol_cluster and abs(_c["y"] - _r["y"]) <= args.fx_symbol_cluster:
                _hit = _c
                break
        if _hit is not None:
            _hit["_xs"].append(_r["x"])
            _hit["_ys"].append(_r["y"])
            _hit["x"] = sum(_hit["_xs"]) / len(_hit["_xs"])
            _hit["y"] = sum(_hit["_ys"]) / len(_hit["_ys"])
        else:
            _rec = dict(_r)
            _rec["_xs"] = [_r["x"]]
            _rec["_ys"] = [_r["y"]]
            fx_symbols.append(_rec)
    for _c in fx_symbols:
        _c["图元数"] = len(_c["_xs"])
    log.info(f"分纤箱符号层 {_sym_layers}: 候选图元 {len(_raw)}"
             f"（闭合矩形{len(_rect)} / 线段{len(_axis)} / 其他{len(_other)}）"
             f" → 判别来源「{fx_symbol_src}」→ {len(fx_symbols)} 个箱符号")
    if not fx_symbols:
        log.error("指定了 --fx-symbol-layer 但没取到任何图元，请核对图层名")
    elif not _rect:
        log.warning("该图层没找到『闭合多段线』符号，已退化为次级判别，结果需人工复核")

# ---------- 5c. 「符号区 / 标题区」同区护栏（2026-09-16 新增，P1-2） ----------
# 符号层取到了图元，但符号 x 与「楼栋 x 带」零重叠 ⇒ 二者不在同一图区。
# 最常见成因：--title-pattern 误匹配到「总图对照表区的楼栋行」而非系统图标题，
# 楼栋 x 范围被切在对照表区，而符号画在系统图区。若不在此处早失败，会一路走到
# 逐栋「本楼栋 x 范围内找不到任何箱图形符号」才报错 —— 那句错误把排错方向指向
# 「图层名不对」，而真因是「标题池 x 与符号 x 不同区」，容易误导（2026-09-16 实测）。
if fx_symbols and bldg_jobs:
    _sx_all = [s["x"] for s in fx_symbols]
    _jlo = min(j["x_lo"] for j in bldg_jobs)
    _jhi = max(j["x_hi"] for j in bldg_jobs)
    if not any(_jlo <= _x <= _jhi for _x in _sx_all):
        _msg = ("箱符号层 %s 取到 %d 个符号（x∈[%.0f,%.0f]），但楼栋 x 带 [%.0f,%.0f] 内"
                "一个都没有 → 二者不在同一图区。请核对 --title-pattern 是否匹配到了"
                "『总图对照表区的楼栋行』而非『系统图标题』：应让其匹配系统图标题"
                "（形如 `(\\d+)#.*?(?:系统图|示意图)`），并确认 --text-layer 覆盖标题所在图层。"
                % (args.fx_symbol_layer, len(_sx_all), min(_sx_all), max(_sx_all), _jlo, _jhi))
        if args.allow_low_pairing:
            log.warning("  [警告] " + _msg + "（已加 --allow-low-pairing，继续执行，结果须人工复核）")
        else:
            log.error("  [失败] " + _msg + " **本次未产出覆盖结果，已按失败退出（码 3）**")
            sys.exit(3)

# ---------- 6. 竖干拼接 ----------
def is_vertical_seg(seg, dx_tol, dy_tol):
    sx, sy = seg["start"]
    ex, ey = seg["end"]
    return abs(ex - sx) <= dx_tol and abs(ey - sy) >= dy_tol


def merge_vertical_segments(segments, dx_tol, dy_tol, merge_tol):
    """把竖线段按 x 聚类 + 端点相接合并成竖干。
    返回: [{x, y_min, y_max, 层们, 段数}]
    """
    vsegs = [s for s in segments if is_vertical_seg(s, dx_tol, dy_tol)]
    # 按 x 聚类
    vgroups = cluster_by_vertical(vsegs, dx_tol, x_key=lambda s: (s["start"][0] + s["end"][0]) / 2)
    trunks = []
    for g in vgroups:
        xs = [((s["start"][0] + s["end"][0]) / 2) for s in g["members"]]
        cx = sum(xs) / len(xs)
        # y 区间合并（相接/重叠容忍 merge_tol）
        intervals = sorted((min(s["start"][1], s["end"][1]), max(s["start"][1], s["end"][1])) for s in g["members"])
        layers = set()
        for s in g["members"]:
            layers.add(s["层"])
        cur_lo, cur_hi = intervals[0]
        for lo, hi in intervals[1:]:
            if lo - cur_hi <= merge_tol:
                cur_hi = max(cur_hi, hi)
            else:
                trunks.append({"x": cx, "y_min": cur_lo, "y_max": cur_hi,
                               "层": sorted(layers), "段数": len(g["members"])})
                cur_lo, cur_hi = lo, hi
        trunks.append({"x": cx, "y_min": cur_lo, "y_max": cur_hi,
                       "层": sorted(layers), "段数": len(g["members"])})
    trunks.sort(key=lambda t: t["x"])
    return trunks


def cluster_by_vertical(segments, tol, x_key):
    """按 x 聚类线段（统一走 ftth_common.cluster_by_x，避免两份等价实现漂移）。"""
    return cluster_by_x(segments, tol, x_key=x_key)


# ---------- 7. 皮线分类（按连接关系，不按 dy 阈值） ----------
def classify_drop_lines(segs, trunks, ins, conn_tol):
    """segs: 单元内全部线段; trunks: 单元内竖干; ins: 单元内设备块
    返回 (drops, unclassified)
    drops: [{竖干x, 设备x, 设备y, 层}]
    """
    drops, unclassified = [], []
    trunk_list = sorted(trunks, key=lambda t: t["x"])
    for seg in segs:
        if is_vertical_seg(seg, args.vert_dx, args.vert_dy):
            continue  # 竖线不参与皮线判定
        p1, p2 = seg["start"], seg["end"]
        hit_trunk, hit_p, other_p = None, None, None
        for t in trunk_list:
            for p in (p1, p2):
                if abs(p[0] - t["x"]) <= conn_tol and (t["y_min"] - conn_tol) <= p[1] <= (t["y_max"] + conn_tol):
                    hit_trunk, hit_p, other_p = t, p, (p2 if p is p1 else p1)
                    break
            if hit_trunk:
                break
        if hit_trunk is None:
            unclassified.append({
                "x1": round(p1[0], 1), "y1": round(p1[1], 1),
                "x2": round(p2[0], 1), "y2": round(p2[1], 1),
                "层": seg["层"], "类型": seg["类型"], "原因": "无端点落在竖干上",
            })
            continue
        # 另一端需落在设备 x 上
        best_dev, best_d = None, float("inf")
        for im in ins:
            d = abs(other_p[0] - im["x"])
            if d < best_d:
                best_d, best_dev = d, im
        if best_dev is not None and best_d <= conn_tol:
            drops.append({
                "竖干x": round(hit_trunk["x"], 1),
                "设备x": round(best_dev["x"], 1), "设备y": round(best_dev["y"], 1),
                "设备名": best_dev["名"], "设备层": best_dev["层"],
                "起点": (round(hit_p[0], 1), round(hit_p[1], 1)),
                "终点": (round(other_p[0], 1), round(other_p[1], 1)),
                "层": seg["层"], "类型": seg["类型"],
            })
        else:
            unclassified.append({
                "起点": (round(p1[0], 1), round(p1[1], 1)),
                "终点": (round(p2[0], 1), round(p2[1], 1)),
                "层": seg["层"], "类型": seg["类型"],
                "原因": "一端在竖干但另一端不在设备x上",
            })
    return drops, unclassified


# ---------- 8. 分纤箱 → 楼栋分组 ----------
result = {"DXF文件": os.path.basename(DXF_PATH),
          "说明": "本文件所有覆盖范围均为线索，需用户裁决，不可直接作为结论",
          "参数": {
              "文字图层": TEXT_LAYERS,
              "连线图层": WIRE_LAYERS if WIRE_LAYERS else "（未指定：已扫描全图，见下方图层统计）",
              "设备块筛选": {"attrib_tag": args.insert_attrib_tag, "attrib_val": INSERT_VAL_KEYS},
              "楼层解析": "内置统一解析（支持 3F/-1F/B1/B2/WF）" if not args.floor_pattern else args.floor_pattern,
              "楼栋单元归属方式": belong_mode,
              "箱位来源": ("图形符号层 " + args.fx_symbol_layer + f"（判别：{fx_symbol_src}）")
                          if fx_symbol_src else "编号文字（未传 --fx-symbol-layer）",
              "排除的箱符号图元数": _skipped_symbols,
          },
          "线段图层来源统计": {
              "参与分析": dict(sorted(seg_layer_stat.items(), key=lambda kv: -kv[1])),
              "全图分布TOP20": dict(sorted(ALL_LAYERS_STAT.items(), key=lambda kv: -kv[1])[:20]),
              "警示": None if WIRE_LAYERS else
                      "未传 --wire-layer：以上『参与分析』图层被直接当作电信主干。"
                      "若其中出现图层 0 / 建筑 / 图框 / 家具 等，本次结果不可用，必须显式指定 --wire-layer",
          },
          "楼栋": {}}


def fl_num(f):
    return floor_num_or_zero(f, args.floor_pattern, use_fullmatch=True)


def floors_equal(a, b):
    """楼层标注等价判定（供总图交叉校验用）。

    同写法直接判等（覆盖 'WF' 这类无非数字写法的情形）；写法不同时按统一解析值比较，
    以兼容 '5F' / '05F' / '5f' 等不同写法。任一方不可解析则判为不等（需人工裁决，
    不做静默等同）。
    """
    if a is None or b is None:
        return False
    if str(a).strip() == str(b).strip():
        return True
    va = parse_floor_label(a)[0]
    vb = parse_floor_label(b)[0]
    return va is not None and vb is not None and va == vb


# ---------- 总图交叉校验（2026-09-13 新增，落实 SKILL.md「Step 1 · 分纤箱总图检查」三项均须一致） ----------
# 总图对照表（口径A：图上直写）是权威参照，区间法（口径B）仅为无直写值时的兜底。
# 二者不一致时以总图为准（SKILL.md「测量方式架构 · 方法对照表」安装楼层=读取标注直写优先），冲突集中记入「需人工裁决」，
# 不得静默采信区间法——旧实现在此处无条件写区间法，导致总图直写值被静默覆盖。
_floor_conflicts = []


for bldg_job in bldg_jobs:
    bldg_name = bldg_job["楼栋"]
    xmin, xmax = bldg_job["x_lo"], bldg_job["x_hi"]
    bldg_units = [u for u in bldg_job["单元"] if u["箱"]]
    if not bldg_units:
        continue
    floors = floors_in_range(xmin, xmax)
    floor_items = [(f["内容"], f["y"]) for f in floors]
    bldg_result = {"单元": {}}

    # 楼层间距（本楼栋刻度）：用于自适应容差（拼接容差 / 断口楼层容差 / 箱符号配对容差）
    # 注意：一个楼栋范围内常并存多套楼层刻度（住宅系统图+配套系统图，y 只差零点几），
    # 若直接把全部标签的相邻差取中位数，会得到"半格值"（如 15 而非 30）→ 容差整体偏小、
    # 断口楼层归属随之判错。故：先按 x 聚刻度，取标签最多的那一套，再算它的层高。
    # 2026-09-15 通用化：此处原为 `round(f["x"] / 40)` —— 40 是绝对坐标容差，只对标定
    # 它的那一档坐标尺度成立（换到层高 15600 的图，整张图会被并成一簇）。
    # 改用「间隙 > k×低分位间隙」的自适应聚类，簇宽的尺子取自 x 数据自身。
    _xkey = {}
    for _gi, _grp in enumerate(cluster_values_by_gap(sorted(f["x"] for f in floors))):
        for _xv in _grp:
            _xkey[round(_xv, 6)] = _gi
    _scales = {}
    for f in floors:
        _scales.setdefault(_xkey[round(f["x"], 6)], []).append(f["y"])
    _main = max(_scales.values(), key=len) if _scales else []
    _my = sorted(_main)
    _mg = [b - a for a, b in zip(_my, _my[1:]) if 0 < b - a <= 100]
    _fgap = sorted(_mg)[len(_mg) // 2] if _mg else 0.0
    # 拼接容差自适应：图纸常在某层处把竖干画成两段（端点差几个单位），那不是物理断口。
    # 判据：小于 40% 层高 → 绘图断缝，拼起来；≥40% 层高 → 物理断口，保留。
    _mtol = max(args.merge_tol, 0.4 * _fgap) if _fgap else args.merge_tol
    _bftol = args.break_floor_tol if args.break_floor_tol > 0 else (0.6 * _fgap if _fgap else 15.0)
    # 断口跨度上限（P0-16）：只有间距 ≤ 该上限的两个连续体才算"同一根竖干被断开的上下段"。
    # 为什么必须有上限：同一 x 上可能并排存在【住宅系统图带】与【配套系统图带】两张图
    #   （住宅系统图带与配套系统图带横向重叠、x 基本重合）。两者之间的空白是**纸面空白**，
    #   不是物理断口。若当成断口，会把另一张图的楼层（如配套图的 B1/WF）拉进来，
    #   产生伪条目、并让"最低段下方紧邻层"规则失效。
    # 取值依据（实测）：真断口跨度约 1.1 倍层高；跨图带伪断口约 3.6 倍层高。
    _maxbrk = args.max_break_span if args.max_break_span > 0 else (2.0 * (_fgap or 30.0))
    bldg_result["楼层刻度"] = [{"内容": f["内容"], "x": f["x"], "y": f["y"]} for f in floors]
    bldg_result["自适应容差"] = {"层高": round(_fgap, 1), "竖干拼接容差": round(_mtol, 1),
                            "断口楼层归属容差": round(_bftol, 1), "断口跨度上限": round(_maxbrk, 1)}

    # ---------- 箱体定位（2026-09-11 重写，P0-10 / P0-11） ----------
    # 为什么不能用编号文字定位：编号文字可能全部只出现在**总图/拓扑图**区（与主干不在一处），
    # 直接用它当箱位置 → 每个箱都"附近找不到竖干"（实测教训：编号文字可能全在总图区，
    # 而主干/箱符号在系统图区）。故：优先图形符号，编号文字只作回退。
    #
    # 指派规则（几何残差，不做"顺序推断"）：
    #   对每个(符号,箱)对，残差 = |符号y − 该箱「对照表安装楼层」对应的楼层线y|（同名楼层取最近线）。
    #   按残差升序做唯一指派（贪心，等价于最小代价匹配的常用近似）。残差 ≤ 阈值 → 判为可信；
    #   残差 > 3×阈值 → 视为不可信，该箱退回编号文字并标"需人工复核"。
    # 为什么用"楼层线y"而不是"最近楼层文字"：同范围内可能并存多套楼层刻度（住宅图+配套图），
    # 取最近文字会跨刻度串味；而按楼层名找线、取最近线，可以自然消解刻度混叠。
    _box_syms = [s for s in fx_symbols if xmin <= s["x"] <= xmax] if fx_symbols else []
    _all_boxes = [(u["单元名"], b) for u in bldg_units for b in u["箱"]]
    unit_boxes_map = {}      # 单元名 -> [箱对象]
    pairing_note = {}
    _pos_src = {}            # 编号 -> (位置来源说明, x, y)

    _yfv = {}                # 楼层值 -> [楼层线y, ...]
    for _fl, _fy in floor_items:
        _v = parse_floor_label(_fl)[0]
        if _v is not None:
            _yfv.setdefault(_v, []).append(_fy)
    _pair_tol = args.symbol_pair_tol if args.symbol_pair_tol > 0 else (0.6 * _fgap if _fgap else 15.0)

    # 坑3（2026-09-15，TeleAgent 复盘）：图上没有任何箱符号时，箱位将回退到编号文字坐标
    # （编号文字常在总图区，与主干无关）→ 竖干配对率 0%、覆盖结果全错但脚本照跑。
    # 静默错误数据不如失败。确认无符号画法后可用 --allow-low-pairing 强行继续。
    if _all_boxes and not _box_syms and not args.allow_low_pairing:
        log.error(
            "  [失败] %s：对照表有 %d 个箱，但本楼栋 x 范围内找不到任何箱图形符号"
            "（--fx-symbol-layer=%s）→ 箱位将回退编号文字坐标，覆盖计算必然失真，"
            "已按失败退出（码 3）。处置：① 核对 --fx-symbol-layer 是否为符号所在图层；"
            "② 确认本图确实无符号画法后加 --allow-low-pairing 强行继续（结果须人工复核）。",
            bldg_name, len(_all_boxes), args.fx_symbol_layer or "未提供")
        sys.exit(3)

    if _box_syms and _all_boxes:
        _cand = []
        for _si, _s in enumerate(_box_syms):
            for _ui, (_un, _b) in enumerate(_all_boxes):
                _fl_txt = _b.get("对照表安装楼层")
                _fv = parse_floor_label(_fl_txt)[0] if _fl_txt else None
                if _fv is None or _fv not in _yfv:
                    continue
                _r = min(abs(_s["y"] - _yy) for _yy in _yfv[_fv])
                _cand.append((_r, _si, _ui))
        _cand.sort(key=lambda t: (t[0], t[1], t[2]))
        _used_s, _used_b, _assign = set(), set(), {}
        for _r, _si, _ui in _cand:
            if _si in _used_s or _ui in _used_b:
                continue
            _used_s.add(_si)
            _used_b.add(_ui)
            _assign[_ui] = (_si, _r)
        _bad = 0
        for _ui, (_un, _b) in enumerate(_all_boxes):
            if _ui in _assign and _assign[_ui][1] <= 3 * _pair_tol:
                _si, _r = _assign[_ui]
                _s = _box_syms[_si]
                _ok = _r <= _pair_tol
                _extra = ""
                if not _ok:
                    # 残差超阈值的常见实况（2026-09-15，实测教训）：符号在该图带内唯一、
                    # 位置本身已定；残差大是因为系统图把符号画在与总图安装层不同的楼层
                    # （图纸自身打架）。文案必须区分「找不到箱」与「找到了但层标注冲突」，
                    # 否则读起来像位置不可信。附几何最近层，供人直接比对。
                    _near = None
                    for _fl, _fy in floor_items:
                        _d = abs(_s["y"] - _fy)
                        if _near is None or _d < _near[1]:
                            _near = (_fl, _d)
                    _near_str = (f"，几何最近层 {_near[0]}（距 {_near[1]:.1f}）"
                                 if _near else "")
                    _extra = (f"；与对照表安装层残差 {_r:.1f} 超阈值 {_pair_tol:.1f}"
                              f"——符号位置本身已明确{_near_str}，"
                              f"多为系统图与总图安装层标注冲突，需人工裁决")
                _pos_src[_b["编号"]] = (
                    "图形符号（%s）；与安装楼层线残差 %.1f（阈值 %.1f）%s"
                    % (fx_symbol_src, _r, _pair_tol, _extra),
                    _s["x"], _s["y"])
                if not _ok:
                    _bad += 1
            else:
                _pos_src[_b["编号"]] = ("编号文字（回退：无可用箱符号或残差过大，需人工复核）", None, None)
                _bad += 1
        # 坑3（2026-09-15）：可信配对率 < 30% 说明符号层/对照表/图层参数至少一项错位，
        # 回退箱位会让覆盖结果系统性失真 —— 硬失败优于静默错误数据。
        _ok_n = sum(1 for _si, _r in _assign.values() if _r <= 3 * _pair_tol)
        _rate = _ok_n / len(_all_boxes)
        pairing_note["符号配对率"] = "%.0f%%（%d/%d，阈值 %.1f）" % (
            _rate * 100, _ok_n, len(_all_boxes), _pair_tol)
        if _rate < 0.3 and not args.allow_low_pairing:
            log.error(
                "  [失败] %s：箱符号可信配对率 %.0f%%（%d/%d）< 30%% —— "
                "符号层/对照表安装层/图层参数至少一项错位，继续跑只会产出错误数据，"
                "已按失败退出（码 3）。核对 --fx-symbol-layer 与对照表『安装楼层』口径；"
                "确属图面特殊情况可加 --allow-low-pairing 强行继续。",
                bldg_name, _rate * 100, _ok_n, len(_all_boxes))
            sys.exit(3)
        _unclaimed = [_box_syms[i] for i in range(len(_box_syms)) if i not in _used_s]
        if _unclaimed:
            pairing_note["未认领箱符号"] = [
                {"x": round(s["x"], 1), "y": round(s["y"], 1)} for s in _unclaimed]
            log.warning(f"  [注意] {bldg_name}：有 {len(_unclaimed)} 个箱符号没被任何箱认领（"
                        f"可能是他楼栋的箱或图面冗余），已记入配对说明")
        pairing_note["配对方式"] = ("符号y ↔ 对照表安装楼层线 的几何残差唯一指派"
                                f"（阈值 {_pair_tol:.1f}）")
        if _bad:
            pairing_note["需人工复核的箱"] = [
                b["编号"] for _un, b in _all_boxes if "人工复核" in _pos_src.get(b["编号"], ("",))[0]]
        log.info(f"  {bldg_name}: 对照表 {len(_all_boxes)} 个箱 / 图上 {len(_box_syms)} 个箱符号，"
                 f"已按安装楼层线残差指派（逐箱位置来源见输出 JSON）")

    for _u in bldg_units:
        _boxes = []
        for _b in _u["箱"]:
            _src, _bx, _by = _pos_src.get(_b["编号"], (None, None, None))
            if _bx is None:
                _tp = _text_pos.get(_b["编号"])
                if _tp is None:
                    log.error(f"  [错误] {_u['单元名']} {_b['编号']}：既没有箱符号也没有编号文字，无法定位")
                    continue
                _src = _src.replace("；需人工复核", "") if _src else ""
                _src = (_src + "；" if _src.startswith("编号文字") else "编号文字（回退）") + \
                       "未取到可靠箱符号，可能不在主干区，需人工复核"
                _bx, _by = _tp
            _boxes.append({"编号": _b["编号"], "x": _bx, "y": _by, "位置来源": _src,
                           "对照表安装楼层": _b.get("对照表安装楼层")})
        if _boxes:
            unit_boxes_map[_u["单元名"]] = _boxes

    for ui, cluster in enumerate(bldg_units):
        unit_name = cluster["单元名"]
        unit_boxes = unit_boxes_map.get(unit_name)
        if not unit_boxes:
            continue
        unit_result = {"分纤箱": [], "箱位来源": sorted({b["位置来源"] for b in unit_boxes})}

        # 单元 x 范围（以分纤箱聚类质心 ± fx_window + conn_tol）
        ux_lo = min(b["x"] for b in unit_boxes) - args.fx_window - args.conn_tol
        ux_hi = max(b["x"] for b in unit_boxes) + args.fx_window + args.conn_tol

        # 单元内线段（与 x 范围相交）
        unit_segs = [
            s for s in segments
            if min(s["start"][0], s["end"][0]) <= ux_hi and max(s["start"][0], s["end"][0]) >= ux_lo
        ]
        unit_ins = [i for i in inserts if ux_lo <= i["x"] <= ux_hi]

        # 单元内竖干
        trunks = merge_vertical_segments(unit_segs, args.vert_dx, args.vert_dy, _mtol)

        # 皮线分类
        drops, unclassified = classify_drop_lines(unit_segs, trunks, unit_ins, args.conn_tol)

        # 按楼层统计设备数/皮线数（区间法）
        dev_per_floor = {}
        for im in unit_ins:
            fl_name, _ = assign_floor_by_interval(im["y"], floor_items)
            dev_per_floor.setdefault(fl_name, []).append(im)
        drop_per_floor = {}
        for d in drops:
            fl_name, _ = assign_floor_by_interval(d["设备y"], floor_items)
            drop_per_floor.setdefault(fl_name, []).append(d)

        # 设备异常检查：有设备但无皮线连接
        anomaly_floors = []
        for fl_name, devs in dev_per_floor.items():
            n_drop = len(drop_per_floor.get(fl_name, []))
            if n_drop == 0:
                anomaly_floors.append({"楼层": fl_name, "设备数": len(devs), "皮线数": 0, "性质": "异常（有设备无皮线）"})

        unit_result["设备层皮线核对"] = {
            "每层设备数": {k: len(v) for k, v in sorted(dev_per_floor.items(), key=lambda kv: (kv[0] is None, fl_num(kv[0])))},
            "每层皮线数": {k: len(v) for k, v in sorted(drop_per_floor.items(), key=lambda kv: (kv[0] is None, fl_num(kv[0])))},
            "异常楼层": anomaly_floors,
        }

        # ---------- 竖干物理断口：单元内主干被断口切成的连续体（2026-09-11 新增，P0-7） ----------
        # 同一 x 上的多个 trunk 就是被物理断口切开的连续体。断口位置是覆盖分界的直接证据。
        # 实测：断口是 y 方向的一段区间，不是单个点。
        unit_trunks = sorted(
            [t for t in trunks if any(abs(t["x"] - b["x"]) < args.fx_window for b in unit_boxes)],
            key=lambda t: (round(t["x"], 1), t["y_min"]))
        breaks = []
        for a, b in zip(unit_trunks, unit_trunks[1:]):
            if abs(a["x"] - b["x"]) <= args.conn_tol and _mtol < (b["y_min"] - a["y_max"]) <= _maxbrk:
                mid = (a["y_max"] + b["y_min"]) / 2
                f_mid, _ = y_to_floor_name(mid, floors)
                breaks.append({
                    "x": round((a["x"] + b["x"]) / 2, 1),
                    "y_low": round(a["y_max"], 1),
                    "y_high": round(b["y_min"], 1),
                    "中点y": round(mid, 1),
                    "断口处最近的楼层标注": f_mid,
                })
        # P0-16：跨度超过上限的连续体对 → 不是断口，单列出来供人核对（多为跨图带误并入）
        far_trunks = []
        for a, b in zip(unit_trunks, unit_trunks[1:]):
            if abs(a["x"] - b["x"]) <= args.conn_tol and (b["y_min"] - a["y_max"]) > _maxbrk:
                far_trunks.append({
                    "x": round((a["x"] + b["x"]) / 2, 1),
                    "下段": "%.1f~%.1f" % (a["y_min"], a["y_max"]),
                    "上段": "%.1f~%.1f" % (b["y_min"], b["y_max"]),
                    "间距": round(b["y_min"] - a["y_max"], 1),
                    "性质": "间距 %.1f 超过断口跨度上限 %.1f → 疑似跨图带/跨单元误并入，未参与断口判定"
                            % (b["y_min"] - a["y_max"], _maxbrk),
                })

        claimed_map = {}      # id(trunk) -> [认领它的箱号]

        # 对每个分纤箱：认领其专属竖干连续体 + 皮线
        for box in unit_boxes:
            bx, by = box["x"], box["y"]
            box_id = box["编号"]

            near_trunks = [t for t in unit_trunks if abs(t["x"] - bx) < args.fx_window]

            # 认领规则（纯几何直读，不作推断）：
            #   箱的 y 落在哪个连续体的 y 区间内，该箱就服务哪个连续体；
            #   都不落在区间内时，取 y 最近的一个。
            # 注意：旧实现取"附近全部竖干的 min~max"，会把断口两侧的连续体合并成一整段，
            #       导致同一单元的两个箱得到完全相同的覆盖范围（P0-7 的核心症状）。
            own, own_how = None, None
            if near_trunks:
                own = next((t for t in near_trunks if t["y_min"] <= by <= t["y_max"]), None)
                if own is not None:
                    own_how = "箱的y坐标落在该连续体区间内（几何直读）"
                else:
                    own = min(near_trunks, key=lambda t: min(abs(by - t["y_min"]), abs(by - t["y_max"])))
                    own_how = "箱的y不在任何连续体区间内，取最近连续体（需复核）"

            box_drops = []
            if own is not None:
                claimed_map.setdefault(id(own), []).append(box_id)
                for dr in drops:
                    if abs(dr["竖干x"] - own["x"]) <= args.conn_tol and \
                       (own["y_min"] - args.conn_tol) <= dr["起点"][1] <= (own["y_max"] + args.conn_tol):
                        box_drops.append(dr)

            coverage_clue = None
            if own is not None:
                # 竖线法覆盖判定（三步走，2026-09-12 重构，替代旧的"遍历全部楼层+边界层审计"）：
                #   ① 每层 y 坐标 → floor_items（本楼栋 x 范围内楼层刻度，已排除总图区文字）；
                #   ② 分纤箱安装楼层 → assign_floor_by_interval(箱y, floor_items)（下方 f_install），
                #      与总图对照表 fx_map.json 的位置校验见箱-单元-符号配对；
                #   ③ 覆盖楼层 = 用区间法测量竖线断口所在层：
                #      底断点（本连续体最低端点 y_min）→ 覆盖下界层；
                #      顶断点（本连续体最高端点 y_max）→ 覆盖上界层；
                #      覆盖层 = 下界层 ~ 上界层 之间全部楼层（闭区间）。
                #      中间楼层 y 必然落在连续体内部，天然连续，无需逐层判定。
                # 为什么断头/断口用区间法测层：断口是一个 y 区间（不是单个点），
                # 端点落在哪两层刻度之间，就属于下方楼层（assign_floor_by_interval 语义）。
                # 不用断口中点——中点落在层带交界处没有物理意义（2026-09-12 用户裁定）。
                # 下限超出最低刻度线 → 取最低层；上限超出最高刻度线 → 取最高层。
                _bot_fl, _ = assign_floor_by_interval(own["y_min"], floor_items, tol=None)
                _top_fl, _ = assign_floor_by_interval(own["y_max"], floor_items, tol=None)
                # 2026-09-12 修复（P0）：本楼栋楼层刻度为空时（实测：楼层列可能紧邻
                # FX 编号文字，距离小于 --total-pad，刻度被 floors_in_range 全量排除），
                # 下面的 min()/max() 会抛 ValueError 让整个脚本中止。
                # 现改为：无刻度则留空覆盖，由后续「覆盖范围无法判定」分支列入待裁决。
                if floor_items:
                    if _bot_fl is None:
                        _bot_fl = min(floor_items, key=lambda f: fl_num(f[0]))[0]
                    if _top_fl is None:
                        _top_fl = max(floor_items, key=lambda f: fl_num(f[0]))[0]
                    _bl, _tl = fl_num(_bot_fl), fl_num(_top_fl)
                    cover_def = sorted({lbl for lbl, _ in floor_items if _bl <= fl_num(lbl) <= _tl},
                                       key=fl_num)
                else:
                    cover_def = []
                coverage_clue = {
                    "连续体": {
                        "x": round(own["x"], 1),
                        "y_min": round(own["y_min"], 1),
                        "y_max": round(own["y_max"], 1),
                        "段数": own["段数"],
                        "层": own["层"],
                    },
                    "覆盖楼层": cover_def,
                    "floor_min": cover_def[0] if cover_def else None,
                    "floor_max": cover_def[-1] if cover_def else None,
                    "皮线数": len(box_drops),
                    "认领依据": own_how,
                    # 2026-09-13 P1-2：判定依据/依据来源 显式成列（用户裁定三字段齐备）——
                    # 避免下游把覆盖楼层当作无出处的结论，也避免「23/23 全量误报」式误读。
                    "判定依据": ("竖线法（断口区间法直读）：箱认领的竖干连续体底端点→覆盖下界层、"
                               "顶端点→覆盖上界层，两端点经区间法对位本楼栋楼层刻度，"
                               "上下界之间全部楼层闭区间即覆盖楼层"),
                    "依据来源": (f"图层 [{args.wire_layer or '全图（未指定 --wire-layer）'}] 竖干连续体 "
                               f"x≈{round(own['x'], 1)} y=[{round(own['y_min'], 1)}, {round(own['y_max'], 1)}]"
                               f"（{own['段数']}段）；本楼栋楼层刻度 {len(floor_items)} 条"
                               f"（楼层间距 {round(_fgap, 1)}）"),
                    "性质": "线索（竖线法：断口区间法直读，需用户裁决）",
                }

            f_install, dist = assign_floor_by_interval(by, floor_items, tol=None)

            # ---- 总图交叉校验（具现 SKILL.md「方法对照表」安装楼层直写优先 / 「Step 1 · 分纤箱总图检查」三项一致）----
            _tb = box.get("对照表安装楼层")
            if _tb:
                _ok = floors_equal(_tb, f_install)
                _final = _tb
                _caliber = ("口径A:图上直写（与区间法一致）" if _ok
                            else "口径A:图上直写（覆盖区间法，冲突已列待裁决）")
                _consistency = "一致" if _ok else "冲突（已以总图为准）"
                if not _ok:
                    _floor_conflicts.append({
                        "对象": judge_object_name(bldg_name, unit_name, box_id),
                        "事项": "安装楼层与总图冲突",
                        "说明": f"总图直写(口径A) {_tb} vs 区间法(口径B) {f_install}"
                                f"（区间法误差 {round(dist, 2)}，箱y={round(by, 1)}）；"
                                f"已按总图直写值采用，请核对两图是否指向同一批分纤箱",
                        "总图直写（口径A）": _tb,
                        "区间法（口径B）": f_install,
                        "区间法误差": round(dist, 2),
                        "箱y": round(by, 1),
                        "处置": "已按总图直写值采用（直写优先）",
                    })
                    log.warning(f"  [冲突] {unit_name}/{box_id} 安装楼层：总图直写 {_tb} vs "
                                f"区间法 {f_install} → 已按总图取值，并列入需人工裁决")
            else:
                _final = f_install
                _caliber = "口径B:区间法（总图无直写值）"
                _consistency = "无法比对（总图无直写值）"

            box_result = {
                "编号": box_id,
                "x": round(bx, 1),
                "y": round(by, 1),
                "位置来源": box.get("位置来源"),
                "位置可信": not ("回退" in (box.get("位置来源") or "") or "回退值" in (box.get("位置来源") or "")),
                "安装楼层": _final,
                "安装楼层口径": _caliber,
                "安装楼层误差": round(dist, 2),
                "安装楼层_区间法": f_install,
                "安装楼层_总图直写": _tb,
                "安装楼层一致性": _consistency,
                "覆盖范围线索": coverage_clue,
                "关联皮线": [
                    {"设备x": d["设备x"], "设备y": d["设备y"], "设备名": d["设备名"], "层": d["层"]}
                    for d in box_drops
                ],
            }
            unit_result["分纤箱"].append(box_result)

            log.info(f"\n  {box_id} (x={bx:.1f}, y={by:.1f}) 安装楼层={_final}(±{dist:.1f})"
                     + (f"｜总图直写 {_tb}｜区间法 {f_install}" if _tb else "｜总图无直写值"))
            if coverage_clue:
                log.info(f"    认领连续体 y=[{coverage_clue['连续体']['y_min']}, {coverage_clue['连续体']['y_max']}]"
                         f" → 覆盖 {'/'.join(str(x) for x in coverage_clue['覆盖楼层'])}"
                         f"（{coverage_clue['floor_min']}~{coverage_clue['floor_max']}, 皮线{len(box_drops)}条）")
            else:
                log.info("    覆盖范围线索: 无（该箱附近未找到竖干）")

        # ---------- 连续体认领健康度（诊断 P0-7） ----------
        unit_result["竖干连续体"] = [
            {"x": round(t["x"], 1), "y_min": round(t["y_min"], 1), "y_max": round(t["y_max"], 1),
             "段数": t["段数"], "层": t["层"]} for t in unit_trunks
        ]
        if breaks:
            unit_result["竖干断口"] = breaks
        if far_trunks:
            unit_result["疑似跨图带连续体"] = far_trunks
            log.warning(f"  [注意] {unit_name} 有 {len(far_trunks)} 处相邻连续体间距超过断口跨度上限 "
                        f"{_maxbrk:.1f}，已按『非断口』处理（多为跨图带误并入），请核对")

        unclaimed = [{"x": round(t["x"], 1), "y_min": round(t["y_min"], 1), "y_max": round(t["y_max"], 1)}
                     for t in unit_trunks if id(t) not in claimed_map]
        if unclaimed:
            unit_result["未认领竖干连续体"] = unclaimed
            log.warning(f"  [异常] {unit_name} 有 {len(unclaimed)} 个竖干连续体没有任何分纤箱认领，"
                        f"可能是漏箱或图层过滤不当")

        shared = []
        for t in unit_trunks:
            v = claimed_map.get(id(t), [])
            if len(v) > 1:
                shared.append({"x": round(t["x"], 1),
                               "y_min": round(t["y_min"], 1), "y_max": round(t["y_max"], 1),
                               "同时被认领的箱": v})
        if shared:
            unit_result["连续体被多箱认领"] = shared
            log.warning(f"  [异常] {unit_name} 有 {len(shared)} 个连续体被多个箱同时认领（覆盖范围会重复），需复核")

        # 未分类线段（按单元汇总，供人工检查）
        unit_result["未分类线段"] = unclassified
        if unclassified:
            log.info(f"\n  [注意] {unit_name} 有 {len(unclassified)} 条未分类线段，见JSON供人工检查")

        # ---------- 多箱分界线索：由竖干物理断口给出（2026-09-11 重写，P0-5 / P0-7） ----------
        # 严禁"按安装楼层从低到高排序、顺序切分楼层"——那是推断而非读图。
        if len(unit_result["分纤箱"]) >= 2:
            unit_result["多箱分界线索"] = {
                "箱数": len(unit_result["分纤箱"]),
                "竖干连续体数": len(unit_trunks),
                "物理断口": breaks,
                "各箱认领": [
                    {
                        "编号": b["编号"],
                        "安装楼层": b["安装楼层"],
                        "认领连续体y": ([b["覆盖范围线索"]["连续体"]["y_min"],
                                       b["覆盖范围线索"]["连续体"]["y_max"]]
                                      if b["覆盖范围线索"] else None),
                        "覆盖楼层": (b["覆盖范围线索"]["覆盖楼层"] if b["覆盖范围线索"] else None),
                    }
                    for b in unit_result["分纤箱"]
                ],
                "性质": "线索：分界由竖干物理断口确定，非按安装楼层排序切分",
                "禁止事项": "不得改用『按安装楼层排序后顺序切分楼层』；断口缺失时应列为待确认项交用户裁决",
            }
            log.info(f"\n  --> 多箱分界线索（{len(unit_result['分纤箱'])}箱 / "
                     f"{len(unit_trunks)}个连续体 / {len(breaks)}个断口）:")
            for b in unit_result["分纤箱"]:
                c = b["覆盖范围线索"]
                if c:
                    log.info(f"      {b['编号']} 安装={b['安装楼层']} "
                             f"认领y=[{c['连续体']['y_min']},{c['连续体']['y_max']}] "
                             f"覆盖={c['floor_min']}~{c['floor_max']}")
                else:
                    log.info(f"      {b['编号']} 安装={b['安装楼层']} 无线索")
            for bk in breaks:
                log.info(f"      断口 x={bk['x']} y={bk['y_low']}~{bk['y_high']} "
                         f"(中点 {bk['中点y']} ≈ {bk['断口处最近的楼层标注']})")

        # 异常提示
        if anomaly_floors:
            unit_result["异常"] = anomaly_floors
            log.info(f"\n  [异常] {unit_name} 有设备但无皮线的楼层: {[a['楼层'] for a in anomaly_floors]}")

        bldg_result["单元"][unit_name] = unit_result

    if pairing_note:
        bldg_result["箱-单元-符号 配对说明"] = pairing_note
    result["楼栋"][bldg_name] = bldg_result

# ---------- 9. 需人工裁决清单 ----------
# 把"脚本自己知道不确定"的地方集中列出来，避免它们被淹没在逐箱明细里。
_judge = []
_sym_use = {}
for _b, _bd in result["楼栋"].items():
    for _u, _ud in _bd.get("单元", {}).items():
        for _bx in _ud.get("分纤箱", []):
            _who = judge_object_name(_b, _u, _bx.get("编号"))
            _src = _bx.get("位置来源") or ""
            if _src.startswith("图形符号"):
                _sym_use.setdefault((_bx.get("x"), _bx.get("y")), []).append(_who)
            if "复核" in _src or "标注冲突" in _src:
                _judge.append({"对象": _who,
                               "事项": "箱安装层标注冲突（符号位置已定）" if "标注冲突" in _src
                                       else "箱位置不确定",
                               "说明": _src})
            _cl = _bx.get("覆盖范围线索")
            if _cl is None:
                _judge.append({"对象": _who, "事项": "覆盖范围无法判定", "说明": "该箱位置附近找不到任何竖干连续体"})
            else:
                if "复核" in (_cl.get("认领依据") or ""):
                    _judge.append({"对象": _who, "事项": "覆盖范围需复核", "说明": _cl.get("认领依据")})
                if not _cl.get("覆盖楼层"):
                    _judge.append({"对象": _who, "事项": "覆盖楼层为空", "说明": "所认领连续体的 y 区间内没有楼层标注"})
for (_sx, _sy), _who in _sym_use.items():
    if len(_who) > 1:
        _judge.append({"对象": _who, "事项": "同一箱符号被多箱共用",
                       "说明": f"符号 (x={_sx}, y={_sy}) 被 {len(_who)} 个箱认领——"
                               f"图上该处可能只画了一个箱，其余箱号在图面缺失"})
        # 共享图区箱位不全（2026-09-13，7#8#10# 实测：三栋楼共享一张系统图，图面只画 1 个
        # 箱标注）：除裁决清单外，逐箱明细与覆盖线索同步标注——该区域箱归属依赖配纤表直读。
        _note = (f"共享图区箱标注不全（{len(_who)} 箱共用同一图形符号 ({_sx},{_sy})），"
                 "该区域箱归属依赖配纤表直读，图面箱位不作准")
        for _b2, _bd2 in result["楼栋"].items():
            for _u2, _ud2 in _bd2.get("单元", {}).items():
                for _bx2 in _ud2.get("分纤箱", []):
                    if ((_bx2.get("x"), _bx2.get("y")) == (_sx, _sy)
                            and (_bx2.get("位置来源") or "").startswith("图形符号")):
                        _bx2["图面箱位备注"] = _note
                        _cl2 = _bx2.get("覆盖范围线索")
                        if _cl2 is not None:
                            _cl2["图面箱位备注"] = _note
# P0-16：被跨度上限挡掉的相邻连续体必须显式列出，不能静默丢弃
for _b, _bd in result["楼栋"].items():
    for _u, _ud in _bd.get("单元", {}).items():
        for _ft in _ud.get("疑似跨图带连续体", []):
            _judge.append({"对象": judge_object_name(_b, _u), "事项": "疑似跨图带连续体（已排除）",
                           "说明": f"x≈{_ft['x']} 处下段 {_ft['下段']} 与上段 {_ft['上段']} 间距 {_ft['间距']}，"
                                   f"超过断口跨度上限，已按『非断口』处理（不同图带/不同单元）；"
                                   f"若实为同一根竖干被远距离断开，请调大 --max-break-span 后重跑"})
# 总图交叉校验的冲突项一并进入待裁决清单（2026-09-13 新增）
_judge.extend(_floor_conflicts)
if args.bldg_map:
    _n_tb = sum(1 for _bd2 in result["楼栋"].values()
                for _ud2 in _bd2.get("单元", {}).values()
                for _x2 in _ud2.get("分纤箱", []) if _x2.get("安装楼层_总图直写"))
    result["安装楼层总图校验"] = {
        "对照表可比对箱数": _n_tb,
        "冲突数": len(_floor_conflicts),
        "冲突明细": _floor_conflicts,
        "口径": "直写优先（SKILL.md「方法对照表」安装楼层）；不一致以总图为准并列入需人工裁决（SKILL.md「Step 1 · 分纤箱总图检查」）",
    }
    log.info("安装楼层总图校验：可比对 %d 箱，冲突 %d 箱（冲突项已按总图取直写值）",
             _n_tb, len(_floor_conflicts))

if _judge:
    result["需人工裁决"] = _judge
    log.warning("需人工裁决 %d 项（详见输出 JSON 的『需人工裁决』）：", len(_judge))
    for _j in _judge[:20]:
        log.warning("  - [%s] %s：%s", _j["事项"], _j["对象"], _j["说明"])

# ---------- 9b. 作业门禁（2026-09-13，P0-3）----------
# 整轮作废不得返回退出码 0：调用方靠退出码判断"能不能用"，
# 空结果返回 0 会让下游把不存在的结果当成成功产物继续流转。
if not result.get("楼栋"):
    log.error("本次运行未产出任何楼栋覆盖结果（作业表 %d 条，成品 0 栋）—— "
              "**已按失败退出（码 2）**，请勿把本结果当作成功产物使用。"
              "常见原因：① --title-pattern 与图上标题写法不符；"
              "② --text-layer 未覆盖标题图层；③ --fx-pattern 未匹配到任何分纤箱。",
              len(bldg_jobs))
    sys.exit(2)

# ---------- 9c. 结果状态契约（L1-C8）产出方落地（2026-09-18）----------
# 两个维度正交，只**登记**、不改动任何数值与归属：
#   origin：安装层与覆盖层均由竖干断口 + 区间法对位**推算** ⇒ derived；
#           覆盖为空 / 无安装层 ⇒ unresolved。
#   confirmation：本单元出现在「需人工裁决」中 ⇒ pending（待裁决，禁止进成品，
#           由 inspect C9 拦下）；否则 settled。与 parse 侧「有客观依据即可定案」一致。
# 此前本脚本从不产出这两字段 ⇒ C9 对本来源恒判「已提供但零字段」，这一半产物没核。
_pend_objs = [str(_x.get("对象", "")) for _x in (result.get("需人工裁决") or [])]
_st_settled = _st_pending = 0
for _bk, _bv in (result.get("楼栋") or {}).items():
    for _uk, _uv in ((_bv or {}).get("单元") or {}).items():
        _unit_pend = any((_bk in _o and _uk in _o) for _o in _pend_objs)
        for _bx in (_uv.get("分纤箱") or []):
            _cov = (_bx.get("覆盖范围线索") or {}).get("覆盖楼层") or []
            _bx["result_origin"] = "derived" if (_cov and _bx.get("安装楼层")) else "unresolved"
            _bx["result_confirmation"] = ("pending"
                                          if (_unit_pend or _bx["result_origin"] == "unresolved")
                                          else "settled")
            _src = str(_bx.get("依据来源") or "")
            if not _src.startswith("E-DXF-"):
                _bx["依据来源"] = "E-DXF-GEOM:" + _src
            if _bx["result_confirmation"] == "settled":
                _st_settled += 1
            else:
                _st_pending += 1
result["结果状态说明"] = {
    # 键名刻意**不复用** result_origin / result_confirmation：inspect 的 C9 闸门按
    # 「键存在即结果项」机械扫描，说明性文字挂在同名键上会被当成一条已定案结果。
    "origin 取值含义": "measured=图上直读/几何测量；derived=按规则算出（竖干断口+区间法对位）；unresolved=无解",
    "confirmation 取值含义": "settled=可进成品；pending=待裁决、禁止进成品（inspect C9 拦下）",
    "统计": {"settled": _st_settled, "pending": _st_pending},
    "判 pending 的条件": "本单元出现在「需人工裁决」中",
}

try:
    os.makedirs(os.path.dirname(os.path.abspath(OUT)) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
except IOError as e:
    log.error(f"无法写入输出文件: {OUT}\n{e}")
    sys.exit(1)

log.info(f"\n覆盖范围线索分析完成 → {OUT}")