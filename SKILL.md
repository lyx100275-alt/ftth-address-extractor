---
name: ftth-address-extractor
description: "FTTH fiber-to-the-home engineering drawing parser. Parses DXF (converted from DWG via ODA by the user) with Python ezdxf, extracts fiber distribution box IDs, floor plans, and household counts, and generates standardized address tables (xlsx) with one row per household linked to distribution boxes, or as a 9-level address tree. Also reads building-level unit/floor/household counts straight from the drawing title block and cross-checks them against a project building intake table (xls). Use when user provides a DWG/DXF file and wants to: (1) extract fiber box info from FTTH engineering drawings, (2) generate standardized address tables (flat per-household or 9-level address tree), (3) parse FTTH PON architecture drawings, (4) rebuild a standard address table for a block/phase not yet done. Triggers: FTTH, 光纤入户, 分纤箱, 标准地址表, 九级地址, 地址树, 图签, 楼宇信息采集表, 图纸解析, DWG, DXF, 通信工程图纸."
name_cn: FTTH标准地址表提取
description_cn: "从FTTH通信工程图纸(DWG/DXF)中提取分纤箱编号、覆盖楼层、户数等信息，自动生成标准地址表(xlsx)——支持每户一行扁平表与九级地址树两种形态；并支持从图纸图签直读栋级 单元数/层数/每层户数，与项目《楼宇信息采集表》逐栋交叉印证。支持ODA转换DWG→DXF、Python ezdxf解析。"
create_source: super-agent-skill-creator
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '408aa368-509f-4693-aaef-11069f5524fc'
  PropagateID: '408aa368-509f-4693-aaef-11069f5524fc'
  ReservedCode1: 'af3f8661-ce95-4b2a-bf91-34df45ce5ab1'
  ReservedCode2: 'af3f8661-ce95-4b2a-bf91-34df45ce5ab1'
---

# FTTH标准地址表提取

## 执行摘要（会话开始先读本节）

**做什么**：从 FTTH 竣工图（DXF）提取分纤箱编号 / 覆盖楼层 / 每层户数，生成每户一行的标准地址表（xlsx）或九级地址树。

**顺序**：`Step 0` 确认 DXF → `Step 1a` 探查（出 `profile.json`）→ `Step 1b` 解析 → `Step 1c` 户号 → `Step 2` 自检 → `Step 3` 用户校验 → `Step 4` 出表。**Step 2 三条硬门禁任一 FAIL 不得出表**；**禁止迁移见「Agent 状态机」**。

**底线（永不违反，全文见 L0）**：不推断、不编造、不私改、矛盾即停、不识标注必问。

**矛盾 / 判不了**：停下 → 按 **L1-C5** 四列列入待确认项 → 交用户裁决 → 锁定为基准值。**禁止静默择一**。
**三层**：`测量`（图上已载信息的量化读取）不受限 → `归一化`（只改写法、不引入新数值）可自动 → `推理`（图上没写、判断哪方像笔误）交人工。判据见 [operations_discipline.md §5.1](references/operations_discipline.md)。

**本文件**：只载协议/状态机/硬约束/名目清单；细则在 `references/` 与 `SKILL_CHANGELOG.md`。

## L0 不变量（总则）

> 本节条款**不因所在步骤而变**，任何步骤、任何脚本均适用；与后文流程描述冲突时**以本节为准**。

### I1 角色与任务

**纯执行者**：① DXF 直读楼栋/单元/楼层/户号→每户一行标准地址；② DXF 直读分纤箱编号/安装楼层/覆盖楼层→每户关联分纤箱。

### I2 五项禁区（违反即失败）

| # | 禁区 | 说明 |
|---|---|---|
| P1 | **禁读图外推理** | 不得从已有信息推导未写的结论（从楼层推户号、从皮线走向推覆盖分界）。**V 型计算属测量，不在此列**。工程判断只列事实交人裁决 |
| P2 | **禁编造** | 无数据不编、不填默认、不假设 |
| P3 | **禁私改** | 已确认数据锁定为基准值，修改须经用户同意 |
| P4 | **矛盾即停** | 内部/跨图/DXF与视觉模型矛盾→交人，**不自行择一，惯例/多数亦不作依据** |
| P5 | **不识标注必问** | 非标准标注/符号不猜含义，暂停问用户（`*N`/`xN` 已定直读，见 L1-C1） |

### I3 证据要求

每个结果须说明**测量过程**与**数据来源**。**「已确认」防伪**：标为「已确认」的口径须能引用**本会话用户原话**，否则列入待确认。机械形态见 I6 与「Agent 状态机·锁定基准」。

### I4 矛盾即停：处置规程

| 环节 | 规程 |
|---|---|
| ① 触发 | I2-P4 四类矛盾；「同一要素多处出现且表述不一致」（见「图纸信息模型」执行纪律） |
| ② 动作 | **按 operations_discipline.md §五 分级处置**；**不静默择一、不由脚本自动取舍** |
| ③ 产出 | 按 **L1-C5** 四列列入待确认项，附双方数值与坐标/来源 |
| ④ 交给谁 | 用户；参考线索（惯例、统计多数、命名规律）仅供参考，**不得作为结论** |
| ⑤ 裁决后 | 裁决结果**锁定为基准值**，后续步骤只能新增、不能覆盖 |

### I5 权威等级（冲突裁决顺序）

| 等级 | 来源 | 效力 |
|---|---|---|
| **A** | 用户在**当前会话**的明确裁定 / 指示 | 覆盖其余全部条款；非常规指示须标注「据用户指示（非常规）」 |
| **B** | L0 不变量、「测量方式架构」铁律 | 不得违反，**违反即返工** |
| **C** | L1 契约、操作纪律、工作流规则 | 可按现场权衡，但须说明理由 |
| **D** | 脚本默认值、示例、历史案例数据 | 仅供参考；**换图必须先按探查结果覆盖** |

