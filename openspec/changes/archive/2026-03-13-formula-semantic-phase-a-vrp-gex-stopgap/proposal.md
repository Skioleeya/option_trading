## Why

审计文档指出两项 `P0` 风险已在运行时真实存在：

1. `vol_risk_premium` 在 L2 与 L3 的单位解释不一致。
2. `GEX / zero_gamma / wall` 仍有被误读成真实 dealer inventory 的风险。

这两项会直接影响信号解释、Guard 触发判断和前端文案，必须先止血。

## What Changes

本子提案只处理 `VRP` 单位与 `GEX proxy` 语义，不做字段改名：

1. 统一 `vol_risk_premium` 为百分比点口径。
2. 对齐 `shared/config/agent_g.py` 的 `vrp_baseline_hv` 与 `shared/system/tactical_triad_logic.py` 的标准化逻辑。
3. 修正 `shared/models/microstructure.py` 与 `shared/config/agent_g.py` 的 GEX regime 阈值注释冲突。
4. 在 L1/L2/SOP 注释中明确：
   - `net_gex` 是 `OI-based proxy`
   - `zero_gamma_level` 是 `OI-based zero-gamma proxy`
   - `call_wall/put_wall` 是 `trading-practice wall proxy`

## Scope

- `l2_decision/feature_store/extractors.py`
- `shared/system/tactical_triad_logic.py`
- `shared/config/agent_g.py`
- `shared/models/microstructure.py`
- `l1_compute/output/enriched_snapshot.py`
- `l2_decision/agents/services/gamma_qual_analyzer.py`
- `docs/SOP/L1_LOCAL_COMPUTATION.md`
- `docs/SOP/L2_DECISION_ANALYSIS.md`

## Parent

- `formula-semantic-contract-parent-governance`
