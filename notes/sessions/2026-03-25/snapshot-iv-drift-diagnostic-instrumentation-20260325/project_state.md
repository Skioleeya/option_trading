# Project State

## Snapshot
- DateTime (ET): 2026-03-25 09:10:25 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `70cc81b`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Add minimal diagnostic-only instrumentation for `snapshot_version_iv_drift` so runtime diagnostics reveal the selected ATM contract and IV source without changing probe behavior.
- Scope In: `l1_compute` ATM-IV context helper, L1 extra metadata instrumentation, `/debug/persistence_status` diagnostic exposure, targeted tests, and session/context records.
- Scope Out: Any change to probe activation logic, IV sync cadence, compute semantics, or runtime process restart behavior.

## What Changed (Latest Session)
- Files: Added `l1_compute/observability/atm_iv_context.py`; updated `l1_compute/reactor.py`, `app/routes/health.py`, `app/tests/test_health_route_diagnostics.py`; added `l1_compute/tests/test_atm_iv_context.py`.
- Behavior: Runtime logic is unchanged. L1 now records ATM IV diagnostics (`atm_symbol/strike/distance/raw_iv/iv_source/confidence/spot`) in `extra_metadata`, and `/debug/persistence_status` exposes that context plus L1 IV source counters.
- Verification: Targeted pytest passed for the new helper and health diagnostics route. `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed.

## Risks / Constraints
- Risk 1: The currently running backend process was started before this code change, so the new diagnostics will not appear in live `/debug/persistence_status` until a restart picks up the new code.
- Risk 2: This session intentionally does not change `snapshot_version_iv_drift` semantics; noisy drift activation can still occur until a follow-up behavior fix is implemented.

## Next Action
- Immediate Next Step: Optionally restart backend in a follow-up ops step if live `/debug/persistence_status` confirmation is required.
- Owner: `Codex`
