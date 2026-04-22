# Handoff

## Session Summary
- DateTime (ET): 2026-04-21 22:28:30 -0400
- Goal: fix the three confirmed live spot / EOD review regressions without restoring stale-spot REST fallback.
- Outcome: complete. The original three regressions are fixed, the host-verified startup deadlock caused by the new stale-gate is removed, ActiveOptions no longer crashes on `empty_snapshot.chain=None`, and `start-all` now keeps the frontend listener alive after startup returns.

## What Changed
- Code / Docs Files:
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
- Runtime / Infra Changes:
  - `ChainStateStore` now emits a dedicated quote-lane telemetry callback on every valid raw source arrival; distinct live-spot listeners remain version/spot owners only.
  - `SharedLoopState` now has a telemetry-only overlay path that updates `governor_telemetry.quote_lane`, preserves top-level `spot/version`, and still bumps payload epoch for L3/L4 broadcast.
  - `build_snapshot_payload()` now normalizes payload `quote_lane` telemetry to `mode=source_cadence` and carries `source_data_timestamp_utc`.
  - `FeedOrchestrator` now treats raw source age `>10s` as a stale gate and skips header aux refresh, strike subscription refresh, and 15-minute research until the next raw source arrival, but allows the initial subscription refresh needed to bootstrap the Arrow writer before the first raw source timestamp arrives.
  - `shared_rust.services.build_active_options_input_snapshot()` now normalizes an explicit `l1_snapshot.chain=None` to an empty L1 overlay instead of raising a type error during merge.
  - `start-all` frontend launch now uses `stdin=DEVNULL`, which keeps the detached Vite listener alive after the parent startup process exits.
  - EOD archive now aborts before publish when any of `daily/<date>`, `by_regime/<primary>/<date>`, or `reports/<date>_quality.json` already exists.
- Commands Run:
  - `python3 manage.py new-session --task-id live-spot-eod-root-fix`
  - `.venv/bin/python manage.py run-pytest app/loops/tests/test_shared_state_live_spot.py app/loops/tests/test_broadcast_loop_phase_lock.py shared/services/l0_runtime/state/test_runtime_state.py shared/services/l0_runtime/services/orchestration/test_feed_orchestrator.py scripts/test/test_eod_bucket_archive.py`
  - `.venv/bin/python manage.py run-pytest app/tests/test_health_route_diagnostics.py shared/services/l0_runtime/services/runtime/test_arrow_events.py`
  - `.venv/bin/python manage.py run-pytest shared/services/l0_runtime/services/orchestration/test_feed_orchestrator.py`
  - `cargo build --release --manifest-path shared_rust_services/Cargo.toml --target-dir tmp/cargo_target_runtime`
  - `cp tmp/cargo_target_runtime/release/libservices.so shared_rust/services.so`
  - `.venv/bin/python manage.py run-pytest infra/ops_cli/test_start_all.py app/loops/tests/test_active_options_input_bridge.py app/loops/tests/test_compute_loop_gpu_dedup.py shared/services/l0_runtime/services/orchestration/test_feed_orchestrator.py`
  - `.venv/bin/python manage.py start-all`
  - `python3 manage.py start-all --verify-only`
  - `curl -I http://127.0.0.1:8001/health`
  - `curl -I http://127.0.0.1:5173`
  - `cmd.exe /C "cd /d C:\\ && curl.exe -I http://localhost:5173"`
  - `cmd.exe /C "cd /d C:\\ && curl.exe http://localhost:5173/api/atm-decay/history?schema=v2"`
  - `python3 manage.py validate-session --strict`

## Verification
- Passed:
  - `.venv/bin/python manage.py run-pytest app/loops/tests/test_shared_state_live_spot.py app/loops/tests/test_broadcast_loop_phase_lock.py shared/services/l0_runtime/state/test_runtime_state.py shared/services/l0_runtime/services/orchestration/test_feed_orchestrator.py scripts/test/test_eod_bucket_archive.py` -> `30 passed`
  - `.venv/bin/python manage.py run-pytest app/tests/test_health_route_diagnostics.py shared/services/l0_runtime/services/runtime/test_arrow_events.py` -> `6 passed`
  - `.venv/bin/python manage.py run-pytest shared/services/l0_runtime/services/orchestration/test_feed_orchestrator.py` -> `4 passed`
  - `.venv/bin/python manage.py run-pytest infra/ops_cli/test_start_all.py app/loops/tests/test_active_options_input_bridge.py app/loops/tests/test_compute_loop_gpu_dedup.py shared/services/l0_runtime/services/orchestration/test_feed_orchestrator.py` -> `11 passed`
  - `.venv/bin/python manage.py start-all` -> Redis/backend/frontend all reported listening; backend healthy on `8001`.
  - `python3 manage.py start-all --verify-only` -> `Redis 6380: True`, `Backend 8001: True`, `Frontend 5173: True`
  - `curl -I http://127.0.0.1:8001/health` -> `HTTP/1.1 405 Method Not Allowed`
  - `curl -I http://127.0.0.1:5173` -> `HTTP/1.1 200 OK`
  - `cmd.exe /C "cd /d C:\\ && curl.exe -I http://localhost:5173"` -> `HTTP/1.1 200 OK`
  - `cmd.exe /C "cd /d C:\\ && curl.exe http://localhost:5173/api/atm-decay/history?schema=v2"` -> columnar JSON payload returned through frontend same-origin proxy
- Failed / Not Run:
  - none

## Pending
- Must Do Next:
  - None.
- Nice to Have:
  - Capture live-session evidence that stale-source gate behavior is acceptable during flat-price periods.
  - Investigate the pre-existing postmarket warnings from `active_options_runtime.py` and `DepthProfile EMA`, which did not block startup or proxy verification here.

## Debt Record (Mandatory)
- DEBT-EXEMPT: targeted root-fix session closed the confirmed regressions plus host-verification breakages with no new temporary wrappers or fallback flags.
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-21
- DEBT-RISK: none within session scope; remaining live-open evidence is backlog, not session debt.
- OPENSPEC-EXEMPT: targeted runtime hotfix on existing contracts; no new OpenSpec proposal was created in this session.
- DEBT-NEW: 0
- DEBT-CLOSED: 6
- DEBT-DELTA: -6
- RUNTIME-ARTIFACT-EXEMPT: rebuilt and replaced `shared_rust/services.so` as required to ship the ActiveOptions input normalization fix.

## How To Continue
- Start Command: `python3 manage.py start-all --verify-only`
- Key Logs: `logs/backend_runtime.current.log`, `logs/frontend_runtime.current.log`
- First File To Read: `notes/sessions/2026-04-21/live-spot-eod-root-fix/project_state.md`
