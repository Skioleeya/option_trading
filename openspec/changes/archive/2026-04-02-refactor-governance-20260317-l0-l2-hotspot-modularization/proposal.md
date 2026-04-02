## Why

`l2_decision/feature_store/extractors.py` 与 `l0_ingest/feeds/option_chain_builder.py` 已形成高耦合、超长文件与多职责混杂风险，持续抬高回归成本与边界违规概率。

为避免“边改边塌”与一次性大爆炸重构，本提案采用父提案 + 子提案治理模式，按依赖顺序分批落地，明确每个文件“单一职责 + 文件行数 <= 450”硬约束。

## What Changes

1. 建立父提案治理框架，统一拆分标准、依赖顺序、回滚策略、验收门槛。
2. 建立 3 个子提案：
   - `dependency`：先解耦 `option_chain_builder.py` 的职责边界。
   - `bloat`：对 `option_chain_builder.py` 执行模块化拆分与行数治理。
   - `bloat`：对 `extractors.py` 执行模块化拆分与行数治理。
3. 固化量化门槛：单文件禁止超过 450 行；单文件单职责；严格门禁留痕。

## Scope

- OpenSpec 治理编排与执行顺序。
- 本父提案不直接改 runtime 代码。

## Child Proposals

- `refactor-dependency-20260317-option-chain-builder-boundary` (order 1)
- `refactor-bloat-20260317-option-chain-builder-module-split` (order 2)
- `refactor-bloat-20260317-feature-extractors-module-split` (order 3)

## Rollback

任一子提案出现以下情况，立即中止后续阶段并回退到上一个已验证状态：

- 触发跨层违规 import / 反模式命中
- 单测或 strict gate 失败
- 文件职责边界不清导致接口语义漂移
- 单文件行数仍 > 450 且无豁免审批
