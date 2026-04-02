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

## Phase 1 - Reference Inventory

- [x] 枚举 parent 与四个 children 的 proposal / design / tasks / spec 引用关系
- [x] 标记 dependency order 语句出现位置
- [x] 标记 closure gate 与 rollback 语句出现位置

## Phase 2 - Order Reconciliation

- [x] 核对四个 children 的 DEPENDENCY_ORDER 唯一且连续
- [x] 核对 parent 与 children 的 blocked_by 关系一致
- [x] 核对各文件中的顺序描述一致

## Phase 3 - Terminology Reconciliation

- [x] 核对 contract freeze 术语是否一义化
- [x] 核对 constants / config governance 术语是否一义化
- [x] 核对 shared + L0 boundary 与 reconciliation 术语是否一义化

## Phase 4 - Gate Reconciliation

- [x] 核对 closure gate 在 parent 与 children 中表述一致
- [x] 核对 rollback 条件是否互不冲突
- [x] 核对 strict evidence 要求是否完整

## Phase 5 - Cohesion and Coupling Review

- [x] 复核 proposal chain 是否高内聚低耦合
- [x] 复核 reconciliation child 未重新定义 upstream scope
- [x] 复核 parent 未承载 child implementation 语义

## Phase 6 - Validation Evidence

- [x] 运行 OpenSpec chain gate
- [x] 运行文本级交叉一致性校验
- [x] 记录发现的问题与修复动作

## Phase 7 - Archive Readiness

- [x] 明确 parent archive 前提条件
- [x] 明确 children completion evidence 引用格式
- [x] 明确未满足条件时保持 open 的规则

## Phase 8 - Closure Gate

- [x] 确认 proposal / design / tasks / spec 全链一致
- [x] 确认 archive-readiness 语句明确无歧义
- [ ] 在 reconciliation 未闭环前保持 child open
