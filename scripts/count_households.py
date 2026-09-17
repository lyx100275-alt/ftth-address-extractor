#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTTH 户数统计脚本（通用版）
统计 DXF 中"1芯皮线光纤"类文字标注的数量，按 1条皮线=1户 的规则估算每层户数。

背景：部分图纸不写"X户"，而是用"1芯皮线光纤"逐条标注每户的入户皮线。
此时每层户数 = 归属该层的皮线文字条数。此规则需用户确认适用性。

用法：
    python count_households.py <输入DXF> [输出JSON] [选项]

示例：
    python count_households.py 图纸.dxf out.json --text-layer 0,智-文字,智-楼层线,DIM-通讯
    python count_households.py 图纸.dxf --probe          # 探查文字/楼层/皮线样例

关键参数（换新图纸前务必用 --probe 确认实际格式再传参）：
    --text-layer       文字所在图层，逗号分隔（必填，由探查提供）
    --title-pattern    楼栋标题正则，需含捕获组数字（必填，由探查提供）
    --floor-pattern    楼层标注正则（缺省=内置统一解析，支持 3F/17F/-1F/B1/B2/WF）
    --fiber-pattern    皮线文字正则（必填，由探查采样后提供；用 fullmatch 全词匹配）
    --special-pattern  特殊楼层正则（默认 "^WF$"，仅屋面层不参与归属；地下层可能有住户，不排除）
    --assign           归属规则（已废弃，保留兼容）：区间法自动判断，此参数不再影响结果
    --match-tol        皮线归属楼层的y容差（缺省=按 1.0 倍层高自适应，层高由楼层标注实测）
    --x-cluster        皮线按x聚簇的阈值（缺省=按 2/3 倍层高自适应）
    --x-y-gap         同层两户皮线的y间距参考（缺省=按 0.2 倍层高自适应；仅参考不参与判定）

说明：
- 输出为"线索"：皮线归属楼层采用 y 坐标关联（口径B），需用户对照图纸原图复核，不作为结论。
- 每条皮线归属到"所在楼层区间带"对应的楼层——按 y 坐标排序楼层线，
  相邻两条楼层线之间的区域即为该层的归属区间（区间法，详见 measurement_methods.md §3.5）。
  落在最低楼层线以下的皮线不归属任何楼层，标为"未归属"。
- 特殊楼层（WF/B1等）不参与归属，但其存在会打印出来供参考。
- 若图中根本没有皮线类文字（如用"X户"直读），会提示改用 parse_dxf_structured.py 的 --hu-pattern。
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

from ftth_common import (
    DEFAULT_MATCH_TOL, DEFAULT_X_CLUSTER, DEFAULT_X_Y_GAP,
    setup_logger, bldg_num, floor_num_or_zero,
    load_dxf, collect_texts, find_bldg_anchors,
    cluster_by_x, compute_bldg_ranges, compute_bldg_ranges_banded, match_y_to_floor,
    assign_floor_by_interval, parse_floor_label,
    clean_text, is_floor_text, require_params,
    floor_step_from_texts, set_expand_bldg_ranges, validate_scale_anchor,
    floor_mark_conflicts,
)

log = setup_logger("count_households")

# ---------- 参数 ----------
ap = argparse.ArgumentParser(description="FTTH 户数统计（皮线计数，输出线索需用户裁决）")
ap.add_argument("--expand-bldg-ranges", action="store_true",
                help="楼栋区间标题（如 `1-3号楼`）按**区间**语义展开为 1,2,3。\n"
                     "默认不展开（只取字面数字并 WARNING 待裁决）——连字符写法\n"
                     "既可能是并列也可能是区间，**须用户确认语义后**才可开启，\n"
                     "不得替用户静默选定语义。")
