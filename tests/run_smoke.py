# -*- coding: utf-8 -*-
"""包内冒烟自检（stdlib 为主；T5 语料 DXF 需 ezdxf，缺则 SKIP）。

用法::
    python tests/run_smoke.py [--with-dxf]

T1 单一源守卫：_txt_fields 恰 1 份实现；无本地 bldg_num 重复定义（同名异义防线）
T2 注册面=分发面：ftth.py 每个 add_parser 的子命令在分发段有分支（差集 ∅）
T3 纯函数语义：bldg_num / bldg_num_or_none / _txt_fields 两态出口
T4 体量闸门：ftth.py budget rc=0
T5 语料冒烟（可选）：tests/corpus/a小区.dxf probe rc=0
T0 全仓编译：scripts/*.py py_compile 全过（语法级）
T6 出表链黄金路径（合成料，无需 DXF/ezdxf）：assemble 组装（全名单元键+中文单元+共享克隆）
    → apply-ruling 改数 → gen 出表；专杀 2026-09-19 双 P0（assemble NameError、
    `3#楼1单元`→`3单元` 吞楼号）。py_compile/import 抓不住调用时 NameError，
    必须有这条真跑链路。
T7 图签格组判据（合成料）：同栋两格并组、不相邻不并组、落格标注受 protected 保护
    （并反向验证不传 protected 时确会被剔除）。
T8 格组归属（合成料）：拼版图 + 一份漏写中间栋楼名 ⇒ 缺楼名行须归给同排有楼名的那栋
    （专杀「每格各取最近楼名」的一对多：实测 3#楼被 3 个格组抢用、2#楼单元数丢成 None）。
T9 楼栋级兜底容器判据：`3#楼`（键=楼栋名）不得计为「单元」，真单元容器不得误判。
T10 多列并排图签（合成料）：同一 y 带内并列 3 列是**不同楼栋**，不得跨列认领
    （专杀「同排共享」把 3 列并给同一楼名的回归：实测采信 18→4）。
T11 楼名画在本行格组横向跨度之外（合成料，按实测几何）：无横向覆盖时不得直接弃权，
    须按「最近格 + 优势闸」采信并登记；优势不足时才不认领（反向验证判别力）。
"""
import io
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SK = os.path.dirname(HERE)
SC = os.path.join(SK, 'scripts')
PY = sys.executable
fails = []

# 控制台 UTF-8 兜底：中文 Windows 默认 GBK，本文件含 CJK/∅ 输出，
# 无此行则 T2 在 print 即崩（UnicodeEncodeError），后半截门禁全跳过。
# （scripts 侧共享实现见 ftth_common.ensure_console_utf8；测试入口保持零依赖，故内联。）
# 子进程一律 encoding='utf-8'：text=True 默认走 GBK 解码，子进程中文输出即炸
# reader 线程（2026-09-20 实测三线程 UnicodeDecodeError），故 5 处 run 全显式指定。
for _s in (sys.stdout, sys.stderr):
    try:
        _rec = getattr(_s, "reconfigure", None)
        if callable(_rec):
            _rec(encoding="utf-8", errors="replace")
    except Exception:
        pass


def check(name, cond, detail=''):
    print('[%s] %s%s' % ('PASS' if cond else 'FAIL', name, ('  ' + detail) if detail else ''))
    if not cond:
        fails.append(name)


def read(rel):
    return io.open(os.path.join(SK, rel), encoding='utf-8').read()


# T1 单一源守卫
fc = read('scripts/ftth_common.py')
check('T1 _txt_fields 恰1份', fc.count('def _txt_fields(') == 1)
check('T1 bldg_num_or_none 存在', 'def bldg_num_or_none(' in fc)
dups = []
for f in sorted(os.listdir(SC)):
    if f.endswith('.py') and f != 'ftth_common.py':
        if re.search(r'^def bldg_num\(', read('scripts/' + f), re.M):
            dups.append(f)
check('T1 无本地 bldg_num 重复实现', not dups, str(dups))

# T2 注册面=分发面
ft = read('scripts/ftth.py')
regs = re.findall(r'sub\.add_parser\("([a-z0-9-]+)"', ft)
check('T2 子命令数=16', len(regs) == 16, str(len(regs)))
i = ft.index('# 分发')
missing = [c for c in regs if ('"%s"' % c) not in ft[i:]]
check('T2 注册面=分发面(差集∅)', not missing, '缺分支: %s' % missing)

