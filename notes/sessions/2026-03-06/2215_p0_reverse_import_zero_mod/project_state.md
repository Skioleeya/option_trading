# Project State

## Snapshot
- DateTime (ET): 2026-03-06 21:22:36 -05:00
- Branch: master
- Last Commit: b65e9ca
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED (one known async-test issue)`

## Current Focus
- Primary Goal: Complete P0 reverse-dependency cleanup (L2->L3, L3->L2, app private-member orchestration).
- Scope In:
  - Move ActiveOptions Flow/DEG runtime to `shared/services/active_options`
  - Remove `AgentG` dependency on L3 presenter implementation
  - Inject `active_options_service` via `AppContainer` public API and rewire loops
  - Remove `USE_L2` legacy fallback branch and enforce L1->L2->L3 path
  - Update SOP + boundary policy and session handoff metadata
- Scope Out:
  - Fix unrelated existing presenter contract test regressions
  - Refactor OptionChainBuilder private `_iv_sync` accessor in compute loop

## What Changed (Latest Session)
- Files:
  - `shared/services/active_options/*` (new shared neutral runtime + Flow/DEG engines)
  - `l2_decision/signals/flow/*` (compatibility shim re-export to shared service)
  - `l3_assembly/presenters/ui/active_options/presenter.py` (legacy alias to shared runtime service)
  - `l2_decision/agents/agent_g.py` (remove L3 import and active-options state ownership)
  - `app/container.py`, `app/lifespan.py`, `app/loops/compute_loop.py`, `app/loops/housekeeping_loop.py`
  - `l2_decision/reactor.py` (public `flush_audit()` API)
  - `scripts/policy/layer_boundary_rules.json`
  - `docs/SOP/SYSTEM_OVERVIEW.md`, `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
- Behavior:
  - L2 no longer imports L3 presenters; L3 no longer imports L2 signal/agent implementations for ActiveOptions.
  - App loops consume `ctr.active_options_service` public API; `_active_options_presenter` private-member path removed.
  - Legacy `USE_L2` path removed from container/lifespan/compute orchestration.
- Verification:
  - `scripts/test/run_pytest.ps1 l3_assembly/tests/test_reactor.py l2_decision/tests/test_institutional_logic.py` (PASS)
  - `scripts/test/run_pytest.ps1 l3_assembly/tests/test_presenters.py -k ActiveOptionsPresenterV2` (PASS)
  - `scripts/validate_session.ps1 -Strict` (PASS)
  - `scripts/test/run_pytest.ps1 l3_assembly/tests/test_presenters.py l3_assembly/tests/test_reactor.py l2_decision/tests/test_institutional_logic.py scripts/test/test_l0_l4_pipeline.py` (43 PASS / 2 FAIL)

## Risks / Constraints
- Risk 1: Existing unrelated presenter tests (`badge token` + `DepthProfileRow.call_gex`) still failing and can mask future regressions if left unresolved.
- Risk 2: Compute loop still reads OptionChainBuilder `_iv_sync` through `getattr(..., "_iv_sync", ...)`; this is a legacy private-access point outside this P0 scope.

## Next Action
- Immediate Next Step: Run `scripts/validate_session.ps1 -Strict` after session metadata finalization, then optionally open a follow-up hotfix for the 3 failing tests.
- Owner: Codex
