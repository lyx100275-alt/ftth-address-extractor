---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '15293d4c-478a-4bed-9d1a-be7dd5856479'
  PropagateID: '15293d4c-478a-4bed-9d1a-be7dd5856479'
  ReservedCode1: '4959067c-760d-41de-8c2b-79887f396925'
  ReservedCode2: '4959067c-760d-41de-8c2b-79887f396925'
---

# SKILL 修订记录（完整版）

> 本文件自 `SKILL.md` 外移（三十一）：SKILL.md 只保留最近两条，本文件保存全部历史。（三十九起 SKILL.md 不再保留条目正文，统一指向本文件。）
> 追加规则：新条目加在**本文件顶部**（本说明之后、最新条目之前），编号沿用 SKILL.md 的序号体系。
> 历史说明：外移前（二十五）与（二十六）顺序笔误，外移时已按编号序修正。

### 2026-10-02（一百四十八）：README 追补 —— 门禁现状与目录表与 0.147 对齐

**动因**：README（给人看的入口）多处停在 0.108 时代：版本号、T14/T17 门禁口径、tests 语料位置；T4c/T4d/T4e/T17b 四项新门禁与分层引擎无处可查。纯文档追补，零代码改动。
| # | 改动 | 文件 |
|---|---|---|
| 一 | 版本号 0.108.0 → 0.147.0（一百四十七） | `README.md` |
| 二 | 冒烟说明刷新：T1b 权威实现锁全表、T4c/T4d/T4e、T14 默认即跑 + `--regen-golden` 唯一重生口、`--with-dxf` 仅 T5 用、T17b 形状覆盖 | `README.md` |
| 三 | 目录表刷新：scripts 43 引擎清单补全（dxf_extract/evidence_builder/conflict_engine/门禁件/ledger_state）、tests 去外置语料改 golden+矩阵+说明、`changelog/` 归档行、`version.json` 行补 contract_coverage 登记义务 | `README.md` |

**验证**：`check_docs` D1~D12 ALL PASS（D7/D9 链接零断链）；`budget` rc=0；`check_contract_coverage` rc=0。代码零改动，smoke 不重跑（上一轮 0.147.0 全绿即本轮代码基线）。
- **版本**：`version.json` 0.147.0 → **0.148.0**

### 2026-10-02（一百四十七）：P2-2 第二组 —— 待裁决后处理抽为 merge_pending_items

**动因**：`analyze_coverage_vshape.py` main 仍逾 1200 行。第一组（尺度锚）已验证“抽取锁真图回归”的做法有效，本轮抽第二组。
| # | 改动 | 文件 |
|---|---|---|
| 一 | 新顶层函数 `merge_pending_items(result)`：待裁决去重（内容 key 保序）+ 同形态合并（仅「V段数与箱数不一致」+「窗口内无箱号锚」≥2 条成组）。块内 45 行逐字节搬移（脚本核对一致），只碰 `result['需人工裁决']`，依赖仅 `json` + `print`、无 main 局部量、无提前退出；main 内原址改为单行调用 | `scripts/analyze_coverage_vshape.py` |
| 二 | T1b 补锁 `merge_pending_items`（单一实现核对，防 main 内重写第二份） | `tests/run_smoke.py` |

**验证**：`py_compile` 全仓 0 错；`check_docs` D1~D12 ALL PASS（D8 43=43=43）；`budget` rc=0；`check_contract_coverage` rc=0；`run_conflict_matrix` ALL PASS；`run_smoke` ALL PASS（含 T1b 新锁、T14 三图 golden 默认回归全对拍一致 —— 抽取行为零漂移）。
- **版本**：`version.json` 0.146.0 → **0.147.0**
- **残留**：main 仍约 1200 行；C8 逐箱状态段（`_dg_ok`/`judge_pending_scope` 循环）与跨阶段对账段留待第三组（需 `args`/`log`，依赖形态不同，另开一轮）。

### 2026-10-02（一百四十六）：C7 登记翻转补齐 —— 契约 9/9 全 enforced + T1b 补锁

**动因**：一百四十五 P2-4 落了 C7 转 enforced 的全部代码（`check_launch_path.py` + 启动器 `FTTH_VIA_LAUNCHER` + `write_json` 写 `_via_launcher` + T4e/T17b），但 `version.json` 登记与两处文档仍写 C7 `declared` —— 代码与登记不一致。本轮只翻登记、零代码改动。
| # | 改动 | 文件 |
|---|---|---|
| 一 | C7 登记翻为 `enforced`：producer 补 `ftth_common.py`、checker 登 `check_launch_path.py`、`evidence` 写清标记链、`evidence_tokens` 登 `FTTH_VIA_LAUNCHER` / `_via_launcher`（门禁逐个核对标识，空即 FAIL） | `version.json` |
| 二 | L1 节首两档表翻为 `enforced` 9 条 / `declared` 空；C7 就地标注改挂标记链与 T4e/T17b（去“唯一 declared”旧文） | `SKILL.md` |
| 三 | §九·补状态句同步为 9 条全 `enforced` | `references/operations_discipline.md` |
| 四 | T1b 补锁 `build_scale_anchors`（analyze_coverage_vshape 主循环抽出的第一组）与 `write_json`（ftth_common 产物标记出口）—— 单一实现核对，防 inspect 内重写 C9 式双实现重演 | `tests/run_smoke.py` |

**验证**：`check_docs` D1~D12 ALL PASS（D8 43=43=43、D10 9/9 双向一致、declared 空、unenforced 空）；`check_contract_coverage` rc=0（9/9 enforced）；`budget` rc=0（SKILL.md 42305 B、operations_discipline.md 43460 B，均在预警线内）；`run_conflict_matrix` ALL PASS；`run_smoke` ALL PASS（含 T1b 新两锁、T4c/T4d/T4e、T17b、T14 三图 golden 默认回归）。
- **版本**：`version.json` 0.145.0 → **0.146.0**

### 2026-10-02（一百四十五）：三方会审整改批 —— 真图回归转正 + 契约/调用链门禁落地 + 版本库建立

**背景**：三方会审（0.144.0）给出 86/100，发现三个要紧问题：① **真图回归长期是红的且没人知道**
（T14 golden 基线自 0.113.0 起跨 30 个修订从未重生成，且默认 `--with-dxf` 才跑 ⇒
「全部门禁通过」这个绿灯**从来不含真图**）；② **云峰 331 户在默认链路上产不出来**
（`household_annotation` 判 `present` 使 plan 选直读法 → parse 产出 214 层全 null →
count-box 被跳过，331 户必须人工知道要跑 `count-box` 才拿得到）；③ 契约落地登记里
C3/C9 两条 `evidence` 与代码现实不符却被判 `enforced` 通过。