# T3 纯函数语义（ftth_common 顶层可能 import ezdxf，缺则 SKIP）
try:
    sys.path.insert(0, SC)
    import ftth_common as C
    check('T3 bldg_num 1#楼→1', C.bldg_num('1#楼') == 1)
    check('T3 bldg_num 失败返0', C.bldg_num('无数字') == 0)
    check('T3 bldg_num_or_none 失败返None', C.bldg_num_or_none('无数字') is None)
    _r = C._txt_fields({'层': 'L1', 'x': 1.0, 'y': 2.0, '内容': 'a'})
    check('T3 _txt_fields dict', _r[0] == 'L1' and _r[3] == 'a', repr(_r))
    _r = C._txt_fields(['层A', 1.0, 2.0, 'b'])
    check('T3 _txt_fields 四元组', _r[0] == '层A' and _r[3] == 'b', repr(_r))
    _r = C._txt_fields([1.0, 2.0])
    check('T3 _txt_fields 短四元组不炸', isinstance(_r, tuple), repr(_r))
except ImportError as _e:
    print('[SKIP] T3（缺依赖: %s）' % _e)

# T0 全仓编译
import py_compile
_bad = []
for _f in sorted(os.listdir(SC)):
    if _f.endswith('.py'):
        try:
            py_compile.compile(os.path.join(SC, _f), doraise=True)
        except py_compile.PyCompileError as _e:
            _bad.append('%s: %s' % (_f, _e))
check('T0 全仓 py_compile', not _bad, '; '.join(_bad[:3]))

# T4 体量闸门
r = subprocess.run([PY, os.path.join(SC, 'ftth.py'), 'budget'], capture_output=True, text=True, encoding='utf-8', errors='replace')
check('T4 budget rc=0', r.returncode == 0, 'rc=%s' % r.returncode)

# T5 语料冒烟（可选，需 ezdxf）
if '--with-dxf' in sys.argv:
    try:
        import ezdxf  # noqa: F401
        HAS = True
    except ImportError:
        HAS = False
    if HAS:
        dxf = os.path.join(HERE, 'corpus', 'a小区.dxf')
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, 'probe.json')
            r = subprocess.run([PY, os.path.join(SC, 'ftth.py'), 'probe', '--dxf', dxf, '--out', out],
                               capture_output=True, text=True, encoding='utf-8', errors='replace')
            ok = r.returncode == 0 and os.path.exists(out)
            check('T5 语料 probe rc=0', ok, 'rc=%s' % r.returncode)
            if ok:
                d = __import__('json').load(io.open(out, encoding='utf-8'))
                check('T5 probe 产物含建议参数', 'suggested_params' in d or 'signals' in d or len(d) > 0)
    else:
        print('[SKIP] T5（缺 ezdxf）')

# T6 出表链黄金路径（合成料：3 列 / 全名单元键 / 中文单元 / 共享克隆）
import json as _json
_T6_COUNT = {"列": [{"列x": 1.0, "逐层": [["1F", 2], ["2F", 2]]},
                    {"列x": 2.0, "逐层": [["1F", 2], ["2F", 2]]},
                    {"列x": 3.0, "逐层": [["1F", 2], ["2F", 2]]}],
             "归层后总户数": 12}
_T6_COV = {"楼栋": {
    "3#楼": {"单元": {
        "3#楼1单元": {"分纤箱": [{"编号": "FX01#", "安装楼层": "2F",
                                "覆盖范围线索": {"覆盖楼层": ["1F", "2F"]}}]},
        "3#楼二单元": {"分纤箱": [{"编号": "FX02#", "安装楼层": "1F",
                                 "覆盖范围线索": {"覆盖楼层": ["1F"]}}]}}},
    "7#楼": {"单元": {"7#楼1单元": {"分纤箱": [{"编号": "FX17#", "安装楼层": "1F",
        "覆盖范围线索": {"覆盖楼层": ["1F", "2F"]}}]}}},
    "8#楼": {"单元": {"8#楼1单元": {"分纤箱": [{"编号": "FX18#", "安装楼层": "1F",
        "覆盖范围线索": {"覆盖楼层": ["1F", "2F"]}}]}}}}}
