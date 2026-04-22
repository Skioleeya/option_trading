# Project State

## Snapshot
- DateTime (ET): 2026-04-16 17:05:25 -04:00
- Branch: chore/sync-all-local-changes-20260313
- Last Commit: e91cff0
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED` (Wave1 only; Wave2/Wave3 pending)

## Current Focus
- Primary Goal: Implement MM Rust Cutover Wave1 (L0 condition passthrough + Rust MM core + MVP integration).
- Scope In:
  - L0 trade condition passthrough and midpoint tick-rule direction path
  - shared_rust_services MM core functions
  - MVP flow/CSV field upgrade and contract tests
  - OpenSpec parent + Wave1 child records and SOP sync
- Scope Out:
  - Full L2/L3 runtime Rust owner migration (Wave2/Wave3)

## What Changed (Latest Session)
- Files:
  - l0_ingest/l0_rust/src/schema.rs
  - l0_ingest/l0_rust/src/gateway_core.rs
  - l0_ingest/l0_rust/src/ipc_writer.rs
  - l0_ingest/l0_rust/src/l0_market_bridge.rs
  - shared/services/l0_runtime/normalize/pipeline/__init__.py
  - shared/services/l0_runtime/normalize/bridges/__init__.py
  - shared/services/l0_runtime/services/runtime/builder.py
  - shared_rust_services/src/mm_flow.rs
  - shared_rust_services/src/lib.rs
  - scripts/test/longport_mvp/{extractors.py,flow.py,stores.py,live_probe.py,csv_monitor.py,__init__.py,models.py}
  - scripts/test/run_longport_option_flow_mvp_monitor.py
  - scripts/test/test_longport_option_flow_mvp_live.py
  - openspec/changes/impl-20260416-mm-rust-cutover-parent/*
  - openspec/changes/impl-20260416-mm-rust-cutover-wave1-l0-condition-and-mm-core/*
  - docs/SOP/L0_DATA_FEED.md
- Behavior:
  - L0 Arrow chain now carries `trade_type` and `trade_session` from LongPort trade push.
  - Trade payload direction now uses midpoint tick-rule with `prev_price` + `prev_direction` continuation.
  - Rust MM core added: condition filter, tick-rule direction, OI participation, delta/gamma exposure formula.
  - MVP now outputs institutional fields: delta/gamma exposure live, midpoint count, condition-filter count, complex spread count, residual delta.
- Verification:
  - Rust build/check passed for `shared_rust_services` and `l0_rust`.
  - Contract tests passed in `scripts/test/test_longport_option_flow_mvp_live.py`.

## Risks / Constraints
- Risk 1: Wave2/Wave3 (L2/L3 runtime full Rust owner) not yet implemented; parent proposal remains open.
- Risk 2: Existing unrelated workspace changes remain in worktree (not touched in this session).

## Next Action
- Immediate Next Step: Execute Wave2 child proposal (L1/L2 runtime owner migration) with same strict gates.
- Owner: Codex
