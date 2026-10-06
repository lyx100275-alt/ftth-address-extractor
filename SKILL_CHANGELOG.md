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
> 编号分叉说明（2026-10-06 一百六十一立）：**156/157/158 各有两条同名异文条目**——顶部三条（SKILL.md 精简 / 五轮迭代待裁决 / R2 缺陷）为审计修复轨，尾部五条（156 三处 P0 / 157 迭代第 4 轮 / 158 迭代第 5 轮 / 159 补登 / 160 y 坐标边界）为版本递进轨（0.155→0.160）。引用时以“标题+日期”区分，不得只报序号；新条目自**一百六十一**续排，不复用旧号。历史不再改写（改写即破坏既有引用）。

### 2026-10-06（一百六十一）：外部审计修复批 —— 文档漂移三处 + 门禁补三项 + 缓存外迁 + SKIP 可见

**动因**：外部深度审计指出三处已发生的文档漂移（README 子命令 16/19、scripts_reference 脚本 42/43 与子命令 16/19、README 版本号落后 13 个修订）而门禁全绿，另有 CHANGELOG 156~158 编号重名、技能目录 `__pycache__` 回潮、T14/T5 缺料 SKIP 与 PASS 不可区分。

| # | 改动 | 文件 |
|---|---|---|
| ① | README：子命令数 16→19 两处、版本号 0.147.0→0.161.0、`check_docs` 门禁范围 D1~D12→D1~D13、缓存位置说明改系统临时目录、T5 缺料补 `FTTH_REQUIRE_CORPUS=1` 说明 | `README.md` |
| ② | scripts_reference：脚本数 42→43、子命令 16→19（含 new-run/summary/verify-answer 全表）、易错点补 signals.json `\d` 示例改写 `[0-9]` 警告 | `references/scripts_reference.md` |
| ③ | D1 扩到 README + scripts_reference 三处对拍（D1b/D1c）；D8 扩到 scripts_reference 脚本数（m8c）；新增 **D13 版本号三处一致**（version.json skill_version 须同时现身 README 与 CHANGELOG） | `scripts/check_docs.py` |
| ④ | version_basis 补分叉说明；skill_version 0.160.0 → **0.161.0** | `version.json` |
| ⑤ | 启动器缓存改写系统临时目录（`FTTH_CACHE_DIR` 可改；旧 `scripts/.interpreter_cache.json` 自动迁移沿用一次），派生子进程置 `PYTHONDONTWRITEBYTECODE=1` 不写 `__pycache__`，技能目录不再新增运行时写入项；删残留 `__pycache__` + 旧缓存 | `scripts/ftth_launcher.py`、技能目录 |
| ⑥ | 冒烟 SKIP 可见性：模块级 `print` 包装计数全部 `[SKIP]` 行，结尾汇总打印 SKIP 清单；`FTTH_REQUIRE_CORPUS=1` 时 T5/T14 缺料 SKIP 转 FAIL（含 T4b 文档一致性门） | `tests/run_smoke.py` |
| ⑦ | 本文件头加编号分叉说明；本条置顶（新号 161，不复用旧号） | `SKILL_CHANGELOG.md` |

**验证**：`budget` rc=0；`check_docs` D1~D13 ALL PASS（含新增 D1b/D1c/D13）；`check_contract_coverage` rc=0；`py_compile` 全仓 0 错；`run_smoke`（无语料机）ALL PASS 且结尾打印 SKIP 清单。

**遗留**：ftth.py 依赖矩阵表仍只列 15 行（new-run/summary/verify-answer/budget/transitions 未入矩阵，另立项）；Step2-C9 与 L1-C9 同名双轴维持现状（改名前缀属 breaking，待裁决）。

- **版本**：`version.json` 0.160.0 → **0.161.0**。

### 2026-10-05（一百五十八）：SKILL.md 精简 −2,177 B（−5.1%，零语义损失）+ 多地块扇出「未判定带」点名

**动因**：用户指示「精炼提示词，语义准确，字数最少」，随后试跑三个项目。

**① SKILL.md 精简（42,637 → 40,460 B，−2,177 B / −5.1%）**

- 口径：**只改表达、不改规则语义**（沿用一百四十三确立的精简原则）。删除的三类内容全是**重复论述**，其权威定义在 `references/` 已存在：
  - **正则四坑的原理段**（`\d` 被 shell 吃掉、缺组 IndexError 的来龙去脉）—— 权威副本在 `pipeline_details.md §3`，SKILL 只留四条可执行规则 + 零命中判据；
  - **两条硬约束的实测反例铺垫** —— 权威副本在 `coverage_rules.md §0.2`，SKILL 只留约束本体 + 指针；
  - **栋级三来源的细则枚举**（来源角色 / 几何关系 / 地块分段 / `--patch` / 键名与执行序 / 待确认项模板）—— 已逐项核实存在于 `titleblock_and_intake_table.md`（§2.2 地块分段、§六 待确认项模板、`--patch` 与执行序段），故 SKILL 只留三来源角色 + 逐栋比对 + 禁止自动择一 + rc=3 处置。
- 同时按本技能「维护原则」修**一处自身违规**：同一规则在 SKILL.md 内重复三处（回读校验 C6/状态机/Step 4、落盘纪律 I6/状态机/Step 3、户数口径 C1/测量架构）已收敛为「一处定义 + 其余引用」。
- **未动**：全部 L0-I1~I6、L1-C1~C9（各条正文与表格）、状态机图与 10 个节点名、禁止迁移 6 条、八项模型、方法池 4 种、户数三口径、铁律 9 条、工作流 Step 0~4 的硬门禁 —— 逐条核对无删减。
- 门禁影响核查（**先读判据再改，防破坏机检**）：`check_docs.py` 的 D1（19 子命令）/D2（11 阶段）/D6（`pipeline_details.md`+16）/D8（`（43 个文件）`）/D10（L1 C1~C9 标题集）/D11（状态机 10 节点名逐字）/D12（迁移表最大编号 6）均为正则硬编码 token，精简时逐条原样保留；**D1~D12 ALL PASS**。

**② 缺陷：多地块扇出把「未判定带」折进一个退出码（试跑柳辛庄 5-9 揪出）**

- 病灶（可复现）：柳辛庄 5-9 地块 band5 的 `coverage`（竖线法）**配对率 0** → rc=2 中止 → 该带**没出 inspect.json**；而扇出汇总只打一行「多地块扇出汇总：4 个带，最严重退出码 2」。该带 parse 已出 **5 栋 / 10 单元 / 20 箱 / 4 项待裁决**（真实 FTTH 内容），即**20 箱覆盖未判定、4 项待裁决从未进入任何报告**，人必须逐个翻目录才发现。违反 L0「不静默丢数」与 Step 2「空集合不得判 PASS」—— 未判定被折进退出码，形态上等同判过。
- 改动：`ftth.py _pipe_fanout_bands` 逐带记 `(带名, rc, inspect.json 路径)`，汇总后**逐带点名**并区分「已出 inspect」/「**未出 inspect —— 该带内容未判定**（不是通过）」，另加一行 `⚠ N 个带未判定（…）—— 整图不得出表`。退出码语义不变（仍取最严重者），**只补观测**、不改判定。
- 验证（还原证明）：同一 5-9 地块复跑，新汇总输出 `band5块地：rc=2，**未出 inspect.json —— 该带内容未判定**` + `⚠ 1 个带未判定（band5块地）`，另三带显示「已出 inspect.json」；1-4 地块四带全部已出 inspect（无未判定）。
- **band5 本身不是 bug**：竖线法配对率 0 属 L1-C2 `rc=2`（输入不足→停），脚本已给出既定处置（显式 `--fx-symbol-layer`，或确认图上确无箱符号后加 `--allow-low-pairing`）。按 L0-I4 交人裁决，**不自动改选法**。

**三项目试跑结果（精简 + 修复后）**：凤鸣朝阳 rc=0（C6/C9/C10 全 PASS，313 户 / 17 箱）；云峰 rc=2（F=5 / W=12，与上轮逐字一致，全为 C9 pending 待人裁决）；柳辛庄 1-4 各带 rc=0/2/2/2（band1 rc=0，余为合法 pending）；柳辛庄 5-9 各带 rc=2（band8 F=5、band9-1 F=8、band9-2 F=24，均为合法 pending）+ **band5 未判定（已点名）**。

**验证**：`py_compile` 全仓 0 错；`check_docs` D1~D12 ALL PASS；`check_contract_coverage` rc=0（9/9 enforced）；`budget` rc=0（SKILL.md 40,460 B，距预警线 6,540 B）；`run_smoke` **ALL PASS**（含 T14 三图 golden 对拍一致、T23b 路径字段、T18 冲突矩阵）。