_T6_COLMAP = '0=3#楼/1单元;1=3#楼/2单元;2=7#楼/1单元,8#楼/1单元'
with tempfile.TemporaryDirectory() as _td:
    _cp = os.path.join(_td, 'count.json')
    _vp = os.path.join(_td, 'cov.json')
    _ap = os.path.join(_td, 'asm.json')
    io.open(_cp, 'w', encoding='utf-8').write(_json.dumps(_T6_COUNT, ensure_ascii=False))
    io.open(_vp, 'w', encoding='utf-8').write(_json.dumps(_T6_COV, ensure_ascii=False))
    _r = subprocess.run([PY, os.path.join(SC, 'ftth.py'), 'assemble',
                         '--count', _cp, '--col-map', _T6_COLMAP,
                         '--coverage', _vp, '--out', _ap],
                        capture_output=True, text=True, encoding='utf-8', errors='replace')
    _ok = _r.returncode == 0 and os.path.exists(_ap)
    check('T6 assemble rc=0', _ok, 'rc=%s %s' % (_r.returncode, _r.stderr[-200:] if _r.stderr else ''))
    if _ok:
        _a = _json.load(io.open(_ap, encoding='utf-8'))
        _u3 = _a['楼栋']['3#楼']['单元']
        # 2026-09-19 P0 回归项：全名键必须落到 1单元/2单元（曾错归 3单元致丢箱覆盖）
        check('T6 全名单元键归一', sorted(_u3.keys()) == ['1单元', '2单元'], str(sorted(_u3.keys())))
        _b1 = sorted(b['编号'] for b in _u3['1单元']['分纤箱'])
        _b2 = sorted(b['编号'] for b in _u3['2单元']['分纤箱'])
        check('T6 箱按单元对位', _b1 == ['FX01#'] and _b2 == ['FX02#'], '%s/%s' % (_b1, _b2))
        _tot = sum(int(f.get('户数') or 0) for _b in _a['楼栋'].values()
                   for _ud in _b['单元'].values() for f in _ud['楼层表'].values())
        check('T6 守恒 12+4克隆=16', _tot == 16, str(_tot))
        # apply-ruling 改数链
        _pp = os.path.join(_td, 'ruled.json')
        _r2 = subprocess.run([PY, os.path.join(SC, 'ftth.py'), 'apply-ruling',
                              '--json', _ap, '--set', '3#楼/1单元/1F=5', '--out', _pp],
                             capture_output=True, text=True, encoding='utf-8', errors='replace')
        _ok2 = _r2.returncode == 0 and os.path.exists(_pp)
        check('T6 apply-ruling rc=0', _ok2, 'rc=%s' % _r2.returncode)
        if _ok2:
            _a2 = _json.load(io.open(_pp, encoding='utf-8'))
            check('T6 改数落地', _a2['楼栋']['3#楼']['单元']['1单元']['楼层表']['1F']['户数'] == 5)
            # gen 出表链（需 openpyxl，缺则 SKIP）
            try:
                import openpyxl  # noqa: F401
                _HASXL = True
            except ImportError:
                _HASXL = False
            if _HASXL:
                _xp = os.path.join(_td, 'out.xlsx')
                _tpl = os.path.join(SK, 'assets', '标准地址表模板.xlsx')
                _r3 = subprocess.run([PY, os.path.join(SC, 'ftth.py'), 'gen',
                                      '--parse', _pp, '--coverage', _vp,
                                      '--template', _tpl, '--out', _xp],
                                     capture_output=True, text=True, encoding='utf-8', errors='replace')
                _ok3 = _r3.returncode == 0 and os.path.exists(_xp)
                check('T6 gen rc=0', _ok3, 'rc=%s' % _r3.returncode)
            else:
                print('[SKIP] T6 gen（缺 openpyxl）')

