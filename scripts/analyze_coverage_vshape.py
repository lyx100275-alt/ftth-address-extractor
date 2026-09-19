#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""皮线 V 形覆盖判定（V型计算）

用途
----
当「竖线法」（analyze_coverage.py）不可用时——例如连线画在与建筑线
混层的图层上、或没有独立的电信连线图层——改用**皮线米数标注的 V 形规律**
判定每个分纤箱的安装楼层与覆盖楼层。

原理（见 references/coverage_rules.md「V型计算」）
-------------------------------------------------------
系统图上每个单元有一列皮线米数标注（形如 `20m*2`），其 y 与楼层列对齐。
皮线自该单元的分纤箱出发，离箱越远米数越大：

       18F  36m                     ← V 一端（覆盖上边界）
       16F  28m
       14F  20m   ← V 底（米数最小）= 分纤箱安装楼层
       12F  28m
       10F  36m                     ← V 另一端（覆盖下边界）

· V 形**局部极小**（谷底）⇒ 该分纤箱的安装楼层
· 一个米数列含 N 个谷底 ⇒ 该单元有 N 个分纤箱，每个覆盖一段
· 双箱单元的覆盖分界：取相邻两个谷底之间的中位行（对称 V 下等价于两曲线交点）

与竖线法的分工
----------------------
· 竖线法：读线段几何（竖干断口），需要干净的连线图层
· V 形法：只读**文字标注**，完全不依赖线段图层 —— 因此对「连线混层」的图纸仍可用

米数标注格式兼容（2026-09-13，P0-2）
----------------------------------
不同图纸的米数写法**字段序不同**，本脚本不假定顺序：
    `20m*2`        米数在前，根数在后
    `2Px2芯x36m`   根数在前，米数在后，带单位后缀（真实案例：358 条全部此写法）
    `2芯x36m`
判定顺序：① 命名组 `(?P<meters>…)` / `(?P<count>…)` →
② `--cable-meters-group` / `--cable-count-group` 显式指定 →
③ 自动：捕获片段带 `m`/`米` 后缀者为米数；否则取数值大者为米数。
任一楼栋窗口内匹配到米数标注但**一条都解析不出**时，脚本以退出码 2 终止并打印样本，
绝不静默跳过、也不抛 IndexError。

自检
----
· V 底对应楼层线 y  vs  箱号文字 y（两独立来源，偏差应恒定）
· V 形单调性（谷底两侧应单调递增，否则告警）

用法
----
  python analyze_coverage_vshape.py <dxf> <out.json>
      --text-layer <探查图层>
      --title-pattern "<探查标题正则>"
      --fx-pattern "<探查编号正则>"
      --cable-pattern "<探查米数正则>"

本脚本不设任何项目默认值：图层名 / 标题写法 / 编号格式 / 米数格式每张图都不同，
必须由 Step 1a 探查结果提供；缺失时直接报错退出（不静默套用别的图纸的值）。

