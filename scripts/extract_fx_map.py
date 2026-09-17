#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTTH 分纤箱总图 FX 映射提取脚本
从 DXF 总图中提取分纤箱编号→楼栋→单元→安装楼层的映射表。

用法：
    python extract_fx_map.py <输入DXF> [输出JSON] [选项]

示例：
    python extract_fx_map.py 图纸.dxf out.json --text-layer <探查得到的图层> --fx-pattern "<探查得到的编号正则>"
    python extract_fx_map.py 图纸.dxf --probe --text-layer <探查得到的图层>

说明：
- 在指定坐标区域内搜索 FX 编号标注和楼栋/单元/楼层标注。
- 通过空间邻近关系建立 FX→楼栋→单元→楼层 映射。
- 输出 JSON 包含完整 FX 映射表，供后续逐栋解析参照。
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

from ftth_common import (
    setup_logger, load_dxf, collect_texts, cluster_by_x, assign_floor_by_interval,
    clean_text, is_floor_text, require_params,
)

log = setup_logger("extract_fx_map")

ap = argparse.ArgumentParser(description="FTTH 分纤箱总图 FX 映射提取")
ap.add_argument("dxf", help="输入DXF文件路径")
ap.add_argument("out", nargs="?", default=None, help="输出JSON路径（默认DXF同目录 _fx映射表.json）")
ap.add_argument("--probe", action="store_true", help="探查模式：列出含FX的文字样例")
ap.add_argument("--config", default=None,
                help="probe 输出的 config.json（suggested_params）；正则类参数优先从此读。"
                     "**强烈建议用它替代命令行传 --fx-pattern/--bldg-pattern/--unit-pattern**："
                     "本脚本经 ftth.cmd(cmd.exe) 调用时，正则里的 `|` 会被 cmd 当管道符解析"
                     "（实测报『此时不应有 …』rc=1），反斜杠亦有被吃掉的风险")
ap.add_argument("--text-layer", default=None, help="文字所在图层，逗号分隔（必填，由探查提供）")
ap.add_argument("--text-type", default="MTEXT,TEXT", help="文字实体类型，逗号分隔")
ap.add_argument("--fx-pattern", default=None, help="分纤箱编号正则（必填，由探查提供）")
ap.add_argument("--bldg-pattern", default=None,
                help="楼栋标注正则（必填，由探查枚举全部楼栋标题/标注写法后提供）。"
                     "必须覆盖『N#配套楼』『N#商业楼』以及无『楼』字的写法，"
                     "否则配套楼的箱会被误归到邻近住宅楼")
ap.add_argument("--unit-pattern", default=None, help="单元标注正则（由探查提供；图纸无单元标注时可省略）")
ap.add_argument("--floor-pattern", default=None, help="楼层标注正则。默认 None＝内置统一解析（支持 3F/17F/-1F/B1/B2/WF）。**不要再用 (-?\\d+)F 覆盖**，否则 B1 整层会被静默丢弃")
ap.add_argument("--x-min", type=float, default=-1e9, help="搜索区域x下界（总图区域）")
ap.add_argument("--x-max", type=float, default=1e9, help="搜索区域x上界")
ap.add_argument("--y-min", type=float, default=-1e9, help="搜索区域y下界")
ap.add_argument("--y-max", type=float, default=1e9, help="搜索区域y上界")
ap.add_argument("--proximity-tol", type=float, default=None, help="FX与楼栋/单元/楼层的空间邻近容差（必填，按探查实测距离设置，不得盲目沿用默认值）")
args = ap.parse_args()