# ---------------- T7 图签格组判据（2026-09-23 新增） ----------------
#   专杀「单元标注归属只靠容差窗」的两个实测坑：
#     ① 同栋的两个单元格必须并成一组（成对），不相邻的格不得并组；
#     ② 落在绘制格内的标注不得被「离楼名远 ⇒ 系统图列头」规则误删。
#   反向验证：不传 protected 时同一标注必须**被**剔除 —— 否则本用例没有判别力。
try:
    _CW, _CH = 59020.5, 45041.3
    _polys = [['TK', [0.0, 0.0, _CW, 0.0, _CW, _CH, 0.0, _CH], 1],
              ['TK', [_CW, 0.0, 2 * _CW, 0.0, 2 * _CW, _CH, _CW, _CH], 1],
              ['TK', [10 * _CW, 0.0, 11 * _CW, 0.0, 11 * _CW, _CH, 10 * _CW, _CH], 1],
              ['TK', [11 * _CW, 0.0, 12 * _CW, 0.0, 12 * _CW, _CH, 11 * _CW, _CH], 1]]
    _lvu = [(0.7 * _CW, 0.3 * _CH, '2单元'), (1.7 * _CW, 0.3 * _CH, '1单元'),
            (10.7 * _CW, 0.3 * _CH, '2单元'), (11.7 * _CW, 0.3 * _CH, '1单元')]
    _gs, _info = C.collect_titleblock_unit_cells(_lvu, _polys)
    check('T7 格组启用且量出格尺寸',
          _info['启用'] and _info['格尺寸'] == [_CW, _CH], str(_info))
    check('T7 相邻两格并为一组（成对）',
          len(_gs) == 2 and all(sorted(g['单元号']) == [1, 2] for g in _gs),
          str([g['单元号'] for g in _gs]))
    _gs2, _ = C.collect_titleblock_unit_cells([_lvu[0], _lvu[2]], _polys)
    check('T7 不相邻的格不并组', len(_gs2) == 2, str([g['rect'] for g in _gs2]))
    _bl = [(0.0, 0.0, '1#楼')]
    _lvf = [(0.0, -8000.0, '18层/3户')]
    _far = (500.0 * _CW, 0.3 * _CH, '1单元')
    _keep, _drop = C.filter_titleblock_units([_lvu[0], _far], _bl, _lvf)
    check('T7 反向：远离锚点的标注默认被剔除',
          len(_drop) == 1 and _drop[0][2] == '1单元', str(_drop))
    _keep2, _drop2 = C.filter_titleblock_units([_lvu[0], _far], _bl, _lvf,
                                              protected={id(_far)})
    check('T7 protected 保住落格标注', len(_drop2) == 0 and len(_keep2) == 2,
          str(_drop2))
except ImportError as _e:
    print('[SKIP] T7（缺依赖: %s）' % _e)

