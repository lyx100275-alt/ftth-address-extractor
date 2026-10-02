#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人工裁决批量改数（apply-ruling）

用途：把人工裁决结论**一次性、可留痕**地写进出表输入 JSON（assemble / gen 的 --dxf-json 输入），
替代「为每条裁决现写一个临时 Python 再手改字段」的做法（实测一次会话为此造了 40 个脚本、
耗 25 分钟）。本脚本只做机械落数，**不做任何推断**：

  · 不给的字段不改；
  · 找不到目标就硬失败并列出「现有键」，不猜、不静默跳过；
  · 裁决值里出现乘号（* / × / 户*N）一律拒绝——裁决值是**绝对户数**，本脚本只落数、
    不做乘法（`*N` 一类乘号标注属**直读**形态，读数在解析阶段已按「乘号后数字即该处
    户数」取出，不在此处展开；两套口径不得混用）。

**两种产物、两条通路**（2026-09-27 补）：
  · 出表输入 JSON（assemble_households.py 产物，顶层「楼栋」含「楼层表」）
    → 类型 {户数, 安装楼层, 覆盖范围, 删除楼层, 删除单元}
  · 覆盖范围 JSON（analyze_coverage.py 产物，顶层含「需人工裁决」）
    → 类型 {解除待裁决}（见下）

用法（推荐经统一入口）：
    ftth.py apply-ruling --json assembly.json --ruling ruling.json
    ftth.py apply-ruling --json assembly.json --set "1#楼/1单元/3层=4" --dry-run
    ftth.py apply-ruling --json coverage.json --ruling ruled_coverage.json --out coverage_ruled.json

--ruling 清单格式（JSON，顶层键「裁决」为数组）：
    {
      "裁决": [
        {"类型": "户数",     "楼栋": "1#楼",  "单元": "1单元", "楼层": "3层", "值": 4},
        {"类型": "安装楼层", "楼栋": "4#配套", "单元": "1单元", "箱": "FX01#", "值": "地下一层"},
        {"类型": "覆盖范围", "楼栋": "4#配套", "单元": "1单元", "箱": "FX01#", "值": "地下一层"},
        {"类型": "删除楼层", "楼栋": "9#楼",  "单元": "2单元", "楼层": "18层"},
        {"类型": "删除单元", "楼栋": "9#楼",  "单元": "3单元"},
        {"类型": "解除待裁决", "对象": "4#配套楼/FX22#", "裁决原文": "取 -1F", "裁决人": "用户",
         "适用范围": "4#配套楼 安装楼层冲突"}
      ]
    }

字段说明：
  · 「类型」∈ {户数, 安装楼层, 覆盖范围, 删除楼层, 删除单元, 解除待裁决}；
  · 「单元」省略 = 对该楼栋**全部单元**生效（共享系统图克隆的全改场景）；
  · 「箱」按分纤箱「编号」精确匹配（不做模糊匹配）；
  · 「值」对户数为正整数，其余为字符串。

**「解除待裁决」类型（2026-09-27 新增；出口见 operations_discipline.md §七.1）**

契约：「**一次锁定，不再复议** —— 收到人工裁决后，该问题**不得再次列为待确认项**」。
补此类型前，`coverage` 的「需人工裁决」清单**一轮一生成、无任何裁决输入入口**，
而 `result_confirmation` 只由该清单驱动 ⇒ 已裁决项的 `pending` **永远消不掉**，
C9 恒 FAIL、正式出表被硬门禁拦下。本类型把「已落盘的人工裁决」机械地作用回产物。

判据与纪律：
  · **只认「需人工裁决」清单内的对象串精确匹配**（复用 ftth_common.split_ruling_object
    的分段口径）；匹配不到**硬失败并列出清单现有对象**，不猜、不静默跳过；
  · 「裁决人」**必填** —— 没有裁决人的「裁决」不算落盘（同 §七.4）；
  · 动作有两项且**同时生效**：① 该项 `阻塞` 置 `false`（不再驱动 pending，
    留痕写 `解除裁决`/`裁决人`/`适用范围`）；② 命中该对象的箱
    `result_confirmation` 置 `settled`（`result_origin` 不动 —— 两字段正交）；
  · **不删条目、不改「事项」文字** —— 只改状态位，保留可见性（同 L426「不静默合并」）。
    产物里留痕可复核，C7 仍会显示这些项，但不再判 pending；
  · 本类型**只对带「需人工裁决」的 coverage 产物有意义**；对 assembly 产物使用即硬失败。