ap.add_argument("dxf", help="输入DXF文件路径")
ap.add_argument("out", nargs="?", default=None, help="输出JSON路径（默认DXF同目录 _户数统计.json）")
ap.add_argument("--text-layer", default=None, help="文字所在图层，逗号分隔（必填，由探查提供）")
ap.add_argument("--text-type", default="MTEXT,TEXT", help="文字实体类型，逗号分隔")
ap.add_argument("--title-pattern", default=None, help="楼栋标题正则，含捕获组数字（必填，由探查提供）")
ap.add_argument("--floor-pattern", default=None, help="楼层标注正则。默认 None＝内置统一解析（支持 3F/17F/-1F/B1/B2/WF）")
ap.add_argument("--fiber-pattern", default=None, help="皮线文字正则（必填，由探查采样后提供；用 fullmatch）")
ap.add_argument("--special-pattern", default=r"^WF$", help="特殊楼层正则（默认^WF$，即仅屋面层不参与楼层归属；本项为通用约定，非项目参数）。"
                 "2026-09-11 修正：旧默认 ^WF$|^B\\d*$ 会把 B1/B2 一并排除，导致地下一层住户全部消失"
                 "（实测教训：地下层确实可能有住户，不能一律排除）")
ap.add_argument("--assign", default="abs", choices=["abs", "up", "down"], help="皮线归属规则（默认abs）")
ap.add_argument("--match-tol", type=float, default=None, help="皮线归属楼层的y容差（None=按 1.0 倍层高自适应，层高由楼层标注实测）")
ap.add_argument("--x-cluster", type=float, default=None, help="皮线按x聚簇的阈值（None=按 2/3 倍层高自适应）")
ap.add_argument("--x-y-gap", type=float, default=None, help="同层两户皮线的y间距参考，仅参考不参与判定（None=按 0.2 倍层高自适应）")
ap.add_argument("--title-band-tol", type=float, default=0.0,
                help="楼栋标题按 y 分带的容差（0=按 2 倍层高自适应）。"
                     "配套楼系统图常与住宅楼系统图上下分带、x 上互相重叠；"
                     "跨带统一做 x 中分会把甲带的皮线列切给乙带"
                     "（实测某图 7# 皮线列被切给 11# 配套）。带内中分即可消除该串扰。")
ap.add_argument("--max-unmatched-ratio", type=float, default=0.5,
                help="未归属皮线占比超过本值即判失败（rc≠0），默认 0.5；0=关闭该守门。"
                     "防止「尺度锚污染 → 全部未归属 → 仍 rc=0 写出空结果」的静默错误。")
ap.add_argument("--allow-lossy", action="store_true",
                help="允许在守门失败（有皮线但无楼层标注 / 全部未归属 / 未归属超阈）时"
                     "仍写出 JSON。默认关闭：**静默的错误数据不如失败**。")
ap.add_argument("--probe", action="store_true", help="探查模式：打印文字/楼层/皮线样例，不解析")
args = ap.parse_args()
# 楼栋区间标题语义（`1-3号楼` = 并列 还是 区间？）由用户裁定后经本开关启用，
# 不设默认开启——替用户静默选定语义会丢/多解楼栋。
set_expand_bldg_ranges(getattr(args, "expand_bldg_ranges", False))

DXF_PATH = args.dxf
OUT = args.out or (os.path.splitext(DXF_PATH)[0] + "_户数统计.json")

if not args.probe:
    require_params([
        ("--text-layer", args.text_layer, "含FTTH标注的文字图层（探查图层清单+采样后确定）"),
        ("--title-pattern", args.title_pattern, "楼栋标题正则，需含组1=楼栋号"),
        ("--fiber-pattern", args.fiber_pattern, "皮线文字正则（用 fullmatch；由探查采样后提供）"),
    ], "count_households")

LAYERS = [x.strip() for x in (args.text_layer or "").split(",") if x.strip()]
TYPES = [x.strip().upper() for x in args.text_type.split(",") if x.strip()]
TITLE_RE = re.compile(args.title_pattern) if args.title_pattern else None
FLOOR_RE = re.compile(args.floor_pattern) if args.floor_pattern else None
FIBER_RE = re.compile(args.fiber_pattern) if args.fiber_pattern else None
SPECIAL_RE = re.compile(args.special_pattern) if args.special_pattern else None


def _clean(s):
    """统一文字清洗（走 ftth_common.clean_text）。"""
    return clean_text(s)


def _is_floor_text(s):
    """楼层标注判定：统一走 ftth_common.is_floor_text（支持 3F / 17F / -1F / B1 / B2 / WF）。

    显式传了 --floor-pattern 时额外兼容该正则。
    """
    return is_floor_text(s, FLOOR_RE)