可经统一入口调用：`ftth.py coverage-vshape --dxf <dxf> --config <probe.json> --out <out.json>`
"""
import argparse
import json
import os
import re
import sys

import ftth_common
from ftth_common import (
    clean_text, collect_texts, cluster_chain_mean, cluster_values_by_gap,
    ensure_console_utf8, floor_num, floor_step_from_texts, first_group,
    judge_pending_scope, load_dxf, median_text_height, parse_bldg_nums,
    parse_bldg_nums_ex, parse_floor_label, pending_items_from_rulings,
    require_params, setup_logger,
)

ensure_console_utf8()

log = setup_logger("analyze_coverage_vshape")


class CableParseError(ValueError):
    """皮线米数标注无法按 --cable-pattern 解析出 (米数, 根数)。"""
    pass


def parse_cable(text, rex, meters_group=None, count_group=None):
    """从皮线米数标注解析 (米数, 根数)，兼容不同图纸的字段序。

    判定顺序（先显式、后自动）：
      1. 命名组：正则含 `(?P<meters>…)` / `(?P<count>…)` 时直接采用；
      2. 显式组号：meters_group / count_group
         （对应 --cable-meters-group / --cable-count-group，1 基）；
      3. 自动：捕获片段带 `m` / `米` 后缀者判为米数；若都带或都不带，取**数值大者**
         为米数（米数量级远大于根数，`20m*2` 与 `2Px2芯x36m` 均成立）。
         只捕获到 1 个数值时视为米数，根数记 1。

    参数:
        text: 单条标注原文，如 `2Px2芯x36m`
        rex:  已编译的米数正则
    返回:
        (米数, 根数)，均为 int
    异常:
        CableParseError — 不匹配 / 组号越界 / 捕获值无法转整数
    """
    m = rex.match(text)
    if not m:
        raise CableParseError('标注 %r 不匹配 --cable-pattern' % text)
    ngroups = m.re.groups or 0
    gd = m.groupdict()

    def _grp(idx, what):
        if idx < 1 or idx > ngroups:
            raise CableParseError('%s=%d 超出正则捕获组数 %d（标注 %r）'
                                  % (what, idx, ngroups, text))
        return m.group(idx)

    m_str = gd.get('meters')
    c_str = gd.get('count')
    if m_str is None and meters_group is not None:
        m_str = _grp(meters_group, '--cable-meters-group')
    if c_str is None and count_group is not None:
        c_str = _grp(count_group, '--cable-count-group')

    if m_str is None or c_str is None:
        cands = [(i + 1, g) for i, g in enumerate(m.groups()) if g is not None]
        if not cands:
            raise CableParseError(
                '--cable-pattern 未捕获到任何数值（标注 %r）；'
                '请在正则里加捕获组，或用 --cable-meters-group 指定' % text)
        if len(cands) == 1:
            m_str, c_str = cands[0][1], '1'
        else:
            def _val(s):
                d = re.sub(r'\D', '', s)
                return int(d) if d else -1
            with_m = [t for t in cands if re.search(r'[mM米]', t[1])]
            pick_m = with_m[0] if len(with_m) == 1 else max(cands, key=lambda t: _val(t[1]))
            pick_c = next(t for t in cands if t is not pick_m)
            if m_str is None:
                m_str = pick_m[1]
            if c_str is None:
                c_str = pick_c[1]

    def _to_int(s, what):
        d = re.sub(r'\D', '', s or '')
        if not d:
            raise CableParseError('%s 无法解析为整数：%r（标注 %r）' % (what, s, text))
        return int(d)

    return _to_int(m_str, '米数'), _to_int(c_str, '根数')


def norm(s):
    """MTEXT 清理：去段落符(\\P)、统一负号(U+2212→-)，再做通用清洗。"""
    return clean_text((s or '').replace('\\P', ' ').replace('\u2212', '-'))


def fl_num(name):
    """楼层名 → 排序值（支持 3F / -1F / B1 / B2 / WF；认不出返回 -9999）。

    2026-09-12：改走 ftth_common.floor_num（parse_floor_label 统一解析），
    旧实现只认 `(-?\\d+)F`，把 `B1` 判为 -9999，与主链口径不一致。
    """
    v = floor_num(name, use_fullmatch=True)
    return v if v is not None else -9999


def unit_no_from_key(key):
    """单元键 → 单元号；取不出返回 None（调用方登记，不静默）。

    兼容 `1单元` 与 `1#楼1单元`（楼名+单元并写）两种实测写法；`全部` 表示该楼
    未拆分单元，按 1 单元对位。
    """
    s = str(key or '')
    m = re.search(r'([0-9]+)单元', s)
    if m:
        return int(m.group(1))
    if s.strip() in ('全部', '全楼'):
        return 1
    return None


def find_valleys(ms):
    """局部极小索引（平台取中点；各段独立判定，不假设全局最小值相同）"""
    n = len(ms)
    if n == 0:
        return []
    out = []
    for i in range(n):
        left = ms[i - 1] if i > 0 else float('inf')
        right = ms[i + 1] if i < n - 1 else float('inf')
        if ms[i] <= left and ms[i] <= right and (ms[i] < left or ms[i] < right):
            out.append(i)
    merged = []
    for i in out:
        if merged and i - merged[-1][-1] <= 1 and ms[i] == ms[merged[-1][-1]]:
            merged[-1].append(i)
        else:
            merged.append([i])
    return [c[len(c) // 2] for c in merged]


def read_texts(dxf_path, layers, ttypes):
    """读取指定图层/类型的文字，返回 [(x, y, 内容, 字高), ...]（统一走 ftth_common.collect_texts）。

    2026-09-15：附带**字高**——它是本图唯一与坐标尺度无关的长度尺子，
    建列容差、窗口边距一律按 `倍数 × 字高` 给，不再写死坐标值。
    """
    _, msp = load_dxf(dxf_path, log)
    items = collect_texts(msp, layers, ttypes)
    texts = []
    for it in items:
        s = norm(it['内容'])
        if s:
            texts.append((it['x'], it['y'], s, it.get('高') or 0.0))
    return texts


def cluster_column_x(vals, tol):
    """按 x 建「米数列」：升序链式合并，相邻差 > tol 即断开。

    返回 [{'x': 中位, 'lo': 最小, 'hi': 最大, 'n': 条数, 'vals': [...]}, ...]
    """
    xs = sorted(vals)
    if not xs:
        return []
    groups, cur = [], [xs[0]]
    for v in xs[1:]:
        if v - cur[-1] <= tol:
            cur.append(v)
        else:
            groups.append(cur)
            cur = [v]
    groups.append(cur)
    out = []
    for g in groups:
        out.append({'x': g[len(g) // 2], 'lo': g[0], 'hi': g[-1],
                    'n': len(g), 'vals': list(g)})
    return out


def main():
    ap = argparse.ArgumentParser(description='皮线 V 形覆盖判定（V型计算）')
    ap.add_argument('dxf', help='输入 DXF 文件路径')
    ap.add_argument('out', help='输出 JSON 路径')
    ap.add_argument('--text-layer', default=None, help='文字所在图层，逗号分隔（必填，由探查提供）')
    ap.add_argument('--text-type', default='MTEXT,TEXT', help='文字实体类型，逗号分隔（默认两者都取）')
    ap.add_argument('--title-pattern', default=None,
                    help='楼栋标题正则，组1为楼栋号（必填，由探查枚举标题写法后提供）')
    ap.add_argument('--fx-pattern', default=None,
                    help='分纤箱编号正则（必填，由探查采样后提供）')
    ap.add_argument('--box-mark-pattern', default=None,
                    help='系统图上**箱位标记文字**的正则（可选），如 `配线箱|分纤箱|光分路箱`。'
                         '用于 V 谷底定层的独立交叉验证——有的图纸系统图上只写「配线箱」'
                         '而不写编号（编号画在平面图区），此时只认 --fx-pattern 会让'
                         '「自检_v底vs箱符号」整段为空、V 底失去第二来源。'
                         '注意：只作**位置锚**，不参与箱编号归属')
    ap.add_argument('--floor-pattern', default=None,
                    help='楼层标注正则。默认 None＝内置统一解析（支持 3F/17F/-1F/B1/B2/WF）；'
                         '不要用 (-?\\d+)F 覆盖，否则 B1 整层静默消失')
    ap.add_argument('--hu-pattern', default=None, help='户数标注正则（可选，用于交叉核对；由探查提供）')
    ap.add_argument('--cable-pattern', default=None,
                    help='皮线米数正则（必填，由探查采样后提供）。默认按「捕获片段带 m/米 后缀者=米数」'
                         '自动判定，再以数值大者兜底；也可用命名组 (?P<meters>…) / (?P<count>…)')
    ap.add_argument('--cable-meters-group', type=int, default=None,
                    help='显式指定米数所在捕获组序号（1 基）。字段序非「米数在前」时使用：'
                         '如 `2Px2芯x36m` 配 `(\\d+)Px(\\d+)芯x(\\d+)m` 时应传 3')
    ap.add_argument('--cable-count-group', type=int, default=None,
                    help='显式指定根数所在捕获组序号（1 基）；与 --cable-meters-group 配套使用')
    ap.add_argument('--x-tol', type=float, default=30,
                    help='同列 x 聚簇阈值**兜底值**（仅在量不出字高时使用）。'
                         '正常路径走 --col-x-tol-factor × 本图米数文字高度中位数')
    ap.add_argument('--col-x-tol-factor', type=float, default=3.0,
                    help='米数列建列容差 = 本系数 × 米数文字高度中位数（**尺度锚**，默认 3.0）。'
                         '2026-09-15 立：实测某图列内 x 抖动 0.79×字高、相邻列间距 23×字高，'
                         '故 3×字高 落在分离带正中；写死坐标值会在换尺度的图纸上整图崩坏')
    ap.add_argument('--min-col-rows', type=int, default=3,
                    help='米数列**最少行数**门槛（默认 3）。低于此数的列不生成单元，'
                         '改写进「需人工裁决」——一条逐层米数列至少应覆盖 3 层')
    ap.add_argument('--y-margin-factor', type=float, default=3.0,
                    help='窗口 y 上下外扩 = 本系数 × 层高（默认 3.0，用于纳入列头/箱位标注）')
    ap.add_argument('--floor-x-tol', type=float, default=3000,
                    help='楼层列 x 聚簇阈值（默认3000）。层号文字按位数右对齐时，x 会随字数抖动'
                         '（实测 `1F` 与 `18F` 同列却差约 1.7e3），沿用默认 30 会被切成 3 列，'
                         '进而触发「楼层列与米数列数量不匹配」而放弃楼层锚定')
    ap.add_argument('--y-tol', type=float, default=20, help='米数行配楼层的 y 容差下限（默认 20；实现为 max(本值, 实测行距×1.5)，随图自适应抬升）')
    ap.add_argument('--box-x-tol', type=float, default=40, help='箱号分派到单元的 x 容差下限（默认 40；实现为 max(本值, 字高中位自适应量)，随图缩放）')
    ap.add_argument('--box-anchor-x-factor', type=float, default=10.0,
                    help='箱位锚到其所属米数列的 **x 邻域上限 = 本系数 × 字高中位**（默认 10.0）。'
                         '2026-09-15（P0-9）立：箱编号常画在平面图区/箱表区，与系统图区同处一个 x '
                         '窗口却无几何关联；实测某图真锚距米数列 4.9~5.8×字高，而箱表区编号 40~59×、'
                         '邻楼锚 34×字高 —— 分离带极宽。超阈者不参与箱编号归属并列入待裁决。'
                         '量不出字高时门禁失效（退回宽松策略），须在证据里说明')
    ap.add_argument('--dev-gate-factor', type=float, default=5.0,
                    help='v底vs箱符号偏差**可信门禁** = 本系数 × 层高（默认 5.0，尺度无关）。'
                         '2026-09-16（12坑复核）立：跨地块/跨图幅数据混入时偏差可达十余万'
                         '（正常远小于 1×层高），此前只打印统计、超阈不报警，混在均值里'
                         '不自我暴露。超阈项登记需人工裁决，不自动改判安装层（原则二）。'
                         '量不出层高锚时门禁失效，并在结果中显式说明')
    ap.add_argument('--fx-locations', default=None,
                    help='箱位直读标注 JSON（extract_fx_locations.py 产出，可选）。'
                         '提供后逐箱比对「V型谷底安装层 vs 直读标注安装层」：'
                         '一致计入自检，不一致并列证据登记需人工裁决——'
                         '不自动改判、不以标注为准（原则二：不自行择一）')
    ap.add_argument('--margin', type=float, default=400, help='首末标题外侧窗口宽度的兜底值（默认 400；有相邻标题时改用间距中位数自适应，本值仅在无法量距时生效）')
    ap.add_argument('--include-basement', action='store_true',
                    help='把全局最低段下方的地下层并入覆盖下界。默认关闭：'
                         'V型计算的数据来源是米数列标注，覆盖范围只含米数列实际覆盖的楼层')
    args = ap.parse_args()

    require_params([
        ('--text-layer', args.text_layer, '含FTTH标注的文字图层（探查图层清单+采样后确定）'),
        ('--title-pattern', args.title_pattern, '楼栋标题正则，需含组1=楼栋号'),
        ('--fx-pattern', args.fx_pattern, '分纤箱编号正则'),
        ('--cable-pattern', args.cable_pattern,
         '皮线米数正则（可用命名组或 --cable-meters-group 指定米数位置）'),
    ], 'analyze_coverage_vshape')

    TITLE = re.compile(args.title_pattern)
    FXRE = re.compile(args.fx_pattern)
    FLRE = re.compile(args.floor_pattern) if args.floor_pattern else None
    HURE = re.compile(args.hu_pattern) if args.hu_pattern else None
    CBRE = re.compile(args.cable_pattern)
    BOXRE = re.compile(args.box_mark_pattern) if args.box_mark_pattern else None

    layers = set(x.strip() for x in args.text_layer.split(','))
    ttypes = set(x.strip().upper() for x in args.text_type.split(','))

    def is_floor(s):
        if parse_floor_label(s)[0] is not None:
            return True
        return bool(FLRE.fullmatch(s)) if FLRE is not None else False

    texts = read_texts(args.dxf, layers, ttypes)

    # ---------- 尺度锚（2026-09-15 立）----------
    # 本脚本原先多处使用绝对坐标阈值（列容差 30、带容差下限 5000、带跨度 500000、
    #   窗口 y 用整带高度…），这些值都是在某一版图纸的坐标尺度上标定的。换一张图
    #   （实测另一项目坐标尺度差 ~10^3 倍）整图崩坏：一条米数列被切成几十段、
    #   窗口吞进相邻地块的数据。
    # 现改为**双锚**：
    #   · 字高锚（本图米数文字高度中位数）→ 一切「x 方向多近算同列」的判据
    #   · 层高锚（本图楼层标注量出的竖向栅格）→ 一切「y 方向多远算同一块」的判据
    # 两者都随图纸缩放，判据因此与坐标尺度无关。
    _hmed = median_text_height(
        [{'内容': s, '高': h} for _, _, s, h in texts], pred=lambda s: bool(CBRE.match(s)))
    _col_tol = (args.col_x_tol_factor * _hmed) if _hmed else args.x_tol
    _hmed_any = median_text_height([{'内容': s, '高': h} for _, _, s, h in texts])
    _fl_step, _fl_why = floor_step_from_texts(
        [{'内容': s, 'x': x, 'y': y} for x, y, s, _ in texts], is_floor)
    if _fl_step is None and _hmed_any:
        # 兜底：无楼层刻度时用字高推一个保守的竖向步长（实测层高 ≈ 5×字高）
        _fl_step, _fl_why = 5.0 * _hmed_any, '楼层刻度量不出，按 5×字高 兜底'
    # 楼层列建列容差同样锚定字高（原先写死 3000）——取两者较大者，
    #   保证「1F 与 15F 同列却因右对齐差 1.4×字高」不被切裂。
    _fl_col_tol = max(args.floor_x_tol, _col_tol) if _hmed else args.floor_x_tol
    _box_tol = max(args.box_x_tol, _col_tol) if _hmed else args.box_x_tol
    _anchor_note = ('字高中位=%s → 建列容差=%.4g；层高锚=%s（%s）'
                    % ('%.4g' % _hmed if _hmed else '量不出',
                       _col_tol if _hmed else args.x_tol,
                       '%.4g' % _fl_step if _fl_step else '量不出', _fl_why))
    log.info('尺度锚：%s', _anchor_note)

    # 2026-09-13（P0-1）：楼号统一走 parse_bldg_nums。旧写法
    #   `int(TITLE.search(s).group(1))` 有两个硬伤：
    #   ① 图上为 `N号楼` 而 title-pattern 写 `(\d+)#` 时匹配不到 → 脚本空转；
    #   ② 共享标题（`3/6号楼…`）只取首号 → 其余楼栋整栋丢失。
    titles = []
    for x, y, s, _h in texts:
        if not TITLE.search(s):
            continue
        nums = parse_bldg_nums(s)
        if not nums:
            # first_group 保证 TITLE 写成 `\d+号楼`（无捕获组）时也不崩
            g = first_group(TITLE.search(s))
            if g is not None and str(g).strip().isdigit():
                nums = [int(str(g).strip())]
        if nums:
            titles.append((x, y, s, nums))
    titles.sort(key=lambda t: t[0])
    if not titles:
        log.error("未匹配到任何楼栋标题，请检查 --title-pattern 与 --text-layer")
        sys.exit(1)

    # 展开为「每栋一个分析窗口」。共享标题的多栋共用同一 x 区间——
    #   此处不按栋切分窗口内数据（切分需图纸语义），改在结果里标注为待人工核对。
    #
    # 2026-09-14（P0-3，多图幅）：一张图纸可含多个「图幅」（系统图块），各图幅的 x 区间
    #   可能完全重叠——实测柳辛庄5-9地块：4 个图幅的楼栋标题 x 全部落在 2.1M~3.0M，
    #   而 y 分属 4 个带（1763108 / 904304 / 2626985 / 73808）。仅按 x 切窗口会把不同图幅
    #   的楼栋数据混到一起，表现为满屏「楼层列与米数列数量不匹配」、部分楼栋误判「无米数」。
    #   故：先按标题 y 聚类分带，带内再按 x 切窗；取数时同时约束 x 与 y。
    def _y_bands(ts, tol=None):
        # 2026-09-14（P0-5）：y 带容差自适应——固定 5000 在坐标尺度不同的图纸上
        #   会误分/误合。实测 1-4 地块两图幅标题 y 相差 14281（应合并），
        #   而 5-9 地块相邻图幅间隔 800K+（应分开）。
        #   方法：取去重后 y 间距，按升序排列，找**相邻间距比最大处**（elbow），
        #   elbow 以下的间距属同一图幅内抖动，elbow 以上属图幅间距。
        #   tol = elbow 处间距 × 1.5，**下限 = 3×层高**（2026-09-15 改：原先写死 5000，
        #   是绝对坐标值；换尺度后 5000 可能大于整个地块的 y 跨度 → 全部地块并成一带）。
        #   注意：必须去重——共享标题使多条标题 y 相同，不去重则中位间距=0。
        if tol is None:
            uniq_ys = sorted(set(t[1] for t in ts))
            _floor_tol = 3.0 * _fl_step if _fl_step else 5000.0
            if len(uniq_ys) >= 3:
                gaps = sorted([abs(uniq_ys[i + 1] - uniq_ys[i])
                               for i in range(len(uniq_ys) - 1)])
                # Elbow detection: 找相邻间距比最大的位置
                max_ratio = 1.0
                elbow_idx = len(gaps)  # 默认不合并
                for i in range(len(gaps) - 1):
                    if gaps[i] > 0:
                        ratio = gaps[i + 1] / gaps[i]
                        if ratio > max_ratio:
                            max_ratio = ratio
                            elbow_idx = i
                if elbow_idx < len(gaps):
                    tol = max(gaps[elbow_idx] * 1.5, _floor_tol)
                else:
                    tol = _floor_tol
            else:
                tol = _floor_tol
        out = []
        for t in sorted(ts, key=lambda a: -a[1]):
            if out and abs(out[-1][-1][1] - t[1]) <= tol:
                out[-1].append(t)
            else:
                out.append([t])
        return out, tol

    def _content_blocks_1d(ys, step):
        """把一组 y（本图米数行）按「相邻间距 > 3×层高 即断开」切成连通块。

        2026-09-15（P0-12）：本图**内容**（米数标注）在 y 上的连通块，是判断
        「图幅究竟是上下分层、还是同一行内并排」的可靠依据 —— 只看标题的 y 分簇
        做不到：同一行内并排的图幅，其标题 y 也可能存在多个微簇，从而被误判成多个带。
        实测：上下分层型图 内容块数 == 标题带数（一一对应）；
              一行内并排型图 内容块数 = 1 而标题带数 = 6（误分）。
        断开阈值取 3×层高，与「第二刀」窗口内的行块检测同一口径。
        """
        ys = sorted(set(ys))
        if not ys:
            return []
        _lim = (3.0 * step) if step else None
        out, cur = [], [ys[0]]
        for _y in ys[1:]:
            if _lim is None or _y - cur[-1] <= _lim:
                cur.append(_y)
            else:
                out.append((cur[0], cur[-1]))
                cur = [_y]
        out.append((cur[0], cur[-1]))
        return out

    _bands, _band_tol_used = _y_bands(titles)
    _band_y = [max(b, key=lambda a: a[1])[1] for b in _bands]
    # 单图幅数据 y 跨度上限：2026-09-15 改为 层高倍数（原先写死 500000 绝对坐标）。
    #   2026-09-16 实测某图：18层楼内容含机房层+B1F 时，标题以上内容可达 ≈23×层高，
    #   20×不够 → 顶部图幅最高的 1~2 行（顶层）被静默切掉。取 26×层高留裕量；
    #   多带图幅的邻带侧仍有中点/邻带-1 封顶，加大 span 只放开最外侧，不外溢。
    _band_span = 26.0 * _fl_step if _fl_step else 500000.0

    # 2026-09-15（P0-12）：内容连通块判据（见 _content_blocks_1d）。
    #   本图米数只有**一个**连通块 ⇒ 全图只有一个图幅，标题的多个 y 微簇是
    #   同一行内并排的图幅/图签，不是上下分层 ⇒ 强制单带，带 y 边界取内容块
    #   范围 ± N×层高（内容块 = 本图数据区的真实纵向范围，与坐标尺度无关）。
    #   多块时不介入，完全沿用原 y 聚类（保证既有图纸零回归）。
    _cblks = _content_blocks_1d(
        [t[1] for t in texts if CBRE.match(t[2])], _fl_step)
    _force_single = (len(_cblks) == 1 and len(_bands) > 1)
    _single_ylo = None
    _single_yhi = None
    if _force_single:
        _mg0 = args.y_margin_factor * _fl_step if _fl_step else 0.0
        _single_ylo = _cblks[0][0] - _mg0
        _single_yhi = _cblks[0][1] + _mg0
        _bands = [sorted(titles, key=lambda a: a[0])]
        _band_y = [max(_bands[0], key=lambda a: a[1])[1]]
    windows = []
    for _bi, _band in enumerate(_bands):
        _band = sorted(_band, key=lambda a: a[0])
        # _bands 按 y 降序排列，故「上一个带」给出上界、「下一个带」给出下界。
        # 注意：系统图数据（层号/米数）常位于楼栋标题的**上方**（实测某图标题 y=1.763M，
        #   数据 y=1.784M~2.106M，即 +2.1万~+34万），故带边界不能用「标题 y ± 固定值」。
        #
        # 2026-09-15（P0-8）：**带的上界不能用相邻带标题 y 的中点，下界仍必须用中点**。
        #   根因：本带内容在标题上方延伸的高度，可能**超过「本带标题与上邻带标题间距的一半」**
        #   —— 此时中点边界会横穿本带内容，把顶部若干层标注整段切掉，
        #   表现为「米数表少几行、V 谷底少 1 个、箱数少 1 个」；
        #   而第一刀 win_x 又按该边界过滤，内容永远无法自证顶端（死锁）。
        #   故上界改取**上邻带标题 y**（上邻带内容只在其标题上方，不越过即安全）。
        #   下界**必须维持中点**：下邻带内容正好在它自己标题的上方，
        #   把下界放到「下邻带标题 y」必然吞进下邻带整块内容
        #   （实测该改法使单元数翻倍、V 段碎裂，属明确回归）。
        #   要点：本类图纸「内容全在标题上方」⇒ 上界可放宽、下界不可放宽，方向不对称。
        # 中点边界：**仅作留档**（'yhi' 字段），自 2026-09-15 起不参与窗口过滤。
        if _force_single:
            # P0-12：单带时不存在「邻带」可混淆，y 边界直接取内容块范围。
            #   本类图纸内容画在标题**下方**，原「上界=邻带标题 y / 下界=中点」
            #   会把内容整段切掉（实测窗口内米数 0 条）。
            _yhi = _single_yhi
            _ylo = _single_ylo
            _yhi_max = _single_yhi
        else:
            _yhi = ((_band_y[_bi - 1] + _band_y[_bi]) / 2 if _bi > 0
                    else _band_y[_bi] + _band_span)
            _ylo = ((_band_y[_bi] + _band_y[_bi + 1]) / 2 if _bi < len(_bands) - 1
                    else _band_y[_bi] - _band_span)
            _yhi_max = (_band_y[_bi - 1] - 1.0) if _bi > 0 else (_band_y[_bi] + _band_span)
        # 首/末标题外侧边界：用带内相邻标题间距的中位数（比固定 margin 稳健——
        #   系统图数据常横跨标题左右两侧，固定 400 会把数据切掉）
        _xs = [t[0] for t in _band]
        _gaps = sorted(_xs[i + 1] - _xs[i] for i in range(len(_xs) - 1))
        _span = _gaps[len(_gaps) // 2] if _gaps else args.margin
        for i, (tx, ty, ts, nums) in enumerate(_band):
            lo = (_band[i - 1][0] + tx) / 2 if i > 0 else tx - _span
            hi = (tx + _band[i + 1][0]) / 2 if i < len(_band) - 1 else tx + _span
            for n in nums:
                windows.append({'x': tx, 'y': ty, 'text': ts, 'num': n,
                                'lo': lo, 'hi': hi, 'ylo': _ylo, 'yhi': _yhi,
                                'yhi_max': _yhi_max,
                                'band': _bi,
                                'shared': list(nums) if len(nums) > 1 else None})

    result = {
        'DXF文件': args.dxf,
        '方法': 'V型计算（皮线米数 V 形规律）：米数谷底→箱安装层；相邻谷底中位行→覆盖分界',
        '说明': '本结果由文字标注几何推得。已用箱号文字 y 做独立交叉验证（自检_v底vs箱符号）',
        '参数': {
            '文字图层': sorted(layers),
            '文字类型': sorted(ttypes),
            '标题正则': args.title_pattern,
            '箱号正则': args.fx_pattern,
            '箱位标记正则': args.box_mark_pattern,
            '皮线米数正则': args.cable_pattern,
            '尺度锚': _anchor_note,
            '字高中位': _hmed,
            '层高锚': _fl_step,
            '层高锚依据': _fl_why,
            '米数列建列容差': _col_tol,
            '米数列最少行数': args.min_col_rows,
            '楼层列容差': _fl_col_tol,
            'y容差': args.y_tol,
            '箱号分派x容差': _box_tol,
            '箱位锚邻域上限': ('%.4g×字高中位' % args.box_anchor_x_factor) if _hmed
                              else '未启用（本图量不出字高）',
            '标题y带容差': _band_tol_used,
            '内容连通块数': len(_cblks),
            '内容连通块y': [[round(a, 1), round(b, 1)] for a, b in _cblks],
            '强制单带': _force_single,
        },
        '楼栋数': len(windows),
        '楼栋': {},
        '自检_v底vs箱符号': [],
        '自检_v形单调性': [],
        '需人工裁决': [],
    }

    # 2026-09-16（12坑复核·坑7）：**同一图幅带内**同名楼标题的防覆盖。
    #   bkey 的 [图幅N] 后缀只按「带」区分；同一带内若有两个同名楼标题
    #   （同带并排多地块 / 标题重复绘制），bkey 相同 → result['楼栋'] 后写覆盖前写，
    #   整栋楼静默丢失。改法：同带同名时给 bkey 追加标题 x 后缀区分（不合并、不择一），
    #   并登记需人工裁决。
    _band_num_cnt = {}
    for _w in windows:
        if _w['shared']:
            continue
        _k = (_w['band'], _w['num'])
        _band_num_cnt[_k] = _band_num_cnt.get(_k, 0) + 1
    _dup_band_num = {k: c for k, c in _band_num_cnt.items() if c > 1}
    for _w in windows:
        if not _w['shared'] and (_w['band'], _w['num']) in _dup_band_num:
            _w['dup_in_band'] = True
    for (_bb, _nn), _cc in sorted(_dup_band_num.items()):
        _xs = [round(_w['x'], 1) for _w in windows
               if not _w['shared'] and _w['band'] == _bb and _w['num'] == _nn]
        result['需人工裁决'].append({
            '对象': '%d#楼[图幅%d]' % (_nn, _bb + 1),
            '事项': '同一图幅带内出现 %d 个同名楼标题（标题x=%s），已按标题x区分键名、未互相覆盖'
                    % (_cc, _xs),
            '说明': '同带并排多地块或标题重复绘制均可导致此现象；请核对各标题对应的物理地块，'
                    '必要时用 --band-anchors 显式分带后重跑。'})

    _fmt_bad = []        # 匹配到米数标注但解析失败的样本（P0-2 体检）
    _fmt_ok = 0          # 成功解析的米数标注条数
    for w in windows:
        tx, ty, ts, n = w['x'], w['y'], w['text'], w['num']
        lo, hi = w['lo'], w['hi']

# ---- 第一刀：只按 x 切（y 用**硬边界**：不越邻楼顶 y）------------------
        # 2026-09-15（P0-8）：从原先此处用中点边界 w['band']，会把该带内容自证顶端的能力
        #   一并掐死（过滤后内容极值永远 ≤ 中点）。改挂上邻带标题 y 后内容极值才可见。
        # 2026-09-16（P0-12/凤鸣朝阳）：仅按 yhi_max 定上界仍不够 —— 该边界是
        #   "带标题 y + 20×层高"的**估算**，实测 8#楼（18F）顶层 17F/18F 的
        #   楼层标注 y 超过 yhi_max（17F=388000.4、18F=388006.1 > 387998.8），
        #   米数行被窗口过滤掉 → 米数表缺 2 行、FL08-FX02 覆盖漏 17F/18F。
        #   故**单带图纸**（无邻带可混淆）上界取「yhi_max」与「本窗口 x 内楼层标注列
        #   y 最大值 + 外扩」的较大者 —— 楼层标注列是栋级最完整的楼层证据，
        #   存在即可证明该层数据应入窗。
        #   **多带图纸不启用**：楼层标注列跨带（如柳辛庄 1-4 图幅4 的楼层标注
        #   属于下带），放宽上界会把邻带楼层/箱位标注吞进窗口（实测箱数 27→42、
        #   安装层错乱），故多带时维持原 yhi_max 不动。
        _fl_win_top = None
        if len(_bands) == 1:
            _fl_win_top = max([t[1] for t in texts
                               if lo <= t[0] < hi and is_floor(t[2])],
                              default=w['yhi_max'])
        _win_y_hi = (max(w['yhi_max'],
                         _fl_win_top + (args.y_margin_factor * _fl_step if _fl_step else 0.0))
                     if _fl_win_top is not None else w['yhi_max'])
        win_x = [t for t in texts
                 if lo <= t[0] < hi and w['ylo'] <= t[1] <= _win_y_hi]

        # ---- 第二刀：窗口 y 收紧（2026-09-15 立，台账 P1-4）--------------------
        # 原实现窗口 y 直接取「相邻地块标题 y 的中点」，实测高 49 万 ≈ 28×层高，
        #   把 y 相差 21 万的**相邻地块**整块米数列吞了进来 → 凭空多出几十个"单元"。
        # 现改为：以标题 y 为块底，向上并入「相邻行距 ≤ 3×层高」的米数行
        #   ——即本栋系统图数据块的真实 y 跨度；上下再外扩 N×层高，纳入列头与箱位标注。
        _my = sorted({round(t[1], 1) for t in win_x if CBRE.match(t[2])})
        _above = [y for y in _my if y > ty]
        _blk = []
        if _above and _fl_step:
            _blk = [_above[0]]
            for _y in _above[1:]:
                if _y - _blk[-1] <= 3.0 * _fl_step:
                    _blk.append(_y)
                else:
                    break            # 行距突增 ＝ 跨到相邻地块，立即停
        if _blk:
            _mg = args.y_margin_factor * _fl_step
            # 2026-09-15（P0-8）：**只上调上界**，且只并入「米数行块顶之上」的**同类标注**
            #   （米数行 / 箱位锚 / 楼层列）—— 它们同样是本栋系统图的最顶标注。
            #   实测某图最高箱位标注比米数行块顶还高，只按米数行块定界会把它连同其上方
            #   数层米数行整段切掉（→ 米数表缺行、V 谷底少 1、箱数少 1）。
            #   刻意**不取窗内全体文字的极值**：窗外仍可能有邻带的箱表/图签文字，
            #   一旦纳入会把窗口反向撑大到邻带（实测单元数翻倍、V 段碎裂）。
            #   下界维持原逻辑不动 —— 本类图纸内容全在标题上方，向下放宽必然吞邻带。
            _ys_up = [t[1] for t in win_x
                      if t[1] > _blk[-1]
                      and (CBRE.match(t[2]) or is_floor(t[2])
                           or FXRE.match(t[2])
                           or (BOXRE is not None and BOXRE.match(t[2])))]
            _ytop = max([_blk[-1]] + _ys_up)
            wy_lo = max(w['ylo'], _blk[0] - _mg)
            # 2026-09-16（P0-12/凤鸣朝阳）：上界由「yhi_max（带标题+20×层高估算）」
            #   改为「窗口内楼层标注列顶 + 外扩」与 yhi_max 的较大者（_win_y_hi，
            #   见第一刀）。根因：8#楼 18F 的楼层标注 y 超出 yhi_max（387998.8），
            #   原实现把顶层米数行整段滤掉 → 覆盖漏 17F/18F。楼层标注列是栋级
            #   最完整的楼层证据，它在窗内即证明该层数据应入窗。
            wy_hi = min(_win_y_hi, max(_blk[-1] + _mg, _ytop + _mg))
            _y_note = ('米数行块 [%.1f, %.1f]（%d 行，行距≤3×层高）；'
                       '块顶之上同类标注最高 y=%.1f；外扩 %.4g；上界 %.1f'
                       '（%s）'
                       % (_blk[0], _blk[-1], len(_blk), _ytop, _mg, wy_hi,
                          ('楼层列顶+外扩 P0-12 兜底' if _fl_win_top is not None
                           else '沿用 yhi_max')))
        else:
            wy_lo, wy_hi = w['ylo'], _win_y_hi
            _y_note = '标题上方未见米数行，沿用带边界（层高锚：%s；P0-12 楼层列顶 %.1f）' % (_fl_why, _win_y_hi)
        win = [t for t in win_x if wy_lo <= t[1] <= wy_hi]

        floors = [(x, y, s) for x, y, s, _h in win if is_floor(s)]
        _raw_cables = [(x, y, s) for x, y, s, _h in win if CBRE.match(s)]
        # 2026-09-13（P0-2）：先做格式体检——匹配到标注但一条都解析不出时，
        #   立刻以退出码 2 终止并打印样本，避免整轮空转后仍报"成功"。
        cables = []
        for _c in _raw_cables:
            try:
                parse_cable(_c[2], CBRE, args.cable_meters_group, args.cable_count_group)
                cables.append(_c)
            except CableParseError as _ce:
                _fmt_bad.append((_c[2], str(_ce)))
        _fmt_ok += len(cables)
        hus = [(x, y, s) for x, y, s, _h in win if HURE and HURE.match(s)]
        # 箱位锚：除 --fx-pattern（编号）外，还可认 --box-mark-pattern（系统图上直写的
        #   「分纤箱／配线箱」字样）。后者是 V 谷底定层的**独立第二来源**——实测有的图
        #   系统图上只写「配线箱」、编号全在平面图区，只认 FX 编号会让自检整段为空。
        boxes = sorted([(x, y, s) for x, y, s, _h in win
                        if FXRE.match(s) or (BOXRE is not None and BOXRE.match(s))],
                       key=lambda b: (b[0], -b[1]))

        fcols = cluster_chain_mean([f[0] for f in floors], _fl_col_tol)
        # 2026-09-15（P0-6 / P1-5）：米数列改「按字高锚建列」＋「最小行数门槛」。
        #   P0-6：旧实现 tol=30 是绝对坐标值，而本图列内 x 抖动可达 2684（0.79×字高）
        #         → 一条 12 行的合法米数列被切成 12 段，规则又是「1 列 = 1 单元」
        #         → 一栋楼凭空多出 30 个单元（用户反馈的"单元数说不清"主因）。
        #   P1-5：1~2 行的碎片列照样生成单元。一条逐层米数列至少覆盖 3 层。
        ccols_all = cluster_column_x([c[0] for c in cables], _col_tol)
        ccols = [c for c in ccols_all if c['n'] >= args.min_col_rows]
        _short = [c for c in ccols_all if c['n'] < args.min_col_rows]
        hcols = cluster_chain_mean([h[0] for h in hus], _col_tol)

        # 2026-09-14（P0-3）：多图幅下同一楼号（如各区都有「1#楼」）会互相覆盖，
        #   故多于一个图幅时给 key 加「[图幅N]」后缀；单图幅保持原样，不影响既有下游。
        # 2026-09-15（P0-7）：**共享标题**不再把整窗复制给标题里的每一栋。
        #   旧实现只登记一条"需人工裁决"，却仍让每栋各跑同一窗口，实测
        #   「2#楼」与「3#楼」的单元结构**逐字相同**、完全不可用。
        #   现改为把它整体输出为**一个组**（组内米数列按 x 升序编号 列1..列N），
        #   并把「哪一列属哪一栋」显式列为待裁决 —— 图纸上确实没有几何证据可判
        #   （箱编号画在平面图区、与系统图区无连线），按原则二不得脚本自行择一。
        _sfx = '[图幅%d]' % (w['band'] + 1) if len(_bands) > 1 else ''
        if w.get('dup_in_band'):
            _sfx = '%s@x%.0f' % (_sfx, tx)
        bkey = ('[共享]%s%s' % (ts, _sfx)) if w['shared'] else ('%d#楼%s' % (n, _sfx))
        binfo = {'图幅带': w['band'], '标题x': round(tx, 1), '标题': ts,
                 '窗口x': [round(lo, 1), round(hi, 1)],
                 '窗口x收紧': [round(wy_lo, 1), round(wy_hi, 1)],
                 '窗口y': [round(w['ylo'], 1), round(w['yhi'], 1)],
                 '窗口y定界依据': _y_note,
                 '共享楼栋': w['shared'],
                 '楼层列x': [round(v, 1) for v in fcols],
                 '米数列x': [round(c['x'], 1) for c in ccols],
                 '米数列行数': [c['n'] for c in ccols],
                 '户数列x': [round(v, 1) for v in hcols],
                 '箱号': [{'编号': b[2], 'x': round(b[0], 1), 'y': round(b[1], 1)} for b in boxes],
                 '单元': {}}

        if _short:
            result['需人工裁决'].append({
                '对象': bkey, '事项': '存在不足 %d 行的米数碎片列，已剔除不生成单元'
                                      % args.min_col_rows,
                '说明': '碎片列 x=%s（行数 %s）。一条逐层米数列至少应覆盖 %d 层；'
                        '若这些列确为真实单元，请下调 --min-col-rows 并复核。'
                        % ([round(c['x'], 1) for c in _short], [c['n'] for c in _short],
                           args.min_col_rows)})
        if _short:
            # 碎片列的识别依据留档：原 x 容差切出的列数 vs 字高锚切出的列数
            binfo['碎片列'] = [{'x': round(c['x'], 1), '行数': c['n'],
                              'x跨度': round(c['hi'] - c['lo'], 1)} for c in _short]

        if not ccols:
            result['需人工裁决'].append({
                '对象': bkey, '事项': '无皮线米数标注，V形法不适用',
                '说明': '该楼窗口内未匹配到 --cable-pattern，请确认标注写法或改用竖线法'})
            result['楼栋'][bkey] = binfo
            continue
        if len(fcols) != len(ccols):
            # 2026-09-14（P0-4）：楼层列与米数列数量不匹配不再是硬告警 ——
            #   常见情形：多单元共享同一楼层列（fcols=1, ccols=2），此时每个米数列
            #   代表一个单元，各自找最近楼层列配对即可。仅当 ccols > fcols 且
            #   无法解释时（如 fcols=0）才作为真告警。
            if len(fcols) == 0:
                result['需人工裁决'].append({
                    '对象': bkey, '事项': '楼层列与米数列数量不匹配',
                    '说明': '楼层列 %d 个 / 米数列 %d 个（无楼层列可用）' % (len(fcols), len(ccols))})
            # else: 共享楼层列是正常布局，不告警

        # 2026-09-15：箱位锚**按最近米数列归属**（尺度无关），不再用绝对容差。
        #   旧实现 `[b for b in boxes if |b.x-ccx|<=tol] or boxes` 有隐患——
        #   实测箱位标注文字与其米数列的 x 差可达 6×字高，固定容差必然落空，
        #   于是回落成「把窗口内全部箱拿来配对」，等于把别单元的箱错配给本单元。
        _box_owner = []
        _box_far = []          # 2026-09-15（P0-9）：超邻域的箱锚，剔除并交人裁决
        _anchor_tol = (args.box_anchor_x_factor * _hmed) if _hmed else None
        for _b in boxes:
            if ccols:
                _k = min(range(len(ccols)), key=lambda k: abs(ccols[k]['x'] - _b[0]))
                _dx = abs(ccols[_k]['x'] - _b[0])
                # 2026-09-15（P0-9）：箱锚必须落在其所属米数列的 **x 邻域** 内。
                #   根因：箱编号常画在「平面图区／箱表区」，与系统图区在 x 上同处一个
                #   窗口却毫无几何关联；窗口一旦放宽（P0-8）就会把邻区甚至邻楼的编号
                #   吞进来，表现为「一个单元配到远多于 V 段数的箱」「V段数≠箱数」的假告警。
                #   实测某图：真锚距米数列 4.9~5.8×字高，而箱表区编号达 40~59×字高、
                #   邻楼锚达 34×字高 —— 分离带极宽，故取 10×字高 作门禁（尺度无关）。
                #   超阈者**不参与箱编号归属**，但必须显式登记，供人直接比对距离。
                if _anchor_tol is not None and _dx > _anchor_tol:
                    _box_far.append((_b, _dx))
                    _box_owner.append(-1)
                else:
                    _box_owner.append(_k)
            else:
                _box_owner.append(-1)

        if _box_far:
            _bf = [{'编号': b[2], 'x': round(b[0], 1), 'y': round(b[1], 1),
                    '距最近米数列': round(dx, 1),
                    '折合字高': round(dx / _hmed, 2) if _hmed else None} for b, dx in _box_far]
            binfo['超邻域箱锚'] = _bf
            result['需人工裁决'].append({
                '对象': bkey,
                '事项': '存在 %d 个超出米数列邻域（>%.4g×字高）的箱位锚，已剔除、不参与箱编号归属'
                        % (len(_box_far), args.box_anchor_x_factor),
                '说明': '箱位锚 %s。箱编号常画在平面图区/箱表区，与系统图区无几何关联；'
                        '若这些确是本单元箱位，请核对图纸或上调 --box-anchor-x-factor 后复核。'
                        % [(_b[2], '距%.0f' % _dx) for _b, _dx in _box_far]})

        # 2026-09-14（P0-4）：遍历**所有米数列**，不再取 min(fcols, ccols)。
        #   每个米数列代表一个单元；楼层列可被多单元共享，
        #   每个米数列找最近楼层列配对即可。
        for ui in range(len(ccols)):
            ccx = ccols[ui]['x']
            # 找最近的楼层列配对（楼层列可共享）
            fcx = min(fcols, key=lambda v: abs(v - ccx)) if fcols else None
            if fcx is None:
                continue
            col_f = sorted([f for f in floors if abs(f[0] - fcx) <= _fl_col_tol], key=lambda a: -a[1])
            col_c = sorted([c for c in cables
                            if ccols[ui]['lo'] - 0.5 <= c[0] <= ccols[ui]['hi'] + 0.5],
                           key=lambda a: -a[1])
            hcx = min(hcols, key=lambda v: abs(v - ccx)) if hcols else None
            col_h = sorted([h for h in hus if hcx is not None and abs(h[0] - hcx) <= _col_tol],
                           key=lambda a: -a[1]) if hcx is not None else []

            # 米数行 → 楼层（按 y 就近）。
            # 2026-09-14（P0-3）：容差改为自适应。米数文字相对楼层线的竖直偏移在同一张图上恒定
            #   （实测约 4.0e3，即文字写在楼层线附近但不同基线），远大于默认 --y-tol 20；
            #   若按 20 判，所有行都会落成 None，整栋楼拿不到「安装层/覆盖楼层」。
            #   故先估基准偏移（各行到最近楼层线距离的中位数），容差 = max(--y-tol, 基准×1.5)。
            #   注意「就近」本身已选定层，容差只用于否决明显错位（残差≈一层高时仍判 None）。
            _d = sorted(abs(min(col_f, key=lambda f: abs(f[1] - cy))[1] - cy)
                        for _, cy, _ in col_c) if col_f else []
            _base = _d[len(_d) // 2] if _d else 0.0
            _ytol = max(args.y_tol, _base * 1.5)
            # 2026-09-15（P0-13）：否决阈值下界抬到「层高/2」。
            #   几何事实：楼层线等距时，任一 y 到**最近**楼层线的距离 ≤ H/2 恒成立——
            #   即残差 < H/2 时最近线必为同层线，不应被任何经验阈值否决。
            #   原经验式「基准×1.5」仅约 0.26×层高：实测某图 3 栋 5 单元的同层米数行
            #   残差恰好越过它（仍远小于 H/2）→ 被误判 None 并**静默丢层**。
            #   上方 P0-3 注释的设计意图本是「残差≈一层高时仍判 None」，
            #   H/2 正是该意图的几何正确实现：只否决必然属于邻层的行。
            _lys = sorted(f[1] for f in col_f)
            _gaps = [b2 - a2 for a2, b2 in zip(_lys, _lys[1:]) if b2 - a2 > 0]
            _hfloor = _gaps[len(_gaps) // 2] if _gaps else 0.0
            if _hfloor > 0:
                _ytol = max(_ytol, _hfloor / 2.0)
            rows = []
            for cx2, cy, cs in col_c:
                mm, cnt = parse_cable(cs, CBRE, args.cable_meters_group, args.cable_count_group)
                near = min(col_f, key=lambda f: abs(f[1] - cy)) if col_f else None
                flname = near[2] if near and abs(near[1] - cy) <= _ytol else None
                rows.append({'楼层': flname, 'y': cy, '米数': mm, '根数': cnt,
                             '楼层线y': near[1] if near else None,
                             '残差': round(abs(near[1] - cy), 1) if near else None})

            # 2026-09-15（P0-13）：判 None 的米数行必须显式登记，禁止静默丢层。
            #   覆盖判定只消费 names（下方 if r['楼层'] 过滤），null 行原本静默消失。
            #   能走到这里的行残差必 > 层高/2——几何上最近线已是邻层
            #   （本层楼层线缺失或标注错位），必须交人核对。
            _null_rows = [r for r in rows if r['楼层'] is None and r['米数'] is not None]
            if _null_rows:
                result['需人工裁决'].append({
                    '对象': '%s / %d单元' % (bkey, ui + 1),
                    '事项': '%d 行米数标注未配对到楼层线（残差 > 层高/2），未纳入覆盖判定'
                            % len(_null_rows),
                    '说明': '行明细(米数,y,残差)=%s。请核对图纸确认归属层；'
                            '若系楼层线漏检，请检查该列楼层标注。'
                            % [(r['米数'], round(r['y'], 1), r['残差']) for r in _null_rows]})

            ms = [r['米数'] for r in rows]
            valleys = find_valleys(ms) if ms else []

            # 分段：相邻谷底之间，取**米数最大**的行作为下箱覆盖上界（该行归下段）。
            #   2026-09-14（P0-3）修正：原按「两谷底索引中点」切分，当谷底间距为偶数层时
            #   会错一层。例：8 区 1 号楼谷底 4F/14F，中点法切出 9F/10F；但
            #   10F 米数 48 = |10-4|×4+24，只能归下箱（4F）；11F 米数 36 = |11-14|×4+24，
            #   只能归上箱（14F）→ 真分界为 10F/11F。
            #   理论上「米数最大行 = 离下箱最远的层」，与逐层米数公式一致，不依赖间距奇偶。
            segs = []
            if len(valleys) == 1:
                segs = [(0, len(rows) - 1, valleys[0])]
            elif len(valleys) >= 2:
                cuts = []
                for a, b in zip(valleys, valleys[1:]):
                    _seg = ms[a:b + 1]
                    _mx = max(_seg)
                    _cand = [a + i for i, v in enumerate(_seg) if v == _mx]
                    if len(_cand) == 1:
                        cuts.append(_cand[0])
                    else:
                        # 并列：两箱的等距层（如 5F/14F 装配的 9F 与 10F，米数同为 40）。
                        # 取靠近区间中点者，使两侧覆盖层数均衡 —— 与设计表一致
                        # （5F/14F→9/10 即此情形；若不处理并列会误得 10/11）。
                        _mid = (a + b) / 2.0
                        cuts.append(min(_cand, key=lambda j: (abs(j - _mid), -j)))
                starts = [0] + cuts
                ends = [c - 1 for c in cuts] + [len(rows) - 1]
                segs = [(s0, s1, v) for (s0, s1), v in zip(zip(starts, ends), valleys)]

            # V 形单调性自检（**限制在本段内**：谷底左侧应递减、右侧应递增。
            # 双箱列若跨过下一段谷底会比较出假告警，故必须先分段）
            for (_s0, _s1, _vi) in segs:
                _seg = ms[_s0:_s1 + 1]
                _k = _vi - _s0
                _l = _seg[:_k + 1]
                _r = _seg[_k:]
                mono_l = all(_l[t] >= _l[t + 1] for t in range(len(_l) - 1))
                mono_r = all(_r[t] <= _r[t + 1] for t in range(len(_r) - 1))
                result['自检_v形单调性'].append({
                    '楼栋': bkey, '单元': '%d单元' % (ui + 1), '段行区间': [_s0, _s1],
                    '谷底行': _vi, '谷底米数': ms[_vi],
                    '左侧单调递减': mono_l, '右侧单调递增': mono_r,
                    '结论': 'OK' if (mono_l and mono_r) else '告警：段内不呈标准V形'})

            uboxes = sorted([_b for _i, _b in enumerate(boxes) if _box_owner[_i] == ui],
                            key=lambda b: -b[1])

            all_floor_names = [f[2] for f in col_f]

            unit = {'米数列x': round(ccx, 1), '楼层列x': round(fcx, 1),
                    '分纤箱': [], '米数表': [], 'v谷底行索引': valleys,
                    '户数标注': [{'y': round(h[1], 1), '值': h[2]} for h in col_h]}

            # 2026-09-16（P0-12/凤鸣朝阳）：记录"有户数标注的楼层集合" ——
            # 覆盖完整性门禁的期望值。户数标注（X户）每层一条，就近配对楼层线；
            # 该集合 = 单元内**实际有住户**的楼层，覆盖楼层并集必须与它一致。
            # 根因：8#楼 FL08-FX02 曾因窗口截断漏 17F/18F，而自检只查 V 形
            #   单调性（0 告警），漏层静默通过 —— 门禁用独立来源（户数标注）
            #   交叉校验覆盖结果，缺层必报。
            _hu_floors = set()
            if col_h and col_f:
                _hu_ytol = max(_ytol, _base * 1.5) if _d else args.y_tol
                for _hx, _hy, _hs in col_h:
                    _hnear = min(col_f, key=lambda f: abs(f[1] - _hy))
                    if _hnear and abs(_hnear[1] - _hy) <= _hu_ytol:
                        _hu_floors.add(_hnear[2])
            unit['户数楼层集合'] = sorted(_hu_floors, key=fl_num)

            for r in rows:
                unit['米数表'].append({'楼层': r['楼层'], 'y': round(r['y'], 1),
                                       '米数': r['米数'], '根数': r['根数'],
                                       '楼层线残差': r['残差']})

            seg_meta = []
            for si, (s0, s1, vi) in enumerate(segs):
                body = rows[s0:s1 + 1]
                names = [r['楼层'] for r in body if r['楼层']]
                if not names:
                    continue
                # 2026-09-12 确立：V型计算的数据来源是米数列标注，
                # 覆盖范围的每一项都必须来自米数列实际存在的行（SKILL.md 原则三：
                # 所有结果都要说明测量过程和数据来源）。
                # 旧实现把全局最低段下方的地下层（楼层列里有、米数列里没有）
                # 并入覆盖下界，结果中出现了米数列数据来源无法支撑的楼层。
                # 地下层是否有住户由 parse 阶段楼层表的户数字段决定，与覆盖判定无关；
                # 地下层无住户时不出行、不影响出表。需要地下层覆盖时可加
                # --include-basement 参数（见下方参数定义）。
                extra = []
                if args.include_basement:
                    seg_min_y = min(r['y'] for r in body)
                    is_lowest = seg_min_y <= min(r['y'] for r in rows) + 1e-6
                    if is_lowest:
                        extra = sorted({nm for nm in all_floor_names
                                        if fl_num(nm) < 0 and fl_num(nm) < fl_num(names[-1])}, key=fl_num)
                cover = sorted(set(extra + names), key=fl_num)
                seg_meta.append({'段序': si, '行区间': [s0, s1], '谷底行': vi,
                                 'v底楼层': rows[vi]['楼层'], 'v底米数': rows[vi]['米数'],
                                 'v底y': round(rows[vi]['y'], 1), '覆盖楼层': cover,
                                 '并入地下层': extra})

            for si, sm in enumerate(seg_meta):
                if si >= len(uboxes):
                    result['需人工裁决'].append({
                        '对象': '%s %d单元' % (bkey, ui + 1),
                        '事项': 'V 段数多于箱数，无法配对',
                        '说明': 'V 段 %d 个 / 箱 %d 个' % (len(seg_meta), len(uboxes))})
                    break
                bx = uboxes[si]
                dev = round(abs(bx[1] - sm['v底y']), 1)
                unit['分纤箱'].append({
                    '编号': bx[2],
                    '安装楼层': sm['v底楼层'],
                    '安装楼层口径': '皮线V形谷底（区间法测谷底行所在层带）',
                    '覆盖范围线索': {
                        '覆盖楼层': sm['覆盖楼层'],
                        '性质': '线索（V形法：皮线米数谷底，已与箱符号y交叉验证）',
                    },
                    '判定依据': 'V形计算',
                    '依据来源': '文字图层 %s，米数列 x≈%.1f，窗口 x∈[%.1f, %.1f]'
                                % ('/'.join(sorted(layers)), ccx, lo, hi),
                    '证据': {
                        'v谷底行索引': sm['谷底行'],
                        'v谷底米数': sm['v底米数'],
                        'v谷底y': sm['v底y'],
                        '箱符号x': round(bx[0], 1),
                        '箱符号y': round(bx[1], 1),
                        'v底与箱符号偏差': dev,
                        'V段行区间': sm['行区间'],
                        '段内米数序列': [rows[k]['米数'] for k in range(sm['行区间'][0], sm['行区间'][1] + 1)],
                    },
                })
                result['自检_v底vs箱符号'].append({
                    '楼栋': bkey, '单元': '%d单元' % (ui + 1), '箱号': bx[2],
                    '安装楼层': sm['v底楼层'], 'v底y': sm['v底y'],
                    '箱符号y': round(bx[1], 1), '偏差': dev})

            # 自检：覆盖范围的每一项都必须来自米数列实际存在的行。
            # 根因：旧实现把地下层并入覆盖但自检全过，因为自检只校验V形质量，
            # 没校验结果是否都有米数列标注的数据来源（SKILL.md 原则三）。
            # 此校验：覆盖范围里每个楼层都能在米数列找到对应行（--include-basement 时放宽）
            if not args.include_basement:
                input_floors = {r['楼层'] for r in rows if r['楼层']}
                for sm in seg_meta:
                    for fl in sm['覆盖楼层']:
                        if fl not in input_floors:
                            result['需人工裁决'].append({
                                '对象': '%s %d单元' % (bkey, ui + 1),
                                '事项': '覆盖范围超出米数列数据范围',
                                '说明': '楼层 %s 在米数列无对应标注行，本方法结果中不得出现（见 coverage_rules.md「V型计算」）' % fl})

            if len(seg_meta) != len(uboxes):
                result['需人工裁决'].append({
                    '对象': '%s %d单元' % (bkey, ui + 1),
                    '事项': 'V段数与箱数不一致',
                    '说明': 'V段 %d 个（谷底 %s）/ 箱 %d 个（%s）'
                            % (len(seg_meta), [s['v底楼层'] for s in seg_meta],
                               len(uboxes), [b[2] for b in uboxes])})

            binfo['单元']['%d单元' % (ui + 1)] = unit

        result['楼栋'][bkey] = binfo

    # ---------- 米数格式门禁（2026-09-13，P0-2）----------
    # 「匹配到标注但一条都解析不出」= 正则与图面字段序不合，必须硬失败，
    #   不得整轮空转后返回 0 —— 旧版此处会抛 IndexError 或静默跑完。
    if _fmt_bad and _fmt_ok == 0:
        log.error('皮线米数标注匹配到 %d 条，但**一条都解析不出米数/根数** —— '
                  '**已按失败退出（码 2）**。\n'
                  '  样本：%s\n'
                  '  当前 --cable-pattern = %r\n'
                  '  若标注形如 `2Px2芯x36m`（米数在后），请显式指定组号，例如\n'
                  '    --cable-pattern "(\\d+)Px(\\d+)芯x(\\d+)m" '
                  '--cable-meters-group 3 --cable-count-group 1',
                  len(_fmt_bad),
                  '；'.join(repr(s) for s, _ in _fmt_bad[:5]),
                  args.cable_pattern)
        sys.exit(2)
    if _fmt_bad:
        log.warning('有 %d 条米数标注解析失败（已跳过），样本：%s',
                    len(_fmt_bad), '；'.join(repr(s) for s, _ in _fmt_bad[:3]))

    # ---------- 楼栋作业门禁（2026-09-13，P0-3）----------
    # 整轮无产出不得返回 0，否则调用方会把"没跑出来"当成"跑出来了"。
    _ok_blds = [b for b, bd in result['楼栋'].items() if bd.get('单元')]
    if not _ok_blds:
        log.error('本次运行未产出任何楼栋的覆盖结果（楼栋 %d 个，全部无可用米数列）—— '
                  '**已按失败退出（码 2）**。最常见原因：--cable-pattern 与图上米数写法不符，'
                  '或 --text-layer 未覆盖米数标注所在图层。', len(result['楼栋']))
        sys.exit(2)

    # ---- 自检：覆盖完整性门禁（2026-09-16，P0-12/凤鸣朝阳）----
    # 每个单元：全部箱的「覆盖楼层」并集，必须等于「有户数标注的楼层集合」。
    # 根因：凤鸣朝阳 8#楼曾因窗口截断漏 17F/18F（FL08-FX02 只覆盖到 16F），
    #   而既有自检只查 V 形单调性 + V底vs箱符号偏差（均 0 告警），漏层静默通过；
    #   门禁用**独立来源**（户数标注 X户）交叉校验覆盖结果，缺层必报。
    _cov_missing = []      # (楼栋, 单元, 缺失楼层列表, 覆盖并集)
    for _bk, _bv in result['楼栋'].items():
        for _un, _uv in _bv['单元'].items():
            _covered = set()
            for _bx in _uv.get('分纤箱', []):
                _covered.update(_bx['覆盖范围线索']['覆盖楼层'])
            _hu_expected = set(_uv.get('户数楼层集合', []))
            if not _hu_expected:
                continue    # 本单元无户数标注（无法建期望），跳过
            _miss = sorted(_hu_expected - _covered, key=fl_num)
            if _miss:
                _cov_missing.append((_bk, _un, _miss,
                                     sorted(_covered, key=fl_num)))

    if _cov_missing:
        print('\n自检 · 覆盖完整性: 发现 %d 个单元覆盖缺层！' % len(_cov_missing))
        for _bk, _un, _miss, _covered in _cov_missing:
            print('   ! %s %s 缺失楼层 %s（覆盖并集 %s）'
                  % (_bk, _un,
                     '/'.join(_miss),
                     '/'.join(_covered) if len(_covered) <= 12
                     else '%s...%s(%d层)' % (_covered[0], _covered[-1], len(_covered))))
            result['需人工裁决'].append({
                '对象': '%s %s' % (_bk, _un),
                '事项': '覆盖范围缺失楼层 %s（V形法结果与户数标注不符）'
                        % '/'.join(_miss),
                '说明': '覆盖并集 %s；户数标注楼层 %s。'
                        '请检查窗口边界/米数列是否被截断（参考凤鸣朝阳 8#楼 P0-12 修复）。'
                        % ('/'.join(_covered) if len(_covered) <= 8
                           else '%s...%s(%d层)' % (_covered[0], _covered[-1], len(_covered)),
                           '/'.join(sorted(_hu_expected, key=fl_num)))})

    # ---- 自检：偏差可信门禁（2026-09-16，12坑复核·坑7）----
    #   阈值 = --dev-gate-factor × 层高（尺度无关，禁用绝对坐标值）。
    #   超阈 → 登记需人工裁决 + 自检_偏差门禁标「不可信」；不自动改判、不阻止出表
    #   （裁决权在人，见 SKILL.md 原则二）。
    _dev_gate = (args.dev_gate_factor * _fl_step) if _fl_step else None
    if _dev_gate:
        _untrusted = [x for x in result['自检_v底vs箱符号'] if x['偏差'] > _dev_gate]
        for x in _untrusted:
            result['需人工裁决'].append({
                '对象': '%s %s %s' % (x['楼栋'], x['单元'], x['箱号']),
                '事项': 'v底与箱符号偏差 %.1f 超过 %.4g（%.1f×层高），安装层判定不可信'
                        % (x['偏差'], _dev_gate, args.dev_gate_factor),
                '说明': '跨地块/跨图幅数据混入的典型症状；请核对分带边界与单元配对后重跑。'})
        result['自检_偏差门禁'] = {'阈值': round(_dev_gate, 1), '系数x层高': args.dev_gate_factor,
                                '超阈项': len(_untrusted),
                                '结论': ('不可信-需人工复核' if _untrusted else '可信')}
    else:
        result['自检_偏差门禁'] = {'结论': '未启用（本图量不出层高锚）'}

    # ---- 自检：箱位直读标注交叉校验（2026-09-16，12坑复核·坑9）----
    #   「N号楼M单元K层」直读标注是安装层最可靠的独立第二来源。
    #   V型谷底判定层与标注层不一致 → 并列证据交人裁定（两侧都不自动优先）。
    if args.fx_locations:
        import json as _json
        try:
            with open(args.fx_locations, 'r', encoding='utf-8') as _fp:
                _fxl = _json.load(_fp)
        except Exception as _ex:                                        # noqa: BLE001
            log.error("无法读取 --fx-locations %s: %s", args.fx_locations, _ex)
            sys.exit(1)
        _loc_idx = {}
        for _e in _fxl.get('唯一箱位') or []:
            _loc_idx.setdefault((_e['楼栋'], _e['单元']), set()).add(_e['安装层'])
        _xchk = {'来源': args.fx_locations, '比对总数': 0, '一致': 0, '不一致': 0,
                 '无标注可校验': 0, '共享组跳过': 0,
                 '标注侧唯一箱位数': len(_fxl.get('唯一箱位') or []),
                 '键未识别未比对': [], '楼栋键区间歧义': []}
        result['自检_箱位直读标注交叉校验'] = _xchk
        for _bk, _b in (result['楼栋'] or {}).items():
            # 楼号一律走共享入口 parse_bldg_nums_ex（覆盖 `N#楼` / `N号楼` / `N#配套楼`
            # / `N-M号楼` / `[共享]…` 等写法），**不再自造正则** —— 本脚本此前用
            # `re.match(r'(\d+)#楼', _bk)` 只认一种写法，共享标题与配套楼被静默丢弃。
            _bnos, _bamb = parse_bldg_nums_ex(_bk,
                                              expand_ranges=ftth_common.EXPAND_BLDG_RANGES)
            if not _bnos:
                # 键形态认不出 ⇒ **显式登记**。旧实现在此直接 continue，
                # 于是「一个都没比」被打印成「自检·交叉校验」而过关。
                if any((u.get('分纤箱') or []) for u in (_b.get('单元') or {}).values()):
                    _xchk['共享组跳过'] += 1
                _xchk['键未识别未比对'].append(str(_bk))
                continue
            if _bamb:
                # `N-M号楼` 连字符写法语义存疑（并列 vs 区间），**不得静默择一**：
                # 按全局开关的字面值参与比对，并把歧义显式登记；用户确认后加
                # --expand-bldg-ranges 才按区间展开 —— 与 parse/count 同口径。
                _xchk['楼栋键区间歧义'].append({
                    '键': str(_bk), '按字面取楼号': _bnos,
                    '说明': '连字符写法语义存疑；未展开区间时中间楼栋不参与本项比对，'
                            '须用户确认后加 --expand-bldg-ranges 重跑'})
            for _uk, _u in (_b.get('单元') or {}).items():
                _uno = unit_no_from_key(_uk)
                if _uno is None:
                    _xchk['键未识别未比对'].append('%s/%s' % (_bk, _uk))
                    continue
                _ann = set()
                for _bno in _bnos:
                    _ann |= _loc_idx.get((_bno, _uno), set())
                for _bx in (_u.get('分纤箱') or []):
                    _vf = fl_num(_bx.get('安装楼层') or '')
                    if _vf is None:
                        continue
                    _xchk['比对总数'] += 1
                    _bx.setdefault('证据', {})['直读标注安装层'] = sorted(_ann) if _ann else None
                    if not _ann:
                        _xchk['无标注可校验'] += 1
                    elif _vf in _ann:
                        _xchk['一致'] += 1
                    else:
                        _xchk['不一致'] += 1
                        result['需人工裁决'].append({
                            '对象': '%s %s %s' % (_bk, _uk, _bx['编号']),
                            '事项': '安装层两来源不一致：V型谷底判 %s，直读标注为 %s'
                                    % (_bx.get('安装楼层'), '/'.join('%dF' % a2 for a2 in sorted(_ann))),
                            '说明': '两来源并列证据，均不自动优先——请对照原图裁定'
                                    '（直读标注可能笔误，V型谷底可能分带/配对错位）。'})
        print('自检 · 箱位直读标注交叉校验: 标注侧箱位 %d 个；本次比对 %d 项，一致 %d，'
              '不一致 %d，无标注 %d，共享组跳过 %d'
              % (_xchk['标注侧唯一箱位数'], _xchk['比对总数'], _xchk['一致'],
                 _xchk['不一致'], _xchk['无标注可校验'], _xchk['共享组跳过']))
        if _xchk['键未识别未比对']:
            print('  ! 有 %d 个楼栋/单元键形态未识别 ⇒ **本次未参与比对**（≠ 已核过）：%s'
                  % (len(_xchk['键未识别未比对']),
                     '、'.join(_xchk['键未识别未比对'][:8])
                     + ('…' if len(_xchk['键未识别未比对']) > 8 else '')))
        if _xchk['比对总数'] == 0 and _xchk['标注侧唯一箱位数']:
            print('  ! 本图给了 %d 个箱位直读标注，却没有任何一项完成比对 —— '
                  '该第二来源**本轮等于未使用**，结论须照此标注'
                  % _xchk['标注侧唯一箱位数'])

    # ============================================================
    # 结果状态契约（L1-C8）产出方落地 —— 两个维度正交，只登记、不改动任何数值与归属
    # ============================================================
    # 此前本脚本**只被契约要求、自身从不产出**这两个字段 ⇒ inspect 的 C9 闸门对本来源
    # 恒判「已提供但零字段」（WARN 点名），闸门看着绿、实则这一半产物根本没核。
    #   origin：安装层与覆盖层都是**推算**（V 形谷底 + 区间法对位）⇒ derived；
    #           配对不上 / 无谷底 / 覆盖为空 ⇒ unresolved。
    #   confirmation：本单元在「需人工裁决」中有条目、或偏差门禁判「不可信」⇒ pending
    #           （待裁决，禁止进成品，由 C9 拦下）；否则 settled。
    #           口径与 parse 侧一致：有客观依据（自检通过、几何归属成立）即可定案。
    # ---- 待裁决清单去重（2026-09-18 实跑修复，P1）----
    #   同一 (对象, 事项) 会在多个判据分支下被重复 append：实测某图 18 项里有 8 项
    #   是同一句话的复制（「V 段数多于箱数」与「V段数与箱数不一致」各出现两遍）。
    #   重复项不改变数值，但把「待裁决 N 项」虚高、稀释人工注意力，也让人误以为
    #   有更多独立疑点。按内容 key 保序去重（不排序 —— 保持判据产出顺序可追溯）。
    _raw_pend = result.get('需人工裁决') or []
    _seen_pend = set()
    _dedup = []
    for _x in _raw_pend:
        _k = json.dumps(_x, ensure_ascii=False, sort_keys=True)
        if _k in _seen_pend:
            continue
        _seen_pend.add(_k)
        _dedup.append(_x)
    result['需人工裁决'] = _dedup
    if len(_dedup) != len(_raw_pend):
        print('  · 待裁决清单去重：%d → %d 项（重复项已合并）' % (len(_raw_pend), len(_dedup)))

    _dg_concl = (result.get('自检_偏差门禁') or {}).get('结论')
    _dg_ok = (_dg_concl == '可信')
    # 裁决项的作用范围一律走共享口径 ftth_common.judge_pending_scope（与竖线法同源）。
    #   本脚本此前用**子串包含** `(_bk in _o and _uk in _o)` 判，两处会错（实测）：
    #   ① 楼栋名形态不同即失配 —— `"4#楼" in "4#配套楼/FX22#"` 为 False
    #      ⇒ 裁决项关联不上、被静默放行；
    #   ② 子串跨号误伤 —— `7#楼` 是 `17#楼` 的子串 ⇒ 邻栋问题算到本栋头上。
    #   并**不判决 `阻塞: false` 的条目**：那是脚本已自行处置完毕的可见性登记
    #   （如『疑似跨图带连续体（已排除）』），不构成「结论待裁决」。
    _pend_items = pending_items_from_rulings(result.get('需人工裁决'))
    _st_settled = _st_pending = 0
    for _bk, _bv in (result.get('楼栋') or {}).items():
        for _uk, _uv in (_bv.get('单元') or {}).items():
            _unit_pend = (not _dg_ok) or any(
                judge_pending_scope(_objs, _uk, None, _bk)[0]
                for _objs, _blk in _pend_items if _blk)
            for _bx in (_uv.get('分纤箱') or []):
                _cov = (_bx.get('覆盖范围线索') or {}).get('覆盖楼层') or []
                _bx['result_origin'] = 'derived' if (_cov and _bx.get('安装楼层')) else 'unresolved'
                _box_pend = any(judge_pending_scope(_objs, _uk, _bx.get('编号'), _bk)[1]
                                for _objs, _blk in _pend_items if _blk)
                _bx['result_confirmation'] = ('pending'
                                              if (_unit_pend or _box_pend
                                                  or _bx['result_origin'] == 'unresolved')
                                              else 'settled')
                _src = str(_bx.get('依据来源') or '')
                if not _src.startswith('E-DXF-'):
                    _bx['依据来源'] = 'E-DXF-TEXT:' + _src
                if _bx['result_confirmation'] == 'settled':
                    _st_settled += 1
                else:
                    _st_pending += 1
    result['结果状态说明'] = {
        # 键名刻意**不复用** result_origin / result_confirmation：inspect 的 C9 闸门按
        # 「键存在即结果项」机械扫描，说明性文字若挂在同名键上会被当成一条已定案结果
        # （实测：加本说明后 C9 计数由 34 变 35，多出来的正是这条说明）。
        'origin 取值含义': 'measured=图上直读/几何测量；derived=按规则算出（V型谷底+区间法对位）；unresolved=无解',
        'confirmation 取值含义': 'settled=可进成品；pending=待裁决、禁止进成品（inspect C9 拦下）',
        '统计': {'settled': _st_settled, 'pending': _st_pending},
        '判 pending 的条件': '本单元出现在「需人工裁决」中（**不含带 `阻塞: false` 的'
                          '已排除项**），或自检_偏差门禁结论非「可信」',
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as fp:
        json.dump(result, fp, ensure_ascii=False, indent=1)

    # ---- 控制台摘要 ----
    print('✓ V形法完成：楼栋 %d 个' % len(windows))
    print('%-8s %-8s %-14s %-8s %-30s %s' % ('楼栋', '单元', '箱号', '安装层', '覆盖楼层', 'V底vs箱符号'))
    for bkey, b in result['楼栋'].items():
        for un, u in b['单元'].items():
            for bx in u['分纤箱']:
                cov = bx['覆盖范围线索']['覆盖楼层']
                covs = '/'.join(cov) if len(cov) <= 8 else '%s ... %s (%d层)' % (cov[0], cov[-1], len(cov))
                print('%-8s %-8s %-14s %-8s %-30s %.1f' %
                      (bkey, un, bx['编号'], bx['安装楼层'], covs,
                       bx['证据']['v底与箱符号偏差']))
    _dg = result.get('自检_偏差门禁') or {}
    if _dg:
        print('自检 · 偏差可信门禁: %s' % (_dg.get('结论'),))
    devs = [x['偏差'] for x in result['自检_v底vs箱符号']]
    if devs:
        print('\n自检 · V底 vs 箱符号偏差: n=%d min=%.1f max=%.1f mean=%.2f'
              % (len(devs), min(devs), max(devs), sum(devs) / len(devs)))
    bad = [x for x in result['自检_v形单调性'] if x['结论'] != 'OK']
    print('自检 · V形单调性: %d 项，告警 %d 项' % (len(result['自检_v形单调性']), len(bad)))
    for x in bad:
        print('   ! %s %s 谷底行%d 米数%d' % (x['楼栋'], x['单元'], x['谷底行'], x['谷底米数']))
    print('需人工裁决: %d 项' % len(result['需人工裁决']))
    for x in result['需人工裁决']:
        print('   - %s：%s（%s）' % (x['对象'], x['事项'], x['说明']))


if __name__ == '__main__':
    main()
