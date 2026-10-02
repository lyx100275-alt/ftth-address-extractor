# -*- coding: utf-8 -*-
"""包内冒烟自检（stdlib 为主；T5 语料 DXF 需 ezdxf，缺则 SKIP）。

用法::
    python tests/run_smoke.py [--with-dxf] [--corpus <dxf路径>]

    语料 DXF 已移出技能目录（版本库 tests/corpus/ 保留）：
    --corpus 参数 > 环境变量 FTTH_TEST_DXF > 内置路径，均缺失则 T5 自动 SKIP。

T1 单一源守卫：_txt_fields 恰 1 份实现；无本地 bldg_num 重复定义（同名异义防线）
T1b 委托锁：归一包装（norm_unit/norm_floor/floor_num_local）必须调共享入口；
    权威实现（unit_num/bldg_num/floor_num/配对/分带）恰 1 份（gen_9level.norm_units
    是另一语义「单元配置→层户数」且零依赖设计，不在此列）
T2 注册面=分发面：ftth.py 每个 add_parser 的子命令在分发段有分支（差集 ∅）
T3 纯函数语义：bldg_num / bldg_num_or_none / _txt_fields 两态出口 + floor_num 楼层归一
T4 体量闸门：ftth.py budget rc=0
T4b 文档一致性门：scripts/check_docs.py rc=0（D1~D7：子命令/阶段/冒烟范围/C项/指针链）
T5 语料冒烟（可选）：语料 DXF probe rc=0（语料缺失自动 SKIP）
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
T12 格组适用性闸门（合成料）：认领率过低整体判不适用且不弃解 + 偏置留痕 + 优势闸判别力。
T13 多栋合并楼名登记（合成料）：只登记不解析 + 反向不误收。
T14 三图 golden 回归（需 --with-dxf + 桌面三图）：fresh 全链对拍产物指纹与门禁行为，
    基线 tests/golden_expected.json（约 3 分钟，缺图自动 SKIP）。
T15 台账确定性：FTTH_FIXED_TIME 冻结时钟后同序列写入逐位一致（生产默认系统时间不变）。
T17 产物契约门（需 T14 本轮产物）：L1-C8 词汇封闭静态检查（check_contracts.py）。
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


# T1 单一源守卫（权威住处：命名归一域住 ftth_naming.py，P1-2 起）
fc = read('scripts/ftth_common.py')
fn = read('scripts/ftth_naming.py')
check('T1 _txt_fields 恰1份', fn.count('def _txt_fields(') == 1 and fc.count('def _txt_fields(') == 0)
check('T1 bldg_num_or_none 存在', 'def bldg_num_or_none(' in fn)
dups = []
for f in sorted(os.listdir(SC)):
    # 权威住处豁免：bldg_num 住 ftth_naming.py（P1-2 起），经 ftth_common re-export
    if f.endswith('.py') and f not in ('ftth_common.py', 'ftth_naming.py'):
        if re.search(r'^def bldg_num\(', read('scripts/' + f), re.M):
            dups.append(f)
check('T1 无本地 bldg_num 重复实现', not dups, str(dups))

# T1b 委托锁（2026-09-26 新增，2026-09-26 P1-2 更新归属表）：归一包装必须调共享入口，
#   禁自写正则分支。权威实现住处：命名归一域 2026-09-26 起住 ftth_naming.py
#   （此前住 ftth_common.py），配对/分带仍住 ftth_common.py / count_box_icons.py。
#   专杀「同一逻辑多份实现必然漂移」——此前 norm_floor 漂移两轮（八十五收 bldg、
#   九十八收 inspect、verify 漏网到一百一十三），每次都靠人肉 grep 发现。
#   豁免：gen_9level_addressbook.norm_units 是另一语义（单元配置→层数/每层户数）
#   且该文件刻意零依赖（八十九），unit_label/bldg_label 仅显示层，不在此列。
_wrap_bad = []
for f in sorted(os.listdir(SC)):
    if not f.endswith('.py'):
        continue
    src = read('scripts/' + f)
    for wn, shared in (('norm_unit', ('unit_num(',)), ('norm_floor', ('floor_num(',)),
                       ('floor_num_local', ('floor_num(',)),
                       # fl_num 两种合法形态：直调 floor_num（V型，-9999 哨兵）/
                       # floor_num_or_zero（竖线法，0 回退），注释须写明选哪种。
                       ('fl_num', ('floor_num(', 'floor_num_or_zero('))):
        for mm in re.finditer(r'(?m)^def %s\(' % wn, src):
            body = src[mm.start():]
            nx = re.search(r'(?m)^def ', body[1:])
            body = body[:nx.start() + 1] if nx else body
            if not any(s in body for s in shared):
                _wrap_bad.append('%s:%s' % (f, wn))
check('T1b 归一包装必须委托共享入口', not _wrap_bad, str(_wrap_bad))
_single = {'def unit_num(': 'ftth_naming.py', 'def bldg_num(': 'ftth_naming.py',
           'def bldg_num_or_none(': 'ftth_naming.py', 'def floor_num(': 'ftth_naming.py',
           'def parse_floor_label(': 'ftth_naming.py',
           'def parse_bldg_nums(': 'ftth_naming.py',
           'def parse_unit_key(': 'ftth_naming.py',
           'def cn2num(': 'ftth_naming.py', 'def _txt_fields(': 'ftth_naming.py',
           'def cluster_by_y(': 'ftth_common.py',
           'def compute_bldg_ranges_banded(': 'ftth_common.py',
           'def column_consensus_y(': 'ftth_common.py',
           'def floor_scales(': 'count_box_icons.py',
           'def parse_col_scale_map(': 'count_box_icons.py'}
_single_bad = []
for sig, owner in _single.items():
    hits = [f for f in sorted(os.listdir(SC))
            if f.endswith('.py') and re.search(r'(?m)^%s' % re.escape(sig), read('scripts/' + f))]
    if hits != [owner]:
        _single_bad.append('%s->%s' % (sig, hits))
check('T1b 权威实现恰1份', not _single_bad, str(_single_bad))

# T1c 出口锁（2026-09-26 新增）：JSON 出口统一走 write_json，控制台统一走
#   ensure_console_utf8。豁免各有去处：ftth_common（实现本体）、ftth_geom
#   （禁 import ftth_common，否则循环）、ftth_launcher/check_budget/
#   check_transitions（刻意零依赖的启动/门禁入口）、ledger_state（自带等效
#   守卫 + sort_keys canonical 出口）、ftth.py（仅 pipeline_timing.json 计时
#   日志，需 newline="\n" 防 Windows CRLF，write_json 无此参数）。
#   新增直调即冒烟变红。
_json_ok, _json_bad, _con_ok, _con_bad = True, [], True, []
for f in sorted(os.listdir(SC)):
    if not f.endswith('.py'):
        continue
    src = read('scripts/' + f)
    if f not in ('ftth_common.py', 'ftth_geom.py', 'ftth_launcher.py',
                 'check_budget.py', 'check_transitions.py', 'ledger_state.py',
                 'ftth.py'):
        if re.search(r'json\.dump\(', src):
            _json_ok = False
            _json_bad.append(f)
    if f not in ('ftth_common.py', 'ledger_state.py'):
        if 'sys.stdout.reconfigure(' in src:
            _con_ok = False
            _con_bad.append(f)
check('T1c JSON出口统一走write_json', _json_ok, str(_json_bad))
check('T1c 控制台统一走ensure', _con_ok, str(_con_bad))

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
    check('T3 floor_num B1→-1', C.floor_num('B1', use_fullmatch=True) == -1)
    check('T3 floor_num 十七层→17', C.floor_num('十七层', use_fullmatch=True) == 17)
    check('T3 floor_num WF→900', C.floor_num('WF', use_fullmatch=True) == C.FLOOR_WF_VALUE)
    check('T3 floor_num 非楼层返None', C.floor_num('3#楼', use_fullmatch=True) is None)
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

# T4b 文档一致性门（2026-09-26 新增）：SKILL/README 声称的数字必须与代码现实一致。
#   专杀「文档声称已改、代码里其实没有」（本项目反复复现的老毛病）——此前靠 opencode
#   人眼审计，今后跑冒烟即审。细则见 scripts/check_docs.py（D1~D12）。
r = subprocess.run([PY, os.path.join(SC, 'check_docs.py')], capture_output=True, text=True, encoding='utf-8', errors='replace')
check('T4b check_docs rc=0', r.returncode == 0, 'rc=%s' % r.returncode)

# T4c 契约落地门（2026-10-02 会审整改 P0-3 新增）：核 version.json 的 contract_coverage
#   登记与仓库现实一致（L1 契约 C 编号双向对拍 / 产出方·检查器文件须存在 /
#   enforced 不得无检查器 / declared 必带 gap）。
#   **接进冒烟链是必须的**：本门禁治的病正是「没人记得手动跑」——
#   此前它只存在于 scripts/ 里，run_smoke / README 对它 0 次命中，
#   等于「新增门禁却永不执行」，比没有门禁更坏（制造已覆盖的错觉）。
r = subprocess.run([PY, os.path.join(SC, 'check_contract_coverage.py')],
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
check('T4c 契约落地门 rc=0', r.returncode == 0, 'rc=%s' % r.returncode)

# T4d 迁移门禁（2026-10-02 会审整改 P0-3 新增）：check_transitions 的 6 条禁止迁移
#   此前也不在冒烟链里。判据 #6（申报态与证据对拍）的**正反用例**由本项覆盖 ——
#   手工验过但没沉淀成回归的门禁等于不存在。
#   覆盖：① 无台账 → rc=3（刻意不给「通过」）；② 有 pending 且申报 ≥ LOCKED → rc=2；
#   ③ 申报 ≥ OUTPUT 而无成品 → rc=2；④ 状态名非法 → rc=2；⑤ 状态回退合法受理 → rc=0。
_t4d_ok, _t4d_notes = True, []
_t4d_dir = tempfile.mkdtemp(prefix='ftth_trans_')
for _a in (['init', '--project-dir'],
           ['snapshot-set', '--project-dir', '--key', 'K', '--value', 'V',
            '--source', 'S', '--status', '待裁决'],
           ['state-set', '--project-dir', '--state', 'LOCKED BASELINE']):
    _a[_a.index('--project-dir') + 1:_a.index('--project-dir') + 1] = [_t4d_dir]
    _r = subprocess.run([PY, os.path.join(SC, 'ledger_state.py')] + _a,
                        capture_output=True, text=True, encoding='utf-8', errors='replace')
    if _r.returncode != 0:
        _t4d_ok, _t4d = False, 'setup %s rc=%s' % (_a[0], _r.returncode)
        _t4d_notes.append(_t4d)
        break
_r = subprocess.run([PY, os.path.join(SC, 'check_transitions.py'), '--project-dir', _t4d_dir],
                    capture_output=True, text=True, encoding='utf-8', errors='replace')
if _t4d_ok and not (_r.returncode == 2 and '#6' in _r.stdout):
    _t4d_ok = False
    _t4d_notes.append('判据#6 未按预期 rc=2（实得 rc=%s）' % _r.returncode)
# 清掉 pending 后同一目录必须转绿（证明是 pending 触发，不是目录本身坏）
_r2 = subprocess.run([PY, os.path.join(SC, 'ledger_state.py'), 'snapshot-set',
                      '--project-dir', _t4d_dir, '--key', 'K', '--value', 'V',
                      '--source', 'S', '--status', '已确认'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
_r3 = subprocess.run([PY, os.path.join(SC, 'check_transitions.py'), '--project-dir', _t4d_dir],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
if _t4d_ok and not (_r2.returncode == 0 and _r3.returncode == 0):
    _t4d_ok = False
    _t4d_notes.append('清 pending 后未转绿（%s/%s）' % (_r2.returncode, _r3.returncode))
# 非法状态名必须 rc=3（state-set 侧），不得静默写入
_r4 = subprocess.run([PY, os.path.join(SC, 'ledger_state.py'), 'state-set',
                      '--project-dir', _t4d_dir, '--state', '随便写'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
if _t4d_ok and _r4.returncode != 3:
    _t4d_ok = False
    _t4d_notes.append('非法状态名未 rc=3（实得 %s）' % _r4.returncode)
check('T4d 迁移门禁 #6 正反用例', _t4d_ok, '; '.join(_t4d_notes) or '4 项按预期')

# T5 语料冒烟（可选，需 ezdxf + 语料；语料缺失自动 SKIP，不阻断）
if '--with-dxf' in sys.argv:
    try:
        import ezdxf  # noqa: F401
        HAS = True
    except ImportError:
        HAS = False
    if HAS:
        # 语料 DXF 已移出技能目录（版本库 tests/corpus/ 保留）：
        # 解析顺序 --corpus 参数 > 环境变量 FTTH_TEST_DXF > 技能目录内置路径
        dxf = None
        if '--corpus' in sys.argv:
            _i = sys.argv.index('--corpus')
            if _i + 1 < len(sys.argv):
                dxf = sys.argv[_i + 1]
        if dxf is None:
            dxf = os.environ.get('FTTH_TEST_DXF')
        if dxf is None:
            dxf = os.path.join(HERE, 'corpus', 'a小区.dxf')
        if not os.path.exists(dxf):
            print('[SKIP] T5（语料缺失: %s；已外置到版本库 tests/corpus/，可用 --corpus 或 FTTH_TEST_DXF 指定）' % dxf)
        else:
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
                                "覆盖范围线索": {"覆盖楼层": ["1F", "2F"]},
                                "判定依据": "竖线法（冒烟合成料）",
                                "依据来源": "E-SMOKE",
                                "result_origin": "derived",
                                "result_confirmation": "settled"}]},
        "3#楼二单元": {"分纤箱": [{"编号": "FX02#", "安装楼层": "1F",
                                "覆盖范围线索": {"覆盖楼层": ["1F"]},
                                "判定依据": "竖线法（冒烟合成料）",
                                "依据来源": "E-SMOKE",
                                "result_origin": "derived",
                                "result_confirmation": "settled"}]}}},
    "7#楼": {"单元": {"7#楼1单元": {"分纤箱": [{"编号": "FX17#", "安装楼层": "1F",
        "覆盖范围线索": {"覆盖楼层": ["1F", "2F"]},
        "判定依据": "竖线法（冒烟合成料）", "依据来源": "E-SMOKE",
        "result_origin": "derived", "result_confirmation": "settled"}]}}},
    "8#楼": {"单元": {"8#楼1单元": {"分纤箱": [{"编号": "FX18#", "安装楼层": "1F",
        "覆盖范围线索": {"覆盖楼层": ["1F", "2F"]},
        "判定依据": "竖线法（冒烟合成料）", "依据来源": "E-SMOKE",
        "result_origin": "derived", "result_confirmation": "settled"}]}}}}}
# T6 合成 parse（2026-09-29 一百二十七：gen 强制绑定闭合，T6 须先 inspect rc=0 再出表；}
# T6 合成 parse（2026-09-29 一百二十七：gen 强制绑定闭合，T6 须先 inspect rc=0 再出表；
#   夹具同步到现行契约：安装楼层与 coverage 双源一致，楼层表全非空且一致）
_T6_PARSE = {"楼栋": {
    "3#楼": {"单元": {
        "1单元": {"楼层表": {"1F": {"户数": 2}, "2F": {"户数": 2}},
                  "分纤箱": [{"编号": "FX01#", "安装楼层": "2F"}]},
        "2单元": {"楼层表": {"1F": {"户数": 2}, "2F": {"户数": 2}},
                  "分纤箱": [{"编号": "FX02#", "安装楼层": "1F"}]}}},
    "7#楼": {"单元": {"1单元": {"楼层表": {"1F": {"户数": 2}, "2F": {"户数": 2}},
                  "分纤箱": [{"编号": "FX17#", "安装楼层": "1F"}]}}},
    "8#楼": {"单元": {"1单元": {"楼层表": {"1F": {"户数": 2}, "2F": {"户数": 2}},
                  "分纤箱": [{"编号": "FX18#", "安装楼层": "1F"}]}}}}}
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
                # 2026-09-29（一百二十七·P0）：gen 强制绑定闭合——先 inspect rc=0，
                #   再带 --inspect 出表； antiguos直调裸出在本版必须 rc=2（见 T19）。
                _pp2 = os.path.join(_td, 'parse.json')
                _ip = os.path.join(_td, 'insp.json')
                io.open(_pp2, 'w', encoding='utf-8').write(_json.dumps(_T6_PARSE, ensure_ascii=False))
                _ri = subprocess.run([PY, os.path.join(SC, 'ftth.py'), 'inspect',
                                      '--parse', _pp2, '--coverage', _vp,
                                      '--json', _ip],
                                     capture_output=True, text=True, encoding='utf-8', errors='replace')
                check('T6 inspect rc=0', _ri.returncode == 0 and os.path.exists(_ip),
                      'rc=%s' % _ri.returncode)
                _r3 = subprocess.run([PY, os.path.join(SC, 'ftth.py'), 'gen',
                                      '--parse', _pp, '--coverage', _vp,
                                      '--inspect', _ip,
                                      '--template', _tpl, '--out', _xp],
                                     capture_output=True, text=True, encoding='utf-8', errors='replace')
                _ok3 = _r3.returncode == 0 and os.path.exists(_xp)
                check('T6 gen带闭合 rc=0', _ok3, 'rc=%s' % _r3.returncode)
            else:
                print('[SKIP] T6 gen（缺 openpyxl）')

# ---------------- T19/T20/T22 出口门禁负向测试（2026-09-29 一百二十七·P0） ----------------
#   专杀「gen 绕过 inspect 直出」：正确输入→正确输出（T6）之外，必须证明
#   错误状态→绝对禁止输出。三个互补方向：
#     T19 无闭合直调 gen（Layer1：缺 --inspect 即 rc=2）；
#     T20 陈旧闭合（Layer2：inspect 后改了 coverage，指纹对不上即 rc=2）；
#     T22 pending 覆盖 + 伪造的 rc=0 闭合（Layer3：gen 自身重扫独立拦下）。
#   另带 T22b：真 inspect rc=2 的闭合直达 gen（Layer1 rc 门）。
try:
    import openpyxl  # noqa: F401
    _HASXL2 = True
except ImportError:
    _HASXL2 = False
if not _HASXL2:
    print('[SKIP] T19/T20/T22（缺 openpyxl）')
else:
    import hashlib as _hl
    _N_P = {"楼栋": {"9#楼": {"单元": {"1单元": {
        "楼层表": {"1F": {"户数": 2}},
        "分纤箱": [{"编号": "FX99#", "安装楼层": "1F"}]}}}}}
    _N_C = {"楼栋": {"9#楼": {"单元": {"9#楼1单元": {"分纤箱": [{
        "编号": "FX99#", "安装楼层": "1F",
        "覆盖范围线索": {"覆盖楼层": ["1F"]},
        "判定依据": "竖线法（冒烟合成料）", "依据来源": "E-SMOKE",
        "result_origin": "derived", "result_confirmation": "settled"}]}}}}}
    with tempfile.TemporaryDirectory() as _td:
        _np = os.path.join(_td, 'p.json')
        _nc = os.path.join(_td, 'c.json')
        _ni = os.path.join(_td, 'i.json')
        _nx = os.path.join(_td, 'o.xlsx')
        _tpl9 = os.path.join(SK, 'assets', '标准地址表模板.xlsx')
        io.open(_np, 'w', encoding='utf-8').write(_json.dumps(_N_P, ensure_ascii=False))
        io.open(_nc, 'w', encoding='utf-8').write(_json.dumps(_N_C, ensure_ascii=False))
        # T19：无 --inspect 直调
        _r19 = subprocess.run([PY, os.path.join(SC, 'gen_addressbook.py'),
                               '--dxf-json', _np, '--coverage', _nc,
                               '--template', _tpl9, '--out', _nx],
                              capture_output=True, text=True, encoding='utf-8', errors='replace')
        check('T19 无闭合直调gen rc=2且无出表',
              _r19.returncode == 2 and not os.path.exists(_nx),
              'rc=%s 出表=%s' % (_r19.returncode, os.path.exists(_nx)))
        # T20：先 inspect（rc=0），再改 coverage 文件 → 指纹过期
        _ri20 = subprocess.run([PY, os.path.join(SC, 'ftth.py'), 'inspect',
                                '--parse', _np, '--coverage', _nc, '--json', _ni],
                               capture_output=True, text=True, encoding='utf-8', errors='replace')
        _ok20 = _ri20.returncode == 0 and os.path.exists(_ni)
        check('T20 inspect基线 rc=0', _ok20, 'rc=%s' % _ri20.returncode)
        if _ok20:
            _c2 = _json.load(io.open(_nc, encoding='utf-8'))
            _c2['楼栋']['9#楼']['单元']['9#楼1单元']['分纤箱'][0]['安装楼层'] = '2F'
            io.open(_nc, 'w', encoding='utf-8').write(_json.dumps(_c2, ensure_ascii=False))
            _r20 = subprocess.run([PY, os.path.join(SC, 'gen_addressbook.py'),
                                   '--dxf-json', _np, '--coverage', _nc,
                                   '--inspect', _ni,
                                   '--template', _tpl9, '--out', _nx],
                                  capture_output=True, text=True, encoding='utf-8', errors='replace')
            check('T20 陈旧闭合gen rc=2且无出表',
                  _r20.returncode == 2 and not os.path.exists(_nx),
                  'rc=%s 出表=%s' % (_r20.returncode, os.path.exists(_nx)))
        # T22：pending 覆盖 + 伪造 rc=0 且指纹吻合的闭合 → Layer3 重扫必须独立拦下
        _cp = {"楼栋": {"9#楼": {"单元": {"9#楼1单元": {"分纤箱": [{
            "编号": "FX99#", "安装楼层": "1F",
            "覆盖范围线索": {"覆盖楼层": ["1F"]},
            "判定依据": "竖线法（冒烟合成料）", "依据来源": "E-SMOKE",
            "result_origin": "derived", "result_confirmation": "pending"}]}}}},
            "需人工裁决": [{"对象": "9#楼/FX99#", "事项": "合成料待裁决",
                            "阻塞": True}]}
        _cpp = os.path.join(_td, 'cp.json')
        _cpi = os.path.join(_td, 'ci.json')
        io.open(_cpp, 'w', encoding='utf-8').write(_json.dumps(_cp, ensure_ascii=False))
        _sh = lambda p: _hl.sha256(io.open(p, 'rb').read()).hexdigest()
        io.open(_cpi, 'w', encoding='utf-8').write(_json.dumps(
            {"rc": 0, "inputs_sha256": {"parse": _sh(_np), "coverage": _sh(_cpp)},
             "checks": [], "fails": [], "warns": []}, ensure_ascii=False))
        _r22 = subprocess.run([PY, os.path.join(SC, 'gen_addressbook.py'),
                               '--dxf-json', _np, '--coverage', _cpp,
                               '--inspect', _cpi,
                               '--template', _tpl9, '--out', _nx],
                              capture_output=True, text=True, encoding='utf-8', errors='replace')
        check('T22 pending覆盖+伪造闭合gen rc=2且无出表',
              _r22.returncode == 2 and not os.path.exists(_nx),
              'rc=%s 出表=%s' % (_r22.returncode, os.path.exists(_nx)))
        # T22b：真 inspect（rc=2）直达 gen → Layer1 rc 门
        _cpi2 = os.path.join(_td, 'ci2.json')
        _ri22 = subprocess.run([PY, os.path.join(SC, 'ftth.py'), 'inspect',
                                '--parse', _np, '--coverage', _cpp, '--json', _cpi2],
                               capture_output=True, text=True, encoding='utf-8', errors='replace')
        _ok22 = _ri22.returncode == 2 and os.path.exists(_cpi2)
        check('T22 真inspect pending判rc=2', _ok22, 'rc=%s' % _ri22.returncode)
        if _ok22:
            _r22b = subprocess.run([PY, os.path.join(SC, 'gen_addressbook.py'),
                                    '--dxf-json', _np, '--coverage', _cpp,
                                    '--inspect', _cpi2,
                                    '--template', _tpl9, '--out', _nx],
                                   capture_output=True, text=True, encoding='utf-8', errors='replace')
            check('T22 非0闭合直达gen rc=2且无出表',
                  _r22b.returncode == 2 and not os.path.exists(_nx),
                  'rc=%s 出表=%s' % (_r22b.returncode, os.path.exists(_nx)))

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

# ---------------- T14 三图 golden 回归（2026-09-26 新增） ----------------
#   专杀「退化发现晚、靠人工兜」——此前云峰刻度漂移跨 14 版本逐字一致无人拦。
#   口径：fresh 全链跑桌面三图，对拍产物指纹 + 门禁行为；只在 --with-dxf 且三图
#   齐备时跑（约 3 分钟），否则 SKIP。指纹设计（防假红）：md5 只锁跨目录逐位一致
#   的文件（parsed/coverage/titleblock/fxmap/fx_locations/unit_box_gaps/count_box）；
#   profile/timing/inspect 内嵌路径与耗时走语义比对（rc/条数/归一化文本哈希，浮点
#   与路径归一）。lxz14 config.json 有探查浮点抖动（已证实），不锁 md5。
#   指纹基线见 tests/golden_expected.json；行为变更须同步更新基线并记 CHANGELOG。
#
# 2026-10-02（会审整改 P0-1）三处改：
#   ① **默认即跑**，不再只在 `--with-dxf` 下跑。此前三图 golden 长期 SKIP，
#      而基线本身已陈旧（skill 0.113.0 生成，跨 30 个修订从未重生成）——于是
#      「全部门禁通过」这个绿灯**从来不含真图**，md5 漂移持续累积无人察觉。
#      现在默认跑；三图不齐才 SKIP（外置语料的机器上仍可跳过）。
#   ② `pipeline_rc` 从基线移除：它已由「各阶段 rc」与 inspect rc 蕴含，重复断言
#      只会在阶段划分调整时给出误导性的第二个红灯。
#   ③ 新增 `--regen-golden`：基线**只能由本命令重生**，手工改 json 不会被任何
#      门禁察觉（此前无任何机制保证基线与代码同批）。
_REGEN = '--regen-golden' in sys.argv
_GOLDEN_PATH = os.path.join(HERE, 'golden_expected.json')
_GOLDEN_KEYS = ('parsed.json', 'coverage.json', 'titleblock.json', 'fxmap.json',
                'fx_locations.json', 'count_box.json', 'unit_box_gaps.json')
try:
    import hashlib as _hl
    import json as _json
    _gm = _json.load(io.open(_GOLDEN_PATH, encoding='utf-8'))
    _cases = _gm['cases']

    def _resolve_dxf(rel):
        """基线里的 dxf 相对路径 → 绝对路径。

        相对基准 = **用户桌面**（语料外置的约定），但为每次运行留两个后手：
        ① 基线里写绝对路径（异地机器复现用）；② 相对 `技能目录/../../..` 等常见
        语料库位置。找不到则返 None → T14 SKIP 并说清缺哪张图，不静默跳过。
        """
        if os.path.isabs(rel):
            return rel if os.path.isfile(rel) else None
        for base in (os.path.join(os.path.expanduser('~'), 'Desktop'),
                     os.path.join(os.path.expanduser('~')),
                     os.path.dirname(SK), os.path.dirname(os.path.dirname(SK))):
            p = os.path.normpath(os.path.join(base, rel.replace('/', os.sep)))
            if os.path.isfile(p):
                return p
        return None

    _resolved, _missing = {}, []
    for _cn, _c in _cases.items():
        _abs = _resolve_dxf(_c['dxf'])
        if _abs:
            _resolved[_cn] = _abs
        else:
            _missing.append('%s(%s)' % (_cn, _c['dxf']))
    if _missing:
        print('[SKIP] T14 真图缺失：%s（基线 relative 于用户桌面；可用 --corpus/基线绝对路径调整）'
              % '、'.join(_missing))
    else:
        _gdir = tempfile.mkdtemp(prefix='ftth_golden_')
        _T14_GDIR = _gdir  # T17 只验本轮产物，不碰历史残留目录
        _regen_cases, _all_ok, _notes = {}, True, []

        def _norm(_s, _od):
            _s = _s.replace(_od, '$OUT')
            return re.sub(r'\d+\.\d+(e[+-]?\d+)?', '#', _s)

        for _cn, _c in _cases.items():
            _od = os.path.join(_gdir, _cn)
            _r = subprocess.run(
                [PY, os.path.join(SC, 'ftth.py'), 'pipeline', '--dxf',
                 _resolved[_cn], '--outdir', _od, '--quiet'],
                capture_output=True, text=True, encoding='utf-8', errors='replace')
            # ---- 无论重生与否，都按同一套判据算实测值 ----
            _files = {}
            for _fn in _GOLDEN_KEYS:
                _p = os.path.join(_od, _fn)
                if os.path.isfile(_p):
                    _files[_fn] = _hl.md5(io.open(_p, 'rb').read()).hexdigest()
            _ij = os.path.join(_od, 'inspect.json')
            _d = _json.load(io.open(_ij, encoding='utf-8')) if os.path.isfile(_ij) else {}
            _fb = sorted(_norm(x, _od) for x in _d.get('fails', []))
            _wb = sorted(_norm(x, _od) for x in _d.get('warns', []))
            _actual = {'files_md5': _files}
            if _d:
                _actual['inspect'] = {
                    'rc': _d.get('rc'), 'fails_n': len(_fb), 'warns_n': len(_wb),
                    'fails_h': _hl.md5('|'.join(_fb).encode('utf-8')).hexdigest()[:12],
                    'warns_h': _hl.md5('|'.join(_wb).encode('utf-8')).hexdigest()[:12]}
            _cb = os.path.join(_od, 'count_box.json')
            if os.path.isfile(_cb):
                _b = _json.load(io.open(_cb, encoding='utf-8'))
                _actual['count_box'] = {
                    'cols': len(_b.get('列', [])), 'total': _b.get('归层后总户数'),
                    'unassigned': _b.get('未归属图标数'),
                    'outliers': len(_b.get('刻度偏移异常列', [])),
                    'shared': len(_b.get('共用刻度列组', []))}

            # 相对基线 dxf 路径的存放形态：能写成桌面子路径就写子路径（可移植）
            _rel = _resolved[_cn]
            _desk = os.path.join(os.path.expanduser('~'), 'Desktop')
            _rel_store = (_rel[len(_desk) + 1:].replace(os.sep, '/')
                          if _rel.lower().startswith(_desk.lower()) else _rel)
            _regen_cases[_cn] = {'dxf': _rel_store, 'expect': _actual}

            if _REGEN:
                continue  # 重生模式：只收集，不判
            _exp = _c['expect']
            _ok = True
            for _fn, _h in (_exp.get('files_md5') or {}).items():
                _got = _files.get(_fn, 'MISSING')
                if _got != _h:
                    _ok = False
                    _notes.append('%s %s md5 %s≠%s' % (_cn, _fn, str(_got)[:12], str(_h)[:12]))
            if 'inspect' in _exp:
                _ei, _ai = _exp['inspect'], _actual.get('inspect') or {}
                if not (_ai.get('rc') == _ei['rc'] and _ai.get('fails_n') == _ei['fails_n']
                        and _ai.get('warns_n') == _ei['warns_n']
                        and _ai.get('fails_h') == _ei['fails_h']
                        and _ai.get('warns_h') == _ei['warns_h']):
                    _ok = False
                    _notes.append('%s inspect 不符（rc=%s F=%s W=%s / 基线 rc=%s F=%s W=%s）'
                                  % (_cn, _ai.get('rc'), _ai.get('fails_n'), _ai.get('warns_n'),
                                     _ei['rc'], _ei['fails_n'], _ei['warns_n']))
            if 'count_box' in _exp and _actual.get('count_box') != _exp['count_box']:
                _ok = False
                _notes.append('%s count_box %s≠%s'
                              % (_cn, _actual.get('count_box'), _exp['count_box']))
            _all_ok = _all_ok and _ok

        if _REGEN:
            _gm2 = {'cases': _regen_cases, 'version': 2,
                    'generated_from': os.path.basename(
                        _json.load(io.open(os.path.join(SK, 'version.json'),
                                           encoding='utf-8')).get('skill_version', '?')),
                    '_note': '本文件由 `tests/run_smoke.py --regen-golden` 重生，请勿手工编辑；'
                             '行为变更须同步更新基线并在 SKILL_CHANGELOG 记明原因。'}
            with io.open(_GOLDEN_PATH, 'w', encoding='utf-8', newline='\n') as _gf:
                _gf.write(_json.dumps(_gm2, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
            print('[PASS] T14 golden 基线已重生（%d 图）→ %s' % (len(_regen_cases), _GOLDEN_PATH))
        else:
            check('T14 三图golden回归', _all_ok, '; '.join(_notes) or '三图全对拍一致')
except Exception as _e:
    check('T14 三图golden回归', False, '异常: %s' % _e)

# ---------------- T17 产物契约门（2026-09-26 新增） ----------------
#   L1-C8 词汇封闭的静态执行方：凡带 result_origin / result_confirmation 的
#   产物项，其值必须在契约词汇内；未知词汇 = 第四种状态，上游按三态解释必错。
#   跑 T14 的三个 fresh 产物目录（缺 T14 即 SKIP，不单独跑管线）。
#   pending/unresolved 只盘点不判 FAIL —— 语义判定权在 C9。
#   2026-10-02：随 T14 一并改为默认执行（原仅 --with-dxf）—— 它消费 T14 的产物，
#   T14 默认跑之后它若还 SKIP，就等于「产物已产出却不验词汇」，是纯漏洞。
try:
    _gm17 = __import__('json').load(io.open(os.path.join(HERE, 'golden_expected.json'), encoding='utf-8'))
    if not _REGEN and ('_T14_GDIR' not in dir() or not os.path.isdir(_T14_GDIR)):
        print('[SKIP] T17（本轮 T14 未产出——真图缺失或处于 --regen-golden 模式）')
    elif _REGEN:
        print('[SKIP] T17（--regen-golden 模式：只重生基线，不跑下游门禁）')
    else:
        _ok17, _notes17 = True, []
        for _cn in _gm17['cases']:
            _od = os.path.join(_T14_GDIR, _cn)
            if not os.path.isdir(_od):
                continue
            _r = subprocess.run([PY, os.path.join(SC, 'check_contracts.py'), _od],
                                capture_output=True, text=True, encoding='utf-8', errors='replace')
            if _r.returncode == 3:
                # 2026-09-27（P0-3 附带）：rc=3 = 该案例目录**无可核对象**
                #   （T14 未产出 / 产物为空）。这既不是通过也不是契约违约 ——
                #   「没核」不得输出成「通过」，故登记但不判 FAIL（判 FAIL 会与
                #   T17 自己的前置「缺 T14 即 SKIP」自相矛盾）。
                _notes17.append('%s rc=3(无可核对象，未核)' % _cn)
            elif _r.returncode != 0:
                _ok17 = False
                _notes17.append('%s rc=%s' % (_cn, _r.returncode))
        check('T17 产物契约词汇封闭', _ok17, '; '.join(_notes17) or '三图产物词汇全合规')
except Exception as _e:
    check('T17 产物契约词汇封闭', False, '异常: %s' % _e)

# ---------------- T15 台账确定性（2026-09-26 新增） ----------------
#   专杀「ledger 每次 md5 必变」——此前 sort_keys 修了一半，_now() 时间戳仍是
#   唯一变量字段。生产行为不变（默认系统时间）；FTTH_FIXED_TIME 冻结时钟后，
#   同序列写入必须逐位一致，否则回归对拍全是假红。
try:
    import hashlib as _hl15
    _env15 = dict(os.environ)
    _env15['FTTH_FIXED_TIME'] = '2026-09-26T00:00:00'
    _d15 = [tempfile.mkdtemp(prefix='ftth_ledger_det_') for _i in range(2)]
    _seq15 = [
        ['init', '--project-dir'],
        ['snapshot-set', '--project-dir', '--key', 'K', '--value', 'V', '--source', 'S'],
        ['ruling-add', '--project-dir', '--question', 'Q', '--ruling', 'R', '--by', 'T'],
        ['alias-add', '--project-dir', '--canonical', 'C', '--raw', 'r1,r2', '--evidence', 'E'],
    ]
    _det_ok, _det_note = True, ''
    for _args in _seq15:
        for _dd in _d15:
            _a = list(_args)
            _a[_a.index('--project-dir') + 1:_a.index('--project-dir') + 1] = [_dd]
            _r = subprocess.run([PY, os.path.join(SC, 'ledger_state.py')] + _a,
                                capture_output=True, text=True, encoding='utf-8',
                                errors='replace', env=_env15)
            if _r.returncode != 0:
                _det_ok, _det_note = False, '%s rc=%s' % (' '.join(_a[:1]), _r.returncode)
    import filecmp as _fc15
    for _fn in ('理解快照.json', '裁决台账.json', '别名台账.json'):
        _p1, _p2 = os.path.join(_d15[0], _fn), os.path.join(_d15[1], _fn)
        _same = _fc15.cmp(_p1, _p2, shallow=False) if os.path.isfile(_p1) and os.path.isfile(_p2) else False
        if not _same:
            _det_ok, _det_note = False, '%s 两次写入不一致' % _fn
    # 锁定守卫：已裁决项无 --by 改值 -> rc=3；带 --by -> rc=0（L0-I4⑤/P3）。
    _g15 = _d15[0]
    _r = subprocess.run([PY, os.path.join(SC, 'ledger_state.py'), 'ruling-add',
                         '--project-dir', _g15, '--question', 'Q2', '--ruling', 'R2',
                         '--by', 'T', '--key', 'K'],
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace', env=_env15)
    _r1 = subprocess.run([PY, os.path.join(SC, 'ledger_state.py'), 'snapshot-set',
                          '--project-dir', _g15, '--key', 'K', '--value', 'V2',
                          '--source', 'S'],
                         capture_output=True, text=True, encoding='utf-8',
                         errors='replace', env=_env15)
    _r2 = subprocess.run([PY, os.path.join(SC, 'ledger_state.py'), 'snapshot-set',
                          '--project-dir', _g15, '--key', 'K', '--value', 'V2',
                          '--source', 'S', '--by', 'T'],
                         capture_output=True, text=True, encoding='utf-8',
                         errors='replace', env=_env15)
    if not (_r.returncode == 0 and _r1.returncode == 3 and _r2.returncode == 0):
        _det_ok, _det_note = False, '锁定守卫 rc=%s/%s/%s（期望 0/3/0）' % (
            _r.returncode, _r1.returncode, _r2.returncode)
    # trace 导出：rc=0 + JSON 可解析 + 项数与快照一致（机械导出零推理）。
    _r3 = subprocess.run([PY, os.path.join(SC, 'ledger_state.py'), 'trace',
                          '--project-dir', _g15],
                         capture_output=True, text=True, encoding='utf-8',
                         errors='replace', env=_env15)
    try:
        _td = __import__('json').loads(_r3.stdout) if _r3.returncode == 0 else {}
        _tok = (_r3.returncode == 0 and isinstance(_td.get('traces'), list)
                and len(_td['traces']) >= 1
                and all(set(t) >= {'element', 'candidates', 'evidence', 'conflicts',
                                   'decision', 'decision_origin', 'confirmation'}
                        for t in _td['traces']))
    except Exception:
        _tok = False
    if not _tok:
        _det_ok, _det_note = False, 'trace 导出异常 rc=%s' % _r3.returncode
    check('T15 台账确定性（固定时钟逐位一致）', _det_ok, _det_note or '三本台账两次写入md5一致')
except Exception as _e:
    check('T15 台账确定性（固定时钟逐位一致）', False, '异常: %s' % _e)

# ---------------- T18 冲突矩阵回归（2026-09-27 新增，报告 §12.4） ----------------
#   故意制造矛盾的输入，验证覆盖来源状态机闭环：降级/登记/unimplemented/absent/unknown
#   /枚举漂移/人工裁决可区分。**纯函数级，不需要 DXF 语料**，故任何时候都能跑。
#   退出码 0=全过 / 2=有失败（沿用 L1-C2）。
try:
    _r18 = subprocess.run([PY, os.path.join(HERE, 'run_conflict_matrix.py')],
                          capture_output=True, text=True, encoding='utf-8',
                          errors='replace')
    # 汇总文案**从矩阵自身的打印行现取**，不再在冒烟里另抄一份计数 ——
    # 抄一份即漂移：2026-09-27 增 S13 段后，此处仍写「12 场景 + 2 元断言」（单一真源纪律）。
    _sum18 = ''
    for _ln in (_r18.stdout or '').splitlines():
        if '冲突矩阵回归' in _ln:
            _sum18 = _ln.strip()
    check('T18 冲突矩阵回归（覆盖来源状态机闭环）', _r18.returncode == 0,
          ('rc=%s' % _r18.returncode) if _r18.returncode
          else (_sum18 or '矩阵未打印汇总行'))
except Exception as _e:
    check('T18 冲突矩阵回归（覆盖来源状态机闭环）', False, '异常: %s' % _e)

print()
print('== 冒烟结果: %s（失败 %d 项）==' % ('ALL PASS' if not fails else 'FAIL', len(fails)))
sys.exit(0 if not fails else 1)
