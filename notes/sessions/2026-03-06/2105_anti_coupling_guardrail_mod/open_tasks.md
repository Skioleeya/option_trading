# Open Tasks

## Priority Queue
- [x] P0: Add anti-coupling hard constraints in `AGENTS.md` and require strict validation enforcement path.
  - Owner: Codex
  - Definition of Done: AGENTS includes explicit forbidden dependency and private-member rules + strict validation contract.
  - Blocking: None
- [x] P1: Sync relevant SOP docs with layer boundary contract.
  - Owner: Codex
  - Definition of Done: `SYSTEM_OVERVIEW`, `L2_DECISION_ANALYSIS`, `L3_OUTPUT_ASSEMBLY` updated with anti-coupling clauses.
  - Blocking: None
- [x] P1: Modularize boundary policy into standalone config file.
  - Owner: Codex
  - Definition of Done: `scripts/policy/layer_boundary_rules.json` created and consumed by validator.
  - Blocking: None
- [x] P2: Integrate policy-driven boundary scan into `scripts/validate_session.ps1`.
  - Owner: Codex
  - Definition of Done: strict mode checks runtime `files_changed`, reports `file:line`, and fails on hit.
  - Blocking: None
- [x] P2: Validate current session with strict gate and update handoff/meta evidence.
  - Owner: Codex
  - Definition of Done: strict validation command recorded in session metadata with pass result.
  - Blocking: None

## Parking Lot
- [x] None

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Anti-coupling guardrails hardened across AGENTS + SOP + strict validator (2026-03-06 20:53 ET)
