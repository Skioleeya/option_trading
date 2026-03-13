# Open Tasks

## Priority Queue
- [ ] P1: Start Phase G (`live canonical contract cutover`) after Phase F completion.
  - Owner: Codex / next implementing agent
  - Definition of Done: Phase G child tasks advanced with updated tests/docs and strict validation evidence.
  - Blocking: Requires dedicated Phase G implementation slice.
- [ ] P2: Keep parent governance closure pending until Phase G/H both complete.
  - Owner: Codex / next implementing agent
  - Definition of Done: parent `tasks.md` closure section reconciled after child chain completion.
  - Blocking: Depends on Phase G/H delivery.

## Parking Lot
- [ ] Evaluate if `guard_vrp_proxy_pct` should be exposed in diagnostics payload for operator debug.
- [ ] Consider adding dedicated unit tests for invalid/non-finite guard inputs in runtime guard path.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Unified `VRPVetoGuard` to `% points` contract with legacy decimal threshold normalization compatibility (2026-03-13 09:43 ET)
- [x] Synced operator/SOP docs to separate `vol_risk_premium` vs `guard_vrp_proxy_pct` semantics (2026-03-13 09:43 ET)
- [x] Passed targeted verification command for Phase F (`63 passed`) (2026-03-13 09:44 ET)
- [x] Passed strict session gate: `scripts/validate_session.ps1 -Strict` (2026-03-13 09:46 ET)