| # | 事项 | 落点 |
|---|---|---|
| 壹 | **P0 形态检验**：新增 `household_annotation` 覆盖率判据 —— 命中 y 去重数 / 楼层带 y 去重数 < 30% 判 `variant`（疑列汇总/图例乘数写法）并指明降级到图标法。云峰实测 1.8%（2 条 `*16` vs 114 个楼层带）→ variant；凤鸣朝阳 87.3%、柳辛庄 87.5% 保持 present。**修复后云峰默认链路即产出 331 户 / 13 列**，与 golden 期望一致 | `scripts/plan_methods.py` `_HH_PER_FLOOR_COV_MIN` |
| 贰 | **P0 真图回归转正**：T14 三图 golden 由「仅 `--with-dxf`」改为**默认执行**；新增 `--regen-golden`（基线只能由该命令重生，手工改 json 无任何机制能察觉）；移除 `pipeline_rc` 重复断言；基线按整改后行为重生（`version:2`）。T17 随 T14 一并默认化 | `tests/run_smoke.py`、`tests/golden_expected.json` |
| 叁 | **P0 新门禁接入冒烟链**：新增 T4c（`check_contract_coverage.py`）与 T4d（`check_transitions.py` 判据 #6 的 4 项正反用例）。此前这两个门禁在 run_smoke/README 里 0 次命中 —— 「新增门禁却永不执行」比没有门禁更坏 | `tests/run_smoke.py` |
| 肆 | **P0 目录卫生**：删 6 个 `*.bak_*`（463 KB，已确认在宿主 `skills/.backup/` 快照内）+ 44 个 `.pyc` + 2 个 `__pycache__` + `.interpreter_cache.json`；新建 `.gitignore`。此前直接违反 L0-I6「技能目录内只放运行文件」 | 技能目录 |
| 伍 | **P1 evidence 内容对拍**：修正 C3（检查器实为 `ftth.py` pipeline 的申报制分支，非 `check_contracts.py`）与 C9（枚举实为 `SOURCE_*`，非 `E-HUMAN-*`；`E-HUMAN-*` 由裁决台账承载）的登记；门禁新增 `evidence_tokens` 字段并**逐个在登记脚本里找** —— 字段非空不等于内容属实，此前正是这条盲区让两条错登记绿灯通过 | `version.json`、`scripts/check_contract_coverage.py` |
| 陆 | **P1 rc 语义统一**：`merge_json.py` 冲突分支写盘失败由「log 后被后续 exit 吞掉」改为 `rc=4`；`ftth_geom.py` 读 DXF 失败由 `except IOError` 改 `OSError`（IOError 是其别名，写法只会让人以为二者不同）。全仓 `except IOError` 由 4 处降为 3 处 | `scripts/merge_json.py`、`scripts/ftth_geom.py` |
| 柒 | **P1 版本库建立**：`version.json` 长期声称「版本库位于工作空间技能版本库」而该目录**根本不存在**，151 条修订无任何 diff 能力。现按 `skill-version-manager` 约定建 `技能版本库/ftth-address-extractor/`（git `main` 分支），基线入库并打 tag `v0.145.0` | `技能版本库/ftth-address-extractor/` |
| 捌 | **P1 户数可信度透传**：`gen_addressbook.py` 新增 `--count-box-json`，读 `count_box.json` 的「户数构成」分级并写入成品**备注列尾行**（不新增数据列 —— 24 列 A~X 是定稿结构；不传该参数则零影响）。云峰 331 户里 231 户（70%）落在自述不可信列上，此前该分级只躺在产物里，下游拿到 331 就当定案 | `scripts/gen_addressbook.py` |
| 玖 | **P2-1 T1b 补锁**：权威实现表新增 `run_c9` / `hu_mult_of` / `sanitize_nonfinite`。此前 C9 曾是两份实现（靠 CHANGELOG 文字搬家），若日后有人在 inspect 里重写，T1b 不会拦 | `tests/run_smoke.py` |
| 拾 | **P2-3 契约两档读法**：SKILL.md L1 节首加「`enforced` 可照着跑 / `declared` 靠自觉」两档表 + C7 就地标注；分档机器真源是 `version.json` 的 `coverage`，改本文文字无效 | `SKILL.md` |
| 拾壹 | **P2-4 C7 升 enforced**：新增 `scripts/check_launch_path.py`。解法不是「门禁去追调用链」（做不到，门禁看不到父进程），而是把调用链变成**产物上可见的事实** —— 启动器设 `FTTH_VIA_LAUNCHER` → `write_json` 在产物顶层写 `_via_launcher: true` → 门禁反查。标记刻意是**布尔真值**而非时间戳/路径（含变量的标记会让 golden 永久假红 —— 一个门禁不能毒化另一个门禁）。配 T4e 正反用例 + T17b 形状覆盖率反查（`_FRESH_KEYS` 漏补即假绿） | `scripts/ftth_launcher.py`、`ftth_common.py`、`check_launch_path.py`、`tests/run_smoke.py` |
| 拾贰 | **P2-2 巨型 main 拆分（第一步）**：`analyze_coverage_vshape.py` 的尺度锚块抽为 `build_scale_anchors()`（main 1275 → 1245 行）。首次抽取漏传局部量 `CBRE` 导致 `NameError`、fmcy coverage 阶段 rc=1 —— **由 T14 golden 当场抓住**，这正是「这类抽取必须锁在真图回归之下做」的实证。后续分批，行为不变为前提 | `scripts/analyze_coverage_vshape.py` |
| 拾叁 | **CHANGELOG 归档**：459 KB / 151 条拆为主文件 20 条 + `changelog/part01~04`（每 40 条），合计条目数 151 零丢失。实测反查「`scripts/ftth.py` 最近何时改」原本只能匹配到 12 个修订前。D9 豁免 `changelog/`（归档正文含正则字面量会被链接正则误判，改了即篡改历史） | `SKILL_CHANGELOG.md`、`changelog/` |

**验证**：`py_compile` 43 脚本 0 错；`check_docs` D1~D12 ALL PASS；`check_budget` rc=0
（SKILL.md 42,058 B，距预警线 4,942 B）；`check_contract_coverage` rc=0 + 负向用例 6 项
（含新增的「evidence_tokens 找不到」一项）；`check_launch_path` 正/反/空目录三项按预期；
`run_conflict_matrix` ALL PASS；**`run_smoke` ALL PASS 且默认含真图**（T14 三图全对拍一致、
T4c/T4d/T4e/T17b 四项新门禁全绿）；云峰全链重跑 331 户由默认链路产出。

- **版本**：`version.json` 0.144.0 → **0.145.0**
- **仍存缺口（诚实登记）**：① `fmcy`/`yf` 的 `parsed.json`/`coverage.json` md5 与整改前
  不同 —— 逐项复核后确认是**预期内**（`_via_launcher` 标记与 `household_annotation` 形态
  检验带来的字段/选法变化），inspect 的 rc/FAIL/WARN 语义比对全部一致，不是回归；
  ② C7 门禁只能判「产物是否经启动器派生」，**判不出「谁调的」**（人工裸调经启动器
  仍算合规）—— 这是跨进程可观测性的上界，已写进脚本 docstring；
  ③ `analyze_coverage_vshape.py` 的 main 仍有 1,245 行，P2-2 只完成第一步；
  ④ `inspect_closure.py` 主流程 1,098 行未拆（无真图覆盖，不宜盲改）；
  ⑤ C3/C9 的 `evidence` 已改正，但**门禁只能核 `evidence_tokens` 里的标识符**，
  自由文本部分的准确性仍靠人。

