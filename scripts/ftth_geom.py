#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""几何/缓存域（2026-09-26 自 ftth_common.py 抽取，P1）。

DXF 单次全量解析 + geom.json 缓存 + 几何查询 —— I6 性能纪律
（"同一张 DXF 一个任务只做一次全量解析"）的执行层。本模块自包含
（stdlib + 函数内 lazy import ezdxf），禁 import ftth_common /
ftth_naming / ftth_cells；ftth_common 经 `from ftth_geom import *` re-export。
"""

import hashlib
import json
import os
import pickle
import re
import sys

__all__ = [
    '_central_cache_path',
    'load_dxf',
    'GEOM_VERSION',
    '_ATTR_VAL_MAX',
    'extract_geom',
    'load_geom',
    'collect_texts',
    'median_text_height',
    'point_rect_dist',
]



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
    失败时打印错误并 sys.exit(2)（C2输入类，与ledger_elements:135对齐）。
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
        sys.exit(2)  # C2 rc=2：DXF不可读/解析失败（输入类）
    for cand in (cache, legacy_cache):
        if not os.path.exists(cand):
            continue
        try:
            with open(cand, "rb") as f:
                blob = pickle.load(f)
            if blob.get("mtime") == st.st_mtime and blob.get("size") == st.st_size:
                doc = blob["doc"]
                return doc, doc.modelspace()
        except Exception as _e:
            # 缓存损坏或 pickle 版本不兼容 → 回退重新解析。
            # 永久设计（非过渡态，不写退役条件）：缓存缺失路径恒正确，重算慢但对；
            # 可见性：debug 留痕（默认不可见，--verbose 可查），不静默。
            if log is not None and hasattr(log, "debug"):
                log.debug("几何缓存 %s 不可用（%s），回退全量解析" % (cand, _e))
            continue
    import ezdxf
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
    except OSError as e:
        # C2 rc=2：DXF 不可读（输入类）。**OSError 而非 IOError**：IOError 是 OSError
        # 的别名，此处写 IOError 只会让人以为二者不同（实测 merge_json.py 已因此
        # 在写盘失败处漏判 rc=4）。读文件失败的正确类是 OSError/FileNotFoundError。
        if log:
            log.error(f"无法读取DXF文件: {path}\n{e}")
        else:
            print(f"无法读取DXF文件: {path}\n{e}")
        sys.exit(2)
    except Exception as e:
        if log:
            log.error(f"解析DXF时出错: {path}\n{e}")
        else:
            print(f"解析DXF时出错: {path}\n{e}")
        sys.exit(2)  # C2 rc=2：DXF 解析失败（输入类）
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
        sys.exit(2)  # C2 rc=2：DXF不可读/解析失败（输入类）
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


def point_rect_dist(px, py, rect):
    """点到轴对齐矩形 (x0,x1,y0,y1) 的最短距离；点在矩形内返回 0。"""
    x0, x1, y0, y1 = rect
    dx = 0.0 if x0 <= px <= x1 else (x0 - px if px < x0 else px - x1)
    dy = 0.0 if y0 <= py <= y1 else (y0 - py if py < y0 else py - y1)
    return (dx * dx + dy * dy) ** 0.5
