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

### 2026-09-27（一百二十三）：专家审核矛盾与重复收敛（零判定放宽批）

**实测动因**：专家视角复核安装版0.122.0，发现计数漂移、分带互斥、rc分叉、正则漂移四类硬伤。本批只收敛定义与实现，不放宽任何门禁（FAIL仍FAIL）。

| # | 改动 | 文件 |
|---|---|---|
| ① | 信号数12→13（`floor_scale`漏同步两处注释+画像描述） | `scripts/plan_methods.py`、`references/measurement_methods.md` |
| ② | 脚本数30→35 | `references/scripts_reference.md` |
| ③ | L1-C9≠Step2-C9命名纪律 | `SKILL.md` |
| ④ | 口径3→5（增A′/B′） | `SKILL.md`、`references/pipeline_details.md` |
| ⑤ | 分带下界优先级终裁（旧维持中点作废）+同名楼守卫rc=2 | `references/coverage_rules.md`、`references/scripts_reference.md` |
| ⑥ | rc=3表述“不适用”→“返回rc=3” | `references/measurement_methods.md` |
| ⑦ | C2补rc=4行、count_box rc=3回落、inspect同码异义 | `SKILL.md` |
| ⑧ | C7增pipeline内部直调例外 | `SKILL.md` |
| ⑨ | coverage参数/质量失败3→2（4处） | `scripts/analyze_coverage.py` |
| ⑩ | gen回读失败3→2 | `scripts/gen_addressbook.py` |
| ⑪ | inspect头注释rc=1无发射点；C9申报纳入count-box | `scripts/inspect_closure.py` |
| ⑫ | norm_floor收敛到`ftth_naming`唯一实现 | `scripts/ftth_naming.py`、`scripts/inspect_closure.py`、`scripts/verify_coverage_truth.py` |
| ⑬ | vshape箱号匹配match→search | `scripts/analyze_coverage_vshape.py` |
| ⑭ | 画像/回落/计时写盘改走`write_json`；删`_pend_scope`薄包装 | `scripts/plan_methods.py`、`scripts/ftth.py`、`scripts/analyze_coverage.py` |

**验证**：`py_compile`全绿；`budget rc=0`；`check_docs D1~D9 ALL PASS`；桌面三项目重跑无回归。`check_budget`零依赖设计保留未动；`assemble`同配置展开、`parse`口径A直判两处自动取舍未动（需用户裁决，列残留）。

- **版本**：`version.json` 0.122.0 → **0.123.0**。

### 2026-09-27（一百二十四）：第二轮审查优化（零判定放宽批）

**实测动因**：第二轮专家复核0.123.0，聚焦首轮残留：体量WARN、分带三方互斥残留、对账旧句、退出码分叉、排序哨兵、箱号匹配半锚定、错误信息缺件、组装展开无机读出口。本批不放宽任何门禁（FAIL仍FAIL）。

| # | 改动 | 文件 |
|---|---|---|
| ① | SKILL体量回OK（C2/C7/C9/口径细则外移，-667B） | `SKILL.md`、`references/scripts_reference.md`、`references/pipeline_details.md` |
| ② | 分带下界旧“维持中点”作废+同名楼守卫rc=2 | `references/coverage_rules.md`、`references/scripts_reference.md` |
| ③ | 户数对账旧句作废（2026-09-27裁决互不校验） | `references/measurement_methods.md` |
| ④ | 口径A唯一映射直写走②类自判+C3交叉，非唯一/空/重号双方列入 | `references/pipeline_details.md §9`、`SKILL.md:376` |
| ⑤ | coverage参数/质量失败3→2（4处）；gen回读失败3→2 | `scripts/analyze_coverage.py`、`scripts/gen_addressbook.py` |
| ⑥ | 写盘失败exit(1)→exit(4)（3处，与C2 rc=4对齐） | `scripts/extract_fx_map.py`、`scripts/count_households.py`、`scripts/parse_dxf_structured.py` |
| ⑦ | C9申报纳入count-box；inspect rc=1无发射点 | `scripts/inspect_closure.py` |
| ⑧ | check_transitions写盘改走`write_json` | `scripts/check_transitions.py` |
| ⑨ | 组装同配置展开：逐层补`result_confirmation=pending`+产物级待核对清单 | `scripts/assemble_households.py` |
| ⑩ | 删`_is_floor_text`×3薄包装，直调共享 | `scripts/analyze_coverage.py`、`scripts/count_households.py`、`scripts/parse_dxf_structured.py` |
| ⑪ | 排序哨兵统一：vshape -9999→0（修地下层误并入）、ftth手写键→`floor_num`、gen直调`floor_num_or_zero` | `scripts/analyze_coverage_vshape.py`、`scripts/ftth.py`、`scripts/gen_addressbook.py` |
| ⑫ | 箱号/米数匹配match→search（`FXRE/HURE/BOXRE/CBRE`） | `scripts/analyze_coverage_vshape.py` |
| ⑬ | `unit_no_from_key`优先走`unit_num` canonical | `scripts/analyze_coverage_vshape.py` |
| ⑭ | 错误信息补三件套（输入路径/参数回显/产物路径，5处） | `scripts/assemble_households.py`、`scripts/parse_dxf_structured.py`、`scripts/analyze_coverage_vshape.py`、`scripts/gen_addressbook.py` |
| ⑮ | 正则默认差异加注（FX四处/DESC三处有意不同，禁合并） | `scripts/plan_methods.py`、`scripts/ledger_elements.py`、`scripts/inspect_closure.py`、`scripts/ftth_common.py`、`scripts/extract_fx_map.py` |

**验证**：`py_compile`全绿；`budget rc=0`全文件OK；`check_docs D1~D9 ALL PASS`；凤鸣朝阳实跑rc=0无回归。`check_budget`零依赖、`ledger_state`原子写、`ftth_geom`紧凑缓存有意保留（已加注，不收敛）。

- **版本**：`version.json` 0.123.0 → **0.124.0**。

### 2026-09-27（一百二十五）：第三轮审查优化（零判定放宽批）

**实测动因**：第三轮专家复核0.124.0，聚焦退出码残留、批量前置、组装机读出口、排序哨兵、状态机/门禁释义、测试缺口。本批不放宽任何门禁（FAIL仍FAIL）。

| # | 改动 | 文件 |
|---|---|---|
| ① | 退出码收敛：coverage/gen回读外其余写盘失败exit(1)→exit(4；`OSError`）；geom/count_box/fxloc DXF失败→rc=2；`read_titleblock`归并冲突/`gen_9level`恒等式字符串退出→rc=2（信息保留） | `scripts/analyze_coverage.py`、`scripts/merge_json.py`、`scripts/split_units.py`、`scripts/gen_addressbook.py`、`scripts/ftth_geom.py`、`scripts/count_box_icons.py`、`scripts/extract_fx_locations.py`、`scripts/read_titleblock_households.py`、`scripts/gen_9level_addressbook.py` |
| ② | C2其他行补缺依赖发`1`（环境类，与输入类`2`区分） | `SKILL.md` |
| ③ | 批量前置校验：解释器存在性+ezdxf探测（裸调早失败，不浪费整轮） | `scripts/ftth_batch.py` |
| ④ | 组装展开机读出口：逐层`pending`+产物级清单（已验证S14） | `scripts/assemble_households.py` |
| ⑤ | 排序/匹配收敛：删`_is_floor_text`×3；vshape哨兵-9999→0；ftth/gen直调共享；箱号/米数match→search；`unit_no`优先canonical | `scripts/analyze_coverage*.py`、`scripts/count_households.py`、`scripts/parse_dxf_structured.py`、`scripts/ftth.py`、`scripts/gen_addressbook.py` |
| ⑥ | 状态机/门禁释义：词汇映射表、11阶段归属、硬门禁范围、有损放行旗I5-A声明、冲突裁决同权威日期规则 | `references/operations_discipline.md`、`references/step2_selfcheck.md` |
| ⑦ | 出表声明：11列回退警告、九级/扁平口径分野 | `scripts/gen_addressbook.py`、`references/addressbook_template.md` |
| ⑧ | 回归用例S14（组装pending）/S15（有损两档） | `tests/run_conflict_matrix.py` |
| ⑨ | D3编号缺口只WARN不拦门（T16历史保留） | `scripts/check_docs.py` |

**验证**：`py_compile`全绿；`budget rc=0`全文件OK；`check_docs D1~D9 ALL PASS`；冲突矩阵ALL PASS（含新S14/S15）；凤鸣朝阳实跑rc=0无回归。有意保留：`read_titleblock`容差量测失败rc=1（确有问题 vs 本图没有，注释已明）、`check_budget`零依赖、`ledger_state`原子写、几何紧凑缓存。

- **版本**：`version.json` 0.124.0 → **0.125.0**。

> 归位记录（2026-09-17）：五十三~五十六 曾被追加到文件末尾且标题层级误为二级，已移至顶部并统一为三级；仅移动与改层级，正文逐字未动。

### 2026-09-27（一百二十二）：户数口径改「标注即户数 · 三口径选定即出数、互不校验」（用户裁决）

**用户裁决（原话）**：「楼层的户数如果标注了可以直读，首选直读，目前遇到两种情况，一个是写明了
2户/3户，另一种是乘法。`*16` 或 `x2`。这个都是首选直读，不再看皮线或者图标个数。如果不能只读，
有图标的首先计算图标的个数，没有图标的才会取数皮线条数，而且不用再去校验。纯粹耽误时间。」

**两处澄清（AskUserQuestion 回答）**：① 乘号标注「直读」出的户数 **＝标注即户数**（`x2` → 该处
2 户；`*16` → 该处 16 户，**不与图标个数相乘**）；② 校验范围 **＝全部取消**（撤销「图标 vs 皮线
并跑互证」与「与 `X户` 直读值对账」）。

**语义变更**：户数提取由「三口径并跑互证 + 与直读对账」改为「**按序取首个可用者，选定即出数**」——
①有层户数标注（`X户` **或** 乘号式 `*N`/`xN`）→ **直读**；②无标注 → 有图标则数图标；
③无图标才数皮线。**三口径互不校验、不对账**（读数有误由人工修正，不回流到自动比对）。

**这是一次硬规则替换，不是新增**：本轮之前，「乘号标注」被 `SKILL.md` P5 禁区与
`operations_discipline.md` §5.1 明确列为「P5 强制裁决项、不得自行相乘」，且带 **122 户事故记录**
（同一项目两通道并行、该不该乘的裁决未跨通道落盘 → 两次交付差 122 户 / 其中 120 户由此而来）。
本轮用户裁决**明文废止该规则** —— 事故记录保留、并就地注明「已由 2026-09-27 裁决定案」。

| # | 改动 | 文件 |
|---|---|---|
| ① **乘号式纳入直读**（单一来源） | 新增 `HU_MULT_RE = re.compile(r"^[*×xX]\s*(\d{1,3})$")`（**全匹配**，故不误吞皮线米数 `20m*2`）与 `hu_mult_of()`；`judge_household_annotation` 接受乘号形态登记、并对乘号条**豁免长句排除**（乘号标注天然是短标签），证据里加「其中乘号式 `*N`/`xN` %d 条，乘号后数字即该处户数」 | `scripts/ftth_common.py`、`scripts/plan_methods.py` |
| ② **多形态交替正则取值修复** | 户数 pattern 由 `(\d+)户` 扩为 `(\d+)\s*户|[*×xX]\s*(\d+)` 后，命中乘号支时 **组 1 为 `None`** ⇒ 原 `int(m.group(1))` 会崩。新增 `first_nonnull_group()`（取**第一个非 None** 捕获组）替代固定取组 1 的 `first_group()`（实测后者实现为 `m.group(1) if m.re.groups >= 1 else None`，取不到「非空组」语义）。`suggested_hu` 改按图面形态四分支给 pattern（both / only_mult / only_hu / 无） | `scripts/ftth_common.py`、`scripts/parse_dxf_structured.py` |
| ③ **C5 门禁由 FAIL 改 WARN** | count_box 质量告警「待裁决乘数 → FAIL」**删除**，改为透传「乘号式户数标注」为**四类一律 WARN**（该形态已是直读，不再阻塞）。字段名 `待裁决_乘数标注` → `乘号式户数标注`（防回退，见 ⑧ 元断言） | `scripts/inspect_closure.py`、`scripts/count_box_icons.py`、`scripts/ftth.py` |
| ④ **裁决落数** | `apply-ruling` 仍**拒绝含乘号的裁决值**（裁决值须为绝对户数、脚本不做乘法），但**理由改**为「乘号标注属直读、读数在解析阶段取出、不经裁决」——避免读者据旧理由以为乘号仍待裁决 | `scripts/apply_ruling.py`、`references/pipeline_details.md` |
| ⑤ **L1-C1 例外条 + 方法池优先级重写** | 户数三口径 + 「乘号后数字即该处户数」+「互不校验、不对账」进契约区与「每层户数实体优先级」 | `SKILL.md`、`references/measurement_architecture.md` |
| ⑥ **清三处正面对立的旧口径**（核证时发现，报告未列） | ①`step2_selfcheck.md`「凡图上出现 `*N`/`xN` 乘数标注…**必须交用户裁决含义与落层口径后再改数**」；②`measurement_architecture.md` 图标法前置条「常配 `xN` 乘数标注」；③`pipeline_details.md`「**乘数是裁决项**」。三处均处**规则层**（非历史叙述），与本次裁决正面冲突，已改写 | `references/step2_selfcheck.md`、`references/measurement_architecture.md`、`references/pipeline_details.md` |
| ⑦ **C9 举例纠偏** | `L1-C8/C9` 段原文以「按 `*16` 算出的户数是 `derived` **且** `pending`（算得出，但须人裁）」作正交性示例 —— 该例已**变成错的**（`*16` 现为 `measured` + `settled`）。换为「按米数走 V 型算出的覆盖层 `derived`，若与图签不符已列待确认则同时 `pending`」，并补注乘号式的两字段取值 | `SKILL.md` |
| ⑧ **回归测试 + 防回退元断言** | `run_conflict_matrix.py` 新增 **S13 户数口径** 11 项（直读/图标/皮线三口径取用顺序、直读胜出、乘号取值、`20m*2` 不误吞、交替正则取组、`first_group` 缺陷面）+ **META 户数** 4 项（cross_check 写入口径与「非并跑·互不校验」、旧口径已移除、**旧字段名零残留扫描**） | `tests/run_conflict_matrix.py` |
| ⑨ **体量回线** | 本轮 SKILL.md 一度 +134 B 触 WARN（47,134），经消除 L1-C1 与「每层户数实体优先级」的重复枚举 + 删两处冗余限定词，压回 **46,990 B（OK）**；裁定追记后再压一次 → **46,973 B（OK，距预警线 27 B）**。**信息零删除**：被压缩的细节均在 `references/measurement_architecture.md` 与 `references/` 内保留 | `SKILL.md` |
| ⑩ **C10 去留裁定落档** | 见下「C10 裁定」段 | `references/step2_selfcheck.md`、`references/operations_discipline.md`、`SKILL.md` |

**C10 裁定（同日追加，用户答「保留吧」）—— 并把「为什么可以保留」写成可判定的通用规则**：

用户取消的是**户数三口径的交叉校验**，`inspect_closure.py` 的 **C10「图签第二来源逐栋比对」不在取消范围内**。两者性质相反，此前只有「多处来源要互相比对」一条笼统规则，**没有区分"两个信息源"与"同一事实两种算法"** —— 这正是本次差点误撤 C10 的根因。故本轮立**区分判据**（通用、可一句话判定）：

> **换一种算法，还是换一个信息源？**
> · **同一事实 × 两种算法**（同一信息源复算）⇒ **选定一法即出数、互不校验**（复算纯粹耽误时间）。
> · **同一事实 × 两个独立标注来源** ⇒ 属 **L0-P4「矛盾即停」**，**必须比对**，不一致列双方数值交人裁定。

| 落点 | 内容 |
|---|---|
| `operations_discipline.md` §5.7 | 新增该判据（含两行对照表 + 「C10 属后者 ⇒ 保留」的实测口径）；§5.7 表头「可用来源数」措辞同步收紧 |
| `step2_selfcheck.md` C10 段 | 就地注明**已裁定保留**及理由（取消 C10 = 图签与系统图打架时无人拦截、矛盾静默进成品） |
| `SKILL.md` L256 | 「有几处**可用**来源」→「有几处**独立**来源」（**同字节替换**，零体量代价）+ 括注「**换算法复算不算第二来源**」；L1-C1 尾注删去与 `references/` 重复的理由句腾出体量 |

**核证时发现并修正的表述不精确（P2）**：原 §5.7 表头写「**可用**来源数」—— 「可用」是**可行性**语义，与判据所需的**独立性**语义不同，易被读成「能算的都算一处来源」，正是误撤 C10 的入口。已改「**独立**来源数」。

**验证**：`check_docs` D1~D9 ALL PASS · `check_budget` rc=0（SKILL.md 46,973 B OK）·
`run_smoke` ALL PASS · `run_conflict_matrix` **ALL PASS（41 项，含新增 S13 11 项 + META 4 项）** ·
全仓 `待裁决_乘数标注` **零残留** · 37 个 `.py` 语法编译 0 失败。

- **版本**：`version.json` 0.121.1 → **0.122.0**（minor 位对应修订序号「一百二十二」）。

### 2026-09-27（一百二十一·补）：文档一致性审核第一批 —— 断链 8 条 + 编号 + 文本损坏 + 断链门禁

**实测动因**：技能一致性审核（`FTTH技能一致性问题审核报告.md`，27 条）落地第一批 ——
**零风险机械修复**那批；P0 六条（户数口径、直读地位、口径 A′ 等）涉及「以哪一侧为准」的
**实质裁决**，另批处理，不在本条目内。

| # | 改动 | 文件 |
|---|---|---|
| ① 断链 ×8 | `references/` 内文件互引时误写 `references/xxx.md` 前缀（Markdown 按**所在目录**解析 ⇒ 指向 `references/references/…`）。去前缀后 **8 → 0 断链**（73 条链接全量实测） | `measurement_architecture.md`(4)、`step2_selfcheck.md`(3)、`scripts_reference.md`(1) |
| ② 约定纠偏（根因） | 「本文件内引用按**技能根目录视角**书写」正是 ① 的**根因声明**——照它写必断链。改为「Markdown 链接按**所在文件目录**解析：本文件在技能根故外链写 `references/xxx.md`；`references/` 内互引写**裸文件名**」，并说明行内代码提及仍按根视角写以便全仓检索 | `references/pipeline_details.md` |
| ③ 陈旧编号 | 冒烟范围 `T0~T18` 加注「**无 T16，历史编号缺口**」（实测 `run_smoke.py` 编号为 T0~T15、T1b/T1c/T4b、T17、T18，确无 T16；D3 只校最大编号故长期不报） | `README.md` |
| ④ 消歧 | 图签段「C1~C9 也没有对应检查」→「**当时的** C1~C9 …」（该句讲 C10 诞生前的状态，加限定防误读为「现只有 9 项」） | `references/pipeline_details.md` |
| ⑤ 文本损坏 | §十一 原理句「故每次修复必须**928087**，不许只加不减」—— 数字串系编辑事故，**无历史版本可考**（技能版本库止于 09-19，该节 09-26 新增）。按本节表格结构重建为「必须**遵循下表修法优先序**」（不造词、不引入新术语），**如您手上有原文请替换** | `references/operations_discipline.md` |
| ⑥ 断链门禁（防复发） | `check_docs.py` 新增 **D9 全仓相对链接存在**：D7 只核 SKILL.md 外链，`references/` 内那 8 条断链长期**无门禁可报**。D9 把链接体检扩到全仓 md（排除 CHANGELOG），docstring 同步列位 | `scripts/check_docs.py` |

**未采纳的 2 条（核证后否掉报告的误判，避免"照报告改反而改错"）**：
- 报告 P2-2「`C0~C10`（不存在 C0）」—— **误报**：`inspect_closure.py:255-277` 实测存在
  「C0 数据集非空门禁」，故 `dxf_parsing_benchmark.md` 的 `C0~C10` 写法**正确**，未改。
- 报告 P2-1 的改法（`C1~C9` → `C1~C10`）—— 会让句子**变错**（C10 正是该信号的对应检查），
  故只加「当时的」消歧，不照改。

**验证**：`check_docs` D1~**D9** ALL PASS · `budget` rc=0 · `run_smoke` ALL PASS · 冲突矩阵 ALL PASS ·
断链 8→**0** · **D9 门禁冒烟**（临时副本人造断链 → FAIL / rc=2，证明其非恒 PASS）。

- **版本**：`version.json` 0.121.0 → **0.121.1**（patch 位对应同一修订序号内的「·补」条目）。

### 2026-09-27（一百二十一）：覆盖判定改「有米标优先 V 型 · 不再并跑互验」（用户裁决）

**用户裁决（原话）**：「如果有米标，就优先用 v 型法，不再相互验证，错误了让人去修正。」

**语义变更**：覆盖判定由「两法 `requires` 同时成立 → **必须并跑比对**，不一致列待确认」
改为「**按候选顺序取首个可用者，非并跑**」—— 有皮线米数标注（`fiber_length_vshape`）即
**优先 V型计算**，不再与竖线法互证；**不因单来源降级**；结论与实际不符由**人工修正**
（列待确认项交人裁定），**不回流到自动比对**。

**只改语义、不改机制**（关键事实，避免误读为"新增了优先级逻辑"）：候选顺序本就是
`_pick_method` 的取用顺序，而 `build_steps` 里 **V型计算已排在竖线法之前** ⇒
「有米标优先 V 型」在**行为上早已成立**。本轮消除的是**声明层**（`cross_check` / 文档 /
自检项 / 测试断言）与新裁决的矛盾 —— 即上一轮（一百二十）遗留项①「并跑执行方未接入」
的直接后果：既然裁决不再要求并跑，那条"未接入"的告警本身即失去意义。

| # | 改动 | 文件 |
|---|---|---|
| ① | 覆盖判定 `cross_check` 整段重写：删「两者 requires 同时成立时必须并跑比对」与「须**人工各跑一次**（`coverage` 与 `coverage-vshape`）逐单元比对，不得只跑一条就出表」，改为「**按候选顺序取首个可用者，非并跑**：有米标 → **优先 V型计算**；米数缺而竖干可追踪 → 竖线法；不因单来源降级；与实际不符交人工修正」；V型候选上加注释点明「列表顺序即取用顺序」 | `scripts/plan_methods.py` |
| ② | 自检清单项「覆盖范围第二来源核对（两法前置都成立时必须双跑）」→「覆盖范围方法选择（有米标取 V型法；单源采信，出错交人工修正）」 | `scripts/plan_methods.py` |
| ③ | 两份图纸档案的 `cross_check` + 自检项同步改写；`shared_mixed/manifest.json` 覆盖候选**顺序纠正** —— 原「竖线法 primary / V型 alternate」⇒「**V型 primary / 竖线 alternate**」（与其新规则一致；此前与 `building_cluster` 相反，属同事实两份表述） | `methods/building_cluster/manifest.json`、`methods/shared_mixed/manifest.json` |
| ④ | **SKILL.md 净减 −34 B**（46985 → **46951**，距预警线 49 B）：L1-C1「两个候选 `requires` 同时成立时**必须并跑交叉比对**」→「**多候选同时可用时按顺序取首个、不并跑**（覆盖：有米标 → V型法）」；「**唯一例外**是户数口径」→「**同类例外**：户数口径」；⑧ 行「否则由皮线米数 V 型 或 竖干断口推出」→「否则**有米标走 V 型**，无则竖干断口」；「必须推导时跑方法池（**并跑互证**见 L1-C1）」→「（**取法规则**见 L1-C1）」；方法选择规则「多路信号同时成立时**并跑互证**，不一致交用户」→「**按候选顺序取首个**」；三条硬门禁之「矛盾即停」删「覆盖两法并跑」 | `SKILL.md` |
| ⑤ | 权威细则与各层表述同步：`coverage_rules.md` §二 方法表「两信号均在 ⇒ **必须并跑两法并比对**」→「**取 V型计算**」；判定流程总结图重排（有米标即优先）；原「⚠ 并跑比对执行方尚未接入」整段 → 改为「**取用实现 = 设计意图**（单命令即非并跑，非缺陷）」。`measurement_architecture.md`（方法选择规则段 + 覆盖判定行）、`step2_selfcheck.md`（完整性段 + 26 条段）、`measurement_methods.md`（阶段表 / profile schema 示例 / 字段说明）同步 | `references/coverage_rules.md`、`references/measurement_architecture.md`、`references/step2_selfcheck.md`、`references/measurement_methods.md` |
| ⑥ | 冲突矩阵回归**断言改判**（原断言与裁决直接冲突，不改即 FAIL）：S1「同可用备选非空 ⇒ 须人工比对」→「**米标成立 ⇒ 取 V型计算**」+「备选仅作信息登记，不要求再跑第二法」；S4 同款改判；S5「两法均可比」→「取 V型」；S7 标签改「无其它可用候选（单源采信）」；**元断言**由「并跑未接入须如实登记」→「**非并跑已写进 `cross_check`**；入口只跑一条子命令 = **设计意图，非缺陷**」 | `tests/run_conflict_matrix.py` |

**验证**：
- `tests/run_conflict_matrix.py` **ALL PASS**（失败 0 项）—— 含改判后的 S1/S4/S5 与「META 非并跑」
- `check_docs.py` **D1~D8 ALL PASS**（脚本数仍 35，无新增 `scripts/*.py`）
- `ftth.py budget` **rc=0**：SKILL.md **46951 B**（净 −34 B，距预警线 **49 B**）
- `tests/run_smoke.py` **ALL PASS**
- 语法/导入自检：`plan_methods` / `ftth` 均正常导入（冲突矩阵即打靶真实函数，非 mock）

**备份**：改前全量备份 `<工作区>/.audit/backup_ftth_v120_vshape_20260927_0917/`
（**63 文件 / 2,174,439 B**，与基线逐文件对拍一致）；回滚 = 整体拷回。

**残留（提请复核）**：`role`（`primary`/`alternate`）仍是**纯显示字段** —— `_pick_method`
不读它（按数组顺序取用）。本轮只理顺**顺序**，未给 `role` 加语义；是否统一表述，待用户裁定。

- **版本**：`version.json` 0.120.0 → **0.121.0**（minor 位对应修订序号一百二十一）。

### 2026-09-27（一百二十）：V3.1 契约收口 —— 覆盖主线假路整改 + V 型唯一算法 + 判定依据枚举 + 权威矩阵

**实测动因**：桌面《FTTH技能专家审查报告_V3》（外部专家，8.7/10）经**逐条核证**后采纳方向
（「减少歧义，而不是增加规则」），但**纠正其 P0-1 前提**并**查出报告漏掉的一处更严重缺陷**：
报告称"覆盖直读**实现层已经支持**" —— 核证为**假**（`parse_dxf_structured.py` 全文零实现，
`RE_COVER_RANGE` 仅 `plan_methods.py` 用于**信号检测**）；而 `ftth.py` 的覆盖脚本映射表
不含该脚本 ⇒ 一旦图上真有「覆盖 -1F~9F」直写，**画像选中 primary → 覆盖阶段静默跳过 →
备选不兜底 → inspect C6 硬 FAIL**（最优证据反把结果拦死）。真机跑 5 张图（云峰/凤鸣/
柳辛庄×2/繁华里）该信号**全部 absent** ⇒ 缺陷为**潜伏**、当前未流血。

| # | 改动 | 文件 |
|---|---|---|
| ① | **P0-1 拆假路**：覆盖候选 primary「读取标注（图上直写覆盖起止层）」标 `implemented=False` + `unimplemented_reason`；`_pick_method` 跳过未接入候选并**登记** `未接入候选`（不静默）；**唯一可用即未接入**时申报新状态 `unimplemented`（**既不冒充 absent 也不冒充 unknown**）→ 计入未作答 → 入口 rc=2 报人 | `scripts/plan_methods.py` |
| ② | **P0-1 入口能力表门禁**：新增 `_PIPE_CAPABILITY`（键用 **handoff 子任务名**、覆盖一栏由 `_COV_SCRIPT_TO_CMD` **派生**，唯一来源）+ `_pipe_capability_problems`；`pipeline` 在 `plan` 之后立即对拍，不一致即 rc=2（此前「映射不到」被当「本图不适用」记 rc=3 静默跳过）；`_pipe_coverage_choice` 由二元组改**三态** `(cmd, note, blocked)` | `scripts/ftth.py` |
| ③ | **P0-2 V 型统一**：`coverage_rules.md`「计算步骤」原为**双 V 曲线拟合 + 交点法**（与同文件上半部分及 `analyze_coverage_vshape.py` 的「相邻谷底间最大米数行」**两套理论并存**）→ 改为唯一正式算法，双 V 交点法列为**已废弃方案**并写明三条理由；同步 `measurement_methods.md` 表述 | `references/coverage_rules.md`、`references/measurement_methods.md` |
| ④ | **P0-3 判定依据机器可枚举**：新增 `COVERAGE_METHODS`（读取标注/竖线法/V型计算/人工裁决/待确认）+ `coverage_method_of`（取首段，唯一来源）；**修正真实漂移** —— `analyze_coverage_vshape.py` 产出「V**形**计算」与契约 70 处「V**型**计算」不一致（同一脚本内两种写法并存）；`check_contracts.py` 加 **R4** 词表闸门（空值同样 FAIL）；`inspect_closure.py` **C6** 加枚举校验（新增计数 `判定依据不可枚举` 并计入 FAIL 条件，cmap 记录扩 1 元） | `scripts/ftth_common.py`、`scripts/analyze_coverage_vshape.py`、`scripts/check_contracts.py`、`scripts/inspect_closure.py` |
| ⑤ | **附带**：`check_contracts.py` docstring 自述「无产物 → rc=3」而实现返 **rc=0**（**空集合判 PASS**）→ 补齐 rc=3；冒烟 T17 对 rc=3 只登记「未核」不判 FAIL（与 T17 自身「缺 T14 即 SKIP」对齐） | `scripts/check_contracts.py`、`tests/run_smoke.py` |
| ⑥ | **P1-1 单箱单元加前置三条件**（单元归属已确认 / 无第二箱缺失疑点 / 住户楼层集合已确定），任一不成立即不得套用；说明"箱漏画 vs 本来只有一个箱"混同即静默丢数；同步 step2 | `references/coverage_rules.md`、`references/step2_selfcheck.md` |
| ⑦ | **P1-2 rc=3 明文**：「`rc=3` 只允许结束解析，**不豁免出表前置**」，机械链写清（rc=3 → 覆盖零产出 → C6 FAIL；`待确认` → pending → C9 FAIL）→ 须 L0-I4/L1-C5 人工裁决落盘方可出表；同步流水线细则 | `references/coverage_rules.md`、`references/pipeline_details.md` |
| ⑧ | **P1-3「推荐」边界**：允许推荐**证据解释**、禁止写成工程裁决（新增「允许/禁止」对照表）；推荐不产生 `settled`，裁决一律 `E-HUMAN-RULING` | `references/operations_discipline.md` |
| ⑨ | **P1-4 规则唯一权威矩阵**（新 §十四）：17 行「规则 → 唯一权威」+ 两条维护纪律（矩阵自身须同步 / 新增规则前先查表）；以本轮 P0-2 为现成反例 | `references/operations_discipline.md` |
| ⑩ | **§12.4 冲突矩阵回归**：新 `tests/run_conflict_matrix.py`（12 场景 + 2 元断言，**纯函数级、不需 DXF 语料**）；接入冒烟 **T18**；README T0~T17→**T0~T18** | `tests/run_conflict_matrix.py`（新）、`tests/run_smoke.py`、`README.md` |
| ⑪ | **覆盖并跑比对「未接入」如实登记**：核证发现「两法必须并跑比对」**只存在于 cross_check 文字、无任何执行方**（`_pipe_coverage_choice` 只返回一条子命令）—— 改为明写「须人工各跑一次并逐单元比对」，不得只跑一条就出表 | `scripts/plan_methods.py`、`references/coverage_rules.md` |
| ⑫ | **SKILL.md（净增 +75 B，46910→46985，仍未触 47000 预警线）**：覆盖判定依据枚举补「读取标注 / 人工裁决」+「**首段须为枚举词、机器可判**」；图纸信息模型⑧「**首选直读**」→「**直读优先·本技能尚未接入该产出口**」（同源的假承诺）；`operations_discipline` 行加「权威矩阵」指针；删重复指针「（当前基线见 SKILL_CHANGELOG.md）」腾字节 | `SKILL.md` |

**验证**：
- `check_docs.py` **D1~D8 ALL PASS**（脚本数仍 35，无新增 `scripts/*.py`）
- `ftth.py budget` **rc=0**：SKILL.md **46985 B**（距预警线 15 B）；references 最大 `scripts_reference.md` 45855 B
- `tests/run_smoke.py`（无 `--with-dxf`，T5/T14/T17 按预置 SKIP）**ALL PASS / 0 FAIL**，含 **T18 全过**
- `tests/run_conflict_matrix.py` **28/28 PASS**
- 本轮自测：P0-1 **16/16**（含故障注入：未接入降级/登记、unimplemented、能力表 rc、四态映射）；
  P0-3 **15/15**（含 `V形计算` 被拦、空值被拦、无产物 rc=3）
- **真机回归**：繁华里（真实 DXF）旧 `plan`（备份）vs 新 `plan` **逐字段一致** ——
  三个子任务 `选定方法/脚本/申报` 全同、`completeness.ok` 与 `gate.status` 一致、
  未作答/不可解析/缺失项计数一致、新增键为空（未接入登记正确缺省）
- **真机信号核证**：5 张真实图 `RE_COVER_RANGE` 命中 **0**（云峰「覆盖N号楼」形态被正则正确排除）

**备份**：改前全量备份 `<工作区>/.audit/backup_ftth-address-extractor_20260927_0642/`（**62 文件 / 2,126,696 B**，
两侧逐文件对拍一致）；回滚 = 整体拷回。

**遗留（未做，须用户决定）**：覆盖直读的**产出口**仍未实现（本轮按「拆假路 + 门禁 + 兜底」处置）；
覆盖并跑比对的**执行方**仍未接入（已如实登记为人工步骤）。二者均待有带该形态的真实图纸或合成语料时再落地。

- **版本**：`version.json` 0.119.0 → **0.120.0**（minor 位对应修订序号一百二十）。

### 2026-09-26（一百一十九）：专家会审落地批——台账锁 + trace 导出 + 产物契约门（唯二语义变更）

**实测动因**：外部专家会审（V3 方向）经审核采纳有条件落地：确定性下沉/证据结构化
部分可直接执行（台账锁、trace 导出、契约词汇封闭、N-run 由 T14 承担）；平行对象图、
一步到位 `ftth/` 包、第二套归属算法三项**明确不做**（复发多份实现，前两轮血泪；
审核结论见 KB）。本批唯二语义变更均带守卫与回滚。

| # | 改动 | 文件 |
|---|---|---|
| ① | 台账锁定保护：已裁决项无 `--by` 改值拒收 rc=3（L0-I4⑤/P3）；带 `--by` 视为新裁决落历史放行；未锁定/同值重记不受影响 | `scripts/ledger_state.py` |
| ② | 新 `trace` 子命令：逐项 candidates/evidence/conflicts/decision/origin/confirmation 机械导出（零推理；confirmation 按 L1-C8 口径；裁决条目未存 key 不强行关联） | `scripts/ledger_state.py` |
| ③ | 新 `check_contracts.py`：L1-C8 词汇封闭（未知 origin/confirmation 即 rc=2；pending 只盘点，语义判定权留给 C9）+ 冒烟 T17（跑本轮 T14 产物，缺 T14 即 SKIP） | `scripts/check_contracts.py`（新）、`tests/run_smoke.py` |
| ④ | T15 扩展（无新编号）：锁定守卫 rc=0/3/0 + trace 导出断言；T1b 委托对新增 `fl_num` | `tests/run_smoke.py` |
| ⑤ | D8 34→35；README T0~T17 + T17 行；清单表补行 | `scripts/check_docs.py`、`README.md`、`references/scripts_reference.md`、`SKILL.md`（数字 2 字节） |

**验证**：`--with-dxf --corpus <版本库语料>` **59 PASS / 0 FAIL / 0 SKIP**
（T17 + 扩展 T15 + T1b/T4b/T14 全绿）；`budget` rc=0（SKILL 46910 B 未动）；
`check_docs` D1~D8 全绿；`py_compile` 全绿。
**备份**：改前文件级备份 `E:\ftth-kb\backup_ftth_true_20260926_*`（96 文件）；回滚 = 整体拷回。

- **版本**：`version.json` 0.118.0 → **0.119.0**（minor 位对应修订序号一百一十九）。

### 2026-09-26（一百一十八）：T5 点亮 + 回退第三批 + pick_scale 根治提案（零行为变更批）

**实测动因**：T5 自语料外移（一百零九）后从未点亮过；分支预算要求回退逐批补；
pick_scale 根治（根因报告 P0）需先出方案待裁决，不直接动算法。

| # | 改动 | 文件 |
|---|---|---|
| ① | T5 点亮：版本库语料 `a小区.dxf` 经 `--corpus` 跑通（probe rc=0）；`tests/README.md` 记录点亮命令与解析顺序 | `tests/README.md`（文档 only；机内路径不进代码，换机重定） |
| ② | 回退第三批（注释 only + 1 处可见性）：vshape 5×字高兜底、`_load_json` 缺席/损坏区分已在上一批，补 geom 缓存损坏 debug（hasattr 防护）+ 永久设计注记；T1b 委托对新增 `fl_num`（双合法形态：直调/-9999 哨兵 vs _or_zero/0 回退） | `scripts/analyze_coverage_vshape.py`、`scripts/ftth_geom.py`、`tests/run_smoke.py` |
| ③ | pick_scale 根治提案：现状四层行号、补丁治标分析、替换式设计（刻度标栋 + 同栋优先 + 折叠两层 + 回归网）、风险回滚、3 项 A 级待裁决。**代码一字未动** | `E:\ftth-kb\reports\pick_scale根治提案_待裁决.md`（KB 侧） |

**验证**：`--with-dxf --corpus <版本库语料>` **58 PASS / 0 FAIL / 0 SKIP**
（T5 双项 + T14 三图 fresh 全链 + T1b/T1c/T4b/T15 全绿，首次零跳过全绿）；
`budget` rc=0（SKILL 46910 B 未动）；`check_docs` D1~D8 全绿。
**备份**：改前文件级备份 `E:\ftth-kb\backup_ftth_true_20260926_*`（96 文件）；回滚 = 整体拷回。

- **版本**：`version.json` 0.117.0 → **0.118.0**（minor 位对应修订序号一百一十八）。

### 2026-09-26（一百一十七）：P1-3 失败信号批——JSON 出口统一 + 控制台收口 + 有损守门 rc 对齐

**实测动因**：opencode 两轮审计挂账至今的批次 2 本体（JSON 出口 22 处直调、
裸 reconfigure 17 处、exit(1) 13 文件）。此前无回归门不敢动；现金 T14 + 冒烟
齐备，逐处 triage 后落地。唯一语义变更是 count_households 有损守门 1→2，
其余全是"同语义、更硬的执行方"。

| # | 改动 | 文件 |
|---|---|---|
| ① | 16 处 `json.dump` 改走 `write_json`（内建 ensure_parent + 非有限浮点清洗为 null，标准 JSON）。`write_json` 本体不动（免改共享函数）：分隔符/排序参数均无新增需求 | 14 个脚本（见验证）；豁免 5 处各有去处：launcher/budget/transitions（刻意零依赖）、geom（禁 import common 否则循环）、ledger（sort_keys canonical 出口已是标杆）、ftth.py（pipeline_timing 需 newline="\n" 防 CRLF） |
| ② | 15 处裸 `reconfigure` 改走 `ensure_console_utf8`（getattr 防护被替换流 + stderr 双切 + errors=replace）。推翻八十九"存量保持不动"决定：09-25 审计证实管道/测试流下裸调用抛 AttributeError，真实控制台行为逐位一致已由 T14 验证。count_hdd shim 删空行（正常流程零输出）；ledger 自带等效守卫不动 | 15 个脚本；ftth_common docstring 同步记录反转理由 |
| ③ | count_households 有损守门 `exit(1)→exit(2)` + 报错文案同步。triage：17 处中 16 处为"命令自身失败/环境失败"（rc=1 合契约）或语义模糊（DXF 读失败、缺依赖——不动）；仅此一处是明文"必须修项"（L1-C2 rc=2：停）。`ftth.py count` 透传 rc 无分支依赖，pipeline 未调用该脚本 | `scripts/count_households.py` |
| ④ | 静默补可见性（行为不变）：`_is_box_symbol_entity` 异常计数 + 汇总 WARN；`_attrib_ok` 异常加 debug；`check_transitions._load_json` 缺席/损坏严格区分（损坏 stderr 留痕，返 None 契约不变） | `scripts/analyze_coverage.py`、`scripts/check_transitions.py` |
| ⑤ | T1c 出口锁（JSON 直调 allowlist 6 文件 + reconfigure allowlist 2 文件，豁免理由写进注释）；回退第二批补 5 处时顺手修两处笔误 | `tests/run_smoke.py` |

**验证**：
- **冒烟**：`--with-dxf` 56 PASS / 0 FAIL / 1 SKIP（T5 语料外置）；T1c/T4b 全绿。
- **三图 T14**：重跑 fresh 全链，凤鸣/柳辛庄/云峰与 golden 逐项一致（write_json 清洗未改变任何产物字节——三图均无非有限浮点）。
- **专项**：merge 双输入合成料 rc=0（2 栋落盘）；split_units 合成料 rc=0（4 户）；probe_titleblock 凤鸣 rc=2 契约退出；extract_fx_locations 凤鸣 rc=2 契约退出；ftth_batch/split_bands/count_hdd --help rc=0。
- **排障实录**：首轮 T14 FAIL 抓到 count_box 写盘块被错嵌进 `if hit and total == 0` 门禁（备份对拍定位，4 空格之差，py_compile 通过但行为错——"语法绿≠行为对"的实例）；另修复 apply/assemble/inspect/vshape 四处同类缩进。教训：凡跨缩进改写必须备份 diff 全量复核（本批已执行，19 文件 hunks 逐段审查）。
- **`budget` rc=0**（SKILL 46910 B 未动）；`check_docs` D1~D8 全绿；`py_compile` 全仓绿。
- **备份**：改前文件级备份 `E:\ftth-kb\backup_ftth_true_20260926_182332\`（96 文件）；回滚 = 整体拷回。

- **版本**：`version.json` 0.116.0 → **0.117.0**（minor 位对应修订序号一百一十七）。

### 2026-09-26（一百一十六）：P1 第二刀——几何/格组域拆分 + 回退标注第二批（零行为变更批）

**实测动因**：P1-2 命名域验证了"搬函数 + re-export + T14 锁行为"模式可行，
按域继续拆。另分支预算 §十一要求回退逐批补退役条件，本批补交互面最大的四处。

| # | 改动 | 文件 |
|---|---|---|
| ① | 新 `ftth_geom.py`（336 行）：DXF 单次全量解析 + geom 缓存 + 几何查询（`load_dxf/load_geom/extract_geom/collect_texts/median/point_rect_dist`），自包含（stdlib + lazy ezdxf），禁 import 其它域 | `scripts/ftth_geom.py`（新） |
| ② | 新 `ftth_cells.py`（424 行）：图签格组判据族唯一家（5 函数）；只许 import 命名/几何域。`estimate_titleblock_tolerances` 留守（它建在谱/TOL 测量原语上，属测量校准） | `scripts/ftth_cells.py`（新） |
| ③ | `ftth_common.py` 2745→2044 行；三行 re-export shim；`EXPAND_BLDG_RANGES` 开关与 TOL/裁决/ruling 域留守 | `scripts/ftth_common.py` |
| ④ | 回退第二批（注释 only）：指纹 fail-open、老画像 must_probe 回退、单锚点 ±1000、两处未定标 AUTO_FALLBACK（注明同源待合并） | `scripts/ftth.py`、`scripts/parse_dxf_structured.py`、`scripts/analyze_coverage.py`、`scripts/count_box_icons.py` |
| ⑤ | D8 32→34；清单表补两行 | `scripts/check_docs.py`、`SKILL.md`（0 字节级改动）、`README.md`、`references/scripts_reference.md` |

**验证**：
- **冒烟**：`--with-dxf` 54 PASS / 0 FAIL / 1 SKIP；T14 用拆分后代码重跑三图 fresh 全链，与 golden 逐项一致。
- **迁移审计**（`audit_split.py`）：备份 common 100 定义在且仅在一处逐字存在；其余 28 脚本逐字节一致；无计划外新增定义。
- **排障实录**：首轮漏迁 `load_dxf`（跨度笔误，T1b/冒烟未覆盖——教训：跨度表须与审计脚本同源生成）；次轮 `RE_DRAWING_WORD` 遗留（T14 probe NameError 当场抓住）。两轮均为"无 T14 必漏生产"类。
- **`budget` rc=0**（SKILL 46910 B 未动）；`check_docs` D1~D8 全绿；改动脚本 `py_compile` 全绿。
- **备份**：改前文件级备份 `E:\ftth-kb\backup_ftth_true_20260926_180403\`（92 文件）；回滚 = 整体拷回。

- **版本**：`version.json` 0.115.0 → **0.116.0**（minor 位对应修订序号一百一十六）。

### 2026-09-26（一百一十五）：P1 首刀——分支预算 + 台账确定性 + 命名域拆分（零行为变更批）

**实测动因**：「屎山评估」五机制中"加法修复膨胀状态空间"与"上帝模块"是两根主梁；
ledger `_now()` 是 T14 可靠性的前提缺口。本批三刀全是结构/机制，不改任何行为。

| # | 改动 | 文件 |
|---|---|---|
| ① P1-1 | `operations_discipline.md` 新增 §十一分支预算纪律（收口>替换>加法；加法必须写`退役条件`；41 处回退逐批补）；三处叠加修复标注退役条件（`_fix_shared_scale`/`side_spectrum`/同配置展开段） | `references/operations_discipline.md`、`scripts/count_box_icons.py`、`scripts/assemble_households.py`（注释 only） |
| ② P1-4 | `ledger_state._now()` 支持 `FTTH_FIXED_TIME` 冻结时钟（生产默认系统时间不变）+ 冒烟 T15（三本台账同序列两次写入逐位一致）；README T0~T15 同步 | `scripts/ledger_state.py`、`tests/run_smoke.py`、`README.md` |
| ③ P1-2 | 命名归一域抽取为 `scripts/ftth_naming.py`（536 行：清洗/楼层/楼栋号/单元/楼名/楼层数字 + `__all__`，仅依赖 re）；`ftth_common.py` 3230→2745 行，经 `from ftth_naming import *` re-export，30 个旧脚本零改动；`EXPAND_BLDG_RANGES` 开关刻意留守（跨模块 global 写会漂移，迁移中实证）；`RE_DRAWING_WORD/RE_BLDG_NO` 随 `is_bldg_title_text` 同行 | `scripts/ftth_naming.py`（新）、`scripts/ftth_common.py` |
| ④ D8 | 脚本数锁：SKILL/README 明数 30→32（旧数在本批前已漂移——`check_docs.py` 本体即第 31 个，D8 首轮 FAIL 自证），`scripts_reference.md` 清单补 `ftth_naming.py` 行 | `scripts/check_docs.py`（D8）、`SKILL.md`（0 字节变动）、`README.md`、`references/scripts_reference.md` |

**验证**：
- **冒烟**：`--with-dxf` 54 PASS / 0 FAIL / 1 SKIP（T5 语料外置）；T1b 归属表更新（命名 9 类住 naming）、T15、T4b（D1~D8）全绿。
- **三图 T14**：拆分后代码重跑三图 fresh 全链，凤鸣/柳辛庄/云峰与 golden 基线逐项一致（零行为变更实锤）。
- **拆分排障实录**：首轮 T14 FAIL 抓到 `is_bldg_title_text` 引用的 `RE_DRAWING_WORD` 遗留 common（NameError，probe rc=1）——正是"搬运漏依赖"类回归，修法为定义随函数同行；另实证跨模块 flag 读写路径完好（vshape 读到 True）。凡此皆是无 T14 时会漏到生产的问题。
- **`budget` rc=0**；SKILL.md 46910 B 未动（剩 90 B）；改动脚本 `py_compile` 全绿。
- **备份**：改前文件级备份 `E:\ftth-kb\backup_ftth_true_20260926_*`（90 文件）；回滚 = 整体拷回。

- **版本**：`version.json` 0.114.0 → **0.115.0**（minor 位对应修订序号一百一十五）。

### 2026-09-26（一百一十四）：防反复 P0 止血批——体量腾挪 + 单一实现锁 + 文档执行方 + 三图 golden

**实测动因**：「屎山风险评估_错乱与反复」确诊四层叠加（上帝模块 + 文档代码失耦 +
无真机回归 + 门控两态）；同期实测体量告急（SKILL 距预警线 75 B、
scripts_reference 仅剩 18 B）。本批只建机制、不改行为：每项都是"把人眼纪律
变成 rc≠0 的硬信号"，后续修复的闸门。

| # | 改动 | 文件 |
|---|---|---|
| ① P0-4 | `§批量编排`（42 行）从 `scripts_reference.md` 外移至 `pipeline_details.md §19`（原文逐字搬入，原地留指针）；三处跨文件指针同步（pipeline_details:27、SKILL:359 精简、scripts_reference:457）。SKILL:359 批量条款整句外移（SKILL 只留引用，符合其体量纪律） | `references/scripts_reference.md`（46982→44942 B）、`references/pipeline_details.md`（+§19）、`SKILL.md`（46925→46910 B） |
| ② P0-1 | 冒烟 T1b 委托锁：`norm_unit/norm_floor/floor_num_local` 必须调共享入口；9 类权威实现恰 1 份（gen_9level.norm_units 另一语义零依赖，豁免并注明）；T3 加 floor_num 四项（B1/十七层/WF/非楼层） | `tests/run_smoke.py` |
| ③ P0-2 | 新增 `check_docs.py`（D1~D7：子命令/阶段/冒烟范围/C项/批量可达/geom链/外链存在）+ 冒烟 T4b；README:56 批量指针、:62 T0~T14、T-list 同步 | `scripts/check_docs.py`（新）、`tests/run_smoke.py`、`README.md` |
| ④ P0-3 | `tests/golden_expected.json` 三图指纹基线 + 冒烟 T14（fresh 全链对拍；md5 只锁跨目录稳定文件，profile/timing/inspect 走归一化语义比对；lxz14 config 探查浮点抖动不锁） | `tests/golden_expected.json`（新）、`tests/run_smoke.py` |
| ⑤ P0-5 | 批次门控加紧急通道第三态（A 级发起+补审清单/期限+台账追踪）；回滚边界更新（git 已外置 v108） | `E:\ftth-kb\tasks\批次门控纪律.md`（KB 侧） |

**验证（先基线、改后全量重跑）**：
- **体量**：`budget` rc=0；SKILL 46910 B（剩 90 B，较批前 +15 B）；scripts_reference 44942 B（剩 2058 B，较批前 +2040 B）；pipeline_details 约 25 KB（上限内）。
- **冒烟**：`tests/run_smoke.py --with-dxf` 53 PASS / 0 FAIL / 1 SKIP（T5 语料外置 SKIP）；含 T1b/T4b/T14 全绿。
- **三图 T14**：凤鸣 rc=0（FAIL0 WARN3、四产物 md5 一致）/ 柳辛庄 parse rc=2（8 阶段停）/ 云峰 inspect rc=2（F6 W10、count 13 列 331 户、偏移 1 组 4）——与批前基线逐项一致。
- **T14 自证判别力**：首轮实跑曾 FAIL（产物嵌入的 DXF 路径分隔符 `\/` 混用致 md5 假红），修 harness 路径归一后转绿——门禁会响。
- **备份**：改前文件级备份 `E:\ftth-kb\backup_ftth_true_20260926_*`（86 文件，含 __pycache__）；回滚 = 整体拷回。

- **版本**：`version.json` 0.113.0 → **0.114.0**（minor 位对应修订序号一百一十四）。

### 2026-09-26（一百一十三）：楼层归一唯一入口收口 + 文档引用规范化（零回归批）

**实测动因**：`verify_coverage_truth.py:53 norm_floor` 仍是独立正则实现（地下/中文/室后缀自写），与 `ftth_common.floor_num/parse_floor_label`（B1/B2/WF/-1F/数字F）同名异义——“同一逻辑多份实现必然漂移”是本技能反复踩过的坑；另 `check_budget.py:16` 留有 2026-09-25 已证伪的“0 命中、没有执行方”断言（执行方就在本文件 47-49 行与 version.json budget 段）；`SKILL.md:264` 矛盾分级与 `:332` 几何缓存引用仍是裸写法（批次 1 #11#12 遗留）。

| # | 改动 | 文件 |
|---|---|---|
| ① | `parse_floor_label` 上收中文层/地下/负层：`([中文\d]+)层`→cn2num、`(?:地下\|负)([中文\d]+)层?`→负值、`[Bb](\d+)(?:层\|F)?` 兼容后缀；既有 B1/WF/数字F 行为逐位不变 | `scripts/ftth_common.py` |
| ② | 删 `verify_coverage_truth.norm_floor` 本地正则分支，改调 `floor_num(t, use_fullmatch=True)`，仅保留定稿表 '室' 尾缀剥离；`cn2num` 导入保留（注释已说明共享绑定） | `scripts/verify_coverage_truth.py` |
| ③ | `check_budget.py:16` 假断言改为历史注：当时 grep 未计入 version.json 与本文件，今后否定断言须双侧全量 grep | `scripts/check_budget.py`（注释 only） |
| ④ | `SKILL.md:264` 补文件限定 `[operations_discipline.md §五](...)`；`:332` 补路径链接 `[references/pipeline_details.md §16](...)` | `SKILL.md`（46814→46925 B，距预警线 75 B） |

**验证（三项目 fresh 全链 + 冒烟 + 体量，均先跑基线再比对）**：
- **凤鸣朝阳**：pipeline rc=0；inspect rc=0 FAIL 0 WARN 3（与基线一致）；parsed/coverage/titleblock/config 四产物 md5 逐位一致（profile 仅 outdir 路径差）。
- **柳辛庄 1-4**：pipeline 在 parse rc=2 中止（8 阶段停，多地块拦截路径与基线一致）。
- **云峰**：pipeline 11 阶段（124s）；count_box rc=0，未调参版偏移异常 1 列 + 共用刻度 4 组，13 列与基线逐列一致；inspect rc=2 FAIL 6 WARN 10（与基线一致）。
- **冒烟**：`tests/run_smoke.py --with-dxf` ALL PASS（T5 语料外置 SKIP）；`budget` rc=0；改动脚本 `py_compile` 全绿；`norm_floor` 等价矩阵 12 项（B1/B1F/3F/-1F/17F/WF/三层/十七层/地下一层/负1层/室后缀/非楼层）新旧一致（WF：旧 None→新 900，双侧一致更优，见条目）。
- **备份**：改前文件级备份 `E:\ftth-kb\backup_ftth_true_20260926_155848\`（56 文件）；回滚 = 该目录整体拷回。

- **版本**：`version.json` 0.112.0 → **0.113.0**（minor 位对应修订序号一百一十三）。

### 2026-09-26（一百一十二）：count_box 自动配刻度列修复——相邻共享刻度列复用 + 整数谱校验（云峰 3#楼2单元 B1 虚增 2 户实锤单修）

**实测动因**：云峰 3#楼2单元出表 B1 层出现 2 户「未分配」且 17F 缺 2 户（34 户总数不变）。区间法复核：底部 2 个图标（y=-3996.37/-3990.37）距 1F 刻度仅 0.6~6.6、距 B1 刻度 23~29，半开区间 [B1,1F) 实为**半开区间把贴 1F 刻度线的图标误归 B1**；根因不是 band_of 区间语义，而是 pick_scale 自动配对错选**邻楼刻度列**：列4 x=25939.8 被配对到 5# 楼刻度列 x=26147.6（距 207.8）而非本楼 x=25706.4（距 233.4）——min_dist 取几何最近但跨楼栋「更近」，配错列后 B1/17F 边界错位。

| # | 问题 | 改动 | 文件 |
|---|---|---|---|
| 1（P0） | pick_scale 自动配对取全图几何最近刻度列，模糊列可能配到**邻楼**刻度列（云峰 3#楼2单元 x=25939.8 → 5# 楼 x=26147.6），错列后归层边界整体错位（B1 虚增、17F 漏） | 新增 _fix_shared_scale(init_pairs) 自动修正：① 相邻列**共享刻度列复用**（同谱列簇内已绑定刻度列的邻居作为候选，优先于全图 min_dist）；② **整数谱校验**（每列配对后偏移谱非整倍数即拒绝该候选、回退 min_dist 并告警）；③ 显式 --col-scale-map 列不参与自动修正。修正列打印 ⚙ 共享刻度列修正：列 x=25939.8 改用邻列刻度列 x=25706.4（谱 30.0 整倍数校验通过）。band_of **维持半开区间 [lo,hi) 语义不变**（曾试点「相邻刻度中点分界」为过度修正，会拆散 1F~17F 每层 2 户模式并误伤 1#楼 B1:1，已回滚） | scripts/count_box_icons.py |
| 2 | 修正后 count 产物与旧基线 diff 依赖人工（回归风险） | `verify_v1_final.py` 对比 13 列：仅列4 变化（刻度列 26147.6→25706.4，B1 2→0、17F 0→2），其余 12 列与基线逐列一致 | `.temp/云峰_fix/verify_v3_final.py`（工作区产物） |

**验证**：
- ① **云峰实测**（count_box_v3.json vs 旧 count_box.json）：13 列仅列4 变化，其余 12 列逐位一致；合计 331→331 户不变、未归属 0；列4 B1:2→0、17F:0→2，1F~17F 各 2 户=34 户成立
- ② **零回归**：1#楼 B1:1（coverage FX01 覆盖 B1~9F 佐证）、11#配套楼 B1:3 均保持；列8 x=26768.9 被标偏移异常 28% 但实测两种候选刻度列归层结果完全一致（每层 2 户），户数不受影响，属已知误报
- ③ 中点法试点（v1/v2）已验证为过度修正（8 列被改坏：列0 B1 1→0、列1/2/3 1F 户被吞、2F 变 3 户），回滚后 v3 不再改动 band_of 语义
- **版本**：`version.json` 0.111.0 → **0.112.0**（minor 位对应修订序号一百一十二）。

### 2026-09-26（一百一十一）：assemble 同配置展开——coverage 有箱但 col-map 无列的楼栋补入（云峰 9#楼 40 户实锤单修）

**实测动因**：云峰出表丢 40 户（346 vs 应为 386，差 9#楼 2 单元各 10 层×2 户）。实测：coverage 有 9#楼 2 单元（FX19#/FX20#，覆盖 1F~10F），count_box 在系统图区 329 个 EQUIP-箱柜图标全识别但 9#楼无独立图标列，assemble col-map（13 列→11 栋，不含 9#楼）产物无 9#楼；旧逻辑只打印「coverage 中有 N 个单元在组装结果中不存在」告警、不补入。用户裁决「按同配置展开」。

| # | 问题 | 改动 | 文件 |
|---|---|---|---|
| 1（P0） | assemble 不检查「coverage 有箱但 col-map 无列」的楼栋——缺图标楼栋静默丢失（只告警不补入） | coverage 合并段后、守恒统计前新增「同配置展开」：遍历 `cov_warn_unmatched`，取缺列单元的 coverage 覆盖楼层集合，在已组装单元中找覆盖楼层集合完全一致的模板（按 `(len(楼栋), 楼栋, 单元)` 排序首个，如 9#楼→7#楼/1单元）；找到则复制模板楼层表补入，补入户 `result_origin="derived"`（非直读），分纤箱保留 coverage 原始箱，打印 `⚠ 同配置展开：B/U 无图标列，按 TB/TU 同配置展开 N 层 × M 户 = T 户（覆盖楼层一致；模板每层户数；result_origin=derived，请核对）`，并从未匹配清单移除；找不到模板 / 无覆盖楼层信息则打印「无同配置模板，需人工补入，不编造户数」，保持告警不补入。无 coverage 时不展开；col-map 有列、共享列克隆行为全不动；有展开时 rc=0 | `scripts/assemble_households.py` |

**任务书偏离说明**：任务书（`.temp/云峰_fix/opencode_prompt_assemble_expand.md`）写「落 SKILL_CHANGELOG『一百零九』」，系拟定时快照滞后（一百零九/一百一十已先行落地），本修按序号顺延为**「一百一十一」**，`version.json` 0.110.0 → **0.111.0**。任务书「合计 386 户」为含裁决口径（raw 331 + 4#配套楼 B1:1→16 即 +15 = 346，再 +9#楼 40 = 386；见 `.temp/云峰_fix/rulings_apply2.json` 与 `assembled_ruled.json`）：assemble 本体只管户数直读+同配置展开，raw 口径为 331→**371**（+40），+15 乘数仍由 apply-ruling 落定，本条目如实记录两口径。

**验证**：
- ① **云峰实测**（count_box.json + coverage_fixed2.json + 13 列 col-map 不含 9#楼）：`⚠ 同配置展开：9#楼1单元/1单元…按 7#楼/1单元…10 层 × 2 户 = 20 户`、`9#楼2单元/2单元` 同理各 20 户，合计 **371**（raw；+rulings_apply2 即 386，与 `assembled_ruled.json` 一致），rc=0，补入户 `result_origin=derived`，分纤箱 FX19#/FX20# 保留；原 coverage.json（`9#楼/1单元、9#楼/2单元` 键形态）同参复测同样展开、合计 371
- ② **零回归**：coverage 去掉 9#楼后重跑 → 无展开行、合计 331、无未匹配告警；无 coverage 单跑 → 无展开、合计 331；共享列克隆单测行为不变
- ③ **无模板不编造**：合成 `12#楼/1单元` 覆盖 {B2,B1}（无相同覆盖模板）→ 打印「无同配置模板，需人工补入，不编造户数」，不补入、合计仍 331、未匹配告警保留、rc=0
- ④ 全仓 `py_compile` 全绿；`budget` rc=0（SKILL.md 46814 B 未动）；`tests/run_smoke.py --with-dxf` ALL PASS（失败 0 项；T5 语料外置 SKIP）

- **版本**：`version.json` 0.110.0 → **0.111.0**（minor 位对应修订序号一百一十一）。

### 2026-09-26（一百一十）：count_box 偏移异常校验左右分谱（云峰 R013 实锤单修）

**实测动因**：云峰 13 列重跑（`count_box.json`）：右侧 9 列偏移 114.4（7 列）/229.2 与 229.1（2 列 = 2×114.4）构成主偏移谱；左侧 4 列（列x < 刻度列x：25611.0/25939.8/26768.9/26769.6，偏移 95.4/207.8/76.9/101.3）与 114.4 不成整数倍，**全部被误报「刻度偏移异常」**，而 4 列的配对与归层全部正确（29/34/20/8 图标与层数分布经 R009 确认）。根因：`mode_base` 把全体列 |偏移| 取单一最大簇中心 = 114.4（右侧占多数），`period_dev` 逐列比对该谱 —— 隐含「全体列偏移同分布」假设；但共用刻度列组形态下左右两侧是两套不同的几何（左侧楼栋画在刻度线左边某处、右侧画在右边某处，间距不必相等），天然不对称。

| # | 问题 | 改动 | 文件 |
|---|---|---|---|
| 1（P0） | 偏移异常校验单侧假设：多栋共享系统图左侧正常列全部误报（4 列 FAIL/WARN，告警疲劳） | **左右分谱**：按偏移方向（列x<刻度列x=左、列x>刻度列x=右）分别建谱，各取最大显著簇中心（沿用 `mode_base` 簇逻辑，新增模块级 `side_spectrum` 供单测）；每列只与**同侧谱**做 `period_dev` 整数倍校验；同侧无主导谱（成员<2，或无显著簇，或最大显著簇未过半数）时该侧**跳过校验**（`偏移异常说明="左侧/右侧…跳过校验"`，`刻度偏移异常=False`，不进 `scale_outliers`）。同一侧内偏离该侧谱仍判异常，真错配照样拦住。归层算法（`pick_scale`、y 覆盖判据、`--col-scale-map`）与退出码语义、共用刻度列组门禁全不动 | `scripts/count_box_icons.py` |
| 2 | 输出口径 | 每列新增 `偏移方向: 左/右/同位`；`参数`新增 `刻度偏移左谱/刻度偏移右谱`（`刻度偏移主偏移`保留全体旧口径，仅兼容比对）；控制台主偏移行改为分别报告左谱/右谱；`scale_outliers` 与 inspect C5 消费格式不变（清单变短）；`--scale-period-tol` help 与 L841-850 注释区同步左右分谱语义 | `scripts/count_box_icons.py` |

**任务书偏离说明**：任务书（`.temp/云峰/opencode_prompt_scale_fix.md`）写「版本 0.107.0 → 0.108.0／落 SKILL_CHANGELOG『一百零八』」，系任务书拟定时快照滞后 —— 「一百零八」（git 管理外移）与「一百零九」（测试语料外移）已先行落地，本修按序号顺延为**「一百一十」**，`version.json` 0.109.0 → **0.110.0**。另任务书「同侧谱不存在（该侧只有一个成员）时跳过」按字面实施时云峰左侧仍剩 1 列误报（76.9 vs 左侧最大显著簇 [95.4,101.3] 中心 98.35 偏离 27.9%）：左侧 4 列分属 4 个不同刻度列组、跨组本无共识谱，偶然接近的 2 列成簇不代表全侧几何。故跳过条件扩展为「无主导谱（最大显著簇未过半数）即跳过」，云峰左侧 4 列（最大簇 2/4 未过半）整体跳过；右侧 9 列（主簇 7/9）照常校验。扩展部分已在合成单测中证明真错配仍可拦（见验证②）。

**验证（三态）**：
- ① **云峰重跑**（`ftth_launcher.py count_box_icons.py 云峰.dxf <out> --wire-layer RX-wire.通讯,WIRE-通讯`，wire-layer 取自画像 `effective_layers`，与原产物同参；任务书 `--out` 系笔误，实为位置参数）：左侧 4 列不再报偏移异常（`刻度偏移异常=False`，说明均为「左侧 4 列最大显著簇未过半数，无主导谱，跳过校验」）；右侧 9 列行为不变（114.4×7 通过、229.2/229.1 作 2× 通过）；`scale_outliers` 由 4 列 → **空**；归层逐列一致（图标数 37/29/29/33/34/34/32/32/20/8/20/3/20，合计 331，未归属 0，共用刻度列 5 组逐字一致）；inspect 重消费新产物 C5 行变为「乘数2/偏移异常0/共用刻度5/多候选0/未归属0」，清单格式不变（仅偏移异常段消失）
- ② **合成错配仍拦截**（`synth_scale_test.py` 经 ezdxf 解释器实跑，10/10 PASS）：左侧可靠谱 [100.0,101.0,99.5] + 错配列 250.0 → 基准 ≈100.17，250.0 偏离 24.8%（2×）被拦下，3 正常列偏离 ≤0.8% 通过；云峰左侧集 → 跳过；单列侧 → 「左侧仅 1 列，无显著簇，跳过校验」口径一致；云峰右侧集 → 基准 114.4，229.2 作 2× 通过（0.2%），合成 300.0 偏离 12.6% 可拦
- ③ **零回归**：单侧图纸新旧基线一致（[114.4,114.5,228.9]→114.45、[100,101]→100.5、5×114.4+229→114.4，新旧逐位一致）；全仓 `py_compile` 全绿；`budget` rc=0（SKILL.md 46814 B 未动，距预警线 186 B）；`tests/run_smoke.py --with-dxf` ALL PASS（失败 0 项；T5 语料外置 SKIP、无 corpus，T6 gen 缺 openpyxl SKIP，均为环境缺件非失败）

- **版本**：`version.json` 0.109.0 → **0.110.0**（minor 位对应修订序号一百一十）。

### 2026-09-26（一百零九）：测试语料外移（tests/corpus 不随技能目录携带）

**动因**：技能目录体积中 `tests/corpus/`（脱敏语料 `a小区.dxf` 1.7 MB + manifest + probe）约占一半；语料属回归基线，不随技能包分发（远端早已「语料 DXF 不随仓发布」，T5 语料缺失自动 SKIP 为既定方向）。

**改动**：

| # | 问题 | 改动 | 文件 |
|---|---|---|---|
| 1 | 技能目录携带语料（约 1.99 MB） | `tests/corpus/` 整体移出技能目录（入回收站）；语料保留在版本库 `tests/corpus/`（git 已跟踪，可持续管理） | 技能目录 `tests/corpus/` |
| 2 | 语料缺失时 T5 冒烟会 FAIL（probe 找不到 dxf） | `run_smoke.py` T5 支持 `--corpus <路径>` 与环境变量 `FTTH_TEST_DXF` 指定外部语料；两者均缺时 T5 自动 **SKIP**（不再 FAIL） | `tests/run_smoke.py` |
| 3 | 文档口径 | README 自检门禁段、tests/README 目录结构与语料清单同步改为「语料外置版本库」口径 | `README.md` / `tests/README.md` |
| 4 | 版本号 | `version.json` 0.108.0 → **0.109.0**（对应本条目「一百零九」） | `version.json` |

**验证**：场景① 技能目录无语料跑 `run_smoke.py --with-dxf` → T5 `[SKIP]`，其余 **ALL PASS（失败 0 项）**；场景② `--corpus <版本库语料>` → T5 真料 `[PASS]`（probe rc=0），ALL PASS。技能目录体量 3.88 MB → **1.93 MB**。

### 2026-09-26（一百零八）：git 管理外移 + 技能目录瘦身（版本库独立管理）

**动因**：技能目录内嵌 `.git/`（约 5.15 MB / 312 个文件，占技能体积约 40%），且上架打包时被平台裁剪成残缺仓库（缺 HEAD/config/index，git 无法识别，仅剩 objects/refs/logs），版本管理在技能目录里既膨胀又不可用。

**改动**：

| # | 问题 | 改动 | 文件 |
|---|---|---|---|
| 1 | 技能目录携带残缺 `.git`（约 5.15 MB），上架打包须排除 | **git 管理整体外移**：`.git/`（残缺）、`.gitattributes`、`.gitignore`、`scripts/.gitignore` 全部移出技能目录（入回收站）；技能目录只保留运行文件，体量 13.00 MB/435 文件 → **7.72 MB/120 文件**（净减 5.28 MB） | 技能目录根 / `scripts/` |
| 2 | 版本历史真源缺失（0.90.1 后 0.91~0.107 变更从未提交） | **版本库迁移**：`.backup` 中的完整仓库（31 个提交、含 0.65~0.90 全部历史、远程 `git@github.com:lyx100275-alt/ftth-address-extractor.git`）迁移至工作空间 `技能版本库/ftth-address-extractor/`；当前 0.107.0 全部内容同步入库并提交为基线（`fc84a74`，tag `v0.107.0`）；`.gitignore` 补 `*.geom.json` 忽略（规则置于 `!tests/**` 之后才生效） | 工作区 `技能版本库/ftth-address-extractor/` |
| 3 | 技能目录不再有 git 后，如何维护版本 | 新增独立「版本管理」技能 `skill-version-manager` 统一驱动提交/打 tag/查看 diff；README 新增「版本管理（git）」章节，说明版本库位置与同步流程 | `README.md` |
| 4 | 版本号口径 | `version.json` 0.107.0 → **0.108.0**（对应本条目「一百零八」），`skill_version_basis` 注明 git 外置事实 | `version.json` |

**验证**：版本库 `git status` 干净、`git log` 完整（0.65.0 → 0.107.0 基线 + 修正提交）；技能目录 `Test-Path` 确认 `.git`/`.gitattributes`/`.gitignore`/`scripts/.gitignore` 均不存在；`ftth.py budget` 与冒烟不受影响（技能脚本未改动，仅目录结构与文档变更）。

### 2026-09-26（一百零七）：merge_json 冲突来源可溯源 + 跨轮一致性扫描（多带合并链路 1 主修 + 1 评估）

**实测动因**：一百零六的冲突即停在柳辛庄 8 带合跑中发现来源标识只记 basename——8 输入全叫 `parsed.json`，`merged_v2_conflict.json` 里 `conflicts["1#楼"]` 7 个元素来源全是 `"parsed.json"`，控制台 FAIL 行与 `--allow-overwrite` WARNING 行同样无法区分哪一带，「冲突即停交人裁决」的溯源价值被削弱。

| # | 问题 | 改动 | 文件 |
|---|---|---|---|
| 16（P2） | merge_json 冲突/覆盖留痕来源只记 basename，同名输入无法溯源 | 来源登记改存**完整路径**（abspath；`conflict.json` 可溯源），控制台显示**父目录+basename**短格式（`band1块地/parsed.json`，可读）：新增 `_src_full/_src_short`，三处 `_register` 调用传完整路径，`处理/无法识别格式`行与 FAIL/WARNING 汇总行显示短格式（`detail` 构造时 `_src_short` 转换，`conflicts` 原样存完整路径）；格式 2/3 的楼栋名提取仍用 basename（正则/后缀逻辑不变） | `scripts/merge_json.py` |
| 评估 17（不修，给理由） | 跨轮改动累积一致性扫描（第 2/6/7/8 轮相互作用复查） | **未发现新断链**，不改代码：① 第 2 轮 parse 溯源标签（口径A′/B′、`E-DXF-TEXT:图上箱位直写…`）只改 `安装楼层口径/依据来源` 文本，gen（`gen_addressbook.py` L207~251 按 `编号` 建键、`_norm_fx` 只归一编号）与 verify-truth（L162 按 `编号` 取箱）键匹配不变，C9 只认 `result_origin/result_confirmation` 枚举（`inspect_closure.py` L747）——标签文本不参与匹配；② C7「单元明细」兼容：`pending_items_from_rulings` 原生收列表对象（`ftth_common.py` L817）、`judge_pending_scope` 逐个匹配、`inspect _c7_one_line` 已处理列表对象（L141~143），`check_transitions.py` 不消费 `需人工裁决`——机读/展示均兼容；③ merge rc=2 对 batch：`ftth_batch.py` L431~437 已按非零计 fail 并截尾输出，无依赖 rc=0 分支（与任务书 L420-437 一致）——冲突会正确拦下批次，符合预期 | 无（评估结论落本条目） |

**文档同步说明**：`references/scripts_reference.md` 46982 B、距预警线仅 18 B，本轮未在该文件加来源字段注记（加即超预警线，按任务书体量红线先外移——注记落本条目：`conflict.json` 的 `来源`=输入文件完整路径，控制台 FAIL/WARNING 行=`父目录/basename` 短格式，同源两种显示）。

**验证**：
- 合成复现（4 带同名 `parsed.json` 各含 `1#楼`，箱数 4/3/2/2）：不传参 → rc=2 + 不写 `--out`（仅 `_conflict.json`）+ FAIL 行显示 `band1块地/parsed.json；band2块地/parsed.json；…` 可区分 + `conflict.json` 来源为 4 条完整路径；传 `--allow-overwrite` → rc=0 + WARNING 行短格式 + 保留末见版本（3 箱，与旧行为一致）
- 零回归：楼号全局唯一两输入（`1#楼`/`2#楼`）→ rc=0 正常合并 2 栋
- 编译：`merge_json.py` 及关联 7 脚本 `py_compile` 全绿；`budget` 改前改后 rc=0（SKILL.md 46814 B 未动；scripts_reference.md 46982 B 未动）；冒烟 `tests/run_smoke.py --with-dxf` ALL PASS（T0~T13 失败 0 项）
- 三项目 pipeline 主链：本环境无柳辛庄/云峰/凤鸣朝阳实战数据目录，仅以冒烟 + 合成 merge 实测 + 楼号唯一回归覆盖；改动面限 merge 来源显示（不碰合并判定/排序/键），零回归风险已隔离

- **版本**：`version.json` 0.106.0 → **0.107.0**（minor 位对应修订序号一百零七）。

### 2026-09-26（一百零六）：merge_json 跨输入同名楼栋冲突即停 + --allow-overwrite（多带合并链路 1 主修 + 1 评估）

**实测动因**：检验面拓宽到 merge_json 多带合并链路（柳辛庄 8 带合一实跑）：8 带箱前缀各不同但楼栋名跨带重复（band1 的 1#楼与 band9-1 的 1#楼为不同物理楼），`merge_json.py` 对同名楼栋 `warning + 覆盖`（后输入覆盖先输入），band1 的 1#楼 4 箱被 band9-1 的 2 箱静默覆盖，合并产物 13 栋/28 箱而 8 带合计 140 箱文字实例；34 条 WARNING 反复触发但不阻止。跨输入同名楼栋本质是数据冲突（同名异楼 vs 同楼跨图），按 L0-I4 须矛盾即停，不得自动覆盖。

| # | 问题 | 改动 | 文件 |
|---|---|---|---|
| 15（P1） | merge_json 对跨输入同名楼栋静默覆盖（warning+覆盖），违反 L0-I4 矛盾即停——多地块合并场景箱级数据整栋丢失 | `merge_json.py` 默认行为改为**冲突即停**：跨输入同名楼栋登记来源（来源文件+各单元数/箱数），循环后按楼名一条汇总报 `[FAIL]`（列出所有来源），写 `<out>_conflict.json` 备查，不写 `--out`，退出码 2；新增 `--allow-overwrite` 显式放行（用户裁定同一物理楼时覆盖，保留 warning 留痕，按 L0-I5-A）。三种输入格式（楼栋/楼层户数表/单元）统一经 `_register` 登记，WARNING 噪音合并为按楼名一条 | `scripts/merge_json.py` + `references/scripts_reference.md`（merge_json 参数行） |
| 评估（不实现，仅给方案） | 是否提供 `--prefix-by-source`（楼栋名加来源前缀）作多地块合并推荐路径 | **不实现，给理由**：① 楼栋名是法定地址要素（进 gen 的 xlsx 楼栋列），自动加前缀会污染成品地址（`band1/1#楼` 进表即错）；② gen 按楼栋键组装，前缀改变键匹配面，牵动下游；③ 消歧须人工确认地块归属（哪两栋同名异楼），脚本自动前缀仍是自动取舍。推荐路径：冲突即停后人工改名消歧再合并 | 无（评估结论落本条目） |

**验证**：
- 合成复现（band1 的 1#楼 4 箱 + band9-1 的 1#楼 2 箱）：不传参 → rc=2 + 冲突详情（含双方来源/箱数）+ 不生成 merged.json（仅 _conflict.json）；传 `--allow-overwrite` → rc=0 生成 merged.json（末见版本 2 箱，与旧行为一致）+ 覆盖留痕 warning 一条
- 零回归：两无同名楼输入合并 → rc=0 正常合并
- 编译：`merge_json.py` `py_compile` 过；`budget` rc=0；冒烟 `tests/run_smoke.py --with-dxf` ALL PASS（见下）

- **版本**：`version.json` 0.105.0 → **0.106.0**（minor 位对应修订序号一百零六）。

### 2026-09-26（一百零五）：verify-truth 与 gen --fx-prefix 对称 + 前缀形态误导报文提示（跨轮断链 1 主修）

**实测动因**：一百零四给 gen 加了 `--fx-prefix`（P 列统一前置验收前缀）后，本轮复跑发现该修复与 verify-truth 存在跨轮相互作用断链 —— 定稿表 P 列「绿城凤鸣朝阳FL01-FX01」（带前缀）vs coverage 线索「FL01-FX01」（裸编号），`verify_coverage_truth.py` 按全等匹配，凤鸣朝阳 17/17 全失配（一致 0 / 不一致 17，rc=2），且反报「线索里有真值表没有的箱」（误导方向：以为表缺箱，实际是编号形态不匹配）。该断链历史上隐性存在（成品表一直带前缀，反查从未通过），前缀正式化为 gen 参数后成为必然 100% 复现的技能缺陷；verify-truth 是「有真值表必跑反查」的回归验收门禁，断链即门禁失效。

| # | 问题 | 改动 | 文件 |
|---|---|---|---|
| 14（P0） | verify-truth 无法匹配带统一前缀的 P 列：gen --fx-prefix 出的定稿表反查全部失配 | `verify_coverage_truth.py` 新增 `--fx-prefix`（与 gen 对称）：比对前对表列值剥前缀（`startswith` 才剥，语义与 gen 侧 `_with_fx_prefix` 镜像；空值/空白/「未分配」天然不受影响），剥完再全等匹配；未传时聚合路径逐字不变。`ftth.py verify-truth` 同步注册该参数（`build_cmd` 自动透传，分发段无需另改）。另修误导报文：未传 `--fx-prefix` 且全部行失配时，检测表列是否为「公共前缀 + 线索编号」形态（长串优先防短串误配；各行前缀一致才点名），是则打印一条「可用 --fx-prefix 重跑」提示；只提示、不自动剥（多小区合并表自动剥有误配风险）。退出码语义不变 | `scripts/verify_coverage_truth.py` + `scripts/ftth.py` + `references/scripts_reference.md`（verify 参数行）+ `references/step2_selfcheck.md`（必跑反查条目补前缀注记一行） |

**验证**：
- 凤鸣朝阳定稿表 + iter07 coverage.json，带 `--fx-prefix "绿城凤鸣朝阳"` 重跑 → 一致 17 / 不一致 0、rc=0（见下）
- 零回归：裸编号形态（定稿表剥前缀副本，不传 `--fx-prefix`）→ 一致 17 / 不一致 0、rc=0；不传前缀跑原带前缀表 → 仍 0/17 rc=2 + 新增前缀形态提示行（行为差异仅提示行）
- 编译：`verify_coverage_truth.py` / `ftth.py` `py_compile` 全绿
- `budget` rc=0（SKILL.md 未动；scripts_reference.md / step2_selfcheck.md 增量在预警线内）
- 冒烟：`tests/run_smoke.py --with-dxf` ALL PASS（见下）

- **版本**：`version.json` 0.104.0 → **0.105.0**（minor 位对应修订序号一百零五）。

### 2026-09-26（一百零四）：gen 分纤箱统一前缀 + fails 机读纪律 + C6 成因分流（下游出表链路 1 主修 + 2 评估）

**实测动因**：pipeline 主链收敛后把检验面拓宽到下游出表链路，从凤鸣朝阳历史实战数据挖出 1 实锤 + 2 评估项，直接改代码（评估项不成立、未改代码）并自验证：

| # | 问题 | 改动 | 文件 |
|---|---|---|---|
| 11（P1） | gen 缺「分纤箱编号统一前缀」能力：验收口径要求 P 列带小区前缀（凤鸣朝阳成品 17 箱全带「绿城凤鸣朝阳」），但 gen 只有逐箱 `--fx-prefix-map`（17 箱写 17 条、柳辛庄 140 箱写 140 条，不可扩展），实战被迫手写 openpyxl 临时脚本手改 xlsx（pipeline_details.md §4 明文禁止的同类形态），且 gen_raw 与成品成两份不一致交付物 | `gen_addressbook.py` 新增 `--fx-prefix <统一前缀>`：P 列每行统一前置，去重（已带不叠加）、空值/空白/「未分配」不加；与 map 并用时**先归一后加前缀**（顺序反了 map 的旧前缀匹配不上）；模板示例行不受影响（只取表头格式不复制数据）。**不从 `--addr` 第 5 级自动推导**：小区名≠验收前缀是实测常态，自动加=把用户裁决口径变脚本推断，违 L0 纪律；gen 只做机械执行，须显式传入（显式参数不违反 P1，属表达层归一化）。`ftth.py` gen 子命令同步注册（`build_cmd` 自动透传，分发段无需另改） | `scripts/gen_addressbook.py` + `scripts/ftth.py` + `references/scripts_reference.md`（gen 参数表） |
| 12（评估·不成立，未改代码） | inspect.json fails 数组混存检查项汇总与明细行（band9-1：C10 出现 3 次=1 汇总+2 明细），机读方难区分 | **维持现状，给理由**：`Report.check()` 已按 cid 去重保证每检查项一条汇总，`R.fail()` 明细行是逐条定位，两者并存是设计（汇总计数与逐行结论自洽）；机读方应读 `checks` 结构化记录。改 fails 形态（加 ID 前缀/拆分）会破坏历史 grep 消费兼容，收益小于风险。文档已在 `step2_selfcheck.md` 明确「fails 仅人类可读摘要、机读读 checks」 | 无（评估结论落本条目 + `references/step2_selfcheck.md` 机读纪律注） |
| 13（评估·不成立，未改代码） | C6 FAIL 在「vshape 窗口无箱锚」（band9-1：提供了 JSON 但箱级 0 条）与「画像申报三法全缺」（band5：未提供 coverage JSON）两类成因下 detail 不区分三法细节，人工处置不同 | **暂不实现，给可行结论**：inspect 输入仅 parse/coverage/geom（无画像），拿不到三法申报，加 `--profile` 取画像违最小改动（要动 inspect + pipeline 两处 CLI 面）。且两类 detail 首句**已区分**（提供但 0 记录 vs 未提供），可据此分流；三法细节在 `profile.json` 覆盖范围 `阻塞原因` + `logs/pipeline.log` coverage rc=3 行已有。文档已在 `step2_selfcheck.md` 加成因分流指引 | 无（评估结论落本条目 + `references/step2_selfcheck.md` 分流指引注） |

**验证**：
- 编译：`gen_addressbook.py` / `ftth.py` `py_compile` 全绿
- `budget` rc=0（SKILL.md 未动；scripts_reference.md 增量在预警线内；step2_selfcheck.md 余量充足）
- 冒烟：`tests/run_smoke.py --with-dxf` ALL PASS（见下）
- 问题 11 凤鸣朝阳实测（`.temp/iter05/凤鸣朝阳/parsed.json` + `coverage.json` + `assets/标准地址表模板.xlsx`，`--addr 河北,石家庄,桥东区,胜利西街,绿城凤鸣朝阳 --branch 石家庄 --fx-prefix 绿城凤鸣朝阳`）：P 列 313/313 全带前缀、无双重前缀、尾行未加；行数恒等式不变（315==315）；非 P 列零差异；与桌面成品逐行 P 列全等（313 行、17 箱集合全等；成品 317=313 数据+1 表头+1 模板尾+2 宿主水印，行对齐按数据行顺序比对）；组合语义 `--fx-prefix-map FL01=FL99` + `--fx-prefix` 得 `绿城凤鸣朝阳FL99-FX01`（先归一后加前缀生效）
- 零回归：gen 不在 pipeline 内；fails/C6 零代码改动

- **版本**：`version.json` 0.103.0 → **0.104.0**（minor 位对应修订序号一百零四）。

### 2026-09-26（一百零三）：C9 明细行旧文案与 warn 新语义对齐 + inspect 裁决感知评估（第 3 轮实跑 1 主修 + 1 评估）

**实测动因**：第 3 轮三项目复跑零回归后又一轮实跑发现 1 实锤 + 1 评估项，直接改代码（评估项不成立、未改代码）并自验证：

| # | 问题 | 改动 | 文件 |
|---|---|---|---|
| 9（P2） | C9 明细行（R.emit）仍是旧文案「已提供但零字段的来源：coverage —— 该来源未被本闸门覆盖」，与同检查项 warns 汇总行新语义「箱级记录为 0、无对象可挂字段、非字段漏写」自相矛盾。根因：一百零一问题 3 只改了 warn 两类拆分分支，L776 明细行漏同步 | 明细行与 warn 分支**单源对齐**：`_cov_box_n/_zero_obj/_zero_fld` 上移至明细行处一次算出（判据逐字复用问题 3：`coverage` + parse 非空 + 箱级 0 条 ⇒ 零对象），零对象形态输出「来源 coverage 已提供但箱级记录为 0 —— 无对象可挂结果状态字段（非字段漏写；覆盖零产出见 C6 FAIL）」、有对象无字段形态输出「来源 X 已提供但零字段 —— 未被结果状态闸门覆盖，不得视为已核」，下文 warn 分支复用同一组变量不再重复计算；grep 确认无第三处同类残留（其余命中均为注释/他脚本说明文字） | `scripts/inspect_closure.py` |
| 10（评估·不成立，未改代码） | inspect 每轮全量重复已裁决告警（凤鸣朝阳 C1/C5/C8、云峰 6 FAIL/10 WARN），提案给 inspect 加 `--ruling-ledger/--project-dir` 对已裁决告警追加「已裁决（见台账 Rxxx）」标注 | **不成立：匹配歧义风险大于收益**，不实现。① 台账无稳定键：schema 仅 `问题/裁决原文/裁决人/适用范围` 自由文本（`ledger_state.py`），实测凤鸣 R001「C1 楼号1-8缺4#」vs 告警「楼号序列 1~8 缺 4#」为改写非原文，R002/R003 `适用范围` 为空，云峰 R001 一条适用范围覆盖三箱三项 C9 pending（多对多）、R004/R005 同一 *16 事项两条裁决先后补充（R005 修正 R004「8+3 列」误读），R004~R006（地址前缀/保存位置）根本无对应告警——文本/键匹配皆不可靠，易错配；② 架构逆序：inspect 是出表前纯核查器（输入仅 parse/coverage/geom，无 `--project-dir`），裁决消化位在 assemble/apply-ruling，闸门前标注闸门后状态即使用户视角省事、也会把「已裁决未消化」读成「已闭合」，与 L0-I4 矛盾即停语义暗冲突（虽不抑制、仍弱化停下效力）；③ 末尾静态提示同样不加：同属无输入无真相的展示层承诺（同输入不同输出，破坏复现性），且 inspect 何时传 project-dir 无调用契约。替代：本结论即文档（本条目），操作侧已由 `transitions --project-dir` 承载裁决核对，不新增 CLI 面 | 无（评估结论落本条目） |

**验证**：
- 编译：`scripts/inspect_closure.py` `py_compile` 过；全仓编译由冒烟 T0 覆盖
- `budget` rc=0（SKILL.md 未动；references 无 C9 文案引用，无需同步；SKILL.md 距预警线仅 186 B，文档只落本文件符合体量纪律）
- 冒烟：`tests/run_smoke.py --with-dxf` ALL PASS（T0~T13 失败 0 项；T13 为多栋合并楼名登记，与 C9 无关；全仓 grep 确认 tests 无 C9 文案断言，无需同步）
- 定向：`.temp/iter03/柳辛庄5-9/band9-1块地/` 真实产物（parsed.json + coverage.json + geom + titleblock）复跑 inspect 单命令，C9 明细行已为「箱级记录为 0、无对象可挂字段」新语义，与 warns 汇总行一致，退出码语义不变
- 零回归：改动仅 C9 展示行（emit 文案 + 变量上移复用），C6/C3 等门禁逻辑未触；云峰/凤鸣朝阳路径为 present/有覆盖形态，走 `_zero_fld`/PASS 分支不受影响

- **版本**：`version.json` 0.102.0 → **0.103.0**（minor 位对应修订序号一百零三）。

### 2026-09-26（一百零二）：absent 溯源标签失真 + quiet 日志丢失 + 改派计数含糊 + C7 同形态合并 + probe 块定义去重（第 2 轮实跑 4 主修 + 2 评估）

**实测动因**：第 2 轮 8 带实跑（柳辛庄 band9-1 absent / 云峰 present / 凤鸣朝阳）暴露 4 项 P1~P2 + 2 评估项，全部直接改代码并自验证：

| # | 问题 | 改动 | 文件 |
|---|---|---|---|
| 4（P1） | absent 下箱级溯源标签失真：走图上箱位直写证据（②）却硬标 `fxmap对照表` / `E-DXF-TEXT:总图对照表`，指向不存在的 fxmap.json，与同产物 `BDGMAP归属.来源=图上箱位直写自证` 自相矛盾 | `BDG_MAP` 双源（① `--bldg-map` 文件 / ② `build_fx_direct_evidence` 直写）按 `_DESC_ADDED_SET` 逐箱区分：② 标 `箱位直写标注（fx_locations）` / `E-DXF-TEXT:图上箱位直写标注（N号楼M单元K层，…）` / `口径A′:图上箱位直写标注（…）`，B′ 落区间分支时依据来源同样标直写；① 标签逐字不变。数值/误差/result 字段不动 | `parse_dxf_structured.py` + `pipeline_details.md §9` |
| 5（P2） | `--quiet` 下 ftth.py 阶段级输出（rc=3 跳过原因/gate 处置/串号提示/告警）零落盘：rc=3 阶段连 log 文件都不存在 | stdout tee 双写 `logs/pipeline.log`（零调用点改动；quiet 与非 quiet 同行为）；恢复点选 `_dump`（全部出口经此收敛已核对）。rc=3 跳过原因并入 pipeline.log | `ftth.py` + `pipeline_details.md` 参数表 |
| 6（P2） | `BDGMAP归属.改派条数=47` 是文字实例级计数（16 箱×多实例），与「16箱」并列误读成 47 箱被改派；清单同编号重复且无坐标 | 拆 `改派文字实例数` + `改派箱数`（旧键删除，tests 无引用），跨栋改派每条补实例坐标 `@(x,y)`；日志同步显式口径。两填充源路径同一段代码，一并生效 | `parse_dxf_structured.py` + `pipeline_details.md §8` |
| 7（评估·成立） | C7「V段数与箱数不一致·窗口内无箱号锚」逐单元 50+ 条同文案，根因（覆盖零产出）已被 C6 FAIL 拦下，淹没真告警 | ≥2 条同形态合并为图级汇总 1 条 + `单元明细`（信息不丢）；`对象` 用列表承载全部单元串（`judge_pending_scope` 原生逐个匹配，各单元 pending 判定不变）；inspect `_c7_one_line` 列表 join 展示（仅展示层）。单条不成组；非本形态逐字保留 | `analyze_coverage_vshape.py` + `inspect_closure.py` |
| 8（评估·成立） | 云峰 probe.log 2095 行中 445 行同一句 `块定义: tag=A text=HDD` | 首见打印 + 重复折叠计数；附带修真 bug：原实现用 stale 变量 `bname`（上一循环遗留）查块定义，N 个不同块打的全是同一块定义，改查本轮 `bn`（纯探查输出，不影响产物） | `parse_dxf_structured.py` |

**全仓审计结论（问题 4 要求）**：parse 侧其余 `E-DXF-*` 赋值点 —— 区间法几何归属（`E-DXF-GEOM`，真实几何来源）、`--fx-map` 回填（真实 fx-map 文件来源）均为单源 genuine，不改；coverage 侧（`analyze_coverage.py` / vshape）依据来源描述各自方法（竖干连续体 / V 型谷底），非多源复用，不改。`operations_discipline.md` A′/B′ 分档已登记箱位直写形态，无需补；`pipeline_details.md §9` 原「absent 时无此口径」已按双源修正。

**验证**：
- 编译：4 个改动脚本 `py_compile` 全绿；`budget` rc=0（SKILL.md 未动 46814 B；references 最大者 scripts_reference.md 46542 B，pipeline_details.md 增量在预警线内）
- 冒烟：`tests/run_smoke.py --with-dxf` ALL PASS（T0~T13 失败 0 项）
- 定向：Q4 真实源码分支 exec 桩测 6/6（直写 A′唯一/配对、B′区间分支标签正确；文件源三处标签逐字回归；pending 路径回归）；Q7 合并块 exec（3 条→1 汇总+3 明细，真告警保留）+ `judge_pending_scope` 列表对象 3 单元命中/无关楼栋不误伤；Q8 语料 probe 9 块 9 定义各显一次（旧 stale 变量下 9 行全同）；Q5 语料全链 `--quiet` rc=0，3 个 rc=3 跳过原因全进 `logs/pipeline.log`（35 行），Q6 新字段格式串实测
- 凤鸣朝阳/云峰零回归：文件源分支字符串逐字未动 + present 路径条件未触（`_DESC_ADDED_SET` 为空时恒走旧标签）；a小区全链复跑 rc=0，17 箱全 `口径B:区间法` + `E-DXF-GEOM`（几何路径，本轮未改）

- **版本**：`version.json` 0.101.0 → **0.102.0**（minor 位对应修订序号一百零二）。

### 2026-09-25（一百）：待裁决项呈现方式「先推理 → 再选择题」（用户裁定）

**实测动因**：云峰实跑后 6 项待裁决（5 项 C9 pending + 1 项 C5 乘数 FAIL）待报人，用户裁定呈现方式：**助手先推理（交叉分析图面证据、列事实与可能性），然后出选择题让用户作答**——不得只列「问题+双方数值」就把取证工作推回给用户。该裁定与 §5.5 既有精神（报人须写成可直接作答的选择题）同源，本次把它细化为两步呈现的硬要求。

| 改动 | 文件 | 内容 |
|---|---|---|
| ① §5.5 扩展 | `references/operations_discipline.md` | 在「最小化二选一」下新增「呈现顺序：先推理，再选择题」两步要求：先推理=呈现证据链（矛盾为什么成立、每个解释的成立条件与反证，可推理可推荐、不裁决）；再出选择题=每项 2~4 个选项覆盖主要解释 + 「其他」兜底 + 推荐项标注（推荐只是线索排序，用户选择才是裁决，落盘 E-HUMAN-RULING）；同一根因的多个矛盾项合并成一题；批量提交原则保持 |

**与既有条款的关系**：不新增检查 ID、不动 rc 语义、不改任何脚本——纯操作纪律细化。§5.6 底线（惯例不得作裁决依据）、§5.7（可推理可推荐不裁决）、§五·补（E-HUMAN-RULING 最高）均不受影响，新要求正是这三条的呈现层落地。

**验证**：budget rc=0（operations_discipline.md 24439 → ~25000 B，距预警线充足）；无代码改动，无需编译/冒烟/MD5 回归。

**备份**：`.temp/ftth_bak_20260925_221641_ruling_format/`（operations_discipline.md 改前快照）。

- **版本**：`version.json` 0.99.0 → **0.100.0**（minor 位对应修订序号一百）。

### 2026-09-25（九十九）：云峰实跑驱动 —— C7 裁决项全量透传 + C5 图标法质量门禁 + unit_gaps 成因文案（opencode 第 6 轮审核）

**实测动因**：云峰（143.5MB，多栋共享系统图 + 图标法户数）全链 11 阶段实跑（rc=2，5 项 C9 pending 属图纸真实矛盾，不在技能审核范围）暴露三个技能自身问题，交 opencode（muse-spark-1.3-contributor-free）独立审核，三项全部确认成立并给出落地方案，照单实施：

| 改动 | 文件 | 内容 |
|---|---|---|
| ① **P0 C7 机读层去截断** | `inspect_closure.py` | 原 warns（进 inspect.json + 末尾汇总）把「需人工裁决」json.dumps 后 [:80] 截断——残差/阈值/「需人工裁决」结论全被切在 JSON 字符串中间（coverage.json 里明明是全文）。新增 `_c7_one_line()`：dict 条目结构化压行（对象=…｜事项=…｜说明=…），非 dict 回退全量 json.dumps；详情行展示层 [:300]、warns 机读层不截断。全文件其余 [:N] 经 opencode 逐一审计：L308/413/417/477/625/702/833 均为展示层或计数式截断，机读层完好，不改。 |
| ② **P0 C5·count-box 质量门禁** | `inspect_closure.py` + `ftth.py` | count_box.json 四类质量告警（待裁决乘数 / 刻度偏移异常列 / 共用刻度列组 / 同一端点多候选）此前仅在 parse-0-箱分支透出偏移异常一类；云峰 parse 有 23 箱 → 全部不可见，且复用轮连 count_box.log 都不打印，`*16` 这类 P5 强制裁决项静默漏网。现随 C5 透传（不新增检查 ID，C1~C10 名目不变）：**乘数未裁决 → FAIL**（L0-P5 禁区 + C9「未定案不得出表」哲学：带未裁决乘数出表 = 编造户数倍数，须人工裁决含义与落层口径后改数），刻度偏移异常列 / 共用刻度列组 / 同一端点多候选 / 未归属图标 → WARN（须复核不阻塞）。pipeline count_box 复用分支加只读摘要行（不重算不覆盖，判定以 inspect 为准）。 |
| ③ **P2 unit_gaps 成因文案** | `ftth.py` + `check_unit_box_gaps.py` | 「骨架侧未就绪（未提供该输入路径）」让用户误以为忘了传参——成因其实在 pipeline 手里。titleblock 阶段逐分支记录 `_tb_note`（画像申报跳过 / 无图层候选不猜 / rc=3 申报制跳过 / 阶段失败），经新增 `--titleblock-note` 参数透传给子脚本替换通用文案。仅文案，unresolved 判定与 rc 语义不变；传了路径但读不了/不存在时仍用 _load_json 错误详情。 |

**云峰实测前后对照**：
- C7 warns：截断 `…"说明": "图形符号（闭合多段线(尺寸≤60)）；与安装楼层线` → 全量 `对象=4#配套楼/FX22#｜事项=箱安装层标注冲突（符号位置已定）｜说明=…与安装楼层线残差 40.7（阈值 18.0）…需人工裁决`
- fails：5 项（C9×5）→ 6 项（**C5 乘数 FAIL 1 项** + C9×5）；warns：8 项（C7×8，截断）→ 10 项（C7×8 全量 + C5 偏移异常 4 列 + 共用刻度列 5 组）
- unit_gaps 预检：`骨架侧未就绪（未提供该输入路径）` → `骨架侧未就绪（titleblock 阶段 rc=3：本图未提供图签形态的成对标注（申报制跳过））`
- count_box 复用轮新增摘要行：`归层后总户数 331；乘数 2 / 偏移异常列 4 / 共用刻度列组 5 / 多候选 0 / 未归属 0`

**验证**：
- 编译：inspect_closure.py / ftth.py / check_unit_box_gaps.py py_compile 全绿
- 体量：budget rc=0（SKILL.md 46814 B 未动，距预警线 186 B）
- 冒烟：tests/run_smoke.py --with-dxf ALL PASS（T0~T13 失败 0 项）
- 凤鸣 MD5 回归：parsed `CC88…E3B` / coverage `6CC2…7AB` 与基线逐位一致（该图 K=None，C5 质量透传块整体跳过——不回归的证明）
- 云峰重跑：三处修复全部生效（见上对照），rc=2（6 fails / 10 warns）
- unit_gaps 三态回归：无参单跑 → 旧通用文案（向后兼容）；--titleblock 指向损坏 JSON → unreadable + 原错误详情（hint 不掩盖真错误）；--titleblock-note → 文案替换生效

**文档同步**：`references/step2_selfcheck.md` C5 行补「count-box 质量告警随 C5 透传」+ 新增「C5·count-box 质量透传」小节（文件 18554 B，余量充足）；SKILL.md 不动（体量红线）；scripts_reference.md 的 unit_gaps 概述行不涉参数枚举，无需改。

**备份**：`.temp/ftth_bak_20260925_215747_yunfeng_review/`（3 个被改文件改前快照）。

- **版本**：`version.json` 0.98.1 → **0.99.0**（minor 位对应修订序号九十九）。

### 2026-09-25（九十八）：三路 stale 守卫 + parse rc=3 对齐 + 参数透传 + 退出码修正（第二轮评审驱动）

**实测动因**：第二轮评审复现基线（凤鸣双跑 md5 逐位一致、云峰 5/46 pending、柳辛庄多地块拦截）后指出 4 项 P0 correctness + 7 项 P1 漂移 + 5 项 P2 体验。含两项参数透传的**失败尝试与回滚教训**。

| 改动 | 文件 | 内容 |
|---|---|---|
| ① **P0 stale 三路守卫** | `ftth.py` | inspect 的 `--coverage`/`--titleblock`/`--count-box` 三路 + unit_gaps 的 `--fx-map`/`--titleblock`/`--fx-locations` 三路 + coverage-vshape 的 `--fx-locations` 消费，全部从裸 `isfile` 改为「本轮产出标志 `_tb_produced`/`_fxl_produced`/`_cov_produced` + 残留 WARN」。复现路径：某 outdir 先跑图标法图，再跑非图标法图 → 旧文件被静默吃掉。 |
| ② **P0 parse rc=3 对齐** | `ftth.py` | parse 的 `if rc:` 一刀切中止改为 `if rc==3: 继续`（与 coverage:866 / count_box 同语义）。按 L1-C2 rc=3=absent 跳过继续。 |
| ③ **P0 count_box 参数透传** | `ftth.py` | fresh-run 从画像 `effective_layers.wire_layer` 透传 `--wire-layer`（语义正确：覆盖判定准备的连线层与 count_box 皮线层同义）。**不透传 `--floor-layer`**：probe 的 text_layer="0"（通用层名，云峰实测）传了破坏自适应 → rc=2。 |
| ④ **P0 退出码修正** | `assemble_households.py` + `inspect_closure.py` | assemble 全员 sys.exit(1) → sys.exit(2)（11 处全是输入类错误）；inspect 输入类 return 1 → return 2（5 处）。按 L1-C2 rc=2=补探查/须修。 |
| ⑤ P1 --stop-at 文档 | `pipeline_details.md` | 补 count_box（10→11 项） |
| ⑥ P1 C1~C7 残留 | `step2_selfcheck.md` | 两处七项→C1~C10 |
| ⑦ P1 冒烟/子命令数 | `README.md` + `SKILL.md` | T0-T6→T0-T13；子命令 13+"等"→16 显式列出（含 split-band/coverage-vshape/verify-truth） |
| ⑧ P1 norm_floor 统一 | `inspect_closure.py` | 删本地漂移版，改调 `ftth_common.floor_num`（支持 B1/B2/WF），加「N层」后缀回退 |
| ⑨ P1 fx_locations 参数透传 | `ftth.py` | 从 probe suggested_params.text_layer 透传 `--text-layer`（语义正确：文字层就是文字层） |
| ⑩ P2 台账确定性 | `ledger_state.py` | `sort_keys=False` → `True` 固定键序；时间戳仍为唯一变量字段 |
| ⑪ P2 入口编码 | `ftth.py` | 裸 `sys.stdout.reconfigure` → `ftth_common.ensure_console_utf8()`（幂等、有 try 守卫） |
| ⑫ P2 C6 节名 | `SKILL.md` | "（含 AIGC 水印行说明）" → "§回读校验与 AIGC 水印行" |
| ⑬ P2 silent except | `ftth.py` | 4 处画像读失败 except 加 DEBUG 打印（stderr），不改行为 |
| ⑭ P2 version 叙述 | `version.json` | "九十三、九十四、九十六未 bump" → "九十四、九十五为九十三补丁无独立节，九十六未 bump" |

**失败尝试与回滚（重要教训）**：
- **titleblock --bldg-re 透传**：从 probe suggested_params.title_pattern 透传 → **实测凤鸣 C10 从 PASS 变 FAIL**（楼1 单元=2/层=18、楼2~8 全消失）。原因：probe 的 title_pattern 是系统图标题正则（`(\d+#楼).*示意图`），与图签楼名（`1#楼/1号楼/1楼`）语义不同。**回滚**，保持脚本内置默认。
- **count_box --floor-layer 透传**：从 probe text_layer 透传 → **实测云峰 rc=2**（text_layer="0" 是通用层名，破坏自适应楼层识别）。**回滚**，floor-layer 留脚本自适应。

**验证（三项目 + 冒烟 + 体量）**：
- **凤鸣朝阳**：titleblock rc=0 + count_box rc=3 跳过 + inspect rc=0 FAIL 0 WARN 3；parsed/coverage MD5 与基线逐位一致（cc88…/6cc2…）—— stale 守卫 + parse rc=3 + norm_floor 回归零差异。
- **云峰**：count_box fresh-run 成功（wire-layer 透传生效，rc=0），inspect 消费 count_box.json，5 pending 不变（图纸真实矛盾）。
- **柳辛庄 1-4**：parse rc=2 多地块拦截路径不变。
- **冒烟**：`run_smoke.py --with-dxf` ALL PASS（T0~T13 失败 0 项）。
- **体量**：SKILL.md 46814 B（距预警线 186 B）；budget rc=0。
- **编译**：ftth.py / assemble_households.py / inspect_closure.py / ledger_state.py 全绿。

**opencode 审核返工（2026-09-25，同日第 3 轮，muse-spark-1.3-contributor-free 实跑驱动）**：

opencode 独立审核九十八全部改动，判定：stale 守卫 ❌（旧裸块未删+_bmap 标志缺失）、norm_floor ✅、assemble 退出码 ✅、全仓退出码 ❌（12+ 处输入类仍用 rc=1）。逐项修复：

| 返工项 | 文件 | 内容 |
|---|---|---|
| ⑤ **删 inspect 旧裸块** | `ftth.py` | 九十八加守卫块时漏删 L981-982/L996-997 两个旧 `isfile` 块 → stale 经旧块照样传入（守卫 WARN 形同虚设）+ 本轮产出时 --coverage/--titleblock 双传。**已删**，只保留守卫块。 |
| ⑥ **补 _fxmap_produced** | `ftth.py` | `_bmap` 原用 `_fx_run and isfile`（gate 决定跑≠跑成功）→ fxmap 失败时旧残留照喂 parse --bldg-map。**加产出标志**（rc==0 置 True），`_bmap`/unit_gaps `--fx-map`/残留 WARN 全改吃该标志。 |
| ⑦ **全仓输入类 rc=1→2** | 7 个脚本 | parse_dxf_structured（5 处：楼栋标题未匹配/--fx-map/--bldg-map 不可读与格式错）、analyze_coverage（1 处：对照表不可读）、analyze_coverage_vshape（2 处：标题未匹配/--fx-locations 不可读）、gen_addressbook（3 处：dxf_json 不存在与不可读/coverage_json 不可读）、extract_fx_locations（1 处：标注未匹配）、verify_coverage_truth（2 处：空表/缺列）、read_titleblock（1 处：容差量不出）。**保留 rc=1**：写盘失败、DXF 读取崩、缺依赖（xlrd/openpyxl）、read_titleblock L822 排版自相矛盾（2026-09-18 已裁定为图面质量问题）。 |
| ⑧ **count_box DXF 指纹校验** | `ftth.py` | 新增 `_cb_fingerprint_ok()`：复用前比对产物「输入」字段（count_box_icons.py 写的完整 DXF 路径）与当前 dxf 的 basename；不匹配 → 不复用 + 显式提示 + fresh-run 重算。同 outdir 换图重跑不再静默喂错户数。 |

**opencode 审核意见中未采纳 1 项**：read_titleblock L822（ToleranceEstimateError 排版自相矛盾）保留 rc=1 —— opencode 建议"一并归入 2"，但该处有 2026-09-18 的明确裁定注释（排版自相矛盾=图面数据质量问题，与输入不足是两回事），尊重既有设计决定。

**opencode 二审返工（2026-09-25，第 4 轮，修复回执复审）**：

opencode 复审上表 4 项修复回执后判定：❌-1/❌-2/指纹校验 ✅到位、L822 保留 ✅同意（三态区分注释链完整），但**rc 修正不算全仓闭环 —— 6 文件 9 处输入类遗漏**（上轮两轮均未覆盖的次级脚本）：

| 文件 | 位置 | 内容 | 修法 |
|---|---|---|---|
| `count_households.py` | :164 | 楼栋未匹配 | →2 |
| `probe_titleblock_tolerances.py` | :127/:139 | DXF 不存在 / 图层不存在 | →2 |
| `merge_json.py` | :44/:48 | 缺参 / 未找到输入 | →2 |
| `split_units.py` | :48/:56 | 输入 JSON / 规则 JSON 不可读 | →2 |
| `ledger_elements.py` | :135/:251 | 图纸不存在 / 正则编译失败（参数写错） | →2 |

**全仓终扫分类（修复后）**：剩余 rc=1 全部合理保留 —— 写盘失败 7 处（analyze_coverage:1524 / parse:2132 / gen:654 / extract_fx_map:445 / count_households:413 / merge_json:146 / split_units:150）、DXF 读取崩 7 处（ftth_common×4 / count_box_icons:575 / probe_tb:132 / read_titleblock:780）、缺依赖 3 处（xlrd / openpyxl / count_hdd:22 垫片）、**守门拦截 2 处**（read_titleblock:822 排版矛盾 / count_households:405 有损结果守门——拒绝不可信结果出表，与"输入不足"是两回事）、误报 4 处（vshape:179 单元号返回值 / read_titleblock:399 比较器 / ftth_batch:451 部分成功 / inspect:169 注释文本）。

**三审返工验证**：5 个改动脚本编译全绿；冒烟 ALL PASS；凤鸣 parsed/coverage MD5 与基线逐位一致（cc88…/6cc2…）；budget rc=0。

**opencode 审核返工验证**：
- 编译：8 个改动脚本全绿（ftth/parse_dxf_structured/analyze_coverage/analyze_coverage_vshape/gen_addressbook/extract_fx_locations/verify_coverage_truth/read_titleblock_households）。
- 凤鸣：parsed/coverage MD5 仍与基线逐位一致（cc88…/6cc2…），inspect rc=0。
- 云峰指纹链路：匹配 → 复用（0.00s）；不匹配 → 提示"指纹不匹配（产物是另一张图的户数）"+ fresh-run 重算（14.58s）+ wire-layer 透传。
- 冒烟 ALL PASS；budget rc=0。

**备份**：`.temp/ftth_bak_20260925_195520_review2/`（11 个文件，改动前快照）。

**opencode 终审返工（2026-09-25，第 5 轮，SystemExit 隐式 rc=1 家族清查）**：

opencode 终审指出：前四轮退出码修正均以 `sys.exit(1)` 为扫描模式，遗漏了 `raise SystemExit("字符串")` 家族——Python 对字符串参数的 SystemExit 隐式取 rc=1，与 L1-C2（rc=2=输入不足/须修）不符，且 `grep sys\.exit\(1\)` 扫不到。全仓按 `raise SystemExit\(` 模式复扫，分类处置：

| 文件 | 位置 | 原 `raise SystemExit("…")` | 改法 |
|---|---|---|---|
| `split_bands.py` | parse_bands :63/:68/:70/:72/:75 + main :94/:179/:181/:198/:201/:203 = 11 处 | --band 格式/数值/名称/区间校验、--config 不存在、DXF 不存在、--auto 与 --band 互斥、--yes 缺 --out-dir、缺 --band/--auto、--band 缺 --out-dir | 新增 `_fail(msg)` 辅助函数 → `sys.exit(2)`（消息仍打 stderr，行为与原 SystemExit 一致） |
| `parse_dxf_structured.py` | :147 | 参数自检：正则捕获组不足（编译通过但解析期 `group(n)` 会 IndexError） | `sys.stderr.write` + `sys.exit(2)`（与文件内已有 rc=2 风格一致） |
| `gen_9level_addressbook.py` | :170 | `--addr` 非 5 个逗号分隔值 | `print(file=sys.stderr)` + `return 2`（入口 `sys.exit(main())` 透传） |
| `read_titleblock_households.py` | :278 | 图签层内未同时找到楼名与层户标注（消息明确「请用 --bldg-re / --lev-re 校正正则」=参数可修） | `print(file=sys.stderr)` + `return 2`（入口 `sys.exit(main())` 透传） |

**刻意保留 rc=1（2 处守门拦截，非参数类）**：`gen_9level_addressbook.py:214` 守恒校验失败（行数≠应有，拒绝不可信结果出表）、`read_titleblock_households.py:163` 归并楼号冲突（需人工处理）——两者均「确实有问题/需人工介入」，与「输入不足·须修」是两回事。

**与 rc=3 出口的分工确认**：`read_titleblock_households.py` L824 `[SKIP] rc=3`（本图整体不适用——estimate_tolerances 返回 None）是更高层设计出口，与 L278 的 rc=2（层内未找到标注、参数可修）分工不冲突——实测空层场景走 L824 rc=3（正确），L278 为量测成功后的次级检查（边缘路径，语义正确、透传安全）。

**验证**：
- **编译**：4 个改动脚本 `py_compile` 全绿。
- **退出码行为**（经 ftth_launcher.py，8 用例）：T1 DXF 不存在 / T2 --auto 与 --band 互斥 / T3 无 --band 无 --auto / T4 --band 格式错 / T5 ymin≥ymax / T6 --addr 格式错 / T7 捕获组不足 → 全部 rc=2 ✓；T8 空层 → rc=3（走 L824 SKIP 分支，设计正确）。
- **凤鸣 MD5 回归**：pipeline --stop-at coverage --reuse-geom --quiet，parsed.json `CC88…E3B` / coverage.json `6CC2…7AB` —— 与基线逐位一致，零差异。
- **全仓复扫**：`raise SystemExit\(` 仅剩 3 处——2 处刻意保留守门 + 1 处 `_fail` docstring 提及（非代码）。

**备份**：`.temp/ftth_bak_20260925_210944_review3/`（4 个改动文件终审返工后已验证快照；上轮中断时改前快照遗漏，此处补已验证状态作回滚锚点）。

- **版本**：`version.json` 0.97.0 → **0.98.0**（minor 位对应修订序号九十八）。
- **版本（·补）**：`version.json` 0.98.0 → **0.98.1**（patch 位对应九十八·补：SystemExit 隐式 rc=1 家族清查）。

### 2026-09-25（九十七）：pipeline 自动衔接 count-box + 文档同步 + 交付水印说明（三项目实跑驱动）

**实测动因**：深度检查（凤鸣朝阳/云峰/柳辛庄三项目实跑）发现画像 handoff 早在 plan 阶段就申报「每层户数=图标法（count_box_icons.py）」（云峰实测 13s 时已申报），但 `_PIPE_STAGES` 没有 count_box 阶段 —— 跑完整链（137s）后 inspect 的 C5/C8 才以 SKIP 提示「户数须由图标法提供」，用户还得手工补 count-box 再重跑 inspect（9/18 云峰留有 count_box.json / count_box_fixed.json 两轮手工痕迹）。「规则写在文档里、没有代码执行」—— 与 ③b titleblock、④b fx_locations 同一形态。

| 改动 | 文件 | 内容 |
|---|---|---|
| ① **P0 pipeline 自动衔接 count-box** | `ftth.py` | `_PIPE_STAGES` 新增 `count_box`（coverage 与 inspect 之间）；新增 `_pipe_countbox_choice(prof)` 辅助函数，**仅当画像申报每层户数脚本 == count_box_icons.py 时执行**（方法池同级，不替画像择法）；rc=2（输入不足）中止主链、rc=3（本图不适用）继续 —— 与 parse/coverage 同语义；count_box.json 已存在时**复用优先不重算**（尊重手工调参产物，与 count_box_icons.py 自身写保护一致）；产物落盘后 ⑦ inspect 已有的「outdir/count_box.json 存在即自动纳入」逻辑即刻生效 |
| ② P1 脚本数统一 | `SKILL.md` / `README.md` / `references/scripts_reference.md` | 三处写死的脚本数（27 / 31 / 31）统一为实测 30 个 `.py`（`ls scripts/*.py` 实测；scripts_reference 自身约定「数量按实测填写」） |
| ③ P1 交付水印说明 | `references/addressbook_template.md` + `gen_addressbook.py` | 新增「回读校验与 AIGC 水印行」小节 + gen 成功输出追加「交付提示」行：宿主对 .xlsx 自动追加 AIGC 水印行（实测凤鸣朝阳：生成 315 行 → 桌面 317 行），属系统预期行为，不是数据错误；统计户数按「楼栋列非空」过滤即可天然排除 |
| ④ P2 interpreter_cache 说明 | `README.md` | scripts/ 行补注：运行生成 `.interpreter_cache.json`（`.gitignore` 已忽略，可安全删除，删除后下次启动重探一次） |

**认知修正（P2 配套楼单元键退化）**：深度检查报告原列「配套楼单元键退化需显式提示」为 P2 建议项；复核云峰 inspect C1 日志发现，**该机制已存在** —— C1 的 `is_bldg_level_container` 判据对单元键==楼栋键的情况已打印「另有楼栋级兜底容器「X#楼」：承载单元号对不上的箱，已登记需人工裁决，不计入单元数」（云峰 11 栋全覆盖）。此为「已验证良好」项，不做代码改动。

**验证（三项目实跑 + 冒烟 + 体量）**：
- **云峰**：count_box 自动触发（10.13s，rc=0），count_box.json 落盘，inspect count_box 字段已指向产物；已存在时复用路径正确（「复用已有 count_box.json —— 手工调参产物优先不重算」）。
- **凤鸣朝阳**：画像申报 parse 直读 → count_box rc=3 跳过（理由打印「画像申报每层户数脚本=parse_dxf_structured.py（非图标法）」）；parsed/coverage/titleblock 三产物 MD5 与改动前**完全一致**（CC88...E3B / 6CC2...7AB / 654B...72F），inspect rc=0 FAIL 0 WARN 3（与历史一致）—— 回归零差异。
- **柳辛庄 1-4**：parse rc=2 中止路径不变（8 阶段停，count_box 阶段未执行，无副作用）。
- **停点边界**：`--stop-at count_box` 跑到 count_box 后正确停止，inspect.json 未被改写。
- **冒烟**：`tests/run_smoke.py --with-dxf` **ALL PASS（T0~T13 失败 0 项）**，exit=0。
- **体量**：`ftth.py budget` rc=0；SKILL.md 46687 B（距预警线 313 B，"27→30"字节数不变）；addressbook_template.md 4196 B（references 预警线内）。
- **编译**：`-W error::SyntaxWarning -m py_compile` 对 ftth.py / gen_addressbook.py 全绿。

**评审返工（2026-09-25，评审驱动 6 项）**：

| 返工项 | 文件 | 内容 |
|---|---|---|
| ① .gitignore 补条目 | `scripts/.gitignore` | 新增 `.interpreter_cache.json`；README 同步改为「已加入 `scripts/.gitignore` 忽略；上架打包前建议手动清理」（原文写「.gitignore 已忽略」但两份 .gitignore 均无该条目 → 失实） |
| ② README 版本号 | `README.md` | 0.95.0＝九十五 → 0.97.0＝九十七 |
| ③ pipeline 阶段链同步 | `SKILL.md` / `scripts_reference.md` / `pipeline_details.md` | 5 处旧阶段链（7~10 阶段、缺 count_box 等）统一为 `_PIPE_STAGES` 全 11 阶段；scripts_reference「串跑 8 个阶段」→「11 阶段」 |
| ④ inspect stale 文件污染 | `ftth.py` | inspect 阶段仅当本轮 `_cb_run=True`（画像确为图标法）才传 `--count-box`；画像非图标法但残留文件存在时 WARN 提示删除，不静默消费（评审残留风险1） |
| ⑤ fresh-run 未调参提示 | `ftth.py` | count_box fresh-run 成功后打印「未调参版（仅自适应量测）；若 C5/C8 户数与图面不符，请手工补跑 `ftth.py count-box --col-scale-map ...`」提示（评审残留风险2） |
| ⑥ C6 水印行指针 | `SKILL.md` | C6 回读校验条补 1 行指向 `addressbook_template.md §回读校验与 AIGC 水印行`（评审指出 Step4/C6 只字未提水印） |

**P2 fxmap 缓存：显式延期**。深度检查报告列为 P2 性能项（~30s/次大图），本次未实施，不改代码也不改文档 —— 属已知可优化项，待后续修订单独落地（若实施需 dxf 指纹校验 + fxmap.json 格式约定，改动面中等）。

**备份**：`.temp/ftth_bak_20260925_182954/`（9 个文件，含 ftth.py / gen_addressbook.py / inspect_closure.py / SKILL.md / README.md / addressbook_template.md / scripts_reference.md / SKILL_CHANGELOG.md / version.json 的改动前快照）。

- **版本**：`version.json` 0.95.0 → **0.97.0**（minor 位对应修订序号九十七；九十六未 bump，本次一并补到位）。

### 2026-09-25（九十六）：启动器解释器缓存 + 探测超时 120s + 裁决批量落盘（凤鸣朝阳实跑驱动）

**实测动因（非设计偏好）**：某 Windows 主机 `import ezdxf` 单次 24~52s（user CPU<0.1s，全为进程冷启动/杀软扫描的 I/O 等待），且**冷热不稳定**。原探测 `timeout=30` 恰好卡在耗时边界 —— 同一天 12:38 pipeline 探测通过、12:56 同一命令探测全失败（rc=9，整链 2m43s）；`FTTH_PYTHON` 设了也每次照付探测成本（实测链式 5 条调用 5m35s，均摊 ~56s/条）。

| 改动 | 文件 | 内容 |
|---|---|---|
| ① 探测超时 | `ftth_launcher.py` | `_ezdxf_ok` timeout 30→120s（远大于实测上界 52s，消除边界抖动） |
| ② 解释器缓存 | `ftth_launcher.py` | 探测命中后写 `scripts/.interpreter_cache.json`（exe + `ezdxf.__file__` + extra_args）；复用时仅两条 `isfile` 校验（0 成本），任一消失即自动重探。探测成本 N 次→1 次（实测命中后启动开销 28s→仅剩业务进程自身 import，属必付成本） |
| ③ 批量裁决 | `ledger_state.py` | `ruling-add --from-json <file>`：JSON 数组 `[{"question","ruling","by"?,"scope"?,"key"?},…]`，`--by` 作条目缺省；一次调用落盘 N 条。实测 4 条裁决 5×56s → 1×28s。单条模式不变（回归通过） |
| ④ 失败提示 | `ftth_launcher.py` | rc=9 提示语补缓存清理办法 |

**冒烟（8 用例真机全过）**：冷启动探测+缓存落盘 / 未初始化 rc=3 / 缓存命中提速 / 批量落盘（默认 by + 条目覆盖）/ 零输入守卫 rc=3 / 坏 JSON rc=3 / 单条模式回归 / 真实台账回归。

**配套建议（未实施，属系统层）**：该主机 import 慢疑与杀软实时扫描相关（每进程 ~10s 基线 + ezdxf 目录扫描 ~15-20s），可评估将 Python 安装目录加入杀软排除项；本技能不做任何杀软/系统改动。



- **背景（上架禁令）**：技能市场导入检测到不允许的文件类型 `scripts\ftth.cmd`
  （扩展名 `.cmd` 禁止导入），技能无法上架。这是唯一触发点；清理后 `scripts/`
  仅剩 `.py`，不再含任何可执行脚本/编译产物。
- **改动①（新增）**：`scripts/ftth_launcher.py` —— Python 版统一启动器，**功能等价**
  于原 `ftth.cmd` + `_launch.py` 的合并：
  - 解释器探测候选顺序不变：`FTTH_PYTHON` → 当前解释器 → 常见安装路径
    （LOCALAPPDATA/ProgramFiles/SystemDrive 下 Python311~313）→ `py -3.13/-3.12/-3.11/-3`
    → PATH 上的 `python`；全部**真实执行** `-c "import ezdxf"`（不按路径猜）。
  - 参数分派不变：首参以 `.py` 结尾即转发该脚本（`scripts/` 前缀可写可不写），否则
    转发 `ftth.py <首参> ...`。
  - 退出码契约不变：透传目标退出码；全部候选失败 → rc=9 并打印处置办法。
  - 附带收益：参数经 subprocess 直接传 argv（不经 shell），原 cmd.exe 吃正则 `|`
    的旧坑（extract_fx_map 曾踩）随旧启动器一起消失；入口 `python` 无需带 ezdxf
    （启动器自身只 import os/subprocess/sys），「禁止裸 python」对启动器入口豁免、
    对业务脚本仍严格。
- **改动②（删除）**：`scripts/ftth.cmd`、`scripts/_launch.py`、`scripts/__pycache__/`
  （30 个 .pyc 运行产物）全部移入回收站。
- **改动③（调用命令全量同步）**：`& "<技能目录>\scripts\ftth.cmd"` →
  `python "<技能目录>\scripts\ftth_launcher.py"`。落点：SKILL.md（C7 契约表、
  Step 1a 示例、Step 1b 说明）、README.md（8 处）、references/scripts_reference.md
  （解释器契约整章重写 + 示例）、references/titleblock_and_intake_table.md、
  references/coverage_rules.md、references/pipeline_details.md（注明旧数据为旧 cmd
  启动器实测）、version.json（runtime_note）、requirements.txt、scripts/ftth.py /
  ftth_batch.py / extract_fx_map.py 注释与 example。
- **改动④（版本）**：`version.json` 0.91.0 → **0.95.0**（minor 位对应修订序号九十五；
  九十三、九十四 未同步 bump，本次一并补到位并在 `skill_version_basis` 注明）。
- **验证（本机实测）**：经被劫持的 TeleAgent runtime（无 ezdxf，Python 3.12）调用
  启动器，全部通过 —— `--help` 子命令转发 rc=0、`dump_geom.py --help` .py 转发
  rc=0、`budget` rc=0、不存在脚本 rc=2、未知子命令 rc=2、`FTTH_PYTHON` 指向无
  ezdxf 解释器时自动回落 rc=0；`-W error::SyntaxWarning -m py_compile` 全绿。
  冒烟（tests/run_smoke.py --with-dxf，主 Python 3.13 实测）：**ALL PASS（失败 0 项）**，
  T0~T13 全绿，exit=0。
- **上架遗留提醒**：① 技能自带 `.git/` 目录，上架打包时须排除；② 任何一次本机
  运行都会再生 `scripts/__pycache__/`，上架前清理或确认打包器忽略（.gitignore 已
  忽略，入库不受影响）。

- **坑4（P0，判据用错范围却逐组弃解）**：格组归属的**前提**是「每个格组所在那一行有它
  的楼名锚点」。前提不成立时，逐组判「不采信」＝把一整批标注**因一个用错范围的判据
  丢出成品**。实测凤鸣朝阳小区：图签 12 个单元格里**仅 1 个**能被楼名认领（8%），
  其余 11 组被判「不落盘」。
  根因（取证：BZ 图层文字转储）：该图图签的楼名写成**多栋合并**
  （`1#楼，2#楼` / `3#楼，5#楼` / `6#楼,7#楼,`），`bldg_re.fullmatch` 要求「整条＝单个
  楼名」故**全不认** ⇒ 图签单元格**零锚点**；判据抓到的 7 个锚点实为**系统图内的单栋
  标签**（离最近格组 362.2~425.0，方向纯横向），全部被**尺度闸**拦下。
  而该图 **C10 实测 PASS**（图签 vs 系统图逐栋 7 栋一致）⇒ 信息另有来源，
  此处纯属**判据用错范围**，不是数据丢失。
- **修法**：① `assign_cells_to_buildings` 新增 `applicability_min=0.5` 认领率闸门 ——
  `采信组/总组 < 0.5` ⇒ 整体判**不适用**：`owner`/`blocked` 置空、**全部**标注交回
  逐标注判据，并在裁决记录里留 `适用`/`不适用原因`；调用方据此**不得**再逐组打印
  「不采信 / 不落盘」（那是误判范围）。返回结构额外给出 `适用`/`不适用原因`。
  ② 新增 `collect_multi_bldg_labels(texts, bldg_re_src)`：把「匹配楼名正则但不
  fullmatch 且含分隔符」的文字**只登记不解析** —— 拆分会把单元挂到错的楼栋
  （分隔符集：`，,、;；`／`~～`／数字-数字）。调用方新增 `[图签·多栋合并楼名]` 登记段。
  ③ 日志新增 `[格组·不适用]` 分支，与逐组裁决**互斥**。
- **阈值实证（为什么取 0.5）**：柳辛庄 band1~band4 认领率 6/6、14/14、18/18、5/6
  （**最低 83%**）；凤鸣朝阳 1/12（**8%**）。50% 落在两者之间且**远离两端边界**。
- **行为变化（如实记录，勿读成回归）**：凤鸣朝阳 `未匹配到层户的单元标注数` 由
  **0 → 12**。原因：那 11 条原先在 `_cell_blocked` 分支被**提前 continue** 吞进
  另一个桶（`[格组·不采信]`），根本走不到 `not cand` 分支，故「未匹配」恒为 0 ——
  **0 是假象**。关掉格组后 12 条全部如实登记为未匹配。
  自证：24 条单元标注 = 落格 12 + 未落格 12；未落格那 12 条命中容差窗，去重后编号数
  恰为 1 + 2×5 + 1 = **12**，与 7 栋汇总表、质量报告「单元24」严丝合缝。
  唯一代价：`[格组·补判]` 少救 1 条，但该条与已有标签**重复**（`8号楼 1单元×2`），
  编号去重后单元数不变（仍为 1）⇒ 净损失 0。
- **验证**：凤鸣朝阳 `pipeline` rc=0；C10 **PASS**（7 栋一致）；修复后连跑三轮
  （run2/run3/run4）stdout 行为差异 **0 行**，`titleblock.json`/`parsed.json`/
  `coverage.json` 三方 md5 **完全一致**（`inspect.json` 差异仅为内嵌产物路径）；
  FAIL/WARN 0/2 不变。柳辛庄 band1~band4 逐行**零行为变化**（唯一差异为"合计 Xs"耗时行），
  认领率均 ≥83% **未触发闸门**。冒烟 **ALL PASS**：新增 T12（认领率过低须整体判不适用
  且不弃解；反向达标须照常适用落盘；偏置认领须留痕；拒绝须来自优势闸而非尺度闸）
  与 T13（多栋合并楼名须登记、单栋楼名与非楼名文字不得误收）。
- **测试自身的坑（记以防再犯）**：T12 初版把合成锚点放在 `x = -_CW`（整整一格宽之外），
  `d1 = 59020.5 >` 一格高 45041.3 ⇒ **先被尺度闸拦下**，两支撑均采信 0 组，
  测的其实是另一条路。修法：偏置改为格宽的 **3.4%**（`_OFF12 = 2000.0`，对齐实测
  band2 的 3.2%），既落在格 x 跨度之外、又在尺度闸内。另修一条**空真**断言：
  原用 `all(... for _s in unclaimed)` 而该场景 `unclaimed` 为空 ⇒ 恒真，等于没测；
  改为构造**等距歧义锚点**（y 取两行正中）使 `unclaimed` 非空后再生效。
- **备份**：`WorkBuddy/2026-09-23-12-44-53/.audit/backup_ftth_skill_20260923_1346`
  （本轮修复**前**状态，已复核 `applicability_min` 出现 0 次、当前源 5 次）。
- **路径备忘（避免后人误判"改的不是跑的那份"）**：
  `~/.workbuddy/skills/ftth-address-extractor` 是指向
  `~/.config/TeleAgent/users/v1_public_1903017811319390212/skills/ftth-address-extractor`
  的**符号链接**（`ftth_common.py` md5 两侧一致），两处是同一份。

### 2026-09-23（九十三）：图签格组归属族修坑 —— 柳辛庄 band1~band4 实跑（含真丢解一例）

- **坑1（P0，真丢解）**：格组归属把「楼名 x 必须落在格组横向跨度内」当**硬闸**，
  无覆盖即判「退让认领 → 不采信」，而不采信**禁止回落逐标注** ⇒ 整行 `N单元`
  全部不落盘、图签侧该栋**单元数丢成 None**。实测 band2 `4#楼`：楼名画在本行格组
  左边界**之外** 3813.2（格宽 118040.9 的 **3.2%**，两份拼版一致），到本行 11167.5、
  到次近格 26201.1（**优势 2.35 倍**）—— 证据充足却被闸掉。修法：无覆盖分支不再弃权，
  改为「最近格 + 优势闸（`d1 ≤ dominance×次近格`）」**采信并登记** `offset_claims`
  （与 `unclaimed` 分开呈现：一个是已落盘但依据弱，一个是压根没落盘）。
  **优势闸只许用于缺结构证据的分支**：有覆盖的支路若也叠加，本行偏移 17705.8 /
  上一行底边 23361.2（行距 41067）会让该行**永久**判「优势不足」（band4 `2#楼` 正是此值）。
  B 步同时删掉「胜者未横向覆盖即不采信」，把该事实降为裁决记录里的一个字段。
- **坑2（P1，证据失真）**：`collect_titleblock_unit_cells` 的「落格」原口径是
  「落在**任意矩形**里」⇒ 只落在图框内的标注被计成已核。实测 band1：20 条里
  **8 条**只落在 585000×430500 的**图框**内（该处根本没有单元格），旧口径报
  「落格 20 / 未落格 0」。修法：「落格」只算**主尺寸族**（单元格），原始计数另存
  `落入任意矩形标注数` 供诊断 —— 「没核」不得呈现成「已核」。
- **坑3（P2，原因标错）**：未认领锚点一律打印「优势不足」，实际原因是**超尺度闸**；
  措辞改为「逐条原因见下」并补锚点坐标。
- **验证**：band1~band4 `pipeline` 全 rc=0；band2 采信 12→14、不采信 2→0、
  图签 `4#楼 单元数 None→2`、C10 可比楼栋 3→7；band1 落格 20→12；
  **band3/band4 逐行零行为变化**；FAIL/WARN 四地块计数不变（11/11/16/7）。
  第二来源：band2 `4#楼` 系统图侧 2 单元（C1）＝图签侧 2（C10 判定可比一致）。
  幂等复跑（同码同输入两轮）行为差异 **0 行**。冒烟 T7~T11 全 PASS（新增 T11：
  偏置但优势明确须采信 / 偏置且优势不足须不认领，并反向验证拒绝来自优势闸而非尺度闸）。
- **备份**：`WorkBuddy/2026-09-23-12-44-53/.audit/backup_ftth_skill_20260923_1346`
  （92/92 文件 md5 逐个一致，BACKUP_OK）。

### 2026-09-22（九十二）：coverage待裁决同单元双条去重 —— 2块地实测

- **Bug**：`analyze_coverage_vshape.py` 同一单元在缺箱时登记两条（配对循环内
  「V 段数多于箱数」＋循环后「V段数与箱数不一致」，后者信息为前者超集）。
  band2 实测 14 项里 7 组是同一句话的复制；band1（1块地）13 项同理。
  0186 去重只杀完全相同的 JSON，杀不掉这种语义重复。
- **Fix**：配对循环内缺箱只 `break` 不登记，统一由循环后一条登记（含谷底明细）；
  零箱时说明追加一句「窗口内无箱号锚（箱编号在布线图区，属图纸固有分离；
  V段仅输出覆盖线索，箱配对见parse侧）」。仍列待裁决、不静默放行（L0-I4）。
  只改登记，不改任何测量值与配对算法。备份：
  `WorkBuddy/backup-ftth-skill-20260922_082751_pre_coverage_dedup/`（4 文件 sha16 逐个核对一致）。
- **验证**：band2 pipeline rc=0，coverage待裁决 14→7、C7 14→7，parse 7栋24箱、
  V谷底/米数表逐字不变；band1 回归 rc=0，C7 13→7（含超邻域箱锚1条保留），
  parse 5栋22箱、V谷底不变。已锁 R010-R016 值不受影响。

### 2026-09-21（九十一）：图签单元归属块方向自判 —— band2-5# 现场复核修假矛盾

- **Bug**：单元标注 → 层户配对的单点「最近者胜」无块方向概念。容差窗上下都大
  （柳辛庄 band2：unit_dy_lo=-88518/hi=108919）而楼块纵向间距仅 ~80k 时，行间标注恒
  命中上下两块；按 |dy| 必偏向行下方的楼块 ⇒ 整列系统性下判一行。band2 实测：
  上行（1#/2#/3#）→4#/5#、中行（4#/5#真值）→6#/7#，5# 收「1单元×4」、1#/2#/3#
  零标签；C10 据此报「图签1 vs 系统2」假矛盾（用户肉眼＋箱位直读＋系统图三方均为
  2 单元；直查 geom 落盘证实 24/24 采全、"2单元"文本存在，采集层无罪）。
- **Fix**（`read_titleblock_households.py`，用户已裁定实施）：两遍式——第一遍只收集
  候选；用窗内仅一栋候选的无歧义标注自判本图方向（dy＝层户y－单元y；dy>0 恒成立⇒
  块底式，反之块顶式；需 ≥3 条且一致率 ≥0.8，否则不锁定、行为与旧版逐位一致）。
  锁定后歧义标注优先同向候选、同向内仍按 (|dy|,|dx|) 最近；无同向候选则回退旧规则
  并在歧义记录加「方向回退」键（加法字段，消费方 .get 兼容）。备份：
  `桌面/柳辛庄/.temp/run20260921_fresh/backup/read_titleblock_households.py.bak_20260921_pre_blockdir`。
- **验证**（fresh 重跑，不读历史；titleblock_fix1.json＋inspect_fix1.json 落各带目录）：
  band2 锁定块底式（8/8）→ 5#=1×4 重复消除、5#=[1,2]、1#=2/2#=1/3#=1 全填上，
  C10 FAIL 2→WARN（rc=2→0）；band1 锁定块底式 → C10 维持 WARN（未核 7→5 处），零回归；
  band4 证据不足不锁定 → 与旧版逐项一致（FAIL 0/WARN 10），零回归；
  band3 锁定块底式 → 修好 2#（∅→[1,2]，对上箱位）与 5#（[1,2]→[1]，对上箱位），
  但 7# [1,2]→[2] 转响：`[8224259,-8721309,1单元]` 是 2# 与 7# 唯一的"1单元"来源
  （零和，不可约——每幅"1单元"少一条），旧版静默饿死 2#（∅），新版交 C10 待裁决。
  静默错→响错是本技能要的方向（L0-I4），但 7# 归属仍需人眼裁定。
### 2026-09-20（九十·补）：图签单元归属消歧改按行（dy 优先）—— 柳辛庄 R1 实测

- **Bug**：单元标注 → 层户配对的「最近者胜」度量为 `(|dx|,|dy|)`。单元列相对层户列
  在 x 上有系统性偏置（60~110k），同行格子 Δy 仅 ~400（同刻度线）—— x 最近 ≠ 同行。
  实测：band3-3# 行同线 `2单元`被判给 6#（离 6# 另一格 108k）；band2 把 4#/5# 行的格子
  划给 100k 开外的 1#/2# 列（用户现场质疑 3#/7# 读数后逐坐标取证确认）。
- **Fix**：度量改为 `(|dy|,|dx|)`（行身份由 y 决定）；仍是最近者胜，单候选零回归；
  歧义逐条留痕（R4 机制）不动，以此 diff 复核。
- **验证**：用户地面真值 band3（3#=2 / 7#=2 / 4#=1）全中；band2 下线符合列模型＋双像对称；
  band9-2-11# 由 `[2]`→`[1,2]`，恰对上系统侧 2 单元。
  已知转移：band3-6#（2→1）转成新 C10，待用户裁定（标签零和，无中生有不得）。

### 2026-09-20（九十）：体量拆分/冒烟编码/1单元回退收紧/刻度兜底可见性/死码删除

- **体量（P0，新瓶颈）**：`scripts_reference.md` 达 48,915 B（距硬上限仅剩 85 B，budget 二次信号）
  → §流水线 pipeline 逐字外移 `pipeline_details.md` §18（原地留指针，`## 流水线` 锚点仍可达），
  回落 45,843 B [OK]；SKILL.md 参考表行同步加“流水线串跑入口”。12 个 references 全回预警线内。
- **冒烟编码**：`run_smoke.py` 5 处 `subprocess.run(text=True)` 补
  `encoding='utf-8', errors='replace'`（中文 Win 默认 GBK 解码曾炸三 reader 线程，
  输出截断则后半截门禁全跳过）；有 openpyxl 的解释器上 T6 gen 由 SKIP 转 PASS
  （另含 T5 真语料 probe），双解释器（有/无三件套）均 ALL PASS。
- **1单元回退收紧（现场复核 P1）**：`assemble_households.py` 合并回退与 229 告警抑制
  同条件收紧为“仅单单元楼”（该楼栋组装结果仅含 1单元）；多单元楼错键不再静默并入
  1单元，改记未匹配清单 + 显式打印（合并点与告警点须同条件，否则一边并入一边告警）。
  单单元行为不变（`('4',bkey='4')` 仍落 1单元，仅多一条回退打印）。一次性脚本验证 7 项全过。
- **刻度兜底可见性（pick_scale）**：无 y 完全覆盖列而走 ③/兜底时记入清单，主循环后统一打印
  `!` 块（只加可见性，不改挑列结果；真错配仍由偏移异常/共用刻度列两门禁 + 人工
  `--col-scale-map` 裁决）。云峰全图实跑：各列均有完全覆盖列，新块静默（符合预期），
  既有 4 列偏移异常 + 5 组共用刻度列告警逐字不变，产物正常落盘。
  完整方向约束仍延期（需多图回归语料护航，延续八十九观察项口径）。
- **死码删除（P1-5 闭环）**：`ftth_common.write_text` 经全仓 import-aware 复核确认零引用
  （跨文件 0、同文件 0；`plan_methods.py:2096` 的 `out.write_text` 是 pathlib 方法，无关）
  后删除，留墓碑注释。八十九“未删任何函数”（当时 11 个全活）与本次不矛盾。
- **验证**：冒烟 ALL PASS（双解释器；有依赖机含 T5 + T6 gen）；`ftth.py budget` rc=0；
  云峰 `count-box` 全图重跑：门禁、偏移/共用告警、产物均正常；改动脚本 py_compile 全过。

### 2026-09-19（八十九）：代码质量审计整改 —— EOL/体量/依赖/归一/冒烟/备份（桌面评估报告逐条落地）

- **EOL（P0-1）**：新增 `.gitattributes`（`* -text`；`*.cmd/*.bat` 强制 CRLF ——
  `ftth.cmd` 入库 LF，fresh checkout 若跟随 `-text` 会变纯 LF，cmd 解析不可靠）；
  SKILL.md / scripts_reference.md / measurement_methods.md 归一 LF
  （SKILL.md 48979→48532；MIXED 5 行并入）；`check_budget.py` 输出换行风格与
  LF 归一字节（信息位，不改判罚）＋距硬上限不足 1000 B 二次信号（rc 不变）。
- **SKILL.md 瘦身 2290 B**：只压探查/出表两处散文重复（规范句、钩子、命令块全留），
  48532→46242，状态回 [OK]（距预警 758 B、距硬上限 2758 B）。
- **requirements.txt**：实测锁定 ezdxf==1.4.4 / openpyxl==3.1.5 / xlrd==2.0.2
  （全仓 import 扫描：无 matplotlib 引用）。
- **norm_unit 统一（P2-3 升级）**：apply_ruling / gen_addressbook 改走
  `unit_num` 唯一入口（ASCII 行为不变，中文单元写法新兼容）；
  gen_9level 刻意不动（零依赖设计，unit_label 仅显示且吃不到全名键）。
- **auto_scaled 上收（P1-4）**：analyze_coverage / count_box_icons 逐字相同 4 行并入
  `ftth_common.auto_scaled`（比率表仍各带，ratios/fallback 强制关键字传参）；
  云峰 r4verify 全链重跑四产物哈希与 r3 逐键一致，零行为差。
- **冒烟 T0+T6**：全仓 py_compile；出表链黄金路径（合成料：全名单元键+中文单元+
  共享克隆 → assemble/apply/gen），专杀八十八双 P0（已用备份旧实现做反向验证：
  旧实现必崩/错归位，新用例必拦；守恒通过不代表对位，箱对位断言才是真守卫）。
- **`.backup` 迁出**：`skills/.backup/ftth-address-extractor`（211 文件/6MB，09-18 旧版）
  移至工作区带时间戳目录，数量字节双向核对一致，源已空。
- **吞异常复核（P1-7 启动）**：ftth_common:425（控制台兜底，有文档，留）；
  ftth_common:1492（落 None 约定，调用方按未测得处理，留）；
  analyze_coverage 符号循环双裸 pass 改计数＋汇总 warning（行为不变，只加可见性）。
- **P1-5 纠偏**：split_ruling_object / parse_ruling_scope / build_fx_direct_evidence /
  ensure_parent 均活着（懒导入/同文件链/传递调用），**未删任何函数**；死代码判定须
  import-aware 重做。
- **有意未动**：巨函数拆分（需语料回归护航，先立项不拆）；P2-2 日志体系；P2-4 文件改名
  （动文件名牵连 ftth.py 分发＋文档链）；P2-5 信号数历史（不改历史，待原作者确认）；
  pick_scale 方向约束（已知失效形态，人工 map 流程保留，记观察项）。
- **验证**：冒烟 ALL PASS（含 T6）；budget rc=0；改动脚本 py_compile 全过；
  30 个 pyc 已逐文件删除（junction 安全，不用 rmtree）。

### 2026-09-19（八十八）：assemble 双 P0 —— 未导入名崩溃 + 单元归一吞楼号（云峰三轮实跑暴露，跑一轮修一轮）

- **P0-1：`assemble_households.py` NameError，全链路阻断**：`norm_unit` 用到
  `UNIT_RE_SRC` / `cn2num` / `unit_num`，但只引了 `protect_out_path` —— 任何 assemble
  调用必崩（实测云峰 `ftth.py assemble` 直接 NameError）。全仓排查仅此一处漏引
  （plan/parse/probe/read_titleblock 均正常引入）。修复：补 import；`cn2num` 修后无引用，
  已移出 import 行。备份：`桌面/云峰/.temp/backup_20260919_2110_pre_assemble_unitresrc/`。
- **P0-2：`norm_unit` 单捕获组吞楼号，多单元楼箱错位并相互覆盖**：原分支
  `(\d+)…楼?…UNIT` 取串首数字，`3#楼1单元`→`3单元`、`3#楼2单元`→`3单元` —— 后者覆盖前者，
  实测 2#楼丢 FX03/FX04、3#楼丢 FX07/FX08、6#楼丢 FX13/FX14、9#楼丢 FX19
  （单单元楼因回退/数字巧合未爆）。gen/apply 用的都是双捕获组正确写法，仅 assemble 偏离。
  修复：改走 `ftth_common.unit_num` 唯一入口（尾部取号，兼顾一单元中文写法），与 gen/apply 同则。
- **非代码修正（参数，非改脚本）**：count-box 4 列配到邻栋刻度（几何最近误配）——
  按 y 分带实测本栋刻度（1×/2× 精确偏移）后显式 `--col-scale-map`
  `25611.0=25381.8;25939.8=25706.4;26768.9=26654.5;26769.6=26655.2` 重跑；
  其中 3#楼2单元 B1:2 幽灵户消除、17F:2 补回（与 FX09/FX10 覆盖区间对齐）。
- **验证（云峰 .temp/iter_20260919_noref_3round/r3）**：三轮管线逐键一致（parsed/coverage/
  count/fxmap 四哈希 ALL_MATCH）；assemble 15 单元箱全部对位、守恒 371=331+40 克隆；
  apply-ruling 2 条（FX23 1F→B1、4#配套楼 B1 1→16）合计 386；gen 386 行逐箱分层核对无误；
  冒烟 ALL PASS；`ftth.py budget` rc=0；改动文件 `py_compile` 通过。
- **遗留（非缺陷）**：coverage 5 pending 无官方回写通道（沿用既有口径，裁决只落成品链）；
  parse 侧单元容器楼栋级与 coverage 单元级结构差异（无 FAIL 驱动，未重构，记观察项）。

### 2026-09-19（八十七）：代码质量整改 —— 控制台编码崩溃修复 + 退出码/重复实现收敛

- **冒烟门禁自身在中文 Windows 上崩溃（测试基础设施，实测复现）**：`tests/run_smoke.py`
  打印 `∅`（U+2205，GBK 不可编码），`UnicodeEncodeError` 中断整个冒烟 run —— T3/T4/T5
  全跳过，"门禁通过"不代表跑过。根因是全仓控制台编码无统一兜底：16 个脚本有裸
  `sys.stdout.reconfigure(encoding="utf-8")`、11 个有 print 的脚本（含冒烟测试）没有，
  中文控制台下凡打印 CJK 即崩（同次会话连外部 `git diff` 打印都复现了同类崩溃）。
- **`ftth_common.ensure_console_utf8()` 唯一实现**（stdout+stderr 双切，`getattr` 防护
  被替换的流，幂等、无害、UTF-8 下为 no-op）：7 个已导入 ftth_common 却无兜底的脚本接入
  （vshape / gaps / dump_geom / fx_locations / probe_tol / read_titleblock / verify_truth）；
  3 个刻意零依赖脚本（check_budget / check_transitions / gen_9level）与冒烟测试内联同语义
  8 行并注释指向共享实现。存量 16 处裸 `reconfigure` 保持不动（真实控制台下行为一致，
  不为统一而全量 churn，见函数 docstring）。
- **`sys.exit(str)` ×2（`analyze_coverage_vshape.py` 无标题分支 / `--fx-locations` 不可读分支）**：
  改为 `log.error` + `sys.exit(1)`。退出码与 stderr 通道与旧行为一致（真机实测 rc=1 不变），
  信息进日志可 grep；此前字符串 exit 无法被日志采集且易被误读为"崩溃"。
- **`bldg_num_local` 薄包装收口（`gen_addressbook.py` / `merge_json.py`）**：各仅一处排序调用，
  内联为共享 `bldg_num` 并删除包装 —— 七十三遗留的"楼号解析多份实现"至此清零
 （`floor_num_local` 调用方多，按既有 NOTE 保留不动）。
- **静默 `except Exception: pass`（parse 探查分支读块定义）**：改为 `log.debug` 留痕 ——
  默认不可见、`--verbose` 可查，不再无声吞错。
- **验证**：冒烟 15 项 ALL PASS（含 `--with-dxf` 语料 probe）；`ftth.py budget` rc=0；
  merge 合并数字排序（1/2/10）不变；vshape 两处错误分支 rc=1 与旧行为一致；
  10 个改动脚本 `--help` 全活；全仓 `py_compile` 通过。
- **未动项（有意）**：单体顶层执行式大脚本（parse 1961 行等）迫使 `ftth.py` 走子进程分发、
  `ftth.py main()` 627 行、`plan_methods main()` 333 行 —— 属架构级重构，需全量回归语料
  护航，本轮只登记不拆；`broad except` 余量多为 CLI 入口兜底，逐处收敛待后续轮次。

### 2026-09-19（八十六）：单元归属链五项缺陷修复 —— 中文单元号漏读 / 单元字段丢弃 / 判定顺序 / 空集合判 PASS / B′级误采图框标题

**共性**：五项全部落在「单元维度」上，且全部为**静默失效**——不报错、rc 正常，但产出错误或空白的单元结构。
更严重的是：其中三项会把**解析缺陷伪装成「图签与系统图矛盾」**（C10 报 FAIL），人工按"矛盾"去查图必然查不到，
是典型的"登记了疑点但拦不住结果"。故一并修复。

- **① 单元号中文写法漏读（`ftth_common.py`）**：新增 `UNIT_NUM_CN` / `UNIT_TOKEN` / `UNIT_RE_SRC`
  与 `unit_num()`，作为**单元号的唯一入口**（`1单元` / `一单元` / 纯号码 三形态归一，含串尾剥离）。
  此前各处各自写 `\d+单元`，实测图上以中文数字书写时**单元划分整批丢失**，
  表现为「单元数=1、单元名=楼栋名」，继而被 C10 报成图签矛盾。
  （同类前科：2026-09-18 的"写死模式须抽共享入口"——本条是同一纪律在正则层面的落实。）
- **② 单元字段"取了又丢"（`parse_dxf_structured.py`）**：`--bldg-map` 收集侧原先以
  `_tu = _tb` 一律用楼栋名，单元字段取出后即弃 → 图上自带的单元划分被整批抹平。
  改为按 `unit_num` 归位；注入侧按单元号建索引注入对应单元容器，
  **仅当图上确无单元轴标注**时才并回楼栋级容器（保留首修"箱与楼层表同键、不建孤儿容器"的初衷）。
  另：单元号须从**真正存着单元号的字段**取——直写证据把楼栋名存进 `单元`、真单元号在 `图上单元`，
  只读前者会让单元号恒为 None。
- **③ 单元划分判定顺序 + 共享列（`parse_dxf_structured.py::split_units`）**：原实现先判 `fx_texts`
  再判 `unit_marks`；当箱编号文字全部落在楼栋 x 区间之外（本类图纸的常见形态）时恒走 `no_fx` 路径，
  单元划分丢失。改为**先判单元标注**。并新增「共享列」逻辑：落在全部单元 x 范围之外
  且**非单元专属**的文字（楼层轴 / 行头）克隆进每个单元——否则单元有了、楼层表全空；
  单元专属文字（箱编号/皮线米数/户数）落空时**不克隆**（克隆会重复计数），改挂最近单元并登记交人。
- **④ 空集合不得判 PASS（`inspect_closure.py` C6）**：coverage 箱级记录为 0 时原判 PASS，
  改为 SKIP + WARN。**"没核"不得输出成"通过"**。
- **⑤ B′ 级证据必须带单元号（`ftth_common.build_fx_direct_evidence`）**：
  B′ 级（`N#楼M单元`）的唯一用途是给出**单元**归属；原文无单元号时它连单元都给不出，
  对本级目标零贡献，采纳它只会制造一个「单元键 = 楼栋名」的**假容器**（与楼层表不同键、无楼层轴）。
  实测无单元号的纯楼栋名标注最常出现在**图框标题 / 分区名**（实测该图 12 条全在 `TK-图框` 层，
  x 坐标与系统图区相差一个数量级），被采纳后会把**总图 / 箱表区**的箱编号认领过来
  （最近距约是真箱位的 10 倍）。后果三连：① 箱落进无楼层轴的容器 ⇒ 安装楼层恒为 null（C2/C9 FAIL）；
  ② C10 把「1单元 + 楼栋名容器」数成 2 个单元 ⇒ **误报图签矛盾**；③ 容器与图签口径对不上。
  收紧后此类箱回到「未采纳 → 登记交人」，符合「归无客观判据不进成品」。
  **注**：本次仅收紧**采纳条件**，未改动任何阈值——属"更保守"，不属"调参拟合"。

**实测收敛**：某工程 8 个分带从零跑 5 轮迭代，FAIL 由 51 项降至 12 项，
且第 3、4、5 轮产物**逐键完全一致**（确定性验证通过）。
剩余 12 项全部核实为**真图面差异**：图签的单元数 / 层数与系统图不符
（其中"层数差 1"经查为图纸楼层刻度**跳号**——图上刻意不写某层号，非解析漏读），
由 C10 正确报警、交人工裁决，**非解析缺陷**。
未归属箱数相应上升（假归属归零、改为登记待裁决），**编号总数守恒**、无静默丢数。

### 2026-09-19（八十五）：代码质量审查整改 —— 同名异义双实现收敛 + 包内冒烟自检

- **`_txt_fields` 收敛为一份**：`ftth_common.py` 内曾有两处定义（死代码版在 import 时被覆盖），
  删除死代码版；行为与整改前实际运行版逐字节一致（parse 逐键 0 差异）。
- **`bldg_num` 两态出口统一**：新增 `ftth_common.bldg_num_or_none`（失败返 None），
  `bldg_num`（失败返 0 既有语义）改为委托；`inspect_closure.py` 删除同名本地实现
  （此前失败返 None，与共享版同名异义），改 import 共享版——inspect stdout 新旧一致。
- **退出码 4 补登记**：`ledger_elements.py`（几何缓存为空/台账写入失败）与
  `parse_dxf_structured.py`（探查产物写入失败）实际使用 rc=4，scripts_reference.md 补记。
- **`tests/run_smoke.py` 新增**：包内冒烟自检（T1 单一源守卫 / T2 注册面=分发面 /
  T3 纯函数两态语义 / T4 体量闸门；`--with-dxf` 加跑语料 probe）。回归用例开始入库。

### 2026-09-19（八十二）：边界线加固四项 —— 分带机制上收唯一实现 + 列共识容差旋钮 + 单锚点取证
   **背景**：边界线主线遗留 4 个加固项（②列共识 ndigits=6 微差分裂 / ③单锚点带
   ±1000 绝对兜底 / ④分带双轨职责未裁定 / ⑥y 分带循环三处各抄一份）。全部为
   机制加固，无成品数值变化。
   - **⑥ 上收**：新增 `ftth_common.cluster_by_y`（锚定语义：带首 y0 锚定、None 跳过），
     `compute_bldg_ranges_banded` 与 `analyze_coverage.py` 的标题分带循环改为共用；
     vshape 的 y 聚类属图幅判别语义（elbow+链式），不同族，保留独立。
     验证：单元等价（300 随机 + 边界）逐位一致；柳辛庄 4 带 15 条真实标题 × 3 档
     容差带结构逐位一致；六图 parse 逐键 0 差异。修一处实施 bug：cluster_by_y 透传
     完整成员，compute_bldg_ranges_banded 下游按 (name,x) 消费 → 调用点映射回二元组。
   - **② 旋钮**：`column_consensus_y` 新增 `x_tol`（链式聚类，语义同
     cluster_chain_mean），parse 暴露为 `--consensus-x-tol`（默认 None=精确同值，
     行为逐位不变；命名避开 count_box_icons.py 同名不同义参数）。实测依据：柳辛庄
     b4 的 x 间隙为 0.01~10 连续谱、无天然分界 → 固定 tol 必有误合并/漏合并，
     故**不默认开启**，留作发现列被拆开时按图显式传值的诊断旋钮；b4 带 0.5 实跑
     rc=0 且逐键 0 差异（旋钮路径真机可用）。
   - **③ 取证**：单锚点带 ±1000 兜底仍无真机命中案例 → 不臆改数值；命中时补
     **测量证据**——带 y 窗口（相邻带 y0 中分为界）内文字 x 跨度与条数，落日志与
     产物，人工据此判断兜底宽度是否合理（该路径代码审读+编译验证，无真机触发）。
   - **④ 裁定**：分带双轨职责已裁定并登记 `references/measurement_architecture.md`
     「分带双轨职责」节——图幅分带（derive_plot_bands）与标题分带
     （compute_bldg_ranges_banded）输入/输出/失效模式均不同，两轨各留唯一实现；
     新增按 y 分带禁止再抄第三份循环。
   **回归**：六图 parse（fmcy 因桌面 profile.json 被清理 rc=2，环境变化非代码回归）
   逐键对拍 0 差异；`ftth.py budget` rc=0。备份 .audit/backup_ftth_20260919_1017_pre82。
   版本 0.81.1 → 0.82.0。

### 2026-09-19（八十一·补）：采纳另一会话 8 文件 —— P0 静默失配修复 + 分带自动模式 + 权威文档
   **背景**：工作区存有另一会话的 8 个未提交文件（4 脚本 + 4 文档），经用户 2026-09-19
   09:21 授权评估后**全部采纳**入库。评估证据：4 脚本语法编译 OK；共享依赖
   （normalize_bldg_name / judge_pending_scope / pending_items_from_rulings /
   derive_plot_bands / is_bldg_title_text）在 HEAD ftth_common 全部在位；
   **r4 管线产物（coverage.json 含 标注侧唯一箱位数/键未识别未比对/楼栋键区间歧义
   等新代码特征字段）即由这批脚本端到端产出**；真机冒烟：split_bands --auto
   （柳辛庄全图 plan 模式 rc=0，锚点识别与排除项逐条给因）、read_titleblock
   （云峰 rc=3 申报制语义正确）。
   **脚本（4）**：
   - analyze_coverage.py（竖线法）：楼栋名**同源投票**（修 P0 静默失配——重建名
     「N#楼」vs 对照表原文「N#配套楼」致裁决项关联不上、箱被静默放行）；
     「已排除」类裁决项标 阻塞=False 不判 pending；待裁决范围判定收敛到
     ftth_common.judge_pending_scope 唯一实现（修子串包含跨号误伤）。
   - analyze_coverage_vshape.py（V 型法）：同上三项 + 楼号解析统一走
     parse_bldg_nums_ex（不再自造正则）；键形态认不出**显式登记**（不再静默跳过）；
     需人工裁决按内容保序去重。
   - read_titleblock_households.py：「本图无图签形态」rc=1 → **rc=3**（申报制语义，
     与 ftth.py 三十·补契约对齐）；量测到但排版矛盾仍 rc=1（两回事）。
   - split_bands.py：新增 --auto（derive_plot_bands 唯一权威实现：地块锚点中点法
     分带，方案先行 --yes 确认；排除项逐条给因；三项独立核对）；ent_y 收编共享模块。
   **文档（4）**：measurement_architecture.md（地块锚点分带规则）、
   operations_discipline.md（④类三道锁 / 5.6 底线3前提 / 5.7 来源数与校验分流 /
   5.8 已确认≠已定案）、step2_selfcheck.md（C1~C10 十项名、C5 扩展、C10 详述，
   另补八十一 C10 字段级口径一段）、titleblock_and_intake_table.md（层户粒度
   栋级/单元级两形态，2026-09-18 用户裁定）。
   **未直跑项**：analyze_coverage.py（竖线法）本轮无同参真机输入，仅有编译 +
   依赖 + 与 V 型法同构 diff 审读；风险低但留痕。

### 2026-09-19（八十一）：C10 口径修复 —— 单侧不可读不得判矛盾；图标法层数回退
   **背景（真机实锤，非推演）**：柳辛庄 r4 pipeline 的 inspect.json 里 C10 FAIL
   「13 处不一致」，逐条拆解 = 9 假 + 4 真：图标法系统图（户数全空 → None）被当
   「与图签矛盾」；0.80 产物复跑 15 处 = 11 假 + 4 真。假阳性把真矛盾（楼3/4/5
   单元数 图签2 vs 系统1）淹没，违反 C10「停下交人裁定」的设计目的。
   **改动（inspect_closure.py，2 处）**：
   - 层数取数回退：有户数非空行维持原口径（凤鸣朝阳路径行为不变）；
     户数全空时回退「地上刻度行数」（排除 B/-/W 前缀），与图签住宅层口径对齐。
   - 字段级可比性：**双非空且不等**才计矛盾 FAIL；单侧 None 显式登记
     「? 单侧不可读，无法比对」，不阻塞、不冒充已核；可比字段全一致但存在
     未核 → WARN（没核不得呈现成通过）。
   **验证（四带全过）**：band1 15 处混报 → 4 处真矛盾 FAIL + 6 处显式未核，
   楼1 层数 18 vs 18 经回退真比对一致；b2/b3/b4 行为一致、无崩溃。
   **提交说明**：本提交同时包含另一会话在本文件的未提交工作（C1~C10 段及
   SKIP/rc 语义等，+129/−4）—— 经用户 2026-09-19 09:06 明确授权一并入库，
   特此留痕。补丁生成与四带验证：.temp/q/al183~al185（沙箱 sandbox_c10）。

### 2026-09-19（八十）：对照表路径补齐单元粒度纪律 —— A′ 直写楼层 × 23 箱全认领
   **背景**：七十九的「图上箱位直写自证」只补对照表缺席的编号；云峰余 5 个编号
   （FX03/05/09/13/15#）最近距 48.87 ≥ 候选间距一半 30.15，几何判据不足、按纪律不采纳。
   **收尾路径（第二来源闭合 → 测量自判）**：extract_fx_map.py（独立实现、独立判据）
   对这 5 个编号的归属与自证最近候选**逐一相同**，且给出安装楼层直写（4F/5F）——
   两源一致属测量，不属推理，走正规入口 `--bldg-map`（fxmap 阶段产物）落数。
   **实测踩中并修掉的坑（本轮核心改动）**：直接传对照表会把箱按对照表原文
   （`2#楼1单元`）凭空建成单元键 —— 楼层表留在「全部」、箱落到新单元，两容器脱节、
   下游 join 不上（正是七十九在自证路径修过的坑，A 级对照表路径漏改）。
   **改动（1 文件）**：对照表路径补齐同一粒度纪律 —— 箱只归**楼栋**单元（与楼层表
   同键），图上单元原文不丢、记入该箱「图上单元」字段留痕；「单元名并存」告警随之清零。
   **验证**：
   - 云峰（带对照表）：23 箱全落数（5 个未决清零）；23 箱安装楼层全部为
     口径A′ 图上直写（err=0.0，measured/settled），区间法原值降级为参考留痕
     （实测区间法参考误差 13.9~142.3，总图区坐标系本不具物理意义）；
     **楼层/户数/布线逐键 0 变化**。
   - 柳辛庄 4 图（自证路径）：单元键名由对照表原文（`1号楼`）统一为楼栋键（`1#楼`）
     —— 与既有「楼栋名同源」修复同方向；**数据值逐键 0 变化**（仅「收敛清单」
     描述串中的单元名回显跟着改）。
   - 六图（不传对照表）重跑与基线逐键 0 差异；真源重跑与沙箱产物逐键 0 差异
     （含云峰带对照表）；`ftth.py budget` rc=0。
   - 凤鸣朝阳真源复跑因桌面侧 r4 profile.json 已被清理而 rc=2（环境变化，非代码
     回归）；其补丁等价性由沙箱（补丁后）与基线差异=0 覆盖。
   **纪律重申**：几何判据不足（最近距 ≥ 间距一半）的编号，若无第二来源即报人工；
   本轮 5 个编号因两独立测量一致方可自判留证 —— 第二来源不成立时不得照抄此路径。

### 2026-09-19（七十九）：分纤箱「图上箱位直写」自动认领（A′/B′ 级证据）

**背景（有能力认领却没收，等于登记了疑点但没拦住结果）**：箱编号常落在独立总图/箱表区
（x 不落在任何楼栋标题区间内），此前只能靠人工 `--bldg-map` 认领；不传就整图 0 箱而
rc 仍 0 —— 实测柳辛庄 4 图 **84 个箱**、云峰 **23 个箱**全部归 0。但图上自己就写着
箱位（`N号楼M单元K层` / `N#楼M单元`）：探查段早已识别该形态并打印「建议做安装层交叉
校验」，却从未用于定归属。

**判据（纯几何、尺度无关、可复核 → 属测量不属推理）**：
`d1 < 0.5 × dAB`（d1＝到最近候选的距离，dAB＝最近与次近两个候选之间的距离）。
由三角不等式 `dAB ≤ d1 + d2` ⇒ `d2 ≥ dAB − d1 > 0.5·dAB > d1`，**最近项严格唯一**。
尺度取局部（最近与次近候选的间距）而非全图最小间距 —— 后者会被图上某一处密集候选对
拉低，导致别处本无歧义的归属被误拒（实测某图因此少认 7 个箱）。

**改动（2 文件；判定实现全工具链唯一，见下）**：
- `ftth_common.py`：新增 `DESC_POS_RE` / `UNIT_POS_RE` / `nearest_unambiguous()` /
  `build_fx_direct_evidence()`。两级证据：A′ 级 `N号楼M单元K层`（楼栋+单元+安装层齐备）、
  B′ 级 `N#楼M单元`（只到单元，安装层仍交区间法，守「只改归属不改安装楼层」）。
  配套/商业/附属写法纳入正则 —— 漏掉它们会把配套楼的箱误归邻近住宅楼。
- `parse_dxf_structured.py`：自证表只补**对照表没有**的编号；产物新增「图上箱位自证」
  （候选/采纳清单/未采纳及原因/因已有几何归属未启用）。

**证据优先级（本轮新增并强制执行）**：
人工对照表(A) > **系统图内几何归属** > 图上箱位直写(A′/B′)。
凡该编号有任何一处文字落在某栋 x 区间内，说明它本就在那栋系统图里，此时**不得**再用
「图上最近的箱位标注」改派 —— 实测放宽判据后凤鸣朝阳已正确归属的 17 个箱被整批改到
错误楼栋（8#楼 吞 10 箱）。自证只救**真正无归属**的编号。

**单元粒度纪律**：自证只定「属于哪栋楼 + 装在哪层」，**不顺带拆单元**。带上单元名会出现
「楼层表留在原容器、箱落到新单元」的脱节（下游 join 不上），也等于凭空引入图上没有
独立单元划分的颗粒度；图上单元号以「图上单元」字段另行留痕。

**验证（六图改前/改后逐键对拍，四要素只变代码版本）**：
- 柳辛庄 4 图：箱 **0 → 84**（b1 22 / b2 24 / b3 28 / b4 10，与图上箱位标注条数
  逐项相等）；云峰：箱 **0 → 18**（含两个配套楼各 1 箱，与独立测量一致）；
  凤鸣朝阳 **0 变化**（17 箱原位不动）—— 强证据优先的回归防护生效。
- 楼层表 **0 变化**、户数 **0 变化**、六图 **0 断号**；沙箱与真源重跑逐键 **0 差异**；
  包内语料冒烟 rc=0（7 栋 17 箱与主图一致）；体量闸门 rc=0。
- 云峰余 5 个编号判据不足（d1 48.9 vs 半间距 30.2），不猜、交人工，产物已附最近候选
  与距离供一键裁决。

### 2026-09-19（七十八）：区间标题「N-M号楼」按图上独立证据自动展开

**背景（登记了疑点 ≠ 拦得住结果）**：`N-M号楼` 语义（并列 vs 区间）文字本身无法判定，
此前一律按字面取端点并告警「楼栋区间待裁决」——实测柳辛庄 band1 **整栋丢 2#楼**、
band3 **整栋丢 5#楼**，而图上另有 `2#楼` / `5#楼` 独立标题与 `5号楼1单元2层` 一类
箱位标注为证。告警出了，楼还是没进成品。

**改动（2 文件）**：
- `ftth_common.py`：新增 `bldg_range_evidence()`。区间 N-M 的中间编号 K，若图上存在
  **另一条**文字含 `K#楼` / `K号楼` / `K号楼X单元Y层`，且该文字不是区间标题本身
  （**端点不得自证中间编号**），判定为区间语义并补入该栋；留痕进模块列表
  `BLDG_RANGE_EXPANDED`（标题 / 区间 / 补入楼栋 / 证据文字与坐标）。
- `parse_dxf_structured.py`：产物「楼栋边界」新增 `区间展开` 字段，展开动作可核对。
- **纪律**：无证据者维持字面取法并继续告警，**不替用户猜语义**。图上另有该编号的独立
  实体属**客观判据**（可测量、可核对），据此展开属自判留证，不是推理；无客观判据的
  区间语义仍按第④类报人。

**验证（六图改前/改后逐键对拍）**：
- lxz_b1 增 `2#楼`（18 刻度，与同区间 1#/3# 差 0）；lxz_b3 增 `5#楼`（15 刻度，
  与同区间 4#/6# 差 0）；共享克隆随之由 `{1#、3#}` → `{1#、2#、3#}`、`{4#、6#}` →
  `{4#、5#、6#}`，楼层按既有共享机制克隆。
- 其余四图楼栋内容 **0 差异**（唯一新增字段为「区间展开」）；告警类别无新增、
  六图楼层 **0 断号**；沙箱与真源重跑逐键 **0 差异**。

### 2026-09-18（七十七）：带端外沿补「贴边同列收回」—— 一根楼层轴不可被边界切断

**背景（七十六 未决 ①，坐标级取证已闭合）**：七十六 解决了「一条列不可按 **y** 拆开」（跨带方向），
但**带端**方向仍在丢数据 —— 带内最端楼栋的外沿由锚点派生（半间距外推），会把该栋的**第二根楼层轴**
切在区间外。实测：某带最左栋只拿到 `1F..9F`（9 层），被切出的同 x 列 `10F..15F` 与区间内那列
**同 y 步长（17550）且首尾相接**（区间内最高层的 y 与区间外最低层的 y 之差恰等于层高），
是同一张系统图的同一栋，却整列丢失 —— 下游表现为该栋层数只有邻栋的一半。
此前只有告警（`业务实体落空_可疑`），**没有收回动作**：登记了疑点 ≠ 拦得住结果。

**改动（1 文件 `scripts/parse_dxf_structured.py`，+约 45 行）**：
- 新增「贴边同列收回」。三条判据**全满足才收，缺一不收**（宁可漏收，不误收）：
  ① 业务实体（楼层刻度 / 箱号 / 每层户数 / 皮线米数）；
  ② 距最近楼栋区间边界 `< τ`（τ ＝ 0.25 × 该楼栋区间宽，与既有 `业务实体落空_可疑` 同一口径）；
  ③ 同 x（精确同值）在落空集合中 **≥2 条** —— 单点是图例或零散文字，不构成「轴」。
- 只把整列**补挂**到该楼栋的文字集，**不改区间**（区间由锚点派生，改它会牵动邻栋）。
- 产物新增 `贴边同列收回`（条数 / 列数 / 明细：楼栋、x、条数、补挂数、内容）——收回动作可核对、可复现。

**验证（三方对拍：同一输入 × 同一参数 × 三份代码，18 次 parse，全部 rc=0）**：
- **零回归**：七十六前 → 七十七 的楼层表逐键递归比对，**5/6 图 0 变化**；唯一变化即目标栋
  **`9 层 → 15 层`**（补回的正是被切出的那 6 条，且补回后序列 `1F..15F` 连续无断号）。
- **跨提交回归（本轮补做）**：上轮只做了「同一代码内 legacy ↔ new」对拍，本轮补做
  **跨提交**对拍（`6946373^` vs `6946373`）：确认七十六 除云峰 6 栋修复外
  **无任何未登记回退**（此前疑似的「单元键名变化」经查属更早批次的产物，非七十六所致）。
- 全量扫描 6 图 43 个楼栋单元的楼层序列：**0 断号**。
- 落地后以真源重跑 6 图，产物与沙箱**逐键 0 差异**。

**备份**：技能目录外 `.audit/backup_ftth_20260918_223803_pre_algo3/`（59 文件 / 3,863,029 B，
逐文件 sha256 一致）。

**未决（沿用七十六，仍报人工）**：① 列分组用**精确同值**（`ndigits=6`）⇒ 同一列内 x 有微差者
会分成多个子列；② `单锚点带` 的 ±1000 绝对兜底（三项目均未命中，无可验证数据前不改）；
③ 云峰 1#楼 左界外 67 条业务实体（距边界 100~285 ≈ 半个区间宽）判为独立图区（总图区箱清单），
未收回 —— 与本次「贴边」判据（τ ＝ 0.25 × 区间宽）不冲突，但**属人工裁决，未自动定案**。

### 2026-09-18（七十六）：跨带重叠的归属改为「列共识 + 共享组展开」—— 一条列不可按 y 拆开

**背景（七十五 的残留缺陷，坐标级取证发现）**：七十五 把归属从「纯 x 先到先得」改为
「分带 + y 就近 + 共享区间克隆」，但两处未接严：
① **`y就近` 分支忘了展开共享组** —— 选中项若属共享区间（一张图服务多栋），只返回**该栋**，
同组其余楼栋仍被独吞；② **判带以「点」为单位** —— 跨带 x 重叠区里，同一条楼层刻度列会被
带分界**拦腰拆开**。实测某图 `x=26654.52` 的 12 个刻度（`B1,1F..10F,WF`，步长恰＝层高）
被判成上半列（1F~6F）归住宅、下半列（7F~WF）归配套楼；同 x 的另一栋整列落空；
一条 20 点的皮线标注列同样被拆成 10/10。下游表现：`8#楼`/`10#楼` **楼层表与标题双空**、
`7#楼` 只 7 层、两栋配套楼各多出 4 层住宅刻度。同时暴露三处「诊断本身不可靠」（见 ④⑤⑥）。

**改动（2 文件，+约 250 行）**：
- `scripts/ftth_common.py`：① `assign_by_xy` 的 `y就近` 分支返回前**展开同区间的整组**
  （新 reason `y就近+共享克隆(候选N)`）；② 新增 `column_consensus_y`：**同 x（精确同值）**
  的实体视为一条「列」，返回列内 y 中位。
- `scripts/parse_dxf_structured.py`：① 接入列共识 —— **仅当 x 命中 ≥2 个楼栋区间**时用列代表 y
  判带（其余点仍用自身 y ⇒ 单候选点逐位不变）；产物新增 `列共识判带`（条数/列数/列 x）。
  ② y 分行**只留一份实现**：边界重叠校验段改用 `compute_bldg_ranges_banded` 已返回的 `_bldg_bands`，
  删掉硬编码 `abs(y−yg)<100` 的第二次分带（同一维度两套口径必然漂移）。
  ③ **截断字段带总数**：`待裁决归属`/`区间过窄`/`业务实体落空`/`业务实体落空_可疑` 由裸列表改为
  `{总数, 展示}` —— 旧实现只存前 100 条且不记总数，实测两处真值 ≥100，下游会把 100 当成全部。
  ④ 新增 `孤儿分类账`：按机械判据分「①贴边疑切出 / ②跨带落空 / ③带内缝隙 / ④图区外(独立图区)」
  计数并各留 3 条样本 —— 此前「未命中」只给一个总数，看不出是独立图区还是被边界切出。
  ⑤ 共享区间条目补 `源标题` + `判据`（人工判「克隆是否成立」的唯一依据）；不同标题落到同一 x 区间
  时告警「疑假共享」。⑥ `单锚点带`（区间走 **±1000 绝对常量**兜底、与图纸比例无关）显式告警并落产物。

**验证（同一输入 × {上轮代码, 本轮代码} × {legacy, new} ＝ 24 次 parse，全部 rc=0）**：
- **零回归**：legacy 产物逐键递归比对，**6/6 图 0 差异**。
- **收益**：凤鸣朝阳 0 变化；柳辛庄 a 区 4 band 0 变化（新分支只由「x 命中 ≥2 区间」触发，条件严格）；
  **云峰 6 栋修复**：`8#楼 0→12 层`、`10#楼 0→12 层`（并补回此前为空的标题）、`7#楼 7→12`、
  `9#楼 7→12`、`11#配套楼 8→4`、`4#配套楼 8→4`（去住宅刻度污染）。
- **七十五 的未决项由此解开**：云峰配套楼刻度组合 `{B1,1F,2F,7F..10F,WF}` 是「列被拆开」的产物，
  不是图面形态。坐标级铁证（同一图上两列 x 仅差 0.67）：住宅列 `x=26654.52`
  （`B1,1F..10F,WF`，y≈−4018~−3688，步长 30）；配套列 `x=26655.19`
  （`B1,1F,2F,WF`，y≈−3603~−3502）。
- 落地后以真源重跑 6 图，产物与沙箱**逐键一致（含 `楼栋边界` 段）**；`ftth.py budget` rc=0。

**备份**：技能目录外 `.audit/backup_ftth_20260918_214930_pre_algo2/`（57 文件 / 3,639,455 B，
逐文件 sha256 一致）。

**未决（报人工，非自动判定）**：① 柳辛庄 a band2 有 6 条楼层刻度（10F~15F，步长 17550 ≠ 该图
主簇 16260）紧贴 1#楼左界外 1112（≈0.07 层高），判为「①贴边疑切出」——是图例/详图还是漏抓楼栋，
**未定**；② 列分组用**精确同值**（`ndigits=6`）⇒ 同一列内 x 有微差者会分成多个子列、各自判带；
本轮实测无可见后果（跨带那个子列是 `WF`，落配套楼而配套楼本就有 `WF`），但这是**已知脆弱点**；
③ 单锚点带的 ±1000 绝对兜底**未改数值**（三项目未命中，避免无法验证的改动），只加告警与登记。

### 2026-09-18（七十五）：楼栋边界归属重做 —— 分带 + 共享区间克隆，废弃「纯 x 先到先得」

**背景（楼栋边界算法冒烟测试）**：`compute_bldg_ranges` 是「全图统一 x 中分」，归属环节
（文字 / INSERT）则是「纯 x 闭区间 + dict 序先到先得」，**完全不看 y**。其成立前提
「各锚点同处一个 y 行、且各栋 x 区间互不重叠」在实测的两类图上都不成立：
① **共享锚点**：一张系统图服务多栋（标题原文形如 `N#、M#住宅光纤入户系统图`），
`_x_groups` 已把同 x 锚点并组共用同一区间，归属时先到先得者**独占**，其余楼栋楼层表
**整片为空**；② **上下分带**：配套楼小图与住宅楼大图 x 上重叠，跨带统一中分导致某栋
区间被压扁（实测某图某栋区间宽仅 37.6，不到邻栋区间宽的 1/7），本栋实体一列归错楼、
一列成孤儿。技能侧 `SKILL.md` 早已写明「多栋共享同一系统图 → 走克隆留痕路径」，
但 **parse 的归属代码从未实现克隆** —— 属「规则写了没接线」。

**改动（3 文件，+189 行）**：
- `scripts/ftth_common.py` 新增三个纯函数：`assign_by_xy`（带内 (x,y) 归属；**单候选
  与旧实现逐位一致**，多候选才分叉：同区间→共享克隆、区间不同→按 |y−锚点y| 就近、
  y 不可比→**返回空并报裁决，不静默择一**）、`group_shared_ranges`（识别并登记共享区间）、
  `bldg_range_diagnostics`（区间宽 / 归属条数 / x 跨度 / 孤儿明细）。
- `scripts/parse_dxf_structured.py`：① 边界计算改走**已有**的 `compute_bldg_ranges_banded`
  （分带容差 = 2 倍层高自适应；层高不可得 → 退单带，与旧行为一致）；② 文字与 INSERT 归属
  改走 `assign_by_xy`（**共享区间克隆给组内每一栋**，与 SKILL.md 既定处置对齐）；
  ③ **删除逐字重复的边界重叠校验段**（原 L709-758 与 L760-809 整段重复 → 同一告警打印两遍，
  实测某图 10 对边界报出 20 条）；④ 新增区间自检（「区间过窄」＝宽 < 中位宽 1/3；
  「业务实体落空」＝含楼层/户数/皮线/箱号特征的文字不落在任何区间且距边界 < 本栋区间宽 1/4）
  并把边界、共享组、归属统计、自检明细**落进产物 `楼栋边界` 段**（此前只进 log，下游拿不到）。
- `scripts/ftth.py`：`parse` 子命令增 `--title-band-tol`（覆盖自适应容差）与
  `--legacy-bldg-assign`（**仅对拍用**，强制旧行为，正式出表不得启用）。

**验证（三项目 A/B 对拍，同一脚本 + `--legacy-bldg-assign` 切换，同一份实现不复制）**：
- **零回归**：legacy 模式产物与项目**现有** `parsed.json` 逐键比对，凤鸣朝阳 + 柳辛庄 a 区
  4 个 band **全部差异 0 条**（证明对拍基线可信、改造可逐位还原）。
- **凤鸣朝阳**：新旧 **0 变化**（单带标准图，符合预期）。
- **柳辛庄 a 区 4 band**：**7 栋楼层表由「空」变「有」**（3#/2# 18 层、6#/7#/9# 15~18 层）。
  根因即共享锚点：标题原文 `1-3号楼综合布线系统图`（技能自身已判定为「并列 2 栋」）
  被展开为同 x 同 y 两个锚点，旧归属下 3#楼恒被 1#楼独占而整片为空。
- **云峰**：分带生效（2 带：住宅 9 栋 / 配套 2 栋）；**9#楼楼层表 0→7**（区间由 37.6 恢复为
  254，本栋皮线列不再被切出/丢弃）、**11#配套楼 0→8**；4#配套楼与 7#楼归属重新分配
  （旧实现把同一批 y≈−3848~−3944 的皮线**同时计入两栋**，跨带串扰，现各归本带）。

**备份**：技能目录外 `.audit/backup_ftth_20260918_204136_pre_bldgrange/`（57 文件 / 3,622,808 B，
逐文件 sha256 一致）。

**未决（报人工，非自动判定）**：云峰配套楼的楼层刻度组合（`{B1,1F,2F,7F..10F,WF}`）与
7#楼住宅（`{B1,1F..6F}`）互补且并集恰为旧实现的 12 刻度，几何自洽；但**未能取得刻度文字的
坐标级铁证**（几何转储的 texts 不含单独刻度串），故仅登记 `楼栋边界.共享区间` 与归属统计
供复核，**未据此改判**。

### 2026-09-18（七十四）：`apply-ruling` 分发补齐 —— 「注册了子命令但没接分发」的 P0 静默空转

**背景（架构评审时审计发现）**：`ftth.py apply-ruling` **只在 argparse 注册了子命令**，`main()` 的 `if/elif`
分发段**没有对应分支** → 走完 `main()` 自然返回，**rc=0、零输出、什么都没做**。而 3 处文档
（`SKILL.md`、`pipeline_details.md` §4 整节、`scripts_reference.md`）都把它当可用入口 —— 它是
「人工裁决批量落数」入口，照文档跑会以为裁决已落数，而产物根本没改。属「登记了入口 ≠ 接得上」的典型。

**取证（真机对照，`--dry-run` 无写入）**

| 组 | 命令 | rc | 输出 |
|---|---|---|---|
| A（补前） | `ftth.py apply-ruling --json <不存在> --dry-run` | **0** | **0 字节** |
| B（对照·直调） | `apply_ruling.py` 同参数 | 1 | 229 B 报错 |
| C（阳性对照） | `ftth.py budget` | 0 | 487 B |

注册面 16 vs 分发面 15，差集**恰好只有 `apply-ruling`**（`probe` 曾被误报，因其分支写 `if` 非 `elif`，非缺口）。

**改动（1 处）**：`scripts/ftth.py` 分发段末端补 `elif args.cmd == "apply-ruling":`（19 行）。

1. `--set` **显式逐条转发**、**不复用 `build_cmd`**：`apply_ruling.py` 是 `for s in args.set` 逐条
   `split("=",1)` / `split("/")`，而 `build_cmd` 经 `fmt_val` 会把列表**拼成单参逗号串**
   → 楼栋名含逗号、解析失败。（这是补丁里唯一有技术含量的一处，其余是机械转发。）
2. `--force` / `--dry-run` 按 `build_cmd` **现行**布尔语义（自 2026-09-15 起 True→`--flag`）显式转发，
   不引入第二口径。

**验收（真机 8/8 全绿）**

| 用例 | rc | 结果 |
|---|---|---|
| T1 双 `--set` 经统一入口 | 0 | 2 处落数（`3层: 2 -> 4` / `5层: 3 -> 6`）—— **证明逐条转发正确**（拼接则必挂） |
| T2 `--ruling` + `--set` 并用 | 0 | 2 处落数（箱安装楼层 + 户数） |
| T3 输入文件不存在 | **1** | 273 B 报错（**补前为 rc=0 / 0 B**） |
| T4 未给任何裁决 | 1 | 报「没有给出任何裁决」 |
| T5 `--out` 同路径无 `--force` | 2 | 写保护（证明 `--out` 已透传） |
| T6 直调 `apply_ruling.py`（T1 同参） | 0 | 与 T1 **等价**（rc 同、落数同） |

**连带更正（记而不改，避免第二口径）**：`ftth.py` 内数处注释仍写「store_true 默认 False 会被
`build_cmd` 转发成 `--flag False`」—— 该描述自 2026-09-15 起**已过时**（`build_cmd` 已统一处理布尔）；
相关处「手工排除后单独处理」属**冗余但行为正确**，本轮**不动**（最小改动面）。

**遗留**：无。差集已归零 —— 注册但无分发 = ∅；`count-hdd` 是 `count-box` 的 `aliases`，非缺口。

### 2026-09-18（七十三）：探查期「单元 × 箱清单」交叉清点 —— 「某单元没分纤箱」提前到 parse 之前（用户裁定）

**背景**：用户裁定「某单元没有分纤箱」应走**更早的探查阶段**。原先该情形只在 **Step 2 自检**
（覆盖完整性门禁）暴露 —— 那时 parse/coverage 已跑完，返工面大。而图面证据**在 parse 之前就齐**：
骨架（`titleblock.json`）与箱清单（`fxmap.json` / `fx_locations.json`）在 `_PIPE_STAGES` 里都排在 parse 之前。

**改动（七处）**

| # | 落点 | 内容 |
|---|---|---|
| 1 | `scripts/check_unit_box_gaps.py`（**新增**） | 骨架 × 箱清单**双向差集**：`骨架有·箱清单无`（候选：该单元未识别到箱）/ `箱清单有·骨架无`（候选：骨架漏记）。箱清单两来源同时存在时**先互校**、分歧并列登记不择一。产物 `unit_box_gaps.json`，结论三态 `pending / settled / unresolved` |
| 2 | `scripts/ftth.py` | `_PIPE_STAGES` 新增 `unit_gaps`（在 `fx_locations` 与 `parse` **之间**）；`--stop-at` choices 随之自动包含；新增 `_pipe_gap_verdict()` 供流水线打印三态结论；`stop_idx` 顺延 |
| 3 | `scripts/ftth_common.py` | 新增 `parse_unit_key()`（「楼栋[单元]」串 → 归属键，**唯一实现**）与 `cn2num()`（**自 verify_coverage_truth.py 上提**，全技能一份） |
| 4 | `scripts/verify_coverage_truth.py` | `cn2num` 改为从 `ftth_common` 导入（保留同名绑定，调用点不变）—— 消除重复实现 |
| 5 | `references/probe_checklist.md` | 新增第 9 项「单元 × 箱清单交叉清点」：两来源明细、双向差集、必须带楼栋维度、**来源缺席 ≠ 数据为 0**、定位说明 |
| 6 | `references/coverage_rules.md` | 覆盖完整性门禁补**两级关系**：探查期早报（`unit_gaps`）× 本条兜底；**早报判 `unresolved` 不解除本条** |
| 7 | `SKILL.md` / `references/pipeline_details.md` / `references/scripts_reference.md` | 探查清单新增第 3 项；阶段串同步为实际值（**并补上此前两轮遗漏的 `fx_locations`**）；产物列表与脚本清单补齐 |

**四条硬约束（都对应实测形态）**

1. **来源缺席 ≠ 数据为 0**：任一侧文件缺失 / 不可读 / 内容为空即判 `unresolved`、**不产生待确认项** ——
   否则「没核过」会被输出成「全部单元无箱」（假失败）或「通过」（假绿灯）。
2. **双向差集都报**：实测同图四条分带中，一条带双向**同时**非空（`5/6号楼2单元` 箱清单无、
   `2/3/7号楼` 骨架无），单项差集必然漏报一半。
3. **必须带楼栋维度**：`1单元` 每栋都有，裸单元号比较会跨楼栋互相污染。
4. **单元键解析只走共享实现**：`ftth_common.parse_unit_key`，不得另写正则。

**实测（真机三项目）**

| 项目 | 骨架 | 箱清单 | 预检结论 |
|---|---|---|---|
| 柳辛庄 band1 | present(8) | fx_locations(10) | `pending`：`箱清单有·骨架无` 2 项（1号楼1/2单元） |
| 柳辛庄 band3 | present(12) | fxmap+fx_locations(14) | `pending`：双向 2 + 4 项 |
| 柳辛庄 band4 | present(6) | fx_locations(6) | `settled`（两侧一致） |
| 云峰 | **无文件** | fxmap(13 键，另 2 条无单元号) | `unresolved` |
| 凤鸣朝阳 | present(12) | **两来源皆无** | `unresolved` |

**遗留（本轮未做，登记备查）**：`bldg_num` 在技能内**仍有 4 份实现**
（`ftth_common.bldg_num` ＋ `gen_addressbook.bldg_num_local` ＋ `inspect_closure.bldg_num`
＋ `merge_json.bldg_num_local`）—— 本轮只收口了 `cn2num` 与单元键解析，楼号解析那四处未动。

### 2026-09-18（七十二）：图纸信息模型「三要素 → 八项」+ 来源数分流与校验分级（用户口径落地）

**背景**：用户就「探查图纸的目的是找到什么」给出完整口径，逐条审查后裁定。原「三要素」
（箱号+安装位置 / 覆盖楼层 / 每层户数）只覆盖**后半截**；楼-单元-层骨架散落在「必须解析」九项
与九级树行数恒等式里，两份清单口径不一。

**改动（八处）**

| # | 落点 | 内容 |
|---|---|---|
| 1 | `SKILL.md` §图纸信息模型 | **三要素 → 八项**：① 楼数量 ② 楼号 ③ 单元数 ④ 楼层（**归属单元**，栋级/单元级两形态均支持）⑤ 每层户数 ⑥ 分纤箱编号 ⑦ 分纤箱安装楼层 ⑧ 分纤箱覆盖楼层 |
| 2 | `SKILL.md` 同节 | 新增**来源数与校验分流**：`0 处`先自证「真的没有」→ 待确认；`1 处`直接采信；`≥2 处`互相比对，不一致**可推理可推荐、列全选项交人选，不裁决**；**禁止为比对自创算法** |
| 3 | `SKILL.md` §C4 | 判据改称**对照表判据**并明写「**只看内容、不看图名**」；§C3①、§Step 1a 第 2 项、§Step 1b 硬约束②、§Step 2 必查项同步改措辞（**图纸名字不作判据**） |
| 4 | `coverage_rules.md` §来源数与采信 | 新增：来源数分流表；**单源值的替代校验 = 总体核对**（覆盖完整性门禁）；**「计算孤立」≠「算不出来」**两概念分列；判据「`判定依据` 为空或『待确认』则不得采信」 |
| 5 | `coverage_rules.md` 覆盖完整性门禁 | 补**前置条件**：先判「该单元一个箱都没有」—— 否则无箱 + 无户数标注双双空集、**空集相等反而判 PASS**；**无箱单元一律登记报人** |
| 6 | `operations_discipline.md` §5.3 | 第④类允许「先推理再推荐」，加**三道锁**：推荐只许进「参考线索」列 / **禁默认值与默认选项** / 必须列全选项 |
| 7 | `operations_discipline.md` §5.7、§5.8 | 新增：来源数与校验分流总则；**「已确认」（用户原话）与「已定案 `settled`」（系统自洽）分词** —— 混用会使 L0-I3 防伪失效 |
| 8 | `probe_checklist.md` 第 8 项、`titleblock_and_intake_table.md` §3.2 | 新增**栋级骨架与层数粒度**探查项与比对分流；补齐「**图签本身即单元级**」形态（原只有「图签栋级 vs 采集表单元级」） |

**关键设计决策**

- **不新增字段、不新增权威口径**：四级校验完全落在既有 L1-C8（`result_origin` × `result_confirmation`）上。
- **「总体核对」指派给既有门禁**：口径「单源靠总体核对」复用**已存在**的覆盖完整性门禁，非新建机制。
- **体量纪律**：SKILL.md 改动途中由 47,928 B 一度升至 48,976 B（距硬上限仅 24 B），
  故同步**压缩三处与新口径重叠的旧条文**（多处一致性条 / 优先用直读条 / 引用纪律条 / 八项体检条），
  终态 **48,805 B**（余量 195 B，未触硬上限）。

**备份**：`.audit/backup_ftth_20260918_1652_pre_eight_items`（技能目录之外；210 文件 / 6,097,183 B；
逐文件 sha256 全 MATCH）。

**验证**：冒烟用例 53 例全绿；`ftth.py budget` rc=0；真源 junction 与 `.config` 真身 sha256 双向 MATCH；
全量差异审计（对备份逐文件对拍）改动文件数 = 预期、0 新增 0 丢失、换行风格一致
（**该文件原即 CRLF**，非 Edit 工具引入）。

### 2026-09-18（七十一）：待裁决项「作用域」失配 —— 疑点列进清单却静默放行（P0）

**背景**：三张图（两块地竣工图 / 单张系统图 ×2）从零冷启动跑两轮，第 2 轮复核时对
**判范围逻辑本身**做了形态矩阵用例（22 例全部取自源码实际拼串格式）—— 结果 **12 例失配**。

**缺陷（P0）**：`analyze_coverage_vshape.py` 的「裁决项 → 本单元/本箱」判定落后于竖线法：

| 现象 | 根因 | 后果 |
|---|---|---|
| 空格式对象串（`4#楼 1单元`）**永远关联不上** | 只按 `/` 拆段，V 型法产出的是空格分隔 | 该单元带着阻塞性疑点被判 `settled` |
| 楼栋名形态不同即失配 | 前缀剥离条件写成「楼号数字相等」，实际比的是**楼栋号 vs 单元号** | 仅当楼号 == 单元号时偶然命中 |
| 楼栋级疑点（对象只有 `4#楼`）**不作用于任何单元** | 判范围只实现了「单元级 / 箱级」两级 | 整栋几何前提存疑却零 pending |
| 同一逻辑抄两份 | 竖线法 / V 型法各写一份 | 必漂移（本次即漂移结果） |

**修复**

1. **作用域三级化**：对象串按实际写了几段决定作用于 **楼栋 / 单元 / 箱** 哪一级，逐级向下拦
   （`ftth_common.parse_ruling_scope`）。
2. **分段改「从尾部剥」**：不再按 `/` 或空格无条件全拆 —— 楼栋名自身可能含 `/`（`3/6号楼综合布线系统图`）
   与空格，只能从尾部剥「`N单元`」「纯编号」两种已确认形态（`split_ruling_object`）。
3. **判范围加楼栋维度**：`judge_pending_scope(..., bldg_key=)`，跨楼栋不误伤（同号才算同栋，
   沿用 `judge_object_name` 既有口径）；不传楼栋键时退化为「不猜楼栋」。
4. **唯一实现**：两个覆盖脚本只保留薄封装，调用点显式传楼栋键。

**验证**

- 形态矩阵 **53 用例全绿**（含切分快照与归段快照），用例源固定为 `probe_objfmt.CASES` 单一文件，
  **禁止测试也抄两份**（本次缺陷的成因就是抄两份）。
- **真机 A/B**（修复前备份里的旧逻辑 vs 新逻辑，跑在真实产物上）：
  两块地图 4 个带共 **+7 个单元**由「静默 settled」翻为 pending（旧逻辑只命中楼号 == 单元号者）；
  竖线法那张图 **5 → 5 完全不变**（现传楼栋键，语义无回归）；无裁决项那张图 0 变化。
- 修复后按同输入同口径重跑三个项目：C0~C10 逐项与修复前**完全一致**（本图 coverage 侧箱级记录为 0，
  C9 本就走 SKIP，故本次修复在这些图上「只堵住漏洞、不改结论」）。

**遗留（未在本次处置，需人工定口径）**

- **coverage → parse 不联动**：coverage 的单元级/箱级待裁决**不传导**到 `parse_dxf_structured.py`
  的箱级 `result_confirmation`（后者只按自身几何判据定案）。实测某带 coverage 有 23 项阻塞性疑点，
  而 parse 侧 26 个箱**全部 settled**。是否联动属跨脚本契约，**引入第二权威口径的风险须先定**再动手。
- **单元级 pending 在「该单元 0 箱」时不落任何字段**：`结果状态说明.统计` 只统计箱，故 0 箱单元的
  pending 无处可见（不影响成品 —— 无箱可进；但 C9 只能 SKIP，「已提供但零字段的来源」靠 C9 的 WARN 点名兜）。

### 2026-09-18（七十）：冷启动三轮实测（多地块双图）—— 「量了没接线」第六例（地块锚点）+ 切点口径缺证

**背景**：对一份**两块地**（1-4 地块 / 5-9 地块，各含 4 个地块、楼号各自从 1 起）的竣工图，
从零冷启动跑三轮，每轮「跑完 → 定位 → 修 → 重跑」。第 1 轮两块地在 `parse` 阶段**双双中止**。

**第 1 轮暴露（4 个真缺陷 + 1 组图纸固有状态）**

| # | 级别 | 现象 | 根因 | 处置 |
|---|---|---|---|---|
| 1 | **P0** | `parse` 因「多地块同名楼」守卫 rc=3 提前中止，日志却打印「**rc=3 = 本图不适用（非错误），按画像降级路径继续**」；人据此以为已降级跑完，而 parsed/coverage/inspect **根本没产出** | `_dump(rc)` 把 rc=3 一律按「继续」措辞；但 `_dump(rc!=0)` 的调用点**全部**是提前 return，链路已终止 —— **退出码语义与「是否真的继续」不一致** | `_dump(rc, stopped=阶段名)`：提前中止时明写「⛔ 已在「X」阶段中止 —— **后续阶段未执行**」「不要把本次产物当作完整链路结果」。说继续就得真继续 |
| 2 | **P0** | 守卫指引的第 2 步（`split-band`）**要求人工手搓 band spec**（`--band 名称:ymin:ymax` 逐条给 y），两块地共 8 条 —— 而图上「N块地」标注早已被探针实测到并写进画像 | **「量了没接线」第六例**：探针量了 → 画像存了 → **没有任何下游消费**。规则写在铁律⑦、尺寸量在 probe、执行环节零接线 | 新增 `split-band --auto`（默认只出方案，核对后 `--yes` 执行）；锚点提取 + 窗口计算收成 `ftth_common.derive_plot_bands` **唯一权威**，probe 与 split-band 共用，画像里直接带「分带窗口/切点/核对疑点」 |
| 3 | **P0** | 按初版实现（切点 = 锚点 y；锚点扫描限定探针建议的 `text_layer`）**两处都错**：① `text_layer` 不含锚点实际所在图层 → **锚点整批为 0**，脚本报「图上没有锚点」；② 改对扫描后，切点取锚点 y → **每带吞进下邻带 4 条场所标注** | ① 图层门禁对「严格相等匹配」的锚点是多余约束，只会丢真锚；② 锚点落在本带图区**内部偏上**，其 y 不是带边界 | 锚点扫描**不限图层**；切点改取**相邻锚点 y 的中点**（实测越界 0 条）。两条口径写进 `measurement_architecture.md`「多地块分带边界 · 图上已有地块锚点时」增补节 |
| 4 | **P1** | 分带属**高风险切分**，初版仅靠「窗口有效」自证 | 缺独立核对 —— 一旦切错，两侧各自自洽、互相矛盾，最易被误判成「图纸自身矛盾」 | `verify_band_split` 三项独立核对：① 切点空置（切点 ±容差内不得有文字）② 带内自证（`N块地…` 标注所在带必须编号相符，与几何切分互证）③ 楼栋标题不跨带（「最近锚点」vs「所在带」两条独立路径一致）。**不阻塞但必须报人，不得当绿灯** |

**第 1 轮附带确认（非缺陷，属设计内的报人）**

- 分带修好后两块地 8 个子图**全部跑通到 inspect**（此前 0 个）。新暴露的是归属类问题：
  `parse` 箱编号归属 0、`coverage` 每单元「箱 0 个」；实测这些箱编号/单元/户数标注的 x 落在
  **光缆布线图/图框区**，而楼栋标题在**综合布线图区**右侧，二者无几何关联 → 脚本按契约记入
  「未归属/未匹配」并**拒入成品、报人裁决**，行为正确（不得按「就近楼栋」推定）。
- `titleblock` 阶段（图签第二来源）**读通了**：从图框层直读出逐栋「层数/每层户数/单元数」。
  其中 12/20 条单元标注在容差内命中多栋 → 脚本按**既定策略**（「不改最近者胜判据、漏读交人核对」）
  显式登记歧义，导致 1 栋单元数缺项、合计偏低。**这不是新缺陷，是 2026-09-17 的用户裁决**。
- 附带查到的**图纸自身差异**（报人，不进成品）：图签逐单元推算 **468 户**，图面说明文字自述
  **467 户**（差 1）；脚本因上述歧义给出的**保守下界 414 户**。三者并列交人，不自动择一。

**第 2 轮暴露（1 个回归 —— 且是本次修复自己引进的）**

| 级别 | 现象 | 根因 | 处置 |
|---|---|---|---|
| **P1** | 全图两图 `probe` 阶段 **rc=1 崩溃**（`TypeError: %d format: a real number is required, not str`），第 2 轮 10 个进程**全部停在 probe**，分带与逐带链路全部无效 | 第 1 轮为「画像带分带窗口」改探针日志时，格式串有 6 个占位符、实参只给了 5 个 —— 新增的「分带窗口 %d 个」漏传 `<窗口数>` | 补齐实参；**真机冒烟**（两图 `probe`+`plan` 均 rc=0，画像 `分带窗口` 4 个、切点与 `split-band` 实算逐值一致） |

> 侧证：第 2 轮同时**验证了 F1 的修法是对的** —— 崩溃时日志正确打出
> 「⛔ 已在「probe」阶段中止（rc=1）—— **后续阶段未执行**」，而不是旧版那句「按画像降级路径继续」。

**第 3 轮（收敛）**：两图全图 pipeline rc=0、分带 rc=0、**8/8 子图跑到 inspect**、**零 Traceback**。
8 带均为 `inspect rc=2`（门禁 FAIL → 拦在人工裁决口），失败项集中在
C0/C2/C3/C6（箱归属）+ C10（图签 vs 系统图逐栋比对）；WARN 集中在 C1/C4/C7。

**教训（可跨图复用）**

1. **「量了没接线」会以新形态反复出现**：同一个量（地块锚点）被度量、被存进产物、被写进文档，
   却没有任何执行方消费 —— 冷启动时必须顺着「画像字段 → 谁读它」逐个走一遍。
2. **切分口径必须有反例证据才准写死**：本轮的「切点取锚点 y」在纸面上完全合理，
   实测每带吞 4 条才算证伪。**边界类参数的默认值必须拿真图跑一遍，不能只凭推理**。
3. **退出码的措辞也是契约**：`rc=3` 同码两义（「不适用、继续」vs「不适用、中止」），
   措辞与行为不一致时，人会照措辞行动 —— 日志里说"继续"就必须真的继续。
4. **日志格式串也是代码**：改一条 `log.info` 的占位符，必须与实参逐个数对齐；
   这类错在「只跑被测命令」的自测里完全看不见 —— **改动落在哪一侧，就必须冒烟测哪一侧**。
   （本轮正是「只测了 split-band、没测 probe」，把 probe 打崩了两轮才抓到。）

### 2026-09-18（六十九）：三轮迭代实跑收敛 —— 「规则写了、没有执行方」第五例（图签第二来源）

**背景**：对一张 7 栋楼 / 12 单元 / 17 箱的 FTTH 竣工图，用 `ftth.cmd pipeline` 连跑三轮，
每轮「跑完 → 定位问题 → 修 → 重跑」。第 1 轮 rc=0 全绿，但绿得不干净。

**第 1 轮暴露（2 个真缺陷 + 2 个描述/命名问题）**

| # | 现象 | 根因 | 处置 |
|---|---|---|---|
| 1 | 12 个单元各带 B1/B2 两个楼层刻度行、户数与布线皆空，**共 24 行**从 C5 清单里凭空消失，C1~C9 无一提及 | C5 用 `if hu is not None or bx is not None` 过滤 —— 把「**有刻度但图上没写户数**」与「**本图没有这一层**」当成了同一件事 | C5 逐条登记该批层行并判 WARN。判据：**「图上确实没有」与「我没读到」必须可区分**；只报事实、不下结论（地下车库/设备层/储藏层都可能是图纸事实） |
| 2 | 画像早已把 `titleblock_annotation` 判为 present 并写明「构成三来源协议的第二来源」，但 `pipeline` **无该阶段**、C1~C9 **无该检查** —— 这条独立来源验证长期空转（实测其读数与系统图逐栋一致，**却从未被比对过**） | 规则写在文档里、无代码执行（本技能**第五例**） | 新增 `titleblock` 阶段（产出 `<outdir>/titleblock.json`）+ 新增 **C10** 逐栋比对；未提供读数时判 SKIP 并写明「本次未做」，**不得判 PASS** |
| 3 | coverage 的 `自检_v底vs箱符号` / `箱符号y` 字段名 | 本图无分纤箱图形符号（画像 `[SYM]` 无候选），实际比的是**编号文字 y**；输出 `说明` 里写对了、键名没写对，易被读成"有图形符号佐证" | 记录待改（牵动 coverage 键名与 C7 透传，本轮刻意不动，已留证） |
| 4 | `gen_addressbook.py` 回读打印「行数恒等式成立（1 + 313 + 1 = 315）」 | 那个 `1` 是**模板自带的 AIGC 水印行**，不是合计行；该"恒等式"随模板行数自洽，**无独立验证力** | 记录待改 |

**第 2 轮暴露（修复引入的新问题 + 既有潜伏缺陷）**

| # | 现象 | 根因 | 处置 |
|---|---|---|---|
| 5 | 新加的 `titleblock` 阶段**静默跳过**（打印"配置未给出文字图层"） | 图层读的是 config **顶层** `text_layer`，实际嵌在 `suggested_params.text_layer` | 三级取值：`titleblock_layer_candidates.候选图层[0]`（probe 专为该脚本产出的 advisory 字段）→ `suggested_params.text_layer` → 取不到就**跳过不猜**（不硬编码图层名） |
| 6 | 经 `ftth.py inspect` 调不出 C10：**rc=2 且零检查项输出** | 只给 `inspect_closure.py` 加了 `--titleblock`，没给 `ftth.py` 的 inspect 子命令加 → argparse 直接判 unrecognized arguments、脚本根本没跑 | 两处补齐（参数定义 + 转发）。**本体冒烟测试全绿也测不到，集成调用才抓到** |
| 7 | 给 `coverage-vshape` 传 `--wire-layer BZ` → `unrecognized arguments` **直接 rc=2** | vshape 完全不消费连线/符号图层（源码 0 命中），pipeline 却无条件追加；**本图画像两图层均 null 才侥幸未触发**，换一张 `dedicated_wire_layer=present` 的图即挂 | 按 `cov_cmd` 分派：`--wire-layer` / `--fx-symbol-layer` / `--bldg-map` **只有 `coverage` 消费**，不再一律传 |

**第 3 轮（收敛确认）**：全新产物目录、零残留、不 `--reuse-geom`，8 阶段全跑。
`parsed.json` / `coverage.json` / `titleblock.json` **sha256 与第 2 轮逐字节相同**；
`inspect.checks/fails/warns/rc` 与 `profile` 的全部实质 key 一致（差异只在路径字段）→ **确定性成立**。

**可复用的三条（已同步进 SKILL.md / references）**

1. **规则 / 契约必须有执行方** —— 本条已是本技能第 5 次复发。新增任何"必须核对 X"，
   必须**同轮**落地"谁的代码、在哪一步跑它"；否则一律视为未完成。
2. **同类缺陷先 grep 全量再修** —— `--bldg-map` 那处早已按子命令分派，`--wire-layer` /
   `--fx-symbol-layer` 却漏了。**只修报出来的那一个，等于留哑弹**。
3. **冒烟测试分两层** —— 本体（直接调脚本）+ 集成（经 `ftth.py` 入口 / 经 `pipeline`）。
   第 6 项正是"本体 5 个用例全绿、集成必炸"。用例须含零输入 / 坏输入 / 路径不存在。

**改动文件**
- `scripts/inspect_closure.py`：C5 扩展登记「有刻度无户数」层行；新增 C10；新增 `--titleblock`
  （`dest=titleblock_json`）；机读产物加 `titleblock` 字段
- `scripts/ftth.py`：`_PIPE_STAGES` 增 `titleblock`；新增 ③b 阶段；`inspect` 子命令补
  `--titleblock` 与转发；图层参数按子命令分派；后段 `stop_idx` 索引顺延（4→5→6→7）
- `references/step2_selfcheck.md`：C1~C9 简表 → C1~C10 表（按实际编号）+ C5 扩展与 C10 详述
- `references/scripts_reference.md`：pipeline 阶段链 / `--stop-at` 取值 / 产物清单 /
  `titleblock` 阶段说明 / 图层参数分派 / `inspect` 示例
- `SKILL.md`：**仅改引用名**（受 47,000 B 预警线约束，净增 2 字符）

**待办（本轮刻意未动，已留证）**
- 缺陷 3：`自检_v底vs箱符号` → 应更名为「v底 vs 箱号文字」
- 缺陷 4：`gen_addressbook.py` 行数校验的描述与独立验证力
- rc=2 语义重叠：argparse 的「参数错误」与 inspect 的「检查 FAIL」同为 rc=2，
  `pipeline` 摘要里无法区分（本轮实测踩到一次）

### 2026-09-18（六十八）：SKILL.md 体量外移 + 体量闸门落地 —— 「规则写了、没有执行方」第四例

**背景**：SKILL.md「参考文件」节自订体量预算纪律（预警线 47,000 B / 硬上限 49,000 B，依据是
宿主对工具输出的通用截断实测 51,200 B、无开关），且（六十六）末尾已把它记为「附带发现…须外移
降至阈值内」。但实测三件事：

- SKILL.md **55,391 B** —— 超硬上限 6,391 B、**超宿主截断线 4,191 B**；
- 按 51,200 B 截断，**被切掉的正好是该条纪律的后半段 + 整张 references 索引表**
  （11 个文件的入口表）—— 文件都在、入口没了；
- `47000 / 49000 / 51200` 在 `scripts/` 全部脚本中 **0 命中** —— 规则写了、**没有执行方**。

这是本技能内「契约 / 闸门只写在文档里、无对应执行方」的**第四例**（前三例：迁移禁止表无核对器、
`result_origin/confirmation` 只定义不产出、本项体量闸门）。

**处置**

- **外移**：SKILL.md **55,391 → 47,616 B（降 14.0%）**。新建 `references/pipeline_details.md`
  （约 12.6 KB），把「Step 1b 结构化解析」的**细则层**下沉 —— 脚本行为、参数细节、口径A 与
  回填实现、`geom.json` schema 三坑、冷启动 vs 热启动、体量阈值依据。Step 1b 本段
  11,679 → 5,016 B；SKILL.md 只留**协议与硬约束**，与其自身「只承载协议 / 状态机 / 硬约束 /
  名目清单」的定位一致。另压缩 Step 2 必查项、铁律 ①~⑨、体量纪律段等冗余表述。
  **守恒校验**：旧 Step 1b 段内 77 个反引号字面量（命令 / 字段名 / 口径名）逐一对拍，
  仅 1 个未命中，且属**原文档笔误修正**（`ft.py _pipe_fxmap_gate` → `ftth.py _pipe_fxmap_gate`）。
- **闸门落地**：新增 `scripts/check_budget.py`（入口 `ftth.py budget`）。阈值**一律从
  `version.json` 的 `budget` 段读**（单一权威）；脚本内只留兜底值并**显式标注实际来源**，
  不制造第二套阈值口径。rc 沿用 L1-C2 语义（0 通过 / 2 超限 / 3 无可核对象 —— 无 SKILL.md 时
  **刻意不给 0**）。**SKILL.md 与 `references/*.md` 单文件同受约束**（否则闸门只是把问题搬家）。
- **接入主入口**：`check_transitions.py`（六十五 已建核对器本体，但**未接线**）一并接入为
  `ftth.py transitions --project-dir <目录>`；`budget` / `transitions` 加入 `--dxf` 免填白名单。
- **version.json** 增 `budget` 段（三阈值 + `applies_to` + 依据说明）。
- **SKILL.md** 登记两处入口：Agent 状态机节写明核对器命令，Step 1b 子命令表补 `budget` /
  `transitions`（**有执行方就必须有可见入口**）。

**验证**

- `ftth.py budget` 真机 rc=0：SKILL.md 47,616 B（[WARN] 触预警线 +616 B）；`references/`
  12 个文件全部在预警线内，最大 `scripts_reference.md` 45,972 B。
- `check_budget.py` 自测 **9 用例全绿**，含「零输入 / 无 version.json（走兜底）/ 无 SKILL.md /
  references 为空 / 超硬上限 / 超宿主截断线 / references 单文件越界」。
- `ftth.py transitions` 真机 rc=3（无台账目录 —— 刻意不给「通过」）。

**未改**：SKILL.md 条款本身（只外移细则与压缩表述，**无一条判据被删**）；`ledger_state.py`
及全部既有脚本逻辑；平台 `.backup/`。外移前全量备份在技能目录之外
（工作区 `.audit/backup_ftth-address-extractor_20260918_1057`，54 文件 / 3,461,343 B 逐文件一致）。

**流程复现命令**

```
ftth.py budget                       # 体量闸门
ftth.py transitions --project-dir <目录>   # 迁移门禁
(Get-Item "<技能目录>\SKILL.md").Length     # 记录改前改后字节
```

### 2026-09-18（六十七）：多轮冷启动实测（另一份图）—— 「文字的每一次出现 ≠ 一个对象」与「本机全绿 ≠ 跨语言可读」

**背景**：对另一份实测图按「连续跑 5 轮、每轮修完再跑下一轮」冷启动复跑（多地块合图，按 y 带切 8 个子图逐带跑）。
逐轮暴露并修复的问题如下，**只固化通用规则**；逐值对账与验收判据见当轮案例报告。

**根问题一：同一编号在图上多处出现，被判成「多个对象」**
箱编号在平面图 / 箱表 / 系统图各印一次 → 解析侧把**每一次文字出现**当一个对象
（实测某带 22 个编号被计成 66 个，恒 3 倍）。
→ 判据（客观、可复核）：**编号是对象的唯一标识** ⇒ 同编号的多次文字出现 = 同一对象的多次绘制。
→ 纪律：仅当各实例的**关键字段一致**（此处为安装楼层）才收敛为一条，主记录保留、其余实例坐标写入
  「多处出现」证据（证据不丢，可回原坐标追溯）；**不一致 ⇒ 不自行择一** —— 全部留存、标 `pending`、
  登记「需人工裁决」，由 `inspect` C9 拦下、不得进入成品。

**根问题二：「真重号」不能一概拒绝，要用实例坐标配对**
上游把同编号的多处出现**一律**判为重号 → 下游「仅接受唯一映射」→ 整批丢弃
（实测某图 22 条对照表一条没挂上，对象数直接归零）。正确做法分两步：
① **收敛判据**：若其中一处在描述里**直写**了规范定位（如「N号楼M单元K层」）且归一化后**唯一**，
   则这些出现属**伪重号**（同一对象的重复绘制），收敛为单实例；
② 仍有多实例的，按**实例坐标**与对照表条目配对（`(编号, x)` 唯一命中）—— 属**测量**，不是推理。
→ 未配对的实例**不得**退回「按标题 x 区间硬切」定归属（硬约束②明文禁止），否则会凭空生成假对象；
  应登记留证、**不新增对象**。

**根问题三：跨来源同一语义、写法不同，比对前必须归一化**
上游对照表的「楼栋」字段写的是带单元/层的**复合描述**，下游按前缀匹配标题锚点 → 匹配不上、
**整批静默丢弃**（日志只写「改派 0 个」，看不出是被丢掉还是本身为空）。同类第二处：`N#楼` 与 `N号楼`。
→ 落地：① 产出侧把复合描述**拆成规范字段**（原文另存留证）；② 消费侧匹配前先**归一化**
（`#`/`＃`/`号` 等价、去单元/层后缀）；③ 解析不到锚点时**必须登记**（点名编号 + 原值 + 候选锚点），
**不静默 `continue`**。

**根问题四：产物里写了非标准 JSON（本轮新增闸门）**
解析产物把「未测得」的距离写成 `inf` → `json.dump` 输出 `Infinity`，而它**不在 JSON 规范内**：
严格解析器（JS / Go / 多数工具）会拒绝**整份**文件，而 Python 自己的 `json.load` 是宽容的
⇒ **本机全绿、跨语言全线不可读**。
→ 落地：① 非有限浮点一律写 `null`（**「未测得」≠ 0**）；② 清洗函数收进公共模块**单一实现**，
  写 `.json` 一律走它（命中项登记进产物，不静默丢）；③ 流水线出口**扫产物目录**，
  命中即把 rc 抬到 2，不得静默出关。
→ 纪律：本仓第二次踩到同一点 —— **新增/修改闸门必须补「反向用例」**（人为注入坏值，确认真的拦住）；
  只跑正向无法区分「闸门通过」与「闸门根本没生效」。本轮正例 8 带 0 假警、反例逐条命中（含坏 JSON）、
  边界（目录不存在 / 空目录）不崩，才算通过。

**本轮结果（口径供复盘）**：8 带冷启动，**7 带 rc=0**；1 带 rc=2，唯一 FAIL 为
「同一编号在对照表内有 4 个互相矛盾的定位（箱表直写 2 处 + 图上符号 2 处，安装楼层互不相同）」
—— 解析侧未自行择一、如实标 `pending`，属**出口闸门的正确动作**而非缺陷，已按第④类报人。

### 2026-09-18（六十六）：多轮冷启动再测 —— 「契约在文档里、不在产出方」与「闸门拿被检对象当真源」

**背景**：按"连续跑 N 轮、每轮修完再跑下一轮"的方式，对实测某图冷启动独立重跑 5 轮，
逐轮修复暴露的问题；出表后做回读校验，暴露 3 项 FAIL。本条只固化通用规则，
逐值对账与验收判据见当轮案例报告。

**根问题一：同一条契约，文档写了、产出方没落**
`references/addressbook_template.md` 明写「格式严格跟模板：列结构、列顺序、**表头名称**…全部以模板为准」，
但出表脚本写表头时复用了"字段映射用的归一化函数"（该函数会去掉表头尾部的 `(必填)` 提示），
导致产出的 5 个列名与模板逐列不一致，而生成侧毫不知情。
→ 教训：**一个函数服务两件事时，输出侧必须重新确认语义** ——
  "归一化以便内部匹配"与"原样对外输出"是两件事，复用前者去干后者，必然悄悄改写对外契约。
→ 落地：输出表头改为**原样照抄模板**；归一化函数只保留"内部字段映射"职责。

**根问题二：跨源同一语义、写法不同，比对前必须归一化**
本链路里"楼层"有三种写法：产物按模板走中文（`一层`）、解析/覆盖产物走 `NF`。
回读脚本直接按字符串比对 → 报出上百处"数值不一致"，**全部是写法差异引起的假 FAIL**。
→ 教训：**多源对账的第一步是"同一语义归一化"，不是"比字符串"**；
  否则假 FAIL 会掩盖真 FAIL（真正的不一致淹在噪声里）。
→ 落地：回读侧统一先把楼层写法归一到整数再比。

**根问题三（由冒烟测试暴露）：闸门不得拿"被检对象自己生成的值"当期望**
首版出口闸门把"内存里的表头变量"当作期望值，去比对"磁盘产物回读的表头"。
反向用例（人为把表头改坏后出表）跑出 **RC=0 + 报"逐列一致"** —— 因为两边同源，
错了也一起错，**闸门自证清白**。改为期望值取 **模板原文**后，反向用例正确报错。
→ 教训：**闸门只认真源**。期望值若来自被测对象自身构造的中间量，闸门恒真，等于没有闸门。

**新增：出表环节的出口断言（`gen_addressbook.py`）**
保存后回读产物，断言 ① 表头逐列 == 模板原文；② 行数恒等式（表头 1 + 数据行 + 模板尾行去重后 = 实际行数）。
任一不成立 → 打印差异明细并 **exit 3**（语义同"未交付"）。

**纪律（自测用例的盲区，实测第二次踩到）**：新增/修改核对器、闸门类代码，
**必须补一条"反向用例"** —— 人为制造它该拦住的错误，确认它**真的拦住**。
只跑正向（"没报错"）无法区分"闸门通过"与"闸门根本没生效"。
本仓两次教训都出自这一点（前次：13 个自测全绿、真实目录一跑即挂）。

**附带发现（本轮未处理，报人）**：`SKILL.md` 实测 53,798 B，
既超本仓自订硬上限 49,000 B，也超工具输出实测截断线 51,200 B ——
**首屏加载会被截断**，须外移降至阈值内（属独立维护项，非本链路缺陷）。
修订记录 / 案例叙述 / 参数表一律写本文件或 `references/`。

### 2026-09-18（六十五）：第二轮多轮迭代 —— 「契约只写进文档、没落到产出方」与「空集合被判 PASS」

**背景**：承接（六十四），对实测某图再连跑三轮（每轮独立副本 + 独立产物目录 + **逐轮冷启动 + 逐轮清几何缓存**）。
第 1 轮 rc=0、箱集已满，但仍暴露 3 处潜伏缺陷；整改后第 2 轮 rc=0；第 2 轮又暴露 2 处新缺陷；
整改后第 3 轮全绿。三轮 count-box 数值（皮线端点数 / 归层后总户数 / 分级统计）**逐值相同**，
说明整改未触碰户数测量链路。逐项对比与验收判据见当轮案例报告，本条只固化通用规则。

**根问题一（第 1 轮暴露）：契约写成检查项，却没写进产出方**
1. 「结果状态闭合」检查（`result_origin` / `result_confirmation` 两字段）**只定义了检查方**，
   产出方脚本从未写入这两个字段 → 检查侧对缺字段一律 SKIP，界面上一片"绿灯"，
   实际是**半个产物从未被覆盖**。契约写在 SKILL.md，却没落到产生该字段的每个分支。
   → 教训：**「检查项落地」≠「被检查项落地」**。新增字段类契约必须**成对落地**（产出方写 + 检查方读），
   且产出方有**多个口径分支**时（对照表口径 / 区间法口径 / 回填口径）须**逐分支**落地，漏一个就留下盲区。
2. 「楼层表直读」把「全图楼层表户数列**皆空**」算成 **合计 0 → INFO** ——
   「读了、结果是 0 户」与「根本没有可读数据」被混为一谈，前者会被下游当成有效结论。
3. 「同单元跨层户数一致性」在「纳入核验的单元数 = 0」时判 **PASS**（理由写作"0 个单元各层户数一致"）——
   **空集合被判通过**。→ 统一改：两者遇空集合一律 **SKIP**，并在 detail 里明写
   「本图户数须由图示法提供，**不得读作合计 0**」，把"为什么 SKIP"写进产物而非留在人脑里。

**根问题二（第 2 轮暴露）：给人看的定位键，各脚本各自拼**
4. 待确认清单的「对象」名在多种命名约定间漂移：`4#楼4#配套楼/FX22#`（楼号被重复并入）、
   `7#楼7#楼1单元`（单元自带「N#楼」前缀又被二次拼接）。根因是拼接处用
   **字符串前缀判重**（`unit.startswith(bldg)`）：遇 `4#配套楼` 这类**楼号本身就带后缀**的值判重失效；
   无条件拼接又会给自带前缀的单元加第二层前缀。
   → 新增**统一取名函数**，按「**同一楼号**」语义判重（从楼号正则提取编号后比对，命中则不再拼接），
   三处调用点全部改为走它。教训：**对象名是给人看的定位键，跨脚本必须同一实现**；
   散落各处的字符串拼接迟早漂移，且漂移只在人工读清单时才被发现。
5. 「结果状态闭合」在**只扫到 parse 一侧**、coverage 一侧零字段时反而报
   **PASS「全部结果均已定案」** —— **假绿灯**：一个来源没被核到，却显示整体通过。
   → 改为**先申报扫描了哪些来源**，对「已提供但零字段」的来源显式报 WARN，并写明
   「未被结果状态闸门覆盖，**不得视为已核**」。

**可复现性对账**：第 2↔3 轮（整改前 / 整改后）做**归一化逐值比对**，差异**恰好且仅有**本轮两处整改
——coverage 侧 5 处对象名 + inspect 侧的状态变更与 1 条新增 WARN（含同一批对象改名）；
parsed / count-box / fxmap / profile **零差异**。证明整改**相互隔离、未产生回归**。

**通用教训（跨项目）**：
- **新增字段类契约必须成对落地**：产出方写、检查方读。只落检查方 → 闸门恒 SKIP（假绿），比不检查更危险。
- **检查只覆盖部分来源时，缺来源要报 WARN，不能默认 PASS** —— 禁止用"扫到的部分全绿"冒充整体通过。
- **空集合一律 SKIP**：既不得判 PASS，也不得折算成 0。此条须在**每个检查点逐一落地**，只在个别处生效不算落地。
- **面向人的标识必须走同一实现**：判重用「同一实体」语义（编号比对），禁用字符串前缀判重与各处自行拼接。
- **整改必须可对账**：改动前后做归一化逐值比对，差异集合应**恰好等于**本轮改动项；出现多余差异即回归，须先查清。
- 多轮迭代的价值在于**迭代本身就是探针**：第 1 轮的"绿灯"掩盖了第 2 轮才会暴露的命名漂移与假绿灯 ——
  **跑得动 ≠ 跑得对**，每轮都要重新审视闸门自身。

### 2026-09-18（六十四）：多轮迭代实测暴露的缺陷整改 —— 一条纪律只落地了一半

**背景**：对实测某图连跑三轮（每轮独立副本 + 独立产物目录 + **逐轮冷启动**），
每轮抛出的问题先整改回真源、再跑下一轮。整改前 parse 侧分纤箱为**空集**且 `inspect` rc=2；
整改后两轮均为满集（图内全部箱编号）且 rc=0，两轮业务产物**逐值一致**（仅耗时字段不同）。
逐项对比与验收判据见当轮案例报告，本条只固化通用规则。

**根问题（值得记住的形态）**：硬约束②「楼栋/单元归属必须以图纸自带分纤箱总图对照表为准，
严禁用标题 x 区间硬切」**只落在 coverage**（它早有 `--bldg-map`），**parse 侧根本没有该参数**。
当箱编号集中在独立的总图对照表图区、落在所有楼栋 x 区间之外时，parse 逐栋得空集而
**rc 仍为 0 —— 静默丢数，不跑 inspect 不会察觉**；而总图对照表其实已被成功提取，
却只被拿去给「不存在的箱」回填字段，等于空操作。
→ 教训：**同一条纪律必须在每个消费该数据的消费方逐一落地，不能假设「上游已处理」。**

1. **`parse --bldg-map`（新增）** —— 按对照表定楼栋/单元归属，三条边界：
   ① 对照表无该编号 / 重号 / 楼栋名不在本图锚点内 → **保持原硬切结果并留痕，不猜、不静默择一**；
   ② 对照表「楼栋」值可能带单元后缀（`N#楼M单元`）而锚点名不含单元 → **须前缀解析后再匹配**，
      否则 `not in` 会静默丢掉绝大多数条目，只剩无后缀的零星命中；
   ③ 改派必须从**全图文字**出发，不能从按楼栋切好的子集里找 —— **丢失物本就不在其中，必然 0 命中**。
   产物写顶层 `分纤箱提取状态` 闸门 + `BDGMAP归属` 留痕段。
2. **阶段顺序改为 `geom→probe→plan→fxmap→parse→coverage→inspect`** —— `fxmap` 必须在 `parse`
   **之前**：parse 与 coverage 都要用对照表定归属，排在其后会变成「先用被明文禁止的方法切完、
   再拿正确数据去补下游」。同一份对照表在 parse（`--bldg-map`+`--fx-map`）与 coverage（`--bldg-map`）
   两处复用、同源。
3. **对照表认领箱的安装楼层取「口径A：图上直写」** —— 箱编号位于总图图区，其 y 与楼栋系统图楼层带
   **不是同一坐标系**，直接套用会算出无物理意义的层号（实测出现 `WF`/越界层）。判据客观
   （对照表唯一映射 + 非空安装楼层）→ 属「**有判据自判**」（是测量，非推理）；区间法原值降级保留在
   `区间法参考值`/`区间法参考误差` 供审计，**证据不丢**；双源交叉检查仍照跑作第二来源。
   （**安装楼层共 3 种口径**：口径A 图上直写／口径A 图上直写（总图对照表）／口径B 区间法。）
4. **`inspect --fx-pattern` 缺省时从 parse 产物自描述读取（`参数.fx_pattern`），pipeline 显式转发** ——
   内置默认正则与实际编号形态不符时，会把 parse 侧**全部**箱误判成「图上无编号文字」，
   形成**纯假警报并把真 FAIL 整个淹掉**。自描述须过滤「未提供（…）」类提示语 —— 它不是正则。
5. **写 `--json` 前建父目录** —— 目标目录不存在时 `open()` 直接 Traceback（rc=1、不落产物、
   报错点远离调用处）。**全量扫描 17 个写产物的脚本，16 个已做、仅此 1 个漏网** →
   按「先全量 grep 同类模式」一次找全，**未只修报出来的那一个**。

**通用教训（跨项目）**：
- **`log.info` 走 stderr** —— 直调子脚本只抓 stdout 会误判「代码块根本没执行」，
  定向验证必须 **stdout+stderr 全抓**。
- **耗时不可横向比** —— `dump_geom` 经 `load_geom` 复用 `<DXF>.geom.json` 缓存
  （同图冷启动 ≈45~50s / 热启动 ≈10s）；多轮可复现检验**每轮必须先清缓存**，
  否则把缓存收益误读成优化收益。
- **比对走「归一化后按值」** —— geom 含浮点末位抖动，逐字节比对会**误报 DIFF**。
- **验证用的临时产物不要留在被审目录**，否则破坏「不参考历史记录」的干净前提。

### 2026-09-18（六十三）：v3.1 三项增量 —— 结果状态契约 / 证据来源等级 / 容量预算闸门

**背景**：外部评审（ChatGPT《FTTH_skill_v3_优化建议》v3 及其修订稿）与亚伦评审三方对齐后，
确认有效缺口只有三项：结果状态体系、证据等级体系、SKILL.md 容量治理。其余（DXF 数据接口契约 /
测量算法工具化 / Agent 决策表 / 架构分层）经逐项核对**均已实现**，不予改动；「矛盾等级 C0–C4」
**不采纳为处置规则** —— 其「C0 表达差异 → 自动归一」通道会拆掉 §5.1 归一化硬边界 1
（`*16` 乘数不是归一化，实测同图两版交付差 122 户 / 其中 120 户由此而来）。

1. **L1-C8 结果状态契约（新增）** —— 产物中每个结论须带两个**机器可枚举**字段：
   - `result_origin` = `measured` / `derived` / `unresolved`（结论怎么来的）
   - `result_confirmation` = `settled` / `pending`（定案没有；`pending` **禁止进成品**，依 §5.6 底线 3）
   - **两字段正交，不得合成单值**：外部评审原提 `confirmed/calculated/suspected/unknown` 单值方案，
     无法表达「`derived` **且** `pending`」（例：按 `*16` 算出的户数 —— 算得出，但须人裁）；
     合成单值必丢一半信息。
   - 与 C1 信号层 `present/absent/variant/unknown` **分层、不共用枚举**：C1 答「图上有没有」（**事实层**），
     本契约答「怎么来的 / 定案没有」（**结果层**）。
   - **不用 `confirmed`**：与 I5-A「用户裁定」语义撞车。

2. **`inspect_closure.py` 新增 C9 结果状态闭合（新增）** —— 递归扫描 parse / coverage 产物，
   `pending` 或 `unresolved` 非空即 **FAIL**；产物未携带本字段判 **SKIP**
   （老产物不得因缺字段被误拦成 FAIL）。
   - **为什么必须配校验**：只定义字段而不校验，字段会退化成没人读的自由文本 ——
     前车之鉴「判定依据 / 依据来源」：SKILL.md 写了 4 次，脚本侧除 `analyze_coverage.py` 外几乎没产出。
   - 实测 4 组（`_t_c9/`）：`A_pending` rc=2 ✓ ／ `B_nofield` SKIP rc=0 ✓ ／
     `C_settled` PASS rc=0 ✓ ／ `D_unresolved` rc=2 ✓。

3. **§5.7 证据来源等级（新增，operations_discipline.md）** —— `E-DXF-TEXT` / `E-DXF-GEOM` / `E-PROC` /
   `E-IMG` / `E-HUMAN-RULING` / `E-HUMAN-GUESS`；SKILL.md **L1-C9** 只留要点与指针。
   - **`E-DXF-TEXT` 与 `E-DXF-GEOM` 之间无全序**（谁优先由场景规则定；箱位即几何 > 文字 ——
     现成规则「位置来源以图形符号开头才可信，编号文字为回退值」）。外部评审的 `E1~E5` 编号全序方案
     与该事实冲突，故不采用。
   - **「人工」拆成两级**：`E-HUMAN-RULING`（用户本会话裁定＝I5-A，**最高**）与
     `E-HUMAN-GUESS`（肉眼推测，最低）。笼统把人工定为最低会与 I5-A **直接打架**。

4. **体量预算闸门（收紧）** —— 预警线 **47,000 B**（触及即新增默认进 `references/`）／
   硬上限 **49,000 B**（触及即禁写）／ `references/` 单文件**同受 47,000 B 约束**（否则闸门只是把问题搬家）／
   **净增为零原则**（每加一条须同时外移等量旧内容）。
   - **阈值实测依据（勿凭感觉调）**：本文件可外移的明细约 **5.3 KB**（实测 48,822 → 43,505 B），
     再往下动就是 L0/L1 硬约束本身；单条新契约约 1~2 KB。曾试设预警线 46,000，
     实测仅剩 **150 B**，触线即无路可走 —— 预警线必须在硬上限**之前**留出可操作空间，故上调至 47,000。
   - 本轮净变化 **48,822 → 45,850 B（-2,972）**：外移 5,317 B（Step 1b 参数表 / Step 1c 户号规则 /
     模板与环境 / Step 2 明细 12 条 / 九级命令块 / 探查清单 / 三要素个案形态列 → `references/`），
     新增 C8 + C9 + 预算条款 2,345 B。
   - **个案形态列已移出「三要素」表**（原含柳辛庄 / 凤鸣朝阳 / 云峰三个项目名），遵循「个案细节不进技能」。

5. **未做（明确记录，防止下轮重复提）**：不拆 `rules/` 子目录（L0/L1 必须首屏可见，
   移走＝Agent 不读＝等于删除）；不新增 C0–C4 自动处理规则；不重新设计解析层；不改架构分层。

### 2026-09-17（六十二）：可用性优化四项 —— `pipeline` 流水线 / 配置噪音治理 / C8 跨层户数一致性 / `--addr` 空串语义

**动机（实测数据）**：一次「从零重跑」实测 12 次调用共 **66.05s**，其中 **约 43s 是纯进程启动开销**（占 65%）。
逐层拆解：`ftth.cmd` 每条命令依次起 **4 层 Python 进程** —— ① 探测 `-c "import ezdxf"` **1.93s**
（裸解释器 0.62s + import ezdxf 1.31s）② `_launch.py` **1.13s** ③ `ftth.py` **0.65s** ④ 子脚本 0.63s＋真实计算。
即每条命令固定付 ≈3.7s，与图纸大小无关。

1. **`ftth.py pipeline`（P0，新增子命令）** —— 一条命令串跑
   `geom → probe → plan → parse → coverage → inspect`，各阶段以子进程直调 `ftth.py`，
   **不再经 `ftth.cmd` / `_launch.py`**，固定开销只付一次。
   - **语义边界（刻意）**：① **只解析、不做裁决，不含 `gen`** —— 出表必须等人工裁决（覆盖 / 安装楼层 / 待确认项），
     流水线不得替人拍板；② **不静默续跑** —— 任一阶段 rc≠0 即停并原样返回该 rc；仅 rc=3（本图确实不提供该子任务数据）
     不中止，记为该阶段「不适用」；③ 产物用固定文件名落 `--outdir`，之后仍可单条命令接着跑或重跑其中一段。
   - **覆盖方法由画像决定**：读 `handoff.②系统图选法.覆盖范围.脚本` 映射为 `coverage-vshape` / `coverage`，
     **不在此处二次推断**；画像申报 `absent` 时该阶段记 rc=3 合法缺席。
   - `--project-dir` **显式透传**给 `plan`（不传会让 `intake_table` 留 `unknown`）。
   - 附带 `--reuse-geom`（缓存比 DXF 新则复用）/ `--stop-at`（分阶段调试）/ `--quiet`（各阶段输出落 `logs/`）。
   - **实测**：同一张图、同 6 个阶段，逐条经 `ftth.cmd` **38.74s** → `pipeline` **18.37s**（省 20.37s / 52.6%）；
     冷缓存下 24.99s。耗时台账落 `<outdir>/pipeline_timing.json`。

2. **配置噪音治理（P1）** —— 原实现把整份 `suggested_params` 逐命令喂下去，本命令用不到的键一律报
   `[WARN] 不是有效参数` 并计入 `[CONFIG-IGNORED]`。**实测 `inspect` 一次刷 11 行**，
   把真告警（如「楼号序列缺号」）整个淹没。
   - 新口径：键在**本工具链别的子命令或独立脚本**里存在 ⇒ 属正常（本命令不需要），只汇总**一行** `[config-skip]`；
     键在任何地方都不存在 ⇒ 才是拼写错误，维持原 `WARN` + `[CONFIG-IGNORED]` 汇总
     （`FTTH_STRICT_CONFIG=1` 语义不变）。
   - **已知键收集必须含「不经 `ftth.py` 调度的独立脚本」**（`extract_fx_map.py` / `ledger_*.py` /
     `read_titleblock_households.py` 等），实现为**惰性**扫描同目录 `*.py` 的 `add_argument("--xxx"`。
     **实测教训**：只收调度层子命令参数时，`bldg_pattern` / `proximity_tol`（实属 `extract_fx_map.py`）
     会被误报成「疑似拼写错误」—— **键名与它的来源要一起核，不能只读报错文本下结论**。
   - **实测**：`[CONFIG-IGNORED]` **6 → 0**；`[WARN] 配置文件中的键` **6 → 0**；
     `[WARN]` 行总数 **7 → 1**（留下的正是那条真告警）。

3. **`inspect_closure.py` 新增 C8「同单元跨层户数一致性」（P1）** ——
   - **动机（漏检实例）**：某图某单元的楼层表中，标准层每层 2 户、**唯独某层是 1 户**，
     当时**没有任何检查项标出**，报告以「整图户数合计 ✓」一句带过。
     **户数守恒（合计对得上）与逐层分布合理是两件事** —— 合计能对上，恰恰掩盖了单层偏离。
   - **判据（通用，不绑项目）**：只用一个单元内「户数」字段自身，**不引入层号、户数绝对值等任何项目特有常量**。
     分档：种类=1 → PASS；种类=2 且有多数 → 少数层为偏离（WARN）；种类=2 平票 或 种类≥3 → 只报分布、不判偏离；
     有效层数 < 3 不纳入。**判 WARN 而非 FAIL** —— 商铺层 / 架空层 / 跃层 / 顶层退台都可能是合法图纸事实，
     **本项只标出「哪单元哪层与其余层不同」，不下结论**，与 L0-I4「发现要主动、裁决交人工」一致。
   - **实测**：精准抓出该偏离层，其余 11 个单元全部一致。

4. **`gen_addressbook.py` 写明 `--addr` 空串语义（P1）** ——
   **传空串与省略该参数行为不等价**：判断点在脚本 `if args.addr:` —— 传空串 ⇒ 五级全空；
   **省略该参数（值为 `None`）⇒ 回退去读模板第 2 行示例值**（模板读取段）。
   实测某项目模板第 2 行是 `<省>` 类占位文本、被 `_is_placeholder()` 拦住，
   **但换成带真实数据的模板就会静默填错地址**。已在 `--help` 与运行时日志两处写明。

5. **`plan_methods.py` 的 `intake_table` 改报相对路径（P2）** ——
   原只报文件名。**实测某项目根目录与其归档子目录各有一份同名 xlsx，打印出两个完全相同的名字**，
   看着像脚本重复枚举（歧义），实为两处各一份。改报相对 `project_dir` 的路径后一眼可辨。

6. **SKILL.md 同步**：子命令清单加 `pipeline` + 一行用法；效率纪律的「连跑 probe→plan→parse→inspect」
   改为 `ftth.py pipeline`；inspect 核查项 `C1~C7` → `C1~C8`；出表章节写明 `--addr` 空串语义。
   **体量**：48,329 → **48,822 B**（中途加到 49,007 触及预警线，按「触及即先压缩」收紧**本次新增表述**，
   未删任何既有条款）。预警线余 **178 B**，硬截断余 **2,378 B**。

**风格实测（改前逐个实测，不作推断）**：`ftth.py` / `gen_addressbook.py` / `analyze_coverage.py` /
`parse_dxf_structured.py` / `ftth.cmd` / `SKILL.md` = **CRLF**；`inspect_closure.py` / `plan_methods.py` /
`ftth_common.py` / `ftth_batch.py` / `SKILL_CHANGELOG.md` 等 = **LF**；**全部无 BOM**。
本次改动一律用 Python 打补丁脚本并**按各文件原风格还原**（图形编辑器会统一成 CRLF，故不用），
每步写回前先 `compile()` 语法自检。
**备份**：技能目录之外 `.temp\bak\ftth-address-extractor_20260917_222622\`（61 文件）。

### 2026-09-17（六十一）：核心文件按「协议 / 状态机 / 硬约束」定位重构，落回 49,000 B 预警线以下

- 起因：外部评审稿（桌面 `SKILL_V2_重构稿.md`，ChatGPT-5.6 提出）的**架构层**借鉴点三条 ——
  ① 显式 **Agent 状态机**；② 核心文件**只留协议 / 状态机 / 硬约束**、细则全部外移；③ **同一条规则只设一个权威定义**。
  内容本身不采用，只取架构。
- **体量（P0）**：`SKILL.md` **50,842 → 48,329 B**。原值**超过 49,000 B 预警线 1,842 B**，
  且距通用截断阈值（实测 51,200 B）**仅 358 B** —— 首屏全量加载随时可能被截断，属既有缺陷，本次一并消除。
  现余量：预警线 **+671 B**、硬截断 **+2,871 B**。逐章节体量按 `Get-Item .Length` 实测。
- **新增结构：「Agent 状态机（迁移门禁）」**（本次唯一新增章节）——
  迁移图（INPUT → PROBE → PLAN → PARSE → INSPECT → USER VALIDATION → LOCKED BASELINE → ASSEMBLE → OUTPUT → READ-BACK）
  ＋ **5 条禁止迁移**：① `unknown`→`confirmed`（含用「继续」「应该没问题」代替裁决）② `contradiction`→`OUTPUT`
  ③ 用脚本默认值 / 历史档案消除 `pending` ④ `INSPECT` hard gate FAIL → `ASSEMBLE` ⑤ 未裁决 `pending` → `OUTPUT`；
  另给出**锁定基准的机械形态**（`理解快照.json` 值/来源/状态 ＋ `裁决台账.json` 问题/裁决原文/裁决人/适用范围）与**回读校验**。
  **不新增任何规则**——只把既有 L0/L1 条款表达为可机械核对的迁移门。
- **外移与压缩（减的是重复，不是规则）**：Step 1a 的 `geom.json` 三坑与 `load_dxf`/`load_geom` 选型、
  Step 1b 的必传参数说明与「提取信息」六项详解、两条硬约束全文、测量架构九条铁律全文、
  Step 3 / Step 4 的实现细节 —— 逐条比对 `references/` 后发现同义条文**均已存在**
  （`coverage_rules.md` §零、`measurement_architecture.md` 架构全文、`measurement_methods.md` §3.5、
  `scripts_reference.md` §`geom.json` schema / §环境与命令纪律），故改为一句话＋指针。
  「必须解析」由六条带解释条目改为 **10 条名目清单**；铁律由 3 列表格改为**条目式**（保留条目名 + 关键判据）。
  经旧稿逐行比对复核：**无规则丢失**（被压缩条目的细则均在 references 中留有权威定义）。
- **新增维护条款**：参考文件节增「**唯一权威定义**」——同一条规则只设一个权威定义，其他位置只引用、不复制全文；
  两处表述不一致时以**条文更新日期较新者**为准并**向用户回报该不一致**；体量改前改后各跑一次
  `(Get-Item "<技能目录>\SKILL.md").Length` 并记录数字。
- **顺带修正一处旧文自相矛盾**：Step 1b「与总图交叉校验」原文为"不一致时**以总图为准**，标记矛盾并列入待确认项交用户裁决"，
  前半句与 L0-I2-P4（不自行择一）冲突。现改为：口径A（图上直写）优先于口径B（区间法）**属客观判据**（直读 > 推算），
  但**双方数值须一并写入待确认项**，**不得任一方被静默丢弃** —— 与 `analyze_coverage.py` 的实际行为
  （取直写值 + 冲突项进「需人工裁决」）一致。
- **校正一处数字**：原文称 `ftth.py`「13 个子命令」但只列 12 个名字；实为 **12 个主命令 + `count-hdd`（`count-box` 别名）**，
  现按此表述。
- **备份**：技能目录之外 `C:\Users\Alpha\WorkBuddy\2026-09-17-21-27-28\.temp\bak\ftth-address-extractor_20260917_213026\`（61 个文件）。
- **验收**：字节数 / BOM / 换行风格实测（**无 BOM + CRLF**，与真源一致）；frontmatter 完整；代码围栏成对（12 个）。
- **遗留（未处理，待定）**：脚本内注释存在指向 SKILL.md 旧标题的**悬空引用**（`analyze_coverage_vshape.py` / `count_box_icons.py`
  的「原则二 / 原则三」、`analyze_coverage.py` 的「方法对照表」「Step 1 · 分纤箱总图检查」）——
  属**本次改动之前**的既有漂移，非本次引入；按「以条文更新日期较新者为准并回报」条款登记在此，未擅改脚本。

### 2026-09-17（六十）：**三本台账落地为可执行载体 `ledger_state.py`（治「规则停在文档层」）**

- 起因：（五十七/五十八）把「理解快照 / 裁决台账 / 别名台账」写成纪律条款，但只写进了文档。
- **先取证再动手**：全盘 `find` 三本台账文件名 → **零命中**；技能目录内除文档提及外，**无任何生成 / 校验命令**。
  ⇒ 规则停在文档层：Agent 要落盘只能自己拼 JSON 结构，跨阶段 / 跨通道结构必然漂移，
  「读回来还得重新解释」这一步本身就是无效推理。
- **新增 `scripts/ledger_state.py`**（独立脚本，经 `ftth.cmd` 转发即可调用；用法 `--help`）：
  `init` / `snapshot-set` / `snapshot-get` / `ruling-add` / `alias-add` / `pending` / `check`。
- **把纪律变成机器约束**（不是把文档抄一遍）：
  ① `snapshot-set` 强制 `--source`；② `ruling-add` 强制 `--by`；
  ③ `alias-add` 标「已确认」时强制 `--evidence`（§5.1 硬边界 2）；
  ④ 别名归属冲突 → **拒绝写入 + rc=2**，只提示报人、**不自动择一**（§5.3 第④类）；
  ⑤ `check` 把「存在未裁决项」升级为 **rc=2 出口门禁**（未裁决值不得进成品）；
  ⑥ `init` 已存在则原样保留；台账缺失报 rc=3 并给补救命令，**不隐式建空文件**
  ——「从未落盘」与「落盘了但为空」是两件事，混同会把前者伪装成后者。
- **退出码对齐 L1-C2**：沿用 0/2/3；并把 argparse 的用法错误由默认 rc=2 改为 **rc=3**
  （rc=2 在本技能专表"图纸输入不足"，用法错误误用它会让上游去补探查）。
- **文档接线**：`operations_discipline.md` §六/§七/§八 各加载体命令 + 新增 §九（汇总与自检 + 三本台账对照表）；
  `scripts_reference.md` 两张脚本表各加一行（与 `ledger_elements.py` **同名不同物**已显式标注）；
  `addressbook_template.md` 的 Q~X 段由「概括为留空」改为**逐列真实列名**。
- **顺带修正一处文档与实现不一致**：该文档原称 Q~X 全留空，但模板 W 列「区县」经
  `HEADER_ALIASES`（`区县 → 区`）**实际会写入区名**、与 D 列「三级」同值 —— 属**数据列**，已改正。
- **体量**：`SKILL.md` 50,796 → **50,842 B**（+46，仅改「落盘纪律」一行为指针），距阈值余量 **358 B**；
  `operations_discipline.md` 14,926 → 17,585；`scripts_reference.md` 40,382 → 41,035；`addressbook_template.md` 2,247 → 3,277。
- **验收**：`ledger_state.py` 22 项断言全通过（未初始化 / 幂等 / 覆盖留历史 / 参数校验 / 冲突拒写 / 门禁 rc / 损坏处置）；
  安装后经 `ftth.cmd` 转发冒烟 4 项通过。
- **未做（待人工裁决）**：成品 **R 列「别名」的取值口径**未定 —— 它位于沙盘对接字段段
  （城郊属性 / 进线标识 / 沙盘临时表ID …），是否等同于「归一化原始异写」**无客观判据**；
  按 §5.3 第④类挂起，未获裁定前不写入（`HEADER_ALIASES` 保持未映射 `别名` / `备注`）。

### 2026-09-17（五十九）：**修正「体量预算纪律」的后果表述 —— 截断阈值实测 50 KiB，且截断有落盘兜底**

- 起因：用户质疑「51,000 的硬上限难道不能向上调一调吗」。
- **实测（三轮独立取证）**：
  ① 内核二进制（45.3 MB）搜 `51000` / `51200` / `52224` → **各 0 命中**；24 个 `OPENCODE_*` 环境变量中**无截断阈值开关**
     ⇒ 该阈值**不可配置**，改内核则升级即失效、收益仅 +200 B，**判定不值得调**。
  ② 全部 5 天服务端日志 3,483 条 `[tool] truncate` 记录，按 `wasTruncated` 布尔标记夹逼：
     **skill 未截断 max=49,245 / 已截断 min=82,486**；powershell 48,725 / 162,745。
     结合「截断后送达长度 51,438~51,556 B」（含提示语约 240~350 B）反推 ⇒ **阈值 = 50 KiB = 51,200 B**。
     原写的 51,000 B 系保守取整，**判断准确**。
  ③ Agent 实收正文（09-17 16:44）：`...137818 bytes truncated...  The tool call succeeded but the output was truncated.
     Full output saved to: <tool-output 路径>`。
- **修正（原表述三处被实测推翻）**：原「超出即被**静默截断**：截断处之后 Agent **完全读不到**且**不报错**」→
  **有正文提示语 / 全文落盘 `tool-output/` 当场给路径、可 Read 或 Grep / 但落盘会被自动清理**
  （实测存活 < 37 分钟：末次落盘 09-17 16:44，`tool-output/` 目录 mtime 17:21，现为空）。
  ⇒ 后果由「会瞎」降级为「**多一次往返 + 兜底可能已失效**」；预算纪律仍然必要，但**理由改写**。
- **体量**：`SKILL.md` 50,588 → **50,796 B**（+208），距阈值余量 **404 B**。
  备份：`skill_backup/SKILL.md.bak-trunc-20260917-205324`（技能目录之外）。
- **未做**：未做 TeleAgent 侧放大实测（需 GUI 会话）；「阈值 = 51,200」系日志反推，**非直接观测**，属未闭合项。

### 2026-09-17（五十八）：**矛盾处置由「一律报人」改为「四级分流」（闸门放出口）**

- 起因：用户对（五十七）的严格度存疑（"这样严格的利弊得失，你来分析一下"），并明确要求
  **「既要利用模型的推理能力，又要防止胡编乱造进入成品」**。确认后的原则三句：**发现要主动 / 裁决交人工 / 成品零容忍**。
- **规则变更（核心）**：原「发现矛盾 → 立即停止当前步骤，不生成下游产物」→ 改为**四级分流**，
  **停机只保留在第④类**（无客观判据 且 冲突值要进成品）：

  | 类 | 判据 | 处置 | 停机 |
  |---|---|---|---|
  | ① | 归一化后语义等价 | 视为一致，只记比对日志 | 否 |
  | ② | **有客观判据**（几何位置 / 物理测量 / 唯一取数来源 / 标注原文直读） | 自行判定并留证（属**测量**，非推理） | 否 |
  | ③ | 无判据，但不进成品、可回滚 | 取安全侧 ＋ 显式标记 | 否 |
  | ④ | 无判据，且要写进成品数值 | **停下报人** | **是（唯一）** |

- **新增机制三件**：
  1. **归一化前置** —— 比对前先对齐单位 / 写法 / 顺序 / 全半角，**归一化后仍冲突才算矛盾**，防假阳性淹没真矛盾；
  2. **数据来源权威等级表**（`references/operations_discipline.md` §5.4）—— **空表 = 一律按第④类**；
     须由用户 / 设计院**显式声明**，**禁止 Agent 依惯例 / 多数自行排定**（那正是被禁的推理）；
  3. **报人须给「最小化二选一」** —— 写成可直接作答的选择题，不得把取证推回用户；并**批量提交**（攒到阶段末）。
- **三条底线未松动**：不得静默择一 / 惯例与多数不得作裁决依据 / **未裁决的值不得进入成品**。
- **放宽的一处**：原「未裁决冲突使**下游产物整体**无效」→ 改为「**相关部分**视为未定稿」，
  并须在交付说明显式列出「本次交付含 N 项未裁决冲突」。
- **依据（量化，见 [references/operations_discipline.md](references/operations_discipline.md) §一）**：
  两会话实测墙钟 93~97 min 中，**等用户回话占约 70%**、工具执行仅 3~7%；「发现即停」与该指标直接对冲，
  故**闸门移向出口**。另：技能内原本**没有「数据来源优先顺序」表**，报人一度是「缺规则后的兜底」而非设计选择。
- 落点：`references/operations_discipline.md`（**§五 全文重写** 6194 → 9648B，新增 5.1~5.6）、
  `SKILL.md` L0-I4 ② 与「三要素·一致性条」（改为指 §五，净 **-3B**；48965B，余量 35B）、
  `ftth-annotation-addressbook/SKILL.md`（两法结论不一致时的分流措辞对齐，不因"坐标更原始"即自动成为判决依据）。
- 备份：`skill_patch/backup_20260917_135713_pre_conflict_grading`（技能目录之外，含 4 个文件改动前副本）。

### 2026-09-17（五十七）：**图内矛盾不得自行推理，一律请求人工验证（用户指令）**

- 用户指令（2026-09-17）：「对于图内前后矛盾的地方，不要自己推理，请求人工验证。」
- 落点三处：`SKILL.md` L0-I2 禁区 P4（补「惯例/多数亦不得作裁决依据」）、L0-I4 处置规程 ④
  （参考线索明确列出惯例 / 统计多数 / 命名规律）、图纸信息模型「执行纪律·一致性条」（补「不得自行推理断定哪一方正确」）；
  边界与处置四步全文另入 [references/operations_discipline.md](references/operations_discipline.md) §五。
- **边界（通用，与项目无关）**：跨图惯例、跨项目统计多数、命名 / 编号规律、图示自洽性 —— 一律只算**参考线索**，
  不构成裁决依据，须原样并列双方表述交人工核验。**测量**（米数 V 型 / 竖干断口、包围盒中心配对等）不属推理，不受此限。
- 起因：某项目箱号上下颠倒溯源中，曾以「其余各处惯例一致」反推哪一方是笔误并据此给出修正建议（详见案例报告）；
  该推定即便成立也只是线索，不能替人工裁决。
- 体量：`SKILL.md` 48968B（预警线 49,000B 之下，余量 32B）；本次未外移任何既有条款。
- 备份：`skill_patch/backup_ftth_20260917_132801`（技能目录之外）。

### 五十六（2026-09-17，楼层格式 auto 失效修复 + 提示键处理 + 交付纪律）

**F1【缺陷·默认路径恒失效】楼层格式 `auto` 判定失效。** `gen_addressbook.py --floor-format auto`（默认值）的判定数据源是**模板示例行的楼层单元格**；而模板示例行自 2026-09-12 起为中性占位（`<楼层>`），被 `_is_placeholder()` 主动排除 ⇒ auto 恒定退回 `3F` 形态，与模板规则的权威格式（中文）相反，「照模板出表」在默认路径上不可达，只有显式 `--floor-format chinese` 才正确。
- 修法（不动默认值语义、最小改动）：`assets/标准地址表模板.xlsx` 示例行楼层格 → `一层`（恢复格式样本）；`references/addressbook_template.md` 增补显式格式规则 + 「示例行不得清成占位」的约束。
- 验证（同一真实输入、逐格内容指纹，xlsx 字节含时间戳故不用文件 sha）：修复后 `auto` 指纹 == 显式 `--floor-format chinese` 指纹 == 既有交付物指纹（三者 64b1c9bc）；修复前 auto 指纹不同（b4a3c3e9）。修复前后差异单元格 313 个**全部落在楼层列**，其它列零差异。
- 备注：`--template` 默认 `None`，不传模板时 auto 同样退化为原样输出（本批未改该默认值）。

**F2【噪音/误判】`*_note` 提示性键被当无效配置键。** `fx_pattern_note`（probe 检出串号风险时携带）恒存在于 probe 产出的配置里，落到 `ftth.py --config` 的「无效键」分支 ⇒ (a) 每次调用都刷 WARN 淹没真告警，(b) `FTTH_STRICT_CONFIG=1` 下把**合法**配置判成硬失败（rc=3）。
- 修法：`ftth.py` 按**后缀约定** `_note` 识别提示性键（非硬编码清单，未来同类键自动覆盖），静默跳过并以 `[config-info]` 原样透传内容，不计入 `[CONFIG-IGNORED]`。
- 验证三格：正例（仅提示键）→ 透传、无 WARN、严格模式不硬失败；反例（真未知键）→ 仍 WARN + `[CONFIG-IGNORED]`、严格模式仍 rc=3；真实配置回归 → `fx_pattern_note` 不再出现在 `[CONFIG-IGNORED]`。

**F3【文档缺口】probe 产物键结构未记录。** `references/scripts_reference.md` 增补「probe 产物键结构」：三个顶层区（`suggested_params` / 4 个画像信号 / `全量文字样例`）、`全量文字样例` 的条目键（`层`/`类型`/`内容`/`x`/`y`）、UTF-8 与「勿用按尺寸受限的 JSON 解析器读」的读法约定。起因：探查阶段为摸清键名额外付了数轮试错（先猜编码、再猜键名）。

**F4【纪律缺口】交付纪律未成文。** `references/operations_discipline.md` 新增「四、交付纪律」：① **覆盖既有交付物前先备份**（时间戳副本；「不参考历史产物」≠ 可销毁历史）；② **交付核验以「数据行数 + 内容指纹」为准，不以文件大小/mtime 为准** —— Office 系编辑器打开带 AI 生成内容标识的成品再保存会**追加标识行并改写字节**，实测交付后数十秒内字节数与 mtime 均变而业务数据一行未变；③ 复核交付结果要重读目标文件本身，不用生成时刻的中间产物代替。

**改动面**：`assets/标准地址表模板.xlsx`、`scripts/ftth.py`、`references/addressbook_template.md`、`references/scripts_reference.md`、`references/operations_discipline.md`。
**未动**：`SKILL.md`（体量余量仅约 100B，且规则落点已有指针，无需改）、`--template` 默认值、`--door-format` 语义、`scripts/` 其余文件。
**备份**：技能目录之外 —— 全量副本 `skill_patch/backup_ftth_<时间戳>`，逐文件副本 `skill_patch/perfile_backup/`。
**行号引用自检**：本次未新增/修改任何「按行号自引用」的写法；未增删文件，故文档中的文件/脚本计数声明不受影响。
### 五十五（2026-09-17，全篇一致性梳理：重复/矛盾审计）
- 修复 6 处（审计方法：按保留清单逐条对原文交叉核对）：
  F1【bug】删除孤行残句：探查纪律"禁内联"条与后续新句重复半截（上轮 B2 锚点选在续行所致）——禁内联全篇恢复唯一；
  F2【死引用】"下方探查清单 1~6"→"第 1 项（六项基础探查）"（清单压缩重编号后旧编号失效）；
  F3【矛盾】Step1b "无户数标注→未标注待确认" 与 09-16 裁决"有图标优先 count-box"打架 → 对齐：无 X户 标注但有图标走 count-box 出数、不属"未标注"；
  F4【歧义】原则二示例"从皮线推覆盖分界"易误伤 V 型法 → 改"从皮线走向/连通性推…（米数 V 型属测量方法不在此列）"；
  F5【重复】相邻两条"最近楼层线法"禁令（安装楼层条+混用条）合并为一条；
  F6【重复】Step0 的 DWG→DXF 解释与「必须具备的软件环境」重复 → 收敛为指针。
- 审计后判定可接受的重复（语境化重申，不动）：行数恒等式 3 处（定义/门禁/脚本内置）、矛盾即停 4 处（原则/三要素/栋级/Step2）、dump_geom 首步 2 处（纪律+流程）、户数口径 2 处（架构实体优先级/Step2 自检视角，互补）、禁内联纪律与解释器契约（探查语境 vs 调用语境）。
- 终态 48,367B（预警线 49,000B 之下）。备份：skill_patch/consistency_backup_20260917_093919。

### 五十四（2026-09-17，大熊裁定：移除"首层减户"特例条款）
- 裁定：**首层减户是某些项目中的特例，不是通用规则**——按 2026-09-14 固化原则（个案细节不进技能正文）从全部活规则落点移除。
- 移除落点：SKILL.md 户号规则复验行 / references/titleblock_and_intake_table.md §4.2 + §六待确认模板示例 / methods/titleblock_based/manifest.json 自检 checks[3]。
- 被删原文留档（供个案项目需要时人工引用）：
  - SKILL.md: **首层可能减户**（采集表只给"每层住户数"时不体现该差异），按均匀户数出表后**必须把"首层是否减户"列入待确认项**，不得自行套用减户规则（回验记录见 SKILL_CHANGELOG.md）。
  - intake_table §4.2: - **首层减户**：已定稿表中确实存在"首层只有 101 一户"的情况（同栋其他层 2 户）。 / 采集表只给"每层住户数"、不体现首层差异 → 按均匀户数出表后，**必须把"首层是否减户"列入待确认项**， / 不得自行套用减户规则。
  - manifest checks[3]: 首层减户：成品表中若存在『首层只 1 户』，必须列入待确认，不得自行套用规则
- 顺带：intake_table §4.2 "1901 户"个案数泛化为"项目已定稿表"（同属个案细节）。
- 保留：本 CHANGELOG 2026-09-16 历史条目中的"首层减户"字样为历史记录，不动。


### 五十三（2026-09-17，SKILL.md 第三次瘦身）
- **背景**：SKILL.md 52,905B，超自述预算（条款 "正文 >48KB 必须先外移再加"，硬上限约51KB）——尾部面临静默截断。
- **动作（外移承接：references/scripts_reference.md 新增 §统一入口与--config 机制，原文逐字）**：
  ① `ftth.py` 统一入口/--config/解释器契约块 345-368 行压缩为规则摘要（~2,200B），原文外移；
  ② probe 回填修复叙述（实测 18→7 个标题）压一行，细节本已在 CHANGELOG P0-3；
  ③ 探查清单 1-6 项压缩为单行（判据原在 probe_checklist.md），第7项重编号；
  ④ 户号复验 1901 户叙述、防伪条款起因案例——个案叙述外移，规则保留（2026-09-14 固化原则）；
  ⑤ 预算条款单一数字化：硬上限 51,000B / 预警线 49,000B（消除 51,000/52,224 两种读法歧义）；
  ⑥ 修复 439 行两条 bullet 挤同一行格式缺陷；scripts/ 文件数量声明按实况修正（split_bands.py 入列后）。
- **结果**：52,905B -> 50,781B（省 2,124B），低于预警线，恢复增长余量。规则零丢失：所有裁定/门禁/判据条款原文保留。


### 五十三·补（2026-09-17，第三轮瘦身第二次切割）
- 第一轮压缩后仍 50,781B（>预警线 49,000B），第二轮外移个案实测数据与查表内容：
  ① 脚本职责表（18 行）逐字外移 scripts_reference.md §脚本清单与职责，SKILL.md 留硬指针；
  ② 几何缓存三级耗时实测（76s/20s/0.2s）、shell 内联故障形态 → scripts_reference.md §实测案例数据；
  ③ 效率纪律实测依据（93~97min / 113万 input）、todo 冻结教训 → operations_discipline.md；
  ④ gen_addressbook 实现参数 7 行压缩为指针+摘要；九级地址树多行命令块压为单行；
- 终态：SKILL.md **48,459B**（52,905 → 省 4,446B），低于预警线 49,000B，硬上限 51,000B 余量 2.5KB。
- 规则零丢失自检 PASS（裁定/门禁/判据条款全保留）；悬空指针 0；reference 链接目标全存在。

### 2026-09-17（五十二）：**多地块同名楼守卫 + split-band 分带子命令（P1 收口）**

- **P0 守卫**：`find_bldg_anchors` 同名锚点出现在显著不同 x（>`DUP_ANCHOR_X_TOL`=10.0）时，旧实现静默保留先出现者
  （实测多地块图应有约 24 锚点只出 9 个，同名楼整栋静默丢失）。新实现：先出现者经邻域校验仍保留、
  后出现者也有楼层刻度佐证 → 抛 `MultiPlotDuplicateAnchorError`；`parse_dxf_structured.py` 捕获后
  **rc=3 早失败**、点名各组同名锚点位置与 split-band 指引、**零产物**（--out 未写）。
  同位重复绘制（≤10.0）仍静默去重；说明文字误中标题正则（邻域无楼层刻度）降级 WARNING 不误伤。
- **新能力**：`ftth.py split-band` → `scripts/split_bands.py`，按 y 带裁剪子 DXF
  （`--band 名称:ymin:ymax` 可重复/逗号分隔）。y 带口径同 `read_titleblock_households.py --band`
  （上界=上邻带标题 y、下界=中点）。守卫：带区间重叠告警（下游重复计数风险）、裁出 0 实体早失败 rc=2。
- **验证**（同一多地块图端到端）：反例=全图 parse rc=3、报错列出 2#/5#/6#/7#楼各组 x 位置、零产物；
  正例=4 个分带子图 parse 全 rc=0，band1 输出与守卫前产物 **sha256 逐字节一致**（"没坏 b"）；
  split-band 重切 4 带与原实测临时脚本实体级一致（band1/2 字节数相同，band3/4 差 3~6B 为 ezdxf 元数据）。
- **文档**：SKILL.md / scripts_reference.md 子命令数 10→11、脚本数 24→25（20 功能脚本）；
  scripts_reference.md「拆分脚本属临时工具，不入技能」口径作废。
- **遗留**：SKILL.md 在本条目前已超自述加载预算（约 51 KB），本次增量约 +200B；
  瘦身外移需单独裁定，未在本次处理。

### 2026-09-17（五十一）：**出表输入组装内建 `ftth.py assemble` + `gen` 透传格式参数（P2 收口）**

**背景**：同任务五连跑实测：凡户数走 count_box 口径，出表输入 JSON 全靠会话**自造组装脚本**拼
（count 列逐层 + 显式列归属 + coverage 分纤箱），每次现场重写、还要烧数轮 edit 修 oldString 不匹配；
`gen_addressbook.py` 早已支持 `--floor-format/--door-format`，但统一入口 `ftth.py gen` 不透传，
调用方想要中文楼层时被迫**绕过统一入口直调子脚本**。两者都是"统一入口有缺口 → 会话现场补"的形态。

**改动**

- 新增 `scripts/assemble_households.py` + `ftth.py assemble` 子命令：
  count 逐层户数 + **显式** `--col-map`（列→楼栋/单元归属映射）+ coverage 分纤箱合并 → gen 输入 JSON。
  - 归属映射是裁决项（count 列不含楼栋归属），脚本不做任何自动猜测；语法错/列号越界/
    同一 (楼栋,单元) 被两列声明（户数翻倍）一律 rc=1 硬失败。
  - **一列映射多单元 = 共享系统图克隆**，机械执行 + 显式打印克隆留痕（每单元户数）。
  - coverage 单元键归一失败时回退 `1单元`——仅当该楼栋确有 1单元；仍失配显式列出，不静默丢。
  - 守恒打印：合计户数 − count 归层总数 应恰等于克隆增量，不等 = col-map 有漏（大声报数）。
- `ftth.py gen` 透传 `--floor-format` / `--door-format` / `--fx-prefix-map` / `--allow-lossy`
  （参数名与 gen_addressbook 逐一相同，build_cmd 仅转发显式项，缺省行为不变）。
- `--dxf` 必填豁免名单加入 `assemble`；示例表/依赖矩阵/专节说明入 `references/scripts_reference.md`。

**验证**（真实数据全链路）：assemble 产物与某会话自造脚本产物逐单元语义比对**差异数 0**（371=371）；
`assemble → gen --floor-format chinese` 出表与该会话已交付 xlsx **逐格比对 0 差异**（373 行 × 24 列）；
全部子命令 `--help` 冒烟通过；gen 不带新参数行为不变；assemble 错误路径（越界/重复声明/缺 --dxf）均显式报错。

### 2026-09-17（五十）：**新增多图批量编排入口 `scripts/ftth_batch.py`（优化路线图 R3）**

**背景**：两会话实测：单图任务（凤鸣朝阳）自造 2 个脚本即交付；多图任务（柳辛庄，2 图 8 地块）自造 **9 个**
批量脚本（split_dxf/split_blocks/batch_parse/batch_coverage/check_parse/check_all/summary/summary2/gen_overview），
其中 batch_coverage 因参数问题**连错两轮、16 次子调用全部作废**。根因是技能只提供单图入口，
多图编排完全靠会话现场发挥。已否决「`--dxf` 改多值」（波及全部下游），本条为替代方案。

**改动**

- 新增 `scripts/ftth_batch.py`（纯 stdlib，约 22 KB）：一个入口跑完
  「逐图 probe → parse → coverage → merge_json 合并 → batch_overview 总览」。
- **不碰现有语义**：不改 `ftth.py --dxf` 单值、不改任何子命令参数、不 import ftth_common（编排层零业务耦合）。
- 关键机制：
  - **解释器继承**：子进程 = `sys.executable`（启动器确认过带 ezdxf 的那个），全程不裸调 `python`；`--python` 可锁定。
  - **参数路由**（防整轮作废）：先跑 `ftth.py <子命令> --help` 建立三步骤参数表，透传参数**只转发给接受它的步骤**
    （`--vert-dx` 只进 coverage、`--expand-bldg-ranges` 只进 parse）；**无人接受 ⇒ 开工前 rc=2 报错**。
    该表从 `--help` 动态获取，不硬编码，ftth.py 加参数无需同步本脚本。
  - **--config 自动串联**：probe 成功的图，其输出自动作为该图 parse/coverage 的 `--config`。
  - **容错**：单图/单步失败不中断批次；`--skip-existing` 断点续跑；`--timeout-sec` 单步超时（默认 3600）；
    图名重复自动加序号。
  - **产物**：`batch_overview.md`（人读总表：每图各步 rc/耗时/楼栋/单元/户数统计）+
    `batch_overview.json`（机读：命令行、rc、失败尾迹）；parse 有成功时自动 merge 为 `<批次名>_合并.json`。
  - **退出码**：0=全成 / 1=部分失败 / 2=全败或前置错误；`--dry-run` 只打印命令并写计划总览。
  - **argparse `allow_abbrev=False`**：实测 `--out` 会被前缀匹配吞成 `--out-dir` 致拦截失效，故显式禁用缩写。
- 文档：`SKILL.md` 加脚本表行 + 批量入口一行；`references/scripts_reference.md` 新增 §批量编排（完整契约）、
  直调表加行、**补台账「退出码门禁」**（压缩主文件前先补 references，防静默丢规则）；
  计数断言 23→24（两处，按磁盘实数重数）。
- 主文件回压：SKILL.md 元素台账段 7 行压缩为 4 行（判据细节 references 已有，rc 门禁保留主文件），
  并修复 343~344 行「支持 3F/17F…」孤行（原本悬在台账引块内、语义错挂）。

**验证**（系统 Python313 + ezdxf，合成 DXF×2）

- T0 编译通过；T1 无参 rc=2 带示例；T2 dry-run 路由 4 参数各归其位（coverage 专属/parse 专属/双步骤）。
- T3 真实批量：probe OK → parse OK（--config 串联生效，无显式参数解析出 2 楼栋）→ coverage 缺参 FAIL rc=3
  ⇒ 批次 rc=1、总览正确记账。
- T4 全成功路径 rc=0 + merge 产物楼栋正确；T5 `--skip-existing` 续跑全 SKIP。
- T6 清单模式（顶层/图级 common 深合并、步骤级参数、skip_coverage、重名改 `甲图_2`）12/12 过。
- T7 拦截：未知参数开工前 rc=2、`--out` 被拒、DXF 不存在报错。T8 `ftth.cmd` 派发 `ftth_batch.py` 链路通。
- 幂等：apply 脚本重跑全 SKIP；SKILL.md 正文 **50,385 B**（净 −287 B，压缩>新增），余量回到 ~1,053 B。

**方法学（写进纪律）**：① 给编排入口做「参数表动态路由 + 开工前拦截」，比事后报错省整轮子调用；
② **argparse 前缀匹配是透传语义的隐形杀手**（`--out`→`--out-dir`），凡 parse_known_args 收透传的入口一律
`allow_abbrev=False`；③ 幂等判断不能只看 old 串是否命中（old 在新状态可能仍唯一），必须配 applied-marker。


### 2026-09-17（四十九）：**整改批次 R2/R3/R4 —— 静默失败全部显式化（判据通用，与项目无关）**

**背景**：2026-09-16 柳辛庄/凤鸣朝阳两会话坑清单（九层归因）定位的三类**静默缺陷**：L3 正则无捕获组解析期 IndexError 裸崩、L2 `--config` 键被静默忽略（全天 42 处/10 会话无一人处理）、L4 自适应容差失准静默丢整地块（12 栋，rc=0）+ 单元标注「最近者胜」无排他约束串楼后被编号去重盖住。本批**不改任何判据本身**，只把静默失败变成响亮失败；成功路径输出经回归验证与改动前逐字节一致。

**改动**

- `parse_dxf_structured.py`：正则编译后立即校验捕获组契约（title/hu/unit ≥1 组、cable ≥2 组，取自脚本内 `m.group(n)` 实际用法），不足即 rc=1 显式报错并给正确形态示例。
- `ftth.py`：config 无效键在逐键 WARN 之外，用固定 token `[CONFIG-IGNORED]` 汇总重申；环境变量 `FTTH_STRICT_CONFIG=1` 时 rc=3 硬失败（走环境变量不走 CLI 开关：`build_cmd` 会把新增参数转发给子脚本造成污染）。
- `read_titleblock_households.py`：
  - **R3 零数据楼**：有楼名证据而 data 无层数 → `[ERROR]` 列楼名+坐标，rc=3（新退出码，docstring 已更新）；`--allow-partial` 人工放行 rc=0。检测在楼名证据写入之后执行（位置敏感，已注释说明）。
  - **R4a 单元归属歧义**：单元标注容差内命中 ≥2 栋楼 → 列候选楼+偏移证据（判给不变）；新增「单元标注落到无主层户上」计数。
  - **R4b 重复单元标签**：某楼某标签次数 **> 本图基准绘制次数** 才报（按众数归一化，正常重复绘制不误报；实测柳辛庄 `3 4号楼 1单元×4` vs 基准×2 精准命中，37 条噪声归零）。
  - 质量报告新增 5 键：单元归属歧义标注数/明细、重复单元标签的楼、单元标注落到无主层户上的数、零数据楼。

**回归验证**（柳辛庄 1-4 图自适应/显式 + 凤鸣朝阳 BZ 层，三例）

- 显式容差与凤鸣朝阳：数据段（除质量报告）与改动前**逐字节一致**，rc=0 不变。
- 自适应容差：rc=0→**3**，`[ERROR]` 精确列出地块3/4 共 12 栋零数据楼（与 2026-09-16 22:19 事故吻合）。
- 歧义明细含事故对：`3 4号楼 偏移[82456.6,43616.7]` vs `3 7号楼 偏移[100966.9,45023.5]`，另白捡地块2 两处同型。
- 正则自检正反例：无组 pattern rc=1 显式报错；带组 pattern probe 正常 rc=0。
- 备份：`WorkBuddy/2026-09-16-22-50-25/skill_backup_20260917-0010/`（51 文件 diff 一致）。

### 2026-09-16（四十八）：**（四十七）收尾 —— 计数断言修正 / 启动器契约入 references / 主文件回压 + 加载体上限定标**

**背景**：（四十七）把 `scripts/` 从 21 个文件加到 23 个，触发三处连带问题；另借机把「加载体上限」从「约 51 KB」的**估计**升级为**实测定标**。

**改动**

1. **修正可实测的计数断言（P1，陈旧缺陷）**
   `SKILL.md` 与 `references/scripts_reference.md` 均写「本skill附带21个文件（19个功能脚本+1统一入口+1公共模块）」——
   该数字**随磁盘实况数得出来**，加 2 个文件后即陈旧。已按**磁盘实数**改为
   「附带23个文件 = 19个功能脚本 + 1 统一入口 `ftth.py` + 1 公共模块 `ftth_common.py` + 1 启动器 `ftth.cmd` + 1 转发层 `_launch.py`」。
   > 纪律：**凡是能在磁盘上数出来的数字，改完必须重数一遍。**
2. **启动器契约补进 `references/scripts_reference.md` §解释器契约（P1）**
   机器核查发现 4 条要素**只在 SKILL.md 有、references 无归宿**：首参分派规则 / `FTTH_PYTHON` 覆盖 /
   `py -3.x` 候选 / 全失败 `exit /b 9`。已在 §解释器契约 顶部新增「首选：直接用启动器」小节（含分派、探测、
   覆盖、退出码、参数保真五项约定表），**先补 references 再压缩主文件**（顺序不可反，否则静默丢规则）。
3. **主文件回压（P1，体量）**
   （四十七）在 `SKILL.md` 加的启动器段 **14 行 / 1,446 B** 与 references 重复度过高，压回 **8 行 / 1,011 B**
   （保留可复制的启动器写法 + 四禁条，机制细节指向 references）。净 −441 B。

**加载体上限定标（实测，34 条加载记录）**

| 维度 | 判决 |
|---|---|
| 按**字节**还是**字符**？ | **按字节**。非截断最大 **49,245 B** vs 截断最小 **51,438 B**（间隔 2,193 B，可分）；按字符则**重叠不可分**（更短的 24,618 字反而被截断） |
| 上限值 | **≈51.5 KB**（截断时送达**停在** 51,438~51,556 B，即上限处） |
| 截断是否报错 | **静默**：工具状态仍 `completed`，只在正文里插一段 `...N bytes truncated...` |
| 现存技能位置 | `SKILL.md` 磁盘 52,512 B → 正文 50,670 B → **预测送达 50.2~50.7 KB < 上限**，**不截断**，余量 ≈**0.7~1.2 KB** |

**验证**：真源 43 文件；无残留测试桩；**22/22 编译通过**；BOM 0；混合换行 0；文档残留裸 `python` **0**；
要素归宿核查 **14/14 全部 OK**（压缩前为 10/14，缺 4 条）。

**方法学（写进纪律）**：主文件体量**按字节**量并留余量 —— 按字符估会**低估**风险；引用上限一律给
「已实测的最坏通过值」而不是「约多少 KB」。

### 2026-09-16（四十七）：**新增统一启动器 `ftth.cmd` + 子命令参数自检 + 文档示例改启动器写法**

**起因**：两会话实测（多地块 + 单图各一）暴露两个**必然损耗**，与 Agent 能力无关：

1. **裸 `python` 被宿主 runtime 劫持**（该解释器无 ezdxf、且 pip 补不上），**每个新会话开局必踩**，
   实测各烧 **44 s / 50 s**；原文档给的是「探测顺序」而非绝对路径契约，属**文档约束**，不保证被遵守。
2. **子命令参数名不统一**：Agent 猜 `--parse-json` 被 argparse 拒；批量场景下**一次参数错**
   → 8 地块 × 2 轮 = **16 次子调用全废**。

**改动**

1. **新增 `scripts/ftth.cmd` + `scripts/_launch.py`（把契约从文档约束升级为机制约束）**
   - `ftth.cmd` 按候选清单**逐个真执行**探测（`<exe> -c "import ezdxf"`，**不是路径猜测**），
     命中即转发；支持 `FTTH_PYTHON` 显式覆盖；全部失败则打印候选清单与处置办法并 `exit /b 9`。
   - 首参数以 `.py` 结尾 ⇒ 转发该脚本（**直调脚本也走同一入口**）；否则转发 `ftth.py <子命令>`。
   - `_launch.py` 只做首参数解析（批处理无法安全删首参），**不解析业务参数、不改退出码**。
   - **附带修正**：`_launch.py` 的 docstring 承诺支持 `ftth.cmd scripts/xxx.py`，但原实现会拼成
     `scripts/scripts/xxx.py` 而失败 —— 已补上 `scripts/` 前缀容忍（`\` 与 `/` 均可），兑现承诺。
2. **`ftth.py` 子命令参数自检**：覆写 `ArgumentParser.error`，出错时打印
   `[参数错误]` / `[可用参数]`（必填带标记）/ `[正确示例]` / `[完整契约]`，**退出码仍为 2**。
   示例表按「子命令 → 一行可复制命令」维护，且**必填项必须出现在示例里**（写脚本时用闸门校验）。
3. **文档示例统一改启动器写法**：`SKILL.md` + 3 个 `references/*.md` 共 **6 处**裸
   `python <脚本>.py` 调用全部改写为 `& "<技能目录>\scripts\ftth.cmd" <脚本>.py`，
   消除「照抄文档即踩解释器坑」的路径。

**验证（每一项都可复现）**

| 项 | 结果 |
|---|---|
| 启动器 T1–T8b | **全通过**：help／参数自检／中文路径 cmd+PS 双链／`FTTH_PYTHON` 覆盖／兜底探测／全失败 exit 9／`<脚本>.py` 转发／绝对路径脚本 |
| 算法路径回归 A/B | **10 个子命令产物 sha256 与改动前逐字节一致**（probe→coverage→count→inspect→gen 全链） |
| 错误路径自检 | **5/5**：缺必填 ×2／不存在子命令／复现原会话 `--parse-json` 误用／未知参数 |
| 真源体检 | 43 文件、无残留测试桩、**22/22 编译通过**、BOM 0、混合换行 0、文档残留裸 `python` **0** |

**不做的事（已否决，勿重开）**

- `--dxf` **不改为多值** —— 会波及全部下游调用；多图编排改用文档级指引（各图分别跑 + `merge_json.py` 汇总）。
- 算法主干（三要素模型 / 方法池平行候选 / 申报制门禁 / 台账分型判据）本轮实测均正常，**未改动**。

### 2026-09-16（四十六）：**修 `count_box_icons.py` 归层失败静默出「0 户」（P0）+ 户数取法形态判别入册**

**背景**：用户补充户数取法口径 —— 图纸上「家居箱画 1 个示意 + 标注数量」时**直读数字**取户数；
「逐户画皮线、末端方块」时**数箱**更准；并指出**未遇到只画线不画箱**的图。遂对全部户数图做形态实测。

**实测四形态**（箱一律存在，但只有「逐户一箱」能直接数）

| 形态 | 图面特征 | 判据 |
|------|---------|------|
| A 逐户画箱 | 每户一箱（块属性 `A=家居配线箱`） | 图标数 = 户数 |
| B 每层一箱 + 乘数 | 每层一箱 + `xN` 标注 | 图标数 = 层数×单元数 ≠ 户数 |
| C 示意箱 + 数量标注 | 箱为示意、旁标 `N户` | 读 `N户` 求和 |
| D 非户数图 | 光交面板 / 杆路路由，无箱、无线缆图层 | 不适用 |

**缺陷（P0，实测证据）**：`count_box_icons.py` 归层循环 `if sc:` **无 else 分支** ——
刻度列 `sc` 为 `None` 时，该列图标**既不进 `per` 也不进 `un`**，凭空消失。
表现为「归层后总户数 0 ／ 未归属 0 ／ rc=0」，下游把 0 户当成功结果消费。改前实跑：

- 柳辛庄1-4：贴末端 **449** 个 → 归层合计 **0**、未归属 **0**、无刻度列 27/27、**rc=0 有产物**
- 柳辛庄5-9：贴末端 **356** 个 → 归层合计 **0**、未归属 **0**、无刻度列 22/22、**rc=0 有产物**
- 云峰（对照）：331 → 331，正常

**修复**
1. 补 `else:` 分支，把无刻度列的全部图标计入「未归属」，消除静默消失；
2. 新增门禁：**贴末端图标 > 0 且 归层后总户数 == 0 ⇒ rc=2 且不写产物**，
   并打印成因（典型 B 形态）与处置（`--floor-layer` ／ 图签参数法 ／ 乘数口径人工裁决）。

**A/B 验证（改前 vs 改后，5 图）**

- 云峰：rc=0 不变，产物 **sha 逐字节一致**（`eb6907b61471`）；**逐键对拍 4031 个叶子键，差异 0**
- 柳辛庄1-4 / 柳辛庄5-9：rc 0 → **2**（由「静默 0 户」转为显式拦断）
- 凤鸣朝阳 / 繁华里：rc=2 不变（在更早的门禁处中止）
- `ftth.py count-box` 子命令 rc 透传正常（柳辛庄5-9 rc=2；云峰 rc=0 有产物）

**附带修复（`inspect_closure.py`）**：`--count-box` 指向的文件不存在时，原实现只报
`No such file or directory`。改为分「打不开 / 解析失败」两段，并提示真实成因
（门禁中止时不写产物）；**rc 不变**（仍 return 1）。

**同步入册**：`references/scripts_reference.md` 新增「户数取法的图纸形态判别」一节
（A/B/C/D 四形态 + 三条铁律）；`SKILL.md` 的「户数口径优先级」追加「数箱前先判形态」一句。

**验证中推翻的两处初判（如实记录，避免复发）**
1. `hu_pattern` 采样判据 `fullmatch(\d+户)` 曾疑似匹配不到花括号形态 —— 实测 probe 产物里含「户」的
   155 条**内容全是 `2户`**（花括号系 MTEXT 格式块 `{\f…;}` 清洗残留，**非图纸真实形态**），
   判据命中正确，且 `N户/层` 与总述文字天然排除。**结论：无此缺陷，未改代码。**
2. 「数箱法会把示意箱当户数静默输出」—— 实测示意箱图在**容差量测门禁**处即 rc=2 中止
   （其箱块**无属性**，无关键词种子），不会静默出错。

**通用纪律（已入册）**：「图上有箱」**不能**推出「能数箱」；归层失败（贴末端 > 0 且 合计 = 0）
必须 rc≠0 —— 0 户不是结果，是没测出来。

---

### 2026-09-16（四十五）：**新增几何侧「元素台账」`ledger_elements.py` + 分纤箱补 `x`（P0×2 / P1×2）**

**背景**：用户指定四项解析要点 —— ① 各楼各单元的位置与边界（x/y 都不丢、不重叠）；② 精准识别分纤箱 /
家居箱 / 线缆 / 楼层线 / 数据标注 / 文字标注；③ 分纤箱编号与位置可准确读出；④ 准确画像与选法。
逐项实测现有链路后定位缺口并补齐。

**缺口（实测证据）**

1. **分纤箱只有 y、没有 x（P0）**：`parse_dxf_structured.py` 的 `parse_floor_info` 中
   `fx_list.append({"编号": …, "y": y})` —— 「安装位置」只剩楼层，同一单元同层的两个箱在几何上无法区分，
   也无法与总图按平面位置对照。实测凤鸣朝阳 **17 条分纤箱全部缺 x**。
2. **楼栋/单元无几何边界（P0）**：`parse` 内部算过 `bldg_ranges` / `unit_ranges`，但**不落盘**；
   且 `merge_json` / `split_units` 会**重建**楼栋字典（只留 `标题`+`单元`），坐标若只塞进 parse 会在合并环节再丢一次
   —— 故边界改由**独立台账出口**承载，不穿链。
3. **六类元素无统一台账（P1）**：`EQUIP-箱柜` 层上块属性直接写着 `A=家居配线箱`
   （云峰 443 / 柳辛庄1-4 449 / 柳辛庄5-9 356），是**免几何推断**的户数判据，但此前只在画像侧用到、无生产侧台账；
   云峰 `智-楼层线`（331 条水平段）是 `floor_scale` 的**独立几何来源**，亦未被利用。
4. **分纤箱编号有假阳性（P1）**：关键词扫描把「说明：…在分纤箱盘留5米」「图例 新建分纤箱」一并计为编号
   （实测柳辛庄 270 条命中中大量属此类），会把箱数抬高一个量级。

**处置**

- 新增 `scripts/ledger_elements.py`（几何侧独立出口，与 parse 业务树互不覆盖）：六类元素带坐标枚举 +
  楼栋/单元 `锚点(x,y)` / `x范围` / **y 分带** + 校验（坐标完整性 / 单元越界 / 重叠分型）；缺项显式登记；
  无单元标注时给「分纤箱 x 聚类**线索**」而**不臆造**边界；`rc` 0=正常 / 2=有坐标缺失或必须修项。
- `parse_dxf_structured.py`：分纤箱记录补 `x`（52,348 → 52,718 B，无BOM/CRLF 保持）。
- `SKILL.md`：计数校正 20→21 / 18→19、脚本表加行、加「元素台账」四要点段；完整参数与字段表入
  `references/scripts_reference.md`。

**自查并修正的四条判据缺陷（防"改好 a 弄坏 b"）**

- 台账首版把 `EQUIP-安防` / `EQUIP-消防` 当箱柜层 → 「17 vs 123」是**假警报**；
  改为箱柜**专用层**，图形侧明确标为**超集**、不参与计数裁决。
- 首版单元 `x范围` 退化为 ±`unit_range`（宽 4000，而该楼栋仅宽 410）→ **单元越出楼栋**；
  已**夹回**楼栋边界，并新增「单元越出楼栋」校验项。
- 首版楼栋 y 取全局极值 → 3#楼 y 跨度达 **8.6 万单位**（跨系统图与平面图两个不连续区）；
  改为 **y 分带**登记并标出含锚点主带。
- 首版把「共享标题展开的多栋」（锚点 x 相同）误报为**切分错误**：实测该情形占全部重叠的 **100%**
  （柳辛庄5-9 三组 8 栋 / 云峰 3 栋 / 柳辛庄1-4 2 栋 / 繁华里 1#·3#）。判据改**分型**：
  `共享锚点重叠` 登记为「须另行核定、非缺陷」，`异锚点同行带重叠` 才计须修。

**回归（多项目 × 多方向）**

- 台账五图（云峰 143.5MB / 凤鸣朝阳 / 柳辛庄1-4 / 柳辛庄5-9 / 繁华里）**全部 rc=0**；
  坐标缺失 **0** / 单元越界 **0** / 必须修 **0**；凤鸣朝阳 7 栋 12 单元边界完整、云峰 44 条楼层线入账。
- `parse` 改前（备份）vs 改后**逐键对拍**：凤鸣朝阳 17 处差异**全部是新增的 `分纤箱.x`**，
  剔除该键后**逐键全同（差异 0）**；柳辛庄5-9 **0 差异**。即「修好 a、没坏 b」。

### 2026-09-16（四十四）：**SKILL.md 正文纠错与体量瘦身（乱码 ×1 / 计数 ×2 / 体量 -1456 B）**

> 起因：收口复检时发现 SKILL.md 正文内含 **U+FFFD 乱码**，且体量 **51,309 B** 已贴住自述上限
> 「约 51 KB」（按 51×1000 读法**已超 309 B**）。本次**不动任何脚本行为**，只动文档正文。

- **① 正文乱码（P2）**：原 L383 的 `⚠` 之后是 **U+FFFD 替换字符**（本应是变体选择符 U+FE0F），
  即 `⚠️` 被损坏成 `⚠<U+FFFD>`。已按字节还原：`\xe2\x9a\xa0\xef\xbf\xbd` → `\xe2\x9a\xa0\xef\xb8\x8f`。
  全技能 `.md`/`.py` 复查：**U+FFFD 归零**（此前仅 SKILL.md 一处；assets 下 xlsx 的命中是二进制假阳性）。
- **② 文件计数勘误（P2，两文件互相矛盾且均与实况不符）**：
  实测 `scripts/` 下 **20 个 `.py` = 18 个功能脚本 + 1 个统一入口 `ftth.py` + 1 个公共模块 `ftth_common.py`**。
  SKILL.md 原写「19 个文件 / 17 个功能脚本」、`references/scripts_reference.md` 原写「18 个 / 16 个」，
  两处均已校正为 **20 / 18**。（`ftth.py` 子命令数「10 个」经复核无误，未改。）
- **③ 体量瘦身（P1，防静默截断）**：SKILL.md **51,309 → 49,853 B（-1,456）**。
  四节按「**保留门禁与触发条件、详情指向 references**」压缩：
  `栋级入户规模` 1409→约 780 B、`九级地址表` 961→约 700 B、`模板规则` 674→约 300 B、
  `必须具备的软件环境` 806→约 460 B；另精简 `Step 1b` 开头与 `scripts_reference.md` 重复的通用尾句。
  **触发条件、行数恒等式门禁、模板格式硬约束、「禁止自动择一」等判据全部保留在正文。**
- **④ 补 references 缺口**：`titleblock_and_intake_table.md` §四 补入「地址树与 `gen_addressbook.py`
  产出的『每户一行』扁平表**不可互替**」——该规则原仅存在于 SKILL.md，**外移前必须先落到 reference**，
  否则属静默丢规则。
- **验收（可复现）**：
  - **外移前逐条机器校验** 17 条待外移内容在 references 的覆盖情况；外移后复验 **18/18 命中、0 未覆盖**。
  - **全树比对**：近 15 分钟内仅 **3 个文件**被写入（SKILL.md / scripts_reference.md /
    titleblock_and_intake_table.md）；另 8 个已记 sha 的文件**逐一未动**。
  - **风格保持**：三文件均无 BOM；SKILL.md 全 CRLF，两 reference 全 LF。
  - **事务保护两次拦停（均未落盘）**：① 首次预演 50,012 B 未达安全线 → 中止；
    ② `NEW` 文本块按 `\r\n` 切分导致回写混入裸 LF → **CRLF 守护断言拦停**，修正后通过。
- **遗留（未动，待裁决）**：49,853 B 距自述「>48 KB 必须先外移」舒适线仍超 **701 B**；
  自述上限「约 51 KB」下余量 +2,371 B（51×1024 读法）/ +1,147 B（51×1000 读法）。
  再降需动 `Step 1b` 的脚本索引表（**1455 B**，`scripts_reference.md` 内有同源内容），
  该节属**探查主流程**，未经裁决不动。


### 2026-09-16（四十三）：**修正（四十二）P0-2 引入的回归 —— 4 个脚本缺 `import os`（P0）**

> **自查发现，非外部报错。** 教训：`compile()` 自检**抓不到函数体内的 NameError**
> （编译期不报，运行到那一行才报）；而（四十二）的验收只跑了 `parse` 一条路径，
> 恰好落在本来就带 `import os` 的文件上，于是 4 个真正受影响的文件**全部漏检**。
> **纪律：补完依赖后必须逐脚本实跑到出错那一行，或做 AST 作用域核对。**

- **缺陷**：`analyze_coverage_vshape.py` / `count_box_icons.py` / `extract_fx_locations.py` /
  `read_titleblock_households.py` 被插入 `os.makedirs(...)` 时**未补 `import os`**
  —— 这 4 个文件顶层导入块原本只有 `argparse` / `json` / `re` / `sys` 等，**独缺 `os`**。
  于是运行到写盘行抛 `NameError: name 'os' is not defined`。
- **改**：各文件顶层导入块**按字母序**插入 `import os`；逐文件保持原 BOM 与换行风格
  （4 文件中仅 `analyze_coverage_vshape.py` 带 BOM，其余无 BOM；全部 LF）。
- **验收（双侧，可复现）**：
  - **实跑 A/B**（A =（四十二）前备份，B = 当前）：柳辛庄5-9 `count-box`、凤鸣朝阳 `coverage-vshape`
    在（四十二）版为 rc=1 且无产物；修后 rc=0，产物与 A 版**逐字节 sha 相同**
    （`a45a37e04972…` / `86c12664f324…`）—— 既证明修好，也证明未改坏。
  - `柳辛庄5-9` 的 `extract_fx_locations`：A 版 `FileNotFoundError`（3 层目录未建）→ 修后 rc=0 且写出产物。
  - **AST 作用域核对**：全技能 **11 处** `os.makedirs` 注入点，作用域链上均可解析到 `os`。
  - **运行期核对**：把注入语句放入**各模块真实命名空间** `exec` 一次 —— **11/11 成功建目录**，
    含自然路径走不到的 `read_titleblock_households.py`（该图无图签层）。
  - **新增行引用名核对**：13 个改动脚本的 **92 个**新增引用名全部可解析，**零可疑**。
- **同时确立回归方法学三条**（已回灌 `teleagent-session-forensics` §十三）：
  ① 批量 A/B 脚本开头必须 **preflight 断言解释器依赖** —— 本机 managed Python 无 `ezdxf`，
     否则每条命令秒退 rc=1/2，表现为「全绿假失败」，极易误判成"脚本被改坏"；
  ② 比对必须**分档**：字节 `sha` / 结构差异（**排除已知新增字段**）/ 两侧同行为（rc + 报错一致）
     —— 否则"新增诊断字段"与"两侧同样缺参"都会被误报成回归；
  ③ 失败时**必须打印 stderr 尾部** —— 否则会把「契约要求的 rc=2（缺必填参数）」误读成缺陷。

### 2026-09-16（四十二）：**修复执行链五处缺陷 + 会话效率纪律（P0×4 / P1×1）**

> 依据：并行两会话（凤鸣朝阳 / 云峰）执行全过程监控 + 五项目回归校验。修复原则：
> **只改异常 / 空数据 / 缺参路径的行为，成功路径输出字节级不变**（已实测 probe/parse 新旧 sha 相同）。

- **P0-1 probe 写盘失败被吞成 rc=0**（`parse_dxf_structured.py`）：`except IOError` 只 WARNING，
  而 `sys.exit(0)` 在 try 之外 → 「探查未产出配置」对外表现为成功。改：`ensure_parent` 兜底 +
  失败 `sys.exit(4)`（与 1 输入错 / 2 门禁中止 / 3 不适用 区分）。
  实测复现：旧版 `--out` 指向不存在目录 → rc=0 且**无产物**；新版 rc=0 且产物 215 KB。
- **P0-2 输出目录不建**（8 个脚本）：`analyze_coverage` / `analyze_coverage_vshape` /
  `count_box_icons` / `count_households` / `extract_fx_locations` / `extract_fx_map` /
  `probe_titleblock_tolerances` / `read_titleblock_households`。
  改：写盘前一行 `os.makedirs(os.path.dirname(os.path.abspath(x)) or ".", exist_ok=True)`，
  **与既有 5 处已正确者（merge_json / split_units / gen_addressbook / plan_methods /
  load_geom）完全同构**，全技能一种写法。另 `ftth.py` 统一入口加同款兜底（不 import，避免模块依赖）。
  实测：3 个项目（凤鸣朝阳 / 柳辛庄5-9 / 繁华里）`--out` 指向 3 层不存在目录，均 rc=0 + 产物落地。
  > ⚠️ **本条已部分回滚修正**：8 个文件中有 4 个原本缺 `import os`，插入后运行时抛 `NameError`。详见（四十三）。
- **P0-3 plan 丢弃 probe 的 suggested_params**（`plan_methods.py`）：`--probe` 只取「全量文字样例」，
  `text_layer` / `title_pattern` / `fx_pattern` / `text_type` 被整包丢弃 → 标题识别退化到通用兜底、
  文字样例未按图层收窄。改：新增 `load_suggested_from_probe()`，从 `--probe` / `--config` 回填
  **命令行未显式指定**的检测类参数并打印来源；`ftth.py` 的 plan 分支不再排除 `--config`；
  画像新增 `param_source_actual` 记录实际生效值。
  实测（凤鸣朝阳）：旧版 `[WARNING] 未提供 --title-pattern，改用通用兜底` → 标题 **18** 个；
  新版回填 `title_pattern` + `text_layer` → 标题 **7** 个。
- **P0-4 inspect 空集合假 PASS**（`inspect_closure.py`）：`boxes=[]` ⇒ `null_boxes=[]` ⇒ 走 else 报
  「PASS 0/0 箱均有安装楼层」（C3/C4/C6 同构）→ 空数据判为全合格、rc=0。改：新增 **C0 数据集非空门禁**，
  C2/C3/C4/C6 在空数据集上不得判 PASS；`Report.check(FAIL/WARN)` 同步登记汇总（原实现漏计，
  出现「5 行 [FAIL] 而汇总写 FAIL 1 项」）。
  实测（云峰图）：旧版 rc=0「无 FAIL，可进入后续自检」；新版 rc=2「存在 FAIL，不得出表」。
- **P1-5 inspect 不接受图标法产物**：新增 `--count-box`（并透传于 `ftth.py inspect`）。
  parse 侧无箱（箱体只画图标不写编号）时作为替代口径，并把图标法自身的
  `刻度偏移异常列` 透出为 FAIL —— 实测该图报出 **3 个偏移异常列**，正是当时人工手核的那 3 列。
- **新增 `ensure_parent` / `write_text` / `write_json`**（`ftth_common.py`）：
  统一写盘入口，失败**抛出、不吞**。
- **新增 `references/operations_discipline.md`** + SKILL.md 总则「效率纪律」要点：
  两会话实测墙钟 93~97 min 中**工具执行仅占 3~7%、约 70% 为等用户回话**；据此立三条纪律
  （一次给全 / 禁反复自造探针 / 断流换会话而非反复「点继续」）。

### 2026-09-16（四十一）：**修复参数供给链三处缺陷 —— 箱符号层无建议 / 标题判据过窄 / 提示自相矛盾（P0）**

- **背景（实测复盘）**：某图竖线法失败——`--fx-symbol-layer` 被传成**文字层**、
  `--title-pattern` 被传成 **`bldg_pattern` 的值**；箱位因此回退编号文字坐标、竖干配对率 0%、
  覆盖全空，而脚本仍返回退出码 0。溯源确认**两个错值都不是凭空生成**：
  文字层取自 probe「FTTH 图层候选」列表（那是**文字**层候选），
  楼栋行正则就是 probe 输出里 `bldg_pattern` 的**原值**。故按工具侧缺陷修。
- **P0-1 标题判据放宽（三处调用点同时失效 → 同时恢复）**：旧判据要求楼栋号后**紧跟『楼』**
  （`\d+[#号]楼`），而实测某图整类标题写作「N#住宅光纤入户系统图」「N#配套光纤入户系统图」，
  数字后接 住宅/配套 → 失配点有三：① `_strong_marks` 的「标题」标记（决定标题层能否进
  `text_layer` 候选）② `title_pattern` 建议 ③ 标题图层**强制并入** `text_layer`。
  实测后果：`title_pattern` 推断为 `None`，且标题所在层未并入 `text_layer`（建议值里缺该层）。
  改为统一走 `ftth_common.is_bldg_title_text` ＝「图纸类词 +（数字+# 或 数字+号楼）」，
  **对旧写法是严格超集**——原本能匹配的图纸不会因本次放宽而失配。
- **P0-2 补上 `fx_symbol_layer_suggest` 的生产者**：该键此前**读 1 处、写 0 处**，
  候选方法里恒输出「探查未给出候选图层」，属空头承诺（对照：`dedicated_wire_layer`、
  `titleblock_layer_candidates` 均已实现）。新增 `ftth_common.suggest_fx_symbol_layers()`：
  读几何缓存即可打分（载入约 0.6 s，**无需重解析大 DXF**），四条**与图纸形态解耦**的判据——
  J1 闭合四点矩形且中位宽高 ≤ 2×层高；J2 尺寸一致性（同尺寸簇占比）；
  J3 与「图纸类词标题 x 带」重叠率；J4 众数簇数量 ≈ 图上编号数。
  输出口径：probe 顶层画像信号 `fx_symbol_layer_candidates`；
  plan 写入 `ctx["fx_symbol_layer_suggest"]` → `profile.json` 的
  `param_source.must_probe.fx_symbol_layer`；并对 probe/plan 两处推荐做交叉核对、不一致即告警。
  **判据取舍有实测依据**：单看「闭合四点 + 小尺寸」时，正确层会被数量更多的干扰层
  （大轮廓、门窗块）压到第 3 名——**J2+J3 才是决定性判据**，J4 只在给出编号数时参与。
  **层高估计必须复用既有 `floor_step_from_texts`**（每列一票、跨列取主簇）：自写的
  「楼层文字相邻差取众数」版本被图上大量极短间距文字污染（估成 0.4 → 尺寸闸门压到 0.8 →
  正确层被 J1 误筛）。该教训与 `measure_column_step` docstring 记录的同源。
- **P1-1 消除自相矛盾的提示**：probe 提示文案删去「含配套楼/商业楼」——该措辞紧邻
  `bldg_pattern` 输出行，正是把模型引向错槽位的诱因；改为明确「**不得用 `bldg_pattern`
  顶替 `--title-pattern`**」，并在 `title_pattern` 推断为空时追加显式告警。
  `--bldg-pattern`（对照表楼栋行）与 `--title-pattern`（图纸标题）的职责边界在 SKILL.md 同步消歧。
- **P1-2 新增标题池形态护栏（主）+ 两区不重叠护栏（辅）**：
  - **形态检验**：`--title-pattern` 匹配到的**文字本身**若**没有一条**含『系统图/布线图/示意图』，
    即判为「匹配对象不是光纤入户系统图标题」并以码 3 退出（`--allow-low-pairing` 时降级为告警），
    消息显式点名两类实测误匹配（总图对照表楼栋行 / 楼层平面图标题）并附命中样例。
  - **两区不重叠**：符号层已取到图元、但其 x 与「楼栋 x 带」并集**零重叠**时同样早失败。
  - **为什么两个都要（反向测试的结论）**：误匹配时楼栋 x 带会**整体平移**——各带宽度正常、
    并集甚至仍覆盖符号带，因此「并集是否重叠」**抓不住它**；只做后者仍会退回到逐栋
    「本楼栋 x 范围内找不到任何箱图形符号」而把真因误导向「图层名不对」。
    形态检验才是决定性判据（实测反向跑：错误正则命中 59 条文字、无一带图纸类词）。
- **实机验证（同一张图，只读）**：probe 现在给出
  `title_pattern='(\d+)#.*(?:系统图|布线图|示意图)'`（此前为 None）、
  `text_layer` 已自动并入标题所在层（此前缺该层）、
  符号层候选首名得分 **1.000**【推荐】（一致性 1.00 / 标题区重叠 1.00 / 众数簇 21 / 层高估值 30）。
- **改动面**：`scripts/ftth_common.py`（+7.4 KB）、`scripts/parse_dxf_structured.py`、
  `scripts/plan_methods.py`、`scripts/analyze_coverage.py`、`SKILL.md`（+715 B，
  正文距 51 KB 加载上限余量 2,887 B）、`references/scripts_reference.md`。
  写入前逐文件 `compile()` 语法自检；BOM / 换行风格逐文件保真。

### 2026-09-16（四十）：**SKILL.md 第二次瘦身 —— 消除技能加载截断（P0）**

- **实测口径（关键，纠正此前误判）**：加载体上限按**字节**而非字符——三个时点的送达正文分别为
  **51,092 / 51,041 / 51,031 B**（相差 <70 B），而字符数差 900+（25,383 / 25,581 / 24,618）。
  故**正文上限 ≈ 51 KB**；超出部分被**静默截断**（提示语给 `N bytes truncated` 与一份落盘副本）。
- **背景**：本文件 89,426 B 时每次加载被截 31,375 B，断口在 Step 1b 参数表，逼出补读回合。
  第一次瘦身（第三十九轮）压到 53,873 B，仍超上限 1,300+ B（当时按字符误估）。
- **本次动作（全部为外移，无删除）**：
  - 标准流程 / 信号驱动选方式 / 测量方式组织 / 图纸类型参考 → `references/measurement_architecture.md`
  - 软件环境与命令纪律 → `references/scripts_reference.md`
  - 模板 24 列对照表 → 新建 `references/addressbook_template.md`
  - 栋级入户规模、九级地址表 → 主文件留摘要 + 指针（完整协议本就在 `titleblock_and_intake_table.md`）
  - Step 2 清单 26 条原文 → `references/step2_selfcheck.md`（主文件保留三条硬门禁 + 摘要）
- **结果**：正文 52,335 → 46,737 B（总 53,873 → 48,275 B），**余量 4,294 B（8.4%）**；
  39 项关键锚点核验通过、10 个 references 链接全部可达、BOM/换行风格逐文件保真。
- **新增纪律**：主文件「参考文件」节写入**体量预算纪律**——正文 >48 KB 必须先外移再加，
  禁止把修订记录 / 参数表 / 详细清单塞回主文件。
- **运维发现（重要）**：TeleAgent 侧存在**技能内容缓存**。实测 11:51:16 会话加载的仍是当日 **09:13 的 36 条版快照**
  （完整正文 82,406 B），**未随磁盘更新刷新**；同日 09:19 起的 5 次加载内容完全一致。
  → **改完技能需重启 TeleAgent 应用，缓存才会刷新。**

### 2026-09-16（三十九）：**SKILL.md 瘦身至加载体上限以下 + `shared_drawing` 形态检验与分图区核对 + vshape help 标签修正**

- **用户口径**：以提高效率为目的修复——消除「每次新会话加载被截断」与「画像信号摇摆误导选路」两个反复咬人的点。
- **SKILL.md 瘦身（89,426 → 53,873 字节）**：实测 `skill` 工具单次加载体上限约 **55 KB**
  （某会话加载本技能被截 31,375 字节，断口恰在 Step 1b 脚本参数表，逼出补读回合）。
  四大段外移至 references/，主文件保留全部裁决/禁令的一行式清单：
  - 测量方式架构全文 → `references/measurement_architecture.md`（主文件留方法池表 + 铁律清单）；
  - Step 1a 探查清单全子项 → `references/probe_checklist.md`（主文件留七项一行式 + 总图关键裁定）；
  - 脚本完整参数表 + probe 顶层画像信号 + geom.json schema → `references/scripts_reference.md`
    （主文件留脚本名+一句话职责；geom 三坑警示保留）；
  - Step 2 自检实测案例叙述 → `references/step2_selfcheck.md`（主文件留全部检查项一行式）。
  版本修订记录不再于 SKILL.md 保留条目正文（此前「仅保留最近两条」约定同步废止），统一指向本文件。
  同步修正陈旧计数：ftth.py 子命令 9→**10**（补 `inspect`）、功能脚本 16→**17**（补 `inspect_closure.py`）。
- **`judge_shared_drawing` 形态检验 + 分图区核对（P1，实测信号摇摆）**：同一图纸同一判据，
  历史画像 7/10 报 `present`、3/10 报 `absent`——根因是候选只看「含多个楼栋号」，
  对照表行（如 `1#楼，2#楼`）在宽 `--title-pattern` 下被当共享图纸标题。修复两重形态检验：
  ① 候选须含**图纸类词**（新增 `RE_DRAWING_TITLE`：系统图/示意图/布线图/平面图/竣工图/施工图），
  纯楼栋号罗列只记入 evidence 供人工核对；② **分图区核对**——候选所涉楼栋若另有各自的
  单栋图纸标题，则每楼独立图纸、判 `absent`；部分覆盖判 `unknown` 交人工。
  回归：真实图三种取标题口径（宽/窄/兜底）全部稳定判 `absent`；合成用例 5/5
  （真共享→present、对照表行→absent、索引行带图纸词→absent、混合→unknown、连字符→present+裁决提示）。
  `methods/signals.json` 的 `detect_method` 已同步。
- **vshape help 标签修正（P2）**：`analyze_coverage_vshape.py` 三处「算法常数，默认N」改为真实语义——
  `--y-tol`/`--box-x-tol` 是**自适应下限**（`max(本值, 尺度量)`），`--margin` 是**兜底值**
  （有相邻标题时用间距中位数）。行为不变，只改标签。
- **验证**：SKILL.md 27 项关键锚点 + 4 个外移文件各 5~6 项锚点全部在位，CRLF/BOM 风格逐文件保真；
  全技能 20 个 `.py` 编译通过；`ftth.py` 十个子命令 `--help` 可用。

### 2026-09-16（三十八）：**出表前一体化闭合核查 `inspect_closure.py` 新增 + 探查纪律入 SKILL.md**

- **起因（实测）**：某会话出表前串行编写 7 个一次性 `inspect_*.py` 核查脚本（内容互相重叠），
  是当轮最大耗时项；其中 1 次 PowerShell 内联 `py -c` 多行脚本被 shell 层截断报错
  （`ScriptBlock should only be specified as a value of the Command parameter`）。
- **新增 `scripts/inspect_closure.py`**：parse 结果（必传）+ 覆盖 JSON（可选）+ geom 缓存（可选）
  三源一次核查七项——楼栋单元全貌（楼号断号提示）/ 安装楼层口径分布（null 即 FAIL，呼应（三十七））/
  安装楼层双源交叉（不一致即 FAIL）/ FX 编号坐标双向核对（漏箱/重号即报）/ 楼层表直读清单 /
  覆盖闭合（缺线索、安装层不在覆盖集合内即 FAIL）/ coverage 顶层自检与需人工裁决透传。
  退出码 0 全过 / 2 有 FAIL / 1 输入错误；`--json` 机读输出；仅依赖标准库。
- **`ftth.py` 新增 `inspect` 子命令**转发；`--dxf` 必需校验对该子命令豁免（只读 JSON）。
- **SKILL.md**：Step 2 自检首部增「一体化闭合核查」条（清单内事项禁止再写临时 `inspect_*.py`）；
  总则增「探查纪律」（探查脚本一律写文件执行、禁止 shell 内联；`gen_addressbook` 自带覆盖 JSON
  格式自动检测、无需预查结构）。
- **与 `verify_coverage_truth.py` 的分工**：本脚本用于出表前（无需 xlsx）；
  verify_coverage_truth 用于有定稿表后的回归反查。阶段不同，不重叠。
- **回归（同产物双跑）**：旧口径 parse 结果（安装楼层 17/17 null）正确报 FAIL、rc=2；
  （三十七）修复后产物 17/17 有值且双源一致、rc=0；仅 parse 降级运行 rc=0（可选项 SKIP）；
  坏输入 rc=1。

### 2026-09-16（三十七）：**分纤箱安装楼层废除距离闸门 —— `install_tol` 全链移除（口径与 `analyze_coverage` 统一）**

- **用户口径**：只处理技能侧可改部分；安装楼层一律走**纯区间法**，与 SKILL.md 既有三条明文一致
  （区间法定义不含距离闸门；安装楼层必须与户数同用区间法；禁止用「最近楼层线法」测安装楼层）。
- **缺陷（P0，实测双源对照）**：`parse_dxf_structured.py` 的「分纤箱安装楼层」是**全技能唯一**带 `tol`
  的区间法调用（`tol = install_tol` ＝ 1/6 倍层高）。闸门在 `bisect_right` **完成区间归属之后**再二次
  否决，效果等价于「必须贴着下方层线才算」＝ 最近楼层线法。同一张图两条产线两个结果：

  | 来源 | 判据 | 结果 |
  |---|---|---|
  | `parse_dxf_structured.py` | `tol = 1/6 × 层高` | **17/17 分纤箱安装楼层全为 `null`**，脚本仍 `rc=0` |
  | `analyze_coverage.py`（`f_install`） | `tol=None` | 同一批箱楼层键全部有值 |

  实测该图 17 个箱到下方层线距离均为 2.3，闸门宽 1.0867（层高 6.52）—— 闸门只覆盖楼层带宽的 **16.7%**。
  箱体落点不固定，任何小容差闸门都必然落空；同一函数在 `count_households.py` 用的是 `1.0 × 层高`
  （闸门恒不触发），两处比值**差 6 倍**。
- **修正**：`tol=args.install_tol` → **`tol=None`**（`dist` 仍返回，口径A/B 判别不受影响）；
  `install_tol` 的比值／回退值／命令行参数／输出 JSON 字段／`ALGO_DEFAULTS` 条目**一并移除**
  —— 该参数两种语义都不成立（当贴线判据用，对象不贴线；当区间兜底用，宽度不足带宽 1/6）。
  `assign_floor_by_interval` 的 `tol` 形参补文档约束：仅用于「标注吸线」，测安装楼层**不得传 tol**。
- **同类误标一并修正**：「随坐标尺度变化」的阈值被标成「算法常数（与图纸无关），可沿用」，
  与该技能自己的判据（「判据是是否随坐标尺度变化，不是名字里带不带容差」）直接冲突。
  涉及 `plan_methods.py` 的 `ALGO_DEFAULTS`、`building_cluster` 与 `shared_mixed` 的 `manifest.json`、
  `measurement_methods.md` 示例、`analyze_coverage.py` 模块 docstring；表内数值实为 `AUTO_FALLBACK` /
  `DEFAULT_*` 兜底值，故改为「由本图自适应，量测失败才回退，不得跨图沿用」。
  `measurement_methods.md` 中「`merge-tol=2.0` 属常数」亦为误述（代码已是 `1/15 × 层高`）。
- **接口变更（破坏性）**：`parse_dxf_structured.py` 与 `ftth.py parse` 不再接受 `--install-tol`；
  沿用旧命令会**显式报错**（而非静默忽略）。输出 JSON 的 `参数` 块不再含 `install_tol`。
- **验收**：改后重跑同一张图，与改前产物**逐单元对账** —— 除 `分纤箱[].安装楼层` 与
  `安装楼层口径` 外，其余字段须逐项一致。


### 2026-09-16（三十六）：**图标法是区间法的一种 —— 图标法 `requires` 补 `floor_scale`（接线缺口修正）**

- **用户口径（第三轮补正）**：**图标法是区间法的一种**；区间法内数每层楼的户数，锚点可以数家居配线箱、
  也可以数皮线条数，**首选数配线箱**（现场更好操作）。此口径把图标法从"与区间法并列的方法"归正为
  **区间法的锚点变体** —— 与 SKILL.md 方法池表既有表述（区间法 → ①每层户数，锚点取皮线标注 / 家居
  配线箱图标）一致，此前 `classify_method` 已补「图标 → 区间法」，但 **`requires` 未随之对齐**。
- **核验发现接线缺口（P0）**：`scripts/plan_methods.py` 的图标法候选 `requires` 原为
  `["dedicated_wire_layer", "box_icon_annotation"]` —— **双前置，漏了区间法公共前置 `floor_scale`**。
  而图标法确凿消费楼层刻度，实测证据（`count_box_icons.py` 产物）：
  - 每列结果均带 `刻度列x`（实测图 13 列**全非空**）；
  - `归层后总户数 331 = 贴末端图标数 331`、`未归属图标数 0`；
  - `逐层` 为 `[["B1",1],["1F",4],…]` 形式的**按楼层带展开**；
  - 无刻度列（`sc` 为空）时其 `if sc` 分支使 `"合计": sum(per.values()) if sc else 0` **恒为 0**、
    `"逐层": []` 为空 —— 即**该法产出全部来自落楼层带**，无刻度列必然空跑却被"选定"。
- **修正（接线，非行为发明）**：
  `requires` → `["floor_scale", "dedicated_wire_layer", "box_icon_annotation"]`。
  **皮线法维持 `["floor_scale"]` 不动** —— 这种不对称是**本质差异**：皮线法的锚点取自**皮线标注
  文字**（`count_households.py` 无「皮线图元」门禁），而图标法的锚点判据是「贴皮线**图元**末端」，
  故必须有可自动识别的专用连线层。
- **补丁后选法（生产路径 `build_steps()` 实测，14 组信号矩阵）**：
  - 有图标 + 有连线层 + **无楼层刻度** → 图标法**不再被选**（与皮线法同因 `floor_scale` 缺失而并列
    不可用，申报 `absent` / 阻塞、交人工）—— 修正前会选出一个必定产 0 的方法；
  - `floor_scale` 为 `unknown` → 同样不再被选（`_pick_method` 只认 `PRESENT`）；
  - **有楼层刻度时逐项不变**：云峰仍选图标法、柳辛庄型（无连线层）与凤鸣朝阳（variant 长句）仍直读。
- **文案同步**：`plan_methods.py` 两处「双前置」→「三前置」并补候选注释（说明 `floor_scale` 的实测
  依据）、`methods/building_cluster/manifest.json`（`requires` / `params.前置` / `cross_check`）、
  SKILL.md「信号状态是选法唯一依据」段与（三十五）条正文。
- **复现命令**：
  - 选法矩阵：`python teleagent-audit/test_pick_household.py`（11 组）、`test_pick_fs.py`（7 组）
  - 改动复验：`python teleagent-audit/verify_r3.py`（风格 / 断言 / JSON / 编译）
  - 全脚本冒烟：`python teleagent-audit/smoke_all.py`
- **未动**：文字归属仍按 x 窗口、不做 y 分带过滤（皮线路径跨带串栋根因，即（三十五）条所载 P0-A）；
  `manifest.json` 其余 3 个子任务（楼栋分组 / 覆盖判定 / 分纤箱提取）的候选表仍与代码有漂移。

### 2026-09-16（三十五）：**户数口径优先级全链核证 + 「前置否决」表述与实现对齐 + 档案候选表漂移归位**

- **背景**：用户复述业务口径要求核证 ——
  「统计每层户数：先看有没有户数标注，有就直读；没有就选区间法；区间法内首选数家居配线箱、次选数皮线」。
  以**生产路径** `build_steps()` 造 11 组合成信号实测（脚本：`teleagent-audit/test_pick_household.py`）。
- **核证结论：口径已实现、候选顺序正确**。候选表顺序 = 直读『X户』→ 图签『N层/M户』→ 图标法 → 皮线法；
  `_pick_method` 按列表顺序取「`requires` 全成立」的首个。11 组实测中 10 组与用户口径一致：
  有『X户』→ 直读（图标法降为同可用备选）；无标注 + 图标 + 连线层 → 图标法；无图标 → 皮线法；
  只图签 → 直读；全无信号 → 申报 `absent`（放行 + 降级）；信号 `unknown` → 申报 `unknown`（拖垮门禁）。
- **唯一分歧项（实测澄清，非缺陷）**：「有图标标识、但图上无皮线图元」时选皮线法，与「有图标就数图标」的
  字面口径不同。真因：图标法的 `requires` 是**双前置**（`dedicated_wire_layer` + `box_icon_annotation`），
  而 `count_box_icons.py` 在找不到任何皮线图元时硬失败 `rc=2`（L482 门禁）、一个结果都产不出 ——
  此时图标法**跑不出来**，回落皮线是唯一可执行路径。已在该类图纸上实测确认（此类图同时具『X户』标注，
  直读在先，实际不受影响）。
- **表述修正（文档 ≠ 实现，已收口）**：皮线法 `params` 的「前置否决」原写
  「`box_icon_annotation` 为 present 时**不得选本法**」—— 与实测行为不符（该情形下皮线法确实当选）。
  改为「**图标法可用时**不得选本法（双前置齐备）；图标法不可用时允许回落」。
  同步点：`build_steps()`、`methods/building_cluster/manifest.json`、SKILL.md 选法总则。
- **`cross_check` 文案纠偏**：户数提取原写「多个候选 `requires` 同时成立时**必须并跑比对**」——
  与用户裁决（有图标就不数皮线）冲突。改为「按候选顺序取首个可用者、**非并跑**；划定实体口径后
  仅与『X户』直读值对账，不一致交用户裁定」。
- **档案候选表与代码的 `requires` 漂移（本子任务已同步）**：`methods/building_cluster/manifest.json`
  的户数提取候选漏挂 `dedicated_wire_layer`、皮线法 `requires` 为空 —— 与 `build_steps()` 不一致。
  已同步为与代码同形并补 `params` 说明。**注**：`compare_archives()` 只读档案的 `signals` 做相似度比对、
  **不消费其 `steps`**，故该漂移不影响选法，属档案文本缺陷。**其余子任务（楼栋分组 / 覆盖判定 /
  分纤箱提取）的档案候选表同样漂移，本轮未动**（需专项决定「档案是否与代码严格镜像」）。
- **回归（三项，均与改动前逐项一致）**：
  ① 11 组合成信号矩阵改动前后**逐项一致**，差异行仅 `cross_check` 文案 1 行；
  ② 云峰画像对拍 4 行差异**全为文案**（`前置否决` + `cross_check`），选定方法仍为图标法、门禁 pass；
  ③ 三图回归 —— 云峰（present + 有连线层）→ 图标法；柳辛庄1-4（present + 无连线层）→ 直读『X户』；
  凤鸣朝阳（variant 长句）→ 直读『X户』；三图门禁均 pass。

### 2026-09-16（三十四）：**户数口径优先级——有家居配线箱图标则数图标、不数皮线**（用户裁决）

**来源**：用户裁决（2026-09-16）。**取代**（三十三）中「`count-box` 与 `count` 双口径并跑互证」
与 SKILL.md 相应条款——旧规定把两条户数口径当平行候选，实作中皮线列会跨楼层带串到邻栋
（某图实测一列皮线 y 跨度横跨两个带、一列混了两栋），而图标是每户一个的物理实体、
实测零重复绘制，可靠性更高。

**新规则**：图上**存在家居配线箱图标（每户一个、贴皮线末端）时，优先数图标、不再数皮线**；
图标不可用（图上无图标 / 图标为「每单元每层一个」的示意画法 / 门禁 rc=2）时才回落皮线计数。
与 `X户` 直读值的对账保留；若两口径都跑了且不一致，仍暂停交用户。

- **`plan_methods.py` 接线补齐（P0，本轮最大缺口）**：`box_icon_annotation` 信号此前
  **只在 `methods/signals.json` 有定义、脚本从未计算** —— 依赖它的候选 `requires` 恒为
  `unknown`，「户数提取」永远选不到图标法。现新增 `collect_insert_idents()`（采集 INSERT
  块名 + 属性值，不取几何——图标是否贴末端属测量阶段判据）与 `judge_box_icon_annotation()`
  （文字实体 + INSERT 双路判标识；无标识但存在专用连线层判 `variant`＝疑「只画方块不写字」，
  须现场确认，**不算前置成立**），并在 `main()` 注册。
- **候选排序即口径优先级**：`_pick_method` 取「requires 全成立的列表首个」，故把图标法排在
  皮线法**之前**、挂 `requires=["dedicated_wire_layer","box_icon_annotation"]`；皮线法候选注明
  `前置否决`。**回归（实测某图，143MB FTTH 系统图）**：改动前选「区间法（INSERT/皮线锚点）」
  → `count_households.py`；改动后选「图标法」→ `count_box_icons.py`，皮线法降为同可用备选。
  信号其余 12 项逐项一致、门禁仍 pass，形态名仅多一项「有家居配线箱图标」。
- **`classify_method` 补「图标 → 区间法」**：图标法是**区间法的锚点变体**（原理同为
  「锚点落楼层带」，只是锚点取箱图标而非皮线标注），与 SKILL.md 方法池表「区间法 →
  ①每层户数（皮线标注 / 家居配线箱图标 落在哪条带）」的既有表述一致。补前归类落到
  「其他」，下游「安装楼层随选定方法导出」的分支判断随之失配。
- **关键词唯一真源**：家居配线箱关键词（`HOME_BOX_STRONG_KEYS` / `HOME_BOX_WEAK_KEYS`）与
  词边界命中工具（`kw_split_ascii` / `kw_hit` / `home_box_kw` / `home_box_hit`）**收敛到
  `ftth_common.py`**，`count_box_icons.py` 改为引用（本地名 `STRONG_KEYS` / `WEAK_KEYS` /
  `_kw_split` / `key_hit` 留别名，下游调用点零改动），`plan_methods.py` 同样引用。
  此前若在 `plan_methods` 另抄一份必然漂移（同「镜像铁律」）。回归：15 个样例词边界判定
  15/15 正确（`HDMI` / `CHD` / `SHD` 未被 `HD` 误命中）。
- **信号判据收紧（三图回归时发现并修复）**：`judge_box_icon_annotation` 的文字实体分支加
  **短标签约束**（`_HOME_BOX_TEXT_MAX = 12`）——长句里的关键词不作存在性证据（依据 SKILL.md
  「信号判 present 须过形态检验」）。起因：实测某图报
  `present :: 命中家居配线箱标识：文字『自地下车库引上至大堂弱电箱』`，而该图并无家居配线箱
  图标——是「弱电箱」被路径说明长句误命中。收紧后该图判 `variant`（evidence 明示「仅长句命中
  疑似词」），图标法不可选、回落直读『X户』。块名 / 属性值天然是短标签，不受长度约束。
  单测 11/11 通过（含 12/13 字边界）。
- **三图回归（最终证据）**：云峰（`present` + 有专用连线层）→ **图标法**；柳辛庄1-4
  （`present` + 无专用连线层）→ 图标法被正确拒绝、回落直读『X户』；凤鸣朝阳（`variant`
  长句 + 无专用连线层）→ 回落直读。三图门禁均 pass。
- **`signals.json` 结构修正**：`box_icon_annotation` 原为**扁平字符串**（13 个信号中唯一不按
  `description`/`detect_method`/`level` 组织的），现补齐为标准结构并加 `applies_to` 与优先级 `note`。
- **档案同步**：`methods/building_cluster/manifest.json` 的户数候选把图标法提到皮线法之前，
  `cross_check` 改写为口径优先级。
- **文档同步（SKILL.md 七处）**：户数实体表加「取用优先级」；图标法小节「必须与皮线并跑互证」
  改为「与皮线口径的取舍」；子任务表「每层户数」行改为「②③同时成立时取②」；自检清单
  「户数双口径并跑互证」改为「户数口径优先级」；`count` / `count-box` 说明改为同属区间法的
  两种口径；「信号状态是选法唯一依据」加唯一例外（户数口径）；信号数 12 → 13。
  `references/measurement_methods.md` 两处：方法缺失去路表（区间法行补锚点优先级）、
  §3.6「无户数标注时的户数统计」。
- **未决（交用户，本轮未动）**：文字归属仍按 x 窗口、不做 y 分带过滤（皮线路径的跨带串栋根因，
  只在 `count_households.py`）。本轮的"有图标则数图标"在**方法层面绕开**了它的实际影响面，
  但该缺口本身未修。

### 2026-09-16（三十三）：**静默错误防护三件套 + 分带能力同步 + 接口/探针补强 + 几何缓存 v3 + 楼层标注自洽性判据**

**来源**：云峰项目会话（22:56→00:01，65 min，产出 386 户标准地址表）全量复盘 + 独立核验。
核验纪律：逐条查源码、不采信自述；**复盘的"坑"全部成立，但它的"时间账"数字大面积失准**
（实测与自述差 2~7 倍，且漏掉占 62% 时长的最大项=单次长推理）。本条目只记**落到技能里的改动**。

**方法论**：整目录备份（32 文件 / 820KB）→ 逐项改动 → **生产参数在真图重跑对拍** →
只接受"变化落在预期维度"的回归 → 逐条记复现命令。

- **静默错误防护（P0，三处）**
  - `count_box_icons.pick_scale`：**保留原配对逻辑不变**，新增**刻度列偏移异常检测**——
    某列配对偏移 > 主偏移中位数 × `--scale-outlier-ratio`（默认 1.5）即标记。结果列加
    `刻度偏移异常` / `偏移异常说明`，JSON 加 `刻度偏移异常列` / `刻度偏移主中位数` /
    `偏移异常阈值倍数`，控制台加 `!` 告警块。
    起因：该函数注释自证 *"全程只看 y 覆盖是否够，**不看偏移大小**"*，且**已返回"刻度偏移"
    字段却无任何阈值校验** —— 配错刻度列是静默的（实测 7#/11#配套 x 仅差 0.7、9#1单元/4#配套
    皮线 x 差 25，两处串扰）。
  - `count_households` **出表守门**：`_gate`（硬失败 `sys.exit(1)`，须 `--allow-lossy` 放行）
    + `_soft`（有损但不阻断，写自检 + log.warning）。触发条件 = 尺度锚校验失败 /
    **全部**栋有皮线却无楼层标注 / 全部皮线均未归属 / 未归属占比超 `--max-unmatched-ratio`（默认 0.5）。
    分级原因：实测 11#配套楼、9#楼局部无楼层标注属正常，**只有"全部栋"无标注才是口径选错**。
    起因：旧实现这些情形只打一行 `log.info` 就照写 JSON（全脚本仅 3 处 `sys.exit`），
    下游拿到一份"看起来正常的空结果"。
  - 尺度锚校验 `ftth_common.validate_scale_anchor(step, texts, lo=1.5, hi=10000.0)`：
    层高与字高中位数之比 < `lo` 判**量测污染**（实测某图把"皮线行距 1.6"当成层高，
    而字高中位数 3.5 → 0.46 倍，排版上不可能）→ 降级绝对默认值并记 `_anchor_fail`。
    **`hi` 必须设极宽**：真实图纸层高/字高比可到几百倍，设窄会误杀大坐标图
    （实测初设 500 即误判 step=3000 为异常，已改 10000）。
- **分带能力同步（P0，"镜像铁律"）**：`--title-band-tol` 此前**仅**存在于 `analyze_coverage.py`。
  现把拆分逻辑提为公共函数 `_x_groups()` / `_ranges_from_x_groups()`，新增
  `ftth_common.compute_bldg_ranges_banded(anchors, band_tol=None, log=None)`
  —— 按 y 分带后再中分，`band_tol=None` **退化为原 `compute_bldg_ranges`（行为逐位一致，已对拍）**；
  `count_households` 接入（容差 = `--title-band-tol` 或 2 倍层高自适应，新增 `--title-band-tol` 参数）。
  **未接线（已知局限）**：`parse_dxf_structured.py` 仍无分带概念。见下方"已知局限"条。
- **新增通用判据 `floor_mark_conflicts(items, y_tol=0.001, max_report=5)`**：
  检查一组楼层标注的**同名多址**与**次序倒挂**，返回冲突描述列表。
  **必须喂未去重的原始列表** —— 字典表 `floor_marks[txt] = y` 已把多址静默覆盖成一条，喂字典等于没查。
  起因：`parse_floor_label` 认可 `B<数字>` 地下层写法，而路由/端子图上的端口标号 `B1`…`B9`
  **与之同形**，会被一并收进楼层表并**静默污染区间法归属**（实测会把分纤箱归到不存在的 `B9` 层）。
  `count_households` 已接线：写入 `楼栋[栋].楼层标注冲突` 与 `自检.楼层标注冲突`，控制台 warning。
  **只报不拦** —— 本脚本输出定位是"线索非结论"，拦死会误伤正常图。
- **皮线同坐标重复绘制去重（P0）**：`count_households` 按 `(x, y, 内容)` 去重并报条数
  （`楼栋[栋].重复绘制条数` / `自检.重复绘制条数` + 控制台告警）。
  起因：实测某图 6#楼同一层两条皮线各画两遍，文字法**静默虚增**（34 vs 图标 32），
  双口径首次对不上、追加一轮核实才发现。**只有三者全同才判重复**（不同层同名文字 y 必然不同，不会误合并）。
- **接口一致性（P1）**：`gen_addressbook` 新增 `_norm_unit_key(ukey, bkey)` ——
  覆盖 JSON 的单元键**全名（`1#楼1单元`）/ 扁平（`1单元`）双形兼容**（旧实现只认一种，
  实测某会话**整轮失配**，需临时写 `coverage_flat.json` 转换），键失配时自检告警
  （借此抓出配套楼 2 处真实缺口）；模板尾行按首列标识前缀**去重**，
  防止"以产物为模板再出表"时标识行累积。
- **探针补强（P1）**：`extract_fx_map --probe` 打破"鸡生蛋" —— 未传 `--fx-pattern` 时
  按**形状模板聚类**自动推荐候选，未传 `--bldg-pattern` 时列出含"楼"文字的候选写法。
  `_shape_template()` 加 `maxlen=20` 且过滤 `\n`/`\r`（防多行说明文字与图名拼成跨行模板排首位）。
  起因：旧实现缺 pattern 时**静默返回 0 条**，实测一次 19.8s 换 0 条。
- **几何缓存 v3（P1）**：`extract_geom` 升 **v3**（`GEOM_VERSION=3`）—— 新增
  `polylines`（**整组顶点**，不拆段，含 `closed`）与 `insert_attrs`（与 `inserts` **同索引**的块属性）；
  `dump_geom.py` stat 补 `n_polylines` / `n_insert_attrs`；`inserts` 保持五元组向后兼容。
  起因：独立核验指出 `count_box_icons` 走不了 `load_geom` 的**真因是缺这两样**，
  而非此前以为的"缺 TEXT/MTEXT 类型字段"（`segs` 是 52,934 条**逐段**线段，不含多段线组与块属性）。
  `geom.json` 字段序已写进 `SKILL.md` Step 1a（**首版读错字段序会白跑一轮**：`texts` 是
  `[图层, x, y, 文本]`，"图层"在首位）。
- **选法池补齐（P2）**：`plan_methods` 户数提取候选表补入**图标法**（`count_box_icons.py`），
  cross_check 扩展到四口径并跑 —— 此前该方法未入选法池，`plan` 永远不会选中它，
  选法与实际脱节、导致人工裁决。
- **参数易用性（P2）**：`gen_addressbook` 新增 `--floor-format`（auto/chinese/raw）
  / `--door-format`（auto/int/str），**显式指定优先于模板示例行**（旧实现只能靠改模板示例行绕过）。

**回归（生产参数在真图重跑，逐栋对拍）**

| 改动 | 回归方式 | 结果 |
|---|---|---|
| 皮线去重 | 云峰全图重跑 vs 改前 JSON | **仅 6#楼变**（68→64 条，15F 8→4）；其余 10 栋逐项一致；修正后与该图**图标法口径一致**（6#楼 64 户） |
| 出表守门 | 云峰重跑两路径 | 尺度锚污染 → rc=1 并打出可执行提示；局部栋缺标注按 `_soft` 放行不阻断；`--allow-lossy` 正常写出 |
| 分带同步 | `band_tol=None` 对拍原 `compute_bldg_ranges` | 行为逐位一致 |
| 键归一化 / 出表 | `gen_addressbook` 产物 vs 改前 | **零差异** |
| 符号层 / 图标法 | `count_box_icons` 产物 vs 改前 | 零差异；告警路径已单独验证触发 |
| `floor_mark_conflicts` | 合成用例 6 条（含 B1~B9 混入 / 同名多址 / 次序倒挂 / 同址重复不误报 / WF 哨兵不误报）+ 云峰真实数据 | 合成用例全过；云峰命中 `4#配套楼`、`7#楼`（见下方"新发现"） |

**本次新发现（已取证，未改动核心逻辑，待裁决）**

- **`分带` 只改锚点网格，文字归属仍按 x —— 跨带泄漏未消除（P0 级结构问题）**。
  证据：`count_households.py` 的文字归属是 `if xmin <= t["x"] <= xmax`（**纯 x 窗口，无 y 分带过滤**），
  分带只影响 `.get("楼")` 的 x 锚点网格。实测云峰（住宅行 y≈-4036 与配套行 y≈-3621.7 的
  标题 x 互相穿插）：`--title-band-tol 100` 让分带数 1→2、`4#配套楼` 冲突消失，
  但 `7#楼` 皮线列由 `[]` 变为拿到 x=26733.6 的 28 条、`9#楼` 拿到 x=26924.8/x=27039.6 的 20 条
  ——**皮线列在栋之间搬家，归属并未变可靠**。另 `cluster_by_x` 按 x 聚簇同样不区分 y，
  实测某 x 列的 y 跨度 -3974.78~-3543.68 **横跨两带**，即一列里混了两栋的皮线。
  → 结论：本图**单带与分带两种跑法都给不出可信的逐栋文字法户数**，现有流程把它当"线索"、
  以图标法 + 用户裁决定案（386 户）是正确处置。**修法方向**：让文字与皮线的归属同时受
  (x 窗口 ∈ 栋) ∧ (y ∈ 该栋所在带) 约束，带 y 范围按相邻带 y0 中分（与 x 中分同构）。
  属**行为变更**（会改户数归属），需专项回归对拍交付表，故**未擅自实施**。

**已知局限（本轮未做，勿误以为已支持）**

- `parse_dxf_structured.py` **无分带能力**（`--title-band-tol` 未接线），且强依赖 `X户` 标注 ——
  遇到"无 X户 标注 + 上下分带"的图，该脚本不可用，应在 Step 1a 画像阶段就**明确声明适用范围**，
  不要等解析时白试一轮。
- `count_box_icons` 的刻度列串扰只加了**告警**，未把"列聚类 + 精确 x 键"的绕法固化进脚本。
- `floor_mark_conflicts` 仅接入 `count_households`；`parse_dxf_structured` / `analyze_coverage*` /
  `extract_fx_map` 的楼层表建表点**尚未接线**（改动会波及各自容差逻辑，宜专项）。
- `coverage.json` 键格式的统一做在**消费端**（`gen_addressbook` 双形兼容）；
  **产出端未变**，SKILL.md 已写明该契约。

### 2026-09-15（三十二）：**缓存集中化（图纸目录零污染）+ docstring 对齐**

- **缓存集中化（P2）**：`ftth_common` 新增 `_central_cache_path()` —— 缓存统一放
  `%LOCALAPPDATA%/ftth-address-extractor/cache/<路径哈希>__<文件名>`；**读**时先集中目录、
  再图纸同目录旧缓存（只读兼容），**写**时只写集中目录。起因：pickle 缓存是整个 ezdxf
  对象图（实测某大图 141MB），落图纸同目录污染用户交付目录。落地时已将既有 5 个缓存
  （约 158MB）迁入集中目录，命中实测正常。同补丁修复 docstring 内反斜杠被解释为转义
  （SyntaxWarning）的问题——**教训：写进 Python 字符串的 Windows 路径一律用正斜杠**。
- **docstring 对齐**：`count_households.py` 头注 8 处「默认XX」与实际 argparse 不符
  （实际 default 全为 None=探查必填/层高自适应），已全部按实际改写；
  `gen_9level_addressbook.py` 头注示例参数名 `--lv5-field/--alias-field` 更正为
  `--lv5-idx/--alias-idx`。
- **目录卫生确认**：scripts 下 5 个一次性探查产物 JSON（约 800KB，其一含用户桌面绝对路径）
  已由前序会话清理，本轮复核为零残留。
- **回归**：两张图纸 vshape 产物与改动前逐项一致（其一含 P0-13 的 14F 修复，
  另一张逐字节一致）。

### 2026-09-15（三十）：**引用纪律 + 只读几何快速路径 `load_geom`**

- **引用纪律（通用）**：技能内文档/代码互相引用一律用**章节名或条目标题**，**禁止写行号**。
  起因：此前文档与代码里有 6 处按行号引用本文档（如「第 70 行 直写优先」「第 331 行 三项均须一致」），两次插入内容后已**实际指错位置**
  （`analyze_coverage.py` 4 处 + SKILL.md 2 处）。本次全部改为章节名锚点，并写入总则防复发
- **新增 `ftth_common.load_geom()`（只读几何 JSON 快速路径）**：读 `<DXF>.geom.json`，命中即 `json.load`。
  实测某 143MB 大图的几何查询：全量解析 76s → pkl 命中 20s → **本路径 0.2s**；
  与 `load_dxf` 直读对账（texts / inserts / segs / layers / bbox）逐项相等。
  `dump_geom.py` 改为复用 `ftth_common.extract_geom()`——抽取逻辑只维护一份，产物带 `_src` 双向互通

### 2026-09-15（二十九）：**性能层落地 —— `load_dxf` 磁盘缓存 + `dump_geom` 全量几何转储（同图只解析一次）**

大图全量解析是分钟级、遍历实体是亚秒级：同图反复 `readfile` 属纯浪费（实测某大图单任务被重复解析 20+ 次）。两项落地：

- **`ftth_common.load_dxf()` 内置 pickle 缓存**：图纸同目录 `<DXF>.pkl`，mtime+size 校验失效，
  损坏/版本不兼容自动回退重解析。所有技能脚本经它加载（返回值与语义不变，下游零改动）
- **新增 `scripts/dump_geom.py`**：Step 1a 首跑，产出 `<DXF>.geom.json`（文字/INSERT/线段/图层/包围盒，
  线段含 `closed` 标记）。内联临时查询一律读它，不再回原图
- SKILL.md：总则增设「性能纪律」；Step 0 增设「脚本路径纪律」（禁猜用户目录——历史事故：按不存在的用户目录试跑，白耗分钟级）
- 清理 `scripts/` 下 4 个历史 `.bak_*` 残留（备份按维护约定一律存技能目录外）

### 2026-09-15（二十八）：**V 型法分带「内容连通块」判据 —— 一行内并排图幅的误切修复**

**触发**：（二十五）三登记的两条隐含前提之一（「各图幅按 y 上下分层」）在某图上不成立，
该图 V 型法 rc=2（全部楼栋无可用米数列）。修法按（二十五）三的候选①方向落地。

1. **根因（两处叠加）**
   - **误分带**：分带按**标题 y 聚类**，而该类图纸各图幅是**同一行内 x 方向并排**，
     其标题 y 存在多个微簇（簇间距远小于本图内容跨度）⇒ 被切成 6 个「带」，
     真·系统图标题与其下方的内容被拆散到不同带。
   - **方向相反**：该类图纸内容画在标题**下方**，而窗口 y 边界的前提是「内容在标题上方」
     （上界 = 邻带标题 y、下界 = 相邻标题中点）⇒ 真标题窗口内米数 **0 条**。
   - 实测：该图 148 条米数全在**一个** y 连通块内（跨度 121），而标题 y 分簇 6 个；
     另实测该图标题 y 混有**平面图图纸名**与**平面图楼栋名**两类非系统图文字，共 18 条。

2. **修法（P0-12，尺度无关）**
   - 新增 `_content_blocks_1d()`：本图米数行按「相邻 y 间距 > 3×层高 即断开」汇成连通块
     （与「第二刀」窗口内行块检测同一口径）。
   - **内容块数 == 1 且 标题带数 > 1** ⇒ 强制单带；带 y 边界直接取该内容块范围 ± N×层高
     （内容块 = 本图数据区的真实纵向范围，与坐标尺度无关）。
   - 多内容块时**完全不介入**，沿用原 y 聚类。
   - 单带时不追加 `[图幅N]` 后缀（`len(_bands) > 1` 条件自然为假）。
   - 「参数」新增 `内容连通块数` / `内容连通块y` / `强制单带` 三项留档。

3. **跨项目验证（pre/post 双版本、同命令、逐字段对账）**

   口径：展平成 `{(楼栋, 单元, 箱序号): (箱编号, 安装楼层, 覆盖楼层元组)}`，
   **只在一侧出现的键必须为 0**。备份 `analyze_coverage_vshape.py.bak_20260915_1330_pre_p0_12`。

   | 图纸形态 | 内容块数 | 改动前 | 改动后 |
   |---|---|---|---|
   | 多地块上下分层型 | 4 | 22 楼栋 / 展平 58 行 / 裁决 3 | **逐字段一致**（仅一侧键 0、值变化 0） |
   | 多地块上下分层型（另一） | 4 | 24 楼栋 / 展平 42 行 / 裁决 19 | **逐字段一致**（仅一侧键 0、值变化 0） |
   | 一行内并排型 | **1** | 6 带、仅 5 个单元出结果、28 项待裁决 | **单带、12 个单元（8 栋楼全覆盖）、11 项待裁决** |
   | 「设备块+连线」型 | 0（无米数） | rc=2 不适用 | rc=2 不适用（**行为不变**） |

> **通用规则**：凡是「按某一维把对象聚成组」的逻辑，定组依据要选**与分组目的同源的量**。
> 此处分组目的是「划分图幅」，同源量是**内容（米数）的空间连通性**，而非标题的坐标分布——
> 标题只是内容的**索引**，索引的分布形态可以与内容的分布形态不一致（本例即完全不一致）。

### 2026-09-15（二十七）：**图签读取 `--band` 分段崩溃修复 —— 落带外标注的 `None` 键**

**触发**：从零测试报告实测暴露。`read_titleblock_households.py` 给了 `--band` 时**直接崩溃**：
`TypeError: '<' not supported between instances of 'str' and 'NoneType'`。

1. **根因**：`_cluster_bands.which(y)` 在标注 y 落于**所有 `--band` 范围之外**时返回 `None`。
   `read_titleblock()` 的「层户 → 楼」「单元 → 楼」两条归属路径**未判 `None`**，
   便把 `None` 当作地块名写进结果字典；输出阶段 `sorted(data.items())` 在
   `str` 与 `NoneType` 之间比较 ⇒ 崩溃。
   （同函数内「楼名证据」路径当年已有 `if bd is None: continue`，**唯独漏了另两条** ——
   同一语义的三处守卫不一致，是本缺陷的形态特征。）

2. **修法（两层）**
   - **归属阶段（根因）**：层户 / 单元 / 楼名三条路径统一加 `None` 守卫；带外标注按
     「不属于任何指定地块」语义**跳过**，并**逐类计数**。
   - **输出阶段（双保险）**：结果字典构造时显式剔除 `None` 键，
     使 `sorted()` 永不遇到 `str` / `NoneType` 混排。
   - 质量报告新增 **`落带外被跳过的标注数`** 字段并打印告警 —— 带外标注**显式登记，不静默丢弃**；
     数量异常时提示核对 `--band` 边界是否覆盖全部目标地块。

3. **零回归证据**：未给 `--band` 时 `which()` 恒返回 `'默认'`，三条守卫均不生效 ⇒
   输出与修复前**逐项一致**（实测同图不带 `--band`：楼栋数、各楼「层数/每层户数」、
   冲突项、未匹配标注数**全部相同**）。带 `--band` 时由崩溃转为正常出结果。

> **通用规则**：凡「按参数把标注分组归段」的脚本，归段函数**必须有明确的『不属于任何段』
> 返回值的处理分支**。该返回值一旦被当作分组键写入字典，会在后续 `sorted()` / 序列化 /
> 下游 join 时才暴露，且报错信息（比较两个类型）与真实根因（归段缺守卫）相距甚远。

### 2026-09-15（二十六）：**总图对照表两处既有缺陷 —— 同编号多实例静默合并 + 安装楼层忽略描述内直写**

由（二十五）的跨项目复核暴露，承载于 `extract_fx_map.py`，与（二十四）的引擎改动无关。

1. **同一编号多实例不得静默覆盖**
   旧实现 `fx_map[编号] = entry`：图上同一编号出现多处时后写覆盖前写 ⇒ **箱位凭空消失、无任何提示**。
   实测某图：箱号标注 72 条、唯一编号仅 64（8 个编号各出现 2 次，且两次指向**不同楼栋**），旧实现输出 64 条。
   现改为按**标注实例**逐条收录，键加 `#序号` 区分并全部保留；输出同时登记
   `标注实例数 / 唯一编号数 / 重号编号`。**重号归属须人工裁决 —— 图纸编号重复本身不可自动择一**。
   下游 `analyze_coverage.py` 载入对照表时同样按编号建键（会二次合并），
   现增加「表内条数 > 载入条数 ⇒ WARNING + 点名重号编号」以防静默。

2. **安装楼层：箱表描述内直写的「K 层」优先于按 y 关联的 F 标注**
   本类图纸把安装层直接写在箱表文字里（`N号楼M单元K层`），而系统图区的 F 标注在 y 上也可能「很近」，
   旧实现一律取 F 标注 ⇒ 安装楼层整体错位。实测某图 84 箱**安装层全部错**（描述写 2 层、输出 14F）；
   改为描述内直写优先后全部回到真值。新增口径 `口径A′`，与原有 A/B 口径并列。
   描述内也拿不到层数时，仍回退原有 y 关联逻辑（不改变他类图纸行为）。

### 2026-09-15（二十五）：**跨项目通用性复核 —— 分带的两条隐含前提及其适用边界**

**触发**：改动（二十四）后被质疑「换项目会不会不适用」。以四张形态不同的图对 V 型法引擎做
**改动前 vs 改动后**双版本实跑对账，并逐图核对入口门禁信号。

**一、改动本身跨项目无回归**（带边界方向不对称 + 箱位锚 x 邻域门禁）

| 图纸形态 | 改前 | 改后 |
|---|---|---|
| 多地块 y 混排型 | 正常 | **逐字段一致** |
| 多地块 y 混排型（另一图） | 正常 | 覆盖楼层 **0 变化**；米数列行数逐单元相同；自检偏差**无一条变差**（max 11.99→9.15×层高） |
| 一行内多图幅并排型 | **rc=2 完全失败**（全部楼栋无可用米数列） | **rc=0**（多数楼栋仍缺米数列，但已可产出） |

箱位锚门禁的分离带在两张**非同源**图上一致：真锚 4.9~5.8×字高、假锚 ≥19.6×字高
⇒ 阈值 k=10 余量充足，**判据可跨图复用**（与具体图纸尺度无关）。

**二、入口门禁是跨项目的隔离层**

`fiber_length_vshape = absent` 的图纸**根本不会进入本脚本**。实测某「平面图 + 设备块 + 连线」型大图：
全图含「米」字文字仅 3 条且均为说明性长句（不成列）⇒ 该信号 absent，转向
`vertical_bus_traceable = present` 的竖线法（竖干配对 21/23、覆盖率 100%）。
故本脚本的影响面 = `fiber_length_vshape = present` 的图纸，不波及他类形态。

**三、分带的两条隐含前提（新暴露，修法待裁决）**

现有分带按**标题 y 聚类**切带，隐含两个前提：① 各图幅**按 y 上下分层**；② 内容一律画在标题**上方**。

实测某图**两条都不成立**：全部米数标注集中在**同一个 y 窄带**（跨度约 18 个层高），
而各图幅实际是**同一行内 x 方向并排**；其楼栋标题 y 存在多个微簇，
**簇间距远小于本带内容的纵向跨度** ⇒ 被误判成多个「带」，米数行跨带被切碎。

> **通用规则（2026-09-15 订正）**：判据必须取**本图内容的 y 连通块数**，
> **不能**用「标题 y 簇间距 vs 内容纵向跨度」——后者拿**全局**内容跨度当参照，
> 在「多个图幅上下分层」的图上会把各图幅**错并成一个**：实测某图全局内容跨度 ≈ 2.8×10⁶，
> 而相邻带间距仅 6~9×10⁵，按该规则全部会被判为「应合并」（真值应为 4 个图幅）。
> 正确口径：本图米数行按「相邻行 y 间距 > 3×层高 即断开」汇成连通块；
> **内容块数 == 1 而标题带数 > 1** ⇒ 这些 y 簇不是「带」，而是**同一行内并排的图幅**，须合并为单带。
> 实测：多图幅上下分层型 内容块数 == 标题带数（一一对应，4 ↔ 4）；
> 一行内并排型 内容块数 = 1 而标题带数 = 6（误分）。
> 修法已实施并跨项目验证 —— 见（二十八）。

**四、连带修复两处与本次改动无关的既有缺陷** —— 见（二十六）。

### 2026-09-15（二十四）：**多地块分带两处 P0 — 带边界方向不对称 + 箱位锚 x 邻域门禁**

`analyze_coverage_vshape.py` 在一张「多地块按 y 混排」的图上暴露两处真实缺陷，均已修复并回归验证。

1. **带的上界不得取相邻带标题 y 的中点（下界才可以）**
   系统图数据一律画在楼栋标题**上方**，故本带内容向上延伸的高度可能**超过**
   「本带与上邻带标题间距的一半」→ 中点边界横穿本带内容，把顶部数层米数行与箱位标注
   **整段切掉**；而第一刀 `win_x` 又按该边界过滤，内容永远无法自证顶端（死锁）。
   修正后某楼由「米数表少 4 行 / V 谷底少 1 个 / 箱数少 1 个、覆盖断裂」恢复为
   「3 谷底、覆盖完整」，且三个箱锚与谷底偏差 1661~2946（≪ 一个层高）。
   上界改取**上邻带标题 y**；下界**必须维持中点** —— 实测把下界也放宽会吞进下邻带整块内容
   （单元数翻倍、V 段碎裂），属明确回归。窗口上界还须并入米数行块顶之上的**同类标注**。

2. **箱位锚 x 邻域门禁（尺度锚 k×字高中位，默认 k=10）**
   箱编号常画在平面图区/箱表区，与系统图区同处一个 x 窗口却无几何关联；
   上条放宽窗口后邻区/邻楼编号被吞入，产生「一个单元配到 8 个箱」的假告警。
   实测真锚 4.9~5.8×字高、假锚 34~59×字高 —— 分离带极宽。
   超阈者不参与箱编号归属，但**必须登记绝对距离**交人裁决（不得静默丢弃）。

同图修复前后对照：`需人工裁决` **114 → 3** 项；`自检_v底vs箱符号` 偏差
max **190621 → 4657.7**（< 0.27×层高）、mean **20034 → 3295**；
V 形单调性 86 项 **0 告警**（即 86/86 箱锚与 V 谷底两个独立来源完全一致）。

### 2026-09-15（二十三）：**「写法变体 → 静默数量丢失」四类铁律（编号 / 标题 / 区间 / 楼名）**

**触发**：柳辛庄项目复核 TeleAgent 报出的问题，实测挖出四处同族缺陷。它们共享一个特征——
**不报错、不崩溃，只是安静地少数据**，因此只能靠铁律而非异常来防。

> 1. **编号 pattern 必须保留完整编号（含前缀），禁止只取尾段。**
>    同一张图上常并存多套同序号编号（如 `FL01FX01` / `FL02FX01` 分属不同地块或楼栋）。
>    pattern 只匹配尾段（`FX\d+`）时，这些箱会塌成同一个编号并相互覆盖归属 ——
>    **数量级静默丢失**。实测：84 个箱被压成 28 个，丢 67%，全程无异常。
>    判别法：**同一尾号若对应多个前缀，就必须用完整形态**。
>    预防：`probe` 已内置串号风险检测（命中即告警，并在 `fx_pattern_note` 给出完整形态）；
>    该字段非空时**必须**采用建议 pattern，不得自行简化。

> 2. **标题 pattern 必须并列枚举楼栋号的两种通用写法（`N#楼` 与 `N号楼`）。**
>    真实图纸可能**整类标题**只用其中一种。只写另一种 → `title_pattern` 推断为空 →
>    整个标题体系无法识别，楼栋边界只能靠猜。区间/并列写法（`N-M号楼`、`N/M号楼`、
>    `N#、M#`）交给楼号解析器统一处理，不要写进标题 pattern。

> 3. **区间标题 `N-M号楼` 的语义（并列 vs 区间）必须交人工裁决，确认后才可展开。**
>    该写法文字本身无法判定语义：取字面会少解中间楼栋（`1-3号楼` → 丢 2#），
>    取区间会多解不存在的楼栋 —— 两种都是数据错误。默认按**字面**取值并打 WARNING；
>    用户确认是区间后加 `--expand-bldg-ranges` 展开为 `N..M`。**禁止**默认开启或静默择一。

> 4. **楼名必须归一为 `N#楼`（保留「配套/商业/附属」修饰词）。**
>    同一栋楼若以 `N号楼`（单楼号标题取原文）与 `N#楼`（共享标题展开时构造）两种形态
>    进入锚点池，会被当作两栋楼各占一个 x → **楼栋边界被切成两半，数据分到错锚点**。
>    统一走 `normalize_bldg_name()`；新增任何楼名来源都必须经过它。

**配套的「采集面」铁律（同源，序号 5）**：

> 5. **标题所在图层必须并入 `--text-layer`。** 标题文字常在专用图层（如 `TEL_SYMB`），
>    该图层不含楼层/芯数/单元等关键词，因此**不会被图层候选推断命中**。
>    漏掉它的症状极具迷惑性：pattern 写对、门禁 PASS，但「标题锚点 0 个 → 楼栋分组不可用」。
>    凡出现「标题锚点 0 个」而 pattern 已给，**先查 `--text-layer` 是否含标题图层**。

**落地**：`ftth_common` 新增 `normalize_bldg_name()` 与区间展开开关
（`EXPAND_BLDG_RANGES` / `set_expand_bldg_ranges()`），并让 `find_bldg_anchors` 真正消费
`parse_bldg_nums_ex` 的 `ambiguous` 返回值（此前该字段**无任何调用方**，规则写了没接线）；
`parse_dxf_structured` 的 probe 推断修正标题/编号两类 pattern 并新增串号风险检测；
`count_households` / `parse_dxf_structured` / `ftth.py` 全线接通 `--expand-bldg-ranges`；
`ftth.py::build_cmd` 统一支持布尔开关透传（此前每个 `store_true` 都要在调用处手工转发）。

### 2026-09-15（二十二）：**通用化复审 — 几何阈值一律按图纸自身层高还原**

**触发**：用户要求复审技能里「只针对一两个项目」的选择条件。复审发现系统性问题：
凡写在代码里的**绝对坐标阈值**（`40 / 80 / 150 / 200 / 30` 之类）都是在某一档坐标
尺度（层高 30）上调出来的，换到层高 15600 的图纸会整体静默失效——不是报错，是判错。

**铁律（通用，跨项目成立）**：

> 1. **凡是随图纸坐标尺度变化的几何阈值，必须写成「无量纲比值 × 本图纸自身层高」**，
>    禁止写死绝对数值。比值跨项目成立，绝对数值只对标定它的那张图成立。
> 2. **不许用绝对容差做聚类**（如 `round(x/40)`、` Δy < 60`）：同一簇内的坐标抖动与
>    簇间距量级天然分离，用「间隙 > k × 低分位间隙」自适应切分，尺子取自数据自身。
> 3. **列状形态的判据用「均匀性」而不是「跨度」**：逐层一列 = 相邻间距都落在
>    `[中位/k, 中位×k]` 内；跨度阈值换尺度就失效，均匀性不会。
> 4. **量不出层高时必须显式标注「未定标」**并给出兜底来源，不得伪装成「已按本图校准」。
> 5. 若某阈值与另一步互相依赖、构成循环（如 `total_pad` ↔ 层高），
>    则**用未经该过滤的原始数据**来量尺度锚，不得图省事直接依赖成品。

**落地**：`ftth_common` 新增 `cluster_values_by_gap`（尺度无关聚类）与
`measure_column_step`（取最密刻度列的 Δy 主簇中位作层高）；`count_box_icons.py` 与
`analyze_coverage.py` 的全部几何阈值改为 `0=按 N 倍层高自适应`；`plan_methods.py`
的米数列判据改为「自适应聚簇 + Δy 均匀」。

### 2026-09-14（二十一）：**P0 铁律 — 三要素多处出现时必须校验一致性**

**触发**：柳辛庄 8 号地 1 号楼 P 列箱号上下颠倒（用户报错）。

**铁律（已写入上方「三要素 · 执行纪律」）**：

> **箱体编号、安装位置、每层户数**这几个元素，若在**图或表中多处出现**，要校验是否统一；
> **若前后矛盾、不统一，请人工复核。**

**教训**：`照抄源数据`也是错误来源的一种——即使链路完全可复现、脚本毫无 bug，
源数据本身可能自相矛盾；不校验就会把矛盾原样搬进成品表。

（本条不再记录该图的具体落图形态与判据——图纸形态因项目而异，不具备通用性；
具体溯源见 `liuxinzhuang-run/柳辛庄8区1号楼_箱号上下颠倒_溯源_20260914.md`。）

### 2026-09-14（二十）：V 型法生产引擎 `analyze_coverage_vshape.py` 多图幅适配 —— 5 处真实缺陷修复（含"分段错一层"）

**背景**：以柳辛庄 8 区（恒盛名邸 8 区）1 号楼做「三要素」走查复核时，用技能自带引擎
`analyze_coverage_vshape.py` 复跑，发现它对**一张 DXF 含多个系统图幅**的情形存在 5 处缺陷
（修订前的脚本版本按「总则 · 维护约定」另存备份，不在技能目录内。）

| # | 缺陷 | 现象 | 修复 |
|---|---|---|---|
| 1 | **多图幅未分带** | 一张图含多个系统图块、x 区间完全重叠（柳辛庄 5/8/9 三区分居不同 y 带），仅按 x 切窗会把不同图幅数据混在一起 | 先按**标题 y 聚类分带**，带内再按 x 切窗；取数同时约束 x 与 y（`w['ylo']<=y<=w['yhi']`）。边界用相邻带中点推——**不能用固定 margin**（系统图数据在标题上方约 +2 万~+34 万） |
| 2 | **多图幅 key 冲突** | 各区都有「1#楼」，JSON 里互相覆盖，8 区结果被 9 区盖掉 | 多图幅时 `bkey = '%d#楼[图幅%d]' % (n, w['band']+1)`；单图幅保持原样 |
| 3 | **楼层列聚类容差过严** | 层号按位数右对齐，`1F` 与 `18F` 同列却差约 1688，原容差 30 把它切成 3 列 | 新增 `--floor-x-tol`（默认 3000），`fcols` 与 `col_f` 取数同步改用它 |
| 4 | **米数行配楼层容差过严** | 米数文字相对楼层线有约 4000 的**恒定偏移**，默认 `--y-tol 20` 使所有行判 None，整栋拿不到覆盖 | 容差**自适应**：先估各行到最近楼层线距离的中位数 `_base`，容差 = `max(args.y_tol, _base*1.5)` |
| 5 | **分段规则错一层** ★ | 原按「两谷底**索引中点**」切分；当两箱层距为**偶数层**时错一层 | 改为取**相邻谷底间米数最大**的行作下箱上界；**并列时取靠近区间中点者** |

**第 5 项是本轮最有价值的发现**。原「中点法」在谷底为偶数层距时出错，用设计表 4 种装配逐一验算：

| 装配（下箱/上箱） | 米数情形 | 正确分界 | 修正前 | 修正后 |
|---|---|---|---|---|
| 5F / 14F（5 区、9 区 1~7 号楼） | 9F 与 10F 并列 | 9 / 10 | 9/10 ✅ | 9/10 ✅ |
| **4F / 14F（8 区 1 号楼）** | 10F 唯一最大 48m | **10 / 11** | 9/10 ❌ | **10/11 ✅** |
| 4F / 10F（9 区 8/10/12/13 号楼） | 8F 唯一最大 | 8 / 9 | 8/9 ✅ | 8/9 ✅ |
| 5F / 12F（5 区 5 号楼） | 9F 唯一最大 | 9 / 10 | 9/10 ✅ | 9/10 ✅ |

→ **原规则只在"两箱层距为偶数"时出错，柳辛庄全项目恰好只有 8 区 1 号楼这一处**，也解释了它为何唯一。

**硬验证（米数恒等式反证法）**：8 区 1 号楼满足 `米数 = |层 − 安装层| × 4 + 24`。
`10F → |10−4|×4+24 = 48`（实测 48，只能归 4F 箱）；`11F → |11−14|×4+24 = 36`（实测 36，只能归 14F 箱）。
两式同时成立且互斥 → **分界只能是 10F/11F**。

**遗留（如实记录，未闭环）**：
- 引擎严格要求「楼层列数 = 米数列数」，遇到**多单元共用同一 y 基准、2 单元无独立楼层刻度列**的图（如 8 区 1 号楼）只处理 1 个单元并报警，2 单元需人工锚定（已实证两单元米数最低点 y 完全重合）。
- 5 区（图幅 1）的单元-箱分派仍错位（引擎 `FL05FX19@4F`，表为 `FL05-FX09#@5F`），疑似该图幅"标题 x 与数据 x"相对位置与其他图幅不同，**待排查**。
- 箱号写在**平面图区**（x≈1.52M），不在系统图窗口内，引擎输出只有"谷底"、不绑定"覆盖→箱"，需人工接箱号。

### 2026-09-14（十九）：**P0 修 — 画像米数信号检测器漏写写法，导致 V 型计算被整条误剔除**

**现象**：柳辛庄 1-4 地块图纸有 25 列 × 18 条米数标注（写法 `1Px2芯x24m`），
覆盖判定却走了竖线法，V 型计算全程未启动。

**根因（三处实现不同步）**：

| 环节 | 支持写法 | 状态 |
|---|---|---|
| `analyze_coverage_vshape.py`（生产引擎） | `20m*2` / `2Px2芯x36m` / `2芯x36m` | ✅ 2026-09-13 P0-2 已兼容 |
| `plan_methods.py` 的 `RE_FIBER_LEN`（画像门禁） | **仅 `Xm*N`** | ❌ 漏改 |
| `SKILL.md` 方法表述 | 写作 `Xm*N` | ❌ 表述过时 |

后果链：画像把 `fiber_length_vshape` 判 `absent`（"全量文字中无『Xm*N』"）→
V 型计算 requires 不成立被剔除 → `gate.skipped_steps=[覆盖判定]` → 我接手既有产物时
沿用竖线法。**引擎能跑，门禁不让进。**

**修复**：

- `plan_methods.py`：`RE_FIBER_LEN` 改为「含数字+米数单位」判据（字段序无关），
  新增 `RE_FIBER_LEN_FORMS` 回报命中形态；`judge_fiber_length_vshape` 在判 `absent` 时
  **强制输出反证材料**（全图含 m/米/芯 的短文字样例）
- 回归测试：4 种写法（`20m*2`/`2Px2芯x36m`/`2芯x36m`/`36m`）全部命中并正确归类；
  4 个干扰项（`1芯皮线光纤`/`GYTS-96B1`/`36mm`/`-0.500`）全部正确排除
- 新增三条流程铁律（见「覆盖判定」节）：**镜像铁律**（检测器与生产脚本写法表必须同步）、
  **档案差异项不得静默**、**接手既有产物必须重跑信号核对**

**教训**：① 正则识别类信号判 `absent` 不等于「图上没有」，只等于「正则没认出」；
② 画像自身的 `archive_comparison` 差异项（本次 80% 一致率、差异项正是 `fiber_length_vshape`）
是明确预警，不得忽略；③ 方法的可用性判据要指向「图纸实际有什么」，不是「我的检测器认不认得」。

### 2026-09-14（十八）：家居配线箱图标法**正名 + 关键词去写死**；新增"图标非户级"的前置条件与门禁诊断

用户指出：**方法名不该绑死在 `HDD` 上** —— 柳辛庄图上该图标的图内文字就是 `HD`
（块属性 `A=家居配线箱`、`$TEXT$=HD`）。据此：

- **正名**：`count_hdd_icons.py` → **`count_box_icons.py`**；子命令 `count-hdd` → **`count-box`**
  （旧名保留为别名 + 旧脚本保留为兼容 shim，不破坏既有调用）。方法对外一律称**「家居配线箱图标法」**。
- **关键词去写死**：弱关键词补 `HD` / `H.D`（原仅 `HDD` / `H.D.D`）。
  **纯 ASCII 缩写改用词边界匹配**（`(?<![A-Za-z0-9])(?:HDD|HD|…)(?![A-Za-z0-9])`）——
  `HD` 绝不能当子串匹配，否则命中 `HDMI` / `CHD` / `SHD`。单元测试 13 例全通过。
- **新增前置条件（本法最大盲区）**：图标必须是**「每户一个」**。柳辛庄 1-4/5-9 两图实测：
  图标是「**每单元每层一个**」的示意画法（每层配一个 `xN` 乘数标注说明代表几户），
  且**全图没有入户皮线图元** —— 图标周围 4800 内最近实体是 `WIRE-照明`。
  → 该方法在这类图上**根本不成立**，读数（449 / 356）不是户数。判据（图纸自身可判）：
  ① 同一 x 列内相邻图标 Δy 是否恒等于一个层高；② 图标总数 ≈ Σ(层×单元) 还是 Σ(层×单元×每层户数)。
- **报告增强**：每列打印「列内 Δy 众数 + 占比」，直接支撑上面的判据①。
- **门禁诊断**：两个门禁（容差定不出来 / 无贴末端候选）都改为打印
  `diagnose_no_bond()` —— 区分「皮线图层没找对」与「本图图标不是户级」，
  避免把后者误判成参数问题而反复空跑。

**柳辛庄实测留档**（供判据校准）：
| 图 | 图标 | 乘数标注 | 图标列内 Δy 众数 | 图上皮线 | 图签读数 |
|---|---|---|---|---|---|
| 1-4 | 449 | 448（`x3`×250、`x2`×198） | 15600 / 17550（＝层高，零例外） | 无 | Σ(层×单元)=661 |
| 5-9 | 356 | 356（`x3`×190、`x2`×166） | 15600（＝层高，零例外） | 无 | Σ(层×单元)=624 |

### 2026-09-14（十七）：图签路径三项收尾 —— patch/area-map 键名、出表口径、真值表自身结构

- **键名坑**：`--patch` / `--intake-area-map` 的键是**分段原始名**（`9块`），不是 `--site-name` 改名后的地名。
  脚本顺序为 `read_titleblock → patch → site-name → intake 比对`；采集表小区被拆成多段时用 `小区名:楼号下限-上限` 区分。
- **出表口径**：采集表小区名与图纸分段名不一致时，**按采集表小区合并后出表**；图纸分段名/FX 编号只用于分段归并。
- **反查真值表先看结构**：已定稿表可能是「节点行段（`N号楼`）+ 户行段（`N#楼`）」两段拼成，两段五级列可能自相矛盾
  → 不得按笔误处理，须列双方数值+坐标+楼层分布交人裁定。
- 以上三条均由柳辛庄项目独立复跑得出（5-9 出表 677/730/963 行、486/516/676 户，与本文档 §五 实测记录逐值相同）。

### 2026-09-13（十六）：gen_addressbook.py 修复——空户数楼层生成幽灵行导致守恒校验失败

**背景**（凤鸣朝阳项目从零重跑暴露）：`gen_addressbook.py` 的 `gen_unit_rows()` 对 `户数=null` 的楼层（如 -2F/-1F 地下层）仍生成一行（`seq=None`、户号留空），导致 `output_rows` 比 `src_households` 多出 24 行（313 vs 337），守恒校验报错中止。SKILL.md Step 1c 已明确规定"若无户数标注，默认不生成户号"，但代码与文档矛盾。

**改动**

- **`scripts/gen_addressbook.py`**：`gen_unit_rows()` 单箱路径与多箱路径的 `if not n_hu:` 分支，由 `rows.append((fl, None, ...))` 改为 `continue`——空户数楼层不生成行，与 SKILL.md Step 1c 对齐。
- **影响范围**：所有含地下室楼层（-2F/-1F 且户数=null）的 FTTH 项目。修复前需手动清理 parse JSON 中的空楼层条目才能出表；修复后直接传入原始 parse JSON 即可。

**验证**（凤鸣朝阳项目）：修复后直接用原始 `parse.json`（含 -2F/-1F 空楼层条目）出表，`gen_addressbook.py` 生成 313 户，守恒校验 313=313 通过，回读校验 315 行（表头1+示例1+数据313）×24 列正确。

### 2026-09-14（十六）：新增「家居配线箱图标法」户数口径 —— 判据为图标贴皮线末端（不依赖块名 / HDD 字样）

**背景**（用户提议 + 实测确立）：户数此前只靠皮线标注文字计数，而文字标注有三个弱点：
① 会重复绘制（实测云峰 335 → 331，且"总数==总数"式守恒校验抓不到）；
② 按块名/属性值识别图标时与楼层平面图撞名（平面图一个户型只画一个图标＝示意画法）；
③ 换个人画图，块名/图层名就变。

用户指出家居配线箱图标的共同特征：**一定紧邻皮线末端**（并且不一定写 HDD，可能只是个方块）。

**实测（云峰，331 户）**

- 「图标 → 最近皮线端点」距离 **331/331 命中**，恒定 **4.04**（310 个 4.04 / 16 个 4.03 / 4 个 4.13 / 1 个 4.37）；
- 反向：1466 个皮线端点中 335 个外侧有家居配线箱图标；
- 平面图区 **126 个同名图标无一贴末端** → 全部落 C 级，不计入户数。

**改动**

- 新增脚本 `scripts/count_hdd_icons.py`（户数统计·家居配线箱图标法）与 `ftth.py count-hdd` 子命令（**8 → 9 个子命令**）。
- **判据是几何、不是名字**：候选图标（INSERT／可选小闭合方块）落在「皮线图元端点」自适应容差内即认定。
  容差 = 距离直方图**最低显著峰 × 1.5**（钳制 [2,30]），随图量测，不写死任何偏移。
- **不恢复** `--insert-attrib-tag/val`：那条属"按属性值匹配"，会重新引入平面图噪声；
  新判据靠几何天然分离两图区，故 `count` 子命令的该参数**继续保持摘除状态**。
- 新增**图区过滤**（以楼层刻度列 y 范围 ± pad 界定）与**物理列切分**（先按 x 容差聚类，再按 y 断口切 run）
  —— 共享图纸上下两行同 x 带必须靠 y 断口分开，否则列会串、归层会漏。
- SKILL.md 同步：方法池「区间法」的户数实体由"皮线标注/INSERT"改为"皮线标注 / 家居配线箱图标"；
  新增「每层户数的三种实体」对照块；脚本表加行；文件数 **15 → 16**（功能脚本 **13 → 14**）。
- 自检新增 **「户数双口径并跑互证」**（必须跑 `count-hdd` 与 `count` 两条，逐列逐层比对，不一致交用户）。
- 修订「户数以系统图为准」表述：把"INSERT 计数不作依据"精确化为"**平面图**的 INSERT 不作依据；
  **系统图**贴皮线末端的图标可用"；`*N` 乘数标注仍须交用户裁决。

**验收（云峰，150MB DXF）**

| 口径 | 结果 |
|---|---|
| `count-hdd`（关键词命中，A 级） | 331 户，13 个物理列，未归属 0 |
| `count-hdd`（**禁用关键词**，纯几何 B 级） | 331 户，**与 A 级坐标集合完全一致**，13/13 列逐层零差异 |
| `count`（皮线文字按坐标去重后） | 331 户，13/13 列与图标口径逐层零差异 |
| 平面图同名图标 | 126 个，全部落 C 级不计入 ✓ |
| `*N` 乘数标注 | 2 处 `*16`，正确告警、未自行相乘 ✓ |

`ftth.py count-hdd` rc=0。两条独立链路各自出表后逐格比对 9264 单元格 **0 差异**。

### 2026-09-13（十五）：去掉楼层平面图数据源 —— 全程只看总图（若有）与系统图

**背景**（用户裁定）："从头到尾不再读取楼层平面图的数据，是为了节约时间，楼层户数就以系统图为准。"
此前住宅楼户数走「系统图 vs 平面图 HDD」交叉验证，实测（云峰）两者口径差一倍时仍需人工回图裁决，
裁决结果一律以系统图为准 —— 平面图校验不产生价值，整条链路删除。

**改动**

- **交接契约 handoff 三要素 → 两要素**：删除「② 楼层平面图」，原「③ 系统图选法」顺位为 ②（必备项不变）。
  判定语义（申报制 / absent 不阻塞 / unknown 才 rc=2）不变。
- **信号 14 → 12**：删除 `multi_floor_plan`、`hdd_symbol`（含 `plan_methods.py` 的
  `judge_multi_floor_plan` / `inspect_hdd_symbol` / `judge_hdd_symbol` / `collect_inserts` 与
  `methods/signals.json` 定义、3 份 manifest 中的对应条目）。
- **删除 `verify_hdd.py`**（平面图 HDD 交叉验证脚本）；脚本总数 16 → 15（功能脚本 14 → 13）。
- **`count_households.py` 摘除「HDD 图块法」**：`--insert-attrib-tag/val` 参数与双源对照逻辑删除，
  只留皮线计数法（系统图）。
- **`ftth.py` count 子命令同步删除 `--insert-attrib-tag/val`**（改造后验收扫描补漏）：该参数原为
  HDD 图块法入口，下游已摘除，残留即成**死参数** —— `build_cmd` 只转发非 None 值，故默认不报错，
  但显式传入或 config 注入时会把下游不认识的参数传过去 → argparse 报「未识别参数」。
  `parse` / `coverage` 子命令的同名参数**保留**（这两个脚本仍按属性值识别设备）。
- **`.gitignore` 移除 `*_hdd验证.json`** 忽略规则（已无脚本产出该文件）。
- **自检口径**：「三类图纸交叉验证」→「两类」（总图（若有）/ 系统图）；
  「楼层数三方交叉校验」→「两方」（系统图楼层线数 vs INSERT 列覆盖楼层数，有总图时另与总图比对）；
  新增明规则：**户数以系统图为准，系统图 INSERT 为示意画法、不作户数依据**。
- B1 层户数口径、方法池路由表、图纸类型参考表同步去除 HDD 图块法 / 平面图字样。

**注意**：契约字段名 `缺失项及降级路径` 不动（ftth.py 按名读取）；
旧版 profile.json（含 `②楼层平面图` 键）仍可过门禁（门禁只读 `completeness`），但重跑 plan 后即按两要素产出。

### 2026-09-13（十四）：四项收尾 —— LWIRE 黑名单 + 伪编号散布判据 + bldg-pattern 断言 + 共享图区标注（含补丁 18 纠偏）

**背景**（用户复核确认 FX22/FX23 归属修复生效后，下达四项收尾建议）

| # | 事项 | 处置 | 验证结果 |
|---|---|---|---|
| 1 | bldg-pattern 漏匹配防护 | `extract_fx_map.py` 运行时断言：区域内有「配套/商业/附属」文字但 bldg-pattern 零命中 ⇒ WARNING 提示 pattern 漏匹配（防 FX22/FX23 误归邻楼根因复发） | 云峰 pattern 已含「配套」→ 不误报；FX22→4#配套楼-1F、FX23→11#配套楼1F 归属正确 |
| 2 | LWIRE 漏网 | `RE_MEP_LAYER` 补 `lwire`（机电走线层名前缀，旧版排除清单有、重写时丢失） | 三图回归不回归 |
| 3 | 柳辛庄伪编号 | `judge_fx_overview_map` 新增判据：**编号 x 跨度占图纸主体 >50% ⇒ 散布全图、不构成集中总图 ⇒ absent**（阈值实测完美分隔：柳辛庄 54%/62%、凤鸣朝阳 75% vs 云峰 4%） | 柳辛庄 1-4（252 条/54%）、5-9（216 条/62%）variant→**absent**；云峰 present 不回归 |
| 4 | 7#8#10# 共享图区箱位不全 | `analyze_coverage.py`：共用同一图形符号的箱，逐箱明细与覆盖线索同步标注「共享图区箱标注不全，该区域箱归属依赖配纤表直读，图面箱位不作准」（此前只在裁决清单集中列） | FX17#/FX18#/FX21# 三箱均带备注（符号 26696.5,-3855.3），覆盖线索同步=True |
| 补丁18 | **词表纠偏**：「光分路箱」误入锚点词表 | 补丁 15 加「光分路箱」过头——实测该词命中的全是 **576 芯落地式光分路箱（ODF/光交设备）**，非 FTTH 楼内分纤箱（云峰 6 处命中：3 处在区域外 x≈28000、3 处在图签设备表区）；从 `RE_FX_ANCHOR_KW` 移除，保留「配线箱」 | 云峰锚点 26→23、覆盖率 91%→**100%**；柳辛庄锚点 58/42 不变（其命中词为「配线箱」） |

**四图回归（补丁 17+18 后，均 rc=0）**

| 图纸 | plan 关键结果 |
|---|---|
| 云峰 | 锚点 23→有效 21→**21/21=100%**；fx_overview present；候选层 2；门禁 PASS |
| 凤鸣朝阳 | absent 不回归；锚点 17（fallback+WARNING）；门禁 PASS |
| 柳辛庄 1-4 / 5-9 | fx_overview **absent**（伪编号判据生效）；锚点 58/42；门禁 PASS、EXIT=0 |

**改动文件**
- `scripts/plan_methods.py`：`RE_MEP_LAYER` 补 lwire；`judge_fx_overview_map` 加散布判据；`RE_FX_ANCHOR_KW` 去「光分路箱」。
- `scripts/extract_fx_map.py`：bldg-pattern 漏匹配运行时 WARNING。
- `scripts/analyze_coverage.py`：共用符号箱逐箱/覆盖线索同步标注。
- `methods/signals.json`：`fx_overview_map` 判据补「x 跨度 >50% ⇒ absent」量化阈值；`dedicated_wire_layer` 黑名单补 lwire。

**经验沉淀**
- 锚点词表每加一个词，必须拿**全部历史图纸**回归——同一词汇在不同图纸指代不同设备（「光分路箱」在柳辛庄语境≈分纤箱俗名候选，在云峰语境=ODF 光交设备）；词表只收**当前已实测为真分纤箱**的词。
- 伪编号形态判定：数量共现不够，**空间散布度**（x 跨度/主体跨度）是区分「集中总图」与「散布标注」的硬指标，阈值 50% 经四图验证。

### 2026-09-13（十三）：第二步链路打通 —— 直写优先验证 + 箱符号层落地 + 四项遗留修复（三图回归）

**背景**（用户逐项裁定六项遗留按优先级处理，处理完整体回归）

| # | 事项 | 处置 | 验证结果 |
|---|---|---|---|
| P0-1 | 安装楼层「直写优先」落地 | **代码已具备**（口径A直写优先、冲突入待裁决），此前从未用新代码重跑验证 | 云峰重跑：初版 23 箱全冲突（箱在配纤表坐标）；接箱符号层后 **21 箱一致 + 2 箱冲突显式列出**，直写值全部保住 |
| P0-2 | 机电专业黑名单 | 新增 `RE_MEP_LAYER`（弱电其他/安防/照明/动力/接地/桥架等，`wire_layer_candidates` 命中即排除） | 云峰候选层 `RX-wire.通讯+WIRE-弱电其他(3层)` → `RX-wire.通讯+WIRE-通讯(2层)`；凤鸣朝阳 absent 不回归 |
| P0-3 | 第二步认不到箱图形符号 | 独立探针定位：云峰箱符号在 **`R-设备.通讯`** 层（21 个闭合小矩形 11.6×4.6，同层无杂线）；`analyze_coverage.py --fx-symbol-layer` 接入 | 23/23 箱位置来源从「编号文字（回退）」→ **图形符号**；**覆盖范围首次全量落地**（FX01#=B1~9F/FX02#=10F~17F，与既有真值核对一致） |
| P0-4 | `intake_table` rglob 吃产物目录 | rglob 遍历时排除 `run_*/_diag/backup` 等产物目录 + 本技能输出文件名前缀 | 云峰（根目录无表格）absent ✓；柳辛庄（根目录 4 张真实地址表）variant ✓；凤鸣朝阳（1 张）variant ✓ |
| P1-1 | 配纤表 23 vs 图面 21 差 2 | **只定位不改逻辑**：差的是 **FX18#(8#)/FX21#(10#)** —— 7#/8#/10# 共享系统图，3 栋低区箱共用同一符号 (26696.5,-3855.3)，裁决清单显式标出「同一箱符号被多箱共用」 | 21 符号全部被认领、23 编号全部定位 |
| P1-2 | 覆盖产物「判定依据/依据来源」字段缺失 | `coverage_clue` 补两字段（判定依据=竖线法断口区间法直读描述；依据来源=图层+连续体坐标+楼层刻度） | 0 次 → **23/23 箱齐备** |
| 补丁15 | 锚点词表缺「配线箱」 | `RE_FX_ANCHOR_KW` 补「配线箱|光分路箱」（柳辛庄系统图箱标注写作『配线箱』；与『配电箱』字符不重叠） | 柳辛庄锚点 0 → **58 个**（TEL_TEXT 层） |

**三图回归（同一命令族，均 rc=0）**

| 图纸 | plan 关键结果 |
|---|---|
| 云峰（共享混合型） | 锚点 23→有效 21→**配对 21/21=100%**；候选层 2 个（黑名单生效）；intake absent；门禁 PASS |
| 凤鸣朝阳（楼-簇组织型） | `vertical_bus_traceable=absent` **不回归**（无通讯层）；intake variant（真实表格）；门禁 PASS |
| 柳辛庄 1-4/5-9（测绘坐标系新形态） | 锚点 58 个（配线箱词表生效）；floor_scale present（36 层刻度）；hdd 449 个；竖线法 absent → 覆盖选 V 型法（同级选法，非降级）；**intake variant（4 张真实表格）**；门禁 PASS、申报 ✔ |

**改动文件**
- `scripts/plan_methods.py`：`RE_MEP_LAYER` + `wire_layer_candidates` 并入黑名单；`judge_intake_table` 排除产物目录；`RE_FX_ANCHOR_KW` 补词。
- `scripts/analyze_coverage.py`：`coverage_clue` 补「判定依据/依据来源」。
- `methods/signals.json`：`dedicated_wire_layer` / `intake_table` / `vertical_bus_traceable` 判据描述同步。
- 产物（云峰 `run_20260913/`）：`fx_map.json`（23 编号全口径A）、`cov_full.json`（23 箱全定位+全量覆盖+冲突 2 项+裁决 8 项）。

**新暴露（未修，转下轮）**
- 柳辛庄 `fx_overview_map=variant`：`FX\d+#?` 在 TEL_TEXT/GCD_HC 命中 252 条散布全图的伪编号（该图无真实 FX 编号，编号 0 条），判据需加「散布全图 ⇒ absent」的形态判定。

### 2026-09-13（十二）：竖线法粒度修正 —— 锚点 (x,y) 二维聚类 +「一节多箱」配对（12 箱 → 21 箱，覆盖率 100%）

**背景**（用户复核提问「是不是 13 个箱体只识别了 12 个」，独立清点探针复核后定位）

（十一）修完后报「12/13 = 92%」，但独立清点（不依赖技能代码的探针）推翻了这个口径：

| 口径 | 数量 | 说明 |
|---|---|---|
| 配纤表登记编号 | 23 | FX01#~FX23# 连续无缺 |
| 图面『分纤箱』文字（简称过滤后） | 23 处 → **二维聚类 23 锚点** | 其中 2 个属图纸另一地块（x≈27995，距最近竖干 >900） |
| **真实箱数** | **21** | 9 个井位各 2 箱（低区 5F + 高区 13F）+ 3 个井位各 1 箱 |

三路独立证据互证：① 文字处数 9×2+3×1=21；② 竖干节数 9×2+3×1=21（低/高区箱各对应一节）；
③ 同井两箱文字 y 差 240 单位 ÷ 层高 30 = **8 层**，恰为 13F−5F；配纤表安装楼层也成对出现
（FX01#=5F/FX02#=13F …）。

**根因与修法**

| # | 缺陷 | 修法 |
|---|---|---|
| A | `pick_fx_anchors()` 按 **x 一维**去重 —— 同井上下两箱被合并成一个锚点（21 → 12） | 锚点改 **(x,y) 二维聚类**（x 容差 15 / y 容差 30），同 x 不同 y 算两箱 |
| B | 补丁初版按「箱 ↔ 节一对一」配对，只配上 13/23 —— 模型错误：**同井低/高区箱共用同一根竖干** | 配对模型改「**一节可服务多箱**」：锚点落在某节 x 邻域内即配对，多箱共享一节；**同节锚点两两 y 间距须 ≥ 2×y_tol（=60，约两个层高）**，同一楼层带的两个箱不算两箱 |
| C | 图纸另一地块的『光缆分纤箱』文字混入锚点池 | 新增**区位剔除**：距全部竖干 >900 单位的锚点剔除且不计入分母 |

**回归（两张真实图纸，同一命令，按组织形态代称）**

| 图纸 | 改动前 | 改动后 |
|---|---|---|
| 共享混合型（有总图 + HDD，150MB） | `present`（12/13 = 92%，**箱数口径错误**） | **`present`**：锚点 23 → 剔除 2 → **有效 21，配对 21 节（覆盖率 100%）**；门禁 PASS，③ 3/3 项 |
| 楼-簇组织型（纯系统图） | `absent`（前置不成立） | `absent` **未回归**（17 锚点 fallback + WARNING 正常）；门禁 PASS |

两图 `ftth.py plan` 均 **rc=0**。云峰判据行：

```
[ANCHOR] 分纤箱锚点 23 个 ← 图面箱文字标注（23 处 → 二维聚类 23 个箱锚点，x 容差 15 / y 容差 30）
[SIGNAL] vertical_bus_traceable = present :: …主层 [RX-wire.通讯]：箱锚点 23 个（有效 21），配对 21 节（覆盖率 100%）…剔除区域外锚点 2 个
```

**改动文件**
- `scripts/plan_methods.py`：`pick_fx_anchors()` 二维聚类 + 区位剔除；`judge_vertical_bus_traceable()` 配对模型改「一节多箱」；`_split_cluster_units()` 按节切分配对单元。
- `methods/signals.json` / `SKILL.md` 正文口径段：同步本节模型（③ 改述 + 新增 ⑤）。

### 2026-09-13（十一）：竖线法两处根因修正 —— 连线层过滤 + 锚点口径（覆盖率 4% → 92%）

**背景**（用户提问「是不是不知道哪一根线是光缆的竖线」，实跑复核后定位）

竖线法在某 150MB 真实图纸上长期判 `variant`（覆盖率 4%），此前归因为「分不清哪根线是光缆」。
实跑复核发现**不是认线问题，是两处取数错位**：

| # | 错位 | 实测证据 | 修法 |
|---|---|---|---|
| A | `segs` 由 `collect_line_and_segments()` **全图**采集，每条竖线其实自带图层名（元组第 4 位），但下游判据只读了 x/y，**layer 被丢弃** | 全图竖线段 24285 条 / x 聚簇 127 个，建筑轴网与墙体占了绝大多数 | 判据新增 `wire_layers` 参数，按连线层候选过滤 → 24285 → 606 条 / 41 簇 |
| B | 锚点取的是**配纤表里的编号坐标**，不是图面箱位置 | 配纤表编号 x∈[24699,24946]，图面箱 x∈[25190,26998]，相差 **500+** 单位，而 `x_tol=15` | 新增 `pick_fx_anchors()`：优先取图面直写『分纤箱/分线箱』字样的位置；无字样时退回编号并**显式告警** |
| C | 文字锚点与图形中心存在**固有偏移**，默认容差卡在门外 | 实测 12 个箱偏移恒为 **+17.0±0.2** —— 差 2 个单位，12 个箱只配上 **1** 个（6%） | 新增 `_pair_anchors_to_clusters()`：带符号中位数估偏移 → 校正后一对一贪心配对 |

**B 的连带修正 —— 锚点文字须是「简称」而非说明性长句**
实测 26 处含『分纤箱』字样的文字里有 4 处是『说明：…由电井分布分纤箱布放一条1芯皮线光纤…』
这类长句，会把锚点数从 12 抬到 16、稀释覆盖率。新增 `_is_fx_anchor_text()`
（长度 ≤ 12 且无句中标点/说明性词头），过滤后 23 处 → 13 个位置。

**逐层试配（新增）**
多候选连线层叠加会把别层（如系统图里的示意连线）的杂簇混进来，聚簇数虚高、配对被稀释。
改为**逐候选层各配一次**，取「配对最多 → 簇最少 → 线段最多」者为主层。实测：

| 候选层 | 配对 | 簇数 | 结论 |
|---|---|---|---|
| `RX-wire.通讯` | **12/13** | **12** | **选为主层** |
| `WIRE-通讯` | 3/13 | 29 | 落选（杂簇 29 个） |
| `WIRE-弱电其他` | 0/13 | 2 | 落选 |

**断口不再是硬门槛**
实测竖干可能**连续无断口**（线型间隙与楼层分界无法用同一阈值区分），旧判据「含断口簇」
会把 12 条连续竖干全部否掉。改为只要求「箱能配到竖线簇」；线型断口降为参考量，
evidence 中保留每箱竖干的 `(段数/节数, y 端点范围)` 供第二步用区间法定层。

**回归（两张真实图纸，同一命令，按组织形态代称）**

| 图纸 | 改动前 | 改动后 |
|---|---|---|
| 共享混合型（有总图 + HDD，150MB） | `vertical_bus_traceable = variant`（4%）<br>门禁 `不可用子任务 = ['覆盖判定']`；③ 2/3 项 | **`present`**（主层 `RX-wire.通讯`，**12/13 = 92%**）<br>门禁 `不可用子任务 = 无`；③ **3/3 项**，覆盖范围 → **竖线法** |
| 楼-簇组织型（纯系统图） | `absent`（前置不成立） | `absent`（前置不成立）**未回归**；新增锚点降级 WARNING |

两图 `ftth.py plan` 均 **rc=0**。

**改动文件**
- `scripts/plan_methods.py`：新增 `RE_FX_ANCHOR_KW` / `RE_FX_ANCHOR_NOISE` / `_dedup_sorted_x()` /
  `_is_fx_anchor_text()` / `pick_fx_anchors()` / `_cluster_segments()` / `_pair_anchors_to_clusters()`；
  改写 `judge_vertical_bus_traceable()`（加 `wire_layers` 形参、逐层试配、覆盖率改用配对口径）；
  `main()` 改用 `pick_fx_anchors()`，`statistics` 新增 `分纤箱锚点数` / `分纤箱锚点来源`。
- `methods/signals.json`：`vertical_bus_traceable` 的 `description` / `detect_method` 改写为本节口径。
- `SKILL.md` / `references/measurement_methods.md`：同步。

**复现命令**（两图，参数按 Step 1a 探查结果显式传入）

```bash
python scripts/ftth.py plan --dxf <图纸>.dxf --out profile.json --probe probe.json \
  --project-dir <项目目录> --text-layer "<探查所得文字图层>" \
  --title-pattern "<探查所得标题正则>" --fx-pattern "<探查所得编号正则>"
```
判据行看 `[SIGNAL] vertical_bus_traceable`：应出现「各层配对：…｜主层 [层名]：…覆盖率 N%」
与「锚点↔图心固有偏移 ±N」。

### 2026-09-13（十）：③ 系统图选法方法池补全 + 新增 `floor_scale` / `cover_range_annotation`

**背景**（用户裁定）：**系统图是必备的** —— ③ 必须给出三项各自的**测定方法**（结果由第二步按方法跑出）：
「分纤箱安装位置」**区间法 / 读取标注**；「每层户数」**读取标注 / 区间法**；
「分纤箱楼层覆盖」**读取标注**（图上直写箱体覆盖起止层）/ **V型法** / **竖线法**（需区间法配合的三步法）。

**修掉的三处「文档有、代码没落」**

| # | 问题 | 修法 |
|---|---|---|
| A | `分纤箱提取` 候选只有「总图对照表」+「编号-符号配对」，**无区间法**；而同一份 `handoff` 却输出「安装楼层口径B（区间法）」—— **契约断言了方法池里不存在的方法** | 候选改为「读取标注（总图对照表）」+「**区间法**（编号文字/箱符号落楼层带）」；`安装楼层口径` 字段改为 **`安装楼层方法`**，**随选定方法导出** |
| B | `覆盖判定` 候选缺「读取标注」（图上直写覆盖起止层） | 新增 primary 候选「读取标注（图上直写箱体覆盖起止层）」 |
| C | V型法/竖线法 `requires` **未表达「需区间法配合」**（`coverage_rules.md §0.5` 三步走第②步、本节谷底定层均走区间法），且**没有「楼层刻度」信号可挂** | 新增第 13 个信号 **`floor_scale`**，挂到 区间法 / 竖线法 / V型法 三处 |

**新增两个信号（12 → 14）**
- **`floor_scale`（楼层刻度可建带，全局筛选信号）** —— 判据用**「最长楼层刻度列」**（按 x 聚类后某列含 ≥5 个不同 y），
  避免"分散在多楼、每处都不成列"被误判 `present`。
- **`cover_range_annotation`（箱体覆盖起止层直写）** —— 属「读取标注」的覆盖形态，**可作覆盖判据**；
  与 `coverage_table`（光交配纤表）**严格区分**：后者只给归属、不给覆盖楼层区间，仍仅作线索不作判据。
  规则本体补进 [references/coverage_rules.md](references/coverage_rules.md) §0.7 ——
  原 `signals.json` 写「见 coverage_rules.md」而该文件并无此条，**引用悬空一并修掉**。

**③ 必备性收紧**
- 「分纤箱位置（安装楼层）」「每层户数」**缺任一 ⇒ 记入 `不可解析` ⇒ 入口 rc=2**（系统图必备）；
- 「覆盖范围」仍可 `absent` + 降级路径放行（不是每张图都给覆盖数据）。

**途中实测暴露的三处判定缺陷（不修则证据链不成立）**
1. **楼层标注必须全匹配**：实测某图 `0` 图层的 `GYTS-96B1` / `GYTS-24B1` 会被宽松 `search` 当成楼层 `B1`。
2. **刻度列须含普通地上层号**：同一张图的 `0` 图层另有一条 **`B1`~`B24` 等距编号竖列**（同 x、y 间距恒定），
   会被 `[Bb]\d+` 全匹配当成"24 层楼层刻度列"→ **最长列取错**。改为「列内须含 `1F`/`17F` 形态」后，
   最长列正确回落到真实楼层刻度图层（19 层）。
3. **MTEXT 花括号**：`MText.plain_text()` 剥掉 `\W0.8;` 格式码却**保留分组花括号**
   （`{\W0.7999999999999999;-1F}` → `{-1F}`），全匹配前须再剥一层（新增 `_strip_group_braces()`）。

**回归（两张真实图纸，同一命令，按组织形态代称）**

| 图纸 | 分纤箱位置（安装楼层） | 每层户数 | 覆盖范围 | `floor_scale` | `cover_range_annotation` |
|---|---|---|---|---|---|
| 楼-簇组织型（纯系统图） | **区间法** | 读取标注 | V型计算 | **present**（179 条 / 最长列 20 层） | absent |
| 共享混合型（有总图 + HDD） | **读取标注**（总图对照表） | **区间法** | `absent`（本图未提供）+ 降级 | **present**（168 条 / 最长列 19 层） | absent |

**③ 必备性负例验证（直调 `build_handoff`，四种信号组合）**

| 场景 | `ok` | 结论 |
|---|---|---|
| 三项都有方法 | true | 放行 |
| 缺「每层户数」 | **false** | `不可解析` → rc=2 |
| 缺「分纤箱位置」 | **false** | `不可解析` → rc=2 |
| 仅「覆盖范围」缺 | true | 进 `缺失项及降级路径`，**放行** |

16 脚本 `py_compile` OK；`methods/` 4 JSON OK；信号数 **12 → 14**；`SKILL.md` / `measurement_methods.md` /
`coverage_rules.md` 同步更新。

### 2026-09-13（八）：Step1 → Step2 交接契约（三要素，逐项申报）

**背景**（用户裁定）：图纸向第二步传递的信息必须**至少**包含三项，否则解析与校验都失去依据——
① 有没有分纤箱总图（编号 + 安装位置）；② 有没有楼层平面图（楼层布线有无户内多媒体箱图标）；
③ 楼内系统图的分纤箱位置 / 覆盖 / 每层户数各用什么方法统计。此前这三项散落在 11 个信号里，
没有任何一项直接回答"图标有没有"，第二步也没有强制入口把三项收齐。

**改动**

- **`plan_methods.py` 新增 `handoff`（画像新顶层键）**：`build_handoff()` 把三要素写成机器可读契约——
  ① 含 `编号数` + `安装位置.{编号同行的楼栋/单元/安装楼层标注数}` + `依据`；
  ② 含 `平面图` 与 `户内多媒体箱图标` 两个来源状态；③ 三个子任务各含
  `选定方法 / 方法池类别 / 脚本 / requires / 同可用备选 / 申报 / 降级 / 待确认`，"分纤箱位置"另附
  `安装楼层口径`（口径A 直写 / 口径B 区间法）。
- **门禁合并**：`handoff.completeness.ok=false`（任一项 `unknown`）→ `gate.status=fail` +
  `gate.handoff_blocked=true`；`ftth.py check_profile_gate()` 增加该分支 → **rc=2 中止**。
  该条的"无可用候选也算未作答"部分**于同日修正为申报制**，见（九）。
- **新增第 12 个信号 `hdd_symbol`**（`methods/signals.json`）。新增 `collect_inserts()` 枚举
  INSERT 块引用，按**块名 + 全部属性值**匹配户内多媒体箱关键词；**仅文字提及而无块符号 → `variant`**。
- **`fx_overview_map` 判据收紧**：由"数量共现"改为"**对照表形态**"，新增 `inspect_overview_map()`
  量测"编号同行"关系（行距、x 容差均由本图量出）。
- **修 `--probe` 复用文字样例的图层污染**：`plan --probe` 原先直接复用 probe 的**全图层**文字
  （实测某图 1530 条，含暖通/图签栏/机电），稳健 x 跨度被撑到 **142 万**（真实主体约 2.2e3）、
  "同行 x 容差"随之放大到 **21 万**，图签栏标注被误算成"与编号同行"。现按 `--text-layer` 收窄
  （收窄后为空则告警且不过滤，不静默丢数据）。

**实测（双向验证，均可复现）**

| 图纸 | 编号数 | 占主体 x 跨度 | 与 `X户`/`Xm*N` 同行 | 与楼栋/单元同行 | `fx_overview_map` |
|---|---|---|---|---|---|
| 图纸A | 17 | **75%** | **100%** | 0% | **absent**（编号嵌在各楼系统图楼层表内） |
| 图纸B | 23 | **4%** | 0% | **100%**（楼栋 23 / 单元 19） | **present**（对照表形态） |

- 图纸A：`hdd_symbol=absent`（151 个 INSERT / 18 种块名，命中 0）；`handoff` 三项全部作答，
  `completeness.ok=true`，门禁 PASS；放行后 `coverage-vshape` → **rc=0**，17 个箱的覆盖分界
  全部给出（V底 vs 箱符号偏差 2.0~2.1、单调性告警 0、需人工裁决 0 项）。
- 图纸B：`hdd_symbol=present`（6040 个 INSERT / 445 种块名，命中 457 个实例）；`handoff.②` 为 present；
  ③ 覆盖范围两个候选前置全不成立 → 当时按"无可用候选即未作答"判 `completeness.ok=false`。
  **该判定于同日修正**（见（九））：本图未提供覆盖数据属合法缺席，应申报 `absent` →
  `coverage` 入口 **rc=3 不适用**（而非 rc=2 中止）。
- 16 脚本 `py_compile` 全 OK；`methods/` 4 个 JSON 全 `json.load` OK；信号数 12。

### 2026-09-13（九）：契约语义修正 —— 「存在性门禁」→「申报制」

**背景**（用户纠正）："有的图纸没有提供总图和楼层配线图，只有系统图，也得过啊，如果有提供，
没有就说没有，那就以现有的图纸校验或者为准。"

（八）把三要素做成了**存在性检查**：要素不存在 ⇒ `completeness.ok=false` ⇒ 全部入口 rc=2。
这**把"图纸没画"当成了"技能没干活"**，与真实图纸形态冲突（本类图纸天然可能只给系统图）。

**修正（三要素仍是三要素，判定语义反转）**

1. **`absent` 不阻塞**：① ② ③ 任一项本图未提供，只要求**如实申报 + 给出降级路径**，不拖掉门禁。
2. **`completeness` 改结构**：`ok` / `已申报` / `未作答`（唯一阻塞项）/ `不可解析` /
   `缺失项及降级路径`。`ok = 未作答为空 且 不可解析为空`。
3. **`gate` 区分性质**：`evaluate_gate()` 按候选前置信号实况把子任务分成
   `blocked_steps`（含 `unknown`，判不了 → rc=2）与 `skipped_steps`（全部明确 `absent`，
   本图未提供 → **rc=3 不适用**）。`gate.status` 只在 `blocked` 时 fail，
   并新增 `gate.handoff_gaps`（缺项及降级路径）。
4. **新增退出码 3 = 不适用**：`ftth.py check_profile_gate()` 返回 3，打印降级路径后放行,
   **不是错误、不需重试**；`plan` 自身仍 rc=0。
5. **③ 子任务降级路径物化**（`_FALLBACK`）：无米数 / 无专用连线层 → 覆盖改用
   「每层户数 × 层数 = 箱容量 × 箱数」守恒替代，成果表覆盖列标注「本图未提供」。
6. **③ 三项全部无候选** → 记入 `不可解析`（本图没有任何可解析依据，出不了地址表）→ rc=2。

**回归验证（真实图纸复跑，rc 可复现）**

| 场景 | ① | ② | ③ | `completeness.ok` | `gate.status` | 命令入口 |
|---|---|---|---|---|---|---|
| 图纸A（纯系统图：无总图、无平面图） | absent | absent | 3/3 已选定 | **true** | pass | `coverage-vshape` **rc=0** |
| 图纸B（有总图 + HDD，无覆盖数据） | present | present | 2/3（覆盖 absent） | **true** | pass | `coverage` **rc=3 不适用** |
| 负例1（契约注入 `unknown`） | — | — | unknown | **false** | fail | **rc=2 中止** |
| 负例2（命令依赖子任务 `unknown`） | — | — | — | true | fail | **rc=2 中止** |

- 图纸A 缺 ① ② 两项：**只申报 + 打印降级路径，放行**；`coverage-vshape` 照常给出 17 个箱的
  覆盖分界（V底 vs 箱符号偏差 2.0~2.1、单调性告警 0、需人工裁决 0 项）。
- 图纸B 缺 ③ 覆盖数据：契约仍 `ok=true`，`gate.skipped_steps=['覆盖判定']`（性质=不适用；
  信号实况 `fiber_length_vshape=absent` / `dedicated_wire_layer=present` /
  `vertical_bus_traceable=variant`）；`coverage` 入口 rc=3，打印降级路径 + 信号实况后跳过。
  **注**：`vertical_bus_traceable=variant`（竖线覆盖率 4%，仅 1/23 箱）在可用性上等同"本图不提供"，
  故不再算未作答 —— 只有 `unknown` 才算。

### 2026-09-13（七）：选法物化 —— `plan_methods.py` + 图纸画像 `profile.json` + 入口门禁

**背景**：选法（各步骤用哪个方法）此前只存在于文档与人的判断中 —— `probe` 只输出参数字符串、
不输出信号状态，`scripts/` 全库 **0 处**引用 `drawing_profile`。后果是选法不可复现、不可门禁：
实测曾出现「覆盖判定两个候选前置全不成立，仍静默跑出可用性未知的结果」。

**改动**

- **新增 `scripts/plan_methods.py`**（图纸画像生成器，**只判定与选法、不测量业务字段**）：
  ① 依 `methods/signals.json` 的 **14 个信号**逐项判定本图状态（`present`/`absent`/`variant`/`unknown`）并写 evidence；
  ② 按「子任务 → 候选方法」生成 `candidates[]`（`role`/`method`/`requires`/`script`/`params`）；
  ③ 与 `methods/*/manifest.json` 逐份比对**一致率**（§五.3「对比」的物化）；
  ④ 评估门禁（某子任务全部候选 `requires` 均不成立 → `gate.status = fail`）；
  ⑤ 补齐原 `probe` 缺失的 Step 1a 探查项 —— **线段图层分布、竖线段统计、坐标范围、文字图层分布、标题锚点数**。
- **`ftth.py`**：新增 `plan` 子命令（调度 **7 → 8**）；`parse` / `coverage` / `coverage-vshape` 新增 `--profile`，
  经 `check_profile_gate()` 做**入口门禁** —— 依赖子任务无可用候选时打印信号实况并 **rc=2 中止**。
- **`methods/signals.json`**：`status_values` 新增 `unknown`（"探查未能判定，**不得当作成立**"），
  避免把"判不了"伪装成 `absent`。
- **`SKILL.md`**：Step 1a 补**图纸画像产物契约**（选法归属第一步，产物为 `profile.json`）；
  文件计数 15 → 16（功能脚本 13 → 14）；子命令 7 → 8；脚本表新增 `plan_methods.py` 行。
- **`measurement_methods.md`**：§五 标题标明为**外层接入 SOP**；§4.2 注明画像由 `plan_methods.py` 产出、
  `manifest.json` 是**沉淀成果**而非手写样板。

**判定口径（两处收紧，均由实测暴露）**

- `dedicated_wire_layer`：图层名关键词命中后**再剔除标注/设备/文字类图层** —— 标注层、设备符号层里的
  "线段"是标注线与符号边框，不是电信连线。实测某图中 `DIM-通讯`、`R-设备.通讯` 被误纳为连线层。
- `vertical_bus_traceable`：判据由「图里有没有竖线」改为「**分纤箱 × 带断口竖线簇的覆盖率**」 ——
  竖线法的测量对象是**每个箱的竖干**，全图竖线再多而与箱不相连也构不成覆盖判据。
  覆盖率 `0` → `absent`；`0 < 覆盖率 < 50%` → `variant`；`≥ 50%` → `present`。
  实测某图 24 285 条竖线段 / 127 个簇，但 23 个箱中仅 **1 个**附近有带断口簇（覆盖率 **4%**）
  → `variant`，竖线法判为不可用。

**实测验证（某 150MB 真实图纸，可复现）**

- `ftth.py plan` → rc=0，46 s，产出 `profile.json`（14 个顶层键，`kind = drawing_profile`）。
- 信号判定 `present=6 / absent=2 / variant=2 / unknown=1`；画像名如实标为「**未归类形态**」
  （与最近档案一致率 77.8%，差异项 `cluster_layout`、`vertical_bus_traceable`）。
- **门禁命中**：`gate.status = fail`，`unavailable_steps = ['覆盖判定']`
  （`fiber_length_vshape=absent`；`dedicated_wire_layer=present` 但 `vertical_bus_traceable=variant`）。
- `ftth.py coverage --profile profile.json` → **rc=2**，打印信号实况与处置建议后中止，未执行解析。
- 16 脚本 `py_compile` 全 OK；`methods/` 4 个 JSON 全部 `json.load` OK；`ftth.py --help` 子命令 8 个。

### 2026-09-13（六）：彻底剔除渲染链路

> 起因：委托人裁定渲染不应留在流程内——本技能以 DXF 直读为唯一数据源，PNG 渲染只服务人工目视核对，
> 却带来 matplotlib 依赖、有损图像判读风险，以及一整套需长期维护的裁剪/避让参数。
> 本次按「脚本 / 入口 / 档案 / 文档 / 忽略规则」五层整体移除；**历史版本记录保持原貌不改**。

- **删除脚本**：`scripts/dxf_to_png.py`，并清除 `__pycache__` 下 2 个对应 `.pyc`。
  功能脚本 **14 → 13**，`scripts/` 文件数 **16 → 15**。
- **`ftth.py`**：移除 `render` 子命令（子命令定义段 + dispatch 分支 + docstring 枚举），调度 **8 → 7**；
  删除 render 专属的 `--group` 列表展开死代码（`build_cmd`）；
  import 清理 `DEFAULT_EDGE_RATIO` / `DEFAULT_CAND_HALF` / `DEFAULT_FILTER_H`；docstring 举例去掉 DPI。
- **`ftth_common.py`**：删除仅渲染消费的常数 `DEFAULT_EDGE_RATIO`、`TEXT_DECONFLICT_MAX_ITER`、
  `DEFAULT_CAND_HALF`、`DEFAULT_FILTER_H`。
- **`count_households.py`**：3 处「需对照 PNG 复核/确认」改为「对照图纸原图」，不再隐含须先渲染。
- **`SKILL.md`**：删「### 渲染（可选，非标准流程）」整节；依赖表去 matplotlib 行；
  脚本表去 `dxf_to_png.py` 行；「探查/解析/自检/**渲染**/出表」归位四步；
  去 LibreCAD 降级渲染说明；子命令计数 8 → 7；文件计数 16 → 15；references 条目描述同步。
- **`references/measurement_methods.md`**：§1.3 标题「五步」→「四步」并删渲染条目；§2.3 表格删渲染行；
  §2.4 删 `--cand-half` / `--dpi`；§3.6 删「渲染：已解决」条；§4.2 示例删 dpi；
  §4.3 举例「阈值/dpi」→「阈值/容差」；§五.4「五步流程」→「四步流程」；核心思路去「+ 可选渲染」。
- **`references/visual_model_lessons.md`**：删「视觉模型调用时的注意事项」整节（纯渲染流程：转 PNG / 按楼栋裁剪 / 300dpi）；
  §1.3 由「PNG 裁剪」改写为通用「局部视图不完整」；节序号顺延（原「四、DXF时代教训」→「三、」）。
- **`methods/`**：`signals.json` 的 `cluster_layout.applies_to` 去「渲染」；
  `building_cluster` / `shared_mixed` 两份 manifest 删「渲染」步骤块，
  并从 `algorithm_defaults` 移除 `dpi` / `cand_half` / `edge_ratio`。
- **`.gitignore` / `scripts/.gitignore`**：删除 `render_output/` 忽略项。
- **保留不动**：版本记录中提及渲染与 `dxf_to_png` 的历史条目（2026-09-13（四）、2026-09-11/12 等）
  原样保留——历史即事实，改了就不是记录。
- **验证（可复现）**：15 个脚本 `py_compile` 全通过；`methods/` 下 4 个 JSON 全部 `json.load` 通过；
  `ftth.py --help` 子命令为 7 个（`probe/parse/coverage/coverage-vshape/verify-truth/count/gen`）；
  `ftth.py render` → **rc=2** 报 `invalid choice: 'render'`（门禁正确拒绝已删子命令）；
  全库 grep `渲染|render|dxf_to_png|matplotlib|LibreCAD|dpi|cand.half|edge.ratio|视口|避让`
  在正文/档案/脚本/references 命中 **0**，仅 SKILL.md 历史版本记录保留 6 处原貌。

### 2026-09-13（五）：安装楼层「总图交叉校验」落地 + 直写优先口径归一

> 起因：`SKILL.md`「Step 1 · 分纤箱总图检查」早就要求「编号、楼栋/单元、安装楼层三项均须与总图一致，不一致以总图为准」，
> `SKILL.md`「测量方式架构 · 方法对照表」也要求安装楼层「读取标注（直写优先）」——**文档写了，代码没做**：
> `analyze_coverage.py` 把总图直写值只当作「箱符号 ↔ 楼层线」配对的坐标锚，
> 最终落盘**无条件**写 `口径B:区间法`，总图直写值被静默覆盖且不报矛盾。
> 实测（云峰图 150MB）：23 箱中 **21 箱冲突**（例：FX01# 总图直写 5F / 区间法 WF）。

- **新增 `floors_equal()`**：楼层标注等价判定。同写法直接判等（覆盖 `WF` 这类非数字写法）；
  写法不同时按 `parse_floor_label` 解析值比较（兼容 `5F` / `05F` / `5f`）；
  任一方不可解析判为**不等**（进人工裁决），不做静默等同。
- **落盘前逐箱插入总图交叉校验**：
  - 有直写值 → **采用直写值**（直写优先），口径写 `口径A:图上直写（与区间法一致）`
    或 `口径A:图上直写（覆盖区间法，冲突已列待裁决）`；
  - 冲突 → 追加进「需人工裁决」（事项 `安装楼层与总图冲突`），并把冲突明细落入
    新增顶层字段 `安装楼层总图校验`（`对照表可比对箱数` / `冲突数` / `冲突明细`）；
  - 无直写值 → 维持 `口径B:区间法（总图无直写值）`，一致性标注 `无法比对（总图无直写值）`。
- **新增审计字段**：`安装楼层_区间法` / `安装楼层_总图直写` / `安装楼层一致性`——
  逐箱可回溯两个来源，不再只剩一个被覆盖后的值。
- **修传递断点**：构造箱位列表时此前**丢掉了 `对照表安装楼层`**（只留 编号/x/y/位置来源），
  总图值根本没到落盘处——这是该功能此前无法实现的直接原因。
- **日志诚实化**：逐箱行原只打印区间法值（`安装楼层=WF`），与采用值不符；
  现打印 `安装楼层=<采用值>｜总图直写 X｜区间法 Y`。
- **回归（云峰图）**：23 箱 **21 冲突 / 2 一致**（FX18# 5F、FX23# 1F 一致）；
  FX01# 由 WF 回归 **5F**，FX02# 13F、FX11# 5F、FX12# 13F，均与总图直写一致；
  「需人工裁决」94 项（其中 21 项为安装楼层冲突）；rc=0——冲突按设计不失败，但**不再静默**。
- **本轮未覆盖**：`parse_dxf_structured.py:524-531` 的 `口径A/B` 是「箱旁直写距离阈值」判定，
  与总图对照表无关，本次未动；该层此前的静默丢箱问题仍独立存在。

### 2026-09-13（四）：`dxf_to_png.py` 的 matplotlib 改惰性加载

- 此前 `import matplotlib` 在模块顶部、argparse 之前，缺库时**连 `--help` 和参数校验都跑不了**（裸 ImportError）。
- 现推迟到 `require_params` 通过之后、真正渲染前才加载（`_load_plt()`）；缺库输出一行可执行的安装指引（`pip install matplotlib`）后退出码 1。
- 渲染验证按委托人裁定不做（该脚本为备用），本次仅验证：编译通过、`--help` rc=0、无参数走参数校验（rc=2）而非 ImportError。

### 2026-09-13（三）：图签容差量测的方向约束 + 等权综合距离 + 量测自检 + 分段交叉校验

> 起因：上一轮遗留「是否支持多地块分别量测容差」。实测（验证图：一张多地块混排竣工图）发现
> 分块量测不但无必要，还暴露出量测算法的一个**真 bug**：按地块拆分量测时，地块A 量出
> `unit-dy = -35906` 的**负容差**。

- **修 `ftth_common.estimate_titleblock_tolerances()`——「层户 ↔ 单元」量测须「方向约束 + 等权综合距离」**：
  - **方向**：只在单元标注**上方**取候选（与解析窗口 `unit_dy_lo <= 层户y-单元y <= unit_dy_hi` 同向）。
    无方向最近邻在「排间距 < 块内间距」的图上会取到**下一排**的层户——地块A 排间距 35906 < 块内间距
    46319，量出 **-35906 的负容差**；负窗口让该栋单元全部配不上层户，**静默丢户且不自我暴露**。
  - **等权综合距离**：候选中按 **|dx| + dy**（同量纲，无需归一化）取，而非任何单一判据。
    实测 4 个歧义点，两个单一判据各错一半：「x 最近」在地块A 判反（错的候选 dx=26219 < 对的 31900，
    但其 dy 差 3 倍）；「y 最近」在地块B 判反（错的候选 dy=33860 < 对的 43443，但其 dx 差 20 倍）。
    等权相加在同一批点上**全部选对**。
  - **效果**：四段配对率全部 100%（此前 16/20、12/24）；全图 `unit-dy` 窗口 **[41179.7, 50234.9]**
    完整覆盖四段窗口（各段 ⊂ 全图），两条路径（显式 vs 自适应）结果**逐字段相同**、均 24 栋一致。
  - ⚠️ **中间过程如实记录**：只加「x 最近」、尚未等权时，窗口收窄为 [44713.1, 49057.1]，把真实值
    **43443.5 挤出主簇** → 自适应路径从 24 栋掉到 **22 栋**（丢地块A/地块B 4 号楼的单元数）。
    **教训：判据改动必须端到端复跑；只看「配对率 100%」会误判为成功。**
  - **新增 `ToleranceEstimateError` + 窗口自检**：窗口自相矛盾（`lo >= hi`）或**跨越 0** → 按失败退出（码 2），
    不静默输出（跨零窗口会把另一侧标注也框进来，数据看着正常实际已串楼）。
- **探针 `--band` 改为分段交叉校验**（不替换建议值）：逐段独立量测，比对全图窗口是否覆盖本段；
  有段落落在窗口之外即告警，并给出「该段单独出表」的命令。**不做分地块容差**——实测分块样本少、
  统计不稳（配对率曾低至 12/24，`unit_dx` 量到 80 万），而全图一组已覆盖全部地块的真实配对。
- **顺手清一处项目痕迹**：`titleblock_and_intake_table.md` 写「单元标注在楼名下方约 46k 处」，
  46k 即本图实测值，而同节又刚声明「不得写死某项目的实测值」——改为「约一个图签行距量级」。

### 2026-09-13（二）：6 个几何容差改为「缺省按图自适应」+ 新增量测探针

> 起因：文档要求这 6 个几何容差「必须由探查量测」，却**没有配套量测手段** —— 现场只能自己现写探针，
> 「必须实测」这句实际不可执行；而同一技能内 `analyze_coverage.py` 早已用「层高比例容差」实现了自适应，
> 两条路径的容差策略不一致。

- **新增 `scripts/probe_titleblock_tolerances.py`**：`--dxf` + 可选 `--layer`（缺省按「形如 `N层/M户`
  的文字条数」自动推荐图签层），一跑即给出 6 个容差的建议值 + 实测证据（配对样本数、主簇区间、分位数）。
- **新增 `ftth_common.estimate_titleblock_tolerances()`**：量测算法固化到公共模块，探针与图签脚本共用。
  原理与竖线法的层高自适应同源——不预设任何坐标值，从图纸自身量「图签行距」当尺子：
  ① 楼名行↔层户行 y 间距 → `dy`；② 同块内 x 间距 → `dx`；③ 层户行↔单元行 y 间距 → `unit_dy`。
  统计一律取「主簇」，跨图签块的离群误配被滤掉（实测配对率 16/48 → 48/48；`dy`、`dx` 与手工实测逐位一致）。
- **`read_titleblock_households.py` 改为三步范式**（与 `analyze_coverage.py` 一致）：
  **命令行显式值优先 → 缺省时按本图自适应 → 推定值与依据写进结果 JSON 的「几何容差」字段**。
  6 个参数不再「一律必填」，但仍**不设固定默认值**——量的是当前这张图，不是套用某个项目的实测值。
- **参数分类判据改写**：原文把「容差」同时归入「检测类（默认清空为 None）」与「算法常数（保留默认）」两类，
  判据被写混。现统一表述为「**是否随图纸坐标尺度变化**」——变的不给固定默认（能自量的则自量），不变的保留。
  涉及 `SKILL.md`、`references/measurement_methods.md`、`methods/titleblock_based/manifest.json`。
- **回归**：两条路径（显式传参 `8000/3000/20000/120000/30000/60000` vs 全自适应）产出结果**逐字段相同**，
  均为 24 栋一致、需人工裁定 0；16 个脚本编译通过。

### 2026-09-13：P0 修复——楼号解析统一 + 米数格式适配 + 作业门禁

> 起因：TeleAgent 同项目会话（7.1 小时未交付）复盘发现，技能不是"没被用"，而是**用不了**：
> `analyze_coverage.py` 硬编码 `(\d+)#` 对图上 `N号楼` 全部返回空 → 13 栋全跳过，**退出码却仍为 0**。

- **P0-1 统一楼号解析**：`ftth_common.parse_bldg_nums()` 成为唯一入口，覆盖
  `N#` / `N号` / `N#、N#` / `N#N#` / `N/M号楼` / `N、M号楼` 六种写法；
  `parse_bldg_nums_ex()` 额外回报 `N-M号楼` 连字符歧义（区间 or 并列），必须列入待确认。
  替换 4 处内联正则（`analyze_coverage.py` ×2、`analyze_coverage_vshape.py` ×1、`dxf_to_png.py` ×1）；
  `find_bldg_anchors` 共享标题展开同步改走该入口（实测 9 条样例：修复前 8 个楼号 → 修复后 24 个）。
- **`first_group()` 安全取组**：标题正则写成 `\d+号楼`（无捕获组）时旧代码 `m.group(1)` 直接 IndexError；
  现统一经 `first_group` 降级为 None。
- **P0-2 米数格式适配**：`analyze_coverage_vshape.parse_cable()` 兼容字段序差异
  （`20m*2` 与 `2Px2芯x36m` 并存）。判定序：命名组 → `--cable-meters-group`/`--cable-count-group`
  显式组号 → 按 `m`/`米` 后缀 → 数值大者。新增上述两个命令行参数。
- **P0-3 作业门禁**：两个覆盖脚本在「无楼栋作业 / 米数标注全不可解析 / 米数正则完全匹配不到」时
  **以退出码 2 终止**并列样本；**空结果不得返回 0**。
  退出码约定：`0`=成功；`1`=输入/文件错误；`2`=门禁拦截（本轮结果不可用，禁止下游当成功消费）。
- **P1 文档一致性**：`coverage_rules.md` 的"任选其一"改为「**必须并跑**」（与 `measurement_methods.md` 对齐）；
  删除"方法一/二/三"编号与降级箭头（避免暗示固定优先级）；修正计数（13→15 个文件、6→8 个子命令）；
  新增 `methods/titleblock_based/manifest.json`（图签标注型画像）。
- **P2**：清除脚本与文档中的具体项目痕迹；与坐标尺度绑定的几何默认值清为 `None`，改由参数传入。

### 2026-09-12（二）：读取标注新增「图签形态」+ 采集表三来源协议 + 地址树出表

- **术语更正（用户裁定）**：图签里的栋级 `N层/M户` + `N单元` 标注属**「读取标注」的图签形态**（测量原理同为直读文字），
  **不是独立方法**——方法池仍为四种（读取标注/区间法/竖线法/V型计算），不得新增第五种
- 「读取标注」的两个形态：①层内形态（逐层 `X户`/箱号/米数）；②图签形态（标题栏层栋级标注 + 固定几何偏移配对）
- 新增 **三来源协议**：图签标注 / 《楼宇信息采集表》/ 图纸实体，逐栋比对 `(单元数,层数,每层户数)`；
  **聚合计数不得作判据**（图纸重复绘制会翻倍）；不一致必须交人裁定
- 新增**图纸质量缺陷识别**：重复绘制（出现次数分布偏离基准）、楼名笔误（与"采集表有而图上无"成对定位）、
  图签内文字整段复制未更新（不得作户数依据）
- 新增 **人工裁定覆盖表**机制（`--patch`），每条裁定运行时留痕，禁止硬编码改数
- 新增**九级地址树出表**形态（每级节点各占一行）及其**行数恒等式**门禁，与扁平表 `gen_addressbook.py` 分离
- 户号规则补记：`层×100+序号` 已对 1901 户回验 0 例外；**首层减户**必须列入待确认项，不得自行套用
- 新增脚本 `scripts/read_titleblock_households.py`、`scripts/gen_9level_addressbook.py`；
  新增参考 [references/titleblock_and_intake_table.md](references/titleblock_and_intake_table.md)
- 实测：24 栋逐栋比对全部一致；出表 3 张（行数 677/730/963，户数 486/516/676），恒等式全部成立，
  与人工独立制作的成果逐表一致

### 2026-09-12：方法池去小区冠名 + 两法分立 + 原则三

- 方法按测量原理命名（读取标注/区间法/竖线法/V型计算），禁止用小区名冠名
- 覆盖判定改为信号驱动，不设固定优先级
- 竖线法只测覆盖楼层，区间法只测户数与安装楼层，两法不混用
- 原则三确立：所有结果必须基于客观数据的测量过程，说明测量过程和数据来源
- **通用化**：脚本与文档清除全部具体项目痕迹。**参数分类的判据是「是否随图纸坐标尺度变化」**（不是「名字里带不带容差」）——
  随尺度变化的检测类参数（图层名/标题正则/编号正则/米数正则/邻近容差）一律不设固定默认值；
  其中**能从图纸自身量出的改为缺省自适应**（竖线法的层高比例容差 `0.4/0.6/2.0×层高`、图签形态的 6 个几何容差），
  量不出的由 `require_params` 报错提示；不随尺度变化的算法常数（阈值/dpi）保留默认值
- **去重**：新增公共模块 `ftth_common.py` 承载 `clean_text / is_floor_text / attrib_hit / require_params / cluster_chain_mean / parse_floor_label`，各脚本删除内联重复实现
- **修矛盾**：`signals.json` 的 `floor_line_continuous` 拆为 `dedicated_wire_layer`（专用连线图层）+ `vertical_bus_traceable`（竖干可追踪，依赖前者）；`manifest.json` 由 `primary/fallback_1/fallback_2` 降级链改为 `candidates`（role: primary/alternate）+ `cross_check` 双跑交叉比对；`status` 改为机器可读枚举
- **统一入口**：`ftth.py` 新增 `coverage-vshape`（V 型计算）与 `verify-truth`（真值反查）子命令，共 8 个子命令

### 2026-09-11：覆盖判定与归属修复

- 新增 `--wire-layer`（连线图层参数），避免扫全图导致建筑线混入
- 新增 `--bldg-map`（FX编号查表归属），替代标题x中分法
- 新增 `--fx-symbol-layer`（图形符号定位箱位），替代编号文字坐标
- 新增 `--insert-attrib-tag/val`（按属性值识别设备，不按块名）
- 楼层正则默认改为 `None`（内置统一解析），支持 B1/WF 等非标准标注
- 守恒校验：出表行数必须等于源户数，不守恒即报错停止
- 覆盖范围改为竖干连续体+物理断口判定，禁止按安装楼层排序切分
- 户数统计新增 HDD 图块法双源对照
- 端点直推法替代旧"边界层"判定
- 新增 `verify_coverage_truth.py`（真值表反查门禁）

### 2026-09-10：探查与校验增强

- 设备块枚举：按属性值识别设备，不按块名
- 楼栋正则覆盖配套楼/商业楼等非标准标题
- 平面图只画代表性楼层时退化校验规则
- 标题重复检查（标题误标时用INSERT坐标交叉核实）
- 单元列数交叉校验（共享图纸换算）

### 2026-09-08：基础流程建立

- 五步标准流程（探查→解析→自检→渲染→出表）
- 三类图纸交叉验证
- 区间法楼层归属（替代最近楼层线法）
- 共享图纸模式识别与处理
- 多楼栋合并出表流程

### 2026-09-18：fxmap 来源收紧——仅限真实集中总图对照表（present），移除降级推算（用户裁决）

> 起因：凤鸣朝阳（长安区中威电机厂地块 FTTH）从零重跑。画像 fx_overview_map=absent
> （编号嵌在各楼系统图楼层表内部、100% 与『X户』/『Xm*N』同行），但 pipeline 旧判据
> 「有编号可提就跑」仍产出降级 fxmap，其『安装楼层』是拿编号文字 y 去**全图楼层刻度混排**
> 推算（图签区 8F 恰好插入 1#楼 5F/6F 刻度之间 → FL01-FX01 被误判 8F，实际 V型谷底=5F），
> 且被 pipeline 自动以 --bldg-map/--fx-map 回填 parse，造成：
>   - C3 双源交叉 8 箱假矛盾（8F vs 5F）→ 用户被迫人工裁决；
>   - parse 单元归属被对照表标题名覆盖，楼层表整批丢失（户数 193→313）。
> 用户裁决：分纤箱所在楼层 / 覆盖 / 每层户数，来源**只允许四种方法**（图上标注直读、
> V型计算、区间法、竖线法）与**不同图纸的多方标注**相互校验；**AI 不得自创算法**
> （如 y 坐标关联推算）参与校验或取值。

- **P0：`ftth.py _pipe_fxmap_gate` 判据收紧**：handoff「①分纤箱总图」状态==present 才产出
  fxmap；absent/variant 一律跳过（rc=3），不再产出降级对照表。旧判据「有编号可提就跑」
  删除（其降级路径曾把 8F 假值带进 parse）。用户显式 --bldg-map（人工确认过总图）仍受尊重。
- **P0：pipeline `_bmap` 不再自动用落盘 fxmap**：`args.bldg_map or (fxmap if (_fx_run and
  isfile) else None)` —— 只有 gate 实际产出（present）或用户显式给才回填；absent 图不会
  再拿残留/降级文件当对照表。
- **P0：SKILL.md 同步**：`parse --fx-map` 回填 / `parse --bldg-map` 定归属 / 对照表安装
  楼层口径A / pipeline 阶段顺序 四处标注「仅限画像 present」；absent 归属改由方法池四法
  测定 + 逐箱交叉验证交人工。
- **验证**：凤鸣朝阳 absent 图重跑 pipeline —— fxmap rc=3 跳过、无 bldg-map 回填、
  C3 17/17 一致（parse 区间法 vs coverage V型）、C1/C9 PASS、户数 313 守恒、FAIL 0 项。
- **备份**：技能目录外 `桌面/_ftth_skill_backup_20260918/`（ftth.py / extract_fx_map.py /
  SKILL.md，bak_20260918-100608_pre_fx_present_only）。

## 六十六（2026-09-18 云峰图三轮迭代实跑：4 处 P0/P1 修复）

场景：`云峰.dxf`（11 栋含 2 配套楼；7#/8#/10# 三栋共享一张系统图；全图无 `N层/M户` 图签
形态、无 `X户` 直读，户数只能走家居配线箱图标法）。从零跑三轮，跑一轮修一轮。

- **P0：coverage 楼栋名与其它产物不同源**（`analyze_coverage.py` 对照表分支）：
  `_bname = f"{_bn}#楼"` 丢弃对照表原文修饰词 —— 实测同一产物内楼栋键是「4#楼」、单元名
  却是「4#配套楼」，而 `parse` / `fxmap` 两侧都写「4#配套楼」。后果不止命名不齐：下游按
  楼栋名关联**静默失配**。改为按同号取对照表原文（走 `normalize_bldg_name`，与 parse
  同一函数）→ 兜底 `N#楼`。
- **P0：C9 待裁决判定用子串包含**（同文件结果状态段）：`(_bk in _o and _uk in _o)` 两处
  会错 —— ① 形态不同即失配（楼栋「4#楼」vs 对象「4#配套楼/FX22#」）⇒ 有实质冲突的箱被
  判 **settled 放行**（实测 FX22#/FX23# 两个「安装楼层与总图冲突」箱漏判，C9 报不出）；
  ② 子串跨号误伤（`7#楼` ⊂ `17#楼`、`1#楼` ⊂ `11#楼`）。改为按 `judge_object_name` 已
  确立的口径（**同一楼号即同一对象**）做精确范围匹配，并区分单元级 / 箱级作用域。
- **P0：已自行处置的提示被当裁决项**（同文件「需人工裁决」构造）：`疑似跨图带连续体
  （已排除）` 自述「已按非断口处理」、同一信息在单元级字段已完整留存，却进了裁决清单并
  据此判 pending ⇒ 一个"已排除"的提示把 7#/8#/10#/11# 四个单元全部卡死。现加机器可读
  `阻塞` 字段（该类为 false），pending 只由**阻塞项**驱动。
- **P1：titleblock 退出码语义**（`read_titleblock_households.py`）：本图无图签形态
  （信号 variant：『N层/M户』0 条）时返回 1（「命令自身失败」），pipeline 打出
  `! ... rc=1 —— 第二来源本次未取得` 的告警形态，把「图上没有」误导成「脚本坏了 / 该去
  校正正则」。改判 rc=3（本图不适用，申报制），并同步 pipeline 的打印分支。
  注意：`ToleranceEstimateError`（量到但排版自相矛盾）仍保留 rc=1 —— 那是"确实有问题"，
  与"本图没有"是两回事。
- **P1：pipeline inspect 阶段不接户数产物**（`ftth.py`）：`--count-box` 从不传入，C5/C8
  恒判 SKIP；即便使用者随后单独跑了 `count-box`，不手工重拼命令就**永远看不出来** ——
  「跑了但没核」会被读成「核过且通过」。现若 `<outdir>/count_box.json` 存在则自动纳入。
- **实测自纠（重要）**：上述 C9 修复的首版「剥楼栋前缀」条件过宽，把**单元名段本身**也
  剥掉（`4#配套楼/FX22#` 首段与单元名同号）⇒ 第 2 轮实跑仍没拦住 FX22#/FX23#；第 3 轮加
  `_parts[0] != unit_name` 后才确认拦下。**新写的门禁必须真机跑一遍再宣布生效** ——
  自测用例覆盖不到"修复本身引入的新缺陷"。
- **验证（三轮）**：第 1 轮 pipeline rc=2（C9 FAIL 3 项、titleblock rc=1）；
  第 2 轮 titleblock rc=3、楼栋名统一、count_box 进 inspect，但 C9 仍漏判 FX22#/FX23#；
  第 3 轮 C9 FAIL **5 项**（4#配套楼/FX22#、7#/8#/10#、11#配套楼/FX23#）—— 全部实质待裁决
  箱均被拦下，门禁由「假绿灯」转为正确拦截，**按契约不得出表**（这是正确行为，不是失败）。
- **未修（留待裁决，非技能缺陷）**：`count-box` 3 个列刻度偏移异常（列x 25939.8 / 26567.4 /
  27074.9）+ 5 组「一条刻度列服务多个图标列」→ 列归属须人工确认后传 `--col-scale-map`；
  `*16` 乘数标注 2 处（不得自行相乘）；`assemble --col-map` 须人工给列→楼栋/单元归属。
- **备份**：技能目录外
  `WorkBuddy/2026-09-18-12-36-09/.audit/backup_ftth_round1_20260918_1245/`
  （analyze_coverage.py / ftth.py / read_titleblock_households.py / inspect_closure.py，
  逐文件字节数已核对一致）。

## 2026-09-19 云峰实跑（gen 修复）

- **修（P0）：`gen_addressbook.py` NameError** —— `_fx_pmap`/`_norm_fx` 定义块原先嵌在
  `if args.coverage_json:` 内，走 assembly 路径（不传 --coverage-json）时 `_norm_fx`
  不存在，而模块级 `gen_unit_rows` 引用它必然 NameError（实测云峰 386 户出表即炸）。
  修法：定义块上移模块级；归一化**应用**块仍在 coverage 加载后（无 coverage 无需归一）。
  备份：`Desktop/云峰/.temp/backup_20260919_1319_pre_fix_normfx/`。
- 教训：模块级函数引用 main/条件块内嵌套定义 = 潜伏 NameError，新增嵌套 helper 时
  必须确认引用方作用域（同类模式排查已做：gen_unit_rows 是唯一中招引用点）。

## 2026-09-19 第二轮实跑（复现验证 + 告警盲区）

- **复现验证（结论：通过）**：同图同参从零重跑（pipeline 10 阶段 → count-box → assemble →
  apply-ruling → gen），与上一轮逐键/逐格零差异（含成品表逐单元格）。**解析链是确定性的**——
  可把「重跑差异非零」当作引入非确定性的回归判据。
- **已知限制（告警判据盲区，勿当判据用）**：`count_box_icons.py` 的「刻度列偏移异常」判据
  = 偏移 > 中位数 × `--scale-outlier-ratio`，隐含**全体列偏移同分布**假设。在「一条刻度列服务
  本栋两个图标列」这类形态下，偏移天然呈双峰（近列 ≈1×单元间距、远列 ≈2×单元间距），
  中位数落在近列批 → **远列必然全部误报**；而跨栋抢占造成的真错配偏移**偏小** → **零告警**。
  即该判据**既淹真阳性、又放真阴性**，只能当"需人工核对"的提示。
- **技能输出的 `--col-scale-map` 建议值禁止直接照抄**：该值是「当前几何最近配对」的镜像，
  在共用刻度列形态下会把错配固化。正确做法：按「楼栋标题 x 邻域 + 本栋单元模式
  （刻度列在本栋标题左侧、图标列在刻度列右侧 1×/2× 单元间距）」独立实测后再显式指定。

## 2026-09-19 云峰第 3 轮（刻度列误合并 P0 修复）

- **修（P0）：`count_box_icons.py` 的 `_scales_from_rows` 合并逻辑吞掉独立刻度列** ——
  原判据只看 x 差（≤1.0）谓"同一列的圆整差"，且按"标注多者胜"丢弃另一条。实测把
  x 仅差 0.7 的**上下两个图区的独立刻度列**（12 层 / 4 层）判成同一列并丢掉后者。
  症状：显式 `--col-scale-map` 指定该列时内部查不到 → 最近邻落到上排列 → 该楼全部图标
  "未归属"、户数 331→323。**通用性**：凡"多图区上下并排、独立刻度列 x 相近"的图都会中招；
  本例两列 y 基准巧合相同属侥幸，层高不同即算错。
  修法：合并判据加"同列必要条件"（标注 y 序列兼容），不再仅凭 x 差。
  备份：`Desktop/云峰/.temp/backup_20260919_1339_count_box_merge_fix/`（sha1 一致）。
- 同类模式全量排查：`analyze_coverage_vshape.py` 的合并基于「索引相邻 + 同值」、
  `ftth_batch` / `merge_json` 为 JSON 合并 —— **唯一中招点即此一处**。

## 2026-09-19 云峰第 4 轮（偏移异常判据改为「主偏移整数倍」）

- **修（P1）：`刻度偏移异常` 判据双向失效** —— 旧判据「偏移 > 全体列偏移中位数 × ratio」
  隐含**全体列偏移同分布**假设。在「一条刻度列服务本栋两个图标列」形态下偏移天然**双峰**
  （近列 ≈1× 单元间距、远列 ≈2×），中位数落近列批 ⇒ **远列全部误报**；而跨栋抢占造成的
  真错配偏移通常**偏小** ⇒ **零告警**。即**既淹真阳性、又放真阴性**。
  实测某图：旧判据 4 报 1 中 / 2 假阳 / 3 漏报；新判据 **4 报 4 中 / 0 假阳**。
- 改法：主偏移改用**最大簇中心**；判据改为「偏移必须是主偏移的**整数倍**」（容差
  `--scale-period-tol`，默认 7%）；新增 `mode_base()` / `period_dev()` 作唯一实现入口。
  旧 `--scale-outlier-ratio` 保留为**已弃用兼容位**（传了不参与判定），避免旧命令行静默失效。
  仍**只标记不自动改结果**（归层是否重算交人工），与既有纪律一致。
- 自测 6 组含边界：2× 占多数（旧判据在此必误报 1×）、全等值、空列表、零值（无除零）、单列。
- **通用性**：任何"一条刻度线/刻度列被多个数据列共用"的图都适用，与楼栋数、单元数无关。

## 2026-09-19 云峰实跑发现（待裁决，勿当已修）

- **契约缺口（P0）**：`result_confirmation` 的 `pending → settled` **没有人工裁决通道**。
  coverage 侧只由 `analyze_coverage*.py` 写 `pending`、parse 侧只按自洽性写，
  `apply_ruling.py` 只改 assembly、`ledger_state.py` 自述"只记录不裁决"。
  后果：只要 coverage 报了 pending，`inspect` 的 **C9 恒 FAIL / rc 恒为 2**，
  「裁决后重跑 inspect 转 PASS」这一步**在技能内不可达**；裁决值只落在成品链（assembly），
  coverage.json 本身仍是矛盾值（实测某箱 coverage 写 1F、成品表为 B1）。
  待选方案：A 新增官方回写通道（按裁决作用域置 settled + 记 `E-HUMAN-RULING:<编号>`）／
  B 明文化允许人工编辑该字段／C 有台账时降级 C9（不推荐）。
- **纠错（我此前的两处断言不成立，勿沿用）**：
  1. 「count-box 的偏移异常会卡 `inspect` 的 C2 门禁」—— **错**。该 FAIL 分支仅在
     parse 侧 **0 箱**时进入；parse 侧有箱时 C2 走 PASS，本判据**不进任何门禁**，只是提示。
  2. 「裁决后重跑 inspect 可使 C9 转 PASS」—— **做不到**，见上条契约缺口。

### 2026-09-25（一百零一）：柳辛庄实跑暴露三缺陷 —— C6 双行 PASS 伪装闭合 + V 型法覆盖零产出静默放行 + C9 零对象/零字段混写（只改 inspect_closure.py）

**实测动因**：柳辛庄 8 带（V 型法形态）全链实跑：band9-1/band9-2 的 inspect.json 里 C6 有两条记录（SKIP +「闭合 0/缺线索 0/安装层越界 0」PASS），机读方按末条消费即把 16 箱零覆盖读成闭合；8 带 coverage 箱级记录全 0（V 型法窗口内无箱号锚，箱编号在布线图区，属图纸固有分离）却 C9 只 WARN、全链无任何 pending/FAIL；band5 覆盖 absent（rc=3）后 20 箱零结论而 inspect FAIL 0 全绿：① **P0 C6 双行**——09-19 修复加的零记录 SKIP + WARN 分支后未短路，落到末尾兜底又追一条 PASS，改为 FAIL 单记录 + else 短路（C3 同期分支有 `elif not cmap: pass` 短路，经核无同构缺陷，不动）；② **P0 覆盖零产出门禁（方案 B）**——parse 有箱而 coverage 箱级记录为 0（含未提供 coverage 的 absent 路径）时 C6 判 FAIL（rc=2 输入不足/须修，非 rc=3；L1-C8 静默放行禁令），未选方案 A（vshape 侧无 parse 箱清单，补箱级 pending 记录需新增输入与管线透传，改动面大且有编造覆盖之嫌）；③ **P1 C9 报文**——「已提供但零字段」拆分为零对象（coverage 箱级 0 条，无对象可挂字段，非字段漏写；已由 C6 FAIL 拦下，此处只解释不重复拦下）与有对象无字段（产出方未落 L1-C8 字段，原口径 WARN 点名），避免问题 2 修复后 C9 自相矛盾。**验证**：py_compile 全绿；budget rc=0（SKILL.md 46814 B 未动）；合成三态 fixture——零覆盖 C6 单条 FAIL/rc=2 且 C3/C6 均单记录、有覆盖 C6 单条 PASS/rc=0（竖线法/凤鸣路径逻辑未动）、缺 coverage C6 单条 FAIL；冒烟 ALL PASS（T5 缺 ezdxf 跳过，与基线一致）。**行为变化（如实记录）**：柳辛庄 band1~band4/band8/band5 此前 rc=0 全绿，修复后因 C6 FAIL 转 rc=2——正是本次要拦下的静默放行，非回归；云峰（23 箱带字段）、凤鸣朝阳（17 箱闭合单行 PASS）两条路径零差异。

> AI生成