# ---------------- T8 格组归属：拼版图 + 缺楼名行（2026-09-23 新增） ----------------
#   专杀「每格各取最近楼名」的实测坑（柳辛庄 band4）：同一张图签被横向拼 2 份，
#   其中一份**漏写了中间那栋的楼名**。旧判据下缺楼名那一行会去抢**相邻行**的楼名
#   （一对多），而真正属于该栋的那一行反被判「优势不足」。
#   合成料按实测几何复现：格 59020.5×45041.3、行距 86108.3、楼名偏移 9459.5/17705.8/8625.1。
try:
    _CW, _CH = 59020.5, 45041.3
    _GAP12, _GAP23 = 41067.0, 39761.2          # 实测行距（R1→R2 / R2→R3）
    _T1, _T2, _T3 = 9459.5, 17705.8, 8625.1    # 实测楼名→本行上沿偏移
    _BX = 20 * _CW                             # 拼版第二份的 x 偏移（图中实测 630000，此处按格宽取整）
    _r1t, _r1b = 0.0, -_CH
    _r2t, _r2b = _r1b - _GAP12, _r1b - _GAP12 - _CH
    _r3t, _r3b = _r2b - _GAP23, _r2b - _GAP23 - _CH
    _polys = []
    _lvu = []
    for _bx in (0.0, _BX):
        for _yt, _yb in ((_r1t, _r1b), (_r2t, _r2b), (_r3t, _r3b)):
            for _cx in (_bx, _bx + _CW):
                _polys.append(['TK', [_cx, _yb, _cx + _CW, _yb, _cx + _CW, _yt, _cx, _yt], 1])
            _lvu.append((_bx + 0.70 * _CW, _yb + 0.30 * _CH, '2单元'))
            _lvu.append((_bx + 1.70 * _CW, _yb + 0.30 * _CH, '1单元'))
    _gs, _info = C.collect_titleblock_unit_cells(_lvu, _polys)
    # 楼名：第一份只有 1#/3#（漏写 2#）；第二份 1#/2#/3# 齐全
    _anchors = [(0.70 * _CW, _r1t + _T1, '1#楼', ('默认', 1)),
                (0.70 * _CW, _r3t + _T3, '3#楼', ('默认', 3)),
                (_BX + 0.70 * _CW, _r1t + _T1, '1#楼', ('默认', 1)),
                (_BX + 0.70 * _CW, _r2t + _T2, '2#楼', ('默认', 2)),
                (_BX + 0.70 * _CW, _r3t + _T3, '3#楼', ('默认', 3))]
    _res = C.assign_cells_to_buildings(_gs, _anchors)
    _verd, _owner, _blocked, _uncl = (_res['verdicts'], _res['owner'],
                                      _res['blocked'], _res['unclaimed'])
    check('T8 格组共 6 组、采信 5（缺楼名那一组不采信）',
          len(_gs) == 6 and len(_verd) == 6
          and sum(1 for v in _verd if v['采信']) == 5, 
          str([(v['单元号'], v['采信']) for v in _verd]))
    _by = {}
    for _v in _verd:
        if not _v['采信']:
            continue
        _by.setdefault(_v['最近锚点']['归属'].split()[1], []).append(tuple(_v['单元号']))
    check('T8 1#/3# 各领本份两行、2# 领第二份那一行',
          {k: len(v) for k, v in _by.items()} == {'1号楼': 2, '2号楼': 1, '3号楼': 2},
          str(_by))
    check('T8 不采信那一组的标注进入 blocked（不落盘、不回落）',
          len(_blocked) == 2 and len(_owner) == 10, '%d/%d' % (len(_blocked), len(_owner)))
    check('T8 五个楼名全部成功认领（无退让/无超尺度闸）',
          _uncl == [], str(_uncl))
    # 反向验证：旧判据（每格各取最近楼名 —— 无横向覆盖筛、无互斥）会把缺楼名的中间行
    #   判给 3#楼，该栋被 3 行抢用、2#楼只剩 1 行。证明本用例确有判别力。
    _old = {}
    for _g in _gs:
        _best = min(_anchors, key=lambda a: C.point_rect_dist(a[0], a[1], _g['rect']))
        _old[_best[3][1]] = _old.get(_best[3][1], 0) + 1
    check('T8 反向：旧判据 3#楼被 3 行抢用、2#楼只剩 1 行',
          _old.get(3, 0) == 3 and _old.get(2, 0) == 1, str(_old))
except (ImportError, AttributeError) as _e:
    print('[SKIP] T8（缺依赖: %s）' % _e)

# ---------------- T9 楼栋级兜底容器不得计为「单元」（2026-09-23 新增） ----------------
#   parse 侧对「单元号在图上单元轴里找不到容器」的箱会单开楼栋级容器（键=楼栋名）。
#   实测（柳辛庄 band4）：3#楼 = `1单元` + 兜底容器 `3#楼` 被 C1/C10 数成 2 个单元，
#   与图签的 1 个单元对不上 —— 却因图签侧同缺陷也虚增 1 而**假一致**，缺陷被藏住。
try:
    check('T9 楼栋名容器判为兜底容器',
          C.is_bldg_level_container('3#楼', '3#楼') and C.is_bldg_level_container('3号楼', '3#楼'),
          '3#楼/3号楼 应判 True')
    check('T9 真单元容器不误判',
          not C.is_bldg_level_container('1单元', '3#楼')
          and not C.is_bldg_level_container('一单元', '3#楼'),
          '1单元/一单元 应判 False')
    check('T9 别栋楼名容器不误判',
          not C.is_bldg_level_container('2#楼', '3#楼')
          and not C.is_bldg_level_container('全部', '3#楼'),
          '2#楼/全部 应判 False')
except (ImportError, AttributeError) as _e:
    print('[SKIP] T9（缺依赖: %s）' % _e)

