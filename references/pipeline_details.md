# 流水线细则：脚本行为、参数细节与实现背景

> **本文件是什么**：SKILL.md 「Step 1b: 结构化解析」的**细则层** —— 脚本行为、参数细节、实现背景与实测案例。SKILL.md 只保留**协议与硬约束**（要点式）。
> **为什么拆**（2026-09-18）：SKILL.md 触体量硬上限（实测 55,391 B > 49,000 B 硬上限、> 51,200 B 宿主截断线）。按「净增为零原则」外移；且这些内容本质属**细则**而非**协议**，SKILL.md 自身定位即"只承载协议 / 状态机 / 硬约束 / 名目清单"。
> **链接写法**：本文件内引用按**技能根目录视角**书写（与 `references/` 现有约定一致）：`references/xxx.md` 指技能根下 `references/` 目录。
> **体量**：单文件同受 47,000 B 约束。
>
> 相关：`references/scripts_reference.md`（脚本参数表 / 统一入口机制 / `geom.json` schema）、`references/coverage_rules.md`（两条硬约束全文）、`references/measurement_methods.md`（算法与判据）。

---

## 1. `ftth.py` 统一入口

调度 `pipeline` / `probe` / `plan` / `parse` / `coverage` / `coverage-vshape` / `inspect` / `assemble` / `apply-ruling` / `count` / `count-box` / `gen` 等子命令；**`ftth.py pipeline` 一条命令串跑 `geom → probe → plan → parse → coverage → inspect`（只解析、不出表，实测 38.7s → 18.4s）**；参数三级优先：命令行显式 > `--config` > 脚本默认值。

子命令清单、依赖矩阵、可抄示例、`--config` 机制、批量编排 `ftth_batch.py` 见 `references/scripts_reference.md`。**口径**：`count` = 皮线计数法；`count-box` = 家居配线箱图标法（旧名 `count-hdd`），两者同属区间法口径；`extract_fx_map.py` / `read_titleblock_households.py` / `gen_9level_addressbook.py` 为直调脚本。

## 2. 必传参数与三个高频坑

完整参数表、可抄示例与三个高频坑（`--wire-layer` / `--title-pattern` / `--floor-pattern`）见 `references/scripts_reference.md`。**默认值仅供参考，换图先按 Step 1a 探查结果覆盖**；三个坑里最易踩的是 `--floor-pattern` **不得显式传 `(-?\d+)F` 覆盖内置解析** —— 会让 `B1` 整层静默消失。

## 3. 正则传参为什么一律写 `[0-9]`

Windows 命令行 / Git Bash 会把 `\d` 里的反斜杠吃掉或转义：实测 `--fx-pattern "FX\d+#?"` **零命中且脚本仍 rc=0**，调用方误判为"图上没有箱"。故凡传正则类参数（`--fx-pattern` / `--title-pattern` / `--hu-pattern` / `--bldg-pattern` …）**一律写字符类**：`FX[0-9]+#?`、`([0-9]+)#楼`。

**判据**：命中数为 0 时先怀疑正则被吃，**不得据零命中改判图纸无此元素**（零命中 ≠ 无元素，与「空结果不得当成功消费」同则）。

## 4. 人工裁决批量改数 `apply-ruling`

裁决结论用 `ftth.py apply-ruling --json <assembly.json> --ruling <裁决清单.json>` 一次落数，**禁止为每条裁决现写临时脚本手改 JSON**。只做机械落数：缺字段不改、找不到目标硬失败并列出候选键；**裁决值含乘号一律拒绝**（`4*16` 须人工展开成 `64` —— 乘数是裁决项，脚本不做乘法）。

## 5. 中间产物写保护

`count-box` / `assemble` / `apply-ruling` 的输出**同名已存在时默认改道 `<原名>_patched.json`**，覆盖原产物须显式 `--force`。

**理由**：自算值一旦覆盖技能原始产物，原始输出永久消失、下游输出反过来当同一条链的证据 → 论证闭环、不可复现。

## 6. 刻度列配错时的显式纠正入口 `count-box --col-scale-map`

`count-box` 默认按"几何最近"给每个图标列配刻度列，**一条刻度列服务多个图标列**的图纸会整列配到邻栋 / 邻图区。脚本已会在出口给出「多列共用同一刻度列」告警；此时**用 `--col-scale-map "列x=刻度列x;..."` 显式指定映射**（x 值取告警里列出的实测列 x），不要靠反复调容差去凑 —— 实测某图为此烧了 25 分钟、40 个临时脚本。