### I6 操作纪律

| 纪律 | 规则 |
|---|---|
| **维护约定** | 技能目录内**只放运行文件**；备份一律存**技能目录之外**（该目录由程序管理、可能被整体清理且不进回收站） |
| **性能纪律** | **同一张 DXF 一个任务里只做一次全量解析**：一律经 `ftth_common.load_dxf()`（内置 `<DXF>.pkl` 缓存，按 mtime+size 校验，**禁绕开它直写 `ezdxf.readfile()`**）；**只查几何**改用 `load_geom()` 读缓存 |
| **探查纪律** | 探查/核查脚本一律写文件执行，**禁 shell 内联**；一次性脚本写 `.temp/<项目>/`；同类核查趸2个改跑 `inspect_closure.py` |
| **环境与调用纪律** | 解释器 / 禁内联 / 禁 pip / 脚本路径四条 → **L1-C7** |
| **效率纪律** | ① 一次给全命令、裁决集中提交（`ftth.py pipeline` 一条跑完，中间产物只落盘不请示）；② 探针只用技能自带命令、禁重写同类；③ 断流后开新会话喂已定案产物 |
| **后果与处置** | `plan` 已输出每个信号的**「后果与处置」**与**本图「风险预告」**（`profile.json` 的 `risk_forecast`），是**既定路径**——照做即可，**不得重新推导、不得自造探查脚本** |
| **进度纪律** | **todo 随做随更**：每完成一个 Step 立即更新，不攒到最后批量改 |
| **落盘纪律** | 四件套（`.temp/<项目>/`）：①`理解快照.json`（值+来源+状态）②`裁决台账.json`（问题+裁决原文+裁决人+适用范围，对话说的不算落盘）③`别名台账.json`（原始异写）④`状态.json`（只记位置）。读写走 `ledger_state.py`，不手拼 JSON；下阶段先读，未变更不重推。口径见 [operations_discipline.md](references/operations_discipline.md) §六~§九 |
| **交付纪律** | 覆盖已存在的交付文件前先以写模式打开目标**探测占用**（被 Excel/WPS 打开时 `Copy-Item -Force` 会长时间挂起、期间正式路径仍是旧版）；被占用则提示用户关闭后重试，**不静默挂等** |

## L1 契约（全局唯一定义）

> 本节是**跨步骤接口定义**；任何步骤提到下列契约一律指回本节，**禁重写副本**。新增/改动契约须登记 `version.json` 的 `contract_coverage`（漏登 rc=2，见 [operations_discipline.md](references/operations_discipline.md) §九·补）。

**两档读法（2026-10-02 会审整改 P2-3）**：C1~C9 中 **`enforced` 的（有机器执行方）可以照着跑**；标 `declared` 的**只有文字纪律、没有检查器，靠自觉**。当前**全部 9 条均为 `enforced`**（C7 于一百四十六由 `check_launch_path.py` 补上检查器后升档）。分档的机器真源是 `version.json` 的 `contract_coverage[*].coverage`，改档须改那里（改本文文字无效，门禁只认登记）。

| 档 | 契约 | 执行方 |
|---|---|---|
| `enforced` | C1 C2 C3 C4 C5 C6 C7 C8 C9 | 见各条「校验」行 / `contract_coverage` 登记 |
| `declared` | （当前无） | —— |

### C1 输入契约：信号状态与选法

| 状态 | 含义 | 处置 |
|---|---|---|
| `present` | 图上有 | 附证据；该方法可用 |
| `absent` | 图上确实没有 | 附证据 + 降级路径；**不阻塞**（方法之间同级、无降级之分） |
| `variant` | 形态变体（如仅文字提及无图标） | 附证据 |
| `unknown` | 判不了 / 没判 | **不得当作成立**，须人工复核或补探查；计入 `completeness.未作答` → **rc=2** |

- **信号状态是选法唯一依据**：某方法 `requires` 不成立即不可用；多候选同时可用按顺序取首个，不并跑、不互校（覆盖：有米标→V型法）。
- **户数口径（2026-09-27 裁决）**：①层户数标注（`X户` 或 `*N`/`xN`：乘号后数字即户数）→直读；②无标注→数图标；③无图标才数皮线。**三口径选定即出数，互不校验**。
- 方法池见「测量方式架构」；信号定义在 `methods/signals.json`（13 个信号，各带 `consequence`）+ `ftth.py plan`（逐条打印后果与 `risk_forecast`）。

### C2 门禁契约：退出码语义

| rc | 语义 | 动作 | 适用范围 |
|---|---|---|---|
| `0` | 正常 | 继续下一步 | 全部脚本 |
| `2` | **输入不足**：未作答`unknown`/坐标缺失/必须修项/归层0 | **停**，补探查重跑`plan`或按C5交人；**禁出表** | `parse`/`coverage`/`coverage-vshape`门禁；`ledger_elements`；`count_box`（示意画法走`3`） |
| `3` | **早失败**：① `absent`→跳过+降级（非错误）；② 提取不完整→禁当完整出表；③ 示意画法确认→回落皮线 | 按分支处置；③仅`count_box` | ① 入口门禁；② `read_titleblock`；③ `count_box` |
| `4` | 写盘/缓存失败 | 读stderr重跑 | 见scripts_reference §退出码语义 |
| 其他 | 命令自身失败；缺第三方依赖发`1`（环境类，与输入类`2`区分） | 读 stderr 重跑 | 全部脚本 |

