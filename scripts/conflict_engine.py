#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""冲突引擎（V3 Phase 6 起步，2026-09-30 一百三十一）。

职责只有五件事（V3 §11）：
1. 发现冲突；2. 分类冲突；3. 保存证据；4. 给出冲突原因；5. 生成待裁决项。

不做的事（硬禁区，构造上保证）：
- 不比较谁对谁错、不自动择一、不写 settled——本文件无任何定案分支，
  所有 issue 的「状态」恒为 pending，只能由 human ruling 在外部闭环。
- 零外部依赖（只用 stdlib；不 import 任何业务模块）——杜绝循环导入，
  inspect/未来 ruling 只按名调用纯函数。

议题模型（机读出口 `inspect.json/conflict_issues` 的元素结构）：
- issue_id  确定性编号（同输入必同输出，供去重与跨产物追溯）
- 类型      ISSUE_* 封闭枚举（新增须同步 CHANGELOG 与 inspect 文案）
- 域        address（地址对象本身未定）/ relation（地址已定、与FX的关联未定；
            会审报告§三：两者不得混为一谈）
- 对象      冲突主体（箱编号 / 来源:路径，不编造归属）
- 候选      并存的候选值原文（只罗列，不排序、不推荐）
- 证据      坐标/口径/上下文原文（只抄录，不解释）
- 说明      人读原因（一句话，不含定案动词）
- 状态      恒为 "pending"
"""
__all__ = [
    "ISSUE_UNASSIGNED", "ISSUE_FXMAP_MISSING", "ISSUE_FXMAP_EXTRA",
    "ISSUE_FLOOR_MISMATCH", "ISSUE_MISSING_RECORD",
    "ISSUE_PENDING_STATE", "ISSUE_INVALID_STATE",
    "STATUS_PENDING",
    "DOMAIN_ADDRESS", "DOMAIN_RELATION",
    "domain_of",
    "make_issue_id", "issue", "summarize",
    "collect_unassigned", "collect_fxmap_gap", "fxmap_issues",
    "floor_mismatch_issue", "run_c9",
]

# ---------- 议题类型（封闭枚举） ----------
ISSUE_UNASSIGNED = "UNASSIGNED"            # 编号文字存在、归属无客观判据（未归属分纤箱）
ISSUE_FXMAP_MISSING = "FXMAP_MISSING"      # 对照表有、parse 无（改派漏斗丢失）
ISSUE_FXMAP_EXTRA = "FXMAP_EXTRA"          # parse 有、对照表无
ISSUE_FLOOR_MISMATCH = "FLOOR_MISMATCH"    # 安装楼层双源不一致（C3）
ISSUE_MISSING_RECORD = "MISSING_RECORD"    # 一侧无记录（coverage 无该箱 / 来源零字段）
ISSUE_PENDING_STATE = "PENDING_STATE"      # 结果未定案（pending / unresolved）
ISSUE_INVALID_STATE = "INVALID_STATE"      # 状态字段值不在契约枚举内（疑似说明文字冒充）

STATUS_PENDING = "pending"


# ---------- 域（会审报告§三：地址对象 vs 地址-FX关系，二者不得混为一谈） ----------
DOMAIN_ADDRESS = "address"      # 地址对象本身未定（户数/户号/地址行未定）
DOMAIN_RELATION = "relation"    # 地址已定、与 FX 的关联未定（归属/安装层/覆盖）

# 静态归关系域的类型（构造上即关于箱↔楼/覆盖 linkage，无地址域实例）
_RELATION_TYPES = frozenset([
    ISSUE_UNASSIGNED, ISSUE_FXMAP_MISSING, ISSUE_FXMAP_EXTRA,
    ISSUE_FLOOR_MISMATCH, ISSUE_MISSING_RECORD,
])


def domain_of(kind, obj):
    """议题归域（纯分类，不定案）。

    静态归 relation 的五类直接返回 relation；PENDING_STATE/INVALID_STATE
    按对象路径启发判定：路径含「分纤箱」/「覆盖」即箱/覆盖 linkage（relation），
    否则为地址对象级（address，如 assemble 逐层户数 pending）。
    未知类型一律归 relation（宁可把地址问题算进关系域待人复核，
    不得把关系问题伪装成地址已定）。
    """
    if kind in _RELATION_TYPES:
        return DOMAIN_RELATION
    _o = str(obj or "")
    if "分纤箱" in _o or "覆盖" in _o:
        return DOMAIN_RELATION
    if kind in (ISSUE_PENDING_STATE, ISSUE_INVALID_STATE):
        return DOMAIN_ADDRESS
    return DOMAIN_RELATION


def make_issue_id(kind, obj):
    """确定性议题编号：同输入必同输出（去重与追溯用，不含随机/时间）。"""
    _k = str(kind or "").strip() or "?"
    _o = str(obj or "").strip() or "?"
    return "ISSUE-%s-%s" % (_k, _o)


def issue(kind, obj, candidates=None, evidence=None, note=""):
    """构造待裁决议题（纯构造：状态恒为 pending，本函数内无任何定案分支）。"""
    return {
        "issue_id": make_issue_id(kind, obj),
        "类型": str(kind or ""),
        "域": domain_of(kind, obj),
        "对象": str(obj or ""),
        "候选": list(candidates or []),
        "证据": list(evidence or []),
        "说明": str(note or ""),
        "状态": STATUS_PENDING,
    }


def summarize(issues):
    """议题汇总：{总数, 按类型:{kind:n}, 按域:{domain:n}}（纯计数，不排序、不定案）。"""
    _by = {}
    _dom = {}
    for _it in (issues or []):
        _k = str((_it or {}).get("类型") or "?")
        _by[_k] = _by.get(_k, 0) + 1
        _d = str((_it or {}).get("域") or domain_of(_k, (_it or {}).get("对象")))
        _dom[_d] = _dom.get(_d, 0) + 1
    return {"总数": len(list(issues or [])), "按类型": _by, "按域": _dom}


def collect_unassigned(unassigned_entries):
    """自 parse「未归属分纤箱」条目收集议题（只抄录编号/原因/位置，不判断归属）。

    Args:
        unassigned_entries: parsed.json「未归属分纤箱」数组（可为 None/[]）。
    """
    _out = []
    for _u in (unassigned_entries or []):
        if not isinstance(_u, dict):
            continue
        _fid = str((_u or {}).get("编号") or "").strip()
        if not _fid:
            continue
        _pos = ["(%.1f,%.1f)" % (p.get("x", 0.0), p.get("y", 0.0))
                for p in ((_u or {}).get("出现位置") or [])[:6]
                if isinstance(p, dict)]
        _out.append(issue(
            ISSUE_UNASSIGNED, _fid,
            candidates=[{k: _e.get(k) for k in ("楼栋", "单元", "安装楼层", "口径", "箱表描述")}
                        for _e in ((_u or {}).get("对照表候选") or [])[:8]
                        if isinstance(_e, dict)],
            evidence=["未归属原因：%s" % ((_u or {}).get("未归属原因") or "?"),
                      "出现位置：%s" % ("、".join(_pos) or "?")],
            note="编号文字存在但归属无客观判据，不进成品，须人工裁决"))
    return _out


def collect_fxmap_gap(expected_list, expected_count, assigned_ids, unassigned_ids):
    """对照表对账集合运算（自 C4b 原样抽出，不含 emit；判据语义与 C4b 逐字一致）。

    Args:
        expected_list: BDGMAP归属.对照表编号清单（可为 []/None；有则按清单模式）。
        expected_count: BDGMAP归属.唯一编号（清单缺席的老产物按计数模式）。
        assigned_ids: parse 已归属编号集合（可迭代）。
        unassigned_ids: parse 未归属编号集合（可迭代）。

    Returns:
        {mode: 清单|计数|无, expected:int|None, assigned:int,
         missing:[], extra:[], unassigned:[],
         aligned:bool}
        aligned 为 True ⟺（missing/extra 均空）且（unassigned 为空）——
        即 C4b 判 PASS 的充要条件；其余一律 FAIL（调用方负责登记，本函数不定案）。
    """
    try:
        _exp_set = set(str(x).strip() for x in (expected_list or []) if str(x).strip())
    except Exception:  # noqa: BLE001
        _exp_set = set()
    try:
        _asg = set(str(x).strip() for x in (assigned_ids or []) if str(x).strip())
    except Exception:  # noqa: BLE001
        _asg = set()
    try:
        _un = set(str(x).strip() for x in (unassigned_ids or []) if str(x).strip())
    except Exception:  # noqa: BLE001
        _un = set()
    if _exp_set:
        _missing = sorted(_exp_set - _asg - _un)
        _extra = sorted((_asg | _un) - _exp_set)
        return {"mode": "清单", "expected": len(_exp_set), "assigned": len(_asg),
                "missing": _missing, "extra": _extra, "unassigned": sorted(_un),
                "aligned": (not _missing and not _extra and not _un)}
    try:
        _exp_n = int(expected_count)
    except (TypeError, ValueError):
        return {"mode": "无", "expected": None, "assigned": len(_asg),
                "missing": [], "extra": [], "unassigned": sorted(_un),
                "aligned": False}
    return {"mode": "计数", "expected": _exp_n, "assigned": len(_asg),
            "missing": [], "extra": [], "unassigned": sorted(_un),
            "aligned": (_exp_n == len(_asg) + len(_un) and not _un)}


def fxmap_issues(gap):
    """自对账结果生成议题（missing/extra/未归属逐号；aligned 时返回 []）。"""
    _out = []
    _gap = gap or {}
    for _m in (_gap.get("missing") or []):
        _out.append(issue(
            ISSUE_FXMAP_MISSING, _m,
            candidates=["对照表有、parse无"],
            evidence=["对照表编号清单含 %s，parse已归属与未归属均无" % _m],
            note="改派漏斗丢失，不得出表"))
    for _e in (_gap.get("extra") or []):
        _out.append(issue(
            ISSUE_FXMAP_EXTRA, _e,
            candidates=["parse有、对照表无"],
            evidence=["parse 侧存在 %s，对照表编号清单无" % _e],
            note="多余编号，须人工确认来源"))
    for _u in (_gap.get("unassigned") or []):
        _out.append(issue(
            ISSUE_UNASSIGNED, _u,
            candidates=["对照表有、parse未归属"],
            evidence=["对照表已定归属、parse 未落位"],
            note="对照表已定归属、parse 未落位，不得出表"))
    return _out


def floor_mismatch_issue(fid, blk, un, parse_val, pctx, psrc, cov_vals, cctxs):
    """单箱双源不一致议题（只罗列双方原文与坐标系，不判定谁对）。

    Args:
        fid/blk/un: 箱编号/楼栋/单元。parse_val: parse 安装楼层原文。
        pctx/psrc: parse 侧统一字段的坐标系/来源（可为 None，老产物）。
        cov_vals: coverage 侧安装楼层原文清单。cctxs: coverage 侧坐标系清单。
    """
    return issue(
        ISSUE_FLOOR_MISMATCH, "%s（%s/%s）" % (fid, blk, un),
        candidates=["parse=%s" % parse_val,
                    "coverage=%s" % ("/".join(str(v) for v in (cov_vals or [])))],
        evidence=["parse坐标系=%s/来源=%s" % (pctx or "legacy", psrc or "?"),
                  "coverage坐标系=%s" % ("/".join(str(c) for c in (cctxs or [])) or "?")],
        note="安装楼层双源不一致；跨坐标体系差值疑似假冲突（V3§8），须先确认语义再裁决")


def run_c9(P, C, K, boxes, R):
    """C9 结果状态闭合（自 inspect_closure.py 原样搬入，判据文案逐字节不变）。

    Args:
        P/C/K: parse/coverage/count-box 产物全文 dict（None 表未提供）。
        boxes: inspect 展平箱清单（仅判空用）。
        R: inspect Report（emit/fail/warn/check 走它，保持截断与汇总口径）。

    Returns:
        本轮议题清单（FAIL 项逐条；WARN/SKIP 路径返回 []，只登记不返议题）。
        门禁结论仍以 R.fails/R.checks 为准，本返回值只供机读出口，不参与 rc。
    """
    def _walk_result_status(node, path=""):
        """递归收集产物中携带结果状态契约字段的条目，返回 [(路径, origin, confirmation)]。"""
        out = []
        if isinstance(node, dict):
            if "result_origin" in node or "result_confirmation" in node:
                out.append((path or "（根）",
                            node.get("result_origin"),
                            node.get("result_confirmation")))
            for k, v in node.items():
                out.extend(_walk_result_status(v, ("%s.%s" % (path, k)) if path else str(k)))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                out.extend(_walk_result_status(v, "%s[%d]" % (path, i)))
        return out

    R.emit()
    R.emit("--- C9 结果状态闭合（result_origin / result_confirmation） ---")
    # 覆盖申报（2026-09-18 补）：只报「扫到多少项」而不说「扫了哪些来源」，
    # 会在某个来源一个字段都没写时仍然判 PASS —— 闸门看着是绿的，实际有一半产物没核。
    # 已提供但零字段的来源必须单独点名（WARN），不得静默当作已核。
    _rs_items = []
    _rs_src_ok, _rs_src_empty = [], []
    # 2026-09-27收敛C8落地缺口：count-box已提供也纳入申报（其产物按设计无result字段，
    #   此处只WARN点名不断言FAIL，避免把历史绿灯图变红；C5质量透传仍是其主闸）。
    for _src_name, _src_obj in (("parse", P), ("coverage", C), ("count-box", K)):
        if _src_obj is None:
            continue
        _n0 = len(_rs_items)
        for _p, _o, _c in _walk_result_status(_src_obj):
            _rs_items.append(("%s:%s" % (_src_name, _p), _o, _c))
        (_rs_src_ok if len(_rs_items) > _n0 else _rs_src_empty).append(_src_name)
    _rs_scope = "已提供来源：%s；其中有字段：%s" % (
        "、".join(_rs_src_ok + _rs_src_empty) or "无",
        "、".join(_rs_src_ok) or "无")
    # 2026-09-26（一百零三，问题 9）：明细行与 warn 分支逻辑对齐 ——
    #   此处旧文案「零字段、未被闸门覆盖」是问题 3 修复漏改残留；coverage「零对象」
    #   形态（箱级 0 条，无对象可挂字段）须与下文 warn 同语义输出，不得暗示漏写。
    _cov_box_n = 0
    if C is not None:
        for _cblk, _cbv in (C.get("楼栋") or {}).items():
            for _cun, _cuv in ((_cbv or {}).get("单元") or {}).items():
                _cov_box_n += len((_cuv or {}).get("分纤箱") or [])
    _zero_obj = [s for s in _rs_src_empty
                 if s == "coverage" and boxes and _cov_box_n == 0]
    _zero_fld = [s for s in _rs_src_empty if s not in _zero_obj]
    if _zero_obj:
        R.emit("  ! 来源 coverage 已提供但箱级记录为 0 —— 无对象可挂结果状态字段"
               "（非字段漏写；覆盖零产出见 C6 FAIL）")
    if _zero_fld:
        R.emit("  ! 来源 %s 已提供但零字段 —— 未被结果状态闸门覆盖，不得视为已核"
               % "、".join(_zero_fld))
    _issues = []
    if not _rs_items:
        R.check("C9", "结果状态闭合", "SKIP",
                "产物未携带 result_origin / result_confirmation 字段"
                "（老产物按缺字段处理，不因此判 FAIL）；" + _rs_scope)
    else:
        # 2026-09-18 补（P0）：**枚举校验**。原实现只判存在性（c=='pending' or o=='unresolved'），
        #   任何字符串都能过 —— 实测在 coverage 产物里加一段「取值含义说明」（键名恰好叫
        #   result_origin/result_confirmation）后，说明文字被当成一条结果项、C9 计数从 34 变 35,
        #   且因为说明文字以 'settled' 开头而**判 PASS**。这正是本闸门自己要防的
        #   「看着绿、实则没核」。故改为：字段值必须落在契约枚举内，否则按未定案拦下。
        _V_ORIGIN = ("measured", "derived", "unresolved")
        _V_CONFIRM = ("settled", "pending")
        _rs_bad = []
        for _p, _o, _c in _rs_items:
            if _c == "pending" or _o == "unresolved":
                _rs_bad.append((_p, _o, _c, "结果未定案（origin=%s / confirmation=%s）—— 不得进入成品"
                                % (_o, _c)))
            elif _o not in _V_ORIGIN or _c not in _V_CONFIRM:
                _rs_bad.append((_p, _o, _c,
                                "字段值不在契约枚举内（origin∈%s；confirmation∈%s）—— "
                                "疑似说明性文字被当成结果项，或产出方写入了非法值，"
                                "一律按未定案拦下（判定依据见 L1-C8）"
                                % ("/".join(_V_ORIGIN), "/".join(_V_CONFIRM))))
        for _p, _o, _c, _why in _rs_bad[:20]:
            R.emit("  x %s  origin=%s  confirmation=%s" % (_p, _o, _c))
            R.fail("C9", "%s %s" % (_p, _why))
        if len(_rs_bad) > 20:
            R.emit("  ... 另有 %d 项未列出" % (len(_rs_bad) - 20))
        if _rs_bad:
            for _p, _o, _c, _why in _rs_bad:
                _issues.append(issue(
                    ISSUE_PENDING_STATE if (_c == "pending" or _o == "unresolved")
                    else ISSUE_INVALID_STATE, _p,
                    candidates=["origin=%s" % _o, "confirmation=%s" % _c],
                    evidence=[_why],
                    note="结果未定案或字段值非法，不得进入成品"))
            R.check("C9", "结果状态闭合", "FAIL",
                    "%d/%d 项结果未定案或字段值非法；%s"
                    % (len(_rs_bad), len(_rs_items), _rs_scope))
        elif _rs_src_empty:
            # 2026-09-25（一百零一，问题 3）：区分「产物没有对象」与「产物没写字段」——
            #   两者处置完全不同：前者（coverage 箱级记录为 0，无对象可挂字段，非字段漏写；
            #   V 型法窗口内无箱号锚形态）是覆盖零产出，已由 C6 判 FAIL 拦下，此处只解释、
            #   不重复拦下（避免双闸矛盾）；后者（有箱级对象却无字段）才是产出方未落
            #   L1-C8 字段，仍按原口径 WARN 点名。C6/C9 联动见 C6 一百零一注释。
            #   2026-09-26（一百零三，问题 9）：_cov_box_n/_zero_obj/_zero_fld 已在上文
            #   明细行处一次算出，此处复用（单源，与明细行恒一致），不再重复计算。
            if _zero_obj:
                R.warn("C9", "来源 coverage 已提供但箱级记录为 0 —— 无对象可挂结果状态字段"
                       "（非字段漏写）；覆盖零产出已由 C6 判 FAIL 拦下（L1-C8），此处不重复拦下")
            if _zero_fld:
                R.warn("C9", "来源 %s 已提供但零字段 —— 未被结果状态闸门覆盖，不得视为已核"
                       % "、".join(_zero_fld))
            _miss_parts = []
            if _zero_obj:
                _miss_parts.append("来源 coverage 箱级记录为 0（无对象可挂字段，非字段漏写；"
                                   "覆盖零产出见 C6 FAIL）")
            if _zero_fld:
                _miss_parts.append("**未覆盖**来源 %s（有对象无字段，产出方未落 L1-C8 字段）"
                                   % "、".join(_zero_fld))
            R.check("C9", "结果状态闭合", "WARN",
                    "%d 项结果均已定案（settled），但%s —— %s"
                    % (len(_rs_items), "；".join(_miss_parts), _rs_scope))
        else:
            R.check("C9", "结果状态闭合", "PASS",
                    "%d 项结果均已定案（settled）；%s" % (len(_rs_items), _rs_scope))
    return _issues
