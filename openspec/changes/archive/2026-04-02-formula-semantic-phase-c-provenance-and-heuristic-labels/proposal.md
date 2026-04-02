## Why

审计指出 `FLOW_D/E/G`、`call_wall/put_wall`、`flip_level_cumulative` 没有 2024-2026 统一标准公式，但代码和注释里仍保留了“像学术标准”的表述。仅靠 scattered comments 不足以长期约束新改动。

需要一个中立 provenance registry，把“academic/proxy/heuristic、单位、符号约定、数据前提”固化成可测试合同。

## What Changes

本子提案引入统一 provenance 注册表，并用它收敛启发式公式说明：

1. 新增中立模块建议：`shared/contracts/metric_semantics.py`
2. 为下列字段登记 provenance：
   - `net_gex`, `zero_gamma_level`, `call_wall`, `put_wall`, `flip_level_cumulative`
   - `FLOW_D`, `FLOW_E`, `FLOW_G`
   - `vol_risk_premium`, `skew_25d_normalized`, `rr25_call_minus_put`
3. 将 `FLOW_D/E/G` 的 docstring 从“论文公式”改为“research heuristic / public-data proxy”
4. 将 wall/flip 文案统一降级为 `trading-practice proxy`

## Scope

- `shared/contracts/metric_semantics.py`（新）
- `shared/services/active_options/flow_engine_d.py`
- `shared/services/active_options/flow_engine_e.py`
- `shared/services/active_options/flow_engine_g.py`
- `l1_compute/aggregation/streaming_aggregator.py`
- `l2_decision/agents/services/greeks_extractor.py`
- `docs/OPTION_PAPER_FORMULA_AUDIT_2024_2026.md`
- `docs/OPTION_PAPER_FORMULA_SOURCEBOOK_2024_2026.md`
- `docs/SOP/L1_LOCAL_COMPUTATION.md`
- `docs/SOP/L2_DECISION_ANALYSIS.md`

## Parent

- `formula-semantic-contract-parent-governance`

## Reconciliation Status (2026-03-13)

- This proposal is retained as historical record.
- Unfinished residual scope is handed off to: `formula-semantic-followup-phase-e-provenance-and-proxy-registry`.
- Active residual closure path is the follow-up family under `formula-semantic-followup-parent-governance`.