**版本**：`version.json` 保持 **0.155.0**（一百五十六起 minor 位落后于修订序号，待用户裁决「minor＝序号」口径后统一追平，本轮不单独 bump）。

---

### 2026-10-05（一百五十七）：桌面三项目五轮迭代 —— 待裁决说明陈旧变量 + 分带退出码违 C2 + yf 基线过期重生

**动因**：用户指示「跑桌面三个项目（凤鸣朝阳 / 云峰 / 柳辛庄）→ 发现问题立即修复 → 迭代 5 轮」。R1 四图全链（凤鸣朝阳 rc=0；云峰 rc=2；柳辛庄 1-4/5-9 各 4 带 rc=2 —— 后三者均为合法 pending 待人裁决，非 bug），跨产物对拍揪出两项可修缺陷，R2 落地，R3 冒烟回归揪出 T14 基线过期，R4 取证定性后重生基线，R5 终验全绿。

**① D1 —— 覆盖完整性待裁决「说明」两字段双空（陈旧循环变量）**

- 病灶（可复现）：柳辛庄 band3 三条「覆盖范围缺失楼层」事项列对了缺失楼层，说明却写「覆盖并集 ；户数标注楼层 。」—— 双空。根因：`analyze_coverage_vshape.py` 自检段把户数期望只存局部变量 `_hu_expected`，后文循环只能见到元组内字段，说明处的户数楼层取到**外层循环最后一个单元的值**（该单元无户数标注即空集）；覆盖并集空时 `'/'.join([])` 得空串。C5 四列要求「图纸已知事实」准确 —— 空说明把正确解的证据弄丢了。
- 改动：`_cov_missing` 元组增第 5 项户数标注楼层（随条目携带）；新增 `_fmt_floors`（空集显式写「无」，非空沿用原 12/8 截断口径）。band3 重跑验证：说明变为「覆盖并集 无；户数标注楼层 1F/2F/…/15F」。
- 影响面：凤鸣朝阳 / 云峰零此类条目（grep 实证），golden 指纹不受影响。

**② D2 —— 单地块图分带退出码违 L1-C2（rc=2 当 rc=3 用）**

- 病灶：`split_bands.py --auto` 在 0 锚点 / 1 锚点（单地块、无需分带）时打 `[ERROR]` + `sys.exit(2)`；而 `ftth.py` pipeline 接到非零即按单地块原路径继续。按 L1-C2：rc=2 = 输入不足→停（禁出表），rc=3 = 不适用→跳过降级 —— 「无需分带」是典型不适用，却占着「须停」的码，继续走即违反门禁语义（凤鸣朝阳 / 云峰每轮必经此分支）。
- 改动：`split_bands.py` 对「无需分带 / 未提取到任何分带锚点」两种 err 改 `[INFO]` + `sys.exit(3)`（坏窗口 / 空带仍 rc=2）；`ftth.py _pipe_fanout_bands` 区分处理（rc=3 报单地块继续，rc≠0 原样告警）。行为不变（均回单地块路径），语义合规。凤鸣朝阳重跑验证：新提示 + inspect 仍 rc=0（FAIL 0/WARN 3 不变）。

**③ D3 —— T14 yf 基线过期（会话前已红，非本轮引入）**

- 现象：R3 全量冒烟唯一 FAIL：`yf parsed.json md5 5800bc…≠d776…；yf inspect（rc=2 F=5 W=12 / 基线 rc=2 F=5 W=11）`，其余全绿。
- 取证（逐条排除，非推断）：① 会话前系统 temp 留存三份 `ftth_golden_*`（10:54/11:10/13:28），yf parsed 三份 md5 **逐位一致**（5800bc）—— 会话前已红，本轮改动无辜；② 种子对照（PYTHONHASHSEED=0/1/unset 三跑）parsed 逐位一致 —— 非哈希序抖动；③ 业务口径对照（fresh-T14 vs 桌面 Round1）：11 栋 / 15 单元 / 23 箱 / coverage 23 条目 5 pending **全一致**，count_box 331 户与基线一致，5 条 FAIL 与基线同为 C9 pending（合法待人裁决）—— 门禁语义与业务数据无回归；④ `.backup` 全量哈希对拍：11:06 同步未改任何脚本（仅本轮 3 文件不同）—— 红在 0.155.0 基线之后、156 未同步重生基线。
- 处置：按既定程序 `--regen-golden` 重生基线（仅 yf parsed + warns 两项变，fmcy/lxz14 逐位不动）；R5 全量冒烟 **ALL PASS**（T14 三图一致、T17/T17b/T23a 随之转绿）。

**验证**：`py_compile` 全仓 0 错；`check_docs` D1~D12 ALL PASS；`check_contract_coverage` rc=0（9/9 enforced，无契约变更）；`budget` rc=0；`run_smoke` ALL PASS；`run_conflict_matrix` ALL PASS。

**版本**：`version.json` 保持 **0.155.0**（与一百五十六同批原则：minor 落后待用户裁决口径后统一追平，不另 bump）。

---

### 2026-10-04（一百五十六）：R2 缺陷三项 —— 超阈箱锚「剔除即阻塞」过宽 + 层数回退被单点污染 + 损失登记冒充闸门

**动因**：r02 全量重跑（F1/F2/F3 落地后）跨产物体检 + 逐项追成因。D1 已清零（全产物 重复=0 / 冲突=0），但柳辛庄分带图仍停在 inspect rc=2，逐条追根后揪出三项。

**① D2 —— 超邻域箱锚「剔除即阻塞」在一窗多栋图上整窗误拦**

- 病灶：`analyze_coverage_vshape.py` 对超出 `--box-anchor-x-factor` 的箱位锚一律「剔除归属 + 阻塞报人」。实测 band1 被剔除两锚折合字高 **40.73× / 47.14×**，正落在本技能 P0-9 注释所载「箱表区 40~59×字高」带（真锚实测 4.9~5.8×、邻楼锚 34×）⇒ 几何上不可能属本窗。但该待裁决项**对象是整窗标题**，一窗多栋时窗内全部成员楼栋一并 pending（band1 12 箱 / band9-1 16 箱 pending 同源于这一条）。
- 改动：新增模块常量 `ANCHOR_FOREIGN_FACTOR = 30.0`（依据：距真锚实测上限 5.2 倍外、落在邻楼/箱表带同侧）。超阈锚再分两档：灰区（<30×）维持阻塞；明确外来（≥30×）判 `阻塞: False` **登记不阻塞**，说明里写明折合字高与判据。
- 验证：band1 pending 箱 12 → **0**。

**② D3 —— C10「层数」回退通道被单点户数污染**

- 病灶：`inspect_closure.py` C10 系统图侧层数原为**全有全无**判据 —— 「任一层有户数 ⇒ 取『有户数的层数』；**全部**无户数才回退『地上刻度行数』」。实测柳辛庄 band1：4#/5#楼 楼层表 19 行（1F~18F+B1F），但**只有 12F 一行带户数**（其余 null）⇒ 层数=1 ⇒ 与图签 18 直接矛盾 ⇒ C10 假 FAIL，把已定案的整图拦在出表前（实测「2 处不一致 / 共同楼栋 5」）。「有 1 行户数」≠「只有 1 层」—— 回退通道不该被**单点**污染关闭。
- 改动：层数取 `max(有户数的层数, 地上刻度行数)`。户数口径本身不动（仍是契约三口径之一），只修「层数」这个派生计数。
- 验证：**对既有图是 no-op**（凤鸣朝阳 / 云峰 逐栋实测 `vals==alt` 恒成立），故 golden 不受影响；band1 C10 由 FAIL → 通过，整图 inspect rc=2 → **rc=0**（可出表）。

**③ D4 —— 跨阶段损失登记冒充闸门（机械上拦不住任何对象）**

- 病灶：`对象 = '（整图跨阶段对账）'` 这类**图级标签**经 `parse_ruling_scope` 取不到楼栋/单元/箱段 ⇒ `judge_pending_scope` 恒不命中 ⇒ 该条**机械作用为零**；而缺失的箱在 coverage 里本无条目，也没有可标 pending 的载体。照旧隐含「阻塞」即「读起来是闸门、实际不拦」。
- 改动：显式 `阻塞: False`，并在事项/说明里写明**执法者是 inspect C3「安装楼层双源交叉」**（实测 band4：`C3 FL04FX10 coverage 无记录` → rc=2），避免双闸矛盾与误读。
- 边界：本项**不是**把损失放行 —— 损失仍被 C3 FAIL 拦下，只是不再由 C9 侧重复声明（同 §一百零一 C6/C9 分工）。

