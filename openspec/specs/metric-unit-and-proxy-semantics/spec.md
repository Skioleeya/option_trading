# metric-unit-and-proxy-semantics Specification

## Purpose
TBD - created by archiving change formula-semantic-phase-a-vrp-gex-stopgap. Update Purpose after archive.
## Requirements
### Requirement: VRP Must Use a Single Percent-Point Contract
`vol_risk_premium` SHALL 在 L2 特征层与 L3 解释层采用同一百分比点口径。

#### Scenario: Baseline HV Stored as Decimal
- **WHEN** `shared.config.agent_g.vrp_baseline_hv = 0.15`
- **THEN** L2 与 L3 MUST 一致地将其解释为 `15.0%`，且 `vol_risk_premium` 计算结果一致。

### Requirement: GEX Family Must Be Labeled as Proxy
`net_gex`、`zero_gamma_level`、`call_wall`、`put_wall` SHALL 被文档与注释明确标识为公开 `OI` 推导的 proxy，而非真实 dealer inventory truth。

#### Scenario: GEX Semantics Appears in Service Output
- **WHEN** `GammaQualAnalyzer` 或 `EnrichedSnapshot` 暴露相关字段
- **THEN** 其注释、说明与 SOP MUST 明确标注 `OI-based proxy` 或等价语义。

### Requirement: GEX Regime Threshold Documentation Must Match Runtime Config
`shared.models.microstructure.GexRegime` 的阈值说明 SHALL 与 `shared.config.agent_g` 默认配置一致。

#### Scenario: Regime Documentation Review
- **WHEN** 工程师查看 `GexRegime` 模型说明
- **THEN** 文档 MUST 不再出现已失效的 `200M/1000M` 阈值描述。

