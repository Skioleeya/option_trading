## Why

`formula-semantic-*` 首轮家族已经完成 A/B/D，但仍存在三类 residual scope：

1. 旧 `Phase C` 没落地，`FLOW_D/E/G` provenance、wall/flip proxy 术语、registry 仍未成体系。
2. `VRPVetoGuard` 与参考配置仍保留半成品单位口径，`config_cloud_ref` 与 live config 也有漂移。
3. L3/L4 live path 仍主要消费 legacy `skew_25d_normalized` / `net_charm` 语义，尚未切到 canonical source-of-truth。

直接续写旧家族会把“已实现历史”和“新 residual scope”混在一起，不利于收口、审计和归档。因此需要新开一个 follow-up 父提案，只治理 residual-only 范围。

## What Changes

本父提案只定义 follow-up 家族的依赖顺序与门禁，不直接承载运行时代码：

1. 固化 follow-up 顺序：`E -> F -> G -> H`
2. 旧 A/B/D 视为已实现历史；旧 `Phase C` 未完成范围改由 follow-up `Phase E` 接管
3. live canonical cutover 只允许替换 L3/L4 内部 source-of-truth，不允许改 WebSocket 顶层 wire shape
4. `VRP / GEX / wall / flip / FLOW / RR25 / charm` 语义改动必须来自 shared/L1/L2 中立合同
5. 最后一个 child 负责旧提案任务状态、closure 与 residual handoff 对账

## Scope

- 新 follow-up 父提案
- 4 个新 child proposals
- 不直接提交 L0/L1/L2/L3/L4 runtime 代码实现

## Child Proposals

- `formula-semantic-followup-phase-e-provenance-and-proxy-registry`
- `formula-semantic-followup-phase-f-guard-unit-and-reference-sync`
- `formula-semantic-followup-phase-g-live-canonical-contract-cutover`
- `formula-semantic-followup-phase-h-openspec-reconciliation`

## Parent / History

- Follow-up family is residual-only and keeps the old `formula-semantic-*` family as immutable implementation history.
- Old `formula-semantic-phase-c-provenance-and-heuristic-labels` remains as the historical proposal record, but its unfinished scope is handed off to follow-up `Phase E`.

## Reconciliation Status (2026-03-13)

- After Phase H reconciliation, this follow-up parent is the sole active residual closure entry for formula semantics governance.
- Old parent `formula-semantic-contract-parent-governance` is historical/archived and no longer carries active residual scope.