### 2026-10-02（一百四十四）：scripts_reference.md 精简瘦身 11036B（-23.2%）——脱预警线

**动因**：scripts_reference.md 47650 B 超预警线 650 B（阈值 47000），与 SKILL.md 精简同批完成。**只精炼表达方式，不改任何参数/判据语义**，三批 multiedit 完成。

**改动**（scripts_reference.md 单文件）：

| 批次 | 区域 | 手法 |
|---|---|---|
| ① | 脚本参数表（14 行）+ probe 画像信号表 + 多地块编排段 | 删每格括号内二次解释、删历史「2026-09-XX」标注、删冗余「实测」修饰；保留全部参数名与判据 |
| ② | 解释器契约（删 PowerShell 探测脚本全文 25 行→表格化）+ 易错点（8 条散段→条目化）+ 实测案例 + 退出码细则 | 删探测脚本代码块（启动器已自动探测，用户无需手敲）；易错点合并同类项；删「为什么」解释留规则 |
| ③ | 统一入口说明 + 户数形态判别 | 删 16 子命令重复列举（已在依赖矩阵表）；删「注册面=分发面」解释留规则；户数形态四类表格压缩 |

**保留**：42 个脚本完整参数列表；16 子命令×依赖矩阵全部 `必需`/`可选`/`—` 值；易错点 8 条全部保留（含本日新加 floor-pattern/hu-pattern 两坑）；解释器候选清单+`FTTH_PYTHON`+rc=9 语义；户数四形态 A/B/C/D+三条铁律；`geom.json` schema v3；`ledger_elements.py` 输出字段表；assemble/apply-ruling 专节语法。

**验证**：`check_docs.py` D1~D12 **ALL PASS**（D8 脚本数 42=42=42、D9 断链=0、D1 子命令 16=16）；`budget` scripts_reference.md **36614 B [OK]** 距预警线余量 10386 B；全部 references 文件均在预警线内。

- **版本**：`version.json` 0.143.0 → **0.144.0**。

### 2026-10-02（一百四十三）：SKILL.md 精简瘦身 6463B（-13.7%）——删解释留规则，脱预警线

**动因**：SKILL.md 47244 B 超预警线 244 B（阈值 47000，宿主截断 51200 无开关），用户要求「同样意思、保持准确的前提下更精炼表达、减少体积」。**只精炼表达方式，不改任何规则语义**，四批 multiedit 完成。

**改动**（SKILL.md 单文件）：

| 批次 | 区域 | 手法 |
|---|---|---|
| ① | 执行摘要 + L0-I1/I2/I3/I6 + L1-C3/C7/C8 | 删背景叙述/实测日期/解释文字：C8 结果状态十三行解释压至七行、I6 落盘纪律长行压缩、C7 解释器规则压缩、I2 五禁区表格说明列精简 |
| ② | 图纸信息模型执行纪律 + 测量架构（铁律九条/户数优先级/覆盖必做）+ Step 1b `--fx-map`/`--bldg-map` 回填段 | 全部条目化去散文，删防御性修饰词（铁律本身即不可违反），删括号内二次解释 |
| ③ | I6 操作纪律表 + L1 节首 + C1 信号状态 + C4 对照表判据 | 散段转表格、删冗余例证（C4 保留判据公式） |
| ④ | 状态机锁定基准/回读校验 + Step 1a 几何缓存/画像 + Step 1b 入口 + Step 2 三条硬门禁/空集合 | 入口子命令清单保留、删旧名与重复出处说明；硬门禁保留判据只删历史标注 |

**保留**（一条不丢）：L0-I# / L1-C# 全部条目编号；全部表格结构；全部 `references/` 引用链接；全部机器可判字段（`result_origin`/`result_confirmation`/口径A~B′/STATES 枚举）；正则传参两坑（本日新加的第二坑 `[-]?` 完整保留）；契约落地登记 `contract_coverage` 指引。

**删掉的仅三类**：① 历史叙述（「2026-09-XX 实测背景」，溯源靠本文件）；② 解释性文字（「为什么这么规定」，执行只需规则本身）；③ 防御性重复修饰（「严禁/必须/绝对不得」在铁律语境下的冗余强调）。

**验证**：`check_docs.py` D1~D12 **ALL PASS**（D9 断链=0、D10 契约登记双向一致 9/9、D11 状态机节点双向对拍、D8 脚本数 42=42=42、D12 禁止迁移 6=6）；凤鸣朝阳 pipeline 8.03s 全阶段 rc=0、inspect rc=0（FAIL 0/WARN 3 与精简前一致，17 箱覆盖闭合不变）；`budget` SKILL.md **40781 B [OK]** 距预警线余量 6219 B。

- **版本**：`version.json` 0.142.0 → **0.143.0**。

### 2026-10-02（一百四十二）：架构 P0 两项 —— 契约落地可观测 + 当前态可观测

**背景**：三方会审（Skill 架构专家视角）指出两个结构性缺口，均属「靠推断/靠自觉的判断没有机器落点」：
① **只定义不产出**：L1-C8 立了整天而产出方零落地，inspect 的 C9 恒 SKIP、从未拦下任何东西，
   而文档读起来一切正常 —— 当时只靠 CHANGELOG 一句**文字**警告兜住（文字是给模型看的，不是给机器看的）；
② **状态机缺正向锚点**：check_transitions 的判据 #1~#5 全是**否定式**检查，「我在哪个节点」全靠推断，
   表现为两条具体漏网：申报走到 OUTPUT 而成品根本没生成（#2/#4/#5 都需成品存在，故一条都不响）；
   三本台账齐 + inspect rc=0 就被当成「已过 USER VALIDATION」，而实际可能仍有 pending。