# ---- --config 回填（2026-09-18）----
# 本脚本曾是本工具链里唯一「正则类参数只能走命令行」的入口：--fx-pattern /
#   --bldg-pattern / --unit-pattern 经 ftth.cmd -> cmd.exe 时，`|` 被当管道符解析
#   （实测 rc=1，cmd 报「此时不应有 号楼。」），反斜杠亦有被吃风险。
#   现与其它子命令对齐：命令行显式 > --config 的 suggested_params > 内置默认。
if args.config:
    try:
        with open(args.config, "r", encoding="utf-8") as _f:
            _sp = (json.load(_f) or {}).get("suggested_params") or {}
    except Exception as _e:                                          # noqa: BLE001
        log.warning("[config] 读取失败（继续用命令行参数）：%s" % _e)
        _sp = {}
    _filled = []
    for _k in ("text_layer", "fx_pattern", "bldg_pattern", "unit_pattern",
               "floor_pattern", "proximity_tol"):
        if getattr(args, _k, None) in (None, "") and _sp.get(_k) not in (None, ""):
            setattr(args, _k, _sp[_k])
            _filled.append(_k)
    if _filled:
        log.info("[config] 自 %s 回填 %d 个参数：%s"
                 % (os.path.basename(args.config), len(_filled), ", ".join(_filled)))
    else:
        log.info("[config] 已加载 %s（命令行已给全，无可回填项）"
                 % os.path.basename(args.config))

DXF_PATH = args.dxf
OUT = args.out or (os.path.splitext(DXF_PATH)[0] + "_fx映射表.json")

if not args.probe:
    require_params([
        ("--text-layer", args.text_layer, "含FTTH标注的文字图层（探查图层清单+采样后确定）"),
        ("--fx-pattern", args.fx_pattern, "分纤箱编号正则"),
        ("--bldg-pattern", args.bldg_pattern, "楼栋标注正则（须覆盖配套楼/商业楼/无『楼』字写法）"),
        ("--proximity-tol", args.proximity_tol, "FX 与楼栋标注的实测邻近距离"),
    ], "extract_fx_map")

FX_RE = re.compile(args.fx_pattern) if args.fx_pattern else None
BLDG_RE = re.compile(args.bldg_pattern) if args.bldg_pattern else None
UNIT_RE = re.compile(args.unit_pattern) if args.unit_pattern else None
FLOOR_RE = re.compile(args.floor_pattern) if args.floor_pattern else None
# 箱表描述内直写的安装层（「N号楼M单元K层」的 K 层）。与系统图区的 F 标注是两个来源，
# 前者更权威——它就在箱号旁边，后者要跨区按 y 关联（见下 P0-11）。
DESC_FLOOR_RE = re.compile(r"(\d+)\s*层")
LAYERS = [x.strip() for x in (args.text_layer or "").split(",") if x.strip()]
TYPES = [x.strip().upper() for x in args.text_type.split(",") if x.strip()]
TOL = args.proximity_tol

doc, msp = load_dxf(DXF_PATH, log)
texts = collect_texts(msp, LAYERS, TYPES)

# 区域筛选
region_texts = [
    t for t in texts
    if args.x_min <= t["x"] <= args.x_max and args.y_min <= t["y"] <= args.y_max
]
log.info(f"区域内文字: {len(region_texts)} 条")

# 分类
fx_items = [t for t in region_texts if FX_RE and FX_RE.search(t["内容"])]
bldg_items = [t for t in region_texts if BLDG_RE and BLDG_RE.search(t["内容"])]
unit_items = [t for t in region_texts if UNIT_RE and UNIT_RE.search(t["内容"])]
floor_items = [t for t in region_texts if is_floor_text(clean_text(t["内容"]), FLOOR_RE)]

log.info(f"FX标注: {len(fx_items)}, 楼栋标注: {len(bldg_items)}, 单元标注: {len(unit_items)}, 楼层标注: {len(floor_items)}")

# 运行时断言（2026-09-13）：bldg-pattern 漏匹配配套/商业/附属类楼栋的防护。
# 实测教训：旧 pattern 未覆盖「N#配套楼」→ 配套楼的箱按最近邻误归到旁边住宅楼（FX22/FX23）。
_RE_AUX_BLDG = re.compile(r"配套|商业|附属")
_aux_on_map = [t for t in region_texts if _RE_AUX_BLDG.search(t["内容"])]
_aux_matched = [t for t in bldg_items if _RE_AUX_BLDG.search(t["内容"])]
if _aux_on_map and not _aux_matched:
    log.warning(
        f"区域内有「配套/商业/附属」类文字 {len(_aux_on_map)} 条，但 bldg-pattern 一条都没匹配到"
        f"（样例：{'｜'.join(t['内容'][:16] for t in _aux_on_map[:3])}）"
        f"→ --bldg-pattern 可能漏匹配该类楼栋写法，箱归属可能误落到邻近住宅楼，请修正 pattern 后重跑")

