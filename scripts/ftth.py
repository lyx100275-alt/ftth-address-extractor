#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTTH 标准地址表提取工具 - 主入口
统一调度：probe / plan / parse / coverage / coverage-vshape / count / count-box / assemble /
apply-ruling / gen / verify-truth / inspect
（`count-box` 的旧名 `count-hdd` 保留为别名，见下方说明）

参数填充优先级（检测类参数无内置默认值，缺失即报错退出）：
  1. 命令行显式指定（最高）
  2. --config 传入 probe 输出的 suggested_params
  3. 算法常数（阈值/容差等，与图纸无关）
检测类参数（图层名 / 标题正则 / 编号正则 / 米数正则 / 邻近距离）必须有 1 或 2 提供，
否则子脚本会报错并列出缺失项——这是刻意的：这些值每张图都不同，不允许静默套用。
"""
import argparse
import json
import os
import re
import sys
import subprocess
import time
from pathlib import Path

# 2026-09-25（评审 P2-14）：入口编码改用 ftth_common.ensure_console_utf8（幂等、
#   有 try 守卫），替代裸 reconfigure（被替换流会炸）。
from ftth_common import ensure_console_utf8, write_json, floor_num, floor_num_or_zero
ensure_console_utf8()


def run_script(script_name: str, args: list) -> int:
    """运行子脚本"""
    script_path = Path(__file__).parent / script_name
    cmd = [sys.executable, str(script_path)] + args
    return subprocess.call(cmd)


def fmt_val(v):
    """将参数值转为命令行字符串；列表用逗号拼接。"""
    if isinstance(v, list):
        return ",".join(str(item) for item in v)
    return str(v)


def build_cmd(args, exclude_keys):
    """从 vars(args) 构造子脚本命令行参数，跳过排除键和 None 值。

    2026-09-15：布尔值统一按「开关」语义处理 —— True 只输出 `--flag`（不带值），
      False 跳过。旧实现把 True 拼成 `--flag True`，而 argparse 的 store_true
      遇到显式值会直接报 "ignored explicit argument"；所以此前每个 store_true
      都必须在调用处手工排除再转发（见 cmd_plan / coverage-vshape 的注释），
      极易遗漏。统一后新增开关不必再做特殊处理。
    """
    cmd = []
    for k, v in vars(args).items():
        if k in exclude_keys or v is None:
            continue
        flag = f"--{k.replace('_', '-')}"
        if isinstance(v, bool):
            if v:
                cmd.append(flag)
            continue
        cmd += [flag, fmt_val(v)]
    return cmd


# 子命令 → 其依赖的画像子任务（用于读取 profile.json 做入口门禁）
GATE_MAP = {
    "parse": ["楼栋分组", "户数提取", "分纤箱提取"],
    "coverage": ["覆盖判定"],
    "coverage-vshape": ["覆盖判定"],
}


def check_profile_gate(cmd_name, profile_path):
    """入口门禁：读 profile.json，按**申报制**契约决定 放行 / 降级 / 中止。

    退出码语义（与 SKILL.md 一致）：
      0 = 放行。契约已逐项申报；本图若有缺项，降级路径已打印。
      2 = 中止。两种情形：① 契约有未作答项（状态 unknown，判不了，须补探查重跑 plan）；
                        ② 本命令依赖的子任务存在 unknown 信号。
      3 = 不适用。本图确实不提供该子任务所需数据（已申报 absent）—— 该命令在本图没有
          输入，跳过即可。**这不是错误、不需重试**；下游改用现有图纸自身的信息校验。

    背景：覆盖判定的两个候选（V型计算 / 竖线法）前置信号可能全不成立。此前行为是照常
    跑完并输出可用性未知的结果（实测出现过全部分纤箱丢失仍 rc=0）。
    """
    if not profile_path:
        return 0
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            prof = json.load(f)
    except Exception as e:
        # 画像读不出来时**不得静默放行**：门禁存在的理由正是拦住"可用性未知的结果"，
        # 而画像损坏恰是最该拦的时刻。显式逃生口 = 去掉 --profile 重跑（见下方提示）。
        print("")
        print("!" * 68)
        print(f"[gate] 已中止：无法读取图纸画像 {profile_path}: {e}")
        print("[gate] 处置：重跑 `ftth.py plan` 重新生成画像；"
              "或确认不需要门禁时去掉 --profile 重跑（结果须自行标注可用性）。")
        print("!" * 68)
        return 2

    # ---- 契约层（申报制）：absent 放行并打印降级；只有未作答 / 不可解析才中止 ----
    ho = (prof.get("handoff") or {}).get("completeness") or {}
    unanswered = list(ho.get("未作答") or []) + list(ho.get("不可解析") or [])
    if unanswered:
        print("")
        print("!" * 68)
        print(f"[gate] 已中止：{cmd_name} 的入口要求 Step 1 交接契约逐项作答（当前有未作答项）")
        for m in unanswered:
            print(f"[gate]   · 未作答 {m}")
        print("[gate] 处置：补齐探查后重跑 `ftth.py plan`；"
              "或确认要以该方式继续时去掉 --profile 重跑（结果须自行标注可用性）。")
        print("!" * 68)
        return 2
    for g in (ho.get("缺失项及降级路径") or []):
        print(f"[gate] 本图未提供 {g['要素']}（状态 {g['状态']}）→ 降级：{g.get('降级')}")

    # ---- 命令层：本图能不能跑这条命令 ----
    gate = prof.get("gate") or {}
    need = GATE_MAP.get(cmd_name, [])
    if "blocked_steps" in gate or "skipped_steps" in gate:
        blocked = [s for s in need if s in set(gate.get("blocked_steps") or [])]
        skipped = [s for s in need if s in set(gate.get("skipped_steps") or [])]
    else:  # 兼容旧画像：无性质区分时一律按"中止"处理（保守）
        blocked = [s for s in need if s in set(gate.get("unavailable_steps") or [])]
        skipped = []

    if blocked:
        print("")
        print("!" * 68)
        print(f"[gate] 已中止：{cmd_name} 依赖的子任务存在 unknown 信号（未作答）")
        for d in (gate.get("details") or []):
            if d.get("子任务") in blocked:
                print(f"[gate]   · {d['子任务']}：{d.get('原因')}")
                for k, v in (d.get("候选信号实况") or {}).items():
                    print(f"[gate]       信号 {k} = {v}")
        print("[gate] 处置：补探查后重跑 `ftth.py plan`。")
        print("!" * 68)
        return 2

    if skipped:
        print("")
        print("-" * 68)
        print(f"[gate] 不适用：{cmd_name} 所需子任务在本图中未提供 →"
              f" 已按申报跳过（rc=3，非错误）")
        print(f"[gate] 本图未提供：{skipped}")
        for d in (gate.get("details") or []):
            if d.get("子任务") in skipped:
                print(f"[gate]   · {d['子任务']}：{d.get('原因')}")
                for k, v in (d.get("候选信号实况") or {}).items():
                    print(f"[gate]       信号 {k} = {v}")
        print("[gate] 处置：无需重试。以现有图纸为准 —— 见上方降级路径。")
        print("-" * 68)
        return 3

    # 2026-09-17：放行时把本图形态已知的下游情况一并带出。
    #   risk_forecast 由 plan_methods.py 就本图信号组合算出，属"已算清、照做即可"的既定处置。
    #   门禁输出是下游每条命令必看的通道 —— 提示放这里，才不必每轮重新推演「这意味着什么」。
    _rf = prof.get("risk_forecast") or []
    if _rf:
        print("")
        print("-" * 68)
        print(f"[gate] 本图形态已知会在下游出现 {len(_rf)} 处情况"
              f"（**属图面固有形态，按既定处置走，不必重新推导**）：")
        for _r in _rf:
            print(f"[gate]   · {_r.get('情况')}")
            print(f"[gate]     信号依据：{_r.get('信号依据')}")
            print(f"[gate]     既定处置：{_r.get('处置')}")
        print("-" * 68)

    return 0


# ---------------------------------------------------------------------------
# 子命令 -> 一行可复制的正确示例（报错时一并打印）
#
# 动机（实测）：调用方（含批量脚本）会猜参数名，同一张图连续两轮全部失败 ——
#   先 "unrecognized arguments"（参数名不存在），改脚本后又
#   "the following arguments are required"（必填缺失）；8 个地块 x 2 轮 = 16 次
#   子进程调用全废。默认 argparse 只回一行 usage，既不说有哪些参数、也不给可复制的
#   写法，调用方只能继续猜。本表与该命令的 argparse 选项集一一对应
#   （示例中出现的每个 --xxx 都由构建脚本校验真实存在）。
# ---------------------------------------------------------------------------
_CMD_EXAMPLES = {
    "probe":
        "ftth.py probe --dxf \"<图.dxf>\" --out \"<probe.json>\"",
    "plan":
        "ftth.py plan --dxf \"<图.dxf>\" --probe \"<probe.json>\" --out \"<profile.json>\"",
    "parse":
        "ftth.py parse --dxf \"<图.dxf>\" --config \"<probe.json>\" --out \"<parse.json>\"",
    "coverage":
        "ftth.py coverage --dxf \"<图.dxf>\" --config \"<probe.json>\" --out \"<coverage.json>\"",
    "coverage-vshape":
        "ftth.py coverage-vshape --dxf \"<图.dxf>\" --config \"<probe.json>\" --fx-locations \"<fxloc.json>\" --out \"<coverage.json>\"",
    "verify-truth":
        "ftth.py verify-truth \"<标准地址表.xlsx>\" \"<coverage.json>\" --dxf \"<图.dxf>\" --config \"<probe.json>\"",
    "inspect":
        "ftth.py inspect --parse \"<parse.json>\" --coverage \"<coverage.json>\" --geom \"<图.dxf.geom.json>\" --json \"<inspect.json>\"",
    "count":
        "ftth.py count --dxf \"<图.dxf>\" --config \"<probe.json>\" --out \"<count.json>\"",
    "count-box":
        "ftth.py count-box --dxf \"<图.dxf>\" --config \"<probe.json>\" --out \"<count_box.json>\"",
    "gen":
        "ftth.py gen --parse \"<parse.json>\" --inspect \"<inspect.json>\" --template \"<模板.xlsx>\" --out \"<标准地址表.xlsx>\"",
    "assemble":
        "ftth.py assemble --count \"<count.json>\" --col-map \"0=1#楼/1单元;8=7#楼/1单元,8#楼/1单元\" --coverage \"<coverage.json>\" --out \"<assembly.json>\"",
    "pipeline":
        "ftth.py pipeline --dxf \"<图.dxf>\" --outdir \"<产物目录>\" --project-dir \"<项目目录>\""
}


class _CliParser(argparse.ArgumentParser):
    """报错时补「可用参数 + 正确示例 + 契约指引」，把"猜参数"变成"照着改"。

    只覆盖报错路径：正常解析、成功路径的行为与退出码均不变。
    """

    def error(self, message):
        parts = (self.prog or "").split()
        sub = parts[-1] if len(parts) > 1 else ""
        # 子解析器的 error 能直接拿到 prog；但 `unrecognized arguments` 是**顶层**
        # parse_args 抛的（子解析器只做 parse_known_args），此时 prog 只有 "ftth.py"。
        # 该形态恰好是调用方最常撞上的（猜错参数名），所以从 argv 回捞子命令名，
        # 并换用该子解析器承载的参数表 —— 否则最需要帮助的那次报错反而没有提示。
        sp = self
        subs = []
        for a in self._actions:
            if not isinstance(a, argparse._SubParsersAction):
                continue
            subs.extend(sorted(a.choices.keys()))
            if not sub:
                for tok in sys.argv[1:]:
                    if not tok.startswith("-") and tok in a.choices:
                        sub = tok
                        break
            if sub and sub in a.choices:
                sp = a.choices[sub]
            break
        if sub == "count-hdd":          # 别名 -> 主名，保证能取到示例
            sub = "count-box"
        sys.stderr.write("\n[参数错误] %s\n" % message)
        opts = []
        for a in sp._actions:
            if isinstance(a, (argparse._HelpAction, argparse._SubParsersAction)):
                continue
            names = [n for n in (a.option_strings or []) if n != "-h"]
            if not names:
                continue
            tag = "/".join(names)
            if getattr(a, "required", False):
                tag += "(必填)"
            opts.append(tag)
        if subs:
            sys.stderr.write("[子命令]   %s\n" % "  ".join(subs))
        if opts:
            sys.stderr.write("[可用参数] %s\n" % "  ".join(opts))
        ex = _CMD_EXAMPLES.get(sub)
        if ex:
            sys.stderr.write("[正确示例] %s\n" % ex)
        sys.stderr.write("[完整契约] references/scripts_reference.md -> "
                         "「子命令 x 上游产物 依赖矩阵」\n")
        self.exit(2)


# ---------------------------------------------------------------------------
# pipeline：一条命令串跑 Step 1a~2 的多阶段（2026-09-17 新增）
#
# 为什么需要它（实测依据，非设计偏好）：
#   经启动器逐条直调时，**每条命令**都要固定付一份启动开销 ——
#     旧 cmd 启动器实测：探测 `python -c "import ezdxf"` 1.93s + _launch.py 1.13s + ftth.py 0.65s ≈ 3.7s。
#   实测某图 12 次调用共 66.05s，其中约 43s 是这层开销，真正算数只占小头。
#   本命令只起一次调度进程，各阶段以子进程直调 ftth.py（不再经启动器 ftth_launcher.py），
#
# 语义边界（刻意约束，不得放宽）：
#   * 只做解析、不做裁决：到 inspect 为止，**不含 gen**。出表必须等人工裁决
#     （覆盖范围 / 安装楼层 / 待确认项），流水线不得替人拍板。
#   * 不静默续跑：任一阶段 rc 非 0 即停，并原样返回该 rc；
#     仅 rc=3（本图确实不提供该子任务数据，申报制）不中止，记为该阶段「不适用」。
#   * 产物用固定文件名落在 --outdir 下，之后仍可单条命令接着跑或重跑其中一段。
# ---------------------------------------------------------------------------
# 2026-09-18（第 2 轮）顺序修正：fxmap 提到 parse **之前** —— SKILL.md 硬约束② 要求
#   「楼栋/单元归属必须以图纸自带的分纤箱总图对照表为准」，parse 自身也按标题 x 中分
#   归属文字，故它同样需要对照表。此前 fxmap 排 parse 之后 = 先用被明文禁止的方法切完、
#   再拿正确数据去补 coverage → parse 侧永远 0 箱。
# 2026-09-25（实跑修复，P0）：新增 `count_box` 阶段（coverage 与 inspect 之间）。
#   画像 handoff 早在 plan 阶段就申报「每层户数=图标法（count_box_icons.py）」（云峰
#   实测：第 13 秒已申报），但阶段表里没有它 —— 跑完整链（137s）后 inspect 的 C5/C8
#   才以 SKIP 提示「户数须由图标法提供」，用户还得手工补 count-box 再重跑 inspect
#   （9/18 云峰留有 count_box.json / count_box_fixed.json 两轮手工痕迹）。
#   「规则写在文档里、没有代码执行」—— 与 ③b titleblock、④b fx_locations 同一形态。
#   仅画像申报脚本 == count_box_icons.py 时执行（方法池同级，不替画像择法）；
#   rc=2（输入不足）中止主链、rc=3（本图不适用）继续 —— 与 parse/coverage 同语义。
_PIPE_STAGES = ("geom", "probe", "plan", "titleblock", "fxmap", "fx_locations",
                "unit_gaps", "parse", "coverage", "count_box", "inspect")
# 2026-09-18（用户裁定）新增 `unit_gaps`：探查期「单元 × 箱清单」交叉清点，位置在
#   parse **之前** —— 骨架(titleblock)与箱清单(fxmap/fx_locations)两样证据在 parse 前
#   就已落盘，故「某单元没分纤箱」可提前暴露，不必等 Step 2 覆盖门禁（那时返工面大）。

# 画像里申报的覆盖判定脚本 -> 本入口的子命令名
_COV_SCRIPT_TO_CMD = {
    "analyze_coverage_vshape.py": "coverage-vshape",
    "analyze_coverage.py": "coverage",
}

# 本入口各子任务**实际接得上**的脚本（能力表；2026-09-27 P0-1 立）。
#   与 plan_methods 的「候选表」是两个不同的东西：候选表 = 方法学上**有哪些路**，
#   本表 = 本入口**实际执行得了哪几条**。二者不一致时必须**报人**，不得静默跳过。
#   退出条件：某子任务新增产出口（新阶段或并入既有阶段）即补进本表。
# 唯一来源纪律（operations_discipline §十二）：覆盖一栏由 _COV_SCRIPT_TO_CMD 派生，
#   **禁止另抄一份** —— 两处各写一份必然漂移，漂移即等于门禁失效。
#   键名口径：用 **handoff 子任务名**（画像里的写法），不是 build_steps 的步骤名 ——
#   同一子任务两处叫法不同（画像「覆盖范围」/ 步骤「覆盖判定」），取画像侧以免对不上。
_PIPE_CAPABILITY = {
    "覆盖范围": frozenset(_COV_SCRIPT_TO_CMD),
}


def _pipe_capability_problems(profile_path):
    """校验画像申报的脚本是否在本入口能力表内；返回问题清单（空 = 通过）。

    背景（2026-09-27，P0-1 实跑核证）：此前 plan 可申报一个本入口**没有映射**的脚本
    —— 实测覆盖判定 primary = `parse_dxf_structured.py`（生产侧对该标注零实现）。
    调用点把「映射不到」当成「本图不适用」**静默跳过**，后果是：
      ① 覆盖零产出，直到 `inspect` C6 才 FAIL，报错文案还指向画像，误导排查方向；
      ② 同可用备选（V型/竖线）**不会自动兜底** —— 最优证据反而把结果拦死。
    故本函数在 plan **之后**立即对拍，不一致即 rc=2 停下报人（fail-closed，不静默）。"""
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            prof = json.load(f)
    except Exception as e:                                          # noqa: BLE001
        return ["画像不可读(%s) —— 无法核对选法与本入口能力表是否一致" % e]
    sysm = ((prof.get("handoff") or {}).get("②系统图选法") or {})
    probs = []
    for sub, cap in _PIPE_CAPABILITY.items():
        sel = sysm.get(sub) or {}
        decl = str(sel.get("申报") or sel.get("状态") or "").strip().lower()
        script = str(sel.get("脚本") or "").strip()
        # absent/missing/none ⇒ 本图不提供该子任务，本阶段合法缺席（rc=3），不核
        if not script or decl in ("absent", "missing", "none"):
            continue
        if script not in cap:
            probs.append(
                "②系统图选法·%s：画像申报脚本 %r **不在本入口能力表** %s 内 —— "
                "该路 plan 声明了、流水线却接不上（无执行方）。不得当「本图不适用」"
                "静默跳过；须接入产出口，或改用能力表内的方法。"
                % (sub, script, sorted(cap)))
    return probs


def _pipe_coverage_choice(profile_path):
    """从画像读出覆盖判定选中的脚本，映射为本入口子命令名。

    返回 `(子命令名 或 None, 说明文本, blocked)`。`blocked=True` ⇒ 调用方**不得**
    当「本图不适用」跳过，须 rc=2 停下报人。四种情形：
      ① `blocked=True` 画像申报 unimplemented（图上有该证据、本技能无产出口）；
      ② `blocked=True` 申报了脚本但本入口映射不到（如 `parse_dxf_structured.py`）
         —— 与 `_pipe_capability_problems` 同一判据（能力表唯一来源）；
      ③ 画像不可读 → 同 ②（须显式暴露，不得静默挑一个方法）；
      ④ `(None, note, False)` 画像申报本图不提供覆盖范围（absent）—— 该阶段合法缺席。
      2026-09-27（P0-1）：② 此前被静默当成「不适用」跳过（回 rc=3），导致覆盖零产出、
      直到 inspect C6 才 FAIL 且文案指向画像；现改为 fail-closed 报人。
    """
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            prof = json.load(f)
    except Exception as e:                                          # noqa: BLE001
        return None, "画像不可读: %s" % e, True
    sel = (((prof.get("handoff") or {}).get("②系统图选法") or {}).get("覆盖范围") or {})
    decl = str(sel.get("申报") or sel.get("状态") or "").strip().lower()
    if decl == "unimplemented":
        return None, ("画像申报覆盖判定=unimplemented（信号成立但本技能未接入产出口："
                      "%s）" % (sel.get("阻塞原因") or sel.get("脚本"))), True
    if decl in ("absent", "missing", "none"):
        return None, "画像申报本图不提供覆盖范围数据(%s) -> 该阶段合法缺席" % decl, False
    cmd = _COV_SCRIPT_TO_CMD.get(sel.get("脚本"))
    if cmd:
        return cmd, "%s <- %s" % (sel.get("选定方法") or cmd, sel.get("脚本")), False
    return None, ("画像申报的覆盖判定脚本 %r 不在本入口能力表 %s 内 —— 该路无执行方，"
                  "不得当「本图不适用」跳过"
                  % (sel.get("脚本"), sorted(_PIPE_CAPABILITY["覆盖范围"]))), True


def _pipe_countbox_choice(profile_path):
    """从画像读出「每层户数」选法，判定 count_box 阶段是否执行。

    2026-09-25（实跑修复，P0）：返回 (执行?, 说明文本)。**仅当画像申报每层户数
    脚本 == count_box_icons.py（图标法）时执行**；其余（含 absent / 皮线法 /
    parse 直读 / 画像不可读）一律不执行并显式说明 —— 方法池同级，不替画像择法，
    「不执行」不是错误：本图按画像申报走它自己的路。
    """
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            prof = json.load(f)
    except Exception as e:
        return False, "画像不可读(%s) -> 不执行 count-box（不静默择法）" % e
    sel = (((prof.get("handoff") or {}).get("②系统图选法") or {}).get("每层户数") or {})
    script = str(sel.get("脚本") or "").strip()
    if script == "count_box_icons.py":
        return True, "画像申报每层户数=%s（图标法）" % (sel.get("选定方法") or script)
    if not script:
        decl = str(sel.get("申报") or sel.get("状态") or "").strip()
        return False, "画像未申报每层户数方法(申报=%r) -> 本图户数不走 count-box" % (decl or "unknown")
    return False, "画像申报每层户数脚本=%s（非图标法）-> 本图户数不走 count-box" % script


def _cb_fingerprint_ok(cb_path, dxf):
    """count_box.json 的 DXF 指纹校验（2026-09-25，opencode 审核建议③）。

    同 outdir 换 DXF 重跑时，旧 count_box.json 是**另一张图**的户数——
    静默复用会喂错数据。比对产物「输入」字段（count_box_icons.py 写的完整
    DXF 路径）的 basename 与当前 dxf：
      - 一致或产物无该字段/读失败 → True（可复用，兼容旧产物）
      - 不一致 → False（另一张图的产物，须 fresh-run 重算）
    """
    try:
        with open(cb_path, "r", encoding="utf-8") as f:
            recorded = str((json.load(f) or {}).get("输入") or "").strip()
    except (IOError, json.JSONDecodeError, OSError):                 # noqa: BLE001
        return True  # 读不了/无字段：不阻止复用（旧产物兼容），风险由 WARN 提示兜底
        # 退役条件：count_box 产物指纹字段全覆盖 + stale 守卫接管后，改为读失败即 False
        # （须 fresh-run 重算）。fail-open 是过渡态，静默复用错图即喂错数据（分支预算纪律 §十一）。
    if not recorded:
        return True
    return os.path.basename(recorded) == os.path.basename(dxf)


def _fb_floor_key(name):
    """回落转换逐层排序键：已知楼层按数值排（B1/-1F为负，WF=900在末），
    未知排最后。2026-09-27二轮改走 floor_num 统一入口（旧手写正则不认
    WF/中文层/N层/室尾缀，与主链口径不一致）。仅排序用，不作判定。"""
    v = floor_num(str(name or "").strip(), use_fullmatch=True)
    if v is not None:
        return (0, v)
    return (1, 0)


def _cb_convert_wire_fallback(fb_path, dxf, cb_out):
    """count 产物 → count_box.json 的「列」格式（2026-09-26，示意画法 L1-C1 回落）。

    逐楼栋的「皮线列」每一项转成一个「列」条目（列x / x范围 / y范围 / 逐层 /
    合计 / 图标数，其中「图标数」语义为皮线文字条数）；列→楼栋归属是裁决项，
    转换不携带楼栋归属（col-map 由 assemble 阶段人工裁决映射，含共享列克隆）。
    「同一端点多候选」/「未归属图标数」补空值，仅为与 inspect C5 质量透传字段
    对齐（皮线口径下这两项无意义，恒空/零）。
    返回 (True, 总户数) / (False, 原因)。
    """
    try:
        with open(fb_path, "r", encoding="utf-8") as f:
            fb = json.load(f) or {}
    except Exception as e:                                          # noqa: BLE001
        return False, "回落产物 %s 不可读：%s" % (fb_path, e)
    bldgs = fb.get("楼栋") or {}
    if not bldgs:
        return False, "回落产物 %s 无「楼栋」数据" % fb_path
    # 2026-09-26（第4轮 Bug A）：逐层改从各线归属明细按列聚合，不再用楼栋级每层户数线索（多列楼栋会被双计）。
    try:
        _tol = float((fb.get("参数") or {}).get("x_cluster") or 0) or None
    except (TypeError, ValueError):
        _tol = None
    if not _tol or _tol <= 0:
        _tol = 20.0  # count_households.DEFAULT_X_CLUSTER 回退（产物无参数时）
    cols = []
    _conv_warns = []
    for _bname in sorted(bldgs):
        _b = bldgs[_bname] or {}
        _details = _b.get("各线归属明细") or []
        for _c in (_b.get("皮线列") or []):
            try:
                _x = float(_c.get("x"))
            except (TypeError, ValueError):
                return False, "回落产物皮线列缺 x：%r" % (_c,)
            _ymin, _ymax = _c.get("y_min"), _c.get("y_max")
            if _ymin is None or _ymax is None:
                return False, "回落产物皮线列 x=%s 缺 y_min/y_max" % (_c.get("x"),)
            try:
                _units = int(_c.get("折算户数"))
                _n = int(_c.get("条数"))
            except (TypeError, ValueError):
                return False, "回落产物皮线列 x=%s 缺 折算户数/条数" % (_c.get("x"),)
            _agg = {}
            for _d in _details:
                try:
                    _dx = float((_d or {}).get("x"))
                except (TypeError, ValueError):
                    continue
                if abs(_dx - _x) > _tol:
                    continue
                _fl = (_d or {}).get("归属")
                if not _fl:
                    continue
                try:
                    _hu = int((_d or {}).get("户数", 1))
                except (TypeError, ValueError):
                    _hu = 1
                _agg[_fl] = _agg.get(_fl, 0) + _hu
            _floors = [[_fn, _agg[_fn]] for _fn in
                       sorted(_agg, key=lambda n: (_fb_floor_key(n), str(n)))]
            _s = sum(_v for _, _v in _floors)
            if _s != _units:
                _w = ("列x=%s（栋%s）：Σ逐层=%d ≠ 折算户数=%d（|明细x-列x|≤%s 聚合；差值多为未归属皮线）"
                      % (round(_x, 1), _bname, _s, _units, _tol))
                _conv_warns.append(_w)
            cols.append({"列x": round(_x, 1), "x范围": [_x, _x],
                         "y范围": [round(_ymin, 2), round(_ymax, 2)],
                         "逐层": _floors, "合计": _units, "图标数": _n})
    if not cols:
        return False, "回落产物皮线列为空（无户数可转）"
    total = sum(_c["合计"] for _c in cols)
    _note = ("示意画法确认（count_box_icons.py [DIAG-SCHEMATIC-ICONS]，rc=3）后按 "
             "L1-C1（2026-09-16 裁决）回落皮线：本文件由 %s 格式转换而来，"
             "「图标数」语义为皮线文字条数；列→楼栋归属未携带，由 assemble "
             "阶段人工 col-map 裁决（含共享列克隆）；逐层按 |明细x-列x|≤列聚类容差(%s) "
             "从各线归属明细聚合（楼栋级每层户数线索不进转换）。" % (fb_path, _tol))
    if _conv_warns:
        _note += "转换守卫Σ逐层≠折算户数（不中断）：%s" % "；".join(_conv_warns)
        print("[count_box] ! 回落转换守卫：Σ逐层≠该列折算户数（不中断，已登记）：%s"
              % "；".join(_conv_warns), flush=True)
    out = {
        "口径": "皮线回落（示意画法；L1-C1 2026-09-16 裁决）",
        "输入": os.path.abspath(dxf),
        "乘号式户数标注": [],
        "刻度偏移异常列": [],
        "共用刻度列组": [],
        "同一端点多候选": [],
        "未归属图标数": 0,
        "归层后总户数": total,
        "列": cols,
        "说明": _note,
    }
    try:
        write_json(cb_out, out)
    except OSError as e:
        return False, "写 %s 失败：%s" % (cb_out, e)
    return True, total


def _pipe_hint_fx_symbol_cands(profile_path):
    """箱符号层「未推荐」时把候选明细摆出来 —— 解决「有答案但不可达」。

    **入参是画像文件路径**（与同级 `_pipe_effective_layers` / `_pipe_profile_status`
    保持一致）；此处不假设调用方已把 JSON 读成 dict —— 实测按 dict 取值直接
    AttributeError 让整条流水线 rc=1，比原来的 rc=2 更难排查。

    背景（2026-10-05，P1）：探查侧确实给每个候选层打过分并落进了
    profile.probe_signals.fx_symbol_layer_candidates，但只有达到「推荐」门槛
    （一致性>=0.8 且 标题区重叠>=0.8 且 数量吻合）的才会写进 suggested_params 下传。
    未达标者被埋着，而 coverage 的失败文案却把人导向「去核对图层名是不是不对」——
    排错方向错了，且猜图层名本身就在踩「靠猜不当」的坑。

    此处**只 print 不决策**：候选连同其未达标分项一并给出，供人据此显式指定或
    确认本图确无符号画法；未达门槛者绝不由本函数自动采信下发。

    返回 bool：是否打印了候选（供调用方判断是否还需别的提示）。
    """
    try:
        with open(profile_path, "r", encoding="utf-8") as _f:
            prof = json.load(_f)
    except Exception as _e:                                            # noqa: BLE001
        print("[pipeline] ! 画像不可读，无法给出箱符号层候选明细：%s" % _e, flush=True)
        return False
    _cands = ((prof or {}).get("probe_signals") or {}).get(
        "fx_symbol_layer_candidates") or []
    if not isinstance(_cands, list):
        _cands = []
    if not _cands:
        print("[pipeline] ! 本画像**没有任何**箱符号层候选 —— coverage 将扫全图找符号，"
              "很可能因此找不到（若本图箱体只写编号、不画符号，加 --allow-low-pairing "
              "强行继续，结果须人工复核）", flush=True)
        return False
    _rec = [c for c in _cands if c.get("推荐")]
    print("[pipeline] 探查给出 %d 个箱符号层候选，其中达「推荐」门槛 %d 个 —— "
          "未达门槛者不予下发（门槛：一致性>=0.8 且 标题区重叠>=0.8 且 数量吻合）："
          % (len(_cands), len(_rec)), flush=True)
    for _cd in _cands[:3]:
        print("    · 层=%s 得分%.2f 推荐=%s（一致性%.2f｜标题区重叠%.2f｜闭合矩形%d｜"
              "众数簇%d｜众数尺寸%s）"
              % (_cd.get("层"), _cd.get("得分", 0.0), _cd.get("推荐"),
                 _cd.get("一致性", 0.0), _cd.get("标题区重叠", 0.0),
                 _cd.get("闭合四点矩形", 0), _cd.get("众数簇", 0),
                 _cd.get("众数尺寸")), flush=True)
    print("[pipeline] 处置二选一（均须人工核对，脚本不代判）：", flush=True)
    print("    ① 若经人工核对确认其中某层确为符号层 → 用 --fx-symbol-layer <层名> 显式指定；",
          flush=True)
    print("    ② 若本图箱体确为「只写编号、不画符号」 → 加 --allow-low-pairing 继续"
          "（箱位会回退编号文字坐标，结果须人工复核）", flush=True)
    return True


def _pipe_fanout_bands(args, dxf, outdir, cfg, pdir, brief_keep=None):
    """多地块图：**自动分带 + 对每个子带跑完整 pipeline**（扇形展开）。

    背景（2026-10-05）：`split-band` 此前只作为**独立子命令**存在，pipeline 阶段链里
    根本没有这一环 —— 源码注释自承「规则写了、尺寸量了、**执行环节零接线**」。后果是
    任何多地块图跑到 parse 必然撞「多地块同名楼」守卫 rc=2（该守卫本身正确：全图解析
    会让同名楼栋按楼名去重、静默串号），而**被提示的正确路径（split-band）在串跑里
    走不到**，只能人工手搓。

    设计（最小侵入）：
      * 仅在 plan 之后、parse 之前介入；**单地块图不受影响**（子带数 < 2 即原路返回）。
      * 子带各跑一条完整 pipeline（递归调本入口），产物落在 <outdir>/bands/<带名>/。
      * 递归时**必须关掉分带**（--no-auto-split-band），否则子图可能二次分带。
      * 汇总退出码 = 各子带最严重者；任一子带失败即非 0（不把部分成功当整体成功）。

    返回 None = 未触发（调用方继续单地块原路径）；否则返回汇总退出码。
    """
    if not getattr(args, "auto_split_band", True):
        return None
    bands_dir = os.path.join(outdir, "bands")
    _self = str(Path(__file__).resolve())
    print("[pipeline] 多地块检测：先跑 split-band --auto 量分带方案 ……", flush=True)
    _rc = subprocess.call([sys.executable, _self, "split-band", "--auto", "--yes",
                           "--dxf", dxf, "--config", cfg, "--out-dir", bands_dir])
    if _rc == 3:
        print("[pipeline] 单地块图无需分带（split-band rc=3 不适用）→ 按单地块原路径继续"
              "（若本图确为多地块，请人工跑 split-band 后逐带处理）", flush=True)
        return None
    if _rc != 0:
        print("[pipeline] ! split-band 退出码 %d —— 不扇出，按单地块原路径继续（"
              "若本图确为多地块，请人工跑 split-band 后逐带处理）" % _rc, flush=True)
        return None
    if not os.path.isdir(bands_dir):
        return None
    _subs = sorted(p for p in os.listdir(bands_dir) if p.lower().endswith(".dxf"))
    if len(_subs) < 2:
        print("[pipeline] 分带结果 %d 个子图 → 非多地块（或只有一带），按单地块原路径继续"
              % len(_subs), flush=True)
        return None
    print("[pipeline] ✔ 检出 %d 个地块子图 → 逐个跑完整 pipeline（产物在 bands/<带名>/）"
          % len(_subs), flush=True)
    _worst = 0
    _rows = []
    for _s in _subs:
        _name = _s[:-4]
        _sub_out = os.path.join(bands_dir, _name)
        _argv = ["pipeline", "--dxf", os.path.join(bands_dir, _s),
                 "--outdir", _sub_out, "--no-auto-split-band",
                 "--stop-at", (args.stop_at or "inspect")]
        if pdir:
            _argv += ["--project-dir", pdir]
        if getattr(args, "project", None):
            _argv += ["--project", args.project]
        if args.quiet:
            _argv += ["--quiet"]
        elif getattr(args, "brief", False):
            _argv += ["--brief"]
        if getattr(args, "allow_low_pairing", False):
            _argv += ["--allow-low-pairing"]
        print("[pipeline] ── 子带 %s ──" % _name, flush=True)
        _rc = subprocess.call([sys.executable, _self] + _argv)
        if _rc > _worst:
            _worst = _rc
        _rows.append((_name, _rc, os.path.join(_sub_out, "inspect.json")))
        print("[pipeline] ── 子带 %s 结束 rc=%d ──" % (_name, _rc), flush=True)
    # 扇出汇总必须逐带点名（2026-10-05）：此前只给一个「最严重退出码」，
    # 实测柳辛庄 5-9 地块 band5 在 coverage 阶段 rc=2 中止 → 20 箱覆盖未判定、
    # 4 项 parse 待裁决从未进入任何报告，而汇总只有一个数字 —— 这正是本技能
    # L0「不静默丢数」与 Step 2「空集合不得判 PASS」要禁的形态：未判定被
    # 折进退出码，人要逐个翻目录才发现该带根本没出 inspect。
    # 故此处逐带报 rc，并**显式点名「未出 inspect」的带**（缺产物 ≠ 通过）。
    print("[pipeline] 多地块扇出汇总：%d 个带，最严重退出码 %d" % (len(_subs), _worst),
          flush=True)
    _missing = []
    for _name, _rc, _ij in _rows:
        if os.path.isfile(_ij):
            print("[pipeline]   · %s：rc=%d，已出 inspect.json" % (_name, _rc), flush=True)
        else:
            _missing.append(_name)
            print("[pipeline]   · %s：rc=%d，**未出 inspect.json —— 该带内容未判定**"
                  "（不是通过；按该带 logs/ 末段给出的处置调参或人工核对后重跑）"
                  % (_name, _rc), flush=True)
    if _missing:
        print("[pipeline] ⚠ %d 个带未判定（%s）—— 整图不得出表；逐带处置见上"
              % (len(_missing), "、".join(_missing)), flush=True)
    return _worst


def _pipe_effective_layers(profile_path):
    """从画像读出**机器可读**的图层建议，返回 (dict, 来源说明)。

    优先读 `effective_layers`（2026-09-18 起由 plan 产出，值为纯层名或 null）。
    老画像没有该字段时回退读 `param_source.must_probe`，但**必须过滤提示语** ——
    该字段历史上把「值」和「提示文案」混排（无候选时写的是整句中文说明），
    直接当参数传会把中文句子送进脚本。读不到一律返回空 dict：不猜。
    退役条件：老画像自然消亡（effective_layers 全覆盖）后删除回退分支（分支预算纪律 §十一）。
    """
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            prof = json.load(f)
    except Exception as e:                                            # noqa: BLE001
        print("[pipeline] DEBUG: 画像读取失败 %s: %s" % (profile_path, e), file=sys.stderr)
        return {}, "画像不可读"
    lay = prof.get("effective_layers")
    if isinstance(lay, dict):
        ok = {k: str(v).strip() for k, v in lay.items()
              if k in ("wire_layer", "fx_symbol_layer")
              and isinstance(v, str) and v.strip()}
        return ok, "effective_layers"
    mp = ((prof.get("param_source") or {}).get("must_probe") or {})
    _hint_words = ("须", "本图", "未给出", "人工", "可能只写", "禁用", "不得")
    ok = {}
    for k in ("wire_layer", "fx_symbol_layer"):
        v = mp.get(k)
        if isinstance(v, str) and v.strip() and not any(w in v for w in _hint_words):
            ok[k] = v.strip()
    return ok, "param_source.must_probe(兼容老画像)"


def _pipe_profile_status(profile_path, signal):
    """读画像里某信号的状态字符串（小写），读不到返回空串。"""
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            prof = json.load(f)
    except Exception as e:                                            # noqa: BLE001
        print("[pipeline] DEBUG: 画像信号读取失败 %s: %s" % (profile_path, e), file=sys.stderr)
        return ""
    return str((((prof.get("signals") or {}).get(signal) or {}).get("status"))
               or "").strip().lower()


def _pipe_fxloc_state(profile_path, cfg_path):
    """读「箱位直读标注」信号 fx_location_annotation 的状态（小写，可能是 present(N条)）。

    2026-09-18：该信号**不在 profile.signals 里** —— 它是**探查信号**，由 probe 产出、
    plan 原样透传进 ``profile.probe_signals``；老画像可能只在 config.json 顶层有。
    两处都读、取先命中者，避免「换了个画像版本就读不到 ⇒ 阶段静默跳过」。
    调用方按 **前缀** 判定 present（值形如 ``present(84条)``）。
    """
    for path, pick in ((profile_path, lambda d: (d.get("probe_signals") or {})
                        .get("fx_location_annotation")),
                       (cfg_path, lambda d: d.get("fx_location_annotation"))):
        try:
            with open(path, "r", encoding="utf-8") as f:
                v = pick(json.load(f))
        except Exception:                                            # noqa: BLE001
            continue
        s = str(v or "").strip().lower()
        if s:
            return s
    return ""


def _pipe_fxmap_gate(profile_path):
    """judge 是否执行 fxmap（总图对照表）阶段。返回 (是否执行, 依据说明)。

    2026-09-18（第 4 轮，用户裁决收紧）：**仅当画像申报存在集中总图对照表
    （fx_overview_map = present / handoff① 状态 = present）时才产出 fxmap**。

    此前（第 2/3 轮）判据是「有编号可提就跑」——把 fx_overview_map=absent
    （编号嵌在各楼系统图楼层表内部）的图也强行产出降级对照表，其「安装楼层」
    是拿编号文字 y 去**全图楼层刻度混排**推算出来的（不在四种测量方法内），
    且会被 pipeline 自动回填 parse（--bldg-map / --fx-map），造成：
      · 安装楼层出现与 V型/区间法矛盾（实测凤鸣朝阳 8 箱假矛盾 8F vs 5F）；
      · 单元归属被对照表标题名覆盖，parse 楼层表整批丢失（实测 193→313 户）。
    按用户裁决：分纤箱所在楼层 / 覆盖 / 每层户数，来源**只允许四种方法**
    （图上标注直读、V型计算、区间法、竖线法）与不同图纸的多方标注互验，
    **AI 不得自创算法参与校验**；「y 坐标关联推算」不在四法内 ⇒ 不得产出。

    新判据：handoff「①分纤箱总图」状态 == present 才跑；absent / variant
    一律跳过（rc=3 语义），不再产出降级对照表。老画像无 handoff 时回退到
    信号 fx_overview_map == present。用户**显式 --bldg-map** 仍受尊重
    （人工确认过总图，属「图上标注直读」来源）。
    """
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            prof = json.load(f)
    except Exception as e:                                            # noqa: BLE001
        print("[pipeline] DEBUG: fxmap gate 画像读取失败 %s: %s" % (profile_path, e), file=sys.stderr)
        return False, "画像不可读"
    ho = prof.get("handoff") or {}
    ent = None
    for k, v in ho.items():
        if isinstance(v, dict) and "分纤箱总图" in str(k):
            ent = v
            break
    if ent is not None:
        st = str(ent.get("状态") or "").strip().lower()
        if st == "present":
            n_id = 0
            try:
                n_id = int(ent.get("编号数") or 0)
            except (TypeError, ValueError):
                n_id = 0
            return True, "画像申报有集中总图（状态=present，编号 %d 个）→ 按对照表定归属" % n_id
        return False, ("画像申报无集中总图（状态=%s）→ 不产出对照表："
                       "y 坐标关联推算不在四种测量方法内（用户裁决 2026-09-18），"
                       "安装楼层由方法池（区间法/V型/直读）测量，不做对照表回填" % (st or "?"))
    # 老画像无 handoff ①：回退到信号
    if _pipe_profile_status(profile_path, "fx_overview_map") == "present":
        return True, "（老画像无 handoff①）信号 fx_overview_map=present"
    return False, "画像未申报总图对照表（无 handoff①，且 fx_overview_map≠present）"


def _pipe_gap_verdict(path):
    """读探查期预检产物 unit_box_gaps.json，返回 (结论, 说明) 供流水线打印。

    三种结论语义**必须区分**（混淆即产生假绿灯或假失败）：
      · ``pending``    —— 两侧来源齐备且差集非空，**有疑点要报人**；
      · ``settled``    —— 两侧齐备且一致；
      · ``unresolved`` —— **某侧来源未就绪，本次未判定**。它不是「通过」，
                          覆盖阶段门禁仍会兜底（不得据此跳过后续检查）。
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:                                            # noqa: BLE001
        print("[pipeline] DEBUG: gap verdict 读取失败 %s: %s" % (path, e), file=sys.stderr)
        return None
    if not isinstance(d, dict):
        return None
    v = d.get("预检结论")
    if not v:
        return None
    return str(v), str(d.get("预检说明") or "")