doc, msp = load_dxf(DXF_PATH, log)

# ---------- 收集文字 ----------
texts = collect_texts(msp, LAYERS, TYPES)

# ---------- 探查模式 ----------
if args.probe:
    log.info("== 文字图层统计 ==")
    cnt = Counter((t["层"], t["类型"]) for t in texts)
    for (lay, typ), n in cnt.most_common():
        log.info(f"  {lay} {typ}: {n}")
    log.info("\n== 楼层标注（--floor-pattern 匹配）样例 ==")
    shown = 0
    for t in texts:
        if _is_floor_text(t["内容"]):
            tag = "【特殊楼层】" if SPECIAL_RE.match(_clean(t["内容"])) else ""
            log.info(f"  {t['内容']!r} @ ({t['x']:.1f},{t['y']:.1f}) {tag}")
            shown += 1
            if shown >= 30:
                break
    log.info(f"\n== 皮线文字（--fiber-pattern 匹配）前40条 ==")
    shown = 0
    for t in texts:
        if FIBER_RE.fullmatch(t["内容"]):
            log.info(f"  {t['内容']!r} @ ({t['x']:.1f},{t['y']:.1f}) [{t['层']}]")
            shown += 1
            if shown >= 40:
                break
    log.info("\n（提示：若皮线文字格式不同，用 --fiber-pattern 指定；")
    log.info("  若楼栋标题不是 'X#楼…示意图'，用 --title-pattern 指定；")
    log.info("  若楼层/特殊楼层格式不同，用 --floor-pattern / --special-pattern 指定。）")
    sys.exit(0)

# ---------- 楼栋锚点 ----------
bldg_anchors = find_bldg_anchors(texts, TITLE_RE)

if not bldg_anchors:
    log.error("未匹配到楼栋标题，请检查 --title-pattern / --text-layer，或先运行 --probe")
    sys.exit(1)

# ---------- 尺度锚：阈值按层高自适应（2026-09-15 通用化，须在首次使用 args.* 前解析） ----------
# 比值的历史出处：层高 30 时 match_tol=30 / x_cluster=20 / x_y_gap=6（原手调默认值）。
# 层高量测自带抗污染（每列一票、跨列取主簇），量不出时回退绝对默认值并告警。
_TOL_RATIOS = {"match_tol": 1.0, "x_cluster": 2.0 / 3.0, "x_y_gap": 0.2}
_TOL_FALLBACK = {"match_tol": DEFAULT_MATCH_TOL, "x_cluster": DEFAULT_X_CLUSTER,
                 "x_y_gap": DEFAULT_X_Y_GAP}
_step, _basis = floor_step_from_texts(texts, _is_floor_text)
# 2026-09-16（P0-2）：尺度锚**可信性**校验 —— "量出 step" 不等于 "量对 step"。
#   实测某图楼层标注被污染后量出 step=1.6（还不到一个字高），
#   随后全部皮线判"未归属"，脚本仍 rc=0 照写 JSON。故此处先校验再用。
_anchor_fail = None
if _step:
    _ok, _why = validate_scale_anchor(_step, texts)
    if not _ok:
        _anchor_fail = "尺度锚校验未通过：%s" % _why
        log.error("%s → 本次**不采用**该层高，改用绝对默认值", _anchor_fail)
        _step = None
if _step:
    for _n, _r in _TOL_RATIOS.items():
        if not getattr(args, _n):        # None / 0 均视为自适应（与 analyze_coverage 的 0=auto 约定一致）
            setattr(args, _n, _r * _step)
    log.info("尺度锚：层高 %.4g（%s）→ match_tol=%.4g / x_cluster=%.4g / x_y_gap=%.4g"
             % (_step, _basis, args.match_tol, args.x_cluster, args.x_y_gap))
else:
    for _n, _d in _TOL_FALLBACK.items():
        if getattr(args, _n) is None:
            setattr(args, _n, _d)
    log.warning("尺度锚量测失败（%s）→ 回退绝对默认值 %s", _basis,
                {k: getattr(args, k) for k in _TOL_FALLBACK})

