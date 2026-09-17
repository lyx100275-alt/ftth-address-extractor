#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""读取标注（图签形态）· 探查：量测 6 个几何容差的建议值

为什么单独出一个脚本：`read_titleblock_households.py` 的 6 个几何容差与图纸
坐标尺度绑定（不同图纸可差几个数量级），文档要求「必须由探查量测」，此前却
没有配套量测手段 —— 现场只能自己现写探针。本脚本把量测固化成一步命令。

量测原理（与 analyze_coverage.py 的「层高自适应」同源）：不预设任何坐标值，
从图纸自身量出「图签行距」当尺子——
    楼名行 <-> 层户行的 y 间距   -> dy-lo / dy-hi
    同块内 楼名 <-> 层户 的 x 间距 -> dx-tol
    层户行 <-> 单元行的 y 间距   -> unit-dy-lo / unit-dy-hi
    同块内 层户 <-> 单元 的 x 间距 -> unit-dx
统计一律取「主簇」，跨图签块的离群误配会被滤掉；配对同时施加**方向**与**同列**
两重先验（详见 ftth_common.estimate_titleblock_tolerances 的说明）。

关于 --band：本脚本**只用它做交叉校验**，不据它替换建议值。
  一张图混排多个地块时，各段排版可能不同；脚本会逐段独立量一次，与全图
  （各段并集）量出的窗口比对。若有段落的窗口落在全图窗口之外，说明该段用
  全图容差会丢户，脚本会告警并给出「该段单独出表」的命令。实测（验证图：多地块混排竣工图）
  各段窗口均落在全图窗口内、配对率 100%，故全图单组容差即可，无需分组。

用法:
  # 自动推荐图签层并量测
  python probe_titleblock_tolerances.py --dxf 图纸.dxf

  # 指定图层 / 自定义正则 / 多地块交叉校验 / 落盘
  python probe_titleblock_tolerances.py --dxf 图纸.dxf --layer <图签层> \
      --bldg-re "\\d+号楼" \
      --band 地块A:<ymin>:<ymax> --band 地块B:<ymin>:<ymax> --out probe.json

输出末段给出一条可直接粘贴的 `read_titleblock_households.py` 命令行。
注意：这 6 个参数**缺省时解析脚本会自行按图自适应**，本脚本给的是建议值，
供你在跑正式解析前核对；两者不一致以显式传入为准。

退出码：0 成功；1 输入/文件错误；2 量测不出（信号不足 / 排版方向异常）
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import os
import re
import sys

from ftth_common import ToleranceEstimateError, estimate_titleblock_tolerances

DEFAULT_BLDG_RE = r"\d+\s*[#＃号]?\s*楼"
DEFAULT_LEV_RE = r"(\d+)层/(\d+)户"
DEFAULT_UNIT_RE = r"\d+单元"

TOL_KEYS = ('dx_tol', 'dy_lo', 'dy_hi', 'unit_dx', 'unit_dy_lo', 'unit_dy_hi')


def load_layer_texts(path, layer=None):
    """读 DXF 中的 TEXT/MTEXT，返回 {图层: [(x, y, 文本), ...]}。layer 给定时只读该层。

    走 ftth_common.load_geom 几何缓存（免全量解析）；缓存内 MTEXT 为 plain_text，
    段落符 \n 归一为空格，与原生 `replace('\\P', ' ')` 口径一致（等价性已实测）。
    """
    from ftth_common import load_geom
    g = load_geom(path)
    out = collections.defaultdict(list)
    for lay, x, y, s in (g.get("texts") or []):
        if layer and lay != layer:
            continue
        out[lay].append((float(x), float(y), str(s).replace("\n", " ").strip()))
    return out


def rank_layers(by_layer, lev_re):
    """按「形如 N层/M户 的文字条数」给图层排序 —— 这是图签层最强的机器可检特征。"""
    score = {lay: sum(1 for _, _, s in tx if re.fullmatch(lev_re, s))
             for lay, tx in by_layer.items()}
    return sorted(score.items(), key=lambda kv: -kv[1])


def parse_bands(specs):
    """[name:ymin:ymax, ...] -> [(name, ymin, ymax), ...]"""
    out = []
    for sp in specs or []:
        name, lo, hi = sp.rsplit(':', 2)
        out.append((name, float(lo), float(hi)))
    return out