# ---------- 探查模式 ----------
# 2026-09-16：**打破「鸡生蛋」**。探查模式的存在意义就是"发现 pattern"，
#   但旧实现下 fx/bldg/unit 样例都靠各自的 --*-pattern 过滤后才打印 ——
#   不传 pattern 就全打空，等于要求用户先知道答案才能探查答案。
#   现改为：未传 pattern 时**主动给出候选 + 推荐正则**，并列出样本供确认。
def _shape_template(s, maxlen=20):
    """把文字归一成「形状模板」：字母段→§A§、数字段→§N§。

    用途：把 `FX01#`/`FX23#` 归成同一形状，从而**从图上反推**编号写法，
    而不是要求用户先给出正则。

    含换行或过长的文字返回 None —— 编号型标注都很短；
    长文本（说明段落、图签）会把模板统计和推荐正则彻底污染（实测某图
    一条含换行的说明文字与图名拼成了一个跨行"模板"，排在推荐首位）。
    """
    x = str(s).strip()
    if not x or len(x) > maxlen or "\n" in x or "\r" in x:
        return None
    x = re.sub(r"[A-Za-z]+", "\u00a7A\u00a7", x)
    x = re.sub(r"\d+", "\u00a7N\u00a7", x)
    return x


def _recommend_pattern(texts, must_have=("#", "号"), limit=12):
    """从文字集里推荐「编号型」正则（按形状模板聚类，取高频且含 #/号 者）。"""
    cnt = Counter(tp for tp in (_shape_template(t["内容"]) for t in texts) if tp)
    recs = []
    for tp, n in cnt.most_common(60):
        if "\u00a7N\u00a7" not in tp:
            continue
        if not any(m in tp for m in must_have):
            continue
        pat = re.escape(tp).replace("\u00a7A\u00a7", "[A-Za-z]+").replace("\u00a7N\u00a7", r"\d+")
        recs.append((n, tp, pat))
        if len(recs) >= limit:
            break
    return recs, cnt


if args.probe:
    if not args.fx_pattern:
        log.info("\n== 【未传 --fx-pattern】自动推荐编号写法 ==")
        recs, cnt = _recommend_pattern(region_texts)
        log.info("  区域内文字形状模板（出现次数前 12）：")
        for tp, n in cnt.most_common(12):
            log.info("    %-26s ×%d" % (tp, n))
        if recs:
            log.info("  → 推荐 --fx-pattern（按出现次数排序，用 search 语义）：")
            for n, tp, pat in recs[:6]:
                log.info("      %-16s  ← 形状 %s（%d 条）" % (pat, tp, n))
        else:
            log.info("  → 未发现含 `#`/`号` 的编号型文字；请核对 --x-min/--x-max/--y-min/--y-max 区域，"
                     "或本图箱号写法特殊，需人工指定 pattern。")
        log.info("  （提示：不传 pattern 时下面各节会列出原始样本，可直接肉眼确认写法）")

    if not args.bldg_pattern:
        log.info("\n== 【未传 --bldg-pattern】含「楼」字的文字候选（前 30） ==")
        _cand_b = [t for t in region_texts if "楼" in t["内容"]]
        for t in _cand_b[:30]:
            log.info("  %r @ (%.1f,%.1f) [%s]" % (t["内容"], t["x"], t["y"], t["层"]))
        if not _cand_b:
            log.info("  （区域内没有含「楼」字的文字，请核对区域参数）")

    log.info("\n== FX 标注样例（前30条）%s ==" % ("（--fx-pattern 匹配）" if args.fx_pattern else "（未传 pattern，为空）"))
    for t in fx_items[:30]:
        log.info("  %r @ (%.1f,%.1f) [%s]" % (t["内容"], t["x"], t["y"], t["层"]))
    if not args.fx_pattern and not fx_items:
        log.info("  区域内全部文字样本（前 40，用于人工确认编号写法）：")
        for t in region_texts[:40]:
            log.info("    %r @ (%.1f,%.1f) [%s]" % (t["内容"], t["x"], t["y"], t["层"]))

    log.info("\n== 楼栋标注样例（前20条） ==")
    for t in bldg_items[:20]:
        log.info("  %r @ (%.1f,%.1f) [%s]" % (t["内容"], t["x"], t["y"], t["层"]))
    log.info("\n== 单元标注样例（前20条） ==")
    for t in unit_items[:20]:
        log.info("  %r @ (%.1f,%.1f) [%s]" % (t["内容"], t["x"], t["y"], t["层"]))
    log.info("\n== 楼层标注样例（前20条） ==")
    for t in floor_items[:20]:
        log.info("  %r @ (%.1f,%.1f) [%s]" % (t["内容"], t["x"], t["y"], t["层"]))
    sys.exit(0)

