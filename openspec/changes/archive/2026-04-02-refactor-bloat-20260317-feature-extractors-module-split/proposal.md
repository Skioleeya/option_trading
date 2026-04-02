PARENT_CHANGE_ID: refactor-governance-20260317-l0-l2-hotspot-modularization
DEPENDENCY_ORDER: 3
BLOCKED_BY: refactor-bloat-20260317-option-chain-builder-module-split

## Why

`l2_decision/feature_store/extractors.py` 职责过多（stateful extractor、recordbatch 兼容、skew/vol/flow 指标混合），长期维护与质量门禁成本高。

本子提案聚焦按主题拆分 extractor 文件，执行单文件 <= 450 行与单文件单职责治理。

## What Changes

1. 将 extractor 按主题拆分为多个模块（flow / skew / vol / shared helpers）。
2. 保持 `build_default_extractors` 对外合同稳定。
3. 对拆分后文件执行 LOC 与复杂度治理。

## Scope

- 目标文件：`l2_decision/feature_store/extractors.py`
- 目标目录：`l2_decision/feature_store/` 下主题化子模块
- 非目标：L0/L1 runtime 逻辑改造

## Parent

- `refactor-governance-20260317-l0-l2-hotspot-modularization`
