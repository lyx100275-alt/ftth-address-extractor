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

# 几何阈值默认值已全部下沉到各子脚本（层高自适应）；本调度层不转发未指定的参数，
# 子脚本的 0/None=auto 约定才不会被绝对值覆盖（2026-09-15 通用化）。

sys.stdout.reconfigure(encoding="utf-8")


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
        "ftth.py gen --parse \"<parse.json>\" --coverage \"<coverage.json>\" --template \"<模板.xlsx>\" --out \"<标准地址表.xlsx>\"",
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
#   经 ftth.cmd 逐条调用时，**每条命令**都要固定付一份启动开销 ——
#     探测 `python -c "import ezdxf"` 1.93s + _launch.py 1.13s + ftth.py 0.65s ≈ 3.7s。
#   实测某图 12 次调用共 66.05s，其中约 43s 是这层开销，真正算数只占小头。
#   本命令只起一次调度进程，各阶段以子进程直调 ftth.py（不再经 ftth.cmd / _launch.py），
#   该固定开销只付一次。
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
_PIPE_STAGES = ("geom", "probe", "plan", "titleblock", "fxmap", "fx_locations",
                "unit_gaps", "parse", "coverage", "inspect")
# 2026-09-18（用户裁定）新增 `unit_gaps`：探查期「单元 × 箱清单」交叉清点，位置在
#   parse **之前** —— 骨架(titleblock)与箱清单(fxmap/fx_locations)两样证据在 parse 前
#   就已落盘，故「某单元没分纤箱」可提前暴露，不必等 Step 2 覆盖门禁（那时返工面大）。

# 画像里申报的覆盖判定脚本 -> 本入口的子命令名
_COV_SCRIPT_TO_CMD = {
    "analyze_coverage_vshape.py": "coverage-vshape",
    "analyze_coverage.py": "coverage",
}


def _pipe_coverage_choice(profile_path):
    """从画像读出覆盖判定选中的脚本，映射为本入口子命令名。

    返回 (子命令名 或 None, 说明文本)。None 表示两者之一：
      ① 画像不可读（须显式暴露，不得静默挑一个方法）；
      ② 画像申报本图不提供覆盖范围数据（absent）—— 该阶段合法缺席。
    """
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            prof = json.load(f)
    except Exception as e:
        return None, "画像不可读: %s" % e
    sel = (((prof.get("handoff") or {}).get("②系统图选法") or {}).get("覆盖范围") or {})
    decl = str(sel.get("申报") or sel.get("状态") or "").strip().lower()
    if decl in ("absent", "missing", "none"):
        return None, "画像申报本图不提供覆盖范围数据(%s) -> 该阶段合法缺席" % decl
    cmd = _COV_SCRIPT_TO_CMD.get(sel.get("脚本"))
    if cmd:
        return cmd, "%s <- %s" % (sel.get("选定方法") or cmd, sel.get("脚本"))
    return None, "画像未给出可识别的覆盖判定脚本(脚本=%r)" % sel.get("脚本")


