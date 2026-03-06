# Open Tasks

## Priority Queue
- [x] P0: Complete MicroStats L0-L4 business logic audit.
  - Owner: Codex
  - Definition of Done: NET GEX / WALL DYN / MOMENTUM / VANNA state, threshold, color flow traced with code evidence.
  - Blocking: None.
- [x] P1: Apply hotfix for severe state/color regressions.
  - Owner: Codex
  - Definition of Done: `wall_dyn` wiring restored and badge token collapse fixed.
  - Blocking: None.
- [x] P2: Add regression tests for MicroStats and vanna threshold sign.
  - Owner: Codex
  - Definition of Done: Tests fail before and pass after patch on wrapper command.
  - Blocking: None.

## Parking Lot
- [ ] Consider consolidating duplicated tracker computations between L1 reactor and L3 `UIStateTracker`.
- [ ] Reconcile threshold defaults between `shared/config` and `shared/config_cloud_ref`.

## Completed (Recent)
- [x] MicroStats hotfix + modularization + targeted tests (2026-03-06 12:59 ET)
