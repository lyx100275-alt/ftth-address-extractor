---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '0984d1ef-40e6-42bd-ace7-2f71d8808c31'
  PropagateID: '0984d1ef-40e6-42bd-ace7-2f71d8808c31'
  ReservedCode1: '3a6f5408-f8d2-45c1-9925-54a0d3cb1970'
  ReservedCode2: '3a6f5408-f8d2-45c1-9925-54a0d3cb1970'
---

# 脚本参数参考（外移自 SKILL.md，2026-09-16 瘦身）

> 全部脚本均支持 `--help`；本表为主要参数速查。SKILL.md 只留脚本名+一句话职责。

探查确定参数后用 ezdxf 提取 FTTH 信息。**42 个脚本**（`scripts/`：含 `ftth.py`/`ftth_common.py`/`ftth_launcher.py`/`ftth_batch.py`）——改文件后同步计数：

| 脚本 | 作用 | 主要参数 |
|------|------|----------|
| `plan_methods.py` | **图纸画像**：13 信号判定+选法+档案一致率+门禁 | `--dxf --out --probe --project-dir --text-layer --text-type --title-pattern --fx-pattern --wire-keywords --vert-dx` |
| `dump_geom.py` | **全量几何转储**→`<DXF>.geom.json` | `--dxf --out` |
| `ledger_elements.py` | **元素台账**（几何侧）：六类元素+楼栋单元边界+校验；线缆候选剔除建筑电气层 | `--dxf --out --geom --config --parse --text-layer --title-pattern --unit-pattern --fx-pattern --hu-pattern --cable-pattern --box-layer-kw --box-attr-re --wire-layer --floorline-layer --verbose` |
| `parse_dxf_structured.py` | 结构化解析：楼栋/单元/分纤箱/楼层表；rc=4=写入失败 | `--text-layer --text-type --title-pattern --floor-pattern --hu-pattern --cable-pattern --cable-keywords --fx-pattern --unit-pattern --unit-cluster --unit-range --y-tol --insert-blocks --insert-attrib-tag --insert-attrib-val --title-band-tol --consensus-x-tol` |
| `count_households.py` | 户数统计（皮线计数法）：同坐标去重+楼层标注自洽检查+出表守门 | `--text-layer --text-type --title-pattern --floor-pattern --fiber-pattern --special-pattern --assign --match-tol --x-cluster --x-y-gap --probe --title-band-tol --max-unmatched-ratio --allow-lossy` |
| `count_box_icons.py` | **户数统计（图标法）**：图标贴皮线末端，不依赖块名；归层失败（图标>0但总户数=0）⇒ rc=2 不写产物 | `--wire-layer --wire-keys --wire-exclude --insert-blocks --include-square --square-min --square-max --tol --search-radius --strong-keys --weak-keys --floor-layer --scale-max-dx --scale-period-tol --region-y --region-pad --col-x-tol --col-gap` |
| `analyze_coverage.py` | 覆盖判定（竖干连续体+物理断口，输出线索非结论） | `--text-layer --text-type --title-pattern --floor-pattern --fx-pattern --unit-cluster --vert-dx --vert-dy --fx-window --merge-tol --conn-tol --wire-layer --insert-attrib-tag --insert-attrib-val --bldg-map --bldg-pad --title-band-tol --fx-symbol-layer --fx-symbol-cluster --fx-symbol-max-size --symbol-pair-tol --total-pad --break-floor-tol --max-break-span` |
| `analyze_coverage_vshape.py` | 覆盖判定（V 型：谷底=安装层，只读文字） | `--text-layer --text-type --title-pattern --fx-pattern --box-mark-pattern --floor-pattern --hu-pattern --cable-pattern --cable-meters-group --cable-count-group --x-tol --col-x-tol-factor --min-col-rows --y-margin-factor --floor-x-tol --y-tol --box-x-tol --box-anchor-x-factor --dev-gate-factor --fx-locations --margin --include-basement`（细则见 coverage_rules.md「V型计算」；`--fx-locations` 引入箱位直读做安装层交叉校验） |
| `verify_coverage_truth.py` | 用已定稿地址表反查覆盖线索（回归验收） | `--sheet --col-box --col-bldg --col-unit --col-floor --col-door --json-key --fx-prefix` |
| `gen_addressbook.py` | 解析JSON+裁决→每户一行xlsx。覆盖 JSON 单元键双形兼容；模板尾行按标识去重 | `--dxf-json --inspect-json --out --coverage-json --template --addr --branch --sheet-name --cover-rule --floor-pattern --floor-format --door-format --fx-prefix-map --fx-prefix --fx-floor-suffix --allow-lossy` |
| `merge_json.py` | 多楼栋解析JSON合并（同名楼冲突默认 rc=2，`--allow-overwrite`放行） | `--inputs/--input-dir --out --allow-overwrite` |
| `extract_fx_map.py` | 总图FX映射提取。`--probe` 自带推荐 | `--text-layer --fx-pattern --bldg-pattern --unit-pattern --floor-pattern --x-min --x-max --y-min --y-max --proximity-tol --probe` |
| `extract_fx_locations.py` | **箱位直读标注提取**（「N号楼M单元K层」→ fx_locations.json）：安装层独立第二来源 | `--dxf --text-layer --pattern --out` |
| `split_units.py` | 多单元楼层户数拆分 | `--input --rules --out` |
| `split_bands.py` | **多地块按 y 带裁剪子 DXF**（`split-band`）：空带/带重叠告警 | `--dxf --out-dir --band` |

