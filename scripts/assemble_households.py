#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
出表输入 JSON 组装（count-box 路线通用版）
把 count_box_icons.py 输出的逐层户数列 + 调用方显式给出的「列→楼栋/单元」归属映射
（可选：coverage JSON 的分纤箱信息）机械合并为 gen_addressbook.py 可直接消费的 JSON。

背景：count.json 的「列」只有 列x + 逐层户数，**不含楼栋/单元归属**——
列与楼栋单元的对应是图纸特有的几何判读（列x ↔ 箱符号 x 对齐等），属于裁决项，
必须由调用方显式给出，本脚本不做任何自动猜测（与「户数直读、禁止假设」同则）。

用法（推荐经统一入口）：
    ftth.py assemble --count count.json \
        --col-map "0=1#楼/1单元;1=2#楼/1单元;8=7#楼/1单元,8#楼/1单元,10#楼/1单元" \
        --coverage coverage.json --out assembly.json

    （直调：python assemble_households.py --count ... --col-map ... --out ...）

--col-map 语法：分号分隔条目；每条 = `列号=楼栋/单元[,楼栋/单元...]`
  - 列号为 count.json「列」数组的 0 基下标；
  - 一列映射到**多个单元** = 共享系统图克隆（同一份逐层户数复制给各单元，显式留痕）；
  - 单元槽写 `N单元`、`楼栋N单元` 全名或省略（`楼栋` 单写 = 单单元楼，归一为 `1单元`，
    与 gen_addressbook 的单元键归一规则一致）；
  - 同一 (楼栋,单元) 只能被一列声明，重复声明硬失败（防止户数翻倍）。

--coverage（可选）：analyze_coverage*.py 输出的覆盖 JSON（嵌套/扁平两种格式自动检测），
  把各单元的分纤箱（编号/安装楼层/覆盖范围线索）合并进组装结果。

输出：gen 输入 JSON（楼栋→单元→{楼层表,分纤箱}），并在 stdout 打印逐单元守恒统计。
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ftth_common import protect_out_path, UNIT_RE_SRC, unit_num, ensure_console_utf8, write_json, sha256_file

ensure_console_utf8()

ap = argparse.ArgumentParser(description="出表输入 JSON 组装（count 逐层户数 + 显式列归属映射 + coverage 分纤箱）")
ap.add_argument("--count", required=True, help="count_box_icons.py 输出的 count.json（含「列」数组）")
ap.add_argument("--col-map", required=True,
                help='列归属映射 "列号=楼栋/单元[,楼栋2/单元2...];..."，分号分隔；'
                     "一列多单元=共享系统图克隆；单元省略=单单元楼（归一 1单元）")
ap.add_argument("--coverage", "--coverage-json", dest="coverage", default=None,
                help="覆盖范围 JSON（可选，合并分纤箱信息）；别名 --coverage-json（统一入口转发用名）")
ap.add_argument("--dxf", default=None, help="DXF 文件名（仅写入输出元信息，可选）")
ap.add_argument("--out", required=True, help="输出 JSON 路径（gen_addressbook 的 --dxf-json 输入）")
ap.add_argument("--force", action="store_true",
                help="允许覆盖已存在的输出产物（默认改道 <原名>_patched.json，写保护）")
args = ap.parse_args()

# ---------- 读 count.json ----------
try:
    with open(args.count, "r", encoding="utf-8") as f:
        count = json.load(f)
except (IOError, json.JSONDecodeError) as e:
    print(f"[assemble] 错误：无法读取 count JSON {args.count}: {e}")
    sys.exit(2)

cols = count.get("列")
if not isinstance(cols, list) or not cols:
    print(f"[assemble] 错误：count JSON {args.count} 中没有「列」数组（确认输入是 count_box_icons.py 的输出）")
    sys.exit(2)


