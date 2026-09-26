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
`references/scripts_reference.md`（依赖矩阵 / 各子命令示例 / 批量编排）。

## 自检门禁

```bat
python "$SK\scripts\ftth_launcher.py" budget                                   rem 体量闸门
<python> tests\run_smoke.py [--with-dxf]                          rem T0-T13 冒烟
```

- 体量纪律：`SKILL.md` 与 `references/*.md` 单文件预警线 47,000 B / 硬上限
  49,000 B / 宿主截断 51,200 B，阈值唯一来源是 `version.json` 的 `budget` 段。
- 冒烟：T0 全仓编译 / T1 单一源守卫 / T2 注册=分发对账 / T3 纯函数 / T4 闸门 /
  T5 真语料 probe（需 ezdxf，加 `--with-dxf`）/ T6 出表链黄金路径（含 gen，需 openpyxl）/
  T7~T13 格组认领/多栋合并/偏置优势闸等图签格组回归（详见 `tests/run_smoke.py`）。

## 目录

| 路径 | 说明 |
|---|---|
| `SKILL.md` | 唯一权威协议（流程 / 状态机 / 硬约束），会话首屏加载 |
| `scripts/` | 30 个 `.py`（含启动器 `ftth_launcher.py`）；统一入口 `scripts/ftth.py`，公共模块 `scripts/ftth_common.py`。运行会在 `scripts/` 生成 `.interpreter_cache.json`（解释器探测缓存，已加入 `scripts/.gitignore` 忽略；可安全删除，删除后下次启动重探一次；上架打包前建议手动清理） |
| `references/` | 细则文档（参数表 / 覆盖规则 / 选法 / 图签协议 / 流水线细则 / 操作纪律…） |
| `methods/` | 图纸类型方法（楼-簇 / 共享混合 / 图签主导）+ 信号定义 |
| `assets/` | 标准地址表模板 xlsx |
| `tests/` | `run_smoke.py` + 语料 `corpus/a小区.dxf` |
| `SKILL_CHANGELOG.md` | 完整修订记录（中文序号，追加放顶部） |
| `version.json` | 版本号 + 台账 schema 标识 + 体量阈值（minor 位 = 修订序号） |

## 版本

`version.json`：`minor` = 修订序号（当前 0.98.0＝九十八），`major` 固定 0、
对外发布时由人工提升；不采用未经验证的语义化版本号。GitHub tag 与 release
只在人工确认后打。

> AI生成