**probe 顶层画像信号**（非命令行参数；plan 透传进 `profile.probe_signals`）：

| 信号 | 含义 | 下游动作 |
|------|------|--------|
| `titleblock_layer_candidates` | 图签候选图层（按「N层/M户、NF+户/层、N单元」命中） | `read_titleblock_households.py --floor-layer` 候选 |
| `plot_band_annotations` | 地块/分带标注清单（含缺号提醒） | **文件名≠地块划分**；检出时按带（`--band`）分别运行 |
| `fx_location_annotation` | 「N号楼M单元K层」标注 present/absent | present 时跑 `extract_fx_locations.py`，传 `coverage-vshape --fx-locations` 做交叉校验 |
| `fx_symbol_layer_candidates` | 分纤箱图形符号层候选（按得分降序） | 取【推荐】项填 `analyze_coverage.py --fx-symbol-layer` |

**多地块/多图幅编排**：`ftth.py --dxf` 是单值。多张 DXF 各跑一遍 `probe→plan→parse`，`merge_json.py` 汇总。一图多地块优先按带参数逐带运行（`--band`），确需物理拆分用 `ftth.py split-band`（`--band "名称:ymin:ymax"`；y 带口径：有锚点走锚点中点，无锚点上界=上邻带标题y、下界=本带标题y）。判据来自 `plot_band_annotations`，**不凭文件名推断地块划分**。


## `ftth.py` 子命令 × 上游产物 依赖矩阵（2026-09-16 新增）

**先读这张表再写命令**，不要用 `--help` 试错。
`必需` = 不传即报错；`可选` = 传了才启用对应口径/校验；`—` = 该子命令无此参数。

| 子命令 | 调度的脚本 | `--dxf` | `--config` | `--probe` | `--profile` | `--parse` | `--coverage` | `--geom` | `--count-box` | `--fx-locations` | 位置参数 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `probe` | parse_dxf_structured | **必需** | 可选 | — | — | — | — | — | — | — | — |
| `plan` | plan_methods | **必需** | 可选 | 可选（强烈建议） | — | — | — | — | — | — | — |
| `parse` | parse_dxf_structured | **必需** | 可选 | — | 可选（门禁） | — | — | — | — | — | — |
| `coverage` | analyze_coverage | **必需** | 可选 | — | 可选（门禁） | — | — | — | — | — | — |
| `coverage-vshape` | analyze_coverage_vshape | **必需** | 可选 | — | 可选（门禁） | 可选（解析侧配对） | — | — | — | 可选 | — |
| `count` | count_households | **必需** | 可选 | — | 可选（不门禁） | — | — | — | — | — | — |
| `count-box` | count_box_icons | **必需** | 可选 | — | 可选（不门禁） | — | — | — | — | — | — |
| `assemble` | assemble_households | — | 可选 | — | — | — | 可选 | — | — | — | — |
| `apply-ruling` | apply_ruling | — | 可选 | — | — | — | — | — | — | — | — |
| `inspect` | inspect_closure | — | 可选 | — | — | **必需** | 可选 | 可选 | 可选 | — | — |
| `gen` | gen_addressbook | — | 可选 | — | — | **必需** | 可选 | — | — | — | — |
| `verify-truth` | verify_coverage_truth | — | 可选 | — | — | — | — | — | — | — | `xlsx` `covjson` |
| `split-band` | split_bands | **必需** | — | — | — | — | — | — | — | — | — |
| `pipeline` | 串跑 11 阶段 | **必需** | — | — | — | — | — | — | — | — | 见下方专节 |