# ---------- 楼栋 x 范围：**按 y 分带后再中分**（2026-09-15 分带能力同步） ----------
# 跨带统一做 x 中分，会把甲带的标题当成乙带的分界 —— 实测某图 7# 的皮线列
# 被切给了 11# 配套（配套小图与主图 x 上重叠）。带内中分即可消除该串扰。
_band_tol = args.title_band_tol or (2.0 * _step if _step else None)
if _band_tol:
    log.info("楼栋标题分带容差 = %.4g（%s）"
             % (_band_tol, "--title-band-tol" if args.title_band_tol else "2 倍层高自适应"))
else:
    log.warning("分带容差不可得（既未量出层高也未传 --title-band-tol）→ 退回单带 x 中分；"
                "若图上有配套楼/住宅楼上下分带，可能串带，请显式传 --title-band-tol")
bldg_ranges, _bands = compute_bldg_ranges_banded(
    [(k, v["x"], v.get("y")) for k, v in bldg_anchors.items()], band_tol=_band_tol, log=log)

bldg_texts = defaultdict(list)
for t in texts:
    for bldg, (xmin, xmax) in bldg_ranges.items():
        if xmin <= t["x"] <= xmax:
            bldg_texts[bldg].append(t)
            break


result = {
    "DXF文件": os.path.basename(DXF_PATH),
    "DXF版本": doc.dxfversion,
    "说明": "户数=皮线条数（1条1芯皮线光纤=1户），需用户确认规则适用；皮线归属为口径B(y坐标关联)，需对照图纸原图复核；"
            "户数以系统图为准（2026-09-13 裁定：不再读取楼层平面图）",
    "参数": {
        "text_layer": LAYERS,
        "text_type": TYPES,
        "title_pattern": args.title_pattern,
        "floor_pattern": args.floor_pattern,
        "fiber_pattern": args.fiber_pattern,
        "special_pattern": args.special_pattern,
        "assign": args.assign,
        "match_tol": args.match_tol,
        "x_cluster": args.x_cluster,
    },
    "楼栋": {},
}