def _est_or_none(texts, a):
    """量一次；量不出（信号不足 / 方向异常）返回异常对象而不中断，供分段校验收集。"""
    try:
        return estimate_titleblock_tolerances(texts, a.bldg_re, a.lev_re, a.unit_re, a.safety)
    except ToleranceEstimateError as ex:
        return ex


def _covers(outer, inner):
    """inner 的 [lo, hi] 是否被 outer 覆盖（用于判断该段用全图窗口会不会丢户）。"""
    o_lo, o_hi = outer
    i_lo, i_hi = inner
    if None in (o_lo, o_hi, i_lo, i_hi):
        return True
    return o_lo <= i_lo and i_hi <= o_hi


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='读取标注（图签形态）· 量测 6 个几何容差的建议值')
    ap.add_argument('--dxf', required=True, help='DXF 图纸路径')
    ap.add_argument('--layer', default=None, help='图签/标题栏所在图层；缺省自动推荐')
    ap.add_argument('--bldg-re', default=DEFAULT_BLDG_RE, help='楼名正则（默认匹配 1#楼 / 1号楼）')
    ap.add_argument('--lev-re', default=DEFAULT_LEV_RE, help='层户正则（默认匹配 N层/M户）')
    ap.add_argument('--unit-re', default=DEFAULT_UNIT_RE, help='单元正则（默认匹配 N单元）')
    ap.add_argument('--safety', type=float, default=1.25,
                    help='建议值相对实测范围的外扩系数（默认 1.25）')
    ap.add_argument('--band', action='append', default=[],
                    help='地块分段 name:ymin:ymax，可重复；用于**交叉校验**各段窗口是否被全图窗口覆盖')
    ap.add_argument('--out', default=None, help='把量测结果写成 JSON')
    a = ap.parse_args(argv)

    if not os.path.isfile(a.dxf):
        sys.stderr.write('[ERROR] 找不到 DXF 文件: %s\n' % a.dxf)
        return 1
    try:
        by_layer = load_layer_texts(a.dxf, a.layer)
    except Exception as ex:                                        # noqa: BLE001
        sys.stderr.write('[ERROR] 读取 DXF 失败: %s\n' % ex)
        return 1

    total = sum(len(v) for v in by_layer.values())
    if a.layer:
        if a.layer not in by_layer:
            sys.stderr.write('[ERROR] 图层 %r 不存在或其中没有文字。可用图层：%s\n'
                             % (a.layer, '、'.join(sorted(by_layer)[:20])))
            return 1
        texts = by_layer[a.layer]
        print('[图层] 指定 %s，文字 %d 条' % (a.layer, len(texts)))
    else:
        ranked = rank_layers(by_layer, a.lev_re)
        print('[图层推荐] 全图 %d 条文字，按「形如 N层/M户 的文字条数」排序：' % total)
        for lay, n in ranked[:5]:
            if n == 0:
                continue
            print('    %-28s %4d 条%s' % (lay, n, '   ← 建议' if n == ranked[0][1] else ''))
        if not ranked or ranked[0][1] == 0:
            sys.stderr.write(
                '[ERROR] 全部图层都没有形如 `N层/M户` 的文字，无法定位图签层。\n'
                '  可能原因：① 本图不含图签（标题栏）；② 层户写法不同，请用 --lev-re 指定。\n')
            return 2
        a.layer = ranked[0][0]
        texts = by_layer[a.layer]
        print('[图层] 采用 %s（%d 条文字）' % (a.layer, len(texts)))

    segs = parse_bands(a.band)
    if segs:
        in_seg = [t for t in texts if any(lo <= t[1] <= hi for _, lo, hi in segs)]
        print('[分段] --band 共 %d 段，段内文字 %d / 全图 %d 条'
              % (len(segs), len(in_seg), len(texts)))
        texts = in_seg

    est = _est_or_none(texts, a)
    if isinstance(est, Exception):
        sys.stderr.write(
            '[ERROR] 量测不出几何容差：%s\n'
            '  请用 --bldg-re / --lev-re / --unit-re 校正正则，或用 --layer 换图层后重试；\n'
            '  若确为排版方向与默认相反，请显式传入 --unit-dy-lo/--unit-dy-hi（负区间）。\n'
            % est)
        return 2

    ev = est.pop('证据')
    print('\n[信号计数] 楼名 %d / 层户 %d / 单元 %d'
          % (ev['楼名数'], ev['层户数'], ev['单元数']))
    for k in ('楼名<->层户', '层户<->单元'):
        if k in ev:
            print('[实测] %s  %s' % (k, json.dumps(ev[k], ensure_ascii=False)))

    print('\n[建议几何容差]（实测范围外扩 %.2f 倍；请对照图纸核对）' % a.safety)
    for n in TOL_KEYS:
        v = est.get(n)
        print('    --%-14s %s' % (n.replace('_', '-'),
                                  ('%.1f' % v) if v is not None else '（本次未量出）'))

    # ---------- 分地块交叉校验（2026-09-13 新增）----------
    # 只校验、不替换：一张图混排多地块时各段排版可能不同，若某段窗口落在全图窗口之外，
    # 该段用全图容差就会丢户。此时告警并给出「该段单独出表」的命令，而不是自动分组——
    # 实测分块量测样本少、统计不稳（配对率曾低至 12/24），不如全图一组稳妥。
    seg_checks, warn = [], []
    if segs:
        print('\n[分地块交叉校验]（各段独立量测，仅核对全图窗口是否覆盖本段）')
        for name, lo, hi in segs:
            sub = [t for t in texts if lo <= t[1] <= hi]
            r = _est_or_none(sub, a)
            if isinstance(r, Exception):
                print('    %-10s ✗ 量不出：%s' % (name, r))
                warn.append('%s：段内量测失败（%s）' % (name, r))
                seg_checks.append({'地块': name, '文字数': len(sub), '量测': '失败', '原因': str(r)})
                continue
            r.pop('证据', None)
            ok_dy = _covers((est.get('unit_dy_lo'), est.get('unit_dy_hi')),
                            (r.get('unit_dy_lo'), r.get('unit_dy_hi')))
            mark = '⊂ 全图 ✓' if ok_dy else '⊄ 全图 ⚠'
            print('    %-10s 文字%3d  unit-dy[%s, %s]  %s'
                  % (name, len(sub), r.get('unit_dy_lo'), r.get('unit_dy_hi'), mark))
            seg_checks.append({'地块': name, '文字数': len(sub),
                               'unit_dy_lo': r.get('unit_dy_lo'), 'unit_dy_hi': r.get('unit_dy_hi'),
                               'unit_dx': r.get('unit_dx'),
                               'dx_tol': r.get('dx_tol'),
                               '窗口被全图覆盖': ok_dy})
            if not ok_dy:
                warn.append('%s：unit-dy 窗口 [%s, %s] 落在全图窗口 [%s, %s] 之外'
                            % (name, r.get('unit_dy_lo'), r.get('unit_dy_hi'),
                               est.get('unit_dy_lo'), est.get('unit_dy_hi')))
        if warn:
            print('    ⚠ ' + '；'.join(warn))
            print('      → 这些地块用全图容差可能丢户。请把该段单独出一次（--band 只给该段），'
                  '并按该段的量测值显式传参：')
            for name, lo, hi in segs:
                if any(name in w for w in warn):
                    print('        python probe_titleblock_tolerances.py --dxf <图纸> '
                          '--layer %s --band %s:%g:%g' % (a.layer, name, lo, hi))
        else:
            print('    → 各段窗口均落在全图窗口内，全图单组容差可用，无需分组。')

    print('\n[可直接使用] 补齐 <图纸> 与上下文参数即可：')
    print('python read_titleblock_households.py --dxf <图纸> --floor-layer %s \\' % a.layer)
    print('    --dx-tol %s --dy-lo %s --dy-hi %s \\'
          % (est['dx_tol'], est['dy_lo'], est['dy_hi']))
    if est.get('unit_dx') is not None:
        print('    --unit-dx %s --unit-dy-lo %s --unit-dy-hi %s \\'
              % (est['unit_dx'], est['unit_dy_lo'], est['unit_dy_hi']))
    print('    --out households.json')
    print('  提示：这 6 个参数现在缺省时脚本会自行按图自适应，本值供核对；'
          '两者不一致时以显式传入为准。')

    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        with io.open(a.out, 'w', encoding='utf-8') as f:
            json.dump({'dxf': a.dxf, '图层': a.layer, '信号计数': ev,
                       '建议几何容差': est, '分地块交叉校验': seg_checks or None}, 
                      f, ensure_ascii=False, indent=2)
        print('\n[写出] %s' % a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
