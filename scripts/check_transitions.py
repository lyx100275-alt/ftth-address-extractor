#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""迁移门禁核对器 —— 把 SKILL.md「Agent 状态机（迁移门禁）」的禁止迁移表机械核对。

职责边界（**与 ledger_state.py check 互补，不重复**）
---------------------------------------------------
`ledger_state.py check` 核的是**三本台账内部一致性**（缺裁决人 / 缺来源 / 同一 raw 挂两个
canonical / 待裁决项阻断）。它**不知道成品有没有生成**。

本脚本的独有能力 = 把「台账里的状态」与「**成品是否已落盘**」做交叉核验。
「成品已生成」是迁移门禁能否被违反的唯一前提：没有成品，一切 pending 都还停在
USER VALIDATION 原地，不算违规；一旦成品落盘，同样的 pending 就构成硬违规。

机械判据（逐条对应 SKILL.md 禁止迁移表，条款号即 SKILL.md 表内编号）
-------------------------------------------------------------------
  #1 `unknown` → `confirmed`           快照项标「已确认」但 来源 缺失，或 来源 命中脚本默认值标记
  #2 `contradiction` → `OUTPUT`        成品已生成 且 裁决台账存在「待裁决」的冲突类条目
  #3 用脚本默认值 / 历史档案消除 pending  裁决台账标「已裁决」但 裁决人 缺失或为脚本/自动标记
  #4 `INSPECT` hard gate FAIL → `ASSEMBLE`  闭包检查结果 rc≠0（有 FAIL）且 成品已生成
  #5 `USER VALIDATION` 尚有 pending → `OUTPUT`  任一台账存在「待裁决」条目 且 成品已生成
  #6 申报态与证据不符（2026-10-02 新增，见下）  状态.json 的 `当前状态` 落在某节点，
     但台账/成品/闭包证据不支持该节点 —— 如申报 `LOCKED BASELINE` 而仍有 pending、
     申报 `OUTPUT`/`READ-BACK VALIDATION` 而成品不存在。

判据 #6 为什么需要（这是本脚本此前唯一的结构性缺口）
---------------------------------------------------
#1~#5 全部是「**禁止**的迁移有没有发生」，即**否定式**检查。否定式检查有个
固有盲区：**状态机没有正向锚点** —— 「我在哪个节点」全靠推断，于是：
  · 申报走到 `OUTPUT` 而成品根本没生成，没有任何判据会响（#2/#4/#5 都需要成品存在）；
  · 三本台账齐 + inspect rc=0 就被当成「已过 USER VALIDATION」，而实际上可能仍 pending。
`ledger_state.py state-set` 提供正向锚点（`状态.json`，`ftth.session_state/v1`），
本判据把它与实际证据对拍。**未申报不是违规**（老项目无此文件）→ 只判 WARN，
这样新增观测点不会把存量项目打成 rc=2。

**本脚本只做「有客观判据」的核对**：不推理、不替 Agent 判断某条 pending 该不该存在、
不自动择一。命中即停（rc=2），把处置交回 Agent 与人。

退出码（沿用 L1-C2 门禁契约语义）
--------------------------------
  0 = 全部禁止迁移均未发生，可继续。
  2 = **停**。命中至少一条禁止迁移 —— 不得出表 / 不得交付。
  3 = 早失败。参数不足 / 目录不存在，或**三本台账均不存在**（无可核对象）。
      刻意不对「无台账」给 rc=0：那会把「根本没核」显示成「核过了」。
      部分台账存在时按空处理并逐条标注缺哪本，仍照常核对。