# ---------- 建立FX映射 ----------
# 2026-09-15（P0-10）：**同一编号在图上出现多处时不得静默覆盖**。
#   根因：旧实现直接用 `fx_map[编号] = entry`，同编号后写覆盖前写 —— 箱位凭空消失。
#   实测某图 TEL_TEXT 层箱号标注 72 条、唯一编号仅 64 条（8 个编号各出现 2 次，
#   且两次指向不同楼栋/不同坐标），旧实现输出 64 条、静默丢掉 8 个箱位。
#   改法：按**标注实例**逐条收录；同编号多实例时，键加 `#序号` 区分并**原样保留**，
#   同时在结果里登记「重号编号」，交人工裁决（遵循原则二：不自行择一）。
_by_id = defaultdict(list)

for fx in fx_items:
    fx_id = FX_RE.search(fx["内容"]).group(0)
    fx_x, fx_y = fx["x"], fx["y"]

    # 找最近的楼栋标注（按距离）
    best_bldg = None
    best_bldg_dist = float("inf")
    for bt in bldg_items:
        d = ((bt["x"] - fx_x) ** 2 + (bt["y"] - fx_y) ** 2) ** 0.5
        if d < best_bldg_dist:
            best_bldg_dist = d
            best_bldg = bt

    # 找最近的单元标注
    best_unit = None
    best_unit_dist = float("inf")
    for ut in unit_items:
        d = ((ut["x"] - fx_x) ** 2 + (ut["y"] - fx_y) ** 2) ** 0.5
        if d < best_unit_dist:
            best_unit_dist = d
            best_unit = ut

    # 找最近的楼层标注（安装楼层）——2026-09-12 P0-6 修正：从最近线法改为区间法
    best_floor = None
    best_floor_dist = float("inf")
    floor_item_pairs = [(clean_text(ft["内容"]), ft["y"]) for ft in floor_items]
    best_floor, best_floor_dist = assign_floor_by_interval(fx_y, floor_item_pairs, tol=None)

    entry = {
        "编号": fx_id,
        "x": round(fx_x, 2),
        "y": round(fx_y, 2),
        "楼栋": None,
        "单元": None,
        "安装楼层": None,
        "安装楼层口径": None,
        "楼栋距离": round(best_bldg_dist, 1) if best_bldg else None,
        "楼层距离": round(best_floor_dist, 1) if best_floor else None,
    }

    if best_bldg and best_bldg_dist <= TOL:
        entry["楼栋"] = best_bldg["内容"].strip()

    # 单元归属（2026-09-11 修正，P0-12）：
    #   旧实现直接取"最近的 X单元 文字"，与楼栋无关 → 总图里「N#配套楼」这类没有单元标注的楼栋，
    #   会被挂到别栋的单元上（实测教训：配套楼的箱被写成邻近住宅楼的单元，
    #   导致这些箱被算进别的楼栋，覆盖范围整体错位）。
    #   新规则：楼栋标注本身即单元级（如「1#楼1单元」）→ 单元=楼栋；否则只有"最近的单元标注
    #   与楼栋同号"时才采用，否则单元=楼栋（视为单单元楼栋）。
    unit_txt, unit_src = None, None
    if entry["楼栋"]:
        unit_txt = entry["楼栋"]
        unit_src = "由楼栋标注推导"
        has_unit_mark = bool(UNIT_RE and UNIT_RE.search(entry["楼栋"]))
        if not has_unit_mark and best_unit and best_unit_dist <= TOL:
            _bn = BLDG_RE.search(entry["楼栋"])
            _un = BLDG_RE.search(best_unit["内容"])
            if _bn and _un and _bn.group(0) == _un.group(0):
                unit_txt = best_unit["内容"].strip()
                unit_src = "最近单元标注（与楼栋同号）"
    elif best_unit and best_unit_dist <= TOL:
        unit_txt = best_unit["内容"].strip()
        unit_src = "最近单元标注（无楼栋标注）"
    entry["单元"] = unit_txt
    entry["单元来源"] = unit_src

    # 2026-09-15（P0-11）：箱表描述内已写「K层」时**直接取用**，优先于按 y 关联的楼层标注。
    #   根因：本类图纸把安装层直接写在箱表文字里（「N号楼M单元K层」），
    #   而系统图区的 F 标注在 y 上也可能「很近」（实测某图偏差近 1 万），
    #   旧逻辑一律取系统图 F → 安装楼层整体错位（实测描述写 2 层、输出 14F）。
    #   优先级：描述内直写（口径A′） > 图上 F 标注（口径A/B）。
    _desc_floor = None
    if entry["楼栋"]:
        _dm = DESC_FLOOR_RE.search(entry["楼栋"])
        if _dm:
            _desc_floor = int(_dm.group(1))
    if _desc_floor is not None:
        entry["安装楼层"] = "%dF" % _desc_floor
        entry["安装楼层口径"] = "口径A′:箱表描述内直写（『N号楼M单元K层』的 K 层）"
    elif best_floor:
        entry["安装楼层"] = best_floor
        if best_floor_dist <= 5.0:
            entry["安装楼层口径"] = "口径A:图上直写"
        else:
            entry["安装楼层口径"] = "口径B:y坐标关联"

    entry["原始编号"] = fx_id
    _by_id[fx_id].append(entry)

