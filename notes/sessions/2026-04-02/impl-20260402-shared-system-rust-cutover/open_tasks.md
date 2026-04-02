# Open Tasks

## Priority Queue
- [x] P0: Session strict gate closeout
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passes and evidence is written to handoff/meta.
  - Blocking: none
- [ ] P1: Sub-wave B audit record completion
  - Owner: L0 runtime migration owner
  - Definition of Done: method-level classification for `shared/system/rust_shm_bridge.py` and consumer cutover plan for `l1_compute/rust_bridge.py`.
  - Blocking: missing method-level audit artifact
- [ ] P1: Sub-wave C readiness verification
  - Owner: L0/L3 integration owner
  - Definition of Done: wave 19 sub-wave D dependency verified; Rust owner parity plan for snapshot/OI approved.
  - Blocking: upstream owner readiness evidence not attached
- [ ] P2: Sub-wave D consumer-by-consumer decision closure
  - Owner: architecture owner
  - Definition of Done: explicit per-consumer decision for `redis_service.py`, `historical_store.py`, `tactical_triad_logic.py` and SOP linkage.
  - Blocking: cross-layer consumer migration plan not finalized

## Parking Lot
- [ ] Consider replacing legacy Sub-wave A test paths with current repo test inventory in a follow-up OpenSpec doc cleanup.
- [ ] Add a dedicated l0_runtime IPC regression test module if retained in CI.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Sub-wave A execution record synchronized to OpenSpec tasks (2026-04-02 ET)
- [x] Pytest entrypoint smoke check passed via required wrapper (`app/tests/test_lifespan_startup.py`) (2026-04-02 ET)
- [x] Session strict validation passed (`scripts/validate_session.ps1 -Strict`) (2026-04-02 ET)