| # | 改动 | 落点 |
|---|---|---|
| 壹 | **契约落地登记**：`version.json` 新增 contract_coverage 段，每条 L1 契约登记 producer_scripts / checker_scripts / coverage(enforced·declared·unenforced) / evidence /（declared 时必填）gap。**只登记 L1 轴**，Step2 的 C1~C10 是另一根轴，仍由 D4 负责（两轴混表会重演「C9 两个含义」的名目冲突） | `version.json` |
| 贰 | **新增契约落地门禁**：SKILL.md L1 契约 C 编号与登记表键**双向**对拍（文档新增 C11 未登记 → FAIL）；产出方/检查器文件须真实存在；unenforced 与「enforced 却无检查器」→ FAIL；declared 必带 gap；evidence 必填。0 一致（可带 declared WARN）/ 2 不一致 / 3 无可核对象 | scripts/check_contract_coverage.py（新增，脚本数 41→42） |
| 叁 | **当前态载体**：状态.json（ftth.session_state/v1，与三本台账同目录），记 当前状态/上一状态/方向/证据/更新时间。子命令 state-set / state-get；状态名不在枚举 → rc=3。**不判迁移是否被允许**（那是 SKILL.md + check_transitions 的权力），只记「我在哪」 | scripts/ledger_state.py |
| 肆 | **迁移判据 #6**（申报态与证据对拍）：① 申报 ≥ LOCKED BASELINE 而仍有 pending；② 申报 ≥ ASSEMBLE 而闭包 rc≠0；③ 申报 ≥ OUTPUT 而无成品。**未申报只判 WARN 不拦门**（存量项目无此文件，新增观测点不得变成破坏性变更）；**不判倒退**（回 REPROBE/USER 是正常作业路径） | scripts/check_transitions.py |
| 伍 | **STATES 成为状态节点枚举唯一权威**（照抄 SKILL.md 状态机图节点名，含空格）；D11 与文档图双向对拍 | scripts/ledger_state.py + check_docs.py |
| 陆 | **D10/D11/D12 三项新检查**：D10 契约登记双向一致 + declared 必带 gap + 无 unenforced；D11 状态机节点名文档==代码；D12 禁止迁移条数代码==文档（N_FORBIDDEN 此前散落 docstring/通过语/SKILL.md 三处，加判据时必漏且机器查不出 —— 本次实测命中） | scripts/check_docs.py |
| 柒 | **D8 暗数改具名常量**：脚本数期望值此前写死在表达式里（
py == 41），是三处计数中唯一 grep 不到的；新增脚本时改了 SKILL/README 也会 FAIL，症状与「忘了改文档」完全一样，误导排查方向 | scripts/check_docs.py |
| 捌 | **体量回压**：SKILL.md 与 scripts_reference.md 本次净增约 700 B / 1100 B，全部靠删除冗余表述回压到 47,000 B 预警线**之内**（分别余 2 B / 27 B）。删除的均为重复限定语与已外移内容的历史日期标注，未删任何判据 | SKILL.md / references/scripts_reference.md |
| 玖 | **口径全表下沉** operations_discipline.md §九·补：当前态三条机械判据 + 三条设计取舍、契约落地四字段与三档取舍、为何只登记 L1 轴 | references/operations_discipline.md |

**验证**：py_compile 42 个脚本 0 错；check_docs ALL PASS（D1~D12）；check_budget rc=0
（SKILL.md 46,998 B / scripts_reference.md 46,973 B，均在预警线内）；conflict_matrix ALL PASS；
check_contract_coverage rc=0 + **负向用例 6 项全部按预期判 FAIL**（C11 未登记 / C1 enforced 无检查器 /
C2·C4 检查器文件缺失 / C3 缺 evidence / C8 产出方文件不存在）；
check_transitions 判据 #6 **正反用例各 4 项**（申报 LOCKED+pending → rc=2；申报 OUTPUT 无成品 → rc=2；
状态名非法 → rc=2；无状态.json → WARN 且 rc=0）；ledger_state 状态回退（USER VALIDATION → PLAN）
正常受理并记 方向=回退或原地（回退是正常作业路径，不拦）。

- **版本**：`version.json` 0.141.1 → **0.142.0**
- **门禁现状（诚实登记）**：L1-C1~C9 中 8 条 enforced、**C7 declared** —— 「业务脚本是否绕过
  ftth_launcher.py 直调」是跨进程事实，现有门禁都跑在单脚本内，机器判不了；缺口原文写在登记的
  gap 字段里，**不得用 declared 掩盖未落地**。这是当前契约覆盖的最大缺口。
- **未做（本次范围外）**：SKILL.md 未整体瘦身（仍 46,998 B，距预警线仅 2 B）；
  SKILL_CHANGELOG.md 未按版本归档（449 KB 单文件）；契约未按「可机检/纪律性」两档拆分。
  这三项属评审 P1，不在本次 P0 范围内。
### 2026-09-30（一百四十一·补）：会审两条冲突项裁定——均维持现状

**用户裁决**：① V型分界降级为候选（报告§五）**否决**，维持2026-09-27裁决“有米标优先V型不再互验”；② 关系pending标记出表（报告§三示例）**否决**，维持P0出口门禁fail-closed（任何pending仍rc=2禁出表）。证据优先级重排一并暂搁。
**改动**：零代码（本补只落盘裁决结论，防后人据报告原文重提）。
- **版本**：`version.json` 0.141.0 → **0.141.1**。
### 2026-09-30（一百四十一）：会审收敛——冲突议题地址/关系分域

**动因**：会审报告§三+§十三.4（地址对象未定 vs 地址已定而与FX关联未定，二者不得混为一谈）。只加不改：门禁判据/rc/机读键名均不动，新增“域”维度。
| # | 改动 | 文件 |
|---|---|---|
| ① | conflict_engine加域词汇+domain_of：五类linkage型恒为relation；PENDING/INVALID按对象路径启发（分纤箱/覆盖→relation，否则address）；未知类型默认relation；issue()自带“域”；summarize加“按域”（缺键老议题回算兼容） | `scripts/conflict_engine.py` |
| ② | inspect冲突汇总段加“按域”展示行（只展示，不参与rc） | `scripts/inspect_closure.py` |
| ③ | 冲突矩阵加META域回归7项（静态映射/路径启发/默认方向/自带域/按域计数/老议题兼容） | `tests/run_conflict_matrix.py` |

**验证**：`py_compile`绿；`conflict_matrix`（含新增7项）/`run_smoke`/`check_docs`/`budget` ALL PASS；凤鸣真图inspect重跑：议题0项，按域空分组，rc=0与上一版一致；合成pending桩（parse箱result_confirmation=pending）：C9 FAIL rc=2不变，议题域=relation，机读口带域。
- **版本**：`version.json` 0.140.0 → **0.141.0**。
- **未动（须用户裁决）**：V型分界降级为候选（与2026-09-27“有米标优先V型不再互验”正面冲突）；关系pending允许出表并标记（与P0出口门禁fail-closed正面冲突）；证据优先级重排选法。
### 2026-09-30（一百四十）：V3楼层表搬家全搬——split_units族入引擎

**动因**：一百三十九只搬了写法谱/楼层分类；分单元几何（云峰八单元全丢的根因区）仍在parse内（214行）。本轮全搬，parse只留编排。
| # | 改动 | 文件 |
|---|---|---|
| ① | floor_engine加分单元五函数：no_fx/marker（含共享列克隆/落空挂靠）/fx_cluster/synth分离合成/dispatcher编排；正则束显式传参，日志与PENDING_NOTES/SYNTH_UNIT_MARKS由调用方执行；仅import ftth_naming+ftth_common底层域 | `scripts/floor_engine.py` |
| ② | parse分单元块214行→50行编排（kind/留痕/日志文案逐字保留；旧实现删除） | `scripts/parse_dxf_structured.py`（2217→2053行，-164行） |