def norm_unit(ukey, bkey=None):
    """单元键归一（与 gen_addressbook._norm_unit_key 同则）：N单元 / 楼栋N单元 / 楼栋名→1单元

    数字写法兼容表见 ftth_common.UNIT_RE_SRC —— 图上并存 `1单元`（图签/对照表）
    与 `一单元`（系统图单元轴），两者必须归一到同一个键（ASCII `N单元`），
    否则跨来源 join 会静默失败。
    """
    s = str(ukey).strip()
    if not s:
        return s
    # 2026-09-19 修（P0）：原先首分支用单捕获组 `(\d+)…楼?…UNIT` 取的是串首数字，
    #   `3#楼1单元` 被归一成 `3单元`（取了楼号），致 coverage 多箱错位并相互覆盖。
    #   改走 ftth_common.unit_num 唯一入口（尾部 N单元 取号，与 gen/apply 同则，
    #   另兼容一单元等中文写法）；楼栋名本身仍归 1单元。
    _n = unit_num(s)
    if _n is not None:
        return "%d单元" % _n
    if bkey is not None and s == str(bkey).strip():
        return "1单元"
    return s


def parse_col_map(spec):
    """解析 --col-map → [(列号, 楼栋, 单元), ...]；语法错误/列号越界一律硬失败"""
    out = []
    for item in spec.split(";"):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            print(f"[assemble] 错误：col-map 条目缺少 '='：{item!r}（应为 列号=楼栋/单元）")
            sys.exit(2)
        left, right = item.split("=", 1)
        left = left.strip()
        if not left.isdigit():
            print(f"[assemble] 错误：列号必须是数字：{left!r}（条目 {item!r}）")
            sys.exit(2)
        ci = int(left)
        if ci < 0 or ci >= len(cols):
            print(f"[assemble] 错误：列号 {ci} 越界（count.json 共 {len(cols)} 列，0 基）")
            sys.exit(2)
        units = [u.strip() for u in right.split(",") if u.strip()]
        if not units:
            print(f"[assemble] 错误：条目 {item!r} 没有给出任何 楼栋/单元")
            sys.exit(2)
        for u in units:
            if "/" in u:
                bkey, ukey = u.split("/", 1)
                bkey, ukey = bkey.strip(), ukey.strip()
            else:
                # 无斜杠：或为「楼栋N单元」全名，或为裸楼栋名（单单元楼 → 1单元）
                #   单元号兼容 ASCII 与中文数字（见 ftth_common.UNIT_RE_SRC）
                m = re.fullmatch(r"(.+?\d+\s*[#号]?\s*楼?)\s*(" + UNIT_RE_SRC + r")", u)
                if m:
                    bkey, ukey = m.group(1).strip(), m.group(2).strip()
                else:
                    bkey, ukey = u, u
            ukey = norm_unit(ukey, bkey)
            out.append((ci, bkey, ukey))
    if not out:
        print("[assemble] 错误：col-map 为空")
        sys.exit(2)
    # 同一 (楼栋,单元) 只能被一列声明
    seen = {}
    for ci, bkey, ukey in out:
        key = (bkey, ukey)
        if key in seen:
            print(f"[assemble] 错误：(楼栋,单元) {bkey}/{ukey} 被列 {seen[key]} 和列 {ci} 同时声明——"
                  f"户数会翻倍。同一单元只能归属一列；如为共享系统图，把多个单元写在同一列的右侧。")
            sys.exit(2)
        seen[key] = ci
    return out


mapping = parse_col_map(args.col_map)

# ---------- 机械合并：逐层户数 ----------
out_data = {"楼栋": {}}
if args.dxf:
    out_data["DXF文件"] = os.path.basename(args.dxf)

claimed = {}   # 列号 -> [单元描述]
for ci, bkey, ukey in mapping:
    col = cols[ci]
    floors = {}
    for fl, n in (col.get("逐层") or []):
        try:
            n = int(n)
        except (TypeError, ValueError):
            print(f"[assemble] 错误：列 {ci} 楼层 {fl!r} 户数非法：{n!r}")
            sys.exit(2)
        if n > 0:
            if fl in floors:
                print(f"[assemble] 错误：列 {ci} 楼层 {fl!r} 在逐层数据中重复出现")
                sys.exit(2)
            floors[fl] = {"户数": n}
    unit = out_data["楼栋"].setdefault(bkey, {"单元": {}})["单元"].setdefault(
        ukey, {"楼层表": {}, "分纤箱": []})
    unit["楼层表"] = floors
    claimed.setdefault(ci, []).append(f"{bkey}/{ukey}")