> 脚本级机器护栏（正则捕获组自检 / `[CONFIG-IGNORED]` / 单元歧证据明细 / 台账字段表）见 [scripts_reference.md](references/scripts_reference.md) §脚本级机器护栏。

### C3 交接契约：`handoff` 申报制（2026-09-13 用户裁定）

**至少**回答两项：**① 编号↔楼栋/单元对照关系**（有无？可读否？安装位置同图可读否）、**② 系统图选法**（分纤箱位置/覆盖范围/每层户数各用什么方法——**只申报方法，结果由第二步跑出**）。**申报制，非存在性检查**：没有对照关系的图纸也得过，有则说有、无则说无，均附证据。

| 怎么答 | 含义 | 是否阻塞 |
|---|---|---|
| `present` | 图上有（附证据） | 不阻塞 |
| `absent` | 确实没有（附证据+降级路径；方法同级无降级） | **不阻塞** |
| `variant` | 形态变体（附证据） | 不阻塞 |
| `unknown` | 判不了/没判 → `completeness.未作答` | **阻塞→rc=2** |

- `absent` 项写进 `completeness.缺失项及降级路径`；`ok = 未作答为空 且 不可解析为空`。
- **②「分纤箱位置（安装楼层）」「每层户数」缺任一⇒不可解析⇒rc=2**（系统图必备）；「覆盖范围」可 absent+降级，不阻塞；前置信号 unknown 才算未作答。
- 安装楼层方法随选定方法导出（读取标注或区间法），不得断言方法池不存在的方法。

> 字段级定义、`completeness` 结构、`gate.status` 评估、JSON 示例、接入 SOP 见 [measurement_methods.md §4.4](references/measurement_methods.md)。

### C4 判定契约：对照表判据

**只看内容不看图名**。编号须与楼栋/单元标注**同行**才算对照表：`|dy|≤本图行距`（由楼层标注 y 差量出）；`|dx|≤主体 x 跨度 15%`。多数编号与 `X户`/`Xm*N` 同行→判 absent（编号属各楼系统图）。实测背景见 [measurement_methods.md §4.5](references/measurement_methods.md)。

### C5 异常契约：待确认项四列格式

凡判定不了、矛盾、需用户裁决的事项，**统一按本表格式**呈现（Step 3 汇总提交）：

| 字段 | 内容 |
|------|------|
| **问题** | 简明描述需要用户裁决的问题 |
| **图纸已知事实** | 从 DXF 直读到的相关数据（标注"直读"） |
| **参考线索** | 相关规律 / 推算逻辑（**仅供用户参考，不得作为结论**） |
| **需要您裁决的内容** | 明确告知用户需要确认什么 |

进入条件：L0-I4（矛盾即停）、C2 `rc=2`、C1 `unknown`。

### C6 输出契约：表结构与行数恒等式

- **九级地址树**（每级节点各占一行）：`行数 = 1 + 1 + 楼栋数 + 单元数 + Σ层数 + Σ户数`。不满足即**报错停止**（检出"整层丢失 / 复制份数算错"最有效）；前 5 级每行重复填、节点行右侧留**空字符串**。
- **扁平表**（每户一行）：24 列 A~X，格式严格跟模板 `assets/标准地址表模板.xlsx`，**数据全部从 DXF 独立生成**。
- **表头**：必须取自项目已定稿的表（`gen_9level_addressbook.py --header-xlsx`），**禁止自造**。两种形态**不可互替**。
- **回读校验**：出表后必须回读复核上列三项，**不通过即视为未交付**。

> 24 列对照表见 [addressbook_template.md](references/addressbook_template.md) §回读校验与 AIGC 水印行；九级填写规则见 [titleblock_and_intake_table.md §四](references/titleblock_and_intake_table.md)。Step 2 门禁与 Step 4 实现均引用本条，**不再复述公式**。

### C7 调用契约：路径、解释器与命令纪律

> **校验**：`ftth_launcher.py` 在派生业务脚本前置 `FTTH_VIA_LAUNCHER=1`，
> `write_json` 见之即在产物顶层写 `_via_launcher: true`（布尔真值，非时间戳/路径）；
> `scripts/check_launch_path.py` 反查产物目录，缺该键即判疑似绕过启动器直调（rc=2）。
> run_smoke T4e/T17b 有正反用例与形状覆盖反查。

| 项 | 规则 |
|---|---|
| **脚本路径** | 技能脚本一律从本技能 `scripts/` 目录（即 SKILL.md 所在目录）调用；**禁止猜测或拼造其他用户目录 / 技能副本路径**（按不存在的目录试跑单次白耗分钟级） |
| **解释器** | 走启动器 `python "<技能目录>\scripts\ftth_launcher.py" <子命令或.py脚本>`（首参以 `.py` 结尾即转发；启动器探测带 ezdxf 的解释器，`FTTH_PYTHON` 可指定）。入口 `python` 无需带 ezdxf；**禁绕过启动器**（宿主PATH常无ezdxf）。例外见 scripts_reference §解释器契约。 |
| **禁内联** | **禁止内联多行 `python -c "…"`**（引号被 shell 吃掉）；分析脚本一律先落盘再执行（同 L0-I6 探查纪律） |
| **禁 pip** | **不要用 `pip` 补装依赖**——镜像不可达时报错会伪装成「包不存在」 |

> 解释器候选清单、退出码 9 语义、探测细节见 [scripts_reference.md](references/scripts_reference.md) §解释器契约。

### C8 结果状态契约：两字段正交（2026-09-18 立）

