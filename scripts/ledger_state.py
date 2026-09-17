#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""状态台账 —— 会话期间三本台账（理解快照 / 裁决台账 / 别名台账）的读写载体。

为什么需要它（与既有脚本的分工）：
  `ledger_elements.py` 是**图侧**台账：一张图上有哪些元素、各在哪，一次性从 DXF 算出、只读。
  本脚本是**会话侧**台账：随作业推进而增长的**状态记录**，三本各管一件事 ——
    ① 理解快照  已确认理解（值 + 来源 + 状态）；下一阶段先读它，未变更的项不得重新推导
    ② 裁决台账  人工裁决（问题 + 裁决原文 + 裁决人 + 适用范围）；裁决跨通道生效的唯一方式
    ③ 别名台账  归一化映射（canonical_id + raw_labels + 判据）；原始写法在产物里的落点
  口径见 references/operations_discipline.md §六 / §七 / §八。

为什么必须落盘（实测依据，非设计偏好）：
  · 长任务里「重新建立全局理解」的推理占**全部推理字符的 26.3%**（对照：一次性把待裁决项
    交人的会话仅 6.7%）。根因是已确认理解没有落盘 —— 换个视角看就得把全局重推一遍。
  · 同一项目在两个通道（GUI 会话 / IM 会话）并行时，A 通道收到的裁决 B 通道看不见，
    同一张图两次交付相差 122 户。落盘是唯一能让裁决跨通道生效的方式。

设计约束（与技能总则一致）：
  · **本脚本只记录，不裁决** —— 检出冲突只报警、不自动取舍（不得静默择一）。
  · **裁决 / 别名台账 append-only**；理解快照按 key 覆盖但保留 `历史`。
  · **缺项显式**：台账不存在时报「未初始化」并给 rc=3，不当成"空台账"混过去。
  · **不预设项目参数**：项目目录由命令行传入，三本台账文件名固定，内容结构通用。

用法：
  python scripts/ledger_state.py init         --project-dir <项目目录>
  python scripts/ledger_state.py snapshot-set --project-dir D --key K --value V --source S [--status 已确认]
  python scripts/ledger_state.py snapshot-get --project-dir D [--key K]
  python scripts/ledger_state.py ruling-add   --project-dir D --question Q --ruling R --by X [--scope S] [--key K]
  python scripts/ledger_state.py alias-add    --project-dir D --canonical C --raw r1,r2 --evidence E [--status 已确认]
  python scripts/ledger_state.py pending      --project-dir D [--md OUT.md]
  python scripts/ledger_state.py check        --project-dir D

退出码（对齐 SKILL.md L1-C2 门禁契约）：
  0  正常（`check` 时＝无待裁决项）
  2  输入不足：`check` 检出「待裁决且未裁决」项 → 不得直接出表
  3  早失败：台账未初始化 / 指定 key 不存在（附补救命令）
"""
import argparse
import datetime
import io
import json
import os
import sys

SNAP_NAME = "理解快照.json"
RULE_NAME = "裁决台账.json"
ALIAS_NAME = "别名台账.json"

SNAP_SCHEMA = "ftth.understanding_snapshot/v1"
RULE_SCHEMA = "ftth.ruling_ledger/v1"
ALIAS_SCHEMA = "ftth.alias_ledger/v1"

ST_OK = "已确认"
ST_PENDING = "待裁决"
ST_RULED = "已裁决"
ST_VALUES = (ST_OK, ST_PENDING, ST_RULED)

# C5 四列（待确认项统一格式，见 SKILL.md L1-C5）
C5_COLS = ["问题", "图纸已知事实", "参考线索", "需要您裁决的内容"]


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _out(msg):
    sys.stdout.write(msg + "\n")


def _err(msg):
    sys.stderr.write(msg + "\n")


def _setup_stdout():
    """Windows 控制台默认非 UTF-8 时，中文输出会炸；能改则改，改不了降级。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _paths(d):
    d = os.path.abspath(d)
    return {
        "dir": d,
        "snap": os.path.join(d, SNAP_NAME),
        "rule": os.path.join(d, RULE_NAME),
        "alias": os.path.join(d, ALIAS_NAME),
    }