**同义参数（2026-09-16 统一；两种写法等价，推荐左侧）**

| 上游产物 | 统一名 | 旧别名 | 出现在 |
|---|---|---|---|
| `parse` 输出的 JSON | `--parse` | `--dxf-json` | `inspect` / `gen` |
| `coverage` 输出的 JSON | `--coverage` | `--coverage-json` | `inspect` / `gen` |

**易错点（实测踩过）**
- `coverage-vshape` 只读文字；`--parse` 已支持（解析侧配对），`--coverage` 仍无此参数，传了报 `unrecognized arguments`。箱位交叉校验用 `--fx-locations`。
- `coverage` 是几何路线：**必须显式传 `--wire-layer`**；有总图时加 `--bldg-map`；箱符号不写编号时加 `--fx-symbol-layer`（取 probe 推荐项）。
- `inspect` 与 `gen` 豁免 `--dxf`（只吃上游 JSON）；`verify-truth`/`assemble`/`apply-ruling` 同豁免。
- `assemble` 独有必填 `--count`（count_box 输出）与 `--col-map`（列归属映射）；`apply-ruling` 独有 `--json`（待改 JSON）与 `--ruling`（或 `--set` 简写）。
- `--profile` 两档含义：`parse`/`coverage`/`coverage-vshape` 上是**门禁**（unknown⇒rc=2）；`count`/`count-box` 上仅接受不报错。
- `gen --addr` 留空时 PowerShell 丢弃空串致 argparse 报错，变通传 `--addr ",,,,,,"`。
- `--floor-pattern` 至少 1 个捕获组：`[-]?[0-9]+F` 编译通过 rc=0 假象，解析期 `m.group(1)` 才 IndexError（已补入启动期自检，缺组即 rc=1）。
- `--hu-pattern` 捕获组只包数字：`([0-9]+户)` 捕获 `2户` 整串致 `int('2户')` 崩（`floor_engine.py` 已加防御性数字提取，正确写法 `([0-9]+)户`）。

### 各子命令可直接抄的完整示例

> **优先用启动器**：`python "$SK\scripts\ftth_launcher.py" <子命令> [参数...]`，直调脚本同写
> `python "$SK\scripts\ftth_launcher.py" dump_geom.py --dxf $D` —— 启动器自己探测带 ezdxf 的解释器，**无需填 `$PY`**。
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
# 12) split-band —— 多地块分带（parse 报「多地块同名楼」rc=2 时走这步，产出按带子 DXF 后逐带 parse）
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
| `read_titleblock_households.py` | 图签形态栋级入户规模读取（`N层/M户`+`N单元` 成对标注）。退出码 0 正常；1 参数/信号缺失；2 比对不一致；**3 提取不完整（有楼名零层户数据，`--allow-partial` 可放行）** |
| `gen_9level_addressbook.py` | 九级地址树出表（内置行数恒等式） |
| `probe_titleblock_tolerances.py` | 图签几何容差量测（缺省自适应，推定值写入结果 JSON） |
| `inspect_closure.py` | 出表前一体化闭合核查 C1~C10（`ftth.py inspect` 可调度；只读 JSON，豁免 `--dxf`） |
| `ftth_batch.py` | **多图批量编排**（probe→parse→coverage→合并→总览） |
| `ledger_state.py` | **状态台账（会话侧）**：理解快照 / 裁决台账 / 别名台账 + **状态节点** `状态.json`（子命令 `init`/`snapshot-set`/`snapshot-get`/`ruling-add`/`alias-add`/**`state-set`**/**`state-get`**/`pending`/`check`）。退出码：0 正常；**2 有未裁决项或别名归属冲突**；3 未初始化 / 台账损坏 / 参数错误 / 状态名不在枚举内。`STATES` = 状态节点枚举唯一权威（D11 与 SKILL.md 状态机图对拍） |

