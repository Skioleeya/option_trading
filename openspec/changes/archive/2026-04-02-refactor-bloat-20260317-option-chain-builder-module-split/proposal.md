PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-hotspot-modularization
DEPENDENCY_ORDER: 2
BLOCKED_BY: refactor-dependency-20260317-option-chain-builder-boundary

## Why

`option_chain_builder.py` 已接近/超过单文件治理上限，且包含多种执行路径与辅助逻辑，存在可读性与变更放大风险。

本子提案聚焦文件臃肿治理：在不改变行为合同前提下完成模块化拆分，确保单文件 <= 450 行且职责单一。

## What Changes

1. 拆分 `option_chain_builder.py` 的桥接、转换、回调分发与工具函数。
2. 保留 builder 主编排职责，剥离非编排细节到中立模块。
3. 目标文件长度治理：所有拆分后文件 <= 450 行。

## Scope

- 目标文件：`l0_ingest/feeds/option_chain_builder.py`
- 目标目录：`l0_ingest/feeds/` 下新增模块
- 非目标：`extractors.py`（由另一个 bloat 子提案处理）

## Parent

- `refactor-governance-20260317-l0-l2-hotspot-modularization`