def _blank(schema, project):
    # 条目类型随台账而异：快照按 key 索引（dict），裁决/别名按序追加（list）。
    return {"schema": schema, "项目": project or "", "更新时间": _now(),
            "条目": {} if schema == SNAP_SCHEMA else []}


class _Parser(argparse.ArgumentParser):
    """把命令行用法错误也归到 rc=3（早失败），与 L1-C2 的 rc=2「输入不足」区分开。

    argparse 默认 exit(2)，会与门禁语义撞车 —— rc=2 在本技能意味着
    「有未作答项 / 坐标缺失，须补探查」，而"少写了 --source"不是那回事，
    误用 rc=2 会让上游把用法错误当成图纸问题去补探查。
    """

    def error(self, message):
        self.print_usage(sys.stderr)
        _err("%s: error: %s" % (self.prog, message))
        _err("（用法错误按 rc=3 早失败上报；rc=2 专表图纸输入不足，两者不得混用。）")
        sys.exit(3)


def _load(path, schema, project, missing_rc=3, label=""):
    """读台账。不存在 → 返回 None 并提示（由调用方决定 rc）。

    刻意不自动建空文件：**"文件不存在"与"台账为空"是两件事**，
    自动建空会把"从未落盘过"伪装成"已落盘但无内容"。
    """
    if not os.path.exists(path):
        return None
    try:
        with io.open(path, encoding="utf-8") as f:
            obj = json.load(f)
    except Exception as e:
        _err("[台账损坏] %s 无法解析：%s" % (path, e))
        _err("   处置：人工核对后用备份替换，或改名后重跑 init（不得静默重建、不得丢弃已有记录）。")
        sys.exit(3)
    if obj.get("schema") != schema:
        _err("[版本不符] %s 的 schema=%r，本脚本要求 %r。" % (path, obj.get("schema"), schema))
        _err("   处置：确认是否混用了不同版本技能的台账；不要直接覆盖。")
        sys.exit(3)
    return obj


def _save(path, obj):
    obj["更新时间"] = _now()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")
    os.replace(tmp, path)
    return path


def _require(obj, cmd, hint):
    if obj is None:
        _err("[未初始化] 台账不存在，本命令不做隐式创建（见下）。")
        _err("   先跑：python scripts/ledger_state.py init %s" % hint)
        sys.exit(3)
    return obj


def _pick_entries(obj):
    """兼容 条目 为 dict（快照按 key）与 list（裁决/别名按序）。"""
    e = obj.get("条目")
    return e if isinstance(e, (dict, list)) else {}


# ---------------------------------------------------------------- init
def cmd_init(a):
    p = _paths(a.project_dir)
    os.makedirs(p["dir"], exist_ok=True)
    made, kept = [], []
    for path, schema, name in (
        (p["snap"], SNAP_SCHEMA, SNAP_NAME),
        (p["rule"], RULE_SCHEMA, RULE_NAME),
        (p["alias"], ALIAS_SCHEMA, ALIAS_NAME),
    ):
        if os.path.exists(path):
            kept.append(name)          # 已存在 → 不动，绝不清空
            continue
        _save(path, _blank(schema, a.project))
        made.append(name)
    _out("[项目目录] %s" % p["dir"])
    if made:
        _out("[已创建]   %s" % "  ".join(made))
    if kept:
        _out("[已存在]   %s（原样保留，未改动）" % "  ".join(kept))
    _out("下一步：snapshot-set 记已确认理解 / ruling-add 记人工裁决 / alias-add 记原始异写。")
    return 0


