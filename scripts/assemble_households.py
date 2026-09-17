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
from ftth_common import protect_out_path

sys.stdout.reconfigure(encoding="utf-8")

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
    sys.exit(1)

cols = count.get("列")
if not isinstance(cols, list) or not cols:
    print("[assemble] 错误：count JSON 中没有「列」数组（确认输入是 count_box_icons.py 的输出）")
    sys.exit(1)


def norm_unit(ukey, bkey=None):
    """单元键归一（与 gen_addressbook._norm_unit_key 同则）：N单元 / 楼栋N单元 / 楼栋名→1单元"""
    s = str(ukey).strip()
    if not s:
        return s
    m = re.search(r"(\d+)\s*[#号]?\s*楼?\s*(\d+)\s*单元", s)
    if m:
        return "%s单元" % m.group(2)
    m2 = re.fullmatch(r"(\d+)\s*单元", s)
    if m2:
        return "%s单元" % m2.group(1)
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
            sys.exit(1)
        left, right = item.split("=", 1)
        left = left.strip()
        if not left.isdigit():
            print(f"[assemble] 错误：列号必须是数字：{left!r}（条目 {item!r}）")
            sys.exit(1)
        ci = int(left)
        if ci < 0 or ci >= len(cols):
            print(f"[assemble] 错误：列号 {ci} 越界（count.json 共 {len(cols)} 列，0 基）")
            sys.exit(1)
        units = [u.strip() for u in right.split(",") if u.strip()]
        if not units:
            print(f"[assemble] 错误：条目 {item!r} 没有给出任何 楼栋/单元")
            sys.exit(1)
        for u in units:
            if "/" in u:
                bkey, ukey = u.split("/", 1)
                bkey, ukey = bkey.strip(), ukey.strip()
            else:
                # 无斜杠：或为「楼栋N单元」全名，或为裸楼栋名（单单元楼 → 1单元）
                m = re.fullmatch(r"(.+?\d+\s*[#号]?\s*楼?)\s*(\d+\s*单元)", u)
                if m:
                    bkey, ukey = m.group(1).strip(), m.group(2).strip()
                else:
                    bkey, ukey = u, u
            ukey = norm_unit(ukey, bkey)
            out.append((ci, bkey, ukey))
    if not out:
        print("[assemble] 错误：col-map 为空")
        sys.exit(1)
    # 同一 (楼栋,单元) 只能被一列声明
    seen = {}
    for ci, bkey, ukey in out:
        key = (bkey, ukey)
        if key in seen:
            print(f"[assemble] 错误：(楼栋,单元) {bkey}/{ukey} 被列 {seen[key]} 和列 {ci} 同时声明——"
                  f"户数会翻倍。同一单元只能归属一列；如为共享系统图，把多个单元写在同一列的右侧。")
            sys.exit(1)
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
            sys.exit(1)
        if n > 0:
            if fl in floors:
                print(f"[assemble] 错误：列 {ci} 楼层 {fl!r} 在逐层数据中重复出现")
                sys.exit(1)
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
        sys.exit(1)
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
                # 归一后仍对不上：回退「1单元」——仅当该楼栋的 1单元 确实存在时
                # （单单元楼/配套楼的 coverage 单元键常写「X#配套楼」等非 N单元 形式）。
                # 仍对不上则记入未匹配清单，不猜、不静默丢。
                fb = out_data["楼栋"].get(bkey, {}).get("单元", {}).get("1单元")
                if fb is not None:
                    print(f"[assemble] 单元键回退：{bkey} 的 coverage 单元 {ukey!r} 归一为 {uk!r} 后无对应，"
                          f"已按单单元楼并入 1单元")
                    tgt = fb
                else:
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
    # 解析规则与上方合并一致：归一键或 1单元 回退，任一命中即算已覆盖
    for bkey in bldg_source:
        if not isinstance(bldg_source.get(bkey), dict):
            continue
        units = bldg_source[bkey].get("单元", bldg_source[bkey])
        if not isinstance(units, dict):
            continue
        asm_units = out_data.get("楼栋", {}).get(bkey, {}).get("单元", {})
        for ukey in units:
            uk = norm_unit(ukey, bkey)
            if uk in asm_units or "1单元" in asm_units:
                continue
            if f"{bkey}/{uk}" not in cov_warn_unmatched:
                cov_warn_unmatched.append(f"{bkey}/{uk}")

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
real_out, diverted = protect_out_path(args.out, force=args.force, label="组装产物")
d = os.path.dirname(os.path.abspath(real_out))
if d and not os.path.isdir(d):
    os.makedirs(d, exist_ok=True)
with open(real_out, "w", encoding="utf-8") as f:
    json.dump(out_data, f, ensure_ascii=False, indent=2)
print(f"[assemble] 已写出: {real_out}")
if diverted:
    print(f"[assemble] （原 --out {args.out} 未被改动）")
