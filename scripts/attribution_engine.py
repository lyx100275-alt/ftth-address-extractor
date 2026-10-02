#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""归属引擎（V3 PhaseB，2026-09-30 一百三十四起步、一百三十五全搬）。

职责（全搬后）：
1. 楼栋名归一化（等价写法折叠，不做语义推断）；
2. 对照表楼栋值解析到本图锚点（前缀匹配，不猜）；
3. --bldg-map 文件载入与结构校验（格式不对由调用方按 L1-C2 判 rc=2）；
4. 改派计算（FX 文字按对照表重挂楼栋/单元；只计算、不改调用方结构、
   不写 settled/pending——摘除、落盘、日志由 parse 编排层执行）。

不做的事（硬禁区）：
- 不判定安装楼层、不写 settled/pending（那是 inspect 的事）；
- 仅允许 import ftth_naming（UNIT_RE_SRC/unit_num）——DAG 无回边，与
  evidence_builder 同纪律；禁止 import parse/coverage/inspect/ftth_common
  重逻辑，杜绝循环导入；
- bug-for-bug：实现自 parse_dxf_structured.py 逐字搬入，
  含注释所述实测坑（# vs 号、单元后缀剥离、前缀最长命中、重号坐标配对、
  全图 texts 出发、单元号双字段）。
