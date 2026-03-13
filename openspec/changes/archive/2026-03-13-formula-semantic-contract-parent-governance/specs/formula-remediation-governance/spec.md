## ADDED Requirements

### Requirement: Formula Remediation Must Use Parent-Child Governance
公式语义整改 SHALL 以父提案 + 子提案方式推进，不得在单个 change 中混合 `P0` 止血、合同更名、provenance 治理与研究增强。

#### Scenario: Mixed Remediation Change
- **WHEN** 一个变更同时修改 `VRP` 单位、`RR25` 合同、`FLOW_D/E/G` provenance 和 realized-vol 新字段
- **THEN** 该变更 MUST 视为治理违规并拆分为父提案定义的子提案阶段。

### Requirement: Child Proposal Ordering
子提案 SHALL 按 `formula-semantic-phase-a-vrp-gex-stopgap -> formula-semantic-phase-b-skew-and-raw-exposure-contracts -> formula-semantic-phase-c-provenance-and-heuristic-labels -> formula-semantic-phase-d-research-metric-upgrades` 顺序实施。

#### Scenario: Later Phase Starts Before Earlier Phase Closes
- **WHEN** Phase C 或 D 在 Phase A/B 未完成前开始实现
- **THEN** 该实现 MUST 视为越序合并并阻断收口。

### Requirement: Compatibility-First Contract Changes
任何字段改名或 canonical 字段引入 SHALL 采用兼容 alias 过渡，不得直接删除现有运行时字段。

#### Scenario: Raw Greek Field Rename
- **WHEN** `net_vanna` 或 `net_charm` 被收敛到更精确命名
- **THEN** 旧字段 MUST 保留为兼容 alias 至少一个阶段，并由测试覆盖两者一致性。
