# Project State

## Snapshot
- DateTime (ET): 2026-04-21 18:21:51 -0400
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `3ff3ba1`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Remove the remaining `RustQuoteRuntime` REST-path `Already borrowed` warnings by fixing single-owner gateway concurrency.
- Scope In: `shared/services/l0_runtime/source/runtime/quote_runtime/__init__.py`, quote-runtime tests, `docs/SOP/L0_DATA_FEED.md`, session/context sync.
- Scope Out: shutdown-path Arrow IPC close owner, frontend/runtime UI work, research persistence.

## What Changed (Latest Session)
- Files:
  - `shared/services/l0_runtime/source/runtime/quote_runtime/__init__.py`
  - `shared/services/l0_runtime/source/runtime/test_quote_runtime.py`
  - `docs/SOP/L0_DATA_FEED.md`
- Behavior:
  - `RustQuoteRuntime` now treats `RustIngestGateway` as a single-owner native resource: gateway creation/state mutation is guarded by an async state lock, and all native `start/stop/subscribe/unsubscribe/rest_*` calls are serialized through a thread lock before entering `asyncio.to_thread(...)`.
  - `_execute()` now captures the gateway instance before entering the worker thread, so concurrent tasks cannot race a later `self._gateway = None` or a fresh gateway replacement into the native call.
- Verification:
  - `.venv/bin/python manage.py run-pytest shared/services/l0_runtime/source/runtime/test_quote_runtime.py shared/services/l0_runtime/source/runtime/test_bootstrap.py app/tests/test_lifespan_startup.py` (`7 passed`)
  - real-host `python3 manage.py start-all`
  - real-host `python3 manage.py start-all --verify-only`
  - real-host log window after the restart: `Already borrowed=0`, `rest_quote failed=0`, `rest_calc_indexes failed=0`, `rest_option_quote failed=0`, `header VIX quote failed=0`, `header 1DTE option quote failed=0`, `Application shutdown failed=0`
  - real-host `ss -ltnp '( sport = :8001 )'` confirmed backend listener ownership on `0.0.0.0:8001` (pid `28883`)

## Risks / Constraints
- Risk 1: this fix serializes all native gateway calls through one owner lock by design; if future throughput targets require parallel REST clients, they must first split gateway ownership rather than bypass this contract.
- Risk 2: sandbox-local localhost requests remain untrusted evidence for real-host health in this WSL2 setup; startup/verify/log/port-owner checks remain the valid source.

## Next Action
- Immediate Next Step: synchronize context files and run `python3 manage.py validate-session --strict`.
- Owner: Codex