**验证**：`py_compile`绿；`check_docs`/`budget`/`conflict_matrix`/`run_smoke` ALL PASS；凤鸣真图parse双路与上一版逐字节零差异。
- **版本**：`version.json` 0.139.0 → **0.140.0**。
- **残留**：单元内组装（floor_table/口径A直判）、scripts_reference清单行（floor_engine）。
### 2026-09-30（一百三十九）：V3楼层表搬家起步——写法谱/楼层分类入引擎

**动因**：一百三十二预告“归属/楼层表搬家”，归属已完（attribution_engine）；本轮搬楼层侧最自洽的一块（分类纯函数），split_units族与楼层表组装另开。
| # | 改动 | 文件 |
|---|---|---|
| ① | 新建`floor_engine.py`：CABLE_FORM_RES写法谱+取值/拼装/检测三函数与parse_floor_info六路分流逐字搬入（取x留痕/乘号取非空组/米数失败可见）；正则束显式传参，warnings出口由调用方打日志；仅import ftth_naming+ftth_common底层域 | `scripts/floor_engine.py`（新） |
| ② | parse写法谱块→同名引用（re-export，count_households组名约定零改动）；parse_floor_info→薄包装（正则束组装+warnings日志转发，6元组返回不变）；冻结注释修订（搬家第三类含floor_engine） | `scripts/parse_dxf_structured.py` |
| ③ | 脚本计数41三处同步；`scripts_reference.md`清单行留待下轮与瘦身同做（47KB预警线内，详见一百三十八） | `SKILL.md`、`README.md`、`scripts/check_docs.py`（D8=41） |

**验证**：`py_compile`绿；`check_docs`/`budget`/`conflict_matrix`/`run_smoke` ALL PASS；凤鸣真图parse双路（absent/合成bldg-map）与上一版逐字节零差异。
- **版本**：`version.json` 0.138.0 → **0.139.0**。
- **残留**：split_units族+楼层表组装、scripts_reference清单行（floor_engine）。
### 2026-09-30（一百三十八）：文档 hygiene——清单补5引擎行+净零瘦身回预警线内

**动因**：V3五引擎（dxf_extract/evidence/conflict/attribution/coverage）无清单行；scripts_reference.md 46897B距预警仅103B，直接加行即超线。按净增为零纪律同步瘦身。
| # | 改动 | 文件 |
|---|---|---|
| ① | 行16计数35→40（同字节）；§清单表补5紧凑行 | `references/scripts_reference.md` |
| ② | 等量瘦身（均指回权威定义、零信息丢失）：gen行P列细则→addressbook_template.md；verify行前缀规则→step2_selfcheck.md；vshape行尺度锚→coverage_rules.md「V型计算」；ledger行箱柜层→本文件§三条判据；count-box行删旧名历史注 | `references/scripts_reference.md` |

**验证**：`check_docs` D7/D9 ALL PASS；`budget` rc=0（46973B，距预警线27B）；`run_smoke`/`conflict_matrix` ALL PASS（纯文档）。
- **版本**：`version.json` 0.137.0 → **0.138.0**。
- **残留**：楼层表搬家另开。
### 2026-09-30（一百三十七）：V3对称收口——竖线法统一字段落地

**动因**：一百三十六只接了V谷底一路；竖线法（analyze_coverage.py）仍零统一字段。本轮收口，coverage双路齐全。
| # | 改动 | 文件 |
|---|---|---|
| ① | `coverage_engine.py`加`vertical_floor_evidence`：与竖线法口径一一对应（有直写采纳→direct+total_map；无直写走区间→derived_calc+interval；None→unresolved+unknown）；词汇仍唯一来源evidence_builder | `scripts/coverage_engine.py` |
| ② | 竖线法箱产出口随行`安装楼层统一`（分支判据/口径文案/rc不动；`多箱分界线索`摘要不重复加——C3只消费`分纤箱[]`条目） | `scripts/analyze_coverage.py` |

**验证**：`py_compile`绿；`check_docs`/`budget`/`conflict_matrix`/`run_smoke` ALL PASS；合成竖线法桩（直写采纳/区间/None三态）全过；凤鸣真图coverage-vshape统一字段不受影响（17/17）。
- **版本**：`version.json` 0.136.0 → **0.137.0**。
- **残留**： scripts_reference 清单表补行（待与瘦身同做）、楼层表搬家另开。
### 2026-09-30（一百三十六）：V3对称起步——coverage统一证据+V谷底产出落地

**动因**：一百三十残留（coverage侧零统一字段，C3按parse单边+legacy比对）。本轮只做V谷底一路（analyze_coverage竖线法另开）。
| # | 改动 | 文件 |
|---|---|---|
| ① | 新建`coverage_engine.py`：`vshape_floor_evidence`薄适配（词汇唯一来源evidence_builder：source=derived_calc/context=vshape/note照抄V谷底口径；只import evidence_builder+ftth_naming） | `scripts/coverage_engine.py`（新） |
| ② | V谷底产出口随行`安装楼层统一`（判据/口径/rc不动；老产物无字段时C3走legacy逐字节不变） | `scripts/analyze_coverage_vshape.py` |
| ③ | 脚本计数40三处同步；`scripts_reference.md`清单表仍不动（预警线原因同前） | `SKILL.md`、`README.md`、`scripts/check_docs.py`（D8=40） |

**验证**：`py_compile`绿；`check_docs`/`budget`/`conflict_matrix`/`run_smoke` ALL PASS；凤鸣真图coverage-vshape重跑：逐箱含`安装楼层统一[derived_calc/vshape]`且 legacy 值零差异。
- **版本**：`version.json` 0.135.0 → **0.136.0**。
- **残留**：analyze_coverage竖线法统一字段、 scripts_reference 清单表补行（待与瘦身同做）、楼层表搬家另开。
### 2026-09-30（一百三十五）：V3 PhaseB全搬——改派循环入引擎+parse只留编排

**动因**：一百三十四只搬了纯函数（归一/解析/载入），改派循环（~120行，parse内最大业务块）仍在parse内。本轮全搬，parse只留摘除/日志/落盘编排。
| # | 改动 | 文件 |
|---|---|---|
| ① | `attribution_engine.py`加`apply_reassignment`（纯计算：全图texts出发/重号坐标配对/单元号双字段/跨栋留痕坐标；不改入参结构、不写settled/pending；只import ftth_naming） | `scripts/attribution_engine.py` |
| ② | parse改派块120行→22行引擎调用+原样日志/meta尾（拼接保留，逐字节一致）；120行旧实现删除 | `scripts/parse_dxf_structured.py`（2441→2318行，-123行） |

