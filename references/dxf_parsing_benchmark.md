---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '162756ec-fb3f-4e6e-a82c-8dadb288fdfd'
  PropagateID: '162756ec-fb3f-4e6e-a82c-8dadb288fdfd'
  ReservedCode1: 'a19b7947-e24c-4af3-b620-dfb4b2129007'
  ReservedCode2: 'a19b7947-e24c-4af3-b620-dfb4b2129007'
---

# DXF 解析方法对标调研（GitHub 开源生态 vs 本技能）

> **本文件是什么**：2026-09-22 GitHub DXF 解析生态调研与本技能解析方法对比的**结论沉淀**（当次产出对比报告《DXF解析方法对比研究报告.html》，存 TeleAgent 工作空间）。
> **状态（重要）**：用户当次明确「**先不要改动**」——下述改进项**全部为待用户裁决的候选，一项也未实施**。后续会话若用户要求落实，以本文为清单依据，**实施任何一项前仍须逐项向用户复述并确认**。
> **定位**：知识沉淀，不新增协议条款、不改变任何现有解析行为。

## 一、调研对象与相关性（2026-09 时点）

| 项目 | 与本技能的关系 |
|---|---|
| mozman/ezdxf | 核心依赖；Python 生态最活跃权威 DXF 库，维持不变 |
| U-C4N/Autocad-MCP | 架构参考价值最高：双引擎（COM 实时 AutoCAD + 无头 ezdxf）、122 工具、证据链输出、fail-closed 契约 |
| jeremylongshore/cad-ai-agent | 工作流同构：DWG→ODA→DXF→分析；模型无关、确定性输出、回归测试思路 |
| gdsestimating/dxf-parser、skymakerolof/dxf 等 JS 库 | 浏览器端解析，场景不同，仅作架构参考 |
| LibreDWG/libredwg | `dwg2dxf` 命令行，可作用户侧 ODA File Converter 的开源备选 |

**已弃维护、勿采用**：fuzziness/kabeja（Java，官方标注不再维护）、haplokuon/netDxf（.NET，已归档）。

## 二、核心结论

本技能的**信号驱动多方法流水线**（信号表 + 四方法池 + 申报制交接 + 五项禁区 + 阈值自适应）在调研的全部项目中**没有同等成熟度的对标物**——是 FTTH 竣工图解析场景深度打磨的产物，**不需要也不能被外部方案整体替代**。对标价值仅在**局部工程实践**的补强。

## 三、可借鉴改进候选（8 项，均未实施）

### 高优先级（3 项，落点明确）

1. **ezdxf recover 兜底**：`ftth_common.load_dxf()` 内加 try-except，`ezdxf.readfile` 失败自动回退 `ezdxf.recover.readfile`（容忍损坏/非标 DXF）。落点唯一（L0-I6 性能纪律指定的全技能唯一解析入口），成本最低、收益最直接。
2. **自测量黄金基线**：选 3~5 张已定案图纸，把 `ftth.py inspect` 的 C0~C10 输出固化为基线；脚本改动后自动比对回归，防解析行为漂移（借鉴 cad-ai-agent 确定性回归思路）。
3. **fail-closed 错误分级**：把「同名多址」等会导致**静默丢数**的检查从 warning 升级为 error（rc=2，走 L1-C2 门禁语义）；现有 `floor_mark_conflicts` 检查可直接改造（借鉴 Autocad-MCP fail-closed 契约）。

### 中优先级（3 项）

4. **pipeline 细粒度计时**：geom/probe/plan/parse/coverage/inspect 各阶段输出耗时，定位慢环节。
5. **排除图层机制**：解析支持显式排除干扰图层（如图框装饰层），减少误匹配。
6. **SKILL.md 分层加载**：SKILL.md 只留协议/硬约束、细则外移 references/——体量纪律已部分实践，可继续深化。

### 低优先级（2 项）

7. **capability 声明**：脚本输出声明自身能力边界（类似 Autocad-MCP 的 tool contract），便于上游调度判断。
8. **按 handle 精确测量**：利用 ezdxf 实体 handle 做精确几何测量（面积/长度），替代部分阈值估算。

## 四、明确不借鉴（6 项，后续会话勿再提议）

| # | 不借鉴项 | 原因 |
|---|---|---|
| 1 | LLM 规划器（用 LLM 规划解析步骤） | 与 L0-I2 五项禁区 P1（禁读图外推理）直接矛盾；FTTH 要求确定性直读 |
| 2 | 双引擎架构（COM 实时 AutoCAD） | 本技能只读不写，不需要 COM 引擎 |
| 3 | 质量评分闭环（0~100 打分） | FTTH 判据是二态（对/错/待裁决），评分制反而模糊责任 |
| 4 | Agent 迭代循环（解析→LLM 反思→重试） | 违反 L0-I4（矛盾即停、交用户裁决），且不可复现 |
| 5 | 版本对比 / diff 功能 | 本技能无编辑需求 |
| 6 | OpenTelemetry 依赖 | 重依赖，与「本机轻量自包含」定位冲突 |

## 五、实施约定（用户批准后才适用）

- 逐项独立改动、独立验证，沿用「踩坑修复进脚本并验证通用性」流程；改前改后各跑 `ftth.py budget`。
- 高优先级 3 项落点明确（`load_dxf` / inspect 基线 / `floor_mark_conflicts`），可先行。
- 实施任何一项前，向用户复述该项内容并取得确认；本文所列一切均为「未裁决」状态。