for bldg in sorted(bldg_ranges.keys(), key=lambda x: bldg_num(x)):
    bldg_txt = bldg_texts[bldg]
    # 楼层标注与特殊楼层
    floor_marks = {}
    special_floors = {}
    # 原始标注列表（**未去重**，专供 floor_mark_conflicts 做自洽性检查）：
    # floor_marks 是字典，同名多址会被静默覆盖成一条，检查必须看原始列表。
    _floor_raw = []
    for t in bldg_txt:
        txt = clean_text(t["内容"])
        if _is_floor_text(txt):
            if SPECIAL_RE is not None and SPECIAL_RE.match(txt):
                special_floors[txt] = t["y"]
            else:
                floor_marks[txt] = t["y"]
                _floor_raw.append((txt, t["y"]))
    # 楼层标注自洽性（2026-09-16，TeleAgent 复盘 P0-4）：
    # 同形的非楼层文字（如路由图上的端口标号 B1~B9）会与 B<数字> 楼层写法撞形，
    # 被并进 floor_marks 后**静默**污染区间法归属。此处只报不拦——本脚本输出
    # 定位是"线索非结论"，拦死会误伤正常图；冲突项写入自检交人工裁决。
    _fl_conflicts = floor_mark_conflicts(_floor_raw)
    # 皮线
    fibers = [t for t in bldg_txt if FIBER_RE.fullmatch(clean_text(t["内容"]))]

    # 同坐标重复绘制去重（2026-09-16）。纪律：同一图层上的同一个字被整条重复绘制
    # （典型是"某层两条皮线各画两遍"）时，文字法会**静默虚增**户数，与图标法对不上，
    # 而下游无法从结果里看出是重复绘制还是真有那么多条。去重键取 (x, y, 内容)——
    # 只有三者全同才判重复（不同层同名文字 y 必然不同，不会误合并）。
    # 重复条数写入结果供核对，不静默丢弃。
    _seen_fiber, _dedup_fibers, _dup_n = set(), [], 0
    for _t in fibers:
        _k = (round(_t["x"], 3), round(_t["y"], 3), clean_text(_t["内容"]))
        if _k in _seen_fiber:
            _dup_n += 1
            continue
        _seen_fiber.add(_k)
        _dedup_fibers.append(_t)
    fibers = _dedup_fibers

    # 皮线按 x 聚簇成列（调用公共函数）
    columns = cluster_by_x(fibers, args.x_cluster)

    # 准备楼层标注列表供二分查找
    floor_items = [(fl, fy) for fl, fy in floor_marks.items()]

    # 每层皮线条数
    floor_hu = {}   # 楼层名 -> 皮线条数
    match_details = []   # 每条皮线的归属记录
    unmatched = []
    if floor_marks:
        # 区间法：统一调用 ftth_common.assign_floor_by_interval
        for t in sorted(fibers, key=lambda t: t["y"]):
            y = t["y"]
            fl_name, dist = assign_floor_by_interval(y, floor_items, tol=args.match_tol)
            if fl_name is None:
                unmatched.append({"y": y, "x": t["x"], "最近楼层": None, "距离": dist})
                continue
            floor_hu[fl_name] = floor_hu.get(fl_name, 0) + 1
            match_details.append({"y": y, "x": t["x"], "归属": fl_name, "距离": dist})

    # 列统计
    col_stats = []
    for c in columns:
        ys = sorted(m["y"] for m in c["members"])
        col_stats.append({
            "x": round(c["x"], 1),
            "条数": len(c["members"]),
            "y_min": ys[0],
            "y_max": ys[-1],
        })

    _srt = lambda kv: floor_num_or_zero(kv[0], args.floor_pattern, use_fullmatch=True)

    result["楼栋"][bldg] = {
        "标题": bldg_anchors[bldg]["内容"],
        "楼层标注": {k: v for k, v in sorted(floor_marks.items(), key=_srt)},
        # 楼层标注自洽性冲突（同名多址 / 次序倒挂）；空列表 = 未发现。见 floor_mark_conflicts
        "楼层标注冲突": _fl_conflicts,
        "特殊楼层": special_floors,
        "皮线列": col_stats,
        # 本栋识别到的皮线总数（=该栋全部皮线字条数）。守门用，
        # 与「各线归属明细+未归属」之和不必然相等——无楼层标注时归属循环不执行。
        "皮线条数": len(fibers),
        # 同坐标重复绘制被去重掉的条数（"皮线条数"已是去重后的真实条数）
        "重复绘制条数": _dup_n,
        "每层户数线索": dict(sorted(floor_hu.items(), key=_srt)),
        "各线归属明细": match_details,
        "未归属皮线": unmatched,
    }
    # 控制台摘要
    log.info(f"\n===== {bldg} =====")
    log.info("  皮线列: " + str([f"x={c['x']} 条数={c['条数']}" for c in col_stats]))
    log.info(f"  每层户数线索: {floor_hu}")
    if unmatched:
        log.info(f"  未归属: {len(unmatched)}条")
    if _dup_n:
        log.info(f"  ! 同坐标重复绘制 {_dup_n} 条已去重（原始 {len(fibers) + _dup_n} 条）")
    if special_floors:
        log.info(f"  特殊楼层(不参与归属): {list(special_floors.keys())}")
    if _fl_conflicts:
        log.warning("  ! 楼层标注自洽性冲突 %d 条（该栋归属可能被同形非楼层文字污染）："
                    % len(_fl_conflicts))
        for _c in _fl_conflicts:
            log.warning("  !   · %s" % _c)

# ---------- 出表守门（2026-09-16，TeleAgent 复盘 P0-2） ----------
# 纪律：「静默的错误数据不如失败」。旧实现在"尺度锚被污染 → 全部皮线未归属"
# 或"整栋没有楼层标注 → 归属循环根本没执行"时，只打一行 log.info，
# **退出码仍是 0、JSON 照常写出** —— 下游拿到一份看起来正常的空结果。
# 现改为：命中任一守门 → rc≠0（须显式 --allow-lossy 才放行）。
_tot_fiber = sum(v.get("皮线条数", 0) for v in result["楼栋"].values())
_tot_un = sum(len(v["未归属皮线"]) for v in result["楼栋"].values())
_tot_asg = sum(len(v["各线归属明细"]) for v in result["楼栋"].values())
_tot_dup = sum(v.get("重复绘制条数", 0) for v in result["楼栋"].values())
_no_floor = [b for b, v in result["楼栋"].items()
             if v.get("皮线条数") and not v["楼层标注"]]
