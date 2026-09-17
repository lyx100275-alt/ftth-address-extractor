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
_PIPE_STAGES = ("geom", "probe", "plan", "fxmap", "parse", "coverage", "inspect")

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

    def _dump(rc):
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
        elif rc == 3:
            print("[pipeline] 有阶段 rc=3 = 本图不适用（非错误），按画像降级路径继续")
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
            return _dump(rc)
    if stop_idx < 1:
        return _dump(0)

    # ---- ② probe ----
    rc = _run("probe", ["probe", "--dxf", dxf, "--out", cfg])
    if rc:
        return _dump(rc)
    if stop_idx < 2:
        return _dump(0)

    # ---- ③ plan（--project-dir 不传会让 intake_table 留 unknown，故显式透传）----
    plan_argv = ["plan", "--dxf", dxf, "--probe", cfg, "--config", cfg, "--out", prof]
    if args.project_dir:
        plan_argv += ["--project-dir", args.project_dir]
    rc = _run("plan", plan_argv)
    if rc:
        return _dump(rc)
    if stop_idx < 3:
        return _dump(0)

    # ---- ④ fxmap（总图对照表；仅画像申报存在总图时跑，失败不中止）----
    # 2026-09-18 整改①：此前这一环完全缺失 —— 画像 handoff 写着「下游：extract_fx_map.py」，
    #   但流水线不接续。实测某图总图对照表位于独立图区（x 与楼栋系统图不重叠），
    #   parse 按楼栋 x 范围归属 → 每栋 0 箱，而没有任何环节提示必须先提对照表。
    # 2026-09-18 整改②（第 2 轮）：顺序再修正 —— 对照表必须在 **parse 之前**产出，
    #   依据 SKILL.md 硬约束②：楼栋/单元归属必须以对照表为准，parse 自身同样受此约束。
    fxmap = os.path.join(outdir, "fxmap.json")
    if _pipe_profile_status(prof, "fx_overview_map") == "present":
        _rc_fx = _run("fxmap", [dxf, fxmap, "--config", cfg], script="extract_fx_map.py")
        if _rc_fx and not os.path.isfile(fxmap):
            print("[pipeline] ! fxmap 阶段失败(rc=%d) —— parse/coverage 无总图对照表，"
                  "楼栋归属回退『标题 x 中分』（仅供线索）" % _rc_fx, flush=True)
    else:
        ledger.append({"阶段": "fxmap", "rc": 3, "秒": 0.0})
        print("[pipeline] %-9s rc=3      0.00s  (画像未申报总图对照表，跳过)" % "fxmap",
              flush=True)
    # 用户显式 --bldg-map 优先；否则用本阶段落盘的 fxmap.json（同一份总图对照表）。
    # 该变量在下游 parse/coverage 两处复用 —— 一份对照表、两处同源，避免各取各的。
    _bmap = args.bldg_map or (fxmap if os.path.isfile(fxmap) else None)
    if stop_idx < 4:
        return _dump(0)

    # ---- ⑤ parse ----
    parse_argv = ["parse", "--dxf", dxf, "--config", cfg,
                  "--profile", prof, "--out", parsed]
    if _bmap:
        # 硬约束② 的落地：有总图对照表时，箱的楼栋/单元归属以它为准（不再按标题 x 中分）。
        # --fx-map 仍只做「缺失安装楼层回填」，不覆盖 parse 实测值。
        parse_argv += ["--bldg-map", _bmap, "--fx-map", _bmap]
    rc = _run("parse", parse_argv)
    if rc:
        return _dump(rc)
    if stop_idx < 5:
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
        _lay, _lay_src = _pipe_effective_layers(prof)
        if args.wire_layer or _lay.get("wire_layer"):
            cov_argv += ["--wire-layer", args.wire_layer or _lay["wire_layer"]]
        if args.fx_symbol_layer or _lay.get("fx_symbol_layer"):
            cov_argv += ["--fx-symbol-layer", args.fx_symbol_layer or _lay["fx_symbol_layer"]]
        # _bmap 已在 fxmap 阶段解析（用户显式 --bldg-map 优先，否则用落盘的 fxmap.json）
        if _bmap:
            cov_argv += ["--bldg-map", _bmap]
        if _lay:
            print("[pipeline] 自画像下传图层(%s)：%s"
                  % (_lay_src, ", ".join("%s=%s" % (k, v) for k, v in _lay.items())),
                  flush=True)
        elif not (args.wire_layer or args.fx_symbol_layer):
            print("[pipeline] ! 画像未给出可用图层候选 —— coverage 将扫描全图所有图层，"
                  "结果仅供线索（用 --wire-layer/--fx-symbol-layer 显式指定可消除）", flush=True)
        if not _bmap:
            print("[pipeline] 提示：无总图对照表(<outdir>/fxmap.json)，"
                  "coverage 楼栋归属将回退『标题 x 中分』", flush=True)
        rc = _run("coverage", cov_argv)
        if rc == 3:
            print("[pipeline] coverage rc=3 = 本图不适用（申报制），按降级路径继续", flush=True)
        elif rc:
            return _dump(rc)
    if stop_idx < 6:
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
    return _dump(_run("inspect", insp_argv))


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
    p_sb.add_argument("--out-dir", required=True, help="子 DXF 输出目录（自动创建）")
    p_sb.add_argument("--band", action="append", required=True,
                      help='分带参数 "名称:ymin:ymax"，可重复传；单值内也可用逗号分隔多条。'
                           'y 带口径：上界取上邻带标题 y、下界维持中点（防切本带/吞邻带）')

    # pipeline: 一条命令串跑多阶段（2026-09-17 新增，见 cmd_pipeline 文档字符串）
    p_pipe = sub.add_parser("pipeline", parents=[common],
                            help="一键串跑 geom->probe->plan->parse->coverage->inspect"
                                 "（只解析、不出表；各阶段产物落 --outdir）")
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
    if args.cmd not in ("gen", "verify-truth", "inspect", "assemble", "apply-ruling") and not args.dxf:
        ap.error("--dxf 是必需参数（gen / verify-truth / inspect / assemble / apply-ruling 除外）")

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
        cmd += build_cmd(args, ("cmd", "dxf", "out", "config", "profile"))
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
        # --band 是列表：build_cmd 会把列表逗号拼接为单个 --band 值，split_bands.py 两种形态都收
        cmd = [args.dxf]
        cmd += build_cmd(args, ("cmd", "dxf", "config"))
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
        if args.json_out:
            cmd += ["--json", args.json_out]
        sys.exit(run_script("inspect_closure.py", cmd))
    elif args.cmd == "pipeline":
        sys.exit(cmd_pipeline(args))


if __name__ == "__main__":
    main()
