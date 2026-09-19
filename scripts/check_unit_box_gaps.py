#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探查期「单元 × 箱清单」交叉清点 —— 提前暴露「某单元没分纤箱」（2026-09-18，用户裁定）

为什么要有它：
    「某单元一个箱都没有」原先只在 **Step 2 自检**（覆盖完整性门禁）阶段才暴露 ——
    此时 parse/coverage 已经跑完，返工面大。而图面证据其实**在 parse 之前就齐了**：
      · 骨架（本图有哪些楼、每楼几单元）→ titleblock.json（栋级层户 + 单元标注）
      · 箱清单（哪些单元有箱）         → fxmap.json 的「FX映射表」或 fx_locations.json 的「唯一箱位」
    两者都在 `_PIPE_STAGES` 的 parse 之前产出，故本检查可提前到探查期做。

定位：**预检告警，不是待裁决项的权威载体**。
    最终待裁决清单仍以 coverage.json / inspect.json 为准；两处不一致时登记矛盾、以后者为准。
    本脚本**不裁决、不静默择一**，只把两个方向的差集连证据一起列出来交人。

四条硬约束（都对应实测踩过的坑）：
  1. **来源缺席 ≠ 数据为 0**。某侧文件缺失/不可读时判 `unresolved`、**不产生 pending** ——
     否则「没核过」会被输出成「全部单元无箱」（假失败），或反过来被当成「通过」（假绿灯）。
  2. **双向都报**。`骨架有·箱清单无`（候选：该单元未识别到箱）与
     `箱清单有·骨架无`（候选：骨架漏记该单元）**都要列** —— 实测同一张图的四条带里
     两个方向**同时**非空，单向差集必然漏报一半。
  3. **必须带楼栋维度**。单元号 `1单元` 在每栋都有，裸单元号比较会让同名单元跨楼栋互相污染。
  4. **单元号解析只走共享实现**（`ftth_common.parse_unit_key`）—— 本技能已因「同一逻辑
     多份实现」漂移过多次（判范围 / 楼号解析 / 中文数字均已因此收口）。

用法：
  python check_unit_box_gaps.py --titleblock titleblock.json \
      --fx-locations fx_locations.json --fx-map fxmap.json --out unit_box_gaps.json
  （三个输入**均可缺省**；缺省即记「该侧来源未提供」，据此判 unresolved。）

输出 JSON 主要键：
  两侧状态 / 骨架单元 / 箱清单单元 / 箱清单两来源分歧 / 差集 / 预检结论 / 需人工复核

退出码：0 正常（**含「两侧未齐，不判定」**，那是合法结论）；1 参数/写盘失败。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ftth_common  # noqa: E402
from ftth_common import (bldg_num, ensure_console_utf8, parse_unit_key,  # noqa: E402
                         write_json)  # noqa: E402

ensure_console_utf8()


def _load_json(path):
    """读 JSON。返回 (状态, 数据, 说明)。

    状态取值：``present``（读到了 dict）/ ``unavailable``（文件不存在或未给出路径）/
    ``unreadable``（文件在但读不了、或不是对象）。
    **不得把后两者与「读到了但内容为空」混为一谈** —— 那正是「没核」冒充「通过」的入口。
    """
    if not path:
        return "unavailable", None, "未提供该输入路径"
    if not os.path.isfile(path):
        return "unavailable", None, "文件不存在: %s" % path
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception as ex:                                         # noqa: BLE001
        return "unreadable", None, "读取失败: %s" % ex
    if not isinstance(d, dict):
        return "unreadable", None, "顶层不是对象（type=%s）—— 多为上游未产出时的占位" % type(d).__name__
    return "present", d, ""


def _key_label(k):
    b, u = k
    if b is None and u is None:
        return "(未识别)"
    if u is None:
        return "%s号楼(单元号未识别)" % b
    return "%s号楼%s单元" % (b, u)


