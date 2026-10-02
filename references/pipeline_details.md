---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '6f604bf3-5665-460e-8d72-4e1d93064a09'
  PropagateID: '6f604bf3-5665-460e-8d72-4e1d93064a09'
  ReservedCode1: 'b81b7b6f-0de8-40d3-81e8-9a86a1fb910a'
  ReservedCode2: 'b81b7b6f-0de8-40d3-81e8-9a86a1fb910a'
---

# 流水线细则：脚本行为、参数细节与实现背景

> **本文件是什么**：SKILL.md 「Step 1b: 结构化解析」的**细则层** —— 脚本行为、参数细节、实现背景与实测案例。SKILL.md 只保留**协议与硬约束**（要点式）。
> **为什么拆**（2026-09-18）：SKILL.md 触体量硬上限（实测 55,391 B > 49,000 B 硬上限、> 51,200 B 宿主截断线）。按「净增为零原则」外移；且这些内容本质属**细则**而非**协议**，SKILL.md 自身定位即"只承载协议 / 状态机 / 硬约束 / 名目清单"。
> **链接写法**：Markdown 链接按**所在文件目录**解析 —— 本文件在技能根，故外链写 `references/xxx.md`；`references/` 内的文件**互相引用写裸文件名**（如 `coverage_rules.md`）；行内代码提及仍按技能根视角写，便于全仓检索。
> **体量**：单文件同受 47,000 B 约束。
>
> 相关：`references/scripts_reference.md`（脚本参数表 / 统一入口机制 / `geom.json` schema）、`references/coverage_rules.md`（两条硬约束全文）、`references/measurement_methods.md`（算法与判据）。

---

## 1. `ftth.py` 统一入口

调度 `pipeline` / `probe` / `plan` / `parse` / `coverage` / `coverage-vshape` / `inspect` / `assemble` / `apply-ruling` / `count` / `count-box` / `gen` 等子命令；**`ftth.py pipeline` 一条命令串跑 `geom → probe → plan → titleblock → fxmap → fx_locations → unit_gaps → parse → coverage → count_box → inspect`（只解析、不出表，实测 38.7s → 18.4s）**；参数三级优先：命令行显式 > `--config` > 脚本默认值。

子命令清单、依赖矩阵、可抄示例、`--config` 机制见 `references/scripts_reference.md`；批量编排 `ftth_batch.py` 见本文件 §19。**口径**：`count` = 皮线计数法；`count-box` = 家居配线箱图标法（旧名 `count-hdd`），两者同属区间法口径；`extract_fx_map.py` / `read_titleblock_households.py` / `gen_9level_addressbook.py` 为直调脚本。

## 2. 必传参数与三个高频坑

完整参数表、可抄示例与三个高频坑（`--wire-layer` / `--title-pattern` / `--floor-pattern`）见 `references/scripts_reference.md`。**默认值仅供参考，换图先按 Step 1a 探查结果覆盖**；三个坑里最易踩的是 `--floor-pattern` **不得显式传 `(-?\d+)F` 覆盖内置解析** —— 会让 `B1` 整层静默消失。

## 3. 正则传参为什么一律写 `[0-9]`

Windows 命令行 / Git Bash 会把 `\d` 里的反斜杠吃掉或转义：实测 `--fx-pattern "FX\d+#?"` **零命中且脚本仍 rc=0**，调用方误判为"图上没有箱"。故凡传正则类参数（`--fx-pattern` / `--title-pattern` / `--hu-pattern` / `--bldg-pattern` …）**一律写字符类**：`FX[0-9]+#?`、`([0-9]+)#楼`。

**判据**：命中数为 0 时先怀疑正则被吃，**不得据零命中改判图纸无此元素**（零命中 ≠ 无元素，与「空结果不得当成功消费」同则）。

## 4. 人工裁决批量改数 `apply-ruling`

