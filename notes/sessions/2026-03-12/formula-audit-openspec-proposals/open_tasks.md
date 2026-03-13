# Open Tasks

## Priority Queue
- [x] P0: Create parent+child OpenSpec proposal set for formula-audit remediation
  - Owner: Codex
  - Definition of Done: One governance parent plus four ordered child proposals exist under `openspec/changes/*`, each with proposal/design/tasks/spec and exact file/field/test scope.
  - Blocking: None
- [ ] P1: Implement `formula-semantic-phase-a-vrp-gex-stopgap`
  - Owner: Codex
  - Definition of Done: `vol_risk_premium` unit and `GEX proxy` semantics are unified in code, SOP, and tests per the child proposal.
  - Blocking: Requires runtime code change session
- [ ] P2: Implement `formula-semantic-phase-b-skew-and-raw-exposure-contracts`
  - Owner: Codex
  - Definition of Done: Canonical `rr25_call_minus_put` and `net_*_raw_sum` contracts land with compatibility aliases and tests.
  - Blocking: Depends on Phase A completion

## Parking Lot
- [ ] Implement `formula-semantic-phase-c-provenance-and-heuristic-labels` after Phase B closes.
- [ ] Implement `formula-semantic-phase-d-research-metric-upgrades` after Phase C closes.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Created formula-semantic governance parent and four ordered child OpenSpec proposals (2026-03-12 14:02 ET)
