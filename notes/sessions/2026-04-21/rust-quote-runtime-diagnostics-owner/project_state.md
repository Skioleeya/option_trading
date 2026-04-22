# Project State

## Snapshot
- DateTime (ET): 2026-04-21 18:37:29 -0400
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `3ff3ba1`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Move `RustQuoteRuntime.diagnostics()` off the live gateway and onto a borrow-free diagnostics handle / cached snapshot surface.
- Scope In: `l0_ingest/l0_rust` diagnostics handle, `RustQuoteRuntime` diagnostics cache, quote-runtime tests, SOP, session/context sync.
- Scope Out: gateway REST ownership, frontend/UI, research persistence, shutdown-path IPC owner.

## What Changed (Latest Session)
- Files:
  - `l0_ingest/l0_rust/src/gateway_push_diag.rs`
  - `l0_ingest/l0_rust/src/gateway_core.rs`
  - `l0_ingest/l0_rust/src/lib.rs`
  - `shared/services/l0_runtime/source/runtime/quote_runtime/__init__.py`
  - `shared/services/l0_runtime/source/runtime/test_quote_runtime.py`
  - `docs/SOP/L0_DATA_FEED.md`
- Behavior:
  - Native side now exposes a dedicated `GatewayPushDiagnosticsHandle` that snapshots `spy_push_diag` without reading through the live `RustIngestGateway` object.
  - `RustQuoteRuntime` now caches that handle and refreshes a local diagnostics snapshot from it; `diagnostics()` no longer touches the live gateway directly.
  - External diagnostics shape stayed unchanged for builder/health consumers.
- Verification:
  - `.venv/bin/python manage.py run-pytest shared/services/l0_runtime/source/runtime/test_quote_runtime.py shared/services/l0_runtime/source/runtime/test_bootstrap.py app/tests/test_lifespan_startup.py` (`8 passed`)
  - `cargo build --release --manifest-path l0_ingest/l0_rust/Cargo.toml --target-dir tmp/cargo_target_runtime_l0`
  - real-host `python3 manage.py start-all`
  - real-host `python3 manage.py start-all --verify-only`
  - post-restart log window from line `8530409` kept all borrow/rest/shutdown counts at `0`
  - `ss -ltnp '( sport = :8001 )'` confirmed backend listener on pid `29685`

## Risks / Constraints
- Risk 1: diagnostics are now snapshot-based; if operations later require stronger temporal guarantees, that must be a deliberate contract change, not an ad hoc live-gateway read.
- Risk 2: the snapshot handle currently covers push diagnostics only; if more gateway internals need observability, they should be added to the borrow-free diagnostics surface rather than reopening live gateway reads.

## Next Action
- Immediate Next Step: sync context files and run `python3 manage.py validate-session --strict`.
- Owner: Codex
