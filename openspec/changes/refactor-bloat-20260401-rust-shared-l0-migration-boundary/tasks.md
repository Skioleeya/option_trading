## Scope

- [x] 锁定目标文件清单（Top N）
- [x] 标记非目标范围（避免扩散）

## Implementation

- [x] 重构实现（仅本主题）
- [x] 边界扫描（无跨层违规 import）
- [x] 魔法数治理（若本主题涉及）

## Verification

- [ ] 相关测试通过（scripts/test/run_pytest.ps1）
- [ ] 指标达标（见量化门槛）
- [ ] SOP 同步或写明 SOP-EXEMPT
- [x] OpenSpec chain 校验通过
- [x] Strict/quality gate 达标（无 runtime Python/Rust files changed）
- [x] SOP-EXEMPT：OpenSpec governance only，无运行时行为变更

## DoD

- [ ] 复杂度/嵌套/长度/重复率达到阈值
- [ ] 无行为回归
- [ ] 变更可回滚、可审计

## Phase 1 - Module Classification

- [x] 为 `shared + L0` 模块打上 Contract / Compute / Runtime / CompatShim 角色
- [x] 标记 RustFirst / RustSoon / Defer 迁移等级
- [x] 标记 Low / Medium / High 风险等级

## Phase 2 - Scope Guard

- [x] 明确纳入范围仅限 `shared` 与 `l0_ingest`
- [x] 明确排除 `l1_compute`、`l2_decision`、`l3_assembly`、`app`、`l4_ui`
- [x] 标记禁止 scope creep 的审查条件

## Phase 3 - Decomposition Rules

- [x] 定义 `shared/services/l0_runtime/*` 的责任拆分规则
- [x] 定义 `shared/services/active_options/*` 的 kernel 边界
- [x] 定义 `shared/system/*` 仅 IPC/diagnostics 子模块可提前进入的规则

## Phase 4 - First-Wave Set

- [x] 固化 `shared/contracts/*` 与 `shared/models/*` 的 early ownership
- [x] 固化 `active_options` core kernel 的 early migration 资格
- [x] 固化 `l0_rust` 从 accelerator 向 runtime-owner 过渡的目标描述

## Phase 5 - Validation Matrix

- [x] 定义 contract parity / source-time parity / diagnostics continuity 验证项
- [x] 定义 active-options sparse fallback parity 验证项
- [x] 定义 L0 snapshot monotonicity / Arrow handoff integrity 验证项

## Phase 6 - Rollback and Cutover

- [x] 定义 dual-run compare 要求
- [x] 定义 rollback radius 与 halt 条件
- [x] 定义 implementation session 的 entry gate

## Phase 7 - Cross-Proposal Consistency Review

- [x] 复核本 child 未重定义上游 contract freeze 结果
- [x] 复核本 child 未重定义上游 constants/config ownership
- [x] 复核 proposal / design / tasks / spec 表述一致

## Phase 8 - Closure Gate

- [x] 确认 child headers 与 parent order 一致
- [x] 确认 spec 场景与 tasks 阶段一致
- [ ] 在边界不清或 rollback 不明前保持 child open
