# openspec-reconciliation Specification

## Purpose
TBD - created by archiving change formula-semantic-followup-phase-h-openspec-reconciliation. Update Purpose after archive.
## Requirements
### Requirement: Historical Formula Phases Must Be Backfilled Before Closure
旧 `formula-semantic` 家族中已实现的 A/B/D phases SHALL 在 reconciliation 中回填任务状态与验证证据。

#### Scenario: Historical Proposal Audit
- **WHEN** 工程师审阅旧 A/B/D tasks
- **THEN** 这些 tasks MUST 不再保留明显与实现事实不符的未完成状态

### Requirement: Old Phase C Residual Scope Must Hand Off to Follow-up Phase E
旧 `formula-semantic-phase-c-provenance-and-heuristic-labels` 的 unfinished scope SHALL 显式标记由 follow-up `Phase E` 接管。

#### Scenario: Residual Scope Audit
- **WHEN** 工程师同时检查旧 `Phase C` 与新 `Phase E`
- **THEN** 文档 MUST 明确只有新 `Phase E` 保持 active residual scope

### Requirement: Follow-up Parent Must Become the Sole Residual Closure Entry
在 reconciliation 完成后，新 follow-up parent SHALL 成为 formula semantics residual scope 的唯一 closure 入口。

#### Scenario: Governance Closure Review
- **WHEN** 工程师检查 old/new parent proposals
- **THEN** 旧 parent MUST 只保留历史记录，新 parent MUST 负责 residual closure