_NONSTD_JSON_TOKENS = ("Infinity", "-Infinity", "NaN")


def _reject_json_const(name):
    """json.load 的 parse_constant 钩子：遇到非标准字面量即抛错。"""
    raise ValueError("非标准 JSON 字面量 `%s`" % name)


def _scan_nonstd_json(outdir):
    """扫描产物目录下的 *.json，返回 [(文件名, 原因)] —— 只为「非标准 JSON」这种事存在。

    动机（2026-09-18 实测）：Python 的 json.dump 默认把 inf/nan 写成
    `Infinity`/`NaN`，而它们**不在 JSON 规范内** —— JS/Go 等严格解析器会拒绝
    **整份**文件，而不是跳过那个字段。产物一旦这样出厂，下游任何非 Python 工具
    都读不进来，而 Python 侧照样 rc=0（自己的 json.load 是宽容的）。
    ⇒ 闸门放出口：流水线跑完扫一遍，命中即把 rc 抬到 2，不让它静默出关。
    """
    bad = []
    if not os.path.isdir(outdir):
        return bad
    for name in sorted(os.listdir(outdir)):
        if not name.endswith(".json"):
            continue
        fp = os.path.join(outdir, name)
        try:
            with open(fp, encoding="utf-8") as f:
                json.load(f, parse_constant=_reject_json_const)
        except ValueError as e:
            bad.append((name, str(e)))
    return bad


