#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""冲突矩阵回归测试（报告 §12.4，2026-09-27 立）。

目的：用**故意制造矛盾**的输入，验证覆盖来源状态机是否闭环 —— 每种情形最终只能
进入**正确的**状态，且「没核 / 未接入」**不得**被呈现成「通过 / 已定案」。
覆盖报告 §12.4 的 12 个场景（见 CASES 注释）。

设计纪律
--------
* **不依赖 DXF 语料**：只打靶真实函数（`plan_methods._pick_method`、
  `ftth._pipe_capability_problems` / `_pipe_coverage_choice`、
  `ftth_common.coverage_method_of`、`check_contracts.py`），故可随时跑、秒级返回。
* **单一真源**：信号/候选表一律从 `plan_methods.build_steps` 现取，测试**不另抄一份**
  （抄两份 = 同一漂移再发生一次，见 operations_discipline §十二.2）。
* **覆盖判定非并跑（2026-09-27 用户裁决）**：有米标即**优先 V型计算**、**不再相互验证**。
  故相关场景断言的是「**取用顺序**」（有米标 ⇒ 选中 V型）与「**未接入登记**」（直读信号成立
  须留痕），而不是"两法须比对"；「同可用备选」只作**信息登记**，不构成"人工再跑第二法"的义务。

退出码：0 = 全过；2 = 有失败；（沿用 L1-C2 语义）
用法：python tests/run_conflict_matrix.py
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SC = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SC)

import plan_methods as pm            # noqa: E402
import ftth as F                     # noqa: E402
from ftth_common import COVERAGE_METHODS, coverage_method_of   # noqa: E402

PRESENT, ABSENT, UNKNOWN = pm.PRESENT, pm.ABSENT, pm.UNKNOWN
PY = sys.executable

FAILS = []


