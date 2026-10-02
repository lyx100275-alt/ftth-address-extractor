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
    0 = 无 FAIL（WARN/INFO 不影响）；2 = 存在 FAIL 项，不得出表（与L1-C2的2同码异义，此处2=门禁拦下）；1 = 保留值，当前无发射点（输入/解析错误统一走2）。

与 verify_coverage_truth.py 的分工：
    本脚本用于**出表前**（无需 xlsx，查 parse/coverage/geom 三源闭合）；
    verify_coverage_truth 用于**有定稿标准地址表之后**的回归反查。阶段不同，不重叠。
"""
import argparse
from ftth_common import bldg_num_or_none  # 楼号提取：失败返 None（勿与 bldg_num 失败返 0 混用）
from ftth_common import is_bldg_level_container  # 楼栋级兜底容器判据（全技能唯一实现）
from ftth_common import floor_num  # 楼层归一统一入口（B1/B2/WF/3F/-1F），2026-09-25 P1-10
from ftth_common import norm_floor  # 全技能唯一实现（2026-09-27收敛双副本，含室剥离+N层回退）
# 覆盖判定依据的机器词表唯一来源（2026-09-27 P0-3）：本模块只引用，不另抄一份。
from ftth_common import coverage_method_of, COVERAGE_METHODS  # C6 判定依据枚举校验
import json
import os
import re
import sys
from collections import Counter, OrderedDict
from ftth_common import ensure_console_utf8, write_json, sha256_file
from conflict_engine import (  # V3 Conflict 层：议题构造与纯集合运算唯一入口（只产议题、不定案）
    collect_fxmap_gap, fxmap_issues, collect_unassigned,
    floor_mismatch_issue, run_c9, summarize as summarize_issues,
    issue as _new_issue, ISSUE_MISSING_RECORD, ISSUE_FLOOR_MISMATCH)

ensure_console_utf8()


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


def _c7_one_line(it):
    """C7「需人工裁决」单条压成一行（对象｜事项｜说明）。

    2026-09-25（云峰实跑 + opencode 审核返工）：原实现把整条 json.dumps 后 [:80]
    截断进 warns（inspect.json 机读出口）——80 字符恰把残差/阈值/「需人工裁决」
    结论切在 JSON 字符串中间，用户裁决失去关键信息（coverage.json 里明明是全文）。
    格式纪律：**展示层可截（防刷屏）、机读层不截**；非 dict 条目回退全量 json.dumps
    （老产物/异构字段不因结构化取值而丢内容）。
    """
    if isinstance(it, dict):
        # 2026-09-26（一百零二·评估项 7）：「对象」可为列表（同形态合并后的图级汇总，
        #   承载全部单元对象串；judge_pending_scope 逐个匹配，机读不受影响）—— 展示层
        #   join 显示。仅展示层改动，机读层（warns 全量）不动。
        _obj = it.get("对象")
        if isinstance(_obj, (list, tuple)):
            obj = "、".join(str(o) for o in _obj)
        else:
            obj = str(_obj or "").strip()
        task = str(it.get("事项") or "").strip()
        note = str(it.get("说明") or "").strip()
        if obj or task or note:
            return "对象=%s｜事项=%s｜说明=%s" % (obj or "?", task or "?", note or "?")
    return json.dumps(it, ensure_ascii=False)


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
    ap.add_argument("--fx-pattern", default=r"FL\d+-FX\d+", help="分纤箱编号正则（仅哨兵：未显式给出时改读parse产物自带值，见下；禁直接用于匹配）")
    ap.add_argument("--titleblock", dest="titleblock_json", default=None,
                    help="read_titleblock_households.py 输出的图签读数 JSON（可选）。"
                         "提供后 C10 做「图签 vs 系统图」逐栋互证；不提供则 C10 判 SKIP"
                         "（写明本次未做交叉校验，不得当作已核）")
    ap.add_argument("--fx-map", dest="fx_map_json", default=None,
                    help="总图 FX 对照表 JSON（extract_fx_map.py 产物，可选）。"
                         "parse floor-mode=nofloor 时 C3 改比 coverage vs 对照表，需本输入；"
                         "不提供则 C3-nofloor 判 SKIP（写明本次未做交叉校验，不得当作已核）")
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
    # 2026-09-30（一百三十一，V3 Conflict）：机读冲突议题出口（只追加、不参与 rc）。
    #   各门禁判据/文案一律不动；议题由 conflict_engine 纯构造，issue_id 确定性去重。
    conflict_issues = []
    _seen_issue_ids = set()

    def _track_issues(new_issues):
        for _it in (new_issues or []):
            _iid = str((_it or {}).get("issue_id") or "")
            if _iid and _iid not in _seen_issue_ids:
                _seen_issue_ids.add(_iid)
                conflict_issues.append(_it)
    # 2026-09-25（评审 P0-4）：以下输入类错误按 L1-C2 应为 rc=2（补探查/须修），
    #   不是 rc=1（会被读成「脚本坏了」）。全部 return 1 → return 2。
    try:
        P = json.load(open(args.parse_json, encoding="utf-8"))
    except Exception as e:
        print("parse JSON 读取失败：%s" % e)
        return 2
    C = None
    if args.coverage_json:
        try:
            C = json.load(open(args.coverage_json, encoding="utf-8"))
        except Exception as e:
            print("coverage JSON 读取失败：%s" % e)
            return 2
    G = None
    if args.geom_json:
        try:
            G = json.load(open(args.geom_json, encoding="utf-8"))
        except Exception as e:
            print("geom JSON 读取失败：%s" % e)
            return 2
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
            return 2
        try:
            K = json.load(_cbf)
        except Exception as e:
            print("count-box JSON 解析失败：%s" % e)
            return 2
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
    R.emit("coverage : %s" % (args.coverage_json or "（未提供，C3 跳过；C6 按覆盖零产出判 FAIL）"))
    R.emit("geom     : %s" % (args.geom_json or "（未提供，C4 跳过）"))
    R.emit("count-box: %s" % (args.count_box_json or "（未提供）"))
    R.emit("fx-map   : %s" % (args.fx_map_json or "（未提供，C3-nofloor 不可核）"))
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
        _uk = list((bv.get("单元") or {}).keys())
        # 楼栋级兜底容器**不计入「单元」**（判据见 ftth_common.is_bldg_level_container）：
        #   它是 parse 侧为「单元号在图上单元轴里找不到容器」的箱单开的承载容器，
        #   键就是楼栋名，与楼层表不同键、已登记需人工裁决 —— 不是图上画出的单元。
        _fb = [u for u in _uk if is_bldg_level_container(u, blk)]
        ulist = [u for u in _uk if u not in _fb]
        nfx = sum(len((bv.get("单元") or {})[u].get("分纤箱") or []) for u in _uk)
        _note = ("（另有楼栋级兜底容器「%s」：承载单元号对不上的箱，已登记需人工裁决，"
                 "不计入单元数）" % "/".join(_fb)) if _fb else ""
        R.emit("  %-6s 单元 %d 个（%s） 分纤箱 %d 个%s"
               % (blk, len(ulist), "/".join(ulist) or "无", nfx, _note))
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

    # 2026-09-30（一百三十二，V3 Phase A）：parse 去决策标记（C2/C3 双模式开关）。
    #   full（默认；老产物无该键按 full）走 legacy 逐字节老路；nofloor 走新分支。
    _parse_nofloor = (str(((P.get("参数") or {}) if isinstance(P, dict) else {}).get("floor_mode")
                          or "full").strip().lower() == "nofloor")

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
    if _parse_nofloor:
        # 2026-09-30（一百三十二）：parse 去决策——parse 侧 null 是声明行为，不拦；
        #   改核 coverage 侧安装楼层（判据与 legacy 同形：null 即 FAIL，空集不得 PASS）。
        _cov_null = []
        _cov_n = 0
        for _blk2, _bv2 in ((C.get("楼栋") or {}).items() if isinstance(C, dict) else []):
            for _un2, _uv2 in (((_bv2 or {}).get("单元") or {}).items()):
                for _fx2 in (((_uv2 or {}).get("分纤箱") or [])):
                    _cov_n += 1
                    if _fx2.get("安装楼层") is None:
                        _cov_null.append((_blk2, _un2, _fx2.get("编号")))
        if C is None:
            R.check("C2", "安装楼层口径分布", "SKIP",
                    "parse 去决策（floor-mode=nofloor）且未提供 coverage —— "
                    "安装楼层无来源可核，不得读作已核")
        elif _cov_n == 0:
            R.check("C2", "安装楼层口径分布", "FAIL",
                    "parse 去决策（floor-mode=nofloor），coverage 侧 0 箱，"
                    "无安装楼层口径可核（空集合不得判 PASS）")
        elif _cov_null:
            for _blk2, _un2, _fid2 in _cov_null[:20]:
                R.emit("  ✗ %s/%s/%s coverage 侧安装楼层=null" % (_blk2, _un2, _fid2))
                R.fail("C2", "%s/%s/%s coverage 侧安装楼层未关联" % (_blk2, _un2, _fid2))
            R.check("C2", "安装楼层口径分布", "FAIL",
                    "coverage 侧 %d/%d 箱安装楼层未关联（parse 去决策，本项核 coverage 侧）"
                    % (len(_cov_null), _cov_n))
        else:
            R.check("C2", "安装楼层口径分布", "PASS",
                    "coverage 侧 %d/%d 箱均有安装楼层（parse 去决策，本项核 coverage 侧）"
                    % (_cov_n, _cov_n))
    elif null_boxes:
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
    # 2026-09-30（一百三十二）：cmap（coverage 箱索引）是 C3-legacy 与 C6 共用的；
    #   nofloor 分支改比 coverage vs 对照表、不消费它，但 C6 在两种模式下都要——
    #   故在此统一构建，与门禁分支无关（构建内容与原 legacy 内联逐字一致）。
    cmap = {}
    if C is not None:
        for blk, bv in (C.get("楼栋") or {}).items():
            for un, uv in (bv.get("单元") or {}).items():
                for fx in (uv.get("分纤箱") or []):
                    cmap.setdefault(fx.get("编号"), []).append(
                        (blk, un, fx.get("安装楼层"),
                         (fx.get("覆盖范围线索") or {}).get("覆盖楼层"),
                         fx.get("判定依据"),
                         fx.get("安装楼层统一") or {}))
    # 2026-09-30（一百三十，V3 Evidence）：parse 侧统一楼层上下文索引
    #   （只读展示用；comparison 判据仍是 legacy 安装楼层归一值，不动）。
    punified = {}
    for _blk, _bv in (buildings.items()):
        for _un, _uv in ((_bv.get("单元") or {}).items()):
            for _fx in ((_uv.get("分纤箱") or [])):
                _fid2 = _fx.get("编号")
                if _fid2 and _fid2 not in punified:
                    _pu = _fx.get("安装楼层统一") or {}
                    punified[_fid2] = (_pu.get("coordinate_context"),
                                       _pu.get("installation_floor_source"))
    if _parse_nofloor:
        # 2026-09-30（一百三十二）：parse 去决策——parse 腿摘掉，改比
        #   coverage vs 总图对照表（--fx-map）。判据与 legacy 同形，仍 FAIL 拦下；
        #   跨体系差值疑似假冲突（V3§8），须先确认语义再裁决，不得自动择一。
        R.emit("  i parse 去决策（floor-mode=nofloor）：本项改比 coverage vs 总图对照表")
        _fxmap_obj = None
        if args.fx_map_json:
            try:
                _fxmap_obj = json.load(open(args.fx_map_json, encoding="utf-8"))
            except Exception as e:
                print("fx-map JSON 读取失败：%s" % e)
                return 2
        _fmap = {}
        if isinstance(_fxmap_obj, dict):
            for _fe in (_fxmap_obj.get("FX映射表") or []):
                if isinstance(_fe, dict) and str(_fe.get("编号") or "").strip():
                    _fno = str(_fe["编号"]).strip()
                    if _fno not in _fmap:
                        _fmap[_fno] = (_fe.get("安装楼层"), _fe.get("安装楼层统一") or {})
        if C is None:
            R.check("C3", "安装楼层双源交叉", "SKIP", "未提供 coverage JSON")
        elif _fxmap_obj is None:
            R.check("C3", "安装楼层双源交叉", "SKIP",
                    "parse 去决策（floor-mode=nofloor）但未提供 --fx-map 对照表 —— "
                    "双源交叉不可核，不得读作已核")
            R.warn("C3", "parse 去决策但未提供 --fx-map —— coverage 侧安装楼层未经第二来源交叉验证")
        else:
            _n3_ok = _n3_bad = _n3_miss = _n3_tot = 0
            for _blk3, _bv3 in (C.get("楼栋") or {}).items():
                for _un3, _uv3 in ((_bv3 or {}).get("单元") or {}).items():
                    for _fx3 in ((_uv3 or {}).get("分纤箱") or []):
                        _fid3 = _fx3.get("编号")
                        _cfl3 = _fx3.get("安装楼层")
                        _cu3 = _fx3.get("安装楼层统一") or {}
                        _frec = _fmap.get(_fid3) if _fid3 else None
                        _n3_tot += 1
                        if _frec is None:
                            R.emit("  ✗ %s（%s/%s）对照表中无记录" % (_fid3, _blk3, _un3))
                            R.fail("C3", "%s 对照表无记录" % _fid3)
                            _track_issues([_new_issue(
                                ISSUE_MISSING_RECORD, "%s（%s/%s）" % (_fid3, _blk3, _un3),
                                candidates=["coverage有记录", "对照表无记录"],
                                evidence=["总图对照表缺 %s" % _fid3],
                                note="一侧无记录，无法双源交叉，须人工确认")])
                            _n3_miss += 1
                            continue
                        _ffl3, _fu3 = _frec
                        _cctx3 = _cu3.get("coordinate_context")
                        _fctx3 = (_fu3 or {}).get("coordinate_context")
                        if norm_floor(_cfl3) == norm_floor(_ffl3):
                            _n3_ok += 1
                        else:
                            R.emit("  ✗ %s（%s/%s）coverage=%s[%s] vs 对照表=%s[%s]" % (
                                _fid3, _blk3, _un3, _cfl3, _cctx3 or "legacy",
                                _ffl3, _fctx3 or "legacy"))
                            if _cctx3 and _fctx3 and _cctx3 != _fctx3:
                                R.emit("    疑似假冲突：两侧分属不同坐标语义体系（V3§8）——"
                                       "须先确认语义是否同一再裁决")
                            R.fail("C3", "%s 安装楼层双源不一致 coverage=%s 对照表=%s"
                                   % (_fid3, _cfl3, _ffl3))
                            _track_issues([_new_issue(
                                ISSUE_FLOOR_MISMATCH, "%s（%s/%s）" % (_fid3, _blk3, _un3),
                                candidates=["coverage=%s" % _cfl3, "对照表=%s" % _ffl3],
                                evidence=["coverage坐标系=%s" % (_cctx3 or "legacy"),
                                          "对照表坐标系=%s" % (_fctx3 or "legacy")],
                                note="安装楼层双源不一致；跨坐标体系差值疑似假冲突（V3§8），"
                                     "须先确认语义再裁决")])
                            _n3_bad += 1
            if not boxes:
                R.check("C3", "安装楼层双源交叉", "FAIL",
                        "parse 侧 0 箱，双源无交集可核（空集合不得判 PASS）")
            elif _n3_tot == 0:
                R.check("C3", "安装楼层双源交叉", "FAIL",
                        "coverage 侧 0 箱，双源无交集可核（空集合不得判 PASS）")
            else:
                _st3 = "PASS" if (_n3_bad == 0 and _n3_miss == 0) else "FAIL"
                R.check("C3", "安装楼层双源交叉", _st3,
                        "一致 %d / 不一致 %d / 无记录 %d（coverage 共 %d 箱）"
                        % (_n3_ok, _n3_bad, _n3_miss, _n3_tot))
    elif C is None:
        R.check("C3", "安装楼层双源交叉", "SKIP", "未提供 coverage JSON")
    else:
        # cmap/punified 已在分支外统一构建（见上；C6 共用），此处只跑门禁循环。
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
                # 2026-09-30（一百三十一）：无记录议题入机读出口（判据不动）。
                _track_issues([_new_issue(
                    ISSUE_MISSING_RECORD, "%s（%s/%s）" % (fid, blk, un),
                    candidates=["parse有记录", "coverage无记录"],
                    evidence=["coverage箱级记录缺 %s" % fid],
                    note="一侧无记录，无法双源交叉，须人工确认")])
                n_miss += 1
                continue
            cfl_vals = {norm_floor(r[2]) for r in recs}
            if norm_floor(fl) in cfl_vals:
                n_ok += 1
            else:
                # 2026-09-30（一百三十，V3 §8）： mismatch 时带出双方坐标语义体系。
                #   跨体系差值（总图 vs 系统图/区间/V型）疑似假冲突——须先确认语义
                #   是否同一再裁决，不得自动择一。判据不动（仍 FAIL），只丰富指引；
                #   双方皆无统一字段的老产物走原报文（逐字节不变）。
                _pctx, _psrc = punified.get(fid, (None, None))
                _cctxs = sorted({str((r[5] or {}).get("coordinate_context") or "legacy")
                                 for r in recs})
                if _pctx or _cctxs != ["legacy"]:
                    R.emit("  ✗ %s（%s/%s）parse=%s[%s/%s] vs coverage=%s[%s]" % (
                        fid, blk, un, fl, _pctx or "legacy", _psrc or "?",
                        "/".join(str(r[2]) for r in recs), "/".join(_cctxs)))
                    if _pctx and "legacy" not in _cctxs and _pctx not in _cctxs:
                        R.emit("    疑似假冲突：两侧分属不同坐标语义体系（V3§8：总图对照表与"
                               "系统图/区间/V型不是同一坐标系）——须先确认语义是否同一再裁决")
                else:
                    R.emit("  ✗ %s（%s/%s）parse=%s vs coverage=%s" % (
                        fid, blk, un, fl, "/".join(str(r[2]) for r in recs)))
                R.fail("C3", "%s 安装楼层双源不一致 parse=%s coverage=%s" % (fid, fl, [r[2] for r in recs]))
                # 2026-09-30（一百三十一）：双源不一致议题入机读出口（C3 自身 FAIL 判据不动）。
                _track_issues([floor_mismatch_issue(
                    fid, blk, un, fl, _pctx, _psrc,
                    [r[2] for r in recs], _cctxs)])
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
    unassigned_ids = []
    for _u in ((P.get("未归属分纤箱") or []) if isinstance(P, dict) else []):
        _fid_u0 = str((_u or {}).get("编号") or "").strip()
        if _fid_u0:
            unassigned_ids.append(_fid_u0)
    # 2026-09-30（一百三十一）：未归属议题入机读出口（C4 自身 WARN/FAIL 判据不动）。
    _track_issues(collect_unassigned((P.get("未归属分纤箱") or [])
                                     if isinstance(P, dict) else []))
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
        #   （unassigned_ids 已在 C4 前预计算，此处直接复用，不重置。）
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

    # ---------- C4b 对照表对账硬门禁（2026-09-30，一百二十八，云峰P0-1） ----------
    # 根因：fxmap 识别 23/23，但 parse 只进 16 箱，7 箱丢在改派漏斗（单元容器缺失/
    #   重号配对超差/楼栋锚点未命中），旧 C4 只按 geom 双向差集核对 —— 未归属计入
    #   parse_ids 后差集为 0，仅 WARN 放行，rc 仍 0（静默丢数）。
    # 门禁：当 parse 产物带 BDGMAP归属（即本轮传了 --bldg-map/对照表）时，
    #   `对照表唯一编号 == parse已归属编号数 + 未归属编号数` 必须成立，且未归属必须为 0；
    #   否则 FAIL 禁止出表，并逐号点名缺失项。无 BDGMAP 时 SKIP（不改变旧行为）。
    R.emit()
    R.emit("--- C4b 对照表对账（fxmap→parse 硬门禁） ---")
    _bdg = (P.get("BDGMAP归属") or {}) if isinstance(P, dict) else {}
    _exp_list = _bdg.get("对照表编号清单") or []
    _exp_n = _bdg.get("唯一编号")
    if not _bdg or (_exp_n is None and not _exp_list):
        R.check("C4b", "对照表对账", "SKIP", "parse 未带 BDGMAP归属（本轮未传 --bldg-map），不做对照表对账")
    else:
        # 2026-09-30（一百三十一）：集合运算走冲突引擎（collect_fxmap_gap），
        #   下文分支只消费 gap 字段作门禁，报文逐字节不变。
        #   旧产物只有计数无清单时，退化为计数核对（无法点名，仅判数量）。
        _gap = collect_fxmap_gap(
            _exp_list, _exp_n,
            [f for _b, _u, f, *_r in boxes],
            unassigned_ids)
        _track_issues(fxmap_issues(_gap))
        _n_asg = int(_gap.get("assigned") or 0)
        _un_sorted = list(_gap.get("unassigned") or [])
        _un_set = set(_un_sorted)
        if _gap.get("mode") == "清单":
            _missing = list(_gap.get("missing") or [])
            _extra = list(_gap.get("extra") or [])
            if _missing or _extra or _un_set:
                for _m in _missing[:20]:
                    R.emit("  ✗ 对照表有、parse 无：%s" % _m)
                    R.fail("C4b", "%s 对照表有、parse 无（改派漏斗丢失）" % _m)
                for _e in _extra[:20]:
                    R.emit("  ✗ parse 有、对照表无：%s" % _e)
                    R.fail("C4b", "%s parse 有、对照表无" % _e)
                if _un_set and not _missing:
                    for _u in sorted(_un_set)[:20]:
                        R.emit("  ✗ 对照表有、parse 未归属：%s" % _u)
                    R.fail("C4b", "%d 个编号未归属（%s）—— 对照表已定归属、parse 未落位，不得出表"
                           % (len(_un_set), "、".join(sorted(_un_set)[:12])))
                R.check("C4b", "对照表对账", "FAIL",
                        "对照表 %d / parse已归属 %d / 未归属 %d；缺失 %d、多余 %d"
                        % (int(_gap.get("expected") or 0), _n_asg, len(_un_set),
                           len(_missing), len(_extra)))
            else:
                R.check("C4b", "对照表对账", "PASS",
                        "对照表 %d == parse已归属 %d + 未归属 0" % (int(_gap.get("expected") or 0), _n_asg))
        else:
            # 无清单旧产物：只核计数
            if _gap.get("mode") == "无":
                R.check("C4b", "对照表对账", "SKIP", "BDGMAP归属无唯一编号/清单，无法对账")
            elif _gap.get("aligned"):
                R.check("C4b", "对照表对账", "PASS",
                        "对照表 %d == parse已归属 %d + 未归属 0" % (int(_gap.get("expected") or 0), _n_asg))
            else:
                _exp_n = int(_gap.get("expected") or 0)
                R.emit("  ✗ 对照表 %d / parse已归属 %d / 未归属 %d（数量不对齐）"
                       % (_exp_n, _n_asg, len(_un_set)))
                R.fail("C4b", "对照表与parse数量不对齐（对照表 %d，parse %d+未归属 %d）"
                       % (_exp_n, _n_asg, len(_un_set)))
                if _un_set:
                    R.fail("C4b", "%d 个编号未归属（%s）—— 不得出表"
                           % (len(_un_set), "、".join(sorted(_un_set)[:12])))
                R.check("C4b", "对照表对账", "FAIL",
                        "对照表 %d / parse已归属 %d / 未归属 %d"
                        % (_exp_n, _n_asg, len(_un_set)))

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
    # 2026-09-26（第4轮 Bug B）：皮线回落路径出现后，直读 SKIP 若 count-box 已有归层户数则改述来源（判定语义不动）。
    _cb_has_hu = (isinstance(K, dict) and isinstance(K.get("归层后总户数"), (int, float))
                  and K.get("归层后总户数") > 0)
    _cb_src = ("直读侧无户数可核；户数已由 count-box 提供（口径=%s，归层合计 %s 户）"
               % (K.get("口径"), K.get("归层后总户数"))) if _cb_has_hu else None
    if n_rows_total == 0:
        R.check("C5", "楼层表直读清单", "SKIP",
                _cb_src if _cb_src else
                ("全图 %d 个单元的楼层表均无任何非空行（户数/布线两列皆空）——"
                 "本图户数须由图标法（count-box）提供；不得读作合计 0" % len(units)))
    elif n_hu_total == 0:
        R.check("C5", "楼层表直读清单", "SKIP",
                _cb_src if _cb_src else
                ("楼层表共 %d 个非空行，但「户数」列全空 —— 本图户数须由图标法（count-box）提供；"
                 "不得把「没有户数列」读作「合计 0」" % n_rows_total))
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

    # ---------- C5·count-box 质量透传（2026-09-25 云峰实跑 + opencode 审核返工）----------
    # 为什么放 C5：C5 的语义就是「每层户数从哪来、可信吗」。云峰实测 parse 楼层表
    #   全空 → C5 SKIP 说「户数须由图标法提供」，但 count_box.json 里的四类质量告警
    #   （乘号式标注 / 刻度偏移异常 / 共用刻度列 / 同一端点多候选）此前没有任何
    #   inspect 出口——复用轮连 count_box.log 都不打印。扩展 C5 而非新增检查 ID：
    #   SKILL.md 的 C1~C10 名目不能扩（体量红线）。
    # 级别（2026-09-27 用户裁决后调整）：**四类一律 WARN** —— 乘号式 `*N` 标注原按
    #   "未裁决乘数"判 FAIL，现改判为「该处 N 户」的**直读**形态（不再是待裁决项），
    #   其 FAIL 依据随之消失，降为登记性 WARN；其余三类本就 WARN（须复核不阻塞）。
    #   C2 的 parse-0-箱分支另有偏移异常 FAIL，此处覆盖 parse 有箱的常规路径。
    # 格式纪律（与 C7 同一标准）：计数 + 单条不截断 + 明细指针 count_box.json。
    if K is not None:
        _cb_m = K.get("乘号式户数标注") or []
        _cb_o = K.get("刻度偏移异常列") or []
        _cb_s = K.get("共用刻度列组") or []
        _cb_d = K.get("同一端点多候选") or []
        _cb_u = K.get("未归属图标数") or 0
        if _cb_m or _cb_o or _cb_s or _cb_d or _cb_u:
            R.emit()
            _cb_tag = ("count-box（皮线回落）质量告警"
                       if "皮线回落" in str((K or {}).get("口径") or "")
                       else "count-box（图标法）质量告警")
            R.emit("  %s：乘号式标注 %d / 偏移异常列 %d / 共用刻度列组 %d / "
                   "多候选 %d / 未归属 %d；归层后总户数 %s"
                   % (_cb_tag, len(_cb_m), len(_cb_o), len(_cb_s), len(_cb_d), _cb_u,
                      K.get("归层后总户数")))
            for _x in _cb_m[:20]:
                R.emit("    i 乘号式户数标注：%s @(%s, %s) 图层=%s —— 乘号后数字即该处户数"
                       "（属直读形态），不由图标法消费" % (_x.get("标注"), _x.get("x"),
                                                          _x.get("y"), _x.get("图层")))
            for _x in _cb_o[:20]:
                R.emit("    ! 偏移异常列：列x=%s 偏移=%s —— %s"
                       % (_x.get("列x"), _x.get("刻度偏移"), _x.get("说明")))
            for _x in _cb_s[:20]:
                R.emit("    ! 共用刻度列：刻度列x=%s ← 图标列 %s"
                       % (_x.get("刻度列x"), "、".join(str(v) for v in (_x.get("图标列x") or []))))
            if len(_cb_m) > 20:
                R.emit("    ... 另有 %d 处乘号式标注未列出（明细见 count_box.json）" % (len(_cb_m) - 20))
            if len(_cb_o) > 20:
                R.emit("    ... 另有 %d 列偏移异常未列出（明细见 count_box.json）" % (len(_cb_o) - 20))
            if _cb_o:
                R.warn("C5", "图标法刻度偏移异常列 %d 个（列x=%s）—— 该列归层不可信，须人工"
                       "核对后重跑（可显式 --col-scale-map / --scale-max-dx）"
                       % (len(_cb_o), "、".join(str(x.get("列x")) for x in _cb_o[:8])))
            if _cb_s:
                R.warn("C5", "图标法共用刻度列组 %d 组 —— 「一条刻度列服务多个图标列」形态下"
                       "几何最近配对不可靠，须人工核对归属" % len(_cb_s))
            # E1（2026-09-27）：把「合计里有多少户是不可信的」送到人工清单 ——
            #   count_box 侧只登记列级不可信，合计字段若不带构成，下游会把待核对当已核消费。
            _cb_hh = K.get("户数构成") or {}
            _cb_nd = _cb_hh.get("待核对户数")
            if isinstance(_cb_nd, int) and _cb_nd > 0:
                R.warn("C5", "归层后总户数 %s 户中有 %d 户落在自述不可信的列上"
                             "（刻度偏移异常列 / 共用刻度列组）—— 合计**未剔除**这些户"
                             "（剔除=丢解），但人工核对前不得当作已核户数消费；"
                             "明细见 count_box.json「户数构成」"
                       % (K.get("归层后总户数"), _cb_nd))
            if _cb_d:
                R.warn("C5", "图标法同一端点多候选 %d 处 —— 须人工复核是否重复绘制" % len(_cb_d))
            if _cb_u:
                R.warn("C5", "图标法未归属图标 %d 个 —— 不计入任何列，已登记待确认" % _cb_u)
            R.check("C5", "楼层表直读清单", "WARN",
                    "图标法质量告警：乘号式标注%d/偏移异常%d/共用刻度%d/多候选%d/未归属%d；"
                    "归层后总户数 %s（其中待核对 %s 户）；明细见 count_box.json"
                    % (len(_cb_m), len(_cb_o), len(_cb_s), len(_cb_d), _cb_u,
                       K.get("归层后总户数"),
                       _cb_nd if isinstance(_cb_nd, int) else "?"))

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
                _cb_src if _cb_src else
                ("无单元可核（「有效层数 ≥3 且户数非空」的单元数 = 0）——"
                 "空集合不得判 PASS；本图户数须由图标法（count-box）提供"))
    else:
        R.check("C8", "同单元跨层户数一致性", "PASS",
                "%d 个单元各层户数一致（有效层数不足 3 的单元未纳入）" % c8_units)

    # ---------- C6 覆盖闭合 ----------
    R.emit()
    R.emit("--- C6 覆盖闭合（parse × coverage） ---")
    if C is None:
        # 2026-09-25（一百零一，问题 2 方案 B）：覆盖判定是解析阶段的独立必做步骤
        #   （SKILL.md 测量方式架构；L1-C8 静默放行禁令）—— parse 有箱而 coverage
        #   未提供 ⇒ 覆盖零产出，不得 SKIP 放行，判 FAIL 拦下（rc=2 输入不足/须修，
        #   非 rc=3 合法缺席）。boxes 为空时无对象可判，沿用 SKIP（C0/_nobox 另有门禁）。
        if boxes:
            R.check("C6", "覆盖闭合", "FAIL",
                    "未提供 coverage JSON，但 parse 侧 %d 个箱的覆盖范围无任何结论 —— "
                    "覆盖判定独立必做步骤未产出（L1-C8 静默放行禁令）；须补做覆盖判定或列待确认项"
                    % len(boxes))
        else:
            R.check("C6", "覆盖闭合", "SKIP", "未提供 coverage JSON")
    else:
        n_ok = n_noclue = n_outof = 0
        n_badbasis = 0   # 2026-09-27（P0-3）：判定依据不在覆盖方法枚举内的箱数
        # 2026-09-19 修复（与 C3 同一条件、同一处置）：coverage 提供了 JSON，但**箱级
        #   记录为 0** 时，上面那个 `for blk, un, fid, ... in boxes` 循环里每个箱都会
        #   走到 `if not recs: continue` —— 循环体一次有效判定都没做，三个计数全 0，
        #   末行 `st = "PASS" if (n_noclue == 0 and n_outof == 0)` 于是输出
        #   「[PASS] 覆盖闭合 —— 闭合 0 / 缺线索 0 / 安装层越界 0」。
        #   这是**空集合判 PASS**：实测柳辛庄 1-4 地块四带全部命中，
        #   把「本图 0 个箱有任何覆盖线索」伪装成「覆盖全部闭合」——最隐蔽的一类静默丢数。
        #   2026-09-25（一百零一，问题 1 + 问题 2 方案 B）：本分支改为判 FAIL 并短路
        #   （else 结构保证单记录，不再落到末尾兜底行；此前 SKIP + WARN 后不短路，
        #   又追加一条「闭合 0/0/0」PASS——机读方按末条/存在 PASS 消费即把零覆盖读成
        #   闭合，正是 09-19 修复注释点名要防的形态）。零产出按 L1-C8 静默放行禁令
        #   判 FAIL（rc=2），不再是 SKIP。
        _cmap_n = 0
        for _blk0, _bv0 in (C.get("楼栋") or {}).items():
            for _un0, _uv0 in (_bv0.get("单元") or {}).items():
                _cmap_n += len(_uv0.get("分纤箱") or [])
        if boxes and _cmap_n == 0:
            R.check("C6", "覆盖闭合", "FAIL",
                    "coverage 提供了 JSON 但其箱级记录为 0 —— 覆盖闭合**无对象可核**"
                    "（空集合不得判 PASS）；parse 侧 %d 个箱的覆盖范围本图未产出，"
                    "覆盖判定须补做或列待确认项（L1-C8 静默放行禁令）" % len(boxes))
        else:
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
                # 2026-09-27（P0-3）：`判定依据` 必须**机器可枚举**（首段 ∈ COVERAGE_METHODS）。
                #   自由文本 = 机器不可判；实测同一脚本内并存「V型计算」/「V形计算」两种写法，
                #   下游按枚举解释即静默出错。空值同样 FAIL（如「判不了就写待确认」，不得留空）。
                #   词表唯一来源 ftth_common.COVERAGE_METHODS，本处只引用（禁另抄一份）。
                for _r in recs:
                    if coverage_method_of(_r[4]) is None:
                        R.emit("  ✗ %s（%s/%s）判定依据不可枚举：%r（须以 %s 之一开头）"
                               % (fid, blk, un, _r[4], "/".join(COVERAGE_METHODS)))
                        R.fail("C6", "%s 判定依据不在覆盖方法枚举内" % fid)
                        n_badbasis += 1
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
                st = "PASS" if (n_noclue == 0 and n_outof == 0 and n_badbasis == 0) else "FAIL"
                R.check("C6", "覆盖闭合", st,
                        "闭合 %d / 缺线索 %d / 安装层越界 %d / 判定依据不可枚举 %d"
                        % (n_ok, n_noclue, n_outof, n_badbasis))

    # ---------- C7 覆盖自检透传 ----------
    R.emit()
    R.emit("--- C7 coverage 顶层自检与需人工裁决（透传） ---")
    if C is None:
        R.check("C7", "覆盖自检透传", "SKIP", "未提供 coverage JSON")
    else:
        for k in ("自检_v底vs箱符号", "自检_v形单调性", "自检_偏差门禁"):
            if k in C:
                R.emit("  %s = %s" % (k, json.dumps(C[k], ensure_ascii=False)[:160]))
        pend = list(C.get("需人工裁决") or [])
        # 同一条疑点可能**两路都带**（coverage 常把 parse 侧登记原样透传）。不去重会把
        #   一条报成两条，人工清单虚增一倍、还会误以为是两个不同问题 —— 按 (对象, 事项) 去重。
        def _c7_key(it):
            if isinstance(it, dict):
                return (str(it.get("对象") or ""), str(it.get("事项") or ""))
            return (str(it), "")
        _seen_pend = set(_c7_key(it) for it in pend)
        # 2026-09-27（十五轮迭代 R2，缺陷 D3）：parse 侧登记的「需人工裁决」此前**不带出**
        #   —— C7 只读 coverage 的顶层键，parse 产物里登记了却进不了人工清单，等于
        #   「登记了疑点但拦不住结果」：人工按 inspect 报告裁决时会整批漏掉 parse 侧疑点
        #   （实测：单元号无轴可承载 4 项只存在于 parsed.json，C7 里一条都没有）。
        #   现两路合并带出，逐条标来源，人工一次看全。
        _ppend = []
        for it in (P.get("需人工裁决") or []):
            if _c7_key(it) in _seen_pend:
                continue          # coverage 已从 parse 透传了同一条 —— 不重复计、不重复报
            _seen_pend.add(_c7_key(it))
            _ppend.append(it)
        #   现两路合并、**一次循环**带出，逐条标来源（parse 来源加 [parse] 前缀），
        #   人工一次看全。注意：不可先循环 _ppend 再循环合并后的 pend —— 那会把 parse
        #   侧每条报两遍（一次带前缀、一次不带），人工清单虚增一倍（实测踩中）。
        _all = [(it, "") for it in pend] + [(it, "[parse] ") for it in _ppend]
        if _all:
            R.emit("  需人工裁决 %d 项（coverage %d / parse %d）："
                   % (len(_all), len(pend), len(_ppend)))
            for it, _src in _all:
                _full = _src + _c7_one_line(it)
                # 展示层可截（防刷屏，放宽到 300）；机读层（warns → inspect.json）不截断
                R.emit("    ! %s" % _full[:300])
                R.warn("C7", "需人工裁决：%s" % _full)
            R.check("C7", "覆盖自检透传", "WARN",
                    "需人工裁决 %d 项（明细见 warns，全量未截断）" % len(_all))
        else:
            R.check("C7", "覆盖自检透传", "PASS", "无需人工裁决项")

    # ---------- C9 结果状态闭合（2026-09-18 新增，v3.1） ----------
    # 配套 L1-C8「结果状态契约」。只定义字段而不校验，字段会退化成没人读的自由文本 ——
    # 前车之鉴：SKILL.md 里「判定依据 / 依据来源」写了 4 次，脚本侧实际产出的只有
    # analyze_coverage.py，其余脚本根本没有这两个键，契约形同虚设。
    # 依据 operations_discipline.md §5.6 底线 3「未裁决的值不得进入成品」：
    #     result_confirmation == "pending"  或  result_origin == "unresolved"  ⇒ FAIL
    # 向后兼容：产物未携带本字段时判 SKIP —— 老产物不得因缺字段被误拦成 FAIL。
    # 2026-09-30（一百三十一）：逻辑已搬入 conflict_engine.run_c9，此处只调用；
    #   判据/文案逐字节不变，FAIL 项议题入机读出口（rc 仍以 R.fails 为准）。
    _track_issues(run_c9(P, C, K, boxes, R))

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
        _fb_notes = []
        for _bn, _bv in buildings.items():
            _k = bldg_num_or_none(_bn)
            if _k is None:
                continue
            # 楼栋级兜底容器不计入单元数（判据见 ftth_common.is_bldg_level_container）。
            #   实测（柳辛庄 band4）：3#楼 = `1单元` + 兜底容器 `3#楼` 被数成 2 个单元，
            #   与图签 1 个单元对不上 —— 却因图签侧同缺陷也虚增 1 而**假一致**，缺陷被藏住。
            _u_all = _bv.get("单元") or {}
            _fbk = [k for k in _u_all if is_bldg_level_container(k, _bn)]
            _u = {k: v for k, v in _u_all.items() if k not in _fbk}
            if not _u:
                _u = _u_all     # 全是兜底容器时不可抹平成 0（此时图上本无单元轴依据）
            elif _fbk:
                _fb_notes.append(
                    "楼%s：系统图侧楼栋级兜底容器 %s 不计入单元数（承载 %d 个单元号对不上的箱，"
                    "已在 parse 侧登记需人工裁决）"
                    % (_k, "/".join("「%s」" % x for x in _fbk),
                       sum(len((_u_all[x] or {}).get("分纤箱") or []) for x in _fbk)))
            _best, _fc, _best_alt = None, [], None
            for _un, _uv in _u.items():
                # 「层数」只数**户数非空**的层：地下刻度行（户数 null）不计入，
                # 恰与图签 `N层` 的住宅层口径对齐（也是 C5 登记的那批行）。
                _vals = [int(_x["户数"]) for _x in ((_uv or {}).get("楼层表") or {}).values()
                         if isinstance((_x or {}).get("户数"), int)]
                # 图标法回退（2026-09-19 实测柳辛庄：户数全空 ⇒ 层数=None ⇒ 与图签必假 FAIL）：
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
                # 字段级可比性（2026-09-19 实测柳辛庄 r4：15 处「不一致」里 11 处是
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
            for _d in _fb_notes[:10]:
                R.emit("  i " + _d)
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
                # 2026-10-01（优化④）：若图签含多栋合并楼名（未参与解析），
                #   在 PASS 信息后追加说明，消除「须人工裁决」与「PASS」的矛盾感。
                #   退役条件：当图签解析支持多栋合并楼名自动拆分后，此提示自然消失。
                _multi_note = ""
                if TB is not None:
                    _qr = TB.get("质量报告") or {}
                    _mb = _qr.get("图签多栋合并楼名(待人工裁决)") or []
                    if _mb:
                        _multi_note = "（注：图签含 %d 条多栋合并楼名未参与解析，见 read_titleblock 提示；不影响本次比对）" % len(_mb)
                R.check("C10", "图签第二来源逐栋比对", "PASS",
                        "%d 栋的 (单元数 / 层数 / 每层户数) 与系统图逐栋一致%s%s%s"
                        % (_both, _notes, "）" if _nonuni else "", _multi_note))

    # ---------- 冲突议题汇总（2026-09-30 一百三十一，V3 Conflict 机读出口） ----------
    # 只展示、不参与 rc（rc 仍以各门禁 R.fails 为准）。议题恒为 pending，
    # 定案只能由 human ruling 在外部闭环，本文件无任何 settled 分支。
    R.emit()
    R.emit("--- 冲突议题汇总（Conflict Engine，只展示） ---")
    _cfsum = summarize_issues(conflict_issues)
    R.emit("  待裁决议题 %d 项；按类型：%s" % (
        _cfsum.get("总数", 0),
        "、".join("%s=%d" % kv for kv in sorted((_cfsum.get("按类型") or {}).items()))
        or "无"))
    R.emit("  按域：%s（address=地址对象未定；relation=地址已定、与FX关联未定）" % (
        "、".join("%s=%d" % kv for kv in sorted((_cfsum.get("按域") or {}).items()))
        or "无"))
    for _it in conflict_issues[:20]:
        R.emit("  ? [%s] %s｜%s" % (_it.get("类型"), _it.get("对象"), _it.get("说明")))
    if len(conflict_issues) > 20:
        R.emit("  ... 另有 %d 项未列出" % (len(conflict_issues) - 20))

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
        # 输入指纹（2026-09-29 一百二十七·P0）：记录本次检查过的各输入文件 SHA256，
        # gen 出表前核对“当前输入 == 被检查过的输入”，堵住“inspect 查 A、gen 用 B”
        # 的陈旧验证旁路。文件缺席/不可读记 null（显式区分“没检查”与“检查过”）。
        _fp = {}
        for _k, _p in (("parse", args.parse_json), ("coverage", args.coverage_json),
                       ("geom", args.geom_json), ("count_box", args.count_box_json),
                       ("titleblock", args.titleblock_json)):
            _fp[_k] = sha256_file(_p) if _p else None
        payload = {"parse": args.parse_json, "coverage": args.coverage_json, "geom": args.geom_json,
                   "count_box": args.count_box_json, "titleblock": args.titleblock_json,
                   "inputs_sha256": _fp,
                   "checks": R.checks, "fails": R.fails, "warns": R.warns, "rc": rc,
                   "conflict_issues": conflict_issues}
        # 2026-09-18：写产物前先建父目录。此前未建 —— 目标目录不存在时 open() 直接
        #   Traceback（实测 rc=1、不落任何产物，且报错点远离调用处，排查成本高）。
        #   工具链内其余 16 个写产物的脚本均已做（os.makedirs / ensure_parent），
        #   本脚本是唯一漏网的（全量扫描得出，非只修报出来的那一个）。
        #   2026-09-26 起改走 write_json（内建 ensure_parent + 非有限浮点清洗）。
        write_json(args.json_out, payload)
        print("机读结果 ->", args.json_out)
    return rc


if __name__ == "__main__":
    sys.exit(main())