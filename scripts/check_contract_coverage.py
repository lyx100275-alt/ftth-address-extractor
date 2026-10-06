#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""契约落地门禁 —— 把「契约是否真被机器执行」从口头警告变成 rc≠0 的硬信号。

背景（这是本脚本存在的唯一理由）
--------------------------------
L1-C8「结果状态契约」立了整天，而**产出方零落地** —— 于是 `inspect` 的 C9 闸门
恒为 SKIP、从未拦下任何东西，而文档读起来一切正常。该失效模式当时是靠
SKILL_CHANGELOG 里一句文字警告（「新增产出方时须同步落地」）兜住的，
**文字是给模型看的，不是给机器看的**：改了代码、忘了改警告，或新增一条契约
而无人记得登记，门禁全绿。

治法：把「谁产出、谁核、当前是否真落地」登记进 `version.json` 的
`contract_coverage` 段（**登记的唯一出处**），本脚本做机械对拍。

检查项（全部「登记声称 vs 仓库现实」，不含主观判断）
---------------------------------------------------
  K1 登记表存在且 contracts 非空；SKILL.md「L1 契约」段的 C 编号集合
     **双向一致** —— 文档新增 C11 未登记 → FAIL；登记了 C11 文档没有 → FAIL。
     （这是防止「新契约静默落地」的根闸门。）
  K2 每条登记的 `producer_scripts` / `checker_scripts` 文件**真实存在**。
  K3 `coverage` 取值 ∈ {enforced, declared, unenforced}；`unenforced` → FAIL。
  K4 `coverage=enforced` 但 `checker_scripts` 为空 → FAIL
     —— 这正是「只定义不产出」的机械形态：没有检查器就没有闸门。
  K5 `coverage=declared` → **WARN 并强制要求 `gap` 字段非空**，且逐条打印。
     允许存在无检查器的契约（诚实登记），但**不允许无声**。
  K6 每条登记须带 `title` 与 `evidence`（证据字段）——「有登记无证据」等于
     把断言搬家，不算落地。

退出码（沿用 L1-C2 门禁契约语义）
--------------------------------
  0 = 全部登记与仓库现实一致（可能带 WARN：declared 契约）
  2 = **停**：登记与现实不一致 —— 先补齐落地或改登记，再改别的
  3 = 早失败：找不到 version.json / SKILL.md（**无可核对象**）
      —— 刻意不判「通过」：缺登记表本身就是本门禁要治的病。