for ci, units in claimed.items():
    if len(units) > 1:
        hu = sum(int(n or 0) for _, n in (cols[ci].get("逐层") or []))
        print(f"[assemble] 共享列：列 {ci} 的逐层户数同时写入 {len(units)} 个单元"
              f"（{', '.join(units)}）——共享系统图克隆，每单元各 {hu} 户，请核对是否符合图纸事实")

# ---------- coverage 合并分纤箱（可选） ----------
cov_warn_unmatched = []
if args.coverage:
    try:
        with open(args.coverage, "r", encoding="utf-8") as f:
            raw_cov = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"[assemble] 错误：无法读取 coverage JSON {args.coverage}: {e}")
        sys.exit(2)
    bldg_source = raw_cov.get("楼栋", raw_cov) if isinstance(raw_cov, dict) else {}
    for bkey, bdata in bldg_source.items():
        if not isinstance(bdata, dict):
            continue
        units = bdata.get("单元", bdata) if isinstance(bdata, dict) else {}
        if not isinstance(units, dict):
            continue
        for ukey, udata in units.items():
            if not isinstance(udata, dict):
                continue
            uk = norm_unit(ukey, bkey)
            tgt = out_data["楼栋"].get(bkey, {}).get("单元", {}).get(uk)
            if tgt is None:
                # 归一后仍对不上：回退「1单元」——仅单单元楼（该楼栋组装结果仅 1单元）。
                # （单单元楼/配套楼的 coverage 单元键常写「X#配套楼」等非 N单元 形式）。
                # 2026-09-20 收紧：此前只要 1单元 存在就并入，多单元楼的错键
                # （如纯号码归一语义变化后的 N单元）会被静默并入 1单元致箱错位；
                # 现多单元楼不再回退，记入未匹配清单交人判断（与下方告警抑制同条件）。
                # 仍对不上则记入未匹配清单，不猜、不静默丢。
                _asm1 = out_data["楼栋"].get(bkey, {}).get("单元", {})
                fb = _asm1.get("1单元")
                if fb is not None and len(_asm1) == 1:
                    print(f"[assemble] 单元键回退：{bkey} 的 coverage 单元 {ukey!r} 归一为 {uk!r} 后无对应，"
                          f"已按单单元楼并入 1单元")
                    tgt = fb
                else:
                    if fb is not None:
                        print(f"[assemble] 单元键未回退：{bkey} 的 coverage 单元 {ukey!r} 归一为 {uk!r} 后无对应，"
                              f"但该楼栋有多单元 {sorted(_asm1)}，不并入 1单元，记入未匹配清单")
                    cov_warn_unmatched.append(f"{bkey}/{uk}")
                    continue
            boxes = []
            fx_list = udata.get("分纤箱", [])
            if isinstance(fx_list, list) and fx_list and isinstance(fx_list[0], dict):
                # 格式②：[{编号, 安装楼层, 覆盖范围线索:...}, ...] 原样保留
                for fx in fx_list:
                    if fx.get("编号"):
                        boxes.append(fx)
            tgt["分纤箱"] = boxes

    # 覆盖里有、组装结果里没有的单元 → 显式列出（可能漏映射，交人判断）
    # 解析规则与上方合并一致：归一键命中、或单单元楼 1单元 回退，任一成立即算已覆盖
    for bkey in bldg_source:
        if not isinstance(bldg_source.get(bkey), dict):
            continue
        units = bldg_source[bkey].get("单元", bldg_source[bkey])
        if not isinstance(units, dict):
            continue
        asm_units = out_data.get("楼栋", {}).get(bkey, {}).get("单元", {})
        for ukey in units:
            uk = norm_unit(ukey, bkey)
            # 2026-09-20 收紧（与上方合并同条件）：仅单单元楼抑制告警；
            # 多单元楼的未匹配键必须显式告警，不得以“有 1单元”一笔带过。
            if uk in asm_units or (len(asm_units) == 1 and "1单元" in asm_units):
                continue
            if f"{bkey}/{uk}" not in cov_warn_unmatched:
                cov_warn_unmatched.append(f"{bkey}/{uk}")