_gate = []
_soft = []          # 有损但不阻断：写 JSON、rc=0，但自检里显式标记
if _anchor_fail:
    # 符合复盘要求：**层高量测异常时 rc≠0**。自适应阈值全部失效后，
    # 回退的绝对默认值只对标定它的那张图成立，结果不可信。
    _gate.append(_anchor_fail)
if _no_floor:
    # 分两级：**全部栋**都没楼层标注 = 口径选错（硬失败）；
    # 仅**部分栋**缺失 = 图纸局部情况（软告警，不阻断其余栋出表）。
    if len(_no_floor) >= len(result["楼栋"]):
        _gate.append("**全部 %d 栋**都有皮线却无楼层标注，归属循环未执行" % len(_no_floor))
    else:
        _soft.append("有皮线但无楼层标注的栋（该栋归属未执行）：%s" % "、".join(sorted(_no_floor)))
if _tot_fiber and _tot_asg == 0:
    _gate.append("全部 %d 条皮线均未归属任何楼层（结果为空）" % _tot_fiber)
elif _tot_fiber and args.max_unmatched_ratio:
    _ratio = _tot_un / _tot_fiber
    if _ratio > args.max_unmatched_ratio:
        _gate.append("未归属占比 %.1f%% 超过阈值 %.1f%%（%d/%d）"
                     % (_ratio * 100, args.max_unmatched_ratio * 100, _tot_un, _tot_fiber))

result["自检"] = {
    "皮线总条数": _tot_fiber,
    "重复绘制条数": _tot_dup,
    # 楼层标注自洽性冲突（同名多址 / 次序倒挂）——非空即"结果可能被同形非楼层文字污染"
    "楼层标注冲突": {b: v["楼层标注冲突"] for b, v in result["楼栋"].items()
                 if v.get("楼层标注冲突")},
    "已归属": _tot_asg,
    "未归属": _tot_un,
    "未归属占比": round(_tot_un / _tot_fiber, 4) if _tot_fiber else None,
    "守门阈值_未归属占比": args.max_unmatched_ratio,
    "尺度锚": _basis,
    "尺度锚校验": _anchor_fail or "通过",
    "楼栋标题分带数": len(_bands),
    "守门": None,   # 下面统一赋值
}
result["自检"]["守门"] = ("通过" if not _gate
                        else ("失败（--allow-lossy 放行）" if args.allow_lossy else "失败"))
result["自检"]["守门明细"] = _gate
result["自检"]["有损告警"] = _soft
if _soft:
    for _s in _soft:
        log.warning("有损（不阻断）：%s", _s)

if _gate and not args.allow_lossy:
    log.error("")
    log.error("!" * 74)
    log.error("! 出表守门**失败**，已中止（未写出 JSON，退出码 1）：")
    for _g in _gate:
        log.error("!   · %s" % _g)
    log.error("! 提示：本结果是线索而非结论；请先修正参数/图纸口径再重跑。")
    log.error("! 确认要保留这份有损结果时，加 --allow-lossy 重跑。")
    log.error("!" * 74)
    sys.exit(1)

try:
    os.makedirs(os.path.dirname(os.path.abspath(OUT)) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
except IOError as e:
    log.error(f"无法写入输出文件: {OUT}\n{e}")
    sys.exit(1)

log.info(f"\n户数统计完成 → {OUT}")
log.info("自检：皮线 %d 条 / 已归属 %d / 未归属 %d（守门=%s）",
         _tot_fiber, _tot_asg, _tot_un, result["自检"]["守门"])
if result["自检"]["楼层标注冲突"]:
    log.warning("自检：%d 栋存在楼层标注自洽性冲突，归属楼层需人工对照原图复核：%s",
                len(result["自检"]["楼层标注冲突"]),
                "、".join(sorted(result["自检"]["楼层标注冲突"])))
log.info("提示: 本结果为线索，皮线条数=户数的规则适用性、及归属楼层，均需用户对照图纸原图确认。")