用法：python scripts/check_contract_coverage.py [--root <技能目录>] [--json <机读输出>]
"""
import argparse
import io
import json
import os
import re
import sys

# 控制台 UTF-8 兜底：中文 Windows 默认 GBK，print CJK 即崩。
# 实现与 ftth_common.ensure_console_utf8 等价，**内联而非 import** —— 与
# check_budget.py / check_transitions.py 同为「刻意零依赖的门禁入口」，
# 冒烟 T1c 已把这一类脚本列入 write_json 出口豁免（见 run_smoke.py T1c 注释）。
for _s in (sys.stdout, sys.stderr):
    try:
        _rec = getattr(_s, "reconfigure", None)
        if callable(_rec):
            _rec(encoding="utf-8", errors="replace")
    except Exception:
        pass

COVERAGE_VALUES = ("enforced", "declared", "unenforced")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ftth_common import write_json  # noqa: E402  （JSON 出口统一入口，冒烟 T1c 出口锁）

# SKILL.md「L1 契约」段的契约标题形态：### C<n> <名称>
_C_HEAD = re.compile(r"^###\s+C(\d+)\s+\S", re.M)


def _out(msg):
    sys.stdout.write(msg + "\n")


def _err(msg):
    sys.stderr.write(msg + "\n")


def skill_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def l1_contract_ids(skill_md):
    """取 SKILL.md「L1 契约」段的 C 编号集合。

    刻意**只取 L1 段**：Step 2 自检的 C1~C10 是另一根轴（同名不同物），
    两轴混在一起对拍必然误报。两轴各自的门禁是 check_docs.py D4。
    """
    m = re.search(r"^##\s+L1\s*契约.*?$", skill_md, re.M)
    if not m:
        return None, "SKILL.md 未找到「## L1 契约」段标题"
    start = m.end()
    nxt = re.search(r"^##\s+\S", skill_md[start:], re.M)
    seg = skill_md[start:start + nxt.start()] if nxt else skill_md[start:]
    ids = {int(x) for x in _C_HEAD.findall(seg)}
    if not ids:
        return None, "SKILL.md「L1 契约」段未解析出任何 `### C<n>` 标题"
    return ids, ""


def check(root):
    """→ (violations, warns, notes)"""
    viol, warns, notes = [], [], []

    vp = os.path.join(root, "version.json")
    sp = os.path.join(root, "SKILL.md")
    for p in (vp, sp):
        if not os.path.isfile(p):
            viol.append("缺文件：%s —— 无可核对象，不得判通过。" % os.path.basename(p))
    if viol:
        return viol, warns, notes

    try:
        vobj = json.loads(read(vp))
    except Exception as e:                                    # noqa: BLE001
        viol.append("version.json 解析失败：%s" % e)
        return viol, warns, notes

    reg = vobj.get("contract_coverage")
    if not isinstance(reg, dict):
        viol.append("version.json 无 contract_coverage 段 —— 契约落地未登记，"
                    "本门禁无从核对（「只定义不产出」的机械形态）。")
        return viol, warns, notes
    contracts = reg.get("contracts")
    if not isinstance(contracts, dict) or not contracts:
        viol.append("contract_coverage.contracts 为空或非字典 —— "
                    "不得用空集合判 PASS（没核 ≠ 核过了）。")
        return viol, warns, notes

    # ---- K1 双向对拍：文档 C 编号集合 vs 登记表键集合 ----
    doc_ids, why = l1_contract_ids(read(sp))
    if doc_ids is None:
        viol.append(why)
    else:
        reg_ids = set()
        for k in contracts:
            m = re.fullmatch(r"C(\d+)", k)
            if not m:
                viol.append("登记表键 %r 不是 C<n> 形态（无法与文档对拍）。" % k)
            else:
                reg_ids.add(int(m.group(1)))
        notes.append("SKILL.md L1 契约 %d 条（C%d~C%d） / 登记 %d 条"
                     % (len(doc_ids), min(doc_ids), max(doc_ids), len(reg_ids)))
        only_doc = sorted(doc_ids - reg_ids)
        only_reg = sorted(reg_ids - doc_ids)
        if only_doc:
            viol.append("SKILL.md 有契约未登记：%s —— 新增契约必须同刻登记"
                        "（producer / checker / coverage），否则本门禁无从核对。"
                        % "、".join("C%d" % i for i in only_doc))
        if only_reg:
            viol.append("登记表有 SKILL.md 不存在的契约：%s —— 登记不得超前于契约正文。"
                        % "、".join("C%d" % i for i in only_reg))

    # ---- K2~K6 逐条核对 ----
    for cid in sorted(contracts, key=lambda s: (len(s), s)):
        c = contracts[cid]
        if not isinstance(c, dict):
            viol.append("%s 登记项不是字典。" % cid)
            continue
        title = c.get("title") or ""
        cov = c.get("coverage")
        prod = c.get("producer_scripts") or []
        chks = c.get("checker_scripts") or []

        if not title:
            viol.append("%s 缺 title。" % cid)
        if not c.get("evidence"):
            # K6：有登记无证据 = 把断言搬家，不算落地
            viol.append("%s 缺 evidence（落地证据）—— 登记必须写清「谁在何处落地了什么」。" % cid)
        # K6b：**evidence 内容对拍**。字段非空是形式对拍，写错内容照样全绿 ——
        # 实测 C3/C9 两条登记的 evidence 与代码现实不符（C3 说 check_contracts 核
        # handoff，实际该文件对 handoff/completeness 零命中；C9 说 evidence_builder
        # 持 E-HUMAN-RULING 枚举，实际它的枚举是 SOURCE_* 前缀），而两条都被判
        # enforced 通过。故：登记须给出 `evidence_tokens`（落地处的字面标识符），
        # 本检查逐个在 producer/checker 脚本里找 —— 找不到即 evidence 写错。
        toks = c.get("evidence_tokens")
        if isinstance(toks, list):
            hay = ""
            for rel in list(prod or []) + list(chks or []):
                fp = os.path.join(root, rel.replace("/", os.sep))
                if os.path.isfile(fp):
                    try:
                        hay += read(fp)
                    except Exception:                                   # noqa: BLE001
                        pass
            if hay:
                lost = [str(x) for x in toks if str(x) and str(x) not in hay]
                if lost:
                    viol.append("%s evidence_tokens 在登记的脚本里找不到：%s —— "
                                "evidence 与代码现实不符（字段非空不等于内容属实）。"
                                % (cid, "、".join(lost)))
        if cov not in COVERAGE_VALUES:
            viol.append("%s coverage=%r 不在 %s 内。" % (cid, cov, list(COVERAGE_VALUES)))
            continue
        if not isinstance(prod, list) or not isinstance(chks, list):
            viol.append("%s producer_scripts / checker_scripts 必须是列表。" % cid)
            continue
        for rel in list(prod) + list(chks):
            if not os.path.isfile(os.path.join(root, rel.replace("/", os.sep))):
                viol.append("%s 登记的脚本不存在：%s —— 登记声称的落地方在仓库里找不到。"
                            % (cid, rel))
        if cov == "unenforced":
            viol.append("%s coverage=unenforced（尚无产出方）—— 契约不得停留在无产出状态。" % cid)
        elif cov == "enforced" and not chks:
            viol.append("%s coverage=enforced 但 checker_scripts 为空 —— 没有检查器就没有闸门，"
                        "这是「只定义不产出」的机械形态。" % cid)
        elif cov == "declared":
            gap = (c.get("gap") or "").strip()
            if not gap:
                viol.append("%s coverage=declared 但缺 gap 说明 —— 无检查器可以，"
                            "无声不可以。" % cid)
            else:
                warns.append("%s %s —— declared（无独立检查器）：%s" % (cid, title, gap))
        else:
            notes.append("%s %s —— enforced（产出 %d 处 / 检查 %d 处）"
                         % (cid, title, len(prod), len(chks)))
    return viol, warns, notes


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="契约落地门禁：核 version.json contract_coverage 登记与仓库现实一致")
    ap.add_argument("--root", default=None, help="技能目录；默认 = 本脚本 scripts/ 的上一级")
    ap.add_argument("--json", dest="json_out", default=None, help="机读结果输出路径（可选）")
    a = ap.parse_args(argv)

    root = a.root or skill_root()
    _out("[契约落地门禁] %s" % os.path.abspath(root))
    viol, warns, notes = check(root)
    for n in notes:
        _out("  · %s" % n)
    if warns:
        _out("  [提示 %d]" % len(warns))
        for w in warns:
            _out("    ! %s" % w)
    if viol:
        _out("  [不一致 %d]" % len(viol))
        for v in viol:
            _out("    × %s" % v)
        _out("  → rc=2：先补齐落地或改登记，再改别的；新增契约必须同刻登记。")
        rc = 2
    else:
        _out("  [通过] 契约登记与仓库现实一致。")
        rc = 0

    if a.json_out:
        # JSON 出口统一走 write_json（冒烟 T1c 的出口锁），与 check_transitions.py 同规。
        write_json(a.json_out, {"root": os.path.abspath(root), "violations": viol,
                                "warns": warns, "notes": notes, "rc": rc})
        _out("  机读结果 -> %s" % os.path.abspath(a.json_out))
    return rc


if __name__ == "__main__":
    sys.exit(main())