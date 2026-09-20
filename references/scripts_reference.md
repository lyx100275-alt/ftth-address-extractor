---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '822f8db2-6ad9-48a4-b5e8-af0bfa5573e5'
  PropagateID: '822f8db2-6ad9-48a4-b5e8-af0bfa5573e5'
  ReservedCode1: 'd8a39163-faa1-4dde-ba3f-0509f90aa61f'
  ReservedCode2: 'd8a39163-faa1-4dde-ba3f-0509f90aa61f'
---

# 脚本参数参考（外移自 SKILL.md，2026-09-16 瘦身）

> 全部脚本均支持 `--help`；本表为主要参数速查。SKILL.md 只留脚本名+一句话职责。

探查确定参数后，用ezdxf提取全部FTTH信息。**本 skill 附带 31 个脚本文件**（位于 `scripts/`：30 个 `.py` + 1 个 `.cmd` 启动器；含统一入口 `ftth.py`、公共模块 `ftth_common.py`、转发层 `_launch.py`、批量编排 `ftth_batch.py`）——**数量按 `ls scripts/ | wc -l` 实测填写，改文件后同步更新**：

| 脚本 | 作用 | 主要参数 |
|------|------|---------|
| `plan_methods.py` | **图纸画像（Step 1a 产物）**：13 信号判定 + 选法 + 档案一致率对比 + 门禁评估 | `--dxf --out --probe --project-dir --text-layer --text-type --title-pattern --fx-pattern --wire-keywords --vert-dx` |
| `dump_geom.py` | **全量几何转储（Step 1a 首步）**：文字/INSERT/线段 → `<DXF>.geom.json`；后续内联查询读此缓存，不回原图 | `--dxf --out` |
| `ledger_elements.py` | **元素台账（几何侧独立出口）**：六类元素（分纤箱/家居箱/线缆/楼层线/数据标注/文字标注）带坐标枚举 + 楼栋单元边界（锚点 x,y / x范围 / y分带）+ 校验。箱柜层取**专用层**（`EQUIP-` 前缀含安防/消防等非分纤箱设备，不取）；线缆候选**剔除建筑电气**层（照明/动力/接地/消防/安防…）；无单元标注时只给 x 聚类线索不臆造边界 | `--dxf --out --geom --config --parse --text-layer --title-pattern --unit-pattern --fx-pattern --hu-pattern --cable-pattern --box-layer-kw --box-attr-re --wire-layer --floorline-layer --verbose`（**`--wire-layer` 建议显式传**） |
| `parse_dxf_structured.py` | 结构化解析：楼栋/单元/分纤箱/楼层表/INSERT；退出码 **4**=探查/解析产物写入失败 | `--text-layer --text-type --title-pattern --floor-pattern --hu-pattern --cable-pattern --cable-keywords --fx-pattern --unit-pattern --unit-cluster --unit-range --y-tol --insert-blocks --insert-attrib-tag --insert-attrib-val --title-band-tol --consensus-x-tol` |
| `count_households.py` | 户数统计（皮线计数法：数皮线标注，系统图）——作为图标法的**对照口径**。同坐标重复绘制自动去重（键 `(x,y,内容)`）并报条数；楼层标注自洽性检查（同名多址 / 次序倒挂）；**出表守门**：尺度锚污染或全部皮线未归属时 rc≠0 | `--text-layer --text-type --title-pattern --floor-pattern --fiber-pattern --special-pattern --assign --match-tol --x-cluster --x-y-gap --probe --title-band-tol --max-unmatched-ratio --allow-lossy` |
| `count_box_icons.py` | **户数统计（家居配线箱图标法：图标贴皮线末端）**——不依赖块名、不要求图上写 HD/HDD；自动把平面图同名图标分离为 C 级不计入；`*N`/`xN` 乘数标注只告警不自行相乘；刻度列配对偏移异常（偏移与主偏移「最大簇中心」不成整数倍、相对偏离超容差）显式告警；门禁拦截时打印"皮线没找对 vs 图标非户级"诊断；**归层失败门禁**：贴末端图标 > 0 但「归层后总户数 = 0」⇒ **rc=2 且不写产物**（典型为「每层一个箱 + xN 乘数」形态：图标数 = 层数×单元数 ≠ 户数） | `--wire-layer --wire-keys --wire-exclude --insert-blocks --include-square --square-min --square-max --tol --search-radius --strong-keys --weak-keys --floor-layer --scale-max-dx --scale-period-tol（旧名 --scale-outlier-ratio 已弃用、不参与判定） --region-y --region-pad --col-x-tol --col-gap` |
| `analyze_coverage.py` | 覆盖范围判定（竖干连续体 + 物理断口，输出线索非结论） | `--text-layer --text-type --title-pattern --floor-pattern --fx-pattern --unit-cluster --vert-dx --vert-dy --fx-window --merge-tol --conn-tol --wire-layer --insert-attrib-tag --insert-attrib-val --bldg-map --bldg-pad --title-band-tol --fx-symbol-layer --fx-symbol-cluster --fx-symbol-max-size --symbol-pair-tol --total-pad --break-floor-tol --max-break-span` |
| `analyze_coverage_vshape.py` | 覆盖范围判定（皮线米数 V 形：谷底=安装层，相邻谷底中位=分界；只读文字不依赖线段图层） | `--text-layer --text-type --title-pattern --fx-pattern --box-mark-pattern --floor-pattern --hu-pattern --cable-pattern --cable-meters-group --cable-count-group --x-tol --col-x-tol-factor --min-col-rows --y-margin-factor --floor-x-tol --y-tol --box-x-tol --box-anchor-x-factor --dev-gate-factor --fx-locations --margin --include-basement`（几何容差一律以**字高中位**为尺度锚；`--box-mark-pattern` 供系统图只写「配线箱」不写编号的图作 V 谷底独立第二来源；`--box-anchor-x-factor` 为箱锚 x 邻域门禁；`--dev-gate-factor` 为 v底vs箱符号偏差可信门禁（×层高，超阈判不可信并登记裁决）；`--fx-locations` 引入箱位直读标注做安装层两来源交叉校验） |
| `verify_coverage_truth.py` | 用已定稿标准地址表**反查**覆盖范围线索（回归验收门禁） | `--sheet --col-box --col-bldg --col-unit --col-floor --col-door --json-key` |
| `gen_addressbook.py` | 由解析JSON+用户裁决 → 每户一行xlsx。覆盖 JSON 的单元键**双形兼容**（全名 `1#楼1单元` 与扁平 `1单元` 均可，失配时自检告警）；模板尾行按标识前缀去重（防止以产物为模板再出表时标识行累积） | `--dxf-json --out --coverage-json --template --addr --branch --sheet-name --cover-rule --floor-pattern --floor-format --door-format --fx-prefix-map --allow-lossy`（`--fx-prefix-map` 多图幅/多地块图纸的箱编号前缀归一，逐条留痕） |
| `merge_json.py` | 多楼栋解析JSON合并为嵌套结构 | `--inputs/--input-dir --out` |
| `extract_fx_map.py` | 分纤箱总图FX映射提取。**`--probe` 自带推荐**：未传 `--fx-pattern` 时按形状模板自动推荐（不再静默返回 0 条），未传 `--bldg-pattern` 时列出含"楼"文字的候选写法 | `--text-layer --fx-pattern --bldg-pattern --unit-pattern --floor-pattern --x-min --x-max --y-min --y-max --proximity-tol --probe` |
| `extract_fx_locations.py` | **箱位直读标注提取**（「N号楼M单元K层」→ fx_locations.json）：安装层最可靠的独立第二来源；按实例收录、同单元多安装层显式登记；定位是交叉校验数据源，不自动替代任何方法结果 | `--dxf --text-layer --pattern --out` |
| `split_units.py` | 多单元楼层户数拆分 | `--input --rules --out` |
| `split_bands.py` | **多地块按 y 带裁剪子 DXF**（`ftth.py split-band`）：同名楼分带解析前置；带重叠告警（重复计数风险）、空带早失败 rc=2 | `--dxf --out-dir --band（名称:ymin:ymax，可重复/逗号分隔）` |

