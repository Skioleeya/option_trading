# Open Tasks

## Priority Queue
- [x] P0: Retire `shared/system/rust_shm_bridge.py`
  - Owner: Codex
  - Definition of Done: file deleted after method-level audit and consumer scan.
  - Blocking: none
- [x] P1: Remove dead `l1_compute/rust_bridge.py`
  - Owner: Codex
  - Definition of Done: file deleted because no runtime consumers remain.
  - Blocking: none
- [x] P2: Run targeted smoke test and strict validation
  - Owner: Codex
  - Definition of Done: `scripts/test/run_pytest.ps1 app/tests/test_lifespan_startup.py -q` passes and `scripts/validate_session.ps1 -Strict` passes.
  - Blocking: none

## Parking Lot
- [x] Item: none
- [x] Item: none

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Method-level audit completed for `shared/system/rust_shm_bridge.py` (2026-04-02 ET)
- [x] Strict validation passed for Sub-wave B (2026-04-02 ET)
