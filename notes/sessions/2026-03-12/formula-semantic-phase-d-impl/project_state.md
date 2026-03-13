# Project State

## Snapshot
- DateTime (ET): 2026-03-12 15:04:09 -04:00
- Branch: `master`
- Last Commit: `bc51cc7`
- Environment:
  - Market: `OPEN`
  - Data Feed: `UNVERIFIED`
  - L0-L4 Pipeline: `UNVERIFIED`

## Current Focus
- Primary Goal: Execute Phase D light research-metric upgrades without changing live decision defaults.
- Scope In:
  - Add neutral `shared/services/realized_volatility.py`.
  - Add `realized_volatility_15m` and `vrp_realized_based` to optional/research L2 feature paths.
  - Persist `rr25_call_minus_put`, `realized_volatility_15m`, `vol_risk_premium`, and `vrp_realized_based` as explicit research feature columns.
  - Record downstream alias scan result for `net_charm` / `net_vanna`.
- Scope Out:
  - No replacement of live `vol_risk_premium`.
  - No L3/L4 contract rename for `net_charm` / `net_vanna`.
  - No official LongPort `historical_volatility/premium/standard` runtime adoption in this session.

## What Changed (Latest Session)
- Files:
  - `shared/services/realized_volatility.py`
  - `shared/tests/test_realized_volatility.py`
  - `l2_decision/feature_store/extractors.py`
  - `l2_decision/tests/test_feature_store.py`
  - `shared/services/research_feature_store.py`
  - `l3_assembly/tests/test_research_feature_store.py`
  - `docs/SOP/L2_DECISION_ANALYSIS.md`
  - `docs/IV_METRICS_MAP.md`
  - `openspec/changes/formula-semantic-phase-d-research-metric-upgrades/tasks.md`
- Behavior:
  - Added rolling `realized_volatility_15m` as a decimal annualized research feature from spot log returns.
  - Added `vrp_realized_based` as a research-only `% point` VRP using explicit RV-to-percent conversion before `compute_vrp()`.
  - Added explicit research-store columns for dual-track skew/VRP fields instead of relying only on `feature_vector_json`.
  - Downstream scan confirmed `net_charm` is already embedded in L3 presentation semantics, so alias retirement is deferred.
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l2_decision/tests/test_feature_store.py shared/tests/test_realized_volatility.py l3_assembly/tests/test_research_feature_store.py`
  - Result: `55 passed`

## Risks / Constraints
- Risk 1: `realized_volatility_15m` is based on local rolling spot history, not official LongPort volatility fields; later data-priority decisions may still supersede this path.
- Risk 2: L3 tactical-triad presentation still consumes `net_charm` by legacy name, so Phase B alias continuity remains required.

## Next Action
- Immediate Next Step: Decide whether official LongPort `historical_volatility/premium/standard` fields should augment or supersede the new research RV path before broader rollout.
- Owner: Codex / next implementing agent
