# guard-vrp-unit-sync Specification

## Purpose
TBD - created by archiving change formula-semantic-followup-phase-f-guard-unit-and-reference-sync. Update Purpose after archive.
## Requirements
### Requirement: Guard VRP Proxy Must Be Expressed in Percentage Points
`VRPVetoGuard` SHALL 使用 `% points` 口径解释其 guard 专用 VRP proxy。

#### Scenario: Legacy Threshold Compatibility
- **WHEN** `guard_vrp_entry_threshold=0.15` 且 `guard_vrp_exit_threshold=0.13`
- **THEN** 系统 MUST 将其解释为 `15.0` 与 `13.0` percent points

### Requirement: Guard VRP Proxy Must Remain Distinct from Live Feature VRP
`guard_vrp_proxy_pct` SHALL 与 `vol_risk_premium` 作为不同语义字段维护，不得混用说明文案。

#### Scenario: Formula Doc Audit
- **WHEN** 工程师检查 operator-facing metrics map
- **THEN** 文档 MUST 明确区分 live feature proxy 与 guard-only proxy

### Requirement: Cloud Reference Config Must Match Live Threshold Scale
`shared/config_cloud_ref/agent_g.py` SHALL 与 live config 使用同一 GEX / guard 阈值量级。

#### Scenario: Config Drift Audit
- **WHEN** 检查 cloud ref 与 live config
- **THEN** 参考配置 MUST 不再保留旧 `200M/1000M` 量级描述