## 7. `parse --fx-map` 回填的实现细节

**只有**图纸存在**真实集中总图对照表**（画像 `fx_overview_map=present`，`extract_fx_map.py` 产物）时，才用 `--fx-map <fxmap.json>` 把对照表的安装楼层回填到 parse 侧**缺失**的箱：

- 只补 null、不覆盖已测值
- 重号不回填并登记交人
- 回填留 `安装楼层口径=fx-map:总图对照表回填` 与产物 `FXMAP回填` 段，可追溯

**absent / variant 一律不回填**：分纤箱所在楼层 / 覆盖 / 每层户数只允许来自四种方法（图上标注直读、V型计算、区间法、竖线法）与多方标注互验；「编号 y 坐标关联推算」不在四法内，禁止作为来源（2026-09-18 用户裁决，pipeline 已在 gate 层拦截）。

## 8. `parse --bldg-map` 定归属的实现细节

**硬约束② 在 parse 侧的落地。** **只有**画像 `fx_overview_map=present`（图纸确有集中总图对照表）时才传 `--bldg-map`；absent/variant 不传（pipeline 已拦截，见 `ftth.py _pipe_fxmap_gate`）。

总图对照表形态的图纸其箱编号集中写在独立图区、x 不落在任何楼栋标题区间内，而 parse 默认按"楼栋标题 x 中分"归属文字 → **逐栋 0 箱且 rc 仍为 0**（静默丢数，下游不跑 inspect 不会察觉）。传 `--bldg-map <fxmap.json>` 后箱的楼栋/单元归属改以对照表为准。

**三条边界**：

1. 对照表无该编号 / 重号 / 楼栋名不在本图锚点内时**保持原硬切结果并留痕**，不猜、不静默择一；
2. 对照表的「楼栋」字段可能带单元后缀（`N#楼M单元`）而本图锚点名不含单元，实现须做前缀解析后再匹配，否则含后缀的条目会被整批丢弃；
3. 改派循环的数据源必须是**全图文字**而非按楼栋切好的子集 —— 后者的"丢失物"本就不在其中，从它里面找必然 0 命中。

**产物**：写 `BDGMAP归属` 段（改派条数 / 跨栋改派清单 / 重号未改派 / 单元名并存）与顶层 `分纤箱提取状态`（0 箱时显式标注"须核是否总图对照表形态"）。

**无对照表图纸（absent）**：箱的楼栋 / 单元 / 安装楼层归属由**方法池**（区间法：编号文字 / 箱符号落楼层带；读取标注：图上直写）测定并逐箱写出依据，交人工复核 —— 不引入 y 坐标关联推算作来源。

## 9. 对照表认领箱的安装楼层为什么取口径A

`--bldg-map` 改派过来的箱，其编号写在**独立的总图对照表图区**，文字 y 与楼栋系统图的楼层刻度**不是同一坐标系** —— 拿它的 y 去套系统图楼层带会得出无物理意义的层号（实测出现过 `WF` / 高层号），并连带让 inspect 的 C3 双源交叉报不一致、C6 报覆盖不闭合。

**故**：对照表有**唯一**映射且带非空安装楼层时，`安装楼层` 取对照表值，口径标 `口径A:图上直写（总图对照表）`、来源标 `fxmap对照表`；区间法原值原样降级保留在 `区间法参考值` / `区间法参考误差` 两个字段供审计（证据不丢）。两条判据不同时成立则一切照旧 —— 不猜、不放宽。

**安装楼层口径因此共 3 个取值**：`口径A:图上直写`（本楼系统图内直写）、`口径A:图上直写（总图对照表）`（对照表直写、跨图区）、`口径B:区间法`（本楼系统图楼层带区间法）—— 输出中必须原样标注用的是哪一个。

**注意**：对照表值本质仍是「图上标注直读」来源，只有存在真实集中总图（present）时才可用；absent 时无此口径，安装楼层只能由四法测出。

## 10. `inspect --fx-pattern` 产物自描述

`inspect_closure.py` 的 `--fx-pattern` 内置默认是 `FL\d+-FX\d+`，与大多数图的编号形态不符。命令行未显式给出时，改用 parse 产物自带的 `参数.fx_pattern`（产物自描述）。**调用方不必再手工传该参数**，传了以命令行优先。

**此前的表现是**：流水线不转发 + 默认值不匹配 ⇒ C4 在 geom 文字里一个编号都搜不到 ⇒ 把 parse 侧**全部**箱误判成"图上无编号文字"（实测某图 23/23 全 FAIL 的纯假警报），把真 FAIL 整个淹掉。