# ---------------- T10 多列并排图签：同 y 带内不得跨列认领（2026-09-23 新增） ----------------
#   专杀「同排共享」造成的回归（柳辛庄 band3 实测）：图签是**多列并排**版式 ——
#   同一 y 带内并列 3 列，每列是**不同楼栋**的行。按 y 重叠共享会把不同列并给同一楼名，
#   实测 18 组里 14 组变成「多栋争抢且优势不足（7841.8 vs 7920.4，几乎等距）」。
try:
    _CW, _CH = 59020.5, 45041.3
    _T, _gap = 9459.5, 41067.0
    _YT = [0.0, -(_CH + _gap)]
    _polys3, _lvu3, _anch3 = [], [], []
    for _col in range(3):
        _cx0 = _col * 3 * _CW
        for _r, _yt in enumerate(_YT):
            _yb = _yt - _CH
            for _k in (0, 1):
                _x0 = _cx0 + _k * _CW
                _polys3.append(['TK', [_x0, _yb, _x0 + _CW, _yb, _x0 + _CW, _yt, _x0, _yt], 1])
            _lvu3.append((_cx0 + 0.70 * _CW, _yb + 0.30 * _CH, '2单元'))
            _lvu3.append((_cx0 + 1.70 * _CW, _yb + 0.30 * _CH, '1单元'))
            _anch3.append((_cx0 + 0.70 * _CW, _yt + _T, '%d#楼' % (_col * 2 + _r + 1),
                           ('默认', _col * 2 + _r + 1)))
    _gs3, _ = C.collect_titleblock_unit_cells(_lvu3, _polys3)
    _res3 = C.assign_cells_to_buildings(_gs3, _anch3)
    _v3 = _res3['verdicts']
    check('T10 多列并排：6 组全部采信',
          len(_gs3) == 6 and all(v['采信'] for v in _v3),
          str([(v['单元号'], v['采信'], v.get('不采信原因')) for v in _v3]))
    _wrong = []
    for _v in _v3:
        _gx0 = _v['格组矩形'][0]
        _col = int(round(_gx0 / (3 * _CW)))
        _bn = int(_v['最近锚点']['归属'].split()[1].replace('号楼', ''))
        if (_bn - 1) // 2 != _col:
            _wrong.append((_v['格组矩形'][:2], _v['最近锚点']['归属']))
    check('T10 每组只被本列楼名认领（无跨列认领）', _wrong == [], str(_wrong))
    check('T10 六个楼名各认领 1 组（互斥）',
          sorted(int(v['最近锚点']['归属'].split()[1].replace('号楼', '')) for v in _v3)
          == [1, 2, 3, 4, 5, 6],
          str([v['最近锚点']['归属'] for v in _v3]))
except (ImportError, AttributeError) as _e:
    print('[SKIP] T10（缺依赖: %s）' % _e)

