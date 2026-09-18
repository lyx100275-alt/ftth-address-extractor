#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTTH 脚本公共模块
存放各脚本共享的常量、工具函数，避免重复代码。
"""
import logging
import math
import os
import re
import sys

# ---------- 常量 ----------
INF_COORD = 1e9          # 坐标边界的"无穷大"值（楼栋 x 范围首尾锚点用）
NEG_INF_COORD = -1e9     # 负无穷坐标值
DEFAULT_UNIT_CLUSTER = 30.0   # fx 聚类阈值
DEFAULT_UNIT_RANGE = 120.0    # 单元文字 x 归属半宽
DEFAULT_Y_TOL = 2.0           # 户数/皮线与楼层 y 坐标匹配容差
DEFAULT_MATCH_TOL = 30.0      # 皮线归属楼层 y 容差
DEFAULT_X_CLUSTER = 20.0      # 皮线 x 聚簇阈值
DEFAULT_X_Y_GAP = 6.0         # 同层两户皮线的y间距参考
DEFAULT_VERT_DX = 3.0         # 垂直线段 x 跨度阈值
DEFAULT_VERT_DY = 3.0         # 垂直线段 y 跨度阈值
DEFAULT_FX_WINDOW = 15.0      # 分纤箱 x 附近线段搜索半宽
DEFAULT_MERGE_TOL = 2.0       # 竖干拼接：端点相接容差
DEFAULT_CONN_TOL = 3.0        # 皮箱连接判定：端点距竖干/设备x容差

DEFAULT_FLOOR_PATTERN = r"(-?\d+)F"   # 仅作 parse_floor_label 认不出时的兜底正则，不要当"标准楼层正则"使用
FLOOR_WF_VALUE = 900     # 屋面层（WF）的排序值。WF 只用于排序，不代表可住楼层


# ---------- 输出写盘卫生（统一实现） ----------

def ensure_parent(path, log=None):
    """写盘前确保输出路径的父目录存在；返回 True 表示本次新建了目录。

    2026-09-16 通用化收口：实测全技能 15 处写盘点（`--out` / `--json`）原先仅 3 处
    （gen_addressbook / plan_methods / load_geom）自建父目录；其余在调用方传入
    `<项目>/.temp/<尚不存在的子目录>/xx.json` 时直接 FileNotFoundError 崩掉，
    个别处还把异常吞成 rc=0，使「失败」对外表现为「成功但无产物」。
    path 为空、或仅为文件名（无父目录）时静默返回。
    """
    if not path:
        return False
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        try:
            os.makedirs(d, exist_ok=True)
        except OSError as e:
            msg = "无法创建输出目录 %s: %s" % (d, e)
            if log:
                log.error(msg)
            else:
                print(msg)
            raise
        if log:
            log.info("[out] 已创建输出目录: %s" % d)
        return True
    return False


def write_text(path, text, encoding="utf-8", log=None):
    """安全写文本：先建父目录再写；**失败抛出、不吞**（由调用方决定退出码）。"""
    ensure_parent(path, log=log)
    with open(path, "w", encoding=encoding) as f:
        f.write(text)
    return path


def sanitize_nonfinite(obj, _path="", _hits=None):
    """就地把非有限浮点（`inf` / `-inf` / `nan`）清洗为 `None`，返回 (obj, 命中路径表)。

    为什么必须做（2026-09-18 实测）：Python 的 `json.dump` 默认把非有限浮点写成
    `Infinity` / `NaN` / `-Infinity` —— 这三个字面量**不在 JSON 规范内**，严格解析器
    （JS / Go / 多数工具的默认实现）会因此**拒绝整份文件**，而不是跳过那个字段。
    且 `inf` 本身是「未测得」的占位值，写成它等于让垃圾值冒充测量结果。

    语义约定：清洗后的 `None` 表示「本图未测得该量」，**与 0 不同**，消费方不得当 0 用。
    调用方应把命中的 `_hits` 登记进产物（如「非有限值清洗」字段），不得静默丢弃。
    """
    if _hits is None:
        _hits = []
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            obj[k] = sanitize_nonfinite(obj[k], "%s.%s" % (_path, k), _hits)
    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = sanitize_nonfinite(obj[i], "%s[%d]" % (_path, i), _hits)
    elif isinstance(obj, float) and not math.isfinite(obj):
        _hits.append(_path)
        return None
    return obj


def write_json(path, obj, encoding="utf-8", log=None, indent=2, ensure_ascii=False):
    """安全写 JSON：先建父目录再 dump；**失败抛出、不吞**（由调用方决定退出码）。

    dump 前强制清洗非有限浮点为 `null`（见 `sanitize_nonfinite`）——
    保证产物是**标准 JSON**，任何语言的严格解析器都读得进来。
    """
    import json
    _hits = []
    obj = sanitize_nonfinite(obj, _hits=_hits)
    if _hits and log is not None:
        log.warning("产物含非有限浮点 %d 处，已清洗为 null：%s"
                    % (len(_hits), "、".join(_hits[:8])))
    ensure_parent(path, log=log)
    with open(path, "w", encoding=encoding) as f:
        json.dump(obj, f, ensure_ascii=ensure_ascii, indent=indent)
    return path


def protect_out_path(path, force=False, suffix="_patched", log=None, label=None):
    """产物写保护：目标**已存在**且未显式 force 时，改写到 `<原名><suffix>.<后缀>`。

    返回 (实际写入路径, 是否改道)。

    动机（2026-09-18 复盘）：实测某会话把自算值直接写回 `countbox.json` /
    `assembly.json` 等**技能产物**，原始输出永久消失，且下游 assemble 的输出反过来
    当了同一条链的证据 → 论证闭环、结果不可复现。
    纪律：中间产物只允许「追加派生」，覆盖原始产物必须显式声明（`--force`）。

    刻意不做的事：
      · 不 hard-fail —— 改道即可，避免因「目录里已有同名文件」把正常重跑卡死；
      · 不递归改名 —— 派生文件（`*_patched`）本身允许被覆盖，否则会滚出
        `_patched_patched…`。
    """
    if not path or force or not os.path.exists(path):
        return path, False
    stem, ext = os.path.splitext(path)
    new = stem + suffix + (ext or ".json")
    msg = ("[写保护] %s 已存在，改写到 %s（确需覆盖原产物请显式加 --force）"
           % (label or os.path.basename(path), os.path.basename(new)))
    if log:
        log(msg)
    else:
        print(msg)
    return new, True


# ---------- 文字清洗（统一实现，替代各脚本内联的 replace 链） ----------
def clean_text(s):
    """统一文字清洗：去全角空格 / 零宽字符 / BOM，再 strip。

    各脚本原先各自内联 `.replace("\\u3000","").replace("\\u200b","").replace("\\ufeff","")`，
    口径容易漂移，统一到这里。
    """
    return str(s).replace("\u3000", "").replace("\u200b", "").replace("\ufeff", "").strip()


# ---------- 参数校验（统一实现） ----------
def require_params(pairs, script_name):
    """校验必填参数，缺一即打印清单并退出（exit code 2）。

    参数:
        pairs: [(参数名, 值, 说明), ...]
        script_name: 脚本名，用于提示

    用途：本技能不预设任何项目特有参数（图层名 / 标题写法 / 编号格式都是每张图不同），
    未经过 Step 1a 探查就调用解析脚本时，必须显式报错，而不是静默套用某个项目的实测值。
    """
    missing = [(n, h) for n, v, h in pairs if v in (None, "", [])]
    if missing:
        print(f"[{script_name}] 缺少必填参数——每张新图纸必须先用 probe 探查后传入，不预设项目参数：")
        for n, h in missing:
            print(f"  {n:22s} {h}")
        sys.exit(2)


# ---------- 楼层标注统一解析（2026-09-11 修正 P0-4） ----------
def parse_floor_label(name):
    """
    把楼层标注解析为整数值，覆盖图纸上出现的全部形态。

    支持：
        '3F' / '17F' / '01F'   →  3 / 17 / 1    （类别 normal）
        '-1F' / '-2F'          → -1 / -2        （类别 normal）
        'B1' / 'B2' / 'b1'     → -1 / -2        （类别 basement）
        'WF'                   → FLOOR_WF_VALUE （类别 roof，仅排序用）

    返回 (值, 类别)；无法识别返回 (None, None)。
    类别 ∈ {'normal', 'basement', 'roof'}

    为什么要有这个函数：旧实现仅用正则 `(-?\\d+)F` 解析楼层，对 `B1`（地下一层）
    和 `WF`（屋面层）一律返回 None，导致：
      · 楼层表把 B1 整层丢掉，B1 住户静默消失（实测：地下一层整层住户在输出中凭空消失，
        且既不报错也不进待确认清单）
      · 'B1' 无法转换为模板要求的「地下一层」
    这类丢失不报错、不进待确认清单，属于最危险的一类缺陷。
    """
    if name is None:
        return None, None
    t = clean_text(name)
    if not t:
        return None, None
    m = re.fullmatch(r"[Bb](\d+)", t)
    if m:
        return -int(m.group(1)), "basement"
    if t.upper() == "WF":
        return FLOOR_WF_VALUE, "roof"
    m = re.fullmatch(r"(-?\d+)\s*[Ff]", t)
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


def attrib_hit(attribs, tags=None, val_keys=None):
    """按【属性值】识别设备（统一实现，替代各脚本重复的 attrib 多 tag 匹配）。

    同一设备在不同图区可能用完全不同的块名，但属性值一致，
    因此识别必须按属性值、不能按块名。

    参数:
        attribs: {tag: value} 属性字典
        tags: 候选 tag 列表（如 ["A", "$TEXT$"]）；为空表示不限 tag
        val_keys: 属性值关键词列表（如 ["HDD", "家居配线箱"]）；为空表示不限值

    返回:
        bool。tags 与 val_keys 都给 = 两者都需命中；只给其一时按该条件命中即可。
    """
    tags = [t for t in (tags or []) if t]
    val_keys = [k for k in (val_keys or []) if k]
    if tags and val_keys:
        return any(any(k in attribs.get(t, "") for k in val_keys) for t in tags)
    if val_keys:
        return any(k in v for v in attribs.values() for k in val_keys)
    if tags:
        return any(t in attribs for t in tags)
    return False


# ---------- 家居配线箱图标识别（关键词与命中的**唯一真源**）----------
# 系统图里每一户的入户端都画一个「家居配线箱」图标。图内文字**没有统一写法**：
# 实测同一设备在不同图纸写作 HDD / HD（块属性 A=家居配线箱、$TEXT$=HD），也可能只是方块。
# 故把已知变体全部列出，并对纯 ASCII 缩写改用**词边界**匹配（`HD` 不得命中 `HDMI`/`CHD`）。
# 本表被 count_box_icons.py（图标法）与 plan_methods.py（信号判定）共用 —— 只此一份，
# 不得在调用方另抄副本：两处各留一份必然漂移（同 SKILL.md「镜像铁律」）。
HOME_BOX_STRONG_KEYS = (
    "家居配线箱", "家庭配线箱", "家居信息箱", "家庭信息箱", "多媒体箱",
    "家庭多媒体箱", "智能家居配线箱", "住户配线箱", "用户配线箱", "弱电箱",
)
HOME_BOX_WEAK_KEYS = ("HDD", "HD", "H.D.D", "H.D", "多媒体信息箱")
HOME_BOX_KEYS = HOME_BOX_STRONG_KEYS + HOME_BOX_WEAK_KEYS


def kw_split_ascii(keys):
    """把关键词分成两路，供命中判定用：

       - 纯 ASCII（HD / HDD / H.D.D 等缩写）→ **词边界**正则，避免误命中更长的词；
       - 含中文等其它字符（家居配线箱 …）→ 直接子串匹配。

    返回 (子串关键词元组, 词边界正则或 None)。
    """
    word, sub = [], []
    for k in keys:
        k = (k or "").strip()
        if not k:
            continue
        if re.fullmatch(r"[A-Za-z0-9._\-]+", k):
            word.append(k)
        else:
            sub.append(k)
    pat = None
    if word:
        pat = re.compile(r"(?<![A-Za-z0-9])(?:%s)(?![A-Za-z0-9])"
                         % "|".join(re.escape(w) for w in word), re.I)
    return tuple(sub), pat


def kw_hit(text, sub, pat):
    """关键词命中判定：中文子串命中 或 ASCII 缩写按词边界命中。"""
    if not text:
        return False
    if sub and any(k in text for k in sub):
        return True
    return bool(pat and pat.search(text))


def home_box_kw(keys=None):
    """家居配线箱关键词的 (子串元组, 词边界正则)；批量判定时编译一次复用。"""
    return kw_split_ascii(keys if keys is not None else HOME_BOX_KEYS)


def home_box_hit(text, kw=None):
    """单条文本是否命中家居配线箱标识（文字实体 / 块名 / 块属性值通用）。"""
    sub, pat = kw if kw else home_box_kw()
    return kw_hit(text, sub, pat)


# ---------- 日志 ----------
def setup_logger(name="ftth", verbose=False):
    """配置日志，替代散落的 print。verbose=True 时输出 DEBUG 级别。"""
    level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


# ---------- DXF 加载 ----------
def _central_cache_path(src_path, suffix):
    """集中缓存路径：%LOCALAPPDATA%/ftth-address-extractor/cache/<hash>__<basename><suffix>。

    集中存放的理由：pickle 缓存是整个 ezdxf 对象图，实测某大图 .pkl 达 141MB，
    落在图纸同目录会污染用户图纸目录（且图纸目录多为交付物所在，不应混入运行缓存）。
    命名含源路径哈希，避免不同目录的同名图纸互相覆盖。
    """
    import hashlib
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".cache")
    d = os.path.join(base, "ftth-address-extractor", "cache")
    h = hashlib.md5(os.path.abspath(src_path).encode("utf-8")).hexdigest()[:12]
    return os.path.join(d, "%s__%s%s" % (h, os.path.basename(src_path), suffix))


def load_dxf(path, log=None):
    """
    加载 DXF 文件，返回 (doc, msp)。带磁盘缓存（实测某大图：全量解析约 2 分钟/次，
    命中缓存后秒级——同一张图被多次加载时收益显著）。
    缓存规则：集中目录缓存（`_central_cache_path`，图纸同目录的旧 `<DXF>.pkl` 仍可命中、
    只读兼容）；以源文件 mtime+size 校验，图纸改动即自动失效；
    缓存损坏/反序列化失败时静默回退全量解析并重建，不影响主流程。
    失败时打印错误并 sys.exit(1)。
    """
    import pickle
    cache = _central_cache_path(path, ".pkl")
    legacy_cache = path + ".pkl"
    try:
        st = os.stat(path)
    except OSError as e:
        if log:
            log.error(f"无法读取DXF文件: {path}\n{e}")
        else:
            print(f"无法读取DXF文件: {path}\n{e}")
        sys.exit(1)
    for cand in (cache, legacy_cache):
        if not os.path.exists(cand):
            continue
        try:
            with open(cand, "rb") as f:
                blob = pickle.load(f)
            if blob.get("mtime") == st.st_mtime and blob.get("size") == st.st_size:
                doc = blob["doc"]
                return doc, doc.modelspace()
        except Exception:
            pass  # 缓存损坏或 pickle 版本不兼容 → 回退重新解析
    import ezdxf
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
    except IOError as e:
        if log:
            log.error(f"无法读取DXF文件: {path}\n{e}")
        else:
            print(f"无法读取DXF文件: {path}\n{e}")
        sys.exit(1)
    except Exception as e:
        if log:
            log.error(f"解析DXF时出错: {path}\n{e}")
        else:
            print(f"解析DXF时出错: {path}\n{e}")
        sys.exit(1)
    try:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, "wb") as f:
            pickle.dump({"mtime": st.st_mtime, "size": st.st_size, "doc": doc},
                        f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:
        pass  # 缓存写失败不影响主流程
    return doc, msp


# ---------- 几何快速路径：只读几何，免去反序列化整个 ezdxf 对象图 ----------
# v2：坐标/旋转角改为**原值不取整**。v1 为压体积做过 round(…,2)，
#     实测会使由坐标推得的几何容差出现末位扰动（如 8350.1 → 8350.2），
#     虽未改变任何判定结果，但测量路径不应引入无谓误差。JSON 的 float 往返
#     在 Python 3 下无损，故去整后缓存与直接解析**逐位一致**；代价约 +30% 体积。
# v3：新增 polylines（**整组顶点**）+ insert_attrs（INSERT 块属性）。
#     起因：count_households / analyze_coverage / extract_fx_map 需要"多段线整组顶点"
#     与"INSERT 属性"这两样几何缓存原本不承载的东西，被迫退回 load_dxf（实测 pkl 命中
#     仍要约 20s，而 geom.json 载入仅约 0.2s —— 差两个数量级）。
#     v2 的 segs 是**逐段拆开**的线段（实测某大图 52,934 条），
#     无法还原"哪几段属于同一条多段线"；inserts 也只有 [layer,x,y,name,rot] 五元组，
#     不含块属性 —— 所以只加一个"类型字段"是不够的，必须补这两类原始结构。
# v2：坐标/旋转角改为**原值不取整**。v1 为压体积做过 round(…,2)，
#     实测会使由坐标推得的几何容差出现末位扰动（如 8350.1 → 8350.2），
#     虽未改变任何判定结果，但测量路径不应引入无谓误差。JSON 的 float 往返
#     在 Python 3 下无损，故去整后缓存与直接解析**逐位一致**；代价约 +30% 体积。
GEOM_VERSION = 3

# INSERT 块属性值的截断长度（属性值可能很长，全量存会把缓存撑大）。
_ATTR_VAL_MAX = 200


def extract_geom(msp):
    """把 modelspace 抽成**轻量几何 dict**（可被 json 直接序列化/载入）。
    结构与 scripts/dump_geom.py 产物一致：
      texts        [layer, x, y, text]                  TEXT/MTEXT
      inserts      [layer, x, y, name, rot]             INSERT（**保持五元组不变**，
                                                       以免破坏既有消费方）
      insert_attrs [{tag: value} | None, ...]           与 inserts **同索引**的块属性
      segs         [layer, x1, y1, x2, y2, closed]      LINE/LWPOLYLINE/POLYLINE 拆段
                                                        (closed=1 表示闭合多段线的封口段)
      polylines    [layer, [x1,y1,x2,y2,...], closed]   **整组顶点**（不拆段）
      layers       {layer: 实体总数}
      bbox         {x_min,y_min,x_max,y_max}
      n_entities   实体总数
    只读几何、不保留 ezdxf 对象——这是它能被 json 承载、载入快两个数量级的原因。
    坐标与旋转角**保留原值不取整**：JSON 的 float 往返无损，去掉取整才能保证本缓存
    与直接解析逐位一致（v1 为压体积做过 round，会让下游由坐标推得的容差出现末位偏差）。
    """
    texts, inserts, insert_attrs, segs, polylines = [], [], [], [], []
    layer_cnt = {}
    n = 0
    for e in msp:
        n += 1
        try:
            dt = e.dxftype()
            lay = e.dxf.layer
            layer_cnt[lay] = layer_cnt.get(lay, 0) + 1
            if dt == "TEXT":
                p = e.dxf.insert
                texts.append([lay, p.x, p.y, str(e.dxf.text).strip()])
            elif dt == "MTEXT":
                p = e.dxf.insert
                texts.append([lay, p.x, p.y, e.plain_text().strip()])
            elif dt == "INSERT":
                p = e.dxf.insert
                inserts.append([lay, p.x, p.y, e.dxf.name,
                                getattr(e.dxf, "rotation", 0) or 0])
                # 块属性（v3 新增）：{tag: value}，无属性记 None。
                _attrs = {}
                try:
                    for _a in e.attribs:
                        _tag = str(_a.dxf.tag or "").strip()
                        _val = str(_a.dxf.text or "").strip()
                        if _tag:
                            _attrs[_tag] = _val[:_ATTR_VAL_MAX]
                except Exception:
                    _attrs = {}
                insert_attrs.append(_attrs or None)
            elif dt == "LINE":
                s, t = e.dxf.start, e.dxf.end
                segs.append([lay, s.x, s.y, t.x, t.y, 0])
                polylines.append([lay, [s.x, s.y, t.x, t.y], 0])
            elif dt == "LWPOLYLINE":
                pts = [(q[0], q[1]) for q in e.get_points("xy")]
                for a, b in zip(pts, pts[1:]):
                    segs.append([lay, a[0], a[1], b[0], b[1], 0])
                _closed = 1 if getattr(e, "closed", False) else 0
                if _closed and len(pts) > 2:
                    segs.append([lay, pts[-1][0], pts[-1][1], pts[0][0], pts[0][1], 1])
                if pts:
                    _flat = []
                    for _x, _y in pts:
                        _flat.append(_x)
                        _flat.append(_y)
                    polylines.append([lay, _flat, _closed])
            elif dt == "POLYLINE":
                pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
                for a, b in zip(pts, pts[1:]):
                    segs.append([lay, a[0], a[1], b[0], b[1], 0])
                _closed = 1 if getattr(e, "is_closed",
                                       getattr(e, "closed", False)) else 0
                if _closed and len(pts) > 2:
                    segs.append([lay, pts[-1][0], pts[-1][1], pts[0][0], pts[0][1], 1])
                if pts:
                    _flat = []
                    for _x, _y in pts:
                        _flat.append(_x)
                        _flat.append(_y)
                    polylines.append([lay, _flat, _closed])
        except Exception:
            continue
    xs = [t[1] for t in texts] + [i[1] for i in inserts] + [s[1] for s in segs] + [s[3] for s in segs]
    ys = [t[2] for t in texts] + [i[2] for i in inserts] + [s[2] for s in segs] + [s[4] for s in segs]
    bbox = dict(x_min=min(xs), x_max=max(xs), y_min=min(ys), y_max=max(ys)) if xs else None
    return dict(texts=texts, inserts=inserts, insert_attrs=insert_attrs,
                segs=segs, polylines=polylines, layers=layer_cnt,
                bbox=bbox, n_entities=n)


def load_geom(path, log=None, rebuild=False, out=None):
    """**只读几何快速路径**：优先读 <DXF>.geom.json，命中即 json.load 返回。

    为什么需要它：`load_dxf` 命中的是 <DXF>.pkl，仍需反序列化整个 ezdxf 对象图——
    实测某大图 pkl 命中约 20s、全量解析约 76s，而本缓存 json 载入约 0.2s。
    凡只需「文字 / INSERT / 线段 / 图层 / 包围盒」这几类几何查询
    （探查、统计、坐标窗口筛选、找锚点），一律走本函数；
    只有确实需要 ezdxf 完整 API 时才用 load_dxf。

    缓存规则：集中目录缓存（`out` 显式传入时仍按 `out`，图纸同目录的旧缓存只读兼容）；
    以源文件 mtime+size+GEOM_VERSION 校验，图纸或结构版本变化即失效；
    损坏/过期/rebuild=True 时经 load_dxf 重新转储回写。
    写盘失败不影响返回。返回 dict：texts / inserts / segs / layers / bbox / n_entities。
    """
    import json
    cache = out or _central_cache_path(path, ".geom.json")
    legacy_cache = path + ".geom.json"
    try:
        st = os.stat(path)
    except OSError as e:
        msg = f"无法读取DXF文件: {path}\n{e}"
        if log:
            log.error(msg)
        else:
            print(msg)
        sys.exit(1)
    cands = [cache] if out else [cache, legacy_cache]
    for cand in cands:
        if rebuild or not os.path.exists(cand):
            continue
        try:
            with open(cand, "r", encoding="utf-8") as f:
                blob = json.load(f)
            src = blob.get("_src") or {}
            if (src.get("mtime") == st.st_mtime and src.get("size") == st.st_size
                    and src.get("v") == GEOM_VERSION):
                blob.pop("_src", None)
                blob.pop("stat", None)
                return blob
        except Exception:
            pass  # 缓存损坏/过期 → 回退重新转储
    doc, msp = load_dxf(path, log=log)
    geom = extract_geom(msp)
    payload = dict(geom)
    payload["_src"] = dict(mtime=st.st_mtime, size=st.st_size, v=GEOM_VERSION, dxf=path)
    try:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        pass  # 缓存写失败不影响主流程
    return geom


# ---------- 文字收集 ----------
def collect_texts(msp, layers, types):
    """
    从 modelspace 收集指定图层和类型的文字实体。
    
    参数:
        msp: ezdxf modelspace
        layers: [str, ...] 目标图层名列表；为空/None 时表示"不限图层"（探查阶段用）
        types: [str, ...] 目标实体类型列表（大写，如 ["MTEXT", "TEXT"]）
    
    返回:
        [{"内容": str, "x": float, "y": float, "层": str, "类型": str, "高": float}, ...]

    注（2026-09-15）：`高` = 文字高度（TEXT 用 dxf.height，MTEXT 用 dxf.char_height）。
    它是**唯一与图纸坐标尺度无关的长度尺子**——坐标可以放大 500 倍而字高按比例同步放大，
    所以凡是需要「多少距离算同一列/同一行」的判据，都应锚定到字高，而不是写死坐标值。
    """
    types = set(t.upper() for t in (types or [])) or {"TEXT", "MTEXT"}
    layer_set = set(layers) if layers else None
    texts = []
    for e in msp:
        if e.dxftype() not in types:
            continue
        if layer_set is not None and e.dxf.layer not in layer_set:
            continue
        txt = e.plain_text().strip() if e.dxftype() == "MTEXT" else str(e.dxf.text).strip()
        if not txt:
            continue
        p = e.dxf.insert
        try:
            h = float(e.dxf.height if e.dxftype() == "TEXT" else (e.dxf.char_height or 0))
        except Exception:
            h = 0.0
        texts.append({"内容": txt, "x": round(p.x, 2), "y": round(p.y, 2),
                      "层": e.dxf.layer, "类型": e.dxftype(), "高": h})
    return texts


def median_text_height(texts, pred=None):
    """取一组文字的**字高中位数**（尺度锚）。pred 为可选的筛选谓词（入参：内容字符串）。

    为什么要它：所有几何容差若写成绝对坐标值，换一张坐标尺度不同的图就失效。
    字高随图缩放，`k × 字高` 才是可移植的判据。量不出时返回 None，调用方须回落到显式参数。
    """
    hs = []
    for t in texts:
        if pred is not None and not pred(t.get("内容", "")):
            continue
        h = t.get("高") or 0
        if h > 0:
            hs.append(h)
    if not hs:
        return None
    hs.sort()
    return hs[len(hs) // 2]


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
EXPAND_BLDG_RANGES = False


def set_expand_bldg_ranges(v):
    """设置全局区间展开开关（由 CLI 参数调用）。"""
    global EXPAND_BLDG_RANGES
    EXPAND_BLDG_RANGES = bool(v)
    return EXPAND_BLDG_RANGES


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


def pending_items_from_rulings(rulings):
    """「需人工裁决」清单 → [(对象列表, 是否阻塞)]，供 judge_pending_scope 消费。

    `阻塞` 语义（2026-09-18 立）：脚本**已自行处置完毕**的提示（显式 ``阻塞=False``，
    或事项名里写明「已排除」）只作可见性登记，**不构成「结论待裁决」**，不得据以判
    ``result_confirmation=pending``。
    """
    out = []
    for _x in (rulings or []):
        _obj = _x.get("对象")
        _objs = _obj if isinstance(_obj, (list, tuple)) else [_obj]
        _blk = _x.get("阻塞")
        if _blk is None:
            _blk = "已排除" not in str(_x.get("事项") or "")
        out.append(([str(_o) for _o in _objs], bool(_blk)))
    return out


# ---------- 裁决项对象串的「分段」与「作用范围」（全技能唯一实现，2026-09-18） ----------
_UNIT_SEG_RE = re.compile(r'^[0-9一二三四五六七八九十]+单元$')
_UNIT_TAIL_RE = re.compile(r'([0-9一二三四五六七八九十]+单元)\s*$')
_BOX_SEG_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9#\-_.]*$')
_BLDG_SEG_RE = re.compile(r'[楼图]')


def _is_box_seg(seg):
    """段是否形如分纤箱编号：纯字母/数字/`#-_.`，不含中文 ⇒ `4#楼` 这类楼栋段不算。"""
    return bool(_BOX_SEG_RE.match(str(seg or '').strip()))


def _is_bldg_seg(seg):
    """段是否形如楼栋：含 `楼`/`图` 特征字，且不是 `N单元`（`7#楼1单元` 归单元段）。"""
    s = str(seg or '').strip()
    return bool(s) and not _UNIT_SEG_RE.match(s) and bool(_BLDG_SEG_RE.search(s))


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


def split_ruling_object(text):
    """裁决项对象串 → 分段列表（**楼栋段 / 单元段 / 编号段**，后两段可缺）。

    兼容两种实测写法（2026-09-18 统一）：
      · 斜杠式 `楼栋[/单元][/编号]` —— 竖线法产出，如 `4#配套楼/FX22#`、`7#楼1单元/FX17#`；
      · 空格式 `楼栋[ 单元][ 编号]` —— V 型法产出，如 `[共享]1-3号楼综合布线系统图 1单元`。

    实现要点（都踩过）：**不能按 `/` 或空格无条件全拆** —— 楼栋名自身就含这两种分隔符
    （`3/6号楼综合布线系统图` 是共享标题的常见写法，楼栋名也可能含空格）。故一律
    **从尾部**最多剥两段，且只剥「`N单元`」「纯编号」两种已确认形态，剩下的一整段
    才是楼栋名。只认斜杠式会让空格式对象**永远关联不上** ⇒ 裁决项静默放行、结果判
    settled —— 属「未裁决却进成品」的假绿灯，比假 FAIL 更危险。
    """
    s = str(text or '').strip()
    if not s:
        return []
    segs, rest = [], s
    for _ in range(2):
        m = re.match(r'^(.*?)[\s/]+(\S+)$', rest)
        if not m:
            break
        tail = m.group(2)
        if not (_UNIT_SEG_RE.match(tail) or _is_box_seg(tail)):
            break
        segs.insert(0, tail)
        rest = m.group(1).strip()
    segs.insert(0, rest)
    return segs


def parse_ruling_scope(text):
    """对象串 → `(楼栋段, 单元段, 编号段)`，缺的段给空串。

    与 :func:`split_ruling_object` 的分工：后者只做**切分**，本函数负责**归段** ——
    把「楼栋与单元写在一段」的 `7#楼1单元` 拆成 `('7#楼', '1单元', '')`，
    把只有楼栋的 `4#楼` 归成 `('4#楼', '', '')`。
    """
    parts = split_ruling_object(text)
    if not parts:
        return '', '', ''
    box = ''
    if len(parts) >= 2 and _is_box_seg(parts[-1]):
        box = parts[-1]
        parts = parts[:-1]
    unit = ''
    if parts and _UNIT_SEG_RE.match(parts[-1]):
        unit = parts[-1]
        parts = parts[:-1]
    if not unit and parts:
        m = _UNIT_TAIL_RE.search(parts[-1])
        if m and len(parts[-1]) > len(m.group(1)):
            unit = m.group(1)
            parts[-1] = parts[-1][:len(parts[-1]) - len(unit)].strip()
            if not parts[-1]:
                parts = parts[:-1]
    return ' '.join(p for p in parts if p), unit, box


def judge_pending_scope(objs, unit_name, box_id=None, bldg_key=None):
    """裁决项是否作用于「本单元全部箱」（第 1 位）/「本箱」（第 2 位）。

    **这是覆盖类脚本判 ``result_confirmation`` 的唯一定义**（2026-09-18 统一）。
    两个覆盖脚本（竖线法 / V 型法）此前各写一份，漂移后 V 型法那份落后为**子串包含**
    且**只认斜杠式**对象串，两处都会错：
      · 楼栋名形态不同即失配 —— ``"4#楼" in "4#配套楼/FX22#"`` 为 False
        ⇒ 裁决项**关联不上、被静默放行**；
      · 子串会跨号误伤 —— ``7#楼`` 是 ``17#楼`` 的子串 ⇒ 邻栋的问题算到本栋头上。

    作用范围按对象串里**实际写了几段**定三级：

      · 只有楼栋段（`4#楼`、`4#楼[图幅1]`）⇒ **楼栋级**：该楼栋全部单元全部箱置 pending
        —— 整栋的几何前提存疑时，单元级结论连带不可信；
      · 楼栋段 + 单元段（`4#楼 1单元`、`7#楼1单元`）⇒ **单元级**：该单元全部箱；
      · 再带编号段（`4#楼 1单元 FX9#`、`7#楼1单元/FX17#`）⇒ **箱级**：只作用于该箱，
        不扩散到同单元其它箱。

    ``bldg_key`` 是本单元所属楼栋的键（调用方应传）：用于**跨楼栋不误伤** ——
    字符串相同，或**楼号相同**（该口径是本技能既有约定，见
    ``analyze_coverage.judge_object_name``）。不传时退化为「只认对象首段与本单元名
    完全相同」，即**不猜楼栋**（保守，不会误伤别栋）。

    返回 ``(是否单元级命中, 是否箱级命中)``。
    """
    u = str(unit_name or '').strip()
    uk = str(bldg_key or '').strip()
    u_unit = _unit_seg_of(u)
    u_bnum = bldg_num(uk or u)
    for _o in objs:
        _b, _un, _bx = parse_ruling_scope(_o)
        if not (_b or _un or _bx):
            continue
        # ① 楼栋段校验：字符串相同，或楼号相同（后者是既有口径）
        if _b:
            _same = (_b == uk) if uk else (_b == u)
            if not _same and u_bnum and bldg_num(_b) == u_bnum:
                _same = True
            if not _same:
                continue
        # ② 单元段：空 = 楼栋级（作用于本楼栋全部单元）；非空 = 必须命中本单元段
        if _un and (not u_unit or _un != u_unit):
            continue
        # ③ 编号段：有则只作用于该箱
        if _bx:
            if box_id is not None and _bx == str(box_id):
                return False, True
            continue
        return True, True
    return False, False


def first_group(m):
    """安全取匹配对象的捕获组 1：正则**无捕获组**时返回 None，不抛 IndexError。

    调用背景：标题正则常被写成 `\\d+号楼`、`\\d+#楼` 这类不含捕获组的形式，
    旧代码裸调 `m.group(1)` 会直接 IndexError 崩溃。
    本函数与 parse_bldg_nums 配套：楼号解析的首选来源是文字本身，
    捕获组只是"自定义写法"的兜底，缺失时应降级而非报错。
    """
    return m.group(1) if (m.re.groups or 0) >= 1 else None


# 多地块同名楼守卫（2026-09-17 新增，通用化自多地块项目实测）：
# 同名楼栋锚点若出现在显著不同的 x 位置，说明图上有多个独立地块各有一栋同名楼
#（如各地块都有「1号楼」）。锚点池按楼名去重、下游按楼名归并，全图解析会静默串号
#（保留先出现者，其余同名楼整栋丢失）——这是产出错误数据，不是可接受的近似。
# 同位判据取绝对阈值（重复绘制的同一标题坐标相同或相差极小；不同地块相距数千以上），
# 不随图幅缩放。配套工具：ftth.py split-band（按 y 带切出子 DXF 后分带解析）。
DUP_ANCHOR_X_TOL = 10.0


class MultiPlotDuplicateAnchorError(ValueError):
    """多地块同名楼检测：同名锚点出现在显著不同位置（全图解析会静默串号）。"""

# ---------- 区间标题「N-M号楼」：按图上独立证据自动展开（2026-09-19） ----------
# 背景：区间语义（并列 vs 区间）文字本身无法判定，此前一律按字面取端点并告警，
#   中间楼栋**整栋丢失**（实测柳辛庄 band1 丢 2#楼、band3 丢 5#楼；图上另有
#   `2#楼` / `5#楼` 独立标题与 `5号楼1单元2层` 箱位标注为证）。
# 纪律：禁止替用户**猜**语义；但「图上另有该编号的独立实体」属**客观判据**
#   （可测量、可核对），据此展开属自判留证，不是猜测。无证据者维持不展开并继续告警。
BLDG_RANGE_EXPANDED = []   # 展开留痕，供产物记录与人工追溯

_RANGE_TITLE_RE = re.compile(r"(\d+)\s*[-~\u2014\u2013]\s*(\d+)\s*[#\uff03]?\s*\u53f7?\s*\u697c")


def bldg_range_evidence(texts, lo, hi, skip_text=None):
    """区间写法 N-M 号楼：返回中间编号里「图上有独立实体证据」的编号列表。

    判据（客观、可核对）：存在**另一条**文字含 `K#楼` / `K号楼` / `K楼`
    （含 `K号楼X单元Y层` 这类箱位标注），且该文字本身不是区间标题
    （不含 `数字-数字号楼` 写法）—— 区间的端点不得自证中间编号。

    返回 [(编号, 证据文字前40字, x, y), ...]
    """
    out = []
    if lo is None or hi is None:
        return out
    try:
        lo, hi = int(lo), int(hi)
    except (TypeError, ValueError):
        return out
    if hi - lo < 2:
        return out
    skip_id = id(skip_text) if skip_text is not None else None
    for k in range(lo + 1, hi):
        pat = re.compile(r"(?<![0-9])%d\s*[#\uff03]?\s*\u53f7?\s*\u697c" % k)
        for t in (texts or []):
            if not isinstance(t, dict) or id(t) == skip_id:
                continue
            s = str(t.get("内容") or "")
            if not s or _RANGE_TITLE_RE.search(s):
                continue
            if pat.search(s):
                out.append((k, s[:40], t.get("x"), t.get("y")))
                break
    return out



def find_bldg_anchors(texts, title_re, log=None, expand_ranges=None):
    """
    从文字列表中搜索楼栋标题，建立锚点。
    
    参数:
        texts: collect_texts() 返回的文字列表
        title_re: 编译好的标题正则（用 .search 匹配，需含捕获组1=楼栋数字）
                  支持「共享标题」：标题中含多个楼栋号（如「1#、2#、3#住宅光纤入户系统图」）
                  时，正则应使用 finditer 或 group(1) 返回逗号分隔的多个数字。
                  本函数会自动展开多楼栋号，为每个楼栋创建独立锚点。
        log: 可选的 logger，用于输出识别信息
    
    返回:
        {楼名: text_item, ...}，楼名取标题原文（如 "2#楼"），失败回退 "N#楼"

    2026-09-12 修正（P0-4）：共享图纸标题（如「1#、2#、3#住宅光纤入户系统图」）
      旧实现只取 m.group(1) 第一个捕获组 → 第 2、第 3 栋整栋静默丢失。
      新实现用 finditer 展开所有匹配，为每个楼栋号创建独立锚点（复制同一 text_item）。
    2026-09-12 修正（P1-13）：m.group(1) 可能为 None 时跳过，不触发 TypeError。
    2026-09-12 复核补丁（P0-4 缺陷修复）：仅靠 title_re.finditer 展开不够——
      含 `.*` 的贪婪标题正则（如 `(\\d+)#.*(?:系统图|示意图)`）中 .* 会吞掉后续楼号，
      finditer 只产生一次匹配（span 覆盖全句），后几个楼栋仍然静默丢失。
      补充方案：标题匹配命中后，再用独立的楼号正则 finditer 扫描整句文字，
      展开全部楼号（如 1#、2#、3# → 1/2/3 三个锚点）；
      单楼号标题退化为原逻辑（用 group(1)），保证向后兼容。
    2026-09-13 修正（P0-1）：上述"独立楼号正则"只认 `N#/N号`，对**斜杠并列写法**
      `3/6号楼综合布线系统图` 仍只取到 6 号楼 —— 实测 12 条标题应展开 10 栋，
      实际只出 5 栋（丢 2/3/8/10/12）。现统一改走 parse_bldg_nums()，
      覆盖 `N#` / `N号` / `N#、N#` / `N/M号楼` / `N、M号楼` 全部写法。
    2026-09-15 修正（P0 接线缺陷）：`parse_bldg_nums_ex` 早就返回 `ambiguous`
      （`N-M号楼` 连字符写法语义存疑），文档写明"调用方必须据此列入需人工裁决，
      不得静默按其中一种语义处理"——**但全代码库无任何调用方消费该字段**，
      规则写了没接线。实测后果：柳辛庄标题「1-3号楼综合布线系统图」静默取到
      [1,3]（丢 2#楼），零告警、不入裁决清单，Agent 只能靠手工探查绕过。
      现改为：本函数内改用 parse_bldg_nums_ex；命中区间写法时**必须**打日志
      （未展开→WARNING 明示当前取法与风险；已展开→INFO 记录展开结果）。
      区间是否按 [N..M] 展开由 expand_ranges 控制（None=取模块开关
      EXPAND_BLDG_RANGES，由 CLI `--expand-bldg-ranges` 在**用户确认语义后**开启）。
    """
    anchors = {}
    _dup_hits = []  # (楼名, 先出现text_item, 后出现text_item)：同名锚点显著异位
    _log = log if log is not None else logging.getLogger("ftth_common")
    if expand_ranges is None:
        expand_ranges = EXPAND_BLDG_RANGES
    for t in texts:
        matches = list(title_re.finditer(t["内容"]))
        if not matches:
            continue
        # 展开标题内全部楼号（共享标题 → 多锚点）。
        # 2026-09-13 统一：走 parse_bldg_nums_ex，覆盖 `N#、N#` / `N/M号楼` /
        #   `N、M号楼` / `N#N#` / 区间 `N-M号楼` 全部写法。
        # 禁止再内联楼号正则——旧 `(\d+)[#号]` 对 `3/6号楼` 只取到 6，5 栋静默丢失。
        _nums, _amb = parse_bldg_nums_ex(t["内容"], expand_ranges=bool(expand_ranges))
        nums = [str(n) for n in _nums]
        if _amb:
            # 区间写法「N-M号楼」：语义（并列 vs 区间）文字本身无法判定，
            # 必须显式暴露给人工，不得静默择一。
            _lo, _hi = (min(_nums), max(_nums)) if _nums else (None, None)
            _cm = re.search(r"(\d+)\s*-\s*(\d+)\s*[#号]?\s*楼", t["内容"])
            _rng = "%s-%s" % (_cm.group(1), _cm.group(2)) if _cm else "跨号"
            if expand_ranges:
                _log.info("  [楼栋区间展开] %r：区间 %s 按区间语义展开 → %s"
                          % (t["内容"][:40], _rng, nums))
            else:
                # 2026-09-19：区间语义不再一律挂起 —— 若中间编号在图上**另有独立实体**
                # （`K#楼` / `K号楼` / `K号楼X单元Y层`，且不是这条区间标题自身），属客观
                # 判据，按区间展开并留痕；无证据者维持字面取法并继续告警待人工。
                _lo2 = _hi2 = None
                if _cm:
                    try:
                        _lo2, _hi2 = int(_cm.group(1)), int(_cm.group(2))
                    except (TypeError, ValueError):
                        _lo2 = _hi2 = None
                _ev = bldg_range_evidence(texts, _lo2, _hi2, t)
                if _ev:
                    for _k, _s, _ex, _ey in _ev:
                        if str(_k) not in nums:
                            nums.append(str(_k))
                    nums.sort(key=lambda s: int(s) if str(s).isdigit() else 0)
                    BLDG_RANGE_EXPANDED.append({
                        "标题": str(t.get("内容"))[:60], "区间": _rng,
                        "补入楼栋": [str(e[0]) for e in _ev],
                        "证据": [{"编号": str(e[0]), "文字": e[1], "x": e[2], "y": e[3]}
                                 for e in _ev],
                    })
                    _log.info("  [楼栋区间按证据展开] %r：区间 %s 的中间编号 %s 在图上有独立实体"
                              "证据（%s）→ 按区间语义补入；其余无证据编号仍按字面取。"
                              % (str(t.get("内容"))[:40], _rng, [e[0] for e in _ev],
                                 "、".join("%s\u2190%r" % (e[0], e[1][:18]) for e in _ev)))
                else:
                    _log.warning(
                        "  [楼栋区间待裁决] 标题 %r 命中连字符写法「%s号楼」，"
                        "语义存疑（并列 %s 栋 vs 区间 %s 至 %s 共 %d 栋）；"
                        "当前按**字面**取到 %s —— 若实为区间，将静默少解中间楼栋。"
                        "请向用户确认后加 --expand-bldg-ranges 重跑。",
                        t["内容"][:40], _rng, len(nums), _rng.split("-")[0], _rng.split("-")[-1],
                        (int(_rng.split("-")[-1]) - int(_rng.split("-")[0]) + 1)
                        if "-" in _rng else len(nums), nums)
        # 标题正则自带捕获组：若给出 parse 未覆盖的楼号（自定义写法），一并并入。
        # 用 first_group 安全取组——正则可能是 `\d+号楼` 这种**无捕获组**写法。
        for m in matches:
            g = first_group(m)
            if g is not None and str(g).isdigit() and str(g) not in nums:
                nums.append(str(g))
        if not nums:
            continue
        # 尝试从标题文字中提取完整楼名（含「配套」「商业」等修饰词）
        bm_name = extract_bldg_name(t["内容"])
        # 共享标题（多楼号）时，楼名后缀按楼号逐一展开；单楼号时保留修饰词楼名。
        # 2026-09-15 归一（P1）：楼名**必须归一为 `N#楼`**（修饰词另拼），否则
        #   「4号楼」（单楼号标题取原文）与「4#楼」（多楼号展开时构造）成为两个不同的
        #   key，同栋楼在锚点池里出现两次、x 各异 → 边界被切成两半，户数分到错锚点。
        #   实测柳辛庄：不归一得 14 个锚点（含 1#楼/1号楼 等 5 组重名），归一后 9 个。
        for num in nums:
            楼名 = normalize_bldg_name(bm_name, num)
            if 楼名 in anchors:
                if abs(anchors[楼名]["x"] - t["x"]) <= DUP_ANCHOR_X_TOL:
                    # 同名锚点几乎同位：重复绘制的同一标题，保留先出现的
                    continue
                # 同名锚点出现在显著不同位置：疑似多地块同名楼，登记待终审
                _dup_hits.append((楼名, anchors[楼名], t))
                continue
            anchors[楼名] = t
            if log:
                log.debug(f"  锚点: {楼名} ← {t['内容']!r} @ ({t['x']}, {t['y']})")
    # ---------- 锚点邻域校验（2026-09-15，坑5） ----------
    # 锚点池可能混入"说明文字"：长说明句里含 `N#楼` 且命中标题正则（如
    # 「说明：…7#楼…」）。它一旦进池，x 中分边界即被污染。几何判据：楼栋标题
    # 标注的是系统图，**附近必有成列的楼层刻度**；说明文字周围没有。
    # 阈值教训（同日实测）：合法标题到最近刻度可达 ~3.6×层高（刻度列常偏离
    # 标题 x 约半个图宽），R 必须取 10×层高 且按**条数分级**：
    #   0 条 → 剔除（明确游离）；1~2 条 → 保留并告警（存疑不误杀）；≥3 条 → 保留。
    # 误杀合法锚点的代价（整栋楼分组丢失）远大于留一个杂锚，故宁松勿紧。
    # 全部被剔时不回退为空——更像楼层文字没采到（--text-layer 漏配），保留并告警。
    if anchors:
        _step, _why = floor_step_from_texts(texts, is_floor_text)
        if _step:
            _R = 10.0 * _step
            _floor_pts = [(t["x"], t["y"]) for t in texts if is_floor_text(t.get("内容", ""))]
            _kept, _dropped, _suspect = {}, [], []
            for _name, _t in anchors.items():
                _n = sum(1 for _fx, _fy in _floor_pts
                         if math.hypot(_t["x"] - _fx, _t["y"] - _fy) <= _R)
                if _n == 0:
                    _dropped.append((_name, _t.get("内容", "")))
                else:
                    _kept[_name] = _t
                    if _n < 3:
                        _suspect.append((_name, _n))
            if _dropped and _kept:
                for _n, _txt in _dropped:
                    if log:
                        log.warning("  [锚点剔除] %s ← %r：周围 %.0f 内无楼层刻度文字，"
                                    "判为说明/无关文字（层高锚 %.4g）",
                                    _n, _txt[:30], _R, _step)
                anchors = _kept
            for _n, _c in _suspect:
                if log:
                    log.warning("  [锚点存疑] %s：周围 %.0f 内仅 %d 条楼层刻度，"
                                "已保留，请人工核对是否为真标题", _n, _R, _c)
            if _dropped and not _kept and log:
                log.warning("  所有锚点周围都无楼层刻度（R=%.0f，层高锚 %.4g）——"
                            "更像楼层文字未采到而非锚点全错，保留原锚点；请核查 --text-layer",
                            _R, _step)
                anchors = dict(anchors)
    # ---------- 多地块同名楼守卫终审（2026-09-17 新增） ----------
    # 只对「先出现者经邻域校验后仍保留」的命中裁决：先出现者已被剔除的，冲突随剔除消解。
    # 后出现者用同一邻域判据复核（层高锚 ×10 半径内有无楼层刻度）：无 → 说明文字
    # 恰好命中标题正则，降级 WARNING 跳过；有 → 真标题，硬失败。
    # 无层高锚（量不出层高）时无法复核，按同名异位直接判多地块（宁可早失败，不静默串号）。
    if _dup_hits:
        _step, _why = floor_step_from_texts(texts, is_floor_text)
        _floor_pts = [(t2["x"], t2["y"]) for t2 in texts if is_floor_text(t2.get("内容", ""))]
        _real = []
        for _n, _first, _second in _dup_hits:
            if _n not in anchors:
                continue  # 先出现者已被邻域校验剔除，冲突消解
            if _step:
                _n2 = sum(1 for _fx, _fy in _floor_pts
                          if math.hypot(_second["x"] - _fx, _second["y"] - _fy) <= 10.0 * _step)
                if _n2 == 0:
                    if log:
                        log.warning("  [同名异位存疑] %s ← %r @ (%.0f, %.0f)：周围 %.0f 内无楼层刻度，"
                                    "判为说明/无关文字，不按同名楼处理",
                                    _n, _second.get("内容", "")[:30], _second["x"], _second["y"], 10.0 * _step)
                    continue
            _real.append((_n, _first, _second))
        if _real:
            _lines = ["检测到多地块同名楼：同名楼栋锚点出现在显著不同的 x 位置。"]
            _seen = {}
            for _n, _first, _second in _real:
                _seen.setdefault(_n, set()).update((_first["x"], _second["x"]))
            for _n, _xs in _seen.items():
                _lines.append("  %s：x = %s（共 %d 个不同位置）"
                              % (_n, " / ".join("%.0f" % _x for _x in sorted(_xs)), len(_xs)))
            _lines.append("锚点池按楼名去重，同名楼会互相覆盖（保留先出现者，其余同名楼整栋静默丢失），"
                          "全图解析的楼栋归属不可信。")
            _lines.append("处理：这是多地块图纸 —— 用 split-band 子命令按 y 带切出各地块子 DXF，"
                          "再对每个子图分别跑 parse / coverage 等下游子命令。")
            _lines.append("  · 图上有「N块地」类标注（已实测）时："
                          "`ftth.py split-band --auto --config <config.json> --dxf <全图> "
                          "--out-dir <目录>` —— 由实测锚点自动算分带窗口，先出方案（含每个"
                          "锚点的原文与坐标），核对后再加 --yes 执行；")
            _lines.append("  · 图上无该类标注时：人工量出各带图名 y 后 "
                          "`--band 「名称:ymin:ymax」`（上界取上邻带标题 y、下界取本带标题 y，"
                          "**不得取相邻标题中点**）。")
            raise MultiPlotDuplicateAnchorError("\n".join(_lines))
    if log and anchors:
        log.info("识别到的楼栋锚点:")
        for k, v in sorted(anchors.items(), key=lambda x: x[1]["x"], reverse=True):
            log.info(f'  {k}: ({v["x"]}, {v["y"]})')
    return anchors


# ---------- 多地块分带锚点（2026-09-18 立，唯一权威） ----------
# 背景（实测）：一张 DXF 含多个独立地块、各块楼号从 1 起（同名楼）时，全图 parse 会串号，
#   find_bldg_anchors 的 MultiPlotDuplicateAnchorError 守卫会拦下，既定补救是
#   `ftth.py split-band` 按 y 带切子图。**但 --band 只能人工给 y**：图上早已实测到的
#   「N块地」标注（probe 的 plot_band_annotations）此前**没有任何下游消费** ——
#   规则写了（铁律⑦）、尺寸量了（probe）、执行环节零接线，人被迫手搓 8 条 band spec。
#   本模块把「锚点提取 + 带窗口计算」收成唯一实现，供 probe 与 split_bands.py 共用，
#   禁止任何一方另写一套判据（副本漂移是历次矛盾的根源）。
#
# 锚点判据（客观、可复现、与项目名解耦）：文字去除首尾空白后**恰好等于**「编号 + 地块词」。
#   据此自动排除两类图上真实存在的干扰项：
#     ① 「N块地弱电机房」—— 带附加字的场所标注（x 常落在住宅图内，非图幅锚点）；
#     ② 「5块地、8块地、9块地」—— 跨地块合并标注（编号不止一个）。
#
# 锚点与本带内容的位置关系**不预设**：铁律⑦ 的模型是「本带内容画在标题上方」，
#   但实测存在相反形态（锚点在本带内容之上）。故逐条实测取向（最近楼栋标题在本锚点的
#   下方还是上方），**全部一致才采纳**；取向不一致即报人（rc=2），不猜、不静默择一。
PLOT_BAND_WORDS = ("块地", "地块", "块区", "组团", "分区")
_PLOT_BAND_RE = re.compile(
    r"^\s*(\d+(?:\s*[-–]\s*\d+)?)\s*(%s)\s*$" % "|".join(PLOT_BAND_WORDS))
# 同编号锚点判为「同一处」的 y 容差（绝对，不随图幅缩放）
_PLOT_ANCHOR_SAME_Y_TOL = 10.0


def _txt_fields(t):
    """兼容两种文字实体形态：collect_texts() 的 dict 与 dump_geom 的 [层,x,y,文] 四元组。"""
    if isinstance(t, (list, tuple)):
        if len(t) >= 4:
            return str(t[0]), float(t[1]), float(t[2]), str(t[3])
        return None, None, None, None
    if isinstance(t, dict):
        return (t.get("层"), t.get("x"), t.get("y"),
                str(t.get("内容") if t.get("内容") is not None else t.get("text") or ""))
    return None, None, None, None


def find_plot_band_anchors(texts, max_len=16):
    """提取多地块分带锚点（客观判据，见上方注释）。

    返回 (anchors, excluded, hits)：
      anchors  —— [{"编号","文字","x","y","层"}]，按 y 降序；**同编号只保留一条**
      excluded —— [{"文字","x","y","层","原因"}]，被排除者逐条给原因（不得静默丢）
      hits     —— 全部「含地块词」的命中（含被排除者），供人工核对

    排除规则（写死为客观判据，不含项目特有判断）：
      · 文字含附加字（不严格等于「编号+地块词」）→ 原因「带附加字，非图幅级锚点」
      · 一段文字里出现多个地块编号 → 原因「跨地块合并标注，编号非唯一」
      · 同编号出现在多个 y（间距 > 容差）→ 原因「同编号多位置，锚点不唯一」
      · 文字过长（> max_len）→ 不入 hits（与探针原口径一致）
    """
    hits, anchors_by_num, excluded = [], {}, []
    for t in texts:
        lay, x, y, s = _txt_fields(t)
        if s is None:
            continue
        s = s.strip()
        if not s or len(s) > max_len:
            continue
        if not any(w in s for w in PLOT_BAND_WORDS):
            continue
        item = {"文字": s, "x": round(x, 1), "y": round(y, 1), "层": lay}
        m = _PLOT_BAND_RE.match(s)
        if not m:
            # 含地块词但不严格等于「编号+地块词」：带附加字 / 组合标注
            nums = re.findall(r"\d+(?:\s*[-–]\s*\d+)?", s)
            why = ("跨地块合并标注，编号非唯一（%s）" % "/".join(n.replace(" ", "") for n in nums)
                   if len(nums) > 1 else "带附加字，非图幅级锚点")
            excluded.append(dict(item, 原因=why))
            hits.append(item)
            continue
        num = m.group(1).replace(" ", "")
        item["编号"] = num
        hits.append(item)
        prev = anchors_by_num.get(num)
        if prev is None:
            anchors_by_num[num] = item
        elif abs(prev["y"] - item["y"]) > _PLOT_ANCHOR_SAME_Y_TOL:
            # 同编号多处不同 y：锚点不唯一，两条都剔除并报人（不静默择一）
            excluded.append(dict(item, 原因="同编号多位置，锚点不唯一（已有 y=%.1f）" % prev["y"]))
            excluded.append(dict(prev, 原因="同编号多位置，锚点不唯一（另有 y=%.1f）" % item["y"]))
            anchors_by_num.pop(num, None)
    anchors = sorted(anchors_by_num.values(), key=lambda a: -a["y"])
    return anchors, excluded, hits


def plot_band_windows(anchors, y_top, y_bot, cut_empty_tol=2000.0, all_texts=None):
    """由分带锚点算窗口。返回 (windows, info, err, warns)。

    windows —— [{"名称","ymin","ymax","锚点y","锚点x","锚点文字","锚点层","边界依据"}]
    info    —— {"切点":[...], "取向说明":str, "y_top":.., "y_bot":..}
    err     —— 非 None 表示无法判定，调用方须按 rc=2 报人（不得猜）
    warns   —— [str,...] 独立核对发现的疑点（**不阻塞**，但必须报给人，不得当绿灯）

    切点口径（实测立，2026-09-18）：
      每块地在本带图区内部有一处「N块地」类锚点（其 y 按地块先后单调排开）。
      带与带的切点取**相邻锚点 y 的中点**；首带上界取图幅顶、末带下界取图幅底。
      · 依据：只用「锚点先后顺序 + 相邻中点」这两个客观量，**不预设内容画在锚点
        上方还是下方**，也不依赖锚点与任一标题的固定偏移。
      · 反例（实测）：直接以锚点 y 作切点，会把下邻带的场所标注吞进本带
        （实测 4 条 / 带）；改中点后 0 条越界。
      · 与铁律⑦ 的关系：铁律⑦ 的「带的下界取本带**楼栋标题** y」适用于**没有**
        地块锚点的图；本图有锚点，锚点层级高于楼栋标题，故按锚点切。
    取向说明仅作信息，不参与切分。
    """
    if not anchors:
        return [], {}, "未提取到任何分带锚点（文字形态可能不在地块词表内，请人工补充词表）", []
    if y_top is None or y_bot is None:
        return [], {}, "图幅上下界取不到，无法定分带边界", []
    if y_top <= y_bot:
        return [], {}, "图幅上下界异常（y_top <= y_bot）", []
    if len(anchors) == 1:
        return [], {}, ("只提取到 1 个分带锚点（%s）—— 单一地块无需分带；"
                        "若确为多地块请人工补充词表或改用 --band" % anchors[0]["文字"]), []

    ys = [a["y"] for a in anchors]          # 已按 y 降序
    cuts = [(ys[i] + ys[i + 1]) / 2.0 for i in range(len(ys) - 1)]
    wins = []
    for i, a in enumerate(anchors):
        ymax = y_top if i == 0 else cuts[i - 1]
        ymin = y_bot if i == len(anchors) - 1 else cuts[i]
        wins.append({"名称": a["文字"], "ymin": ymin, "ymax": ymax,
                     "锚点y": a["y"], "锚点x": a["x"], "锚点文字": a["文字"],
                     "锚点层": a.get("层"),
                     "边界依据": ("上界=图幅顶" if i == 0 else "上界=锚点「%s」与「%s」的中点"
                                  % (anchors[i - 1]["文字"], a["文字"]))
                                 + "；"
                                 + ("下界=图幅底" if i == len(anchors) - 1
                                    else "下界=锚点「%s」与「%s」的中点"
                                         % (a["文字"], anchors[i + 1]["文字"]))})
    bad = [w["名称"] for w in wins if not (w["ymin"] < w["ymax"])]
    if bad:
        return [], {}, "以下分带窗口无效（ymin>=ymax）：%s" % "/".join(bad), []

    info = {"切点": cuts, "y_top": y_top, "y_bot": y_bot,
            "取向说明": "（本节不预设取向；切点由锚点中点定）"}
    # 取向仅作信息：锚点与其最近楼栋标题的上下关系
    warns = []
    if all_texts:
        warns = verify_band_split(wins, anchors, all_texts, cut_empty_tol)
    return wins, info, None, warns


def verify_band_split(windows, anchors, texts, cut_empty_tol=2000.0):
    """独立核对分带结果（不阻塞，只报疑点）。返回 [str,...]。

    三项客观核对：
      ① 切点空置：切点 y ± 容差内不得有文字 —— 有则说明切点落在内容里（会切坏）。
      ② 带内自证：文字形如「N块地…」时，其所在带必须是编号 N 那块地的带。
         图纸自身标注与几何切分互相印证；不一致=图纸标注陈旧 或 切点错，须人看。
      ③ 楼栋标题不跨带：每条楼栋标题的「最近锚点」与「所在带」必须一致。
         （最近锚点由标题 y 判，所在带由窗口判 —— 两条独立路径互证。）
    """
    warns = []
    # 归一化为 (层,x,y,文)：兼容 collect_texts 的 dict 与 geom 的四元组
    _T = []
    for t in texts:
        lay, x, y, s = _txt_fields(t)
        if s is not None and y is not None:
            _T.append((lay, _f(x), _f(y), s))
    # ① 切点空置
    for c in [w["ymin"] for w in windows[:-1]]:
        near = [t for t in _T if abs(t[2] - c) <= cut_empty_tol]
        if near:
            warns.append("切点 y=%.1f 附近 %d 条文字（最近 y=%.1f「%s」）——"
                         "切点可能落在内容里，请核对分带"
                         % (c, len(near), near[0][2], str(near[0][3])[:20]))
    # ② 带内自证（用图纸自身的「N块地…」标注）
    import re as _re
    for i, w in enumerate(windows):
        wname = str(w["锚点文字"]).replace(" ", "")
        for t in _T:
            s = str(t[3]).strip()
            m = _re.match(r"^(\d+(?:\s*[-–]\s*\d+)?)\s*(?:%s)" % "|".join(PLOT_BAND_WORDS), s)
            if not m or s == wname:
                continue
            # 合并标注（如「5块地、8块地、9块地」）编号非唯一，不参与自证（已独立报过）
            if len(_re.findall(r"\d+(?:\s*[-–]\s*\d+)?", s)) > 1:
                continue
            if w["ymin"] <= t[2] < w["ymax"] and abs(t[2] - w["ymin"]) > cut_empty_tol:
                num = m.group(1).replace(" ", "")
                if not wname.startswith(num):
                    warns.append("带「%s」内出现标注「%s」(y=%.1f, x=%.1f) —— "
                                 "该标注自述属 %s 块地，与几何切分不符；"
                                 "多为图纸标注陈旧，请人工核对（不得当作已核）"
                                 % (w["名称"], s, t[2], t[1], num))
    # ③ 楼栋标题：最近锚点 vs 所在带
    for t in _T:
        if not is_bldg_title_text(str(t[3])):
            continue
        y = t[2]
        near = min(range(len(anchors)), key=lambda k: abs(anchors[k]["y"] - y))
        inside = next((k for k, w in enumerate(windows) if w["ymin"] <= y < w["ymax"]), None)
        if inside is not None and inside != near:
            warns.append("楼栋标题「%s」(y=%.1f) 最近锚点是「%s」，却落在带「%s」——"
                         "两条独立路径不一致，请核对分带"
                         % (str(t[3])[:24], y, anchors[near]["文字"], windows[inside]["名称"]))
    return warns


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def ent_y(e):
    """取实体代表性 y 坐标（文字/INSERT 用插入点，线段/多段线用顶点均值）。

    唯一实现在此（2026-09-18 上收）：split_bands 与任何需要「按 y 分带」的脚本
    必须共用本函数，否则同一个实体在探针与分带两处落到不同带（副本漂移）。
    """
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


def derive_plot_bands(msp, texts=None, cut_empty_tol=2000.0):
    """一次算齐「分带锚点 + 分带窗口 + 独立核对」——唯一权威入口。

    探针（写画像）与 split-band（切子图）都必须走本函数，**禁止任一方另算一遍**：
    两处各算一次必然出现「画像里的窗口」与「实际切的带」不一致，且无人察觉。

    返回 dict：
      {"锚点":[...], "锚点排除":[...], "命中":[...], "分带窗口":[...],
       "切点":[...], "y_top":.., "y_bot":.., "疑点":[...], "错误": None|str,
       "去向": str}
    """
    if texts is None:
        texts = collect_texts(msp, None, ["MTEXT", "TEXT"])
    anchors, excluded, hits = find_plot_band_anchors(texts)
    ys = [y for y in (ent_y(e) for e in msp) if y is not None]
    y_top = max(ys) if ys else None
    y_bot = min(ys) if ys else None
    wins, info, err, warns = plot_band_windows(anchors, y_top, y_bot,
                                               cut_empty_tol=cut_empty_tol,
                                               all_texts=texts)
    out = {"锚点": anchors, "锚点排除": excluded, "命中": hits,
           "分带窗口": wins, "切点": (info or {}).get("切点", []),
           "y_top": y_top, "y_bot": y_bot, "疑点": warns, "错误": err,
           "去向": ("%d 个分带窗口 → `ftth.py split-band --auto --dxf <图> "
                     "--out-dir <目录>`（先出方案，核对后加 --yes）" % len(wins))
                   if wins else "无可用分带窗口"}
    return out


# ---------- 楼名/楼层工具 ----------
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


def bldg_num(bldg_name):
    """从楼名提取数字（如 '1#楼'→1, '2号楼'→2），失败返回 0。

    注意：**失败返回 0 是本函数的既有语义**（调用点众多、依赖该行为），故保留不变；
    新增代码若需要区分「解析失败」与「真的是 0 号」，请改用
    :func:`parse_unit_key`（失败时返回 None，不冒充 0）。
    """
    m = re.search(r"(\d+)", bldg_name)
    return int(m.group(1)) if m else 0


# ---------- 中文数字（2026-09-18 上提自 verify_coverage_truth.py，全技能唯一实现） ----------
# 上提理由：`cn2num` 原先只存在于 verify_coverage_truth.py 一个文件里，任何新脚本要用
#   就只能再抄一份 —— 「同一逻辑多份实现必然漂移，且漂移后没有任何东西会报错」是本技能
#   反复踩过的坑（判范围 / 楼号解析均已因此收口为共享实现，见 parse_unit_key）。
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


# ---------- fx 聚类通用函数 ----------
def cluster_chain_mean(vals, tol):
    """一维数值聚类（链式锚定 + 取均值中心），返回各簇中心列表。

    与 cluster_by_x 的区别（两者语义不同，不可互换）：
      · 本函数：簇内与**上一个入簇值**比较（链式），阈值判定用 `<=`，簇中心取**均值**。
      · cluster_by_x：簇内与**簇首值**比较，阈值判定用 `<`，簇中心取**簇首值**。
    V形法按列聚 x 需要"链式 + 均值"语义（列内点密集、列间留白），故单独提供。
    """
    vals = sorted(vals)
    out = []
    for v in vals:
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [sum(c) / len(c) for c in out]


def cluster_by_x(items, threshold, x_key=None):
    """
    按 x 坐标聚类，返回聚类列表 [{x, members}, ...]。
    
    参数:
        items: 待聚类的对象列表
        threshold: 聚类阈值（x 距离小于此值的归入同簇）
        x_key: 从对象中取 x 坐标的函数，默认用 ['x'] 键
    
    返回:
        [{x: float, members: [...]}, ...]，按 x 升序排列
    """
    if x_key is None:
        x_key = lambda t: t["x"]
    
    clusters = []
    for item in sorted(items, key=x_key):
        x = x_key(item)
        placed = False
        for c in clusters:
            if abs(c["x"] - x) < threshold:
                c["members"].append(item)
                placed = True
                break
        if not placed:
            clusters.append({"x": x, "members": [item]})
    
    clusters.sort(key=lambda c: c["x"])
    return clusters


# ---------- 楼栋 x 范围计算（中分法） ----------
def _x_groups(items):
    """[(name, x), ...] → [(x, [name, ...]), ...]（x 升序，同一 x 的锚点并组）。

    同一 x 的锚点来自同一份**共享图纸**（一个标题展开出多个楼号），
    语义上应共用同一 x 区间、不得互相中分——否则中间楼栋被切成零宽区间。
    """
    groups = []
    for name, x in sorted(items, key=lambda t: t[1]):
        if groups and abs(x - groups[-1][0]) <= 1e-6:
            groups[-1][1].append(name)
        else:
            groups.append((x, [name]))
    return groups


def _ranges_from_x_groups(groups):
    """按 x 升序的锚点组 → {name: (xmin, xmax)}：相邻中分，首尾按半间距外延。

    首尾不用 ±INF（会吞掉总图区/平面图区文字），而用与最近邻间距的一半外延。
    """
    n = len(groups)
    ranges = {}
    for i, (x, names) in enumerate(groups):
        if n == 1:
            # 只有一个锚点组：给一个合理范围（±1000）
            for name in names:
                ranges[name] = (x - 1000, x + 1000)
            continue
        if i == 0:
            xmin = x - (groups[i + 1][0] - x) / 2
        else:
            xmin = (groups[i - 1][0] + x) / 2
        if i == n - 1:
            xmax = x + (x - groups[i - 1][0]) / 2
        else:
            xmax = (x + groups[i + 1][0]) / 2
        for name in names:
            ranges[name] = (xmin, xmax)
    return ranges


def compute_bldg_ranges_banded(anchors, band_tol=None, log=None):
    """**按 y 分带后再做 x 中分**——多带图纸的楼栋 x 范围。

    参数:
        anchors: [(name, x, y), ...]（也兼容 (name, x) 二元组 → 退化为单带）
        band_tol: 相邻锚点 y 相差不超过本值者视为同一带；None/0 → 单带
                  （等价于 compute_bldg_ranges，用于无分带需求的图纸）
        log: 可选 logger，用于记录分带结论

    为什么需要它：配套楼系统图常与住宅楼系统图**上下分带、x 上互相重叠**。
    跨带统一做 x 中分，会把甲带的标题当成乙带的分界——实测某图 7# 的皮线列
    被切给了 11# 配套（x 中分落错带）。带内中分即可消除该串扰。

    返回 (ranges, bands)：
        ranges 同 compute_bldg_ranges；
        bands = [{"y0": float, "names": [str, ...]}, ...]，供调用方记录分带结论。
    """
    items = [(a[0], a[1], a[2] if len(a) >= 3 else None) for a in anchors]
    if not band_tol or all(y is None for _n, _x, y in items):
        return (_ranges_from_x_groups(_x_groups([(n, x) for n, x, _y in items])),
                [{"y0": None, "names": [n for n, _x, _y in items]}])

    bands = []          # [{"y0": float, "items": [(name, x)]}]
    for name, x, y in sorted(items, key=lambda t: (t[2] is None, t[2])):
        if y is None:
            continue
        if bands and abs(y - bands[-1]["y0"]) <= band_tol:
            bands[-1]["items"].append((name, x))
        else:
            bands.append({"y0": y, "items": [(name, x)]})

    ranges = {}
    band_info = []
    for b in bands:
        ranges.update(_ranges_from_x_groups(_x_groups(b["items"])))
        band_info.append({"y0": b["y0"], "names": [n for n, _x in b["items"]]})
    if log and len(band_info) > 1:
        log.info("楼栋标题按 y 分带 = %d 个带（容差 %.4g）：%s"
                 % (len(band_info), band_tol,
                    " ｜ ".join("带%d(y0=%.1f): %s"
                                % (i + 1, bi["y0"], ",".join(bi["names"]))
                                for i, bi in enumerate(band_info))))
    return ranges, band_info


def compute_bldg_ranges(anchors, total_pad=None):
    """
    根据楼栋锚点计算 x 范围（相邻锚点 x 中分）。
    
    参数:
        anchors: [(name, x), ...] 楼栋锚点列表
        total_pad: 总图区排除容差。若不为 None，则锚点 x 间距 < total_pad 的
                   视为同一区域（总图区），这些锚点不参与 x 范围中分计算的外边界，
                   而是共用同一组范围。
                   （P0-2 修正：总图区的多个标题锚点彼此 x 很近，中分法会把这些锚点
                   之间的文字全部归给最左锚点，且首尾锚点用 ±INF 会导致总图区文字
                   被吞进首楼、末锚点吞入平面图区。）
    
    返回:
        {name: (xmin, xmax), ...}

    2026-09-12 修正（P0-2）：首尾锚点不再用 ±INF，改为用最近邻锚点的 x 范围延伸。
      旧实现首锚点 xmin=-1e9 吞掉左侧所有文字（含总图区），末锚点 xmax=+1e9
      吞掉右侧所有文字（含平面图区）。新实现用首尾锚点与最近邻的中分边界
      向外延伸一个合理距离（最近邻间距的一半），避免无限制吞入其他图区。
    """
    # 分组与区间计算统一走 _x_groups / _ranges_from_x_groups（与分带版共用一份实现，
    # 避免"分带修复只落在其中一个函数上"——镜像铁律）。
    return _ranges_from_x_groups(_x_groups([(a[0], a[1]) for a in anchors]))


# ---------- 带内 (x,y) 归属 + 共享区间识别（2026-09-18 新增） ----------
# 病灶（实测）：旧归属是「纯 x 闭区间 + dict 序先到先得」，完全不看 y。它成立的前提是
#   「x 区间互不重叠」，而这在两种图上不成立：
#     ① **共享锚点**：一张系统图服务多栋（标题原文 `7#、8#、10#住宅光纤入户系统图`），
#        `_x_groups` 已把同 x 锚点并组共用同一区间 → 区间内多栋、先到先得者独占，
#        其余楼栋楼层表整片为空（实测某图 8#/10# 全空、7# 独占 12 条）。
#     ② **上下分带**：配套楼小图与住宅楼大图 x 上重叠 → 分带后区间可重叠，
#        纯 x 归属必错（实测某图 9# 楼实体第 1 列落左界外归了 4# 配套楼、
#        第 2 列超右界成孤儿）。
# 处置原则：**单候选零回归，多候选才启用新判据** —— 与旧实现只在多候选处分叉。
def assign_by_xy(x, y, ranges, anchor_y_of=None, eps=1e-6):
    """按 (x, y) 把点归属到楼栋，返回 (names, reason)。

    参数:
        x, y: 点坐标
        ranges: {楼栋名: (xmin, xmax)}
        anchor_y_of: {楼栋名: 锚点 y}，用于多候选时按 y 就近
        eps: 边界含入容差（浮点比较）

    返回 (names, reason)：
        names = [] → 未命中任何区间（孤儿）
        names = [名] → 唯一归属
        names = [名1, 名2, ...] → **共享区间**，须克隆给组内全部（不是二选一）

    reason 取值（供调用方分类登记，不得当布尔用）：
        "x唯一命中"             —— 与旧实现行为逐位一致
        "共享锚点(同区间N栋)"    —— 一张图服务多栋，按标题原文克隆
        "y就近(候选N)"          —— 区间重叠，取 |y-锚点y| 最小者（几何测量，非推理）
        "y就近+共享克隆(候选N)"   —— 同上前提，但选中项属共享区间 → 返回**整组**
        "重叠无y判据(候选N)"     —— **不静默择一**：调用方须登记为待裁决
        "x未落入任何楼栋区间"    —— 孤儿
    """
    hits = [(b, lo, hi) for b, (lo, hi) in ranges.items() if lo - eps <= x <= hi + eps]
    if not hits:
        return [], "x未落入任何楼栋区间"
    if len(hits) == 1:
        return [hits[0][0]], "x唯一命中"
    keys = {(round(lo, 6), round(hi, 6)) for _b, lo, hi in hits}
    if len(keys) == 1:
        return sorted(b for b, _lo, _hi in hits), "共享锚点(同区间%d栋)" % len(hits)
    if anchor_y_of and y is not None:
        have = [(b, lo, hi) for b, lo, hi in hits if anchor_y_of.get(b) is not None]
        if have:
            def _dy(h):
                return (abs(y - anchor_y_of[h[0]]), -(h[2] - h[1]))
            best = min(have, key=_dy)
            # 2026-09-18 修：选中项若属**共享区间**（一图服务多栋），必须把该组**整组**
            # 返回 —— 否则同组其余楼栋被独吞。实测某图 y 就近分支把这批点全给了同组
            # 其中一栋，致同组另两栋整列落空（8#/10# 楼层表为空）。
            _bk = (round(best[1], 6), round(best[2], 6))
            _grp = sorted(b for b, lo, hi in hits if (round(lo, 6), round(hi, 6)) == _bk)
            if len(_grp) > 1:
                return _grp, "y就近+共享克隆(候选%d)" % len(hits)
            return [best[0]], "y就近(候选%d)" % len(hits)
    # 多候选、且 y 不可比 —— 不猜，交调用方报裁决
    return [], "重叠无y判据(候选%d)" % len(hits)


def column_consensus_y(items, x_key="x", y_key="y", ndigits=6):
    """同 x（精确到 ndigits 位小数）实体视为一条「列」，返回 {id(item): 列的 y 中位}。

    动机（实测，非推理）：跨带 x 重叠时**逐点**按 y 就近归属，会把同一条楼层刻度列
    在带分界处拦腰拆开 —— 实测某图 1F~6F 归住宅、7F~WF 归配套楼，下游表现为
    甲栋少 5 层、乙配套楼多 4 层，且同 x 的另一栋整列落空。
    一条列来自同一张系统图（同一根楼层轴），**不可按 y 拆开**，故判带须以「列」为
    单位取共识（列内 y 中位）。调用方只应对「x 命中多个楼栋区间」的点使用本值，
    其余点仍用自身 y —— 保证单候选点与改造前逐位一致（零回归）。
    """
    buckets = {}
    for it in items:
        x = it.get(x_key)
        if x is None:
            continue
        buckets.setdefault(round(float(x), ndigits), []).append(it)
    out = {}
    for _x, grp in buckets.items():
        ys = sorted(float(it[y_key]) for it in grp if it.get(y_key) is not None)
        if not ys:
            continue
        n = len(ys)
        med = ys[n // 2] if n % 2 else (ys[n // 2 - 1] + ys[n // 2]) / 2.0
        for it in grp:
            out[id(it)] = med
    return out


def group_shared_ranges(ranges):
    """{名:(lo,hi)} → [{"lo":..,"hi":..,"names":[...]}]，只保留 >=2 栋的共享组（x 区间完全相同）。

    用途：出表前显式登记「哪几栋共用同一 x 区间」——共享意味着这些楼的实体/文字
    在几何上不可分，正解是克隆（一张系统图服务多栋）或人工指定，**不得先到先得**。
    """
    g = {}
    for n, (lo, hi) in ranges.items():
        g.setdefault((round(lo, 6), round(hi, 6)), []).append(n)
    return [{"lo": k[0], "hi": k[1], "names": sorted(v)}
            for k, v in sorted(g.items()) if len(v) >= 2]


def bldg_range_diagnostics(ranges, items, featured=None, anchor_y_of=None):
    """区间自检：每栋区间宽、归属条数、x 跨度，以及**孤儿明细**（不猜、只登记）。

    参数:
        ranges: {名:(lo,hi)}
        items: [{"x":..,"y":..,"内容":..}, ...]（待归属的物件；仅读 x/y/内容）
        featured: 判「业务实体」的函数（内容 → bool）；None 则全视为非业务
        anchor_y_of: {名: 锚点 y}

    返回 {"楼栋": [...], "孤儿": [...], "共享组": [...], "异常": [...]}
      「异常」= 区间宽 < 归属条数>0 时的 x 跨度（区间装不下自己的实体）→ 须复核；
      若同时存在**含业务特征的孤儿**，则一并点名（这是实测的"整列被切出去"形态）。
    """
    is_feat = featured or (lambda _c: False)
    rows, orphans = [], []
    for b in sorted(ranges, key=lambda k: ranges[k][0]):
        lo, hi = ranges[b]
        mine = [t for t in items if lo <= t.get("x", 0) <= hi]
        xs = [t["x"] for t in mine]
        rows.append({"楼栋": b, "xlo": lo, "xhi": hi, "宽": hi - lo, "条数": len(mine),
                     "x跨度": (max(xs) - min(xs)) if xs else 0.0,
                     "x最左": min(xs) if xs else None, "x最右": max(xs) if xs else None,
                     "锚点y": (anchor_y_of or {}).get(b)})
    for t in items:
        names, reason = assign_by_xy(t.get("x", 0), t.get("y"), ranges, anchor_y_of)
        if names:
            continue
        near, nd = None, None
        for b, (lo, hi) in ranges.items():
            d = 0.0 if lo <= t["x"] <= hi else min(abs(t["x"] - lo), abs(t["x"] - hi))
            if nd is None or d < nd:
                near, nd = b, d
        orphans.append({"x": t.get("x"), "y": t.get("y"), "内容": t.get("内容"),
                        "最近楼栋": near, "距边界": nd, "业务实体": bool(is_feat(t.get("内容", "")))})
    anomalies = []
    for r in rows:
        if r["条数"] > 0 and r["宽"] < 1e-9:
            anomalies.append({"楼栋": r["楼栋"], "类型": "区间零宽", "宽": r["宽"]})
        elif r["条数"] > 0 and r["x跨度"] > r["宽"] + 1e-6:
            anomalies.append({"楼栋": r["楼栋"], "类型": "跨度超区间", "宽": r["宽"], "x跨度": r["x跨度"]})
    biz_orphans = [o for o in orphans if o["业务实体"]]
    for o in biz_orphans:
        anomalies.append({"楼栋": o["最近楼栋"], "类型": "业务实体被切出区间",
                          "x": o["x"], "距边界": o["距边界"], "内容": o["内容"]})
    return {"楼栋": rows, "孤儿": orphans, "共享组": group_shared_ranges(ranges), "异常": anomalies}


# ---------- 楼层匹配（排序+二分，替代 O(N×M) 遍历） ----------
def match_y_to_floor(y, items, tol=None, y_key=None):
    """
    在一组带 y 坐标的对象中找最近的（排序+二分查找，O(log N)）。
    
    参数:
        y: 待匹配的 y 坐标
        items: 对象列表，格式由 y_key 决定
        tol: 最大容差，超过则返回 (None, distance)
        y_key: 从对象中取 y 坐标的函数。
               默认 None 时，items 格式为 [(name, y), ...]，
               返回 (name, distance)。
               传入 y_key 时，返回 (原始对象, distance)。
    
    返回:
        (匹配对象或名字, distance)
    """
    if not items:
        return None, float("inf")
    
    if y_key is None:
        # 默认模式：items = [(name, y), ...]
        sorted_items = sorted(items, key=lambda ft: ft[1])
        item_ys = [ft[1] for ft in sorted_items]
        get_y = lambda item: item[1]
        get_name = lambda item: item[0]
    else:
        # 自定义模式：用 y_key 取 y 坐标
        sorted_items = sorted(items, key=y_key)
        item_ys = [y_key(it) for it in sorted_items]
        get_y = y_key
        get_name = lambda item: item
    
    import bisect
    idx = bisect.bisect_left(item_ys, y)
    
    candidates = []
    if idx > 0:
        candidates.append(idx - 1)
    if idx < len(sorted_items):
        candidates.append(idx)
    
    best_name, best_dist = None, float("inf")
    for ci in candidates:
        it = sorted_items[ci]
        d = abs(get_y(it) - y)
        if d < best_dist:
            best_dist = d
            best_name = get_name(it)
    
    if tol is not None and best_dist >= tol:
        return None, best_dist
    return best_name, best_dist


# ---------- 区间法楼层归属（统一实现） ----------
def assign_floor_by_interval(y, floor_items, tol=None):
    """
    区间法：y 落在哪两条楼层线之间，归属下方楼层线对应的楼层。
    
    参数:
        y: 待归属的 y 坐标
        floor_items: [(楼层名, y), ...] 楼层线列表
        tol: 最大容差，y 与归属楼层线的距离超过此值则返回 (None, distance)。
             **仅适用于「标注吸线」类场景**（标注就写在层线旁，如户数 / 皮线米数标注）。
             测「分纤箱安装楼层」时**不得传 tol** —— 箱体落点不固定，任何距离闸门都等价于
             「最近楼层线法」（SKILL.md 明文禁止），实测某图曾因小容差闸门导致安装楼层整列落空。
    
    返回:
        (楼层名|None, 距离)
        - y 低于最低楼层线 → (None, 距最低线距离)
        - y 高于最高楼层线 → 归属最高楼层
        - tol 不为 None 且距离超容差 → (None, distance)
    """
    if not floor_items:
        return None, float("inf")
    
    items = sorted(floor_items, key=lambda f: f[1])
    floor_ys = [f[1] for f in items]
    floor_names = [f[0] for f in items]
    
    import bisect
    idx = bisect.bisect_right(floor_ys, y)
    
    if idx == 0:
        # y 低于最低楼层线
        return None, round(abs(y - floor_ys[0]), 1)
    
    fl_name = floor_names[idx - 1]
    dist = round(abs(y - floor_ys[idx - 1]), 1)
    
    if tol is not None and dist > tol:
        return None, dist
    
    return fl_name, dist


# ---------- 图签几何容差自适应估计（2026-09-13 新增） ----------
def _dominant_cluster(vals, rel_tol=0.10):
    """一维数值取主簇：排序后按间隙切分，返回样本最多的那一簇。

    与 analyze_coverage.py 的「层高自适应」同源——不预设绝对阈值，
    改用中位数的量级作相对尺子，使不同坐标尺度的图纸共用同一套判据。
    """
    if not vals:
        return []
    vs = sorted(vals)
    if len(vs) == 1:
        return vs
    thresh = rel_tol * (abs(vs[len(vs) // 2]) or 1.0)
    clusters, cur = [], [vs[0]]
    for a, b in zip(vs, vs[1:]):
        if b - a <= thresh:
            cur.append(b)
        else:
            clusters.append(cur)
            cur = [b]
    clusters.append(cur)
    return max(clusters, key=len)


def _median(xs):
    s = sorted(xs)
    return s[len(s) // 2] if s else 0.0


def cluster_values_by_gap(vals, k=4.0, low_q=0.25):
    """**尺度无关**的一维聚类：在「相邻间隙 > k × 低分位间隙」处切分。

    为什么不用绝对容差（如 `round(x/40)`）：那份 40 是在某一张图纸的坐标尺度上标定
    的，换到层高 15600 的坐标系会把整张图并成一簇。这里的尺子取自数据自身
    ——同一列内坐标抖动（绘图精度）远小于列间距（绘图栅格），二者量级天然分离。

    vals：数值序列；返回按簇分组的列表（每组升序）。
    """
    xs = sorted(vals)
    if len(xs) <= 1:
        return [list(xs)]
    gaps = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    nz = sorted(g for g in gaps if g > 0)
    if not nz:
        return [list(xs)]          # 全部同值
    base = nz[min(len(nz) - 1, int(low_q * len(nz)))] or nz[0]
    thr = base * k
    groups, cur = [], [xs[0]]
    for i, g in enumerate(gaps):
        if g > thr:
            groups.append(cur)
            cur = [xs[i + 1]]
        else:
            cur.append(xs[i + 1])
    groups.append(cur)
    return groups


def measure_column_step(columns, min_n=3):
    """由若干刻度列（每列一组**升序 y**）估计图纸的竖向栅格步长（层高）。

    为什么要「每列一票、跨列取主簇」而不是「取成员最多的那一列」：两者都要防同一个坑
    ——一个楼栋范围内常并存多套刻度（住宅系统图 + 配套系统图，x 只差零点几），把全部
    标签的相邻差混算会得到半格值（如 15 而非 30）→ 所有按层高倍数给的容差整体偏小。
    但只取"最密那一列"同样不可靠：总图/拓扑图区每个箱旁都写一个安装楼层（单列可达 20+
    条、间距只有层高的三分之一），它会以条数压过真正的楼层刻度列，把层高量成 10.27
    而不是 30。故改为**先每列各自算步长，再跨列取主簇**——每条外来列只占一票。

    返回 (步长, 依据)；样本不足返回 (None, 原因)。
    """
    steps = []
    for c in columns:
        if len(c) < min_n:
            continue
        ys = sorted(c)
        dys = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
        dys = [d for d in dys if d > 0]
        if len(dys) < 2:
            continue
        dom = _dominant_cluster(dys, rel_tol=0.20) or dys
        steps.append(_median(dom))
    if not steps:
        return None, "无 ≥%d 条的刻度列，无法量测竖向栅格" % min_n
    dom = _dominant_cluster(sorted(steps), rel_tol=0.20) or sorted(steps)
    step = _median(dom)
    return (step, "%d 个刻度列各自的步长取主簇（%s）→ %.4g"
            % (len(steps), "/".join("%.4g" % s for s in sorted(steps)[:6]), step))


def floor_step_from_texts(texts, is_floor_fn, min_n=3):
    """由楼层标注文字直接量层高（**尺度锚**，供各脚本的自适应阈值共用）。

    texts：collect_texts 的输出（须含 x/y/内容）；is_floor_fn：楼层文字判定函数。
    内部：取楼层文字 (x,y) → x 按 cluster_values_by_gap 聚成刻度列 →
    measure_column_step（每列一票、跨列取主簇，抗总图伪刻度列污染）。

    返回 (步长, 依据)；量不出返回 (None, 原因)。
    """
    rows = [(t["x"], t["y"]) for t in texts if is_floor_fn(t.get("内容", ""))]
    if len(rows) < min_n:
        return None, "楼层标注不足 %d 条，无法量测层高" % min_n
    xs = sorted(x for x, _ in rows)
    cols = []
    for g in cluster_values_by_gap(xs):
        sel = set(round(v, 6) for v in g)
        cols.append(sorted(y for x, y in rows if round(x, 6) in sel))
    return measure_column_step(cols, min_n=min_n)


def validate_scale_anchor(step, texts, lo=1.5, hi=10000.0):
    """校验量出的层高（**尺度锚**）是否可信。返回 (ok, reason)。

    判据：**层高必须与图纸自身的文字高度同量级**——图纸坐标可整体缩放，
    但"一层楼有几个字高"是稳定的排版事实，与坐标尺度无关。

    实测教训：某图楼层标注被污染后量出 step=1.6，而字高约 3.0，
    即"一层楼还没有一个字高"，物理上不可能。后果是全部皮线判为未归属，
    脚本仍 rc=0 照常写出 JSON —— 静默产出空结果
    （违反「静默的错误数据不如失败」纪律）。

    故：step < lo × 字高 → 判为不可信（**下界是主要抓手**，实测命中的就是这一类）；
        step > hi × 字高 → 判为不可信（hi 默认取得极宽，仅作极端值兜底）。
    hi 之所以不设小：**层高/字高的比值在真实图纸里可以到几百倍**
    （坐标单位与字高单位不必同尺），设窄会把正常图纸误杀。
    字高不可得时（texts 未带「高」字段）返回 (True, 跳过校验)——
    此时由调用方自己的其他守门（如未归属占比）兜底。
    """
    heights = [t.get("高") for t in texts if t.get("高")]
    if not heights or not step:
        return True, "字高不可得，跳过锚校验"
    h = _median(sorted(heights))
    if h <= 0:
        return True, "字高中位数为 0，跳过锚校验"
    ratio = step / h
    if ratio < lo:
        return False, ("层高 %.4g 仅 %.2f 倍字高（字高中位数 %.4g）——"
                       "小于 %.1f 倍字高的『层高』在排版上不可能，判定为量测污染"
                       % (step, ratio, h, lo))
    if ratio > hi:
        return False, ("层高 %.4g 达 %.1f 倍字高（字高中位数 %.4g）——"
                       "超出合理上界 %.1f 倍，判定为量测污染" % (step, ratio, h, hi))
    return True, "层高/字高 = %.2f（字高中位数 %.4g）" % (ratio, h)


def _quant(xs, q):
    """简易分位数（q 取 0~1），用于给证据附上分布概要。"""
    s = sorted(xs)
    if not s:
        return 0.0
    return s[min(len(s) - 1, int(q * len(s)))]


# 图签容差量测的算法常数（2026-09-13 集中定义）。
# 这些都是**无量纲比值**，与图纸坐标尺度无关 —— 按技能通用化判据「是否随图纸坐标尺度
# 变化」，它们属于"不变的保留默认值"一类，故**不做成命令行参数**（免得接口变重、
# 又给人"必须调"的错觉）。集中在这里是为了改一处即可全局生效，并便于在证据里复核。
TOL_CLUSTER_REL_TOL = 0.10     # 一维主簇切分阈值（相对中位数）
TOL_CORE_LO = 0.80             # 中心带下界（× 主簇中位数）
TOL_CORE_HI = 1.25             # 中心带上界
TOL_BAND_REL = 0.10            # 配对窗口匹配带宽（相对中位数）
TOL_PAD_REL = 0.02             # 窗口最小外扩（相对中位数；实测极差为 0 时的兜底）


class ToleranceEstimateError(ValueError):
    """几何容差无法按图纸自身结构推定（排版方向异常 / 信号不足）。

    调用方必须把它当作**失败**处理（退出码 2），不得静默退回某个默认值——
    量测不出来却继续跑，产出的窗口要么全空（丢楼）要么过宽（串楼），
    两者都不会自我暴露。
    """
    pass


def filter_titleblock_units(lvu, bl, lvf, gap_ratio=3.0):
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
    """
    anchors = list(bl) + list(lvf)
    if not anchors or not lvu:
        return list(lvu), []
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
    keep = [u for i, u in enumerate(lvu) if i in keep_i]
    drop = [u for i, u in enumerate(lvu) if i not in keep_i]
    return keep, drop


