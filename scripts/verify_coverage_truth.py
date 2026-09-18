#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
覆盖范围验收脚本：用【已定稿的标准地址表】反查【覆盖范围JSON】，逐箱比对覆盖楼层。

为什么需要它：
    analyze_coverage.py 输出的永远是"线索"，不是结论。若手上有已定稿的标准地址表
    （含「分纤箱」列），则每行"户→分纤箱"的关系本身就是覆盖范围的**真值**。
    本脚本把真值聚合到「分纤箱 → 覆盖楼层集合」，与覆盖范围JSON里的线索逐箱比对，
    使"回归验收"可执行、可复现，而不是靠人肉翻表。

用法：
    python verify_coverage_truth.py <标准地址表.xlsx> <覆盖范围.json> [选项]

选项：
    --sheet 标准地址        工作表名（默认：自动取第一个含「分纤箱」列的表）
    --col-box 分纤箱        分纤箱列（按表头文字定位，默认「分纤箱」）
    --col-bldg 六级         楼栋列（默认「六级」，即九级地址的六级）
    --col-unit 七级         单元列（默认「七级」）
    --col-floor 八级        楼层列（默认「八级」）
    --col-door 九级         户号列（默认「九级」，仅用于计数校验）
    --json-key 覆盖范围线索 覆盖JSON里存放线索的键（默认「覆盖范围线索」）

退出码：
    0 = 全部一致；2 = 存在不一致或无法比对；1 = 输入/解析错误。
