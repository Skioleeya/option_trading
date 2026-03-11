# Open Tasks

## Priority Queue
- [ ] P0: SUPERSEDED-BY: 2026-03-11/agents-new-session-pointer-policy
  - Owner: N/A
  - Definition of Done: N/A
  - Blocking: None
- [ ] P1: SUPERSEDED-BY: 2026-03-11/agents-new-session-pointer-policy
  - Owner: N/A
  - Definition of Done: N/A
  - Blocking: None
- [ ] P2: SUPERSEDED-BY: 2026-03-11/agents-new-session-pointer-policy
  - Owner: Codex
  - Definition of Done: Re-run `l2_decision/tests/test_reactor_and_guards.py` in writable temp environment and confirm green.
  - Blocking: Local temp directory permission/chmod (`WinError 5`), reproduced even with redirected `TMP/TEMP`.

## Parking Lot
- [ ] Add explicit regression test to ensure runtime code never references `to_legacy_agent_result` again.
- [ ] Investigate/standardize pytest temp-path permission policy on this machine.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Removed `DecisionOutput.to_legacy_agent_result` and switched compute loop to typed-contract direct path (2026-03-11 ET)
- [x] Updated SOP for Stage2 contract behavior (`docs/SOP/L2_DECISION_ANALYSIS.md`) (2026-03-11 ET)
- [x] Updated `清单.md` P2 item to completed (2026-03-11 ET)