**验证**：全量冒烟 / 冲突矩阵 / 文档一致性 / 契约登记 / 预算自检全绿；三图 fresh 重跑（r03）见同轮报告。

**版本**：`version.json` 保持 **0.155.0**（本条与一百五十五 同批，不另 bump）。

---

### 2026-10-04（一百五十五）：R1 缺陷 D1 —— 共享窗证据副本重复计状态、跨节点互斥

**动因**：桌面三图（凤鸣朝阳 / 云峰 / 柳辛庄）fresh 首轮（r01）跨产物体检。柳辛庄 1-4 / 5-9 两地块**分带子图**暴露：`[共享]N-M号楼综合布线系统图` 窗节点自身产出的箱记录，与「共享组逐楼栋展开」到成员楼栋条目的**同号箱并存**，两处**都带** result_origin / result_confirmation，且状态可能互斥 —— 窗节点按**整窗**作用域判 pending、成员楼栋按**本栋**判 settled。

**实测（可复现）**：`柳辛庄1-4地块` band1 的 coverage.json：箱行 24（含 12 份源窗副本）、唯一编号 12，逐编号均为「1 份源窗 + 1 份成员楼栋」；其中 8 个编号两侧状态互斥（源窗 pending vs 成员 settled）。后果两条，方向相反：

- ① **幽灵 pending**：C9 主闸扫到源窗那份 pending ⇒ 整链 rc=2 不得出表，而成员楼栋侧本已 settled —— 属**判据用错范围把正确解整批拦下**；
- ② **反向假绿**：`apply_ruling._settle_boxes` 按 `bldg_num` 近似匹配（`bldg_num('[共享]1-3号楼…')==1==bldg_num('1#楼')`），裁决 `1#楼` 会连带改写源窗副本，把已降级副本**重新写回 settled**，状态再次分裂。

**根因（两处，同源）**：产物侧 —— 源窗副本不该带结果状态字段（同一物理箱被计两次）；判据侧 —— `judge_pending_scope` 楼栋段旧口径取「首个楼号」（`[共享]1-3号楼…` → 1 ⇒ 只命中 `1#楼`），同源证据被按楼号任意切分。

**改动**：

1. `scripts/analyze_coverage_vshape.py` / `scripts/analyze_coverage.py`（对称）：先扫出「确已展开到成员楼栋」的副本集合（成员条目带 `来源共享窗` == 窗键），对这几份**去掉** result_origin / result_confirmation、改挂 `副本归属` 指针；**未展开**的窗节点照旧带字段（此时它是唯一载体，降级即丢解）。降级数落进 `结果状态说明.共享窗证据副本（不计入统计）`，不静默。
2. `scripts/ftth_common.py`：新增 `is_shared_title`（走 `parse_bldg_nums_ex`，>1 楼号即真）与 `ruling_bldg_matches(scope_bldg, bldg_key, src_window)` 三级判据（① 字符串相同 ② 同源共享窗 ③ 同楼号**仅当**作用域非共享标题）；`judge_pending_scope` 增 `src_window` 形参并委托给 `ruling_bldg_matches`（消除「取首个楼号」的任意口径）。
3. `scripts/apply_ruling.py::_settle_boxes`：整体跳过共享标题楼栋、不回写已降级副本，楼栋段匹配改走 `ruling_bldg_matches`（修 ②）。
4. `scripts/inspect_closure.py`：C9 **追加检查项**「共享窗证据副本降级」—— 源节点副本与成员侧同号箱并存且仍带状态字段即 FAIL（逐箱列出，议题入机读出口）；无共享窗时不产检查行（不冒充已核）。使该类缺陷由技能**自身**拦下，而非靠外部体检发现。

**验证（还原证明）**：同一 band1 产物，C9 追加项修复前判 **FAIL 12 项**、修复后 **PASS 0 项**；无共享窗的凤鸣朝阳不产该项（不适用）。全量冒烟 / 冲突矩阵 / 文档一致性 / 契约登记 / 预算自检全绿（见同轮报告）。

**边界声明**：本项只降级「确已展开到成员楼栋」的副本；**未展开**窗节点不降级、不判 FAIL。不自动裁定副本与成员谁对谁错（L0-I4）。

**版本**：`version.json` 0.150.0 → **0.155.0**。说明：version.json 自带口径为「minor 位＝SKILL_CHANGELOG 修订序号」，本轮一次性追平（一百五十一～一百五十四 未 bump；本条对齐至当前序号 155）。若用户否决该口径，改回即可。

---

### 2026-10-04（一百五十四）：轮次实测两项 —— 从零纪律首步失效 + 分带子图跨轮不可复现

**动因**：桌面三图（凤鸣朝阳 / 云峰 / 柳辛庄）fresh 全链轮次复跑 + **跨轮逐产物对拍**（口径同 一百四十九 / 一百五十 的 R1/R2/R3），实测两处缺陷。

**① `new-run` 空目录不可用（「从零纪律」首步在全新项目上失效）**

- 病灶（可复现）：`ftth.py new-run --project-dir <不存在目录>` 打印「项目目录不存在」并 `return 1` —— **不建目录、不落台账**；而同一目录随后由 `pipeline --outdir` 自动创建，**两条入口行为不一致**。一百五十一落地 `new-run` 时目录已存在（凤鸣朝阳靠 Agent 手工归档 40 项），故该分支未被覆盖。机械后果：空目录上 `transitions --project-dir` 判 rc=3「三本台账均不存在，无可核对象」，全链无机器证据。
- 改动：`scripts/ftth.py` `cmd_new_run` 把「目录不存在 → `return 1`」改为 `mkdir(parents=True, exist_ok=True)` + 打印「已创建」，随后照常走 `ledger_state.py init`。空目录本无历史可归档，语义与「已存在但干净」对齐。
- 验证（还原证明）：修复前 rc=1、目录未建、0 台账；修复后同一命令 rc=0、目录已建、三本台账落盘，且 `transitions` 由 rc=3「无可核对象」转 **rc=0「[通过] 6 条禁止迁移均未发生」**。

**② 分带子 DXF 跨轮不可逐位复现（复现基准被中间产物污染）**

- 病灶（可复现）：**同一输入连跑两次**，`split-band` 产出的 1-4 地块 4 个 band 与 5-9 地块 4 个 band **全部**逐位不同（8/8）。跨轮对拍（r02 vs r03）中表现为子图 `geom.json` 的源 `mtime`/`size` 与 inspect 的 `geom` 指纹漂移；文件大小在 580660 / 580662 间抖动。
- 根因（**两个，缺一不可**，逐个实验锁定）：
  - **a) ezdxf 存盘写「当前时间/随机值」**：`$TDCREATE` / `$TDUPDATE`（`juliandate(now)`）、`$FINGERPRINTGUID` / `$VERSIONGUID`（随机 GUID）、以及 `CREATED_BY_EZDXF` / `WRITTEN_BY_EZDXF` 两个 `DICTIONARYVAR` 里的 `1.4.4 @ <UTC now>` 标记串。（差异簇共 6 处，修 a 后由 6 簇降为 1 簇、大小抖动消失。）
  - **b) CLASSES 段两条 CLASS 顺序互换**（`LAYOUT` ↔ `ACDBPLACEHOLDER`，132 B）：ezdxf 收集「本次用到的类」经 set/dict 迭代，顺序随 `PYTHONHASHSEED` 变化。同实验组加 `PYTHONHASHSEED=0` 后**逐位一致**。
  - **取证教训**：a 的三处起初被「就近取 `$VAR`」的启发式误标成 `$SHADOWPLANELOCATION` —— 该字段只是最近的上游变量名，**归纳变量名不等于看内容**；打印真实字节片段后才看清是 ezdxf 标记串。定位不到真因时先看内容，别停在最近的标签上。
