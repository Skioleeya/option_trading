# Project State

## Snapshot
- DateTime (ET): 2026-04-03 12:28:03 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `6c68068`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Root-cause fix for ActiveOptions degraded/synthetic rows without downgrade/fallback path.
- Scope In:
  - `compute_loop` ActiveOptions input path contract fix.
  - Rust ActiveOptions input/engine/ranking contract hardening.
  - OI snapshot sync call path fix.
  - Diagnostics/audit/hotfix verification script hardening.
  - Session/context strict handoff closure.
- Scope Out:
  - Unrelated legacy sessions and unrelated runtime refactors.

## What Changed (Latest Session)
- Files:
  - `app/loops/compute_loop.py`
  - `shared_rust_services/src/active_options/input.rs`
  - `shared_rust_services/src/active_options/engines.rs`
  - `shared_rust_services/src/active_options/support.rs`
  - `shared/cache/oi_snapshot.py`
  - `scripts/diag/replay_active_options_partial_fallback.py`
  - `scripts/diag/check_active_options_freeze_rootcause.py`
  - `scripts/diag/audit_intraday_core_flow.py`
  - `scripts/diag/check_active_options_no_data_cause.py`
  - `scripts/ops/verify_active_options_hotfix.ps1`
  - `app/loops/tests/test_active_options_input_bridge.py`
  - `docs/SOP/L0_DATA_FEED.md`
- Behavior:
  - ActiveOptions input now receives full `EnrichedSnapshot` instead of legacy dict downcast.
  - Rust input bridge now recognizes `chain/chain_elements` and pulls `atm_iv` from snapshot/aggregates/dict.
  - Rust FlowEngine OI delta lookup switched to sync-safe call path.
  - Top5 ranking prioritizes fully LIVE rows over degraded rows.
  - Audit/hotfix scripts now fail on degraded rows instead of warning-only pass.
- Verification:
  - ActiveOptions bridge tests pass.
  - Freeze/no-data diagnostics show no active issue.
  - Intraday flow audit passes with real rows and no degraded rows.
  - Hotfix verify script passes with `live_rows=5` and `degraded_rows=0`.

## Risks / Constraints
- Existing repository has large unrelated in-flight changes; this session did not revert or modify unrelated scopes.
- Historical log tails may include old warnings; latest runtime tail validation required for fresh-signal judgment.

## Next Action
- Immediate Next Step: Final strict session validation and handoff sync.
- Owner: Codex