def _skeleton_units(tb):
    """从 titleblock.json 抽「应有单元」集合。

    两个来源**取并集**（实测二者互补，缺一即漏）：
      · `地块.<地块>.<楼栋>.单元编号` —— 聚合字段，**经常为空**（实测某带 1 号楼、
        另一带 3/4 号楼均为空），不能当唯一来源；
      · `证据坐标.<地块>.<楼栋>.单元` —— 原始单元标注，更全，但含「单元归属歧义」项
        （归属本身待裁决，此处照录并标注，不替人裁决）。

    返回 (units:set, detail:list, note:str)。集合为空时 note 写明「骨架不可用」。
    """
    units, detail = set(), []
    for land, bmap in (tb.get("地块") or {}).items():
        if not isinstance(bmap, dict):
            continue
        for bname, v in bmap.items():
            if not isinstance(v, dict):
                continue
            b = bldg_num(bname) or None
            for u in (v.get("单元编号") or []):
                try:
                    uu = int(u)
                except (TypeError, ValueError):
                    continue
                units.add((b, uu))
                detail.append({"键": _key_label((b, uu)), "来源": "titleblock.地块.单元编号",
                               "楼栋键": bname, "原文": str(u)})
    for land, bmap in (tb.get("证据坐标") or {}).items():
        if not isinstance(bmap, dict):
            continue
        for bname, v in bmap.items():
            if not isinstance(v, dict):
                continue
            b0 = bldg_num(bname) or None
            for it in (v.get("单元") or []):
                txt = str(it[2]) if isinstance(it, (list, tuple)) and len(it) >= 3 else str(it)
                bb, uu = parse_unit_key(txt)
                b = bb if bb is not None else b0
                if uu is None:
                    detail.append({"键": _key_label((b, None)), "来源": "titleblock.证据坐标.单元",
                                   "楼栋键": bname, "原文": txt,
                                   "说明": "单元号未识别 —— 已登记，未计入可比键"})
                    continue
                units.add((b, uu))
                detail.append({"键": _key_label((b, uu)), "来源": "titleblock.证据坐标.单元",
                               "楼栋键": bname, "原文": txt,
                               "坐标": (list(it[:2]) if isinstance(it, (list, tuple)) and len(it) >= 2 else None)})
    note = "" if units else "骨架单元集合为空 —— 视为骨架不可用（不得拿空骨架去算差集，否则全部箱会被误判为『骨架缺单元』）"
    return units, detail, note


def _boxes_from_map(fm):
    """从 fxmap.json 的「FX映射表」抽箱清单（每箱自带楼栋 + 单元）。

    条目 `单元` 字段形如 `1#楼1单元`（楼号与单元号**紧贴无分隔**），故必须走
    `parse_unit_key`（它用 `N#`/`N号楼` + 尾部 `N单元` 两段解析），不能用「按空格拆」。
    无单元号时（如只有楼栋级的箱）**不得当作单元级** —— 登记为「单元粒度不可得」。
    """
    units, detail, no_unit = set(), [], []
    rows = fm.get("FX映射表") or []
    if not isinstance(rows, list):
        return units, detail, "「FX映射表」不是列表"
    for it in rows:
        if not isinstance(it, dict):
            continue
        src_txt = str(it.get("单元") or it.get("楼栋") or "")
        b, u = parse_unit_key(src_txt)
        if b is None:
            b2 = it.get("楼栋")
            b = int(b2) if isinstance(b2, int) else b
        rec = {"键": _key_label((b, u)), "来源": "fxmap.FX映射表",
               "编号": it.get("编号"), "原文": src_txt,
               "安装楼层": it.get("安装楼层")}
        if u is None:
            # 无单元号的箱（如仅楼栋级）**不得**当成单元级 —— 也不得直接从证据里消失：
            # 登记进 no_unit（进「证据明细」供人工归属），但不进可比键集合。
            no_unit.append(rec)
            detail.append(dict(rec, 说明="无单元号，未计入单元级可比键，须人工确认其单元归属"))
            continue
        units.add((b, u))
        detail.append(rec)
    note = ""
    if no_unit:
        note = "%d 条箱记录**无单元号**（如仅楼栋级），未计入单元级可比键，须人工确认其单元归属" % len(no_unit)
    return units, detail, note


