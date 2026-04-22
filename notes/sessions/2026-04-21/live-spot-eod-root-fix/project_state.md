# Project State

## Snapshot
- DateTime (ET): 2026-04-21 22:28:30 -0400
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `3ff3ba1`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `HOST STARTUP VERIFIED`
  - L0-L4 Pipeline: `TARGETED TESTS GREEN + START-ALL VERIFIED`

## Current Focus
- Primary Goal: close the live spot / EOD review root regressions without reintroducing REST spot fallback or compatibility shims.
- Scope In:
  - `quote_lane` cadence propagation to payload even when SPY midpoint is flat
  - `FeedOrchestrator` raw-source stale fast-fail at `10s`
  - EOD staged publish all-target preflight before first rename
  - startup deadlock / active-options bridge regressions discovered during real-host verification
  - `start-all` frontend listener persistence under detached startup
- Scope Out:
  - new cold-storage contract redesign
  - any Python fallback restoration for stale spot repair

## What Changed (Latest Session)
- Files:
  - `app/loops/compute_loop.py`
  - `app/loops/tests/test_active_options_input_bridge.py`
  - `app/loops/shared_state.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
  - `infra/ops_cli/start_all.py`
  - `infra/ops_cli/test_start_all.py`
  - `scripts/diagnostics/eod_bucket_archive.py`
  - `scripts/test/test_eod_bucket_archive.py`
  - `shared/services/l0_runtime/projection/snapshot/__init__.py`
  - `shared/services/l0_runtime/services/orchestration/feed_orchestrator.py`
  - `shared/services/l0_runtime/services/orchestration/test_feed_orchestrator.py`
  - `shared/services/l0_runtime/services/runtime/builder.py`
  - `shared/services/l0_runtime/state/runtime/__init__.py`
  - `shared/services/l0_runtime/state/test_runtime_state.py`
  - `shared_rust_services/src/active_options/input.rs`
- Behavior:
  - `ChainStateStore.update_spot_from_source()` now emits an independent quote-lane cadence callback on every valid raw source arrival.
  - `SharedLoopState` now supports telemetry-only `quote_lane` overlays that bump payload epoch without mutating top-level `spot/version`.
  - `FeedOrchestrator` now stale-gates on raw source arrival age and skips spot-dependent work instead of calling REST `quote(["SPY.US"])`, while still allowing the bootstrap subscription refresh that makes the Arrow writer ready before the first raw source timestamp exists.
  - Active-options snapshot normalization now treats `l1_snapshot.chain=None` as an empty L1 overlay instead of throwing `chain rows must be list-like or expose to_pylist()`.
  - `start-all` now launches the Vite frontend with `stdin=DEVNULL`, preventing the detached frontend listener from exiting when the parent startup command returns.
  - EOD archive now preflights all three final publish targets before the first staged rename.
- Verification:
  - `.venv/bin/python manage.py run-pytest app/loops/tests/test_shared_state_live_spot.py app/loops/tests/test_broadcast_loop_phase_lock.py shared/services/l0_runtime/state/test_runtime_state.py shared/services/l0_runtime/services/orchestration/test_feed_orchestrator.py scripts/test/test_eod_bucket_archive.py`
  - `.venv/bin/python manage.py run-pytest app/tests/test_health_route_diagnostics.py shared/services/l0_runtime/services/runtime/test_arrow_events.py`
  - `.venv/bin/python manage.py run-pytest infra/ops_cli/test_start_all.py app/loops/tests/test_active_options_input_bridge.py app/loops/tests/test_compute_loop_gpu_dedup.py shared/services/l0_runtime/services/orchestration/test_feed_orchestrator.py`
  - `.venv/bin/python manage.py start-all`
  - `python3 manage.py start-all --verify-only`
  - `curl -I http://127.0.0.1:5173`
  - `cmd.exe /C "cd /d C:\\ && curl.exe -I http://localhost:5173"`
  - `cmd.exe /C "cd /d C:\\ && curl.exe http://localhost:5173/api/atm-decay/history?schema=v2"`
  - `python3 manage.py validate-session --strict`

## Risks / Constraints
- Risk 1: the repo worktree is already dirty outside this session; unrelated changes were left untouched.
- Risk 2: postmarket startup is verified, but the new stale-gate/bootstrap path still needs live-open observation before any threshold tuning.
- Risk 3: backend log still shows pre-existing ActiveOptions/DepthProfile warnings outside this root-fix scope; they did not block health, proxy traffic, or startup verification in this session.

## Next Action
- Immediate Next Step: session complete; next work can continue from this handoff.
- Owner: Codex
