#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""箱位直读标注提取 —— 「N号楼M单元K层」格式标注 → fx_locations.json（2026-09-16，12坑复核·坑9）

适用信号：图纸文字层存在「N号楼M单元K层」格式的箱位直读标注（probe 信号
    fx_location_annotation = present 时）。此类标注直接给出每个分纤箱的
    楼栋/单元/安装层，是箱位最可靠的**独立第二来源**——V型谷底、竖线法、
    系统图 F 标注都需要跨区几何关联，而它把三件事写在同一处。

定位：**交叉校验数据源**，不自动替代任何方法的结果。与 V型法/竖线法的
    安装层判定并列举证，不一致交人裁定（原则二：不自行择一）。

用法：
  python extract_fx_locations.py --dxf 图纸.dxf --out fx_locations.json
  python extract_fx_locations.py --dxf 图纸.dxf --text-layer TEL_TEXT,GCD_HC --out fx_locations.json

输出 JSON：
  标注实例：逐条收录（同一 楼/单元/层 在多图幅重复绘制时各实例均保留）
  唯一箱位：按 (楼栋,单元,安装层) 去重后的清单 + 实例计数
  矛盾箱位：同一 (楼栋,单元) 对应多个不同安装层 → 显式登记，交人工裁决

退出码：0 正常；1 参数/信号缺失
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(description='箱位直读标注提取（N号楼M单元K层 → fx_locations.json）')
    ap.add_argument('--dxf', required=True)
    ap.add_argument('--text-layer', default=None,
                    help='文字图层，逗号分隔；缺省扫描全部图层（结果按图层分组展示，便于定位）')
    ap.add_argument('--pattern', default=None,
                    help='覆盖内置正则（捕获组：楼号,单元号,安装层）。内置兼容 '
                         '「N号楼M单元K层」「N#楼M单元K层」「N号楼M单元KF」写法；'
                         '本图写法不同（如「M单元K层」无楼号）时显式提供')
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)

    # 内置正则：楼号写法 号楼/#楼 并列；层写法 层/F 并列；允许空白。
    loc_re = re.compile(a.pattern) if a.pattern else re.compile(
        r'(\d+)\s*(?:号楼|#\s*楼)\s*(\d+)\s*单元\s*(?:安装(?:在|于)?\s*)?(\d+)\s*(?:层|F(?!\w))')

    from ftth_common import load_geom
    try:
        g = load_geom(a.dxf)
    except Exception as ex:                                        # noqa: BLE001
        sys.stderr.write('[ERROR] 读取 DXF 失败: %s\n' % ex)
        return 1

    layers = None
    if a.text_layer:
        layers = {x.strip() for x in a.text_layer.split(',') if x.strip()}

    instances = []
    for lay, x, y, s in (g.get('texts') or []):
        if layers is not None and lay not in layers:
            continue
        t = str(s).replace('\n', ' ').strip()
        m = loc_re.search(t)
        if not m:
            continue
        instances.append({'楼栋': int(m.group(1)), '单元': int(m.group(2)),
                          '安装层': int(m.group(3)),
                          'x': round(float(x), 1), 'y': round(float(y), 1),
                          '图层': lay, '文字': t})

    if not instances:
        sys.stderr.write('[参数/信号缺失] 未匹配到任何「N号楼M单元K层」格式标注'
                         '（图层筛选=%s）。若 probe 信号 fx_location_annotation=present，'
                         '请核对 --text-layer 或用 --pattern 覆盖内置正则。\n'
                         % (a.text_layer or '全部图层'))
        return 1

    # 唯一箱位：按 (楼,单元,层) 聚合实例（重复绘制不静默丢弃，登记实例数）
    by_loc = collections.defaultdict(list)
    for e in instances:
        by_loc[(e['楼栋'], e['单元'], e['安装层'])].append(e)
    unique = [{'楼栋': b, '单元': u, '安装层': f, '实例数': len(v),
               '实例': [{'x': e['x'], 'y': e['y'], '图层': e['图层']} for e in v]}
              for (b, u, f), v in sorted(by_loc.items())]

    # 矛盾箱位：同一 (楼,单元) 对应多个不同安装层 —— 多箱单元（低区/高区各一箱）
    # 属正常；但配合实例数可发现标注错误。只登记、不判定。
    by_bu = collections.defaultdict(set)
    for b, u, f in by_loc:
        by_bu[(b, u)].add(f)
    conflicts = [{'楼栋': b, '单元': u, '安装层集合': sorted(fs),
                  '说明': '同一单元多个安装层：多箱单元（低/高区）属正常，请人工核对'}
                 for (b, u), fs in sorted(by_bu.items()) if len(fs) > 1]

    layer_stat = collections.Counter(e['图层'] for e in instances)

    result = {
        '来源': '箱位直读标注提取（N号楼M单元K层）',
        '用途': '安装层判定的独立第二来源——与 V型法/竖线法结果交叉校验；'
               '不一致时并列证据交人裁定，本脚本不自动择一',
        '正则': a.pattern or '内置（号楼/#楼 × 层/F）',
        '图层筛选': a.text_layer or '全部图层',
        '标注实例数': len(instances),
        '唯一箱位数': len(unique),
        '图层分布': dict(layer_stat),
        '标注实例': instances,
        '唯一箱位': unique,
        '矛盾箱位': conflicts,
        '需人工复核': True,
        '复核说明': '直读标注可能含笔误（如实测某图 2号楼/3号楼 图签笔误）；'
                   '与系统图标题楼号集合比对可定位',
    }

    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as fp:
        json.dump(result, fp, ensure_ascii=False, indent=1)

    print('[提取] 标注实例 %d 条 → 唯一箱位 %d 个（图层分布 %s）'
          % (len(instances), len(unique), dict(layer_stat)))
    if conflicts:
        print('[⚠] 矛盾箱位 %d 个（同一单元多个安装层），需人工核对：' % len(conflicts))
        for c in conflicts[:10]:
            print('    %d号楼%d单元 → 层 %s' % (c['楼栋'], c['单元'], c['安装层集合']))
    print('[写出] %s' % a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