字段一律复用 `ledger_state.py` 的常量（SNAP_NAME / RULE_NAME / ALIAS_NAME / ST_* /
*_SCHEMA），**本文件不得自造同义字段或副本常量** —— 否则形成第二权威口径。
"""

import argparse
import glob
import json
import os
import sys

# 控制台 UTF-8 兜底：中文 Windows 默认 GBK，print CJK 即崩；被替换的流则跳过。
# （共享实现见 ftth_common.ensure_console_utf8；本文件只依赖 ledger_state，故内联。）
for _s in (sys.stdout, sys.stderr):
    try:
        _rec = getattr(_s, "reconfigure", None)
        if callable(_rec):
            _rec(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger_state as LS  # noqa: E402  （同目录模块，复用其 schema 常量与读取函数）
from ftth_common import write_json  # noqa: E402  （产物写盘走统一入口，inf清洗+建父目录）

# 脚本默认值 / 自动标记：命中即视为「不是人的裁决」，用于判据 #1 与 #3。
# 这些是**形态匹配**（机械可判），不是对裁决内容的判断。
AUTO_MARKERS = ("默认值", "default", "auto", "自动", "脚本推定", "历史档案")

# 冲突类条目的形态匹配（判据 #2）。只做词面匹配，不判断冲突是否真实存在。
CONFLICT_MARKERS = ("冲突", "矛盾", "不一致", "conflict", "contradiction")

# 禁止迁移的条数（判据 #1~#6）。**唯一权威**，SKILL.md 禁止迁移表的行数由
# check_docs.py D12 对拍 —— 此前「5 条」在 docstring、通过语、SKILL.md 三处各写一遍，
# 加判据时必漏（本次加 #6 即命中：漏了通过语，机器查不出来）。
N_FORBIDDEN = 6


def _load_json(path):
    """读 JSON：缺席返 None（调用方按"未初始化/合法缺席"处置）；损坏/不可读
    同样返 None（保持既有容忍语义），但 stderr 留痕——损坏与缺席严格区分，
    否则坏文件被当成"没建台账"，永远定位不到（2026-09-26）。
    """
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        sys.stderr.write("[check_transitions] 读 %s 失败（视作缺席，请人工核对是否文件损坏）: %s\n" % (path, e))
        return None


def _entries(obj, default):
    """台账不存在时 _load 返回 None —— 必须在此拦截。

    实测教训：直接调 LS._pick_entries(None) 会 AttributeError 崩成 rc=1
    （Traceback 而非契约退出码），且崩点远离调用处。真机冒烟测试才发现 ——
    自测用例全部写了台账，恰好漏掉「台账从未初始化」这一最常见场景。
    不改 ledger_state.py（其 cmd_check 先判 None 故自身无此问题），在本层防御。
    """
    return LS._pick_entries(obj) if obj is not None else default


def _load_ledgers(project_dir, project):
    """按 ledger_state 的既有 schema 读取三本台账；缺失返回 None（不当错误）。"""
    p = LS._paths(project_dir)
    return {
        "dir": p["dir"],
        "snap": LS._load(p["snap"], LS.SNAP_SCHEMA, project),
        "rule": LS._load(p["rule"], LS.RULE_SCHEMA, project),
        "alias": LS._load(p["alias"], LS.ALIAS_SCHEMA, project),
    }


def _find_product(project_dir, explicit):
    """成品定位。

    实测教训（真机冒烟测试发现）：产物命名有**两种形态** ——
      `标准地址表*.xlsx`（.gitignore 采用的写法）与 `凤鸣朝阳标准地址表.xlsx`（项目名在前）。
    只按前缀匹配会把后者判成「未出表」，进而漏掉 #2/#4/#5 的成品交叉核验
    （假阴性 —— 比误报更危险，因为它给出绿灯）。

    故：包含式匹配 + 排除模板/备份类同名物 + 多候选取最新 mtime 并**列出全部候选**，
    选择结果打印在 facts 里供复核（不静默择一）。
    """
    if explicit:
        return explicit if os.path.exists(explicit) else None
    EXCLUDE = ("模板", "备份", "buk", "bak", "~$", "副本", "历史产物")
    cands = [p for p in glob.glob(os.path.join(project_dir, "*标准地址表*.xlsx"))
             if not any(x in os.path.basename(p) for x in EXCLUDE)]
    if not cands:
        return None
    return max(cands, key=os.path.getmtime)


def _product_candidates(project_dir):
    """供 facts 展示的候选清单（含被排除项，便于人复核排除是否合理）。"""
    EXCLUDE = ("模板", "备份", "buk", "bak", "~$", "副本", "历史产物")
    out = []
    for p in sorted(glob.glob(os.path.join(project_dir, "*标准地址表*.xlsx"))):
        n = os.path.basename(p)
        out.append("%s%s" % (n, "（已排除：备份/模板类）" if any(x in n for x in EXCLUDE) else ""))
    return out


def _has_auto_marker(s):
    s = (s or "").lower()
    return any(m.lower() in s for m in AUTO_MARKERS)


def _check_declared_state(led, product, closure, pend, viol, warns, facts):
    """判据 #6：申报态（状态.json）与实际证据对拍。

    设计取舍三条：
      1. **只对拍有客观证据的节点**。`PARSE`/`INSPECT` 这类节点的证据是"跑过某命令"，
         无产物可查 —— 机器判不了就不判（否则就成了假阳性来源）。
         可判的只有三类：① 申报 ≥ USER VALIDATION 却仍有 pending；
         ② 申报 ≥ ASSEMBLE 而闭包有 FAIL；③ 申报 ≥ OUTPUT 而成品不存在。
      2. **未申报只 WARN 不 FAIL**。存量项目没有状态.json，若据此 rc=2 就把
         「新增观测点」变成「破坏性变更」。
      3. **不判倒退**。回退（回 REPROBE / USER）是正常作业路径，不是违规。
    """
    p = LS._paths(led["dir"])
    st = _load_json(p["state"])
    if st is None:
        warns.append("状态.json 不存在 —— 当前态只能靠推断（三本台账齐 + inspect rc=0 ≈ "
                     "USER VALIDATION 之后），无机器证据。"
                     "申报入口：ledger_state.py state-set --state <节点名>")
        return
    cur = st.get("当前状态")
    rank = LS.state_rank(cur) if cur else -1
    if rank < 0:
        viol.append("#6 状态.json 的「当前状态」=%r 不在状态机枚举内 —— 申报态不可信，"
                    "先按 ledger_state.py 的枚举改正。" % (cur,))
        return
    facts.append("申报状态：%s（上一态 %s / %s）"
                 % (cur, st.get("上一状态") or "（首次）", st.get("方向") or "?"))

    # ① 申报已过 USER VALIDATION 却仍有 pending
    uv = LS.state_rank("USER VALIDATION")
    if rank >= uv and pend:
        viol.append("#6 申报状态=%s（已过 USER VALIDATION）但仍有 %d 项「%s」"
                    "—— 锁定基准未成立即声明越过，状态申报与证据不符。"
                    % (cur, len(pend), LS.ST_PENDING))
    # ② 申报已过 ASSEMBLE 而闭包有 FAIL
    asm = LS.state_rank("ASSEMBLE")
    if rank >= asm and closure is not None and closure.get("rc"):
        viol.append("#6 申报状态=%s（已过 ASSEMBLE）但闭包检查 rc=%s（FAIL %d 项）"
                    "—— hard gate 未过即声明进入组装。"
                    % (cur, closure.get("rc"), len(closure.get("fails") or [])))
    # ③ 申报已出表而成品不存在
    outp = LS.state_rank("OUTPUT")
    if rank >= outp and not product:
        viol.append("#6 申报状态=%s 但目录内未发现成品（标准地址表*.xlsx）"
                    "—— 声称已交付而无交付物。" % cur)


def check(project_dir, project, product, closure_path):
    """返回 (violations, warns, facts)。violations 非空 ⇒ rc=2。"""
    viol, warns, facts = [], [], []
    led = _load_ledgers(project_dir, project)
    se = _entries(led["snap"], {})
    re_ = _entries(led["rule"], [])
    ae = _entries(led["alias"], [])

    product = _find_product(project_dir, product)
    closure = _load_json(closure_path) if closure_path else None

    missing = [k for k in ("snap", "rule", "alias") if led[k] is None]
    facts.append("台账目录 %s：快照 %d 项 / 裁决 %d 条 / 别名 %d 条%s"
                 % (led["dir"], len(se), len(re_), len(ae),
                    ("（缺 %s）" % "、".join(missing)) if missing else ""))
    facts.append("成品：%s" % (product if product else "未发现（未出表）"))
    cands = _product_candidates(project_dir)
    if len(cands) > 1:
        facts.append("成品候选 %d 个：%s —— 取 mtime 最新者为成品" % (len(cands), "；".join(cands)))
    if len(missing) == 3:
        warns.append("三本台账均不存在 —— 无可核对象。落盘纪律见 operations_discipline.md §六。")
        if product:
            warns.append("且成品已存在（%s）：本次无法核对来源与确认状态，"
                         "该成品的可追溯性未获任何机器证据支持。"
                         % os.path.basename(product))
    if closure_path:
        if closure is None:
            warnings_only = "闭包结果读不出：%s（按未提供处理，判据 #4 跳过）" % closure_path
            warns.append(warnings_only)
        else:
            facts.append("闭包检查：rc=%s / FAIL %d 项"
                         % (closure.get("rc"), len(closure.get("fails") or [])))

    # ---- 判据 #1：unknown → confirmed（标已确认，但来源缺失或是脚本默认值） ----
    for k, v in se.items():
        if (v or {}).get("状态") != LS.ST_OK:
            continue
        src = (v or {}).get("来源") or ""
        if not src:
            viol.append("#1 %r 标「%s」但无「来源」—— 无法排除由 unknown 直接置为已确认。"
                        % (k, LS.ST_OK))
        elif _has_auto_marker(src):
            viol.append("#1 %r 标「%s」但「来源」为脚本默认值/自动标记（%r）"
                        "—— 属 L0-I5-D 禁止的「用脚本默认值消除 pending」。"
                        % (k, LS.ST_OK, src))

    # ---- 判据 #3：用脚本默认值 / 历史档案消除 pending（已裁决但无裁决人） ----
    for it in re_:
        if it.get("状态") != LS.ST_RULED:
            continue
        who = (it.get("裁决人") or "").strip()
        if not who:
            viol.append("#3 裁决台账 %s 标「%s」但无「裁决人」—— 只在对话里说过的不算锁定基准。"
                        % (it.get("id"), LS.ST_RULED))
        elif _has_auto_marker(who):
            viol.append("#3 裁决台账 %s 的「裁决人」为脚本/自动标记（%r）"
                        "—— 非人工裁决，不得据此消除 pending。" % (it.get("id"), who))

    # ---- 判据 #2 / #5：与成品交叉（只有成品落盘时才成立） ----
    pend = []
    for k, v in se.items():
        if (v or {}).get("状态") == LS.ST_PENDING:
            pend.append(("快照", k))
    for t in ae:
        if (t or {}).get("状态") == LS.ST_PENDING:
            pend.append(("别名", t.get("canonical_id")))
    for it in re_:
        if (it or {}).get("状态") == LS.ST_PENDING:
            pend.append(("裁决", it.get("id")))

    if product:
        for where, key in pend:
            viol.append("#5 %s台账存在「%s」项 %r，而成品已生成（%s）"
                        "—— 未裁决值不得进入成品。"
                        % (where, LS.ST_PENDING, key, os.path.basename(product)))
        for it in re_:
            prob = str(it.get("问题") or "")
            if it.get("状态") != LS.ST_RULED and any(m in prob.lower() or m in prob
                                                     for m in CONFLICT_MARKERS):
                viol.append("#2 裁决台账 %s 为冲突类条目且未裁决（问题=%r），而成品已生成"
                            "—— 矛盾不得流入成品。"
                            % (it.get("id"), prob[:60]))
    elif pend:
        warns.append("存在 %d 项「%s」但尚未出表 —— 处于 USER VALIDATION 阶段，"
                     "按状态机属正常等待，不构成违规。" % (len(pend), LS.ST_PENDING))

    # ---- 判据 #4：INSPECT hard gate FAIL → ASSEMBLE ----
    if closure and product and closure.get("rc"):
        viol.append("#4 闭包检查 rc=%s（FAIL %d 项）而成品已生成 —— hard gate FAIL 不得 ASSEMBLE。"
                    % (closure.get("rc"), len(closure.get("fails") or [])))
    # ---- 判据 #6：申报态与证据对拍（正向锚点，补 #1~#5 的否定式盲区）----
    _check_declared_state(led, product, closure, pend, viol, warns, facts)
    return viol, warns, facts, product, (len(missing) == 3)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="迁移门禁核对器：核 SKILL.md「禁止迁移」表 5 条（与成品落盘交叉核验）。")
    ap.add_argument("--project-dir", required=True, help="三本台账所在目录")
    ap.add_argument("--project", default=None, help="项目名（台账内字段，可选）")
    ap.add_argument("--product", default=None,
                    help="成品路径；不传则在该目录扫 标准地址表*.xlsx")
    ap.add_argument("--closure", default=None,
                    help="inspect_closure.py --json 的机读结果（可选，用于判据 #4）")
    ap.add_argument("--json", dest="json_out", default=None, help="机读结果输出路径（可选）")
    a = ap.parse_args(argv)

    if not os.path.isdir(a.project_dir):
        sys.stderr.write("[transitions] 目录不存在：%s\n" % a.project_dir)
        return 3

    viol, warns, facts, product, uninitialized = check(a.project_dir, a.project, a.product, a.closure)

    print("[迁移门禁核对] %s" % os.path.abspath(a.project_dir))
    for f in facts:
        print("  · %s" % f)
    if warns:
        print("  [提示 %d]" % len(warns))
        for w in warns:
            print("    ! %s" % w)
    if viol:
        print("  [禁止迁移命中 %d]" % len(viol))
        for v in viol:
            print("    × %s" % v)
        print("  → rc=2：停在当前位置，按 C5 四列报人；不得出表 / 不得交付。")
        rc = 2
    elif uninitialized:
        print("  → rc=3：早失败。三本台账均不存在，无可核对象；不给出「通过」结论"
              "（避免把「没核」误读成「核过了」）。")
        rc = 3
    else:
        print("  [通过] %d 条禁止迁移均未发生。" % N_FORBIDDEN)
        rc = 0

    if a.json_out:
        write_json(a.json_out, {"project_dir": os.path.abspath(a.project_dir),
                                "product": product, "closure": a.closure,
                                "violations": viol, "warns": warns, "rc": rc})
        print("机读结果 ->", a.json_out)
    return rc


if __name__ == "__main__":
    sys.exit(main())
