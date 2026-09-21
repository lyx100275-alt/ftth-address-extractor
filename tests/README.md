# tests —— 回归校验方法

> **语料说明（2026-09-21 更新）**：本目录原内置 `corpus/a小区.dxf` 等回归语料，因仓库转为公开，**不再内置任何图纸语料**。
> 需要跑 T5 语料冒烟时，请自行放置脱敏后的 DXF 到 `tests/corpus/` 并按 `run_smoke.py --with-dxf` 执行；语料缺失时 T5 自动 SKIP。

## 目录

```
tests/
  README.md                 本文件
  run_smoke.py              包内冒烟自检
```

## 冒烟自检

```bash
python tests/run_smoke.py            # 无语料 DXF，T5 自动 SKIP
python tests/run_smoke.py --with-dxf # 需自行放置 tests/corpus/a小区.dxf（脱敏语料）
```

测试项：
- T1 单一源守卫：`_txt_fields` 恰 1 份实现；无本地 `bldg_num` 重复定义（同名异义防线）
- T2 注册面=分发面：`ftth.py` 每个 `add_parser` 的子命令在分发段有分支（差集 ∅）
- T3 纯函数语义：`bldg_num` / `bldg_num_or_none` / `_txt_fields` 两态出口
- T4 体量闸门：`ftth.py budget` rc=0
- T5 语料冒烟（可选，需 ezdxf + 语料 DXF）：probe rc=0
- T6 出表链黄金路径（合成料，无需 DXF/ezdxf）

## 维护约定

- 语料如需入包，必须先脱敏、后校验、再入库（三层校验细则见历史版本）。
- 禁止把未脱敏的原始图纸放入本目录（本目录会随技能包同步 / 备份 / 分发）。