def ck(case, name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    print("  [%s] %s :: %s%s" % (tag, case, name, ("  " + detail) if detail else ""))
    if not cond:
        FAILS.append("%s/%s" % (case, name))


_ALL_SIG = ("cluster_layout", "shared_drawing", "household_annotation", "fiber_length_vshape",
            "floor_scale", "titleblock_annotation", "box_icon_annotation",
            "dedicated_wire_layer", "fx_overview_map", "cover_range_annotation",
            "vertical_bus_traceable")


def steps():
    """现取候选表（单一真源）——测试不另抄。"""
    return pm.build_steps({k: (ABSENT,) for k in _ALL_SIG}, {})


def sig(**present):
    d = {k: (ABSENT, "注入") for k in _ALL_SIG}
    for k in present:
        d[k] = (PRESENT, "注入")
    return d


def pick(**present):
    return pm._pick_method(steps(), sig(**present), "覆盖判定")


def profile(cov):
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump({"handoff": {"②系统图选法": {"覆盖范围": cov}}}, f, ensure_ascii=False)
    return p


def cc(dirpath):
    r = subprocess.run([PY, os.path.join(SC, "check_contracts.py"), dirpath],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode


def covdir(basis):
    d = tempfile.mkdtemp()
    with io.open(os.path.join(d, "coverage.json"), "w", encoding="utf-8") as f:
        json.dump({"楼栋": {"1#楼": {"单元": {"1单元": {"分纤箱": [
            {"编号": "FX1#", "判定依据": basis}]}}}}}, f, ensure_ascii=False)
    return d


TMP = []


def P(cov):
    p = profile(cov)
    TMP.append(p)
    return p


def D(basis):
    d = covdir(basis)
    TMP.append(d)
    return d


# ============================================================
# 场景 1：直读 = V型 = 竖线（三来源齐备且一致）
# ============================================================
# 直读产出口未接入 ⇒ 必须**降级**到已接入候选并**登记**未接入；
# 且米标成立 ⇒ **按候选顺序取 V型计算**（2026-09-27 裁决：不再并跑互验）。
o = pick(cover_range_annotation=True, fiber_length_vshape=True,
         floor_scale=True, dedicated_wire_layer=True, vertical_bus_traceable=True)
ck("S1 三来源齐备", "降级到已接入方法（不选未接入的直读）",
   o.get("选定方法") and "读取标注" not in str(o.get("选定方法")), str(o.get("选定方法")))
ck("S1 三来源齐备", "未接入的直读被登记（不静默）", bool(o.get("未接入候选")))
ck("S1 三来源齐备", "米标成立 ⇒ 取 V型计算（有米标优先，不并跑）",
   "V型" in str(o.get("选定方法")), str(o.get("选定方法")))
ck("S1 三来源齐备", "同可用备选仅作信息登记（不要求再跑第二法）",
   len(o.get("同可用备选") or []) >= 1, json.dumps(o.get("同可用备选"), ensure_ascii=False))

# ============================================================
# 场景 2~4：直读与某一法冲突 / 两法冲突
# ============================================================
# 说明：直读**无产出口**，故"直读≠X"当前无法由机器算出结论 —— 这正是必须
# 登记未接入的原因。此处断言：只要直读信号成立，画像必带 `未接入候选`，
# 人工据此知道"还有一路直读证据没被消费"。
# 2026-09-27 裁决后：**"≠"不再由比对解决，而由「候选顺序」解决** —— 米标成立即取 V型，
# 场景名沿用报告 §12.4 编号以保持可追溯，断言改为判「取用结果」。
for nm, has_direct, kw in (
        ("S2 直读≠V型（V型+竖线均缺）", True,
         dict(cover_range_annotation=True, fiber_length_vshape=True, floor_scale=True)),
        ("S3 直读≠竖线", True,
         dict(cover_range_annotation=True, dedicated_wire_layer=True,
              vertical_bus_traceable=True, floor_scale=True)),
        ("S4 V型≠竖线（直读缺）", False,
         dict(fiber_length_vshape=True, floor_scale=True, dedicated_wire_layer=True,
              vertical_bus_traceable=True))):
    o = pick(**kw)
    if has_direct:
        ck(nm, "直读信号成立 ⇒ 必带未接入登记（人工据此知有未消费证据）",
           bool(o.get("未接入候选")))
    else:
        ck(nm, "米标成立 ⇒ 取 V型计算（优先，不并跑互验）",
           "V型" in str(o.get("选定方法")), "选定=%s" % o.get("选定方法"))

# ============================================================
# 场景 5：三者全不同（直读+V型+竖线同时成立）
# ============================================================
o = pick(cover_range_annotation=True, fiber_length_vshape=True, floor_scale=True,
         dedicated_wire_layer=True, vertical_bus_traceable=True)
ck("S5 三者全不同", "登记未接入 + 取 V型（信息不丢、不并跑）",
   bool(o.get("未接入候选")) and "V型" in str(o.get("选定方法")))

# ============================================================
# 场景 6：只有直读 —— 图上有、技能没有 ⇒ unimplemented（既非 absent 亦非 unknown）
# ============================================================
o = pick(cover_range_annotation=True)
ck("S6 只有直读", "申报 unimplemented（不得冒充 absent）",
   o.get("申报") == "unimplemented", str(o.get("申报")))
ck("S6 只有直读", "选定方法为空、未接入候选已登记",
   o.get("选定方法") is None and bool(o.get("未接入候选")))
pp = P({"申报": "unimplemented", "脚本": None, "阻塞原因": "注入"})
_pp, _nn, _blk = F._pipe_coverage_choice(pp)
ck("S6 只有直读", "入口侧 blocked=True（不得 rc=3 静默跳过）", _blk)

# ============================================================
# 场景 7/8：只有 V型 / 只有竖线 —— 单源采信（不因单来源降级）
# ============================================================
o = pick(fiber_length_vshape=True, floor_scale=True)
ck("S7 只有V型", "选定V型且无其它可用候选（单源采信）",
   "V型" in str(o.get("选定方法")) and not (o.get("同可用备选") or []),
   "选定=%s 备选=%s" % (o.get("选定方法"), o.get("同可用备选")))
ck("S7 只有V型", "入口可映射为 coverage-vshape",
   F._pipe_coverage_choice(P({"申报": "已选定", "脚本": "analyze_coverage_vshape.py"}))[0]
   == "coverage-vshape")

o = pick(dedicated_wire_layer=True, vertical_bus_traceable=True, floor_scale=True)
ck("S8 只有竖线", "选定竖线法且同可用备选为空",
   "竖线法" in str(o.get("选定方法")) and not (o.get("同可用备选") or []),
   "选定=%s" % o.get("选定方法"))
ck("S8 只有竖线", "入口可映射为 coverage",
   F._pipe_coverage_choice(P({"申报": "已选定", "脚本": "analyze_coverage.py"}))[0] == "coverage")

# ============================================================
# 场景 9：全部没有 ⇒ absent（放行 + 降级路径），且入口侧 rc=3 合法缺席
# ============================================================
o = pick()
ck("S9 全无", "申报 absent", o.get("申报") == "absent", str(o.get("申报")))
_p9 = P({"申报": "absent", "脚本": None})
ck("S9 全无", "入口侧 cmd=None 且 blocked=False（rc=3 合法缺席，非错误）",
   F._pipe_coverage_choice(_p9)[0] is None and F._pipe_coverage_choice(_p9)[2] is False)
ck("S9 全无", "能力表校验不报问题（absent 不核）", F._pipe_capability_problems(_p9) == [])

# ============================================================
# 场景 10：unknown（判不了）⇒ 未作答，入口 rc=2
# ============================================================
_s = {k: (UNKNOWN, "注入") for k in _ALL_SIG}
o = pm._pick_method(steps(), _s, "覆盖判定")
ck("S10 unknown", "申报 unknown（未作答，不得当 absent 放行）",
   o.get("申报") == "unknown", str(o.get("申报")))

# ============================================================
# 场景 11：pending —— 判定依据=待确认 / 空 / 漂移写法
# ============================================================
ck("S11 pending", "判定依据=待确认 在枚举内（合法但仍不得采信）",
   coverage_method_of("待确认") == "待确认")
ck("S11 pending", "判定依据=空 ⇒ 取不出方法（不得采信）",
   coverage_method_of("") is None)
ck("S11 pending", "判定依据=V形计算（漂移写法）⇒ FAIL 拦下", cc(D("V形计算")) == 2)
ck("S11 pending", "判定依据=竖线法（合规）⇒ 通过", cc(D("竖线法（断口区间法直读）：…")) == 0)
ck("S11 pending", "枚举为唯一真源（词表常量）",
   set(COVERAGE_METHODS) == {"读取标注", "竖线法", "V型计算", "人工裁决", "待确认"})

# ============================================================
# 场景 12：人工裁决后又出现新解析值 —— 不得静默覆盖
# ============================================================
# 契约层：`人工裁决` 是枚举内的**独立**取值 ⇒ 与 `读取标注/竖线法/V型计算` 区分得开，
# 下游据此可判「该值来自人工裁定」，而不是又一个自动解析值（这才是"不得静默覆盖"的机械前提）。
ck("S12 人工裁决", "coverage_method 有独立的『人工裁决』取值（与自动解析值可区分）",
   "人工裁决" in COVERAGE_METHODS)
ck("S12 人工裁决", "裁决来源标识 E-HUMAN-RULING 类契约存在（C9 表）",
   "E-HUMAN-RULING" in io.open(os.path.join(SC, "..", "SKILL.md"),
                               encoding="utf-8").read())

# ============================================================
# 场景 13：户数三口径（2026-09-27 用户裁决）
#   用户原话：「楼层的户数如果标注了可以直读，首选直读 …… 这个都是首选直读，不再看皮线
#   或者图标个数。如果不能〔直读〕，有图标的首先计算图标的个数，没有图标的才会取数皮线
#   条数，而且不用再去校验。」
#   裁定：①有直读标注（『X户』**或**乘号式 `*N`/`xN`）⇒ 直读；②无标注 ⇒ 有图标数图标；
#   ③无图标才数皮线。**三口径选定即出数，互不校验。**（乘号后数字即该处户数，不与图标相乘）
# ============================================================
def hh(**kw):
    """取『户数提取』子任务的选法结果（pick() 写死了覆盖判定，此处须直接调）。"""
    return pm._pick_method(steps(), sig(**kw), "户数提取")


o = hh(household_annotation=True)
ck("S13 户数直读", "有『X户』/乘号式标注 ⇒ 命中直读候选（不数图标/皮线）",
   "读取标注" in str(o.get("选定方法")), str(o.get("选定方法")))

o = hh(box_icon_annotation=True, dedicated_wire_layer=True, floor_scale=True)
ck("S13 户数直读", "无标注 + 图标三前置齐备 ⇒ 取图标法（不数皮线）",
   "图标" in str(o.get("选定方法")), str(o.get("选定方法")))

o = hh(floor_scale=True)
ck("S13 户数直读", "无标注 + 无图标 ⇒ 才回落皮线法",
   "皮线" in str(o.get("选定方法")), str(o.get("选定方法")))

o = hh(household_annotation=True, box_icon_annotation=True,
       dedicated_wire_layer=True, floor_scale=True)
ck("S13 户数直读", "直读与图标同时可用 ⇒ 直读胜出（首选直读）",
   "读取标注" in str(o.get("选定方法")), str(o.get("选定方法")))

# ---- 乘号式标注的机械判据（正则单一来源：ftth_common）----
from ftth_common import HU_MULT_RE, hu_mult_of, first_group, first_nonnull_group  # noqa: E402
_mm = [("*16", 16), ("x2", 2), ("×3", 3), ("X16", 16), ("* 5", 5)]
ck("S13 乘号式", "乘号式取乘号后数字为该处户数（= 直读读数）",
   all(hu_mult_of(t) == n for t, n in _mm), str([(t, hu_mult_of(t)) for t, _ in _mm]))
ck("S13 乘号式", "米数标注不被误吞（全匹配 ⇒ `20m*2` 不是户数形态）",
   hu_mult_of("20m*2") is None and hu_mult_of("20m") is None and hu_mult_of("2户") is None)

# ---- 多形态交替正则取值：命中哪支决定哪组有值 → 须取第一个非 None 组 ----
_ap = re.compile(r"(\d+)\s*户|[*×xX]\s*(\d+)")
ck("S13 取值", "交替正则命中乘号支 ⇒ 取组2（first_nonnull_group 不取空组1）",
   first_nonnull_group(_ap.search("*16")) == "16")
ck("S13 取值", "交替正则命中『X户』支 ⇒ 取组1",
   first_nonnull_group(_ap.search("3户")) == "3")
ck("S13 取值", "first_group（固定取组1）在乘号支上取到 None —— 即本轮修复的缺陷面",
   first_group(_ap.search("*16")) is None)

# ============================================================
# 元断言（2026-09-27 用户裁决「有米标优先 V 型、不再相互验证」）：
#   「非并跑」必须写进 cross_check；入口只跑一条子命令 = **设计意图**，
#   不许再被读成"待补的缺陷"。
# ============================================================
o = pick(fiber_length_vshape=True, floor_scale=True, dedicated_wire_layer=True,
         vertical_bus_traceable=True)
_cx = (steps()["解析"]["覆盖判定"].get("cross_check") or "")
ck("META 非并跑", "取法规则已写进 cross_check（按顺序取首个 · 有米标优先 V型 · 非并跑）",
   ("非并跑" in _cx) and ("优先" in _cx), _cx[:70])
ck("META 非并跑", "入口只跑一条子命令（单命令 = 非并跑的设计意图，非缺陷）",
   len([k for k in ("coverage", "coverage-vshape")
        if k == F._pipe_coverage_choice(P({"申报": "已选定",
                                           "脚本": "analyze_coverage.py"}))[0]]) == 1)

# ============================================================
# 元断言（2026-09-27 用户裁决「户数三口径选定即出数、互不校验」）：
#   ①三口径与「非并跑」必须写进户数子任务的 cross_check；
#   ②乘号式属**直读**形态（乘号后数字即户数），旧口径「乘数须报人裁决」已废；
#   ③旧字段名 `待裁决_乘数标注` 全仓零残留（防回退）——「已改」不等于「改得住」。
# ============================================================
_cx_hh = (steps()["解析"]["户数提取"].get("cross_check") or "")
ck("META 户数", "三口径与『非并跑 · 互不校验』已写进 cross_check",
   ("非并跑" in _cx_hh) and ("互不校验" in _cx_hh), _cx_hh[:60])
ck("META 户数", "乘号式属直读已写进 cross_check（乘号后数字即该处户数）",
   ("乘号" in _cx_hh) and ("直读" in _cx_hh) and ("该处户数" in _cx_hh), _cx_hh[:60])
ck("META 户数", "旧口径『乘数须自行相乘 / 报人裁决』已从 cross_check 移除",
   "不得自行相乘" not in _cx_hh)
_ghosts = []
for _fn in os.listdir(SC):
    if not _fn.endswith(".py"):
        continue
    try:
        if "待裁决_乘数标注" in io.open(os.path.join(SC, _fn), encoding="utf-8").read():
            _ghosts.append(_fn)
    except OSError:
        pass
ck("META 户数", "旧字段名『待裁决_乘数标注』在脚本侧零残留（防回退）",
   not _ghosts, str(_ghosts))

# ============================================================
# 场景 14：组装同配置展开 —— 复制户数须带pending + 机读清单
# ============================================================
# 无图标列单元按同覆盖配置模板复制户数时（result_origin=derived），须同时
# 落 result_confirmation=pending 并入产物级「同配置展开待核对」清单
# （C9不扫assemble，此清单是唯一机读出口；只print=不可判）。
_s14d = tempfile.mkdtemp(); TMP.append(_s14d)
_s14count = os.path.join(_s14d, "count.json")
_s14cov = os.path.join(_s14d, "cov.json")
_s14out = os.path.join(_s14d, "asm.json")
with io.open(_s14count, "w", encoding="utf-8") as f:
    json.dump({"列": [{"逐层": [["1F", 2], ["2F", 2]]}]}, f, ensure_ascii=False)
def _s14box(no):
    return {"编号": no, "安装楼层": "1F",
            "覆盖范围线索": {"覆盖楼层": ["1F", "2F"]}}

def _s14unit(no):
    return {"1单元": {"分纤箱": [_s14box(no)]}}

with io.open(_s14cov, "w", encoding="utf-8") as f:
    json.dump({"楼栋": {"1#楼": {"单元": _s14unit("FX01")},
                        "2#楼": {"单元": _s14unit("FX02")}}}, f, ensure_ascii=False)
_s14r = subprocess.run([PY, os.path.join(SC, "assemble_households.py"),
                        "--count", _s14count, "--col-map", "0=1#楼/1单元",
                        "--coverage", _s14cov, "--out", _s14out],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
_s14o = {}
try:
    with io.open(_s14out, encoding="utf-8") as f:
        _s14o = json.load(f)
except (IOError, ValueError):
    pass
_s14u = ((_s14o.get("楼栋") or {}).get("2#楼") or {}).get("单元", {}).get("1单元", {})
_s14fl = _s14u.get("楼层表") or {}
_s14lst = _s14o.get("同配置展开待核对") or []
ck("S14 组装展开", "无图标列按同配置模板补入（rc=0，不断链）",
   _s14r.returncode == 0 and bool(_s14fl), "rc=%d" % _s14r.returncode)
ck("S14 组装展开", "展开户两字段正交齐全（derived+pending，缺一即机器不可判）",
   all(v.get("result_origin") == "derived" and v.get("result_confirmation") == "pending"
       for v in _s14fl.values()) if _s14fl else False, str(len(_s14fl)))
ck("S14 组装展开", "产物级待核对清单有且仅有该单元",
   len(_s14lst) == 1 and _s14lst[0].get("对象") == "2#楼/1单元"
   and _s14lst[0].get("result_confirmation") == "pending", str(len(_s14lst)))

# ============================================================
# 场景 15：出表有损放行 —— 默认中止rc=2，加旗才放行rc=0
# ============================================================
# 楼层号解析失败整层丢弃时：默认须中止（rc=2，禁出表）；用户显式
# --allow-lossy 才放行（I5-A用户指示覆盖）。两档缺一即门禁失灵。
# 2026-09-29（一百二十七·P0）：两档都必须先过出口闭合门（带 --inspect），
#   否则第一档测的是“缺闭合”而非“有损”，判别力丢失。
_s15d = tempfile.mkdtemp(); TMP.append(_s15d)
_s15p = os.path.join(_s15d, "parse.json")
with io.open(_s15p, "w", encoding="utf-8") as f:
    json.dump({"楼栋": {"1#楼": {"单元": {"1单元": {
        "楼层表": {"1F": {"户数": 2}, "未知层": {"户数": 2}},
        "分纤箱": [{"编号": "FX01", "安装楼层": "1F"}]}}}}}, f, ensure_ascii=False)
_s15c = os.path.join(_s15d, "cov.json")
with io.open(_s15c, "w", encoding="utf-8") as f:
    json.dump({"楼栋": {"1#楼": {"单元": {"1#楼1单元": {"分纤箱": [{
        "编号": "FX01", "安装楼层": "1F",
        "覆盖范围线索": {"覆盖楼层": ["1F"]},
        "判定依据": "竖线法（冒烟合成料）", "依据来源": "E-SMOKE",
        "result_origin": "derived", "result_confirmation": "settled"}]}}}}},
        f, ensure_ascii=False)
_s15i = os.path.join(_s15d, "insp.json")
_s15ri = subprocess.run([PY, os.path.join(SC, "ftth.py"), "inspect",
                        "--parse", _s15p, "--coverage", _s15c,
                        "--json", _s15i],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
ck("S15 有损放行", "闭合基线 rc=0（未知层不拦 inspect，拦 gen）",
   _s15ri.returncode == 0, "rc=%d" % _s15ri.returncode)
_s15a = subprocess.run([PY, os.path.join(SC, "gen_addressbook.py"),
                        "--dxf-json", _s15p, "--inspect", _s15i,
                        "--out", os.path.join(_s15d, "a.xlsx")],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
_s15b = subprocess.run([PY, os.path.join(SC, "gen_addressbook.py"),
                        "--dxf-json", _s15p, "--inspect", _s15i,
                        "--out", os.path.join(_s15d, "b.xlsx"),
                        "--allow-lossy"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
ck("S15 有损放行", "丢层默认中止（rc=2，不得出表）", _s15a.returncode == 2,
   "rc=%d" % _s15a.returncode)
ck("S15 有损放行", "显式--allow-lossy才放行（rc=0，用户指示覆盖）",
   _s15b.returncode == 0, "rc=%d" % _s15b.returncode)

# ============================================================
# META 议题域：地址对象 vs 地址-FX关系（会审报告§三，双双只增不改）
# ============================================================
# 会审要求：地址本身已定、但与FX的关联未定，不得与地址对象未定混为一谈。
# 本节只断言 domain_of 映射与 issue/summarize 落盘，不改任何门禁语义。
import conflict_engine as CE  # noqa: E402
ck("META 域", "五类 linkage 型恒为 relation",
   all(CE.domain_of(k, "任意对象") == "relation"
       for k in ("UNASSIGNED", "FXMAP_MISSING", "FXMAP_EXTRA",
                 "FLOOR_MISMATCH", "MISSING_RECORD")))
ck("META 域", "PENDING分纤箱/覆盖路径归 relation",
   CE.domain_of("PENDING_STATE", "parse:楼栋.1#楼.分纤箱[0]") == "relation"
   and CE.domain_of("PENDING_STATE", "coverage:某单元.覆盖范围线索") == "relation")
ck("META 域", "PENDING非箱/覆盖路径归 address（如assemble逐层户数）",
   CE.domain_of("PENDING_STATE", "assemble:2#楼/1单元") == "address"
   and CE.domain_of("INVALID_STATE", "count:某列") == "address")
ck("META 域", "未知类型默认 relation（宁可待人复核，不伪装地址已定）",
   CE.domain_of("SOME_FUTURE_TYPE", "x") == "relation")
_it_r = CE.issue("UNASSIGNED", "FX01")
_it_a = CE.issue("PENDING_STATE", "assemble:2#楼/1单元")
ck("META 域", "issue 自带域",
   _it_r.get("域") == "relation" and _it_a.get("域") == "address"
   and _it_r.get("状态") == "pending",
   str((_it_r.get("域"), _it_a.get("域"))))
_sdom = CE.summarize([_it_r, _it_a, CE.issue("FLOOR_MISMATCH", "FX02（1#楼/1单元）")])
ck("META 域", "summarize 按域计数",
   _sdom.get("按域") == {"relation": 2, "address": 1}
   and _sdom.get("总数") == 3, str(_sdom.get("按域")))
ck("META 域", "老议题（无域键）按域回算不崩",
   CE.summarize([{"类型": "UNASSIGNED", "对象": "FX09"}]).get("按域") == {"relation": 1})

for p in TMP:
    try:
        if os.path.isdir(p):
            for fn in os.listdir(p):
                os.remove(os.path.join(p, fn))
            os.rmdir(p)
        else:
            os.remove(p)
    except OSError:
        pass

print()
print("== 冲突矩阵回归: %s（失败 %d 项）==" % ("ALL PASS" if not FAILS else "FAIL", len(FAILS)))
for f in FAILS:
    print("  ! %s" % f)
sys.exit(0 if not FAILS else 2)