"""
import json
import os
import re

from ftth_naming import UNIT_RE_SRC, unit_num  # noqa: F401  （归一唯一入口）

__all__ = [
    "norm_bldg",
    "resolve_bldg_name",
    "load_bdg_map",
    "apply_reassignment",
]


def norm_bldg(s):
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
    #   单元号写法见 ftth_naming.UNIT_RE_SRC：`3#楼2单元` 与 `3#楼二单元` 都要剥掉。
    t = re.sub(UNIT_RE_SRC + r".*$", "", t)
    t = re.sub(r"\d+\s*层.*$", "", t)
    return t


def resolve_bldg_name(name, bldg_ranges):
    """把对照表的「楼栋」值解析为本图锚点楼栋名（bldg_ranges 的键）。

    对照表由 extract_fx_map.py 产出，其「楼栋」字段取自最近楼栋标注，形态可为
    `3#楼` 或 `3#楼2单元`；而 parse 侧 bldg_ranges 的键是**不含单元**的楼栋名
    （如 `3#楼`）。不做这一步解析，含单元后缀的条目会被 `not in bldg_ranges`
    整批丢掉（2026-09-18 实测：23 条里只有 4#配套楼 / 11#配套楼两个无后缀的通过，
    箱数只从 0 涨到 2 而非 23）。

    2026-09-18 二次修正：仅做前缀匹配还不够 —— 另有 `1号楼…`（`号`）与锚点
    `1#楼`（`#`）**写法不同**的形态，实测某图 22 条对照表因此一条都挂不上。
    现改为先归一化（见 norm_bldg）再匹配，等价写法折叠、数字一律不动。

    规则：归一化后精确命中优先；否则取「归一化后是它的前缀」的最长锚点名；
    都不命中返回 None（不猜），并由调用方**登记**而非静默丢弃。
    """
    if not name:
        return None
    if name in (bldg_ranges or {}):
        return name
    _n = norm_bldg(name)
    if not _n:
        return None
    for _b in (bldg_ranges or {}):
        if _b != name and norm_bldg(_b) == _n:
            return _b
    best = None
    for _b in (bldg_ranges or {}):
        _nb = norm_bldg(_b)
        if _nb and _n.startswith(_nb) and (best is None or len(_nb) > len(norm_bldg(best))):
            best = _b
    return best


def load_bdg_map(path):
    """载入 --bldg-map 文件（extract_fx_map.py 产物），返回 (BDG_MAP, meta, error)。

    成功时 error 为 None；失败时返回 (None, None, 消息），调用方按 L1-C2
    输入类错误判 rc=2（parse 现有行为：读失败/格式不对均 sys.exit(2)）。
    本函数不 exit、不 log（保持纯函数可测；等价桩可直调）。
    """
    try:
        with open(path, "r", encoding="utf-8") as _f:
            _raw2 = json.load(_f)
    except (IOError, OSError, json.JSONDecodeError, ValueError) as e:
        return None, None, "无法读取 --bldg-map %s: %s" % (path, e)
    _entries2 = _raw2.get("FX映射表") if isinstance(_raw2, dict) else _raw2
    if not isinstance(_entries2, list):
        return None, None, "--bldg-map 格式不对：顶层应含「FX映射表」数组（确认是 extract_fx_map.py 产物）"
    _map = {}
    for _e2 in _entries2:
        if isinstance(_e2, dict) and _e2.get("编号"):
            _map.setdefault(str(_e2["编号"]).strip(), []).append(_e2)
    _dups2 = sorted(k for k, v in _map.items() if len(v) > 1)
    _meta = {"文件": os.path.basename(path), "条目数": len(_entries2),
             "唯一编号": len(_map), "重号编号": _dups2}
    return _map, _meta, None


def apply_reassignment(texts, bdg_map, bldg_ranges, bldg_texts, fx_re):
    """改派计算：把 FX 文字按对照表重挂楼栋/单元（纯计算，不改入参结构）。

    来源：parse_dxf_structured.py --bldg-map 改派块逐字搬入（含全部实测注释
    所指行为：全图 texts 出发、重号坐标配对、单元号双字段、跨栋留痕坐标）。

    Args:
        texts: 全图文字列表（每项含 内容/x/y/高）。
        bdg_map: load_bdg_map 产物（编号->[条目]；可为 {} / None）。
        bldg_ranges: 楼栋锚点区间（键为本图楼栋名）。
        bldg_texts: 已按标题 x 切好的楼栋文字（只读，用于建原归属表；本函数
            不摘除不修改，摘除由调用方按返回的 claimed_ids 执行）。
        fx_re: 分纤箱编号正则（compiled；None 则零改派）。

    Returns:
        dict：fx_force（楼栋->{单元号->[text]}，text 为原文引用）、fx_entry
        （(编号, round(x,2))->条目）、moved（跨栋留痕）、skip_dup（重号未改派）、
        dup_matched（重号配对留痕）、unresolved（楼栋值未解析）、no_unit
        （单元号未取到）、moved_count（文字实例数）、moved_nos（编号集合）、
        claimed_ids（需摘除的文字 id 集合）。
    """
    _force = {}
    _entry = {}
    _moved = []
    _skip_dup = []
    _dup_matched = []
    _unresolved = []
    _no_unit = set()
    _moved_count = 0
    _moved_nos = set()
    _claimed = set()
    if not bdg_map:
        return {"fx_force": _force, "fx_entry": _entry, "moved": _moved,
                "skip_dup": _skip_dup, "dup_matched": _dup_matched,
                "unresolved": _unresolved, "no_unit": _no_unit,
                "moved_count": _moved_count, "moved_nos": _moved_nos,
                "claimed_ids": _claimed}
    _owner = {}
    for _b0 in list((bldg_texts or {}).keys()):
        for _t0 in (bldg_texts or {})[_b0]:
            _owner[id(_t0)] = _b0
    for _t in (texts or []):
        _m = fx_re.search(_t["内容"]) if fx_re else None
        if not _m:
            continue
        _no = _m.group(0).strip()
        _cand = (bdg_map or {}).get(_no)
        if not _cand:
            continue
        if len(_cand) > 1:
            _scored = []
            for _e in _cand:
                try:
                    _ex, _ey = float(_e.get("x")), float(_e.get("y"))
                except (TypeError, ValueError):
                    continue
                _scored.append((abs(_ex - _t["x"]) + abs(_ey - _t["y"]), _e))
            _ymatch_tol = max(1.0, 0.5 * float(_t.get("高") or 0.0))
            if not _scored or min(_scored, key=lambda z: z[0])[0] > _ymatch_tol:
                _skip_dup.append(_no)
                continue
            _dist1, _pick1 = min(_scored, key=lambda z: z[0])
            _cand = [_pick1]
            _dup_matched.append(
                "%s@(%.1f,%.1f)：对照表 %d 个实例中按坐标配对到「%s/%s %s」（距离 %.2f）"
                % (_no, _t["x"], _t["y"], len(_scored),
                   _pick1.get("楼栋"), _pick1.get("单元"), _pick1.get("安装楼层"), _dist1))
        _tb0 = str(_cand[0].get("楼栋") or "").strip()
        _tb = resolve_bldg_name(_tb0, bldg_ranges)
        if not _tb:
            _unresolved.append("%s: 对照表楼栋=%r 未命中本图锚点（锚点：%s）"
                               % (_no, _tb0, "/".join(sorted(bldg_ranges or {})[:8])))
            continue
        _tu_raw = str(_cand[0].get("单元") or "").strip()
        _tu_num = unit_num(_cand[0].get("图上单元"))
        if _tu_num is None:
            _tu_num = unit_num(_tu_raw)
        _force.setdefault(_tb, {}).setdefault(_tu_num, []).append(_t)
        if _tu_num is None:
            _no_unit.add("%s（对照表单元字段=%r）" % (_no, _tu_raw))
        _entry[(_no, round(_t["x"], 2))] = _cand[0]
        _claimed.add(id(_t))
        _moved_count += 1
        _moved_nos.add(_no)
        _old = _owner.get(id(_t))
        if _old != _tb:
            _moved.append("%s@(%.1f,%.1f): %s -> %s/%s"
                          % (_no, _t["x"], _t["y"],
                             _old or "(不在任何楼栋x区间)", _tb,
                             _tu_raw or "(单元字段为空→待定)"))
    return {"fx_force": _force, "fx_entry": _entry, "moved": _moved,
            "skip_dup": _skip_dup, "dup_matched": _dup_matched,
            "unresolved": _unresolved, "no_unit": _no_unit,
            "moved_count": _moved_count, "moved_nos": _moved_nos,
            "claimed_ids": _claimed}