def cmd_summary(args) -> int:
    """打印 parsed.json 的楼栋×单元×楼层×户数×分纤箱总览表。

    2026-10-04（P1-E4）：Step 3 提交材料的半成品，取代手写汇总脚本。
    内联实现，不产生子脚本依赖。可选合并 coverage.json 的覆盖楼层列。
    """
    with open(args.parse_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    buildings = data.get("楼栋", {})
    if not isinstance(buildings, dict):
        print("[summary] parsed.json 的「楼栋」字段不是字典，无法汇总")
        return 1

    # 可选：读 coverage.json 补覆盖楼层
    cov_map = {}  # (楼栋, 单元, 箱号) -> 覆盖楼层
    if args.coverage_json and os.path.isfile(args.coverage_json):
        with open(args.coverage_json, "r", encoding="utf-8") as f:
            cov = json.load(f)
        for bname, b in (cov.get("楼栋") or {}).items():
            for uname, u in (b.get("单元") or {}).items():
                for fx in (u if isinstance(u, list) else u.get("分纤箱", [])):
                    if isinstance(fx, dict):
                        cov_map[(bname, uname, fx.get("编号", ""))] = fx.get("覆盖楼层", "")

    total_hu = 0
    total_units = 0
    fx_rows = []
    print("=" * 72)
    for bname in sorted(buildings.keys(), key=lambda s: int(''.join(c for c in s if c.isdigit()) or '0')):
        b = buildings[bname]
        units = b.get("单元", {})
        print(f"\n== {bname} ==  标题: {b.get('标题', '')}  单元数: {len(units)}")
        for uname in sorted(units.keys(), key=lambda s: int(''.join(c for c in s if c.isdigit()) or '0')):
            u = units[uname]
            total_units += 1
            fxs = u.get("分纤箱", [])
            if isinstance(fxs, str):
                fxs = []
            ft = u.get("楼层表", {}) or {}
            hu_sum = 0
            anno_layers = []
            null_layers = []
            # 2026-10-04 实测修复（P0）：原为手写 `int(k.replace('F',''))`，只认 '18F'/
            #   '-1F'，图上出现 'B1'（负楼层中文写法，naming 模块与 Step 1c 均列为已知
            #   形态）即 ValueError 崩溃、整个总览不可用。此处是同一份实现的漏网手抄本，
            #   现统一走 floor_num_or_zero（唯一入口，支持 B1/B2/WF/-1F/18F/中文层）。
            for fl in sorted(ft.keys(), key=lambda k: floor_num_or_zero(k)):
                rec = ft[fl]
                hu = rec.get("户数")
                if hu is None:
                    null_layers.append(fl)
                else:
                    hu_sum += int(hu)
                    anno_layers.append(f"{fl}={hu}")
            total_hu += hu_sum
            print(f"  {uname}: {hu_sum}户  {' '.join(anno_layers)}")
            if null_layers:
                print(f"    无户数层: {', '.join(null_layers)}")
            for fx in fxs:
                if isinstance(fx, dict):
                    fxid = fx.get("编号", "")
                    inst = fx.get("安装楼层", "")
                    cov_fl = cov_map.get((bname, uname, fxid), "")
                    cov_str = f"  覆盖={cov_fl}" if cov_fl else ""
                    print(f"    {fxid} 安装={inst}{cov_str}")
                    fx_rows.append((bname, uname, fxid, inst, cov_fl))
    print("\n" + "=" * 72)
    print(f"汇总: 楼栋={len(buildings)} 单元={total_units} 户数={total_hu} 分纤箱={len(fx_rows)}")
    return 0


def cmd_verify_answer(args) -> int:
    """成品 xlsx vs 参考答案 xlsx 逐行对拍（楼栋/单元/楼层/户号/分纤箱 五列）。

    2026-10-04（P1-E5）：用户固定工作流收尾步骤，取代手写对拍脚本。
    按「楼栋列非空」过滤水印行；输出差异行 + 每栋汇总。
    内联实现，不产生子脚本依赖。

    2026-10-05（一百五十九）：五列**按表头名定位**，不再硬写列字母 —— 初版写的
    H/J/L/N/P 只是 24 列定稿模板的布局，用在 11 列降级表上会整体错位。docstring
    同步改写（原「（H/J/L/N/P 五列）」已与实现不符，文档层不得滞后于规则层）。
    """
    try:
        from openpyxl import load_workbook
    except ImportError:
        print("[verify-answer] 需要 openpyxl，请先安装")
        return 1

    # 2026-10-05（一百五十九，边界探针 E6）：开卷前先验输入。实测传一个**存在但
    #   不是 Excel** 的路径（如 .dxf）时，openpyxl 抛 InvalidFileException 直接
    #   穿透到顶层 ⇒ rc=1 + Traceback，用户看到的是第三方库堆栈而不是「你给错了
    #   文件」。缺参与错型都属**用法错误**，在此拦下并给中文说明，返回 2。
    for _p, _label in ((args.new_xlsx, "--new"), (args.answer_xlsx, "--answer")):
        if not os.path.isfile(_p):
            print("[参数错误] %s 指向的文件不存在：%s" % (_label, _p))
            return 2
        if os.path.splitext(_p)[1].lower() not in (".xlsx", ".xlsm", ".xltx", ".xltm"):
            print("[参数错误] %s 不是 Excel 工作簿（扩展名 %r）：%s"
                  "—— 本子命令只比对 gen 产出的 .xlsx 与参考答案 .xlsx"
                  % (_label, os.path.splitext(_p)[1], _p))
            return 2

    # 2026-10-05（P1）：同一语义在不同模板下的**表头写法**（长的排前面，避免
    #   「分纤箱编号」被「分纤箱」抢先命中）。增加新模板时只改这里。
    _CANON = (("楼栋", ("六级", "楼栋")),
              ("单元", ("七级", "单元")),
              ("楼层", ("八级", "楼层")),
              ("户号", ("九级", "户号")),
              ("分纤箱", ("分纤箱编号", "分纤箱")))

    def _colmap(ws):
        """按**表头名**定位五列 -> ({语义: 列号}, [缺失语义...])。

        为什么不能硬写列字母（原实现 column=8/10/12/14/16，即 H/J/L/N/P）：
        那只是**24 列定稿模板**的布局。未传 --template 时 gen 走内置 11 列降级表头
        （楼栋/单元/楼层/户号/分纤箱编号），五列位置完全不同 —— 实测对拍取到的是
        「单元/户号/越界空/越界空/越界空」，于是**逐行全 DIFF**，而现场逐行读两面
        可知楼栋·单元·户号·分纤箱四项**完全一致**。这是把「列错位」呈现成「结果全错」，
        属可机械识别的失准，必须修。缺列时报人，不静默取空（空值会让差异看起来像数据问题）。
        """
        hdr = {}
        for c in range(1, ws.max_column + 1):
            v = ws.cell(row=1, column=c).value
            if v is not None and str(v).strip():
                hdr.setdefault(str(v).strip(), c)
        mapping, missing = {}, []
        for canon, aliases in _CANON:
            col = next((hdr[a] for a in aliases if a in hdr), None)
            if col is None:
                missing.append(canon)
            else:
                mapping[canon] = col
        return mapping, missing

    def _load(path, tag):
        wb = load_workbook(path, data_only=True)
        ws = wb.active
        mapping, missing = _colmap(ws)
        if missing:
            raise ValueError(
                "%s：未在表头找到 %s 列（按名定位，不硬写列字母）。"
                "当前表头：%s。若本表不是标准地址表或用了未登记的新模板，请先登记其表头写法"
                "（cmd_verify_answer._CANON）。已中止，避免按错位列输出误导性差异。"
                % (tag, "/".join(missing),
                   "、".join(sorted(hdr_names(ws))[:16]) or "(空)"))
        print("[verify-answer] %s 列定位：%s（数据行起于第 2 行）"
              % (tag, "，".join("%s=%s" % (k, openpyxl_col(mapping[k]))
                                for k in ("楼栋", "单元", "楼层", "户号", "分纤箱"))))
        rows = []
        for r in range(2, ws.max_row + 1):
            h = ws.cell(row=r, column=mapping["楼栋"]).value
            if h in (None, ""):
                continue
            vals = []
            for canon in ("楼栋", "单元", "楼层", "户号", "分纤箱"):
                v = ws.cell(row=r, column=mapping[canon]).value
                vals.append(str(v) if v is not None else "")
            rows.append(tuple(vals))
        return rows

    def hdr_names(ws):
        out = []
        for c in range(1, ws.max_column + 1):
            v = ws.cell(row=1, column=c).value
            if v is not None and str(v).strip():
                out.append(str(v).strip())
        return out

    def openpyxl_col(idx):
        """1-based 列号 -> Excel 列字母（仅用于给人看的定位回显）。"""
        from openpyxl.utils import get_column_letter
        return get_column_letter(idx)

    try:
        rows_new = _load(args.new_xlsx, "新表")
        rows_ans = _load(args.answer_xlsx, "标准答案")
    except ValueError as e:
        print("[verify-answer] [失败] %s" % e)
        return 1
    print(f"新表数据行: {len(rows_new)} | 标准答案数据行: {len(rows_ans)}")

    diff = []
    for i in range(max(len(rows_new), len(rows_ans))):
        a = rows_new[i] if i < len(rows_new) else None
        b = rows_ans[i] if i < len(rows_ans) else None
        if a != b:
            diff.append((i + 2, a, b))
    # 2026-10-05：把「只有楼层列不同」的差异单独归类。原因：两张表可能一个
    #   用英文写型（1F）、一个用中文（一层）—— 那是**口径写法**差异，不是数据错。
    #   不静默抹平（仍计入 diff），但要在汇总里点明，否则会淹没在成百上千行里。
    _floor_only = [d for d in diff
                   if d[1] and d[2]
                   and d[1][0] == d[2][0] and d[1][1] == d[2][1]
                   and d[1][3] == d[2][3] and d[1][4] == d[2][4]
                   and d[1][2] != d[2][2]]
    if _floor_only:
        print("[verify-answer] 其中 %d 行**仅有楼层写型不同**（楼栋/单元/户号/分纤箱四项一致）"
              " —— 属口径写法差异，非户数/归属错；样例：%s"
              % (len(_floor_only),
                 "、".join("新表%s vs 答案%s" % (d[1][2], d[2][2]) for d in _floor_only[:3])))

    print(f"差异行数: {len(diff)}")
    for d in diff[:50]:
        print(f"  行{d[0]}: 新表={d[1]}  答案={d[2]}")
    if len(diff) > 50:
        print(f"  ...（还有 {len(diff) - 50} 行差异未显示）")

    # 每栋汇总
    from collections import Counter, defaultdict
    def _stat(rows):
        cnt = Counter(); fx = defaultdict(set)
        for h, j, l, n, p in rows:
            cnt[h] += 1
            fx[h].add(p)
        return cnt, fx
    c_new, fx_new = _stat(rows_new)
    c_ans, fx_ans = _stat(rows_ans)
    print("\n=== 每栋户数对比 ===")
    for b in sorted(c_new, key=lambda x: int(''.join(c for c in x if c.isdigit()) or '0')):
        mark = "OK" if c_new[b] == c_ans.get(b) else f"DIFF(答案{c_ans.get(b)})"
        fx_ok = "OK" if fx_new[b] == fx_ans.get(b) else f"DIFF(答案{fx_ans.get(b)})"
        print(f"  {b}: 新表{c_new[b]}户 [{mark}]  分纤箱{fx_new[b]} [{fx_ok}]")
    print(f"\n合计: 新表{sum(c_new.values())}户  答案{sum(c_ans.values())}户")
    return 0 if not diff else 1


def _newrun_keep(e) -> bool:
    """new-run 归档时**原地保留**的判定：输入图纸 / 解析缓存 / 验证基准。

    2026-10-04（P0-A3）：唯一实现，禁止在别处另抄一份保留名单。
    为什么要有这张表：new-run 语义是「清掉历史产物」，但桌面项目里输入 DXF、
    <DXF>.geom.json（技能明示可复用的无损投影缓存）、<DXF>.pkl（load_dxf 缓存）
    与标准答案 xlsx（verify-answer 的比对基准）都和产物同目录 —— 一并归档等于
    把下一轮的输入和判卷标准搬走。未知形态默认返回 False（照常归档），故本表
    只需覆盖「已知不可搬」的输入类，宁可少列也不误判成品为输入。
    """
    low = e.name.lower()
    if low.endswith((".dxf", ".dwg", ".pkl")):
        return True
    if low.endswith(".geom.json"):
        return True
    if low.endswith((".xlsx", ".xls")) and any(
            h in e.name for h in ("标准答案", "参考答案", "answer")):
        return True
    return False


def cmd_new_run(args) -> int:
    """从零跑清场：项目目录内历史产物归档进 run_<时间戳>/，重建空三本台账。

    2026-10-04（P0-A2）：三本台账是累计式，「从零跑」若不隔离，上一轮裁决会被
    误当「已确认基准」（违反从零语义）。归档不删除、可追溯；旧 run_* 归档目录
    不再二次归档（避免套娃）。

    2026-10-04（P0-A3 实测修复）：归档范围由「非 run_* 全搬」改为**排除输入与基准**。
    原实现的隐含前提是「project-dir 内只放产物」，该前提在本机桌面三项目上**不成立**
    （DXF / <DXF>.geom.json / 标准答案 xlsx 与产物同目录）→ 输入被搬空，紧随其后的
    pipeline 必然找不到 DXF（首轮即复现）。故：输入图纸、几何/解析缓存、**验证基准**
    一律原地保留并显式打印，`unknown` 形态默认不动（宁可少搬，不可误伤输入）。
    """
    import shutil
    from datetime import datetime

    pdir = Path(args.project_dir)
    if not pdir.is_dir():
        # 2026-10-04（轮次实测）：原实现在目录不存在时 rc=1 直接返回、不建目录，
        #   与 pipeline 自建 --outdir 的行为不一致 —— 文档「从零纪律」首步
        #   「new-run → pipeline」在全新项目上必然失败（空目录 = 首跑最常见形态）。
        #   空目录本无历史可归档，正确动作是建目录并交给 ledger_state init 落三本台账。
        try:
            pdir.mkdir(parents=True, exist_ok=True)
        except OSError as ex:
            print(f"[new-run] 无法创建项目目录 {pdir}: {ex}")
            return 1
        print(f"[new-run] 项目目录不存在，已创建: {pdir}")
    entries = [e for e in sorted(pdir.iterdir())
               if not (e.is_dir() and e.name.startswith("run_"))]
    if entries:
        # P0-A3：区分「历史产物」与「输入/基准」。保留类原地不动并登记（不静默）。
        to_archive, kept = [], []
        for e in entries:
            (kept if _newrun_keep(e) else to_archive).append(e)
        for e in kept:
            print(f"[new-run] 保留原位（输入/基准/缓存，非产物）：{e.name}")
        if to_archive:
            arch = pdir / ("run_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
            arch.mkdir(exist_ok=True)
            moved, failed = [], []
            for e in to_archive:
                try:
                    shutil.move(str(e), str(arch / e.name))
                    moved.append(e.name)
                except OSError as ex:
                    failed.append((e.name, str(ex)))
            print(f"[new-run] 已归档 {len(moved)} 项 → {arch.name}/（不删除，可追溯）")
            for n in moved:
                print(f"    · {n}")
            if failed:
                print(f"[new-run] 归档失败 {len(failed)} 项（保留原位，不阻塞）：")
                for n, ex in failed:
                    print(f"    ! {n}: {ex}")
        else:
            print("[new-run] 项目目录内仅剩输入与基准，无历史产物可归档")
    else:
        print("[new-run] 项目目录已干净，无需归档")
    rc = run_script("ledger_state.py",
                    ["init", "--project-dir", str(pdir)]
                    + (["--project", args.project] if args.project else []))
    print("[new-run] 从零定义：DXF 同目录的 <DXF>.geom.json 为无损投影缓存可复用；"
          "本目录内产物一律重生成")
    return rc


def cmd_pipeline(args):
    """串跑多阶段，返回退出码。

    每阶段耗时记入 <outdir>/pipeline_timing.json —— 优化/排障都以该台账为准，
    不凭印象。
    """
    self_py = str(Path(__file__).resolve())
    dxf = args.dxf
    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)
    logdir = os.path.join(outdir, "logs")
    # 2026-09-26（一百零二，问题 5）：阶段级 print 的 tee 落盘。
    #   背景：--quiet 是批量跑的标准姿势，但 _run 只把**子进程**输出落盘
    #   logs/<阶段>.log，ftth.py 自身的阶段级 print（[pipeline]/[gate] 跳过原因与
    #   既定处置、[config-info] 串号风险提示、[ERROR] 拦截等）无任何落盘 —— rc=3
    #   跳过的阶段连 log 文件都不存在，事后只剩裸 rc=3 可查。
    #   实现：stdout tee（控制台 + logs/pipeline.log 双写），零调用点改动 ——
    #   本函数内全部 print（含 _dump 收尾）自动落盘；quiet 与非 quiet 同行为
    #   （控制台照旧）。恢复点选 _dump：本函数全部出口均经 _dump 收敛（已核对
    #   L638~L1086 全部 `return _dump(...)`，无旁路 return），单点恢复即可。
    os.makedirs(logdir, exist_ok=True)
    _plog_path = os.path.join(logdir, "pipeline.log")
    _plog_fh = open(_plog_path, "w", encoding="utf-8", newline="\n")
    _real_stdout = sys.stdout

    class _Tee(object):
        def __init__(self, *fps):
            self._fps = fps

        def write(self, s):
            for _fp in self._fps:
                try:
                    _fp.write(s)
                except Exception:                              # noqa: BLE001
                    pass                                       # 落盘失败不阻塞控制台

        def flush(self):
            for _fp in self._fps:
                try:
                    _fp.flush()
                except Exception:                              # noqa: BLE001
                    pass

        def isatty(self):
            return False

        def __getattr__(self, name):
            return getattr(_real_stdout, name)

    sys.stdout = _Tee(_real_stdout, _plog_fh)
    geom_json = dxf + ".geom.json"
    cfg = os.path.join(outdir, "config.json")
    prof = args.profile or os.path.join(outdir, "profile.json")
    parsed = os.path.join(outdir, "parsed.json")
    cov = os.path.join(outdir, "coverage.json")
    insp = os.path.join(outdir, "inspect.json")
    stop_idx = _PIPE_STAGES.index(args.stop_at or "inspect")

    ledger = []
    t_all = time.time()

    _BRIEF_TAIL = 30  # --brief 每阶段控制台最多保留的子进程输出尾行数
    _BRIEF_KEYS = ("[WARNING]", "[ERROR]", "FAIL", "WARN", "[gate]")

    def _brief_lines(text, tail=_BRIEF_TAIL):
        """退役条件：当 pipeline 改为结构化事件流（子进程输出机读化）后可删除，改由事件订阅做摘要。

        --brief 摘要过滤：只保留「最后 tail 行 + 含关键字的行」（关键字见
        _BRIEF_KEYS，[pipeline] 阶段状态行由调用方始终打印，不在此列）。
        其余输出仍在 logs/<stage>.log，不丢信息，只是不刷屏。
        """
        lines = (text or "").splitlines()
        n = len(lines)
        return [l for i, l in enumerate(lines)
                if i >= n - tail or any(k in l for k in _BRIEF_KEYS)]

    def _sink(stage):
        # 2026-10-01（优化①）：--brief 与 --quiet 同落盘；区别只在控制台是否
        #   打摘要（见 _run/_run_capture 的 brief 分支）。--quiet 行为不变。
        return os.path.join(logdir, "%s.log" % stage) \
            if (args.quiet or getattr(args, "brief", False)) else None

    def _run(stage, argv, script=None):
        """起一个子进程；--quiet 时输出落 logs/<stage>.log，否则透传。"""
        t0 = time.time()
        if script:
            cmd = [sys.executable, str(Path(__file__).parent / script)] + argv
        else:
            cmd = [sys.executable, self_py] + argv
        sink = _sink(stage)
        brief = bool(getattr(args, "brief", False)) and not args.quiet
        if sink:
            os.makedirs(logdir, exist_ok=True)
            with open(sink, "w", encoding="utf-8", newline="\n") as f:
                rc = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT)
        else:
            rc = subprocess.call(cmd)
        el = time.time() - t0
        ledger.append({"阶段": stage, "rc": rc, "秒": round(el, 2)})
        print("[pipeline] %-9s rc=%-2s %7.2fs" % (stage, rc, el), flush=True)
        if brief:
            # --brief：控制台只显示摘要（全文见 log）。阶段状态行已在上行打印，
            #   不受 brief 影响；关键字行（_BRIEF_KEYS）已由 _brief_lines 透传。
            try:
                with open(sink, "r", encoding="utf-8", errors="replace") as _bf:
                    _btxt = _bf.read()
            except OSError:
                _btxt = ""
            _bl = _brief_lines(_btxt)
            if _bl:
                print("[pipeline] %s 摘要（全文见 %s）：" % (stage, sink), flush=True)
                for _l in _bl:
                    print(_l, flush=True)
        return rc

    def _run_capture(stage, argv, script=None):
        """起一个子进程并捕获合并输出；返回 (rc, 输出文本)。

        2026-09-26（示意画法回落）：count_box 阶段需检查子进程 stdout 是否含
        [DIAG-SCHEMATIC-ICONS] token，_run 只回 rc 不回输出，故单列此变体。
        输出去向与 _run 同口径：--quiet 落 logs/<stage>.log，否则透传控制台
        （经外层 tee 同步进 pipeline.log）。--brief 同 --quiet 落盘，但额外在
        控制台打摘要（_brief_lines 过滤）。子进程 stdout 已由
        ensure_console_utf8 重定向为 UTF-8，故按 UTF-8 解码（不用 locale，
        中文 Windows 默认 GBK 会解错）。
        """
        t0 = time.time()
        if script:
            cmd = [sys.executable, str(Path(__file__).parent / script)] + argv
        else:
            cmd = [sys.executable, self_py] + argv
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
        out = (proc.stdout or b"").decode("utf-8", errors="replace")
        sink = _sink(stage)
        brief = bool(getattr(args, "brief", False)) and not args.quiet
        if sink:
            os.makedirs(logdir, exist_ok=True)
            with open(sink, "w", encoding="utf-8", newline="\n") as f:
                f.write(out)
            if brief:
                # --brief：控制台只显示摘要（全文见 log，返回仍是全量 out）。
                for _l in _brief_lines(out):
                    print(_l, flush=True)
        else:
            sys.stdout.write(out)
            sys.stdout.flush()
        el = time.time() - t0
        ledger.append({"阶段": stage, "rc": proc.returncode, "秒": round(el, 2)})
        print("[pipeline] %-9s rc=%-2s %7.2fs" % (stage, proc.returncode, el),
              flush=True)
        return proc.returncode, out

    def _std_json_gate(rc):
        """产物 JSON 标准性闸门（2026-09-18）：非标准字面量 ⇒ rc 抬到 2，不得静默出关。"""
        bad = _scan_nonstd_json(outdir)
        if bad:
            for name, why in bad:
                print("[pipeline] ! 产物非标准 JSON：%s（%s）—— 严格解析器会拒绝整份文件，"
                      "须由产出脚本在 dump 前清洗为 null" % (name, why), flush=True)
            ledger.append({"阶段": "json标准性", "rc": 2, "秒": 0.0})
            return 2 if rc in (0, 3) else rc
        return rc

    def _dump(rc, stopped=None):
        """收尾台账。stopped=阶段名 表示流水线在该阶段**提前中止**（末阶段失败也算）。

        2026-09-18（实跑修复，P0）：此前 rc=3 一律打印「本图不适用（非错误），按画像
          降级路径继续」—— 但 `_dump(rc!=0)` 的调用点**全部**是提前 return，即链路
          已经终止。实测某图 parse 因多地块同名楼守门 rc=3，日志却写着"继续"，
          人据此以为已降级跑完，而 parsed/coverage/inspect 根本没产出。
          退出码语义必须与「是否真的继续」一致：说继续就得真继续。
        """
        total = time.time() - t_all
        path = os.path.join(outdir, "pipeline_timing.json")
        write_json(path, {"dxf": dxf, "outdir": outdir, "total_sec": round(total, 2),
                          "stages": ledger})
        print("")
        print("-" * 68)
        print("[pipeline] 合计 %.2fs（%d 阶段）  产物目录: %s" % (total, len(ledger), outdir))
        for r in ledger:
            print("[pipeline]   %-9s rc=%-2s %7.2fs" % (r["阶段"], r["rc"], r["秒"]))
        print("[pipeline] 耗时台账: %s" % path)
        if rc == 0:
            print("[pipeline] 下一步：人工裁决待确认项后再出表（gen 不在流水线内，见本函数文档）")
        elif stopped:
            print("[pipeline] ⛔ 已在「%s」阶段中止（rc=%d）—— **后续阶段未执行**，"
                  "本次没有产出更下游的产物。" % (stopped, rc))
            print("[pipeline]    处置：按该阶段打印的提示处理后重跑；"
                  "**不要**把本次产物当作完整链路结果。")
        else:
            print("[pipeline] 有阶段 rc=%d，但流水线已跑完（该阶段为「本图不适用」，"
                  "非错误），下游按画像降级路径执行" % rc)
        print("-" * 68)
        # 2026-09-26（一百零二，问题 5）：tee 收尾 —— 本行同样进 pipeline.log；
        #   此后恢复 stdout 并关闭文件（本函数全部出口经此，单点恢复）。
        print("[pipeline] 阶段级日志已落盘: %s（rc=3 跳过原因/既定处置见其中）"
              % _plog_path)
        try:
            sys.stdout = _real_stdout
        finally:
            try:
                _plog_fh.close()
            except Exception:                                  # noqa: BLE001
                pass
        return rc

    # ---- ① geom ----
    if args.reuse_geom and os.path.isfile(geom_json) \
            and os.path.getmtime(geom_json) >= os.path.getmtime(dxf):
        ledger.append({"阶段": "geom", "rc": 0, "秒": 0.0})
        print("[pipeline] %-9s rc=0      0.00s  (复用已有几何缓存)" % "geom", flush=True)
    else:
        rc = _run("geom", ["--dxf", dxf], script="dump_geom.py")
        if rc:
            return _dump(_std_json_gate(rc), "geom")
    if stop_idx < 1:
        return _dump(0)

    # ---- ② probe ----
    rc = _run("probe", ["probe", "--dxf", dxf, "--out", cfg])
    if rc:
        return _dump(_std_json_gate(rc), "probe")
    if stop_idx < 2:
        return _dump(0)

    # ---- ③ plan（--project-dir 不传会让 intake_table 留 unknown，故显式透传）----
    plan_argv = ["plan", "--dxf", dxf, "--probe", cfg, "--config", cfg, "--out", prof]
    if args.project_dir:
        plan_argv += ["--project-dir", args.project_dir]
    rc = _run("plan", plan_argv)
    if rc:
        return _dump(_std_json_gate(rc), "plan")
    # 2026-09-27（P0-1，实跑修复）：plan 之后立即对拍「画像选法 × 本入口能力表」。
    #   此前画像可申报一个本入口没有映射的脚本而**无人报错** —— 该路被静默跳过，
    #   直到 inspect C6 才 FAIL，报错文案还指向画像（误导排查方向）。此处 fail-closed。
    _cap_probs = _pipe_capability_problems(prof)
    if _cap_probs:
        print("[pipeline] ! 画像选法与本入口能力表不一致（禁止静默跳过）：", flush=True)
        for _p in _cap_probs:
            print("[pipeline]     - %s" % _p, flush=True)
        ledger.append({"阶段": "plan.capability", "rc": 2, "秒": 0.0})
        return _dump(2, "plan")
    if stop_idx < 3:
        return _dump(0)

    # 注：多地块扇出**不在这里**（plan 之后），而在 unit_gaps 之后 —— 见 1568 行旁说明。

    # ---- ③b titleblock（图签第二来源；仅画像申报 present / variant 时跑）----
    # 2026-09-18（实跑修复，P1）：画像把 titleblock_annotation 判为 present 并明确写出
    #   「后果与处置：图签可直读栋级入户规模 → 与采集表构成『三来源协议』的第二来源」。
    # 2026-09-25（评审 P0 stale 守卫）：本阶段**产出追踪标志**，供 inspect/unit_gaps
    #   判断「文件来自本轮还是旧轮残留」——仅 rc==0 时置 True。
    tb = os.path.join(outdir, "titleblock.json")
    _tb_produced = False
    # 2026-09-25（云峰实跑 + opencode 审核返工，问题 3）：骨架侧（titleblock.json）
    #   未产出时，unit_gaps 预检此前只报「未提供该输入路径」——成因其实在 pipeline
    #   手里（申报制跳过 / 无图层候选 / 阶段失败），逐分支记录，仅供文案透传，
    #   不参与判定。
    _tb_note = ""
    _tb_state = _pipe_profile_status(prof, "titleblock_annotation")
    if _tb_state not in ("present", "variant"):
        _tb_note = ("titleblock 阶段未跑：画像申报 titleblock_annotation=%s"
                    "（非 present/variant，申报制跳过）" % (_tb_state or "未知"))
        ledger.append({"阶段": "titleblock", "rc": 3, "秒": 0.0})
        print("[pipeline] %-9s rc=3      0.00s  (画像申报 titleblock_annotation=%s，跳过)"
              % ("titleblock", _tb_state or "未知"), flush=True)
    else:
        # 图层取值三级：① probe 专为该脚本产出的 titleblock_layer_candidates（最准，
        #   config.json 明写「用途：read_titleblock_households.py --floor-layer 候选」）→
        #   ② 通用文字图层 suggested_params.text_layer → ③ 取不到就**不猜**，跳过并说明。
        #   （2026-09-18 实跑踩坑：只读顶层 text_layer 取不到 —— 实际它嵌在 suggested_params
        #   里，于是本阶段静默跳过、C10 白 SKIP，属"修了但没生效"。）
        _tbl = ""
        try:
            with open(cfg, "r", encoding="utf-8") as _cf2:
                _c = json.load(_cf2) or {}
            _cand = ((_c.get("titleblock_layer_candidates") or {}).get("候选图层") or [])
            if _cand:
                _tbl = str(_cand[0]).strip()
            if not _tbl:
                _sp = _c.get("suggested_params") or {}
                _tl = _sp.get("text_layer")
                if isinstance(_tl, list) and _tl:
                    _tbl = str(_tl[0]).strip()
                elif isinstance(_tl, str):
                    _tbl = _tl.split(",")[0].strip()
        except (IOError, json.JSONDecodeError, OSError):             # noqa: BLE001
            _tbl = ""
        if not _tbl:
            _tb_note = ("titleblock 阶段未跑：配置里既无 titleblock_layer_candidates 也无 "
                        "suggested_params.text_layer，不猜图层")
            ledger.append({"阶段": "titleblock", "rc": 3, "秒": 0.0})
            print("[pipeline] titleblock 跳过：配置里既无 titleblock_layer_candidates 也无 "
                  "suggested_params.text_layer，不猜图层；C10 将判 SKIP 并注明本次未做交叉校验",
                  flush=True)
        else:
            # 2026-09-25（评审 P1-11 → 回滚）：曾尝试从 probe 的 suggested_params.title_pattern
            #   透传 --bldg-re，但 probe 的 title_pattern 是为**系统图标题**设计的正则
            #   （如 `(\d+#楼).*示意图`），与图签楼名（`1#楼 / 1号楼 / 1楼`）语义不同——
            #   实测凤鸣：传后 titleblock 读取错乱（楼1 单元=2/层=18、楼2~8 全消失）、
            #   C10 从 PASS 变 FAIL。**不透传**，保持脚本内置默认正则。
            #   容差六件套（--dx-tol 等）同样无上游来源可透传（probe 不产出容差），
            #   靠脚本自适应；自适应失准时用户须跑 probe_titleblock_tolerances.py 手工量测。
            _rc_tb = _run("titleblock",
                          ["--dxf", dxf, "--floor-layer", _tbl, "--out", tb],
                          script="read_titleblock_households.py")
            if _rc_tb == 0:
                _tb_produced = True  # 本轮实际产出，inspect/unit_gaps 可消费
            elif _rc_tb == 3:
                # 2026-09-18（实跑修复）：rc=3 = 本图未提供图签形态（申报制语义），
                #   不是脚本故障。此前一律按 `!` 告警打印，把「图上没有」写成
                #   「第二来源未取得」，且掩盖了它与真失败的区别。
                _tb_note = "titleblock 阶段 rc=3：本图未提供图签形态的成对标注（申报制跳过）"
                print("[pipeline] titleblock rc=3 = 本图未提供图签形态的成对标注"
                      "（申报制），第二来源本次不参与；C10 将判 SKIP 并注明「本次未做」",
                      flush=True)
            elif _rc_tb:
                _tb_note = "titleblock 阶段失败 rc=%d —— 须先修复该阶段（第二来源本次未取得）" % _rc_tb
                print("[pipeline] ! titleblock 阶段 rc=%d —— 第二来源本次**未取得**，"
                      "inspect 的 C10 将判 SKIP（本次未做图签交叉校验）" % _rc_tb, flush=True)
    if stop_idx < 4:
        return _dump(0)

    # ---- ④ fxmap（总图对照表；仅画像申报存在总图时跑，失败不中止）----
    # 2026-09-18 整改①：此前这一环完全缺失 —— 画像 handoff 写着「下游：extract_fx_map.py」，
    #   但流水线不接续。实测某图总图对照表位于独立图区（x 与楼栋系统图不重叠），
    #   parse 按楼栋 x 范围归属 → 每栋 0 箱，而没有任何环节提示必须先提对照表。
    # 2026-09-18 整改②（第 2 轮）：顺序再修正 —— 对照表必须在 **parse 之前**产出，
    #   依据 SKILL.md 硬约束②：楼栋/单元归属必须以对照表为准，parse 自身同样受此约束。
    fxmap = os.path.join(outdir, "fxmap.json")
    _fxmap_produced = False  # 2026-09-25（opencode 审核）：fxmap 实际产出标志（区别于 gate 决定跑）
    # 2026-09-18（第 3 轮）：判据从「画像申报有集中总图」改为「**有 FX 编号可提**」。
    #   原 gate 把 7/8 个分带整段跳过（这些图的箱编号嵌在各楼系统图箱表内，
    #   fx_overview_map=absent，但 handoff① 明写编号可读/编号数），后果是 parse 侧
    #   箱归属全空、rc 仍 0 —— 静默丢数。详见 _pipe_fxmap_gate 的说明。
    _fx_run, _fx_note = _pipe_fxmap_gate(prof)
    if _fx_run:
        print("[pipeline] fxmap 依据：%s" % _fx_note, flush=True)
        _rc_fx = _run("fxmap", [dxf, fxmap, "--config", cfg], script="extract_fx_map.py")
        if _rc_fx == 0:
            _fxmap_produced = True
        if _rc_fx and not os.path.isfile(fxmap):
            print("[pipeline] ! fxmap 阶段失败(rc=%d) —— parse/coverage 无总图对照表，"
                  "楼栋归属回退『标题 x 中分』（仅供线索）" % _rc_fx, flush=True)
    else:
        ledger.append({"阶段": "fxmap", "rc": 3, "秒": 0.0})
        print("[pipeline] %-9s rc=3      0.00s  (%s，跳过)" % ("fxmap", _fx_note),
              flush=True)
    # 用户显式 --bldg-map 优先（人工确认过总图对照表，属「图上标注直读」来源）；
    # 否则仅当 fxmap 阶段**本轮实际产出**（_fxmap_produced）时才用。
    # 2026-09-25（opencode 审核返工）：_fx_run 只是「gate 决定跑」，不是「跑成功」——
    #   若 extract_fx_map 本轮 rc!=0 但旧 fxmap.json 残留，_bmap 照样指向旧文件
    #   并喂给 parse --bldg-map/--fx-map（stale 污染）。改吃产出标志。
    # 2026-09-18（第 4 轮，用户裁决）：absent 图不再产出 fxmap —— gate 未跑则文件
    #   不存在，_bmap 自然为 None；不自动把「旧残留/降级产物」当作对照表回填。
    _bmap = args.bldg_map or (fxmap if (_fxmap_produced and os.path.isfile(fxmap)) else None)
    if not args.bldg_map and not _fxmap_produced and os.path.isfile(fxmap):
        print("[pipeline] ! 检测到残留 fxmap.json 但本轮 fxmap 未成功 —— "
              "parse/coverage 已忽略（不传 --bldg-map），避免 stale 文件污染；"
              "如需清除请删除 %s" % fxmap, flush=True)
    if stop_idx < 5:
        return _dump(0)

    # ---- ④b fx_locations（箱位直读标注；仅探查申报 present 时跑）----
    # 2026-09-18（实跑修复，P0）：probe 把 fx_location_annotation 判为 "present(N条)"、
    #   plan 原样透传并只在日志里 log 一句「建议 extract_fx_locations.py 提取后给
    #   coverage-vshape 传 --fx-locations 做交叉校验」——**流水线里既没有这个阶段、
    #   也不给 coverage-vshape 传参**，与 ③b titleblock 属同一形态的
    #   「规则写在文档里、没有代码执行」。
    #   后果（实测某图）：图上 22 条「N号楼M单元K层」直读标注是**安装层最可靠的独立
    #   第二来源**，全部未被使用；coverage-vshape 的交叉校验恒为「比对 0 项」，
    #   箱位锚只剩编号文字那一路，18 项待裁决里大半本可由本来源消解。
    #   本阶段只**提取并落盘**（<outdir>/fx_locations.json），消费点见 ⑥ coverage；
    #   非 0 退出**不中止主链路**（它是校验来源，不是主数据来源），但必须显式打印。
    fxl = os.path.join(outdir, "fx_locations.json")
    _fxl_produced = False  # 2026-09-25（评审 P0 stale 守卫）：本轮产出追踪标志
    _fxl_state = _pipe_fxloc_state(prof, cfg)
    if not _fxl_state.startswith("present"):
        ledger.append({"阶段": "fx_locations", "rc": 3, "秒": 0.0})
        print("[pipeline] %-9s rc=3      0.00s  (探查申报 fx_location_annotation=%s，跳过)"
              % ("fx_locations", _fxl_state or "未知"), flush=True)
    else:
        # 2026-09-25（评审 P1-11）：补 --text-layer 透传（probe 的 suggested_params.text_layer），
        #   避免裸跑全图扫描被杂层噪声污染；--pattern 保持内置正则（N号楼M单元K层 等三形态），
        #   图上写法不同时用户须手工重跑本阶段带 --pattern。
        _fxl_argv = ["--dxf", dxf, "--out", fxl]
        try:
            with open(cfg, "r", encoding="utf-8") as _cf5:
                _sp5 = (json.load(_cf5).get("suggested_params") or {})
            _fxl_tl = _sp5.get("text_layer")
            if isinstance(_fxl_tl, list) and _fxl_tl:
                _fxl_tl = ",".join(str(x).strip() for x in _fxl_tl if str(x).strip())
            elif isinstance(_fxl_tl, str):
                _fxl_tl = _fxl_tl.strip()
            if _fxl_tl:
                _fxl_argv += ["--text-layer", _fxl_tl]
        except (IOError, json.JSONDecodeError, OSError):             # noqa: BLE001
            pass
        _rc_fxl = _run("fx_locations", _fxl_argv, script="extract_fx_locations.py")
        if _rc_fxl == 0:
            _fxl_produced = True
        if _rc_fxl and not os.path.isfile(fxl):
            print("[pipeline] ! fx_locations 阶段失败(rc=%d) —— 箱位直读标注本次**未取得**，"
                  "coverage-vshape 将无安装层第二来源，结论须照此标注"
                  % _rc_fxl, flush=True)
    if stop_idx < 6:
        return _dump(0)

    # ---- ④c unit_gaps（探查期「单元 × 箱清单」交叉清点；提前暴露「某单元没分纤箱」）----
    # 2026-09-18（用户裁定）：此前「某单元一个箱都没有」只在 **Step 2 自检**（覆盖完整性
    #   门禁）阶段才暴露 —— 那时 parse/coverage 已跑完，返工面大。而图面证据其实在 parse
    #   **之前**就齐了：骨架 = titleblock.json（栋级层户 + 单元标注），箱清单 = fxmap.json
    #   （对照表）与/或 fx_locations.json（箱位直读标注）。故本检查提前到此处。
    #   定位：**预检告警，不是待裁决项的权威载体** —— 后者仍以 coverage/inspect 为准。
    #   铁律：**两侧来源任缺即判 unresolved、不产生 pending** —— 「没核过」不得输出成
    #   「全部单元无箱」（假失败）或「通过」（假绿灯）；脚本原理见 check_unit_box_gaps.py。
    #   非 0 退出不中止主链路（它是预检，不是主数据来源），但必须显式打印。
    ug = os.path.join(outdir, "unit_box_gaps.json")
    ug_argv = ["--out", ug]
    # 2026-09-25（评审 P0 stale 守卫 + opencode 审核返工）：仅喂本轮实际产出的文件，
    #   旧残留不吃；--fx-map 用产出标志（不用 _fx_run：gate 决定跑≠跑成功）
    for _uflag, _upath, _uprod in (
            ("--titleblock", tb, _tb_produced),
            ("--fx-locations", fxl, _fxl_produced),
            ("--fx-map", fxmap, _fxmap_produced)):
        if _uprod and os.path.isfile(_upath):
            ug_argv += [_uflag, _upath]
        elif not _uprod and os.path.isfile(_upath):
            print("[pipeline] ! 检测到残留 %s 但本轮对应阶段未产出 —— unit_gaps 已忽略，"
                  "避免 stale 文件污染" % os.path.basename(_upath), flush=True)
    # 2026-09-25（云峰实跑 + opencode 审核返工，问题 3）：骨架侧未就绪的**成因**
    #   在 pipeline 手里，透传给子脚本替换通用文案「未提供该输入路径」——用户不再
    #   误以为忘了传参。仅文案，unresolved 判定与 rc 语义均不变。
    if not _tb_produced and _tb_note:
        ug_argv += ["--titleblock-note", _tb_note]
    _rc_ug = _run("unit_gaps", ug_argv, script="check_unit_box_gaps.py")
    if _rc_ug and not os.path.isfile(ug):
        print("[pipeline] ! unit_gaps 阶段失败(rc=%d) —— 探查期「单元×箱」预检本次**未取得**，"
              "「某单元无分纤箱」只能等覆盖阶段门禁暴露" % _rc_ug, flush=True)
    else:
        _v = _pipe_gap_verdict(ug)
        if _v:
            print("[pipeline] 预检「单元×箱」%s：%s" % _v, flush=True)
            if _v[0] == "unresolved":
                print("[pipeline]   （unresolved = 本次**未判定**，不是通过；"
                      "覆盖阶段门禁仍会兜底）", flush=True)
    if stop_idx < 7:
        return _dump(0)

    # ---- ④c 多地块自动分带（2026-10-05）：把 split-band 接进串跑 ----
    #   位置选在 **unit_gaps 之后、parse 之前**：串号风险只来自 parse 及下游（同名楼栋
    #   按楼名去重），而 geom/probe/plan/titleblock/fxmap/fx_locations/unit_gaps 全是
    #   parse 之前的整图级阶段，**无串号风险、且整图级有独立价值**（图签第二来源、
    #   单元×箱预检）。若把扇出放在 plan 之后，这些整图产物会一起消失 —— 实测冒烟
    #   golden 立刻报 lxz14 的 titleblock/fx_locations/unit_box_gaps 三项 MISSING。
    if stop_idx >= _PIPE_STAGES.index("parse"):
        _fanned = _pipe_fanout_bands(args, dxf, outdir, cfg, args.project_dir)
        if _fanned is not None:
            ledger.append({"阶段": "split_band.fanout", "rc": _fanned, "秒": 0.0})
            print("[pipeline] 本图为多地块，已按带分别跑完；**各带产物分别在 "
                  "<outdir>/bands/<带名>/**。整图级只保留 parse 之前的阶段产物"
                  "（图签/箱清单/单元预检），**不产出整图级 parse/inspect** —— "
                  "整图解析会让同名楼栋串号，是刻意不做的", flush=True)
            return _dump(_fanned, "split_band.fanout")

    # ---- ⑤ parse ----
    parse_argv = ["parse", "--dxf", dxf, "--config", cfg,
                  "--profile", prof, "--out", parsed]
    # 2026-09-18（第 3 轮）：区间楼号语义（`1-3号楼` = 1、2、3 号还是 1、3 号）
    #   只能由人裁决 —— parse/count 早有 --expand-bldg-ranges 开关，但**流水线不接续**，
    #   用户确认语义后无法在 pipeline 里启用（实测某图因此丢一栋楼的全部箱）。
    #   此处只做透传，不在代码里替用户决定。
    if getattr(args, "expand_bldg_ranges", False):
        parse_argv += ["--expand-bldg-ranges"]
        print("[pipeline] 已按 --expand-bldg-ranges 展开区间楼号（`N-M号楼` → N..M 全部）",
              flush=True)
    # 2026-09-30（一百二十八，云峰P0-1机制①）：分离形态单元轴合成开关透传。
    #   probe 已在 suggested_params.unit_split_keyword 给出建议（如`单元`），parse 侧
    #   已支持 --unit-split-keyword，但 pipeline 从不转发 —— 云峰 2#/3#/6# 楼八单元
    #   全丢即因此（marker 容器缺失，对照表单元号无处可挂）。此处按三级取值：
    #   ① pipeline 显式 --unit-split-keyword 优先；② cfg 探查建议；③ 都没有则不传。
    _usk = getattr(args, "unit_split_keyword", None)
    if not _usk:
        try:
            with open(cfg, "r", encoding="utf-8") as _cf_usk:
                _sp_usk = (json.load(_cf_usk).get("suggested_params") or {})
            _usk = (_sp_usk.get("unit_split_keyword") or "").strip() if isinstance(
                _sp_usk.get("unit_split_keyword"), str) else _sp_usk.get("unit_split_keyword")
        except (IOError, json.JSONDecodeError, OSError):             # noqa: BLE001
            _usk = None
    if _usk and str(_usk).strip() and str(_usk).strip().lower() not in ("null", "none", "未提供"):
        parse_argv += ["--unit-split-keyword", str(_usk).strip()]
        print("[pipeline] 已下传 --unit-split-keyword %s（分离形态单元轴合成；来源：%s）"
              % (str(_usk).strip(),
                 "pipeline 参数" if getattr(args, "unit_split_keyword", None) else "探查建议"),
              flush=True)
    # 2026-09-30（一百三十二，V3 Phase A）：parse 去决策开关透传（默认关闭）。
    if getattr(args, "parse_no_floor", False):
        parse_argv += ["--floor-mode", "nofloor"]
        print("[pipeline] 已按 --parse-no-floor 下传 parse --floor-mode nofloor"
              "（只定归属不定安装楼层；C2/C3/gen 双模式消费）", flush=True)
    if _bmap:
        # 硬约束② 的落地：有总图对照表时，箱的楼栋/单元归属以它为准（不再按标题 x 中分）。
        # --fx-map 仍只做「缺失安装楼层回填」，不覆盖 parse 实测值。
        parse_argv += ["--bldg-map", _bmap, "--fx-map", _bmap]
    rc = _run("parse", parse_argv)
    # 2026-09-25（评审 P0-2）：parse 的 rc=3 语义对齐 L1-C2 与兄弟阶段 ——
    #   rc=3 = 本图不适用（申报制语义，如多地块守门在某些图上报 rc=3），继续走下游；
    #   其余非 0 照旧中止。此前 `if rc:` 一刀切，把 rc=3 也当中止 ——
    #   与 coverage:866 / count_box:898 的 `if rc == 3: 继续` 不对称。
    if rc == 3:
        print("[pipeline] parse rc=3 = 本图不适用（申报制），按降级路径继续；"
              "下游 coverage/inspect 将按缺失如实呈现", flush=True)
    elif rc:
        return _dump(_std_json_gate(rc), "parse")
    if stop_idx < 8:
        return _dump(0)

    # ---- ⑥ coverage（方法由画像决定，不在此处二次推断）----
    _cov_produced = False  # 2026-09-25（评审 P0 stale 守卫）：本轮产出追踪标志
    cov_cmd, cov_note, cov_blocked = _pipe_coverage_choice(prof)
    print("[pipeline] 覆盖判定选法: %s" % cov_note, flush=True)
    if cov_blocked:
        # 2026-09-27（P0-1）：申报了脚本但本入口接不上（或 unimplemented）——
        #   不是「本图不适用」，不得 rc=3 放过（那会让覆盖零产出直到 C6 才暴露）。
        ledger.append({"阶段": "coverage", "rc": 2, "秒": 0.0})
        return _dump(2, "coverage")
    if cov_cmd is None:
        ledger.append({"阶段": "coverage", "rc": 3, "秒": 0.0})
        print("[pipeline] %-9s rc=3      0.00s  (本图不适用，非错误)" % "coverage", flush=True)
    else:
        cov_argv = [cov_cmd, "--dxf", dxf, "--config", cfg,
                    "--profile", prof, "--out", cov]
        # 2026-09-18（实跑修复，P0）：把 ④b 产出的箱位直读标注喂给 V 型法做安装层交叉校验。
        #   此前该参数只出现在 `ftth.py coverage-vshape` 的手工命令里，走流水线就永远不接
        #   —— 「信号申报了、产物提了、却没人核」。
        #   只有 coverage-vshape 消费它（analyze_coverage.py 无此参数，传了 rc=2），
        #   故按子命令分派，与下方图层/对照表参数同一处理。
        # 2026-09-25（评审 P0 stale 守卫）：fx_locations 也用产出标志，不用裸 isfile
        if cov_cmd == "coverage-vshape" and _fxl_produced and os.path.isfile(fxl):
            cov_argv += ["--fx-locations", fxl]
            print("[pipeline] 箱位直读标注已接入 V 型法交叉校验: %s" % fxl, flush=True)
        elif cov_cmd == "coverage-vshape":
            print("[pipeline] 提示：本次无箱位直读标注(<outdir>/fx_locations.json)，"
                  "V 型法安装层缺独立第二来源，结论须照此标注", flush=True)
        # 2026-09-26（第5轮迭代）：V 型法箱号锚缺席配对 —— parsed.json 存在时透传
        # --parse，不存在不传、行为不变。仅 coverage-vshape 消费该参数
        # （analyze_coverage.py 无此参数，传了即 unrecognized arguments rc=2），
        # 故按子命令分派，与 --fx-locations 同处理。
        if cov_cmd == "coverage-vshape" and os.path.isfile(parsed):
            cov_argv += ["--parse", parsed]
            print("[pipeline] 解析侧安装层已接入 V 型法锚缺席配对: %s" % parsed, flush=True)
        _lay, _lay_src = _pipe_effective_layers(prof)
        # 2026-09-18（实跑修复，P1）：**图层参数按子命令分派**。analyze_coverage_vshape.py
        #   （V 型法）只吃文字标注与米数列，**完全不消费 --wire-layer / --fx-symbol-layer**
        #   —— 传它一律 `unrecognized arguments` 直接 rc=2（实测：给 coverage-vshape 加
        #   `--wire-layer BZ` 立即报参数错误并列出全部可用参数）。原代码无条件追加，只因
        #   本图画像两个图层均为 null 才侥幸未触发；换一张 dedicated_wire_layer=present
        #   的图即挂。与下方 --bldg-map 属同一类缺陷 —— 那处已分派、这两处此前漏修。
        _want_wl = args.wire_layer or _lay.get("wire_layer")
        _want_fx = args.fx_symbol_layer or _lay.get("fx_symbol_layer")
        if cov_cmd == "coverage":
            if _want_wl:
                cov_argv += ["--wire-layer", _want_wl]
            if _want_fx:
                cov_argv += ["--fx-symbol-layer", _want_fx]
            else:
                _pipe_hint_fx_symbol_cands(prof)
            # 2026-10-05（P1）：子脚本提示用户加的开关，统一入口必须能透传。
            #   coverage 的硬失败文案原文让用户加 --allow-low-pairing，而 pipeline 此前
            #   没有该参数 —— 用户照做只会得到 unrecognized arguments（接口断层）。
            if getattr(args, "allow_low_pairing", False):
                cov_argv += ["--allow-low-pairing"]
                print("[pipeline] 已透传 --allow-low-pairing：符号配对率不足时不再硬失败，"
                      "结果须人工复核", flush=True)
            if _lay:
                print("[pipeline] 自画像下传图层(%s)：%s"
                      % (_lay_src, ", ".join("%s=%s" % (k, v) for k, v in _lay.items())),
                      flush=True)
            elif not (_want_wl or _want_fx):
                print("[pipeline] ! 画像未给出可用图层候选 —— coverage 将扫描全图所有图层，"
                      "结果仅供线索（用 --wire-layer/--fx-symbol-layer 显式指定可消除）", flush=True)
        else:
            _ign = [n for n, v in (("--wire-layer", _want_wl),
                                   ("--fx-symbol-layer", _want_fx)) if v]
            print("[pipeline] 本轮选法 %s **不消费**连线/符号图层参数%s —— 其覆盖与归属均由"
                  "文字标注（米数列 / 标题窗口几何）决定，故不下传（传了会被判"
                  "unrecognized arguments 直接 rc=2）"
                  % (cov_cmd, ("（画像/命令行给出的 " + "、".join(_ign) + " 已按此忽略）")
                     if _ign else ""), flush=True)
        # _bmap 已在 fxmap 阶段解析（用户显式 --bldg-map 优先，否则用落盘的 fxmap.json）
        if _bmap:
            # 2026-09-18（第 3 轮）：--bldg-map 只有 analyze_coverage.py（coverage 子命令）接。
            #   analyze_coverage_vshape.py 的楼栋归属由**标题窗口几何**决定，对照表不参与，
            #   传它被判 unrecognized arguments 直接 rc=2 —— 实测凡产出 fxmap 的分带全中
            #   （先前被误当成「覆盖无判据」）。此处按子命令分派，不再一律传。
            if cov_cmd == "coverage":
                cov_argv += ["--bldg-map", _bmap]
            else:
                print("[pipeline] 注意：本轮选法 %s **不消费**总图对照表（其楼栋/单元归属"
                      "由标题窗口几何决定），故不传 --bldg-map；该来源的归属未经对照表"
                      "交叉验证，结论须照此标注" % cov_cmd, flush=True)
        if not _bmap:
            print("[pipeline] 提示：无总图对照表(<outdir>/fxmap.json)；%s"
                  % ("coverage 楼栋归属将回退『标题 x 中分』" if cov_cmd == "coverage"
                     else "本选法楼栋归属由标题窗口几何决定，不读对照表"), flush=True)
        rc = _run("coverage", cov_argv)
        if rc == 0:
            _cov_produced = True
        elif rc == 3:
            print("[pipeline] coverage rc=3 = 本图不适用（申报制），按降级路径继续", flush=True)
        elif rc:
            return _dump(_std_json_gate(rc), "coverage")
    if stop_idx < 9:
        return _dump(0)

    # ---- ⑥b count_box（户数·图标法；仅画像申报图标法时执行）----
    # 2026-09-25（实跑修复，P0）：画像 handoff 早在 plan 阶段就申报「每层户数=图标法」
    #   （云峰实测 13s 时已申报），但阶段表里没有它 —— 跑完整链后 inspect 的 C5/C8
    #   才以 SKIP 提示「户数须由图标法提供」，用户还得手工补 count-box 再重跑 inspect。
    #   本阶段按画像申报自动执行；产物落盘后 ⑦ inspect 已有的
    #   「outdir/count_box.json 存在即自动纳入」逻辑即刻生效，无需手工接续。
    #   rc=2（输入不足）中止主链、rc=3（本图不适用）继续 —— 与 parse/coverage 同语义。
    cb_out = os.path.join(outdir, "count_box.json")
    _cb_run, _cb_note = _pipe_countbox_choice(prof)
    if not _cb_run:
        ledger.append({"阶段": "count_box", "rc": 3, "秒": 0.0})
        print("[pipeline] %-9s rc=3      0.00s  (%s，跳过)" % ("count_box", _cb_note),
              flush=True)
    elif os.path.isfile(cb_out) and _cb_fingerprint_ok(cb_out, dxf):
        # 写保护语义的对偶：已存在 = 用户/上轮已产出（可能带 --col-scale-map 等手工
        # 调参），**复用优先**、不重算 —— 与 count_box_icons.py 自身的「默认改道
        # _patched.json」写保护一致，绝不覆盖人工调参产物。
        # 2026-09-25（opencode 审核建议③）：复用前校验 DXF 指纹 —— 同 outdir 换图
        #   重跑时旧产物是另一张图的户数，不校验会静默喂错数据。
        ledger.append({"阶段": "count_box", "rc": 0, "秒": 0.0})
        print("[pipeline] %-9s rc=0      0.00s  (复用已有 count_box.json —— 手工调参产物"
              "优先不重算；如需重算请先删除该文件再跑)" % "count_box", flush=True)
        # 2026-09-25（云峰实跑 + opencode 审核返工，问题 2 配套）：复用轮次不重跑
        #   count_box_icons.py，其质量告警（乘号式标注/偏移异常/共用刻度列等）只躺在旧 log
        #   里 —— 此处只读产物打一行摘要，不重算不覆盖；判定与裁决出口统一在
        #   inspect 的 C5 count-box 质量透传。
        try:
            with open(cb_out, "r", encoding="utf-8") as _cbf:
                _cb = json.load(_cbf) or {}
            print("[pipeline]   count_box 复用摘要：归层后总户数 %s；乘号式标注 %d / 偏移异常列 %d / "
                  "共用刻度列组 %d / 多候选 %d / 未归属 %s（判定以 inspect C5 透传为准）"
                  % (_cb.get("归层后总户数"), len(_cb.get("乘号式户数标注") or []),
                     len(_cb.get("刻度偏移异常列") or []), len(_cb.get("共用刻度列组") or []),
                     len(_cb.get("同一端点多候选") or []), _cb.get("未归属图标数")), flush=True)
        except (OSError, ValueError, TypeError):
            pass  # 摘要打不出不阻塞：产物异常会在 inspect 阶段暴露
    else:
        # 指纹不匹配时显式说明为什么不复用（opencode 审核建议③）
        if os.path.isfile(cb_out):
            print("[pipeline] ! count_box.json 指纹不匹配（产物是另一张图的户数）—— "
                  "不复用，走 fresh-run 重算（count_box_icons.py 自身写保护会改道 "
                  "_patched.json；如需覆盖请先删除旧产物）", flush=True)
        # count_box_icons.py 只收位置参数 dxf [out]：--config/--profile 在 ftth.py
        # 子命令层「接受不报错」但从不转发（build_cmd 排除键），直传会被判
        # unrecognized arguments —— 故此处只传位置参数 + **画像/probe 可用参数透传**。
        # 2026-09-25（评审 P0-3 → 修正）：fresh-run 之前注定是"未调参版"，因 --wire-layer
        #   等 20+ 调参全丢。现从画像 effective_layers 透传 wire_layer（语义正确：
        #   effective_layers 是 plan 为覆盖判定准备的连线图层，与 count_box 的
        #   皮线图层同义）。
        #   **不透传 --floor-layer**：probe 的 text_layer 是 parse 的通用文字层
        #   （云峰实测值 "0"，通用图层名），与 count_box 的楼层标注层语义不同，
        #   传了会破坏脚本自适应（实测 rc=2）。楼层标注层由 count_box 自适应识别。
        #   其余调参（--col-scale-map 等图级）仍留自适应，fresh-run 后有未调参版提示兜底。
        _cb_argv = [dxf, cb_out]
        _cb_lay, _ = _pipe_effective_layers(prof)
        _cb_wl = (_cb_lay or {}).get("wire_layer")
        if _cb_wl:
            _cb_argv += ["--wire-layer", _cb_wl]
            print("[pipeline] count_box 下传 wire-layer: %s（来源：画像 effective_layers）"
                  % _cb_wl, flush=True)
        _rc_cb, _cb_text = _run_capture("count_box", _cb_argv,
                                           script="count_box_icons.py")
        if _rc_cb == 3 and "[DIAG-SCHEMATIC-ICONS]" in _cb_text:
            # 2026-09-26：示意画法确认 → 按 L1-C1（2026-09-16 裁决）回落皮线执行
            # count_households.py（替换显式留痕，非静默择法）；格式转换后写
            # count_box.json，该阶段记 rc=3（申报制）继续流水线（后续照跑）。
            print("[count_box] 示意画法确认 → 按 L1-C1（2026-09-16 裁决）回落皮线执行 "
                  "count_households.py（替换显式留痕，非静默择法）", flush=True)
            _fb_path = os.path.join(outdir, "count_fallback.json")
            _rc_fb = _run("count_fallback",
                          ["count", "--dxf", dxf, "--config", cfg,
                           "--profile", prof, "--out", _fb_path])
            if _rc_fb:
                print("[count_box] 皮线回落失败（rc=%d），原样停机，不硬凑；"
                      "其输出见上方（非 --quiet/--brief）或 logs/count_fallback.log"
                      "（--quiet/--brief）"
                      % _rc_fb, flush=True)
                return _dump(_std_json_gate(_rc_fb), "count_box")
            _ok, _msg = _cb_convert_wire_fallback(_fb_path, dxf, cb_out)
            if not _ok:
                print("[count_box] 回落产物格式转换失败：%s —— 原样停机，不硬凑"
                      % _msg, flush=True)
                return _dump(_std_json_gate(2), "count_box")
            print("[count_box] 回落完成：count_box.json 来源=皮线回落（%s），"
                  "归层后总户数=%s —— 后续 coverage/inspect 照跑" % (_fb_path, _msg),
                  flush=True)
        elif _rc_cb == 3:
            print("[pipeline] count_box rc=3 = 本图不适用（申报制），按降级路径继续；"
                  "inspect 的 C5/C8 将按缺失如实判 SKIP", flush=True)
        elif _rc_cb:
            return _dump(_std_json_gate(_rc_cb), "count_box")
        else:
            print("[pipeline] 户数（图标法）产物已落盘: %s —— inspect 将自动纳入 C5/C8"
                  % cb_out, flush=True)
            # 2026-09-25（评审返工，残留风险2）：fresh-run 只传了 dxf [out] 两个位置参数，
            #   count_box_icons.py 的 --col-scale-map / --wire-layer 等调参无法透传
            #   （它本就不收 --config）。若图上存在「一条刻度列服务多个图标列」等需调参
            #   形态，自动版可能不准 —— 显式提示用户核对，必要时手工补跑。
            print("[pipeline] 提示：pipeline 自动跑的 count-box 为**未调参版**（仅自适应"
                  "量测）；若 inspect 的 C5/C8 户数与图面不符，请手工补跑 "
                  "`ftth.py count-box --dxf ... --config ... --col-scale-map ... --out ...`"
                  " 后重跑 inspect（pipeline 复用已有 count_box.json）", flush=True)
    if stop_idx < 10:
        return _dump(0)

    # ---- ⑦ inspect ----
    # 2026-09-25（opencode 审核返工）：删除本处旧裸 isfile 块（--coverage/--titleblock
    #   两路），只保留下方「产出标志 + 残留 WARN」守卫块 —— 旧块不删则 stale 文件
    #   照样经旧块传入（守卫 WARN 形同虚设），且本轮产出时参数被传两次。
    insp_argv = ["inspect", "--parse", parsed, "--geom", geom_json, "--json", insp]
    # 2026-09-18（第 2 轮）：显式下传 --fx-pattern。inspect 的内置默认是 FL\d+-FX\d+，
    #   与本图编号形态（FX\d+#?）不符；不下传则 C4 在 geom 里搜不到任何编号，把 parse
    #   侧全部箱误判成「图上无编号文字」（实测 23/23 假 FAIL）。取 config 的 suggested_params。
    _fxp = ""
    try:
        with open(cfg, "r", encoding="utf-8") as _cf:
            _fxp = str(((json.load(_cf).get("suggested_params") or {}).get("fx_pattern")) or "").strip()
    except (IOError, json.JSONDecodeError, OSError):                 # noqa: BLE001
        _fxp = ""
    if _fxp and not any(w in _fxp for w in ("未提供", "不提取", "留空")):
        insp_argv += ["--fx-pattern", _fxp]
    # 2026-09-18（实跑修复，P1）：把 ③b 产出的图签读数喂给 C10 做逐栋互证。
    #   文件不存在（本图无图签 / 阶段跳过）时不传 ⇒ C10 判 SKIP 并写明「本次未做」。
    # 2026-09-25（opencode 审核返工）：删旧裸 isfile 块，由下方守卫块统一传入。
    # 2026-09-18（实跑修复，P1）：户数（图标法）产物若已落在 outdir，自动喂给 inspect。
    # 2026-09-25（评审 P0 stale 守卫）：**仅当本轮该阶段实际产出时才传** ——
    #   跨画像重跑时旧文件会被静默吃掉。下面三路 --coverage / --titleblock / --count-box
    #   统一用「本轮产出标志 + 残留 WARN」模式（照 count_box 范本）。
    if _cov_produced and os.path.isfile(cov):
        insp_argv += ["--coverage", cov]
    elif not _cov_produced and os.path.isfile(cov):
        print("[pipeline] ! 检测到残留 coverage.json 但本轮 coverage 未产出 —— 已忽略，"
              "避免 stale 文件污染；如需清除请删除 %s" % cov, flush=True)
    if _tb_produced and os.path.isfile(tb):
        insp_argv += ["--titleblock", tb]
    elif not _tb_produced and os.path.isfile(tb):
        print("[pipeline] ! 检测到残留 titleblock.json 但本轮 titleblock 未产出 —— 已忽略，"
              "避免 stale 文件污染；如需清除请删除 %s" % tb, flush=True)
    _cb_path = os.path.join(outdir, "count_box.json")
    if _cb_run and os.path.isfile(_cb_path):
        insp_argv += ["--count-box", _cb_path]
    elif not _cb_run and os.path.isfile(_cb_path):
        print("[pipeline] ! 检测到残留 count_box.json 但本轮画像非图标法 —— "
              "已忽略，避免 stale 文件污染；如需清除请删除 %s" % _cb_path, flush=True)
    # 2026-09-30（一百三十二）：C3-nofloor 用对照表作第二来源。_bmap 创建时已有
    #   “本轮产出/用户显式”守卫，此处只补 isfile（stale 残留早被置空，不会到这）。
    if _bmap and os.path.isfile(_bmap):
        insp_argv += ["--fx-map", _bmap]
    _rc_insp = _run("inspect", insp_argv)
    return _dump(_rc_insp, "inspect" if _rc_insp else None)