def estimate_titleblock_tolerances(texts, bldg_re, lev_re, unit_re, safety=1.25):
    """按图纸自身的图签行结构，推定 6 个几何容差（读取标注·图签形态专用）。

    为什么需要它：这 6 个值与图纸坐标尺度绑定（不同图纸可差几个数量级），
    SKILL.md 要求「必须实测」，但此前没有配套量测手段，现场只能自己现写探针。
    本函数把量测算法固化，供 probe_titleblock_tolerances.py 与
    read_titleblock_households.py 共用。

    原理（与 analyze_coverage.py 的层高自适应同源）：不预设任何坐标值，
    从图纸自身量出「图签行距」当尺子——
      ① 楼名行 <-> 层户行 的 y 间距  -> dy
      ② 层户行 <-> 单元行 的 y 间距  -> unit_dy
      ③ 同块内标注之间的 x 间距        -> dx / unit_dx
    再乘 safety 得到建议值。统计一律取「主簇」，跨图签块的离群误配会被滤掉。

    为什么按行 y 集合量 unit_dy：单元标注在同一图签块内横向排开，跨度可达数万，
    若先做「单元 -> 层户」最近邻配对会大量串到隔壁块；而「层户行 y」与「单元行 y」
    各自是离散的少数几个值，取最近行差即可，不需要先配对。

    参数:
        texts: [(x, y, 文本), ...]，图签层全部文字
        bldg_re / lev_re / unit_re: 三类标注的匹配正则（fullmatch）
        safety: 安全系数，建议值在实测范围外扩的比例
    返回:
        dict（含 6 个建议值与 "证据"）；找不到楼名或层户时返回 None。
        注意：返回的是**建议值**，用于人工核对；调用方不得据此静默判定结果。
    """
    bl = [(x, y, s) for x, y, s in texts if re.fullmatch(bldg_re, s)]
    lvf = [(x, y, s) for x, y, s in texts if re.fullmatch(lev_re, s)]
    lvu = [(x, y, s) for x, y, s in texts if re.fullmatch(unit_re, s)]
    if not bl or not lvf:
        return None

    ev = {"楼名数": len(bl), "层户数": len(lvf), "单元数": len(lvu)}

    # ① 楼名 <-> 层户：先按 x 最近粗配对，再对 dy 取主簇，滤掉跨块误配
    raw = []
    for v in lvf:
        # 用欧氏距离而非纯 x 距离：一张图常混排多个地块，不同地块的楼名 y 不同，
        # 纯按 x 最近会选到「x 勉强接近但 y 相差很远」的别块楼名（实测配对率仅 16/48）。
        b = min(bl, key=lambda t: (t[0] - v[0]) ** 2 + (t[1] - v[1]) ** 2)
        raw.append((b[0] - v[0], b[1] - v[1]))
    dy_all = [r[1] for r in raw]
    dy_main = _dominant_cluster(dy_all, rel_tol=TOL_CLUSTER_REL_TOL)
    if not dy_main:
        return None
    dy_med = _median(dy_main)
    dy_win = max(1.0, TOL_BAND_REL * abs(dy_med))
    dxs = [abs(r[0]) for r in raw if abs(r[1] - dy_med) <= dy_win]
    if not dxs:
        return None
    dy_pad = max(max(dy_main) - min(dy_main), TOL_PAD_REL * abs(dy_med))
    # 2026-09-15 效率优化：同排布局兜底——分离标注 variant（如 NF + M户/层）中
    # 楼名与层户在同一 y，dy 偏移≈0，主簇退化（min≈max），导致 dy_lo >= dy_hi。
    # 此时用已算出的 dy_win（最小 1.0）作 dy_pad，确保窗口非退化但不过宽。
    if dy_pad < 0.01:
        dy_pad = dy_win
    ev["楼名<->层户"] = {"配对样本": len(dxs), "层户总数": len(lvf),
                     "dy主簇": [round(min(dy_main), 3), round(max(dy_main), 3)],
                     "dy分位": [round(_quant(dy_all, q), 3) for q in (0.05, 0.5, 0.95)],
                     "dx最大": round(max(dxs), 3)}

    out = {
        "dx_tol": round(max(dxs) * safety, 1),
        "dy_lo": round(min(dy_main) - dy_pad * 0.5, 1),
        "dy_hi": round(max(dy_main) + dy_pad * 0.5, 1),
        "unit_dx": None,
        "unit_dy_lo": None,
        "unit_dy_hi": None,
    }

    # ② 层户 <-> 单元：dy 直接按「行 y 集合」量，不需要先配对
    if lvu:
        # 逐「单元」取样，而不是逐「去重后的单元行 y」：同一 y 行上的单元可能属于不同
        # 地块、对应不同的层户行，按行去重会把这种差异抹掉（实测下界因此从 43443 漂到 44783）。
        #
        # 2026-09-13（P0）：**方向约束 + 综合距离**，两者都不能少。
        #   ① 方向：只取单元标注「上方」的层户（v[1] > uy）。解析窗口语义是
        #      `unit_dy_lo <= 层户y - 单元y <= unit_dy_hi`，即默认「单元在层户下方」；
        #      若用无方向最近邻，在「排间距 < 块内间距」的图上会误取到**下一排**的层户：
        #      实测地块A 排间距 35906 < 块内间距 46319，量出 -35906 的**负容差**
        #      （负窗口让该栋全部单元配不上层户 → 静默丢户，且不自我暴露）。
        #   ② 综合距离：候选中按 **|dx| + dy 等权**取，而非单一判据。
        #      两个单一判据各错一半（实测 4 个歧义点，各错 2 个）：
        #        · 「x 最近」在地块A 判反——错的候选 dx=26219 < 对的 31900，但其 dy 差 3 倍；
        #        · 「y 最近」在地块B 判反——错的候选 dy=33860 < 对的 43443，但其 dx 差 20 倍。
        #      等权相加（dx、dy 同量纲，无需归一化）在同一批点上**全部选对**。
        # 2026-09-18 重写（P0，实测某图）——旧实现有两处缺陷，会让单元归属**整体串楼**：
        #   ① 硬方向约束 `v[1] > uy`（＝假设单元恒在层户**下方**）。同一张图的图签表里方向
        #      可以不一致：实测某图左右两栏并列楼栋，左栏单元在楼名行下方、右栏在上方。
        #      方向约束把右栏样本全部排除后，只能退取「上一层楼」的层户行，量出 43~50 的
        #      跨行偏移（真实值 ±4.4），窗口因此**系统性地把每个单元判给它上一层的那栋楼**。
        #   ② `N单元` 在系统图里也出现（每栋系统图楼层列顶部的单元列头），与图签同图层同写法，
        #      一起量容差/配对 ⇒ 单元配到错误楼栋，出现 `1单元×6 / 2单元×5` 重复标签。
        #   实测后果：7 栋里 5 栋单元数错，脚本只打 ⚠、退出码仍为 0（下游按成功消费即得错值）。
        # 现改为：① 先把单元限定在图签块内（同一判据的共享实现，与生产脚本共用一处）；
        #   ② **以楼名行为锚**量偏移（楼名行有「楼号 + 两 x 栏」双重区分度，比层户行稳），
        #      方向无关 —— 窗口跨零是方向混排时的**正确**结果。
        _blk, _blk_out = filter_titleblock_units(lvu, bl, lvf)
        if _blk_out:
            ev['剔除非图签块单元'] = {
                '剔除数': len(_blk_out), '保留数': len(_blk),
                '剔除样例': ['%s@[%.1f,%.1f]' % (d[2], d[0], d[1]) for d in _blk_out[:8]]}
        udy_all = []
        for ux, uy, _ in _blk:
            b0 = min(bl, key=lambda t: abs(t[0] - ux) + abs(t[1] - uy))
            v0 = min(lvf, key=lambda t: abs(t[0] - b0[0]) + abs(t[1] - b0[1]))
            udy_all.append(v0[1] - uy)
        # 已限定在图签块内 ⇒ 样本本身就是块内偏移，无需再聚类剔噪；窗口取样本极差外扩。
        if udy_all:
            udy_sel = udy_all
            udy_med = _median(udy_sel)
            _span = max(udy_sel) - min(udy_sel)
            udy_pad = max(_span, TOL_PAD_REL * max(abs(udy_med), _span))
            _wlo = min(udy_sel) - udy_pad * 0.5
            _whi = max(udy_sel) + udy_pad * 0.5
            uxs = []
            for u in _blk:
                cand = [v for v in lvf if _wlo <= (v[1] - u[1]) <= _whi]
                if not cand:
                    continue
                uxs.append(abs(min(cand, key=lambda t: abs(t[0] - u[0]))[0] - u[0]))
            if uxs:
                p90 = _quant(uxs, 0.9)
                out["unit_dx"] = round(p90 * safety, 1)
                out["unit_dy_lo"] = round(_wlo, 1)
                out["unit_dy_hi"] = round(_whi, 1)
                ev["层户<->单元"] = {"配对样本": len(uxs), "单元总数": len(lvu),
                                 "图签块内单元数": len(_blk),
                                 "dy窗口样本": [round(min(udy_sel), 3), round(max(udy_sel), 3)],
                                 "dy分位": [round(_quant(udy_all, q), 3) for q in (0.05, 0.5, 0.95)],
                                 "dxP90": round(p90, 3), "dx最大": round(max(uxs), 3)}

    # 用到的算法常数写进证据：这些比值不随图纸变化，但写出来才能让"量出来的是建议值"
    # 这件事可复核——换图后若窗口偏窄/偏宽，可据此判断是常数需调还是图纸排版特殊。
    ev["算法常数"] = {"主簇相对阈值": TOL_CLUSTER_REL_TOL,
                   "中心带": [TOL_CORE_LO, TOL_CORE_HI],
                   "匹配带宽": TOL_BAND_REL, "最小外扩": TOL_PAD_REL, "安全系数": safety}

    # ---------- 量测结果自检（2026-09-13，P0）----------
    # 窗口若自相矛盾或跨越 0，说明配对方向相反或配错：跨零窗口会把「另一侧」的标注
    # 也框进来，产出的覆盖数据看着完全正常，实际已串楼。宁可失败，不可静默输出。
    #
    # 2026-09-15 效率优化：同排布局例外——分离标注 variant 中楼名与层户在同一 y，
    # dy 偏移≈0，窗口合法地跨零。当两侧边界都在小范围（|lo|,|hi| ≤ 2.0）内时跳过
    # 跨零校验，仅对「真正有方向性但配对方向搞反」的情况报错。
    # 2026-09-18：跨零校验**只保留给「楼名<->层户」**。「层户<->单元」不再按跨零拦截 ——
    #   该窗口自本次起由**楼名锚定**量出（见上方 ② 的注释），样本本身就是图签块内偏移；
    #   同一张图签表左右两栏方向相反时，跨零是**正确**结果，旧规则会把这类图误判成
    #   「配对方向搞反」而整体中止，反而堵死唯一的量测路径。
    _SAME_LINE_TOL = 2.0
    for _lo_k, _hi_k, _lab in (('dy_lo', 'dy_hi', '楼名<->层户'),
                               ('unit_dy_lo', 'unit_dy_hi', '层户<->单元')):
        _lo, _hi = out.get(_lo_k), out.get(_hi_k)
        if _lo is None or _hi is None:
            continue
        if _lo >= _hi:
            raise ToleranceEstimateError(
                '%s 量出的窗口非法：%s=%.1f >= %s=%.1f。请显式传入容差后复核。'
                % (_lab, _lo_k, _lo, _hi_k, _hi))
        if (_lab == '楼名<->层户' and _lo <= 0 <= _hi
                and not (abs(_lo) <= _SAME_LINE_TOL and abs(_hi) <= _SAME_LINE_TOL)):
            raise ToleranceEstimateError(
                '%s 量出的窗口跨越 0（%s=%.1f, %s=%.1f）：正常排版下楼名应稳定落在'
                '层户标注的同一侧，跨零说明配对方向相反或配错，请显式传入容差后复核。'
                % (_lab, _lo_k, _lo, _hi_k, _hi))

    out["证据"] = ev
    return out
