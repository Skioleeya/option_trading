# Open Tasks

## Priority Queue
- [ ] P1: Decide whether to open an archive session for parent governance final bookkeeping.
  - Owner: Codex / next implementing agent
  - Definition of Done: archive action plan documented and executed if required.
  - Blocking: depends on team release/governance cadence.
- [ ] P2: Continue long-horizon backlog item `wall_collapse_flow_intensity_threshold` calibration.
  - Owner: Codex / next implementing agent
  - Definition of Done: threshold calibrated with historical/live samples and documented.
  - Blocking: depends on dedicated data calibration session.

## Parking Lot
- [ ] Evaluate if OpenSpec historical phases should adopt a standard `HISTORICAL-HANDOFF` metadata field template.
- [ ] Add CI lint rule preventing old/new proposals from simultaneously claiming active residual ownership.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Backfilled old Phase A/B/D tasks to completed states with explicit evidence references (2026-03-13 10:14 ET)
- [x] Marked old Phase C unfinished scope as handed off to follow-up Phase E (2026-03-13 10:14 ET)
- [x] Reconciled old/new parent governance docs to a single active residual owner (2026-03-13 10:15 ET)
- [x] `openspec list` reconciliation audit passed with Phase H complete (2026-03-13 10:18 ET)
- [x] Passed strict session gate: `scripts/validate_session.ps1 -Strict` (2026-03-13 10:16 ET)