**验证**：`py_compile`绿；`check_docs`/`budget`/`conflict_matrix`/`run_smoke` ALL PASS；凤鸣真图absent路与present合成路双重跑：与一百三十四产物逐字节零差异（57141B/57946B）。
- **版本**：`version.json` 0.134.0 → **0.135.0**。
- **残留**：coverage侧统一字段对称（0.130残留，待coverage_engine）、楼层表搬家另开一轮。
### 2026-09-30（一百三十四）：V3 PhaseB起步——归属纯函数独立+parse改调薄包装

**动因**：V3去parse业务决策。PhaseA已给安装楼层加去决策开关（--floor-mode nofloor）；本轮把归属侧纯函数搬出parse（归属/楼层表搬家第一步，只搬无状态部分，改派循环仍在parse编排）。
| # | 改动 | 文件 |
|---|---|---|
| ① | 新建`attribution_engine.py`：`norm_bldg`/`resolve_bldg_name`自parse逐字搬入（bug-for-bug，含# vs 号、前缀最长命中）+`load_bdg_map`（文件载入与结构校验，失败返回error由调用方判rc=2，不exit不log）；仅import ftth_naming（与evidence_builder同DAG纪律），零业务依赖，不定案 | `scripts/attribution_engine.py`（新） |
| ② | parse改调：加`import attribution_engine`；`--bldg-map`载入走`load_bdg_map`（log文案/rc=2语义逐字保留）；`_norm_bldg`/`_resolve_bldg_name`改为薄包装（调用点零改）；冻结注释修订（允许第三类：搬家类抽取） | `scripts/parse_dxf_structured.py` |
| ③ | 脚本计数38→39三处同步；`scripts_reference.md`清单表本轮不动（该文件距47KB预警线仅103B，加行即超线，留待下轮与瘦身同做） | `SKILL.md`、`README.md`、`scripts/check_docs.py`（D8=39） |

**验证**：`py_compile`绿；`run_smoke`/`conflict_matrix`/`check_docs`（D8=39）ALL PASS；`budget` rc=0（SKILL同字节38→39，scripts_reference未动）；等价桩（归一折叠/#号互换/单元后缀剥离/前缀最长/载入失败与格式错两路rc=2/与parse旧实现逐字对拍）全过；凤鸣真图`probe/plan/parse` rc=0（7栋/17编号/画像100%楼-簇），合成`--bldg-map`单条present路parse rc=0且`parse箱总数=17`、`对照表编号清单=[FL01-FX01]`。
- **版本**：`version.json` 0.133.0 → **0.134.0**。
- **残留**：改派循环（_FX_FORCE/_FX_ENTRY/MOVED/SKIP/UNRESOLVED）仍在parse内；coverage侧统一字段对称、楼层表搬家另开一轮。
### 2026-09-30（一百三十三）：分光方式整项删除（用户裁决：不得由模型猜测）

**动因**：用户裁决分光方式（一级/二级）不得由模型猜测、该项删除。核查：零代码（scripts无分光判定逻辑）、成品表无此列（gen/template均无分光字段）——纯文档层删除，零交付影响。
| # | 改动 | 文件 |
|---|---|---|
| ① | 删除`splitter_rules.md`全文（含“参考线索”芯数推算表——一并删除，不再向用户呈现推算） | `references/splitter_rules.md`（删文件） |
| ② | 清理引用：Step3待确认项举例去“分光方式”并删整条splitter规则行；参考文件索引表删该行；P1禁区举例去“从芯数推分光方式”（禁区本身不动）；frontmatter description去“splitter configs”（分光请求不再触发本技能） | `SKILL.md`（4处，纯删减） |
| ③ | 自检清单删分光条目×2；方法总表删该列项；探查总图特征举例去“分光方式” | `references/step2_selfcheck.md`、`measurement_methods.md`、`probe_checklist.md`（纯删减） |

**有意保留**（非分光方式判定，与本次裁决无关）：`parse_dxf_structured.py:394`探查层`分光器`文字归类（图层信号打分用，不产出任何分光结论）；`probe_checklist`“光分路器”设备属性识别（箱图标计数用）。
**验证**：全仓`分光/splitter`残留零条（上两项除外）；`check_docs`（D7/D9无断链）/`budget` rc=0（纯删减，体量只降不升）；`run_smoke`/`conflict_matrix` ALL PASS。
- **版本**：`version.json` 0.132.0 → **0.133.0**。
### 2026-09-30（一百三十二）：V3 PhaseA——parse去决策开关+C2/C3/gen双模式+凤鸣A/B零差异

**动因**：用户问“parse能否省略安装楼层判定”。核查：coverage独立判定（--bldg-map自消费）、vshape --parse可选、gen回退链None穿透——唯C2/C3/vshape锚配对三处耦合。云峰FX01（parse WF vs coverage 5F vs 答案5F）证明parse多推导一套专产假冲突。
| # | 改动 | 文件 |
|---|---|---|
| ① | parse加`--floor-mode full/nofloor`（默认full）：nofloor跳直写/区间法/回填三路，只定归属（重号丢弃/confirmation/依据来源与区间法分支逐字一致），楼层一律null+“parse未判定”显式标记（result仍描述归属，不触发C9）；非法值rc=2；`参数.floor_mode`落盘；冻结注释修订（允许fail-closed门禁+去决策删减） | `scripts/parse_dxf_structured.py` |
| ② | 统一入口：`parse --floor-mode`镜像注册；`pipeline --parse-no-floor`透传；`inspect --fx-map`注册+透传；pipeline inspect透传`--fx-map _bmap`（_bmap已有产出守卫） | `scripts/ftth.py` |
| ③ | inspect双模式：C2-nofloor改核coverage侧（null即FAIL，无coverage判SKIP）；C3-nofloor改比coverage vs 对照表（需--fx-map，否则SKIP+WARN；跨体系疑似假冲突指引，仍FAIL）；legacy两路逐字节不动；cmap构建上提（C6共用） | `scripts/inspect_closure.py` |
| ④ | vshape潜伏缩进bug修复（nofloor暴露）：`result`骨架建在`if _PARSE_BOXES`内，无可用箱即UnboundLocalError（rc=1）；现提到if外+else补日志。语义：nofloor-parse等价于“未传parse”（配对路守卫本就None-safe），V谷底主计算不受影响 | `scripts/analyze_coverage_vshape.py` |
| ⑤ | gen零改确认：`_fx_display`按`_b.get("安装楼层")` truthy回退，None天然穿透用coverage；mismatch硬停在nofloor下不可触发 | ——（无改动） |

