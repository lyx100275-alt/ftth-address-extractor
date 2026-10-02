#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""读取标注（图签形态）—— 从 FTTH 图纸图签（标题栏）层读出楼栋级入户规模

适用信号：图纸图签层（标题栏类图层）存在成对标注
    楼名  「N#楼」/「N号楼」
    层户  「N层/M户」
    单元  「N单元」/「M单元」
且三者在图形坐标上保持固定几何偏移（同图纸内为常数）。

输出每个地块下每栋楼的 {单元数, 层数, 每层户数} 及其证据坐标，
并附带图纸质量报告（重复绘制次数分布 / 疑似楼名笔误）。

用法示例（6 个几何容差可省略——缺省时脚本按本图自适应，并把推定值打印出来）：
  # 最简：不给几何容差
  python read_titleblock_households.py \
      --dxf 图纸.dxf --floor-layer <图签/标题栏图层> \
      --out households.json

  # 显式传参（优先于自适应，用于覆盖推定值或复现历史结果）
  python read_titleblock_households.py \
      --dxf 图纸.dxf --floor-layer <图签/标题栏图层> \
      --dx-tol <实测值> --dy-lo <实测值> --dy-hi <实测值> \
      --unit-dx <实测值> --unit-dy-lo <实测值> --unit-dy-hi <实测值> \
      --out households.json

  # 单独量测这 6 个值（输出建议值与实测证据）
  python probe_titleblock_tolerances.py --dxf 图纸.dxf --layer <图签层>

  # 一张 DXF 混排多个地块时，用 y 分段把楼名归段（顺序即图纸自上而下）
  python read_titleblock_households.py --dxf 图纸.dxf --floor-layer <图签层> \
      --band 地块A:<ymin>:<ymax> --band 地块B:<ymin>:<ymax> \
      --out households.json

  # 与《楼宇信息采集表》逐栋比对（可选）
  python read_titleblock_households.py --dxf 图纸.dxf --floor-layer <图签层> \
      --band ... --intake-xls 楼宇信息采集表.xls --intake-cols 5,6,7,8,9 \
      --out households.json

退出码：0 正常；1 参数/信号缺失；2 比对发现不一致（需人工裁定）；
        3 提取不完整——有楼名标注的楼一条层户/单元都没配上（2026-09-17，
        针对自适应容差失准时整地块静默消失的实测坑；--allow-partial 可放行）
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import os
import re
import sys

from ftth_common import (ToleranceEstimateError, assign_cells_to_buildings,
                         collect_multi_bldg_labels, collect_titleblock_unit_cells,
                         ensure_console_utf8,
                         estimate_titleblock_tolerances, filter_titleblock_units,
                         load_geom, UNIT_RE_SRC, write_json)

ensure_console_utf8()


def _load_dxf_texts(path, layer):
    """只读 TEXT/MTEXT 几何 → 走 ftth_common.load_geom 几何缓存（免全量解析）。

    与原生路径的等价性已实测：缓存内 MTEXT 为 plain_text（段落符保留为 \n），
    本函数把 \n 归一为空格，与原生 `replace('\\P', ' ')` 口径一致。
    """
    from ftth_common import load_geom
    g = load_geom(path)
    out = []
    for lay, x, y, s in (g.get("texts") or []):
        if lay != layer:
            continue
        out.append((float(x), float(y), str(s).replace("\n", " ").strip()))
    return out


def _layer_candidates_hint(dxf, bldg_re, lev_re):
    """报错辅助：列出「含楼名/层户标注的图层」候选（2026-09-16，12坑复核·坑3）。

    图签标注常在独立图签层（与 FTTH 强特征层不同），选错 --floor-layer 时此前
    只能靠试错。走 geom 缓存全量文字，成本低；候选仅作提示，需人工确认。
    """
    try:
        from ftth_common import load_geom
        _g = load_geom(dxf)
        _lay_cnt = {}
        for _lay, _x, _y, _s in (_g.get('texts') or []):
            _t = str(_s).replace('\n', ' ').strip()
            _hits = 0
            if re.fullmatch(lev_re, _t):
                _hits += 2
            if re.fullmatch(bldg_re, _t):
                _hits += 1
            if _hits:
                _lay_cnt[_lay] = _lay_cnt.get(_lay, 0) + _hits
        if _lay_cnt:
            _top = sorted(_lay_cnt.items(), key=lambda kv: -kv[1])[:5]
            return ('；含楼名/层户标注的图层候选：'
                    + '、'.join('%s(%d)' % (k, v) for k, v in _top))
    except Exception:
        pass
    return ''


def _cluster_bands(texts, specs):
    """按 y 分段归属；未给 band 时全部归到 '默认'。"""
    bands = []
    for sp in specs or []:
        name, lo, hi = sp.rsplit(':', 2)
        bands.append((name, float(lo), float(hi)))
    if not bands:
        return lambda y: '默认'

    def which(y):
        for name, lo, hi in bands:
            if lo <= y <= hi:
                return name
        return None
    return which


def apply_patch(data, evidence, patch):
    """应用人工裁定覆盖表。patch 结构：
        {"地块": {"3号楼": {"单元数":1,"层数":18,"每层户数":3}}}   # 补录/修正
        {"地块": {"5号楼": {"删除": true}}}                        # 剔除
    每条裁定都打印 [人工裁定]，保证可追溯；脚本绝不自动补数。
    """
    for bd, blds in patch.items():
        data.setdefault(bd, {})
        evidence.setdefault(bd, {})
        for bl, adj in blds.items():
            bn = int(re.search(r'(\d+)', bl).group(1))
            if adj.get('删除'):
                data[bd].pop(bn, None)
                print(f'  [人工裁定] {bd} {bl}：剔除')
                continue
            cur = data[bd].setdefault(bn, {})
            for k in ('单元数', '层数', '每层户数'):
                if k in adj and cur.get(k) != adj[k]:
                    print(f'  [人工裁定] {bd} {bl} {k}：{cur.get(k)} → {adj[k]}'
                          f'（来源：{adj.get("来源", "人工裁定")}）')
                    cur[k] = adj[k]
            cur.setdefault('裁定', []).append({k: v for k, v in adj.items()})
    return data, evidence


def rename_sites(data, evidence, spec):
    """按 "原分段=目标地块名" 归并地块；同目标名的分段合并为一（楼号不得冲突）。"""
    if not spec:
        return data, evidence, {}
    m = {}
    for item in spec.split(';'):
        if '=' in item:
            a, b = item.split('=', 1)
            m[a.strip()] = b.strip()
    nd, ne, sub = collections.defaultdict(dict), collections.defaultdict(dict), {}
    for bd, blds in data.items():
        tgt = m.get(bd, bd)
        for bn, v in blds.items():
            if bn in nd[tgt] and nd[tgt][bn] != v:
                sys.stderr.write(f'[错误] 归并 {bd}→{tgt} 时楼号 {bn} 冲突，需人工处理后再运行\n')
            raise SystemExit(2)  # C2 rc=2：归并冲突须人工（原字符串参数隐式rc=1）
            nd[tgt][bn] = v
            ne[tgt][bn] = evidence.get(bd, {}).get(bn, {})
            if tgt != bd:
                sub.setdefault(tgt, {}).setdefault(bn, bd)
    return dict(nd), dict(ne), sub


