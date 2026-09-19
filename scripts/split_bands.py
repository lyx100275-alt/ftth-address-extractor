# -*- coding: utf-8 -*-
"""split_bands.py —— 多地块图纸按 y 带裁剪出子 DXF（2026-09-17 新增）。

用途：一张 DXF 含多个独立地块、各块楼号从 1 起（同名楼）时，全图 parse 会因
锚点池按楼名去重而串号（find_bldg_anchors 的 MultiPlotDuplicateAnchorError 守卫
会拦下并提示走到本步骤）。先用本脚本按 y 带切出各地块子 DXF，再对每个子图分别跑
parse / coverage 等下游子命令。

用法（推荐经统一入口）：
  ftth.py split-band --dxf 全图.dxf --out-dir <目录> --band "1:ymin:ymax" --band "2:..."
  --band 可重复传，也可在单个值里用逗号分隔多条（"1:ymin:ymax,2:..."）。

  # 自动模式（2026-09-18 新增）：由图上实测的「N块地」锚点自动算分带窗口
  ftth.py split-band --auto --config <config.json> --dxf 全图.dxf --out-dir <目录>
  默认只打印方案（含每个锚点原文/坐标/被排除项），核对无误后加 --yes 执行。

y 带取值口径：
  · 图上有「N块地」类**地块锚点**时 → 用 `--auto`：切点取**相邻锚点 y 的中点**，
    首带上界取图幅顶、末带下界取图幅底（只用「锚点顺序 + 相邻中点」两个客观量）。
  · 图上无锚点、只能按**楼栋标题**定界时 → 人工给 `--band`：上界取上邻带标题 y、
    下界取本带标题 y，**不得取相邻标题中点**（实测中点会横穿本带内容）。
  `--auto` 走 ftth_common.derive_plot_bands（唯一权威实现，与 probe 画像里的
  「分带窗口」同源同算法），并附三项独立核对（切点空置 / 带内自证 / 标题不跨带），
  疑点不阻塞但必须报人。

注意：无坐标实体不参与分带（保持被丢弃，实测不影响文字解析）；各带间 y 区间
若重叠，重叠区实体会同时进入两个子 DXF → 下游逐带统计会重复计数，故显式告警。
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from ftth_common import (load_dxf, collect_texts, derive_plot_bands, ent_y,
                         is_bldg_title_text)

import ezdxf


def parse_bands(specs):
    """解析 "名称:ymin:ymax"（列表/逗号混合），校验数值与区间合法性。"""
    items = []
    for spec in specs:
        for piece in str(spec).split(","):
            piece = piece.strip()
            if not piece:
                continue
            parts = piece.rsplit(":", 2)
            if len(parts) != 3:
                raise SystemExit("[split-band] --band 格式应为 名称:ymin:ymax，收到: %r" % piece)
            name, ymin, ymax = parts[0].strip(), parts[1], parts[2]
            try:
                ymin, ymax = float(ymin), float(ymax)
            except ValueError:
                raise SystemExit("[split-band] --band 的 ymin/ymax 必须是数字: %r" % piece)
            if not name:
                raise SystemExit("[split-band] --band 名称不能为空: %r" % piece)
            if ymin >= ymax:
                raise SystemExit("[split-band] --band 要求 ymin < ymax: %r" % piece)
            items.append((name, ymin, ymax))
    if not items:
        raise SystemExit("[split-band] 未收到任何有效 --band")
    # 重叠检测：重叠区实体会进两个子图 → 逐带统计重复计数
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            n1, lo1, hi1 = items[i]
            n2, lo2, hi2 = items[j]
            if lo1 < hi2 and lo2 < hi1:
                print("[WARN] 分带 %s 与 %s 的 y 区间重叠（%.0f ~ %.0f）——"
                      "重叠区实体会同时进入两个子 DXF，下游逐带统计会重复计数，请核对分带边界"
                      % (n1, n2, max(lo1, lo2), min(hi1, hi2)))
    return items


def _cfg_text_layer(cfg_path):
    """从 config.json 读文字图层与标题正则建议值（缺失则 None，不猜）。"""
    tl = tp = None
    if not cfg_path:
        return tl, tp
    if not os.path.isfile(cfg_path):
        raise SystemExit("[split-band] --config 不存在: %s" % cfg_path)
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    sp = cfg.get("suggested_params") or {}
    v = sp.get("text_layer")
    if v:
        tl = [s.strip() for s in str(v).split(",") if s.strip()]
    v = sp.get("title_pattern")
    if v:
        tp = str(v)
    return tl, tp


def auto_bands(dxf, text_layer, title_pattern):
    """由实测锚点算分带窗口。返回 (bands, info, err, warns)。

    走 ftth_common.derive_plot_bands（**唯一权威**：与画像里「分带窗口」同源同算法）。
    """
    doc, msp = load_dxf(dxf)
    all_texts = collect_texts(msp, None, ["MTEXT", "TEXT"])
    d = derive_plot_bands(msp, all_texts)
    wins = d["分带窗口"] or []
    # 标题判据样本数：仅供人核对「楼栋标题不跨带」这一核对是否真有对象。
    # 缺省用通用判据；给了 --title-pattern 则按正则。**不参与切分**。
    if title_pattern:
        import re as _re
        _tr = _re.compile(title_pattern)
        _n_title = sum(1 for t in all_texts if _tr.search(t.get("内容") or ""))
    else:
        _n_title = sum(1 for t in all_texts if is_bldg_title_text(t.get("内容") or ""))
    info = dict(d)
    info.update({"全文字数": len(all_texts), "标题判据样本": _n_title})
    bands = [(w["名称"], w["ymin"], w["ymax"]) for w in wins]
    return (None if d["错误"] else bands), info, d["错误"], d["疑点"]


def _print_plan(bands, info, warns):
    print("=" * 72)
    print("分带方案（由实测锚点自动计算；核对后再加 --yes 执行）")
    print("=" * 72)
    print("图幅 y：%s（顶） ~ %s（底）；文字 %s 条；锚点 %d 个；标题判据样本 %s 条"
          % ("%.1f" % info["y_top"] if info.get("y_top") is not None else "?",
             "%.1f" % info["y_bot"] if info.get("y_bot") is not None else "?",
             info.get("全文字数", "?"), len(info.get("锚点") or []),
             info.get("标题判据样本", "?")))
    print("-" * 72)
    print("%-16s %16s %16s %16s %s" % ("名称", "ymin", "ymax", "锚点y", "锚点x"))
    for row in (bands or []):
        n, lo, hi = row
        a = next((x for x in (info.get("锚点") or []) if x["文字"] == n), {})
        print("%-16s %16.1f %16.1f %16.1f %s" % (n, lo, hi, a.get("y", 0), a.get("x", "")))
    print("-" * 72)
    print("含地块词的全部命中（%d 条，含被排除者）：" % len(info.get("命中") or []))
    for h in sorted(info.get("命中") or [], key=lambda x: -x["y"]):
        print("   y=%-16.1f x=%-16s %s" % (h["y"], h["x"], h["文字"]))
    if info.get("锚点排除"):
        print("-" * 72)
        print("被排除项（不静默丢弃，逐条给原因）：")
        for h in info["锚点排除"]:
            print("   y=%-16.1f %-24s → %s" % (h["y"], h["文字"], h["原因"]))
    print("-" * 72)
    if warns:
        print("独立核对疑点 %d 条（不阻塞，但**不得当作已核**，请人工过目）：" % len(warns))
        for w in warns:
            print("   ! %s" % w)
    else:
        print("独立核对：切点空置 / 带内自证 / 楼栋标题不跨带 —— 三项均无疑点。")
    print("=" * 72)


def main():
    ap = argparse.ArgumentParser(description="多地块 DXF 按 y 带裁剪（同名楼分带解析前置）")
    ap.add_argument("dxf", help="输入全图 DXF 路径")
    ap.add_argument("--out-dir", help="子 DXF 输出目录（自动创建）")
    ap.add_argument("--band", action="append",
                    help='分带参数 "名称:ymin:ymax"，可重复；单值内可用逗号分隔多条')
    ap.add_argument("--auto", action="store_true",
                    help="由图上实测的地块锚点自动算分带窗口（默认只出方案）")
    ap.add_argument("--yes", action="store_true", help="--auto 下确认执行")
    ap.add_argument("--text-layer", help="文字图层（逗号分隔）；缺省读 --config 建议值")
    ap.add_argument("--title-pattern", help="楼栋标题正则；缺省用通用标题判据")
    ap.add_argument("--config", help="探查生成的 config JSON（读 text_layer / title_pattern）")
    args = ap.parse_args()

    if not os.path.exists(args.dxf):
        raise SystemExit("[split-band] 输入 DXF 不存在: %s" % args.dxf)
    if args.auto and args.band:
        raise SystemExit("[split-band] --auto 与 --band 互斥：自动分带不接受人工边界")

    cfg_tl, cfg_tp = _cfg_text_layer(args.config)

    if args.auto:
        tl = ([s.strip() for s in args.text_layer.split(",") if s.strip()]
              if args.text_layer else cfg_tl)
        tp = args.title_pattern or cfg_tp
        bands, info, err, warns = auto_bands(args.dxf, tl, tp)
        _print_plan(bands, info, warns)
        if err:
            print("[ERROR] 无法自动分带：%s" % err)
            sys.exit(2)
        if not args.yes:
            print("[plan] 以上仅为方案，未写任何文件。核对无误后加 --yes 执行。")
            return
        if not args.out_dir:
            raise SystemExit("[split-band] --yes 执行必须给 --out-dir")
    else:
        if not args.band:
            raise SystemExit("[split-band] 需给 --band 或 --auto（人工边界 / 实测锚点自动）")
        if not args.out_dir:
            raise SystemExit("[split-band] --band 模式必须给 --out-dir")
        bands = parse_bands(args.band)

    os.makedirs(args.out_dir, exist_ok=True)

    doc, msp = load_dxf(args.dxf)

    # 复制图层表（按名；颜色/线型属性不复制——实测文字/INSERT 解析不受影响）
    layer_names = []
    for l in doc.layers:
        layer_names.append(l.dxf.name)

    total = len(bands)
    empty_bands = []
    for name, ymin, ymax in bands:
        doc2 = ezdxf.new(dxfversion=doc.dxfversion)
        msp2 = doc2.modelspace()
        for lname in layer_names:
            if lname not in doc2.layers:
                try:
                    doc2.layers.add(lname)
                except Exception:
                    pass
        kept = dropped = 0
        for e in msp:
            y = ent_y(e)
            if y is None:
                # 无坐标实体不参与分带（实测不影响文字解析）
                continue
            if ymin <= y <= ymax:
                try:
                    msp2.add_entity(e.copy())
                    kept += 1
                except Exception as ex:
                    print("  [skip-copy] %s %s" % (e.dxftype(), ex))
            else:
                dropped += 1
        safe = str(name).replace("/", "_").replace("\\", "_").replace(":", "_")
        out = os.path.join(args.out_dir, "band%s.dxf" % safe)
        doc2.saveas(out)
        if kept == 0:
            empty_bands.append(name)
        print("band%s: kept=%d dropped=%d -> %s" % (name, kept, dropped, out))

    if empty_bands:
        # 空带 = 分带边界错（该带里没有任何实体）——早失败，不产出空子图
        print("[ERROR] %d 个分带裁出 0 个实体：%s —— 分带 y 边界大概率填错"
              "（应取地块锚点实测 y），请修正后重跑"
              % (len(empty_bands), ",".join(empty_bands)))
        sys.exit(2)
    print("裁剪完成：%d 个子 DXF -> %s" % (total, args.out_dir))


if __name__ == "__main__":
    main()