**验证**：`py_compile`绿；`run_smoke`/`conflict_matrix`/`check_docs` ALL PASS；`budget` rc=0；合成桩（C2覆盖侧PASS/FAIL/SKIP三态、C3对照表一致/不一致/缺输入、legacy-null原路FAIL）全过。**凤鸣真图A/B**（full vs --parse-no-floor）：parse 17=17箱（B全null+标记）、coverage 17=17**零差异**（V配对路未触发）、inspect除C3 PASS→SKIP外全同（双rc=0，零issues）、gen双出313户表**零格差异**、B表与桌面20260929终版**零格差异**。
- **使用指引**：nofloor推荐**有总图对照表**图（云峰类；滴水不漏的正是fxmap抄写与回填两路）；absent图（凤鸣类）保持full——parse区间法是独立第二来源，nofloor会诚实地把C3-PASS降为SKIP。PhaseB（归属/楼层表搬家）另开一轮。
- **版本**：`version.json` 0.131.0 → **0.132.0**。
### 2026-09-30（一百三十一）：V3 Phase6起步——冲突引擎独立+C4b/C9改调+issues机读出口

**动因**：V3 §11（Conflict只报冲突不替人消灭冲突）。C9/C4b逻辑收归`conflict_engine`，inspect只剩门禁登记与展示；判据/文案/rc语义逐字节不变，另增`inspect.json/conflict_issues`机读出口（gen仅读rc+指纹，加键安全已核）。
| # | 改动 | 文件 |
|---|---|---|
| ① | 新建`conflict_engine.py`：议题类型封闭枚举7种+`make_issue_id`（确定性）+`issue`（状态恒pending，文件内唯一状态写入）+`summarize`+`collect_unassigned`/`collect_fxmap_gap`（C4b集合运算原样抽出，清单/计数/无三模式）/`fxmap_issues`/`floor_mismatch_issue`+`run_c9`（C9整段原样搬入，R透传保emit截断与汇总口径）；零外部依赖，不定案 | `scripts/conflict_engine.py`（新） |
| ② | inspect改调：C4未归属/C4b（集合运算走引擎，分支报文逐字节不变）/C3不一致+无记录分支议题跟踪；C9整段替换为`run_c9`一行调用；新增“冲突议题汇总”展示段（只展示不参与rc）；payload加`conflict_issues`（issue_id去重） | `scripts/inspect_closure.py` |
| ③ | 脚本计数37→38三处同步 | `SKILL.md`、`README.md`、`scripts/check_docs.py` |

**验证**：`py_compile`绿；`run_smoke`/`conflict_matrix`/`check_docs`（D8=38）ALL PASS；`budget` rc=0（同字节替换，scripts_reference未动）；引擎桩（恒pending/确定性/汇总/无settled定案分支/三模式对账数学）全过；合成inspect桩BAD（16+7 vs 23+pending：rc=2，C4b/C9 FAIL，issues=8〈7 UNASSIGNED+1 PENDING_STATE〉唯一id，闭合字段完整）/GOOD（23+0：C4b/C9 PASS，issues=0）全过；老产物（无统一字段）C3报文逐字节不变。
- **版本**：`version.json` 0.130.0 → **0.131.0**。
### 2026-09-30（一百三十）：V3 Phase3起步——箱证据层+安装楼层统一字段+C3坐标系提示

**动因**：V3 §8（总图与系统图不是同一坐标系，直接比Y造假冲突）+v0.126 P1-1（统一安装楼层对象）。只对“箱”建模，不碰户数/覆盖；legacy键一律保留并存，判据不动。
| # | 改动 | 文件 |
|---|---|---|
| ① | 新建`evidence_builder.py`：来源词汇（direct/derived_calc/map_fill/unresolved）+坐标系词汇（total_map/system_diagram/box_annotation/interval/vshape/unknown）+`make_evidence_id`（确定性）+`unified_installation_floor`（六键对象，原值不归一化）+`box_evidence`；纯构造零裁决，仅import ftth_naming（无循环） | `scripts/evidence_builder.py`（新） |
| ② | parse三处组箱点补`安装楼层统一`：直写分支（direct，总图/箱位标注按源区分）/区间法分支（口径A→direct+system_diagram，口径B→derived_calc+interval，null→unresolved+unknown）/fx-map回填（map_fill+total_map）；收敛选主整dict保留，统一字段随行 | `scripts/parse_dxf_structured.py` |
| ③ | fxmap条目补`安装楼层统一`（坐标系恒total_map；口径A→direct，口径B→derived_calc，无值→unresolved） | `scripts/extract_fx_map.py` |
| ④ | C3 mismatch报文带双方`[context/source]`并加“疑似假冲突”指引（仍FAIL，不自动择一）；R.fail字串不变；双方皆legacy老产物走原报文逐字节不变；cmap recs append第六元，既有r[3]/r[4]不受影响 | `scripts/inspect_closure.py` |
| ⑤ | 脚本计数36→37三处同步 | `SKILL.md`、`README.md`、`scripts/check_docs.py` |

**验证**：`py_compile`绿；`run_smoke`/`conflict_matrix`/`check_docs`（D8=37）ALL PASS；`budget` rc=0（SKILL/README同字节替换，scripts_reference未动）；单元桩（确定性/置信映射/null不断言/原值 verbatim/无定案键）全过；合成C3桩（一致PASS/不一致FAIL判据不动/legacy报文不变/跨体系提示渲染）全过。
- **残留**：coverage侧尚未产出统一字段（C3按parse单边上下文+legacy比对；对称建模待coverage_engine抽取时做）。
- **版本**：`version.json` 0.129.0 → **0.130.0**。
### 2026-09-30（一百二十九）：V3 Phase1-2——冻结parse+抽出dxf_extract.py事实层

**动因**：桌面两份报告研究结论（见2026-09-30研究报告）：v0.126守门（P0出口已修完）+V3路线（去parse业务决策）。按V3附表执行P0第二行“冻结Parse”+P1“抽取dxf_extract”。
| # | 改动 | 文件 |
|---|---|---|
| ① | 新建`dxf_extract.py`事实提取层：只答“图纸上有什么”，`load_dxf/collect_texts/extract_geom`自`ftth_geom` re-export（单一真源，禁再抄）；唯一自有函数`collect_inserts`自parse内联块逐字搬出（含bug-for-bug）；业务正则（UNIT/FX/TITLE/HU/CABLE/FLOOR）一律不得进入本文件 | `scripts/dxf_extract.py`（新） |
| ② | parse宣布冻结纪律（文件头注释：只允许fail-closed门禁类修改，新增识别规则/启发式一律去新分层）；INSERT内联块改调`collect_inserts`，行为零改（空路径无日志/log文案逐字节/None照旧崩） | `scripts/parse_dxf_structured.py` |
| ③ | 脚本计数35→36三处同步（D8门禁要求） | `SKILL.md`、`README.md`、`scripts/check_docs.py` |

**验证**：`py_compile`绿；`run_smoke` ALL PASS；`conflict_matrix` ALL PASS；`check_docs` ALL PASS（D8=36）；`budget` rc=0（SKILL/README系同字节35→36，scripts_reference未动）；等价桩：空路径/None路径/命中过滤/`re.compile(None)`抛TypeError/单一真源（is同一对象）全过。
- **版本**：`version.json` 0.128.0 → **0.129.0**。
### 2026-09-30（一百二十八）：云峰P0对照表对账——fxmap主索引+C4b硬门禁+单元合成透传