裁决结论用 `ftth.py apply-ruling --json <assembly.json> --ruling <裁决清单.json>` 一次落数，**禁止为每条裁决现写临时脚本手改 JSON**。只做机械落数：缺字段不改、找不到目标硬失败并列出候选键；**裁决值须为绝对户数、含乘号一律拒绝**（`4*16` 须人工展开成 `64`）—— 乘号式 `*N`/`xN` 标注属**直读**形态、读数在解析阶段取出、不经裁决，脚本不做乘法。

**两种产物、两条通路**：出表输入 JSON（`--json assembly.json`）支持 `户数 / 安装楼层 / 覆盖范围 / 删除楼层 / 删除单元`；coverage 产物（`--json coverage.json`，含顶层「需人工裁决」）支持 `解除待裁决`。

**`解除待裁决`（2026-09-27 补）**：把已落盘的人工裁决**机械回灌**到 coverage 产物，消除恒消不掉的 `pending`（契约见 [operations_discipline.md](operations_discipline.md) §七.1/§七.5）。对象串须与清单里的**逐段一致**（楼栋/单元/箱，复用以 `parse_ruling_scope` 为唯一实现的分段口径，不做子串匹配）；`裁决人` 必填；命中项的 `阻塞` 置 `false` 并留痕，命中对象的箱 `result_confirmation` 置 `settled`（`result_origin` 不动）；**不删条目、不改「事项」文字**。示例：

```json
{"裁决": [{"类型": "解除待裁决", "对象": "4#配套楼/FX22#", "裁决原文": "-1f",
          "裁决人": "用户", "适用范围": "4#配套楼/FX22# 安装楼层"}]}
```

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

**产物**：写 `BDGMAP归属` 段（改派文字实例数 / 改派箱数 / 跨栋改派清单·每条带实例坐标 / 重号未改派 / 单元名并存）与顶层 `分纤箱提取状态`（0 箱时显式标注"须核是否总图对照表形态"）。旧 `改派条数` 为文字实例级计数（一百零二起拆分为两字段，不再使用）。

**无对照表图纸（absent）**：箱的楼栋 / 单元 / 安装楼层归属由**方法池**（区间法：编号文字 / 箱符号落楼层带；读取标注：图上直写）测定并逐箱写出依据，交人工复核 —— 不引入 y 坐标关联推算作来源。

## 9. 对照表认领箱的安装楼层为什么取口径A

`--bldg-map` 改派过来的箱，其编号写在**独立的总图对照表图区**，文字 y 与楼栋系统图的楼层刻度**不是同一坐标系** —— 拿它的 y 去套系统图楼层带会得出无物理意义的层号（实测出现过 `WF` / 高层号），并连带让 inspect 的 C3 双源交叉报不一致、C6 报覆盖不闭合。

**故**：对照表有**唯一**映射且带非空安装楼层时，`安装楼层` 取对照表值，口径标 `口径A:图上直写（总图对照表）`、来源标 `fxmap对照表`；区间法原值原样降级保留在 `区间法参考值` / `区间法参考误差` 两个字段供审计（证据不丢）。两条判据不同时成立则一切照旧 —— 不猜、不放宽。

**安装楼层口径因此共 5 个取值**：`口径A:图上直写`（本楼系统图内直写）、`口径A:图上直写（总图对照表）`（对照表直写、跨图区）、`口径B:区间法`（本楼系统图楼层带区间法）、`口径A′`、`口径B′`（后两者见下条双源标签区分）—— 输出中必须原样标注用的是哪一个。

**双源标签区分（一百零二）**：`BDG_MAP` 有两个填充源 —— ① `--bldg-map` 文件（extract_fx_map.py 产物，总图对照表，仅 present 时）；② 图上箱位直写证据（build_fx_direct_evidence，直写自证，absent 时补①未覆盖的编号）。逐箱标签**按实际填充源区分**：① 走现标签（`fxmap对照表` / `E-DXF-TEXT:总图对照表…`）；② 标 `箱位直写标注（fx_locations）` / `E-DXF-TEXT:图上箱位直写标注（N号楼M单元K层，…）`、口径 `口径A′:图上箱位直写标注（…）`。B′ 级（只到单元、安装层走区间法）落在区间分支时，依据来源标直写、不标对照表。数值语义（安装楼层值/误差/result 字段）不受影响，只修标签。


