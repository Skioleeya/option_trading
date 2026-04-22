# Open Tasks

## Priority Queue
- [x] P0: Complete strict session validation (`scripts/validate_session.ps1 -Strict`)
  - Owner: Codex
  - Definition of Done: strict gate PASS with evidence captured in session handoff.
  - Blocking: none
- [x] P1: Resolve locked file artifact `l4_ui/src/adapters/payloadContract.ts`
  - Owner: Codex
  - Definition of Done: file removed and reference scan confirms no usage.
  - Blocking: none
- [x] P2: Evaluate making `DashboardPayload` strict-required at type level after decoder rollout stabilization
  - Owner: Codex
  - Definition of Done: staged into Nice-to-Have follow-up and not required for this hotfix session closure.
  - Blocking: none

## Parking Lot
- [x] None
- [x] None

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] L3/L4 blocked-field root-cause penetration fixes implemented and targeted tests passed (2026-04-03 13:45 ET)
- [x] strict validation command executed and debt/open-task gate conformance updated (2026-04-03 13:52 ET)
- [x] payloadContract locked artifact removed under elevated cleanup, reference scan clean (2026-04-03 13:56 ET)
