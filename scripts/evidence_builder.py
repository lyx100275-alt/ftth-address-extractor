#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""箱证据层（V3 Phase 3 起步，2026-09-30 一百三十）。

只组织证据，不做业务裁决：
- 本文件只回答“这个安装楼层值从哪来、在什么坐标系下、证据编号是什么”；
- 禁止在此比较两个来源谁对、禁止 settled/pending 定案（那是 Conflict/Inspect 层的事）；
- 禁止 import 业务阶段模块（parse/coverage/inspect/ftth_common 重逻辑均不得拖入；
  仅允许 ftth_naming 归一函数——DAG 无回边，见一百三十研究报告 §6）。

统一安装楼层对象（v0.126 P1-1 + V3 §8 合集）：
- installation_floor           安装楼层原值（不归一化，`-1F`/`B1` 与图纸口径一致）
- installation_floor_source    取值：direct（图上直写）/ derived_calc（规则计算）
                               map_fill（对照表回填，经手一次）/ unresolved（未测得）
- installation_floor_confidence high（直写）/ medium（推导）/ low（保留位）/ null（未测得）
- installation_floor_evidence  证据说明（口径原文/方法名，不引入新数值关系）
- coordinate_context           坐标语义体系：total_map（总图对照表）/ system_diagram
                               （系统图内几何）/ box_annotation（箱位直写标注）
                               interval（区间法 y 关联）/ vshape（V 型谷底）/ unknown
- evidence_id                  确定性证据编号（同输入必同输出，供跨产物追溯）
"""
from ftth_naming import norm_floor  # noqa: F401  （归一唯一入口；本层仅在自检里用，不改值）

__all__ = [
    "SOURCE_DIRECT", "SOURCE_DERIVED", "SOURCE_MAP_FILL", "SOURCE_UNRESOLVED",
    "CTX_TOTAL_MAP", "CTX_SYSTEM_DIAGRAM", "CTX_BOX_ANNOTATION",
    "CTX_INTERVAL", "CTX_VSHAPE", "CTX_UNKNOWN",
    "CONF_HIGH", "CONF_MEDIUM", "CONF_LOW",
    "make_evidence_id", "confidence_for_source", "unified_installation_floor",
    "box_evidence",
]

# ---------- 来源词汇（封闭枚举；新增须同步 inspect C3 文案与 CHANGELOG） ----------
SOURCE_DIRECT = "direct"          # 图上直写（系统图 F 标注 / 箱位标注 / 对照表直写）
SOURCE_DERIVED = "derived_calc"   # 规则计算（区间法 / V 型谷底；图上没写、算出来的）
SOURCE_MAP_FILL = "map_fill"      # 对照表回填（parse 自身测不出，经 fx-map 补——经手一次，须留痕）
SOURCE_UNRESOLVED = "unresolved"  # 未测得（值为 null，不作任何语义断言）

# ---------- 坐标语义体系（V3 §8：总图与系统图不是同一坐标系，不可直接比 Y） ----------
CTX_TOTAL_MAP = "total_map"            # 总图对照表（箱表行，独立图区）
CTX_SYSTEM_DIAGRAM = "system_diagram"  # 系统图内几何归属（标题 x 区间 / 单元容器）
CTX_BOX_ANNOTATION = "box_annotation"  # 箱位直写标注（N号楼M单元K层，A′级）
CTX_INTERVAL = "interval"              # 区间法（编号文字 y 关联楼层带）
CTX_VSHAPE = "vshape"                  # 皮线 V 型谷底推导
CTX_UNKNOWN = "unknown"                # 未测得 / 无法确定体系

# ---------- 置信度（只描述证据强度，不作定案依据） ----------
CONF_HIGH = "high"      # 直写：图上明确写出
CONF_MEDIUM = "medium"  # 推导：规则算出，可复核
CONF_LOW = "low"        # 保留位：弱证据（当前无产出方使用，占位防枚举漂移）


def make_evidence_id(context, box_no, tag=""):
    """确定性证据编号：同输入必同输出（跨产物追溯用，不含随机/时间）。

    格式 ``EV:{context}:{box_no}``，tag 非空时追加 ``@{tag}``
    （调用方传实例坐标等区分同一箱的多次文字实例，如 ``x1250.3``）。
    """
    _ctx = str(context or CTX_UNKNOWN).strip() or CTX_UNKNOWN
    _no = str(box_no or "").strip() or "?"
    _tag = str(tag or "").strip()
    _eid = "EV:%s:%s" % (_ctx, _no)
    if _tag:
        _eid += "@%s" % _tag
    return _eid


def confidence_for_source(source):
    """来源→置信度默认映射（调用方显式给 confidence 时不经此函数）。

    direct→high；derived_calc/map_fill→medium；unresolved→None（未测得不断言）。
    未知来源一律 None（不猜，交上游明确）。
    """
    if source == SOURCE_DIRECT:
        return CONF_HIGH
    if source in (SOURCE_DERIVED, SOURCE_MAP_FILL):
        return CONF_MEDIUM
    return None


def unified_installation_floor(value, source, coordinate_context, evidence_id,
                               confidence=None, note=""):
    """组装统一安装楼层对象（纯构造，不比较、不定案）。

    Args:
        value: 安装楼层原值（可为 None；原样保留，不归一化）。
        source: SOURCE_* 之一（未知传 SOURCE_UNRESOLVED）。
        coordinate_context: CTX_* 之一。
        evidence_id: make_evidence_id 产物（调用方负责跨实例唯一）。
        confidence: 显式置信度；None 则按来源自动映射（value 为 None 时恒为 None）。
        note: 证据说明（建议填 legacy 口径原文/方法名，如实抄，不发挥）。

    Returns:
        dict（键名固定六个；note 非空时加第七键 `_note`——下划线前缀，
        与 legacy 键空间隔离，旧消费方按名取键不受影响）。
    """
    _src = str(source or SOURCE_UNRESOLVED).strip() or SOURCE_UNRESOLVED
    _ctx = str(coordinate_context or CTX_UNKNOWN).strip() or CTX_UNKNOWN
    if value is None:
        _conf = None
    elif confidence is not None:
        _conf = confidence
    else:
        _conf = confidence_for_source(_src)
    _u = {
        "installation_floor": value,
        "installation_floor_source": _src,
        "installation_floor_confidence": _conf,
        "installation_floor_evidence": str(note or ""),
        "coordinate_context": _ctx,
        "evidence_id": str(evidence_id or ""),
    }
    return _u


def box_evidence(box_no, bldg, unit, floor_unified, geom_ref=None):
    """组装单箱证据记录（纯组织：身份 + 统一楼层 + 几何引用，不定案）。

    Args:
        box_no: 分纤箱编号原文。
        bldg/unit: 归属楼栋/单元（“未归属”传 None，不得编造归属）。
        floor_unified: unified_installation_floor 产物（原样引用，不拆解重写）。
        geom_ref: 几何引用（{x, y, 层}，可为 None；只记录、不参与判断）。

    Returns:
        dict（evidence_id 与 floor_unified 内的一致；conflict/inspect 只读不改）。
    """
    _fu = dict(floor_unified or {})
    return {
        "evidence_id": _fu.get("evidence_id") or make_evidence_id(CTX_UNKNOWN, box_no),
        "编号": str(box_no or "").strip(),
        "楼栋": bldg,
        "单元": unit,
        "安装楼层统一": _fu,
        "几何引用": dict(geom_ref or {}),
    }