--set 简写：`楼栋/单元/楼层=户数`（等价于一条「户数」裁决），可重复传；与 --ruling 可并用。

写保护（默认）：--out 省略时写 `<原名>_patched.json`；--out 与输入同路径时必须显式加 --force。
目的是不让自算值覆盖技能原始产物（count/assemble 的原始输出一旦被覆盖即永久消失）。
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ftth_common import (protect_out_path, unit_num, ensure_console_utf8, write_json,
                         pending_items_from_rulings)

ensure_console_utf8()

K_TYPES = ("户数", "安装楼层", "覆盖范围", "删除楼层", "删除单元", "解除待裁决")
K_COVERAGE_TYPES = ("解除待裁决",)   # 只作用于 coverage 产物的类型
MUL_RE = re.compile(r"[*xX×]")

ap = argparse.ArgumentParser(
    description="按人工裁决清单批量改出表输入 JSON（户数/箱安装楼层/覆盖范围）")
ap.add_argument("--json", required=True, help="待改数的出表输入 JSON（assemble_households.py 产物）")
ap.add_argument("--ruling", default=None, help="裁决清单 JSON 路径（顶层「裁决」数组）")
ap.add_argument("--set", action="append", default=None,
                help='简写「楼栋/单元/楼层=户数」，可重复传；与 --ruling 可并用')
ap.add_argument("--out", default=None,
                help="输出 JSON 路径；省略则写 <原名>_patched.json（写保护默认）")
ap.add_argument("--force", action="store_true",
                help="允许 --out == 输入路径（覆盖原产物，须显式声明）")
ap.add_argument("--dry-run", action="store_true", help="只打印变更，不写文件")
args = ap.parse_args()


def die(msg, code=1):
    print("[apply-ruling] 错误：%s" % msg)
    sys.exit(code)


# ---------- 读输入 ----------
try:
    with open(args.json, "r", encoding="utf-8") as f:
        data = json.load(f)
except (IOError, json.JSONDecodeError) as e:
    die("无法读取 JSON %s: %s" % (args.json, e))

if not isinstance(data, dict):
    die("%s 不是 JSON 对象" % args.json)
if not isinstance(data.get("楼栋"), dict):
    die("%s 既非出表输入 JSON、也非覆盖范围 JSON（缺顶层「楼栋」对象）" % args.json)
# 产物形态判定：决定「解除待裁决」类裁决能否作用
HAS_PENDING_LIST = isinstance(data.get("需人工裁决"), list)

# ---------- 收集裁决 ----------
rulings = []

if args.ruling:
    try:
        with open(args.ruling, "r", encoding="utf-8") as f:
            rj = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        die("无法读取裁决清单 %s: %s" % (args.ruling, e))
    lst = rj.get("裁决") if isinstance(rj, dict) else rj
    if not isinstance(lst, list):
        die("裁决清单格式不对：顶层应为对象且含「裁决」数组，或直接是数组")
    rulings.extend(lst)

for s in (args.set or []):
    if "=" not in s:
        die("--set 缺 '='：%r（应为 楼栋/单元/楼层=户数）" % s)
    left, val = s.split("=", 1)
    parts = [p.strip() for p in left.split("/")]
    if len(parts) != 3:
        die("--set 需三段式 楼栋/单元/楼层：%r" % s)
    rulings.append({"类型": "户数", "楼栋": parts[0], "单元": parts[1], "楼层": parts[2], "值": val})

if not rulings:
    die("没有给出任何裁决（--ruling 或 --set 至少给一个）")