def main():
    ap = _CliParser(description="FTTH DXF 解析工具链")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # 通用参数（所有子命令共享）
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", help="探查生成的配置 JSON，自动填充其它参数")
    common.add_argument("--dxf", help="输入 DXF 文件路径")

    # probe: 探查图层/文字格式
    p_probe = sub.add_parser("probe", parents=[common], help="探查图纸结构，输出建议参数")
    p_probe.add_argument("--text-layer", default=None)
    p_probe.add_argument("--text-type", default=None)
    p_probe.add_argument("--title-pattern", default=None)
    p_probe.add_argument("--floor-pattern", default=None)
    p_probe.add_argument("--hu-pattern", default=None)
    p_probe.add_argument("--cable-pattern", default=None)
    p_probe.add_argument("--fx-pattern", default=None)
    p_probe.add_argument("--unit-pattern", default=None)
    p_probe.add_argument("--cable-keywords", default=None, help="光缆识别关键词正则")
    p_probe.add_argument("--insert-blocks", default=None, help="INSERT块名列表，逗号分隔")
    p_probe.add_argument("--insert-attrib-tag", default=None, help="ATTRIB属性tag名，逗号分隔")
    p_probe.add_argument("--insert-attrib-val", default=None, help="ATTRIB属性值筛选正则")
    p_probe.add_argument("--out", help="探查结果输出 JSON 路径")

    # plan: 图纸画像（Step 1a 探查的选法产物）
    p_plan = sub.add_parser("plan", parents=[common],
                            help="生成图纸画像 profile.json（信号判定 + 选法 + 门禁评估）")
    p_plan.add_argument("--out", required=True, help="输出 profile.json 路径")
    p_plan.add_argument("--probe", default=None, help="已生成的 probe.json（复用其文字样例）")
    p_plan.add_argument("--project-dir", default=None, help="项目目录（检测《楼宇信息采集表》）")
    p_plan.add_argument("--text-layer", default=None)
    p_plan.add_argument("--text-type", default=None)
    p_plan.add_argument("--title-pattern", default=None)
    p_plan.add_argument("--fx-pattern", default=None)
    p_plan.add_argument("--wire-keywords", default=None,
                        help="连线图层关键词正则（覆盖内置通用清单）")
    p_plan.add_argument("--vert-dx", type=float, default=3.0, help="竖线段 x 跨度阈值")
    p_plan.add_argument("--verbose", action="store_true")

    # parse: 结构化解析
    p_parse = sub.add_parser("parse", parents=[common], help="结构化解析 DXF -> JSON")
    p_parse.add_argument("--expand-bldg-ranges", action="store_true", default=None,
                         help="楼栋区间标题（如 `1-3号楼`）按区间语义展开为 1,2,3；"
                              "默认不展开（只取字面数字并 WARNING 待裁决）——须用户确认后启用")
    p_parse.add_argument("--out", default=None, help="输出 JSON 路径")
    p_parse.add_argument("--title-band-tol", type=float, default=None,
                         help="楼栋标题分带容差（y）；留空 → 2 倍层高自适应，层高不可得 → 单带")
    p_parse.add_argument("--consensus-x-tol", type=float, default=None,
                         help="列共识分列容差（x）；留空 = 精确同值分桶（历史行为）")
    p_parse.add_argument("--legacy-bldg-assign", action="store_true", default=False,
                         help="【仅对拍】强制旧的纯 x 先到先得楼栋归属（忽略 y）")
    p_parse.add_argument("--text-layer", default=None)
    p_parse.add_argument("--text-type", default=None)
    p_parse.add_argument("--title-pattern", default=None)
    p_parse.add_argument("--floor-pattern", default=None)
    p_parse.add_argument("--hu-pattern", default=None)
    p_parse.add_argument("--cable-pattern", default=None)
    p_parse.add_argument("--fx-pattern", default=None)
    p_parse.add_argument("--fx-map", dest="fx_map", default=None,
                         help="总图 FX 对照表 JSON（extract_fx_map.py 产物）；"
                              "只回填 parse 侧缺失的安装楼层，不覆盖已测值，重号不回填")
    p_parse.add_argument("--bldg-map", dest="bldg_map", default=None,
                         help="总图 FX 对照表 JSON（同上）；提供后箱的**楼栋/单元归属以"
                              "对照表为准**（SKILL.md 硬约束②，禁用标题 x 中分）。"
                              "总图对照表形态的图纸不传它则逐栋 0 箱；只改归属不改安装楼层")
    p_parse.add_argument("--unit-pattern", default=None)
    p_parse.add_argument("--unit-split-keyword", default=None,
                         help="分离形态单元轴合成关键词（单元轴=纯数字+含关键词纯文字两个实体，"
                              "如『1』+『单元电井』）；传入（如`单元`）后启用合成锚点")
    p_parse.add_argument("--floor-mode", default=None, choices=["full", "nofloor"],
                         help="安装楼层判定模式（2026-09-30 V3 Phase A）：full=现行判定照旧；"
                              "nofloor=去决策（只定归属不定安装楼层；默认 full，老行为不变）")
    p_parse.add_argument("--cable-keywords", default=None, help="光缆识别关键词正则")
    p_parse.add_argument("--unit-cluster", type=float, default=None, help="留空=子脚本按层高自适应")
    p_parse.add_argument("--unit-range", type=float, default=None, help="留空=子脚本按层高自适应")
    p_parse.add_argument("--y-tol", type=float, default=None, help="留空=子脚本按层高自适应")
    p_parse.add_argument("--clone-shared-hu", action="store_true", default=False,
                         help="共用轴户数列落空时克隆进该栋每个单元（一百五十九，默认关）。"
                              "属归属裁定：须先以图签第二来源（「层数×每层户数×单元数」）核对"
                              "确为「每单元每层」口径后再开，否则会把「整栋每层」口径翻倍；"
                              "仅对户数生效，箱编号/皮线米数仍不克隆")
    p_parse.add_argument("--insert-blocks", default=None, help="INSERT块名列表，逗号分隔")
    p_parse.add_argument("--insert-attrib-tag", default=None, help="ATTRIB属性tag名，逗号分隔")
    p_parse.add_argument("--insert-attrib-val", default=None)
    p_parse.add_argument("--profile", default=None,
                         help="plan 生成的 profile.json；提供则按画像门禁校验后执行")

    # coverage: 覆盖范围分析
    p_cov = sub.add_parser("coverage", parents=[common], help="分纤箱覆盖范围线索分析")
    p_cov.add_argument("--out", default=None, help="输出 JSON 路径")
    p_cov.add_argument("--text-layer", default=None)
    p_cov.add_argument("--text-type", default=None)
    p_cov.add_argument("--title-pattern", default=None)
    p_cov.add_argument("--floor-pattern", default=None)
    p_cov.add_argument("--fx-pattern", default=None)
    p_cov.add_argument("--unit-cluster", type=float, default=None, help="留空=子脚本按层高自适应")
    p_cov.add_argument("--vert-dx", type=float, default=None, help="留空=子脚本按层高自适应")
    p_cov.add_argument("--vert-dy", type=float, default=None, help="留空=子脚本按层高自适应")
    p_cov.add_argument("--fx-window", type=float, default=None, help="留空=子脚本按层高自适应")
    p_cov.add_argument("--merge-tol", type=float, default=None, help="留空=子脚本按层高自适应")
    p_cov.add_argument("--conn-tol", type=float, default=None, help="留空=子脚本按层高自适应")
    p_cov.add_argument("--wire-layer", default=None)
    p_cov.add_argument("--insert-attrib-tag", default=None)
    p_cov.add_argument("--insert-attrib-val", default=None)
    p_cov.add_argument("--bldg-map", default=None)
    p_cov.add_argument("--bldg-pad", type=float, default=None, help="留空=子脚本按层高自适应")
    p_cov.add_argument("--title-band-tol", type=float, default=None, help="留空=子脚本按层高自适应")
    p_cov.add_argument("--fx-symbol-layer", default=None)
    p_cov.add_argument("--fx-symbol-cluster", type=float, default=None, help="留空=子脚本按层高自适应")
    p_cov.add_argument("--fx-symbol-max-size", type=float, default=None, help="留空=子脚本按层高自适应")
    p_cov.add_argument("--symbol-pair-tol", type=float, default=0.0)
    p_cov.add_argument("--total-pad", type=float, default=None, help="留空=子脚本按层高自适应")
    p_cov.add_argument("--break-floor-tol", type=float, default=0.0)
    p_cov.add_argument("--max-break-span", type=float, default=0.0)
    p_cov.add_argument("--profile", default=None,
                       help="plan 生成的 profile.json；提供则按画像门禁校验后执行")
    # 2026-09-18 整改：analyze_coverage.py 早就有这个开关（低于配对率阈值时强行继续），
    #   但统一入口没透传 —— 它的报错文案却明确让用户「加 --allow-low-pairing 强行继续」，
    #   用户照做只会得到 "unrecognized arguments"。直调脚本有、统一入口没有 = 接口断层。
    p_cov.add_argument("--allow-low-pairing", action="store_true", default=False,
                       help="箱符号可信配对率 <30%% 时不再硬失败，强行继续（结果须人工复核）")

    # coverage-vshape: 覆盖范围分析（皮线 V 形法，只读文字标注，不需要连线图层）
    p_vs = sub.add_parser("coverage-vshape", parents=[common],
                          help="分纤箱覆盖范围判定（皮线 V 形法：米数谷底→箱安装层）")
    p_vs.add_argument("--out", default=None, help="输出 JSON 路径")
    p_vs.add_argument("--text-layer", default=None)
    p_vs.add_argument("--text-type", default=None)
    p_vs.add_argument("--title-pattern", default=None)
    p_vs.add_argument("--floor-pattern", default=None)
    p_vs.add_argument("--fx-pattern", default=None)
    p_vs.add_argument("--box-mark-pattern", default=None,
                      help="系统图上箱位标记文字正则（可选），如 配线箱|分纤箱；"
                           "作 V 谷底定层的独立第二来源")
    p_vs.add_argument("--hu-pattern", default=None)
    p_vs.add_argument("--cable-pattern", default=None)
    p_vs.add_argument("--cable-meters-group", type=int, default=None,
                      help="米数所在捕获组序号（1 基）。字段序非「米数在前」时必填，"
                           "如 `2Px2芯x36m` 配 (\\d+)Px(\\d+)芯(\\d+)m 时传 3")
    p_vs.add_argument("--cable-count-group", type=int, default=None,
                      help="根数所在捕获组序号（1 基）")
    p_vs.add_argument("--x-tol", type=float, default=None,
                      help="建列容差兜底值（仅在量不出字高时使用）")
    p_vs.add_argument("--col-x-tol-factor", type=float, default=None,
                      help="米数列建列容差 = 本系数 × 米数文字高度中位数（尺度锚，默认 3.0）")
    p_vs.add_argument("--min-col-rows", type=int, default=None,
                      help="米数列最少行数门槛（默认 3），低于此数不生成单元")
    p_vs.add_argument("--y-margin-factor", type=float, default=None,
                      help="窗口 y 上下外扩 = 本系数 × 层高（默认 3.0）")
    p_vs.add_argument("--y-tol", type=float, default=None)
    p_vs.add_argument("--floor-x-tol", type=float, default=None,
                      help="楼层列 x 聚类容差（默认 3000，由 vshape 自带）")
    p_vs.add_argument("--box-x-tol", type=float, default=None)
    p_vs.add_argument("--box-anchor-x-factor", type=float, default=None,
                      help="箱锚 x 邻域门禁系数（默认 10.0，由 vshape 自带）")
    p_vs.add_argument("--margin", type=float, default=None)
    p_vs.add_argument("--include-basement", action="store_true",
                      help="把全局最低段下方的地下层并入覆盖下界（默认关闭）")
    p_vs.add_argument("--fx-locations", default=None,
                      help="箱位直读标注 JSON（extract_fx_locations.py 产出，可选）；"
                           "提供后 vshape 做安装层两来源交叉校验")
    p_vs.add_argument("--parse", default=None,
                      help="结构化解析产物 parsed.json（可选）；箱号锚缺席时 vshape 按"
                           "解析侧安装层（口径A′箱位直读）与 V 谷底配对归属"
                           "（2026-09-26 第5轮迭代；文件不存在/无数据时行为不变）")
    p_vs.add_argument("--dev-gate-factor", type=float, default=None,
                      help="v底vs箱符号偏差可信门禁系数（×层高）；留空=vshape 默认 5.0")
    p_vs.add_argument("--profile", default=None,
                      help="plan 生成的 profile.json；提供则按画像门禁校验后执行")

    # verify-truth: 用已定稿标准地址表反查覆盖范围线索（回归验收）
    p_vt = sub.add_parser("verify-truth", parents=[common], help="用标准地址表反查覆盖范围线索")
    p_vt.add_argument("xlsx", help="已定稿的标准地址表 xlsx")
    p_vt.add_argument("covjson", help="analyze_coverage.py 输出的 JSON")
    p_vt.add_argument("--sheet", default=None)
    p_vt.add_argument("--col-box", default="分纤箱")
    p_vt.add_argument("--col-bldg", default="六级")
    p_vt.add_argument("--col-unit", default="七级")
    p_vt.add_argument("--col-floor", default="八级")
    p_vt.add_argument("--col-door", default="九级")
    p_vt.add_argument("--json-key", default="覆盖范围线索")
    p_vt.add_argument("--fx-prefix", default=None,
                      help="定稿表分纤箱列统一前缀（与 gen --fx-prefix 对称；"
                           "gen 出表加了前缀时反查传同一前缀，不传行为不变）")

    # inspect: 出表前一体化闭合核查（替代临时 inspect_*.py，只读 JSON、不需 --dxf）
    p_insp = sub.add_parser("inspect", parents=[common], help="出表前一体化闭合核查（parse/coverage/geom 三源）")
    p_insp.add_argument("--parse", dest="parse_json", required=True, help="parse_dxf_structured 输出的 JSON")
    p_insp.add_argument("--coverage", dest="coverage_json", default=None, help="覆盖范围 JSON（可选）")
    p_insp.add_argument("--geom", dest="geom_json", default=None, help="<DXF>.geom.json 几何缓存（可选）")
    p_insp.add_argument("--count-box", dest="count_box_json", default=None,
                        help="count_box_icons.py 的输出 JSON（可选）；parse 侧无箱时作为替代口径")
    p_insp.add_argument("--fx-pattern", default=r"FL\d+-FX\d+", help="分纤箱编号正则")
    # 2026-09-18（实跑修复，P1）：C10「图签第二来源逐栋比对」的输入。此前 inspect_closure.py
    #   单独调用能收到该参数，但经本入口时 argparse 直接判 unrecognized arguments →
    #   inspect 根本没跑、rc=2 而**没有任何检查项输出**（实测，冒烟测试只测本体测不到）。
    p_insp.add_argument("--titleblock", dest="titleblock_json", default=None,
                        help="read_titleblock_households.py 输出的图签读数 JSON（可选，供 C10）")
    p_insp.add_argument("--fx-map", dest="fx_map_json", default=None,
                        help="总图 FX 对照表 JSON（extract_fx_map.py 产物，可选；"
                             "parse floor-mode=nofloor 时 C3 改比 coverage vs 对照表，需本输入）")
    p_insp.add_argument("--json", dest="json_out", default=None, help="机读结果输出路径（可选）")

    # count: 户数统计（皮线计数）
    p_count = sub.add_parser("count", parents=[common], help="皮线计数估算户数（特定图纸适用）")
    p_count.add_argument("--expand-bldg-ranges", action="store_true", default=None,
                             help="楼栋区间标题（如 `1-3号楼`）按**区间**语义展开；须用户确认后启用")
    p_count.add_argument("--out", default=None, help="输出 JSON 路径")
    p_count.add_argument("--profile", default=None, help="plan 生成的 profile.json（count 不做门禁检查，仅接受不报错，便于统一调用）")
    p_count.add_argument("--text-layer", default=None)
    p_count.add_argument("--text-type", default=None)
    p_count.add_argument("--title-pattern", default=None)
    p_count.add_argument("--floor-pattern", default=None)
    p_count.add_argument("--fiber-pattern", default=None)
    p_count.add_argument("--special-pattern", default=None)
    p_count.add_argument("--assign", default=None, choices=["abs", "up", "down"])
    p_count.add_argument("--match-tol", type=float, default=None, help="留空=子脚本按层高自适应")
    p_count.add_argument("--x-cluster", type=float, default=None, help="留空=子脚本按层高自适应")
    p_count.add_argument("--x-y-gap", type=float, default=None, help="留空=子脚本按层高自适应")
    # 注：`--insert-attrib-tag/val`（旧「HDD 图块法」）已于 2026-09-13 随「不读楼层平面图」裁定摘除 ——
    # 那次摘的是**按属性值数平面图 INSERT** 这条路（平面图一个户型只画一个图标＝示意画法）。
    # 2026-09-14 新增 `count-box` 子命令（`count_box_icons.py`）：同样用家居配线箱图标，
    # 但判据换成**几何**——图标必须紧贴「皮线图元」端点（实测云峰恒定偏移 4.04，331/331 命中），
    # 平面图图标因周边没有系统图皮线而不可能贴末端，天然被排除。
    # 故此处仍不恢复 `--insert-attrib-tag/val`（那是属性值匹配，会重新引入平面图噪声）。
    #
    # 2026-09-14 晚：子命令由 `count-hdd` 正名为 **`count-box`**（家居配线箱图标法）——
    # 方法名不得绑死在 `HDD` 一种图内文字上（云峰写 HDD、柳辛庄写 HD）。
    # 旧名 `count-hdd` 保留为别名，不破坏既有调用。

    # count-box: 户数统计（家居配线箱图标法：图标贴皮线末端）
    p_hdd = sub.add_parser("count-box", aliases=["count-hdd"], parents=[common],
                           help="户数统计（家居配线箱图标法：图标贴皮线末端）")
    p_hdd.add_argument("--out", default=None, help="输出 JSON 路径")
    p_hdd.add_argument("--profile", default=None, help="plan 生成的 profile.json（count-box 不做门禁检查，仅接受不报错，便于统一调用）")
    p_hdd.add_argument("--wire-layer", default=None,
                       help="皮线/连线图层名，逗号分隔（显式指定，优先于关键词）")
    p_hdd.add_argument("--wire-keys", default=None, help="皮线图层关键词，逗号分隔")
    p_hdd.add_argument("--wire-exclude", default=None, help="排除的图层关键词，逗号分隔")
    p_hdd.add_argument("--insert-blocks", default=None, help="限定 INSERT 块名，逗号分隔（默认全部）")
    p_hdd.add_argument("--include-square", action="store_true",
                       help="追加『小闭合方块』为候选（覆盖只画方块、不插块的图纸）")
    p_hdd.add_argument("--square-min", type=float, default=None, help="方块最小边")
    p_hdd.add_argument("--square-max", type=float, default=None, help="方块最大边")
    p_hdd.add_argument("--tol", type=float, default=None, help="贴合容差（默认自适应量测）")
    p_hdd.add_argument("--search-radius", type=float, default=None, help="最近端点搜索半径")
    p_hdd.add_argument("--strong-keys", default=None, help="强关键词，逗号分隔")
    p_hdd.add_argument("--weak-keys", default=None, help="弱关键词，逗号分隔")
    p_hdd.add_argument("--floor-layer", default=None, help="楼层标注图层（默认自动识别）")
    p_hdd.add_argument("--scale-max-dx", type=float, default=None, help="图标列到刻度列的最大 x 距离")
    p_hdd.add_argument("--region-y", default=None, help="显式限定图区 y 范围 min,max")
    p_hdd.add_argument("--region-pad", type=float, default=None, help="图区 y 方向余量")
    p_hdd.add_argument("--col-x-tol", type=float, default=None, help="同一物理列的 x 聚类容差")
    p_hdd.add_argument("--col-gap", type=float, default=None, help="同一 x 带上不同图区的 y 断口阈值")
    p_hdd.add_argument("--col-scale-map", dest="col_scale_map", default=None,
                       help="显式指定「图标列 x → 刻度列 x」，格式 \"列x=刻度列x;...\""
                            "（用于『一条刻度列服务多个图标列』的图纸）")
    p_hdd.add_argument("--force", action="store_true",
                       help="允许覆盖已存在的输出产物（默认改道 <原名>_patched.json，写保护）")

    # gen: 生成标准地址表
    p_gen = sub.add_parser("gen", parents=[common], help="生成每户一行的标准地址表 xlsx")
    # 2026-09-16：上游产物参数名与 `inspect` 侧统一（同一产物统一叫 --parse / --coverage）。
    # 旧名 --dxf-json / --coverage-json 保留为别名，既有调用不受影响（dest 不变）。
    p_gen.add_argument("--parse", "--dxf-json", dest="dxf_json", required=True,
                       help="parse 输出的 JSON（别名 --dxf-json）")
    # 2026-09-29（一百二十七·P0）：gen 强制绑定闭合核查。缺省即 rc=2 禁出表，
    #   不再允许直调裸出（此前 pending 可绕过 inspect 进入成品）。
    p_gen.add_argument("--inspect", "--inspect-json", dest="inspect_json", required=True,
                       help="inspect 输出的闭合 JSON（必传，rc==0 且输入指纹一致）")
    p_gen.add_argument("--out", required=True, help="输出 xlsx 路径")
    p_gen.add_argument("--coverage", "--coverage-json", dest="coverage_json",
                       help="用户裁决后的覆盖范围 JSON（别名 --coverage-json）")
    p_gen.add_argument("--template", help="标准地址模板 xlsx/xls")
    p_gen.add_argument("--addr", help="前5级地址：省,市,区,街道,小区")
    p_gen.add_argument("--branch", help="分公司名称（模板第1列）")
    p_gen.add_argument("--sheet-name", default="标准地址")
    p_gen.add_argument("--cover-rule", default="floor100", choices=["floor100", "floor10", "unit"])
    p_gen.add_argument("--floor-pattern", default=None)
    # 2026-09-17（P2-1）：以下参数 gen_addressbook.py 早已原生支持，但调度层此前不透传，
    #   调用方想要楼层中文格式等能力时被迫绕过统一入口直调子脚本（实测某会话为此旁路）。
    #   参数名与子脚本逐一相同，build_cmd 只转发显式指定的项，缺省行为完全不变。
    p_gen.add_argument("--floor-format", default=None, choices=["auto", "chinese", "raw"],
                       help="楼层列格式：auto=按模板示例行自动判定（默认）；chinese=三层；raw=3F")
    p_gen.add_argument("--door-format", default=None, choices=["auto", "int", "str"],
                       help="户号列格式：auto=按模板示例行自动判定（默认）；int=101；str=101室")
    p_gen.add_argument("--fx-prefix-map", default=None,
                       help="分纤箱编号前缀归一化映射 \"旧=新;旧2=新2\"（须人工确认后显式传入）")
    p_gen.add_argument("--fx-prefix", default=None,
                       help="分纤箱编号统一前缀：P 列每行统一前置（已带则不叠加；空值/未分配不加；与 map 并用时先归一后加前缀；不从 --addr 自动推导）")
    p_gen.add_argument("--allow-lossy", action="store_true",
                       help="允许丢弃楼层继续出表（默认关闭：有楼层被丢即中止）")

    # assemble: 出表输入 JSON 组装（count-box 路线：逐层户数 + 显式列归属映射 + coverage 分纤箱）
    p_asm = sub.add_parser("assemble", parents=[common],
                           help="出表输入 JSON 组装（count 逐层户数 + 显式 col-map + coverage 分纤箱）")
    p_asm.add_argument("--count", required=True,
                       help="count_box_icons.py 输出的 count.json（列不含楼栋归属，归属由 --col-map 显式给出）")
    p_asm.add_argument("--col-map", required=True,
                       help='列归属映射 "列号=楼栋/单元[,楼栋2/单元2...];..."；'
                            "一列多单元=共享系统图克隆；单元省略=单单元楼（归一 1单元）")
    p_asm.add_argument("--coverage", dest="coverage_json", default=None,
                       help="覆盖范围 JSON（可选，合并各单元分纤箱信息）")
    p_asm.add_argument("--out", required=True, help="输出 JSON 路径（gen 的 --dxf-json 输入）")
    p_asm.add_argument("--force", action="store_true",
                       help="允许覆盖已存在的输出产物（默认改道 <原名>_patched.json，写保护）")

    # apply-ruling: 按人工裁决清单批量改数（2026-09-18 新增，消灭逐条手改脚本的返工）
    p_rul = sub.add_parser("apply-ruling", parents=[common],
                           help="按人工裁决清单批量改出表输入 JSON（户数/箱安装楼层/覆盖范围）")
    p_rul.add_argument("--json", dest="json", required=True,
                       help="待改数的出表输入 JSON（assemble_households.py 产物）")
    p_rul.add_argument("--ruling", default=None, help="裁决清单 JSON 路径（顶层「裁决」数组）")
    p_rul.add_argument("--set", action="append", default=None,
                       help='简写「楼栋/单元/楼层=户数」，可重复传；与 --ruling 可并用')
    p_rul.add_argument("--out", default=None,
                       help="输出 JSON 路径；省略则写 <原名>_patched.json（写保护默认）")
    p_rul.add_argument("--force", action="store_true",
                       help="允许 --out == 输入路径（覆盖原产物，须显式声明）")
    p_rul.add_argument("--dry-run", action="store_true", help="只打印变更，不写文件")

    # split-band: 多地块图纸按 y 带切出子 DXF（同名楼分带解析的前置步骤）
    p_sb = sub.add_parser("split-band", parents=[common],
                          help="多地块图纸按 y 带裁剪出各地块子 DXF（供 parse/coverage 分带运行）")
    p_sb.add_argument("--out-dir", help="子 DXF 输出目录（自动创建；--auto 出方案时可省）")
    p_sb.add_argument("--band", action="append",
                      help='分带参数 "名称:ymin:ymax"，可重复传；单值内也可用逗号分隔多条。'
                           '边界须取实测锚点 y（有「N块地」类锚点时用 --auto）；'
                           '无锚点、只能按楼栋标题定界时，上界取上邻带标题 y、'
                           '**不得取相邻标题中点**。与 --auto 互斥。')
    p_sb.add_argument("--auto", action="store_true",
                      help="由图上实测的「N块地」类锚点自动算分带窗口（探针与分带共用同一"
                           "实现）。默认只出方案不写文件，核对后加 --yes 执行")
    p_sb.add_argument("--yes", action="store_true",
                      help="--auto 下确认执行（不加则只打印分带方案）")
    p_sb.add_argument("--text-layer", help="文字图层（逗号分隔）；缺省读 --config 的建议值")
    p_sb.add_argument("--title-pattern", help="楼栋标题正则；缺省读 --config 的建议值")

    # pipeline: 一条命令串跑多阶段（2026-09-17 新增，见 cmd_pipeline 文档字符串）
    p_pipe = sub.add_parser("pipeline", parents=[common],
                            help="一键串跑 geom->probe->plan->titleblock->fxmap->parse->"
                                 "coverage->inspect（只解析、不出表；各阶段产物落 --outdir）")
    p_pipe.add_argument("--outdir", required=True,
                        help="产物目录；各阶段产物用固定文件名（config/profile/parsed/coverage/inspect）落在此处")
    p_pipe.add_argument("--project-dir", default=None,
                        help="项目目录，透传给 plan（用于检测《楼宇信息采集表》；不传则 plan 的 intake_table 留 unknown）")
    p_pipe.add_argument("--profile", default=None,
                        help="复用指定画像；默认 <outdir>/profile.json")
    p_pipe.add_argument("--stop-at", default="inspect", choices=list(_PIPE_STAGES),
                        help="跑到该阶段为止（含）；默认 inspect")
    p_pipe.add_argument("--reuse-geom", action="store_true",
                        help="几何缓存比 DXF 新时直接复用，不重跑 dump_geom")
    p_pipe.add_argument("--quiet", action="store_true",
                        help="各阶段输出写入 <outdir>/logs/<阶段>.log，不刷屏")
    p_pipe.add_argument("--brief", action="store_true",
                        help="日志落盘 + 控制台只显示摘要（每阶段最后 30 行 + "
                             "[WARNING]/[ERROR]/FAIL/WARN/[gate] 行；全文见 "
                             "<outdir>/logs/<阶段>.log）。--quiet 为完全静默")
    # 2026-09-18 整改：画像早已探明这两个图层，但流水线没有环节把它喂给 coverage，
    #   导致 coverage 裸跑（扫全图建筑 WALL 层 / 找不到箱符号层）实测 rc=3。
    #   留空则自动取自画像（effective_layers，兼容老画像的 param_source.must_probe）。
    p_pipe.add_argument("--wire-layer", default=None,
                        help="连线/皮线图层，逗号分隔；留空=自画像 effective_layers 取")
    p_pipe.add_argument("--fx-symbol-layer", default=None,
                        help="分纤箱图形符号所在图层；留空=自画像 effective_layers 取")
    p_pipe.add_argument("--bldg-map", default=None,
                        help="总图 FX 对照表 JSON；留空=自动用 <outdir>/fxmap.json（若存在）")
    p_pipe.add_argument("--expand-bldg-ranges", action="store_true", default=None,
                         help="把标题里的区间楼号 `N-M号楼` 展开为 N..M 全部楼栋（默认关闭）。"
                              "区间语义（`1-3号楼`=1、2、3 号 还是 1、3 号）只能由人裁决，"
                              "**确认后**再开启；开启动作会透传给 parse。")
    p_pipe.add_argument("--unit-split-keyword", default=None,
                         help="分离形态单元轴合成关键词（如`单元`）；留空=自动取探查建议 "
                              "suggested_params.unit_split_keyword；显式给出优先。")
    p_pipe.add_argument("--parse-no-floor", action="store_true", default=None,
                        help="parse 去决策（V3 Phase A）：只定归属、不定安装楼层 "
                             "（透传 parse --floor-mode nofloor；C2/C3/gen 双模式消费；"
                             "默认关闭，老行为不变）。")
    # 2026-10-05（P1）：同一处接口断层在 coverage 这个开关上重演过一次 —— 该处的报错
    #   文案原文让用户「加 --allow-low-pairing 强行继续」，而流水线入口一直没有这个参数，
    #   用户照做只会拿到 unrecognized arguments。凡子脚本提示用户加的开关，统一入口
    #   必须同步具备，否则提示即死路。默认 False（保持原硬失败行为），仅透传不代判。
    p_pipe.add_argument("--allow-low-pairing", action="store_true", default=False,
                        help="本图确无箱图形符号（箱体只写编号）时，允许 coverage 在低/零"
                             "配对率下强行继续（结果须人工复核）；仅透传给 coverage 子命令。")
    # 2026-10-05：多地块图的分带此前**只在独立子命令里**，串跑撞同名楼守卫必然 rc=2
    #   而正确路径走不到。默认开启（单地块图量出 <2 带即原路返回，零影响）。
    p_pipe.add_argument("--no-auto-split-band", dest="auto_split_band",
                        action="store_false", default=True,
                        help="关闭「多地块自动分带并逐带跑完整 pipeline」（默认开启；"
                             "子带数 <2 时自动退回单地块路径）")

    # budget: SKILL.md 体量闸门（2026-09-18 新增）
    #   阈值从 version.json 的 budget 段读（单一权威）；脚本内只留兜底值，且会标注实际来源。
    p_bud = sub.add_parser("budget", parents=[common],
                           help="SKILL.md / references 体量闸门（阈值取自 version.json）")
    p_bud.add_argument("--json-out", default=None, help="把结果写成 JSON")

    # transitions: 迁移门禁核对（2026-09-18 接入主入口；核对器本体此前已存在但未接线）
    p_tr = sub.add_parser("transitions", parents=[common],
                          help="迁移门禁核对：核 SKILL.md「禁止迁移」5 条（与成品落盘交叉核验）")
    p_tr.add_argument("--project-dir", required=True, help="三本台账所在目录")
    p_tr.add_argument("--project", default=None, help="项目名（台账内字段，可选）")
    p_tr.add_argument("--product", default=None,
                      help="成品路径；不传则在该目录扫 标准地址表*.xlsx")
    p_tr.add_argument("--closure", default=None,
                      help="inspect_closure.py --json 的机读结果（可选，用于判据 #4）")
    p_tr.add_argument("--json-out", default=None, help="机读结果输出路径（可选）")

    # new-run: 从零跑清场（2026-10-04 新增，P0-A2）
    #   动机：三本台账累计式，复跑不隔离会让上一轮裁决被误当「已确认基准」。
    #   行为：项目目录内非 run_* 产物全部归档进 run_<时间戳>/（不删除），随后重建空台账。
    p_nr = sub.add_parser("new-run", parents=[common],
                          help="从零跑清场：归档项目目录内历史产物并重建三本台账")
    p_nr.add_argument("--project-dir", required=True, help="项目产物目录（三本台账所在目录）")
    p_nr.add_argument("--project", default=None, help="项目名（写入台账的项目字段，可选）")

    # summary: 解析结果总览（2026-10-04 新增，P1-E4）
    #   动机：每次跑完 parse 都手写汇总脚本才能看到楼栋×单元×户数×箱，浪费。
    #   行为：读 parsed.json，打印总览表（Step 3 提交材料的半成品），内联实现无子脚本。
    p_sum = sub.add_parser("summary", parents=[common],
                          help="打印 parse.json 的楼栋×单元×户数×分纤箱总览表")
    p_sum.add_argument("--parse", dest="parse_json", required=True,
                       help="parse_dxf_structured.py 输出的 JSON")
    p_sum.add_argument("--coverage", dest="coverage_json", default=None,
                       help="coverage-vshape.py 输出 JSON（可选，附加覆盖楼层列）")

    # verify-answer: 成品 vs 参考答案逐行对拍（2026-10-04 新增，P1-E5）
    #   动机：跑完必核对是用户固定工作流，每次手写对拍脚本，口径可能不一致。
    #   行为：openpyxl 逐行对比 H/J/L/N/P 五列，打印差异 + 每栋汇总，内联实现。
    p_va = sub.add_parser("verify-answer", parents=[common],
                         help="成品 xlsx vs 参考答案 xlsx 逐行对拍（H/J/L/N/P 五列）")
    p_va.add_argument("--new", dest="new_xlsx", required=True, help="待验证的成品 xlsx")
    p_va.add_argument("--answer", dest="answer_xlsx", required=True, help="标准答案 xlsx")

    args = ap.parse_args()

    # 读取配置文件并填充缺失参数（H2 修复：参数默认值改为 None，config 可覆盖）
    if args.config and os.path.exists(args.config):
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # P1-16 修正：校验 config 中的 key 是否为当前子命令的有效参数
        # 获取当前子命令的合法参数名集合
        valid_keys = set(vars(args).keys())
        # 2026-09-17（配置噪音治理）：收集**本工具链全部子命令**认识的参数名。
        #   动机：probe 产出的 suggested_params 是给整条流水线用的（含 bldg_pattern、
        #   hu_pattern、proximity_tol 等）。逐命令喂下去时，本命令用不到的键此前
        #   一律报 "[WARN] 不是有效参数" 并计入 CONFIG-IGNORED —— 实测 inspect 一次
        #   刷 11 行，把真告警（如『楼号缺 4#』）整个淹没。
        #   新口径：键在本工具链**别的**子命令里存在 ⇒ 属正常（本命令不需要），
        #   只汇总一行 [config-skip]；键不在任何子命令里 ⇒ 才是拼写错误/未知键，
        #   维持原 WARN 与 [CONFIG-IGNORED] 汇总（FTTH_STRICT_CONFIG 语义不变）。
        _all_known_cache = []

        def _all_known():
            """本工具链**全部**已知参数名（下划线形式）。惰性构建并缓存。

            两条来源缺一不可：
              ① ftth.py 各子命令的参数；
              ② 同目录下**不经 ftth.py 调度**的独立脚本（extract_fx_map.py /
                 ledger_*.py / read_titleblock_households.py 等）的参数 —— 它们同样会
                 被 probe 写进 suggested_params。实测 bldg_pattern / proximity_tol 属
                 extract_fx_map.py，只收 ① 会把这两个合法键误报成「疑似拼写错误」。
            """
            if _all_known_cache:
                return _all_known_cache[0]
            _ks = set()
            for _act in ap._actions:                       # ① 调度层子命令
                if not isinstance(_act, argparse._SubParsersAction):
                    continue
                for _sp in _act.choices.values():
                    for _sa in _sp._actions:
                        for _nm in (_sa.option_strings or []):
                            if _nm.startswith("--"):
                                _ks.add(_nm[2:].replace("-", "_"))
            try:                                           # ② 独立脚本（扫源码）
                for _f in sorted(Path(__file__).parent.glob("*.py")):
                    try:
                        _txt = _f.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        continue
                    for _m in re.finditer(
                            r'add_argument\(\s*"(--[A-Za-z0-9][A-Za-z0-9_-]*)"', _txt):
                        _ks.add(_m.group(1)[2:].replace("-", "_"))
            except Exception:
                pass
            _all_known_cache.append(_ks)
            return _ks

        _skip_cfg = []
        # config key → 子命令参数名的别名映射（仅当原始 key 在当前子命令中无效时生效）
        # 2026-09-15 效率优化：count 子命令用 --fiber-pattern，但 probe 输出 cable_pattern
        CONFIG_KEY_ALIASES = {
            "cable_pattern": "fiber_pattern",  # count 子命令
        }
        _ignored_cfg = []
        for k, v in cfg.get("suggested_params", {}).items():
            # 跳过不应被 config 覆盖的键
            if k in ("cmd", "dxf", "out", "outdir", "config", "dxf_json"):
                continue
            # 统一用下划线形式的属性名
            k_norm = k.replace("-", "_")
            # 2026-09-17：以 _note 结尾的键是**提示性键**（probe 用来传达风险/说明，
            #   如 fx_pattern_note 携带串号风险提示），不是任何子命令的参数。它们恒存在于
            #   probe 产出的配置里，若落到下方的「无效键」分支，会 (a) 每次调用都刷 WARN
            #   淹没真告警，(b) 在 FTTH_STRICT_CONFIG=1 下把合法配置判成硬失败。
            #   故静默跳过，并以 [config-info] 原样透传其内容，保证提示不丢。
            if k_norm.endswith("_note"):
                if v:
                    print(f"[config-info] {k}: {v}")
                continue
            # 先看原始 key 是否有效；无效则尝试别名映射
            if k_norm in valid_keys:
                k_target = k_norm
            else:
                k_target = CONFIG_KEY_ALIASES.get(k_norm, k_norm)
            if k_target not in valid_keys:
                if k_norm in _all_known():
                    # 本工具链别的子命令要用、本命令不需要 —— 正常，不报 WARN
                    _skip_cfg.append(k)
                else:
                    _ignored_cfg.append(k)
                    print(f"[WARN] 配置文件中的键 {k!r} 不在本工具链任何子命令的参数中"
                          f"（疑似拼写错误），子命令 '{args.cmd}' 已忽略")
                continue
            if getattr(args, k_target, None) in (None, "", []):
                setattr(args, k_target, v)
        print(f"[config] 已加载配置: {args.config}")
        if _skip_cfg:
            print(f"[config-skip] {len(_skip_cfg)} 个键属其它子命令专用，"
                  f"命令 '{args.cmd}' 不需要（正常，非告警）："
                  + ", ".join(repr(k) for k in _skip_cfg))
        # 2026-09-17（R2 配置键自检）：被忽略的键此前只有一行混在输出里的 WARN，
        #   2026-09-16 全天实测 42 处 / 10 会话无一处被处理——proximity_tol 这类
        #   「必须实测、禁止默认值」的键被静默丢掉后按默认值跑，结果失真且 rc=0。
        #   这里用固定 token [CONFIG-IGNORED] 在输出里汇总重申（可 grep / 可计数）；
        #   设环境变量 FTTH_STRICT_CONFIG=1 时升级为硬失败（rc=3）。
        #   走环境变量而非 CLI 开关：build_cmd 会把新增参数转发给子脚本，造成污染。
        if _ignored_cfg:
            print(f"[CONFIG-IGNORED] {len(_ignored_cfg)} 个配置键对子命令 '{args.cmd}' 不生效："
                  + ", ".join(repr(k) for k in _ignored_cfg))
            print("[CONFIG-IGNORED] 被忽略的多为容差/正则类参数——忽略=回退默认值，结果可能静默失真。"
                  "请核对键名拼写，或从配置中删除该子命令用不到的键。")
            if os.environ.get("FTTH_STRICT_CONFIG", "").strip() not in ("", "0"):
                print("[CONFIG-IGNORED] FTTH_STRICT_CONFIG 已启用 → 按硬失败处理（rc=3）。")
                sys.exit(3)

    # 2026-09-16：输出目录兜底。子脚本历史上多数不建 --out 父目录，
    # 由本层（统一入口）先建好，保证「通过 ftth.py 调用」这条主路径不再因目录缺失失败。
    # 就地实现（不 import ftth_common），避免为建目录引入模块依赖。
    for _k in ("out", "json_out", "outdir"):
        _p = getattr(args, _k, None)
        if _p:
            _d = os.path.dirname(os.path.abspath(_p))
            if _d and not os.path.isdir(_d):
                try:
                    os.makedirs(_d, exist_ok=True)
                    print(f"[out] 已创建输出目录: {_d}")
                except OSError as _e:
                    ap.error(f"无法创建输出目录 {_d}: {_e}")

    # H3: 校验 --dxf 参数（gen / verify-truth / inspect / assemble / apply-ruling 子命令不需要）
    if args.cmd not in ("gen", "verify-truth", "inspect", "assemble", "apply-ruling",
                        "budget", "transitions", "new-run", "summary", "verify-answer") and not args.dxf:
        ap.error("--dxf 是必需参数（gen / verify-truth / inspect / assemble / apply-ruling / budget / transitions / new-run / summary / verify-answer 除外）")

    # H3.5: plan --project-dir 自动推断（2026-10-04 P1-E1）
    #   plan 手动直调漏传 --project-dir → intake_table=unknown 阻塞（三次实测复发）。
    #   pipeline 已透传；手动直调时从 --dxf 父目录自动推断。
    if args.cmd == "plan" and getattr(args, "project_dir", None) is None and getattr(args, "dxf", None):
        _inferred = os.path.dirname(os.path.abspath(args.dxf))
        args.project_dir = _inferred
        print(f"[param] --project-dir 未传，由 --dxf 路径推断 = {_inferred}")

    # 分发
    if args.cmd == "probe":
        cmd = [args.dxf, "--probe"]
        if args.out:
            cmd += [args.out]
        cmd += build_cmd(args, ("cmd", "dxf", "out", "config"))
        sys.exit(run_script("parse_dxf_structured.py", cmd))
    elif args.cmd == "plan":
        # verbose 是 store_true（默认 False 会被 build_cmd 转发成 "--verbose False"），排除后单独处理
        # 2026-09-16：--config 不再排除。文件头「参数填充优先级」第 2 条
        # （--config 传入 probe 输出的 suggested_params）在 plan 上此前落空 ——
        # plan_methods.py 当时也不接受 --config，直接后果是 probe 已探明的
        # text_layer / title_pattern 传不进画像，标题识别退化为通用兜底。
        cmd = build_cmd(args, ("cmd", "verbose"))
        if args.verbose:
            cmd += ["--verbose"]
        sys.exit(run_script("plan_methods.py", cmd))
    elif args.cmd == "parse":
        rc = check_profile_gate("parse", getattr(args, "profile", None))
        if rc:
            sys.exit(rc)
        cmd = [args.dxf]
        if args.out:
            cmd += [args.out]
        cmd += build_cmd(args, ("cmd", "dxf", "out", "config", "profile", "legacy_bldg_assign"))
        if args.legacy_bldg_assign:
            cmd += ["--legacy-bldg-assign"]
        sys.exit(run_script("parse_dxf_structured.py", cmd))
    elif args.cmd == "coverage":
        rc = check_profile_gate("coverage", getattr(args, "profile", None))
        if rc:
            sys.exit(rc)
        cmd = [args.dxf]
        if args.out:
            cmd += [args.out]
        cmd += build_cmd(args, ("cmd", "dxf", "out", "config", "profile"))
        sys.exit(run_script("analyze_coverage.py", cmd))
    elif args.cmd == "coverage-vshape":
        rc = check_profile_gate("coverage-vshape", getattr(args, "profile", None))
        if rc:
            sys.exit(rc)
        cmd = [args.dxf]
        if args.out:
            cmd += [args.out]
        # include_basement 是 store_true，默认 False，且 build_cmd 会跳过 None——
        # False 不是 None，会被转发为 "--include-basement False"，故排除后单独处理
        cmd += build_cmd(args, ("cmd", "dxf", "out", "config", "profile", "include_basement"))
        if args.include_basement:
            cmd += ["--include-basement"]
        sys.exit(run_script("analyze_coverage_vshape.py", cmd))
    elif args.cmd == "count":
        cmd = [args.dxf]
        if args.out:
            cmd += [args.out]
        cmd += build_cmd(args, ("cmd", "dxf", "out", "config", "profile"))
        sys.exit(run_script("count_households.py", cmd))
    elif args.cmd in ("count-box", "count-hdd"):
        cmd = [args.dxf]
        if args.out:
            cmd += [args.out]
        # include_square 是 store_true（默认 False 会被 build_cmd 转发成 "--include-square False"），
        # 排除后单独处理
        cmd += build_cmd(args, ("cmd", "dxf", "out", "config", "include_square", "profile"))
        if args.include_square:
            cmd += ["--include-square"]
        sys.exit(run_script("count_box_icons.py", cmd))
    elif args.cmd == "gen":
        cmd = ["--dxf-json", args.dxf_json, "--out", args.out]
        cmd += build_cmd(args, ("cmd", "dxf_json", "out", "config", "dxf"))
        sys.exit(run_script("gen_addressbook.py", cmd))
    elif args.cmd == "assemble":
        cmd = build_cmd(args, ("cmd", "dxf", "config"))
        sys.exit(run_script("assemble_households.py", cmd))
    elif args.cmd == "verify-truth":
        cmd = [args.xlsx, args.covjson]
        cmd += build_cmd(args, ("cmd", "xlsx", "covjson", "config", "dxf"))
        sys.exit(run_script("verify_coverage_truth.py", cmd))
    elif args.cmd == "split-band":
        # --band 是列表：build_cmd 会把列表逗号拼接为单个 --band 值，split_bands.py 两种形态都收。
        # --config 需透传（--auto 要从其中读 text_layer / title_pattern 建议值）。
        cmd = [args.dxf]
        cmd += build_cmd(args, ("cmd", "dxf"))
        sys.exit(run_script("split_bands.py", cmd))
    elif args.cmd == "inspect":
        cmd = ["--parse", args.parse_json]
        if args.coverage_json:
            cmd += ["--coverage", args.coverage_json]
        if args.geom_json:
            cmd += ["--geom", args.geom_json]
        if args.count_box_json:
            cmd += ["--count-box", args.count_box_json]
        if args.fx_pattern:
            cmd += ["--fx-pattern", args.fx_pattern]
        if getattr(args, "titleblock_json", None):
            cmd += ["--titleblock", args.titleblock_json]
        if getattr(args, "fx_map_json", None):
            cmd += ["--fx-map", args.fx_map_json]
        if args.json_out:
            cmd += ["--json", args.json_out]
        sys.exit(run_script("inspect_closure.py", cmd))
    elif args.cmd == "pipeline":
        sys.exit(cmd_pipeline(args))
    elif args.cmd == "budget":
        # 阈值一律从 version.json 读，本命令不引入第二套口径。
        _c = []
        if args.json_out:
            _c += ["--json", args.json_out]
        sys.exit(run_script("check_budget.py", _c))
    elif args.cmd == "transitions":
        _c = ["--project-dir", args.project_dir]
        for _flag, _val in (("--project", args.project), ("--product", args.product),
                            ("--closure", args.closure), ("--json", args.json_out)):
            if _val:
                _c += [_flag, _val]
        sys.exit(run_script("check_transitions.py", _c))
    elif args.cmd == "apply-ruling":
        # 2026-09-18 修复（P0）：本子命令此前**只注册了参数、文档登记了入口，分发段却无
        #   对应分支** —— 走完 main() 自然返回，rc=0、零输出、**什么都没做**（静默空转）。
        #   它是「人工裁决批量落数」入口：照文档跑会以为裁决已落数，而产物根本没改
        #   —— 「登记了入口 != 接得上」的典型，故补齐。
        # 注意 --set：apply_ruling.py 是 `for s in args.set` 逐条解析「楼栋/单元/楼层=户数」，
        #   而 build_cmd 走 fmt_val 会把列表**拼成单参逗号串** → 楼栋名含逗号、解析失败。
        #   故此处显式逐条转发，**不复用 build_cmd**。
        _c = ["--json", args.json]
        if args.ruling:
            _c += ["--ruling", args.ruling]
        for _s in (getattr(args, "set", None) or []):
            _c += ["--set", _s]
        if args.out:
            _c += ["--out", args.out]
        if args.force:
            _c += ["--force"]
        if args.dry_run:
            _c += ["--dry-run"]
        sys.exit(run_script("apply_ruling.py", _c))
    elif args.cmd == "new-run":
        # 2026-10-04（P0-A2）：登记了入口就必须接得上派发分支（apply-ruling 的前车之鉴）
        sys.exit(cmd_new_run(args))
    elif args.cmd == "summary":
        sys.exit(cmd_summary(args))
    elif args.cmd == "verify-answer":
        sys.exit(cmd_verify_answer(args))


if __name__ == "__main__":
    main()
