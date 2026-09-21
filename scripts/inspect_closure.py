#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
出表前一体化闭合核查（Step 2 自检第一项）。

为什么需要它：
    出表前的疑点核查（箱安装层口径 / 楼栋单元全貌 / FX 编号坐标归属 / 楼层表直读 /
    覆盖闭合）若靠临时编写一次性 inspect_*.py，会串行消耗多个回合且内容互相重叠
    （实测某会话连写 7 个，是当轮最大耗时项）。本脚本把这类核查一次跑完：
    读 parse 结果（必传）+ 覆盖范围 JSON（可选）+ 几何缓存（可选），输出七项结论，
    并以退出码显式给出「可否出表」。

检查项：
    C1 楼栋单元全貌      楼号序列与断号提示（事实陈述，供人裁决）、每栋单元数、每单元楼层表规模
    C2 安装楼层口径分布  parse 侧逐箱口径统计；存在 null/「未关联」即 FAIL（区间法口径下应为 0）
    C3 安装楼层双源交叉  parse.安装楼层 vs coverage.安装楼层（独立方法），不一致即 FAIL
    C4 FX 编号坐标归属   geom 文字中匹配编号正则：parse 有而图上无 / 图上有而 parse 漏 即 FAIL；
                         同一编号多处出现（系统图+对照表）列出坐标，属 INFO
    C5 楼层表直读清单    每单元「楼层 | 户数 | 布线」非空行与合计，整图总户数（INFO）
    C6 覆盖闭合          逐箱：覆盖范围线索缺失即 FAIL；安装楼层不在覆盖楼层集合内即 FAIL；
                         同单元多箱覆盖楼层完全相同列为 WARN（须复核，见 Step 2「覆盖范围重复检测」）
    C7 覆盖自检透传      coverage 顶层自检键与「需人工裁决」原样带出（WARN）
    C8 同单元跨层户数一致性  一个单元内各层户数应一致；某层与同单元其余层不成比例
                         即标出（WARN，不下结论——商铺层/架空层/跃层都可能是图纸事实）
    C9 结果状态闭合      逐条扫描产物里的 result_origin / result_confirmation：
                         confirmation=pending 或 origin=unresolved 即 FAIL
                         （未裁决的值不得进入成品）；字段值**不在契约枚举内**同样 FAIL
                         （防止说明性文字冒充结果项）；产物未携带本字段则 SKIP

用法：
    python inspect_closure.py --parse parse_result.json [--coverage 覆盖.json] [--geom 图纸.geom.json]
                              [--fx-pattern "FL\\d+-FX\\d+"] [--json 机读输出.json]

退出码：
    0 = 无 FAIL（WARN/INFO 不影响）；2 = 存在 FAIL 项，不得出表；1 = 输入/解析错误。

与 verify_coverage_truth.py 的分工：
    本脚本用于**出表前**（无需 xlsx，查 parse/coverage/geom 三源闭合）；
    verify_coverage_truth 用于**有定稿标准地址表之后**的回归反查。阶段不同，不重叠。
