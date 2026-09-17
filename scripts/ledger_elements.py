#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""元素台账 —— 把一张 FTTH 竣工图上的**元素**按类别枚举成带坐标的结构化台账。

为什么需要它（与既有脚本的分工）：
  `parse_dxf_structured.py` 只输出「楼栋→单元→分纤箱/楼层表」这棵**业务树**；
  它按设计不落盘楼栋/单元的几何边界，分纤箱也曾只留 y 层位、丢掉 x。
  本脚本是**几何侧的独立台账**：把「有哪些元素、各在哪、边界在哪」讲清楚，
  供人工核对与下游消费。两路出口互不覆盖：业务树仍走 parse，几何台账走本脚本。

六类元素（用户 2026-09-16 指定）：
  ① 分纤箱   ② 家居箱   ③ 线缆   ④ 楼层线   ⑤ 数据标注   ⑥ 文字标注

执行纪律（与技能既有总则一致）：
  · **不预设项目参数**：图层关键词、编号正则、块属性判据全部可按图传参；
    未传时按图纸自身推断，并在 `参数来源` 里逐项写明是「命令行传入 / probe 配置 / 按图推断」。
  · **缺项显式登记**：某类元素在本图找不到，写进 `缺项[]` 并给降级路径，**不留空、不静默**。
  · **两路信号不一致不择一**：分纤箱的「文字编号」与「箱柜图层图标」各自成表，
    语义不同（后者是**超集**，含安防/消防等非分纤箱设备），对账只提示差异、不裁决。
  · **坐标完整性自证**：任何元素的 x 或 y 缺失都计入 `校验.坐标完整性`。
  · **边界不得越界**：单元 x 区间必须含于所属楼栋 x 区间（单单元楼栋尤甚，
    否则会退化成 ±unit_range 的宽区间、跨越邻楼）。
  · **y 必须分带**：同一楼栋 x 带内的文字可能来自多个不连续的图区（系统图 / 平面图），
    故 y 不取全局极值，而是按 y 聚类成**带**逐带登记，并标出含锚点的主带。

用法：
  python scripts/ledger_elements.py --dxf 图纸.dxf [--out ledger.json]
         [--geom 图纸.dxf.geom.json] [--config probe.json] [--parse parse.json]
         [--wire-layer 图层1,图层2]        # 线缆层**建议显式传入**（见下方「线缆」段说明）
