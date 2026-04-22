# Project State

## Snapshot
- DateTime (ET): 2026-04-03 11:20:57 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `6c68068`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED` (strict backend booted, Arrow IPC mapping repeatedly unavailable)
  - L0-L4 Pipeline: `DEGRADED` (WS reachable but strict penetration/audit checks fail)

## Current Focus
- Primary Goal: Enforce hard-fail policy across startup and penetration-test tooling (no degraded/compat/fallback execution path).
- Scope In:
  - `scripts/ops/start_backend.ps1`
  - `scripts/ops/start_all.ps1`
  - `shared/services/l0_runtime/source/runtime/bootstrap.py`
  - `scripts/test/test_l0_l4_pipeline.py`
  - `scripts/diag/audit_intraday_core_flow.py`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
  - `docs/SOP/L0_DATA_FEED.md`
- Scope Out:
  - L1/L2/L3 numerical algorithm changes
  - ActiveOptions fallback engine internals
  - Frontend rendering logic changes

## What Changed (Latest Session)
- Files:
  - Updated strict startup scripts (`start_backend`, `start_all`) to remove degraded retry/entry.
  - Updated L0 startup connectivity probe to reject `strict_connectivity=false` and fail fast.
  - Reworked `test_l0_l4_pipeline.py` to assert-fail on connection/contract violations (no silent pass).
  - Hardened `audit_intraday_core_flow.py` to strict PASS/FAIL semantics and degraded-row rejection.
  - Synced SOP startup policy to strict-only/hard-fail wording.
- Behavior:
  - `-Degraded` startup path is now blocked at script entry.
  - L0 runtime startup probe no longer permits non-strict operation.
  - L0-L4 penetration test now fails immediately when backend is unreachable or payload contracts are incomplete.
  - Intraday core flow audit no longer emits WARN pass-through; non-compliant states are FAIL.
- Verification:
  - `scripts/ops/start_backend.ps1 -DryRun` succeeded in strict mode.
  - `scripts/ops/start_backend.ps1 -Degraded -DryRun` failed as expected (policy enforcement).
  - `scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py -q` failed with `ConnectionRefusedError` (expected hard-fail when backend down).
  - `scripts/test/run_pytest.ps1 app/tests/test_health_route_diagnostics.py -q` passed (`2 passed`).
  - `scripts/ops/start_backend.ps1` strict boot launched backend process; logs show repeated Arrow IPC mapping errors (`sentinel_shm_live_arrow`).
  - `scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py -q` rerun failed on strict contract assertion (`Missing governor_telemetry in top-level payload`).
  - `python scripts/diag/audit_intraday_core_flow.py --json` returned `overall=FAIL` with all 5 checks failed.
  - `scripts/validate_session.ps1 -Strict` passed after evidence sync.

## Risks / Constraints
- Risk 1: L0 runtime keeps emitting Arrow IPC mapping errors (`winerr=2` on `sentinel_shm_live_arrow`), blocking strict freshness/continuity.
- Risk 2: ActiveOptions remains fully degraded (`rows_degraded=5`), violating strict no-fallback quality expectation.

## Next Action
- Immediate Next Step: Keep strict-only policy, continue debug on Arrow IPC mapping/root-cause path, and rerun penetration+audit until both PASS.
- Owner: Codex