| 字段 | 取值 | 含义 |
|---|---|---|
| `result_origin` | `measured`/`derived`/`unresolved` | 图上直读或几何测量 / 按规则算出（V型/断口/区间法）/ 无解 |
| `result_confirmation` | `settled`/`pending` | settled 可进成品；pending 禁进成品 |

- **两字段正交**：「怎么来的」≠「定案没有」。V型算出=derived；与图签不符列待确认=同时pending。`*N`/`xN`=measured+settled。
- **与 C1 分层**：C1 回答「图上有没有」（事实层），本契约回答「怎么来的/定案没有」（结果层），不共用枚举。
- **校验**：`inspect` C9 项扫描全部产物，pending/unresolved 非空即 FAIL；缺字段判 SKIP（老产物不误拦）。
- **覆盖申报**：C9 须显式申报扫了哪些来源、哪些有字段。已提供但零字段的来源判 WARN 并点名。
- **产出方须落地**：`parse_dxf_structured.py` 分纤箱级已产出两字段。新增产出方须登记 `contract_coverage`（见 L1 节首）。
- **pending 须有作用域**：疑点须能机械关联到楼栋/单元/箱才产生 pending。见 [coverage_rules.md §待裁决项的作用域](references/coverage_rules.md)。

### C9 证据来源等级（2026-09-18 立，与Step2自检C9不同名目）

来源冲突按等级取信（人工拆`E-HUMAN-RULING`最高/`E-HUMAN-GUESS`最低），完整表见 [operations_discipline.md §五·补](references/operations_discipline.md)。

## Agent 状态机（迁移门禁）

> 本节**不新增规则**，只把已有条款表达为可机械核对的迁移门。**核对器：`ftth.py transitions --project-dir <项目目录>`**（三本台账全缺给 rc=3）。与 L0 冲突时以 L0 为准。

```
INPUT ──► PROBE ──► PLAN ──┬─ 有 unknown ──────► REPROBE / USER
                           ▼
                         PARSE ──┬─ 矛盾 ───────► USER（C5）
                                 ├─ 不完整 ─────► REPROBE / USER
                                 ▼
                              INSPECT ──┬─ hard gate FAIL ──► STOP
                                        ▼
                             USER VALIDATION ──┬─ 有 pending ──► USER（C5）
                                               ▼
                                   LOCKED BASELINE（裁决已落盘）
                                               ▼
                                     ASSEMBLE ──► OUTPUT ──► READ-BACK VALIDATION
```

| # | 禁止迁移 | 依据 |
|---|---|---|
| 1 | `unknown` → `confirmed`（含用「继续」「应该没问题」代替裁决） | L1-C1 / L1-C2 |
| 2 | `contradiction` → `OUTPUT` | L0-I4 |
| 3 | 用脚本默认值 / 历史档案消除 `pending` | L0-I5-D |
| 4 | `INSPECT` 任一 hard gate FAIL → `ASSEMBLE` | Step 2 / L1-C6 |
| 5 | `USER VALIDATION` 尚有未裁决 `pending` → `OUTPUT` | Step 3 / Step 4 前置 |
| 6 | **申报态与证据不符**：`状态.json` 申报 `LOCKED BASELINE`/`ASSEMBLE`/`OUTPUT` 而 `pending` 未清 / 闭包 FAIL / 成品不存在 | L1-C2（口径见 [operations_discipline.md](references/operations_discipline.md) §九） |

> **当前态可观测**：①~⑤是否定式检查，缺正向锚点。`ledger_state.py state-set` 落 `状态.json`，判据#6 与台账/闭包/成品对拍；未申报只判 WARN 不拦门。枚举权威＝`ledger_state.py` 的 `STATES`；口径见 [operations_discipline.md](references/operations_discipline.md) §九。

**锁定基准**：用户裁决按 I6 写台账，机械形态＝`理解快照.json`（值/来源/状态=已确认）＋`裁决台账.json`（问题/裁决原文/裁决人/适用范围）。**对话说的不算锁定**；新值冲突按 L0-I4 停，不覆盖。

**回读校验**：出表后按 L1-C6 复核行数恒等式与户级字段，不通过视为未交付。

## 图纸信息模型：八项（2026-09-14 立三要素，2026-09-18 扩八项，最顶层）

> **一张 FTTH 竣工图上，需要读的只有八样东西。八样读全，标准地址表即可直接推出，不需要任何额外的工程判断。**

**图纸叫什么名字不作判据**（总图 / 光缆路由图 / 综合布线系统图都只是叫法），一律**按内容特征**识别。

| # | 项 | 回答什么问题 |
|---|---|---|
| ① | **楼数量** | 一共几栋 |
| ② | **楼号** | 都是哪几栋 |
| ③ | **单元数** | 每栋几个单元 |
| ④ | **楼层** | 每个单元几层（**层归属单元**；栋级 / 单元级两种粒度均支持） |
| ⑤ | **每层户数** | 每层展开几行 |
| ⑥ | **分纤箱编号** | 这个箱是谁 |
| ⑦ | **分纤箱安装楼层** | 装在哪层 |
| ⑧ | **分纤箱覆盖楼层** | 管哪些层（**直读优先·尚未接入产出口**；否则**有米标走 V 型**，无则竖干断口） |

**组装规则（八项 → 标准地址表）**

```
P列(某层某户) = 该层所属分纤箱编号
行数          = Σ(覆盖层 的 每层户数)
安装位置      只作校验，不参与分配
```

**来源数分流（2026-09-18 裁定）**：逐项数图上**独立来源数**（换算法复算不算）——`0`先自证「真的没有」（没找到≠图上没有），仍无则待确认；`1`**直接采信**；`≥2`**互相比对**，不一致列全选项交人选不裁决。禁自创比对算法。细则见 [operations_discipline.md §五](references/operations_discipline.md) / [coverage_rules.md](references/coverage_rules.md)。

