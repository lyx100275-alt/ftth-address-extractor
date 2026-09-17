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
"""
import argparse
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

from ftth_common import setup_logger, bldg_num

log = setup_logger("merge_json")

ap = argparse.ArgumentParser(description="FTTH 多楼栋 JSON 合并")
ap.add_argument("--inputs", nargs="+", help="输入JSON文件列表（空格分隔）")
ap.add_argument("--input-dir", help="输入目录（读取目录下所有 *_解析结果.json）")
ap.add_argument("--out", required=True, help="输出合并JSON路径")
args = ap.parse_args()

# 收集输入文件
input_files = []
if args.inputs:
    input_files = args.inputs
elif args.input_dir:
    input_files = sorted(glob.glob(os.path.join(args.input_dir, "*_解析结果.json")))
else:
    log.error("需要指定 --inputs 或 --input-dir")
    sys.exit(1)

if not input_files:
    log.error("未找到输入JSON文件")
    sys.exit(1)

log.info(f"待合并文件: {len(input_files)} 个")

merged = {"楼栋": {}}

def bldg_num_local(name):
    return bldg_num(name)

for fpath in input_files:
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        log.warning(f"无法读取 {fpath}: {e}")
        continue

    fname = os.path.basename(fpath)
    log.info(f"  处理: {fname}")

    # 格式1：标准 parse_dxf_structured.py 输出（含 "楼栋" 键）
    if "楼栋" in data:
        for bldg_name, bldg_data in data["楼栋"].items():
            if bldg_name in merged["楼栋"]:
                log.warning(f"    楼栋 {bldg_name} 已存在，来自 {fname} 将覆盖")
            merged["楼栋"][bldg_name] = bldg_data
            n_units = len(bldg_data.get("单元", {}))
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
        merged["楼栋"][bldg_name] = {
            "标题": data.get("标题", ""),
            "单元": {
                "1单元": {
                    "楼层表": 楼层表,
                    "分纤箱": 分纤箱,
                }
            }
        }
        log.info(f"    {bldg_name}: {len(楼层表)} 层, {len(分纤箱)} 个分纤箱")

    # 格式3：直接含 "单元" 键
    elif "单元" in data:
        # 从文件名提取楼栋名
        m = re.match(r"(\d+)", fname)
        bldg_name = f"{m.group(1)}#楼" if m else fname.replace("_解析结果.json", "")
        merged["楼栋"][bldg_name] = data
        log.info(f"    {bldg_name}: {len(data.get('单元', {}))} 个单元")

    else:
        log.warning(f"    无法识别的JSON格式: {fname}")
        continue

# 按楼栋编号排序
sorted_buildings = {}
for name in sorted(merged["楼栋"].keys(), key=bldg_num_local):
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
os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
try:
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
except IOError as e:
    log.error(f"无法写入输出文件: {args.out}\n{e}")
    sys.exit(1)
log.info(f"已保存: {args.out}")