def read_titleblock(dxf, layer, bldg_re, lev_re, unit_re,
                    dx_tol, dy_lo, dy_hi, unit_dx, unit_dy_lo, unit_dy_hi, specs,
                    texts=None):
    # texts 允许由调用方预读：main 为了自适应量测已读过一次，避免同一张 DXF 读两遍。
    if texts is None:
        texts = _load_dxf_texts(dxf, layer)
    which = _cluster_bands(texts, specs)
    bl = [(x, y, s) for x, y, s in texts if re.fullmatch(bldg_re, s)]
    lvf = [(x, y, s) for x, y, s in texts if re.fullmatch(lev_re, s)]
    lvu = [(x, y, s) for x, y, s in texts if re.fullmatch(unit_re, s)]
    # 图签层里「一格里写了多栋」的楼名（`1#楼，2#楼` / `6#楼,7#楼,`）——`fullmatch` 一条都不认，
    #   若只静默跳过，症状会跑到下游很远的地方才显露（实测凤鸣朝阳：图签 12 个单元格零锚点，
    #   下游却报成「格组 11 条不落盘」，根因完全看不出来）。此处只登记、不解析。
    multi_bldg = collect_multi_bldg_labels(texts, bldg_re)
    if multi_bldg:
        print('[图签·多栋合并楼名] %d 条：%s'
              % (len(multi_bldg),
                 '、'.join('%s@[%.1f,%.1f]' % (s, x, y) for x, y, s in multi_bldg[:8])))
        print('    └ 这**不是**本脚本可解析的楼名（正则要求整条=单个楼名）——「格内单元 ↔ 各栋」'
              '的对应关系取决于格内单元画序，图上并未逐栋标注 ⇒ 交人工裁决；'
              '此类图的图签第二来源须说明「本次未参与/仅部分参与」'
              '（注：C10 逐栋比对**不受此影响**——C10 用的是图签逐栋读数 titleblock.json，'
              '非多栋合并行；若 C10 PASS 则图签交叉校验已通过，此提示仅说明多栋合并行未参与图签解析）')
    if not bl or not lvf:
        # 2026-09-15 效率优化：分离标注 variant fallback
        # 当主正则（如 (\d+)层/(\d+)户 合并写法）匹配不到时，尝试分离写法：
        # 楼层数标注「NF」（如 18F / 10F / 8F）+ 每层户数标注「M户/层」（如 2户/层 / 3户/层）
        # 两者在同一 y 坐标附近，按 y 邻近配对后合成 N层/M户 格式，后续逻辑无需改动。
        if bl:
            floor_re = re.compile(r'(\d+)F')
            hu_re = re.compile(r'(\d+)户/层')
            floor_texts = [(x, y, s) for x, y, s in texts if floor_re.fullmatch(s)]
            hu_texts = [(x, y, s) for x, y, s in texts if hu_re.fullmatch(s)]
            if floor_texts and hu_texts:
                # 以 M户/层 为锚，每个只配 x 最近 的 NF（系统图逐层 NF 离图签区
                # 几百单位远，自然被排除）。y 容差取 2.0 兜底。
                _y_tol = 2.0
                used_floors = set()
                synth_lvf = []
                for ht in hu_texts:
                    cands = [(ft, abs(ft[0] - ht[0]) + abs(ft[1] - ht[1]))
                             for ft in floor_texts if id(ft) not in used_floors
                             and abs(ft[1] - ht[1]) <= _y_tol]
                    if cands:
                        cands.sort(key=lambda c: c[1])
                        ft = cands[0][0]
                        used_floors.add(id(ft))
                        fm = floor_re.match(ft[2])
                        hm = hu_re.match(ht[2])
                        if fm and hm:
                            floors, perfl = int(fm.group(1)), int(hm.group(1))
                            synth = (ft[0], ft[1], '%d层/%d户' % (floors, perfl))
                            synth_lvf.append(synth)
                if synth_lvf:
                    lvf = synth_lvf
                    print('[variant] 图签为分离标注形式（NF + M户/层），已自动配对合成 %d 条层户标注' % len(lvf))
    # 2026-09-23（柳辛庄 band3 实测）：图签明细表的**绘制格**是「N单元」归属的客观边界。
    #   背景：本脚本原判据是「单元标注 → 最近层户」，靠容差窗 + 块方向自判消歧；但
    #   同栋「单元列」相对「层户列」的 x 偏置逐栋不同（实测 0.6k~101k），偏置一旦
    #   超过 --unit-dx（本图自适应量出 90571），真主被排除、隔壁楼入选或直接落空 ——
    #   实测 7# 的 `1单元` 判给 4#、8# 的 `1单元` 因 |dx|=102356 超窗而落空，
    #   7#/8# 单元数 2→1，C10 报成「图签与系统图矛盾」（人工按矛盾查图必然查不到）。
    #   而图上每个 `(楼栋, 单元)` 都画了一格，格内同时写着该单元的箱编号；格的位置
    #   就是归属。故新增「格组」判据（属**测量**：用图上已画的边界做包含/相邻判定），
    #   逐标注的最近层户判据整体保留为**回退**与**对照**（两者不一致时逐条留痕）。
    _cells_info = None
    _cell_groups = []
    _cell_protected = set()
    if lvu and dxf:
        try:
            from ftth_common import load_geom
            _geom = load_geom(dxf)
            _cell_groups, _cells_info = collect_titleblock_unit_cells(
                lvu, _geom.get('polylines') or [])
            # 落进「主尺寸格」的标注 = 图签数据本体，禁止被 filter 当系统图列头剔除
            for _g in _cell_groups:
                for _m in _g['members']:
                    _cell_protected.add(id(_m))
            print('[格组] %s' % ('启用：格尺寸 %s，格组 %d 个（落格 %d / 未落格 %d）'
                                 % (_cells_info['格尺寸'], len(_cell_groups),
                                    _cells_info['落格标注数'], _cells_info['未落格标注数'])
                                 if _cells_info['启用'] else
                                 '未启用（%s）—— 回落逐标注最近层户判据' % _cells_info['原因']))
            for _d in _cells_info['弃用组'][:8]:
                print('[格组·弃用] 格 x[%.1f,%.1f] y[%.1f,%.1f]：%s'
                      % (_d['格'][0], _d['格'][1], _d['格'][2], _d['格'][3], _d['原因']))
        except Exception as _e:      # 判据不可用不得中断主流程，但必须留痕
            print('[格组] 判据不可用（%r）—— 回落逐标注最近层户判据' % (_e,))
            _cell_groups, _cell_protected = [], set()

    # 2026-09-18（P0）：把「图签块内的单元标注」从全图同名标注里分出来。
    #   `N单元` 在**系统图里也出现**（每栋系统图楼层列顶部的单元列头），与图签同图层同写法。
    #   旧实现把两者一起配对 ⇒ 单元被配到错误楼栋：实测某图 7 栋里 5 栋单元数错、
    #   一栋收到 `1单元×6 / 2单元×5` 重复标签，而脚本只打 ⚠、退出码仍为 0。
    #   判据与容差量测共用同一处实现（ftth_common.filter_titleblock_units），两侧不得各写一份。
    if lvu:
        _lvu_all = len(lvu)
        lvu, _lvu_drop = filter_titleblock_units(lvu, bl, lvf,
                                                 protected=_cell_protected)
        if _lvu_drop:
            print('[图签块] 单元标注 %d 个 → 保留 %d 个、剔除 %d 个'
                  '（离任何楼名/层户都远 ⇒ 属系统图内的单元列头，非图签数据）：%s'
                  % (_lvu_all, len(lvu), len(_lvu_drop),
                     '、'.join('%s@[%.1f,%.1f]' % (d[2], d[0], d[1]) for d in _lvu_drop[:8])))
    if not bl or not lvf:
        # 2026-09-16（12坑复核·坑3）：报错时列出「含楼名/层户标注的图层」候选——
        #   图签标注常在独立图签层（与 FTTH 强特征层不同），此前只能靠试错找层。
        #   走 geom 缓存全量文字，成本低；候选仅作提示，需人工确认。
        _cand_hint = _layer_candidates_hint(dxf, bldg_re, lev_re)
        print(f'[参数/信号缺失] 图签层 {layer} 内未同时找到 楼名({len(bl)}) 与 层户标注({len(lvf)})，'
              f'请用 --bldg-re / --lev-re 校正正则' + _cand_hint, file=sys.stderr)
        return 2  # 2026-09-25（opencode 三审 SystemExit 家族清查）：参数可修类 rc=1 → rc=2

    def bldg_id(s):
        m = re.search(r'(\d+)', s)
        return int(m.group(1))

    # ---- 格组 → 归属（判据实现在 ftth_common.assign_cells_to_buildings，全技能唯一一份）----
    #   判据要点与两轮修正的实测依据见该函数 docstring：
    #     A 楼名主导认领（取「横向投影覆盖它的格组」中最近的一个 —— 楼名是行头，
    #       横向必落在本行 x 跨度内，实测四个地块真主 dx 恒为 0，且与图形朝向无关）
    #     + B 格组定锚（多栋争抢需优势明确，否则不判）+ 尺度闸（认领距离 ≤ 一个格高）。
    #   被删除的「同排共享」：band3 实测图签是**多列并排**版式（同一 y 带内并列 3 列，
    #   是**不同楼栋**的行），同排共享会把不同列误并 → 18 组里 14 组「多栋争抢」。
    #   而「一行多格」已由 collect_titleblock_unit_cells 的相邻并组解决，无需共享。
    #   为什么距离以「格组矩形」为基准而不是「标注点」：格组与楼名是**表格行关系**——
    #     楼名紧贴格组上沿（实测 8.6k~23.5k），而标注点自己可能离本栋楼名有 10 万
    #     （同栋单元列相对层户列的 x 偏置）。用标注点算距离＝把表格结构信息丢掉。
    _cell_owner = {}
    _cell_verd = []
    _cell_blocked = set()
    _cell_anchors_unclaimed = []
    _cell_offset_claims = []
    _cell_applicable = True
    _cell_inapplicable_why = ''
    if _cell_groups:
        try:
            _ch = float((_cells_info or {}).get('格尺寸', [None, None])[1])
        except (TypeError, ValueError, IndexError):
            _ch = None
        # 锚点只用**楼名**：楼名是图上唯一的楼栋自证文字；层户文字形如 `15层/2户`，
        #   取号会取到层数（15），**不得**拿它当楼号（本函数首版踩过）。
        _anchors = [(_a[0], _a[1], _a[2], (which(_a[1]), bldg_id(_a[2])))
                    for _a in bl if which(_a[1]) is not None]
        _cres = assign_cells_to_buildings(_cell_groups, _anchors, cell_h=_ch)
        _cell_verd = _cres['verdicts']
        _cell_owner = _cres['owner']
        _cell_blocked = _cres['blocked']
        _cell_anchors_unclaimed = _cres['unclaimed']
        # 采信但「楼名画在本行格组横向跨度之外」的认领 —— 与「未认领」分开呈现：
        #   前者已落盘、只是依据较弱；后者压根没落盘。混在一起会读成同一件事。
        _cell_offset_claims = _cres.get('offset_claims') or []
        # 判据**前提不成立**（认领率过低）⇒ 整体不适用：owner/blocked 置空，
        #   全部标注交回逐标注判据；调用方不得逐组打印「不采信/不落盘」（那是误判范围）。
        _cell_applicable = _cres.get('适用', True)
        _cell_inapplicable_why = _cres.get('不适用原因') or ''

    # 2026-09-15 修复（P0-12）：给了 --band 时，落带外的标注 which() 返回 None。
    #   旧逻辑不判 None 就把 None 当地块名写入 data，输出阶段 sorted(data.items())
    #   比较 str 与 NoneType 直接崩溃（TypeError: '<' not supported between
    #   instances of 'str' and 'NoneType'）。此处按「带外标注不属于任何指定地块」
    #   语义跳过，并逐类计数，绝不静默丢弃。
    #   未给 --band 时 which() 恒返回 '默认' -> 三条守卫均不生效，零回归。
    _out_of_band = {'楼名': 0, '层户': 0, '单元': 0}
    # 楼名 -> 层户：楼名正下方固定偏移、同 x
    lvl_owner = {}
    for v in lvf:
        bd = which(v[1])
        if bd is None:
            _out_of_band['层户'] += 1
            continue
        cand = [b for b in bl if which(b[1]) == bd and abs(b[0] - v[0]) <= dx_tol
                and dy_lo <= (b[1] - v[1]) <= dy_hi]
        if len(cand) != 1:
            continue
        lvl_owner[id(v)] = (bd, bldg_id(cand[0][2]))

    data = collections.defaultdict(lambda: collections.defaultdict(dict))
    evidence = collections.defaultdict(lambda: collections.defaultdict(dict))
    _cross_band_conflicts = []   # 12坑复核·坑4：疑似跨地块同名楼（冲突值来自不同y簇）
    for v in lvf:
        key = lvl_owner.get(id(v))
        if not key:
            continue
        bd, bn = key
        m = re.match(lev_re, v[2])
        floors, perfl = int(m.group(1)), int(m.group(2))
        d = data[bd][bn]
        if '层数' in d and (d['层数'], d['每层户数']) != (floors, perfl):
            _conf = {'坐标': [round(v[0], 1), round(v[1], 1)], '值': [floors, perfl]}
            # 2026-09-16（12坑复核·坑4）：同名楼出现多个不同层户值时，若冲突标注
            # 与既有证据的 y 差远超图签偏移尺度 → 大概率是不同地块的同名楼被
            # 并带提取。显式标记并提示分带（不自动分带——带边界需人工确认）。
            _ev_ys = [e[1] for e in evidence[bd][bn].get('层户', [])]
            if _ev_ys:
                _ev_ym = sorted(_ev_ys)[len(_ev_ys) // 2]
                _yscale = max(abs(dy_lo), abs(dy_hi), 1.0)
                if abs(v[1] - _ev_ym) > 2.0 * _yscale:
                    _conf['疑似跨地块同名楼'] = ('y差 %.0f 远超图签偏移尺度 %.0f'
                                             % (abs(v[1] - _ev_ym), _yscale))
                    _cross_band_conflicts.append('%s %d号楼' % (bd, bn))
            d.setdefault('冲突', []).append(_conf)
        d['层数'] = floors
        d['每层户数'] = perfl
        evidence[bd][bn].setdefault('层户', []).append([round(v[0], 1), round(v[1], 1), v[2]])

    # 单元标注 -> 楼：所属楼层户标注正下方固定偏移
    # 12坑复核·坑6：未匹配到层户的单元标注必须显式登记（旧版静默 continue，
    #   楼栋单元数因此被少算且不自我暴露）。**不改匹配算法**——不设硬性 x 容差
    #   会把别楼栋的层户标注配过来（违背不串楼原则）；漏读交人核对。
    _unmatched_units = []
    # 2026-09-17（R4 单元归属歧义显式化）：**不改「最近者胜」判据本身**，
    #   但当一个单元标注在容差内命中 ≥2 栋楼的层户时必须摆证据留痕——
    #   2026-09-16 柳辛庄实测：地块3『1单元』同时够到 4/7 号楼，被判给 4 号楼后
    #   7 号楼单元数 2→1、4 号楼拿两个『1单元』又被编号去重盖住，全程无异常提示。
    #   判据升级（排他约束/成对间距）需人工先裁定，脚本不自动择一。
    _unit_ambiguous = []
    _units_no_bldg = 0
    # 2026-09-21（块方向自判，柳辛庄 band2-5# 现场复核立项、用户已裁定实施）：
    #   背景：单元行相对所属楼块层户行可能偏上（块顶式）或偏下（块底式），
    #   同图内为常量但图图不同。容差窗上下都大（本图 ±90~108k）而楼块纵向
    #   间距仅 ~80k 时，行间标注恒命中上下两块；单点最近者胜按 |dy| 必偏向
    #   行下方的楼块 ⇒ 整列系统性下判一行（band2 实测：上行→4#/5#、中行→6#/7#，
    #   5# 收「1单元×4」、1#/2#/3# 零标签，C10 报假矛盾；用户肉眼＋箱位直读
    #   ＋系统图三方均为 2 单元）。
    #   判据：先用窗内仅一栋候选的**无歧义标注**自判本图方向（dy＝层户y－单元y；
    #   dy＞0 恒成立⇒块底式，dy＜0 恒成立⇒块顶式；需 ≥3 条且一致率 ≥0.8，
    #   否则不锁定）。锁定后歧义标注优先同向候选、同向内仍按 (|dy|,|dx|) 最近；
    #   无同向候选则回退旧规则并在歧义记录标「方向回退」。不锁定或单候选时
    #   行为与旧版逐位一致。第一遍只收集候选、不判决。
    def _dysgn(d):
        return 1 if d > 0 else (-1 if d < 0 else 0)

    _unit_cands = []   # [(u, cand)]
    _dir_votes = []    # 无歧义标注的 dy 符号（取同楼候选中 |dy| 最小者的符号）
    _cell_conflicts = []   # 2026-09-23：格组判据与逐标注判据不一致的留痕
    _cell_only = []        # 逐标注判据**够不到**（超容差窗 ⇒ 旧版直接落空）但格组判据能判的标注
    _cell_blocked_labels = []   # 所在绘制格**不采信** ⇒ 不落盘、不回落（交人）
    for u in lvu:
        bd = which(u[1])
        if bd is None:
            _out_of_band['单元'] += 1
            continue
        if id(u) in _cell_blocked:
            # 该标注所在的绘制格**判据不采信**（无楼名认领 / 多栋争抢且优势不足）：
            #   **不落盘、也不回落逐标注判据** —— 回落出来的值已被实测证伪
            #   （柳辛庄 band4：逐标注把 2#楼那一行判给了 3#楼，而格内箱编号自证属 2#楼）。
            #   取安全侧（少解，可见）而非回落（错解被当成已核，不可见），逐条交人。
            _cell_blocked_labels.append([round(u[0], 1), round(u[1], 1), u[2]])
            continue
        cand = [v for v in lvf if which(v[1]) == bd and abs(v[0] - u[0]) <= unit_dx
                and unit_dy_lo <= (v[1] - u[1]) <= unit_dy_hi]
        if not cand:
            # 超容差窗：旧版在此落空（登记后交人）。若该标注落在图签绘制格内、
            #   格组判据已给出归属，则它不是「漏读」而是「容差窗量偏了」——两者都登记。
            if id(u) in _cell_owner:
                _cell_only.append([round(u[0], 1), round(u[1], 1), u[2],
                                   '%s %d号楼' % _cell_owner[id(u)]])
            else:
                _unmatched_units.append([round(u[0], 1), round(u[1], 1), u[2]])
            continue
        _unit_cands.append((u, cand))
        _ow = {lvl_owner.get(id(t)) for t in cand} - {None}
        if len(_ow) == 1:
            _bv = min(cand, key=lambda t: abs(t[1] - u[1]))
            _s = _dysgn(_bv[1] - u[1])
            if _s:
                _dir_votes.append(_s)
    _n_v = len(_dir_votes)
    _n_pos = sum(1 for s in _dir_votes if s > 0)
    _lock_dir = None
    if _n_v >= 3 and _n_pos >= 0.8 * _n_v:
        _lock_dir = 1
    elif _n_v >= 3 and (_n_v - _n_pos) >= 0.8 * _n_v:
        _lock_dir = -1
    if _lock_dir is not None:
        print('[块方向自判] 无歧义标注 %d 条（dy>0 有 %d 条）→ 锁定%s式'
              '（单元行在层户行%s方），歧义标注优先同向候选、同向内仍按 (|dy|,|dx|)'
              % (_n_v, _n_pos if _lock_dir == 1 else _n_v - _n_pos,
                 '块底' if _lock_dir == 1 else '块顶',
                 '下' if _lock_dir == 1 else '上'))
    elif _dir_votes:
        print('[块方向自判] 无歧义标注 %d 条但方向不一致（dy>0 有 %d 条），'
              '证据不足不锁定，维持旧规则' % (_n_v, _n_pos))
    for u, cand in _unit_cands:
        # 2026-09-20 度量 (|dy|,|dx|) 保持（见上注释）；本轮只加同向优选。
        _pool = cand
        _dir_fb = False
        if _lock_dir is not None:
            _same = [t for t in cand
                     if (t[1] - u[1]) == 0 or _dysgn(t[1] - u[1]) == _lock_dir]
            if _same:
                _pool = _same
            else:
                # 无同向候选：回退旧规则（全池最近），歧义记录里标记。
                _dir_fb = True
        # 2026-09-20（柳辛庄 R1 实测 + 用户现场地面真值，升级 R4 预留判据）：
        #   仍是「最近者胜」，度量从 (|dx|,|dy|) 改为 (|dy|,|dx|) ——
        #   行身份由 y 决定：单元行与楼名行上下错层（本图单元行整体偏上/偏下
        #   20~50k），同行格子 Δy 仅 ~400（同刻度线）；而单元列相对层户列在 x
        #   上有系统性偏置（60~110k），x 最近 ≠ 同行。旧度量曾把 4#/5# 行的格子
        #   划给 100k 开外的 1#/2# 列（band2），把 3# 行同线 2单元判给 6#
        #   （band3，离 6# 另一格 108k）。只影响命中 ≥2 栋的歧义标注；
        #   判给结果照旧逐条记入「单元归属歧义标注」，以此 diff 复核。
        #   已验证：band3（3#=2/7#=2 系用户地面真值，4#保持1）＋ band2 下线
        #   （列模型一致＋双像对称）＋ band9-2-11#（[2]→[1,2] 对上系统侧）。
        #   已知转移：band3-6#（2→1）转成新 C10 待裁定——标签零和，无中生有不得。
        v = min(_pool, key=lambda t: (abs(t[1] - u[1]), abs(t[0] - u[0])))
        key = lvl_owner.get(id(v))
        if not key:
            _units_no_bldg += 1
            continue
        bd2, bn = key
        _ownermap = {}
        for _t in cand:
            _k = lvl_owner.get(id(_t))
            if _k:
                _ownermap.setdefault(_k, _t)
        if len(_ownermap) > 1:
            _rec = {
                '标注': [round(u[0], 1), round(u[1], 1), u[2]],
                '命中楼栋数': len(_ownermap),
                '候选': [{'地块': _k[0], '楼栋': '%d号楼' % _k[1],
                          '与标注偏移': [round(abs(_t[0] - u[0]), 1), round(abs(_t[1] - u[1]), 1)]}
                         for _k, _t in sorted(_ownermap.items(), key=lambda kv: kv[0][1])],
                '判给了': [bd2, bn]}
            if _dir_fb:
                # 2026-09-21：块方向锁定下无同向候选、已回退旧规则（全池最近）。
                _rec['方向回退'] = True
            _unit_ambiguous.append(_rec)
        # ---- 格组判据优先（2026-09-23）----
        #   为何优先：格是图上画出来的归属边界（属测量），而「最近层户」只是代理量，
        #   其容差窗无法表达「同栋单元列相对层户列的 x 偏置逐栋不同」。两者不一致时
        #   **必须逐条留痕**（不得静默覆盖旧判据的结论）。
        _co = _cell_owner.get(id(u))
        if _co and (_co[0], _co[1]) != (bd2, bn):
            _cell_conflicts.append({
                '标注': [round(u[0], 1), round(u[1], 1), u[2]],
                '逐标注判据': '%s %d号楼' % (bd2, bn),
                '格组判据': '%s %d号楼' % _co,
                '采信': '格组判据（图上绘制格边界）'})
            bd2, bn = _co
        elif _co:
            bd2, bn = _co
        evidence[bd2][bn].setdefault('单元', []).append([round(u[0], 1), round(u[1], 1), u[2]])

    # 逐标注判据**超容差窗落空**但格组判据能判的标注：按格组归属落盘（2026-09-23）
    for _co_x, _co_y, _co_s, _co_own in _cell_only:
        _k = _co_own.split(' ')
        evidence[_k[0]][int(_k[1].replace('号楼', ''))].setdefault(
            '单元', []).append([_co_x, _co_y, _co_s])

    for bd, blds in evidence.items():
        for bn, ev in blds.items():
            nums = sorted({int(re.search(r'(\d+)', e[2]).group(1)) for e in ev.get('单元', [])})
            data[bd][bn]['单元数'] = len(nums) if nums else None
            data[bd][bn]['单元编号'] = nums

    # 楼名证据
    for x, y, s in bl:
        bd = which(y)
        if bd is None:
            _out_of_band['楼名'] += 1
            continue
        evidence[bd][bldg_id(s)].setdefault('楼名', []).append([round(x, 1), round(y, 1), s])

    # 2026-09-17（R3 零数据楼检测）：有楼名证据而 data 里没有层数 = 该楼一条
    #   层户/单元都没配上。2026-09-16 22:19 实测：自适应容差失准时地块3/4 共
    #   12 栋楼全部静默消失（汇总里没有、rc=0、JSON 只有部分地块）。
    #   检测与容差来源无关——只要有楼名而零数据，就是提取不完整。
    #   注意位置：必须在楼名证据写入之后检测（否则永远检不出）。
    _nameless = []
    for bd, blds in evidence.items():
        for bn, ev in blds.items():
            if ev.get('楼名') and not (data.get(bd, {}).get(bn) or {}).get('层数'):
                _nameless.append({'地块': bd, '楼栋': '%d号楼' % bn,
                                  '楼名坐标': ev['楼名'][0][:2],
                                  '楼名文字': ev['楼名'][0][2]})

    # 质量报告
    rep = collections.Counter((which(y), bldg_id(s)) for x, y, s in bl if which(y) is not None)
    dist = collections.Counter(rep.values())
    base = max(dist, key=lambda k: dist[k]) if dist else 0
    dup = sorted([(k[0], k[1], v) for k, v in rep.items() if v != base],
                 key=lambda t: -t[2])
    # 2026-09-17（R4b）重复单元标签检测：同楼收到多余单元标注的典型成因是
    #   邻楼串标（柳辛庄实测：4 号楼收到 4 份『1单元』而基准是 2 份，被编号去重后
    #   单元数=1，毫无异常）。**按本图基准出现次数归一化**——大量图纸标注
    #   重复绘制 N 次（base 为众数），合法标签正好出现 base 次，只有
    #   count > base（多收了别人的标注）才报；count < base 的少收场景由
    #   未匹配统计与单元数缺项暴露，不在本条重复。
    _unit_dup_labels = []
    if base:
        for bd, blds in evidence.items():
            for bn, ev in blds.items():
                _cnt = collections.Counter(e[2] for e in ev.get('单元', []))
                for _lab, _c in _cnt.items():
                    if _c > base:
                        _unit_dup_labels.append({'地块': bd, '楼栋': '%d号楼' % bn,
                                                 '标签': _lab, '次数': _c, '基准': base})
    _band_given = bool(specs)
    if _band_given and any(_out_of_band.values()):
        print('[带外标注] 有标注落在所有 --band 范围之外，已跳过'
              f'（不属于任何指定地块）：楼名 {_out_of_band["楼名"]}、'
              f'层户 {_out_of_band["层户"]}、单元 {_out_of_band["单元"]} 条。'
              '若数量过大，请核对 --band 边界是否覆盖了全部目标地块。')
    # 格组判据留痕（2026-09-23）：采信了哪些格组、哪些不采信、与旧判据冲突了哪几条。
    #   不采信/冲突项**一律交人核对**，不自动择一。
    if _cell_verd and not _cell_applicable:
        # 前提不成立 ⇒ 判据整体不适用：**不逐组打印**（逐组打印会造出「11 条不落盘」这种
        #   离根因很远的告警，而标注其实全部交回逐标注判据、并未丢解）。
        print('[格组·不适用] %s' % _cell_inapplicable_why)
        print('    └ 处置：本图的「N单元」**全部**走逐标注判据（与启用格组判据前的行为一致）；'
              '格组逐组裁决仅作留痕，不参与落盘。根因通常是图签楼名写法不被 bldg-re 接受'
              '（看上一段 [图签·多栋合并楼名]）或图签层混入了系统图的格。')
    elif _cell_verd:
        print('[格组·归属] 共 %d 组：采信 %d、不采信 %d'
              % (len(_cell_verd), sum(1 for _r in _cell_verd if _r['采信']),
                 sum(1 for _r in _cell_verd if not _r['采信'])))
        for _r in _cell_verd:
            _an = _r.get('最近锚点')
            if _an:
                print('    %s 单元 %s → %s（最近 %s「%s」距离 %.1f；次近不同栋 %s）'
                      % ('✓' if _r['采信'] else '✗', _r['单元号'],
                         _an['归属'], _an['类型'], _an['文字'], _an['距离'],
                         (_r['次近不同栋'] or {}).get('归属') or '(无)'))
            else:
                print('    %s 单元 %s → (无楼名认领本行)' % ('✓' if _r['采信'] else '✗',
                                                          _r['单元号']))
            if not _r['采信']:
                print('       └ %s' % _r.get('不采信原因', ''))
    if _cell_anchors_unclaimed:
        print('[格组·锚点] %d 个楼名未对任何行做认领（逐条原因见下；不猜，交人核对）：'
              % len(_cell_anchors_unclaimed))
        for _s in _cell_anchors_unclaimed[:8]:
            print('    · %s' % _s)
    if _cell_offset_claims:
        print('[格组·偏置认领] %d 个楼名的 x 落在本行格组横向跨度之外，已按'
              '「最近格 + 优势闸」认领（**已采信并落盘**，与上一项「未认领」不同；'
              '逐条登记供复核）：' % len(_cell_offset_claims))
        for _s in _cell_offset_claims[:8]:
            print('    · %s' % _s)
    if _cell_conflicts:
        print('[格组·改判] %d 条标注的归属被格组判据改写（逐条对照如下，供复核）：'
              % len(_cell_conflicts))
        for _r in _cell_conflicts[:12]:
            print('    %s：逐标注判据→%s｜格组判据→%s'
                  % (_r['标注'][2], _r['逐标注判据'], _r['格组判据']))
    if _cell_only:
        print('[格组·补判] %d 条标注超出 --unit-dx/--unit-dy 容差窗（旧版直接落空），'
              '已按格组归属：%s' % (len(_cell_only),
                              '、'.join('%s→%s' % (r[2], r[3]) for r in _cell_only[:8])))
    if _cell_blocked_labels:
        print('[格组·不采信] %d 条单元标注因所在绘制格判据不采信而**未落盘**'
              '（不回落逐标注判据 —— 回落值已被实测证伪），逐条交人核对：%s'
              % (len(_cell_blocked_labels),
                 '、'.join('%s@[%.1f,%.1f]' % (r[2], r[0], r[1])
                          for r in _cell_blocked_labels[:8])))
    return data, evidence, {'楼名标注总数': len(bl), '层户标注总数': len(lvf),
                            '单元标注总数': len(lvu),
                            '出现次数分布': {str(k): v for k, v in sorted(dist.items())},
                            '基准出现次数': base,
                            '偏离基准的楼(疑似重复绘制或楼名笔误)': dup,
                            '未唯一匹配到楼名的层户标注数': len(lvf) - len(lvl_owner),
                            '未匹配到层户的单元标注数': len(_unmatched_units),
                            '未匹配到层户的单元标注': _unmatched_units[:20],
                            '格组判据': _cells_info,
                            '格组判据适用': _cell_applicable,
                            '格组判据不适用原因': _cell_inapplicable_why,
                            '图签多栋合并楼名(待人工裁决)': multi_bldg[:20],
                            '格组归属': _cell_verd,
                            '格组未做认领的楼名': _cell_anchors_unclaimed,
                            '格组偏置认领(已采信)': _cell_offset_claims,
                            '格组不采信而未落盘的单元标注': _cell_blocked_labels,
                            '格组补判(超容差窗)': _cell_only,
                            '格组改写旧判据的标注': _cell_conflicts,
                            '单元归属歧义标注数': len(_unit_ambiguous),
                            '单元归属歧义标注': _unit_ambiguous[:20],
                            '重复单元标签的楼': _unit_dup_labels,
                            '单元标注落到无主层户上的数': _units_no_bldg,
                            '零数据楼(有楼名无任何层户数据)': _nameless,
                            '疑似跨地块同名楼': sorted(set(_cross_band_conflicts)),
                            '落带外被跳过的标注数': dict(_out_of_band) if _band_given else None}


def load_intake_xls(path, sheet, cols):
    """读《楼宇信息采集表》：cols = 小区名称,楼宇名称,单元数,层数,每层住户数 的列号（0 基）"""
    import xlrd
    bk = xlrd.open_workbook(path)
    sh = bk.sheet_by_name(sheet) if sheet else bk.sheet_by_index(0)
    c_area, c_b, c_u, c_f, c_p = cols
    out = collections.defaultdict(lambda: collections.defaultdict(dict))
    for r in range(1, sh.nrows):
        vals = [sh.cell_value(r, c) for c in (c_area, c_b, c_u, c_f, c_p)]
        if not str(vals[0]).strip():
            continue
        try:
            b, u, f, p = (int(float(v)) for v in vals[1:])
        except (TypeError, ValueError):
            continue
        out[str(vals[0]).strip()][b][u] = {'层数': f, '每层户数': p}
    return out


def parse_area_map(spec, bands):
    """--intake-area-map "地块=采集表小区名[:楼号区间];..." -> {地块: (小区名, lo, hi)}

    楼号区间用于「一个采集表小区被图纸拆成多个地块分段」的情形（如 9区 拆为 A段/B段）。
    区间写法 a-b / a- / -b；缺省为不限。
    """
    if not spec:
        return {b: (b, None, None) for b in bands}
    m = {}
    for item in spec.split(';'):
        item = item.strip()
        if not item:
            continue
        band, rest = item.split('=', 1)
        rng = None
        if ':' in rest:
            rest, rng = rest.rsplit(':', 1)
        lo = hi = None
        if rng:
            if '-' in rng:
                a, b = rng.split('-', 1)
                lo = int(a) if a.strip() else None
                hi = int(b) if b.strip() else None
            else:
                lo = hi = int(rng)
        m[band.strip()] = (rest.strip(), lo, hi)
    return m


def intake_lookup(intake, area_map, bd, bn):
    """按 地块->小区 映射 + 楼号区间，取该栋的 (单元数, 层/户配置集合)"""
    area, lo, hi = area_map.get(bd, (bd, None, None))
    if area not in intake:
        return None, ()
    if lo is not None and bn < lo:
        return None, ()
    if hi is not None and bn > hi:
        return None, ()
    units = intake[area].get(bn)
    if not units:
        return None, ()
    cfg = tuple(sorted({(v['层数'], v['每层户数']) for v in units.values()}))
    return len(units), cfg


def main(argv=None):
    ap = argparse.ArgumentParser(description='读取标注（图签形态）：读出楼栋级 单元数/层数/每层户数')
    ap.add_argument('--dxf', required=True)
    ap.add_argument('--floor-layer', required=True,
                    help='图签/标题栏所在图层名（必需，禁止默认值）')
    ap.add_argument('--bldg-re', default=r'\d+\s*[#＃号]?\s*楼',
                    help=r'楼名正则，默认匹配 1#楼 / 1号楼 / 1楼')
    ap.add_argument('--lev-re', default=r'(\d+)层/(\d+)户')
    ap.add_argument('--unit-re', default=UNIT_RE_SRC)
    # 以下 6 个几何容差**与图纸坐标尺度绑定**（不同图纸可差几个数量级），故一律不设
    # 固定默认值；缺省时由 estimate_titleblock_tolerances 按本图量出，显式传入优先。
    _TOL_H = '（缺省时按图自适应；随图纸坐标尺度变化）'
    ap.add_argument('--dx-tol', type=float, default=None,
                    help='楼名与层户标注的 x 容差' + _TOL_H)
    ap.add_argument('--dy-lo', type=float, default=None,
                    help='楼名相对层户标注的 y 偏移下限' + _TOL_H)
    ap.add_argument('--dy-hi', type=float, default=None,
                    help='y 偏移上限' + _TOL_H)
    ap.add_argument('--unit-dx', type=float, default=None,
                    help='单元标注与层户标注的 x 容差' + _TOL_H)
    ap.add_argument('--unit-dy-lo', type=float, default=None,
                    help='单元标注相对层户标注的 y 偏移下限' + _TOL_H)
    ap.add_argument('--unit-dy-hi', type=float, default=None,
                    help='单元标注的 y 偏移上限' + _TOL_H)
    ap.add_argument('--band', action='append', default=[],
                    help='地块分段 name:ymin:ymax，可重复；缺省则不分段')
    ap.add_argument('--intake-xls', help='可选：《楼宇信息采集表》xls，用于逐栋比对')
    ap.add_argument('--intake-sheet')
    ap.add_argument('--intake-cols', default='5,6,7,8,9',
                    help='采集表列号(0基)：小区名称,楼宇名称,单元数,层数,每层住户数')
    ap.add_argument('--intake-area-map', default=None,
                    help='地块->采集表小区名 映射 "地块=小区名[:楼号下限-上限];..."，'
                         '用于一个采集表小区被图纸拆成多个地块分段的情形；缺省按同名匹配')
    ap.add_argument('--patch', help='人工裁定覆盖表 JSON（补录/修正/剔除），每条裁定都会打印留痕')
    ap.add_argument('--allow-partial', action='store_true',
                    help='放行「有楼名但零层户数据」的楼栋（缺省 rc=3 硬失败——'
                         '2026-09-16 实测自适应容差失准时 12 栋楼静默消失）。'
                         '仅限人工确认图上确无层户标注的楼后使用')
    ap.add_argument('--site-name', default=None,
                    help='地块改名/归并 "原分段=目标地块名;..."，同目标名自动合并（楼号不得冲突）')
    ap.add_argument('--sys-title-layer', default=None,
                    help='可选：系统图标题所在图层。提供后做「系统图标题楼号集合 vs 图签楼号集合」'
                         '交叉校验（2026-09-16，12坑复核·坑12）——图签漏读/笔误'
                         '（系统图有某楼号而图签完全缺失）自动显形；仅报告，不影响退出码')
    ap.add_argument('--sys-title-pattern', default=None,
                    help='系统图标题正则（组1=楼号），缺省内置 `(\\d+)(?:#|号楼)`（search 语义）')
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)

    # ---------- 几何容差：显式传入优先 -> 缺省则按图自适应 -> 推定值打进结果 ----------
    # 为什么不设固定默认值：这 6 个值与图纸坐标尺度绑定（不同图纸可差几个数量级），
    #   套用任一项目的实测值，换图后必然出错（太宽串楼、太窄丢楼）。
    # 为什么不再「一律必填」：真正的判据是「是否随图纸坐标尺度变化」，而不是
    #   「名字里带不带容差」——随尺度变化的参数应当**从本图量**，而不是逼人先手工量一遍。
    # 机制与 analyze_coverage.py 的层高自适应同源：显式值优先，缺省时按图量，量到什么写进结果。
    _tol_args = ('dx_tol', 'dy_lo', 'dy_hi', 'unit_dx', 'unit_dy_lo', 'unit_dy_hi')
    _tol_missing = [n for n in _tol_args if getattr(a, n) is None]
    _tol_est = None
    _tol_src = '显式传入'
    try:
        _texts = _load_dxf_texts(a.dxf, a.floor_layer)
    except Exception as ex:                                        # noqa: BLE001
        sys.stderr.write('[ERROR] 读取 DXF 失败: %s\n' % ex)
        return 1
    # 2026-09-15 效率优化：分离标注 variant 预处理
    # 当主正则 lev_re（如 (\d+)层/(\d+)户）匹配不到任何文字时，检测分离写法
    # （NF + M户/层），配对后合成 N层/M户 格式注入 _texts，使下游容差估计与
    # read_titleblock 的主逻辑无需改动即可正常工作。
    _lev_re_compiled = re.compile(a.lev_re)
    _has_lev = any(_lev_re_compiled.fullmatch(s) for _, _, s in _texts)
    if not _has_lev:
        _floor_re = re.compile(r'(\d+)F')
        _hu_re = re.compile(r'(\d+)户/层')
        _floor_texts = [(x, y, s) for x, y, s in _texts if _floor_re.fullmatch(s)]
        _hu_texts = [(x, y, s) for x, y, s in _texts if _hu_re.fullmatch(s)]
        if _floor_texts and _hu_texts:
            _y_tol = 2.0
            _used = set()
            _synth = []
            for ht in _hu_texts:
                _cands = [(ft, abs(ft[0] - ht[0]) + abs(ft[1] - ht[1]))
                          for ft in _floor_texts if id(ft) not in _used
                          and abs(ft[1] - ht[1]) <= _y_tol]
                if _cands:
                    _cands.sort(key=lambda c: c[1])
                    ft = _cands[0][0]
                    _used.add(id(ft))
                    fm = _floor_re.match(ft[2])
                    hm = _hu_re.match(ht[2])
                    if fm and hm:
                        _synth.append((ft[0], ft[1], '%d层/%d户' % (int(fm.group(1)), int(hm.group(1)))))
            if _synth:
                _texts = list(_texts) + _synth
                print('[variant] 图签为分离标注形式（NF + M户/层），已自动配对合成 %d 条层户标注' % len(_synth))
    if _tol_missing:
        try:
            _tol_est = estimate_titleblock_tolerances(_texts, a.bldg_re, a.lev_re, a.unit_re)
        except ToleranceEstimateError as ex:
            # 量测失败（排版方向异常 / 窗口自相矛盾）必须**失败退出**，不得退回某个猜测值：
            # 猜出来的窗口要么全空（静默丢楼）要么过宽（静默串楼），两者都不自我暴露。
            sys.stderr.write(
                '[ERROR] read_titleblock_households: 有 %d 项几何容差未显式传入，'
                '而按图自适应量测失败——\n  %s\n'
                '  请显式传入 6 个容差（可先用 probe_titleblock_tolerances.py 量测并核对）。\n'
                % (len(_tol_missing), ex))
            return 1
        if _tol_est is None:
            # rc 语义修复（2026-09-18 实跑）：本条**不是「命令自身失败」**，而是
            #   **本图未提供图签形态的成对标注**（图层内「楼名」与「层户」标注不同时
            #   出现足够的量），属申报制下的 rc=3 早失败：跳过 + 走降级路径，
            #   不是错误、不需重试、不必去调参。
            #   此前 return 1 会让调用方把「图上没有」呈现成「脚本坏了」
            #   （实测 pipeline 打出 `! titleblock 阶段 rc=1 —— 第二来源本次未取得` 的
            #   告警形态），把排错方向误导到「校正正则 / 补传容差」。
            #   注意上一分支（ToleranceEstimateError，量测到但排版自相矛盾）仍保持
            #   rc=1：那是"确实有问题"，与"本图没有"是两回事。
            sys.stderr.write(
                '[SKIP] read_titleblock_households: 本图未提供图签形态的成对标注'
                '（图层 %s 内没有同时出现足够的「楼名」与「层户」标注），'
                '有 %d 项几何容差按图无从量测。\n'
                '  处置：rc=3（本图不适用，非错误）——第二来源本次不参与，'
                '调用方应跳过本环节并注明「本次未做」。\n'
                '  若确认本图另有可读的层户标注，请用 --bldg-re / --lev-re 校正正则，'
                '或显式传入 6 个容差（可先用 probe_titleblock_tolerances.py 量测）。%s\n'
                % (a.floor_layer, len(_tol_missing),
                   _layer_candidates_hint(a.dxf, a.bldg_re, a.lev_re)))
            return 3
        for n in _tol_missing:
            setattr(a, n, _tol_est[n])
        _still = [n for n in _tol_missing if getattr(a, n) is None]
        if _still:
            sys.stderr.write(
                '[ERROR] 以下参数既未显式传入，按图也量不出来：'
                + '、'.join('--' + n.replace('_', '-') for n in _still) + '\n'
                '  多为该图缺少对应标注所致；请先用 probe_titleblock_tolerances.py 量测后传入。\n')
            return 2  # 2026-09-25（opencode 审核）：量不出来=输入不足，按 L1-C2 应为 rc=2。
                      # 上一分支（ToleranceEstimateError）保持 rc=1 不动——排版自相矛盾
                      # 是图面数据质量问题（2026-09-18 已裁定），与输入不足是两回事。
        _tol_src = '按图自适应（%d 项由图纸量出）' % len(_tol_missing)
        print('[几何容差] 未显式传入的项已按图自适应推定：')
        for n in _tol_missing:
            print('    --%-14s %.1f' % (n.replace('_', '-'), getattr(a, n)))
        print('  提示：如与图纸实测不符，请显式传参覆盖；'
              'probe_titleblock_tolerances.py 可单独量测并给出证据。')

    data, evidence, report = read_titleblock(
        a.dxf, a.floor_layer, a.bldg_re, a.lev_re, a.unit_re,
        a.dx_tol, a.dy_lo, a.dy_hi, a.unit_dx, a.unit_dy_lo, a.unit_dy_hi, a.band,
        texts=_texts)

    if a.patch:
        with io.open(a.patch, encoding='utf-8') as f:
            data, evidence = apply_patch(data, evidence, json.load(f))
    data, evidence, sub = rename_sites(data, evidence, a.site_name)
    if sub:
        for tgt, mp in sub.items():
            print(f'[地块归并] {tgt} ← ' + '、'.join(f'{v}的{b}号楼' for b, v in sorted(mp.items())))

    # 归一化：band 名 -> 采集表小区名的匹配靠"地块数字"模糊对应，交由调用方核对
    result = {
        '来源': '读取标注(图签形态)',
        '图层': a.floor_layer,
        '几何容差': {'来源': _tol_src,
                  'dx_tol': a.dx_tol, 'dy_lo': a.dy_lo, 'dy_hi': a.dy_hi,
                  'unit_dx': a.unit_dx, 'unit_dy_lo': a.unit_dy_lo, 'unit_dy_hi': a.unit_dy_hi,
                  '推定依据': _tol_est['证据'] if _tol_est else None},
        # 双保险（P0-12）：即便归属阶段已跳过带外标注，输出阶段仍显式剔除 None 键，
        # 保证 sorted() 永不遇到 str 与 NoneType 混排而崩溃。
        '地块': {bd: {f'{bn}号楼': dict(v) for bn, v in sorted(blds.items())}
                 for bd, blds in sorted(data.items(), key=lambda kv: str(kv[0]))
                 if bd is not None},
        '证据坐标': {bd: {f'{bn}号楼': v for bn, v in sorted(b.items())}
                     for bd, b in sorted(evidence.items(), key=lambda kv: str(kv[0]))
                     if bd is not None},
        '质量报告': report,
        '细分地块': sub,
        '逐栋比对': None,
    }

    rc = 0
    orig_band = {(tgt, bn): sub.get(tgt, {}).get(bn, tgt)
                 for tgt, blds in data.items() for bn in blds}
    if a.intake_xls:
        cols = tuple(int(x) for x in a.intake_cols.split(','))
        intake = load_intake_xls(a.intake_xls, a.intake_sheet, cols)
        bands = sorted({v for v in orig_band.values()})
        area_map = parse_area_map(a.intake_area_map, bands)
        rows = []
        no_match = []
        for bd, blds in sorted(data.items()):
            for bn, v in sorted(blds.items()):
                bd_orig = orig_band.get((bd, bn), bd)
                d_units = v.get('单元数')
                d_cfg = (v.get('层数'), v.get('每层户数'))
                x_units, x_cfg = intake_lookup(intake, area_map, bd_orig, bn)
                label = f'{bd}/{bn}号楼' if bd_orig == bd else f'{bd}(原{bd_orig})/{bn}号楼'
                if x_units is None:
                    no_match.append({'地块': bd, '楼栋': f'{bn}号楼', '原始分段': bd_orig})
                    rows.append({'地块': bd, '楼栋': f'{bn}号楼', '原始分段': bd_orig,
                                 '图签(单元数,层,户)': [d_units, d_cfg[0], d_cfg[1]],
                                 '采集表(单元数,(层,户))': None,
                                 '判定': '采集表无此栋-需人工裁定'})
                    rc = 2
                    continue
                same = (d_units == x_units) and (d_cfg in x_cfg)
                if not same:
                    rc = 2
                rows.append({'地块': bd, '楼栋': f'{bn}号楼', '原始分段': bd_orig,
                             '图签(单元数,层,户)': [d_units, d_cfg[0], d_cfg[1]],
                             '采集表(单元数,(层,户))': [x_units, list(x_cfg)],
                             '判定': '一致' if same else '不一致-需人工裁定'})
        result['逐栋比对'] = rows
        # 采集表有、图签无的楼栋（配合"出现次数偏离基准"可定位楼名笔误）
        have = {(orig_band.get((r['地块'], int(re.search(r"(\d+)", r['楼栋']).group(1))),
                              r['地块']), r['楼栋']) for r in rows}
        only_intake = []
        for bd_orig in bands:
            area, lo, hi = area_map.get(bd_orig, (bd_orig, None, None))
            for bn in intake.get(area, {}):
                if (lo is not None and bn < lo) or (hi is not None and bn > hi):
                    continue
                if (bd_orig, f'{bn}号楼') not in have:
                    only_intake.append({'原始分段': bd_orig, '楼栋': f'{bn}号楼'})
        result['采集表有而图签无'] = only_intake
        n_ok = sum(1 for r in rows if r['判定'] == '一致')
        print(f'[逐栋比对] {len(rows)} 栋：一致 {n_ok}，需人工裁定 {len(rows) - n_ok}')
        for r in rows:
            if r['判定'] != '一致':
                print(f"  ★ {r['地块']} {r['楼栋']}：图签={r['图签(单元数,层,户)']} "
                      f"采集表={r['采集表(单元数,(层,户))']}")
        if only_intake:
            print(f'  ⚠ 采集表有、图签无的楼栋: {[x["原始分段"] + " " + x["楼栋"] for x in only_intake]}')
            print('     → 与「出现次数偏离基准的楼」成对出现时，即定位为图签楼名笔误')
        if rc == 2:
            print('  ⚠ 不一致项必须列双来源证据交人裁定，脚本不自动择一')
    elif a.intake_area_map:
        print('[提示] 指定了 --intake-area-map 但未给 --intake-xls，映射未使用', file=sys.stderr)

    # ---------- 系统图标题交叉校验（2026-09-16，12坑复核·坑12）----------
    # 图签笔误/漏读的典型形态：系统图标题含某楼号，图签层完全读不到它，
    # 同时另一楼号出现次数异常高（笔误把楼号写错）。两个集合一比对即显形。
    if a.sys_title_layer:
        _st_re = re.compile(a.sys_title_pattern) if a.sys_title_pattern             else re.compile(r'(\d+)(?:#|号楼)')
        try:
            from ftth_common import load_geom
            _g = load_geom(a.dxf)
            _st_nums = set()
            for _lay, _x, _y, _s in (_g.get('texts') or []):
                if _lay != a.sys_title_layer:
                    continue
                _m = _st_re.search(str(_s).replace('\n', ' ').strip())
                if _m:
                    _st_nums.add(int(_m.group(1)))
            _tb_nums = {bn for blds in data.values() for bn in blds}
            _miss_in_tb = sorted(_st_nums - _tb_nums)
            _extra_in_tb = sorted(_tb_nums - _st_nums)
            result['系统图标题交叉校验'] = {
                '系统图标题楼号': sorted(_st_nums), '图签楼号': sorted(_tb_nums),
                '系统图有而图签无(疑似漏读/笔误)': _miss_in_tb,
                '图签有而系统图无': _extra_in_tb,
            }
            print('[交叉校验] 系统图标题楼号 %d 个 vs 图签楼号 %d 个'
                  % (len(_st_nums), len(_tb_nums)))
            if _miss_in_tb:
                print('  ⚠ 系统图有而图签无: %s → 疑似图签漏读/笔误；'
                      '与「出现次数偏离基准的楼」成对出现即可定位' % _miss_in_tb)
            if _extra_in_tb:
                print('  ⚠ 图签有而系统图无: %s → 请核对（可能为配套楼/其他图纸楼栋）'
                      % _extra_in_tb)
        except Exception as _ex:                                        # noqa: BLE001
            print('[交叉校验] 读取系统图标题图层失败（跳过校验）: %s' % _ex,
                  file=sys.stderr)

    write_json(a.out, result)
    print(f'[写出] {a.out}')
    print(f"[质量报告] 楼名{report['楼名标注总数']} 层户{report['层户标注总数']} "
          f"单元{report['单元标注总数']} 出现次数分布{report['出现次数分布']}")
    if report['偏离基准的楼(疑似重复绘制或楼名笔误)']:
        print(f"[⚠] 偏离基准的楼: {report['偏离基准的楼(疑似重复绘制或楼名笔误)']}")
    if report['未唯一匹配到楼名的层户标注数']:
        print(f"[⚠] {report['未唯一匹配到楼名的层户标注数']} 条层户标注未匹配到楼名 → 校正 --dx-tol/--dy-lo/--dy-hi")
    if report.get('未匹配到层户的单元标注数'):
        print(f"[⚠] {report['未匹配到层户的单元标注数']} 条单元标注未匹配到层户标注 → "
              "核对 --unit-dx/--unit-dy-lo/--unit-dy-hi（逐条坐标见 JSON 质量报告）")
    if report.get('疑似跨地块同名楼'):
        print(f"[⚠] 疑似跨地块同名楼（冲突值来自不同 y 簇）: {report['疑似跨地块同名楼']} → "
              "建议按地块分带（--band）分别提取")
    if report.get('单元归属歧义标注数'):
        print(f"[⚠] {report['单元归属歧义标注数']} 条单元标注在容差内命中多栋楼"
              "（已按「最近者胜」判，但串楼风险高，逐条核对归属）：")
        for _x in report['单元归属歧义标注']:
            print(f"    {_x['标注'][2]} @{_x['标注'][:2]} → 候选 "
                  + "；".join(f"{c['地块']} {c['楼栋']} 偏移{c['与标注偏移']}" for c in _x['候选'])
                  + f" ⇒ 判给了 {_x['判给了'][0]} {_x['判给了'][1]}号楼")
    if report.get('重复单元标签的楼'):
        print(f"[⚠] 以下楼收到重复单元标签（典型成因：邻楼串标后被编号去重盖住）："
              + "；".join(f"{x['地块']} {x['楼栋']} {x['标签']}×{x['次数']}"
                          for x in report['重复单元标签的楼']))
    if report.get('零数据楼(有楼名无任何层户数据)'):
        _nl = report['零数据楼(有楼名无任何层户数据)']
        print(f"[ERROR] 提取不完整：{len(_nl)} 栋有楼名标注，但一条层户/单元都没配上"
              "（它们不会出现在下方汇总里）→ 几何容差失准或 --floor-layer 选错，"
              "禁止当作完整结果使用：")
        for _x in _nl:
            print(f"    {_x['地块']} {_x['楼栋']}  「{_x['楼名文字']}」@{_x['楼名坐标']}")
        if a.allow_partial:
            print("  [--allow-partial] 已放行（rc 不变），但上述楼栋数据仍缺失，结果为部分结果。")
        else:
            print("  处置：用 probe_titleblock_tolerances.py 量测后显式传 6 个容差重跑；"
                  "人工确认图上确无层户标注的楼，可加 --allow-partial 放行（rc=0）。")
            rc = 3
    print('[汇总]')
    for bd, blds in result['地块'].items():
        for bn, v in blds.items():
            print(f'  {bd:<10}{bn:<10} 单元数={v.get("单元数")} 层数={v.get("层数")} '
                  f'每层户数={v.get("每层户数")}'
                  + (f'  ⚠冲突{v["冲突"]}' if v.get('冲突') else ''))
    return rc


if __name__ == '__main__':
    sys.exit(main())
