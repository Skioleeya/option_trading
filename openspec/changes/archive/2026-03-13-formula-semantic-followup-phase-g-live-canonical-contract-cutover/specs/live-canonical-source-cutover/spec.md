## ADDED Requirements

### Requirement: Live Skew State Must Use Canonical RR25 Source
L3 live skew mapping SHALL 使用 `rr25_call_minus_put` 作为唯一 source-of-truth，并保留 `skew_25d_valid` 作为有效性 gate。

#### Scenario: Live Skew Mapping
- **WHEN** L3 生成 `ui_state.skew_dynamics`
- **THEN** `skew_25d_normalized` MUST NOT 再作为 live source-of-truth

### Requirement: Live Tactical Charm Must Use Canonical Raw-Sum Source
L3 live tactical charm SHALL 使用 `net_charm_raw_sum` 作为唯一 source-of-truth。

#### Scenario: Live Tactical Triad Mapping
- **WHEN** L3 生成 `ui_state.tactical_triad.charm`
- **THEN** legacy `net_charm` MUST NOT 再作为 live source-of-truth

### Requirement: Canonical Cutover Must Preserve Top-Level Payload Shape
canonical cutover SHALL 不改变 payload 顶层字段命名或 schema 包络。

#### Scenario: Payload Contract Review
- **WHEN** 工程师检查 L3/L4 提案与测试
- **THEN** 顶层 payload field names MUST 保持兼容