# 展开为映射表（同编号多实例 → 键加 #序号，全部保留）
fx_map = {}
_dup_ids = {k: v for k, v in _by_id.items() if len(v) > 1}
for _fid, _lst in _by_id.items():
    if len(_lst) == 1:
        fx_map[_fid] = _lst[0]
    else:
        for _i, _e in enumerate(_lst, 1):
            fx_map["%s#%d" % (_fid, _i)] = _e

# ---------- 输出 ----------
result = {
    "DXF文件": os.path.basename(DXF_PATH),
    "搜索区域": {"x_min": args.x_min, "x_max": args.x_max, "y_min": args.y_min, "y_max": args.y_max},
    "FX总数": len(fx_map),
    # 2026-09-15（P0-10）：重号可见化。旧实现静默覆盖 → 箱数凭空变少且无任何提示；
    #   现同时给出「标注实例数 / 唯一编号数 / 重号清单」，便于发现图纸编号重复或漏录。
    "标注实例数": len(fx_items),
    "唯一编号数": len(_by_id),
    "重号编号": {k: len(v) for k, v in sorted(_dup_ids.items())},
    "重号说明": (("同一编号在图上出现多处的，各实例均按『编号#序号』收录、未自动择一；"
                  "其归属请人工裁决（实测某图 8 个编号各出现 2 次，且两次指向不同楼栋）")
                 if _dup_ids else ""),
    "FX映射表": list(fx_map.values()),
    # P1-17 修正：增加「需人工复核」提示字段
    "需人工复核": True,
    "复核说明": "FX→楼栋→单元→安装楼层 映射必须人工目视核对原图确认，不得直接作为结论使用",
}

# 控制台摘要
log.info("\n===== FX 映射表摘要 =====")
log.info("（提示：以下映射需人工目视核对原图确认）")
for entry in sorted(fx_map.values(), key=lambda e: e["编号"]):
    log.info(f"  {entry['编号']}: {entry['楼栋']} {entry['单元']} {entry['安装楼层']} ({entry['安装楼层口径']})")

try:
    os.makedirs(os.path.dirname(os.path.abspath(OUT)) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
except IOError as e:
    log.error(f"无法写入输出文件: {OUT}\n{e}")
    sys.exit(1)
log.info(f"\n已保存: {OUT}")
