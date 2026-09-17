#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTTH 多图批量编排入口（多张 DXF / 多地块场景）。

为什么需要它：多图任务里逐图手敲 probe/parse/coverage 极易造出一堆自造批量脚本，
且参数逐图复制易错。本脚本把「逐图 probe → parse → coverage → 合并 → 总览」
收拢为一个入口；**不改变 `ftth.py --dxf` 单值语义**（`--dxf` 改多值已被否决）。

用法一（快路径：所有图共用同一组参数）：

    ftth.cmd ftth_batch.py --dxf 图A.dxf --dxf 图B.dxf --out-dir batch_out ^
        --title-pattern "(\\d+)#.*?系统图" --text-layer 文字

    末尾透传参数与 ftth.py 子命令同名。脚本先跑 `ftth.py <子命令> --help`
    建立各步骤参数表，把每个透传参数**只转发给接受它的步骤**（如 `--vert-dx`
    只进 coverage），发现任何步骤都不接受的参数则**开工前报错**，避免整轮子调用作废。

用法二（清单模式：每图独立参数）：

    ftth.cmd ftth_batch.py --plan batch.json

    batch.json 结构（顶层键均可省略）：
    {
      "out_dir": "batch_out",                   // 默认输出根目录
      "common": {"--title-pattern": "..."},     // 注入每张图
      "items": [
        {"dxf": "C:/.../图A.dxf",               // 必填
         "name": "图A",                          // 可选，默认取文件名主干
         "out_dir": "batch_out/图A",             // 可选，默认 <out_dir>/<name>
         "common": {"--text-layer": "..."},      // 与顶层 common 深合并，图级优先
         "probe": {}, "parse": {}, "coverage": {},   // 仅该步骤追加的参数
         "skip_probe": false, "skip_coverage": false}
      ]
    }
    键写不写前导 `--` 均可；值为 true 表示纯开关，false/null 表示省略。

约定与退出码：

- 子进程解释器 = **当前解释器**（sys.executable，即启动器确认过带 ezdxf 的那个）；
  可用 --python 显式锁定。**全程不再裸调 python**。
- probe 成功的图，其输出 JSON 自动作为该图 parse/coverage 的 `--config`
  （透传里显式给了 --config 时不覆盖）。
- 单图/单步失败**不中断**批次；跑完后在 <out_dir> 写 `batch_overview.md`
  （人读总表）与 `batch_overview.json`（机读明细，含命令行与失败尾迹）。
- parse 成功数 >= 1 时自动调用 merge_json.py 合并为 `<批次名>_合并.json`
  （--no-merge 关闭）。
- 退出码：0=全部成功；1=部分失败；2=全部失败或前置错误（参数/清单/DXF 不存在）。
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
FTTH_PY = os.path.join(HERE, "ftth.py")
MERGE_PY = os.path.join(HERE, "merge_json.py")
STEPS_ALL = ("probe", "parse", "coverage")