**同理**：任何"用正则扫全图再与 parse 对账"的核查都必须先确认用的是**该图实际生效的那个正则**。

## 11. `ftth.py pipeline` 阶段顺序为什么固定

`geom → probe → plan → titleblock → fxmap → fx_locations → unit_gaps → parse → coverage → inspect`，`--stop-at` 的 choices 与之一致（**由 `ftth.py` 的 `_PIPE_STAGES` 单一定义**，本节仅为说明 —— 两者不一致时以代码为准并改本节）。

`fxmap` 必须在 `parse` **之前** —— 依据硬约束 ②，parse 与 coverage 都需要总图对照表来定楼栋 / 单元归属；排在其后会变成"先用被明文禁止的方法切完、再拿正确数据去补 coverage"，parse 侧永远 0 箱（实测 C0/C2/C3/C4/C6 全 FAIL）。同一份对照表在 parse（`--bldg-map` + `--fx-map`）与 coverage（`--bldg-map`）两处复用，**一份数据、两处同源**，避免各取各的。

**2026-09-18 收紧**：`fxmap` 阶段仅当画像申报存在真实集中总图对照表（`fx_overview_map=present`）时执行；absent / variant 一律跳过（rc=3），不再产出降级对照表，pipeline 自动不向 parse / coverage 回填 —— 四种方法之外禁止自创来源，见 `ftth.py _pipe_fxmap_gate`。

`fx_locations` 与 `unit_gaps` 同理必须在 `parse` **之前**：前者是安装层的独立第二来源、要在 coverage 交叉校验前备好；后者做「**单元 × 箱清单**」交叉清点，把「某单元没分纤箱」提前暴露（否则只能等 Step 2 覆盖门禁，那时 parse/coverage 已跑完、返工面大）。

**`unit_gaps` 的三态语义（2026-09-18 新增，勿混）**：产物 `<outdir>/unit_box_gaps.json`，`预检结论` 取 `pending`（两侧来源齐备且差集非空，**有疑点要报人**）/ `settled`（齐备且一致）/ `unresolved`（**某侧来源未就绪，本次未判定**）。`unresolved` **不是通过** —— 它只说明探查期没核成，覆盖阶段门禁仍须照跑兜底。该阶段非 0 退出**不中止主链路**（它是预检，不是主数据来源），但必须显式打印。

## 12. 冷启动 vs 热启动的耗时不可横向比

`dump_geom.py` 经 `ftth_common.load_geom` 落 `<DXF>.geom.json` 缓存，缓存新鲜时直接复用（实测某图冷启动约 45~50s、热启动约 10s）。做"多轮结果可复现"检验时，每轮**必须先清 geom 缓存**，否则把热启动轮次与冷启动轮次的耗时并列会把缓存收益误读成优化收益。

## 13. 元素台账 `ledger_elements.py`

`parse` 出的是**业务树**，「有哪些元素、各在哪、边界在哪」由台账回答（六类元素带坐标 + 楼栋/单元边界 + 重叠**分型** + 缺项显式）；rc 见 SKILL.md **L1-C2**，字段表见 `references/scripts_reference.md` §元素台账。

## 14. 其余细则的落点

- **必须解析项的判据与算法** → `references/measurement_methods.md`、`references/coverage_rules.md`
- **安装楼层与户数楼层归属为何必须同用区间法**（取最近楼层线会越过带中点误判）→ `references/measurement_methods.md §3.5`
- **`analyze_coverage.py` 的 `安装楼层总图校验`** → `references/coverage_rules.md`
- **两条硬约束全文、实测反例与其余前置约束**（`--wire-layer` 图层来源统计等）→ `references/coverage_rules.md §零`

## 15. SKILL.md 体量阈值依据（原「参考文件」节移入）

**阈值为什么是这两个数（2026-09-18 实测，勿凭感觉调）**：外移能力有极限 —— SKILL.md 可外移的明细约 5.3 KB（实测 48,822 → 43,505），再往下动就是 L0/L1 硬约束本身；而单条新契约约 1~2 KB。故预警线须在硬上限**之前留出可操作空间**，设 47,000；设 46,000 会出现「触线即无路可走」（实测仅剩 150 B）。

**宿主截断不可配置**：本文件是每次会话首屏全量加载的唯一文件，工具输出有通用截断（实测 51,200 B，无开关）—— 把阈值调到它以上没有意义。