def _boxes_from_loc(fl):
    """从 fx_locations.json 的「唯一箱位」抽箱清单（字段已是 楼栋:int / 单元:int）。"""
    units, detail = set(), []
    rows = fl.get("唯一箱位") or []
    if not isinstance(rows, list):
        return units, detail, "「唯一箱位」不是列表"
    for it in rows:
        if not isinstance(it, dict):
            continue
        try:
            b, u = int(it.get("楼栋")), int(it.get("单元"))
        except (TypeError, ValueError):
            continue
        units.add((b, u))
        detail.append({"键": _key_label((b, u)), "来源": "fx_locations.唯一箱位",
                       "安装层": it.get("安装层"), "实例数": it.get("实例数")})
    return units, detail, ""


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="探查期「单元 × 箱清单」交叉清点（无箱单元预检）")
    ap.add_argument("--titleblock", default=None, help="titleblock.json（骨架来源）")
    ap.add_argument("--fx-locations", default=None, help="fx_locations.json（箱清单来源之一）")
    ap.add_argument("--fx-map", default=None, help="fxmap.json（箱清单来源之一，读其「FX映射表」）")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    # ---------- 骨架侧 ----------
    tb_state, tb, tb_err = _load_json(a.titleblock)
    skel, skel_detail, skel_note = (set(), [], "")
    if tb_state == "present":
        skel, skel_detail, skel_note = _skeleton_units(tb)
    else:
        skel_note = tb_err or "骨架来源未提供"

    # ---------- 箱清单侧 ----------
    fl_state, fl, fl_err = _load_json(a.fx_locations)
    fm_state, fm, fm_err = _load_json(a.fx_map)

    box_srcs, box_detail = [], []
    u_map = u_loc = set()
    map_note = loc_note = ""
    if fm_state == "present":
        u_map, d, map_note = _boxes_from_map(fm)
        box_srcs.append({"来源": "fxmap.FX映射表", "键数": len(u_map),
                         "文件": os.path.basename(a.fx_map)})
        box_detail += d
    if fl_state == "present":
        u_loc, d, loc_note = _boxes_from_loc(fl)
        box_srcs.append({"来源": "fx_locations.唯一箱位", "键数": len(u_loc),
                         "文件": os.path.basename(a.fx_locations)})
        box_detail += d

    box = u_map | u_loc
    both = (fm_state == "present") and (fl_state == "present")
    diverge = None
    if both:
        # 两来源都在时**先互校**：分歧必须显式登记，不得静默取并集了事
        only_map, only_loc = u_map - u_loc, u_loc - u_map
        diverge = {
            "仅对照表(fxmap)有": sorted(_key_label(k) for k in only_map),
            "仅箱位标注(fx_locations)有": sorted(_key_label(k) for k in only_loc),
            "说明": "两个箱清单来源同时存在且不完全一致 —— 已并列登记，须人工核对；本脚本不择一",
        }

    box_note = "；".join(x for x in (map_note, loc_note) if x)

    # ---------- 判定 ----------
    # 铁律：来源缺席 ≠ 数据为 0。任一侧不可用 → unresolved，**不产生 pending**。
    skel_ok = (tb_state == "present") and bool(skel)
    box_ok = (fm_state == "present") or (fl_state == "present")

    if not skel_ok:
        verdict, reason = "unresolved", "骨架侧未就绪（%s）⇒ 不做差集，交覆盖阶段门禁兜底" % (
            skel_note or tb_state)
        gaps = None
    elif not box_ok:
        verdict, reason = "unresolved", ("箱清单侧未就绪（fxmap=%s / fx_locations=%s）"
                                         "⇒ 不做差集，交覆盖阶段门禁兜底" % (fm_state, fl_state))
        gaps = None
    else:
        a_gap = sorted((skel - box))
        b_gap = sorted((box - skel))
        gaps = {
            "骨架有·箱清单无": [{"键": _key_label(k),
                                 "候选解释": "该单元未识别到箱（图纸真无箱 / 箱未识别到 / 骨架误记）"}
                                for k in a_gap],
            "箱清单有·骨架无": [{"键": _key_label(k),
                                 "候选解释": "骨架缺该单元（骨架漏记 / 箱归属误判）"}
                                for k in b_gap],
        }
        _dv_hit = bool(diverge and (diverge["仅对照表(fxmap)有"]
                                    or diverge["仅箱位标注(fx_locations)有"]))
        if not box:
            # 两侧都在、但箱清单一条都没有：这不是「全图单元无箱」的结论，而是**须先分清**
            # 是「本图本就不用这个来源」还是「脚本没匹配上」。
            verdict = "pending"
            reason = ("箱清单**两来源均 0 条** —— 须先确认是「本图无箱位数据」还是"
                      "「匹配失败」，不得径直判为全图单元无箱")
        elif a_gap or b_gap or _dv_hit:
            # 注意 `_dv_hit` 这一支：两来源**分歧**时，若各自给出的是**不相交**的单元
            # （如 A 只给 1号楼1单元、B 只给 1号楼2单元），取并集后差集反而为空 ——
            # 若只看差集就会判 settled，等于「**静默取并集了事**」，把两个来源互相矛盾
            # 这件事吞掉。实测该形态由冒烟用例捕获，故分歧本身即须计入 pending。
            verdict = "pending"
            _bits = []
            if a_gap or b_gap:
                _bits.append("差集非空：骨架有·箱清单无 %d 项 / 箱清单有·骨架无 %d 项"
                             % (len(a_gap), len(b_gap)))
            if _dv_hit:
                _bits.append("箱清单两来源分歧（仅对照表 %d 项 / 仅箱位标注 %d 项）"
                             % (len(diverge["仅对照表(fxmap)有"]),
                                len(diverge["仅箱位标注(fx_locations)有"])))
            reason = "；".join(_bits)
        else:
            verdict, reason = "settled", "两侧单元集合一致，无差集"

    result = {
        "来源": "探查期「单元 × 箱清单」交叉清点",
        "定位": "预检告警：在 parse/coverage 之前提前暴露「某单元无分纤箱 / 骨架缺单元」。"
                "**不是**待裁决项的权威载体 —— 最终待裁决清单仍以 coverage.json / inspect.json 为准，"
                "两处不一致时登记矛盾并以后者为准。",
        "两侧状态": {
            "骨架": {"状态": tb_state, "文件": os.path.basename(a.titleblock or ""),
                     "键数": len(skel), "说明": skel_note},
            "箱清单": {"状态": "present" if box_ok else ("unavailable" if not (fm_state == "unreadable" or fl_state == "unreadable") else "unreadable"),
                       "来源": box_srcs, "键数": len(box), "说明": box_note},
        },
        "骨架单元": sorted(_key_label(k) for k in skel),
        "箱清单单元": sorted(_key_label(k) for k in box),
        "箱清单两来源分歧": diverge,
        "差集": gaps,
        "预检结论": verdict,
        "预检说明": reason,
        "需人工复核": verdict == "pending",
        "复核说明": ("预检结论 pending —— 请对照原图裁定；本脚本只列证据与候选解释，不结论、不择一。"
                     if verdict == "pending" else
                     ("两侧来源未齐，本次**未判定**（unresolved）—— 不是「通过」，覆盖阶段门禁仍会兜底。"
                      if verdict == "unresolved" else "两侧一致，无待确认项。")),
        "证据明细": {"骨架": skel_detail, "箱清单": box_detail},
    }
    if diverge:
        result["需人工复核"] = True

    write_json(a.out, result)

    print("[预检] 骨架=%s(%d) 箱清单=%s(%d) → %s"
          % (tb_state, len(skel),
             "present" if box_ok else fm_state, len(box), verdict))
    if verdict == "pending":
        _g = gaps or {}
        for _k in ("骨架有·箱清单无", "箱清单有·骨架无"):
            _items = _g.get(_k) or []
            if _items:
                print("[⚠] %s %d 项：" % (_k, len(_items)))
                for _it in _items[:10]:
                    print("      %s" % _it["键"])
        if not box:
            print("[⚠] 箱清单两来源均 0 条：须先分清「本图无箱位数据」与「匹配失败」")
    elif verdict == "unresolved":
        print("[预检] %s" % reason)
    if diverge and (diverge["仅对照表(fxmap)有"] or diverge["仅箱位标注(fx_locations)有"]):
        print("[⚠] 箱清单两来源分歧：仅对照表 %d 项 / 仅箱位标注 %d 项"
              % (len(diverge["仅对照表(fxmap)有"]), len(diverge["仅箱位标注(fx_locations)有"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