**probe 顶层画像信号**：`ftth.py probe` 的输出 JSON 除 `suggested_params` 外，还在顶层携带四个画像信号（非命令行参数；plan 会透传进 `profile.probe_signals` 并日志提醒）：

| 信号 | 含义 | 下游动作 |
|------|------|---------|
| `titleblock_layer_candidates` | 按图层统计「N层/M户、NF+户/层、N单元」命中给出的图签候选图层 | `read_titleblock_households.py --floor-layer` 候选，免试错 |
| `plot_band_annotations` | 地块/分带标注清单（内置通用词表 块地/地块/块区/组团/分区，含缺号提醒） | **文件名不等于地块划分**：一张图可含多个独立地块、楼号各自从 1 起。检出时 read_titleblock / coverage 应按带（`--band`）分别运行，避免跨地块同名楼混叠；该信号只提醒、不阻塞 |
| `fx_location_annotation` | 「N号楼M单元K层」箱位直读标注 present/absent | present 时跑 `extract_fx_locations.py`，并给 `coverage-vshape --fx-locations` 做交叉校验 |
| `fx_symbol_layer_candidates` | 分纤箱**图形符号层**候选（按得分降序，含 一致性 / 标题区重叠 / 众数尺寸 / 层高依据 明细）。判据：闭合四点矩形 + 尺寸一致性 + 与「图纸类词标题 x 带」重叠 + 众数簇数量≈编号数，全部随图自适应 | **取【推荐】项填 `analyze_coverage.py --fx-symbol-layer`**，不要自行猜图层名；plan 亦写入 `profile.json` 的 `param_source.must_probe.fx_symbol_layer`。箱体只写编号、不画符号的图本项为空 |

**多地块 / 多图幅编排（2026-09-16 补）**：`ftth.py` 的 `--dxf` 是**单值**。当项目含多张 DXF、
或一张 DXF 含多个独立地块（`plot_band_annotations` 检出多个地块标注、各楼号从 1 起）时：

1. **多张 DXF** —— 对每张图**各跑一遍** `probe → plan → parse`，产物按图命名（如 `probe_<图名>.json`），
   最后用 `merge_json.py --inputs ... --out 合并.json` 汇总。**不需要**自行切割 DXF 文件。
2. **一图多地块** —— 优先用按带参数逐带运行（`read_titleblock_households.py --band`）；
   确需物理拆分时用 `ftth.py split-band`（2026-09-17 起内建，原临时脚本转正）：`--band "名称:ymin:ymax"`，y 带口径同 `read_titleblock_households.py --band`（上界=上邻带标题 y、下界=中点）。全图 parse 命中同名楼守卫（rc=3）时按报错指引走此步。
3. 判据来自 `probe` 顶层信号 `plot_band_annotations`（画像里为 `profile.probe_signals`）——
   **不要凭文件名推断地块划分**。


## `ftth.py` 子命令 × 上游产物 依赖矩阵（2026-09-16 新增）

**先读这张表再写命令**，不要用 `--help` 试错。
`必需` = 不传即报错；`可选` = 传了才启用对应口径/校验；`—` = 该子命令无此参数。

| 子命令 | 调度的脚本 | `--dxf` | `--config` | `--probe` | `--profile` | `--parse` | `--coverage` | `--geom` | `--count-box` | `--fx-locations` | 位置参数 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `probe` | parse_dxf_structured | **必需** | 可选 | — | — | — | — | — | — | — | — |
| `plan` | plan_methods | **必需** | 可选 | 可选（强烈建议） | — | — | — | — | — | — | — |
| `parse` | parse_dxf_structured | **必需** | 可选 | — | 可选（门禁） | — | — | — | — | — | — |
| `coverage` | analyze_coverage | **必需** | 可选 | — | 可选（门禁） | — | — | — | — | — | — |
| `coverage-vshape` | analyze_coverage_vshape | **必需** | 可选 | — | 可选（门禁） | — | — | — | — | 可选 | — |
| `count` | count_households | **必需** | 可选 | — | 可选（不门禁） | — | — | — | — | — | — |
| `count-box` | count_box_icons | **必需** | 可选 | — | 可选（不门禁） | — | — | — | — | — | — |
| `assemble` | assemble_households | — | 可选 | — | — | — | 可选 | — | — | — | — |
| `apply-ruling` | apply_ruling | — | 可选 | — | — | — | — | — | — | — | — |
| `inspect` | inspect_closure | — | 可选 | — | — | **必需** | 可选 | 可选 | 可选 | — | — |
| `gen` | gen_addressbook | — | 可选 | — | — | **必需** | 可选 | — | — | — | — |
| `verify-truth` | verify_coverage_truth | — | 可选 | — | — | — | — | — | — | — | `xlsx` `covjson` |
| `split-band` | split_bands | **必需** | — | — | — | — | — | — | — | — | — |
| `pipeline` | 串跑 8 个阶段 | **必需** | — | — | — | — | — | — | — | — | 见下方专节 |

