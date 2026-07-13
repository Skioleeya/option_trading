# Open Tasks

## Priority Queue
- [x] P0: Stop AtmDecayChart from connecting pre-reset ATM history to the current locked anchor segment.
  - Owner: Codex
  - Definition of Done: Chart hydrate consumes anchor identity fields; series generation trims to latest anchor segment; targeted tests/build/start-all pass.
  - Blocking: None
- No open P1/P2 tasks for this session.

## Parking Lot
- None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Diagnosed 12:31:32 -> 12:31:47 history discontinuity: PUT ~+230% to ~-1%, CALL ~-95% to 0%, `strike_changed=false`, matching the frontend vertical line. (2026-07-13 12:48 ET)
- [x] Updated L4 chart history consumption to retain only latest `locked_at + base_strike/strike` anchor segment before building series. (2026-07-13 12:48 ET)
- [x] Removed template placeholder unchecked tasks so debt validation reflects actual session state. (2026-07-13 12:52 ET)
- [x] Corrected over-trimming regression: chart now preserves full-day history and inserts whitespace gaps at anchor boundaries. (2026-07-13 13:32 ET)