def _pipe_effective_layers(profile_path):
    """从画像读出**机器可读**的图层建议，返回 (dict, 来源说明)。

    优先读 `effective_layers`（2026-09-18 起由 plan 产出，值为纯层名或 null）。
    老画像没有该字段时回退读 `param_source.must_probe`，但**必须过滤提示语** ——
    该字段历史上把「值」和「提示文案」混排（无候选时写的是整句中文说明），
    直接当参数传会把中文句子送进脚本。读不到一律返回空 dict：不猜。
    """
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            prof = json.load(f)
    except Exception:                                                # noqa: BLE001
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
    except Exception:                                                # noqa: BLE001
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
    except Exception:                                                # noqa: BLE001
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
    except Exception:                                                # noqa: BLE001
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
    geom_json = dxf + ".geom.json"
    cfg = os.path.join(outdir, "config.json")
    prof = args.profile or os.path.join(outdir, "profile.json")
    parsed = os.path.join(outdir, "parsed.json")
    cov = os.path.join(outdir, "coverage.json")
    insp = os.path.join(outdir, "inspect.json")
    stop_idx = _PIPE_STAGES.index(args.stop_at or "inspect")

    ledger = []
    t_all = time.time()

    def _sink(stage):
        return os.path.join(logdir, "%s.log" % stage) if args.quiet else None

    def _run(stage, argv, script=None):
        """起一个子进程；--quiet 时输出落 logs/<stage>.log，否则透传。"""
        t0 = time.time()
        if script:
            cmd = [sys.executable, str(Path(__file__).parent / script)] + argv
        else:
            cmd = [sys.executable, self_py] + argv
        sink = _sink(stage)
        if sink:
            os.makedirs(logdir, exist_ok=True)
            with open(sink, "w", encoding="utf-8", newline="\n") as f:
                rc = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT)
        else:
            rc = subprocess.call(cmd)
        el = time.time() - t0
        ledger.append({"阶段": stage, "rc": rc, "秒": round(el, 2)})
        print("[pipeline] %-9s rc=%-2s %7.2fs" % (stage, rc, el), flush=True)
        return rc

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
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"dxf": dxf, "outdir": outdir, "total_sec": round(total, 2),
                       "stages": ledger}, f, ensure_ascii=False, indent=1)
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
    if stop_idx < 3:
        return _dump(0)

    # ---- ③b titleblock（图签第二来源；仅画像申报 present / variant 时跑）----
    # 2026-09-18（实跑修复，P1）：画像把 titleblock_annotation 判为 present 并明确写出
    #   「后果与处置：图签可直读栋级入户规模 → 与采集表构成『三来源协议』的第二来源」，
    #   但流水线的阶段列表里**根本没有它** —— 规则写在文档里、没有代码执行，
    #   第二来源永不参与，实测某图 7 栋的图签读数与系统图逐栋一致却从未被比对过。
    #   本阶段只**读取并落盘**（<outdir>/titleblock.json），比对交给 inspect 的 C10。
    #   非 0 退出**不中止主链路**（它是校验来源，不是主数据来源），但必须显式打印，
    #   并让 C10 判 SKIP —— 「没核」不得呈现成「通过」。
    tb = os.path.join(outdir, "titleblock.json")
    _tb_state = _pipe_profile_status(prof, "titleblock_annotation")
    if _tb_state not in ("present", "variant"):
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
            ledger.append({"阶段": "titleblock", "rc": 3, "秒": 0.0})
            print("[pipeline] titleblock 跳过：配置里既无 titleblock_layer_candidates 也无 "
                  "suggested_params.text_layer，不猜图层；C10 将判 SKIP 并注明本次未做交叉校验",
                  flush=True)
        else:
            _rc_tb = _run("titleblock",
                          ["--dxf", dxf, "--floor-layer", _tbl, "--out", tb],
                          script="read_titleblock_households.py")
            if _rc_tb == 3:
                # 2026-09-18（实跑修复）：rc=3 = 本图未提供图签形态（申报制语义），
                #   不是脚本故障。此前一律按 `!` 告警打印，把「图上没有」写成
                #   「第二来源未取得」，且掩盖了它与真失败的区别。
                print("[pipeline] titleblock rc=3 = 本图未提供图签形态的成对标注"
                      "（申报制），第二来源本次不参与；C10 将判 SKIP 并注明「本次未做」",
                      flush=True)
            elif _rc_tb:
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
    # 2026-09-18（第 3 轮）：判据从「画像申报有集中总图」改为「**有 FX 编号可提**」。
    #   原 gate 把 7/8 个分带整段跳过（这些图的箱编号嵌在各楼系统图箱表内，
    #   fx_overview_map=absent，但 handoff① 明写编号可读/编号数），后果是 parse 侧
    #   箱归属全空、rc 仍 0 —— 静默丢数。详见 _pipe_fxmap_gate 的说明。
    _fx_run, _fx_note = _pipe_fxmap_gate(prof)
    if _fx_run:
        print("[pipeline] fxmap 依据：%s" % _fx_note, flush=True)
        _rc_fx = _run("fxmap", [dxf, fxmap, "--config", cfg], script="extract_fx_map.py")
        if _rc_fx and not os.path.isfile(fxmap):
            print("[pipeline] ! fxmap 阶段失败(rc=%d) —— parse/coverage 无总图对照表，"
                  "楼栋归属回退『标题 x 中分』（仅供线索）" % _rc_fx, flush=True)
    else:
        ledger.append({"阶段": "fxmap", "rc": 3, "秒": 0.0})
        print("[pipeline] %-9s rc=3      0.00s  (%s，跳过)" % ("fxmap", _fx_note),
              flush=True)
    # 用户显式 --bldg-map 优先（人工确认过总图对照表，属「图上标注直读」来源）；
    # 否则仅当 fxmap 阶段**因 present 实际产出**时才用（_fx_run 控制产出）。
    # 2026-09-18（第 4 轮，用户裁决）：absent 图不再产出 fxmap —— gate 未跑则文件
    # 不存在，_bmap 自然为 None；不自动把「旧残留/降级产物」当作对照表回填。
    _bmap = args.bldg_map or (fxmap if (_fx_run and os.path.isfile(fxmap)) else None)
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
    _fxl_state = _pipe_fxloc_state(prof, cfg)
    if not _fxl_state.startswith("present"):
        ledger.append({"阶段": "fx_locations", "rc": 3, "秒": 0.0})
        print("[pipeline] %-9s rc=3      0.00s  (探查申报 fx_location_annotation=%s，跳过)"
              % ("fx_locations", _fxl_state or "未知"), flush=True)
    else:
        _rc_fxl = _run("fx_locations", ["--dxf", dxf, "--out", fxl],
                       script="extract_fx_locations.py")
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
    for _uflag, _upath in (("--titleblock", tb), ("--fx-locations", fxl), ("--fx-map", fxmap)):
        if os.path.isfile(_upath):
            ug_argv += [_uflag, _upath]
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
    if _bmap:
        # 硬约束② 的落地：有总图对照表时，箱的楼栋/单元归属以它为准（不再按标题 x 中分）。
        # --fx-map 仍只做「缺失安装楼层回填」，不覆盖 parse 实测值。
        parse_argv += ["--bldg-map", _bmap, "--fx-map", _bmap]
    rc = _run("parse", parse_argv)
    if rc:
        return _dump(_std_json_gate(rc), "parse")
    if stop_idx < 8:
        return _dump(0)

    # ---- ⑥ coverage（方法由画像决定，不在此处二次推断）----
    cov_cmd, cov_note = _pipe_coverage_choice(prof)
    print("[pipeline] 覆盖判定选法: %s" % cov_note, flush=True)
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
        if cov_cmd == "coverage-vshape" and os.path.isfile(fxl):
            cov_argv += ["--fx-locations", fxl]
            print("[pipeline] 箱位直读标注已接入 V 型法交叉校验: %s" % fxl, flush=True)
        elif cov_cmd == "coverage-vshape":
            print("[pipeline] 提示：本次无箱位直读标注(<outdir>/fx_locations.json)，"
                  "V 型法安装层缺独立第二来源，结论须照此标注", flush=True)
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
        if rc == 3:
            print("[pipeline] coverage rc=3 = 本图不适用（申报制），按降级路径继续", flush=True)
        elif rc:
            return _dump(_std_json_gate(rc), "coverage")
    if stop_idx < 9:
        return _dump(0)

    # ---- ⑦ inspect ----
    insp_argv = ["inspect", "--parse", parsed, "--geom", geom_json, "--json", insp]
    if os.path.isfile(cov):
        insp_argv += ["--coverage", cov]
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
    if os.path.isfile(tb):
        insp_argv += ["--titleblock", tb]
    # 2026-09-18（实跑修复，P1）：户数（图标法）产物若已落在 outdir，自动喂给 inspect。
    #   此前本阶段不接该产物 ⇒ C5/C8 恒判 SKIP；即便使用者随后单独跑了 count-box，
    #   只要不手工重拼 inspect 命令就**永远看不出来** —— 「跑了但没核」会被读成
    #   「核过且通过」，是本技能最忌讳的假绿灯形态。自动纳入可消除这一手工接续点。
    _cb_path = os.path.join(outdir, "count_box.json")
    if os.path.isfile(_cb_path):
        insp_argv += ["--count-box", _cb_path]
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
    p_parse.add_argument("--cable-keywords", default=None, help="光缆识别关键词正则")
    p_parse.add_argument("--unit-cluster", type=float, default=None, help="留空=子脚本按层高自适应")
    p_parse.add_argument("--unit-range", type=float, default=None, help="留空=子脚本按层高自适应")
    p_parse.add_argument("--y-tol", type=float, default=None, help="留空=子脚本按层高自适应")
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
                        "budget", "transitions") and not args.dxf:
        ap.error("--dxf 是必需参数（gen / verify-truth / inspect / assemble / apply-ruling / budget / transitions 除外）")

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


if __name__ == "__main__":
    main()
