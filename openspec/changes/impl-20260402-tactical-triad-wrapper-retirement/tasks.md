## Scope

- [x] Confirm prerequisite `refactor-dependency-20260402-tactical-triad-shared-rust-export` is complete:
  - `python -c "from shared_rust.services import tactical_compute_vrp, tactical_classify_vrp_state, tactical_normalize_svol_state, tactical_resolve_svol_fields; print('prereq-ok')"` passed
- [x] Confirm all 5 consumer files and their exact import locations:
  - `l2_decision/agents/agent_g.py`
  - `l2_decision/feature_store/extractors_registry.py`
  - `l2_decision/feature_store/extractors_volatility.py`
  - `l2_decision/guards/rail_engine.py`
  - `l3_assembly/assembly/ui_state_tracker.py`
- [x] Mark non-target scope: no call-site changes, no Rust changes, no other system files

## Implementation

- [x] Step 1 — retarget `l2_decision/agents/agent_g.py`
- [x] Step 2 — retarget `l2_decision/feature_store/extractors_registry.py`
- [x] Step 3 — retarget `l2_decision/feature_store/extractors_volatility.py`
- [x] Step 4 — retarget `l2_decision/guards/rail_engine.py`
- [x] Step 5 — retarget `l3_assembly/assembly/ui_state_tracker.py`
- [x] Step 6 — delete `shared/system/tactical_triad_logic.py`
- [x] Step 7 — residual reference scan
- [x] Step 8 — combined consumer import smoke

## Verification

- [x] Prerequisite check passes
- [x] Per-step import smokes pass using valid module symbols (`AgentG`, `build_default_extractors`, `_RealizedVolatilityMetricsExtractor`, `GuardRailEngine`, `UIStateTracker`)
- [x] `shared/system/tactical_triad_logic.py` deleted
- [x] Residual reference scan returns 0 matches
- [x] Combined consumer smoke passes
- [ ] `pwsh scripts/test/run_pytest.ps1 l2_decision/tests/ l3_assembly/tests/` passes
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passes
- [x] SOP-EXEMPT: import-path change only; no SOP semantic contract changed

## DoD

- [x] `shared/system/tactical_triad_logic.py` does not exist
- [x] Zero runtime references to `shared.system.tactical_triad_logic` in `.py` source
- [x] All 5 consumers import from `shared_rust.services` with `as` aliases where needed
- [x] No call-site changes in consumer files
- [x] Consumer import smokes pass
- [x] Strict gate passes

## Evidence

- `python -c "from shared_rust.services import tactical_compute_vrp, tactical_classify_vrp_state, tactical_normalize_svol_state, tactical_resolve_svol_fields; print('prereq-ok')"` -> PASS
- `python -c "from l2_decision.agents.agent_g import AgentG; print('agent_g-ok')"` -> PASS
- `python -c "from l2_decision.feature_store.extractors_registry import build_default_extractors; print('registry-ok', len(build_default_extractors()) > 0)"` -> PASS
- `python -c "from l2_decision.feature_store.extractors_volatility import _RealizedVolatilityMetricsExtractor; print('volatility-ok')"` -> PASS
- `python -c "from l2_decision.guards.rail_engine import GuardRailEngine; print('rail-ok')"` -> PASS
- `python -c "from l3_assembly.assembly.ui_state_tracker import UIStateTracker; print('ui-state-ok')"` -> PASS
- `python -c "import shared.system.tactical_triad_logic"` -> `ModuleNotFoundError` (expected)
- `rg "shared\.system\.tactical_triad_logic" app l0_ingest l1_compute l2_decision l3_assembly l4_ui shared scripts --glob "*.py"` -> no matches
- `python -c "from l2_decision.agents.agent_g import AgentG; from l2_decision.feature_store.extractors_volatility import _RealizedVolatilityMetricsExtractor; from l2_decision.guards.rail_engine import GuardRailEngine; from l3_assembly.assembly.ui_state_tracker import UIStateTracker; print('all-consumers-ok')"` -> PASS
- `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l2_decision/tests/ l3_assembly/tests/` -> FAIL (pre-existing `tmp/pytest_cache` ACL ownership mismatch)
- `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` -> PASS
