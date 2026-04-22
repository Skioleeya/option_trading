# Open Tasks

## Priority Queue
- [x] P0: Restore readable `WallMigration` strike cells in compact width.
  - Owner: Codex
  - Definition of Done: `h1/h2/current` strike cells are all readable in the live browser layout without changing the two-row module structure.
  - Blocking: None.
- [x] P1: Verify the fix in a real browser, not just tests.
  - Owner: Codex
  - Definition of Done: browser-side inspection on `localhost:5173` confirms the rendered `WallMigration` rows show full compact strike labels.
  - Blocking: None.
- [x] P2: Record strict validation evidence and sync context indexes.
  - Owner: Codex
  - Definition of Done: `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passes and the evidence is recorded in session/context handoff.
  - Blocking: None.

## Parking Lot
- [ ] If future wall ladders emit half-point strikes, define whether `WallMigration` should round, floor, or display one decimal.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Equal-width `WallMigration` tracks landed for `h1/h2/current` (2026-04-17 16:41 ET)
- [x] Integer-only `WallMigration` strike formatter landed (2026-04-17 16:35 ET)
- [x] Frontend tests passed (`41` files, `197` tests) (2026-04-17 16:44 ET)
- [x] Browser-side mock payload verification passed on `localhost:5173` with equal strike widths (`45.66px | 45.67px | 45.67px`) (2026-04-17 16:46 ET)
- [x] Strict validation passed (2026-04-17 16:47 ET)