# ---------- 校验 ----------
for i, r in enumerate(rulings, 1):
    if not isinstance(r, dict):
        die("第 %d 条裁决不是对象：%r" % (i, r))
    t = str(r.get("类型", "")).strip()
    if t not in K_TYPES:
        die("第 %d 条类型 %r 非法，应为 %s 之一" % (i, t, "/".join(K_TYPES)))
    r["类型"] = t
    # ---- 「解除待裁决」：只作用于 coverage 产物，字段口径与出表类不同 ----
    if t in K_COVERAGE_TYPES:
        if not HAS_PENDING_LIST:
            die("第 %d 条类型「%s」需作用于覆盖范围产物（含顶层「需人工裁决」数组），"
                "但 %s 没有该数组——本类型对出表输入 JSON 无意义" % (i, t, args.json))
        if not r.get("对象"):
            die("第 %d 条（%s）缺「对象」（应为「楼栋/箱」形式，如 4#配套楼/FX22#）" % (i, t))
        if not str(r.get("裁决人", "")).strip():
            die("第 %d 条（%s）缺「裁决人」——没有裁决人的裁决不算落盘（见 §七.4）" % (i, t))
        continue
    # ---- 出表类 ----
    if not r.get("楼栋"):
        die("第 %d 条缺「楼栋」" % i)
    if t in ("户数", "删除楼层") and not r.get("楼层"):
        die("第 %d 条（%s）缺「楼层」" % (i, t))
    if t in ("安装楼层", "覆盖范围") and not r.get("箱"):
        die("第 %d 条（%s）缺「箱」" % i)
    if t == "删除单元" and not r.get("单元"):
        die("第 %d 条（删除单元）缺「单元」" % i)
    if t == "户数":
        raw = str(r.get("值", "")).strip()
        if MUL_RE.search(raw):
            die("第 %d 条户数 %r 含乘号——裁决值须为绝对户数（例：应写 64）。"
                "本脚本不做乘法；乘号标注属直读形态、读数在解析阶段取出" % (i, raw))
        try:
            r["值"] = int(raw)
        except ValueError:
            die("第 %d 条户数 %r 不是整数" % (i, raw))
        if r["值"] < 0:
            die("第 %d 条户数为负：%d" % (i, r["值"]))


def norm_unit(u):
    """单元键归一（与 assemble_households.norm_unit / gen_addressbook 同则）。

    2026-09-19 八十九：改走 ftth_common.unit_num 唯一入口（此前自写双分支只认
    ASCII 数字，`7#楼二单元` 等中文写法原样返回致失配；ASCII 输入行为不变）。
    """
    s = str(u).strip()
    if not s:
        return s
    _n = unit_num(s)
    return "%d单元" % _n if _n is not None else s


def pick_units(bkey, ukey):
    """返回 [(实际单元键, 单元数据)]；ukey 为空 = 该楼栋全部单元"""
    b = data["楼栋"].get(bkey)
    if b is None:
        # 宽容：楼栋键带不带「#」「楼」的差异做一次归一尝试
        cands = [k for k in data["楼栋"] if norm_unit(k) == norm_unit(bkey) or str(k).strip() == str(bkey).strip()]
        if len(cands) == 1:
            bkey = cands[0]
            b = data["楼栋"][bkey]
        else:
            die("楼栋 %r 不存在。现有楼栋：%s" % (bkey, "、".join(sorted(data["楼栋"]))))
    units = b.get("单元", {})
    if not ukey:
        return list(units.items())
    uk = norm_unit(ukey)
    if uk not in units:
        die("单元 %r（归一 %r）在楼栋 %s 中不存在。现有单元：%s"
            % (ukey, uk, bkey, "、".join(sorted(units)) or "(空)"))
    return [(uk, units[uk])]


# ---------- 执行 ----------
changes = []


def _obj_tokens(entry):
    """把某条「需人工裁决」的 `对象` 展开成对象串列表（**沿用全技能唯一口径**
    `pending_items_from_rulings`：`对象` 既可能是单串、也可能是列表）。"""
    return pending_items_from_rulings([entry])[0][0]


