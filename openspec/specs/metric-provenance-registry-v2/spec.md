# metric-provenance-registry-v2 Specification

## Purpose
TBD - created by archiving change formula-semantic-followup-phase-e-provenance-and-proxy-registry. Update Purpose after archive.
## Requirements
### Requirement: Formula Metrics Must Have Machine-Readable Provenance
关键公式指标 SHALL 在中立 registry 中登记 `classification`、`unit`、`sign_convention`、`data_prerequisites`、`canonical_description` 与 `live_usage`。

#### Scenario: Registry Lookup
- **WHEN** 工程师查询 `FLOW_D`、`net_gex`、`rr25_call_minus_put` 或 `net_charm_raw_sum`
- **THEN** 系统 MUST 返回该指标的 provenance 和 live/research usage

### Requirement: Flow Engines Must Not Claim Unsupported Academic Exactness
`FLOW_D`、`FLOW_E`、`FLOW_G` 的实现说明 SHALL 标记为研究启发式或公开数据 proxy，不得宣称为统一 academic exact formula。

#### Scenario: Flow Engine Docstring Audit
- **WHEN** 检查 flow engine 顶部说明
- **THEN** 文案 MUST 不再把当前 composite formula 写成已证实的统一 academic formula

### Requirement: Wall and Flip Terminology Must Be Explicitly Proxy-Labeled
`call_wall`、`put_wall`、`flip_level_cumulative` SHALL 被导出为 `trading-practice proxy` 或等价语义。

#### Scenario: L1/L2 Export Review
- **WHEN** 工程师审阅相关字段的导出注释或 bridge 说明
- **THEN** 文档 MUST 不再把这些字段写成 2024-2026 论文统一正式定义

