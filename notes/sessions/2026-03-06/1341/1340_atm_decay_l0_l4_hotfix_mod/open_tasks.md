# Open Tasks

## Priority Queue
- [x] P0: Complete L0-L4 trace for `AtmDecayChart.tsx`, `AtmDecayOverlay.tsx`, and `atmDecayTime.ts`.
  - Owner: Codex
  - Definition of Done: Source-to-render chain verified across L1 tracker, L3 payload pass-through, store merge/hydration, and center-panel rendering behavior.
  - Blocking: None.
- [x] P1: Hotfix severe overlay/chart session-window divergence.
  - Owner: Codex
  - Definition of Done: Overlay no longer displays out-of-session latest tick while chart filters it out.
  - Blocking: None.
- [x] P2: Modularize and test ATM time/display helpers.
  - Owner: Codex
  - Definition of Done: Time parsing and display selection moved to pure helpers with unit tests and build pass.
  - Blocking: None.

## Parking Lot
- [ ] Backend: enforce tracker close cutoff at 16:00 ET to stop generating post-session ATM payloads.
- [ ] Performance: migrate ATM chart from full `setData` each tick to incremental update path.

## Completed (Recent)
- [x] ATM center panel hotfix + modularization (2026-03-06 13:48 ET)
