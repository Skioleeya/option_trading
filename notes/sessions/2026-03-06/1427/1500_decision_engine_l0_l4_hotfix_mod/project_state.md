# Project State

## Snapshot
- DateTime (ET): 2026-03-06 15:23:28 -05:00
- Branch: `master`
- Last Commit: `f587b9d`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `PARTIAL` (targeted suites pass; `test_l0_l4_pipeline.py` blocked by missing async pytest plugin in env)

## Current Focus
- Primary Goal: Audit all DecisionEngine indicators (threshold/state/asian color semantics) and execute `hotfix + modularization` where high-risk contract drift exists.
- Scope In:
  - `l2_decision/feature_store/store.py`
  - `l2_decision/tests/test_feature_store.py`
  - `l2_decision/events/decision_events.py`
  - `l2_decision/events/fused_signal_contract.py`
  - `l2_decision/reactor.py`
  - `l2_decision/tests/test_fused_signal_contract.py`
  - `l2_decision/tests/test_reactor_and_guards.py`
  - `l4_ui/src/components/right/DecisionEngine.tsx`
  - `l4_ui/src/components/right/decisionEngineModel.ts`
  - `l4_ui/src/components/__tests__/decisionEngineModel.test.ts`
- Scope Out:
  - Signal threshold retuning in L2 generators
  - Non-related tempfile permission residue in `test_reactor_and_guards.py`
  - Unrelated runtime artifact `data/atm_decay/atm_series_20260306.json`

## What Changed (Latest Session)
- Files:
  - `l2_decision/feature_store/store.py`
  - `l2_decision/tests/test_feature_store.py`
  - `l2_decision/events/fused_signal_contract.py` (new)
  - `l2_decision/events/decision_events.py`
  - `l2_decision/reactor.py`
  - `l2_decision/tests/test_fused_signal_contract.py` (new)
  - `l2_decision/tests/test_reactor_and_guards.py`
  - `l4_ui/src/components/right/DecisionEngine.tsx`
  - `l4_ui/src/components/right/decisionEngineModel.ts`
  - `l4_ui/src/components/__tests__/decisionEngineModel.test.ts`
- Behavior:
  - Fixed major IV realtime bug in `FeatureStore`: TTL cache is now invalidated on snapshot `version` change, preventing stale `atm_iv/iv_velocity` propagation into IV REGIME decisions.
  - Modularized FeatureStore cache logic into helper methods (`_is_cache_hit`, `_invalidate_cache_on_snapshot_change`, `_extract_snapshot_version`) for clearer contract and testability.
  - Added regression tests for version-driven cache invalidation and immediate ATM IV refresh on new versions.
  - Fixed major L2->L4 contract bug: DecisionEngine `regime` / `gex_intensity` are no longer hardcoded to `NORMAL/NEUTRAL`.
  - Added modular fused-signal contract helper for `iv_regime` normalization and `gex_intensity` classification.
  - L2 reactor now derives runtime `gex_intensity` from net_gex (config thresholds) and stamps `iv_regime`/`gex_intensity` into DecisionOutput.
  - Added backend regression tests locking contract behavior.
  - Fixed frontend regime label formatter that produced per-letter split (`N E U T R A L`).
  - Added explicit `MODERATE -> badge-amber` mapping and test coverage.

## Verification
- `./scripts/test/run_pytest.ps1 l2_decision/tests/test_feature_store.py l2_decision/tests/test_signals.py l2_decision/tests/test_reactor_and_guards.py::TestL2DecisionReactor::test_fused_signal_contract_uses_runtime_regime_and_gex_labels -q` (pass, 81 passed)
- `./scripts/test/run_pytest.ps1 l2_decision/tests/test_fused_signal_contract.py l2_decision/tests/test_reactor_and_guards.py::TestL2DecisionReactor::test_fused_signal_contract_uses_runtime_regime_and_gex_labels -q` (pass, 5 passed)
- `./scripts/test/run_pytest.ps1 l2_decision/tests/test_signals.py -q` (pass, 40 passed)
- `./scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py -q` (fail, async pytest plugin missing in env)
- `npm --prefix l4_ui run test -- src/components/__tests__/decisionEngineModel.test.ts` (pass, escalated after sandbox `spawn EPERM`)
- `npm --prefix l4_ui run build` (pass)

## Risks / Constraints
- Risk 1: Full `l2_decision/tests/test_reactor_and_guards.py` still has known temp-permission residue failures (`WinError 5`) in this environment; unrelated to this hotfix.
- Risk 2: DecisionEngine `IV REGIME` card weight remains `0%` by design in current L2 fusion (regime gating signal excluded from direct fusion weights).
- Risk 3: End-to-end async pipeline test currently cannot run in this environment without async pytest plugin availability.

## Next Action
- Immediate Next Step: Add render-level DecisionEngine tests for `weight vs conf` semantics and explicit `iv_regime` card behavior; then restore runnable async plugin path for `scripts/test/test_l0_l4_pipeline.py`.
- Owner: Codex / next agent
