# Open Tasks

## Priority Queue
- [x] P0: Remove the `vite build` regression that incorrectly hard-required `VITE_BACKEND_ORIGIN`.
  - Owner: Codex
  - Definition of Done: `npm run build` succeeds without exporting `VITE_BACKEND_ORIGIN`, while `vite serve` still fast-fails if the proxy origin is missing/invalid.
  - Blocking: none
- [x] P1: Restore full-history ATM live dedupe.
  - Owner: Codex
  - Definition of Done: a hydrated older ATM timestamp is not re-appended by a later live/init payload.
  - Blocking: none
- [x] P1: Resync `AtmDecayChart` on tab visibility recovery.
  - Owner: Codex
  - Definition of Done: chart catches up on `visibilitychange -> visible` without waiting for another ATM tick.
  - Blocking: none

## Parking Lot
- [ ] Monitor whether `AtmDecayChart.tsx` should be split in the next governance cleanup wave.
- [ ] Add a broader reconnect/init chart regression if future ATM transport changes touch this path again.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Closed the three frontend review regressions with targeted build/store/chart tests (2026-04-21 19:01 ET)