### 脚本级机器护栏（2026-09-17，判据通用、与项目无关）

| 护栏 | 触发条件 | 行为 |
|---|---|---|
| `parse_dxf_structured.py` 正则组自检 | `--title-pattern`/`--floor-pattern`/`--hu-pattern`/`--unit-pattern` 少于 1 个捕获组，或 `--cable-pattern` 少于 2 个 | 编译后立刻 rc=1 显式报错并给正确形态示例（替代解析期 `IndexError` 裸崩；`--floor-pattern` 为 2026-10-02 实测后补入） |
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
- **裁决值含乘号（`4*16`）一律拒绝 rc=1**：裁决值须是**绝对户数**（写 `64`），脚本不做乘法 —— `*N` 一类乘号标注属**直读**形态，读数在解析阶段已取出，不在此处展开（两套口径不得混用）。
- 找不到目标（楼栋/单元/楼层/箱）**硬失败并列出当前存在的键**，不猜、不静默跳过。
- 写保护：`--out` 省略 → 写 `<原名>_patched.json`；`--out` 与输入同路径 → 须显式 `--force`（否则 rc=2）；
  `--out` 指向的已存在文件 → 默认改道 `*_patched`。派生覆盖原产物一律要 `--force`。

## 批量编排 `ftth_batch.py`（已外移 → [pipeline_details.md §19](pipeline_details.md)，2026-09-26）

> 本节原在此处（2026-09-17 立）。因本文件 46,982 B 距预警线仅剩 18 B，快路径、清单模式与契约表已外移至 [pipeline_details.md §19](pipeline_details.md)；子命令清单/依赖矩阵/可抄示例仍在本文件。

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

## 环境与命令纪律

### 解释器契约（开工第一件事：先定 `$PY`）

**铁律**：所有脚本一律用「绝对路径解释器」或启动器调用，**禁裸 `python`/`py`**。宿主常把自带无 ezdxf 的 runtime 前置到 PATH，裸 `python` 命中它即 `ModuleNotFoundError`。

**首选：直接用启动器**

```powershell
python "$SK\scripts\ftth_launcher.py" <子命令> [参数...]      # -> ftth.py <子命令> ...
python "$SK\scripts\ftth_launcher.py" dump_geom.py --dxf $D   # -> scripts\dump_geom.py ...
```

| 项 | 约定 |
|---|---|
| 参数分派 | 首参以 `.py` 结尾⇒转发该脚本；否则转发 `ftth.py <首参>` |
| 解释器探测 | 逐个真执行 `import ezdxf`：`FTTH_PYTHON`→当前解释器→`Python311~313`→`py -3.13/-3.12/-3.11/-3`→PATH `python` |
| 指定解释器 | 设 `FTTH_PYTHON=<python.exe 绝对路径>`，优先级高于全部候选 |
| 退出码 | 透传目标脚本；全部候选失败→rc=9 |
| 参数保真 | subprocess 直传 argv，不重排不改写 |

> **启动器入口可用裸 `python`**（启动器自身不 import ezdxf）；**业务脚本禁裸 `python` 直调**。pipeline 内部各阶段直调同解释器 `ftth.py` 是等价例外。

**必须用「真执行」验证**（`& $<候选> -c "import ezdxf"`），只 `Test-Path` 会选到没依赖的解释器。

**⚠️ 禁用 `pip install` 补依赖**：镜像不可达时报 `from versions: none`，**看起来像「包不存在」实际是「索引不可达」**，别在此费轮次。确需安装先用默认源验证：`& $PY -m pip index versions ezdxf`。

### 必须具备的软件环境