# ---------- 同配置展开（2026-09-26）：coverage 有箱但 col-map 无列的楼栋补入 ----------
# 动因：云峰 9#楼 2 单元（各 10 层×2 户=40 户）在系统图区无独立图标列，
#   col-map 未映射 → 产物缺 9#楼 → 出表丢 40 户，而旧逻辑只告警不补入。
# 规则：仅当 coverage 有覆盖楼层、且已组装楼栋中有覆盖楼层集合完全一致的
#   模板单元时，才复制模板楼层表补入（result_origin=derived，非直读）。
#   无模板 / 无覆盖楼层信息时不编造，保持告警不补入。无 coverage 时不展开。
# 退役条件：count_box 覆盖无图标列形态（画像申报 + 自动列发现）后删除本段（分支预算纪律 §十一）。
if args.coverage and cov_warn_unmatched:
    def _cov_floor_set(fx_list):
        s = set()
        if isinstance(fx_list, list):
            for fx in fx_list:
                if not isinstance(fx, dict):
                    continue
                clue = fx.get("覆盖范围线索") or {}
                if not isinstance(clue, dict):
                    continue
                for fl in (clue.get("覆盖楼层") or []):
                    s.add(str(fl).strip())
        return s

    # 模板索引：已组装且楼层表非空、且有覆盖楼层信息的单元
    _tmpl = []  # [(楼栋, 单元, frozenset(覆盖楼层))]
    for _tb, _bv in (out_data.get("楼栋") or {}).items():
        _us = (_bv or {}).get("单元") or {}
        for _tu, _ud in _us.items():
            if not isinstance(_ud, dict):
                continue
            if not (_ud.get("楼层表") or {}):
                continue
            _fs = _cov_floor_set(_ud.get("分纤箱") or [])
            if not _fs:
                continue
            _tmpl.append((_tb, _tu, frozenset(_fs)))
    _tmpl.sort(key=lambda t: (len(t[0]), t[0], t[1]))

    _expanded = []
    for _entry in list(cov_warn_unmatched):
        if "/" in _entry:
            _eb, _eu = _entry.split("/", 1)
        else:
            _eb, _eu = _entry, "1单元"
        # 取该缺列单元的 coverage 覆盖楼层 + 原始分纤箱
        _cov_boxes = []
        _cov_floors = set()
        _src_units = {}
        try:
            _src_b = bldg_source.get(_eb)
            if isinstance(_src_b, dict):
                _src_units = _src_b.get("单元", _src_b)
        except Exception:
            _src_units = {}
        if isinstance(_src_units, dict):
            for _ok, _ov in _src_units.items():
                if not isinstance(_ov, dict):
                    continue
                if norm_unit(_ok, _eb) != _eu:
                    continue
                _bl = _ov.get("分纤箱") or []
                if isinstance(_bl, list):
                    _cov_boxes.extend(_bl)
            _cov_floors = _cov_floor_set(_cov_boxes)
        if not _cov_floors:
            print(f"[assemble] ⚠ 同配置展开：{_eb}/{_eu} 无图标列，且无覆盖楼层信息或无同配置模板"
                  f"（覆盖楼层：{sorted(_cov_floors) if _cov_floors else '未知'}），需人工补入，不编造户数")
            continue
        _cands = [(tb, tu) for (tb, tu, fs) in _tmpl if fs == frozenset(_cov_floors)]
        if not _cands:
            print(f"[assemble] ⚠ 同配置展开：{_eb}/{_eu} 无图标列，且无同配置模板"
                  f"（覆盖楼层：{sorted(_cov_floors)}），需人工补入，不编造户数")
            continue
        _tb, _tu = _cands[0]
        _tpl_floors = out_data["楼栋"][_tb]["单元"][_tu]["楼层表"]
        _new_floors = {}
        for _fl, _fv in _tpl_floors.items():
            _hu = int((_fv or {}).get("户数") or 0)
            # 2026-09-27二轮：同配置展开属按规则算出且待人工核对，两字段正交缺一不可
            # （旧实现只写origin，confirmation缺失即机器不可判）。
            _new_floors[_fl] = {"户数": _hu, "result_origin": "derived",
                                "result_confirmation": "pending"}
        _tgt = out_data["楼栋"].setdefault(_eb, {"单元": {}})["单元"].setdefault(
            _eu, {"楼层表": {}, "分纤箱": []})
        _tgt["楼层表"] = _new_floors
        if _cov_boxes:
            _tgt["分纤箱"] = [dict(fx) if isinstance(fx, dict) else fx for fx in _cov_boxes]
        _n = len(_new_floors)
        _tot = sum(int(v.get("户数") or 0) for v in _new_floors.values())
        _per_vals = sorted(set(int(v.get("户数") or 0) for v in _new_floors.values()))
        _per_detail = "、".join(f"{fl}:{_new_floors[fl].get('户数')}"
                                for fl in sorted(_new_floors))
        if len(_per_vals) == 1:
            _hu_txt = f"{_n} 层 × {_per_vals[0]} 户 = {_tot} 户"
        else:
            _hu_txt = f"{_n} 层共 {_tot} 户（每层户数：{_per_detail}）"
        print(f"[assemble] ⚠ 同配置展开：{_eb}/{_eu} 无图标列，按 {_tb}/{_tu} 同配置展开 {_hu_txt}"
              f"（覆盖楼层一致：{sorted(_cov_floors)}；模板每层户数：{_per_detail}；"
              f"result_origin=derived/result_confirmation=pending，非直读，请核对）")
        _expanded.append(_entry)
        # 2026-09-27二轮：展开项入产物级待核对清单（C9不扫assemble，此清单是唯一机读出口）。
        out_data.setdefault("同配置展开待核对", []).append({
            "对象": f"{_eb}/{_eu}", "模板": f"{_tb}/{_tu}",
            "覆盖楼层": sorted(_cov_floors), "户数": _per_detail,
            "result_origin": "derived", "result_confirmation": "pending",
            "说明": "无图标列，按同覆盖配置模板复制户数；须人工核对后才可进成品",
        })
    for _e in _expanded:
        if _e in cov_warn_unmatched:
            cov_warn_unmatched.remove(_e)

