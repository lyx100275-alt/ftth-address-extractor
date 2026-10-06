#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""产物契约检查（L1-C8 词汇封闭 + C9 闭合盘点，静态审计用）。

背景
----
SKILL.md L1-C8 规定：`result_origin` ∈ measured/derived/unresolved，
`result_confirmation` ∈ settled/pending；C9 在 inspect 运行时校验闭合。
此前没有任何静态门禁锁词汇 —— 写错一个 origin 字符串即静默产生"第四种状态"，
下游按既有三态解释，错得悄无声息。

检查（只断言契约写明的，不替 C9 断语义）：
  R1 凡带 result_origin 的 dict，其值必须在三者之中；
  R2 凡带 result_confirmation 的 dict，其值必须在两者之中；
  R3 盘点：pending / unresolved 条数（只报告，不判 FAIL —— FAIL 是 C9 的权力）。
  R4 凡带 `判定依据` 的 dict，其值**首段**必须在 COVERAGE_METHODS 枚举内（2026-09-27
     P0-3 新增）。治的病：「怎么得到的」只在自由文本里 ⇒ 机器不可判；实测同一脚本内
     并存「V型计算」/「V形计算」两种写法，下游按枚举解释即静默出错。空值同样 FAIL
     （规则本体：coverage_rules.md「可机械检查的判据 —— 判定依据为空不得采信」）。
未知词汇 → rc=2（停：产物已污染）；目录不可读/无产物 → rc=3（早失败，无可核对象）。

用法：python scripts/check_contracts.py <产物目录> [...]
"""
import io
import json
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _rec = getattr(_s, "reconfigure", None)
        if callable(_rec):
            _rec(encoding="utf-8", errors="replace")
    except Exception:
        pass

ORIGINS = ("measured", "derived", "unresolved")
CONFS = ("settled", "pending")
PRODUCTS = ("parsed.json", "coverage.json", "count_box.json", "titleblock.json",
            "fxmap.json", "fx_locations.json")

# R4 覆盖判定依据的**机器可枚举词表**只有一个来源：ftth_common.COVERAGE_METHODS。
#   本脚本只**引用**，不另抄一份（抄两份必然漂移 —— 2026-09-27 P0-3 实测同一脚本内
#   并存「V型计算」/「V形计算」就是这个成因）。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from ftth_common import COVERAGE_METHODS, coverage_method_of
except Exception as _e:                                             # noqa: BLE001
    print("[FAIL] 无法加载共享词表 ftth_common.COVERAGE_METHODS: %s" % _e)
    sys.exit(3)


def _walk(o, origins, confs, bad):
    if isinstance(o, dict):
        if "result_origin" in o:
            if o["result_origin"] not in ORIGINS:
                bad.append("result_origin=%r" % (o["result_origin"],))
            else:
                origins.append(o["result_origin"])
        if "result_confirmation" in o:
            if o["result_confirmation"] not in CONFS:
                bad.append("result_confirmation=%r" % (o["result_confirmation"],))
            else:
                confs.append(o["result_confirmation"])
        if "判定依据" in o:
            _b = o["判定依据"]
            if coverage_method_of(_b) is None:
                bad.append("判定依据=%r 首段不在覆盖方法枚举 %s 内（空值同样不得采信）"
                           % (_b, list(COVERAGE_METHODS)))
        for v in o.values():
            _walk(v, origins, confs, bad)
    elif isinstance(o, list):
        for v in o:
            _walk(v, origins, confs, bad)


def main(argv):
    dirs = [a for a in argv[1:] if not a.startswith("-")]
    if not dirs:
        print("用法: python scripts/check_contracts.py <产物目录> [...]")
        return 3
    bad_all, total_pend, total_unres, n_files = [], 0, 0, 0
    for d in dirs:
        if not os.path.isdir(d):
            print("[FAIL] 产物目录不存在: %s" % d)
            return 3
        for fn in PRODUCTS:
            p = os.path.join(d, fn)
            if not os.path.isfile(p):
                continue
            n_files += 1
            try:
                with io.open(p, encoding="utf-8") as f:
                    obj = json.load(f)
            except Exception as e:
                print("[FAIL] %s 解析失败: %s" % (p, e))
                return 2
            origins, confs, bad = [], [], []
            _walk(obj, origins, confs, bad)
            for b in bad:
                bad_all.append("%s: %s" % (os.path.join(os.path.basename(d), fn), b))
            total_pend += sum(1 for c in confs if c == "pending")
            total_unres += sum(1 for c in origins if c == "unresolved")
            print("[OK] %s origin=%s conf=%s" % (
                os.path.join(os.path.basename(d), fn),
                {o: origins.count(o) for o in sorted(set(origins))},
                {c: confs.count(c) for c in sorted(set(confs))}))
    print("盘点: 文件 %d 个 / pending %d 条 / unresolved %d 条（语义判定权在 C9）"
          % (n_files, total_pend, total_unres))
    # 2026-09-27（P0-3 附带修复）：本脚本 docstring 自述「目录可读但无产物 → rc=3」，
    #   而实现里缺这一支 —— 无产物时 n_files=0、bad_all 空，直接落到 ALL PASS。
    #   这是**空集合判 PASS**：把「一个产物都没核」报成「词汇全合规」。
    #   按本技能通则「没核不得输出成通过」，补齐 rc=3。
    if n_files == 0:
        print("[FAIL] 无可核对象：%d 个目录下均未找到 %s 任一 —— "
              "空集合不得判 PASS" % (len(dirs), " / ".join(PRODUCTS)))
        return 3
    if bad_all:
        print("[FAIL] 未知词汇 %d 处:" % len(bad_all))
        for b in bad_all[:10]:
            print("  ! %s" % b)
        return 2
    print("== 产物契约: ALL PASS ==")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
