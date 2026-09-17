# -*- coding: utf-8 -*-
"""split_bands.py —— 多地块图纸按 y 带裁剪出子 DXF（2026-09-17 新增）。

用途：一张 DXF 含多个独立地块、各块楼号从 1 起（同名楼）时，全图 parse 会因
锚点池按楼名去重而串号（find_bldg_anchors 的 MultiPlotDuplicateAnchorError 守卫
会拦下并提示走到本步骤）。先用本脚本按 y 带切出各地块子 DXF，再对每个子图分别跑
parse / coverage 等下游子命令。

用法（推荐经统一入口）：
  ftth.py split-band --dxf 全图.dxf --out-dir <目录> --band "1:ymin:ymax" --band "2:..."
  --band 可重复传，也可在单个值里用逗号分隔多条（"1:ymin:ymax,2:..."）。

y 带取值口径（与 read_titleblock_households.py --band 一致）：
  上界取上邻带标题 y、下界维持中点——反则切本带内容或吞邻带内容。
  分带边界应来自 probe 的 plot_band_annotations 信号或图签/系统图标题实测 y，
  不要凭文件名推断。

注意：无坐标实体不参与分带（保持被丢弃，实测不影响文字解析）；各带间 y 区间
若重叠，重叠区实体会同时进入两个子 DXF → 下游逐带统计会重复计数，故显式告警。
"""
import argparse
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from ftth_common import load_dxf

import ezdxf


def ent_y(e):
    """取实体代表性 y 坐标（文字/INSERT 用插入点，线段/多段线用顶点均值）。"""
    try:
        t = e.dxftype()
        if t in ("TEXT", "MTEXT", "INSERT"):
            return e.dxf.insert.y
        if t == "LINE":
            s, p = e.dxf.start, e.dxf.end
            return (s.y + p.y) / 2.0
        if t == "LWPOLYLINE":
            pts = list(e.get_points())
            return sum(p[1] for p in pts) / len(pts) if pts else None
        if t == "POLYLINE":
            try:
                vs = list(e.vertices)
                if vs:
                    return sum(v.dxf.location.y for v in vs) / len(vs)
            except Exception:
                pass
            return None
        return None
    except Exception:
        return None


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


def main():
    ap = argparse.ArgumentParser(description="多地块 DXF 按 y 带裁剪（同名楼分带解析前置）")
    ap.add_argument("dxf", help="输入全图 DXF 路径")
    ap.add_argument("--out-dir", required=True, help="子 DXF 输出目录（自动创建）")
    ap.add_argument("--band", action="append", required=True,
                    help='分带参数 "名称:ymin:ymax"，可重复；单值内可用逗号分隔多条')
    args = ap.parse_args()

    bands = parse_bands(args.band)
    if not os.path.exists(args.dxf):
        raise SystemExit("[split-band] 输入 DXF 不存在: %s" % args.dxf)
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
        out = os.path.join(args.out_dir, "band%s.dxf" % name)
        doc2.saveas(out)
        if kept == 0:
            empty_bands.append(name)
        print("band%s: kept=%d dropped=%d -> %s" % (name, kept, dropped, out))

    if empty_bands:
        # 空带 = 分带边界错（该带里没有任何实体）——早失败，不产出空子图
        print("[ERROR] %d 个分带裁出 0 个实体：%s —— 分带 y 边界大概率填错"
              "（应取地块标题/图签实测 y，上界=上邻带标题 y、下界=中点），请修正后重跑"
              % (len(empty_bands), ",".join(empty_bands)))
        sys.exit(2)
    print("裁剪完成：%d 个子 DXF -> %s" % (total, args.out_dir))


if __name__ == "__main__":
    main()