**同义参数（2026-09-16 统一；两种写法等价，推荐左侧）**

| 上游产物 | 统一名 | 旧别名 | 出现在 |
|---|---|---|---|
| `parse` 输出的 JSON | `--parse` | `--dxf-json` | `inspect` / `gen` |
| `coverage` 输出的 JSON | `--coverage` | `--coverage-json` | `inspect` / `gen` |

**易错点（实测踩过）**
- `coverage-vshape` **只读文字标注**，没有 `--parse` / `--coverage` 参数；传了即
  `ftth.py: error: unrecognized arguments`。需要箱位交叉校验时用 `--fx-locations`。
- `coverage` 是**几何路线**：**必须显式传 `--wire-layer`**；图上含分纤箱总图时加 `--bldg-map`；
  系统图只画箱符号不写编号时加 `--fx-symbol-layer`（层名取 probe 的 `fx_symbol_layer_candidates` 【推荐】项）。
- `inspect` 与 `gen` **豁免 `--dxf`**（只吃上游 JSON）；`verify-truth`、`assemble`、`apply-ruling` 同样豁免，`verify-truth` 改用位置参数。
- `assemble` 另有两个独有必填参数 `--count`（count_box 输出）与 `--col-map`（列归属映射，语法见下文专节）；
  上表未单列。`count` 的 `--out` 等子命令自有参数同样不在表中，以各子命令报错提示为准。
- `apply-ruling`（2026-09-18 新增）独有参数 `--json`（待改数的出表输入 JSON，必填）与 `--ruling`（裁决清单 JSON）；
  可用 `--set "楼栋/单元/楼层=户数"` 简写代替清单文件。见下方专节。
- `--profile` 的含义分两档：`parse` / `coverage` / `coverage-vshape` 上是**门禁**（`unknown` 信号 ⇒ rc=2 中止）；
  `count` / `count-box` 上**仅接受不报错**，不做门禁。
- `gen --addr` 留空（前5级地址不填）时，**PowerShell 会丢弃空字符串参数**：`--addr ""` 传给原生 exe 后 argparse 报 `expected one argument`，无论经 `ftth.cmd` 启动器还是直调 `python.exe` 均如此（PowerShell 对 native 调用的已知行为，非脚本缺陷）。**变通**：传 `--addr ",,,,,,"`（逗号分隔的空值串），脚本内部 `split` 后得空列表，效果等同留空。

### 各子命令可直接抄的完整示例

> **优先用启动器**：`& "$SK\scripts\ftth.cmd" <子命令> [参数...]`，直调脚本同写
> `& "$SK\scripts\ftth.cmd" dump_geom.py --dxf $D` —— 启动器自己探测带 ezdxf 的解释器，**无需填 `$PY`**。
> 下列 `& $PY ...` 是**等价显式写法**（非 Windows 环境、或需锁定某个解释器时用）。

```powershell
$SK = "<...>\skills\ftth-address-extractor"        # 启动器写法只需它
$PY = "<绝对路径>\python.exe"                       # 显式写法才需要（见「解释器契约」，禁止裸 python）
$D  = "C:\...\图纸.dxf"
$T  = "C:\...\.temp\<项目>"

# 1) probe —— 探查，产出建议参数
& $PY "$SK\scripts\ftth.py" probe --dxf $D --out "$T\probe.json"

# 2) plan —— 图纸画像（选法 + 门禁）；带 --probe 回填检测类参数，别省
& $PY "$SK\scripts\ftth.py" plan --dxf $D --probe "$T\probe.json" --out "$T\profile.json"

# 3) parse —— 结构化解析（带 --profile 走门禁）
& $PY "$SK\scripts\ftth.py" parse --dxf $D --config "$T\probe.json" --profile "$T\profile.json" --out "$T\parse.json"

# 4) coverage —— 几何路线（必须显式 --wire-layer；有总图映射时加 --bldg-map）
& $PY "$SK\scripts\ftth.py" coverage --dxf $D --wire-layer "<皮线/光缆图层，逗号分隔>" --bldg-map "$T\fx_map.json" --profile "$T\profile.json" --out "$T\coverage.json"

# 5) coverage-vshape —— 皮线米数 V 形路线（只读文字；不吃 parse/coverage 产物）
& $PY "$SK\scripts\ftth.py" coverage-vshape --dxf $D --profile "$T\profile.json" --fx-locations "$T\fx_locations.json" --out "$T\coverage.json"

# 6) count —— 皮线计数口径
& $PY "$SK\scripts\ftth.py" count --dxf $D --profile "$T\profile.json" --out "$T\count.json"

# 7) count-box —— 家居配线箱图标口径（图上存在家居箱图标时优先用它）
& $PY "$SK\scripts\ftth.py" count-box --dxf $D --wire-layer "<皮线图层>" --profile "$T\profile.json" --out "$T\count_box.json"

# 8) inspect —— 出表前一体化闭合核查（豁免 --dxf，只吃上游 JSON）
& $PY "$SK\scripts\ftth.py" inspect --parse "$T\parse.json" --coverage "$T\coverage.json" --geom "$D.geom.json" --json "$T\inspect.json"
#    有图签读数时追加 --titleblock "$T\titleblock.json"，C10 才做「图签 vs 系统图」逐栋互证；
#    不传则 C10 判 SKIP 并写明「本次未做交叉校验」（SKIP ≠ 通过）

# 9) assemble —— 出表输入 JSON 组装（count-box 路线；豁免 --dxf；独有必填 --count/--col-map）
& $PY "$SK\scripts\ftth.py" assemble --count "$T\count_box.json" --col-map "0=1#楼/1单元;1=2#楼/1单元,2#楼/2单元" --coverage "$T\coverage.json" --out "$T\assembly.json"

# 10) gen —— 出表（豁免 --dxf；楼层/户号格式默认按模板示例行自动判定，可用 --floor-format/--door-format 显式指定）
& $PY "$SK\scripts\ftth.py" gen --parse "$T\parse.json" --coverage "$T\coverage.json" --template "$SK\assets\标准地址表模板.xlsx" --addr "省,市,区,街道,小区" --floor-format chinese --out "C:\...\标准地址表.xlsx"

# 11) verify-truth —— 回归验收（位置参数，豁免 --dxf）
# 12) split-band —— 多地块分带（parse 报「多地块同名楼」rc=3 时走这步，产出按带子 DXF 后逐带 parse）
& $PY "$SK\scripts\ftth.py" verify-truth "C:\...\标准地址表.xlsx" "$T\coverage.json"
```