| 工具 | 用途 | 验证命令（用 `$PY`） |
|------|------|---------|
| ODA File Converter (≥27.1) | 用户侧 DWG→DXF 转换（助手不调用） | 检查安装目录存在 |
| Python 3.x + ezdxf | DXF 解析 | `& $PY -c "import ezdxf; print(ezdxf.__version__)"` |
| openpyxl | 生成 xlsx 成品 | `& $PY -c "import openpyxl"` |
| xlrd | 读取 .xls 模板（模板为 xlsx 时不需要） | `& $PY -c "import xlrd"` |

ODA 转换由用户完成。

**PowerShell 输出编码纪律**：`>` 重定向默认产出 UTF-16。脚本产物一律由 Python 自己写文件（`open(path,"w",encoding="utf-8")`），禁 PowerShell 重定向落盘。确需读重定向产物时先转码再读。

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

## 户数取法的图纸形态判别

户数按 **L1-C1 优先级**取首个可用者（标注直读→数图标→数皮线）；本节讲"数图标"的形态判别。实测四类形态：

| 形态 | 图面特征 | 判据 | 动作 |
|------|---------|------|------|
| **A 逐户画箱** | 每户一个箱图标，`A=家居配线箱` | 图标数=户数 | `count-box` 直接数 |
| **B 每层一箱+乘号** | 每层/每单元一个箱+`xN` | 图标数=层数×单元数≠户数；`xN` 本身可直读 | `count-box` 归层为 0⇒rc=2 拦断；改走直读或图签法 |
| **C 示意箱+数量标注** | 箱为示意、旁标 `N户` | 读 `N户` 求和 | `--hu-pattern` 直读；禁用图标数 |
| **D 非户数图** | 光交/杆路图：无家居箱、无线缆层 | 不适用 | `count-box` 在皮线门禁处 rc=2；改判「图纸类型不符」 |

**三条铁律**：
1. **「图上有箱」≠「能数箱」**：只有 A 能直接数，B 的箱是「层」的计量单位，C/D 的箱是示意。
2. **`N户` 采样是严格全匹配** `fullmatch(\d+户)`：`N户/层`、`共覆盖住户N户`等形态天然被排除。
3. **归层失败必须 rc≠0**：`贴末端图标>0 且归层后总户数==0` 是「没测出来」不是「0 户」。

## 流水线 `pipeline`（已外移 → [pipeline_details.md §18](pipeline_details.md)，2026-09-20）

> 本节原在此处（2026-09-17 立）。因本文件 48,915 B 距硬上限仅剩 85 B，串跑入口、参数表与语义边界已外移至 [pipeline_details.md §18](pipeline_details.md)；依赖矩阵/可抄示例仍在本文件。


## 统一入口 `ftth.py` 与 `--config` 机制

`ftth.py` 是统一调度入口，支持 16 个子命令（`probe/plan/parse/split-band/coverage/coverage-vshape/inspect/assemble/apply-ruling/count/count-box/gen/verify-truth/pipeline/budget/transitions`）。参数优先级：命令行显式>`--config`>脚本默认。`--config` 传入 probe 输出的 `suggested_params` JSON，自动填充未指定的参数。

**典型工作流**：`probe`→`plan`（选法）→`parse --config --profile`。

多张 DXF 用批量编排：`python "<技能目录>\scripts\ftth_launcher.py" ftth_batch.py --dxf 图A.dxf --dxf 图B.dxf --out-dir batch_out`（清单模式见 [pipeline_details.md](pipeline_details.md) §19）。

> ⚠️ **调脚本前先定解释器——首选启动器，别自己拼 `python`**：
> - 子命令：`python "<技能目录>\scripts\ftth_launcher.py" <子命令> [参数...]`
> - 直调脚本：`python "<技能目录>\scripts\ftth_launcher.py" dump_geom.py --dxf <图.dxf>`
> - 启动器入口裸 `python` 是唯一豁免；业务脚本禁裸 `python`（宿主 runtime 常劫持且无 ezdxf）
> - 禁内联多行 `python -c "..."`（PowerShell 引号被吃）；禁 `pip` 补依赖（镜像报错伪装成「包不存在」）
>
> **注册面=分发面**：`add_parser` 注册的每个子命令 `main()` 分发段必须有分支，差集须为 ∅（曾漏 `apply-ruling`，rc=0 零输出静默空转）。
>
> 需**直接调用**（未接统一入口）的脚本 6 个：`gen_9level_addressbook.py`、`ledger_elements.py`、`ledger_state.py`、`merge_json.py`、`probe_titleblock_tolerances.py`、`split_units.py`。