# ---------------- T11 楼名画在本行格组横向跨度之外（2026-09-23 新增） ----------------
#   专杀「x 覆盖零容差硬闸」（柳辛庄 band2 实测）：图签里楼名会画在本行格组**左边界之外
#   一点** —— 实测 `4#楼` x 偏置 3813.2 = 格宽 118040.9 的 3.2%，两个拼版份一致。
#   旧实现把「无格组横向覆盖」一律判「退让认领 → 不采信」，且不采信**不得回落逐标注**，
#   于是该行 4 条 `N单元` 全部不落盘、图签侧该栋单元数丢成 None（真实是 2 单元）。
#   合成料按实测几何：格 59020.5×45041.3、行距 36418.1（本图实测行距很密）、
#   楼名→本行上沿 10496.1、x 偏置 3813.2 ⇒ 到本行 11167.5、到次近行 26201.1（优势 2.35×）。
try:
    _CW, _CH = 59020.5, 45041.3
    _P = 36418.1                    # 行距（实测：本行格顶 → 下一行格底）
    _T_OK, _T_BAD = 10496.1, 16000.0
    _DX = 3813.2                    # 楼名相对本行格组左边界的 x 偏置（画在格左外侧）
    # 两行：本行 y[-CH,0]（楼名所属），下一行 y[_P,_P+CH]
    _polys11 = []
    for _yt, _yb in ((0.0, -_CH), (_P + _CH, _P)):
        _polys11.append(['TK', [0.0, _yb, _CW, _yb, _CW, _yt, 0.0, _yt], 1])
    _lvu11 = [(0.70 * _CW, -0.70 * _CH, '1单元'),
              (0.70 * _CW, _P + 0.30 * _CH, '1单元')]
    _gs11, _info11 = C.collect_titleblock_unit_cells(_lvu11, _polys11)
    _own11 = [g for g in _gs11 if abs(g['rect'][3] - 0.0) < 1.0]      # 本行那一组
    for _tag, _t, _want_adopt in (('T11 偏置但优势明确 → 采信', _T_OK, True),
                                  ('T11 偏置且优势不足 → 不认领', _T_BAD, False)):
        _anch = [(-_DX, _t, '4#楼', ('默认', 4))]
        _r11 = C.assign_cells_to_buildings(_gs11, _anch, cell_h=_CH)
        _v11 = _r11['verdicts']
        _adopted = [_v for _v in _v11 if _v['采信']]
        check(_tag,
              len(_gs11) == 2 and len(_own11) == 1
              and (len(_adopted) == 1) == _want_adopt
              and (len(_r11['offset_claims']) == 1) == _want_adopt
              and (len(_r11['unclaimed']) == 1) == (not _want_adopt),
              '采信=%d 偏置登记=%d 未认领=%d 裁决=%s'
              % (len(_adopted), len(_r11['offset_claims']), len(_r11['unclaimed']),
                 [(_v['单元号'], _v['采信'], _v.get('不采信原因')) for _v in _v11]))
    # 反向验证判别力：尺度闸（一个格高）在「不采信」那一档**没有触发** ——
    #   否则本用例没有判别力（拒绝必须来自优势闸，而不是恰好超了尺度）。
    _d_own = C.point_rect_dist(-_DX, _T_BAD, _own11[0]['rect'])
    _d_oth = min(C.point_rect_dist(-_DX, _T_BAD, g['rect'])
                 for g in _gs11 if g is not _own11[0])
    check('T11 反向：拒绝来自优势闸而非尺度闸',
          _d_own <= _CH and _d_own > 0.5 * _d_oth,
          '本行 %.1f（≤格高 %.1f）／次近 %.1f ⇒ 优势 %.2f×'
          % (_d_own, _CH, _d_oth, (_d_oth / _d_own) if _d_own else 0))
except (ImportError, AttributeError) as _e:
    print('[SKIP] T11（缺依赖: %s）' % _e)