- 改动：① `scripts/split_bands.py` 建 doc **之前**置 `ezdxf.options.write_fixed_meta_data_for_testing = True`（`_update_metadata()` 只在 `ezdxf.new()` 时调用，故必须前置），整轮分带跑完还原原值；② `scripts/ftth_launcher.py` 派生**子进程**前 `env.setdefault("PYTHONHASHSEED", "0")` —— 哈希种子只在解释器启动时读取，运行期改无效，启动器（L1-C7 唯一入口）是唯一可行点；用 `setdefault` 尊重用户显式设置；③ `scripts/split_bands.py` 存盘后把子图 mtime 定为**源图 mtime**（`os.utime(out, (src_mtime, src_mtime))`）—— 否则每轮重生成的 mtime 必变，经 `<子图>.geom.json` 的 `mtime` 字段传导到 inspect 的 `inputs_sha256.geom`，多地块图纸**永远**做不到跨轮逐位对拍。继承源图 mtime 另有第二重正确性：源图更新则子图 mtime 随之更新，`load_dxf` 的 pkl 缓存与 `--reuse-geom` 失效判定依然准确。失败只 WARN 不阻塞。
- 验证：修 ① 后大小抖动消失（580626 稳定）但仍有 1 簇；修 ①+② 后 **8/8 逐位一致**（同 shell、未设外部 `PYTHONHASHSEED`）；再修 ③ 后子图 mtime == 源图 mtime，`<子图>.geom.json` 与另一轮**仅差源路径回显一行**（去目录名后逐位一致）。
- 边界声明：`geom.json` 的 `dxf` 路径回显、`inspect.json` 的输入路径回显属**溯源必需**（一百五十 已定：`inspect.json` 刻意排除在复现基准外）；除此之外分带链已无不确定项。
- 附带观察（**未改动**，列为可选优化）：成品 xlsx 跨轮**单元格级 0 差异**（316 行全同），字节不同只因 zip 容器各条目时间戳与 `docProps/core.xml` 的 `dcterms:created/modified`（openpyxl 写入生成时刻）；如需 xlsx 字节级可复现，可固定 `wb.properties.created/modified`，属新增需求，未经裁决不做。

**版本**：`version.json` 保持 **0.150.0**。说明：一百五十一～一百五十三 三条修订均未 bump（version.json 自一百五十 起未动），本条沿用现状不单独 bump。**该口径漂移（minor 位＝修订序号，当前已落后 3 个序号）建议一并裁决**。

---

### 2026-10-04（一百五十三）：P2 审视落地 —— 四项防误读/防噪音/命名统一

**动因**：P0+P1 完成后用户裁决「剩余的继续优化」。P2 四项为低频但防误导/防复发噪音类（审视报告 A3/E3/E9/E10）。

**A3 — C10 PASS 加 C8 偏离交叉引用**
- 病灶：C10 用标准层口径（多数层户数）逐栋比对判 PASS，C8 抓层间偏离（如 1#楼 1F=1户 vs 标准层 2户）判 WARN。两者并存时 PASS 可被误读为「图签确认了所有层户数」，实际 C10 不覆盖 C8 的偏离维度——矛盾靠 Agent 敏锐度去拼。
- 改动：`inspect_closure.py` C10 PASS 分支加注「标准层口径」+ 若 `c8_bad` 非空追加 C8 偏离明细（栋/单元+偏离层），让矛盾自动浮出。

**E3 — fx_location_annotation absent 分支提示**
- 病灶：`fx_location_annotation` 在 probe 有值、画像只对 present 打提示（「建议跑 extract_fx_locations.py」），absent 无任何输出 → Agent 只看到 present 提示，不知 absent 时该跳过，白白跑一轮 rc=2。
- 改动：`plan_methods.py` 新增 absent 分支 `log.info("箱位直读标注信号 absent → 跳过 extract_fx_locations.py（coverage-vshape 不传 --fx-locations 即可）")`。

**E9 — probe INSERT 样例按 FTTH 相关性过滤**
- 病灶：probe stdout 打印大量非 FTTH INSERT 块（LEB/MEB/暖通/电气设备），挤占截断窗口，FTTH 相关块被推出可见范围。
- 改动：`parse_dxf_structured.py` INSERT 块明细（ATTDEF+ATTRIB）按 FTTH 关键词（FX/分纤箱/皮线/光缆/ONU/通信/光纤/弱电/配线/光交/接头/熔接/telecom/fiber/optic/cable）过滤；统计行仍打印全部块名+数量（探查不丢信息），只过滤明细。非 FTTH 块明细省略数汇总一行。

**E10 — probe.json 字段命名统一**
- 病灶：probe.json 字段命名中英混合——`suggested_params` 英文 / 「全量文字样例」中文。Agent 取 `text_samples` 踩空（本次实测 2 轮）。
- 改动：`parse_dxf_structured.py` 写出时新增英文键 `text_samples`（与旧中文键「全量文字样例」并存兼容）；`plan_methods.py` 消费方 `load_texts_from_probe` 优先读 `text_samples`、回退旧键。不破坏任何现有消费方。

**测试**：全量冒烟 **ALL PASS（失败 0 项）**；T14 golden 无需重建（probe.json 不在指纹集内，parsed/coverage 内容不变）。budget OK（SKILL.md 42637 B 不变，无新增 SKILL.md 内容）。

**凤鸣朝阳实跑验证**：
- A3：inspect C10 PASS 信息含「标准层口径」+「C8 检出 1 个单元层间户数偏离 → 1#楼/1单元，须人工确认不因 C10 PASS 而豁免」。
- E3：plan 输出「箱位直读标注信号 absent → 跳过 extract_fx_locations.py」。
- E9：INSERT 块统计打印全部块名+数量，ATTDEF 明细省略 9 个非 FTTH 块，ATTRIB 样例 0 个 FTTH 相关。
- E10：probe.json 同时含 `text_samples`（1530 条）和 `全量文字样例`，plan 读新键成功。

---

### 2026-10-04（一百五十二）：P1 审视落地 —— 六项接口摩擦消除

**动因**：P0 完成后用户裁决「继续修改 P1」。P1 六项均为手动分步模式下每次跑项目都会遇到的接口摩擦（审视报告 E1/E2/E4/E5/E6/E7）。

**E1 — plan --project-dir 自动推断**
- 病灶：plan 手动直调漏传 `--project-dir` → `intake_table=unknown` 阻塞（三次实测复发：云峰、凤鸣朝阳历史、本次）。pipeline 已透传，直调无默认。
- 改动：`ftth.py` H3.5 段——plan 且 `--project-dir` 未传且 `--dxf` 有值时，从 `--dxf` 父目录自动推断，打印 `[param] --project-dir 未传，由 --dxf 路径推断 = …`。
- 附带：`plan_methods.py` intake_table evidence 路径做 basename 归一（与一百五十同源，T23a 拦住后修）。

**E2 — read_titleblock --floor-layer auto**
- 病灶：`--floor-layer` 必传 required=True，probe 已给出 `titleblock_layer_candidates` 候选却断链——手动直调漏传即 usage rc=2 浪费一轮。
- 改动：`read_titleblock_households.py` 新增 `--config <probe.json>` 参数；`--floor-layer auto` 时从 probe.json 的 `titleblock_layer_candidates.候选图层[0]` 自动读取，打印 `[param] --floor-layer auto → 从 probe.json 取图签候选图层: …`。

**E4 — ftth.py summary 子命令**
- 病灶：每次跑完 parse 手写汇总脚本才能看到楼栋×单元×户数×箱，浪费一轮且口径可能不一致。
- 改动：`ftth.py` 新增 `summary --parse <parsed.json> [--coverage <coverage.json>]`，内联打印总览表（Step 3 提交材料半成品），可选合并覆盖楼层列。无子脚本依赖。

**E5 — ftth.py verify-answer 子命令**
- 病灶：跑完必核对是用户固定工作流收尾步骤，每次手写对拍脚本，口径可能不一致（口径不一致本身就是准确性风险）。
- 改动：`ftth.py` 新增 `verify-answer --new <成品.xlsx> --answer <参考.xlsx>`，openpyxl 逐行对比 H/J/L/N/P 五列，打印差异行 + 每栋汇总，按「楼栋列非空」过滤水印行。rc=0 无差异 / rc=1 有差异。无子脚本依赖。

**E6 — ledger ruling-add --from-json 报错附样例**
- 病灶：`--from-json` 格式无文档、报错不带样例——本次试错 3 轮（中文键名→对象包装→数组才过）。
- 改动：`ledger_state.py` 两处报错（非数组、缺 question/ruling）均附期望格式样例与键名提示。

**E7 — gen_addressbook --addr-empty 开关**
- 病灶：文档说「留空显式传空串」，PowerShell 宿主传 `--addr ""` 空串被吃 rc=2（本次一轮浪费）。
- 改动：`gen_addressbook.py` 新增 `--addr-empty` 无值开关（store_true），为 True 时 `--addr` 视为空串。与 `--addr` 同时出现时 `--addr-empty` 优先。绕过 PowerShell 空串传参被吃的坑。

**SKILL.md 登记**：子命令清单 17→19 并加 `summary`/`verify-answer`。

**测试**：T2 断言 17→19；golden 基线经 `--regen-golden` 重建（三图全对拍一致）；全量冒烟 **ALL PASS（失败 0 项）**。