def _match_entries(objs):
    """对象串列表 → 命中的「需人工裁决」条目下标；用**分段精确匹配**（复用
    `judge_pending_scope` 同款分段 `parse_ruling_scope`，不做子串包含）。

    匹配不到时**硬失败并列出清单现有对象** —— 不猜、不静默跳过（本脚本总纪律）。
    """
    from ftth_common import parse_ruling_scope
    want = []
    for o in objs:
        b, u, bx = parse_ruling_scope(o)
        if not (b or u or bx):
            die("解除待裁决：对象串 %r 无法分段（既非「楼栋[/单元][/箱]」写法）" % o)
        want.append((b, u, bx))
    hits = []
    for idx, entry in enumerate(data["需人工裁决"]):
        if not isinstance(entry, dict):
            continue
        have = []
        for t in _obj_tokens(entry):
            b, u, bx = parse_ruling_scope(t)
            have.append((b, u, bx))
        for (b, u, bx) in want:
            for (hb, hu, hx) in have:
                if (b, u, bx) == (hb, hu, hx):
                    hits.append((idx, entry))
                    break
            else:
                continue
            break
    if not hits:
        cur = []
        for entry in data["需人工裁决"]:
            if isinstance(entry, dict):
                cur.extend(_obj_tokens(entry))
        die("解除待裁决：对象 %s 在「需人工裁决」清单中匹配不到。现有对象：%s"
            "（对象串须逐段一致：楼栋/单元/箱，不做子串匹配）"
            % ("、".join(objs), "、".join(sorted(set(cur))) or "(空)"))
    return hits


def _settle_boxes(objs):
    """把命中对象对应的分纤箱 `result_confirmation` 置 `settled`（`result_origin` 不动）。

    对象粒度：`楼栋/箱` ⇒ 该箱；`楼栋/单元` ⇒ 该单元全部箱；`楼栋` ⇒ 该楼栋全部箱。
    找不到对应箱**不硬失败** —— 箱级状态由 coverage 产物自身承载，此处只作同步；
    留痕列出实际改了几处，改不到即如实报 0（不得静默给绿灯）。

    坑（实测踩）：coverage 产物的**单元键是「楼栋前缀式」**（`7#楼1单元`），
    而裁决对象串里的单元段是**裸式**（`1单元`）——直接字符串比较**恒不相等**，
    会静默同步 0 处、pending 消不掉。故一律走 ``unit_num`` 归一比较（两边都归一），
    与 assemble_households.norm_unit 同则。
    """
    from ftth_common import parse_ruling_scope, bldg_num
    n = 0
    for o in objs:
        b, u, bx = parse_ruling_scope(o)
        u_n = unit_num(u) if u else None
        for bkey, bd in (data.get("楼栋") or {}).items():
            # 楼栋段比对：字符串相同或楼号相同（同 judge_pending_scope 口径）
            if b and b != bkey:
                if not (bldg_num(b) and bldg_num(b) == bldg_num(bkey)):
                    continue
            for uk, ud in (bd.get("单元") or {}).items():
                if u:
                    # 裸式单元段 vs 楼栋前缀式单元键 —— 走 unit_num 归一
                    if unit_num(uk) != u_n:
                        continue
                for box in (ud.get("分纤箱") or []):
                    if not isinstance(box, dict):
                        continue
                    if bx and str(box.get("编号", "")).strip() != bx:
                        continue
                    if box.get("result_confirmation") != "settled":
                        box["result_confirmation"] = "settled"
                        n += 1
    return n