"""
import argparse
import io
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ftth_common as C  # noqa: E402

# ---------- 默认（按图自适，不是项目常数） ----------
# 箱柜**专用**层。不使用宽泛的 EQUIP- 前缀：实测同前缀下还有 EQUIP-安防 / EQUIP-消防 /
# EQUIP-插座，那些是别的专业设备，混进来会把「分纤箱」数量抬高一个量级。
BOX_LAYER_KW_DEFAULT = ("箱柜",)
BOX_LAYER_KW_FALLBACK = ("箱柜", "EQUIP")
BOX_ATTR_RE_DEFAULT = r"家居配线箱|家庭信息箱|多媒体箱|HDD|HD|FZHK"

# 线缆候选：优先 FTTH 语义词。
WIRE_LAYER_KW_DEFAULT = ("纤芯", "皮线", "光缆", "蝶形", "CABLE", "RX-", "通讯", "弱电", "TEL")
# 排除项：**建筑电气**回路的图层特征，不是 FTTH 入户皮线。
# 命中它们的图层只登记为「候选中被排除」，绝不充当线缆算法输入 ——
# 否则竖线法会顺着配电干线跑，覆盖结论整片跑偏。
WIRE_LAYER_EXCLUDE = ("照明", "动力", "接地", "消防", "安防", "暖通", "插座", "应急", "母线", "消防")
FLOORLINE_LAYER_KW_DEFAULT = ("楼层线",)
FX_TEXT_RE_DEFAULT = r"[A-Z]{2}\d{1,2}[-－]?FX\d{1,3}|FX\d{1,3}"
HU_RE_DEFAULT = r"[（({\[]?\s*(\d+)\s*户(?:\s*/\s*层)?\s*[）)}\]]?"
CABLE_RE_DEFAULT = r"(\d+)\s*m\s*[*×]\s*(\d+)"
CORE_RE_DEFAULT = r"(\d+)\s*芯"

# 长句/说明类文字不是编号（实测：图上『说明：…在分纤箱盘留5米』『图例 新建分纤箱』
# 都会命中「分纤箱」关键词，误计为编号会直接把箱数抬高一个量级）。
_NONLABEL_HINT = ("说明", "图例", "注：", "备注", "盘留", "各楼层", "详见", "参见")


def _is_label_like(txt, max_len=24):
    """短标签判据：编号/名称类标注天然极短，且不含说明性提示词。"""
    if not txt:
        return False
    if "\n" in txt or "\r" in txt:
        return False
    if len(txt) > max_len:
        return False
    return not any(h in txt for h in _NONLABEL_HINT)


def _rng(vals):
    """返回 [min, max]（保留 2 位）或 None。"""
    v = [x for x in vals if x is not None]
    if not v:
        return None
    return [round(min(v), 2), round(max(v), 2)]


def _bands(pairs, anchor_y=None, tol_ratio=0.02):
    """按 y 把 (y, x) 聚成**带**（同一楼栋 x 带内的文字可能来自多个不连续图区）。

    返回 [{y范围, 文字数, x范围, 主带}]，主带 = 含 anchor_y 的那一带（anchor_y 为 None 时取文字最多的一带）。
    """
    pts = sorted([(y, x) for y, x in pairs if y is not None])
    if not pts:
        return []
    span = (pts[-1][0] - pts[0][0]) or 1.0
    tol = max(span * tol_ratio, 1e-6)
    groups = [[pts[0]]]
    for y, x in pts[1:]:
        if y - groups[-1][-1][0] <= tol:
            groups[-1].append((y, x))
        else:
            groups.append([(y, x)])
    out = []
    for gr in groups:
        ys = [p[0] for p in gr]
        xs = [p[1] for p in gr]
        out.append({"y范围": _rng(ys), "文字数": len(gr), "x范围": _rng(xs), "主带": False})
    if anchor_y is not None:
        best = min(range(len(out)), key=lambda i: min(abs(anchor_y - y) for y in
                                                      [p[0] for p in groups[i]]))
    else:
        best = max(range(len(out)), key=lambda i: out[i]["文字数"])
    out[best]["主带"] = True
    return out


def _floor_step(labels, xlo, xhi):
    """由该 x 带内**楼层标注**的 y 差量出层高。

    用途：无单元标注时，「分纤箱 x 聚类」的聚类阈值需与图面尺度同量纲
    （parse 侧同口径用实测层高作 unit_cluster），不预设坐标常数。
    量不出（带内楼层标注少于 2 条）返回 None，由调用方退化为按箱间距推定。
    """
    ys = sorted({d["y"] for d in labels
                 if d["类别"] == "楼层标注" and xlo <= d["x"] < xhi})
    if len(ys) < 2:
        return None
    diffs = [b - a for a, b in zip(ys, ys[1:]) if b > a]
    return statistics.median(diffs) if diffs else None


def _load_geom(args, log):
    dxf = os.path.abspath(args.dxf)
    cache = args.geom or (dxf + ".geom.json")
    if not os.path.exists(dxf):
        log.error("图纸不存在：%s", dxf)
        sys.exit(1)
    if os.path.exists(cache):
        g = C.load_geom(dxf, log=log, out=cache)
    else:
        log.info("geom 缓存不存在，现建：%s", cache)
        g = C.load_geom(dxf, log=log, rebuild=True, out=cache)
    if not isinstance(g, dict) or not g.get("texts"):
        log.error("几何缓存为空或结构不符：%s", cache)
        sys.exit(4)
    return g, cache


def _cfg_params(args, g, log):
    """参数来源：命令行 > probe 配置 > 按图推断。逐项记录来源与命中情况，不静默。"""
    src = {}
    notes = {}
    sug = {}
    if args.config and os.path.exists(args.config):
        try:
            sug = (json.load(io.open(args.config, encoding="utf-8")) or {}).get("suggested_params") or {}
        except Exception as e:
            log.warning("读 --config 失败（%s），该项按推断处理", e)
    layers = list((g.get("layers") or {}).keys())

    def pick(name, cli_val, sug_key, default):
        if cli_val:
            src[name] = "命令行传入"
            return cli_val
        if sug_key and sug.get(sug_key):
            src[name] = "probe 配置"
            return sug[sug_key]
        src[name] = "按图推断（内置默认）"
        return default

    def pick_layers(name, cli_val, kwset, hint, fallback=None, exclude=None):
        """返回 (命中图层, 被排除图层, 状态)。"""
        if cli_val:
            hit = [x.strip() for x in cli_val.split(",") if x.strip()]
            src[name] = "命令行传入"
            return hit, [], "命令行传入"
        hit = [ln for ln in layers if any(k in ln for k in kwset)]
        excl = []
        if exclude:
            excl = [ln for ln in hit if any(k in ln for k in exclude)]
            hit = [ln for ln in hit if ln not in excl]
        if not hit and fallback:
            hit = [ln for ln in layers if any(k in ln for k in fallback)]
            src[name] = "按图推断（无专用层，回落兜底关键词 %s，命中 %d 层）" % ("/".join(fallback), len(hit))
        else:
            src[name] = "按图推断（命中 %d 层%s）" % (len(hit), "，排除 %d 层" % len(excl) if excl else "")
        if not hit:
            log.warning("  [缺项] %s 无候选图层（%s）——登记为缺项，不静默补默认层", name, hint)
        return hit, excl, src[name]

    p = {
        "title_pattern": pick("title_pattern", args.title_pattern, "title_pattern",
                              r"(\d+)#(?:配套|商业|附属)?楼|(\d+)号楼"),
        "unit_pattern": pick("unit_pattern", args.unit_pattern, "unit_pattern", r"(\d+)\s*单元"),
        "fx_pattern": pick("fx_pattern", args.fx_pattern, "fx_pattern", FX_TEXT_RE_DEFAULT),
        "hu_pattern": pick("hu_pattern", args.hu_pattern, "hu_pattern", HU_RE_DEFAULT),
        "cable_pattern": pick("cable_pattern", args.cable_pattern, "cable_pattern", CABLE_RE_DEFAULT),
        "box_attr_re": pick("box_attr_re", args.box_attr_re, None, BOX_ATTR_RE_DEFAULT),
        "text_layer": pick("text_layer", args.text_layer, "text_layer", None),
    }
    p["box_layers"], p["box_layers_excluded"], notes["box_layers"] = pick_layers(
        "box_layers", args.box_layer_kw, BOX_LAYER_KW_DEFAULT, "箱柜/EQUIP", fallback=BOX_LAYER_KW_FALLBACK)
    p["wire_layers"], p["wire_layers_excluded"], notes["wire_layers"] = pick_layers(
        "wire_layers", args.wire_layer, WIRE_LAYER_KW_DEFAULT, "纤芯/皮线/光缆/RX-",
        exclude=WIRE_LAYER_EXCLUDE)
    p["floorline_layers"], p["floorline_layers_excluded"], notes["floorline_layers"] = pick_layers(
        "floorline_layers", args.floorline_layer, FLOORLINE_LAYER_KW_DEFAULT, "楼层线")
    return p, src, notes


def main():
    ap = argparse.ArgumentParser(description="元素台账（六类元素 + 楼栋单元边界 + 坐标/边界校验）")
    ap.add_argument("--dxf", required=True)
    ap.add_argument("--out", default=None, help="输出 JSON（默认 <DXF>.ledger.json）")
    ap.add_argument("--geom", default=None, help="geom 缓存路径（默认 <DXF>.geom.json）")
    ap.add_argument("--config", default=None, help="probe 配置（回填检测类参数）")
    ap.add_argument("--parse", default=None, help="可选：parse.json，用于两路对账")
    ap.add_argument("--text-layer", default=None)
    ap.add_argument("--title-pattern", default=None)
    ap.add_argument("--unit-pattern", default=None)
    ap.add_argument("--fx-pattern", default=None)
    ap.add_argument("--hu-pattern", default=None)
    ap.add_argument("--cable-pattern", default=None)
    ap.add_argument("--box-layer-kw", default=None, help="箱柜类图层关键词，逗号分隔")
    ap.add_argument("--box-attr-re", default=None, help="家居箱块属性值判据正则")
    ap.add_argument("--wire-layer", default=None,
                    help="线缆类图层（逗号分隔）。**建议显式传入**：自动推断只给候选，"
                         "建筑电气的 WIRE-* 会被排除")
    ap.add_argument("--floorline-layer", default=None, help="楼层线图层关键词，逗号分隔")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    log = C.setup_logger("ledger", verbose=args.verbose)
    dxf = os.path.abspath(args.dxf)
    out = os.path.abspath(args.out) if args.out else dxf + ".ledger.json"

    g, cache = _load_geom(args, log)
    texts, inserts = g.get("texts") or [], g.get("inserts") or []
    attrs, segs, polys = g.get("insert_attrs") or [], g.get("segs") or [], g.get("polylines") or []
    layers = g.get("layers") or {}
    p, psrc, pnotes = _cfg_params(args, g, log)

    try:
        TITLE_RE = re.compile(p["title_pattern"]) if p["title_pattern"] else None
        UNIT_RE = re.compile(p["unit_pattern"]) if p["unit_pattern"] else None
        FX_RE = re.compile(p["fx_pattern"]) if p["fx_pattern"] else None
        HU_RE = re.compile(p["hu_pattern"]) if p["hu_pattern"] else None
        CABLE_RE = re.compile(p["cable_pattern"]) if p["cable_pattern"] else None
        BOXATTR_RE = re.compile(p["box_attr_re"]) if p["box_attr_re"] else None
        CORE_RE = re.compile(CORE_RE_DEFAULT)
    except re.error as e:
        log.error("正则编译失败（参数写错？）：%s", e)
        sys.exit(1)

    missing, ledger, pending = [], {}, []

    # ================= ① 分纤箱 =================
    box_layers = set(p["box_layers"])
    box_icons = []
    for i, ins in enumerate(inserts):
        lay = ins[0] or ""
        if lay not in box_layers:
            continue
        a = attrs[i] if i < len(attrs) else None
        box_icons.append({"层": lay, "x": round(ins[1], 2), "y": round(ins[2], 2),
                          "块名": ins[3], "属性": a or {}})
    # 文字侧编号：短标签过滤后再过编号正则（防说明/图例长句假阳）
    fx_txt = []
    for t in texts:
        lay, x, y, txt = t[0], t[1], t[2], (t[3] or "")
        if not _is_label_like(txt):
            continue
        if FX_RE and FX_RE.search(txt):
            fx_txt.append({"层": lay, "x": round(x, 2), "y": round(y, 2), "编号": txt})
    # 家居箱（属性判据）—— 与分纤箱同在箱柜层，按属性区分，避免互相吞并
    home_icons = [d for d in box_icons
                  if BOXATTR_RE and any(BOXATTR_RE.search(str(v)) for v in (d["属性"] or {}).values())]
    other_icons = [d for d in box_icons if d not in home_icons]
    grp = {}
    for d in box_icons:
        k = "%s | %s" % (d["层"], d["块名"])
        grp[k] = grp.get(k, 0) + 1

    ledger["分纤箱"] = {
        "判定": "① **文字编号**（权威计数）：短标签形态过滤（无换行、≤24字、不含说明/图例/盘留等提示词）"
                "后过编号正则 —— 给出**编号 + 完整 (x,y)**；"
                "② **箱柜图层图标**（超集）：箱柜专用层上的 INSERT，含安防/消防等**非分纤箱**设备，"
                "仅作独立第二来源，不参与计数裁决",
        "文字编号": fx_txt,
        "箱柜图层图标": box_icons,
        "箱柜图标分组(层|块名)": grp,
        "对账": {
            "文字编号数(权威)": len(fx_txt),
            "箱柜图层图标数(超集)": len(box_icons),
            "其中家居箱(属性判据)": len(home_icons),
            "其中非家居箱": len(other_icons),
            "结论": ("文字编号为主计数；箱柜图标数 %d %s 文字编号数 %d —— %s"
                     % (len(box_icons),
                        ">" if len(box_icons) > len(fx_txt) else ("<" if len(box_icons) < len(fx_txt) else "="),
                        len(fx_txt),
                        "差值由**非分纤箱的箱柜设备**（安防/消防/插座等）解释，须按 `箱柜图标分组` 逐组核对，"
                        "不得把图标数当分纤箱数"
                        if len(box_icons) > len(fx_txt) else
                        ("两侧一致" if len(box_icons) == len(fx_txt)
                         else "文字侧多于图标侧 —— 可能有编号只写了文字、未画图标，须人工确认"))),
        },
        "数量": len(fx_txt) if fx_txt else len(box_icons),
        "x范围": _rng([d["x"] for d in (fx_txt or box_icons)]),
        "y范围": _rng([d["y"] for d in (fx_txt or box_icons)]),
    }
    if not fx_txt and not box_icons:
        missing.append({"元素": "分纤箱", "状态": "absent",
                        "降级路径": "本图无分纤箱文字编号也无箱柜图层图标 → 出表前须人工确认编号承载形式"
                                     "（可能写在各楼系统图楼层表内），不得据空表出地址表"})
    elif not fx_txt:
        missing.append({"元素": "分纤箱文字编号", "状态": "absent",
                        "降级路径": "只有箱柜图标、无编号文字 → 编号须另寻承载形式（系统图楼层表 / 图签对照表）"})

    # ================= ② 家居箱 =================
    home_attr_vals = {}
    for d in home_icons:
        for k, v in (d["属性"] or {}).items():
            if BOXATTR_RE and BOXATTR_RE.search(str(v)):
                home_attr_vals["%s=%s" % (k, v)] = home_attr_vals.get("%s=%s" % (k, v), 0) + 1
    ledger["家居箱"] = {
        "判定": "箱柜类图层 INSERT 的**块属性值**命中 %r —— 属性法（不依赖几何推断，"
                "与「贴皮线末端」图标法互为独立来源）" % p["box_attr_re"],
        "属性命中数": len(home_icons),
        "按属性值分组": home_attr_vals,
        "逐条": home_icons,
        "x范围": _rng([d["x"] for d in home_icons]),
        "y范围": _rng([d["y"] for d in home_icons]),
    }
    if not home_icons:
        missing.append({"元素": "家居箱(属性法)", "状态": "absent",
                        "降级路径": "无块属性命中 → 回落图标法几何判据（count_box_icons.py）或皮线计数；"
                                     "两者口径不一致时停、交用户裁决"})

    # ================= ③ 线缆 =================
    wire_layers = set(p["wire_layers"])
    wsegs = [s for s in segs if (s[0] or "") in wire_layers]
    wpoly = [q for q in polys if (q[0] or "") in wire_layers]
    per_layer = {}
    for s in wsegs:
        per_layer[s[0]] = per_layer.get(s[0], 0) + 1
    # 候选全谱（供人工显式指定 --wire-layer；自动推断只做剔除，不替人拍板）
    cand = {}
    for ln, c in layers.items():
        if any(k in ln for k in ("线", "缆", "WIRE", "CABLE", "纤")):
            cand[ln] = {"实体总数": c,
                        "被排除": any(k in ln for k in WIRE_LAYER_EXCLUDE)}
    ledger["线缆"] = {
        "判定": "指定/推断的线缆类图层上的 LINE/LWPOLYLINE/POLYLINE 实体；"
                "建筑电气回路（照明/动力/接地/消防/安防…）已从自动候选中**剔除**",
        "采用图层": sorted(wire_layers),
        "图层线段数": per_layer,
        "线段数": len(wsegs),
        "多段线数": len(wpoly),
        "候选全谱": cand,
        "被排除图层": p["wire_layers_excluded"],
        "x范围": _rng([s[1] for s in wsegs] + [s[3] for s in wsegs]),
        "y范围": _rng([s[2] for s in wsegs] + [s[4] for s in wsegs]),
    }
    if not wsegs:
        missing.append({"元素": "线缆", "状态": "absent",
                        "降级路径": "无专用连线层 → 竖线法前置 dedicated_wire_layer 不成立，"
                                     "覆盖判定改走 V 型计算或待确认"})
    else:
        pending.append({"项": "线缆图层认定",
                        "说明": "自动候选已剔除建筑电气层；本图采用 %s。竖线法/皮线计数的输入层"
                                "须与本项一致，**建议显式传 --wire-layer 复核**" % sorted(wire_layers)})

    # ================= ④ 楼层线 =================
    fl_layers = set(p["floorline_layers"])
    fl_segs = [s for s in segs if (s[0] or "") in fl_layers]
    horiz = [s for s in fl_segs if abs(s[2] - s[4]) <= 1e-9]
    y_lines = []
    if horiz:
        ys = sorted(set(round(s[2], 3) for s in horiz))
        span = (max(ys) - min(ys)) or 1.0
        tol = max(span * 0.005, 1e-6)
        groups = []
        for y in ys:
            if groups and y - groups[-1][-1] <= tol:
                groups[-1].append(y)
            else:
                groups.append([y])
        y_lines = sorted(round(statistics.fmean(gr), 3) for gr in groups)
    ledger["楼层线"] = {
        "判定": "① 真几何：楼层线图层上的**水平**线段，按 y 聚类成楼层线；"
                "② 无该图层时回落楼层**文字**的 y（见「数据标注」内的楼层标注）",
        "图层": {ln: sum(1 for s in fl_segs if s[0] == ln) for ln in fl_layers},
        "水平段数": len(horiz),
        "楼层线y清单": y_lines,
        "楼层线数": len(y_lines),
        "x范围": _rng([s[1] for s in fl_segs] + [s[3] for s in fl_segs]),
        "y范围": _rng([s[2] for s in fl_segs] + [s[4] for s in fl_segs]),
        "推断层高": (round(statistics.median([b - a for a, b in zip(y_lines, y_lines[1:])]), 3)
                    if len(y_lines) >= 2 else None),
    }
    if not y_lines:
        missing.append({"元素": "楼层线(几何)", "状态": "absent",
                        "降级路径": "本图楼层刻度只能由楼层**文字**的 y 建立（floor_scale 仍成立，"
                                     "但少一路独立来源）；结论须标注来源为文字"})

    # ================= ⑤ 数据标注 / ⑥ 文字标注 =================
    data_labels, text_labels = [], []
    for t in texts:
        lay, x, y, txt = t[0], t[1], t[2], (t[3] or "")
        if not txt:
            continue
        kind = None
        if HU_RE and HU_RE.search(txt):
            kind = "户数"
        elif CABLE_RE and CABLE_RE.search(txt):
            kind = "皮线米数"
        elif CORE_RE.search(txt):
            kind = "芯数"
        elif C.RE_DRAWING_WORD.search(txt) or (TITLE_RE and TITLE_RE.search(txt)):
            kind = "图纸标题"
        elif UNIT_RE and UNIT_RE.search(txt):
            kind = "单元标注"
        elif FX_RE and FX_RE.search(txt) and _is_label_like(txt):
            kind = "分纤箱编号"
        elif re.fullmatch(r"\s*[-−]?\d{1,3}\s*[FBWFwbf]+\s*", txt):
            kind = "楼层标注"
        if kind:
            data_labels.append({"类别": kind, "层": lay, "x": round(x, 2), "y": round(y, 2), "内容": txt})
        else:
            text_labels.append({"层": lay, "x": round(x, 2), "y": round(y, 2), "内容": txt})

    kinds = {}
    for d in data_labels:
        kinds[d["类别"]] = kinds.get(d["类别"], 0) + 1
    ledger["数据标注"] = {
        "判定": "带**量值语义**的标注：户数 / 皮线米数 / 芯数 / 楼层 / 单元 / 分纤箱编号 / 图纸标题",
        "分类计数": kinds,
        "逐条": data_labels,
        "数量": len(data_labels),
        "x范围": _rng([d["x"] for d in data_labels]),
        "y范围": _rng([d["y"] for d in data_labels]),
    }
    ledger["文字标注"] = {
        "判定": "其余文字（设备名、说明、图例、路径描述等）",
        "数量": len(text_labels),
        "x范围": _rng([d["x"] for d in text_labels]),
        "y范围": _rng([d["y"] for d in text_labels]),
        "样例": text_labels[:20],
    }

    # ================= 楼栋 / 单元 位置与边界 =================
    tdicts = [{"层": t[0], "x": t[1], "y": t[2], "内容": t[3] or ""} for t in texts]
    bldg_boundaries, bnd_missing = [], []
    if not TITLE_RE:
        bnd_missing.append("未提供 --title-pattern，楼栋边界无法建立")
    else:
        anchors = C.find_bldg_anchors(tdicts, TITLE_RE, log)
        if not anchors:
            bnd_missing.append("标题正则未命中任何楼栋锚点")
        else:
            axs = sorted([(k, v["x"]) for k, v in anchors.items()], key=lambda z: z[1])
            branges = C.compute_bldg_ranges(axs)
            for bname in sorted(branges.keys(), key=C.bldg_num):
                xlo, xhi = branges[bname]
                ain = anchors[bname]
                ay = ain.get("y", 0)
                btexts = [t for t in tdicts if xlo <= t["x"] < xhi]
                bybands = _bands([(t["y"], t["x"]) for t in btexts], anchor_y=ay)
                units_out = []
                units_clue = None
                umarks = [t for t in btexts if UNIT_RE and UNIT_RE.search(t["内容"])] if UNIT_RE else []
                if umarks:
                    urefer, seen = [], set()
                    for t in sorted(umarks, key=lambda z: z["x"]):
                        m = UNIT_RE.search(t["内容"])
                        un = (m.group(1) + "单元") if (m and m.lastindex) else t["内容"]
                        if un in seen:
                            continue
                        seen.add(un)
                        urefer.append((un, t["x"], t["y"]))
                    uranges = C.compute_bldg_ranges([(u, x) for u, x, _y in urefer])
                    for un, ux, uy in urefer:
                        ulo, uhi = uranges[un]
                        # 边界不得越界：单元区间必须含于楼栋区间（单单元楼栋会退化成
                        # ±unit_range 的宽带，跨过邻楼 —— 必须夹回楼栋边界内）
                        clo, chi = max(ulo, xlo), min(uhi, xhi)
                        clamped = (clo != ulo) or (chi != uhi)
                        usub = [t for t in btexts if clo <= t["x"] < chi]
                        units_out.append({
                            "名称": un,
                            "锚点": {"x": round(ux, 2), "y": round(uy, 2)},
                            "x范围": [round(clo, 2), round(chi, 2)],
                            "x范围原值": [round(ulo, 2), round(uhi, 2)] if clamped else None,
                            "已夹回楼栋边界": clamped,
                            "y带": _bands([(t["y"], t["x"]) for t in usub], anchor_y=uy),
                            "文字数": len(usub),
                        })
                else:
                    # 无单元标注 → **不臆造**单元边界（缺项须显式、结论须有第二来源）。
                    # 改为给出「分纤箱 x 聚类」**线索**，供人工核定后再用 --unit-pattern 重跑。
                    bfx = sorted(d["x"] for d in fx_txt if xlo <= d["x"] < xhi)
                    clue = []
                    if bfx:
                        step = _floor_step(data_labels, xlo, xhi)
                        thr = step if step else max((max(bfx) - min(bfx)) / max(len(bfx), 1), 1.0)
                        clue = [round(c["x"], 2) for c in C.cluster_by_x([{"x": v} for v in bfx], thr)]
                    units_clue = {
                        "口径": "分纤箱 x 聚类（**线索，非结论**——本图无单元标注）",
                        "聚类阈值": round(thr, 3) if bfx else None,
                        "聚类x": clue, "聚类数": len(clue),
                        "提示": "须人工确认后，才可用 --unit-pattern 显式传入该图单元写法重跑台账",
                    }
                    bnd_missing.append("%s：无单元标注（单元切分需回落分纤箱 x 聚类；见本栋「单元线索」）" % bname)
                bldg_boundaries.append({
                    "楼栋": bname,
                    "锚点": {"x": round(ain["x"], 2), "y": round(ay, 2)},
                    "x范围": [round(xlo, 2), round(xhi, 2)],
                    "y带": bybands,
                    "文字数": len(btexts),
                    "单元": units_out,
                    "单元线索": units_clue,
                })

    # ================= 校验：坐标完整性 + 越界 + 重叠 =================
    completeness = {}
    for name, items in [("分纤箱(文字编号)", fx_txt), ("箱柜图层图标", box_icons), ("家居箱", home_icons),
                        ("数据标注", data_labels), ("文字标注", text_labels)]:
        bad = sum(1 for d in items if d.get("x") is None or d.get("y") is None)
        completeness[name] = {"总数": len(items), "缺x或y": bad}
    for b in bldg_boundaries:
        bad = 0 if (b["x范围"] and b["锚点"]["x"] is not None and b["锚点"]["y"] is not None
                    and b["y带"]) else 1
        bad += sum(1 for u in b["单元"]
                   if not (u["x范围"] and u["锚点"]["x"] is not None
                           and u["锚点"]["y"] is not None and u["y带"]))
        completeness["楼栋/单元边界·%s" % b["楼栋"]] = {"总数": 1 + len(b["单元"]), "缺x或y": bad}

    out_of_bounds, overlaps = [], []
    for b in bldg_boundaries:
        for u in b["单元"]:
            if u["x范围"][0] < b["x范围"][0] - 1e-6 or u["x范围"][1] > b["x范围"][1] + 1e-6:
                out_of_bounds.append({"类型": "单元x区间越出楼栋", "楼栋": b["楼栋"], "单元": u["名称"],
                                      "楼栋x范围": b["x范围"], "单元x范围": u["x范围"],
                                      "处置": "边界错误，必须修（单元不可能比楼栋宽）"})
    # 共享锚点组：同一句共享标题（如「7#、8#楼综合布线系统图」）展开出的多个楼栋锚在
    # 同一 (x,y)，其 x 范围**由构造相同** —— 这不是切分错误，但意味着「边界无法由标题区分」，
    # 必须显式登记（否则会被误报成缺陷，也会让人误以为边界可用）。
    share_groups, _byx = [], {}
    for b in bldg_boundaries:
        # 键取 **x**：楼栋 x 范围由 compute_bldg_ranges(锚点x) 唯一决定，与 y 无关。
        # 同一共享标题的两句文字 y 可差十几单位（实测 1#/3# 差 14.9），按 (x,y) 全同判会漏。
        _byx.setdefault(round(b["锚点"]["x"], 2), []).append((b["楼栋"], b["锚点"]["y"]))
    for kx, v in sorted(_byx.items()):
        if len(v) > 1:
            share_groups.append({
                "锚点x": kx,
                "各栋锚点y": {n: y for n, y in v},
                "楼栋": sorted([n for n, _y in v], key=C.bldg_num),
                "说明": "锚点 x 相同的多楼栋（同一共享标题展开 / 标题重复绘制），"
                        "x 范围**由构造相同**；边界不能靠标题区分，须按各楼系统图的实际图区另行核定",
            })

    for i in range(len(bldg_boundaries)):
        for j in range(i + 1, len(bldg_boundaries)):
            A, B = bldg_boundaries[i], bldg_boundaries[j]
            lo, hi = max(A["x范围"][0], B["x范围"][0]), min(A["x范围"][1], B["x范围"][1])
            if hi - lo <= 1e-6:
                continue
            # 同锚点 = x 相同（x 范围只由 x 决定）；y 差多少都不影响范围是否由构造相同
            same_anchor = round(A["锚点"]["x"], 2) == round(B["锚点"]["x"], 2)
            same_band = abs(A["锚点"]["y"] - B["锚点"]["y"]) <= 100
            if same_anchor:
                overlaps.append({
                    "类型": "楼栋x区间重叠(共享锚点)", "甲": A["楼栋"], "乙": B["楼栋"],
                    "重叠x": [round(lo, 2), round(hi, 2)], "重叠宽度": round(hi - lo, 2),
                    "锚点y": [A["锚点"]["y"], B["锚点"]["y"]], "同行带": same_band, "须修": False,
                    "处置": "同一共享标题展开 → 范围**由构造相同**，非切分错误；"
                            "但该边界不足以区分这几栋，须另行核定",
                })
            else:
                overlaps.append({
                    "类型": "楼栋x区间重叠(异锚点)", "甲": A["楼栋"], "乙": B["楼栋"],
                    "重叠x": [round(lo, 2), round(hi, 2)], "重叠宽度": round(hi - lo, 2),
                    "锚点y": [A["锚点"]["y"], B["锚点"]["y"]], "同行带": same_band,
                    "须修": bool(same_band),
                    "处置": "同行带内重叠=切分错误（必须修）"
                            if same_band else
                            "跨行带 x 重叠属正常（系统图上下叠放），但按 x 归属会串扰 —— 须带内切分",
                })
    for b in bldg_boundaries:
        us = b["单元"]
        for i in range(len(us)):
            for j in range(i + 1, len(us)):
                lo, hi = max(us[i]["x范围"][0], us[j]["x范围"][0]), min(us[i]["x范围"][1], us[j]["x范围"][1])
                if hi - lo > 1e-6:
                    overlaps.append({"类型": "单元x区间重叠", "楼栋": b["楼栋"],
                                     "甲": us[i]["名称"], "乙": us[j]["名称"],
                                     "重叠x": [round(lo, 2), round(hi, 2)],
                                     "重叠宽度": round(hi - lo, 2), "同行带": True, "须修": True,
                                     "处置": "切分错误，必须修"})

    coord_bad = sum(v["缺x或y"] for v in completeness.values())
    must_fix = len(out_of_bounds) + sum(1 for o in overlaps if o.get("须修"))
    ledger_out = {
        "DXF文件": os.path.basename(dxf),
        "几何缓存": cache,
        "参数": p,
        "参数来源": psrc,
        "参数说明": pnotes,
        "元素台账": ledger,
        "楼栋单元边界": bldg_boundaries,
        "校验": {
            "坐标完整性": completeness,
            "坐标缺失合计": coord_bad,
            "单元越出楼栋": out_of_bounds,
            "区间重叠": overlaps,
            "共享锚点组": share_groups,
            "必须修的边界问题合计": must_fix,
            "边界缺项": bnd_missing,
            "结论": ("坐标完整、边界无越界、无必须修的区间重叠"
                     if coord_bad == 0 and must_fix == 0
                     else "**存在坐标缺失 / 单元越界 / 必须修的区间重叠 → 不得直接出表**"),
        },
        "缺项": missing,
        "待确认": pending,
    }

    if args.parse and os.path.exists(args.parse):
        try:
            pj = json.load(io.open(args.parse, encoding="utf-8"))
            pf = []
            for bn, bd in (pj.get("楼栋") or {}).items():
                for un, ud in (bd.get("单元") or {}).items():
                    for fx in (ud.get("分纤箱") or []):
                        pf.append({"楼栋": bn, "单元": un, "编号": fx.get("编号"),
                                   "x": fx.get("x"), "y": fx.get("y")})
            ledger_out["与parse对账"] = {
                "parse分纤箱数": len(pf),
                "台账文字编号数": len(fx_txt),
                "parse缺x的分纤箱数": sum(1 for d in pf if d.get("x") is None),
                "结论": ("parse 分纤箱缺 x → 几何侧以台账为准补齐"
                         if any(d.get("x") is None for d in pf) else "parse 已带 x，两路可互校"),
            }
        except Exception as e:
            log.warning("读 --parse 失败：%s", e)

    try:
        C.write_json(out, ledger_out, log=log)
    except OSError as e:
        log.error("无法写入台账 %s: %s", out, e)
        sys.exit(4)

    log.info("\n===== 元素台账摘要（%s）=====", os.path.basename(dxf))
    for k, v in ledger.items():
        n = v.get("数量", v.get("属性命中数", v.get("线段数", v.get("楼层线数", ""))))
        log.info("  %-8s 数量=%-7s x范围=%s  y范围=%s", k, n, v.get("x范围"), v.get("y范围"))
    log.info("  楼栋 %d 栋、单元 %d 个；坐标缺失 %d；必须修的边界问题 %d",
             len(bldg_boundaries), sum(len(b["单元"]) for b in bldg_boundaries), coord_bad, must_fix)
    if p["wire_layers_excluded"]:
        log.info("  线缆候选中已排除建筑电气层：%s", p["wire_layers_excluded"])
    if ledger_out["校验"]["共享锚点组"]:
        for gr in ledger_out["校验"]["共享锚点组"]:
            log.warning("  [共享锚点] 锚点x=%.2f 下共 %d 栋（%s）—— x 范围由构造相同，"
                        "非切分错误，但边界不能靠标题区分，须另行核定",
                        gr["锚点x"], len(gr["楼栋"]), "、".join(gr["楼栋"]))
    if missing:
        log.warning("  缺项 %d：%s", len(missing), "；".join(m["元素"] for m in missing))
    log.info("台账已写入: %s", out)
    sys.exit(2 if (coord_bad or must_fix) else 0)


if __name__ == "__main__":
    main()