**凤鸣朝阳实跑验证（六项逐项）**：
- E1：plan 不传 `--project-dir` → 自动推断桌面凤鸣朝阳目录 → intake_table=absent、门禁 PASS、evidence 无路径泄漏。
- E2：`--floor-layer auto --config probe.json` → 自动取 BZ → rc=0（汇总正确）。
- E4：`summary --parse parsed.json --coverage coverage_vshape.json` → 直接打印 7 栋 12 单元 313 户 17 箱总览表。
- E5：`verify-answer --new 成品.xlsx --answer 标准答案核对版.xlsx` → 313 行零差异、每栋全 OK、rc=0。
- E6：错误格式 JSON → 报错附期望键名 `question / ruling / by / scope / key`。
- E7：`--addr-empty` → gen rc=0、313 户、回读一致（不再依赖 PowerShell 空串）。

---

### 2026-10-04（一百五十一）：P0 审视落地 —— probe 建议正则自相矛盾修复 + new-run 从零跑隔离

**动因**：2026-10-04 凤鸣朝阳从零跑全程复盘（14 次脚本调用 5 次浪费），审视报告识别两个 P0 准确性缺陷，用户裁决「只修 P0」。

**A1 — probe 建议正则 `\d` → `[0-9]`（自相矛盾修复）**
- 病灶：`parse_dxf_structured.py` 的建议值模板（title/fx/hu/bldg/cable 形态）输出 `\d` 形态，与自家 L1-C7 坑①「一律写 [0-9] 不写 \d」**自相矛盾**。经 `--config` 文件传递无害，但 Agent 按文档指导「显式覆盖」把建议值抄到命令行时，`\d` 在 Git Bash 被吃 → **零命中且 rc=0**（命中 0 先怀疑正则被吃 → 源头建议值本身就是雷，每次新图都可能复发）。
- 改动（三处）：
  1. `parse_dxf_structured.py`：11 处建议模板 `\d` → `[0-9]`（`\s` 保留、`\.` 保留——坑①仅及 \d）；`FX\d+` 提示文本同改。
  2. `floor_engine.py` `_cable_pattern_for`：输出处 `.replace(r"\d", "[0-9]")`——检测侧 `CABLE_FORM_RES` 保持 `\d` 不动（Python 内部无此坑），仅输出解耦，语义零变化。
  3. `parse_dxf_structured.py` 写出建议值前加自检 WARN：任何字符串建议值含 `\d` 即报（拦未来新增模板回归）。
- 验证（还原证明）：新代码 fresh 跑凤鸣朝阳全链，把产物 JSON 文本里 `[0-9]` 字面还原为 `\\d` 后算 md5 —— `parsed.json=5cf42d0782ee`、`coverage.json=8bf8a91b47d8`，**与旧 golden 基线逐位一致** → 指纹变化 100% 来自建议值文本改写，**数据本体（楼栋/单元/楼层/户数/分纤箱/覆盖）零变化**。云峰 `parsed.json` 同理。

**A2 — `ftth.py new-run` 子命令（从零跑隔离）**
- 病灶：三本台账累计式，「从零跑」若不隔离，上一轮裁决会被误当「已确认基准」（违反从零语义，是隐性准确性风险——本次凤鸣朝阳靠 Agent 手动归档 40 项历史产物才干净）。
- 实现：`ftth.py new-run --project-dir <项目目录>` —— 项目目录内非 `run_*` 产物全部归档进 `run_<时间戳>/`（**不删除、可追溯**），随后调 `ledger_state.py init` 重建空三本台账。旧 `run_*` 归档目录不再二次归档（避免套娃）。
- 从零定义（写进 SKILL.md I6「从零纪律」）：DXF 同目录 `<DXF>.geom.json` 是无损投影缓存（不在本目录、不归档、可复用）；其余产物一律重生成。

**SKILL.md 登记**：I6 操作纪律表加「从零纪律」行；子命令清单「16 子命令」→「17 子命令」并加 `new-run`。

**测试**：`T2 子命令数=17` 断言同步更新；`T14 golden` 基线经 `--regen-golden` 重建（凤鸣朝阳/云峰/柳辛庄三图全对拍一致）；全量冒烟 **ALL PASS（失败 0 项）**。

**未修的审视项**：A3（C10/C8 口径互引）、E1~E10（手动直调接口摩擦、缺 summary/verify-answer 命令等）按用户裁决留待后续批次。

---

### 2026-10-04（一百五十）：十轮迭代 R2/R3 —— 路径泄漏二轮清剿 + 新增 T23 执行器

**动因**：一百四十九修复后复跑 R2/R3 做指纹对照，暴露**同类缺陷仍在**：柳辛庄八带的 `coverage.json` 出现 R1≠R2（全量 diff **仅 1 行**），而 R1↔R2 其余产物逐位一致 —— 说明仍有「调用方路径原文入产物」的漏网点。

**根因**：两处字段把调用方路径原文写进产物，**违反的是技能已有成文原则**（`check_launch_path.py` 开篇第 1 条：「标记是布尔真值，不是时间戳/路径。含变量的标记会让每次运行的产物 md5 都变，golden 回归（T14）将永久假红」），但该原则此前**只有文字、没有任何执行方**。

| # | 位置 | 原写法 | 为何 T14 抓不到 |
|---|---|---|---|
| 一 | `analyze_coverage_vshape.py:1500` 自检段 `来源` | `args.fx_locations` 原文 | 只在传 `--fx-locations` 时产出，T14 三图不传 |
| 二 | `plan_methods.py:2205` profile `source_dxf` | `str(Path(args.dxf).resolve())` | profile.json **不在** T14 指纹集内 |
| 三 | `plan_methods.py:2206` profile `source_probe` | `str(Path(args.probe).resolve())` | 同上 |
| 四 | `plan_methods.py:2252` `param_source_actual.params_json_path` | `_probe_like` 原文 | 同上（且静态 lint 亦漏 —— RHS 无 `args.` 字面） |

**改动**：
| # | 改动 | 文件 |
|---|---|---|
| 一~四 | 四处一律改 `os.path.basename(...)`；**`_probe_like` 变量本身不动**（2029/2030 行用于真实读文件，改则断 I/O），仅产物字段处归一 | `scripts/analyze_coverage_vshape.py`、`scripts/plan_methods.py` |
| 五 | **新增 T23 产物路径无关性**（`T23a` 动态 / `T23b` 静态 / `T23c` AST 三段）——把上面那条只写在文档里的原则变成 rc≠0 的硬信号 | `tests/run_smoke.py` |
| 六 | `scripts/plan_methods.py` 补 `import os`（见下「本轮自伤」） | `scripts/plan_methods.py` |

**本轮自伤（记下来，教训比结论值钱）**：改动一~四落地后首次全量冒烟**判 FAIL** —— T14 三图全部产物 `MISSING`、T17 报「无可核对象」、整轮仅 2 分 35 秒（正常十几分钟）。根因是改动四所在文件 `plan_methods.py` **顶层没有 `import os`**，`os.path.basename` 运行即 `NameError`（plan 阶段 rc=1 → 下游全断）。

**为何两道现成门禁都没拦住**：`py_compile` 只查语法、不解析名字；`T23b` 静态 lint 只看「该字段有没有走 basename」——两者判不出缺导入。**是 T14 的真跑链路把它揪出来的**（与 `run_smoke.py` T6 条目早就写下的判断一致：「py_compile/import 抓不住调用时 NameError，必须有这条真跑链路」）。更深一层的原因是我自己的取证错误：早先一条 grep 把两个文件的输出混在一起，我把 `analyze_coverage_vshape.py:63` 的 `import os` 错记到 `plan_methods.py` 头上，**没有取第二来源就动手**——故本条目把该教训写进技能文档，并新增 `T23c` 把这类错变成可机器拦下的信号。

**T23 三段为何必须并存**：`T23a` 只扫 T14 真跑到的分支（上表 #一 的 `--fx-locations` 分支 T14 不经过，故 A 段抓不到它）；`T23b` 静态扫产出脚本的「路径语义字段」（`DXF文件`/`输入`/`来源`/`source_dxf`/`source_probe`/`params_json_path`）是否直接赋 `args.*`/`Path(args.*)`；`T23c` 用 **AST** 判「用了 `os.*` 却没 `import os`」——只认真正的属性访问，字符串/注释里的 `os.` 不算，零误报。

**判别力反向验证（三段各一）**：`T23b` 判据打到修复前备份命中 **5 处**（含 F3/F4 两处历史漏网点）、打到现行代码 **0 处**；`T23c` 判据打到合成样例（`import json` + `os.path.basename(...)`）命中 `broken.py`、打到修复前备份与现行代码均 **0 处**（该缺导入是本轮自伤引入，非历史遗留——故合成样例才是它的判别力证据）；`T23a` 依据 = 修复前 T14 fresh 产物中 `profile.json` 三字段共 **9 处**绝对路径。