**`references/` 单文件同受 47,000 B 约束**（否则闸门只是把问题搬家）。

**本条历史**：原在 SKILL.md 「参考文件」节内，2026-09-18 外移至本文件以腾出体量；SKILL.md 保留两个阈值数字与闸门入口。

## 16. `geom.json` 字段序（schema v3）三坑

`dump_geom.py` 产出的 `<DXF>.geom.json` 字段序有三处易错，**读错字段序会白跑一轮**：

| # | 字段 | 正确形态 |
|---|---|---|
| 1 | `texts` | `[图层, x, y, 文本]` —— **「图层」在首位**（不是末尾） |
| 2 | `segs` vs `polylines` | `segs` 是**逐段**线段；`polylines` 才是**整组顶点** |
| 3 | `insert_attrs` vs `inserts` | 两者**同索引**（第 i 个 `inserts` 的属性在 `insert_attrs[i]`） |

- **完整 schema** 与 `_src` 失效判据（`mtime + size + GEOM_VERSION`，任一变化即缓存失效）见 `references/scripts_reference.md`。
- **前置约束**：需要**"多段线整组顶点"或"INSERT 块属性"**的脚本必须走 `ftth_common.load_dxf`（pkl 缓存），**不能走 `load_geom`**。
- **本条的来源**：原在 SKILL.md 「Step 1a」节内，2026-09-18 外移至本文件（SKILL.md 仅保留"三坑"提示与指针）。

## 17. `pipeline` 阶段细则：`titleblock` 与「图层参数按子命令分派」

> 本条从 `scripts_reference.md` 外移（2026-09-18，该文件触 47,000 B 预警线）。
> 阶段链与参数表仍在 `scripts_reference.md`；此处只放细则。

### 17.1 `titleblock` 阶段（2026-09-18 实跑新增）

**做什么**：画像 `titleblock_annotation = present / variant` 时，调 `read_titleblock_households.py`
产出 `<outdir>/titleblock.json`（图签第二来源读数：栋级 `N层/M户每层` + `N单元`），
并由 `inspect` 阶段作为 **C10** 的输入透传（`--titleblock`）。

**为什么要有它**：画像早已把该信号判为 present 并写明「构成三来源协议的第二来源」，
但 `pipeline` 的阶段列表里没有它、C1~C9 也没有对应检查 —— **规则写在文档里、没有代码执行它**。
实测某图 7 栋的图签读数与系统图逐栋一致，可这条独立来源验证**从未发生过**。

**行为约定**

| 情形 | 行为 |
|---|---|
| 画像申报 `absent` | 该阶段合法缺席，记 rc=3（申报制语义，非错误） |
| 脚本非 0 退出 | **不中止主链路**（它是校验来源、不是主数据来源），但**显式打印**，且 C10 随之判 **SKIP** —— 「没核」不得呈现成「通过」 |
| 图层取不到 | **跳过不猜**（不硬编码图层名），同样打印 + C10 SKIP |

**图层取值三级**（2026-09-18 实跑踩坑：只读 config 顶层 `text_layer` 取不到 ——
实际它嵌在 `suggested_params` 里，于是本阶段静默跳过、C10 白 SKIP，属"修了但没生效"）：

1. `config.json` → `titleblock_layer_candidates.候选图层[0]`
   （probe **专为该脚本**产出的 advisory 字段，`用途` 字段里写明）；
2. 回退 `config.json` → `suggested_params.text_layer`（取逗号首项）；
3. 都取不到 → 跳过并说明。

### 17.2 图层参数按子命令分派（2026-09-18 实跑修复）

`--wire-layer` / `--fx-symbol-layer` / `--bldg-map` **只有 `coverage`（`analyze_coverage.py`）消费**。

`coverage-vshape`（V 型法）的覆盖与楼栋/单元归属**全由文字标注决定**（米数列谷底 / 标题窗口几何），
连线与符号图层对它无意义 —— 实测给 `coverage-vshape` 传 `--wire-layer BZ` 会得到
`unrecognized arguments` 并**直接 rc=2**（脚本打印全部可用参数后退出）。

原实现无条件追加这三个参数，只是恰好"画像两个图层都为 null"才未触发；
换一张 `dedicated_wire_layer = present` 的图即挂。现按 `cov_cmd` 分派，不再一律传。

> **同类缺陷提示**：`--bldg-map` 那处早已按子命令分派，这两处却漏了 ——
> **只修报出来的那一个，等于留哑弹**。改动图层/对照表参数的传递逻辑前，先 grep 全部同类参数。