# ------------------------------------------------------------ snapshot
def cmd_snapshot_set(a):
    p = _paths(a.project_dir)
    obj = _require(_load(p["snap"], SNAP_SCHEMA, a.project), "snapshot-set", "--project-dir %s" % a.project_dir)
    if a.status not in ST_VALUES:
        _err("[参数错误] --status 只能是 %s 之一。" % " / ".join(ST_VALUES))
        return 3
    if not a.source:
        _err("[参数错误] --source 必填：快照项必须自带来源（哪个读数/哪条命令/哪条标注），")
        _err("           否则下一阶段无法判断它是否仍然成立。")
        return 3
    entries = _pick_entries(obj)
    old = entries.get(a.key)
    hist = list((old or {}).get("历史") or [])
    if old:
        hist.append({k: old.get(k) for k in ("值", "来源", "状态", "裁决人", "更新时间") if k in old})
    entries[a.key] = {
        "值": a.value,
        "来源": a.source,
        "状态": a.status,
        "裁决人": (a.by or ""),
        "更新时间": _now(),
        "历史": hist,
    }
    obj["条目"] = entries
    _save(p["snap"], obj)
    _out("[快照已写] %s" % a.key)
    _out("  值   = %s" % a.value)
    _out("  来源 = %s" % a.source)
    _out("  状态 = %s%s" % (a.status, ("（裁决人 %s）" % a.by) if a.by else ""))
    if hist:
        _out("  （覆盖旧值，已保留 %d 条历史）" % len(hist))
    return 0


def cmd_snapshot_get(a):
    p = _paths(a.project_dir)
    obj = _load(p["snap"], SNAP_SCHEMA, a.project)
    if obj is None:
        _err("[未初始化] %s 不存在。先跑 init。" % p["snap"])
        return 3
    entries = _pick_entries(obj)
    if not entries:
        _out("[快照为空] 尚未记录任何已确认理解。")
        return 0
    if a.key:
        item = entries.get(a.key)
        if item is None:
            _err("[无此项] 快照里没有 key=%r。" % a.key)
            _err("   已知 key：" + "、".join(sorted(entries.keys())))
            return 3
        _out("%s = %s" % (a.key, item.get("值")))
        _out("  来源 = %s" % item.get("来源"))
        _out("  状态 = %s%s" % (item.get("状态"), ("（裁决人 %s）" % item.get("裁决人")) if item.get("裁决人") else ""))
        return 0
    # 全量：按状态分组打印，**下一阶段先读它**
    by = {}
    for k, v in entries.items():
        by.setdefault(v.get("状态") or "未标", []).append(k)
    _out("[理解快照] 共 %d 项（%s）" % (len(entries), os.path.relpath(p["snap"], p["dir"])))
    for st in (ST_OK, ST_RULED, ST_PENDING):
        keys = by.get(st) or []
        if not keys:
            continue
        _out("  %s（%d）：" % (st, len(keys)))
        for k in sorted(keys):
            it = entries[k]
            _out("    · %s = %s  ← %s" % (k, it.get("值"), it.get("来源")))
    other = [k for k in by if k not in ST_VALUES]
    if other:
        _out("  状态异常（%d）：%s" % (len(other), "、".join(sorted(other))))
    return 0


# --------------------------------------------------------------- ruling
def cmd_ruling_add(a):
    p = _paths(a.project_dir)
    obj = _require(_load(p["rule"], RULE_SCHEMA, a.project), "ruling-add", "--project-dir %s" % a.project_dir)
    entries = _pick_entries(obj)
    if not isinstance(entries, list):
        _err("[结构异常] 裁决台账的 条目 应为列表。")
        return 3
    if not a.by:
        _err("[参数错误] --by 必填（裁决人）。没有裁决人的「裁决」不算落盘，")
        _err("           无法在返工复核时追溯是谁定的。")
        return 3
    rid = "R%03d" % (len(entries) + 1)
    entries.append({
        "id": rid,
        "问题": a.question,
        "裁决原文": a.ruling,
        "裁决人": a.by,
        "时间": _now(),
        "适用范围": a.scope or "",
    })
    obj["条目"] = entries
    _save(p["rule"], obj)
    _out("[裁决已落盘] %s  裁决人=%s" % (rid, a.by))
    _out("  问题：%s" % a.question)
    _out("  裁决：%s" % a.ruling)
    if a.scope:
        _out("  适用范围：%s" % a.scope)
    # 显式给了 --key 才联动快照；不猜、不自动匹配（避免静默改状态）
    if a.key:
        snap = _load(p["snap"], SNAP_SCHEMA, a.project)
        if snap is None:
            _out("[提示] --key %r 未联动：理解快照尚未初始化。" % a.key)
        else:
            se = _pick_entries(snap)
            it = se.get(a.key)
            if it is None:
                _out("[提示] --key %r 未联动：快照无此项（不自动新建）。" % a.key)
            else:
                it["状态"] = ST_RULED
                it["裁决人"] = a.by
                it["更新时间"] = _now()
                _save(p["snap"], snap)
                _out("[已联动] 快照项 %r 状态 → %s（裁决人 %s）" % (a.key, ST_RULED, a.by))
    return 0