**待确认口径（2026-09-27二轮，与SKILL L1-C5对齐）**：对照表**唯一映射+非空安装楼层**的直写值走②类有客观判据自判（区间法原值降级留痕+C3双源交叉作第二来源），不另列待确认项；**非唯一映射/空值/重号**情形双方数值须一并列入待确认项交用户裁决。

**注意**：对照表值本质仍是「图上标注直读」来源；absent 时无对照表口径，但图上箱位直写证据（A′/B′，见 operations_discipline.md §五·补分档）仍可产出 settled 安装楼层 —— 标签须如上指向直写源，不得指向不存在的 fxmap.json。

## 10. `inspect --fx-pattern` 产物自描述

`inspect_closure.py` 的 `--fx-pattern` 内置默认是 `FL\d+-FX\d+`，与大多数图的编号形态不符。命令行未显式给出时，改用 parse 产物自带的 `参数.fx_pattern`（产物自描述）。**调用方不必再手工传该参数**，传了以命令行优先。

**此前的表现是**：流水线不转发 + 默认值不匹配 ⇒ C4 在 geom 文字里一个编号都搜不到 ⇒ 把 parse 侧**全部**箱误判成"图上无编号文字"（实测某图 23/23 全 FAIL 的纯假警报），把真 FAIL 整个淹掉。

**同理**：任何"用正则扫全图再与 parse 对账"的核查都必须先确认用的是**该图实际生效的那个正则**。

## 11. `ftth.py pipeline` 阶段顺序为什么固定

`geom → probe → plan → titleblock → fxmap → fx_locations → unit_gaps → parse → coverage → count_box → inspect`，`--stop-at` 的 choices 与之一致（**由 `ftth.py` 的 `_PIPE_STAGES` 单一定义**，本节仅为说明 —— 两者不一致时以代码为准并改本节）。

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
> 串跑入口与参数表见本文件 §18（2026-09-20 外移）；依赖矩阵/可抄示例仍在 `scripts_reference.md`。

### 17.1 `titleblock` 阶段（2026-09-18 实跑新增）

**做什么**：画像 `titleblock_annotation = present / variant` 时，调 `read_titleblock_households.py`
产出 `<outdir>/titleblock.json`（图签第二来源读数：栋级 `N层/M户每层` + `N单元`），
并由 `inspect` 阶段作为 **C10** 的输入透传（`--titleblock`）。

**为什么要有它**：画像早已把该信号判为 present 并写明「构成三来源协议的第二来源」，
但 `pipeline` 的阶段列表里没有它、当时的 C1~C9 也没有对应检查 —— **规则写在文档里、没有代码执行它**。
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

## 18. 流水线 `pipeline` 串跑入口（外移自 `scripts_reference.md`，2026-09-20）

> 外移原因：`scripts_reference.md` 达 48,915 B、距硬上限仅剩 85 B（`ftth.py budget` 二次信号）。
> 本节原文逐字搬入（2026-09-17 立）；依赖矩阵/可抄示例仍在 `scripts_reference.md`。

一条命令串跑 `geom → probe → plan → titleblock → fxmap → fx_locations → unit_gaps → parse → coverage → count_box → inspect`（以 `ftth.py` 的 `_PIPE_STAGES` 为准）。各阶段以子进程直调 `ftth.py`，
**不再经启动器 `ftth_launcher.py`**，固定启动开销只付一次。

```bat
ftth.py pipeline --dxf "<图.dxf>" --outdir "<产物目录>" --project-dir "<项目目录>"
```

