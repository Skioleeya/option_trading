# Open Tasks

## Priority Queue
- [x] P0: Remove L0 dead runtime side paths and duplicate event processor while preserving active L0 behavior
  - Owner: Codex
  - Definition of Done: Orphan runtime adapter removed, active event processor converged to a single implementation, and runtime tree no longer exposes dead side paths.
  - Blocking: None
- [x] P0: Split `l0_ingest/tests/v2/test_quote_runtime.py` into focused modules and keep all Python test files under 400 lines
  - Owner: Codex
  - Definition of Done: Shared fakes extracted, focused test modules created, and V2 pytest passes.
  - Blocking: None
- [x] P0: Pass strict session validation with OpenSpec and SOP governance in sync
  - Owner: Codex
  - Definition of Done: `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` returns PASS with no unresolved gates.
  - Blocking: None

## Parking Lot
- [ ] Item: Reassess near-limit `l0_ingest/tests/v2/test_chain_state_store.py` in a later hygiene session if it grows further.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] `longport_adapter.py` removed from the active `l0_ingest/v2/source/runtime` tree (2026-03-24 21:56 ET)
- [x] `ChainEventProcessor` removed and replaced with `StateEventProcessor` coverage (2026-03-24 22:00 ET)
- [x] `l0_ingest/tests/v2/test_quote_runtime.py` split into focused modules and support helpers (2026-03-24 21:51 ET)
- [x] `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/v2` passed with `73 passed` (2026-03-24 22:02 ET)
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed (2026-03-24 22:03 ET)
