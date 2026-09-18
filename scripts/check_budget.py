#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SKILL.md / references 体量闸门（阈值取自 version.json，单一权威）。

背景
----
SKILL.md「参考文件」节写着体量预算纪律：

    预警线 47,000 B（触及即新增内容默认进 references/，本文件只留引用）
    硬上限 49,000 B（触及即禁写，必须先外移再新增）

并注明本文件是每次会话**首屏全量加载**的唯一文件，宿主对工具输出有**通用截断
（实测 51,200 B，无开关）** —— 超出即静默截断。实测被截掉的正是该条纪律的后半段
与整张 references 索引表（11 个文件的入口表），文件都在、入口没了。

但 `47000 / 49000 / 51200` 在 scripts/ 全部脚本中 **0 命中**：规则写了、**没有执行方**。
本脚本即该纪律的执行方，作用是把「体量超限」在**写坏之前**变成 rc≠0 的硬信号。

阈值来源（单一权威）
--------------------
一律读 `<技能目录>/version.json` 的 `budget` 段。本脚本内的 DEFAULTS 仅在
version.json 缺段时兜底，且输出会**显式标注实际来源** —— 不制造第二套阈值口径。

退出码（沿用 SKILL.md L1-C2 语义）
----------------------------------
  0 = 通过（可能带 WARN：触及预警线但未触硬上限）
  2 = **停**：触及硬上限或宿主截断线 —— 必须先外移再新增
  3 = 早失败：找不到 SKILL.md（**无可核对象**）—— 不得输出成"通过"
"""
import argparse
import glob
import json
import os
import sys

DEFAULT_BUDGET = {
    "warning_bytes": 47000,
    "hard_limit_bytes": 49000,
    "host_truncation_bytes": 51200,
}


def skill_root():
    """技能目录 = 本脚本所在 scripts/ 的上一级。"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_budget(root):
    """读 version.json 的 budget 段；缺段则兜底并如实标注来源。"""
    p = os.path.join(root, "version.json")
    fallback_why = None
    obj = None
    if not os.path.exists(p):
        fallback_why = "version.json 不存在"
    else:
        try:
            with open(p, encoding="utf-8") as f:
                obj = json.load(f)
        except Exception as e:
            fallback_why = "version.json 解析失败（%s）" % e

    if obj is None:
        return dict(DEFAULT_BUDGET), "内置兜底（%s）" % fallback_why

    b = obj.get("budget")
    if not isinstance(b, dict):
        return dict(DEFAULT_BUDGET), "内置兜底（version.json 无 budget 段）"

    got = 0
    out = dict(DEFAULT_BUDGET)
    for k in DEFAULT_BUDGET:
        if isinstance(b.get(k), int) and b[k] > 0:
            out[k] = b[k]
            got += 1
    return out, "version.json budget 段（%d/%d 项生效）" % (got, len(DEFAULT_BUDGET))


def judge(size, budget):
    """→ (state, rc_contribution, 说明)"""
    warn = budget["warning_bytes"]
    hard = budget["hard_limit_bytes"]
    trunc = budget["host_truncation_bytes"]
    if size >= trunc:
        return "FAIL", 2, "超宿主截断线 +%d B（会被静默截断）" % (size - trunc)
    if size >= hard:
        return "FAIL", 2, "超硬上限 +%d B（禁写，须先外移）" % (size - hard)
    if size >= warn:
        return "WARN", 0, "触及预警线 +%d B（新增内容默认进 references/）" % (size - warn)
    return "OK", 0, "距预警线还有 %d B" % (warn - size)


def main():
    ap = argparse.ArgumentParser(
        description="SKILL.md / references 体量闸门（阈值取自 version.json，单一权威）")
    ap.add_argument("--root", default=None,
                    help="技能目录；默认 = 本脚本所在目录的上一级")
    ap.add_argument("--json", dest="json_out", default=None,
                    help="把结果写成 JSON（机器可读）")
    a = ap.parse_args()

    root = a.root or skill_root()
    budget, source = load_budget(root)
    warn = budget["warning_bytes"]
    hard = budget["hard_limit_bytes"]
    trunc = budget["host_truncation_bytes"]

    print("[体量闸门] %s" % os.path.abspath(root))
    print("  阈值来源：%s" % source)
    print("  预警线 %d B / 硬上限 %d B / 宿主截断 %d B" % (warn, hard, trunc))
    print()

    sk = os.path.join(root, "SKILL.md")
    if not os.path.exists(sk):
        print("  [早失败] 找不到 SKILL.md —— 无可核对象，**不得视为通过**。")
        return 3

    rc = 0
    sk_size = os.path.getsize(sk)
    state, drc, note = judge(sk_size, budget)
    rc = max(rc, drc)
    print("  SKILL.md  %d B  [%s] %s" % (sk_size, state, note))

    # references 单文件同受约束（否则闸门只是把问题搬家）
    refs = sorted(glob.glob(os.path.join(root, "references", "*.md")))
    print()
    if not refs:
        print("  references/*.md：**0 个文件** —— 未核到任何对象，"
              "不得据此判「通过」（目录缺失或为空须人工确认）。")
    else:
        worst = None
        print("  references/*.md（%d 个文件）" % len(refs))
        for p in refs:
            sz = os.path.getsize(p)
            st, d, nt = judge(sz, budget)
            rc = max(rc, d)
            if st != "OK":
                print("    %-38s %7d B  [%s] %s" % (os.path.basename(p), sz, st, nt))
            if worst is None or sz > worst[1]:
                worst = (os.path.basename(p), sz)
        print("    最大者：%s %d B（%s）" % (worst[0], worst[1], judge(worst[1], budget)[0]))
        n_bad = sum(1 for p in refs if judge(os.path.getsize(p), budget)[0] != "OK")
        if n_bad == 0:
            print("    全部 references 文件均在预警线内。")

    print()
    if rc == 0:
        print("  结论：未触及硬上限 —— 可继续新增；若 SKILL.md 为 [WARN]，新增内容进 references/。")
    else:
        print("  结论：**停**。先外移再新增；宿主截断不可配置，把阈值调到截断线之上没有意义。")

    if a.json_out:
        payload = {
            "root": os.path.abspath(root),
            "threshold_source": source,
            "budget": budget,
            "skill_md": {"bytes": sk_size, "state": state, "note": note},
            "references": [{"file": os.path.basename(p), "bytes": os.path.getsize(p),
                            "state": judge(os.path.getsize(p), budget)[0]}
                           for p in refs],
            "rc": rc,
        }
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print("  [out] JSON 已写入 %s" % a.json_out)

    print("  → rc=%d" % rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
