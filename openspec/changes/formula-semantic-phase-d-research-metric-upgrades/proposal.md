## Why

前面三个阶段只解决“语义正确”。但审计还给出了两条明确的 `P2` 研究升级方向：

1. 提供标准市场口径的 `RR25`
2. 提供基于 realized volatility 的更标准 `VRP`

这两项不应和 `P0/P1` 混改，但应在提案层先明确未来落地方式。

## What Changes

本子提案定义两类非阻断升级：

1. 双轨 skew：
   - `skew_25d_normalized` 保留为工程特征
   - `rr25_call_minus_put` 作为标准研究字段进入 feature/research path
2. 双轨 VRP：
   - `vol_risk_premium` 保留为现网 proxy
   - 新增 `vrp_realized_based`
   - 新增 realized vol 计算组件，例如 `shared/services/realized_volatility.py`
3. 为未来 inventory-aware gamma 升级预留字段命名空间，但不在本阶段要求接入 proprietary 数据。

## Scope

- `shared/services/realized_volatility.py`（新）
- `l2_decision/feature_store/extractors.py`
- `shared/services/research_feature_store.py`
- `docs/OPTION_PAPER_FORMULA_AUDIT_2024_2026.md`
- `docs/OPTION_PAPER_FORMULA_SOURCEBOOK_2024_2026.md`
- `docs/SOP/L2_DECISION_ANALYSIS.md`

## Parent

- `formula-semantic-contract-parent-governance`
