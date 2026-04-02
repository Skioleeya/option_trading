## Scope

- [x] 锁定目标文件清单（Top N）
- [x] 标记非目标范围（避免扩散）

## Implementation

- [x] 重构实现（仅本主题）
- [x] 边界扫描（无跨层违规 import）
- [x] 魔法数治理（若本主题涉及）

## Verification

- [x] 相关测试通过（scripts/test/run_pytest.ps1）
- [ ] 指标达标（见量化门槛）
- [x] SOP 同步或写明 SOP-EXEMPT

## DoD

- [ ] 复杂度/嵌套/长度/重复率达到阈值
- [ ] 无行为回归
- [x] 变更可回滚、可审计

## Owner API Prerequisite Matrix

- [x] 定义 Rust owner API 映射表（`shared_rust.*` vs `_native_generated.l0_rust`）
- [x] 锁定 owner API 列表：`OptionChainBuilder/L0QuoteRuntime(or RustQuoteRuntime)/APIRateLimiter/FeedOrchestrator/OptionSubscriptionManager/IVBaselineSync/build_runtime_bundle/CallbackHooks/SnapshotRequest`
- [x] 为每个 owner API 标记当前消费者与目标导入路径
- [x] 产出“不满足 owner API 不允许删 Python owner”阻断规则

## Retarget And Parity Gates

- [x] 定义 consumer retarget 顺序（先 source/runtime，再 services，再 facade）
- [x] 定义 Sub-wave B/C/D/E/F 分层 parity gate
- [x] 定义 dual-run 证据结构（full session, compare dimensions, divergence criteria）
- [x] 定义 rollback 触发条件（owner 缺失、契约漂移、双跑不一致）

## Chain Wiring

- [x] 将 `impl-20260402-l0-runtime-rust-cutover` 的 `BLOCKED_BY` 对齐到本子提案
- [x] 运行 `openspec validate` 校验本 change
- [x] 运行 OpenSpec chain gate 并留痕

## Notes

- `相关测试通过` 在本治理子提案中以 OpenSpec 校验与链路门禁校验为准（无 runtime 代码改动）。
- `SOP-EXEMPT`：治理变更，不涉及 L0-L4 运行时行为变更。
