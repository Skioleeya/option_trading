# Open Tasks

## Priority Queue
- [ ] P1: Live/replay verify no AtmDecay interaction degraded-mode error after prolonged hover stress.
  - Owner: Codex / next implementing agent
  - Definition of Done: no `[AtmDecayChart] Entering degraded mode at stage=interaction` logs in replay window.
  - Blocking: replay/live validation window.
- [ ] P2: Add integration test for mixed wall row labels (legacy short labels and canonical labels).
  - Owner: Codex / next implementing agent
  - Definition of Done: mapping to gamma_walls remains deterministic for CALL/PUT classes.
  - Blocking: test matrix design.

## Parking Lot
- [ ] Consider exposing explicit `row_kind: call|put` from backend to remove label-string inference in L4.
- [ ] Add telemetry counter for L4 chart interaction exceptions.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] AtmDecay hover path switched to de-emphasis (no visibility toggling) (2026-03-13 11:13 ET)
- [x] WallMigration strike unified to canonical `gamma_walls` source (2026-03-13 11:24 ET)
- [x] Updated L4 SOP for both interaction safety and wall source rule (2026-03-13 11:24 ET)
- [x] Targeted frontend tests passed (2026-03-13 11:24 ET)
