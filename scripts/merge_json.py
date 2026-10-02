#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTTH 多楼栋 JSON 合并脚本
将多个单栋解析JSON（parse_dxf_structured.py 输出的 flat 结构）合并为
gen_addressbook.py 期望的嵌套结构 {楼栋: {单元: {楼层表, 分纤箱}}}。

用法：
    python merge_json.py --inputs 1楼_解析结果.json 2楼_解析结果.json ... --out 全小区_合并.json
    python merge_json.py --input-dir 解析结果目录/ --out 全小区_合并.json

说明：
- 输入JSON格式：{"楼栋": {"1#楼": {"单元": {"1单元": {...}}}, ...}} 或 {"楼层户数表": {..., "分纤箱": [...]}
- 输出格式：{"楼栋": {"1#楼": {"单元": {"1单元": {"楼层表": {...}, "分纤箱": [...]}}}}}
- 自动按楼栋编号排序。
- 同名楼栋跨输入默认冲突即停（rc=2，不写 --out，冲突详情写 <out>_conflict.json）；
  确认为同一物理楼时传 --allow-overwrite 显式放行覆盖（L0-I5-A）。
"""
import argparse
import glob
import json
import os
import re
import sys

from ftth_common import setup_logger, bldg_num, ensure_console_utf8, write_json

ensure_console_utf8()

log = setup_logger("merge_json")

ap = argparse.ArgumentParser(description="FTTH 多楼栋 JSON 合并")
ap.add_argument("--inputs", nargs="+", help="输入JSON文件列表（空格分隔）")
ap.add_argument("--input-dir", help="输入目录（读取目录下所有 *_解析结果.json）")
ap.add_argument("--out", required=True, help="输出合并JSON路径")
ap.add_argument("--allow-overwrite", action="store_true",
                help="同名楼栋确为同一物理楼时显式放行覆盖（默认冲突即停 rc=2）")
args = ap.parse_args()

# 收集输入文件
input_files = []
if args.inputs:
    input_files = args.inputs
elif args.input_dir:
    input_files = sorted(glob.glob(os.path.join(args.input_dir, "*_解析结果.json")))
else:
    log.error("需要指定 --inputs 或 --input-dir")
    sys.exit(2)  # 2026-09-25（opencode 三审）：输入类错误按 L1-C2 应为 rc=2

if not input_files:
    log.error("未找到输入JSON文件")
    sys.exit(2)  # 2026-09-25（opencode 三审）：同上

log.info(f"待合并文件: {len(input_files)} 个")

merged = {"楼栋": {}}

# 楼号排序直接用共享入口 ftth_common.bldg_num（失败返 0，排最前）。
# 此处曾有 `bldg_num_local` 薄包装（2026-09-18 七十三遗留），仅一处调用，已内联删除。

# 同名楼栋跨输入登记：楼名 -> [{来源, 单元数, 箱数}]（2026-09-26 一百零六：
# 跨输入同名楼栋可能是同名异楼，多地块合并场景自动覆盖即整栋丢箱，按 L0-I4 冲突即停）。
def _count_units_boxes(bldg_data):
    units = bldg_data.get("单元", {}) if isinstance(bldg_data, dict) else {}
    n_units = len(units)
    n_boxes = 0
    for ud in units.values():
        if isinstance(ud, dict):
            boxes = ud.get("分纤箱", [])
            if isinstance(boxes, list):
                n_boxes += len(boxes)
    return n_units, n_boxes


bldg_sources = {}  # bldg_name -> list[{来源(完整路径), 单元数, 箱数}]

# 2026-09-26（一百零七·问题 16）：来源标识只记 basename，同名输入
# （如 8 带全叫 parsed.json）无法溯源。改后：登记存完整路径（abspath，
# conflict.json 可溯源），控制台显示父目录+basename 短格式（可读）。
def _src_full(fpath):
    try:
        return os.path.abspath(fpath)
    except (OSError, ValueError):
        return fpath


def _src_short(full):
    base = os.path.basename(full)
    parent = os.path.basename(os.path.dirname(full))
    return "%s/%s" % (parent, base) if parent else base


def _register(bldg_name, bldg_data, src):
    n_units, n_boxes = _count_units_boxes(bldg_data)
    bldg_sources.setdefault(bldg_name, []).append(
        {"来源": src, "单元数": n_units, "箱数": n_boxes})
    if bldg_name in merged["楼栋"]:
        if args.allow_overwrite:
            merged["楼栋"][bldg_name] = bldg_data
        # 默认冲突即停：保留首见版本，待循环结束后统一报冲突退出
        return True
    merged["楼栋"][bldg_name] = bldg_data
    return False


for fpath in input_files:
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        log.warning(f"无法读取 {fpath}: {e}")
        continue

    fname = os.path.basename(fpath)  # 仅用于格式2/3的楼栋名提取（正则/后缀逻辑），不作来源标识
    src_full = _src_full(fpath)  # 登记与 conflict.json 用：完整路径
    src_short = _src_short(src_full)  # 控制台用：父目录+basename
    log.info(f"  处理: {src_short}")

    # 格式1：标准 parse_dxf_structured.py 输出（含 "楼栋" 键）
    if "楼栋" in data:
        for bldg_name, bldg_data in data["楼栋"].items():
            _register(bldg_name, bldg_data, src_full)
            n_units = len(bldg_data.get("单元", {})) if isinstance(bldg_data, dict) else 0
            log.info(f"    {bldg_name}: {n_units} 个单元")

    # 格式2：flat 结构（含 "楼层户数表" 和 "分纤箱" 键）
    elif "楼层户数表" in data:
        # 从文件名提取楼栋名（如 "1楼_解析结果.json" -> "1#楼"）
        m = re.match(r"(\d+)", fname)
        if m:
            bldg_name = f"{m.group(1)}#楼"
        else:
            bldg_name = fname.replace("_解析结果.json", "")

        # 构造 gen_addressbook.py 期望的结构
        楼层表 = {}
        for fl, info in data["楼层户数表"].items():
            if isinstance(info, dict):
                楼层表[fl] = info
            elif isinstance(info, (int, float)):
                楼层表[fl] = {"户数": int(info)}
            else:
                楼层表[fl] = {"户数": None}

        分纤箱 = data.get("分纤箱", [])
        _register(bldg_name, {
            "标题": data.get("标题", ""),
            "单元": {
                "1单元": {
                    "楼层表": 楼层表,
                    "分纤箱": 分纤箱,
                }
            }
        }, src_full)
        log.info(f"    {bldg_name}: {len(楼层表)} 层, {len(分纤箱)} 个分纤箱")

    # 格式3：直接含 "单元" 键
    elif "单元" in data:
        # 从文件名提取楼栋名
        m = re.match(r"(\d+)", fname)
        bldg_name = f"{m.group(1)}#楼" if m else fname.replace("_解析结果.json", "")
        _register(bldg_name, data, src_full)
        log.info(f"    {bldg_name}: {len(data.get('单元', {}))} 个单元")

    else:
        log.warning(f"    无法识别的JSON格式: {src_short}")
        continue

# 同名楼栋跨输入冲突判定（按楼名一条汇总，列出所有来源）
conflicts = {k: v for k, v in bldg_sources.items() if len(v) > 1}
if conflicts:
    for bldg_name in sorted(conflicts.keys(), key=bldg_num):
        srcs = conflicts[bldg_name]
        detail = "；".join(
            f"{_src_short(s['来源'])}（{s['单元数']}单元/{s['箱数']}箱）" for s in srcs)
        if args.allow_overwrite:
            log.warning(f"    楼栋 {bldg_name} 在 {len(srcs)} 个输入中重复，已按 --allow-overwrite 覆盖（保留末见版本）：{detail}")
        else:
            log.error(f"[FAIL] 楼栋 {bldg_name} 在 {len(srcs)} 个输入中重复（疑似同名异楼，需人工裁决）：{detail}")

if conflicts and not args.allow_overwrite:
    log.error("合并中止：检测到跨输入同名楼栋（同名异楼 vs 同楼跨图需人工裁决，不得自动覆盖）。"
              "确认同为同一物理楼时传 --allow-overwrite 显式放行；"
              "多地块同名异楼请先改名消歧后再合并。")
    conflict_path = args.out
    if conflict_path.lower().endswith(".json"):
        conflict_path = conflict_path[:-5] + "_conflict.json"
    else:
        conflict_path = conflict_path + "_conflict.json"
    try:
        write_json(conflict_path, {"status": "FAIL", "reason": "跨输入同名楼栋",
                                   "conflicts": conflicts}, log=log)
        log.info(f"冲突详情已写入备查：{conflict_path}")
    except OSError as e:  # C2 rc=4：写盘失败（同本文件正式产物出口；IOError 过窄）
        log.error(f"无法写入冲突详情文件：{conflict_path}\n{e}")
        sys.exit(4)
    sys.exit(2)

# 按楼栋编号排序
sorted_buildings = {}
for name in sorted(merged["楼栋"].keys(), key=bldg_num):
    sorted_buildings[name] = merged["楼栋"][name]
merged["楼栋"] = sorted_buildings

# 统计
total_units = 0
total_floors = 0
total_boxes = 0
for bldg_name, bldg_data in merged["楼栋"].items():
    units = bldg_data.get("单元", {})
    total_units += len(units)
    for unit_data in units.values():
        total_floors += len(unit_data.get("楼层表", {}))
        total_boxes += len(unit_data.get("分纤箱", []))

log.info(f"\n合并完成: {len(merged['楼栋'])} 栋楼, {total_units} 个单元, {total_floors} 个楼层记录, {total_boxes} 个分纤箱")

# 写入
try:
    write_json(args.out, merged, log=log)
except OSError as e:  # C2 rc=4：写盘失败（含ensure_parent；IOError过窄）
    log.error(f"无法写入输出文件: {args.out}\n{e}")
    sys.exit(4)  # C2 rc=4：写盘失败
log.info(f"已保存: {args.out}")