"""
import argparse
import json
import os
import re
import sys
from collections import OrderedDict

try:
    import openpyxl
except ImportError:
    print("缺少 openpyxl：请先 pip install openpyxl")
    sys.exit(1)

# 中文数字换算（`cn2num`）已上提为**共享实现**（2026-09-18）：全技能只保留
# `ftth_common.cn2num` 一份，此处保留同名绑定，调用点（norm_floor 等）无需改动。
# 上提理由：该逻辑原先仅存在于本脚本，任何新脚本要用就只能再抄一份 ——
# 「同一逻辑多份实现必然漂移，且漂移后没有任何东西会报错」是本技能反复踩过的坑。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ftth_common import cn2num  # noqa: E402


def norm_floor(name):
    """楼层名归一化 → 整数（B1/地下一层/-1F → -1；十七层/17F → 17）。无法识别返回 None。"""
    if name is None:
        return None
    t = str(name).replace("　", "").replace(" ", "").strip()
    t = re.sub(r"室$", "", t)
    m = re.fullmatch(r"(?:地下|负)([一二三四五六七八九十\d]+)层?", t)
    if m:
        v = cn2num(m.group(1))
        return -v if v else None
    m = re.fullmatch(r"[Bb](\d+)(?:层|F)?", t)
    if m:
        return -int(m.group(1))
    m = re.fullmatch(r"([一二三四五六七八九十\d]+)层", t)
    if m:
        return cn2num(m.group(1))
    m = re.fullmatch(r"(-?\d+)\s*[Ff]", t)
    if m:
        return int(m.group(1))
    return None


def summarize(floors):
    """把楼层整数集合压成区间串：[-1..9] → 'B1~9F'"""
    xs = sorted(x for x in floors if x is not None)
    if not xs:
        return "（无）"
    if xs == list(range(xs[0], xs[-1] + 1)):
        return f"{fmt(xs[0])}~{fmt(xs[-1])}"
    return "/".join(fmt(x) for x in xs)


def fmt(v):
    return f"B{-v}" if v < 0 else f"{v}F"


def main():
    ap = argparse.ArgumentParser(description="用标准地址表反查覆盖范围线索")
    ap.add_argument("xlsx", help="已定稿的标准地址表 xlsx")
    ap.add_argument("json", help="analyze_coverage.py 输出的覆盖范围 JSON")
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--col-box", default="分纤箱")
    ap.add_argument("--col-bldg", default="六级")
    ap.add_argument("--col-unit", default="七级")
    ap.add_argument("--col-floor", default="八级")
    ap.add_argument("--col-door", default="九级")
    ap.add_argument("--json-key", default="覆盖范围线索")
    args = ap.parse_args()

    wb = openpyxl.load_workbook(args.xlsx, data_only=True)
    ws = wb[args.sheet] if args.sheet else wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        print("标准地址表为空")
        return 1
    header = [("" if c is None else str(c).strip()) for c in rows[0]]

    def colidx(name):
        for i, h in enumerate(header):
            if h == name:
                return i
        for i, h in enumerate(header):
            if name in h:
                return i
        return None

    ci = {k: colidx(v) for k, v in
          (("box", args.col_box), ("bldg", args.col_bldg), ("unit", args.col_unit),
           ("floor", args.col_floor), ("door", args.col_door))}
    missing = [k for k, v in ci.items() if v is None]
    if missing:
        print(f"标准地址表缺少列：{missing}（表头：{header}）")
        return 1

    # 真值聚合：分纤箱 → {楼层整数: 户数}
    truth = OrderedDict()
    n_rows = 0
    for r in rows[1:]:
        if not r or r[ci["box"]] in (None, ""):
            continue
        box = str(r[ci["box"]]).strip()
        fl = norm_floor(r[ci["floor"]])
        n_rows += 1
        d = truth.setdefault(box, {"楼栋": str(r[ci["bldg"]] or ""), "单元": str(r[ci["unit"]] or ""),
                                   "楼层": OrderedDict(), "户数": 0})
        d["楼层"][fl] = d["楼层"].get(fl, 0) + 1
        d["户数"] += 1
    print(f"真值：{n_rows} 户 / {len(truth)} 个分纤箱")

    cov = json.load(open(args.json, encoding="utf-8"))
    got = {}   # box -> (楼栋, 单元, 覆盖集合, 来源)
    for bldg, bd in (cov.get("楼栋") or {}).items():
        for unit, ud in (bd.get("单元") or {}).items():
            for b in ud.get("分纤箱", []):
                box = str(b.get("编号", "")).strip()
                clue = b.get(args.json_key)
                if clue:
                    d = {norm_floor(x) for x in (clue.get("覆盖楼层") or [])}
                else:
                    d = set()
                got[box] = (bldg, unit, d, "线索" if clue else "无")

    print(f"线索：{len(got)} 个分纤箱\n")
    print("%-8s %-16s %-24s %-24s %s" % ("箱号", "归属(真值)", "真值覆盖", "线索覆盖", "结论"))
    print("-" * 104)
    bad = []
    for box, d in truth.items():
        tset = {x for x in d["楼层"] if x is not None}
        if box not in got:
            print("%-8s %-16s %-24s %-24s %s" % (box, f'{d["楼栋"]}{d["单元"]}', summarize(tset), "（未出现）", "✗ 未比对"))
            bad.append(box)
            continue
        gb, gu, gdef, src = got[box]
        if gdef == tset:
            verdict = "✓ 一致"
        else:
            verdict = "✗ 不一致"
            bad.append(box)
        print("%-8s %-16s %-24s %-24s %s" % (
            box, f'{d["楼栋"]}{d["单元"]}', summarize(tset), summarize(gdef), verdict))
        if verdict == "✗ 不一致":
            print("%-8s   差异：多 %s / 少 %s" % (
                "", summarize(gdef - tset), summarize(tset - gdef)))
            print("%-8s   线索覆盖：%s" % ("", summarize(gdef)))

    extra = [b for b in got if b not in truth]
    if extra:
        print("\n线索里有真值表没有的箱：%s" % extra)
    print("\n合计：一致 %d / 不一致 %d / 总计 %d"
          % (len(truth) - len(bad), len(bad), len(truth)))
    return 0 if not bad else 2


if __name__ == "__main__":
    sys.exit(main())
