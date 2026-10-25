#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""覆盖引擎（V3 对称起步，2026-09-30 一百三十六）。

动因（0.130 残留）：parse 侧与 fxmap 已产出「安装楼层统一」（evidence_builder），
coverage 侧零产出 —— C3 按 parse 单边上下文 + legacy 比对，对称建模缺一半。

职责只有一件事（起步最小）：
- V 型谷底安装楼层的统一证据构造（纯构造，不比较、不定案）。

不做的事（硬禁区）：
- 不判定覆盖范围、不比较双源、不写 settled/pending（那是 inspect 的事）；
- 词汇唯一来源 evidence_builder（SOURCE/CTX/make_evidence_id/
  unified_installation_floor），本文件只做薄适配，禁另起一套枚举；
- 仅允许 import evidence_builder + ftth_naming（DAG 无回边）；禁止 import
  parse/coverage/inspect/ftth_common 重逻辑。

调用方（analyze_coverage_vshape V 谷底产出口）只加一个字段
「安装楼层统一」，判据、口径文案、rc 语义逐字不动；老产物无该字段时
C3 走 legacy 原路（逐字节不变）。
"""
from evidence_builder import (  # 词汇唯一来源；本层只适配、不另起枚举
    SOURCE_DIRECT,
    SOURCE_DERIVED,
    SOURCE_UNRESOLVED,
    CTX_TOTAL_MAP,
    CTX_INTERVAL,
    CTX_VSHAPE,
    CTX_UNKNOWN,
    make_evidence_id,
    unified_installation_floor,
)

__all__ = [
    "vshape_floor_evidence",
    "vertical_floor_evidence",
    # 会审 P1-2/P1-3（加法式，不改既有函数行为）：
    "PENDING_COVERAGE_DATA_INCOMPLETE",
    "PENDING_COVERAGE_WINDOW_INCOMPLETE",
    "PENDING_COVERAGE_BOX_BINDING_UNKNOWN",
    "PENDING_COVERAGE_SOURCE_CONFLICT",
    "PENDING_COVERAGE_TRUE_GAP",
    "PENDING_COVERAGE_CATEGORIES",
    "classify_coverage_pending",
    "TIER_SHARED_GEOMETRY",
    "TIER_SHARED_BUSINESS",
    "TIER_BUILDING_SPECIFIC",
    "evidence_tier_for",
]

# ---------- 待裁决分类（会审 P1-2，封闭枚举；只打标、不改判据） ----------
# 动因：V型/竖线 coverage pending 此前汇聚成一句"覆盖范围缺失楼层"，
# 人工看到时分不清是"没有数据"还是"数据有但箱不知道是谁"。
# 五类只回答"缺的是哪一环"，判定逻辑与 rc 语义逐字不动，仍由人工裁决。
PENDING_COVERAGE_DATA_INCOMPLETE = "COVERAGE_DATA_INCOMPLETE"  # 窗口内无米数列/无连续体/无户数期望，建不出判定
PENDING_COVERAGE_WINDOW_INCOMPLETE = "COVERAGE_WINDOW_INCOMPLETE"  # 米数列/窗口被截断，覆盖并集小于户数期望
PENDING_COVERAGE_BOX_BINDING_UNKNOWN = "COVERAGE_BOX_BINDING_UNKNOWN"  # V段存在但箱号锚缺失，绑不到具体箱
PENDING_COVERAGE_SOURCE_CONFLICT = "COVERAGE_SOURCE_CONFLICT"  # V底 vs 箱安装层 / 双源覆盖不一致
PENDING_COVERAGE_TRUE_GAP = "COVERAGE_TRUE_GAP"  # 数据齐但并集确有缺层，疑似真覆盖缺失

PENDING_COVERAGE_CATEGORIES = (
    PENDING_COVERAGE_DATA_INCOMPLETE,
    PENDING_COVERAGE_WINDOW_INCOMPLETE,
    PENDING_COVERAGE_BOX_BINDING_UNKNOWN,
    PENDING_COVERAGE_SOURCE_CONFLICT,
    PENDING_COVERAGE_TRUE_GAP,
)


def classify_coverage_pending(事项=None, 说明=None):
    """待裁决条目 → 五类之一（纯分类，不定案；关键词命中，默认 DATA_INCOMPLETE）。

    顺序即优先级：绑定失败 > 来源冲突 > 窗口截断 > 缺层陈述 > 无数据 > 真缺口兜底。
    未命中任何关键词时返回 DATA_INCOMPLETE（"缺判断依据"本身即缺数据，不得伪装成真缺口）。
    """
    _t = "%s %s" % (事项 or "", 说明 or "")
    if any(k in _t for k in ("无箱号锚", "V段数与箱数不一致", "无法绑定", "绑不到", "锚点缺失")):
        return PENDING_COVERAGE_BOX_BINDING_UNKNOWN
    if any(k in _t for k in ("两来源不一致", "不一致", "偏差", "冲突", "需复核", "交叉校验")):
        # "覆盖范围缺失楼层"若同时含截断提示，优先判窗口截断（下分支先行）——
        # 故此处排除已含"截断"的缺层陈述，避免把窗口问题误归为来源冲突。
        if "缺失楼层" in str(事项 or "") and "截断" in _t:
            return PENDING_COVERAGE_WINDOW_INCOMPLETE
        return PENDING_COVERAGE_SOURCE_CONFLICT
    if any(k in _t for k in ("截断", "窗口边界", "米数列是否被截", "P0-12")):
        return PENDING_COVERAGE_WINDOW_INCOMPLETE
    if "缺失楼层" in _t:
        return PENDING_COVERAGE_TRUE_GAP
    if any(k in _t for k in ("无法判定", "覆盖楼层为空", "找不到任何", "无可用米数列", "无户数")):
        return PENDING_COVERAGE_DATA_INCOMPLETE
    # 兜底：分不清缺哪一环 = 缺判断依据 = 缺数据，不得伪装成"真缺口"。
    if "缺失" in _t or "缺层" in _t:
        return PENDING_COVERAGE_TRUE_GAP
    return PENDING_COVERAGE_DATA_INCOMPLETE


# ---------- 共享证据三层（会审 P1-3，封闭枚举；只打标、不改克隆行为） ----------
# 动因：共享系统图"克隆"此前不区分"复制图元=复制业务事实"。
# 三层只回答"这份证据允不允许跨栋复制"：
#   shared_geometry           同一米数窗/竖干几何，可天然克隆（米数表/V段/谷底/连续体）；
#   shared_business_evidence  须克隆+楼栋证据绑定（箱编号归属、户数列落位）；
#   building_specific_evidence 不允许跨栋复制（单栋安装层/覆盖判定结论）。
TIER_SHARED_GEOMETRY = "shared_geometry"
TIER_SHARED_BUSINESS = "shared_business_evidence"
TIER_BUILDING_SPECIFIC = "building_specific_evidence"


def evidence_tier_for(bldg_key=None, has_src_window=False, is_window_node=False):
    """共享条目 → 证据层（纯分类，不改克隆行为）。

    - 窗节点（键含[共享]）→ shared_geometry（几何本身）；
    - 成员条目（带来源共享窗的非窗节点）→ shared_business_evidence（须按栋绑定复核）；
    - 其余 → building_specific_evidence（本栋私有，不得跨栋复制）。
    """
    _k = str(bldg_key or "")
    _is_win = bool(is_window_node) or _k.startswith("[共享]")
    if _is_win:
        return TIER_SHARED_GEOMETRY
    if bool(has_src_window):
        return TIER_SHARED_BUSINESS
    return TIER_BUILDING_SPECIFIC


def vshape_floor_evidence(box_no, floor_value, window_tag=""):
    """V 谷底安装楼层的统一证据（纯构造）。

    Args:
        box_no: 分纤箱编号原文。
        floor_value: V 谷底定层原值（可为 None；原样保留，不归一化）。
        window_tag: 窗口标识（米数列 x / 窗口区间，供 evidence_id 跨实例唯一）。

    Returns:
        unified_installation_floor 产物（source=derived_calc，
        context=vshape，note 照抄 V 谷底口径原文）。
    """
    return unified_installation_floor(
        floor_value,
        SOURCE_DERIVED,
        CTX_VSHAPE,
        make_evidence_id(CTX_VSHAPE, box_no, window_tag),
        note="皮线V形谷底（区间法测谷底行所在层带）",
    )


def vertical_floor_evidence(box_no, floor_value, has_direct_value, window_tag=""):
    """竖线法安装楼层的统一证据（纯构造）。

    分支与 analyze_coverage.py 现有口径一一对应（判据不动）：
    - 有总图直写值并采用（口径A）→ direct + total_map（图上明确写出）；
    - 无直写值走区间法（口径B）→ derived_calc + interval（规则算出）；
    - 值为 None → unresolved + unknown（未测得不断言）。

    Args:
        box_no: 分纤箱编号原文。
        floor_value: 采用后的安装楼层原值（_final，可为 None）。
        has_direct_value: 对照表直写值是否存在（bool(_tb)）。
        window_tag: 箱标识（箱 x，供 evidence_id 跨实例唯一）。
    """
    if floor_value is None:
        return unified_installation_floor(
            None, SOURCE_UNRESOLVED, CTX_UNKNOWN,
            make_evidence_id(CTX_UNKNOWN, box_no, window_tag),
            note="竖线法未测得安装楼层",
        )
    if has_direct_value:
        return unified_installation_floor(
            floor_value, SOURCE_DIRECT, CTX_TOTAL_MAP,
            make_evidence_id(CTX_TOTAL_MAP, box_no, window_tag),
            note="口径A:图上直写（总图对照表安装楼层）",
        )
    return unified_installation_floor(
        floor_value, SOURCE_DERIVED, CTX_INTERVAL,
        make_evidence_id(CTX_INTERVAL, box_no, window_tag),
        note="口径B:区间法（箱y落楼层带）",
    )