## probe 产物键结构

`ftth.py probe --out probe.json` 写出的三个顶层区：

| 顶层键 | 内容 | 下游消费 |
|---|---|---|
| `suggested_params` | 建议参数（键名＝子命令参数名；仅键名合法者会被 `--config` 回填） | 各子命令的 `--config` |
| 画像信号（4 个） | `titleblock_layer_candidates` / `plot_band_annotations` / `fx_location_annotation` / `fx_symbol_layer_candidates` | `plan --probe` → `profile.probe_signals` |
| `全量文字样例` | 全图文字条目数组（探查/画像/排查共用素材） | 人工排查、方法判据 |

`全量文字样例` 的**条目键**（勿猜键名）：

| 键 | 类型 | 说明 |
|---|---|---|
| `层` | str | 图层名 |
| `类型` | str | 实体类型（`TEXT` / `MTEXT` 等） |
| `内容` | str | 文字内容 |
| `x` / `y` | float | 插入点坐标（图纸原坐标） |

读法约定：文件为 **UTF-8**；条目常达千级（单图实测千余条），
按尺寸/按行受限的 JSON 解析器（如 `ConvertFrom-Json`）会报 `Invalid object passed in`，
**一律用 Python `json.load` 读**。

**`*_note` 结尾的键是提示性键**（不是任何子命令的参数，如 `fx_pattern_note` 携带串号风险提示）：
`ftth.py --config` 跳过它们并以 `[config-info]` 原样透传，不计入 `[CONFIG-IGNORED]`。

## 统一入口外的直调脚本

以下脚本**直接调用**、不经 `ftth.py` 入口（用法见各自 `--help`）：

| 脚本 | 作用 |
|---|---|
| `read_titleblock_households.py` | 图签形态栋级入户规模读取（`N层/M户`+`N单元` 成对标注）。退出码 0 正常；1 参数/信号缺失；2 比对不一致；**3 提取不完整（有楼名零层户数据，禁止当完整结果用，`--allow-partial` 可放行）** |
| `gen_9level_addressbook.py` | 九级地址树出表 |
| `probe_titleblock_tolerances.py` | 图签几何容差量测（缺省自适应，推定值写入结果 JSON） |
| `inspect_closure.py` | 出表前一体化闭合核查 C1~C10（`ftth.py inspect` 可调度；只读 JSON，豁免 `--dxf`） |
| `ftth_batch.py` | **多图批量编排**（probe→parse→coverage→合并→总览；契约见下 §批量编排） |
| `ledger_state.py` | **状态台账（会话侧）**：理解快照 / 裁决台账 / 别名台账三本台账的读写载体（子命令 `init`/`snapshot-set`/`snapshot-get`/`ruling-add`/`alias-add`/`pending`/`check`）。退出码：0 正常；**2 有未裁决项或别名归属冲突**；3 未初始化 / 台账损坏 / 参数错误。口径见 [operations_discipline.md](operations_discipline.md) §六~§九 |

### 脚本级机器护栏（2026-09-17，判据通用、与项目无关）

| 护栏 | 触发条件 | 行为 |
|---|---|---|
| `parse_dxf_structured.py` 正则组自检 | `--title-pattern`/`--hu-pattern`/`--unit-pattern` 少于 1 个捕获组，或 `--cable-pattern` 少于 2 个 | 编译后立刻 rc=1 显式报错并给正确形态示例（替代解析期 `IndexError` 裸崩） |
| `ftth.py` 配置键忽略汇总 | `--config` 含当前子命令无效的键 | 逐键 WARN 之外，用固定 token **`[CONFIG-IGNORED]`** 汇总重申（可 grep）；设环境变量 `FTTH_STRICT_CONFIG=1` 时 rc=3 硬失败 |
| `read_titleblock_households.py` 零数据楼 | 有楼名标注的楼一条层户/单元都没配上 | `[ERROR]` 列楼名+坐标，rc=3（自适应容差失准静默丢整地块的实测坑，与容差来源无关） |
| `read_titleblock_households.py` 单元归属歧义 | 一条单元标注容差内命中 ≥2 栋楼 | 列候选楼与偏移证据；判据不变（仍「最近者胜」），串楼风险交人核对 |
| `read_titleblock_households.py` 重复单元标签 | 某楼某标签次数 > 本图基准绘制次数 | 报「多收了别人的标注」（如串标 `1单元×4` vs 基准×2；正常重复绘制不误报） |

## 出表输入组装 `assemble`（count-box 路线，2026-09-17 新增）

`ftth.py assemble` 把 count_box 口径的逐层户数 + coverage 分纤箱信息，机械合并为
`gen` 可直接消费的 JSON（`楼栋→单元→{楼层表,分纤箱}`）。**凡户数来自 count_box 的图，
出表输入一律用它组装，不要自造组装脚本**（实测每会话自造一份、且各自烧掉数轮 edit 修正）。

```
ftth.py assemble --count <count_box.json> \
    --col-map "0=1#楼/1单元;1=2#楼/1单元;8=7#楼/1单元,8#楼/1单元,10#楼/1单元" \
    --coverage <coverage.json> --out <assembly.json>
```