"""
import argparse
from ftth_common import bldg_num_or_none  # 楼号提取：失败返 None（勿与 bldg_num 失败返 0 混用）
import json
import os
import re
import sys
from collections import Counter, OrderedDict

sys.stdout.reconfigure(encoding="utf-8")


def norm_floor(v):
    """楼层名归一化 → 整数（5F/5层/5 → 5；B1/地下一层 → -1）。无法识别返回 None。"""
    if v is None:
        return None
    t = str(v).replace("　", "").replace(" ", "").strip()
    m = re.fullmatch(r"[Bb](\d+)(?:层|F)?", t)
    if m:
        return -int(m.group(1))
    m = re.fullmatch(r"(-?\d+)\s*(?:[Ff]|层)?", t)
    if m:
        return int(m.group(1))
    return None


def fmt_floor(v):
    return "B%d" % -v if v is not None and v < 0 else ("%sF" % v if v is not None else "?")


class Report:
    def __init__(self):
        self.lines = []
        self.fails = []
        self.warns = []
        self.checks = []

    def emit(self, s=""):
        self.lines.append(s)
        print(s)

    def check(self, cid, name, status, detail=""):
        self.checks.append({"id": cid, "name": name, "status": status, "detail": detail})
        self.emit("[%s] %s %s" % (status, cid, name + (" —— " + detail if detail else "")))
        # 2026-09-16：判 FAIL/WARN 时同步登记到汇总，使「汇总计数」与上方逐行结论自洽。
        #   原实现只在显式调用 R.fail()/R.warn() 时登记，凡「check 判 FAIL 而无逐项登记」
        #   的检查项即漏计 —— 实测某图出现「5 行 [FAIL] 而汇总写 FAIL 1 项」的矛盾。
        #   按 cid 去重，保证既有「逐项登记 + 一次 check」型检查项的数字不变。
        #   rc 语义不变（仍由 self.fails 是否非空决定）。
        bucket = {"FAIL": self.fails, "WARN": self.warns}.get(status)
        if bucket is not None and not any(x.startswith(cid + " ") for x in bucket):
            bucket.append("%s %s" % (cid, name))

    def fail(self, cid, msg):
        self.fails.append("%s %s" % (cid, msg))

    def warn(self, cid, msg):
        self.warns.append("%s %s" % (cid, msg))


def count_box_summary(K):
    """把 count_box_icons.py 的输出压成一行摘要（供 C2 在用图标法口径时展示）。"""
    if not isinstance(K, dict):
        return "count-box JSON 结构不可解析"
    cols = K.get("列") or []
    bad = K.get("刻度偏移异常列") or []
    tot = K.get("归层后总户数")
    una = K.get("未归属图标数")
    parts = ["图标法物理列 %d 个" % len(cols),
             "归层后总户数 %s" % (tot if tot is not None else "?")]
    if una:
        parts.append("未归属图标 %d" % una)
    if bad:
        parts.append("刻度偏移异常列 %d 个（该列归层不可信，须人工核对后重跑）" % len(bad))
    return "；".join(parts)


# bldg_num 已上收：ftth_common.bldg_num_or_none（失败返 None，原语义一致）


def main():
    ap = argparse.ArgumentParser(description="出表前一体化闭合核查")
    ap.add_argument("--parse", dest="parse_json", required=True, help="parse_dxf_structured 输出的 JSON（必传）")
    ap.add_argument("--coverage", dest="coverage_json", default=None, help="覆盖范围 JSON（可选）")
    ap.add_argument("--geom", dest="geom_json", default=None, help="<DXF>.geom.json 几何缓存（可选）")
    ap.add_argument("--count-box", dest="count_box_json", default=None,
                    help="count_box_icons.py 的图标法 JSON（可选）。本图 parse 侧无分纤箱"
                         "（箱体只画图标、不写编号）时，用它提供箱清单的替代口径；"
                         "否则 C2/C3/C4/C6 在零箱数据上会得出无意义的 PASS。")
    ap.add_argument("--fx-pattern", default=r"FL\d+-FX\d+", help="分纤箱编号正则")
    ap.add_argument("--titleblock", dest="titleblock_json", default=None,
                    help="read_titleblock_households.py 输出的图签读数 JSON（可选）。"
                         "提供后 C10 做「图签 vs 系统图」逐栋互证；不提供则 C10 判 SKIP"
                         "（写明本次未做交叉校验，不得当作已核）")
    ap.add_argument("--json", dest="json_out", default=None, help="机读结果输出路径（可选）")
    args = ap.parse_args()

    # ---- --fx-pattern 缺省自描述（2026-09-18 新增）----
    # 本脚本 --fx-pattern 的默认值写死为 FL\d+-FX\d+，与大多数图的编号形态不符；而
    #   流水线此前不转发该参数 → C4 在 geom 文字里按错正则匹配 → 一个都搜不到 →
    #   把 parse 侧**全部**箱误判成「图上无编号文字」（实测某图 23/23 全 FAIL，纯假警报，
    #   且会把真 FAIL 淹掉）。
    # 改为：命令行未显式给出时，读 parse 产物自带的 参数.fx_pattern（产物自描述，parse
    #   已把它实际使用的正则记在产物里）。要过滤「未提供（…）」这类提示语 —— 它不是
    #   正则，直接 compile 会崩。
    if args.fx_pattern == "FL\\d+-FX\\d+":        # 仍是内置默认值 ⇒ 视为未显式给出
        _fp = ""
        try:
            with open(args.parse_json, "r", encoding="utf-8") as _pf:
                _fp = str(((json.load(_pf).get("参数") or {}).get("fx_pattern")) or "").strip()
        except (IOError, json.JSONDecodeError):                      # noqa: BLE001
            _fp = ""
        if _fp and not any(w in _fp for w in ("未提供", "不提取", "留空")):
            args.fx_pattern = _fp
            print("[inspect] --fx-pattern 未显式给出，自 parse 产物取: %s" % _fp)

    R = Report()
    try:
        P = json.load(open(args.parse_json, encoding="utf-8"))
    except Exception as e:
        print("parse JSON 读取失败：%s" % e)
        return 1
    C = None
    if args.coverage_json:
        try:
            C = json.load(open(args.coverage_json, encoding="utf-8"))
        except Exception as e:
            print("coverage JSON 读取失败：%s" % e)
            return 1
    G = None
    if args.geom_json:
        try:
            G = json.load(open(args.geom_json, encoding="utf-8"))
        except Exception as e:
            print("geom JSON 读取失败：%s" % e)
            return 1
    K = None
    if args.count_box_json:
        try:
            _cbf = open(args.count_box_json, encoding="utf-8")
        except OSError as e:
            # count_box_icons.py 在归层门禁处中止（rc=2）时**不写产物**，此处路径会不存在。
            # 原实现只报 "No such file or directory"，看不出真实原因，故分两段处理。
            print("count-box JSON 打不开：%s" % e)
            print("  常见原因：count_box_icons.py 在门禁处中止（rc=2）时不写产物 ——")
            print("  先单独跑 `ftth.py count-box`，确认其 rc 与门禁信息，再决定是否传本参数。")
            return 1
        try:
            K = json.load(_cbf)
        except Exception as e:
            print("count-box JSON 解析失败：%s" % e)
            return 1
        finally:
            _cbf.close()

    buildings = P.get("楼栋") or {}
    # 展开 parse：箱清单 + 单元清单
    boxes = []   # (楼栋, 单元, 编号, 安装楼层, 口径, 误差, y)
    units = []   # (楼栋, 单元, 楼层表dict)
    for blk, bv in buildings.items():
        for un, uv in (bv.get("单元") or {}).items():
            units.append((blk, un, uv.get("楼层表") or {}))
            for fx in (uv.get("分纤箱") or []):
                boxes.append((blk, un, fx.get("编号"), fx.get("安装楼层"),
                              fx.get("安装楼层口径"), fx.get("安装楼层误差"), fx.get("y")))

    R.emit("=" * 72)
    R.emit("出表前一体化闭合核查")
    R.emit("parse    : %s" % args.parse_json)
    R.emit("coverage : %s" % (args.coverage_json or "（未提供，C3/C6 跳过）"))
    R.emit("geom     : %s" % (args.geom_json or "（未提供，C4 跳过）"))
    R.emit("count-box: %s" % (args.count_box_json or "（未提供）"))
    R.emit("=" * 72)

    # ---------- C0 数据集非空门禁（2026-09-16 修复 P0-4） ----------
    # 原实现在空数据集上会全线 PASS：boxes=[] ⇒ null_boxes=[] ⇒ C2 落入 else 报
    #   「[PASS] 0/0 箱均有安装楼层」（C3/C4/C6 同构），退出码 0。
    # 实测某会话据此宣布「可进入后续自检」，而该图 parse 侧本就 0 箱 0 楼层表 ——
    # 采信即交付空表。此处显式拦断：核查所依赖的数据集为空时，不得判 PASS。
    _nobox = (len(boxes) == 0)
    _nobldg = (len(buildings) == 0)
    if _nobldg or (_nobox and K is None):
        R.emit()
        R.emit("--- C0 数据集非空门禁 ---")
        if _nobldg:
            R.emit("  ✗ parse.楼栋 为空")
            R.fail("C0", "parse.楼栋 为空 —— 核查无有效数据，不得据此出表")
        if _nobox and K is None:
            R.emit("  ✗ parse 侧分纤箱清单为空（0 箱）")
            R.fail("C0", "parse 侧 0 箱且未提供 --count-box —— 核查无有效数据，不得据此出表")
        R.check("C0", "数据集非空门禁", "FAIL",
                "空集合不得判 PASS；请核对 --parse 是否为本图产物"
                + ("，或改用 --count-box 提供图标法箱清单" if _nobox else ""))
    elif _nobox and K is not None:
        R.emit()
        R.emit("--- C0 数据集非空门禁 ---")
        R.check("C0", "数据集非空门禁", "WARN",
                "parse 侧 0 箱：C2 改用 --count-box 图标法口径；"
                "C3/C4/C6 依赖 parse 箱清单，本图为空故判 FAIL（非 PASS）")

    # ---------- C1 楼栋单元全貌 ----------
    R.emit()
    R.emit("--- C1 楼栋单元全貌 ---")
    nums = sorted(n for n in (bldg_num_or_none(b) for b in buildings) if n is not None)
    for blk in sorted(buildings, key=lambda b: (bldg_num_or_none(b) is None, bldg_num_or_none(b) or 0)):
        bv = buildings[blk]
        ulist = list((bv.get("单元") or {}).keys())
        nfx = sum(len((bv.get("单元") or {})[u].get("分纤箱") or []) for u in ulist)
        R.emit("  %-6s 单元 %d 个（%s） 分纤箱 %d 个" % (blk, len(ulist), "/".join(ulist), nfx))
    gap = []
    if nums:
        full = set(range(min(nums), max(nums) + 1))
        gap = sorted(full - set(nums))
    if gap:
        detail = "楼号序列 %d~%d 缺 %s（事实陈述：图上无这些楼号标题；项目是否应有，须人工裁决）" % (
            min(nums), max(nums), "/".join("%d#" % g for g in gap))
        R.check("C1", "楼栋单元全貌", "INFO", detail)
        R.warn("C1", detail)
    else:
        R.check("C1", "楼栋单元全貌", "INFO", "楼号序列连续：%s" % "/".join("%d#" % n for n in nums))

    # ---------- C2 安装楼层口径分布 ----------
    R.emit()
    R.emit("--- C2 分纤箱安装楼层口径分布（parse 侧） ---")
    dist = OrderedDict()
    null_boxes = []
    for blk, un, fid, fl, caliber, err, y in boxes:
        key = caliber or ("有值" if fl is not None else "（无口径字段）")
        dist[key] = dist.get(key, 0) + 1
        if fl is None:
            null_boxes.append((blk, un, fid, err))
    for k, v in dist.items():
        R.emit("  %-44s %d" % (k, v))
    if null_boxes:
        for blk, un, fid, err in null_boxes:
            R.emit("  ✗ %s/%s/%s 安装楼层=null（误差 %s）" % (blk, un, fid, err))
            R.fail("C2", "%s/%s/%s 安装楼层未关联" % (blk, un, fid))
        R.check("C2", "安装楼层口径分布", "FAIL", "%d/%d 箱安装楼层未关联" % (len(null_boxes), len(boxes)))
    elif not boxes:
        # 2026-09-16 修复 P0-4：boxes 为空 ⇒ null_boxes 必为空 ⇒ 原实现落入 else 报
        #   「PASS 0/0 箱均有安装楼层」，把空集合当成「全部合格」（C3/C4/C6 同构）。
        #   按数据源分流：有 --count-box 则改用图标法口径并透出其不可信标记，否则判 FAIL。
        if K is not None:
            kbad = K.get("刻度偏移异常列") or []
            R.check("C2", "安装楼层口径分布", "FAIL" if kbad else "WARN",
                    "parse 侧 0 箱 → 改用 --count-box 图标法口径：" + count_box_summary(K))
            for it in kbad[:8]:
                R.emit("  ✗ 刻度偏移异常列: %s" % json.dumps(it, ensure_ascii=False)[:150])
            if kbad:
                R.fail("C2", "图标法刻度列配对偏移异常 %d 列 —— 该列归层不可信" % len(kbad))
        else:
            R.check("C2", "安装楼层口径分布", "FAIL",
                    "parse 侧 0 箱，无安装楼层口径可核（空集合不得判 PASS）")
    else:
        R.check("C2", "安装楼层口径分布", "PASS", "%d/%d 箱均有安装楼层" % (len(boxes), len(boxes)))

    # ---------- C3 安装楼层双源交叉 ----------
    R.emit()
    R.emit("--- C3 安装楼层双源交叉（parse vs coverage） ---")
    if C is None:
        R.check("C3", "安装楼层双源交叉", "SKIP", "未提供 coverage JSON")
    else:
        cmap = {}
        for blk, bv in (C.get("楼栋") or {}).items():
            for un, uv in (bv.get("单元") or {}).items():
                for fx in (uv.get("分纤箱") or []):
                    cmap.setdefault(fx.get("编号"), []).append(
                        (blk, un, fx.get("安装楼层"), (fx.get("覆盖范围线索") or {}).get("覆盖楼层")))
        n_ok = n_bad = n_miss = 0
        # 2026-09-18 修复：coverage 提供了 JSON，但其**箱级记录为 0** 时，原实现会把
        #   parse 侧每个箱都判「coverage 无记录」= FAIL —— 把「第二来源结构上无常」
        #   当成了「逐箱矛盾」。实测某图 66 个箱被逐一 FAIL，闸门失去分辨力（那种
        #   图例：编号锚全部超出米数列邻域，coverage 侧本就不产出箱级安装楼层）。
        #   正确处置 = 按「不可核」报出并**明示仍是单一来源**，不得读作已核；
        #   绝不改判 PASS（空集合不得判 PASS）。
        if not cmap and boxes:
            R.check("C3", "安装楼层双源交叉", "SKIP",
                    "coverage 提供了 JSON 但其箱级记录为 0（本图箱号锚不可归属，"
                    "该来源本图不产出箱级安装楼层）—— 双源交叉**不可核**；"
                    "parse 侧 %d 个箱的安装楼层仅**单一来源**，未经第二来源交叉验证"
                    % len(boxes))
            R.warn("C3", "coverage 未提供箱级安装楼层（本图箱号锚不可归属）——"
                   "parse 侧 %d 个箱的安装楼层仅单一来源、未交叉验证，不得读作已核"
                   % len(boxes))
        for blk, un, fid, fl, caliber, err, y in boxes:
            if not cmap:
                break
            recs = cmap.get(fid)
            if not recs:
                R.emit("  ✗ %s（%s/%s）coverage 中无记录" % (fid, blk, un))
                R.fail("C3", "%s coverage 无记录" % fid)
                n_miss += 1
                continue
            cfl_vals = {norm_floor(r[2]) for r in recs}
            if norm_floor(fl) in cfl_vals:
                n_ok += 1
            else:
                R.emit("  ✗ %s（%s/%s）parse=%s vs coverage=%s" % (
                    fid, blk, un, fl, "/".join(str(r[2]) for r in recs)))
                R.fail("C3", "%s 安装楼层双源不一致 parse=%s coverage=%s" % (fid, fl, [r[2] for r in recs]))
                n_bad += 1
        # 2026-09-16 修复 P0-4：parse 侧 0 箱时两源无交集，n_bad/n_miss 均为 0，
        #   原判据会给出 PASS —— 空集合不得判 PASS。
        if _nobox:
            R.check("C3", "安装楼层双源交叉", "FAIL",
                    "parse 侧 0 箱，双源无交集可核（空集合不得判 PASS）")
        elif not cmap:
            pass          # 已按「不可核」报出（见上），此处不得再判 PASS 覆盖
        else:
            st = "PASS" if (n_bad == 0 and n_miss == 0) else "FAIL"
            R.check("C3", "安装楼层双源交叉", st,
                    "一致 %d / 不一致 %d / 无记录 %d（共 %d 箱）" % (n_ok, n_bad, n_miss, len(boxes)))

    # ---------- C4 FX 编号坐标归属 ----------
    R.emit()
    R.emit("--- C4 FX 编号坐标归属（geom 文字双向核对） ---")
    if G is None:
        R.check("C4", "FX 编号坐标归属", "SKIP", "未提供 geom 缓存")
    else:
        rx = re.compile(args.fx_pattern)
        geom_ids = {}
        for row in (G.get("texts") or []):
            layer, x, y, text = row[0], row[1], row[2], str(row[3])
            for m in rx.finditer(text):
                geom_ids.setdefault(m.group(0), []).append((x, y, layer))
        parse_ids = {fid for _, _, fid, *_ in boxes}
        # 2026-09-18 修复：parse 的「未归属分纤箱」也是**已收录**的编号文字（只是归属
        #   无客观判据、未定案）。必须计入 parse 侧 —— 否则 C4 会把「已收录但待裁决」
        #   误报成「漏收录」。两者严重程度不同，混为一谈会让闸门失去意义：
        #     漏收录 = 静默丢数（图上确有文字、产物里没有）⇒ FAIL；
        #     未归属 = 已收录、标 pending、不进成品、须人工裁决 ⇒ WARN。
        unassigned_ids = []
        for _u in ((P.get("未归属分纤箱") or []) if isinstance(P, dict) else []):
            _fid_u = str((_u or {}).get("编号") or "").strip()
            if _fid_u:
                unassigned_ids.append(_fid_u)
        parse_ids = set(parse_ids) | set(unassigned_ids)
        miss_in_geom = sorted(parse_ids - set(geom_ids))
        miss_in_parse = sorted(set(geom_ids) - parse_ids)
        for fid in miss_in_geom:
            R.emit("  ✗ %s parse 有、geom 文字中找不到" % fid)
            R.fail("C4", "%s 图上无编号文字" % fid)
        for fid in miss_in_parse:
            R.emit("  ✗ %s geom 文字中存在、parse 未收录（位置 %s）" % (
                fid, ["(%.1f,%.1f)" % (p[0], p[1]) for p in geom_ids[fid]]))
            R.fail("C4", "%s parse 漏收录" % fid)
        for fid in sorted(geom_ids):
            if len(geom_ids[fid]) > 1:
                R.emit("  · %s 出现 %d 处：%s" % (fid, len(geom_ids[fid]),
                       " ".join("(%.1f,%.1f,%s)" % p for p in geom_ids[fid])))
        if unassigned_ids:
            R.emit("  ! %d 个编号未归属（对照表无法定楼栋/单元）：%s"
                   % (len(set(unassigned_ids)), "、".join(sorted(set(unassigned_ids))[:12])))
            R.emit("    已收录、标 pending、**不进成品** —— 须人工裁决（明细见 parsed.json 的"
                   "「未归属分纤箱」与「需人工裁决」）")
            R.warn("C4", "%d 个编号未归属（%s）—— 已收录标 pending、不进成品，须人工裁决"
                   % (len(set(unassigned_ids)), "、".join(sorted(set(unassigned_ids))[:12])))
        # 2026-09-16 修复 P0-4：parse 侧 0 编号时双向差集必为空，原判据给出 PASS。
        if not parse_ids:
            R.check("C4", "FX 编号坐标归属", "FAIL",
                    "parse 侧 0 箱，无编号可核（空集合不得判 PASS）")
        elif miss_in_geom or miss_in_parse:
            R.check("C4", "FX 编号坐标归属", "FAIL",
                    "geom 中编号 %d 个 / parse 收录 %d 个；双向差集 %d+%d" % (
                        len(geom_ids), len(parse_ids), len(miss_in_geom), len(miss_in_parse)))
        else:
            R.check("C4", "FX 编号坐标归属", "PASS",
                    "geom 中编号 %d 个 / parse 收录 %d 个（其中未归属 %d 个，已标 pending）"
                    "；双向差集 0+0" % (len(geom_ids), len(parse_ids),
                                       len(set(unassigned_ids))))

    # ---------- C5 楼层表直读清单 ----------
    R.emit()
    R.emit("--- C5 楼层表直读清单（parse 侧，INFO） ---")
    grand = 0
    n_rows_total = 0      # 全图非空行数（户数或布线任一非空）
    n_hu_total = 0        # 其中「户数」列非空的行数
    # 2026-09-18（实跑修复，P1）：**「有楼层刻度、但户数/布线两列皆空」的层行**。
    #   原实现把它们直接从清单里过滤掉（`if hu is not None or bx is not None`），
    #   后果是这些层既不出现、也不被告知 —— 实测某图 12 个单元各带 B1/B2 两个刻度行、
    #   24 行全部消失，C1~C9 无一提及，出表后地下 2 层凭空不见且零说明。
    #   这与 SKILL.md Step 1c 硬点②「某层无户数标注即不生成户号，**列待确认项**」冲突：
    #   「图上确实没有户数」与「我没读到户数」必须可区分。
    #   本项只**登记事实**、不下结论（地下车库/设备层/储藏层都是合法图面事实）。
    blank_rows = []             # (楼栋, 单元, 层名)
    for blk, un, fltab in units:
        rows = []
        for fname, fv in fltab.items():
            hu, bx = fv.get("户数"), fv.get("布线")
            if hu is not None or bx is not None:
                rows.append((fv.get("fl_num", norm_floor(fname)), fname, hu, bx))
            else:
                blank_rows.append((blk, un, fname))
        rows.sort(key=lambda r: (r[0] is None, r[0]))
        subtotal = sum(r[2] for r in rows if isinstance(r[2], int))
        grand += subtotal
        n_rows_total += len(rows)
        n_hu_total += sum(1 for r in rows if isinstance(r[2], int))
        R.emit("  %s/%s：非空 %d 行，户数合计 %s" % (blk, un, len(rows), subtotal))
        for _, fname, hu, bx in rows:
            R.emit("      %-6s 户数 %-4s 布线 %s" % (fname, hu if hu is not None else "-", bx if bx is not None else "-"))
    # 空集合不得判 PASS，也不得把「没取到数」写成「合计 0」（实测某图户数列全空，
    # 旧实现输出「整图户数合计 0」，把「无户数列」伪装成「数就是 0」）。
    if n_rows_total == 0:
        R.check("C5", "楼层表直读清单", "SKIP",
                "全图 %d 个单元的楼层表均无任何非空行（户数/布线两列皆空）——"
                "本图户数须由图标法（count-box）提供；不得读作合计 0" % len(units))
    elif n_hu_total == 0:
        R.check("C5", "楼层表直读清单", "SKIP",
                "楼层表共 %d 个非空行，但「户数」列全空 —— 本图户数须由图标法（count-box）提供；"
                "不得把「没有户数列」读作「合计 0」" % n_rows_total)
    else:
        _c5_note = ("整图户数合计 %d（来源：楼层表户数列，非空户数行 %d/%d）"
                    % (grand, n_hu_total, n_rows_total))
        if blank_rows:
            R.emit("  ↓ 有楼层刻度、但「户数/布线」两列皆空的层（%d 行）：" % len(blank_rows))
            for _b, _u, _f in blank_rows[:40]:
                R.emit("      %s/%s/%s" % (_b, _u, _f))
            if len(blank_rows) > 40:
                R.emit("      ... 另有 %d 行未列出" % (len(blank_rows) - 40))
            R.check("C5", "楼层表直读清单", "WARN",
                    _c5_note + ("；另有 %d 个层行**有楼层刻度但无户数/布线标注** —— "
                                "按 Step 1c 这些层不生成户号，须人工确认是否图纸事实"
                                "（地下车库/设备层/储藏层等），明细见上" % len(blank_rows)))
        else:
            R.check("C5", "楼层表直读清单", "INFO", _c5_note)

    # ---------- C8 同单元跨层户数一致性（2026-09-17 新增） ----------
    # 为什么要它（实测依据）：
    #   某图 1#楼/1单元 的楼层表里，2F~10F 每层 2 户，唯独 1F 是 1 户。该形态当时
    #   没有被任何检查项标出——报告里以「整图户数合计 ✓」一句带过。可户数**守恒**
    #   （合计对得上）与逐层**分布合理**是两件事：合计能对上，恰恰掩盖了单层偏离。
    #
    # 判据（通用，不绑任何项目）：
    #   一个单元内，住宅标准层的户数应当一致。某层与同单元其余层不成比例，即为
    #   **可自动标出的可疑形态**——但本项只负责标出「哪单元哪层与其余层不同」，
    #   **不下结论**：商铺层 / 架空层 / 跃层 / 顶层退台都是合法的图纸事实，
    #   是否可接受属人工裁决（与 L0-I4 的「发现要主动、裁决交人工」一致）。
    #   实现上只用「户数」字段自身，不引入层号、户数绝对值等任何项目特有常量。
    #
    # 分档：
    #   · 户数值种类 = 1            → 全单元一致（PASS）
    #   · 户数值种类 = 2 且有多数   → 少数者为偏离层，逐个列出（WARN）
    #   · 户数值种类 = 2 且平票     → 无多数标准层，只报分布，不判偏离
    #   · 户数值种类 ≥ 3            → 视为无统一标准层，只报分布，不判偏离
    #   · 有效层数 < 3              → 谈不上「标准层」，不纳入本项
    #   判 WARN 而非 FAIL：这是**提示复核**，不是数据错误，不阻塞出表。
    R.emit()
    R.emit("--- C8 同单元跨层户数一致性 ---")
    c8_units = 0
    c8_bad = []
    for blk, un, fltab in units:
        vals = []
        for fname, fv in fltab.items():
            hu = fv.get("户数")
            if isinstance(hu, int):
                vals.append((fv.get("fl_num", norm_floor(fname)), fname, hu))
        if len(vals) < 3:
            continue
        c8_units += 1
        cnt = Counter(v[2] for v in vals)
        if len(cnt) == 1:
            R.emit("  %s/%s：%d 层全部 %d 户" % (blk, un, len(vals), vals[0][2]))
            continue
        pairs = sorted(cnt.items(), key=lambda kv: -kv[1])
        if len(cnt) >= 3 or pairs[0][1] == pairs[1][1]:
            R.emit("  · %s/%s：户数分布 %s（无多数标准层，不作偏离判定）" % (
                blk, un, "、".join("%d户×%d层" % (k, v) for k, v in sorted(cnt.items()))))
            continue
        (maj, maj_n), (mino, mino_n) = pairs[0], pairs[1]
        offs = ["%s=%s" % (v[1], v[2]) for v in vals if v[2] == mino]
        detail = ("%s/%s：标准层 %d 户（%d 层），偏离 %d 层 → %s（差 %+d）"
                  % (blk, un, maj, maj_n, mino_n, "、".join(offs), mino - maj))
        R.emit("  ! " + detail)
        R.warn("C8", detail)
        c8_bad.append((blk, un, len(offs)))
    if c8_bad:
        R.check("C8", "同单元跨层户数一致性", "WARN",
                "%d 个单元存在层间户数不一致，须人工确认是否图纸事实（商铺层/架空层/跃层等）"
                % len(c8_bad))
    elif c8_units == 0:
        # 空集合不得判 PASS（与 C0/C2/C4 同则）：0 个单元 ≠ 0 个不一致。
        R.check("C8", "同单元跨层户数一致性", "SKIP",
                "无单元可核（「有效层数 ≥3 且户数非空」的单元数 = 0）——"
                "空集合不得判 PASS；本图户数须由图标法（count-box）提供")
    else:
        R.check("C8", "同单元跨层户数一致性", "PASS",
                "%d 个单元各层户数一致（有效层数不足 3 的单元未纳入）" % c8_units)

    # ---------- C6 覆盖闭合 ----------
    R.emit()
    R.emit("--- C6 覆盖闭合（parse × coverage） ---")
    if C is None:
        R.check("C6", "覆盖闭合", "SKIP", "未提供 coverage JSON")
    else:
        n_ok = n_noclue = n_outof = 0
        # 2026-09-19 修复（与 C3 同一条件、同一处置）：coverage 提供了 JSON，但**箱级
        #   记录为 0** 时，上面那个 `for blk, un, fid, ... in boxes` 循环里每个箱都会
        #   走到 `if not recs: continue` —— 循环体一次有效判定都没做，三个计数全 0，
        #   末行 `st = "PASS" if (n_noclue == 0 and n_outof == 0)` 于是输出
        #   「[PASS] 覆盖闭合 —— 闭合 0 / 缺线索 0 / 安装层越界 0」。
        #   这是**空集合判 PASS**：实测小区甲 1-4 地块四带全部命中，
        #   把「本图 0 个箱有任何覆盖线索」伪装成「覆盖全部闭合」——最隐蔽的一类静默丢数。
        #   处置与 C3 一致：报 SKIP + WARN，**明示不可核**，绝不判 PASS。
        _cmap_n = 0
        for _blk0, _bv0 in (C.get("楼栋") or {}).items():
            for _un0, _uv0 in (_bv0.get("单元") or {}).items():
                _cmap_n += len(_uv0.get("分纤箱") or [])
        if boxes and _cmap_n == 0:
            R.check("C6", "覆盖闭合", "SKIP",
                    "coverage 提供了 JSON 但其箱级记录为 0 —— 覆盖闭合**无对象可核**"
                    "（空集合不得判 PASS）；parse 侧 %d 个箱的覆盖范围本图未产出，"
                    "覆盖判定须补做或列待确认项" % len(boxes))
            R.warn("C6", "覆盖判定本图未产出任何箱级覆盖范围（parse 侧 %d 个箱全部无法闭合）"
                   "—— 不得读作覆盖已闭合" % len(boxes))
        # 同单元覆盖楼层完全相同 → WARN
        for blk, bv in (C.get("楼栋") or {}).items():
            for un, uv in (bv.get("单元") or {}).items():
                seen = {}
                for fx in (uv.get("分纤箱") or []):
                    clue = tuple((fx.get("覆盖范围线索") or {}).get("覆盖楼层") or [])
                    if clue:
                        seen.setdefault(clue, []).append(fx.get("编号"))
                for clue, ids in seen.items():
                    if len(ids) > 1:
                        R.emit("  ! %s/%s 箱 %s 覆盖楼层完全相同（%d 层）——须复核（Step 2 覆盖范围重复检测）" % (
                            blk, un, "/".join(ids), len(clue)))
                        R.warn("C6", "%s/%s %s 覆盖楼层完全相同" % (blk, un, ids))
        for blk, un, fid, fl, caliber, err, y in boxes:
            recs = cmap.get(fid) if C is not None else None
            if not recs:
                continue  # C3 已报
            clue_sets = [set(r[3] or []) for r in recs]
            if not any(clue_sets):
                R.emit("  ✗ %s（%s/%s）缺覆盖范围线索" % (fid, blk, un))
                R.fail("C6", "%s 缺覆盖范围线索" % fid)
                n_noclue += 1
                continue
            fln = norm_floor(fl)
            covered = any(fln in {norm_floor(x) for x in cs} for cs in clue_sets if cs)
            if fln is not None and not covered:
                R.emit("  ✗ %s（%s/%s）安装楼层 %s 不在覆盖楼层集合 %s 内" % (
                    fid, blk, un, fl, [sorted(cs) for cs in clue_sets]))
                R.fail("C6", "%s 安装楼层不在覆盖集合内" % fid)
                n_outof += 1
            else:
                n_ok += 1
        # 2026-09-16 修复 P0-4：boxes 为空时循环体一次不进，三个计数全 0 → 原判据 PASS。
        if _nobox:
            R.check("C6", "覆盖闭合", "FAIL",
                    "parse 侧 0 箱，覆盖闭合无对象可核（空集合不得判 PASS）")
        else:
            st = "PASS" if (n_noclue == 0 and n_outof == 0) else "FAIL"
            R.check("C6", "覆盖闭合", st,
                    "闭合 %d / 缺线索 %d / 安装层越界 %d" % (n_ok, n_noclue, n_outof))

    # ---------- C7 覆盖自检透传 ----------
    R.emit()
    R.emit("--- C7 coverage 顶层自检与需人工裁决（透传） ---")
    if C is None:
        R.check("C7", "覆盖自检透传", "SKIP", "未提供 coverage JSON")
    else:
        for k in ("自检_v底vs箱符号", "自检_v形单调性", "自检_偏差门禁"):
            if k in C:
                R.emit("  %s = %s" % (k, json.dumps(C[k], ensure_ascii=False)[:160]))
        pend = C.get("需人工裁决")
        if pend:
            R.emit("  需人工裁决 %d 项：" % len(pend))
            for it in pend:
                R.emit("    ! %s" % json.dumps(it, ensure_ascii=False)[:140])
                R.warn("C7", "需人工裁决：%s" % json.dumps(it, ensure_ascii=False)[:80])
            R.check("C7", "覆盖自检透传", "WARN", "需人工裁决 %d 项" % len(pend))
        else:
            R.check("C7", "覆盖自检透传", "PASS", "无需人工裁决项")

    # ---------- C9 结果状态闭合（2026-09-18 新增，v3.1） ----------
    # 配套 L1-C8「结果状态契约」。只定义字段而不校验，字段会退化成没人读的自由文本 ——
    # 前车之鉴：SKILL.md 里「判定依据 / 依据来源」写了 4 次，脚本侧实际产出的只有
    # analyze_coverage.py，其余脚本根本没有这两个键，契约形同虚设。
    # 依据 operations_discipline.md §5.6 底线 3「未裁决的值不得进入成品」：
    #     result_confirmation == "pending"  或  result_origin == "unresolved"  ⇒ FAIL
    # 向后兼容：产物未携带本字段时判 SKIP —— 老产物不得因缺字段被误拦成 FAIL。

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
    for _src_name, _src_obj in (("parse", P), ("coverage", C)):
        if _src_obj is None:
            continue
        _n0 = len(_rs_items)
        for _p, _o, _c in _walk_result_status(_src_obj):
            _rs_items.append(("%s:%s" % (_src_name, _p), _o, _c))
        (_rs_src_ok if len(_rs_items) > _n0 else _rs_src_empty).append(_src_name)
    _rs_scope = "已提供来源：%s；其中有字段：%s" % (
        "、".join(_rs_src_ok + _rs_src_empty) or "无",
        "、".join(_rs_src_ok) or "无")
    if _rs_src_empty:
        R.emit("  ! 已提供但零字段的来源：%s —— 该来源未被本闸门覆盖"
               % "、".join(_rs_src_empty))
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
            R.check("C9", "结果状态闭合", "FAIL",
                    "%d/%d 项结果未定案或字段值非法；%s"
                    % (len(_rs_bad), len(_rs_items), _rs_scope))
        elif _rs_src_empty:
            R.warn("C9", "来源 %s 已提供但零字段 —— 未被结果状态闸门覆盖，不得视为已核"
                   % "、".join(_rs_src_empty))
            R.check("C9", "结果状态闭合", "WARN",
                    "%d 项结果均已定案（settled），但**未覆盖**来源 %s —— %s"
                    % (len(_rs_items), "、".join(_rs_src_empty), _rs_scope))
        else:
            R.check("C9", "结果状态闭合", "PASS",
                    "%d 项结果均已定案（settled）；%s" % (len(_rs_items), _rs_scope))

    # ---------- C10 图签第二来源逐栋比对（2026-09-18 实跑新增，P1） ----------
    # 为什么需要它（实测依据，非设计偏好）：
    #   图纸画像把 titleblock_annotation 判为 present，并明确写出「后果与处置：图签可直读
    #   栋级入户规模 → 与采集表构成『三来源协议』的第二来源」。但**全流程没有任何环节去读它**：
    #   `ftth.py pipeline` 的阶段列表里没有它，C1~C9 也没有它。实测某图 7 栋楼的图签
    #   (单元数/层数/每层户数) 与系统图解析**逐栋一致**，可这条「独立来源互证」从未发生 ——
    #   属典型的「规则只写在文档里、没有代码执行它」。本项把比对落到可机械判定的检查项上。
    # 判据：逐栋比 (单元数, 层数, 每层户数)，楼栋按**楼号数字**归一化配对
    #   （图签写 `N号楼`、系统图写 `N#楼`，字符串不等但同一栋）。
    #   不一致即列双方数值交人裁定（L0-I4，禁止自动择一）；两侧楼号集合不同的也逐条列出。
    #   未提供 titleblock JSON 时判 SKIP 并写明「本次未做」，**不得判 PASS**。
    R.emit()
    R.emit("--- C10 图签第二来源逐栋比对 ---")
    TB = None
    if not args.titleblock_json:
        R.check("C10", "图签第二来源逐栋比对", "SKIP",
                "未提供 --titleblock（<outdir>/titleblock.json）—— 本次**未做**图签交叉校验，"
                "不等于已核；图上确无图签形态时属正常")
    else:
        try:
            with open(args.titleblock_json, "r", encoding="utf-8") as _tf:
                TB = json.load(_tf)
        except Exception as _te:                                     # noqa: BLE001
            R.check("C10", "图签第二来源逐栋比对", "SKIP",
                    "titleblock JSON 不可读（%s）—— 本次未做交叉校验" % _te)
            TB = None
    if args.titleblock_json and TB is not None:
        _tb_b = {}
        for _area, _bl in (TB.get("地块") or {}).items():
            for _bn, _bv in (_bl or {}).items():
                _k = bldg_num_or_none(_bn)
                if _k is not None:
                    _tb_b[_k] = {"楼": _bn, "单元数": (_bv or {}).get("单元数"),
                                 "层数": (_bv or {}).get("层数"),
                                 "每层户数": (_bv or {}).get("每层户数")}
        _p_b = {}
        for _bn, _bv in buildings.items():
            _k = bldg_num_or_none(_bn)
            if _k is None:
                continue
            _u = _bv.get("单元") or {}
            _best, _fc, _best_alt = None, [], None
            for _un, _uv in _u.items():
                # 「层数」只数**户数非空**的层：地下刻度行（户数 null）不计入，
                # 恰与图签 `N层` 的住宅层口径对齐（也是 C5 登记的那批行）。
                _vals = [int(_x["户数"]) for _x in ((_uv or {}).get("楼层表") or {}).values()
                         if isinstance((_x or {}).get("户数"), int)]
                # 图标法回退（2026-09-19 实测小区甲：户数全空 ⇒ 层数=None ⇒ 与图签必假 FAIL）：
                # 户数一列全空时，层数改取**地上刻度行数**（数字前缀为正的键），
                # 地下/夹层（B\d、-\d、W 前缀）不计，住宅层口径与图签仍对齐。
                # 有任何户数非空则维持原口径（已与凤鸣朝阳图签逐栋验证一致，不得改动）。
                _keys = list(((_uv or {}).get("楼层表") or {}).keys())
                _alt = sum(1 for _f in _keys
                           if re.match(r'^\s*(\d+)', str(_f)) and not re.match(r'^\s*[-BWW]', str(_f)))
                if _vals:
                    _fc.append(len(_vals))
                    if _best is None or len(_vals) > len(_best):
                        _best = _vals
                if _best_alt is None or _alt > _best_alt:
                    _best_alt = _alt
            if _best is not None:
                _p_b[_k] = {"楼": _bn, "单元数": len(_u), "层数": len(_best),
                            "每层户数": max(set(_best), key=_best.count),
                            "各单元层数": sorted(set(_fc))}
            elif _best_alt:
                _p_b[_k] = {"楼": _bn, "单元数": len(_u), "层数": _best_alt,
                            "每层户数": None, "层数口径": "地上刻度行数（图标法回退，无户数标注）"}
            else:
                _p_b[_k] = {"楼": _bn, "单元数": len(_u), "层数": None, "每层户数": None}
        if not _tb_b:
            R.check("C10", "图签第二来源逐栋比对", "SKIP",
                    "titleblock JSON 里没有任何楼栋读数（本图无图签形态？）—— 本次未做交叉校验")
        else:
            _diff, _both, _nonuni, _unver = [], 0, [], []
            for _k in sorted(set(_tb_b) | set(_p_b)):
                _t, _p = _tb_b.get(_k), _p_b.get(_k)
                if _t is None:
                    _diff.append("楼%s：图签**无**此楼，系统图有（%s）" % (_k, _p["楼"]))
                    continue
                if _p is None:
                    _diff.append("楼%s：系统图**无**此楼，图签有（%s）" % (_k, _t["楼"]))
                    continue
                _both += 1
                # 字段级可比性（2026-09-19 实测小区甲 r4：15 处「不一致」里 11 处是
                # 单侧不可读被当矛盾——图标法系统图不标户数 ⇒ None vs 图签有值 ⇒ 假 FAIL，
                # 把真矛盾淹没）。判据：**双非空且不等**才算矛盾；
                # 单侧 None = 「无法比对」，单独登记、不计 FAIL、不冒充已核。
                for _f in ("单元数", "层数", "每层户数"):
                    _tv, _pv = _t.get(_f), _p.get(_f)
                    if _tv is None or _pv is None:
                        _unver.append("楼%s %s（图签=%s，系统图=%s）"
                                      % (_k, _f, _tv, _pv))
                    elif _tv != _pv:
                        _diff.append("楼%s（图签 %s / 系统图 %s）：%s 图签=%s，系统图=%s"
                                     % (_k, _t["楼"], _p["楼"], _f, _tv, _pv))
                if len(_p.get("各单元层数") or []) > 1:
                    _nonuni.append("楼%s 各单元层数不一致 %s（本项取层数最多的单元比对）"
                                   % (_k, _p["各单元层数"]))
            for _d in _diff[:30]:
                R.emit("  x " + _d)
            for _d in _nonuni[:10]:
                R.emit("  ! " + _d)
            for _d in _unver[:15]:
                R.emit("  ? " + _d + " —— 单侧不可读，无法比对（不计矛盾）")
            if _diff:
                _note = ("；另有 %d 处单侧不可读未核" % len(_unver)) if _unver else ""
                R.check("C10", "图签第二来源逐栋比对", "FAIL",
                        "%d 处不一致（共同楼栋 %d）—— 图签与系统图矛盾，按 L0-I4 停下交人裁定，"
                        "**禁止自动择一**；双方数值见上%s" % (len(_diff), _both, _note))
                for _d in _diff[:20]:
                    R.fail("C10", _d)
            elif _unver:
                # 没核不得呈现成通过：可比字段全一致、但存在单侧不可读字段 ⇒ WARN。
                R.check("C10", "图签第二来源逐栋比对", "WARN",
                        "可比字段逐栋一致（共同楼栋 %d）；另有 %d 处**单侧不可读**未核"
                        "（系统图标法户数 / 图签缺项），不冒充已核，见上" % (_both, len(_unver)))
            elif _both == 0:
                # 防御分支：两侧都有楼栋读数、却按楼号归一化后零交集 —— 说明楼名里取不出
                # 数字（如 `甲号楼`），此时**没有可比对的共同楼栋**，不得判 PASS。
                R.check("C10", "图签第二来源逐栋比对", "SKIP",
                        "图签 %d 栋 / 系统图 %d 栋，按楼号归一化后共同楼栋为 0 —— "
                        "未形成有效比对（空集合不得判 PASS）" % (len(_tb_b), len(_p_b)))
            else:
                _notes = "；另有 %d 个单元层数不一致的楼（" % len(_nonuni) if _nonuni else ""
                R.check("C10", "图签第二来源逐栋比对", "PASS",
                        "%d 栋的 (单元数 / 层数 / 每层户数) 与系统图逐栋一致%s%s"
                        % (_both, _notes, "）" if _nonuni else ""))

    # ---------- 汇总 ----------
    R.emit()
    R.emit("=" * 72)
    R.emit("汇总：FAIL %d 项 / WARN %d 项" % (len(R.fails), len(R.warns)))
    for f in R.fails:
        R.emit("  ✗ %s" % f)
    for w in R.warns:
        R.emit("  ! %s" % w)
    rc = 2 if R.fails else 0
    R.emit("退出码 %d（%s）" % (rc, "存在 FAIL，不得出表" if rc else "无 FAIL，可进入后续自检"))
    R.emit("=" * 72)

    if args.json_out:
        payload = {"parse": args.parse_json, "coverage": args.coverage_json, "geom": args.geom_json,
                   "count_box": args.count_box_json, "titleblock": args.titleblock_json,
                   "checks": R.checks, "fails": R.fails, "warns": R.warns, "rc": rc}
        # 2026-09-18：写产物前先建父目录。此前未建 —— 目标目录不存在时 open() 直接
        #   Traceback（实测 rc=1、不落任何产物，且报错点远离调用处，排查成本高）。
        #   工具链内其余 16 个写产物的脚本均已做（os.makedirs / ensure_parent），
        #   本脚本是唯一漏网的（全量扫描得出，非只修报出来的那一个）。
        _parent = os.path.dirname(os.path.abspath(args.json_out))
        if _parent:
            os.makedirs(_parent, exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print("机读结果 ->", args.json_out)
    return rc


if __name__ == "__main__":
    sys.exit(main())