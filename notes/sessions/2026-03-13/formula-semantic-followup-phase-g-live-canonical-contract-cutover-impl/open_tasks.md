# Open Tasks

## Priority Queue
- [ ] P1: Start Phase H (`openspec reconciliation`) after Phase G completion.
  - Owner: Codex / next implementing agent
  - Definition of Done: Phase H tasks completed with parent/child governance reconciliation and strict validation evidence.
  - Blocking: Depends on dedicated Phase H implementation slice.
- [ ] P2: Parent governance final closure after Phase H completion.
  - Owner: Codex / next implementing agent
  - Definition of Done: parent `formula-semantic-followup-parent-governance/tasks.md` closure section complete.
  - Blocking: Depends on Phase H outputs.

## Parking Lot
- [ ] Evaluate whether to expose canonical source provenance diagnostics (`rr25_call_minus_put`, `net_charm_raw_sum`) in debug payload metadata.
- [ ] Consider adding a non-blocking warning path when `skew_25d_valid=1` but canonical RR25 field is absent.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Switched L3 live skew mapping to canonical `rr25_call_minus_put` with `skew_25d_valid` gate (2026-03-13 09:58 ET)
- [x] Switched L3 tactical charm live mapping to canonical `net_charm_raw_sum` (2026-03-13 09:58 ET)
- [x] Updated L3/L4 regression tests for canonical cutover while preserving UI contract shape (2026-03-13 09:59 ET)
- [x] Updated `docs/SOP/L3_OUTPUT_ASSEMBLY.md` with canonical live-source rules (2026-03-13 09:59 ET)
- [x] Passed strict session gate: `scripts/validate_session.ps1 -Strict` (2026-03-13 10:01 ET)
