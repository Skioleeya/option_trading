# Open Tasks

## Priority Queue
- [x] P0: implement conservative partial fallback for ActiveOptions when `active_options_input.valid=true` but `min_volume` leaves fewer than `limit` real rows.
  - Owner: Codex
  - Definition of Done: sparse filtered sets are supplemented from turnover/OI-ranked candidates without relaxing the primary volume threshold.
  - Blocking: none
- [x] P0: expose diagnostics that distinguish empty-filter fallback from partial fallback.
  - Owner: Codex
  - Definition of Done: `/debug/persistence_status.active_options` includes filtered-candidate count, supplemented-row count, and partial-fallback counters/timestamps.
  - Blocking: none
- [x] P1: verify the patched backend during regular hours and confirm the five-slot panel no longer keeps slot 5 as a long-lived placeholder after restart.
  - Owner: Codex
  - Definition of Done: post-restart diagnostics and websocket snapshots show slot 5 as a real contract rather than a persistent placeholder.
  - Blocking: none

- [x] P1: capture a live or replayable sparse-candidate window that exercises `partial_fallback_count > 0`.
  - Owner: Codex
  - Definition of Done: live or replay evidence shows the new sparse-supplement branch firing outside unit tests, with diagnostics proving supplemented rows.
  - Blocking: none

## Parking Lot
- [ ] Evaluate whether the 3-tick switch-confirm gate still slows visible row turnover after partial fallback is live.
- [ ] Decide whether `contract_symbol` should remain internal-only or be formally documented as a hidden diagnostics field.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Root-caused the low-real-row behavior to `min_volume` filtering plus fallback only firing on fully empty filtered sets (2026-03-26 10:05 ET)
- [x] Added partial fallback supplementation and preserved synthetic row tagging for empty-filter, partial-fallback, and engine-empty cases (2026-03-26 10:16 ET)
- [x] Added targeted unit coverage for sparse filtered sets and diagnostics contract assertions (2026-03-26 10:17 ET)
- [x] Restarted the backend and confirmed across 12 post-restart websocket init snapshots that slot 5 was real in all samples, with `rows_real=5` and `rows_placeholder=0` in `/debug/persistence_status` (2026-03-26 10:29 ET)
- [x] Added `scripts/diag/replay_active_options_partial_fallback.py` and verified it drives `filtered_candidates_count=2`, `supplemented_rows=3`, and `partial_fallback_count=1` outside pytest (2026-03-26 10:36 ET)
