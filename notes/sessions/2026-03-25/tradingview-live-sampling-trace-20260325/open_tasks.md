# Open Tasks

## Priority Queue
- [x] P0: Trace the frontend TradingView ATM decay chart data path from hydration through websocket updates to incremental series rendering.
  - Owner: Codex
  - Definition of Done: Confirm whether call/put/straddle values receive continuous new timestamps and whether the chart uses incremental append or full reset semantics.
  - Blocking: None
- [x] P1: Capture live browser evidence for overlay/chart behavior and direct websocket evidence for ATM payload continuity.
  - Owner: Codex
  - Definition of Done: Browser observation, direct websocket sampling, and backend history inspection agree on the live state.
  - Blocking: None
- [x] P2: Record investigation results and sync session/context files.
  - Owner: Codex
  - Definition of Done: Session/context files summarize root findings and strict validation passes.
  - Blocking: None

## Parking Lot
- [ ] Repair ATM decay history timestamp correctness and ordering so live points no longer land behind persisted future rows.
- [ ] Repair backend ATM live payload continuity so `dashboard_delta/dashboard_update` keep advancing `atm.timestamp` during market hours.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Traced frontend normalization and incremental update code paths. (2026-03-25 09:49:20 ET)
- [x] Ran headless browser observation and direct websocket sampling. (2026-03-25 09:55:20 ET)
- [x] Confirmed persisted ATM history contains out-of-order future timestamps. (2026-03-25 09:56:40 ET)
