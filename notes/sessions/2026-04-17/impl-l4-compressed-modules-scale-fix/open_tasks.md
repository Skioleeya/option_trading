# Open Tasks

## Priority Queue
- [x] P0: Rebalance compact-profile scaling without changing `WallMigration` or `ActiveOptions` canonical structures.
  - Owner: Codex
  - Definition of Done: left/right rail tokens and module spacing remove visible squeeze while `WallMigration` remains two-row horizontal and `ActiveOptions` keeps the standard table header order.
  - Blocking: None.
- [x] P1: Remove right offensive-area horizontal status bars.
  - Owner: Codex
  - Definition of Done: `DecisionEngine` and `MtfFlow` expose state via text/badge/dot only; no horizontal progress strips remain.
  - Blocking: None.
- [x] P2: Capture strict validation evidence and sync context indexes.
  - Owner: Codex
  - Definition of Done: `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passes and the exact result is recorded in session/context handoff.
  - Blocking: None.

## Parking Lot
- [ ] Live-browser smoke check on the exact main/secondary monitor windows.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Compact-profile rail/token rebalance landed (2026-04-17 16:08 ET)
- [x] Horizontal status bars removed from `DecisionEngine` / `MtfFlow` (2026-04-17 16:08 ET)
- [x] Frontend tests passed (`40` files, `195` tests) (2026-04-17 16:09 ET)
- [x] Strict validation passed and context sync prepared (2026-04-17 16:17 ET)
