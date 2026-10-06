#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图签格组域（2026-09-26 自 ftth_common.py 抽取，P1）。

图签"格组归属"判据族（认领率闸门/偏置认领/多栋合并登记）的唯一家。
只许 import ftth_naming（归一）与 ftth_geom（几何），禁 import
ftth_common（否则循环）；ftth_common 经 `from ftth_cells import *` re-export。
"""

import re

from ftth_geom import point_rect_dist
from ftth_naming import is_bldg_title_text, unit_num

__all__ = [
    'MULTI_BLDG_LABEL_SEP',
    'collect_multi_bldg_labels',
    'collect_titleblock_unit_cells',
    'assign_cells_to_buildings',
    'filter_titleblock_units',
]



MULTI_BLDG_LABEL_SEP = "[，,、;；]|[~～]|\\d\\s*-\\s*\\d"


def collect_multi_bldg_labels(texts, bldg_re_src):
    """图签层里「一格写了多栋」的楼名（`1#楼，2#楼` / `4、6-7号楼` / `6#楼,7#楼,`）。

    **只登记、绝不解析成多个楼号**：多栋合并写法里「格内单元 ↔ 各栋」的对应关系取决于
    格内单元的画序，图上并未逐栋标注 ⇒ 属**待人工裁决**。自行拆分会把单元挂到错的楼栋。
    实测（凤鸣朝阳小区）：图签 4 行楼名全是合并写法（`1#楼，2#楼` / `3#楼，5#楼` /
    `6#楼,7#楼,` / `8#楼`），`bldg_re.fullmatch` 一条都不认 ⇒ 图签 12 个单元格零锚点 ——
    这就是格组判据在该图被误用到**系统图**单元格上的直接原因。登记出来即可让人一眼看见
    根因，不必等下游闸门报「11 条不落盘」这种离症状很远的信号。

    参数：texts=[(x, y, 文本), …]（该图签层的全部文字）；bldg_re_src=楼名正则**源码串**
    （与调用方 `--bldg-re` 必须同一份，避免两处各写一份漂移）。
    返回 [(x, y, 文本), …]，按 (y 降序, x 升序)。
    """
    if not texts:
        return []
    _re = re.compile(bldg_re_src)
    _sep = re.compile(MULTI_BLDG_LABEL_SEP)
    out = []
    for x, y, s in texts:
        if _re.fullmatch(s):
            continue
        if _re.search(s) and _sep.search(s):
            out.append((x, y, s))
    return sorted(out, key=lambda r: (-r[1], r[0]))


def collect_titleblock_unit_cells(lvu, polylines, size_rel_tol=0.02, adj_rel=0.02):
    """按图签明细表**画出来的格**，把 `N单元` 标注分组成「格组」（同栋的单元集）。

    为什么需要（2026-09-23，柳辛庄 band3 实测）：图签里的 `N单元` 是与**格子**绑定的 ——
    每个 `(楼栋, 单元)` 占一格，格内同时写着该单元的箱编号；格的归属由它在表格里的位置
    决定。而「单元到最近层户」的邻近判据无法表达这件事：同栋「单元列」相对「层户列」的
    x 偏置逐栋不同（实测 0.6k~101k），偏置一旦大于容差窗，真主就被排除、隔壁楼反而入选 ——
    实测某图 7# 的 `1单元` 被判给 4#、8# 的 `1单元` 因超窗直接落空，单元数虚低。
    格是**图上画出来的客观边界**，用它分组属**测量**，不引入任何图面含义推断。

    做法（全部由图纸自身量出，不预设坐标）：
      ① 每个标注取「最小包含它的轴对齐矩形」＝ 它所在的格；
      ② 出现的格尺寸里取**唯一主尺寸**（占比 ≥ 一半且格数 ≥2）＝「单元格尺寸」，
         其余尺寸的格不参与（多尺寸族的图不启用本判据）；
      ③ 两格**共享竖直边**（边界差 ≤ adj_rel×格宽）且 y 区间相交 ⇒ 同一格组；
      ④ 组内出现**重复单元号**或格数 > 该图单元号最大值 ⇒ 视为串标风险，该组不启用
         （把标注交回旧判据，并登记原因）。

    返回 (groups, info)：
      groups: [{'rect': (x0,x1,y0,y1), 'members': [(x,y,文本), ...]}, ...]
      info:   诊断字典（是否启用、格尺寸、落格/未落格数、弃用组与原因）。
              **「落格」= 落在单元格（主尺寸族）里**；只落在图框等非格矩形里的标注
              计 `未落格`，原始计数另存 `落入任意矩形标注数` —— 两者不得混为一谈，
              否则「没核」会被读成「已核」（实测某图 20 条里 8 条只落在图框内）。
    调用方只应把 groups 当作**归属证据**使用，并把 info 一并落进产物/日志。
    """
    import collections
    info = {"启用": False, "格尺寸": None, "落格标注数": 0, "未落格标注数": 0,
            "落入任意矩形标注数": 0, "弃用组": [], "原因": ""}
    if not lvu:
        info["原因"] = "无单元标注"
        return [], info
    rects = []
    for item in (polylines or []):
        try:
            pts = item[1]
        except (TypeError, IndexError):
            continue
        n = len(pts) // 2
        if n not in (4, 5):          # 四边形（5 点＝首尾闭合重复一点）
            continue
        xs, ys = pts[0::2], pts[1::2]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        if x1 - x0 <= 0 or y1 - y0 <= 0:
            continue
        # 轴对齐校验：每个顶点都必须落在包围盒的某一个角上（斜放的四边形不认）
        corners = {(round(x0, 3), round(y0, 3)), (round(x1, 3), round(y0, 3)),
                   (round(x1, 3), round(y1, 3)), (round(x0, 3), round(y1, 3))}
        if not {(round(xs[i], 3), round(ys[i], 3)) for i in range(n)} <= corners:
            continue
        rects.append((x0, x1, y0, y1))
    if not rects:
        info["原因"] = "几何缓存无轴对齐矩形（本判据不适用）"
        return [], info

    cell_of = {}
    for u in lvu:
        hit = [r for r in rects if r[0] <= u[0] <= r[1] and r[2] <= u[1] <= r[3]]
        if not hit:
            continue
        hit.sort(key=lambda r: (r[1] - r[0]) * (r[3] - r[2]))
        cell_of[id(u)] = hit[0]
    # 「落格」只能指**落在单元格（主尺寸族）里**，不得拿「落在任意矩形里」充数：
    #   实测某图 20 条标注里 8 条只落在 585000×430500 的**图框**内（该处根本没有单元格），
    #   旧口径报成「落格 20 / 未落格 0」，等于把「没核」呈现成「已核」。
    #   故：另存原始计数 `落入任意矩形标注数` 供诊断，「落格/未落格」在量出主尺寸族后重算。
    info["落入任意矩形标注数"] = len(cell_of)
    info["落格标注数"] = 0
    info["未落格标注数"] = len(lvu)
    if len(cell_of) < 2:
        info["原因"] = "落入矩形的标注不足 2 条，无法成组"
        return [], info

    sizes = collections.Counter((round(c[1] - c[0], 1), round(c[3] - c[2], 1))
                                for c in cell_of.values())
    (cw, ch), cn = sizes.most_common(1)[0]
    if cn < 2 or cn < 0.5 * len(cell_of):
        info["原因"] = ("格尺寸无唯一主尺寸（%s），不启用" % dict(sizes))
        return [], info
    info["格尺寸"] = [cw, ch]
    _tol_w = max(1.0, adj_rel * cw)
    _fam = {i: c for i, c in cell_of.items()
            if abs((c[1] - c[0]) - cw) <= max(1.0, size_rel_tol * cw)
            and abs((c[3] - c[2]) - ch) <= max(1.0, size_rel_tol * ch)}
    info["落格标注数"] = len(_fam)
    info["未落格标注数"] = len(lvu) - len(_fam)
    if len(_fam) < 2:
        info["原因"] = "主尺寸格不足 2 个"
        return [], info

    # 并查集：共享竖直边 + y 区间相交 ⇒ 同组
    par = {i: i for i in _fam}

    def _find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    _ids = sorted(_fam)
    for _i in range(len(_ids)):
        for _j in range(_i + 1, len(_ids)):
            a, b = _ids[_i], _ids[_j]
            ra, rb = _fam[a], _fam[b]
            _share_v = (abs(ra[1] - rb[0]) <= _tol_w) or (abs(rb[1] - ra[0]) <= _tol_w)
            _ov = min(ra[3], rb[3]) - max(ra[2], rb[2])
            if _share_v and _ov > 0.5 * min(ra[3] - ra[2], rb[3] - rb[2]):
                par[_find(a)] = _find(b)

    by_root = collections.defaultdict(list)
    for i in _fam:
        by_root[_find(i)].append(i)
    by_id = {id(u): u for u in lvu}
    groups = []
    for root, ids in sorted(by_root.items(), key=lambda kv: min(_fam[i][0] for i in kv[1])):
        members = [by_id[i] for i in ids]
        nums = [unit_num(m[2]) for m in members]
        if any(n is None for n in nums):
            info["弃用组"].append({"格": _fam[ids[0]], "原因": "组内有单元号解析不出的标注"})
            continue
        if len(set(nums)) != len(nums):
            info["弃用组"].append({"格": _fam[ids[0]],
                                   "原因": "组内单元号重复（串标风险）：%s" % nums})
            continue
        xs0 = min(_fam[i][0] for i in ids)
        xs1 = max(_fam[i][1] for i in ids)
        ys0 = min(_fam[i][2] for i in ids)
        ys1 = max(_fam[i][3] for i in ids)
        groups.append({"rect": (xs0, xs1, ys0, ys1), "members": members,
                       "单元号": nums})
    info["启用"] = bool(groups)
    if not groups:
        info["原因"] = info["原因"] or "所有格组均被弃用"
    return groups, info


def assign_cells_to_buildings(groups, anchors, cell_h=None, dominance=0.5,
                              applicability_min=0.5):
    """格组 → 楼栋归属（**楼名主导认领 + 互斥**）—— 全技能唯一实现。

    参数
      groups : `collect_titleblock_unit_cells` 的输出（每项需含 'rect' / 'members' / '单元号'）
      anchors: [(x, y, 文字, 归属键)]；归属键由调用方给出（如 `('默认', 7)`）——
               楼号解析与地块归属留在调用方，本函数不做任何文字解析。
      cell_h : 格高（尺度闸用）；None 时取各组自身高的最大值。
    返回 dict：
      'verdicts' : 逐格组裁决记录（'采信' / '不采信原因' / '最近锚点' …），供留痕与人工复核
      'owner'    : {id(标注) -> 归属键}，仅含**采信**的格组
      'blocked'  : 不采信格组的标注 id 集合 —— 调用方**不得**再把这些标注回落到
                   逐标注判据落盘（回落出来的值已被实测证伪，见下）
      'unclaimed': 楼名侧未做认领的原因清单，交人核对
      'offset_claims': **采信但无横向覆盖结构证据**的认领登记（实测偏置 + 优势倍数）。
                   调用方须与 'unclaimed' **分开呈现** —— 一个是「没认领」，一个是
                   「认领了但依据较弱，登记供复核」，混在一起会读成同一件事。
      '适用'     : False 表示**判据前提不成立**（认领率低于 `applicability_min`）——
                   此时 'owner' 为空、'blocked' 为空，调用方必须把**全部**标注交回
                   逐标注判据，并且**不得**逐组打印「不采信 / 不落盘」（那是误判范围）。
      '不适用原因': 上面那条的说明文字。

    判据（2026-09-23，柳辛庄 band1~band4 四地块实测后定稿；两步全部是图上已画边界的**测量**）：
      A. **楼名主导认领**：楼名是「行」的标签，由楼名去认领它所属的那一行 ——
         ① 优先取「**横向投影覆盖它**（x 落在格的 x 跨度内）的格组中、离它最近的一个」；
         ② 没有任何格组横向覆盖它时**不直接弃权**，改为取全体最近的格组，但加一道
            **优势闸**（`d1 ≤ dominance × 次近格`）—— 过闸才认领，并登记进 'offset_claims'。
         为什么①按 x 覆盖筛：楼名是**行头**，横向上落在本行的 x 跨度内 —— 该结构证据
         **与图形朝向无关**（不假设「楼名在上方」），比按 dy 正负判方向稳。
         为什么②不能把①当**硬**闸（柳辛庄 band2 实测）：图签里楼名会画在本行格组的
         **左边界之外一点** —— 实测 `4#楼` x 偏置 3813.2 = 格宽 118040.9 的 **3.2%**，
         两个拼版份一致（x 平移后偏置仍是 3813.5）。零容差硬闸把这一整行判死：4 条
         `N单元` 标注全部不落盘 ⇒ 图签侧该栋**单元数丢成 None**，C10 退化成「单侧不可读」
         （真实答案是 2 单元，与该栋系统图一致）。而该锚点到本行 11167.5、到次近格
         26201.1（**优势 2.35 倍**）—— 证据本身充足，是该采的。
         优势闸**只用在②这一支**：实测「楼名→本行上沿」偏移（8.6k~17.7k）会大于相邻行
         间距的一半 —— 行距 41067 时本行 17705.8、**上一行底边**只有 23361.2，永远落在
         2 倍以内（行距 86108 时同理：17706 vs 68403 的一半）。若对有覆盖的支路也施加
         优势闸，该行会被**永久**判「优势不足」（band4 的 `2#楼` 正是此值）。
         尺度闸（两支持平）：认领距离不得超过**一个格高**（超过则标签已落进别的行）。
      B. **格组定锚**：格组在**认领它的**楼名里取距离最近者。多栋争抢时要求胜者有明确
         优势（≤ `dominance` × 次近的不同栋认领者），否则**不判**、交人。
         `横向覆盖=False` 的胜者**不因此被拒**（band2 实测的 `4#楼` 就靠这一条落盘），
         只把该事实留在裁决记录里供复核。

    判据适用性闸门（同日新增，凤鸣朝阳小区实测）：
      本判据的**前提**是「每个格组所在的那一行有它的楼名锚点」。前提不成立时逐组判
      「不采信」＝把一批标注**因一个用错范围的判据丢出成品** —— 实测该小区：图签的
      楼名写成**多栋合并**（`1#楼，2#楼` / `3#楼，5#楼` / `6#楼,7#楼,` / `8#楼`），
      `bldg_re.fullmatch` 全不认 ⇒ 图签 12 个单元格**零锚点**；判据抓到的 8 个锚点实为
      **系统图内的单栋标签**（离格组 362~425、方向纯横向），全被尺度闸拦下 ⇒
      采信 1/12，其余 11 组被判「不落盘」。而该图 C10（图签 vs 系统图逐栋）实测 **PASS**，
      说明这些标注的信息另有来源、此处纯属**判据用错范围**。
      故：**认领率 < `applicability_min`（默认 0.5）⇒ 整体判不适用**（owner/blocked 置空、
      全部标注交回逐标注判据），而不是逐组弃解。实测认领率：柳辛庄 6/6、14/14、18/18、
      5/6（最低 83%）；凤鸣朝阳 1/12（8%）—— 阈值 50% 落在两者之间且远离边界。

    为什么去掉「同排共享」（同日更早一版，band3 实测后删除）：
      曾按「y 区间重叠 > 50%」把格组并入同一行，理由是拼版图各份的同一行 y 区间相同。
      但**本类图纸的图签有多列并排版式**（实测 band3：同一 y 带内并列 3 列，x≈8.15M /
      8.33M / 8.50M），同 y 带内是**不同楼栋**的行 —— 共享把 6#/7#/4# 三个楼名都并到
      同一格组，18 组里 14 组变成「多栋争抢且优势不足」（7841.8 vs 7920.4，几乎等距），
      判据整体失效（回归实测：采信 18→4）。
      而「一行画出多个格」这件事**已由 `collect_titleblock_unit_cells` 的相邻并组解决**
      （同一行的 1单元格与 2单元格共享竖边，必被并成一组），不需要额外的同排共享。

    为什么这样判（取代首版「每格各取最近楼名 + 0.5 优势闸」）：
      首版把优势闸放在「最近栋 vs **次近的不同栋**（不论它是否认领本格）」上，实测
      **判据方向反了**：拼版图里相邻行的行距（实测 86108）只有楼名偏移（17706）的
      4.9 倍，导致某一行的**邻行楼名**永远落在 2 倍以内 ⇒ 该行永被判「优势不足」。
      后果（柳辛庄 band4 实测）：① 允许**一对多** —— 缺楼名那一行的格组抢用相邻行的
      楼名，3#楼被 3 个格组同时认领、收到 `1单元×4`（编号去重后单元数仍是 2，症状被
      掩盖）；② 真正属于 2#楼的那一行反被判不采信 ⇒ 2#楼单元数丢成 None。
      改判据后 band4 逐格与「图签格内直写箱编号 → 系统图箱自证」完全一致：
      1#=2单元 / 2#=2单元 / 3#=1单元（3# 只有一格 `1单元`，格内写着 FX09+FX10），
      且 15×2×2 + 15×2×2 + 15×3×1 = 165 户，与图纸「共覆盖住户165户」吻合。

    为什么 'blocked' 必须**排除**而不是回落逐标注判据：
      band4 的 2#楼那一行（第一份拼版里漏写楼名）在首版判据下被逐标注判据判给了 3#楼，
      而格内箱编号（FX05–FX08）自证属 2#楼 —— **回落出来的值已被实测证伪**。
      把它排除后：该行内容由第二份拼版里同号的那一行给出（同样是 1单元+2单元），
      结果不变；被排除的标注逐条登记交人。取安全侧（少解可见）而非回落（错解被当已核）。
    """
    verdicts, owner, blocked, unclaimed, offset_claims = [], {}, set(), [], []
    if not groups or not anchors:
        return {"verdicts": verdicts, "owner": owner, "blocked": blocked,
                "unclaimed": unclaimed, "offset_claims": offset_claims}
    _ch = cell_h
    if not _ch:
        _ch = max((g["rect"][3] - g["rect"][2]) for g in groups)

    # A 步：楼名 → 认领的格组（优先横向投影覆盖它的最近格组；无覆盖则最近格 + 优势闸）
    claims = []
    for _x, _y, _t, _key in anchors:
        covering = [g for g in groups if g["rect"][0] <= _x <= g["rect"][1]]
        pool = covering or groups
        sc = sorted(((point_rect_dist(_x, _y, g["rect"]), g) for g in pool),
                    key=lambda z: z[0])
        d1, g1 = sc[0]
        if d1 > _ch:
            unclaimed.append(
                "%s「%s」@[%.1f,%.1f]：最近格组 x[%.1f,%.1f] y[%.1f,%.1f] 超出尺度闸"
                "（%.1f > 一个格高 %.1f）—— 不做认领"
                % (_key[0], _t, _x, _y, g1["rect"][0], g1["rect"][1],
                   g1["rect"][2], g1["rect"][3], d1, _ch))
            continue
        if not covering:
            # 无横向覆盖＝缺结构证据 ⇒ 要求距离上明显最近，否则交人（不猜）。
            _d2 = min((point_rect_dist(_x, _y, g["rect"])
                       for g in groups if g is not g1), default=None)
            if _d2 is not None and d1 > dominance * _d2:
                unclaimed.append(
                    "%s「%s」@[%.1f,%.1f]：无格组的横向跨度覆盖它，且最近格优势不足"
                    "（%.1f 未 ≤ %.2f×次近格 %.1f）—— 不做认领，交人核对"
                    % (_key[0], _t, _x, _y, d1, dominance, _d2))
                continue
            _gw = g1["rect"][1] - g1["rect"][0]
            _off = (g1["rect"][0] - _x) if _x < g1["rect"][0] else (_x - g1["rect"][1])
            offset_claims.append(
                "%s「%s」@[%.1f,%.1f]：楼名画在本行格组横向跨度之外（最近格 "
                "x[%.1f,%.1f] y[%.1f,%.1f]，x 偏置 %.1f = 格宽的 %.1f%%），按"
                "「最近格 + 优势闸（%.1f ≤ %.2f×%.1f）」认领 —— 已采信，登记供复核"
                % (_key[0], _t, _x, _y, g1["rect"][0], g1["rect"][1],
                   g1["rect"][2], g1["rect"][3], _off,
                   (100.0 * _off / _gw) if _gw else 0.0,
                   d1, dominance, (_d2 if _d2 is not None else d1)))
        claims.append({"x": _x, "y": _y, "文字": _t, "归属键": _key, "距离": d1,
                       "格组": g1, "横向覆盖": bool(covering)})

    # B 步：每个格组在认领它的楼名里取胜者
    for g in groups:
        cand = sorted([(c["距离"], c) for c in claims if c["格组"] is g],
                      key=lambda z: z[0])
        rec = {"格组矩形": [round(v, 1) for v in g["rect"]],
               "单元号": sorted(g.get("单元号") or []),
               "标注": [[round(m[0], 1), round(m[1], 1), m[2]] for m in g["members"]]}
        if not cand:
            rec.update({"最近锚点": None, "次近不同栋": None, "采信": False,
                        "不采信原因": "无楼名认领本行（图上该行未写楼名，或该楼名被"
                                  "尺度/优势闸拦下 —— 原因见调用方打印的"
                                  "「[格组·锚点]」逐条登记）—— 该行标注**不落盘**，"
                                  "交人核对"})
            verdicts.append(rec)
            blocked.update(id(m) for m in g["members"])
            continue
        d1, c1 = cand[0]
        d2 = c2 = None
        for _d, c in cand[1:]:
            if c["归属键"] != c1["归属键"]:
                d2, c2 = _d, c
                break
        rec["最近锚点"] = {"类型": "楼名", "文字": c1["文字"], "距离": round(d1, 1),
                       "归属": "%s %d号楼" % c1["归属键"]}
        rec["次近不同栋"] = (None if c2 is None else
                        {"文字": c2["文字"], "距离": round(d2, 1),
                         "归属": "%s %d号楼" % c2["归属键"]})
        rec["同格组竞争者"] = ["%s「%s」距离 %.1f" % (c["归属键"][0], c["文字"], d)
                         for d, c in cand[1:6]]
        rec["胜者横向覆盖"] = bool(c1["横向覆盖"])
        why = []
        if d2 is not None and d1 > dominance * d2:
            why.append("同格组内多栋争抢且优势不足（%.1f 未 ≤ %.2f×%.1f）"
                       % (d1, dominance, d2))
        rec["采信"] = not why
        if why:
            rec["不采信原因"] = "；".join(why) + " —— 该行标注**不落盘**，交人核对"
            verdicts.append(rec)
            blocked.update(id(m) for m in g["members"])
            continue
        verdicts.append(rec)
        for m in g["members"]:
            owner[id(m)] = c1["归属键"]
    # 判据适用性闸门（前提是「每行有它的楼名锚点」；认领率过低即前提不成立）——
    #   此时**不得逐组判「不采信」把标注丢出成品**，而要整体退出、交回逐标注判据。
    #   实测认领率：柳辛庄 6/6、14/14、18/18、5/6（最低 83%）；凤鸣朝阳小区 1/12（8%）。
    _adopted = sum(1 for _r in verdicts if _r["采信"])
    if verdicts and (_adopted / float(len(verdicts))) < applicability_min:
        _why = ("格组 %d 个中仅 %d 个能被楼名认领（%.0f%% < %.0f%%）—— 锚点与格组之间"
                "不存在结构关系，判据前提不成立 ⇒ **本图整体不适用**，全部单元标注交回"
                "逐标注判据（不在此处丢解）"
                % (len(verdicts), _adopted, 100.0 * _adopted / len(verdicts),
                   100.0 * applicability_min))
        return {"verdicts": verdicts, "owner": {}, "blocked": set(),
                "unclaimed": unclaimed, "offset_claims": offset_claims,
                "适用": False, "不适用原因": _why}
    return {"verdicts": verdicts, "owner": owner, "blocked": blocked,
            "unclaimed": unclaimed, "offset_claims": offset_claims,
            "适用": True, "不适用原因": ""}


def filter_titleblock_units(lvu, bl, lvf, gap_ratio=3.0, protected=None):
    """把「图签块内的单元标注」从全图同名标注里分出来（2026-09-18，P0）。

    为什么需要：`N单元` 这个写法在图签里有，在**系统图里也有**（每栋系统图楼层列
    顶部的单元列头），两者同图层、同写法。若不区分，单元标注会被配到错误楼栋 ——
    实测某图图签 12 个 + 系统图 11 个混在一起配对，7 栋里 5 栋单元数错，
    其中一栋收到 `1单元×6 / 2单元×5` 的重复标签，而脚本只打 ⚠、退出码仍为 0
    （下游按成功消费即得错的单元数）。

    判据（属**测量**：对图上已有距离做量化切分，不是对图纸含义的推断）：
    单元到「最近的楼名或层户」的 2D 距离 `|dx| + |dy|` 在图上常呈**明显两簇** ——
    图签块内的单元紧邻其楼名行（实测 10~30），系统图里的单元离任何楼名都有半个
    图幅远（实测 440+）。取排序后相邻距离的最大比值处切开，比值 < gap_ratio 视为
    无断层、原样返回（不切、不猜）。

    返回 (保留项, 剔除项)。**调用方必须把剔除量写进证据**，不得静默丢弃。

    protected（2026-09-23 增，柳辛庄 band3 实测）：`保护名单` = 已确认落在**图签明细表
    绘制格**内的标注 id 集合。为什么要有它：本判据只看「离楼名/层户多远」，
    而实测存在**真图签格离最近楼名 14.8 万**（同栋单元列相对层户列的 x 偏置可达 10 万），
    于是真数据被当「系统图列头」剔除 —— 表现为该栋单元数凭空少 1，下游 C10 报成
    图面矛盾。格是图上画出来的边界：**落格即属图签数据**，距离不足以推翻。
    故 protected 内的标注一律保留（不参与剔除），并请在调用方留痕。
    """
    anchors = list(bl) + list(lvf)
    if not anchors or not lvu:
        return list(lvu), []
    _prot = set(protected or ())
    dists = [min(abs(a[0] - u[0]) + abs(a[1] - u[1]) for a in anchors) for u in lvu]
    order = sorted(range(len(lvu)), key=lambda i: dists[i])
    best_i, best_ratio = None, 0.0
    for k in range(len(order) - 1):
        a, b = dists[order[k]], dists[order[k + 1]]
        if a <= 0:
            continue
        if b / a > best_ratio:
            best_ratio, best_i = b / a, k
    if best_i is None or best_ratio < gap_ratio:
        return list(lvu), []
    keep_i = set(order[:best_i + 1])
    keep = [u for i, u in enumerate(lvu) if i in keep_i or id(u) in _prot]
    drop = [u for i, u in enumerate(lvu) if i not in keep_i and id(u) not in _prot]
    return keep, drop