**执行纪律**

- **八项逐栋×逐单元读全**：缺项先找其他承载形式（换图层/写法/实体类型），**不得因"这个写法没匹配上"就判不存在**（absent 须自证）。
- 必须推导时跑方法池（取法见 **L1-C1**）。
- **引用纪律**：文档/代码互引只用章节名或条目名（`L0-I#`/`L1-C#`），**禁写行号**（随插入失效）。
- **读全后先做八项体检**：六要素齐全才允许生成表。
- **同一要素多处出现须交叉校验**；矛盾按 [operations_discipline.md §五](references/operations_discipline.md) 分级处置，不静默择一。

## 测量方式架构

> **核心原则（2026-09-12 用户确立）：方法按测量原理命名，禁止用小区名冠名；没有统一模式，每张图纸按标注情况从方法池选组合。**
> 完整架构（方法池详表、铁律全文、算法细节、实测判据、标准流程详解、图纸类型参考表）见 [references/measurement_architecture.md](references/measurement_architecture.md)。

方法池（四种，按测量原理命名；互为**平行候选**、无主用/备用/降级之分 —— 2026-09-13 用户裁决）：

| 测量方法 | 测什么 | 判定依据 |
|---|---|---|
| **读取标注** | 图上明确写了的量：编号、楼层、户数、米数、芯数等（含图签形态栋级 `N层/M户`+`N单元`） | 直读文字标注内容与坐标 |
| **区间法**（楼层带归属） | ① 每层户数（皮线标注/家居配线箱图标落带）；② 分纤箱安装楼层 | 楼层线切 y 轴成带，`y_i ≤ y < y_{i+1}` 归属第 i 层 |
| **竖线法**（端点直推） | 分纤箱覆盖楼层（需干净竖干连线） | 沿竖干追踪，断头端点定覆盖分界 |
| **V型计算** | 分纤箱覆盖楼层（需皮线米数标注；写法不固定，检测器与生产脚本须全兼容） | 米数 V 形：谷底=安装层，相邻谷底间米数最大行=分界（该行归下段） |

**每层户数优先级**：① 层户数标注（`X户` 或 `*N`/`xN`，**乘号后数字即户数**）直读最高；② 无标注数家居配线箱图标（每户一个、贴皮线末端；皮线先按 `(x,y,内容)` 去重）；③ 无图标才数皮线。图标不可用三情形（无图标/示意画法/rc=2）回落皮线。**三口径选定即出数、互不校验**；见 L1-C1。

**选法规则**：信号在则用、缺则换同级方法；多路同时成立按候选顺序取首个。共同前置 `floor_scale`（区间法、竖线法、V型谷底定层均依赖）；无楼层刻度只剩纯文字直读。**标准流程＝探查→解析→自检→出表**（探查是"测量的指挥"——只定怎么测，自己不测量）。

**铁律**（**违反即返工**；只列条目名与关键判据，全文与实测反例见 [measurement_architecture.md](references/measurement_architecture.md)）：

① 禁跨用途混用：竖线/V型只测覆盖，区间法只测户数与安装层；禁「按安装层排序切分」当覆盖判据。
② 镜像铁律：检测器与脚本写法兼容表同步维护；absent 须附反证。
③ present 须过形态检验：命中文字形态与脚本消费形态一致。
④ 档案差异项不得静默：须人工复核后才可 skip。
⑤ 箱位残差超阈≠位置不可信：区分「找不到箱」与「安装层冲突」，附几何最近层。
⑥ 接手既有产物必须重跑信号核对：入口固定「读画像→重选方法」，禁继承上轮方法。
⑦ 多地块分带：每带＝本带图名 y→上邻带图名 y（最上带取顶）；取中点吞邻带内容。
⑧ 箱位锚 x 邻域门禁：箱锚到米数列 x 距离≤k×字高中位（默认k=10），超阈登记不静默丢。
⑨ 竖线法前置五条：简称锚点/专用图层过滤/偏移校正/逐候选层各配一次/锚点二维聚类一节多箱。

**覆盖判定是解析阶段独立必做**：每箱必给 `覆盖楼层`、`判定依据`（∈读取标注/竖线法/V型计算/人工裁决/待确认，**首段须为枚举词**）、`依据来源`（图层+坐标区间）。判不了显式写 `判定依据=待确认` 列入清单，**不留空、不用"整栋楼"填充**。

## 栋级入户规模：读取标注（图签形态）+ 采集表三来源协议

**触发条件**（任一命中即走本路径）：图签层有成对标注 `N#楼` + `N层/M户` + `N单元`；或项目另附《楼宇信息采集表》。

采集表（逐栋逐单元）=**第一来源**，图签标注（逐栋）=**第二来源（独立复核）**；**逐栋**比对 `(单元数, 层数, 每层户数)`，不一致即列双方数值 + 坐标交人裁定，**禁止自动择一**；**聚合计数不作判据**。图签脚本 rc=3（提取不完整）见 **L1-C2**，不得当完整结果出表。

> **完整协议**（来源角色、几何关系、地块分段、`--patch` 裁定覆盖表、键名与执行序、待确认项模板）与机器护栏见 [titleblock_and_intake_table.md](references/titleblock_and_intake_table.md)、[scripts_reference.md](references/scripts_reference.md)；脚本 `scripts/read_titleblock_households.py`。

**九级地址表 = 地址树展开**（**不是"每户一行"的扁平表**，两者**不可互替**）：每一级节点自身占一行；**行数恒等式硬门禁**见 **L1-C6**（`gen_9level_addressbook.py` 内置校验）；前 5 级每行重复填、节点行右侧留空字符串；填写 / 户号规则见 [titleblock_and_intake_table.md §四](references/titleblock_and_intake_table.md)。

