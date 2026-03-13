# Project State

## Snapshot
- DateTime (ET): 2026-03-12 14:36:10 -04:00
- Branch: `master`
- Last Commit: `bc51cc7`
- Environment:
  - Market: `OPEN`
  - Data Feed: `UNVERIFIED`
  - L0-L4 Pipeline: `UNVERIFIED`

## Current Focus
- Primary Goal: Execute OpenSpec `formula-semantic-phase-a-vrp-gex-stopgap`.
- Scope In:
  - Unify `vol_risk_premium` to percent-point semantics.
  - Clarify `net_gex/call_wall/put_wall/zero_gamma_level` as proxy contracts.
  - Sync L1/L2 SOP wording and add targeted regression coverage.
- Scope Out:
  - No L0 ingest changes.
  - No Phase B renames (`RR25`, `net_vanna_raw_sum`, `net_charm_raw_sum`).
  - No Phase D research metric expansion.

## What Changed (Latest Session)
- Files:
  - `l2_decision/feature_store/extractors.py`
  - `shared/system/tactical_triad_logic.py`
  - `shared/config/agent_g.py`
  - `shared/models/microstructure.py`
  - `l1_compute/output/enriched_snapshot.py`
  - `l2_decision/agents/services/gamma_qual_analyzer.py`
  - `l2_decision/tests/test_feature_store.py`
  - `l2_decision/tests/test_reactor_and_guards.py`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `docs/SOP/L2_DECISION_ANALYSIS.md`
- Behavior:
  - `vol_risk_premium` now reuses `compute_vrp()` and always emits percentage points.
  - `vrp_baseline_hv=0.15` and `vrp_baseline_hv=15.0` are explicitly documented as equivalent inputs for feature-level VRP.
  - `GEX/wall/zero-gamma` comments and SOP wording now consistently describe `OI-based proxy` / `trading-practice proxy` semantics.
  - GEX regime docstrings now match the live `20B/100B` MMUSD threshold scale.
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l2_decision/tests/test_feature_store.py l2_decision/tests/test_reactor_and_guards.py l2_decision/tests/test_gamma_qual_analyzer.py`
  - Result: `105 passed, 1 warning`

## Risks / Constraints
- Risk 1: `VRPVetoGuard` still uses decimal-fraction guard thresholds; Phase A documents this explicitly but does not migrate guard semantics.
- Risk 2: Working tree contains many unrelated user/runtime changes; this session intentionally avoided reverting or normalizing them.

## Next Action
- Immediate Next Step: Execute Phase B for `skew_25d` / raw Greek sum naming contracts after reviewing downstream consumers.
- Owner: Codex / next implementing agent