**为什么要它（实测依据，非设计偏好）**：经启动器逐条直调时，**每条命令**都要固定付一份启动开销 ——
（以下为旧 `ftth.cmd` 启动器实测数据，2026-09-17 立；新版 `ftth_launcher.py` 已合并 cmd+_launch 两层，数值只会更低，定性结论不变）
`cmd` 批处理 0.78s + 探测 `-c "import ezdxf"` 1.93s（裸解释器 0.62s ＋ import ezdxf 1.31s）
+ `_launch.py` 1.13s + 调度层 `ftth.py` 0.65s ≈ **3.7s/条**，与图纸大小无关。
实测某图 6 个阶段逐条调用 **38.74s** → 本命令 **18.37s**（冷缓存 24.99s）。

| 参数 | 必需 | 含义 |
|---|---|---|
| `--dxf` | **必需** | 输入 DXF |
| `--outdir` | **必需** | 产物目录；各阶段用固定文件名落在此处（`config.json` / `profile.json` / `titleblock.json` / `fxmap.json` / `fx_locations.json` / `unit_box_gaps.json` / `parsed.json` / `coverage.json` / `inspect.json`），**之后仍可单条命令接着跑，或重跑其中一段** |
| `--project-dir` | 建议 | 透传给 `plan`，用于检测《楼宇信息采集表》。**不传会让 `intake_table` 留 `unknown`** |
| `--profile` | 可选 | 复用指定画像；默认 `<outdir>/profile.json` |
| `--stop-at` | 可选 | 跑到该阶段为止（`geom` / `probe` / `plan` / `titleblock` / `fxmap` / `fx_locations` / `unit_gaps` / `parse` / `coverage` / `count_box` / `inspect`，默认 `inspect`）；分阶段调试用 |
| `--reuse-geom` | 可选 | 几何缓存比 DXF 新时直接复用，不重跑 `dump_geom` |
| `--quiet` | 可选 | 各阶段输出写 `<outdir>/logs/<阶段>.log`，不刷屏；ftth.py 自身阶段级输出（跳过原因/既定处置/告警）同步 tee 写 `<outdir>/logs/pipeline.log`（一百零二起恒落盘，quiet 与否一致） |

> **`titleblock` 阶段 + 图层参数按子命令分派**（2026-09-18 实跑新增/修复）——
> 前者产出 C10 的输入（`read_titleblock_households.py` → `<outdir>/titleblock.json`），
> **非 0 退出不中止主链路**但 C10 随之判 SKIP；后者说明 `--wire-layer` / `--fx-symbol-layer` /
> `--bldg-map` **只有 `coverage` 消费**，传给 `coverage-vshape` 一律 `unrecognized arguments`
> **直接 rc=2**。细则见本文件 §17。

**语义边界（刻意约束，勿放宽）**

- **只解析、不做裁决，不含 `gen`** —— 出表必须等人工裁决（覆盖范围 / 安装楼层 / 待确认项），
  流水线**不得替人拍板**。
- **不静默续跑** —— 任一阶段 rc≠0 即停并**原样返回该 rc**；仅 **rc=3**（本图确实不提供该子任务数据，
  申报制）不中止，记为该阶段「不适用」。
- **覆盖方法由画像决定** —— 读 `handoff.②系统图选法.覆盖范围.脚本` 映射为 `coverage-vshape` / `coverage`，
  **不在此处二次推断**；画像申报 `absent` 时该阶段合法缺席（rc=3）。
- **rc=3 不豁免出表前置（2026-09-27 P1-2）** —— `rc=3`＝「本图不提供该子任务数据」，只允许**结束解析**，
  **不等于该字段可以跳过**。覆盖范围属标准地址表重要字段：`rc=3` → 覆盖零产出 → `inspect` **C6 FAIL**；
  即便有产物而 `判定依据=待确认` 也是 `pending` → **C9 FAIL**。两条都须走 L0-I4 / L1-C5 人工裁决并落盘，
  才允许 Step 4 出表（原文见 [coverage_rules.md §待确认](coverage_rules.md)）。
