# research-metric-upgrades Specification

## Purpose
TBD - created by archiving change formula-semantic-phase-d-research-metric-upgrades. Update Purpose after archive.
## Requirements
### Requirement: Standard RR25 Must Be Available for Research Paths
系统 SHALL 为研究与诊断路径提供标准 `RR25` 字段 `rr25_call_minus_put`。

#### Scenario: Research Export Requests Canonical Skew
- **WHEN** 研究导出请求标准 25Δ risk reversal
- **THEN** 导出结果 MUST 包含 `rr25_call_minus_put`，且不依赖 legacy `skew_25d_normalized` 的符号约定。

### Requirement: Realized-Vol-Based VRP Must Be Isolated from Live Proxy VRP
系统 SHALL 将 `vrp_realized_based` 与现有 `vol_risk_premium` 作为不同字段隔离维护。

#### Scenario: Live Feature Path Uses Proxy VRP
- **WHEN** 现网 L2 继续读取 `vol_risk_premium`
- **THEN** 引入 `vrp_realized_based` MUST NOT 隐式改变该字段的现有语义。

### Requirement: Inventory-Aware Gamma Upgrades Must Not Overwrite Proxy Fields
未来若接入 inventory-aware gamma 数据，系统 SHALL 使用新字段命名空间，而不是覆盖现有 `net_gex`/`zero_gamma_level` proxy 字段。

#### Scenario: Proprietary Gamma Data Becomes Available
- **WHEN** 更高质量的 inventory 数据源接入
- **THEN** 新实现 MUST 新增 canonical inventory-aware 字段，而不是复用现有 proxy 字段名。

