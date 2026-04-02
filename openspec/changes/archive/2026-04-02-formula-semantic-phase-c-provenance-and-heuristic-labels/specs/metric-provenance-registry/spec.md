## ADDED Requirements

### Requirement: Key Formula Metrics Must Have Machine-Readable Provenance
关键公式指标 SHALL 在中立 registry 中登记其 `classification`、`unit`、`sign_convention` 与 `data_prerequisites`。

#### Scenario: Metric Review
- **WHEN** 工程师查询 `net_gex`、`zero_gamma_level`、`FLOW_D` 或 `skew_25d_normalized`
- **THEN** 系统 MUST 能返回该指标是 `academic_standard`、`proxy` 或 `heuristic` 以及对应单位和符号约定。

### Requirement: Flow Engines Must Not Claim Unsupported Academic Exactness
`FLOW_D`、`FLOW_E`、`FLOW_G` 的实现说明 SHALL 标记为研究启发式或公开数据 proxy，不得宣称为统一标准学术公式。

#### Scenario: Flow Engine Docstring Audit
- **WHEN** 检查 flow engine 顶部说明
- **THEN** 文案 MUST 不再把当前 exact composite formula 表述为已证实的统一 academic formula。

### Requirement: Wall and Flip Terminology Must Be Labeled as Trading-Practice Proxy
`call_wall`、`put_wall`、`flip_level_cumulative` SHALL 被描述为 `trading-practice proxy` 或等价语义。

#### Scenario: Wall Metric Export
- **WHEN** 相关字段被导出到研究或服务层
- **THEN** 对应说明 MUST 不将其描述成 2024-2026 论文统一正式定义。