- **能力表门禁（2026-09-27 P0-1）** —— `plan` 之后立即核对「画像申报脚本 ∈ 本入口能力表
  （`ftth.py _PIPE_CAPABILITY`）」，不一致即 **rc=2 停下报人**；此前「映射不到」被当「本图不适用」
  静默跳过，最优证据反而把结果拦死（实测覆盖主线 `parse_dxf_structured.py` 无产出口）。
- 耗时台账落 `<outdir>/pipeline_timing.json`（逐阶段 rc ＋ 秒数）—— **排障与优化都以它为准，不凭印象**。
- **各阶段参数自洽**：`probe` 产物 `config.json` 同时作为 `--probe` 与 `--config` 传给 `plan`，
  再传给 `parse` / `coverage*`，与手工逐条调用等价；**校验口径不因走流水线而放宽**。

## 19. 批量编排 `ftth_batch.py`（外移自 `scripts_reference.md`，2026-09-26）

> 外移原因：`scripts_reference.md` 达 46,982 B、距预警线仅剩 18 B（`ftth.py budget` 实测）。
> 本节原文逐字搬入（2026-09-17 立）；子命令清单/依赖矩阵/可抄示例仍在 `scripts_reference.md`。

多张 DXF 时**不要逐图手敲、更不要自造批量脚本**：一个入口跑完
「逐图 probe → parse → coverage → merge_json 合并 → batch_overview 总览」。

### 快路径（所有图共用参数）

```powershell
python "$SK\scripts\ftth_launcher.py" ftth_batch.py --dxf 图A.dxf --dxf 图B.dxf --out-dir batch_out `
    --title-pattern "(\d+)#.*?系统图" --text-layer 文字
```

### 清单模式（每图独立参数）—— `--plan batch.json`

```json
{
  "out_dir": "batch_out",
  "common": {"--title-pattern": "..."},
  "items": [
    {"dxf": "C:/.../图A.dxf", "name": "图A",
     "common": {"--text-layer": "文字"},
     "parse": {"--hu-pattern": "(\\d+)户"},
     "coverage": {"--wire-layer": "WIRE"},
     "skip_coverage": false}
  ]
}
```

### 契约

| 项 | 约定 |
|---|---|
| 解释器 | 子进程 = **当前解释器**（启动器确认过带 ezdxf 的那个）；`--python` 可显式锁定；全程不裸调 `python` |
| 参数路由 | 先跑 `ftth.py <子命令> --help` 建各步骤参数表，透传参数**只转发给接受它的步骤**（如 `--vert-dx` 只进 coverage）；**无人接受 ⇒ 开工前 rc=2 报错**，防整轮子调用作废 |
| 禁传 | `--out`/`--out-dir` 由编排统一管理，透传即报错；`--plan` 与 `--dxf` 互斥 |
| --config 串联 | probe 成功的图，其输出自动作为该图 parse/coverage 的 `--config`（透传显式给了 --config 则不覆盖） |
| 容错 | 单图/单步失败**不中断**批次；`--skip-existing` 断点续跑（输出已存在且可解析即跳过）；`--timeout-sec` 单步超时（默认 3600） |
| 产物 | `<out_dir>/<图名>/<图名>_<step>.json`；`batch_overview.md`（人读总表）+ `batch_overview.json`（机读明细：命令行、rc、耗时、失败尾迹）；parse 有成功时自动 merge 为 `<批次名>_合并.json`（`--no-merge` 关闭） |
| 退出码 | 0=全部成功；1=部分失败；2=全部失败或前置错误（参数/清单/DXF 不存在）；`--dry-run` 只打印将执行的命令并写计划总览 |
| 重名 | 图名重复自动加序号（`图A`、`图A_2`） |
| 前缀匹配 | 本入口 argparse 已禁前缀缩写（`allow_abbrev=False`）：`--out` 不会被吞成 `--out-dir`，未知参数一律落入透传被拦截 |

> AI生成
