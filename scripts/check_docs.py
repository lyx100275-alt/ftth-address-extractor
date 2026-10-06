#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""文档-代码一致性门（阈值/数字/指针不断言即腐烂）。

背景
----
本技能反复复现的老毛病：「文档声称已改、代码里其实没有」「规则写在文档里、
没有代码执行方」（整改单批次1、审单调批次1）。人眼审定不可持续，故把四类
数字与两类指针变成 rc≠0 的硬信号。

检查（全部是「文档声称 vs 代码现实」对拍，不含主观判断）：
  D1 子命令数：SKILL.md / README.md / scripts_reference.md 声称的 N 子命令 == ftth.py add_parser 个数
  D2 阶段数：SKILL.md 声称的 M 阶段 == ftth.py _PIPE_STAGES 元组长度
  D3 冒烟范围：README.md 声称的 T0~K == run_smoke.py 最大的 check('T<整数>'
  D4 自检项覆盖：step2_selfcheck.md 声称 C1~C10 在 inspect_closure.py 里逐项存在，
      且代码侧不得出现 C11+（新增项必须同步改文档，否则判 FAIL）
  D5 批量编排可达：scripts_reference.md 指针 + pipeline_details.md §19 双向存在
      （2026-09-26 外移 aftermath，防指针悬空）
  D6 几何缓存指针链：SKILL.md → pipeline_details.md §16 → scripts_reference.md
      geom.json schema 三段可达（2026-09-25 批次1 #11 aftermath）
  D7 SKILL.md 外链文件存在：每个 ](references/xxx.md...) 目标文件必须存在
  D8 脚本数三处一致：SKILL.md / README.md / scripts_reference.md 声称数 == scripts/*.py 个数
      （2026-10-06 审计补：此前只核 SKILL/README，scripts_reference 的 42/43 漂移无门禁可报）
  D9 全仓相对链接存在：全部 md（除 CHANGELOG）的相对链接按**所在文件目录**可解析
      （2026-09-27 新增：D7 只核 SKILL.md 的外链，references/ 内文件误写成
       `references/xxx.md` 前缀的 8 条断链长期无门禁可报）
  D13 版本号三处一致：version.json 的 skill_version 须同时出现在 README.md 与
      SKILL_CHANGELOG.md（2026-10-06 审计补：README 曾落后 13 个修订而全绿）

退出码（沿用 L1-C2 语义）：0 = 全过；2 = 任一不一致（停，先对齐再改别的）。

用法：python scripts/check_docs.py；冒烟 T4b 自动调本脚本。
"""
import io
import json
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _rec = getattr(_s, 'reconfigure', None)
        if callable(_rec):
            _rec(encoding='utf-8', errors='replace')
    except Exception:
        pass


def skill_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with io.open(os.path.join(skill_root(), rel), encoding='utf-8') as f:
        return f.read()


fails = []


def check(name, cond, detail=''):
    print('[%s] %s%s' % ('PASS' if cond else 'FAIL', name, ('  ' + detail) if detail else ''))
    if not cond:
        fails.append(name)


SKILL = read('SKILL.md')
FT = read('scripts/ftth.py')

# D1 子命令数（三处文档 == 代码；2026-10-06 审计补：此前只核 SKILL.md，
#   README 与 scripts_reference 的 16/19 漂移无门禁可报）
m1 = re.search(r'(\d+)\s*子命令', SKILL)
regs = re.findall(r'sub\.add_parser\("([a-z0-9-]+)"', FT)
check('D1 子命令数文档==代码', bool(m1) and int(m1.group(1)) == len(regs),
      'SKILL=%s 代码=%d' % (m1.group(1) if m1 else '?', len(regs)))
_m1r = re.search(r'(\d+)\s*子命令', read('README.md'))
check('D1b README子命令数==代码', bool(_m1r) and int(_m1r.group(1)) == len(regs),
      'README=%s 代码=%d' % (_m1r.group(1) if _m1r else '?', len(regs)))
_m1s = re.search(r'支持\s*(\d+)\s*个子命令', read('references/scripts_reference.md'))
check('D1c scripts_reference子命令数==代码', bool(_m1s) and int(_m1s.group(1)) == len(regs),
      'SR=%s 代码=%d' % (_m1s.group(1) if _m1s else '?', len(regs)))

# D2 阶段数
m2 = re.search(r'(\d+)\s*阶段', SKILL)
mp = re.search(r'_PIPE_STAGES\s*=\s*\((.*?)\)', FT, re.S)
nstage = len(re.findall(r'"([a-z_]+)"', mp.group(1))) if mp else -1
check('D2 阶段数文档==代码', bool(m2) and int(m2.group(1)) == nstage,
      '文档=%s 代码=%d' % (m2.group(1) if m2 else '?', nstage))

# D3 冒烟范围
README = read('README.md')
SMOKE = read('tests/run_smoke.py')
m3 = re.search(r'T0\s*[-~]\s*T?(\d+)', README)
tmax = max([int(x) for x in re.findall(r"check\('T(\d+)", SMOKE)] or [-1])
check('D3 冒烟范围文档==代码', bool(m3) and int(m3.group(1)) == tmax,
      '文档=T0~T%s 代码最大T%d' % (m3.group(1) if m3 else '?', tmax))
_tnums = sorted(set(int(x) for x in re.findall(r"check\('T(\d+)", SMOKE)))
_tgap = [n for n in range(tmax + 1) if n not in _tnums] if tmax >= 0 else []
if _tgap:
    print('[WARN] D3 编号缺口（历史保留，不拦门；新增用例禁复用缺号）：缺 %s' % _tgap)

# D4 自检项覆盖
STEP2 = read('references/step2_selfcheck.md')
INS = read('scripts/inspect_closure.py')
code_c = set(int(x) for x in re.findall(r'\bC(\d+)\b', INS))
need = set(range(1, 11))
check('D4 C1~C10逐项存在', 'C1~C10' in STEP2 and need <= code_c,
      '文档=%s 代码C项=%s' % ('C1~C10' in STEP2, sorted(code_c)))
extra = code_c - need - {0}  # C0 是数据集可用性预检（2026-09-16），不在十项内，豁免
check('D4 无C11+悬空（新增须同步文档）', not extra, 'extra=%s' % sorted(extra))

# D5 批量编排可达
SR = read('references/scripts_reference.md')
PD = read('references/pipeline_details.md')
check('D5 批量编排指针+落点双向存在',
      ('pipeline_details.md' in SR and '19' in SR) and re.search(r'(?m)^## 19\.', PD) is not None,
      '指针=%s 落点=%s' % ('pipeline_details.md §19' in SR, bool(re.search(r'(?m)^## 19\.', PD))))

# D6 几何缓存指针链
check('D6 geom指针链三段可达',
      ('pipeline_details.md' in SKILL and '16' in SKILL)
      and re.search(r'(?m)^## 16\.', PD) is not None
      and 'geom.json' in SR and 'scripts_reference.md' in PD,
      'SKILL→PD§16→SR')

# D7 SKILL 外链文件存在
miss = []
for t in set(re.findall(r'\]\((references/[A-Za-z0-9_.-]+\.md)[^)]*\)', SKILL)):
    if not os.path.isfile(os.path.join(skill_root(), t.replace('/', os.sep))):
        miss.append(t)
check('D7 SKILL外链文件存在', not miss, '缺失=%s' % miss)

# D8 脚本数文档==代码（2026-09-26 P1-2 新增）：新增 .py 必须同步三处计数，
# 否则下次审计又要人肉对账。SKILL 与 README 各一处明数，scripts_reference 一处明数。
#   NPY_EXPECTED 是**第四处**计数（另三处在 SKILL.md / README.md / scripts_reference.md 的正文里）。
#   此前本项把 41 写死在表达式里，新增脚本时它是唯一不会被 grep 找到的暗数 ——
#   改了 SKILL/README 也会 FAIL，症状与「忘了改文档」完全一样，误导排查方向。
NPY_EXPECTED = 43
import glob as _glob
npy = len(_glob.glob(os.path.join(skill_root(), 'scripts', '*.py')))
m8a = re.search(r'（(\d+) 个文件）', SKILL)
m8b = re.search(r'(\d+) 个 `\.py`', README)
m8c = re.search(r'\*\*(\d+) 个脚本\*\*', read('references/scripts_reference.md'))
check('D8 脚本数文档==代码', npy == NPY_EXPECTED and bool(m8a) and int(m8a.group(1)) == npy
      and bool(m8b) and int(m8b.group(1)) == npy
      and bool(m8c) and int(m8c.group(1)) == npy,
      '代码=%d SKILL=%s README=%s SR=%s' % (npy, m8a.group(1) if m8a else '?',
                                            m8b.group(1) if m8b else '?',
                                            m8c.group(1) if m8c else '?'))

# D9 全仓相对链接存在（2026-09-27 新增）：D7 只核 SKILL.md 的外链，
# references/ 内的 md 互相引用时若照「技能根视角」写 `references/xxx.md`，
# Markdown 按**所在文件目录**解析 ⇒ 指向 references/references/… ⇒ 断链，
# 且没有任何门禁会报（实测 8 条）。此处把链接体检扩到全仓 md。
_badlinks = []
for _p in _glob.glob(os.path.join(skill_root(), '**', '*.md'), recursive=True):
    _bn = os.path.basename(_p)
    if _bn == 'SKILL_CHANGELOG.md':
        continue
    # changelog/ 是**历史条目冻结副本**（2026-10-02 归档），不随代码维护。
    #   排除理由不是「懒得查」：归档条目里大量正文含正则字面量（如
    #   `([中文\d]+)层`），会被 D9 的 `](...)` 链接正则误判成断链 —— 实测
    #   part01 因此恒假红。冻结副本的链接不修（改了即篡改历史），故整目录豁免。
    if os.path.basename(os.path.dirname(_p)) == 'changelog':
        continue
    _rel = os.path.relpath(_p, skill_root()).replace(os.sep, '/')
    _txt = io.open(_p, encoding='utf-8', errors='replace').read()
    for _m in re.finditer(r'\]\(([^)\s]+)\)', _txt):
        _raw = _m.group(1)
        _tgt = _raw.split('#')[0]
        if not _tgt or _tgt.startswith(('http://', 'https://', 'mailto:')):
            continue
        _full = os.path.normpath(os.path.join(os.path.dirname(_p), _tgt))
        if not os.path.exists(_full):
            _badlinks.append('%s -> %s' % (_rel, _raw))
check('D9 全仓相对链接存在', not _badlinks,
      '断链=%d %s' % (len(_badlinks), _badlinks[:5]))

# D10 契约落地登记（2026-10-02 P0 新增）：L1 契约每一条都要在 version.json 的
#   contract_coverage 段登记「谁产出 / 谁核 / 是否真落地」。治的病是
#   「只定义不产出」——L1-C8 立了整天而产出方零落地，inspect C9 恒 SKIP，
#   文档读起来却一切正常。此处只对拍「登记表与仓库现实一致」，
#   逐条判据由 scripts/check_contract_coverage.py 承担（含 declared 的 gap 强制）。
_vj = json.load(io.open(os.path.join(skill_root(), 'version.json'), encoding='utf-8'))
_cct = (_vj.get('contract_coverage') or {}).get('contracts') or {}
_m1c = re.search(r'(?m)^##\s+L1\s*契约.*?$', SKILL)
_l1ids = set()
if _m1c:
    _seg = SKILL[_m1c.end():].split('\n## ')[0]
    _l1ids = set(re.findall(r'^###\s+C(\d+)\s+\S', _seg, re.M))
check('D10 契约落地登记双向一致',
      bool(_cct) and _l1ids == set(k[1:] for k in _cct if re.fullmatch(r'C\d+', k)),
      'SKILL.md L1 %d 条 / 登记 %d 条%s'
      % (len(_l1ids), len(_cct),
         '' if _l1ids else '（L1 段未解析出 C 编号）'))
#   declared 契约允许存在（诚实登记），但必须逐条有 gap —— 否则等于把「未落地」藏进登记表。
_decl = [k for k, v in _cct.items() if isinstance(v, dict) and v.get('coverage') == 'declared']
_nogap = [k for k in _decl if not (_cct[k].get('gap') or '').strip()]
check('D10 declared 契约均带 gap 说明', not _nogap, 'declared=%s 缺 gap=%s' % (_decl, _nogap))
_unenf = [k for k, v in _cct.items() if isinstance(v, dict) and v.get('coverage') == 'unenforced']
check('D10 无 unenforced 契约（不得停留在无产出状态）', not _unenf, 'unenforced=%s' % _unenf)

# D11 状态机枚举双向对拍（2026-10-02 P0 新增）：状态机的十个节点名此前**只存在于
#   SKILL.md 的 ASCII 图里** —— 机器侧没有任何枚举，于是 check_transitions.py 只能核
#   「禁止的迁移有没有发生」（否定式），核不了「申报态与证据是否一致」（正向锚点）。
#   ledger_state.py 的 STATES 是机器侧唯一权威；此处与文档图逐名对拍，
#   防止「文档改了节点名、代码还按旧名判」这类只在换图时才暴露的漂移。
CT = read('scripts/check_transitions.py')
LSRC = read('scripts/ledger_state.py')
_m11 = re.search(r'(?m)^```\n(INPUT.*?)```', SKILL, re.S)
_diagram = _m11.group(1) if _m11 else ''
#   图是 ASCII 流程图，节点名含空格（USER VALIDATION），**按空白切词会把一个节点
#   切成两个 token** —— 故此处不做「文档 token 集合 == 代码集合」的等值对拍，
#   改为双向包含判定：① 代码每个节点名须在图中原样出现（防止代码有、文档无）；
#   ② 图中每个大写 token 须是某个代码节点名的子串（防止文档有、代码无）。
#   这也是唯一对含空格节点名稳健的形式。
_mlst = re.search(r'STATES\s*=\s*\((.*?)\)', LSRC, re.S)
_codestates = re.findall(r'"([A-Z][A-Z -]{2,})"', _mlst.group(1)) if _mlst else []
_doctoks = [t for t in re.findall(r'\b([A-Z][A-Z-]{2,})\b', _diagram)
            if t not in ('REPROBE', 'STOP', 'FAIL')]
_lost_in_doc = [s for s in _codestates if s not in _diagram]
_lost_in_code = [t for t in _doctoks if not any(t in s for s in _codestates)]
check('D11 状态机节点名文档==代码（双向）',
      bool(_diagram) and bool(_codestates) and not _lost_in_doc and not _lost_in_code,
      '代码 %d 节点；文档缺=%s / 代码缺=%s'
      % (len(_codestates), _lost_in_doc or '无', _lost_in_code or '无'))
# D12 禁止迁移条数三方一致（2026-10-02 P0 附带）：N_FORBIDDEN 此前以「5 条」散落在
#   docstring / 通过语 / SKILL.md 三处，加判据时必漏其中一处且机器查不出（本次实测命中）。
_nf = re.search(r'N_FORBIDDEN\s*=\s*(\d+)', CT)
_m12 = re.search(r'(?m)^\| `\|?\s*(\d+)\s*\|', SKILL)
_m12b = re.findall(r'(?m)^\|\s*`?(\d)`?\s*\|', SKILL)
_doc_nf = max((int(x) for x in _m12b), default=0)
check('D12 禁止迁移条数代码==文档',
      bool(_nf) and int(_nf.group(1)) == _doc_nf and ('N_FORBIDDEN' in CT),
      '代码 N_FORBIDDEN=%s / 文档表最大编号=%s' % (_nf.group(1) if _nf else '?', _doc_nf))

# D13 版本号三处一致（2026-10-06 审计补）：version.json 的 skill_version 须同时
#   出现在 README.md 与 SKILL_CHANGELOG.md。治的病是「README 版本号落后 13 个修订
#   而全绿」——此前没有任何门禁核版本号。
_vj_ver = (_vj.get('skill_version') or '').strip()
_cl = read('SKILL_CHANGELOG.md')
check('D13 版本号三处一致', bool(_vj_ver) and _vj_ver in README and _vj_ver in _cl,
      'version.json=%s README含=%s CHANGELOG含=%s'
      % (_vj_ver or '?', bool(_vj_ver and _vj_ver in README),
         bool(_vj_ver and _vj_ver in _cl)))

print()
print('== 文档一致性: %s（失败 %d 项）==' % ('ALL PASS' if not fails else 'FAIL', len(fails)))
sys.exit(0 if not fails else 2)