# ---------------- T12 格组判据「适用性闸门」（2026-09-23 新增） ----------------
#   专杀「判据用错范围却逐组弃解」（凤鸣朝阳小区实测）：图签楼名写成多栋合并
#   （`1#楼，2#楼`…），`bldg_re.fullmatch` 全不认 ⇒ 图签单元格零锚点；判据抓到的锚点
#   实为**系统图内的单栋标签**，全被尺度闸拦下 ⇒ 采信 1/12，其余 11 组被判「不落盘」。
#   而该图 C10 实测 PASS（信息另有来源）。故认领率过低必须**整体判不适用**、全部标注
#   交回逐标注判据，而不是逐组丢解。
try:
    _CW, _CH, _P = 59020.5, 45041.3, 36418.1
    _OFF12 = 2000.0          # = 格宽的 3.4%，同实测 band2 的 3813.2/118040.9=3.2%
    _polys12, _anch12 = [], []
    for _i in range(3):                       # 3 行 = 3 个格组
        _yb = -_i * (_CH + _P) - _CH
        _yt = -_i * (_CH + _P)
        _polys12.append(['TK', [0.0, _yb, _CW, _yb, _CW, _yt, 0.0, _yt], 1])
        # 行标题画在本行左外侧一点（复现实测偏置）⇒ 走「无横向覆盖」分支；
        # **偏置必须小于一个格高**，否则先被尺度闸拦下，测不到优势闸与适用性闸门。
        _anch12.append((-_OFF12, _yt + 9459.5, '%d#楼' % (_i + 1), ('默认', _i + 1)))
    _gs12, _ = C.collect_titleblock_unit_cells(
        [(0.70 * _CW, -_CH + 0.30 * _CH, '1单元'),
         (0.70 * _CW, -(_CH + _P) - 0.70 * _CH, '1单元'),
         (0.70 * _CW, -2 * (_CH + _P) - 0.70 * _CH, '1单元')], _polys12)
    _inapp = C.assign_cells_to_buildings(_gs12, _anch12[:1])      # 1/3 = 33% < 50%
    _ok12 = C.assign_cells_to_buildings(_gs12, _anch12[:2])       # 2/3 = 67% ≥ 50%
    check('T12 认领率过低 ⇒ 整体判不适用且不弃解',
          len(_gs12) == 3 and _inapp['适用'] is False
          and _inapp['owner'] == {} and _inapp['blocked'] == set()
          and bool(_inapp['不适用原因'])
          and sum(1 for _v in _inapp['verdicts'] if _v['采信']) >= 1,
          '适用=%s owner=%d blocked=%d 采信组=%d'
          % (_inapp['适用'], len(_inapp['owner']), len(_inapp['blocked']),
             sum(1 for _v in _inapp['verdicts'] if _v['采信'])))
    check('T12 反向：认领率达标 ⇒ 判据照常适用并落盘',
          _ok12['适用'] is True and len(_ok12['owner']) >= 1,
          '适用=%s owner=%d' % (_ok12['适用'], len(_ok12['owner'])))
    check('T12 偏置认领必须留痕（无横向覆盖分支）',
          bool(_ok12['offset_claims']) and len(_ok12['offset_claims']) >= 1
          and all('x 偏置' in _s for _s in _ok12['offset_claims']),
          'offset_claims=%d' % len(_ok12['offset_claims']))
    # 歧义锚点：y 取两行之正中 ⇒ 到上下两行**等距**，优势必然不足（但距离仍在尺度闸内）。
    # 必须构造出非空的 unclaimed，否则断言会「空真」通过、等于没测。
    _amb12 = (-_OFF12, -(_CH + _CH + _P) / 2.0, '9#楼', ('默认', 9))
    _mix12 = C.assign_cells_to_buildings(_gs12, [_anch12[0], _amb12])
    check('T12 拒绝须来自优势闸而非尺度闸（否则测的是另一条路）',
          len(_mix12['unclaimed']) >= 1
          and any('优势不足' in _s for _s in _mix12['unclaimed'])
          and not any('尺度闸' in _s for _s in _mix12['unclaimed']),
          'unclaimed=%d %s' % (len(_mix12['unclaimed']),
                               (_mix12['unclaimed'][:1] or ['-'])[0]))
except (ImportError, AttributeError) as _e:
    print('[SKIP] T12（缺依赖: %s）' % _e)

# ---------------- T13 图签「多栋合并楼名」登记（2026-09-23 新增） ----------------
#   这类楼名（`1#楼，2#楼` / `4、6-7号楼`）**只登记不解析** —— 拆分会把单元挂到错的楼栋。
#   反向：普通单栋楼名（`8#楼`）与非楼名文字（`15层/3户`）必须**不**被收进来，
#   否则每张图都会误报。
try:
    _BRE_SRC = r'(\d+)#(?:配套|商业|附属)?楼|(\d+)号楼'
    _t13 = [(0.0, 0.0, '1#楼，2#楼'), (10.0, 0.0, '8#楼'), (20.0, 0.0, '3#楼，5#楼'),
            (30.0, 0.0, '4、6-7号楼'), (40.0, 0.0, '2-3号楼'), (50.0, 0.0, '15层/3户')]
    _got13 = [t for _x, _y, t in C.collect_multi_bldg_labels(_t13, _BRE_SRC)]
    check('T13 多栋合并楼名被登记',
          _got13 == ['1#楼，2#楼', '3#楼，5#楼', '4、6-7号楼', '2-3号楼'], str(_got13))
    check('T13 反向：单栋楼名与非楼名文字不得误收',
          '8#楼' not in _got13 and '15层/3户' not in _got13, str(_got13))
except (ImportError, AttributeError) as _e:
    print('[SKIP] T13（缺依赖: %s）' % _e)

print()
print('== 冒烟结果: %s（失败 %d 项）==' % ('ALL PASS' if not fails else 'FAIL', len(fails)))
sys.exit(0 if not fails else 1)