## 运行环境与模板

- **环境**：Python 3.x + `ezdxf` + `openpyxl`；DWG→DXF 由用户侧 ODA 完成（**助手不调用**）；**脚本产物一律由 Python 自己写文件**（勿重定向，默认产出 UTF-16）。解释器确认一次后本会话不再重探 —— 完整环境表见 [scripts_reference.md](references/scripts_reference.md) §环境与命令纪律。
- **模板**：`assets/标准地址表模板.xlsx`（Sheet「标准地址」，24 列 A~X，无合并单元格），**示例行只示格式、不得照搬数据**；24 列对照表见 [addressbook_template.md](references/addressbook_template.md)；输出契约见 **L1-C6**。

## 工作流

### Step 0: 确认DXF文件

- 用户直接提供DXF文件路径，助手无需做任何格式转换；DWG→DXF 由用户侧转换（用户请求辅助时说明 ODA 操作步骤）
- **脚本路径与调用纪律**：见 **L1-C7 调用契约**（全局唯一出处）。

### Step 1: 探查 → 解析

#### Step 1a: 图纸探查（每张新图纸必做，不假设参数）

**首步：生成全量几何缓存（一次成本换全程秒查）**

```
python "<技能目录>\scripts\ftth_launcher.py" dump_geom.py --dxf 图纸.dxf
```

产出图纸同目录 `<DXF>.geom.json`（文字/INSERT/线段/图层统计/包围盒）。后续任何几何统计或临时查询读该 JSON，不再回原图。⚠️ `geom.json` 三坑与 schema 见 [pipeline_details.md §16](references/pipeline_details.md)；整组顶点/块属性走 `load_dxf`。

对每张新DXF，先用ezdxf探查（**不预设任何项目特有参数**；全子项与判据见 [probe_checklist.md](references/probe_checklist.md)）：

1. **六项基础探查**（图层/文字/采样/尺度/线段/INSERT；**按属性值识别设备、不按块名**）
2. **对照表检查（如有，先做）**：按内容特征定位提映射（`--bldg-map` 优先几何；正则先枚举本图写法；映射须人工目视核对；absent/variant不推算）
3. **单元×箱交叉清点**：双向差集，缺席记「未核」。

探查结果决定后续解析脚本使用的参数（图层名、文字类型、坐标阈值等），**不硬编码**。

**Step 1a 产物：图纸画像 `profile.json`**（选法结果，必须显式产出）。探查不只出参数，还须出画像——「探查是测量的指挥」的落地。

```
ftth.py plan --dxf 图纸.dxf --probe config.json --out profile.json
```

