# Open Tasks

## Priority Queue
- [x] P0: Gate ATM decay ordinary samples on L0 source freshness and CALL/PUT leg freshness.
  - Owner: Codex
  - Definition of Done: stale or mixed-freshness inputs do not publish ordinary points; recovery points carry freshness metadata; backend tests pass.
  - Blocking: none known.
- [x] P0: Break L4 ATM chart continuity on stale recovery and long adjacent gaps.
  - Owner: Codex
  - Definition of Done: chart data builder inserts whitespace for recovery/gap cases while preserving CALL red and PUT green semantics; L4 tests pass.
  - Blocking: none known.
- [x] P1: Preserve `strike_changed` after suppressed roll-anchor opening zero tick.
  - Owner: Codex
  - Definition of Done: marker persists until the next published ATM sample; regression coverage added.
  - Blocking: none known.

## Parking Lot
- Deferred runtime evidence note: standard `start-all` was intentionally stopped by explicit user request after market close on 2026-07-15. This is not an open implementation task.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Session and OpenSpec skeleton initialized. (2026-07-15 14:19 ET)
- [x] ATM freshness implementation and targeted verification completed. (2026-07-15 15:59 ET)
- [x] Strict validation passed. (2026-07-15 16:09 ET)
