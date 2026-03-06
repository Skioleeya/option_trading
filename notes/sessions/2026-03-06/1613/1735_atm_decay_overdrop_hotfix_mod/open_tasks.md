# Open Tasks

## Priority Queue
- [x] P0: Bound ATM decay stitching to eliminate `CALL <-100%` overdrop.
  - Owner: Codex
  - Definition of Done: roll stitching moved to multiplicative factor and returned `pct >= -1.0`.
  - Blocking: None
- [x] P1: Add session and day-boundary guards for tracker update lifecycle.
  - Owner: Codex
  - Definition of Done: post-close cutoff + trade-date rollover reset covered by tests.
  - Blocking: None
- [ ] P2: Reduce ATM decay storage write amplification.
  - Owner: Next agent
  - Definition of Done: remove per-tick full-history `lrange + full-file rewrite` in storage append path.
  - Blocking: Requires storage format migration decision.

## Parking Lot
- [ ] Add L4 debug pill showing active stitching mode (`factor` vs legacy).
- [ ] Add metric/alert when legacy offset restore requires floor clamp.

## Completed (Recent)
- [x] Added bounded multiplicative stitching helpers and tracker integration (2026-03-06 16:17 ET)
- [x] Added tracker tests: compounding floor, post-close cutoff, day rollover reset, legacy-offset conversion (2026-03-06 16:17 ET)
- [x] Synced SOP docs for ATM decay stitching/session guards (2026-03-06 16:17 ET)
