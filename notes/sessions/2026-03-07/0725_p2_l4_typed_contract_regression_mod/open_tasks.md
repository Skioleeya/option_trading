# Open Tasks

## Priority Queue
- [x] P2: Tighten L4 right-panel typed contracts (`tactical_triad/skew_dynamics/mtf_flow/active_options`).
  - Owner: Codex
  - Definition of Done: `dashboard.ts` right-panel `ui_state` fields use explicit interfaces and component render path no longer uses `as any`.
  - Blocking: None
- [x] P2: Add cross-layer contract regression tests (L1/L2 -> L3 payload -> L4 render model consistency).
  - Owner: Codex
  - Definition of Done: Python reactor regression + L4 integration regression tests pass under required test entrypoints.
  - Blocking: None
- [ ] P2: Remove legacy shim (`DecisionOutput.to_legacy_agent_result`) and switch to typed-contract direct path (Stage2).
  - Owner: Codex
  - Definition of Done: Compute loop/L3 consumption path no longer depends on shim and Stage2 tests pass.
  - Blocking: Requires dedicated Stage2 change set to minimize runtime regression risk.

## Parking Lot
- [x] None

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] P2 Stage1 typed-contract hardening + cross-layer regression coverage (2026-03-07 08:04 ET)
