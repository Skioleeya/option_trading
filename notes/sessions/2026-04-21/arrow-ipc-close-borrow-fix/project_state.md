# Project State

## Snapshot
- DateTime (ET): 2026-04-21 18:11:59 -0400
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `3ff3ba1`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Remove the shutdown-path `ArrowIpcReader.close(): Already borrowed` failure from real-host backend restarts.
- Scope In: `l0_ingest/l0_rust/src/ipc_runtime.rs`, `shared/services/l0_runtime/source/runtime/ipc.py`, `docs/SOP/L0_DATA_FEED.md`, session/context sync.
- Scope Out: quote-source cadence, frontend behavior, research persistence, any new compatibility path.

## What Changed (Latest Session)
- Files:
  - `l0_ingest/l0_rust/src/ipc_runtime.rs`
  - `shared/services/l0_runtime/source/runtime/ipc.py`
  - `docs/SOP/L0_DATA_FEED.md`
- Behavior:
  - `NativeArrowIpcReader.close()` is now an interruptible immutable close that sets a closed flag and signals the named event, so a blocked `read_next_payload()` exits without requiring a mutable PyO3 borrow.
  - Python `ArrowIpcReader.read_next_batch()` now captures the native reader before `asyncio.to_thread(...)`, and `close()` detaches the Python handle before issuing the native close.
- Verification:
  - `cargo build --release --manifest-path l0_ingest/l0_rust/Cargo.toml --target-dir tmp/cargo_target_runtime_l0`
  - `.venv/bin/python manage.py run-pytest shared/services/l0_runtime/source/runtime/test_bootstrap.py app/tests/test_lifespan_startup.py` (`4 passed`)
  - real-host `python3 manage.py start-all` succeeded twice in a row; `python3 manage.py start-all --verify-only` returned all services `True`; final port owner was `python` pid `27719` listening on `0.0.0.0:8001`
  - `logs/backend_runtime.current.log` shows no new `Already borrowed` / `Application shutdown failed` entries after the new boots at `18:09:40 ET` and `18:10:59 ET`

## Risks / Constraints
- Risk 1: `cargo test` for `l0_ingest/l0_rust` still hits the crate's pre-existing PyO3 lib-test linker limitation in this environment; release build remains the valid native verification path here.
- Risk 2: sandbox-local `curl http://127.0.0.1:8001/health` is not reliable evidence for real-host localhost reachability; restart evidence must rely on real-host `start-all`, `--verify-only`, log, and port-owner checks.

## Next Action
- Immediate Next Step: synchronize `notes/context/*`, run `python3 manage.py validate-session --strict`, and archive the session once strict is green.
- Owner: Codex
