# -*- coding: utf-8 -*-
"""包内冒烟自检（stdlib 为主；T5 语料 DXF 需 ezdxf，缺则 SKIP）。

用法::
    python tests/run_smoke.py [--with-dxf]

T1 单一源守卫：_txt_fields 恰 1 份实现；无本地 bldg_num 重复定义（同名异义防线）
T2 注册面=分发面：ftth.py 每个 add_parser 的子命令在分发段有分支（差集 ∅）
T3 纯函数语义：bldg_num / bldg_num_or_none / _txt_fields 两态出口
T4 体量闸门：ftth.py budget rc=0
T5 语料冒烟（可选）：tests/corpus/a小区.dxf probe rc=0
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

print()
print('== 冒烟结果: %s（失败 %d 项）==' % ('ALL PASS' if not fails else 'FAIL', len(fails)))
sys.exit(0 if not fails else 1)
