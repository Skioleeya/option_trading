# Open Tasks

## Priority Queue
- [ ] P1: Retire versioned Wave 4-9 generated-extension candidate fallbacks. SUPERSEDED-BY: `2026-04-01/wave11-small-python-cleanup`
  - Owner: Codex
  - Definition of Done: the default `_native_generated/l0_rust.pyd` path is refreshable again and the runtime no longer needs wave-specific probing.
  - Blocking: external process still locks the default generated extension path.
- [ ] P1: Continue `shared/services/l0_runtime/services/*` migration with the next bounded owner cluster. SUPERSEDED-BY: `2026-04-01/wave10-l0-poller-helper-cluster`
  - Owner: Codex
  - Definition of Done: one additional services cluster moves to Rust-backed owner semantics without widening beyond L0.
  - Blocking: completed by Wave 10; next cluster tracked in the newer session.
- [ ] P2: Remove residual thin Python orchestration helper facades when all direct consumers have shifted.
  - Owner: Codex
  - Definition of Done: orchestration helper files become removable or trivially generated.
  - Blocking: later consumer cutovers.

## Parking Lot
- [ ] Decide whether the next cleaner bounded slice is poller helper extraction or `orchestrator.py` split-first decomposition. SUPERSEDED-BY: `2026-04-01/wave10-l0-poller-helper-cluster`
- [ ] Evaluate whether `read_shm_u64` should remain exposed at the orchestration helper layer after wider IPC cleanup.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Wave 9 orchestration helper cluster completed (2026-04-01 17:28:00 -04:00)
