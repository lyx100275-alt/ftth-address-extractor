#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人工裁决批量改数（apply-ruling）

用途：把人工裁决结论**一次性、可留痕**地写进出表输入 JSON（assemble / gen 的 --dxf-json 输入），
替代「为每条裁决现写一个临时 Python 再手改字段」的做法（实测一次会话为此造了 40 个脚本、
耗 25 分钟）。本脚本只做机械落数，**不做任何推断**：

  · 不给的字段不改；
  · 找不到目标就硬失败并列出「现有键」，不猜、不静默跳过；
  · 裁决值里出现乘号（* / × / 户*N）一律拒绝——乘数属于裁决项，须人工展开成绝对户数
    （与 SKILL.md「未裁决值不得进入成品」同则）。

用法（推荐经统一入口）：
    ftth.py apply-ruling --json assembly.json --ruling ruling.json
    ftth.py apply-ruling --json assembly.json --set "1#楼/1单元/3层=4" --dry-run

--ruling 清单格式（JSON，顶层键「裁决」为数组）：
    {
      "裁决": [
        {"类型": "户数",     "楼栋": "1#楼",  "单元": "1单元", "楼层": "3层", "值": 4},
        {"类型": "安装楼层", "楼栋": "4#配套", "单元": "1单元", "箱": "FX01#", "值": "地下一层"},
        {"类型": "覆盖范围", "楼栋": "4#配套", "单元": "1单元", "箱": "FX01#", "值": "地下一层"},
        {"类型": "删除楼层", "楼栋": "9#楼",  "单元": "2单元", "楼层": "18层"},
        {"类型": "删除单元", "楼栋": "9#楼",  "单元": "3单元"}
      ]
    }

字段说明：
  · 「类型」∈ {户数, 安装楼层, 覆盖范围, 删除楼层, 删除单元}；
  · 「单元」省略 = 对该楼栋**全部单元**生效（共享系统图克隆的全改场景）；
  · 「箱」按分纤箱「编号」精确匹配（不做模糊匹配）；
  · 「值」对户数为正整数，其余为字符串。

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
from ftth_common import protect_out_path

sys.stdout.reconfigure(encoding="utf-8")

K_TYPES = ("户数", "安装楼层", "覆盖范围", "删除楼层", "删除单元")
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

if not isinstance(data, dict) or not isinstance(data.get("楼栋"), dict):
    die("%s 不是出表输入 JSON（缺顶层「楼栋」对象）" % args.json)

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
            die("第 %d 条户数 %r 含乘号——乘数是裁决项，须人工展开为绝对户数后再写入"
                "（例：4*16 应写成 64）。本脚本不做乘法。" % (i, raw))
        try:
            r["值"] = int(raw)
        except ValueError:
            die("第 %d 条户数 %r 不是整数" % (i, raw))
        if r["值"] < 0:
            die("第 %d 条户数为负：%d" % (i, r["值"]))


def norm_unit(u):
    """单元键归一（与 assemble_households.norm_unit / gen_addressbook 同则）"""
    s = str(u).strip()
    if not s:
        return s
    m = re.search(r"(\d+)\s*[#号]?\s*楼?\s*(\d+)\s*单元", s)
    if m:
        return "%s单元" % m.group(2)
    m2 = re.fullmatch(r"(\d+)\s*单元", s)
    if m2:
        return "%s单元" % m2.group(1)
    return s


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
for r in rulings:
    t = r["类型"]
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
for bkey in data["楼栋"]:
    for uk, ud in data["楼栋"][bkey].get("单元", {}).items():
        total += sum(int(f.get("户数") or 0) for f in (ud.get("楼层表") or {}).values()
                     if isinstance(f, dict))
print("[apply-ruling] 改后合计户数 = %d" % total)

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

d = os.path.dirname(os.path.abspath(out))
if d and not os.path.isdir(d):
    os.makedirs(d, exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("[apply-ruling] 已写出: %s" % out)
