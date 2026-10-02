#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DXF 事实提取层（V3 Phase 1-2，2026-09-30 一百二十九）。

只回答“图纸上有什么”，不做业务语义判断：
- TEXT/MTEXT/INSERT/LINE/POLYLINE 等实体原样读取（坐标/图层/属性/句柄）。
- 不产生“安装楼层/归属/覆盖/户数”等业务结论（那是 Reason 层的事）。
- 不做楼栋/单元/箱/楼层正则判断（UNIT_RE/FX_RE/TITLE_RE 等一律不得出现在此文件）。

单一真源纪律：
- load_dxf/collect_texts/extract_geom 唯一实现在 ftth_geom.py，本文件只 re-export，
  禁止再抄一份（镜像铁律②；见 SKILL_CHANGELOG 一百二十九）。
- 本文件唯一自有函数是 collect_inserts（自 parse_dxf_structured.py 内联块原样搬出，
  bug-for-bug：None 参数照旧崩、空路径无日志、log 文案逐字节一致）。
"""
from ftth_geom import load_dxf, collect_texts, extract_geom, median_text_height  # noqa: F401
import re

__all__ = ["load_dxf", "collect_texts", "extract_geom", "median_text_height",
           "collect_inserts"]


def collect_inserts(msp, insert_blocks_str, attrib_tag_str, attrib_val_pat, log=None):
    """收集匹配的 INSERT 实体（自 parse 内联块逐字搬出，行为零改）。

    Args:
        msp: ezdxf modelspace.
        insert_blocks_str: --insert-blocks 原值（逗号分隔；falsy 则返回 [] 且无日志）。
        attrib_tag_str: --insert-attrib-tag 原值（逗号分隔）。
        attrib_val_pat: --insert-attrib-val 原值（正则源；None 时 re.compile 照旧抛 TypeError）。
        log: logger（有则打“收集到 N 个匹配的 INSERT 实体”，与原实现逐字节一致）。

    Returns:
        list[{块名, x, y, 属性, 层}]，x/y 按原实现 round(p.x, 2)。
    """
    insert_items = []  # [{块名, x, y, 属性: {tag: val}, layer}]
    if insert_blocks_str:
        INSERT_BLOCK_SET = set(b.strip() for b in insert_blocks_str.split(",") if b.strip())
        ATTRIB_TAGS = set(t.strip() for t in attrib_tag_str.split(",") if t.strip())
        ATTRIB_VAL_RE = re.compile(attrib_val_pat)
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
        if log is not None:
            log.info(f"收集到 {len(insert_items)} 个匹配的 INSERT 实体")
    return insert_items
