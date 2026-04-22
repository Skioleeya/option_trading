## ADDED Requirements

### Requirement: Follow-up Formula Semantics Work Must Be Residual-Only
新的 follow-up 家族 SHALL 只覆盖旧 `formula-semantic-*` 家族未完成的 residual scope，不得重写已实现的 A/B/D 阶段。

#### Scenario: Proposal Review
- **WHEN** 工程师检查 follow-up parent proposal
- **THEN** 文档 MUST 明确旧 A/B/D 为已实现历史，旧 C 的 unfinished scope 由 follow-up E 接管

### Requirement: Live Canonical Cutover Must Preserve Top-Level Wire Shape
follow-up `Phase G` SHALL 只替换 L3/L4 internal source-of-truth，不得更改 WebSocket 顶层字段命名或 schema 包络。

#### Scenario: L3/L4 Cutover Review
- **WHEN** 工程师阅读 `Phase G` proposal/spec
- **THEN** 文档 MUST 明确 canonical cutover 不等于 payload top-level rename

### Requirement: Reconciliation Must Run After Runtime Residual Scope Closes
旧/new proposal 状态对账 SHALL 只能在 follow-up `Phase H` 中执行。

#### Scenario: Governance Ordering
- **WHEN** 工程师检查 follow-up task order
- **THEN** reconciliation / closure MUST 出现在最后一个 child