# ---------- 分纤箱图形符号层候选打分（2026-09-16 新增，P0-2） ----------
# 背景：箱符号所在的图层名每张图都不同，而「怎么把它找出来」此前没有实现 ——
#   plan 输出里的 `fx_symbol_layer_suggest` **只有读、没有写**，恒等于
#   「探查未给出候选图层」，测量方无据可依只能猜（实测猜成文字层 → 箱位回退编号
#   文字坐标 → 竖干配对率 0% → 覆盖全空，而脚本仍返回退出码 0）。
#   本函数把「找符号层」变成可复算的打分；输入只需几何缓存（extract_geom / load_geom
#   的产物），不需要重新解析 DXF。
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


def suggest_fx_symbol_layers(polylines, texts, fx_count=None, top=3):
    """给「分纤箱图形符号图层」候选打分（与具体图纸形态解耦，随图自适应）。

    入口参数与几何缓存同构：
      polylines  [[层, [x1,y1,...], closed], ...]   extract_geom / load_geom 的 polylines
      texts      [[层, x, y, 内容], ...]            extract_geom / load_geom 的 texts
    返回按得分降序的候选，每项含 层 / 得分 / 推荐 / 各项明细（供人工核对与复算）。

    四条判据（全部由图纸自身量测，无项目常数）：
      J1 闭合四点矩形，中位宽高 <= 2 x 层高（层高由楼层标注自适应估得；估不出用兜底 60，
         与 analyze_coverage 的 AUTO_FALLBACK 同量级）
      J2 尺寸一致性：同尺寸(±0.1)簇占比 —— 箱符号是同一模板复制，占比接近 1
      J3 与「图纸类词标题的 x 带」重叠率 —— 箱符号画在系统图区，与标题同区
      J4 众数簇数量 ≈ 图上编号数（仅在给出 fx_count 时参与）
    得分 = 一致性 x 标题区重叠 x (0.5 + 0.5 x 数量吻合)
    「推荐」= 一致性 >= 0.8 且 标题区重叠 >= 0.8 且（未给编号数 或 数量吻合）。

    为什么不能只判几何：实测单看「闭合四点矩形 + 小尺寸」时，正确层可被数量更多的
    干扰层（大轮廓、门窗 / 家具块）压到第 3 名；**尺寸一致性 + 与标题同区**才是决定性判据。
    """
    # ---- 文字记录归一（兼容两种形态）----
    _recs = [_txt_fields(t) for t in texts]
    # ---- 标题 x 带（图纸类词标题所在 x 区间；无标题时退化为「含图纸类词」的文字）----
    txs = [r[1] for r in _recs if is_bldg_title_text(r[3])]
    if not txs:
        txs = [r[1] for r in _recs if RE_DRAWING_WORD.search(r[3] or "")]
    if txs:
        _span = max(txs) - min(txs)
        _pad = 0.05 * _span if _span > 0 else 0.0
        band = (min(txs) - _pad, max(txs) + _pad)
    else:
        band = None
    # ---- 层高（随图自适应；估不出用兜底值）----
    # 必须走 ftth_common.floor_step_from_texts（每列一票、跨列取主簇）：
    #   起初本函数用「全部楼层文字的 y 相邻差取众数」，实测被污染 —— 图上存在大量
    #   极短间距的文字，众数落到 0.4，尺寸闸门随之下压到 0.8，真正的符号层
    #   （本例 11.6x4.6）反被 J1 筛掉、候选表里只剩 WINDOW 块。既有估计器正是
    #   为抗这类污染而写（其 docstring 记录了同源踩坑）。
    _step, _step_why = floor_step_from_texts(
        [{"内容": r[3], "x": r[1], "y": r[2]} for r in _recs if is_floor_text(r[3] or "")],
        is_floor_text)
    _size_max = 2.0 * _step if _step else 60.0
    # ---- 逐层收「闭合四点矩形」----
    per = {}
    for it in polylines:
        try:
            lay, pts, closed = it[0], it[1], it[2]
        except Exception:
            continue
        if not closed or len(pts) != 8:
            continue
        xs, ys = pts[0::2], pts[1::2]
        per.setdefault(lay, []).append((max(xs) - min(xs), max(ys) - min(ys), sum(xs) / 4.0))
    out = []
    for lay, rects in per.items():
        if len(rects) < 3:
            continue
        _w = sorted(r[0] for r in rects)
        _h = sorted(r[1] for r in rects)
        if not (_w[len(_w) // 2] <= _size_max and _h[len(_h) // 2] <= _size_max):
            continue
        grp = {}
        for w, h, _x in rects:
            k = (round(w, 1), round(h, 1))
            grp[k] = grp.get(k, 0) + 1
        (mkw, mkh), mode_n = max(grp.items(), key=lambda kv: kv[1])
        cons = mode_n / float(len(rects))
        ov = (sum(1 for _w, _h, x in rects if band and band[0] <= x <= band[1])
              / float(len(rects))) if band else 0.0
        if fx_count:
            close = abs(mode_n - fx_count) <= max(2, 0.15 * fx_count)
            score = cons * ov * (1.0 if close else 0.5)
        else:
            close = None
            score = cons * ov
        out.append({"层": lay, "得分": round(score, 3),
                    "推荐": bool(cons >= 0.8 and ov >= 0.8 and close is not False),
                    "闭合四点矩形": len(rects), "众数簇": mode_n,
                    "一致性": round(cons, 2), "标题区重叠": round(ov, 2),
                    "众数尺寸": "%.1fx%.1f" % (mkw, mkh),
                    "层高估值": (round(_step, 2) if _step else None),
                    "层高依据": _step_why})
    out.sort(key=lambda d: (-d["得分"], d["层"]))
    return out[:top]

# ---------- 图上箱位直写证据（2026-09-19，唯一实现） ----------
# 背景：分纤箱编号文字常落在独立的总图/箱表区（x 不落在任何楼栋标题区间内），
#   此前只能靠人工传 --bldg-map（extract_fx_map 产物）才能认领；不传就整图 0 箱
#   （实测某项目 4 张图 84 个箱、另一图 23 个箱，全部归 0，rc 仍 0）。
#   但图上往往**自己就写着箱位**（「N号楼M单元K层」或「N#楼M单元」），这是 A′ 级
#   直写证据 —— 有能力自动认领却没认领，属「登记了疑点但没拦住结果」。
# 纪律：本段是**全工具链唯一**的直写证据判定实现，extract_fx_map.py 与
#   parse_dxf_structured.py 都调它，不得各抄一份（各抄一份必然漂移）。
import math as _math

# 箱位描述的完整拆分：楼栋号 / 单元号 / 安装层。写法容错：`号楼` 与 `#楼` 都收，
#   单元号可缺省（单单元楼栋）。
DESC_POS_RE = re.compile(r"(\d+)\s*(?:号楼|#?\s*(?:配套|商业|附属)?\s*楼)\s*(?:(\d+)\s*单元)?\s*(\d+)\s*层")
# 仅到单元级的楼栋标注（`N#楼1单元` / `N号楼`），无安装层 —— 信息弱于上者，仅作二级证据。
UNIT_POS_RE = re.compile(r"(\d+)\s*(?:号楼|#?\s*(?:配套|商业|附属)?\s*楼)\s*(?:(\d+)\s*单元)?")


def nearest_unambiguous(x, y, cands, x_key="x", y_key="y"):
    """在候选集里找**几何无歧义**的最近项。

    判据（纯几何、尺度无关、可复核，故属「测量」不属「推理」）：
        d1（到最近项 A 的距离）< 0.5 × dAB（A 与次近项 B 之间的距离）
    推导：由三角不等式 dAB ≤ d1 + d2 ⇒ d2 ≥ dAB − d1 > 0.5·dAB > d1，
        即**最近项严格唯一**——不是"比其他近一点"，而是落在以 A 为圆心、
        半径为 dAB/2 的圆内，该圆内不可能再有第二个候选。
    尺度取自**局部**（A 与 B 的间距）而非全图最小间距：后者会被图上某一处
        特别密集的候选对拉低，导致别处本无歧义的归属被误拒（实测某图因此
        少认 7 个箱）。局部判据同样满足上述推导，严格性不降。

    返回 dict{best, d1, d2, dAB, min_gap, ok}；cands 少于 2 项时 ok=False。
    """
    res = {"best": None, "d1": None, "d2": None, "dAB": None, "min_gap": None, "ok": False}
    if len(cands) < 2:
        return res
    ds = sorted((_math.hypot(x - c[x_key], y - c[y_key]), c) for c in cands)
    d1, best = ds[0]
    d2, second = ds[1]
    dAB = _math.hypot(best[x_key] - second[x_key], best[y_key] - second[y_key])
    min_gap = None
    for i in range(len(ds)):
        for j in range(i + 1, len(ds)):
            g = _math.hypot(ds[i][1][x_key] - ds[j][1][x_key],
                            ds[i][1][y_key] - ds[j][1][y_key])
            if min_gap is None or g < min_gap:
                min_gap = g
    res.update({"best": best, "d1": d1, "d2": d2, "dAB": dAB, "min_gap": min_gap})
    if not dAB:
        return res
    res["ok"] = bool(d1 < 0.5 * dAB)
    return res


def build_fx_direct_evidence(texts, fx_re, max_len=24):
    """从图上文字里直接构建「编号 -> 箱位」的直写证据表。

    两级证据（信息越完整越优先）：
      A′ 级：`N号楼M单元K层` —— 楼栋/单元/安装层三者齐备；
      B′ 级：`N#楼M单元`   —— 只到单元，安装层留给调用方的区间法（纪律：只改归属不改楼层）。
    采纳条件（缺一不可，无法满足则**不采纳、交人工**，绝不猜）：
      ① 编号的每个出现位置都能用 nearest_unambiguous 定出唯一最近候选；
      ② 各位置推出的箱位归一化后**唯一**（同编号多处绘制指向同一箱位才收敛）；
      ③ 编号在同级证据里不与其它编号冲突（此处不做全局分配，冲突由调用方按 ② 判定）。
    返回 (emap, report)；emap[编号] = {楼栋, 单元, 安装楼层, 口径, 证据, 距离, 次近, 最小间距}
    """
    fx_items, desc_items, unit_items = [], [], []
    for t in texts:
        c = str(t.get("内容") or "").strip()
        if not c or len(c) > max_len:
            continue
        if fx_re is not None and fx_re.search(c):
            fx_items.append((fx_re.search(c).group(0).strip(), t))
        elif DESC_POS_RE.fullmatch(c):
            desc_items.append(t)
        elif UNIT_POS_RE.fullmatch(c):
            unit_items.append(t)
    report = {"FX文字": len(fx_items), "A级箱位描述": len(desc_items),
              "B级单元标注": len(unit_items), "采纳": [], "未采纳": []}
    if not fx_items:
        return ({}, report)

    def _try(cands, level):
        """对全部编号在给定候选集上试判，返回 {编号: entry}"""
        out = {}
        _skip = {}
        for fx_id, t in fx_items:
            nu = nearest_unambiguous(t["x"], t["y"], cands)
            best, d1, d2, gap, ok = (nu["best"], nu["d1"], nu["d2"], nu["min_gap"], nu["ok"])
            if not ok:
                _why = ("候选不足 2 个，无从判歧义" if len(cands) < 2 else
                        ("最近距 %.2f ≥ 最近与次近两候选间距的一半 %.2f（几何上有歧义，不猜）"
                         % (d1, 0.5 * nu["dAB"]) if d1 is not None and nu["dAB"]
                         else "无法度量"))
                _skip.setdefault(fx_id, []).append(
                    {"证据": level, "原因": _why,
                     "最近候选": (str(best.get("内容")) if best else None),
                     "最近距": (round(d1, 2) if d1 is not None else None),
                     "次近距": (round(d2, 2) if d2 is not None else None),
                     "最近与次近间距": (round(nu["dAB"], 2) if nu["dAB"] else None),
                     "候选最小间距": (round(gap, 2) if gap else None)})
                continue
            c = str(best.get("内容") or "").strip()
            m = DESC_POS_RE.fullmatch(c) if level == "A" else None
            if level == "A" and m:
                bno, uno, fl = m.group(1), m.group(2), m.group(3)
                # 单元名**不拆**：产物单元粒度由图纸自身的单元划分决定；本证据只解决
                #   「箱属于哪栋楼」+「装在哪一层」。若在此处带上单元名，会出现
                #   「楼层表留在原容器、箱落到新单元」的脱节（下游 join 不上），
                #   且等于凭空引入图上没有独立单元划分的颗粒度。图上单元号原文另行留痕。
                e = {"楼栋": "%s号楼" % bno,
                     "单元": "%s号楼" % bno,
                     "图上单元": ("%s单元" % uno) if uno else None,
                     "安装楼层": "%sF" % fl,
                     "安装楼层口径": "口径A′:图上箱位直写（『N号楼M单元K层』）"}
            else:
                mu = UNIT_POS_RE.fullmatch(c)
                if not mu:
                    continue
                bno, uno = mu.group(1), mu.group(2)
                # 楼栋名保留**原文写法**（含「配套/商业/附属」等修饰词），只去掉尾部单元号。
                #   若统一改写成「N号楼」，锚点是「4#配套楼」这类形态的楼会匹配不上，
                #   配套楼的箱会被 silently 丢掉（实测某图 2 个配套楼箱因此无归属）。
                _bn_full = re.sub(r"\d+\s*单元\s*$", "", c).strip()
                e = {"楼栋": _bn_full,
                     "单元": _bn_full,
                     "楼号": bno,
                     "图上单元": ("%s单元" % uno) if uno else None,
                     "安装楼层": None,
                     "安装楼层口径": "口径B′:图上单元标注直写（仅楼栋/单元，安装层仍走区间法）"}
            e.update({"证据": level, "原文": c, "x": round(t["x"], 2), "y": round(t["y"], 2),
                      "距离": round(d1, 2), "次近": round(d2, 2),
                      "最近与次近间距": round(nu["dAB"], 2), "最小间距": round(gap, 2)})
            out.setdefault(fx_id, []).append(e)
        return out, _skip

    emap = {}
    for level, cands in (("A", desc_items), ("B", unit_items)):
        if not cands:
            continue
        got, skipped = _try(cands, level)
        for fx_id, lst in got.items():
            if fx_id in emap:
                continue                       # 高级证据已覆盖
            keys = {(str(e.get("楼栋")), str(e.get("单元")), str(e.get("安装楼层"))) for e in lst}
            if len(keys) != 1:
                report["未采纳"].append({"编号": fx_id, "证据": level,
                                        "原因": "同编号多处绘制推出的箱位不一致（未自行择一）",
                                        "候选": sorted(keys)[:4]})
                continue
            e = dict(lst[0])
            e["出现次数"] = len(lst)
            emap[fx_id] = e
            report["采纳"].append({"编号": fx_id, "证据": level, "楼栋": e["楼栋"],
                                   "单元": e["单元"], "安装楼层": e["安装楼层"],
                                   "原文": e["原文"], "距离": e["距离"], "次近": e["次近"],
                                   "最小间距": e["最小间距"], "出现次数": len(lst)})
    # 未采纳登记：只有在 A/B 两级都没采纳的编号才报（便于人工一次裁决）
    _adopted = set(emap)
    for _lv, _cands in (("A", desc_items), ("B", unit_items)):
        if not _cands:
            continue
        _, _sk = _try(_cands, _lv)
        for _fid, _rows in _sk.items():
            if _fid in _adopted:
                continue
            _r = dict(_rows[0])
            _r["编号"] = _fid
            _r["出现次数"] = len(_rows)
            report["未采纳"].append(_r)
    report["采纳数"] = len(emap)
    return (emap, report)
