# Project State

## Snapshot
- DateTime (ET): 2026-03-24 22:05:00 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `724efb3`
- Environment:
  - Market: `OPEN`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: Remove dead L0 runtime side paths, converge facade event processing onto a single active processor, and restore test/file governance compliance.
- Scope In: `l0_ingest/v2/source/runtime/*`, `l0_ingest/v2/normalize/events/*`, `l0_ingest/tests/v2/*`, `l0_ingest/README.md`, `docs/SOP/L0_DATA_FEED.md`, `openspec/changes/refactor-governance-20260324-l0-runtime-dead-path-cleanup/*`
- Scope Out: L1/L2/L3 behavior changes, app wiring changes, and Rust runtime behavior changes.

## What Changed (Latest Session)
- Files:
  - `l0_ingest/v2/source/runtime/base_feed.py`
  - `l0_ingest/v2/source/runtime/longport_adapter.py` removed
  - `l0_ingest/v2/normalize/events/chain_event_processor.py` removed
  - `l0_ingest/tests/v2/quote_runtime_support.py`
  - `l0_ingest/tests/v2/test_state_event_processor.py`
  - `l0_ingest/tests/v2/test_quote_runtime_rust.py`
  - `l0_ingest/tests/v2/test_quote_runtime_failover.py`
  - `l0_ingest/tests/v2/test_quote_runtime_python.py`
  - `l0_ingest/tests/v2/test_quote_runtime.py` removed
  - `l0_ingest/tests/v2/test_chain_event_processor.py` removed
  - `l0_ingest/README.md`
  - `docs/SOP/L0_DATA_FEED.md`
  - `openspec/changes/refactor-governance-20260324-l0-runtime-dead-path-cleanup/*`
- Behavior:
  - Removed the orphan `longport_adapter.py` side path from the active `v2/source/runtime` tree.
  - Removed the runtime-dead `ChainEventProcessor` and kept `StateEventProcessor` as the single active facade event processor.
  - Replaced the legacy processor test with `StateEventProcessor` coverage.
  - Split the oversized quote runtime test file into support + focused modules so all resulting Python files remain under the 400-line ceiling.
  - Updated README/SOP/OpenSpec to document the active L0 runtime/provider path and dead-path cleanup rules.
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/v2/test_quote_runtime_rust.py l0_ingest/tests/v2/test_quote_runtime_failover.py l0_ingest/tests/v2/test_quote_runtime_python.py` -> `6 passed`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/v2` -> `73 passed`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` -> `PASS`

## Risks / Constraints
- Risk 1: Worktree contains unrelated pre-existing temp artifacts and pointer files; this session must not revert unrelated changes.
- Risk 2: `l0_ingest/tests/v2/test_chain_state_store.py` remains close to the 400-line ceiling and may need a later hygiene pass.

## Next Action
- Immediate Next Step: None. Session is ready for handoff.
- Owner: Codex