# ---------------------------------------------------------------- alias
def cmd_alias_add(a):
    p = _paths(a.project_dir)
    obj = _require(_load(p["alias"], ALIAS_SCHEMA, a.project), "alias-add", "--project-dir %s" % a.project_dir)
    entries = _pick_entries(obj)
    if not isinstance(entries, list):
        _err("[结构异常] 别名台账的 条目 应为列表。")
        return 3
    if a.status not in (ST_OK, ST_PENDING):
        _err("[参数错误] --status 只能是 %s / %s（别名台账不存「已裁决」状态，裁决进裁决台账）。"
             % (ST_OK, ST_PENDING))
        return 3
    raws = [x.strip() for x in (a.raw or "").replace("，", ",").split(",") if x.strip()]
    if not raws:
        _err("[参数错误] --raw 必填：至少给一个原始写法。")
        return 3
    # 判据是硬要求：§5.1 硬边界 2 —— 归组前须先证是同一物理体，判据限「坐标邻近 + 连线关系」
    if a.status == ST_OK and not a.evidence:
        _err("[参数错误] 状态为「已确认」时 --evidence（判据）必填，且须可外部复核：")
        _err("           限「坐标邻近 + 连线关系」两类，不接受『看起来像』。")
        _err("           判据不足时请用 --status 待裁决 先入账，不要标已确认。")
        return 3
    # 冲突检测：同一 raw 写法不得同时挂到两个 canonical_id（§八）
    clash = []
    for it in entries:
        if it.get("canonical_id") == a.canonical:
            continue
        for r in raws:
            if r in (it.get("raw_labels") or []):
                clash.append((r, it.get("canonical_id")))
    if clash:
        _err("[冲突] 以下原始写法已挂在别的 canonical_id 下，本脚本**不自动择一**：")
        for r, c in clash:
            _err("   %r 已属 %r，本次又属 %r" % (r, c, a.canonical))
        _err("   处置：按 operations_discipline.md §八 —— 立即拆开并按 §5.3 第④类报人。")
        return 2
    entries.append({
        "canonical_id": a.canonical,
        "raw_labels": raws,
        "判据": a.evidence or "",
        "状态": a.status,
        "时间": _now(),
    })
    obj["条目"] = entries
    _save(p["alias"], obj)
    _out("[别名已落盘] %s ← %s  状态=%s" % (a.canonical, "、".join(raws), a.status))
    if a.evidence:
        _out("  判据：%s" % a.evidence)
    _out("  提示：状态为「已确认」的别名方可写入成品别名列；「待裁决」的只列待确认项。")
    return 0