for r in rulings:
    t = r["类型"]
    # ---- 覆盖范围产物专用：解除待裁决（把已落盘的人工裁决回灌，消除 pending）----
    if t in K_COVERAGE_TYPES:
        objs = r["对象"] if isinstance(r["对象"], list) else [r["对象"]]
        objs = [str(o).strip() for o in objs]
        hits = _match_entries(objs)
        n_box = _settle_boxes(objs)
        for idx, entry in hits:
            if entry.get("阻塞") is False:
                changes.append("解除待裁决 %s（清单第 %d 条本已 阻塞=false，仅补留痕）"
                               % ("/".join(objs), idx + 1))
            else:
                entry["阻塞"] = False
                changes.append("解除待裁决 %s（清单第 %d 条 阻塞 -> false）"
                               % ("/".join(objs), idx + 1))
            entry["解除裁决"] = True
            entry["裁决人"] = str(r["裁决人"]).strip()
            entry["裁决原文"] = str(r.get("裁决原文", "") or "")
            if r.get("适用范围"):
                entry["适用范围"] = str(r["适用范围"])
        changes.append("  ↳ 同步箱 result_confirmation=settled 共 %d 处" % n_box)
        continue
    for uk, ud in pick_units(r["楼栋"], r.get("单元")):
        if t == "删除单元":
            del data["楼栋"][r["楼栋"]]["单元"][uk]
            changes.append("删除单元 %s/%s" % (r["楼栋"], uk))
            continue
        if t == "删除楼层":
            fl = r["楼层"]
            ft = ud.get("楼层表", {})
            if fl not in ft:
                die("楼层 %r 在 %s/%s 不存在。现有楼层：%s"
                    % (fl, r["楼栋"], uk, "、".join(sorted(ft)) or "(空)"))
            old = ft[fl].get("户数")
            del ft[fl]
            changes.append("删除楼层 %s/%s %s（原户数 %s）" % (r["楼栋"], uk, fl, old))
            continue
        if t == "户数":
            fl = r["楼层"]
            ft = ud.setdefault("楼层表", {})
            old = ft.get(fl, {}).get("户数") if isinstance(ft.get(fl), dict) else ft.get(fl)
            ft[fl] = {"户数": r["值"]}
            changes.append("户数 %s/%s %s: %s -> %d" % (r["楼栋"], uk, fl, old, r["值"]))
            continue
        # 分纤箱类
        boxes = ud.get("分纤箱", [])
        if not isinstance(boxes, list) or not boxes:
            die("%s/%s 没有分纤箱条目，无法执行「%s」。若为未分配单元，请先补 coverage 或人工录入箱条目。"
                % (r["楼栋"], uk, t))
        hit = [b for b in boxes if isinstance(b, dict) and str(b.get("编号", "")).strip() == str(r["箱"]).strip()]
        if not hit:
            die("箱 %r 在 %s/%s 不存在。现有箱：%s"
                % (r["箱"], r["楼栋"], uk,
                   "、".join(str(b.get("编号")) for b in boxes if isinstance(b, dict)) or "(空)"))
        tgt_key = {"安装楼层": "安装楼层", "覆盖范围": "覆盖范围线索"}[t]
        for b in hit:
            old = b.get(tgt_key)
            b[tgt_key] = r["值"]
            changes.append("%s %s/%s %s(%s): %s -> %s"
                           % (t, r["楼栋"], uk, r["箱"], tgt_key, old, r["值"]))

# ---------- 统计 ----------
print("[apply-ruling] 裁决 %d 条，落数 %d 处：" % (len(rulings), len(changes)))
for c in changes:
    print("  · " + c)

total = 0
_n_floor_tables = 0
for bkey in data["楼栋"]:
    for uk, ud in data["楼栋"][bkey].get("单元", {}).items():
        _ft = ud.get("楼层表")
        if isinstance(_ft, dict):
            _n_floor_tables += 1
        total += sum(int(f.get("户数") or 0) for f in (_ft or {}).values()
                     if isinstance(f, dict))
if _n_floor_tables:
    print("[apply-ruling] 改后合计户数 = %d（%d 个单元含楼层表）" % (total, _n_floor_tables))
else:
    # 覆盖范围产物无「楼层表」（户数在 assembly 产物里）——不得把「无此字段」印成「0 户」
    print("[apply-ruling] 本产物无「楼层表」字段（覆盖范围 JSON），不统计户数"
          "（本类型只改裁定状态位，不涉户数）")

# ---------- 写保护 + 写出 ----------
out = args.out
if out:
    if os.path.abspath(out) == os.path.abspath(args.json) and not args.force:
        die("--out 与输入同路径（%s）会覆盖原始产物，原始输出将永久消失。"
            "确需覆盖请显式加 --force；否则去掉 --out 用默认 *_patched。" % out, code=2)
    out, diverted = protect_out_path(out, force=args.force, label="改数产物")
    if diverted:
        print("[apply-ruling] （原 --out %s 未被改动）" % args.out)
else:
    stem, ext = os.path.splitext(args.json)
    out = stem + "_patched" + (ext or ".json")
    print("[apply-ruling] --out 未指定，按写保护默认写 %s" % out)

if args.dry_run:
    print("[apply-ruling] --dry-run：未写文件")
    sys.exit(0)

write_json(out, data)
print("[apply-ruling] 已写出: %s" % out)
