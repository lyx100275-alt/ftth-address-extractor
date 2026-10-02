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
]


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
