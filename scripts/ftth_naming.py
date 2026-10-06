#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命名归一域（2026-09-26 自 ftth_common.py 抽取，P1-2）。

收拢楼栋/单元/楼层/中文数字全部写法归一入口 —— 历史上"同一判据多份实现"
漂移的重灾区（norm_* 三轮收口）。本模块只依赖 stdlib（re），禁 import
ftth_common（否则循环）；ftth_common 经 `from ftth_naming import *` re-export，
30 个脚本零改动。
全局开关 EXPAND_BLDG_RANGES 刻意留在 ftth_common（CLI 运行时状态，非命名逻辑；
跨模块 global 写会漂移，见迁移记录）。
"""

import re

__all__ = [
    'UNIT_NUM_CN',
    'UNIT_TOKEN',
    'UNIT_RE_SRC',
    'DEFAULT_FLOOR_PATTERN',
    'FLOOR_WF_VALUE',
    '_BLDG_NUM_SUFFIX_RE',
    '_BLDG_NUM_LIST_RE',
    '_UNIT_TAIL_RE',
    'RE_BLDG_MODIFIER',
    'RE_DRAWING_WORD',
    'RE_BLDG_NO',
    'CN_DIGIT',
    'clean_text',
    'parse_floor_label',
    'is_floor_text',
    'floor_mark_conflicts',
    'parse_bldg_nums_ex',
    'parse_bldg_nums',
    '_unit_seg_of',
    'parse_unit_key',
    'extract_bldg_name',
    'normalize_bldg_name',
    'bldg_num_or_none',
    'bldg_num',
    'unit_num',
    'is_bldg_level_container',
    'cn2num',
    'floor_num',
    'floor_num_or_zero',
    'norm_floor',
    'is_bldg_title_text',
    '_txt_fields',
]



# ---------- 文字清洗（统一实现，替代各脚本内联的 replace 链） ----------
def clean_text(s):
    """统一文字清洗：去全角空格 / 零宽字符 / BOM，再 strip。

    各脚本原先各自内联 `.replace("\\u3000","").replace("\\u200b","").replace("\\ufeff","")`，
    口径容易漂移，统一到这里。
    """
    return str(s).replace("\u3000", "").replace("\u200b", "").replace("\ufeff", "").strip()


# ---------- 参数校验（统一实现） ----------


# ---------- 楼层标注 ----------
DEFAULT_FLOOR_PATTERN = r"(-?\d+)F"   # 仅作 parse_floor_label 认不出时的兜底正则，不要当"标准楼层正则"使用
FLOOR_WF_VALUE = 900     # 屋面层（WF）的排序值。WF 只用于排序，不代表可住楼层

# ---------- 楼层标注统一解析（2026-09-11 修正 P0-4） ----------

def parse_floor_label(name):
    """
    把楼层标注解析为整数值，覆盖图纸上出现的全部形态。

    支持：
        '3F' / '17F' / '01F'   →  3 / 17 / 1    （类别 normal）
        '-1F' / '-2F'          → -1 / -2        （类别 normal）
        'B1' / 'B2' / 'b1'     → -1 / -2        （类别 basement，兼容 'B1层'/'B1F' 后缀）
        'WF'                   → FLOOR_WF_VALUE （类别 roof，仅排序用）
        '3层' / '十七层' → 3 / 17 （类别 normal，中文数字经 cn2num）
        '地下一层' / '负1层' / '负一层' → -1    （类别 basement）
        定稿表楼层列偶带 '室' 尾缀（如 '3层室'）——调用方剥离后再调本函数，本函数不吞该后缀。

    返回 (值, 类别)；无法识别返回 (None, None)。
    类别 ∈ {'normal', 'basement', 'roof'}

    为什么要有这个函数：旧实现仅用正则 `(-?\\d+)F` 解析楼层，对 `B1`（地下一层）
    和 `WF`（屋面层）一律返回 None，导致：
      · 楼层表把 B1 整层丢掉，B1 住户静默消失（实测：地下一层整层住户在输出中凭空消失，
        且既不报错也不进待确认清单）
      · 'B1' 无法转换为模板要求的「地下一层」
    这类丢失不报错、不进待确认清单，属于最危险的一类缺陷。

    2026-09-26（一百一十三）扩展：此前中文层（十七层）、地下/负层写法散落在
    verify_coverage_truth.norm_floor 本地实现里，与本函数同名异义、必然漂移。
    本次上收为唯一入口，各脚本一律调 floor_num，禁再自写正则。
    """
    if name is None:
        return None, None
    t = clean_text(name)
    if not t:
        return None, None
    m = re.fullmatch(r"[Bb](\d+)(?:层|F)?", t)
    if m:
        return -int(m.group(1)), "basement"
    if t.upper() == "WF":
        return FLOOR_WF_VALUE, "roof"
    m = re.fullmatch(r"(-?\d+)\s*[Ff]", t)
    if m:
        return int(m.group(1)), "normal"
    m = re.fullmatch(r"(?:地下|负)([一二三四五六七八九十\d]+)层?", t)
    if m:
        v = cn2num(m.group(1))
        return (-v, "basement") if v else (None, None)
    m = re.fullmatch(r"([一二三四五六七八九十\d]+)层", t)
    if m:
        v = cn2num(m.group(1))
        return (v, "normal") if v else (None, None)
    m = re.fullmatch(r"(-?\d+)层", t)
    if m:
        return int(m.group(1)), "normal"
    return None, None

def is_floor_text(s, floor_re=None):
    """楼层标注判定（统一实现，替代各脚本重复定义的 `_is_floor_text`）。

    先走 parse_floor_label（支持 3F/17F/-1F/B1/B2/WF）；
    显式传入 floor_re 时，额外兼容该正则的写法。
    """
    if parse_floor_label(s)[0] is not None:
        return True
    if floor_re is not None:
        return bool(floor_re.fullmatch(clean_text(s)))
    return False

def floor_mark_conflicts(items, y_tol=0.001, max_report=5):
    """检查一组「楼层标注」的自洽性，返回冲突描述列表（无冲突返回 []）。

    适用面：凡"把某区域内的楼层标注收成 楼层名→y 表"的环节，都应在**建表时**
    先跑一遍本检查——防止同形的非楼层文字被静默并入楼层表。

    两条判据都是与项目无关的通用几何事实：

    ① **同名多址**：同一个楼层名出现在两个以上不同标高。同一区域内一个楼层
       只应有一条楼层线；出现多址即说明这组标注混入了非楼层文字。
       旧实现写成 `floor_marks[txt] = y`（字典覆盖），多址会被**静默合并成一条**，
       既不报错也不进待确认清单 —— 属最危险的一类缺陷。故本检查必须喂
       **未去重**的原始标注列表，喂去重后的字典等于没检查。
    ② **次序倒挂**：按 y 升序排列后，楼层数值须单调不减。出现倒挂说明混入了
       不属于本区域楼层序列的标注。

    典型命中场景（与文字写法无关）：路由/端子图上以 `B1`…`B9` 标端口，与
    `parse_floor_label` 认可的地下层写法 `B<数字>` **同形**，被一并收进楼层表，
    实测会把分纤箱归到不存在的 `B9` 层。

    参数:
        items      : [(楼层名, y), ...] —— **未去重**的原始标注
        y_tol      : 判定"同一个标高"的容差（图纸单位，默认 0.001）
        max_report : 每类冲突最多报几条（防止噪声淹没日志）

    返回:
        [描述字符串, ...]
    """
    out = []
    if not items:
        return out

    # ① 同名多址
    grouped = {}
    for name, y in items:
        grouped.setdefault(clean_text(name), []).append(y)
    _n_dup = 0
    for name in sorted(grouped):
        uniq = []
        for y in sorted(grouped[name]):
            if not uniq or abs(y - uniq[-1]) > y_tol:
                uniq.append(y)
        if len(uniq) > 1:
            _n_dup += 1
            if _n_dup <= max_report:
                out.append("楼层名「%s」在本区域出现 %d 处不同标高（y=%s）—— 同一区域"
                           "一个楼层只应有一条楼层线，疑似混入了同形的非楼层文字"
                           "（如端口标号 B1~B9）"
                           % (name, len(uniq), "、".join(str(round(v, 1)) for v in uniq)))
    if _n_dup > max_report:
        out.append("（同上，另有 %d 个楼层名存在多址，已省略）" % (_n_dup - max_report))

    # ② 次序倒挂
    seq = []
    for name, y in sorted(items, key=lambda p: p[1]):
        v, _cat = parse_floor_label(name)
        if v is not None:
            seq.append((y, clean_text(name), v))
    _n_rev, _prev_v, _prev_n = 0, None, None
    for y, name, v in seq:
        if _prev_v is not None and v < _prev_v:
            _n_rev += 1
            if _n_rev <= max_report:
                out.append("楼层序列在 y=%s 处倒挂：「%s」(%d) 排在「%s」(%d) 之后，"
                           "与楼层递增次序矛盾，疑似混入了非楼层文字"
                           % (round(y, 1), name, v, _prev_n, _prev_v))
        _prev_v, _prev_n = v, name
    if _n_rev > max_report:
        out.append("（同上，另有 %d 处次序倒挂，已省略）" % (_n_rev - max_report))

    return out


# ---------- 楼栋号解析 ----------
# ---------- 楼栋锚点提取 ----------
# 楼栋号书写形态（2026-09-13 统一入口；禁止各脚本再内联写楼号正则）
#   A 后缀重复式：`1#、2#、3#住宅` / `1#2#3#楼` / `1号楼` / `1#楼`
#   B 前缀共享式：`3/6号楼` / `3、6号楼` / `3#6#楼`（仅末号带「楼」字）
# 真实教训：某项目 12 条系统图标题本应展开 10 栋，旧写法只认 `N#、N#`
#   与 `N#N#`，对 `3/6号楼` 只取到 6 号楼 → 2/3/8/10/12 五栋静默丢失。
# 注意：这里**不能**加 `(?!\d)` 负向断言。`(\d+)` 已经贪婪吃掉多位数字，
#   而 `1#2#3#楼` 这种"号紧跟号"的写法恰恰需要逐号命中；
#   加上 `(?!\d)` 会把 `1#`(后随 2)、`2#`(后随 3) 全部排除，只剩 `3#` → 丢 2 栋。

_BLDG_NUM_SUFFIX_RE = re.compile(r"(\d+)\s*[#号]")
_BLDG_NUM_LIST_RE = re.compile(r"((?:\d+\s*[/、,，\-]\s*)+\d+)\s*[#号]?\s*楼")

def parse_bldg_nums_ex(text, expand_ranges=False):
    """解析楼栋号并标记歧义。返回 (nums, ambiguous)。

    nums:      int 列表，**按原文出现位置**排序去重（顺序即图面顺序）
    ambiguous: True 表示命中 `N-M号楼` 连字符写法——它既可能是「N 号与 M 号」，
               也可能是区间「N~M」（如 `3-6号楼` = 3 至 6 号共 4 栋）。
               语义无法由文字本身判定，调用方**必须**据此列入「需人工裁决」，
               不得静默按其中一种语义处理。
    expand_ranges: 当 True 且 ambiguous=True 时，将 `N-M` 按**区间**展开为
               [N, N+1, ..., M]。调用方须在**用户确认**区间语义后才能传 True。
               默认 False 保持原有行为（仅取字面数字，不展开中间值）。

    规则：
      · 后缀重复式 `1#` `1#楼` `1号楼` `1#2#3#楼` `1#、2#、3#住宅`
      · 前缀共享式 `3/6号楼` `3、6号楼` `3#6#楼` `1/2/3号楼`
      · 区间式 `1-3号楼`（expand_ranges=True → [1,2,3]；False → [1,3] + ambiguous）
      · 两类结果按位置合并排序，避免"后缀式先抓到末号"导致顺序颠倒
    """
    hits = []                     # (位置, 楼号)
    ambiguous = False
    for m in _BLDG_NUM_SUFFIX_RE.finditer(text):
        hits.append((m.start(), int(m.group(1))))
    for m in _BLDG_NUM_LIST_RE.finditer(text):
        chunk = m.group(1)
        if "-" in chunk:
            ambiguous = True
        if expand_ranges and ambiguous:
            # 按 `/、,，` 拆分 chunk，对含 `-` 的子段做区间展开
            for part in re.split(r'[/、,，]', chunk):
                part = part.strip()
                rm = re.match(r'(\d+)\s*-\s*(\d+)', part)
                if rm:
                    lo, hi = int(rm.group(1)), int(rm.group(2))
                    for n in range(lo, hi + 1):
                        hits.append((m.start(), n))
                else:
                    for mm in re.finditer(r"\d+", part):
                        hits.append((m.start() + mm.start(), int(mm.group())))
        else:
            for mm in re.finditer(r"\d+", chunk):
                hits.append((m.start() + mm.start(), int(mm.group())))
    seen, out = set(), []
    for _, n in sorted(hits):
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out, ambiguous


# ---------- 全局开关：楼栋区间标题是否按「区间」语义展开 ----------
# `N-M号楼` 既可能是「N 号与 M 号并列」，也可能是区间「N~M」，文字本身无法判定。
# 默认 False（只取字面数字，并 WARNING 待裁决）；由 CLI `--expand-bldg-ranges`
# 在**用户确认区间语义后**开启。禁止默认开启——那等于替用户静默选定语义。

def parse_bldg_nums(text, expand_ranges=False):
    """从标题/标注文字解析全部楼栋号，返回 int 列表（按图面顺序、去重）。

    覆盖写法：
      · 后缀重复式：`1#`、`1#楼`、`1号楼`、`1#、2#、3#住宅`、`1#2#3#楼`
      · 前缀共享式：`3/6号楼`、`3、6号楼`、`3#6#楼`（/ 、 , ， - 为并列分隔）
      · 区间式：`1-3号楼`（expand_ranges=True → [1,2,3]；默认 False → [1,3]）

    需要知道 `3-6号楼` 是否语义存疑时，改用 parse_bldg_nums_ex()。
    需要展开区间时传 expand_ranges=True（须用户确认区间语义后使用）。
    """
    return parse_bldg_nums_ex(text, expand_ranges=expand_ranges)[0]


# ---------- 单元归一 ----------
# ---------- 「N单元」数字写法兼容表（全技能唯一权威定义，2026-09-19 立） ----------
# 为什么必须是共享入口：实测同一张图上**两种写法并存** ——
#   · `1单元`：图签（TK-图框）、对照表、箱位直读标注 `N号楼M单元K层`；
#   · `一单元`：系统图单元轴的标注（TEL_TEXT，每个单元轴一条，y 在顶层刻度之上）。
# 病灶（实测）：各检测点各自写死 `\d+单元`，于是**只认图签那一路**，系统图自带的
#   单元划分整批落空；下游表现仅是「单元数=1 且单元名=楼栋名」，无任何告警，
#   直到 C10 把它报成「图签与系统图矛盾」——**把解析漏洞误报成图面矛盾**。
# 纪律：凡判「是否 N单元」一律引用本常量，禁止再写裸 `\d+单元`。
UNIT_NUM_CN = "0-9一二三四五六七八九十"
UNIT_TOKEN = "[%s]+" % UNIT_NUM_CN
UNIT_RE_SRC = UNIT_TOKEN + r"\s*单元"

_UNIT_TAIL_RE = re.compile(r'([0-9一二三四五六七八九十]+单元)\s*$')

def _unit_seg_of(name):
    """从名称里抽出**单元段**：`7#楼1单元`→`1单元`；`1单元`→`1单元`；`4#配套楼`→``。

    竖线法的单元名会把楼号一并带上（`7#楼1单元`），V 型法只有单元段（`1单元`）；
    两侧都归一到单元段再比，同一对象串才能对上两种命名习惯。
    """
    m = _UNIT_TAIL_RE.search(str(name or '').strip())
    return m.group(1) if m else ''

def parse_unit_key(text, expand_ranges=False):
    """「楼栋[单元]」串 → 归属键 ``(楼栋号, 单元号)``（**全技能唯一实现**，2026-09-18）。

    用途：把不同来源的楼栋/单元写法归一到**同一个可比键**，供跨来源清点使用
    （探查期「单元 × 箱清单」交叉清点即第一个消费者）。两侧命名习惯实测并存：
      · 箱位直读标注 ``N号楼M单元K层``（extract_fx_locations，楼号/单元号已分开存字段）；
      · 对照表 ``N#楼M单元``（extract_fx_map 的 `单元` 字段，楼号与单元号**紧贴无分隔**）；
      · 图签证据坐标 ``M单元``（只有单元段，楼栋由所在键给出）。

    实现**必须复用**既有解析器，不得另写正则（本技能已因「同一逻辑多份实现」漂移过多次）：
      · 楼号走 :func:`parse_bldg_nums_ex`（覆盖 `N#楼` / `N号楼` / `N#配套楼` / 共享标题）；
      · 单元号取串尾 `N单元`（``_UNIT_TAIL_RE``），中文数字走 :func:`cn2num`。

    返回 ``(楼栋号, 单元号)``；**无法判定的一位返回 None，不得用 0 冒充** ——
    0 会与真实楼号/单元号 0 混淆，把「没解析出来」伪装成「解析成 0 号」。

    注意：多楼号共享标题（``[共享]1-3号楼…``）只取**首个**楼号，其 ``ambiguous``
    由调用方按 :func:`parse_bldg_nums_ex` 自行登记待裁决 —— 不得静默取首值。
    """
    s = str(text or '').strip()
    if not s:
        return None, None
    nums, _amb = parse_bldg_nums_ex(s, expand_ranges=expand_ranges)
    m = _UNIT_TAIL_RE.search(s)
    u = cn2num(m.group(1)[:-2]) if m else None      # 去掉尾部「单元」二字
    return (nums[0] if nums else None), u

CN_DIGIT = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
            "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12,
            "十三": 13, "十四": 14, "十五": 15, "十六": 16, "十七": 17,
            "十八": 18, "十九": 19, "二十": 20, "二十一": 21, "二十二": 22}

def cn2num(s):
    """中文数字 → 整数（支持 一 / 十 / 十一 / 二十 / 二十一 …）；无法识别返回 None。

    **不得用 0 冒充失败值** —— 楼号 / 单元号 / 层号里 0 与「解析失败」语义完全不同；
    失败一律 None，由调用方决定是否登记「未识别」。
    """
    s = str(s or "").strip()
    if not s:
        return None
    if s in CN_DIGIT:
        return CN_DIGIT[s]
    m = re.fullmatch(r"([一二三四五六七八九])?十([一二三四五六七八九])?", s)
    if m:
        return (CN_DIGIT[m.group(1)] if m.group(1) else 1) * 10 + \
               (CN_DIGIT[m.group(2)] if m.group(2) else 0)
    if re.fullmatch(r"\d+", s):
        return int(s)
    return None

def unit_num(text):
    """从「N单元」写法里取单元号（int），取不到返回 None —— **全技能唯一实现**。

    接受 `1单元` / `一单元` / `十一单元` / `1#楼2单元` / `7#楼一单元`；
    也接受**整串就是一个号码**的来源（`1` / `一`）—— 实测箱位直读证据
    （`fx_locations.json`）与对照表的「单元」字段就是 int，图上写法则带「单元」二字，
    两种都必须能取号，否则箱按单元号归位时会整批落到楼栋级容器（实测踩中）。

    纪律：**不得用 0 冒充失败值** —— 单元号 0 与「没解析出来」语义不同，失败一律 None。
    """
    s = str(text or "").strip()
    if not s:
        return None
    m = _UNIT_TAIL_RE.search(s)
    if m:
        return cn2num(m.group(1)[:-2])      # 去掉尾部「单元」二字
    return cn2num(s)                        # 纯号码来源；混合串（`1号楼`）由 cn2num 返 None


# ---------- 楼名归一 ----------
def extract_bldg_name(text):
    """从标题文字中提取楼名原文（如 '2#楼'、'2号楼'、'4#配套楼'），失败回退 None。

    2026-09-12 修正（P1-18）：旧正则要求「数字+# + 楼」连续出现，
      但 `N#配套光纤入户系统图` 中 `#` 和 `楼` 之间插了「配套」→匹配失败→回退为 `N#楼`，
      丢失「配套楼」标识，导致下游按楼名 join 时与平面图的 `N#楼` 同名不同物串行。
      新正则允许 `#` 和 `楼` 之间出现「配套」「商业」「附属」等修饰词。
    2026-09-12 复核补丁（P1-18 缺口修复）：某些标题 `N#配套光纤入户系统图` 中
      修饰词后**无「楼」字**，原正则仍匹配失败。
      补充规则：`N#+修饰词`（无「楼」）也识别为配套楼名，如 `N#配套` → `N#配套楼`。
    """
    bm = re.search(r"([\d一二三四五六七八九十]+[#号](?:配套|商业|附属)?楼)", text)
    if bm:
        return bm.group(1)
    # 修饰词后无「楼」字：补「楼」构成完整楼名（如 '4#配套' → '4#配套楼'）
    bm = re.search(r"([\d一二三四五六七八九十]+[#号](?:配套|商业|附属))(?![\d一二三四五六七八九十])", text)
    if bm:
        return bm.group(1) + "楼"
    # 回退：不含修饰词的普通楼名
    bm = re.search(r"([\d一二三四五六七八九十]+[#号]?楼)", text)
    return bm.group(1) if bm else None

# 楼名修饰词（决定楼名归一后的形态，如 `4#配套楼`）。
# **只收「影响归属的楼栋类别」**（配套/商业/附属 —— 与 extract_bldg_name 保持一致）；
# 不收「住宅/综合」等用途词：它们在标题里出现但 `extract_bldg_name` 根本不捕获，
# 收进来会给同一栋楼造出第二种形态，反而制造新的重名。
RE_BLDG_MODIFIER = re.compile(r"(配套|商业|附属)")

def normalize_bldg_name(name, num):
    """楼名归一化：统一为 `N#楼`（保留「配套/商业/附属」等修饰词）。

    为什么必须归一（2026-09-15 柳辛庄实测，P1）：
      · 单楼号标题走 `extract_bldg_name` 原文 → 得到「4号楼」
      · 多楼号共享标题展开时构造 → 得到「4#楼」
      两者作为 dict key 不同，**同一栋楼会在锚点池里出现两次**、x 位置各异，
      楼栋边界被 x 中分切成两半，户数/箱体分到错误锚点。
      实测柳辛庄未归一时 14 个锚点（含 1#楼/1号楼…5 组重名），归一后 9 个。
    修饰词（配套楼/商业楼）是**真实的楼栋类别**，必须保留，不得一并抹平。
    """
    n = str(num)
    m = RE_BLDG_MODIFIER.search(name or "")
    return "%s#%s楼" % (n, m.group(1)) if m else "%s#楼" % n

def bldg_num_or_none(bldg_name):
    """从楼名提取数字（'1#楼'→1）；**失败返回 None**（不冒充 0）。

    与 :func:`bldg_num`（失败返 0 的既有语义）是同一解析的两态出口；
    需要区分「解析失败」与「真的是 0 号」时用本函数（2026-09-19 审查后统一：
    此前 inspect_closure 有一份同名但失败返 None 的本地实现，属同名异义漂移）。
    """
    m = re.search(r"(\d+)", bldg_name)
    return int(m.group(1)) if m else None

def bldg_num(bldg_name):
    """从楼名提取数字（如 '1#楼'→1, '2号楼'→2），失败返回 0。

    注意：**失败返回 0 是本函数的既有语义**（调用点众多、依赖该行为），故保留不变；
    需要区分「解析失败」时改用 :func:`bldg_num_or_none`。
    """
    n = bldg_num_or_none(bldg_name)
    return n if n is not None else 0


# ---------- 中文数字（2026-09-18 上提自 verify_coverage_truth.py，全技能唯一实现） ----------
# 上提理由：`cn2num` 原先只存在于 verify_coverage_truth.py 一个文件里，任何新脚本要用
#   就只能再抄一份 —— 「同一逻辑多份实现必然漂移，且漂移后没有任何东西会报错」是本技能
#   反复踩过的坑（判范围 / 楼号解析均已因此收口为共享实现，见 parse_unit_key）。

def is_bldg_level_container(key, bldg_name):
    """容器键是否为「**楼栋级兜底容器**」—— 全技能唯一实现。

    背景（2026-09-23 实测柳辛庄 band4）：parse 侧把箱按**单元号**注入图上已有的单元
      容器；当某箱的单元号在图上的单元轴里找不到对应容器时，会**单开一个楼栋级容器**
      承载它并登记「需人工裁决」（见 parse_dxf_structured.py 的 `_to_bldg` 分支，
      该容器与楼层表不同键是**刻意**的）。这类容器的键就是**楼栋名**（如 `3#楼`）。

    判据（客观、可复核，属测量非推理）：**取不出单元号**（unit_num → None）且
      **与楼栋同号**（bldg_num_or_none 相等）。两条同时成立才是兜底容器。

    为什么要判它：兜底容器不是图上画出的单元。把它计入「单元数」会**虚增栋级单元数**，
      实测后果是把解析缺陷**报成图面矛盾** —— band4 的 3#楼 图签与系统图都说 1 个单元
      （图签只有一格 `1单元`，格内写着 FX09+FX10），但系统图侧因这个兜底容器被数成 2，
      与图签虚增后的 2「一致」⇒ C10 看不出问题，缺陷被藏住（人工按矛盾去查图必然查不到）。
    """
    if unit_num(key) is not None:
        return False
    _kn, _bn = bldg_num_or_none(key), bldg_num_or_none(bldg_name)
    return _kn is not None and _kn == _bn

# 楼栋标题判据正则（随 is_bldg_title_text 外移；suggest_fx_symbol_layers 等经 re-export 引用）
RE_DRAWING_WORD = re.compile(r"系统图|布线图|示意图")
RE_BLDG_NO = re.compile(r"\d+\s*#|\d+\s*号楼")

def is_bldg_title_text(t):
    """判断一段文字是否为**楼栋图纸标题**（系统图 / 布线图 / 示意图）。

    通用判据 = 「图纸类词」+「楼栋号写法」；由图纸类词负责排除
    「防护分区抗爆单元示意图」这类无编号标题。
    **楼栋号后不要求紧跟『楼』** —— 实测某图整类标题写作
    「N#住宅光纤入户系统图」「N#配套光纤入户系统图」，数字后接『住宅 / 配套』；
    旧判据（要求 `数字+#+楼`）整类失配，会使「标题正则建议」与「标题图层并入
    text_layer」两道防线**同时静默失效**。放宽为「数字+#」或「数字+号楼」后两处
    同时恢复；对旧写法仍是**严格超集**，不会让原本能匹配的图纸失配。
    """
    if not t:
        return False
    return bool(RE_DRAWING_WORD.search(t) and RE_BLDG_NO.search(t))

def _txt_fields(t):
    """文字记录归一：兼容几何缓存的 [层, x, y, 内容] 与 collect_texts 的 dict。"""
    if isinstance(t, dict):
        return (t.get("层") or t.get("layer") or "", t.get("x"), t.get("y"),
                t.get("内容") or t.get("text") or "")
    try:
        return t[0], t[1], t[2], t[3]
    except Exception:
        return "", None, None, ""


# ---------- 楼层数字 ----------
def floor_num(fl_name, floor_pattern=None, use_fullmatch=False):
    """
    从楼层名提取数字（如 '3F'→3, '-1F'→-1, 'B1'→-1, 'WF'→900），失败返回 None。

    参数:
        fl_name: 楼层标注名
        floor_pattern: 楼层正则。**建议保持 None**（2026-09-11 起为默认推荐）：
                       为 None 时走统一解析 parse_floor_label，支持 B1/B2/WF；
                       显式传入时按该正则解析（向后兼容旧调用）。
        use_fullmatch: True 时用 fullmatch（严格匹配），False 时用 search（宽松匹配）

    2026-09-11 修正（P0-4）：默认路径改为 parse_floor_label，修复 B1/WF 被丢弃的问题。
    """
    if floor_pattern is None:
        v, _ = parse_floor_label(fl_name)
        if v is not None:
            return v
        if use_fullmatch:
            return None      # 严格模式：认不出就是认不出，不做模糊 search 兜底
        floor_pattern = DEFAULT_FLOOR_PATTERN
    cleaned = str(fl_name).replace("\u3000", "").replace("\u200b", "").replace("\ufeff", "").strip()
    if use_fullmatch:
        m = re.fullmatch(floor_pattern, cleaned)
    else:
        m = re.search(floor_pattern, cleaned)
    return int(m.group(1)) if m else None

def floor_num_or_zero(fl_name, floor_pattern=None, use_fullmatch=False):
    """
    floor_num 的零回退包装：提取楼层数字，失败返回 0（用于排序等场景）。
    等价于各脚本中重复定义的 楼层数字() / fl_num() / floor_num_local()。
    """
    v = floor_num(fl_name, floor_pattern, use_fullmatch=use_fullmatch)
    return v if v is not None else 0


def norm_floor(fl_name):
    """楼层名归一化 → 整数，全技能唯一实现（收敛inspect/verify双副本）。

    覆盖：B1/B2/WF/3F/-1F（经floor_num统一入口）+ 定稿表'室'尾缀 + 'N层'后缀回退。
    无法识别返回None。2026-09-27收敛inspect_closure/verify_coverage_truth双副本。
    """
    if fl_name is None:
        return None
    t = str(fl_name).replace("　", "").replace(" ", "").strip()
    t = re.sub(r"室$", "", t)
    n = floor_num(t, use_fullmatch=True)
    if n is not None:
        return n
    m = re.fullmatch(r"(-?\d+)(?:层|F)", t)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"[Bb](\d+)(?:层|F)?", t)
    if m:
        return -int(m.group(1))
    return None


# ---------- fx 聚类通用函数 ----------
