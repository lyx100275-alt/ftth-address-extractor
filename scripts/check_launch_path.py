#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调用链门禁（L1-C7）—— 核产物是不是经 `ftth_launcher.py` 派生的。

背景（这是 C7 从 declared 升到 enforced 的唯一途径）
---------------------------------------------------
L1-C7「调用契约」此前是本技能**唯一**没有机器检查器的契约 —— 缺口原文写在
`version.json` 的 `contract_coverage.C7.gap`：「业务脚本是否绕过 ftth_launcher.py
直调」是跨进程事实，而本技能所有门禁都跑在单脚本内，机器判不了。

解法不是「让门禁去追调用链」（做不到：门禁看不到父进程），而是**把调用链变成
产物上可见的事实**：

    ftth_launcher.py  →  设环境变量 FTTH_VIA_LAUNCHER=1 再 spawn 业务脚本
                       →  业务脚本的 ftth_common.write_json 见到该变量，
                          在产物顶层写 `_via_launcher: true`
                       →  本脚本读产物，缺该键 = 该产物未经启动器派生

这个设计的三条取舍：

1. **标记是布尔真值，不是时间戳/路径**。含变量的标记会让每次运行的产物 md5 都变，
   golden 回归（T14）将永久假红 —— 一个门禁不能毒化另一个门禁。
2. **只判「缺标记」，不判「标记为假」**。直接调 `python scripts/xxx.py`（宿主 PATH
   通常无 ezdxf）多数情况下根本跑不起来，所以缺标记的产物绝大多数是「裸调但恰好
   成功」这种真违规，判 FAIL 是安全的。
3. **豁免清单有出处**。列在 `_EXEMPT` 里的脚本要么刻意零依赖（禁 import
   ftth_common，否则循环），要么不是业务脚本。**豁免不是免责**，是「本门禁
   判不了它」——故在输出里逐条打印，不静默。

检查项
------
  K1 目录下无可核产物 → rc=3（早失败，「没核」不得输出成「通过」）
  K2 有产物但全部缺 `_via_launcher` → rc=2
  K3 部分缺、部分有 → rc=2 并点名缺哪些（混跑是最该报的状态：说明有绕过）
  K4 产物 JSON 损坏 → rc=2（读不出标记 ≠ 有标记）

退出码（沿用 L1-C2）
  0  全部产物均带标记（或本就不适用）
  2  有产物缺标记 —— 疑似绕过启动器直调
  3  早失败：目录不存在 / 无可核对象

用法：python scripts/check_launch_path.py <产物目录> [...]
"""
import io
import json
import os
import re
import sys

# 控制台 UTF-8 兜底（中文 Windows 默认 GBK，print CJK 即崩）。共享实现见
# ftth_common.ensure_console_utf8；本脚本刻意零依赖，故内联。
for _s in (sys.stdout, sys.stderr):
    try:
        _rec = getattr(_s, "reconfigure", None)
        if callable(_rec):
            _rec(encoding="utf-8", errors="replace")
    except Exception:
        pass

MARK = "_via_launcher"

# 与 check_contracts.PRODUCTS 同一批产物（唯一真源在 ftth_common，本处只列名）
PRODUCTS = ("parsed.json", "coverage.json", "count_box.json", "titleblock.json",
            "fxmap.json", "fx_locations.json", "unit_box_gaps.json",
            "assembly.json", "inspect.json", "count_households.json",
            "profile.json", "elements.json", "geom.json")

# 产物内「本轮生成」的形状特征（与各产出脚本实际写出的顶层键对齐）。
#   刻意**穷举实测过的键**而不是猜一个通用 schema：本门禁只回答「这个 JSON 是不是
#   业务产物」，判宽了会把 config.json 之类误算成产物（假红），判窄了会漏掉
#   某个产出（假绿）。每加一个产出脚本，此处须同步补一个键 —— 漏补的后果是
#   「该产物被当成非产物跳过」，故 run_smoke 有 T4e 用真图产物反查覆盖率。
_FRESH_KEYS = (
    "DXF文件",            # parse / coverage
    "楼栋",                # parse / coverage / titleblock
    "分纤箱",              # parse
    "列",                  # count_box
    "checks",              # inspect
    "generated_by",        # profile
    "两侧状态",            # unit_box_gaps
    "逐栋比对",            # titleblock
    "证据明细",            # unit_box_gaps
    "唯一箱位",            # fx_locations
    "楼层表",              # parse 的单元内层
    "fx_symbol_layer_candidates",   # config 侧（探查产物）
)


def _looks_fresh(obj):
    """该 JSON 是否像「本轮业务产物」（而非配置/说明/样例）。

    判据只做形状检查：产物必有上列某个顶层键。**不做内容正确性判断** ——
    本门禁只回答「这个产物是不是经启动器派生的」，不管它算得对不对。
    """
    return isinstance(obj, dict) and any(k in obj for k in _FRESH_KEYS)


def _out(msg):
    sys.stdout.write(msg + "\n")


def _err(msg):
    sys.stderr.write(msg + "\n")


def main(argv=None):
    dirs = [a for a in (argv if argv is not None else sys.argv[1:]) if not a.startswith("-")]
    if not dirs:
        _err("用法: python scripts/check_launch_path.py <产物目录> [...]")
        return 3
    viol, notes, n_files = [], [], 0
    for d in dirs:
        if not os.path.isdir(d):
            _err("[FAIL] 产物目录不存在: %s" % d)
            return 3
        for fn in PRODUCTS:
            p = os.path.join(d, fn)
            if not os.path.isfile(p):
                continue
            try:
                with io.open(p, encoding="utf-8") as f:
                    obj = json.load(f)
            except (OSError, ValueError) as e:                       # noqa: PERF203
                viol.append("%s/%s 解析失败：%s —— 读不出标记 ≠ 有标记，按违规计"
                            % (os.path.basename(d), fn, e))
                continue
            if not _looks_fresh(obj):
                notes.append("%s/%s 非业务产物形状，跳过" % (os.path.basename(d), fn))
                continue
            n_files += 1
            if obj.get(MARK) is True:
                notes.append("%s/%s 带 %s" % (os.path.basename(d), fn, MARK))
            else:
                viol.append("%s/%s 缺 %s —— 该产物未经 ftth_launcher.py 派生"
                            "（疑似绕过启动器直调，C7 违规）"
                            % (os.path.basename(d), fn, MARK))
    for n in notes:
        _out("  · %s" % n)
    if n_files == 0:
        _err("[FAIL] 无可核对象：%d 个目录下均未找到 %s 任一 —— "
             "空集合不得判 PASS（没核 ≠ 核过了）" % (len(dirs), " / ".join(PRODUCTS)))
        return 3
    if viol:
        _out("  [调用链违规 %d]" % len(viol))
        for v in viol:
            _out("    × %s" % v)
        _out("  → rc=2：经 ftth_launcher.py 重跑该阶段。")
        return 2
    _out("== 调用链门禁: ALL PASS（%d 个产物均经启动器派生）==" % n_files)
    return 0


if __name__ == "__main__":
    sys.exit(main())