class Batch(object):
    def __init__(self):
        self.log_fp = None
        self.config_wire = {}   # dxf -> probe 输出 JSON（自动 --config 串联）
        self.fail = 0           # 失败步数
        self.executed = 0       # 实际执行步数

    # ---------- 基础 ----------
    @staticmethod
    def err_exit(msg, example=None):
        """R2 风格报错：缺什么 + 一行可复制示例 + 契约指向。"""
        sys.stderr.write("[ftth_batch] 错误: %s\n" % msg)
        if example:
            sys.stderr.write("  示例: %s\n" % example)
        sys.stderr.write("  完整契约: references/scripts_reference.md §批量编排(ftth_batch.py)\n")
        sys.exit(2)

    def log(self, msg):
        line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
        print(line, flush=True)
        if self.log_fp:
            self.log_fp.write(line + "\n")
            self.log_fp.flush()

    # ---------- 参数路由 ----------
    @staticmethod
    def build_vocab(python):
        """跑 ftth.py <子命令> --help，收集各步骤接受的选项及是否带值。

        ftth.py 是调度层、顶部不 import ezdxf，--help 任何解释器可用。
        """
        vocab = {}
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        for sub in STEPS_ALL:
            r = subprocess.run([python, FTTH_PY, sub, "--help"],
                               capture_output=True, encoding="utf-8",
                               errors="replace", env=env, timeout=60)
            if r.returncode != 0:
                Batch.err_exit(
                    "无法获取 ftth.py %s 的参数表（rc=%d）\n%s"
                    % (sub, r.returncode, ((r.stderr or "") + (r.stdout or ""))[-800:]),
                    example='& "<技能目录>\\scripts\\ftth.cmd" %s --help' % sub)
            flags = {}
            # argparse 帮助形如 "--title-pattern TITLE_PATTERN"；store_true 无 metavar
            for m in re.finditer(r"(--[A-Za-z0-9][\w-]*)(?:\s+([A-Z][A-Z0-9_]*))?",
                                 r.stdout):
                flag = m.group(1)
                flags[flag] = flags.get(flag, False) or (m.group(2) is not None)
            vocab[sub] = flags
        return vocab

    @staticmethod
    def tokenize(argv):
        """透传 argv -> [(flag, value|None)]；value=None 表示纯开关或末尾缺值。"""
        pairs, i, n = [], 0, len(argv)
        while i < n:
            tok = argv[i]
            if not tok.startswith("--"):
                Batch.err_exit("无法识别的位置参数: %r（透传参数必须以 -- 开头）" % tok,
                               example="ftth.cmd ftth_batch.py --dxf 图A.dxf --text-layer 文字")
            if "=" in tok:
                f, v = tok.split("=", 1)
                pairs.append((f, v))
                i += 1
            elif i + 1 < n and not argv[i + 1].startswith("--"):
                pairs.append((tok, argv[i + 1]))
                i += 2
            else:
                pairs.append((tok, None))
                i += 1
        return pairs

    def route_params(self, pairs, vocab, source):
        """把 (flag, value) 路由到接受它的步骤；无人接受 => 开工前报错。"""
        routed = {s: [] for s in STEPS_ALL}
        for flag, value in pairs:
            if flag in ("--out", "--out-dir"):
                self.err_exit("透传参数含 %s —— 输出路径由 ftth_batch 统一管理，请删除"
                              % flag,
                              example="ftth.cmd ftth_batch.py --dxf 图A.dxf --out-dir batch_out")
            dest = [s for s in STEPS_ALL if flag in vocab[s]]
            if not dest:
                self.err_exit("透传参数 %s（来自%s）不被 probe/parse/coverage 任何"
                              "子命令接受（拼写错误？）" % (flag, source),
                              example="ftth.cmd ftth.py parse --help  # 查看合法参数")
            if len(dest) < len(STEPS_ALL):
                self.log("  参数路由(%s): %s -> %s" % (source, flag, "/".join(dest)))
            for s in dest:
                routed[s].append(flag)
                if value is not None:
                    routed[s].append(value)
        return routed

    @staticmethod
    def dict_pairs(d, source):
        out = []
        for k, v in (d or {}).items():
            f = str(k).strip()
            if not f.startswith("--"):
                f = "--" + f
            if v is True:
                out.append((f, None))
            elif v is False or v is None:
                continue
            else:
                out.append((f, str(v)))
        return out

    # ---------- 执行 ----------
    def run_step(self, python, step, dxf, extra_pairs, out_json, timeout, env):
        cmd = [python, FTTH_PY, step, "--dxf", dxf]
        cmd += extra_pairs
        if "--config" not in cmd and step in ("parse", "coverage") \
                and self.config_wire.get(dxf):
            cmd += ["--config", self.config_wire[dxf]]
        cmd += ["--out", out_json]
        t0 = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, encoding="utf-8",
                               errors="replace", env=env, timeout=timeout)
            tail = ((r.stdout or "") + "\n" + (r.stderr or ""))[-2000:]
            return {"rc": r.returncode, "cmd": cmd,
                    "sec": round(time.time() - t0, 1), "out": out_json,
                    "tail": tail if r.returncode != 0 else ""}
        except subprocess.TimeoutExpired:
            return {"rc": 124, "cmd": cmd, "sec": round(time.time() - t0, 1),
                    "out": out_json, "tail": "TIMEOUT %ss" % timeout}

    @staticmethod
    def parse_stats(data):
        """parse JSON -> 楼栋/单元/楼层记录/分纤箱/户数合计（口径同 merge_json）。"""
        b = data.get("楼栋", {}) if isinstance(data, dict) else {}
        n_u = n_f = n_x = n_h = 0
        for bd in b.values():
            if not isinstance(bd, dict):
                continue
            units = bd.get("单元", {}) or {}
            n_u += len(units)
            for ud in units.values():
                if not isinstance(ud, dict):
                    continue
                ft = ud.get("楼层表", {}) or {}
                n_f += len(ft)
                for info in ft.values():
                    if isinstance(info, dict):
                        v = info.get("户数")
                        if isinstance(v, (int, float)):
                            n_h += int(v)
                    elif isinstance(info, (int, float)):
                        n_h += int(info)
                n_x += len(ud.get("分纤箱", []) or [])
        return {"楼栋": len(b), "单元": n_u, "楼层记录": n_f,
                "分纤箱": n_x, "户数合计": n_h}

    def write_overview(self, out_dir, batch_name, rows, planned=False):
        ov_json = os.path.join(out_dir, "batch_overview.json")
        ov_md = os.path.join(out_dir, "batch_overview.md")
        detail = {"batch": batch_name, "planned": planned,
                  "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                  "items": rows}
        with open(ov_json, "w", encoding="utf-8") as f:
            json.dump(detail, f, ensure_ascii=False, indent=2)
        lines = ["# FTTH 批量总览：%s" % batch_name, "",
                 "- 生成时间：%s%s" % (detail["generated_at"],
                                      "（**dry-run 计划，未实际执行**）" if planned else ""),
                 "",
                 "| 图 | probe | parse | coverage | 楼栋 | 单元 | 楼层记录 | 分纤箱 |"
                 " 户数合计 | 备注 |",
                 "|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            def cell(step):
                st = r["steps"].get(step)
                if st is None:
                    return "SKIP"
                if planned:
                    return "PLAN"
                return ("OK(%ss)" % st["sec"] if st["rc"] == 0
                        else "FAIL(rc=%s)" % st["rc"])
            s = r.get("stats") or {}
            lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                r["name"], cell("probe"), cell("parse"), cell("coverage"),
                s.get("楼栋", "-"), s.get("单元", "-"), s.get("楼层记录", "-"),
                s.get("分纤箱", "-"), s.get("户数合计", "-"),
                (r.get("note") or "")[:80]))
        if not planned:
            lines += ["", "失败步骤数：%d（明细见 batch_overview.json 的 tail 字段）"
                      % self.fail]
        with open(ov_md, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return ov_md

    # ---------- 主流程 ----------
    def run(self, argv):
        ap = argparse.ArgumentParser(
            description="FTTH 多图批量编排（probe→parse→coverage→合并→总览）",
            allow_abbrev=False)  # 禁前缀匹配：--out 不能被吞成 --out-dir，必须落入透传被拦截
        ap.add_argument("--plan", help="批次清单 JSON（清单模式）")
        ap.add_argument("--dxf", action="append", default=None,
                        help="DXF 路径，可重复（快路径；与 --plan 二选一）")
        ap.add_argument("--out-dir", default="ftth_batch_out", help="输出根目录")
        ap.add_argument("--name", default=None, help="批次名（默认按来源命名）")
        ap.add_argument("--steps", default="probe,parse,coverage",
                        help="要跑的步骤，逗号分隔（默认全部）")
        ap.add_argument("--python", default=sys.executable,
                        help="子进程解释器（默认当前解释器，一般不用传）")
        ap.add_argument("--timeout-sec", type=int, default=3600, help="单步超时秒数")
        ap.add_argument("--skip-existing", action="store_true",
                        help="输出 JSON 已存在且可解析时跳过（断点续跑）")
        ap.add_argument("--no-merge", action="store_true",
                        help="不调用 merge_json.py 合并")
        ap.add_argument("--dry-run", action="store_true",
                        help="只打印将执行的命令并写计划总览，不实际执行")
        args, passthrough = ap.parse_known_args(argv)

        if not args.plan and not args.dxf:
            self.err_exit("需要 --plan <batch.json> 或至少一个 --dxf <图纸.dxf>",
                          example='& "<技能目录>\\scripts\\ftth.cmd" ftth_batch.py '
                                  "--dxf 图A.dxf --dxf 图B.dxf --out-dir batch_out")
        if args.plan and args.dxf:
            self.err_exit("--plan 与 --dxf 互斥，请二选一")
        steps = [s.strip() for s in args.steps.split(",") if s.strip()]
        bad = [s for s in steps if s not in STEPS_ALL]
        if bad:
            self.err_exit("--steps 含非法步骤: %s（合法: %s）"
                          % (",".join(bad), "/".join(STEPS_ALL)))

        # ---- 组装 items ----
        if args.plan:
            try:
                with open(args.plan, "r", encoding="utf-8") as f:
                    plan = json.load(f)
            except (IOError, json.JSONDecodeError) as e:
                self.err_exit("无法读取清单 %s: %s" % (args.plan, e))
            top_dir = plan.get("out_dir") or args.out_dir
            top_common = plan.get("common") or {}
            items = []
            for it in plan.get("items", []):
                d = dict(it)
                if not d.get("dxf"):
                    self.err_exit("清单 item 缺 dxf 字段: %r" % d.get("name"))
                stem = os.path.splitext(os.path.basename(d["dxf"]))[0]
                d.setdefault("name", stem)
                d.setdefault("out_dir", os.path.join(top_dir, d["name"]))
                merged_common = dict(top_common)
                merged_common.update(d.get("common") or {})
                d["common"] = merged_common
                items.append(d)
            if not items:
                self.err_exit("清单里 items 为空")
            batch_name = args.name or ("plan_" + os.path.splitext(
                os.path.basename(args.plan))[0])
        else:
            items = []
            for dxf in args.dxf:
                stem = os.path.splitext(os.path.basename(dxf))[0]
                items.append({"dxf": dxf, "name": stem,
                              "out_dir": os.path.join(args.out_dir, stem),
                              "common": {}})
            top_dir = args.out_dir
            batch_name = args.name or ("cli_%d图" % len(items))
        batch_name = re.sub(r'[\\/:*?"<>|]', "_", batch_name)

        for it in items:
            if not os.path.isfile(it["dxf"]):
                self.err_exit("DXF 不存在: %s" % it["dxf"])

        os.makedirs(top_dir, exist_ok=True)
        self.log_fp = open(os.path.join(top_dir, "ftth_batch.log"), "a",
                           encoding="utf-8")
        self.log("批次=%s  图数=%d  步骤=%s%s  解释器=%s"
                 % (batch_name, len(items), "/".join(steps),
                    "  [DRY-RUN]" if args.dry_run else "", args.python))

        # ---- 参数表 + 路由（开工前完成，防整轮作废）----
        vocab = self.build_vocab(args.python)
        cli_routed = self.route_params(self.tokenize(passthrough), vocab, "命令行")
        env = dict(os.environ, PYTHONIOENCODING="utf-8")

        rows, used_names = [], {}
        for it in items:
            name = it["name"]
            if name in used_names:
                used_names[name] += 1
                name = "%s_%d" % (name, used_names[name])
            else:
                used_names[name] = 1
            it_out = it.get("out_dir") or os.path.join(top_dir, name)
            os.makedirs(it_out, exist_ok=True)
            item_routed = self.route_params(
                self.dict_pairs(it.get("common"), name), vocab, name) \
                if it.get("common") else {s: [] for s in STEPS_ALL}
            row = {"name": name, "dxf": it["dxf"], "out_dir": it_out, "steps": {}}
            self.log("── %s ── %s" % (name, it["dxf"]))

            for step in STEPS_ALL:
                if step not in steps:
                    continue
                if it.get("skip_probe") and step == "probe":
                    self.log("  %s: SKIP(skip_probe)" % step)
                    continue
                if it.get("skip_coverage") and step == "coverage":
                    self.log("  %s: SKIP(skip_coverage)" % step)
                    continue
                out_json = os.path.join(it_out, "%s_%s.json" % (name, step))
                if args.skip_existing and os.path.isfile(out_json):
                    try:
                        with open(out_json, "r", encoding="utf-8") as f:
                            json.load(f)
                        row["steps"][step] = {"rc": 0, "cmd": ["<skip-existing>"],
                                              "sec": 0, "out": out_json, "tail": ""}
                        self.log("  %s: SKIP(已存在)" % step)
                        continue
                    except (IOError, json.JSONDecodeError):
                        self.log("  %s: 已存在但不可解析，重跑" % step)
                step_pairs = self.dict_pairs(it.get(step) or {},
                                             "%s/%s" % (name, step))
                extra = cli_routed[step] + item_routed[step]
                for p_flag, p_val in step_pairs:
                    extra.append(p_flag)
                    if p_val is not None:
                        extra.append(p_val)
                if args.dry_run:
                    cmd = [args.python, FTTH_PY, step, "--dxf", it["dxf"]] + \
                        extra + ["--out", out_json]
                    row["steps"][step] = {"rc": 0, "cmd": cmd, "sec": 0,
                                          "out": out_json, "tail": ""}
                    self.log("  %s: PLAN  %s" % (step, subprocess.list2cmdline(cmd)))
                    continue
                self.executed += 1
                st = self.run_step(args.python, step, it["dxf"], extra, out_json,
                                   args.timeout_sec, env)
                row["steps"][step] = st
                self.log("  %s: %s (rc=%d, %ss)"
                         % (step, "OK" if st["rc"] == 0 else "FAIL", st["rc"],
                            st["sec"]))
                if st["rc"] != 0:
                    self.fail += 1
                    sys.stderr.write(st["tail"] + "\n")
                else:
                    if step == "probe":
                        self.config_wire[it["dxf"]] = st["out"]
                    if step == "parse":
                        try:
                            with open(st["out"], "r", encoding="utf-8") as f:
                                row["stats"] = self.parse_stats(json.load(f))
                        except (IOError, json.JSONDecodeError):
                            pass
            rows.append(row)

        # ---- 合并 ----
        parses = [r["steps"]["parse"]["out"] for r in rows
                  if r["steps"].get("parse", {}).get("rc") == 0
                  and os.path.isfile(r["steps"]["parse"]["out"])]
        if parses and not args.no_merge:
            merged = os.path.join(top_dir, "%s_合并.json" % batch_name)
            mcmd = [args.python, MERGE_PY, "--inputs"] + parses + ["--out", merged]
            if args.dry_run:
                self.log("merge: PLAN  %s" % subprocess.list2cmdline(mcmd))
            else:
                self.executed += 1
                try:
                    r = subprocess.run(mcmd, capture_output=True,
                                       encoding="utf-8", errors="replace",
                                       env=env, timeout=args.timeout_sec)
                    self.log("merge: %s (rc=%d) -> %s"
                             % ("OK" if r.returncode == 0 else "FAIL",
                                r.returncode, merged))
                    if r.returncode != 0:
                        self.fail += 1
                        sys.stderr.write(((r.stdout or "") + (r.stderr or ""))
                                         [-1500:] + "\n")
                except subprocess.TimeoutExpired:
                    self.fail += 1
                    self.log("merge: TIMEOUT")

        ov_md = self.write_overview(top_dir, batch_name, rows,
                                    planned=args.dry_run)
        self.log("总览: %s" % ov_md)
        if self.log_fp:
            self.log_fp.close()
        if args.dry_run:
            return 0
        if self.fail == 0:
            return 0
        return 1 if self.fail < self.executed else 2


if __name__ == "__main__":
    sys.exit(Batch().run(sys.argv[1:]))
