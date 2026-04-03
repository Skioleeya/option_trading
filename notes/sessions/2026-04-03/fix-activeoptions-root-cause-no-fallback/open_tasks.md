# Open Tasks

## Priority Queue
- [x] P0: Restore ActiveOptions live input contract from L1 to runtime service.
  - Owner: Codex
  - Definition of Done: `computed_gamma/computed_vanna/atm_iv` survive into ActiveOptions input snapshot.
  - Blocking: None
- [x] P0: Remove degraded-row tolerance in diagnostics/hotfix gates.
  - Owner: Codex
  - Definition of Done: hotfix verifier and intraday audit fail when degraded rows appear.
  - Blocking: None
- [x] P0: Complete strict validation closure for this session.
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passes for this session.
  - Blocking: None

## Parking Lot
- None

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] ActiveOptions root-cause fixed without fallback path (2026-04-03 ET)
- [x] ActiveOptions runtime/audit diagnostics now enforce strict LIVE-only quality (2026-04-03 ET)
