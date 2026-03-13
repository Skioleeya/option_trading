# skew-and-raw-greek-contracts Specification

## Purpose
TBD - created by archiving change formula-semantic-phase-b-skew-and-raw-exposure-contracts. Update Purpose after archive.
## Requirements
### Requirement: RR25 Must Have a Canonical Call-Minus-Put Field
系统 SHALL 提供标准市场口径的 25Δ risk reversal 字段 `rr25_call_minus_put`。

#### Scenario: Valid 25Δ Legs Available
- **WHEN** CALL `+0.25` 与 PUT `-0.25` 两侧 delta 均在容差内
- **THEN** 系统 MUST 输出 `rr25_call_minus_put = IV_call(25Δ) - IV_put(25Δ)`。

### Requirement: Legacy Skew Field Must Remain Explicitly Non-Canonical
`skew_25d_normalized` SHALL 保留为兼容字段，但必须明确其语义是 `(put_iv - call_iv) / atm_iv`，不得再被描述为标准 `RR25`。

#### Scenario: Existing Feature Consumers Read Legacy Skew
- **WHEN** 下游继续读取 `skew_25d_normalized`
- **THEN** 该字段 MUST 保持兼容值，同时文档与描述 MUST 明确其非 canonical 性质。

### Requirement: Raw Greek Sum Fields Must Be Distinguished from Exposures
L1/L2 SHALL 提供 `net_vanna_raw_sum` 与 `net_charm_raw_sum` 作为 canonical 命名，并保留 `net_vanna` / `net_charm` 兼容 alias。

#### Scenario: Snapshot Export
- **WHEN** `EnrichedSnapshot` 或研究导出暴露 vanna/charm 汇总字段
- **THEN** canonical 字段 MUST 可用，且 legacy alias MUST 与 canonical 值一致。

