---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'de515cca-2cd0-480a-8fab-4ff3c3a7c25d'
  PropagateID: 'de515cca-2cd0-480a-8fab-4ff3c3a7c25d'
  ReservedCode1: 'a516bea9-36f2-47d9-b075-5a8f0b8ffbea'
  ReservedCode2: 'a516bea9-36f2-47d9-b075-5a8f0b8ffbea'
---

# FTTH 标准地址表提取（ftth-address-extractor）

从 FTTH 竣工图（DXF，用户侧经 ODA 由 DWG 转换）提取分纤箱编号 / 覆盖楼层 /
每层户数，生成每户一行的标准地址表（xlsx）或九级地址树；并支持从图纸图签
直读栋级单元数 / 层数 / 每层户数，与《楼宇信息采集表》逐栋交叉印证。

> Agent 入口与完整协议见 [`SKILL.md`](SKILL.md)（会话首屏全量加载的唯一文件）；
> 本文件只给人看：安装、跑通、查问题。规则的权威定义一律在 `SKILL.md` 与
> `references/`，此处不复制——两处不一致时以更新日期较新者为准。

## 环境

- Python 3.11–3.13（实测 3.13.12），依赖锁定见 [`requirements.txt`](requirements.txt)：
  `ezdxf==1.4.4` / `openpyxl==3.1.5` / `xlrd==2.0.2`
- DWG→DXF 由用户侧 ODA 完成，助手不调用。
- Windows 下**一律走启动器**（自动探测真正含 ezdxf 的解释器，探测不到报 `rc=9`）：

```bat
python "<技能目录>\scripts\ftth_launcher.py" <子命令> [参数...]
python "<技能目录>\scripts\ftth_launcher.py" <脚本.py> [参数...]   rem 首参 .py 结尾即直调该脚本
```

启动器入口的 `python` 无需带 ezdxf（启动器自行探测并转发到带 ezdxf 的解释器）；绕过启动器直调业务脚本仍禁止裸 `python`（宿主 runtime 常劫持且无 ezdxf）。
详见 `references/scripts_reference.md` §解释器契约。

## 最快跑通

```bat
$SK = "<技能目录>"
$D  = "C:\...\图纸.dxf"
$T  = "C:\...\.temp\<项目>"

python "$SK\scripts\ftth_launcher.py" probe --dxf $D --out "$T\probe.json"
python "$SK\scripts\ftth_launcher.py" plan --dxf $D --probe "$T\probe.json" --out "$T\profile.json"
python "$SK\scripts\ftth_launcher.py" parse --dxf $D --config "$T\probe.json" --profile "$T\profile.json" --out "$T\parse.json"
```

或一条命令串跑解析全链（只解析、不出表；出表必须等人工裁决）：

```bat
python "$SK\scripts\ftth_launcher.py" pipeline --dxf $D --outdir $T --project-dir "<项目目录>"
```

16 个子命令的参数矩阵与可抄示例见
`references/scripts_reference.md`（依赖矩阵 / 各子命令示例）；批量编排见
`references/pipeline_details.md` §19。

## 自检门禁

```bat
python "$SK\scripts\ftth_launcher.py" budget                                   rem 体量闸门
<python> tests\run_smoke.py [--with-dxf] [--corpus <语料dxf>]      rem T0~T22 冒烟（无 T16/T21，历史编号缺口）
```

- 体量纪律：`SKILL.md` 与 `references/*.md` 单文件预警线 47,000 B / 硬上限
  49,000 B / 宿主截断 51,200 B，阈值唯一来源是 `version.json` 的 `budget` 段。
- 冒烟：T0 全仓编译 / T1 单一源守卫（含 T1b 归一委托锁）/ T2 注册=分发对账 /
  T3 纯函数 / T4 闸门（含 T4b 文档一致性 `check_docs.py`）/
  T5 真语料 probe（需 ezdxf + 语料，加 `--with-dxf`；语料已外置版本库
  `tests/corpus/`，可用 `--corpus <路径>` 或环境变量 `FTTH_TEST_DXF` 指定，缺失自动 SKIP）/
  T6 出表链黄金路径（含 gen，需 openpyxl）/
  T7~T13 格组认领/多栋合并/偏置优势闸等图签格组回归（详见 `tests/run_smoke.py`）/
  T14 三图 golden 回归（需 `--with-dxf` + 桌面三图齐备，缺图自动 SKIP；
  基线 `tests/golden_expected.json`）/
  T15 台账确定性（`FTTH_FIXED_TIME` 冻结时钟后同序列写入逐位一致）/
  T17 产物契约门（需本轮 T14 产物：`check_contracts.py` 锁 L1-C8 词汇封闭）/
  T18 冲突矩阵回归（`tests/run_conflict_matrix.py`，覆盖来源状态机闭环，
  **纯函数级、不需 DXF 语料**，任何时候都能跑）/
  T19~T22 出口门禁负向测试（无闭合/陈旧闭合/pending覆盖直达 gen 必须 FAIL）。

## 目录

| 路径 | 说明 |
|---|---|
| `SKILL.md` | 唯一权威协议（流程 / 状态机 / 硬约束），会话首屏加载 |
| `scripts/` | 43 个 `.py`（含启动器 `ftth_launcher.py`）；统一入口 `scripts/ftth.py`，公共模块 `scripts/ftth_common.py`（命名归一域已抽取为 `scripts/ftth_naming.py`，由前者 re-export，调用方零改动；归属纯函数已抽取为 `scripts/attribution_engine.py`；V 谷底统一证据为 `scripts/coverage_engine.py`；写法谱/楼层分类为 `scripts/floor_engine.py`）。运行会在 `scripts/` 生成 `.interpreter_cache.json`（解释器探测缓存，由版本库 `.gitignore` 忽略，不入库；可安全删除，删除后下次启动重探一次；上架打包前建议手动清理） |
| `references/` | 细则文档（参数表 / 覆盖规则 / 选法 / 图签协议 / 流水线细则 / 操作纪律…） |
| `methods/` | 图纸类型方法（楼-簇 / 共享混合 / 图签主导）+ 信号定义 |
| `assets/` | 标准地址表模板 xlsx |
| `tests/` | `run_smoke.py` + 语料 `corpus/a小区.dxf` |
| `SKILL_CHANGELOG.md` | 完整修订记录（中文序号，追加放顶部） |
| `version.json` | 版本号 + 台账 schema 标识 + 体量阈值（minor 位 = 修订序号） |

## 版本

`version.json`：`minor` = 修订序号（当前 0.108.0＝一百零八），`major` 固定 0、
对外发布时由人工提升；不采用未经验证的语义化版本号。GitHub tag 与 release
只在人工确认后打。

## 版本管理（git）

- **git 仓库不随技能目录携带**（技能目录只含运行文件）：完整历史与版本管理
  位于工作空间 `技能版本库/ftth-address-extractor/`（远程
  `git@github.com:lyx100275-alt/ftth-address-extractor.git`，本地分支领先
  远程时为未推送变更）。
- 提交 / 打 tag / 查看 diff 等操作由「版本管理」技能（skill-version-manager）统一
  驱动，不手工在技能目录里 `git init`。
- 技能内容变更后：把技能目录文件同步进版本库工作区 → `git add -A` → 按
  `SKILL_CHANGELOG.md` 序号提交 → 需要时打 tag。

> AI生成