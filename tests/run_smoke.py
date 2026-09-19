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
r = subprocess.run([PY, os.path.join(SC, 'ftth.py'), 'budget'], capture_output=True, text=True)
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
                               capture_output=True, text=True)
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
                        capture_output=True, text=True)
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
                             capture_output=True, text=True)
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
                                     capture_output=True, text=True)
                _ok3 = _r3.returncode == 0 and os.path.exists(_xp)
                check('T6 gen rc=0', _ok3, 'rc=%s' % _r3.returncode)
            else:
                print('[SKIP] T6 gen（缺 openpyxl）')

print()
print('== 冒烟结果: %s（失败 %d 项）==' % ('ALL PASS' if not fails else 'FAIL', len(fails)))
sys.exit(0 if not fails else 1)