**边界声明（不搞一刀切）**：`inspect.json`（门禁报告，记录「我读了哪些产物」是本分）与 `pipeline_timing.json`（耗时记录）天然含运行环境信息，**刻意排除**在复现基准外；`conflict.json` 的 `来源` 按其历史决定（一百零六）仍写完整路径——八路输入同名 `parsed.json` 时溯源需要完整路径区分，属另一类需求。

**验证**：`py_compile` 全仓 0 错；补导入后单点复跑 `pipeline --stop-at plan` 三阶段 rc=0（此前 plan rc=1），产物 `profile.json` 路径字段归零；全量冒烟 ALL PASS（T14 转绿 + 新增 T23a/T23b/T23c）；`budget` / `check_docs`(D1~D12) / `check_contract_coverage` 三道门禁全过（其中 check_docs D3 首轮 FAIL 是因「冒烟范围」串在 README 第 63 行命令注释里，漏改该处即 FAIL——已补）。

- **版本**：`version.json` 0.149.0 → **0.150.0**

### 2026-10-04（一百四十九）：十轮迭代 R1 —— T14「三图 golden 回归」假红根因修复

**动因**：用户指示「跑桌面三项目 → 修问题 → 复跑，迭代 10 轮」。R1 实跑（凤鸣朝阳 / 云峰 / 柳辛庄1-4 / 柳辛庄5-9）暴露 `run_smoke` T14 判 FAIL：12 个产物指纹与基线不符，而 CHANGELOG 一百四十七明确记「T14 三图 golden 默认回归全对拍一致」——**同代码两结论，必有假红**。

**根因（三重证据链，逐步排除）**：
1. **指纹交叉**：T14 自产 fresh 产物 vs 生产式调用产物，12 项中 **10 项 md5 逐位相同**，仅 2 项（`analyze_coverage_vshape` 的 `DXF文件`、`count_box_icons` 的 `输入`）不同 —— 二者恰是唯一记录「调用方路径原文」的产物，diff 证实差异仅为分隔符（`C:\\…` vs `C:/…`）。
2. **历史 fresh 留档**：系统 temp 中留存 5 份 `ftth_golden_*`；2026-10-02 的 4 份指纹与旧基线**完全一致**，2026-10-03 23:46 的本轮**全部不一致** → 差异发生在 10-02 23:05 与 10-03 23:46 之间。
3. **逐字节 diff 两期产物**：唯一差异是多出一行 `"_via_launcher": true`。

→ 定论：`FTTH_VIA_LAUNCHER=1` 由 `ftth_launcher.py` 置入 → 经环境继承传给 `run_smoke.py` → 被 T14 **直调** `ftth.py` 的子进程继承 → T14 产物多写 `_via_launcher` 键，而基线（直调口径生成）不含该键 → **回归门禁永久假红**。一百四十七记录「全绿」是因当时 smoke 未经 launcher 启动。

| # | 改动 | 文件 |
|---|---|---|
| 一 | T14 子进程显式剔除 `FTTH_VIA_LAUNCHER`（`env=` 传入过滤后的环境），使直调语义自洽、不再受父进程启动方式影响 | `tests/run_smoke.py` |
| 二 | 相对路径解析增加**技能根回退**：`HERE/<rel>` 不存在时再试 `SKILL_ROOT/<rel>`（文档写的 `tests/run_smoke.py` 属技能根相对，原实现只容忍 `scripts/` 前缀 → rc=2「找不到脚本」） | `scripts/ftth_launcher.py` |
| 三 | `'DXF文件': args.dxf` → `os.path.basename(args.dxf)`，与技能内其余 5 个产出脚本既有约定一致 | `scripts/analyze_coverage_vshape.py` |
| 四 | `"输入": args.dxf` → `os.path.basename(args.dxf)`；消费方 `ftth.py::_cb_fingerprint_ok` 本就按 basename 比对，兼容 | `scripts/count_box_icons.py` |
| 五 | 基线按修后代码重生（`--regen-golden`） | `tests/golden_expected.json` |

**验证**：`py_compile` 全仓 0 错；**相对路径**调用 `run_smoke` 可正常命中脚本（修复二生效）；`--regen-golden` rc=0，冒烟 ALL PASS；重生后基线中**除两处按约定修动的产物外，其余 md5 与旧基线逐位一致** —— 反证本轮**不存在代码回归**，纯属门禁口径缺陷。另：R1↔R2 两轮全量复跑 12/12 产物 md5 逐位一致，技能确定性无恙。

**未修（列为待议，不阻塞）**：① T14 以「直调 ftth.py」为口径，与生产「经 launcher」路径产物天然不同（C7 要求产物带 `_via_launcher`），基线因此无法覆盖生产路径产物；② 「图面确无分纤箱图形符号」的图纸（柳辛庄）在 coverage 侧出现两种门禁结论（rc=2 硬失败 vs rc=0+全 pending），二者应统一。
- **版本**：`version.json` 0.148.0 → **0.149.0**

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

### 2026-10-04（一百五十六）：桌面三项目实跑暴露的三处 P0（new-run 误归档 / B1 崩溃 / 户数整列丢）

**实测动因**：按用户要求，对本机桌面三项目（凤鸣朝阳、柳辛庄、云峰，含 4 张 DXF）**不参考历史记录**从零实跑迭代。跑批经 `ftth_launcher.py` 驱动。三处缺陷均为「自测用例覆盖不到、真机一跑即现」型，其中第三处已造成数量级错误产出。

| # | 改动 | 文件 |
|---|---|---|
| ① | `new-run` 归档范围由「目录内非 run_* 全搬」改为**排除输入与基准**：新增单一实现 `_newrun_keep()`，输入图纸 `.dxf/.dwg/.pkl`、几何缓存 `*.geom.json`、验证基准（表名含「标准答案/参考答案/answer」）原地保留并**逐条打印**（不静默）。原隐含前提「project-dir 内只放产物」在桌面三项目上不成立 —— DXF/geom/答案与产物同目录，会被一并搬空，紧随的 pipeline 必然找不到输入 | `scripts/ftth.py` |
| ② | `summary` 楼层排序 key 由手写 `int(k.replace('F',''))` 改为复用 `floor_num_or_zero`（唯一入口）。原写法遇 `B1` 抛 `ValueError` 使总览整体崩溃；而 `B1层→B101` 是文档已载的已知形态，且该函数在本文件顶部早已导入并在别处使用 —— 属「同一件事两份实现」的必然漂移。全量 grep 确认同类写法仅此一处 | `scripts/ftth.py` |
| ③ | **层数/布线归属改由区间法定带**：不再调 `match_y_to_floor(..., tol=args.y_tol)`（语义＝「最近 + 距离闸门」）。`--y-tol` 缺省按层高/15 自适应，实测某图为 1040，而户数列与楼层刻度列存在系统性错位 dy=1059，仅超阈 19 即**整列拒配、脚本仍 rc=0**。同文件安装楼层当年因同一根因整列落空、已改纯区间法，本次补齐户数与布线这条漏网之鱼；带内多候选时按 y 距离取最近并**登记冲突交人**，落在带外的候选显式告警不采用 | `scripts/parse_dxf_structured.py` |
| ④ | 户数/皮线正则**形态对齐**：`HU_RE`/`CABLE_RE` 两处消费由 `search` 改 `fullmatch`（与主管路 `parse_dxf_structured.py` 业务特征判定、`floor_engine.py` 一致）。原 search 会把皮线规格标注 `2Px2芯x28m` 中的 `x28` 读成 28 户（实测该类误命中 445 条），污染元素台账与 V 型窗口。两者互为镜像，故同时改 | `scripts/ledger_elements.py`、`scripts/analyze_coverage_vshape.py` |

**验证**：`py_compile` 四个文件均绿。**回归三项目**：凤鸣朝阳三轮一致（313 户 / 非空层行 148/148 / FAIL 0 / WARN 3），未受改动影响；柳辛庄 1块地由 **8 户 → 468 户**、非空层行 4/4 → **180/180**，且经**三源独立印证**（图签 `N层/M户` 算得 468、逐层直读修复后 468、图上自述「共覆盖住户467户」差 1）；云峰两轮结果一致，未发现由本次改动引入的回归。

**遗留（未修，已登记）**：云峰图标法 331 户中 231 户落在共用刻度列/偏移异常列（inspect 明示不得当已核消费），与 parse 直读 16 户构成两来源冲突；云峰 C9 五项未定案致 inspect rc=2；`split-band` 仍未接入 pipeline 阶段链，多地块图须手工分带。以上均需人工裁决或后续改造，本轮未擅自改动。

