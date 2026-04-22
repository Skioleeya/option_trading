PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-hotspot-modularization
DEPENDENCY_ORDER: 1
BLOCKED_BY: none

## Why

`l0_ingest/feeds/option_chain_builder.py` 目前同时承担 runtime 初始化、Rust 事件桥接、payload 映射、回调分发等职责，边界混杂导致后续拆分风险高。

先做 dependency 子提案，先把职责边界与模块依赖关系固定，再进入 bloat 拆分，避免拆分过程中跨层污染。

## What Changes

1. 定义 `OptionChainBuilder` 内可外置的职责边界与接口。
2. 约束桥接逻辑仅依赖中立 helper/adapter，不引入反向层依赖。
3. 为后续文件级拆分准备模块依赖图和迁移顺序。

## Scope

- 目标：`l0_ingest/feeds/option_chain_builder.py` 的职责边界与依赖清理。
- 不涉及 `extractors.py` 拆分（由后续 bloat 子提案处理）。

## Parent

- `refactor-governance-20260317-l0-l2-hotspot-modularization`