**实测动因**：桌面评审报告（`云峰真实DXF专家组实跑评审报告.md` §4）P0：fxmap识别23/23，但parse只进16箱（丢FX03/FX05/FX07/FX09/FX13/FX15/FX22），旧C4仅WARN放行。按报告`fxmap_count==parse_count`要求fail-closed。
| # | 改动 | 文件 |
|---|---|---|
| ① | pipeline新增`--unit-split-keyword`参数；未显式给出时自动取探查建议`suggested_params.unit_split_keyword`下传parse（分离形态单元轴`纯数字+单元关键词`合成开关；云峰2#/3#/6#八单元全丢即因此） | `scripts/ftth.py` |
| ② | parse产物`BDGMAP归属`补对账字段：`对照表编号清单`/`改派文字实例数`/`重号未改派`/`未归属编号数+清单`/`重号未配对实例数`/`parse箱总数`（inspect机读口） | `scripts/parse_dxf_structured.py` |
| ③ | inspect新增C4b对照表对账硬门禁：有BDGMAP时`对照表==parse已归属+未归属`必须成立且未归属必须为0，否则FAIL点名缺失；无BDGMAP时SKIP（旧行为不变）；C4未归属预计算前移，geom缺席时C4b仍可判 | `scripts/inspect_closure.py` |

**验证**：`py_compile`绿；`run_smoke.py` ALL PASS；`run_conflict_matrix.py` ALL PASS；`check_docs` ALL PASS；`budget` rc=0（SKILL.md/scripts_reference.md未动，避开47KB预警线）；合成桩BAD（16+7 vs 23）C4b FAIL、GOOD（23+0 vs 23）C4b PASS。
- **版本**：`version.json` 0.127.0 → **0.128.0**。
### 2026-09-29（一百二十七）：P0 出口门禁——gen 强制绑定 inspect 闭合

**实测动因**：桌面评审报告（`ftth_expert_group_review_v0.126.0.md`）P0-1：pending 覆盖直调 `gen` 仍 rc=0 出表（本轮以最小桩复现确认）。按报告三层方案 fail-closed。

| # | 改动 | 文件 |
|---|---|---|
| ① | `inspect` 产物新增 `inputs_sha256`（parse/coverage/geom/count-box/titleblock 输入指纹；缺席记 null，明示“没检查”） | `scripts/inspect_closure.py` |
| ② | `gen` 新增必传 `--inspect`：①闭合 rc==0；②指纹一致（直路比 parse，组装路认 provenance 链）；③本次输入重扫 pending/unresolved/阻塞（含 assemble「同配置展开待核对」；缺字段老产物 SKIP）；缺一即 rc=2 且不写 xlsx | `scripts/gen_addressbook.py` |
| ③ | `assemble` 产物新增 `provenance`（count/coverage 输入指纹；apply-ruling 整 dict 回写保留，裁决后链依然有效） | `scripts/assemble_households.py` |
| ④ | `ftth_common` 新增 `sha256_file` 唯一入口（指纹一律走它） | `scripts/ftth_common.py` |
| ⑤ | 统一入口 `gen` 注册透传 `--inspect`，示例同步 | `scripts/ftth.py` |
| ⑥ | T6 夹具同步现行契约（coverage 箱补判定依据/来源/result 字段；新增合成 parse；inspect→gen 带闭合）；新增 T19（无闭合）/T20（陈旧闭合）/T22（pending＋伪造闭合，Layer3 重扫独立拦下；另带真 rc=2 闭合门） | `tests/run_smoke.py` |
| ⑦ | Step 4 前置与实现方式补闭合绑定句；gen 参数表补 `--inspect-json` | `SKILL.md`、`references/scripts_reference.md` |
| ⑧ | 冒烟范围 T0~T18→T0~T22（新增 T19/T20/T22；T21 缺号保留） | `README.md` |
| ⑨ | S15 跟随闭合绑定（两档都带 --inspect，保判别力）；D8 漂移归位（`scripts/_launch.py`＋`ftth.cmd` 系被 `ftth_launcher.py` 取代的遗留入口，全仓零活引用，删除，计数保持 35） | `tests/run_conflict_matrix.py`、`scripts/_launch.py`、`scripts/ftth.cmd` |

**验证**：`run_smoke.py` ALL PASS；P0 最小桩改走新版 gen 得 rc=2 且无 xlsx（修复前 rc=0）；凤鸣朝阳真图重跑 inspect→gen 带闭合一次通过（313 户）；云峰组装路（provenance 链）带闭合通过（386 户）。`budget` rc=0（SKILL.md/scripts_reference.md 均 < 47KB 预警线，见验证输出）。
### 2026-09-28（一百二十六）：P 列分纤箱新格式「编号＋（安装楼层）」（用户裁决）

**实测动因**：用户更新桌面云峰/凤鸣朝阳交付表——分纤箱列每个编号后统一加全角括号标注安装位置（云峰 `FX01#（5F）`、凤鸣朝阳 `FL01-FX01（14F）`），并要求技能出表按此要求执行。

| # | 改动 | 文件 |
|---|---|---|
| ① | P 列新格式 `--fx-floor-suffix on`（默认）：编号后加全角括号安装楼层原值（不归一化，`-1F`/`B1` 与图纸口径一致）；安装楼层 coverage JSON 优先、parse JSON 回退；双来源都有且不一致＝矛盾即停 rc=2（L0-I4）；均缺失＝不编造，纯编号+汇总告警列待确认；空值/未分配不加括号；`off` 回退纯编号 | `scripts/gen_addressbook.py` |
| ② | 回读校验③：分纤箱列逐行与内存值比对（出口断言，与表头①/行数②同位阶） | `scripts/gen_addressbook.py` |
| ③ | 模板示例行 P 列 `<分纤箱编号>` → `<分纤箱编号（安装楼层）>`（保持占位形态，楼层/户号格式样本未动） | `assets/标准地址表模板.xlsx` |
| ④ | 模板规则新增分纤箱列格式条目 + 列结构表 P 列说明更新 | `references/addressbook_template.md` |
| ⑤ | Step 4「关联分纤箱编号」行同步新格式 + gen 参数表补 `--fx-floor-suffix` | `SKILL.md`、`references/scripts_reference.md` |

**验证**：`py_compile`绿；`budget` rc=0（SKILL.md 46.7KB、scripts_reference.md 46.9KB 均 < 47KB 预警线）；凤鸣朝阳产物重跑 gen：313 户、17 箱全部 `FLxx-FXxx（nF）` 新格式、分纤箱列 313 行逐行回读一致，且与桌面人工改版逐值一致；`--fx-floor-suffix off` 回退纯编号回归通过；云峰 23 箱格式人工比对一致（含 `-1F`/`B1` 原值写法保留）。

- **版本**：`version.json` 0.125.0 → **0.126.0**。