- **版本**：`version.json` 0.155.0 → **0.156.0**。
### 2026-10-05（一百五十七）：迭代第 4 轮 —— 柳辛庄 5-9 地块首次实跑 + 成品首次对拍答案暴露的三处缺陷

**实测动因**：继续「跑 → 发现 → 修 → 回归」。本轮首次跑到**此前从未执行的路径**：柳辛庄 5-9 地块（含 `9-1/9-2` 连字符地块名的分带）、`gen` 成品出表、`verify-answer` 对标准答案。三条均为首次真机执行。

| # | 改动 | 文件 |
|---|---|---|
| ① | **补上被调用方提示、入口却没有的通道**：`coverage` 早在 2026-09-18 就有 `--allow-low-pairing`（低于配对率阈值时强行继续），其失败文案原文让用户加该开关，**而 `pipeline` 一直没有这个参数** —— 用户照做只会拿到 `unrecognized arguments`（与其注释自承的「直调脚本有、统一入口没有 = 接口断层」同类缺陷重演）。本次给 pipeline 补同名开关，`cov_cmd == "coverage"` 时透传；**默认 False**，保持原硬失败语义，仅消除死路，不替人决策 | `scripts/ftth.py` |
| ② | **消除「有答案但不可达」**：新增 `_pipe_hint_fx_symbol_cands()`（单一实现，入参为画像**路径**，与同级 `_pipe_effective_layers` 一致）。当 `_want_fx` 为空时列出 `probe_signals.fx_symbol_layer_candidates` 的层名/得分/推荐与否/判据分项（一致性·标题区重叠·闭合矩形·众数簇·众数尺寸），并给出「显式指定图层」与「确无符号画法则加 `--allow-low-pairing`」两条处置。**不自动采信未达门槛者**。此前候选只因未满足「一致性>=0.8 且 标题区重叠>=0.8 且 数量吻合」就被埋在 profile 里，而 coverage 的失败文案却把人导向「去猜图层名」—— 排错方向被带偏 | `scripts/ftth.py` |
| ③ | **`verify-answer` 列定位改为按表头名**（当日 P1-E5 刚上线即修复）：原实现硬写 Excel 列位 `column=8/10/12/14/16`（H/J/L/N/P），那**只是 24 列定稿模板**的布局；用未传 `--template` 的内置 11 列降级表产物去对拍时五列整体错位（实测取到「单元/户号/越界空/越界空/越界空」）→ **逐行全 DIFF、每栋 `[DIFF(答案None)]`**，把「列错位」呈现成「结果全错」。改为按别名表（六级↔楼栋、七级↔单元、八级↔楼层、九级↔户号、分纤箱编号↔分纤箱）按名定位，缺列时**报人中止**而非静默取空；并把「仅楼层写型不同」的差异单独归类提示（不抹平，仍计入 diff） | `scripts/ftth.py` |

**交叉验证（第二来源）**：
- 第 1-3 轮的户数区间法修复（`parse_dxf_structured.py`）在**全新 4 个子带**上全部生效且与首次实测一致：band8 非空层行 **194/194**、band9-1 **142/142**、band9-2 **108/108**（修复前同类图为 4/4）。
- **凤鸣朝阳端到端对拍：差异行数 0**（313 户，每栋户数 `OK`、每栋分纤箱集合 `OK`、合计 313=313）。流程：`pipeline` → `gen --floor-format chinese` → `verify-answer`（答案＝项目自带的「标准答案核对版」）。这是首次把成品表与人工答案逐行对齐。
- 柳辛庄 5-9 的 `AXIS` 符号层候选**经客观几何证否**：12 个闭合矩形尺寸完全一致（14640×9840），但 FX 编号到最近矩形 min 距离 **132962**（≈矩形宽的 9 倍）、含 FX 的矩形 **0/12** —— 保守不推荐是正确的，未冤枉它。

**验证**：`py_compile` 绿；技能自带冒烟仅 T14 FAIL（云峰 golden 漂移，上一轮已登记的待裁决项），**本轮改动零新增失败**。

**遗留（未修，已登记）**：柳辛庄 5-9 四带的 inspect 均 rc=2（C9 大量未定案 / C10 图签与系统图矛盾 / C6 覆盖闭合缺线索），属需人工裁决的第④类，**未出成品**；band5 需 `--allow-low-pairing` 才能过 coverage（结果须人工复核，不得当成品）；云峰 T14 golden 漂移（`*16` 是否某层真户数待裁决）；`split-band` 仍未接入 pipeline 阶段链，多地块图仍须手工分带。

- **版本**：`version.json` 0.156.0 → **0.157.0**。
### 2026-10-05（一百五十八）：迭代第 5 轮 —— split-band 接入串跑 + 整单元户数缺失被「有布线」掩盖

**实测动因**：继续「跑 → 发现 → 修 → 回归」。本轮首次把柳辛庄 1-4 剩下的 3 个分带跑完，并解决「多地块图必须人工手搓分带」这一结构性缺口。

| # | 改动 | 文件 |
|---|---|---|
| ① | **`split-band` 接进 pipeline 串跑**（填补「执行环节零接线」）：新增 `_pipe_fanout_bands()`，在 `unit_gaps` 之后、`parse` 之前量分带方案；子带数 >=2 即扇出，对每个子带**递归跑一条完整 pipeline**（产物在 `<outdir>/bands/<带名>/`），汇总退出码取最严重者。位置**刻意选在 parse 之前的所有阶段之后** —— 串号风险只来自 parse 及下游（同名楼栋按楼名去重会静默串号），而 titleblock/fxmap/fx_locations/unit_gaps 是整图级、无串号风险且各有独立价值（图签第二来源、单元×箱预检）。开关 `--no-auto-split-band`（默认开启；单地块图量出 <2 带自动原路返回，零影响）。递归时强制关闭分带，防二次分带 | `scripts/ftth.py` |
| ② | **C5「整单元户数缺失」检测**：此前只统计「户数+布线**两列皆空**」的层行（blank_rows）。实测存在「布线读到了（`32m*2`）、户数却是 None」的层 —— 它们**不是** blank_rows，于是在 C5 里既不进明细、也不告警，**户数凭空少一半却全无提示**（band4 图签 165 户 / 直读 105 户）。改为按「**户数缺失**」口径统计，整单元 100% 缺失时点名列出（含同楼有户数的兄弟单元作对照），并明确「不得按地下车库层等图面事实处理，确认前不得出表」。该检测**独立于 blank_rows 分支**执行（否则全图每层都有布线值时会被整段跳过） | `scripts/inspect_closure.py` |
| ③ | 扇出位置回归修正：首版把扇出放在 `plan` 之后，冒烟 golden 立刻报柳辛庄 1-4 的 `titleblock/fx_locations/unit_box_gaps` 三项 **MISSING** —— 整图级阶段被连带跳过。移至 `unit_gaps` 后即恢复。记录此坑：改串跑链时，**插入点之后的既有阶段会整体消失**，须以 golden/冒烟兜底 | `scripts/ftth.py` |

**交叉验证（第二来源）**：
- 柳辛庄 1-4 与 5-9 两张多地块图，由「必须人工手搓分带 + 逐带手跑」变为**一条命令自动跑完 8 个带**。
- 柳辛庄 1块地 `pipeline → gen --floor-format chinese` 出表 **468 户**，与图签 `N层/M户` 独立算出的 468 **吻合**。
- 凤鸣朝阳回归不变（313 户 / 148/148 / FAIL 0 / WARN 3）；单地块图未产生 bands/ 目录，未受影响。
- 技能自带冒烟**仅剩 T14 一项**（云峰 golden 漂移，第 1-3 轮已登记的待裁决），本轮改动零新增失败。

**遗留（未修，已登记）**：**多单元共用户数列只读到一个单元** —— 客观证据：同一层同一布线 `32m*2`，1单元读到户数 2、2单元读到 None（band4 1#/2#楼 2单元各 16 层全缺）。图签逐栋对账量化：柳辛庄 1-4 的 band1/band3 差 0，band2 差 **-99**、band4 差 **-60**（合计 -159 户）。归属属第④类，**不得自动裁定**，须人工确认是否为共用刻度列；该检测已能报出，但缺失本身未修。云峰 C9 仍有 5/46 项未定案 → 不可出表。

- **版本**：`version.json` 0.157.0 → **0.158.0**。

### 2026-10-05（一百五十九）：补登收尾 —— clone_shared_hu 落地（P0 语法修复 + 统一入口补通道）