# -------------------------------------------------------------- pending
def cmd_pending(a):
    p = _paths(a.project_dir)
    snap = _load(p["snap"], SNAP_SCHEMA, a.project)
    alias = _load(p["alias"], ALIAS_SCHEMA, a.project)
    if snap is None and alias is None:
        _err("[未初始化] 理解快照与别名台账都不存在。先跑 init。")
        return 3
    items = []
    for k, v in (_pick_entries(snap) or {}).items():
        if v.get("状态") == ST_PENDING:
            items.append({
                "来源台账": SNAP_NAME, "标识": k,
                "问题": k,
                "图纸已知事实": v.get("值") or "",
                "参考线索": v.get("来源") or "",
                "需要您裁决的内容": "",
            })
    for i, t in enumerate((_pick_entries(alias) or [])):
        if t.get("状态") == ST_PENDING:
            items.append({
                "来源台账": ALIAS_NAME, "标识": t.get("canonical_id") or ("条目%d" % (i + 1)),
                "问题": "别名归组待裁决：%s ← %s" % (t.get("canonical_id"), "、".join(t.get("raw_labels") or [])),
                "图纸已知事实": t.get("判据") or "",
                "参考线索": "",
                "需要您裁决的内容": "",
            })
    if not items:
        _out("[无待裁决项] 理解快照与别名台账中均无「%s」条目。" % ST_PENDING)
        return 0
    _out("[待裁决 %d 项] —— 按 C5 四列格式，建议**攒到阶段末一次性提交**" % len(items))
    _out("（逐条打断与「约 70% 墙钟耗在等用户回话」直接对冲，见 operations_discipline.md §二·1）")
    _out("")
    for n, it in enumerate(items, 1):
        _out("%d) [%s / %s]" % (n, it["来源台账"], it["标识"]))
        for c in C5_COLS:
            val = it.get(c) or "（待补）"
            _out("   %s：%s" % (c, val))
        _out("")
    if a.md:
        lines = ["| " + " | ".join(C5_COLS) + " |", "|" + "---|" * len(C5_COLS)]
        for it in items:
            lines.append("| " + " | ".join((it.get(c) or "").replace("|", "\\|") for c in C5_COLS) + " |")
        with io.open(a.md, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        _out("[已导出] %s" % os.path.abspath(a.md))
    return 0


# ---------------------------------------------------------------- check
def cmd_check(a):
    p = _paths(a.project_dir)
    snap = _load(p["snap"], SNAP_SCHEMA, a.project)
    rule = _load(p["rule"], RULE_SCHEMA, a.project)
    alias = _load(p["alias"], ALIAS_SCHEMA, a.project)
    if snap is None and rule is None and alias is None:
        _err("[未初始化] 三本台账都不存在。先跑 init。")
        return 3
    warns, blockers = [], []

    se = _pick_entries(snap) or {}
    re_ = _pick_entries(rule) or []
    ae = _pick_entries(alias) or []

    # ① 裁决台账自检：必须有裁决人（无裁决人＝只在对话里说的，不算落盘）
    for it in re_:
        if not it.get("裁决人"):
            warns.append("裁决台账 %s 缺「裁决人」—— 无法追溯，不构成有效落盘。" % it.get("id"))

    # ② 快照标「已裁决」但裁决台账为空 → 状态没有出处
    if any(v.get("状态") == ST_RULED for v in se.values()) and not re_:
        warns.append("快照中存在「%s」项，但裁决台账为空 —— 裁决没有出处（可能只在对话里说了）。" % ST_RULED)

    # ③ 待裁决项
    pend_snap = [k for k, v in se.items() if v.get("状态") == ST_PENDING]
    pend_alias = [t.get("canonical_id") for t in ae if t.get("状态") == ST_PENDING]
    n_pend = len(pend_snap) + len(pend_alias)
    if n_pend:
        blockers.append("存在 %d 项「%s」未裁决：快照 %s%s" % (
            n_pend, ST_PENDING,
            "、".join(pend_snap) or "无",
            ("；别名 " + "、".join(str(x) for x in pend_alias)) if pend_alias else ""))
        blockers.append("→ 按 operations_discipline.md §5.3 第④类：未裁决值不得进入成品；"
                        "跑 `pending` 取 C5 四列表批量提交。")

    # ④ 别名台账：已确认但无判据 / 同一 raw 挂两个 canonical
    seen = {}
    for t in ae:
        if t.get("状态") == ST_OK and not t.get("判据"):
            warns.append("别名台账 %r 标「%s」但无判据（§5.1 硬边界 2 要求判据可外部复核）。"
                         % (t.get("canonical_id"), ST_OK))
        for r in t.get("raw_labels") or []:
            seen.setdefault(r, []).append(t.get("canonical_id"))
    for r, cs in seen.items():
        if len(cs) > 1:
            blockers.append("原始写法 %r 同时挂在 %s 下 —— 冲突，归属未定（§八：须报人，不得择一）。"
                            % (r, "、".join(str(c) for c in cs)))

    # ⑤ 快照项缺来源（来源是"能否在下阶段复用"的判据）
    for k, v in se.items():
        if not v.get("来源"):
            warns.append("快照项 %r 缺「来源」—— 下一阶段无法判断它是否仍成立。" % k)

    _out("[台账自检] %s" % p["dir"])
    _out("  理解快照 %d 项 / 裁决台账 %d 条 / 别名台账 %d 条" % (len(se), len(re_), len(ae)))
    if warns:
        _out("  [警告 %d]" % len(warns))
        for w in warns:
            _out("    ! %s" % w)
    if blockers:
        _out("  [阻断 %d]" % len(blockers))
        for b in blockers:
            _out("    × %s" % b)
        return 2
    if not warns:
        _out("  无不一致项。")
    return 0


def main(argv=None):
    _setup_stdout()
    ap = _Parser(
        description="状态台账（理解快照 / 裁决台账 / 别名台账）；只记录、不裁决")
    sub = ap.add_subparsers(dest="cmd", required=True, parser_class=_Parser)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project-dir", required=True, help="项目目录（三本台账所在目录）")
    common.add_argument("--project", default=None, help="项目名（写入台账的项目字段，可选）")

    sp = sub.add_parser("init", parents=[common], help="初始化三本台账（已存在的原样保留）")
    sp.set_defaults(func=cmd_init)

    s = sub.add_parser("snapshot-set", parents=[common], help="写入/更新一条已确认理解")
    s.add_argument("--key", required=True, help="条目键（如「3#楼-2单元-刻度列」）")
    s.add_argument("--value", required=True, help="该条理解的值")
    s.add_argument("--source", required=True, help="来源：哪个读数/哪条命令/哪条标注")
    s.add_argument("--status", default=ST_OK, help="%s / %s / %s（默认 %s）" % (ST_OK, ST_PENDING, ST_RULED, ST_OK))
    s.add_argument("--by", default=None, help="裁决人（--status 已裁决 时填）")
    s.set_defaults(func=cmd_snapshot_set)

    g = sub.add_parser("snapshot-get", parents=[common], help="读回理解快照（下一阶段先跑这个）")
    g.add_argument("--key", default=None, help="只读某一项；不给则全量分组打印")
    g.set_defaults(func=cmd_snapshot_get)

    r = sub.add_parser("ruling-add", parents=[common], help="追加一条人工裁决")
    r.add_argument("--question", required=True, help="被裁决的问题")
    r.add_argument("--ruling", required=True, help="裁决原文（用户原话）")
    r.add_argument("--by", required=True, help="裁决人")
    r.add_argument("--scope", default=None, help="适用范围")
    r.add_argument("--key", default=None, help="可选：联动同名的快照项状态 → 已裁决")
    r.set_defaults(func=cmd_ruling_add)

    al = sub.add_parser("alias-add", parents=[common], help="追加一条别名归组（归一化映射）")
    al.add_argument("--canonical", required=True, help="规范写法 canonical_id")
    al.add_argument("--raw", required=True, help="原始写法，逗号分隔")
    al.add_argument("--evidence", default=None, help="判据（坐标邻近 + 连线关系）；标已确认时必填")
    al.add_argument("--status", default=ST_OK, help="%s / %s（默认 %s）" % (ST_OK, ST_PENDING, ST_OK))
    al.set_defaults(func=cmd_alias_add)

    pd = sub.add_parser("pending", parents=[common], help="汇总待裁决项（C5 四列格式）")
    pd.add_argument("--md", default=None, help="另存为 Markdown 表，便于直接提交")
    pd.set_defaults(func=cmd_pending)

    ck = sub.add_parser("check", parents=[common], help="三本台账一致性自检（有未裁决项 → rc=2）")
    ck.set_defaults(func=cmd_check)

    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
