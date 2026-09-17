#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTTH 多单元楼层户数拆分脚本
当一栋楼的楼层户数表是全楼的合计，需按单元拆分时使用。

用法：
    python split_units.py --input 解析结果.json --out 拆分后.json --rules 拆分规则.json

拆分规则 JSON 格式：
{
  "3#楼": {
    "1单元": {"1F": 2, "2F": 2, ...},
    "2单元": {"1F": 1, "2F": 2, ...}
  },
  ...
}

说明：
- --rules 中的规则是用户确认后的拆分方案，每单元每层各几户。
- 脚本读取原始解析JSON中的楼层户数表，按规则拆分到各单元。
- 拆分后输出标准嵌套结构 {楼栋: {单元: {楼层表, 分纤箱}}}。
- 未在规则中出现的楼层，从原表按比例或均分（需用户确认）。
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from ftth_common import setup_logger, bldg_num

log = setup_logger("split_units")

ap = argparse.ArgumentParser(description="FTTH 多单元楼层户数拆分")
ap.add_argument("--input", required=True, help="输入解析JSON（含楼层户数表的flat结构或标准结构）")
ap.add_argument("--rules", required=True, help="拆分规则JSON")
ap.add_argument("--out", required=True, help="输出拆分后JSON")
args = ap.parse_args()

# 读取输入
try:
    with open(args.input, "r", encoding="utf-8") as f:
        input_data = json.load(f)
except (IOError, json.JSONDecodeError) as e:
    log.error(f"无法读取输入JSON: {args.input}\n{e}")
    sys.exit(1)

# 读取拆分规则
try:
    with open(args.rules, "r", encoding="utf-8") as f:
        rules = json.load(f)
except (IOError, json.JSONDecodeError) as e:
    log.error(f"无法读取拆分规则JSON: {args.rules}\n{e}")
    sys.exit(1)

# 解析输入结构
buildings = {}  # {楼名: {原始楼层表, 分纤箱, 标题}}

if "楼栋" in input_data:
    # 标准结构
    for bldg_name, bldg_data in input_data["楼栋"].items():
        units = bldg_data.get("单元", {})
        # 合并所有单元的楼层表
        merged_floors = {}
        all_boxes = []
        for unit_name, unit_data in units.items():
            for fl, info in unit_data.get("楼层表", {}).items():
                if fl not in merged_floors:
                    merged_floors[fl] = info
                else:
                    # 合并户数
                    old_n = merged_floors[fl].get("户数", 0) or 0
                    new_n = info.get("户数", 0) or 0
                    merged_floors[fl]["户数"] = old_n + new_n
            all_boxes.extend(unit_data.get("分纤箱", []))
        buildings[bldg_name] = {"楼层表": merged_floors, "分纤箱": all_boxes, "标题": bldg_data.get("标题", "")}
elif "楼层户数表" in input_data:
    # flat结构
    import re
    m2 = re.match(r"(\d+)", os.path.basename(args.input))
    bldg_name = f"{m2.group(1)}#楼" if m2 else os.path.basename(args.input)
    buildings[bldg_name] = {
        "楼层表": input_data["楼层户数表"],
        "分纤箱": input_data.get("分纤箱", []),
        "标题": input_data.get("标题", ""),
    }

# 按规则拆分
result = {"楼栋": {}}

for bldg_name in sorted(buildings.keys(), key=bldg_num):
    bldg_data = buildings[bldg_name]
    orig_floors = bldg_data["楼层表"]
    all_boxes = bldg_data["分纤箱"]

    if bldg_name not in rules:
        # 不需要拆分，保持原样
        result["楼栋"][bldg_name] = {
            "标题": bldg_data["标题"],
            "单元": {"1单元": {"楼层表": orig_floors, "分纤箱": all_boxes}},
        }
        log.info(f"{bldg_name}: 无拆分规则，保持原样")
        continue

    bldg_rules = rules[bldg_name]
    units_out = {}

    # 分配分纤箱到各单元（按编号顺序或规则中单元数均分）
    unit_names = sorted(bldg_rules.keys(), key=lambda n: bldg_num(n) if bldg_num(n) else int(re.search(r"(\d+)", n).group(1)) if re.search(r"(\d+)", n) else 0)
    boxes_per_unit = max(1, len(all_boxes) // len(unit_names)) if all_boxes else 0
    box_idx = 0

    for unit_name in unit_names:
        unit_rules = bldg_rules[unit_name]
        unit_floors = {}
        for fl, n_hu in unit_rules.items():
            # 从原始楼层表复制其他信息（如布线），替换户数
            orig = orig_floors.get(fl, {})
            unit_floors[fl] = {
                "户数": n_hu,
                "布线": orig.get("布线") if isinstance(orig, dict) else None,
            }
        # 分配分纤箱
        unit_boxes = all_boxes[box_idx:box_idx + boxes_per_unit] if all_boxes else []
        box_idx += boxes_per_unit
        units_out[unit_name] = {"楼层表": unit_floors, "分纤箱": unit_boxes}
        log.info(f"  {bldg_name} {unit_name}: {len(unit_floors)} 层, {sum(v['户数'] for v in unit_floors.values() if v.get('户数'))} 户")

    result["楼栋"][bldg_name] = {"标题": bldg_data["标题"], "单元": units_out}

# 统计
total_households = 0
for bldg_name, bldg_data in result["楼栋"].items():
    for unit_data in bldg_data["单元"].values():
        for fl_info in unit_data.get("楼层表", {}).values():
            n = fl_info.get("户数")
            if n:
                total_households += int(n)
log.info(f"\n拆分完成: {len(result['楼栋'])} 栋楼, 共 {total_households} 户")

# 写入
os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
try:
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
except IOError as e:
    log.error(f"无法写入输出文件: {args.out}\n{e}")
    sys.exit(1)
log.info(f"已保存: {args.out}")