- 画像：`plan` 逐信号判定写 evidence（先核对 `param_source_actual`）；与档案一致率低即新形态，走 measurement_methods §4.2/§五接入 SOP。
- 交接契约与总图判据见 **L1-C3**/**L1-C4**。

**搜索纪律**：禁窄范围、禁关键词首扫、无标注查实体（visual_model_lessons §四）。

#### Step 1b: 结构化解析

探查确定参数后，用 ezdxf 提取全部 FTTH 信息。脚本清单与职责（43 个文件）见 [scripts_reference.md](references/scripts_reference.md) §脚本清单与职责，**调用一律走 `ftth_launcher.py` 启动器**（见 **L1-C7**）。

**入口**：`ftth.py`（16 子命令：`pipeline`/`probe`/`plan`/`parse`/`coverage`/`coverage-vshape`/`inspect`/`assemble`/`apply-ruling`/`count`/`count-box`/`gen`/`budget`/`transitions`/`split-band`/`verify-truth`）；参数优先级：命令行显式>`--config`>默认。**`ftth.py pipeline` 串跑 11 阶段**（以 `_PIPE_STAGES` 为准，完整链见 [pipeline_details.md](references/pipeline_details.md) §11；只解析不出表）。**口径**：`count`=皮线计数法、`count-box`=家居配线箱图标法，同属区间法口径。

**必传参数**：完整参数表与三个高频坑见 [scripts_reference.md](references/scripts_reference.md)；最易踩的是 `--floor-pattern` **不得显式传 `(-?[0-9]+)F`**——会让 `B1` 整层静默消失。**默认值仅供参考，换图先按 Step 1a 探查结果覆盖**。

**正则传参四坑**：① 一律写 `[0-9]` 不写 `\d`（2026-09-18 复盘落地）——Windows 命令行 / Git Bash 会吃掉 `\d` 的反斜杠，**零命中且脚本仍 rc=0**，凡 `--fx-pattern` / `--title-pattern` / `--hu-pattern` / `--bldg-pattern` 等一律写字符类（`FX[0-9]+#?`）；② **值以 `-` 开头会被 argparse 当选项**（报 `expected one argument`；`--opt=-值` 等号形式同样失效——2026-10-02 凤鸣朝阳实测）——负楼层正则写 `[-]?` 不写 `-?`（如 `([-]?[0-9]+)F`）；③ **捕获组只包数字**（2026-10-02 凤鸣朝阳实测）——`--hu-pattern` 写 `([0-9]+)户` 不写 `([0-9]+户)`（组含「户」曾致 `int('2户')` 崩；`floor_engine` 已加防御性数字提取，正确写法仍只捕数字）；④ **`--floor-pattern` 传则须含捕获组**（2026-10-02 凤鸣朝阳实测）——写 `([-]?[0-9]+)F` 不写 `[-]?[0-9]+F`（缺组曾致解析期 `m.group(1)` IndexError、崩点远离传参处；parse 参数自检已拦、启动即报正确形态）。判据：命中数为 0 时先怀疑正则被吃，**不得据零命中改判图纸无此元素**。

**脚本行为细则**（`apply-ruling` 批量落数 / 中间产物写保护 / `count-box --col-scale-map` / `inspect --fx-pattern` 产物自描述 / `ledger_elements.py` 元素台账 / 冷启动 vs 热启动 / pipeline 阶段顺序）—— 全文见 [pipeline_details.md](references/pipeline_details.md)。

**`--fx-map`/`--bldg-map` 双回填，仅限画像 present**：仅 `fx_overview_map=present`（确有真实集中总图对照表）时可用；absent/variant 不传不回填——分纤箱楼层/覆盖/户数**只允许来自四法**（直读、V型、区间法、竖线法）与多方标注互验，「编号 y 坐标关联推算」**禁止作为来源**（2026-09-18 裁决，pipeline 已拦截）。`--fx-map` 只补 null、不覆盖已测值、重号登记交人；`--bldg-map` 三边界：①对照表无该编号/重号/楼栋名不在锚点→保持原硬切留痕；②「楼栋」字段带单元后缀须前缀解析；③改派数据源必须是全图文字。不传而图确为对照表形态时 parse **逐栋 0 箱且 rc=0**（静默丢数）。**absent**：归属由方法池测定并逐箱写依据、交人工复核。

**对照表认领箱安装层取口径A（仅限 present）**：对照表有唯一映射且带非空安装层时取对照表值（标 `口径A:图上直写（总图对照表）`），区间法原值降级保留供审计。**口径共5个，输出原样标注**：`口径A:图上直写`、`口径A:图上直写（总图对照表）`、`口径B:区间法`、`口径A′`、`口径B′`（后两者见 pipeline_details.md §9）。

**必须解析**（判据与算法见 [measurement_methods.md](references/measurement_methods.md)、[coverage_rules.md](references/coverage_rules.md)）：FTTH 标注层文字 / 楼栋 / 单元 / 分纤箱编号及位置 / 安装楼层（**须标注口径 A/A′/B/B′**）/ 每层户数 / 覆盖范围（独立必做，三字段齐全）/ 必要连线 / 栋级入户规模 / 所有证据坐标。

**安装楼层与户数楼层归属必须同用区间法，禁止"最近楼层线法"**（取最近楼层线会越过带中点误判；细则见 [measurement_methods.md §3.5](references/measurement_methods.md)）。

**与对照表交叉校验**：比对编号/楼栋/单元/安装层四项。冲突时**口径A优先于口径B**（直读>推算）；任一方不得静默丢弃。**覆盖判定属解析阶段**：出表只组装不判定——换覆盖测量方式只改解析，出表不动。

> ⚠️ **两条硬约束（违反即判解析失败）**：**① 覆盖分界只能由竖干物理断口（或连线直读）确定** —— 严禁按安装楼层排序切分、严禁取箱附近全部竖干 min~max；**② 楼栋/单元归属必须以图纸自带的编号↔楼栋单元对照关系为准** —— 严禁用标题 x 区间硬切（系统图区常两行交错排布、按标题 x 中分**必然串行**）。**对法、实测反例与其余前置约束**（`--wire-layer` 图层来源统计等）见 [coverage_rules.md](references/coverage_rules.md) §零。

#### Step 1c: 户号生成

根据每层户数（DXF直读）生成户号。**完整规则见 [titleblock_and_intake_table.md §四](references/titleblock_and_intake_table.md)**，三条硬点：① 默认 `楼层×100+序号`；② **某层无户数标注即不生成户号**，列待确认项；③ 负楼层按 `B+楼层×100+序号`（B1层3户 → B101/B102/B103），**格式以模板为准**。`gen_addressbook.py` 已支持 B101/B102 与中文楼层名转换。

### Step 2: 自检

解析完成后进行内部交叉校验。**完整清单（26 条，含实测案例叙述）见 [step2_selfcheck.md](references/step2_selfcheck.md)**——出表前必须逐条过。

**三条硬门禁（任一 FAIL 不得出表）**

1. **一体化闭合核查**：先跑 `ftth.py inspect`，一次出齐 C1~C10（十项名与判据见 [step2_selfcheck.md](references/step2_selfcheck.md)）。清单内事项禁再写 `inspect_*.py`。
2. **计数守恒**：出表行数＝源户数之和；地址树恒等式见 **L1-C6**，不成立报错停止。
3. **矛盾即停**：任何不一致按 **L0-I4** 停下列待确认，禁静默择一。

**其余必查项（四条硬点；完整 26 条清单见 [step2_selfcheck.md](references/step2_selfcheck.md) —— 出表前必须逐条过）**

- **口径**：户数按 L1-C1 优先级取首个可用者（直读 → 图标 → 皮线；皮线先去重）；归属用区间法。
- **空集合不得判 PASS**：有效对象数=0 时只能判 `SKIP` 写明原因，不得判 PASS、不得把空集合合计写 `0`——否则「没取到数」看起来像「数就是 0」。未取到数须交接图标法（`count-box`）。
- **覆盖三字段+交叉**：逐箱三字段齐全；有真值表必跑verify反查；户数以逐层标注图为准（不读平面图）。

### Step 3: 提交用户校验

- 自检通过后生成总览表（Markdown）提交用户复核；用户用 DWG 原图与脚本输出 JSON 核对
- 包含：分纤箱总览表（编号/楼号/单元/安装楼层+口径标注）+ 楼层表（每层户数/皮线）+ 待确认项清单
- **待确认项必须包含**：所有 DXF 无法直接回答、且助手也无法通过已验证方法判定的问题（如竖线法与 V 型计算均失败的双箱覆盖分界、户级归属、未标注户数层等），以及自检中发现的所有矛盾
- **待确认清单统一格式**：见 **L1-C5**（四列）。
- **「已确认事项」防伪条款**：见 **L0-I3**（必须能引用本会话中用户的原话，否则一律列入待确认）
- 用户校验过的数据锁定为基准值，后续步骤只能新增不能覆盖；**落盘见 I6「落盘纪律」，「Agent 状态机 · 锁定基准」给出机械形态**

### Step 4: 生成标准地址表（成品）

**前置（三者齐备才允许生成 xlsx）**：Step 2 三条 hard gate 全 PASS、所有待确认项已获用户明确裁决并落盘、基准值已锁定（见「Agent 状态机」）；gen 另须 `--inspect` 闭合绑定（rc0＋指纹一致＋重扫无阻塞，缺一即 rc=2）。

- **每户一行**
- **地址结构**（9级）：前5级用户提供（省/市/区/街道/小区）；后4级助手填写（楼栋/单元/楼层/户）
- **户号**：按 Step 1c 规则生成，格式以模板为准；此处只核对生成结果与之一致
- **关联分纤箱编号**：每行标注该户所属分纤箱编号**＋（安装楼层）**（如`FX01#（5F）`，2026-09-28 用户裁决；覆盖与安装楼层均按解析判定值，细则见 addressbook_template.md）
- **双箱覆盖**：按解析阶段判定的覆盖范围分配各楼层用户到对应分纤箱（竖线法或 V 型计算结果；若为待确认项则等用户裁决后填写）
- 输出格式：xlsx，保存到桌面或用户指定位置（覆盖已存在文件时按 **L0-I6「交付纪律」** 先探测占用）

**实现方式**：`gen_addressbook.py` —— `--dxf-json` 解析 JSON、`--coverage-json` 裁决后覆盖 JSON、`--inspect` 闭合 JSON（必传）、`--template` 仅取表头列结构（**不复制示例数据**）、`--addr` 前5级地址（**留空须显式传空串**，省略会回退读模板示例值）。生成后**回读校验**（**L1-C6**）。完整参数与可抄示例见 [scripts_reference.md](references/scripts_reference.md)。

**多楼栋合并**：逐栋解析→`merge_json`合并→gen；全楼合计户数先`split_units`拆分（用户确认规则）。

**九级树**：用`gen_9level`（不用gen_addressbook）；`--header-xlsx`必需（表头取定稿表）；恒等式见L1-C6；单元数>1同配置展开须核对。

## 参考文件

> **维护原则（唯一权威定义）**：同一条规则**只设一个权威定义**，其他位置**只引用、不复制全文**；两处不一致时**以更新日期较新者为准并向用户回报**。
> **体量纪律（闸门 `ftth.py budget` / `scripts/check_budget.py`）**：本文件是每次会话**首屏全量加载**的唯一文件，工具输出有**通用截断（实测 51,200 B，无开关）**。**预警线 47,000 B（触及即新增默认进 `references/`）／硬上限 49,000 B（触及即禁写，先外移再新增）**；**`references/` 单文件同受 47,000 B 约束**。**净增为零**：每加一条须同时外移等量。修订记录 / 案例叙述 / 参数表写 `SKILL_CHANGELOG.md` 或 `references/`。阈值依据与拆分层级见 [pipeline_details.md §15](references/pipeline_details.md)；改前改后各跑 `ftth.py budget`。

| 参考文件 | 内容 |
|---|---|
| [measurement_architecture.md](references/measurement_architecture.md) | 架构完整版：方法池详表 / 铁律全文 / 算法细节 / 标准流程详解 / 分带与箱位锚门禁 |
| [probe_checklist.md](references/probe_checklist.md) | Step 1a 探查清单完整版（全子项与判据） |
| [scripts_reference.md](references/scripts_reference.md) | 脚本参数表 / 统一入口机制 / 画像信号 / 调用契约细则 / `geom.json` schema / 元素台账字段 |
| [step2_selfcheck.md](references/step2_selfcheck.md) | Step 2 自检完整清单（26 条，含实测案例） |
| [measurement_methods.md](references/measurement_methods.md) | 信号驱动选法 / 图纸类型参考 / manifest 规范 / handoff 字段级定义 / 总图判据实测背景 |
| [titleblock_and_intake_table.md](references/titleblock_and_intake_table.md) | 图签形态三来源协议 + 九级地址树出表 |
| [coverage_rules.md](references/coverage_rules.md) | 覆盖范围判定规则（竖线法 / V型 / 待确认）+ 两条硬约束全文 |
| [visual_model_lessons.md](references/visual_model_lessons.md) | 降级兜底规范与踩坑教训 |
| [addressbook_template.md](references/addressbook_template.md) | 模板 24 列对照表 |
| [pipeline_details.md](references/pipeline_details.md) | 流水线串跑入口 / Step 1b 细则：脚本行为 / 参数细节 / 口径A 与回填实现 / `geom.json` schema 三坑 / 体量阈值依据 |
| [operations_discipline.md](references/operations_discipline.md) | 会话效率实测 / 断流处置 / 矛盾分级 / 三本台账 / **契约落地与当前态**（§九·补）/ **权威矩阵** |
| [dxf_parsing_benchmark.md](references/dxf_parsing_benchmark.md) | GitHub DXF 解析生态对标调研：8 项可借鉴改进候选（待用户裁决、未实施）+ 6 项明确不借鉴 |

## 版本修订记录
> 本文档不再保留条目正文；**完整修订记录见 [SKILL_CHANGELOG.md](SKILL_CHANGELOG.md)**。
