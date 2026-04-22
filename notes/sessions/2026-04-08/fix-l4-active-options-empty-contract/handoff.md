# Handoff

## Session Summary
- DateTime (ET): 2026-04-08 11:05:31 -04:00
- Goal: 按要求把 ActiveOptions 硬切到“当日累计成交量 (`volume`)”排序/门槛口径，禁止 `current_volume` fallback。
- Outcome: Completed. ActiveOptions filter/rank path now uses day cumulative volume only; fallback branch removed.

## What Changed
- Code / Docs Files:
  - `shared_rust_services/src/active_options/support.rs`
  - `shared/services/active_options_runtime.py`
  - `shared/services/active_options_runtime_metrics.py`
  - `app/loops/housekeeping_loop.py`
  - `app/tests/test_active_options_day_volume_policy.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/L4_FRONTEND.md`
- Runtime / Infra Changes:
  - Rebuilt Rust extension crate `shared_rust_services`.
  - Replaced runtime extension artifact: `shared_rust/services.pyd` from `E:\US.market\cargo_target\release/services.dll`.
  - Restarted backend via `scripts/ops/start_backend.ps1`.
- Commands Run:
  - `cargo build --release` (workdir `shared_rust_services`)
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/tests/test_active_options_day_volume_policy.py app/loops/tests/test_housekeeping_gpu_dedup.py -q`
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1`
  - `Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8001/debug/persistence_status`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Verification
- Passed:
  - New policy regression test: `volume=0,current_volume>0` no longer passes `min_volume` gate.
  - Targeted pytest suite: `7 passed`.
  - Runtime health endpoint returns active rows and day-volume diagnostics (`input_day_volume_ge_min_last` present).
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed.
- Failed / Not Run:
  - Full-repo pytest/cargo suite not run in this session.

## Pending
- Must Do Next:
  - Observe one sustained open-window sample for `filtered_candidates_count` stability under strict `flow_active_min_volume=100`.
- Nice to Have:
  - Add integration test for `/debug/active_options_capture` asserting day-volume-only gate semantics.

## Debt Record (Mandatory)
- DEBT-EXEMPT: n/a
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-15
- DEBT-RISK: low
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: n/a
- RUNTIME-ARTIFACT-EXEMPT: none
- OPENSPEC-EXEMPT: Emergency runtime policy correction for production release window; no new product capability.

## SOP Sync
- Updated SOP files:
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/L4_FRONTEND.md`

## How To Continue
- Start Command:
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1`
- Key Logs:
  - `logs/backend_runtime.current.log`
  - `/debug/persistence_status` (`active_options.*` fields)
- First File To Read:
  - `shared_rust_services/src/active_options/support.rs`
