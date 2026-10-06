#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""楼层表引擎（V3 楼层表搬家起步，2026-09-30 一百三十九）。

职责（起步）：
1. 皮线米数标注写法谱（CABLE_FORM_RES + 取值/拼装/检测三函数）——
   与 plan_methods.RE_FIBER_LEN_FORMS 的形态表须一致（镜像铁律②）；
2. 楼层信息分类（parse_floor_info）：单元文字 → 楼层标/箱编号/户数/
   皮线米数/线缆名/其他 六路分流（纯分类，不定案）。

不做的事（硬禁区）：
- 不判定覆盖、不定归属、不写 settled/pending；
- 允许 import ftth_naming（clean_text/is_floor_text）与 ftth_common
  （first_nonnull_group）——二者均为底层归一域，不 import 任何业务阶段
  模块（parse/coverage/inspect），DAG 无回边；
- bug-for-bug：实现自 parse_dxf_structured.py 逐字搬入（含 2026-09-16
  取 x 留痕、乘号支取非空组、米数解析失败可见三处实测坑）；
- 日志不直接打：米数解析失败以 warnings 出口返回，由调用方（parse）
  按原文案打 log（行为逐字一致）。

调用方（parse）保留同名薄包装与 re-export（count_households 注释引用
parse_dxf_structured.CABLE_FORM_RES 组名约定，零改动）。
"""
import re

from ftth_common import compute_bldg_ranges, cluster_by_x, first_nonnull_group
from ftth_naming import clean_text, is_floor_text, unit_num

__all__ = [
    "CABLE_FORM_RES",
    "_cable_pattern_for",
    "_cable_forms_in",
    "_cable_tuple",
    "_is_business_text",
    "parse_floor_info",
    "split_units_no_fx",
    "split_units_by_marker",
    "split_units_by_fx_cluster",
    "synth_unit_marks_by_split",
    "split_units_for_bldg",
]


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
    # 2026-10-04（P0-A1）：建议值会进命令行/配置，`\d` 踩 L1-C7 坑①（反斜杠被吃
    #   → 零命中且 rc=0）。检测侧 CABLE_FORM_RES 保持 `\d` 不动（Python 内部无此坑），
    #   仅在**输出**处统一改写为 `[0-9]`（检测与建议解耦，语义零变化）。
    return r"^(?:" + "|".join(p.replace(r"\d", "[0-9]") for p in parts) + r")$"


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


def parse_floor_info(unit_texts, rx):
    """楼层信息分类（纯分类：六路分流，不定案）。

    Args:
        unit_texts: 单元文字列表（每项含 内容/x/y）。
        rx: 正则束（TITLE_RE 必传；FLOOR_RE/HU_RE/CABLE_RE/FX_RE/CABLE_KW_RE
            可为 None 表示该路未提供——与 parse 现有“未提供即跳过”一致）。

    Returns:
        (floor_marks, fx_list, hu_count, cable_info, cable_names, others,
         warnings)：前六项与 parse 旧实现逐字一致；warnings 为
        [(txt, bad)]（米数匹配上却解析不出，调用方负责可见性日志）。
    """
    floor_marks = {}   # 楼层名(如"1F") -> y
    fx_list = []       # {编号, x, y}
    hu_count = {}      # y -> 户数
    cable_info = {}    # y -> (米数, 根数)
    cable_names = {}   # 文字 -> y
    others = []
    warnings = []
    for t in unit_texts:
        txt = clean_text(t["内容"])
        y = t["y"]
        if is_floor_text(txt, rx.get("FLOOR_RE")):
            floor_marks[txt] = y
            continue
        if rx.get("FX_RE") is not None:
            m = rx["FX_RE"].search(txt)
            if m:
                # 2026-09-16：原实现只留 y（层位）、**丢掉 x** —— 分纤箱「安装位置」因此
                #   只剩楼层、没有平面位置，两个同层同单元的箱无法在几何上区分，也无法与
                #   台账/总图按平面位置对照。x 与编号同源同行文字，直接取用最稳。
                fx_list.append({"编号": m.group(0), "x": t["x"], "y": y})
                continue
        if rx.get("HU_RE") is not None:
            m = rx["HU_RE"].fullmatch(txt)
            if m:
                # 户数直读支持**多形态交替** pattern（`(\\d+)\\s*户|[*×xX]\\s*(\\d+)`，
                #   见 suggested_hu）：命中哪一支决定哪一组有值，故取**第一个非 None 组**，
                #   固定取 group(1) 会静默漏掉乘号那一支。
                _hu_v = first_nonnull_group(m)
                if _hu_v is not None:
                    # 2026-10-02（凤鸣朝阳实测坑）：用户传 `([0-9]+户)` 把"户"也
                    #   捕获进组，int('2户') 崩。防御性清洗：只取连续数字。
                    _hu_digits = re.search(r'[0-9]+', str(_hu_v))
                    if _hu_digits:
                        hu_count[y] = int(_hu_digits.group())
                    else:
                        print("[floor_engine] 警告：户数匹配但无数字可转（_hu_v=%r），跳过" % _hu_v)
                    continue
        if rx.get("CABLE_RE") is not None:
            m = rx["CABLE_RE"].fullmatch(txt)
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
                    warnings.append((txt, _bad))
                continue
        if rx["TITLE_RE"].search(txt):
            continue
        if rx.get("CABLE_KW_RE") is not None and rx["CABLE_KW_RE"].search(txt):
            # P1-14 修正：排除图框标题（含换行符或过长的文字）和已被 TITLE_RE 匹配的标题
            if '\n' in txt or len(txt) > 40:
                continue
            cable_names[txt] = y
            continue
        others.append((txt, y))
    return floor_marks, fx_list, hu_count, cable_info, cable_names, others, warnings


# ---------- 分单元（优先用单元标注锚点，其次 fx 聚类） ----------
# 自 parse_dxf_structured.py 逐字搬入（V3 楼层表搬家一百四十）：
# - 日志与 PENDING_NOTES 由调用方（parse）按返回事件执行，本层只计算；
# - _UNIT_SPLIT_SRC/SYNTH_UNIT_MARKS 仍由调用方持有，本层返回 kind/records。

def split_units_no_fx(bldg_text_list):
    """无 fx 文字时，全部文字归入'全部'单元。"""
    return {"全部": bldg_text_list}


def _is_business_text(content, rx):
    """退役条件：当 attribution_engine 的归一化前置过滤覆盖此逻辑后可删除。

    保守判断「与 FTTH 入户规模直接相关的文字」（共享列克隆准入）：
      ① 楼层标注（is_floor_text：FLOOR_RE 或 F/层/B/WF 等内置写法）；
      ② 单元标注（含「单元」关键词，或命中 UNIT_RE）；
      ③ 楼栋标题（同时含「#/＃/楼」与「系统图/布线图/示意图」）。
    三类之外的全部文字 → 非业务文字（公司名/地块名/多栋合并楼名等），不克隆。
    判断必须保守：拿不准的（含空文字、判据异常）一律返回 True（克隆，
    保持当前行为），绝不丢数。
    """
    c = clean_text(content or "")
    if not c:
        return True
    try:
        if is_floor_text(c, (rx or {}).get("FLOOR_RE")):
            return True
    except Exception:                                      # noqa: BLE001
        return True
    if "单元" in c:
        return True
    _ure = (rx or {}).get("UNIT_RE")
    if _ure is not None:
        try:
            if _ure.search(content or ""):
                return True
        except Exception:                                  # noqa: BLE001
            return True
    if ("#" in c or "＃" in c or "楼" in c) and (
            "系统图" in c or "布线图" in c or "示意图" in c):
        return True
    return False


def split_units_by_marker(bldg_text_list, unit_marks, rx, bldg_name=None,
                          clone_shared_hu=False):
    """有单元标注时，以单元标注 x 为锚点中分。

    2026-10-05（一百五十九）新增 `clone_shared_hu`（**默认 False**，行为不变）：
      落在全部单元 x 范围之外的户数列，此前一律「挂最近单元」（见下方 orphans 处置），
      于是多单元楼只有**一个单元**拿到户数，其余单元整单元为空 —— 实测柳辛庄某带
      图签 165 户 / 直读 105 户，差的正好是一整个单元；云峰更达 14 个单元整单元缺失。
      是否该克隆属**归属裁定**，本函数不代判：默认维持原行为并登记交人；人工据第二
      来源（图签「层数×每层户数×单元数」）确认后，可用本开关让共用轴户数列进每个
      单元。克隆只作用于**户数**，箱编号/皮线米数仍不克隆（那些克隆必重复计数）。

    2026-09-12 修正（P0-2）：
      1. 单元名重名时报错退出，不再静默覆盖（旧实现 dict key 覆盖导致 1#楼只剩 2 个假单元）。
      2. 若 bldg_name 提供，校验单元标注与楼栋同号（如「2#楼」只认「2#楼N单元」），
         避免总图区的「N#楼M单元」被误归给不相关楼栋。

    2026-09-19 补「共享列」：单元锚点 x 只圈住**单元块**，而一栋一张系统图时
      **楼层轴只画一根**、且常画在各单元块之外——按锚点中分会让这条共用轴落在
      所有单元范围之外，结果是**每个单元的楼层表都为空**。处置（有客观判据，
      属测量非推理）：落在所有单元范围之外、且**不是**单元专属实体（箱编号 /
      皮线米数 / 户数）的文字，判为该图共用图元 → **克隆进每个单元**；
      单元专属实体若落空则不克隆（会重复计数），改挂最近的单元。

    Returns:
        (result, shared, orphans)：result 为 {单元名: [text]}（已含共享克隆与
        落空挂入）；shared 为 None 或 {bldg, count, n_units, samples,
        filtered_samples}（filtered_samples 为被过滤的非业务文字样例，
        不计入 count；调用方打 info + [单元共享列·过滤]）；orphans 为落空的单元专属文字列表（调用方告警+登记）。
        重名单元的旧“warning 并仅保留首次”语义保留，dup_names 一并返回。
    """
    UNIT_RE = rx.get("UNIT_RE")
    units = []
    seen_names = set()
    dup_names = []
    for t in sorted(unit_marks, key=lambda t: t["x"]):
        # 2026-09-27（T5 根因修复）：UNIT_RE 可能为 None —— 分离形态合成锚点
        #   （synth_unit_marks_by_split）的内容是 `N单元`，取号走 unit_num，
        #   不依赖 UNIT_RE；这里补 None 保护，避免合成路径裸崩。
        m = UNIT_RE.search(t["内容"]) if UNIT_RE else None
        # 单元键**统一归一为 ASCII `N单元`**（2026-09-19）：图上系统图单元轴写 `一单元`、
        #   图签/对照表写 `1单元`，两者是同一对象；若原样保留 `一单元`，
        #   下游 assemble/gen 的 norm_unit（产出 `N单元`）与本键对不上，join 静默失败。
        #   归一走 ftth_common.unit_num（中文数字 → int），取不到号时保留原文不编造。
        _n = unit_num(t["内容"])
        if _n is not None:
            uname = "%d单元" % _n
        elif m:
            uname = m.group(1) + "单元"
        else:
            uname = t["内容"]
        # P0-2 修正③：重名单元报错，不静默覆盖
        if uname in seen_names:
            dup_names.append((uname, t["内容"]))
            continue
        seen_names.add(uname)
        units.append({"x": t["x"], "名": uname})
    result = {}
    unit_anchors = [(u["名"], u["x"]) for u in units]
    if not unit_anchors:
        return result, None, [], dup_names
    unit_ranges = compute_bldg_ranges(unit_anchors)
    for u in units:
        xlo, xhi = unit_ranges[u["名"]]
        result[u["名"]] = [t for t in bldg_text_list if xlo <= t["x"] < xhi]

    # ---- 共享列补齐（见 docstring） ----
    _covered = set()
    for _lst in result.values():
        for _t in _lst:
            _covered.add(id(_t))
    _left = [t for t in bldg_text_list if id(t) not in _covered]
    shared = None
    orphans = []
    if _left:
        def _is_unit_specific(c):
            """单元专属实体：箱编号 / 皮线米数 / 户数 —— 克隆会给每个单元重复计数。"""
            c = c or ""
            if rx.get("FX_RE") and rx["FX_RE"].search(c):
                return True
            if rx.get("HU_RE") and rx["HU_RE"].fullmatch(clean_text(c)):
                return True
            if rx.get("CABLE_RE") and rx["CABLE_RE"].fullmatch(clean_text(c)):
                return True
            return False

        _shared = [t for t in _left
                   if not _is_unit_specific(t.get("内容"))
                   and _is_business_text(t.get("内容"), rx)]
        orphans = [t for t in _left if _is_unit_specific(t.get("内容"))]
        # 非业务文字（公司名/地块名/多栋合并楼名等）：不克隆，只落痕供调试，
        #   不计入 count（调用方打 [单元共享列·过滤] 日志）。
        _filtered = [t for t in _left
                     if not _is_unit_specific(t.get("内容"))
                     and not _is_business_text(t.get("内容"), rx)]
        if _shared:
            for _k in result:
                result[_k].extend(_shared)
            shared = {"bldg": bldg_name or "?",
                      "count": len(_shared),
                      "n_units": len(result),
                      "samples": sorted({(t.get("内容") or "")[:10] for t in _shared})[:8],
                      "filtered_count": len(_filtered),
                      "filtered_samples": sorted(
                          {(t.get("内容") or "")[:14] for t in _filtered})[:8]}
        elif _filtered:
            # 共享列整体无业务文字时仍落痕（调用方可据此打过滤日志）
            shared = {"bldg": bldg_name or "?",
                      "count": 0,
                      "n_units": len(result),
                      "samples": [],
                      "filtered_count": len(_filtered),
                      "filtered_samples": sorted(
                          {(t.get("内容") or "")[:14] for t in _filtered})[:8]}
        # 2026-10-05（一百五十九）：户数落空的两条处置路（见 docstring）。
        #   `clone_shared_hu=True` ⇒ 克隆进每个单元（人工据第二来源确认后的路径）；
        #   默认 False ⇒ 维持「挂最近单元」并登记交人（原行为，未裁决值不进成品）。
        _hu_orphans = [t for t in orphans
                       if rx.get("HU_RE") and rx["HU_RE"].fullmatch(
                           clean_text(t.get("内容")))]
        for _t in orphans:
            if clone_shared_hu and _t in _hu_orphans:
                for _k in result:
                    result[_k].append(_t)
                continue
            _best = min(units, key=lambda u: abs(u["x"] - _t["x"]))
            result[_best["名"]].append(_t)
        if clone_shared_hu and _hu_orphans:
            shared = dict(shared or {}, bldg=bldg_name or "?",
                          cloned_hu=len(_hu_orphans), n_units=len(result))
    return result, shared, orphans, dup_names


def split_units_by_fx_cluster(fx_texts, bldg_text_list, unit_cluster, unit_range):
    """无单元标注时，用 fx 聚类分单元。"""
    fx_clusters = cluster_by_x(fx_texts, unit_cluster)
    result = {}
    for i, c in enumerate(fx_clusters):
        cx = c["x"]
        if i == 0:
            xlo = cx - unit_range
        else:
            xlo = max((fx_clusters[i - 1]["x"] + cx) / 2, cx - unit_range)
        if i == len(fx_clusters) - 1:
            xhi = cx + unit_range
        else:
            xhi = min((cx + fx_clusters[i + 1]["x"]) / 2, cx + unit_range)
        uname = f"单元{i+1}"
        result[uname] = [t for t in bldg_text_list if xlo <= t["x"] < xhi]
    return result


def synth_unit_marks_by_split(all_texts, keyword, rx, bldg_name="", x_range=None,
                              floor_texts=None, unit_cluster=None, y_tol=None):
    r"""分离形态单元轴合成（2026-09-27 T5 根因修复）。

    形态：单元轴标注 = 两个独立文字实体 —— 纯数字（`1`/`2`）+ 含关键词的纯文字
    （如 `单元电井`），数字在文字左侧近旁、同 y。任何单实体正则（`(\d+)单元`）
    都匹配不到，导致图上明明有单元轴、parse 却判「无单元轴标注」→ 箱并回楼栋
    级容器、单元级整批丢失（实测云峰项目 2#/3#/6#/9# 楼，四栋八单元全丢）。

    判据（全部满足才合成）：
      ① 关键词文字：含 keyword 且不含任何数字 —— `1#楼1单元` 一类完整形态
         自带数字，天然排除，不走本路；
      ② 候选从**全局文字**取（不只本楼 bldg_texts —— x 区间重叠的楼栋会把
         标注错配给邻栋，实测 7#1单元被 11#配套楼抢走、9#2单元被 4#配套抢走，
         只扫本楼会漏）；x 须落在本楼栋 x 区间内；
      ③ y 带校验：锚点 y 须贴近本楼栋**楼层刻度的 y 范围**（±unit_cluster）。
         锚点天然在列顶上方约半层高内；x 重叠但 y 相距一个图区的错配
         （实测 90+ 单位）被本判据排除。本楼无楼层刻度 → 不合成（无从校验，
         宁缺勿错）；
      ④ 数字文字：fullmatch 1~2 位纯数字，在关键词文字左侧近旁、同 y
         （|dy| ≤ y_tol、-unit_cluster/2 ≤ dx < 0；人防图 `防护单元`+右侧
         数字 dx 为正，被本判据天然排除）。
    合成锚点：内容 = `N单元`（归一 ASCII，下游 unit_num 取号与既有路径一致），
    x 取关键词文字 x（标注主体）；逐条登记 SYNTH_UNIT_MARKS 交人工核对。

    Returns:
        (marks, records)：marks 为合成锚点列表；records 为留痕条目列表
        （调用方负责 extend 进 SYNTH_UNIT_MARKS 并打 info 日志）。
    """
    if not keyword or x_range is None:
        return [], []
    xlo, xhi = x_range
    marks = []
    records = []
    # y 带校验基准：本楼栋楼层刻度的 y 范围（区间法刻度列是最稳的图区 y 锚）
    floor_ys = [t["y"] for t in (floor_texts or [])
                if is_floor_text(clean_text(t.get("内容") or ""), rx.get("FLOOR_RE"))]
    if not floor_ys:
        return [], []
    ylo, yhi = min(floor_ys), max(floor_ys)
    tol = unit_cluster
    kw_texts = [t for t in all_texts
                if keyword in (t.get("内容") or "")
                and not re.search(r"\d", t.get("内容") or "")
                and xlo <= t["x"] <= xhi
                and ylo - tol <= t["y"] <= yhi + tol]
    num_texts = [t for t in all_texts
                 if re.fullmatch(r"\d{1,2}", (t.get("内容") or "").strip())]
    for kw in kw_texts:
        best = None
        for n in num_texts:
            dx = n["x"] - kw["x"]
            dy = n["y"] - kw["y"]
            if abs(dy) <= y_tol and -unit_cluster / 2.0 <= dx < 0:
                if best is None or abs(dx) < abs(best[1]["x"] - kw["x"]):
                    best = (n, dx)
        if best is None:
            continue
        n, dx = best
        _no = int(n["内容"].strip())
        marks.append({"内容": "%d单元" % _no, "x": kw["x"], "y": kw["y"],
                      "合成": True, "数字实体": n["内容"].strip(), "关键词实体": kw["内容"],
                      "数字dx": round(dx, 2)})
        records.append({"楼栋": bldg_name, "单元号": _no, "x": kw["x"], "y": kw["y"],
                        "数字实体": n["内容"].strip(), "关键词实体": kw["内容"],
                        "数字dx": round(dx, 2)})
    return marks, records


def split_units_for_bldg(bldg, bldg_texts, bldg_ranges, texts, rx,
                         unit_split_keyword=None, unit_cluster=None, unit_range=None,
                         y_tol=None, clone_shared_hu=False):
    """单楼栋单元划分编排（原 split_units 调度逻辑；计算在此，kind 由调用方落盘）。

    Returns:
        (units, kind, events)：kind ∈ marker/no_fx/fx_cluster；events 含
        shared/orphans/dup_names/synth_marks/synth_records（调用方负责日志、
        PENDING_NOTES 登记与 SYNTH_UNIT_MARKS 落盘）。
    """
    # 记录本次划分**来自哪一路**（2026-09-19）：只有 `marker` 一路是图上真实存在的
    #   单元轴标注；`fx_cluster` 是兜底合成名（`单元1/单元2`），其编号与图上「N单元」
    #   无对应关系。把箱按单元号归位时**只允许**认 `marker` 一路，否则会拿合成编号
    #   去冒充图上单元号（一次静默错挂）。
    # 判「走哪一路」只看**图上有没有单元轴标注**，不再先看有没有 FX 文字。
    #   病灶（实测）：本类图纸的箱编号文字全部落在楼栋 x 区间之外（在独立的箱位直读/
    #   箱表区），`--bldg-map` / 直写自证又会把这些文字**从 bldg_texts 里摘走**；
    #   于是 `fx_texts` 恒为空 ⇒ 永远走 `split_units_no_fx` ⇒ 全部楼层挤进「楼栋名」一个
    #   容器 ⇒ **单元划分整批丢失**（图上明明有一单元/二单元两根轴）。
    #   楼层表按「层归属单元」组织是图纸信息模型的固有要求，与有没有 FX 文字无关。
    fx_texts = [t for t in bldg_texts[bldg] if rx.get("FX_RE") and rx["FX_RE"].search(t["内容"])]
    unit_marks = [t for t in bldg_texts[bldg] if rx.get("UNIT_RE") and rx["UNIT_RE"].search(t["内容"])]
    # 2026-09-27（T5 根因修复）：单实体正则匹配不到时，尝试分离形态合成
    #   （数字+关键词两实体）。合成锚点同属图上真实标注（marker 一路），
    #   与完整形态互斥：UNIT_RE 命中时不用合成，避免两路混杂。
    synth_marks, synth_records = [], []
    if not unit_marks and unit_split_keyword:
        synth_marks, synth_records = synth_unit_marks_by_split(
            texts, unit_split_keyword, rx, bldg_name=bldg,
            x_range=bldg_ranges.get(bldg), floor_texts=bldg_texts[bldg],
            unit_cluster=unit_cluster, y_tol=y_tol)
        if synth_marks:
            unit_marks = synth_marks
    if unit_marks:
        units, shared, orphans, dup_names = split_units_by_marker(
            bldg_texts[bldg], unit_marks, rx, bldg_name=bldg,
            clone_shared_hu=clone_shared_hu)
        return units, "marker", {"shared": shared, "orphans": orphans,
                                 "dup_names": dup_names,
                                 "synth_marks": synth_marks,
                                 "synth_records": synth_records}
    if not fx_texts:
        return split_units_no_fx(bldg_texts[bldg]), "no_fx", {"shared": None,
               "orphans": [], "dup_names": [], "synth_marks": [],
               "synth_records": synth_records}
    return split_units_by_fx_cluster(
        fx_texts, bldg_texts[bldg], unit_cluster,
        unit_range), "fx_cluster", {"shared": None, "orphans": [],
               "dup_names": [], "synth_marks": [], "synth_records": synth_records}