**实测动因**：外部 AI 架构审核报告（桌面 `ftth-address-extractor审核报告.md`）实测指出 `floor_engine.py` P0 语法阻塞、全链不可运行。交叉审视复核结论：**P0 属实（已复现）**；报告另有两处口径偏差一并修正 —— ① changelog 主文件实已登记 157/158（非「最新只到 156」），`minor=修订序号` 口径未破，真正缺口仅本条（159 功能改了代码未登记版本）；② T14 无真图时判 **SKIP** 而非 FAIL（`run_smoke.py` 明示 `[SKIP] T14 真图缺失`），报告所见「三图全 MISSING」的直接死因是**跑冒烟的解释器无 ezdxf**（T14 直调 `ftth.py` 不经启动器、`PY=sys.executable`），以内置 Python 跑即全 MISSING，属环境假象；**冒烟须以带 ezdxf 的主 Python 跑**。本条补登 clone_shared_hu（上轮代码已落、带语法错、未登记版本）并收尾。

| # | 改动 | 文件 |
|---|---|---|
| ① | **P0 语法修复（解阻塞）**：`split_units_by_marker` 新增 docstring 被 243 行 `"""` 提前闭合，245 行起旧注释（09-12 修正 / 09-19 共享列）成裸文本，`2026-09-12` 前导零触发 SyntaxError → `import floor_engine` 即炸，parse/coverage/inspect 全链不可运行（py_compile 43 中 1 坏、T0/T23c 连带红）。修法＝删 243 行闭合引号、旧注释收进同一 docstring；docstring 不入产物，零行为变更 | `scripts/floor_engine.py` |
| ② | **统一入口补通道**（157① 同构缺陷第三例）：`--clone-shared-hu` 上一轮只落在直调入口，`ftth.py parse` 未注册 → 传参报 `unrecognized arguments`（「加开关必漏」坑再应验）。补 `p_parse` 注册（store_true 默认 False）；`build_cmd` 按 2026-09-15 布尔统一规则自动转发，分发段零改动 | `scripts/ftth.py` |
| ③ | **参数表登记**：parse 主要参数列表补 `--clone-shared-hu`；高频坑区补语义与边界（含「pipeline 未透传，多带图须逐带直跑 parse」） | `references/scripts_reference.md` |

**功能语义（补登，上轮已写未录）**：共用轴户数列（落在**全部单元 x 范围之外**）默认只挂最近单元 → 多单元楼其余单元整单元无户数（158 遗留「合计 -159 户」根因，C5 已能点名报出）；加开关则克隆进该栋每个单元。**属归属裁定、默认关** —— 须人工以图签第二来源（「层数×每层户数×单元数」）核对确为「每单元每层」口径后再开，否则把「整栋每层」口径翻倍；仅克隆户数，箱编号/皮线米数仍不克隆（克隆必重复计数）。

**验证**：py_compile 全仓 43/43 绿；`ftth.py parse --help` 正常显示新参数；主 Python 3.13（ezdxf 1.4.4）跑 `run_smoke.py` 全套：除 T14 云峰已登记漂移外**全绿**，fmcy/lxz14 golden md5 与基线一致（①②改动零行为回归的直接证据）。T14 云峰差异与本轮改动无关：`parsed.json` md5 ≠ 基线源于 156 ③④（fullmatch / 区间法带归属）+「`*16` 是否某层真户数待裁决」；inspect F=5/W=12 与 158 遗留清单逐条对应（C9 5/46 未定案、331 户中 231 户落不可信列），不得 regen 基线。

**遗留（未修，已登记）**：pipeline 未透传 `--clone-shared-hu`（扇出递归构造 argv 改动面 3~4 处，独立立项）；云峰 golden 漂移与 C9 五项 pending 仍待人工裁决；审核报告其余结构性建议（parse/analyze_coverage 加 main 守卫、fl_num/unit_no/cable 单一源收敛、拆 ftth_common、ftth.py 分发表静态校验、T0 纳入提交门禁）待用户裁决优先级。

- **版本**：`version.json` 0.158.0 → **0.159.0**。

### 2026-10-06（一百六十）：y 坐标用途边界成文 + 口径B:y坐标关联退役（柳辛庄会审视议落地）

**实测动因**：桌面《柳辛庄项目_技能会审报告.md》提"P1-1 清理 y 坐标旧口径"，复审时外部 AI 给出"修正意见"主张"不要删 y 坐标、应降级为几何归属证据"。交叉核实代码后确认：**现行体系里被禁的只是"y 最近邻推算安装/覆盖楼层"，y 用于空间归属/楼层带包含/连续体认领/图标贴合本就合法且在用**——误会源于"口径B"一词两义（旧=`y坐标关联`推算已废弃 2026-09-18；新=`区间法`四法之一合法）。云峰产物实证：`coverage.json` 认领依据"箱的y坐标落在该连续体区间内（几何直读）"、`count_box.json` 图标按容差 6.0 贴皮线末端、`fxmap.json` 23 编号全"口径A:图上直写"——**全程零最近邻推算、全包含/贴合/对位**，是"y 该保留"的最强正例。但代码层一处真 bug：`extract_fx_map.py:341` 的"口径B:y坐标关联"分支在 present 场景下仍产出安装楼层值，parse 回填分支（`FX_MAP 非空+唯一映射`）不区分口径来源 → 四法外推算可经对照表通路静默进成品。本条成文边界 + 堵漏。

| # | 改动 | 文件 |
|---|---|---|
| ① | **行为收口（核心）**：`extract_fx_map.py` 编号与楼层标注 |dy|>5.0（非紧贴同行）的"y 最近邻"分支退役——不再赋安装楼层（留 None + `最近楼层标注_留证`/`最近楼层距离_留证` 留证），标签改"未定：y最近邻不作来源（2026-09-18裁决）"。下游 parse 回填分支因"安装楼层非空"条件不满足而自然不采信 → 四法外推算无法经对照表通路进成品。|dy|≤5.0（紧贴同行=直写）保留。空间归属（楼栋/单元）不受影响 | `scripts/extract_fx_map.py` |
| ② | **方法池死条目删除**：`_METHOD_POOL_RULES` 删 `("编号文字", "读取标注 + 坐标关联")`——methods/*.json 无真实触发者（候选描述含"编号文字"时必含"区间"，先命中"区间法"条目）；且分类目标"读取标注 + 坐标关联"非方法池四类之一，被触发会让 `install_by` 误判为"读取标注（编号旁直写）" | `scripts/plan_methods.py` |
| ③ | **handoff 措辞精确化**（保留空间归属语义）："坐标关联"→"几何空间归属（x/y 双坐标分区）"+ 注明"不用于推算安装/覆盖楼层"；降级提示同步改"『依系统图坐标关联』"→"『依系统图几何空间归属』" | `scripts/plan_methods.py` |
| ④ | **术语/注释清理**：`parse_dxf_structured.py:28` docstring 旧术语"口径B y坐标关联"更新为四法+禁令语境；`count_households.py` 皮线归属标注为区间法（行为就是区间法，旧标签误标）+ LEGACY 定位；`step2_selfcheck.md` 口径B检查项"y坐标关联距离合理"→"安装楼层误差在合理范围内" | `scripts/parse_dxf_structured.py`、`scripts/count_households.py`、`references/step2_selfcheck.md` |
| ⑤ | **铁律⑩成文**：SKILL.md 浓缩版加铁律⑩"y 坐标用途边界"（合法：包含判定/容差贴合/区间对位；禁止：最近邻比较推算）；`measurement_architecture.md` 全文版+云峰正例/柳辛庄 band8 反例+边界词"包含 vs 距离比较"+落地说明 | `SKILL.md`、`references/measurement_architecture.md` |

**边界一句话**：y 坐标回答"它在谁的辖区里"（包含/贴合/对位，合法——楼栋-单元空间归属、楼层带归属、竖线法连续体认领、图标贴合）；y 距离回答"它离谁最近"（最近邻比较推算安装/覆盖楼层，禁止作为结果来源）。

**验证**：py_compile 全仓 43/43 绿；`run_smoke.py` 全套（含 T14 三图 golden）ALL PASS——云峰 fxmap 23 编号全口径A，收口分支不触发 → fxmap/parsed/coverage/inspect 全不变（零行为回归的直接证据）；凤鸣朝阳无 fxmap、柳辛庄1-4 全图守卫早停均不受影响。柳辛庄 5-9 分带复跑对拍 iter10 基准：band5/8/9-1/9-2 inspect rc/F/W 全一致（band3 fxmap 全口径A，收口零差异）。

- **版本**：`version.json` 0.159.0 → **0.160.0**。
