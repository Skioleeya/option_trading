# Open Tasks

## Priority Queue
- [x] P0: Hard-cut ActiveOptions gate/sort to day cumulative volume (`volume`) only.
  - Owner: Codex
  - Definition of Done: `current_volume` no longer participates in `min_volume` pass condition or fallback substitution.
  - Blocking: none
- [x] P1: Add regression tests for day-volume-only behavior.
  - Owner: Codex
  - Definition of Done: test verifies `volume=0,current_volume>0` is filtered out when `min_volume` not met by `volume`.
  - Blocking: none
- [x] P2: Sync SOP language to hard-cut policy.
  - Owner: Codex
  - Definition of Done: L0/L4 SOP explicitly states no `current_volume` fallback for ActiveOptions gate/sort.
  - Blocking: none

## Parking Lot
- [ ] Monitor first post-change open window for sustained `input_day_volume_ge_min_last` collapse events.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] ActiveOptions day-volume hard cut implemented in Rust normalize/filter owner (2026-04-08 11:00 ET).
- [x] Runtime/housekeeping debug counters switched to `day_volume_ge_min` (2026-04-08 11:01 ET).
- [x] Targeted regression tests passed (7/7) (2026-04-08 11:04 ET).