- `--col-map` 语法：分号分隔条目；每条 = `列号=楼栋/单元[,楼栋2/单元2,...]`，列号为
  count JSON「列」数组 0 基下标。单元槽写 `N单元`、`楼栋N单元` 全名或省略（裸楼栋名 =
  单单元楼，归一 `1单元`，与 gen 的单元键归一规则一致）。
- **一列映射到多个单元 = 共享系统图克隆**（同一份逐层户数复制给各单元）——这属于图纸
  事实判断，脚本只机械执行并显式打印克隆留痕，是否符合图纸由调用方核对。
- **列→单元的归属映射是裁决项，脚本不做任何自动猜测**（count JSON 的列只有列 x + 逐层
  户数，不含楼栋归属；归属依据 = 列 x 与箱符号/楼栋边界的几何对齐，属判读结论）。
  语法错误 / 列号越界 / 同一 (楼栋,单元) 被两列声明（户数会翻倍）一律硬失败 rc=1。
- `--coverage`（可选）合并各单元分纤箱（嵌套/扁平两种格式自动检测）；coverage 单元键
  归一后仍对不上时回退 `1单元`——**仅当该楼栋确有 1单元**（单单元楼/配套楼的 coverage
  键常写非 N单元 形式），仍对不上则显式列出交人核对，不静默丢。
- 守恒打印：逐单元户数与箱号、合计户数、count 归层总户数、共享列克隆增量；
  **合计−归层总数 应恰等于克隆增量**，不等 = col-map 有漏（部分映射时差值会大声报数）。
- 输出给 gen 时 `--parse assembly.json`；分箱归属仍按 gen 侧规则（单箱单元自动全配，
  多箱单元用用户裁决后的覆盖 JSON）。

## 人工裁决批量改数 `apply-ruling`（2026-09-18 新增）

**裁决结论一律用本子命令落数，禁止为每条裁决现写临时脚本手改 JSON**
（实测某会话为此造了 17 个脚本、耗 27 分钟，且改完无留痕不可复现）。

```
ftth.py apply-ruling --json <assembly.json> --ruling <裁决清单.json> [--out <out.json>] [--force] [--dry-run]
ftth.py apply-ruling --json <assembly.json> --set "1#楼/1单元/3层=4" --dry-run     # 简写，可重复传
```

裁决清单格式（顶层 `{"裁决":[...]}` 或直接是数组）：

| 类型 | 必填字段 | 作用 |
|---|---|---|
| `户数` | 楼栋 / 单元 / 楼层 / 值 | 改写该层户数（值须为整数） |
| `安装楼层` | 楼栋 / 单元 / 箱 / 值 | 改写指定箱的安装楼层 |
| `覆盖范围` | 楼栋 / 单元 / 箱 / 值 | 改写指定箱的 `覆盖范围线索` |
| `删除楼层` | 楼栋 / 单元 / 楼层 | 删除该层 |
| `删除单元` | 楼栋 / 单元 | 删除该单元 |

- `单元` 省略 = 对该楼栋**全部单元**生效（共享系统图克隆的全改场景）。
- `箱` 按 `编号` **精确匹配**，不模糊匹配。
- **裁决值含乘号（`4*16`）一律拒绝 rc=1**：乘数是裁决项，须人工展开成绝对户数（写 `64`），脚本不做乘法。
- 找不到目标（楼栋/单元/楼层/箱）**硬失败并列出当前存在的键**，不猜、不静默跳过。
- 写保护：`--out` 省略 → 写 `<原名>_patched.json`；`--out` 与输入同路径 → 须显式 `--force`（否则 rc=2）；
  `--out` 指向的已存在文件 → 默认改道 `*_patched`。派生覆盖原产物一律要 `--force`。

## 批量编排 `ftth_batch.py`（多图/多地块，2026-09-17 新增）

多张 DXF 时**不要逐图手敲、更不要自造批量脚本**：一个入口跑完
「逐图 probe → parse → coverage → merge_json 合并 → batch_overview 总览」。

### 快路径（所有图共用参数）

```powershell
& "$SK\scripts\ftth.cmd" ftth_batch.py --dxf 图A.dxf --dxf 图B.dxf --out-dir batch_out `
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

## `geom.json` schema（v3，外移自 SKILL.md）

| 键 | 元素结构 | 说明 |
|---|---|---|
| `texts` | `[图层, x, y, 文本]` | **注意是「图层」在首位**，不是文本 |
| `inserts` | `[图层, x, y, 块名, 图层]` 五元组 | 保持向后兼容 |
| `insert_attrs` | `[{tag: value} \| None, ...]` | 与 `inserts` **同索引**的块属性（v3 新增） |
| `segs` | `[图层, x1, y1, x2, y2]` | **逐段**线段，非多段线整组顶点 |
| `polylines` | `[图层, [x1,y1,x2,y2,...], closed]` | **整组顶点**不拆段，`closed` 为 0/1（v3 新增） |
| `layers` / `bbox` / `n_entities` / `_src` | — | 图层计数 / 包围盒 / 实体数 / 源文件校验 |

`_src` 含源文件 `mtime+size+GEOM_VERSION`，图纸或结构版本变化即缓存失效。

## 环境与命令纪律（外移自 SKILL.md，2026-09-16 第二次瘦身）

### 解释器契约（开工第一件事：先定 `$PY`，再干别的）

**铁律：本技能所有脚本一律用「绝对路径解释器」调用，禁止裸 `python` / 裸 `py`。**

**为什么**（实测结论，换机同样成立）：Agent 宿主（如 TeleAgent）通常把自己附带的 Python runtime
前置到 PATH，使裸 `python` 解析到**该 runtime** —— 它既没有 `ezdxf`，`pip` 也补不上。
裸 `python` 一旦命中它，每个脚本都会 `ModuleNotFoundError: No module named 'ezdxf'`。
`py` 启动器虽然按注册表选择解释器（不受 PATH 影响），但宿主环境可能没装它、或默认版本不含依赖，
同样不可依赖。

**首选：直接用启动器 `scripts/ftth.cmd`，不必自己探测解释器**

```powershell
$SK = "<...>\skills\ftth-address-extractor"
& "$SK\scripts\ftth.cmd" <子命令> [参数...]      # -> scripts\ftth.py <子命令> ...
& "$SK\scripts\ftth.cmd" dump_geom.py --dxf $D   # -> scripts\dump_geom.py --dxf ...
```