# ---------- 守恒统计 ----------
print("[assemble] 逐单元户数：")
total = 0
for bkey in sorted(out_data["楼栋"], key=lambda s: (len(s), s)):
    for ukey, udata in out_data["楼栋"][bkey]["单元"].items():
        hu = sum(int(f.get("户数") or 0) for f in udata["楼层表"].values())
        total += hu
        boxes = [fx.get("编号") for fx in udata["分纤箱"]]
        warn = "" if boxes else "  << 无分纤箱（出表将标『未分配』，除非 gen 另传 --coverage-json）"
        print(f"  {bkey} / {ukey}: 户数={hu} 箱={boxes}{warn}")

count_total = count.get("归层后总户数")
clone_extra = 0
per_col_units = {}
for ci, bkey, ukey in mapping:
    per_col_units.setdefault(ci, 0)
    per_col_units[ci] += 1
for ci, n_units in per_col_units.items():
    if n_units > 1:
        clone_extra += (n_units - 1) * sum(int(n or 0) for _, n in (cols[ci].get("逐层") or []))

print(f"[assemble] 合计户数 = {total}")
if count_total is not None:
    print(f"[assemble] count.json 归层后总户数 = {count_total}；"
          f"共享列克隆增量 = {clone_extra}；差值 = {total - int(count_total)}（应恰等于克隆增量）")
if cov_warn_unmatched:
    print(f"[assemble] 警告：coverage 中有 {len(cov_warn_unmatched)} 个单元在组装结果中不存在"
          f"（可能漏写 col-map，请核对）：{'、'.join(cov_warn_unmatched)}")

# ---------- 写出 ----------
# 产物写保护（2026-09-18）：同名已存在时默认改道 *_patched，
# 覆盖原始产物须显式 --force（原始输出一旦被自算值覆盖即不可复现）
# 来源指纹（2026-09-29 一百二十七·P0）：记录组装输入的 SHA256，gen 出表前核对
# “当前 coverage == 被 inspect 检查过的 coverage”，堵住陈旧验证旁路。
# apply-ruling 只改值不碰本段（整 dict 回写保留），故裁决后指纹依然有效。
out_data["provenance"] = {
    "count_sha256": sha256_file(args.count),
    "coverage_sha256": sha256_file(args.coverage) if args.coverage else None,
    "produced_by": "assemble_households.py",
}
real_out, diverted = protect_out_path(args.out, force=args.force, label="组装产物")
write_json(real_out, out_data)
print(f"[assemble] 已写出: {real_out}")
if diverted:
    print(f"[assemble] （原 --out {args.out} 未被改动）")
