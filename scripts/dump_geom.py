#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量几何转储:一次性把 DXF 的 文字/INSERT/线段 抽成轻量 JSON 缓存。

用途:大图全量解析耗时可达分钟级,同一任务内任何新的几何维度查询
(INSERT 分布、某图层线段、坐标窗口统计等)都应读本缓存,不再回原图。

产物:图纸同目录 <DXF>.geom.json(--out 可改),结构:
  texts        : [layer, x, y, text]             TEXT/MTEXT
  inserts      : [layer, x, y, name, rot]        INSERT(五元组,保持兼容)
  insert_attrs : [{tag: value}|None, ...]        与 inserts 同索引的块属性(v3 新增)
  segs         : [layer, x1, y1, x2, y2, closed]  LINE/LWPOLYLINE/POLYLINE 拆段
                 (closed=1 表示该段属于闭合多段线的封口段)
  polylines    : [layer, [x1,y1,x2,y2,...], closed] **整组顶点**(v3 新增,不拆段)
  layers       : {layer: 实体总数}
  bbox         : 全部实体坐标包围盒
  stat         : 本次转储的耗时与体量(验收用)

v3 说明:segs 是**逐段拆开**的(实测某大图 52,934 条),无法还原"哪几段属于同一条
多段线";inserts 也不含块属性。凡需要"多段线整组顶点"或"INSERT 属性"的脚本,
此前只能退回 load_dxf(实测 pkl 命中仍需约 20s,而本缓存载入约 0.2s)。v3 补上
polylines 与 insert_attrs 后,这类查询也可走缓存。

经 ftth_common.load_geom(rebuild=True) 生成——缓存的载入/校验/落盘都由它负责,
本工具只做参数解析与统计输出,避免与消费侧出现两份实现。
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ftth_common  # noqa: E402

ftth_common.ensure_console_utf8()


def main():
    ap = argparse.ArgumentParser(description="DXF 全量几何转储(轻量 JSON 缓存)")
    ap.add_argument("--dxf", required=True, help="DXF 文件路径")
    ap.add_argument("--out", default=None, help="输出 JSON 路径(默认 <DXF>.geom.json 同目录)")
    args = ap.parse_args()

    dxf = os.path.abspath(args.dxf)
    out = os.path.abspath(args.out) if args.out else dxf + ".geom.json"

    t0 = time.time()
    geom = ftth_common.load_geom(dxf, rebuild=True, out=out)
    total_s = time.time() - t0

    stat = dict(dxf=dxf, dxf_mb=round(os.path.getsize(dxf) / 1048576, 1),
                total_s=round(total_s, 1),
                cache_mb=round(os.path.getsize(out) / 1048576, 2) if os.path.exists(out) else None,
                geom_version=ftth_common.GEOM_VERSION,
                n_entities=geom.get("n_entities"),
                n_texts=len(geom.get("texts") or []),
                n_inserts=len(geom.get("inserts") or []),
                n_insert_attrs=len([a for a in (geom.get("insert_attrs") or []) if a]),
                n_segs=len(geom.get("segs") or []),
                n_polylines=len(geom.get("polylines") or []),
                n_layers=len(geom.get("layers") or {}))
    print(json.dumps(stat, ensure_ascii=False, indent=2))
    print("saved ->", out)


if __name__ == "__main__":
    main()
