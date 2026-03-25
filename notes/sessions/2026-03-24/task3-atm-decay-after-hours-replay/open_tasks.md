# Open Tasks

## Priority Queue
- [x] P0: Implement a test-only after-hours ATM replay path inside the L1 ATM tracker boundary.
  - Owner: Codex
  - Definition of Done: Replay config, replay loader, today-history seeding, and tracker runtime integration are implemented without app private-member access or new frontend-only contracts.
  - Blocking: None
- [x] P1: Prove replay-backed persistence/API/WS/frontend flow over a 60-second after-hours validation window.
  - Owner: Codex
  - Definition of Done: History stays non-empty and non-flat, WS ATM timestamps advance, and the TradingView overlay exits `-- PENDING`.
  - Blocking: None
- [x] P2: Sync governance artifacts for the runtime change.
  - Owner: Codex
  - Definition of Done: Relevant SOP docs updated, OpenSpec change chain added, session/context handoff files synchronized, and strict validation passes.
  - Blocking: None

## Parking Lot
- [ ] Consider whether replay mode should expose an explicit cleanup wrapper for today replay-written ATM files and Redis keys after validation.
- [ ] Consider whether after-hours replay cadence should emit more than three unique ATM timestamps per 60-second validation window for denser UI motion.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Reproduced and then fixed the after-hours `NO_DATA` validation path by replaying prior real ATM series data through the standard tracker/history/WS pipeline. (2026-03-24 23:57:50 ET)