| 项 | 约定 |
|---|---|
| 参数分派 | **首参以 `.py` 结尾 ⇒ 转发该脚本**（相对/绝对路径均可，`scripts\` 前缀可写可不写）；否则转发 `ftth.py <首参> ...` |
| 解释器探测 | 按候选清单**逐个真执行**（`<exe> -c "import ezdxf"`）命中即停：`$env:LOCALAPPDATA` / `$env:ProgramFiles` / `%SystemDrive%` 下 `Python311~313` → `py -3.13 / -3.12 / -3.11 / -3` → PATH 上的 `python` |
| 指定解释器 | 设 `FTTH_PYTHON=<python.exe 绝对路径>`，优先级**高于全部候选**；该路径不带 ezdxf 时自动回落继续探测 |
| 退出码 | 透传目标脚本的退出码；**全部候选失败 ⇒ `exit /b 9`** 且打印候选清单与处置办法 |
| 参数保真 | **不重排、不改写参数**，含空格/中文的引号原样透传 |

> 非 Windows 环境、或需锁定某个解释器时，再用下面的显式 `& $PY ...` 写法。

**第一步：确定可用解释器**（一次成本，确认后本会话复用，勿反复探测）

```powershell
# 候选清单按优先级探测，命中即停；<venv> 换成项目自带虚拟环境（若有）
$cands = @(
  "<venv>\Scripts\python.exe",                                # 1. 项目虚拟环境（最优先，若有）
  "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",  # 2. 用户级 Python 3.13
  "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",  # 3. 用户级 Python 3.12
  "$env:ProgramFiles\Python313\python.exe",                   # 4. 机器级
  "$env:ProgramFiles\Python312\python.exe"
)
$PY = $null
foreach ($c in $cands) {
  if (Test-Path $c) {
    & $c -c "import ezdxf, openpyxl" 2>$null
    if ($LASTEXITCODE -eq 0) { $PY = $c; break }
  }
}
if (-not $PY) { Write-Error "未找到带 ezdxf 的解释器，请人工指定后继续"; return }
& $PY -c "import sys; print('PY =', sys.executable)"   # 回显确认，务必核对
```

**必须用「真执行」验证**（`& $<候选> -c "import ezdxf"`），只 `Test-Path` 判断存在性会选到没依赖的解释器。
确认后本会话所有调用统一写 `& $PY "<skill>\scripts\<脚本>.py" ...`。

**⚠️ 不要试图用 `pip install` 补依赖**：
- 装进宿主 runtime 属污染程序自管辖目录，且宿主可能重置，不一定持久生效；
- **镜像陷阱**：网络环境有代理/受限时，指定第三方镜像（如清华源）会报
  `ERROR: Could not find a version that satisfies the requirement ezdxf (from versions: none)`。
  这条报错**看起来像「包不存在」，实际是「索引不可达」**，极具误导性 —— 别在此浪费轮次。
  确需安装时**先用默认源验证可达**：`& $PY -m pip index versions ezdxf`。

### 必须具备的软件环境

| 工具 | 用途 | 验证命令（用 `$PY`） |
|------|------|---------|
| ODA File Converter (≥27.1) | 用户侧 DWG→DXF 转换（助手不调用） | 检查安装目录存在 |
| Python 3.x + ezdxf | DXF 解析 | `& $PY -c "import ezdxf; print(ezdxf.__version__)"` |
| openpyxl | 生成 xlsx 成品 | `& $PY -c "import openpyxl"` |
| xlrd | 读取 .xls 模板（模板为 xlsx 时不需要） | `& $PY -c "import xlrd"` |

ODA 转换由用户完成。

**PowerShell 输出编码纪律**：PowerShell 的 `>` 重定向默认产出 UTF-16 文件，直接读取会失败或乱码。
- 脚本产物一律由 Python 自己写文件（`open(path, "w", encoding="utf-8")`），**不要用 PowerShell 重定向落盘**。
- 确需读 PowerShell 重定向产物时，先转码（UTF-16 → UTF-8）再读，勿用 read 工具硬读。

## 元素台账 `ledger_elements.py` 输出字段（六类元素 + 边界 + 校验）

`parse` 输出**业务树**（楼栋→单元→分纤箱/楼层表），不落盘几何边界；本文件是**几何侧独立出口**，
两路互不覆盖。产物默认 `<DXF>.ledger.json`。

| 顶层键 | 内容 |
|------|------|
| `参数` / `参数来源` / `参数说明` | 每项写明是「命令行传入 / probe 配置 / 按图推断」，图层类另附命中与被排除层数 |
| `元素台账.分纤箱` | `文字编号`（**权威计数**，短标签形态过滤后过编号正则，带完整 (x,y)）、`箱柜图层图标`（**超集**，含非分纤箱设备，只作第二来源）、`对账`、`数量`、`x范围`/`y范围` |
| `元素台账.家居箱` | 箱柜层 INSERT 的**块属性值**判据（`A=家居配线箱` / `$TEXT$=HDD` 等）→ `属性命中数` / `按属性值分组` / 逐条坐标。与「图标贴皮线末端」的图标法互为独立来源 |
| `元素台账.线缆` | `采用图层` / `图层线段数` / `线段数` / `多段线数` / `候选全谱`（含"被排除"标记）/ `被排除图层` |
| `元素台账.楼层线` | `图层` / `水平段数` / **`楼层线y清单`**（按 y 聚类）/ `推断层高`。有该图层时是 `floor_scale` 的**独立几何第二来源**；无则登记缺项并回落楼层文字 y |
| `元素台账.数据标注` | `分类计数`：户数 / 皮线米数 / 芯数 / 楼层 / 单元 / 分纤箱编号 / 图纸标题，逐条带 (x,y) |
| `元素台账.文字标注` | 其余文字（设备名/说明/图例/路径），数量 + 范围 + 样例 |
| `楼栋单元边界` | 逐栋：`锚点{x,y}`、`x范围`、**`y带`**（逐带 y范围/文字数/主带标记）、`单元[]`（`锚点`/`x范围`/`已夹回楼栋边界`/`y带`）、`单元线索` |
| `校验` | `坐标完整性`（逐类总数与缺 x/y 数）、`单元越出楼栋`、`区间重叠`（**分型**：共享锚点 / 异锚点 / 单元）、`共享锚点组`、`必须修的边界问题合计`、`边界缺项`、`结论` |
| `缺项` / `待确认` | 缺失元素 + 降级路径；需人工确认的事项（如线缆图层认定） |
| `与parse对账` | 传 `--parse` 时给出「parse 分纤箱数 / 台账文字编号数 / parse 缺 x 条数」 |

> **退出码门禁**：rc=0 正常；**rc=2 = 有坐标缺失或「必须修」边界问题 ⇒ 不得直接出表**，
> 先按 `校验.必须修的边界问题合计` 清单处理后再出表。

**三条判据为什么这样定（实测证据，换图仍适用）**
1. **箱柜层取专用层**：宽泛 `EQUIP-` 前缀下还有 `EQUIP-安防`(51) / `EQUIP-消防`(5)，
   与箱柜混算会把「分纤箱」数量抬高一个量级；图形侧一律标为**超集**、不参与计数裁决。
2. **y 必须分带**：同一楼栋 x 带内的文字可来自系统图与平面图两个**不连续**图区，
   取全局极值会得到跨数万单位的假 y 范围；改按 y 聚类逐带登记并标出含锚点的主带。
3. **重叠要分型**：同一句共享标题（如「7#、8#楼…系统图」）展开出的多栋**锚点 x 相同**、
   x 范围**由构造相同** —— 这是「边界不足以区分这几栋」，**不是切分错误**；
   只有**异锚点**且同行带的重叠才是必须修的切分错误。（判据取 **x** 即可：x 范围由 `compute_bldg_ranges(锚点x)`
   唯一决定，与 y 无关；按 (x,y) 全同判会漏掉标题重复绘制 y 差十几单位的情形。）

## 户数取法的图纸形态判别（2026-09-16 实测立）

户数一律锚在**家居配线箱**上；皮线只作**定位/校验**，不作计数来源。实测四类形态：

| 形态 | 图面特征 | 判据 | 动作 |
|------|---------|------|------|
| **A 逐户画箱** | 每户一个箱图标，块属性 `A=家居配线箱` | 图标数 = 户数 | `count-box` 直接数 |
| **B 每层一箱 + 乘数** | 每层/每单元一个箱 + `xN` 标注 | 图标数 = 层数×单元数 ≠ 户数 | `count-box` 归层为 0 ⇒ **rc=2 拦断**；改走图签参数法（`read_titleblock_households.py`）或按乘数口径人工裁决 |
| **C 示意箱 + 数量标注** | 箱为示意、旁标 `N户` | 读 `N户` 求和 | `--hu-pattern` 直读；**不得**用图标数（会差数倍） |
| **D 非户数图** | 光交面板 / 杆路路由图：无家居箱、无线缆图层 | 不适用 | `count-box` 在皮线门禁处即 rc=2；应改判「图纸类型不符」而非「识别有误」 |

**三条铁律**

1. **「图上有箱」不能推出「能数箱」** —— 四种形态里箱都存在，但只有 A 能直接数；
   B 的箱是「层」的计量单位，C/D 的箱是示意。
2. **`N户` 采样判据是严格全匹配** `fullmatch(\d+户)`：`N户/层`（复合语义）、
   `共覆盖住户N户。`（总述）等形态**天然被排除**，不会误取；无需另设排除表。
3. **归层失败必须 rc≠0** —— `贴末端图标 > 0 且 归层后总户数 == 0` 是「没测出来」，
   不是「0 户」。原实现会 rc=0 写出总户数 0，下游按成功消费即得空表。

## 流水线 `pipeline`（已外移 → [pipeline_details.md §18](pipeline_details.md)，2026-09-20）

> 本节原在此处（2026-09-17 立）。因本文件 48,915 B 距硬上限仅剩 85 B，串跑入口、参数表与语义边界已外移至 [pipeline_details.md §18](pipeline_details.md)；依赖矩阵/可抄示例仍在本文件。


## 统一入口 `ftth.py` 与 `--config` 机制（外移自 SKILL.md，2026-09-17 第三次瘦身）

**`ftth.py` 统一入口与 `--config` 机制**：

`ftth.py` 是统一调度入口，支持 `probe/plan/parse/split-band/coverage/coverage-vshape/inspect/verify-truth/assemble/apply-ruling/count/count-box/count-hdd/gen/pipeline/budget/transitions` 十六个子命令。各子命令参数默认值为 `None`（不硬编码），通过以下优先级填充：

1. **命令行显式指定**：最高优先级，直接使用
2. **`--config` 自动填充**：传入 `probe` 子命令输出的 `suggested_params` JSON，自动填充未在命令行指定的参数
3. **子脚本内置默认值**：若命令行和 config 均未提供，使用子脚本自身的 argparse 默认值

典型工作流：`ftth.py probe --dxf 图纸.dxf --out config.json` → `ftth.py plan --dxf 图纸.dxf --probe config.json --out profile.json`（**选法，第一步产物**）→ `ftth.py parse --dxf 图纸.dxf --config config.json --profile profile.json`，探查结果与图纸画像共同透传到解析步骤。

多张DXF时不要逐图手敲，用批量编排入口：`& "<技能目录>\scripts\ftth.cmd" ftth_batch.py --dxf 图A.dxf --dxf 图B.dxf --out-dir batch_out`（清单模式/参数路由/退出码见 [references/scripts_reference.md](references/scripts_reference.md) §批量编排）。

> ⚠️ **调脚本前先定解释器 —— 首选本技能自带的启动器，别自己拼 `python` 命令：**
> - **子命令**：`& "<技能目录>\scripts\ftth.cmd" <子命令> [参数...]`
> - **直调脚本**：`& "<技能目录>\scripts\ftth.cmd" dump_geom.py --dxf <图.dxf>`
>   （**首参以 `.py` 结尾即转发该脚本**，否则转发 `ftth.py`；可用环境变量 `FTTH_PYTHON` 指定解释器绝对路径）
> - **必须手写命令时**用**绝对路径**解释器，**禁止裸 `python`**（宿主 runtime 常劫持且无 ezdxf，实测每个新会话必踩）
> - **禁止内联多行 `python -c "..."`**（尤其 PowerShell，引号被 shell 吃掉）；分析脚本一律**先落盘再执行**
> - **不要用 `pip` 补装依赖**：镜像不可达时报错会**伪装成「包不存在」**（`from versions: none`）
> - 启动器候选清单 / `exit /b 9` 语义 / 探测细节 / 镜像陷阱见 [references/scripts_reference.md](references/scripts_reference.md) §解释器契约
>
> **注意**：`ftth.py` 当前调度 **16 个子命令**（`probe` / `plan` / `parse` / `split-band` / `coverage` / `coverage-vshape` / `inspect` / `assemble` / `apply-ruling` / `count` / `count-box`（别名 `count-hdd`）/ `gen` / `verify-truth` / `pipeline` / `budget` / `transitions`，其中 `probe` 与 `parse` 共用 `parse_dxf_structured.py`）。
> **注册面 = 分发面**（2026-09-18 立）：`add_parser` 注册的每个子命令，`main()` 分发段必须有分支，**差集须为 ∅** —— 曾漏 `apply-ruling`，表现为 rc=0、零输出、静默空转（照文档跑会以为已落数）。交付前自查：`add_parser` 名字集合 vs `args.cmd ==` 分支集合对账（`count-hdd` 是别名，不计缺口）。
> `count` = 皮线计数法（`count_households.py`）；`count-box` = 家居配线箱图标法（`count_box_icons.py`），旧名 `count-hdd` 保留为别名（方法名不绑死图内文字写法）。两者是**同属区间法的两种户数口径**（锚点分别取箱图标 / 皮线标注）；**图上存在家居配线箱图标时优先 `count-box`，不再跑 `count`**（2026-09-16 用户裁决），图标不可用时才回落到 `count`。
> 需**直接调用**（未接统一入口）的脚本 6 个：`gen_9level_addressbook.py`、`ledger_elements.py`、`ledger_state.py`、`merge_json.py`、`probe_titleblock_tolerances.py`、`split_units.py`；`extract_fx_map.py` / `extract_fx_locations.py` / `read_titleblock_households.py` 已并入 `pipeline` 阶段（**仍保留直调入口**）。参数速查见本文件 §统一入口外的直调脚本。

## 脚本清单与职责（外移自 SKILL.md，2026-09-17 第三次瘦身）

| 脚本 | 作用 |
|------|------|
| `plan_methods.py` | **图纸画像（Step 1a 产物）**：信号判定 + 选法 + 档案一致率对比 + 门禁评估 |
| `dump_geom.py` | **全量几何转储（Step 1a 首步）** → `<DXF>.geom.json`，后续查询读此缓存 |
| `ledger_elements.py` | **元素台账（几何侧独立出口）**：六类元素带坐标枚举 + 楼栋/单元 x/y 边界与 y 分带 + 坐标/越界/重叠校验；退出码 **4**=几何缓存为空/台账写入失败 |
| `ledger_state.py` | **状态台账（会话侧）**：理解快照 / 裁决台账 / 别名台账的读写与自检 —— 治「重启式梳理」与「裁决不跨通道」（`ledger_elements` 是图侧只读台账，两者勿混） |
| `parse_dxf_structured.py` | 结构化解析：楼栋/单元/分纤箱/楼层表/INSERT；退出码 **4**=探查/解析产物写入失败 |
| `count_households.py` | 户数统计（皮线计数法，对照口径）：同坐标去重、楼层标注自洽检查、出表守门 |
| `count_box_icons.py` | **户数统计（家居配线箱图标法）**：图标贴皮线末端判据，平面图同名图标自动分离 |
| `analyze_coverage.py` | 覆盖范围判定（竖干连续体 + 物理断口，输出线索非结论） |
| `analyze_coverage_vshape.py` | 覆盖范围判定（皮线米数 V 形：谷底=安装层，只读文字） |
| `inspect_closure.py` | **出表前一体化闭合核查（Step 2 首步）**：C1~C10 一次跑完。C5 登记「有刻度但无户数」的层行；C10 用 `--titleblock` 做图签第二来源逐栋比对（2026-09-18 新增） |
| `verify_coverage_truth.py` | 用已定稿地址表反查覆盖线索（回归验收门禁） |
| `gen_addressbook.py` | 解析JSON+用户裁决 → 每户一行xlsx（覆盖 JSON 双形兼容、格式自动检测） |
| `merge_json.py` | 多楼栋解析JSON合并 |
| `ftth_batch.py` | **多图批量编排**：多DXF → 逐图 probe→parse→coverage（自动 --config 串联）→ 合并 → 总览 |
| `extract_fx_map.py` | 分纤箱总图FX映射提取（`--probe` 自带推荐） |
| `extract_fx_locations.py` | 箱位直读标注提取（安装层独立第二来源） |
| `check_unit_box_gaps.py` | **探查期「单元 × 箱清单」交叉清点**（`unit_gaps` 阶段）：骨架与箱清单双向差集，提前暴露「某单元没分纤箱」；**任一侧来源缺席即判 `unresolved`、不产生 pending**；产物 `unit_box_gaps.json` |
| `split_units.py` | 多单元楼层户数拆分 |
| `split_bands.py` | **多地块按 y 带裁剪子 DXF（split-band）**：同名楼分带解析前置，空带/带重叠守卫 |
| `count_hdd_icons.py` | **兼容 shim（勿删）**：`runpy` 转发到 `count_box_icons.py`，保留旧脚本名调用；`count-hdd` 子命令别名同理 |

## 实测案例数据（外移自 SKILL.md，2026-09-17）

  返回（文字 / INSERT / 线段 / 图层 / 包围盒）。实测同一张图的几何查询耗时：
  全量解析 76s → `load_dxf` 的 pkl 命中 20s → **本路径 0.2s**。

shell 内联故障形态（2026-09-15 实测）：
  shell 层吃掉。实测两类故障——PowerShell 报 `ScriptBlock should only be specified as a value
  of the Command parameter`；Bash 把反引号/`$()` 当命令替换导致标识符**静默缺失**（rc=0 不报错）。