## 脚本清单与职责（外移自 SKILL.md，2026-09-17 第三次瘦身）

| 脚本 | 作用 |
|------|------|
| `plan_methods.py` | **图纸画像（Step 1a 产物）**：信号判定 + 选法 + 档案一致率对比 + 门禁评估 |
| `dump_geom.py` | **全量几何转储（Step 1a 首步）** → `<DXF>.geom.json`，后续查询读此缓存 |
| `ledger_elements.py` | **元素台账（几何侧独立出口）**：六类元素带坐标枚举 + 楼栋/单元 x/y 边界与 y 分带 + 坐标/越界/重叠校验；退出码 **4**=几何缓存为空/台账写入失败 |
| `ledger_state.py` | **状态台账（会话侧）**：理解快照 / 裁决台账 / 别名台账 + **状态节点** 的读写与自检 —— 治「重启式梳理」「裁决不跨通道」「当前态靠推断」（`ledger_elements` 是图侧只读台账，两者勿混）。子命令与 `状态.json` 见本文件 §统一入口外的直调脚本 |
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
| `ftth_naming.py` | **命名归一域（2026-09-26 自 `ftth_common.py` 抽取）**：楼栋/单元/楼层/中文数字归一唯一入口；只依赖 stdlib，禁 import `ftth_common`；由后者 re-export，调用方零改动 |
| `ftth_geom.py` | **几何/缓存域（2026-09-26 抽取）**：DXF 单次全量解析 + geom.json 缓存 + 几何查询（I6 性能纪律执行层）；自包含（stdlib + lazy ezdxf） |
| `ftth_cells.py` | **图签格组域（2026-09-26 抽取）**：格组归属判据族唯一家；只许 import 命名/几何域 |
| `check_contracts.py` | **产物契约检查（L1-C8 词汇封闭）**：R1/R2 `result_origin/result_confirmation` 未知取值即 rc=2；**R4 `判定依据` 首段必须 ∈ `ftth_common.COVERAGE_METHODS`，空值同样 FAIL**；R3 pending 只盘点（语义判定权在 C9）；**无可核对象 → rc=3（空集合不得判 PASS）** |
| `check_contract_coverage.py` | **契约落地门禁（2026-10-02 P0）**：核 `version.json` 的 `contract_coverage` 登记与仓库现实一致。0 一致（可带 declared WARN）/ **2 不一致** / 3 无可核对象。判据见 [operations_discipline.md](operations_discipline.md) §九·补 |
| `check_transitions.py` | **迁移门禁核对器**：核 SKILL.md 禁止迁移表 **6 条**（#1~#5 否定式 + **#6 申报态与证据对拍**）。台账全缺 → rc=3（刻意不给「通过」） |
| `dxf_extract.py` | 事实提取层：只答图上有什么 |
| `evidence_builder.py` | 箱证据层：统一安装楼层对象，不裁决 |
| `conflict_engine.py` | 冲突引擎：议题枚举+机读出口，恒pending |
| `attribution_engine.py` | 归属引擎：归一/解析/载入/改派 |
| `coverage_engine.py` | 覆盖引擎：V谷底/竖线统一证据 |

## 实测案例数据

几何查询耗时：全量解析 76s → `load_dxf` pkl 命中 20s → 缓存路径 0.2s。shell 内联故障：shell 层吃掉反引号与 `$()`，标识符**静默缺失**（rc=0 不报错）。

## 退出码语义细则

- `rc=4`=写盘/缓存失败（`parse:697`探查产物、`ledger_elements:649`台账、`:143`几何空）。
- 参数错误发`2`禁发`3`；`inspect`的`2`=存在FAIL（同码异义）。
