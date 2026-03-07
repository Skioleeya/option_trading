# Open Tasks

## Priority Queue
- [x] P1: Refactor L2 gamma service to qualitative-only (`GammaQualAnalyzer`) and remove `l1_compute.analysis` coupling.
  - Owner: Codex
  - Definition of Done: `l2_decision/agents/services/*` has no `l1_compute.analysis` import on gamma path; compatibility payload preserved.
  - Blocking: None
- [x] P1: Refactor `l3_assembly/assembly/ui_state_tracker.py` to consume only L1/L2 output contracts.
  - Owner: Codex
  - Definition of Done: no direct import of `l1_compute.trackers/*` or `l1_compute.analysis/*`; existing output schema preserved.
  - Blocking: None
- [x] P1: Add full-repository layer boundary CI gate and extend policy coverage for assembly/services paths.
  - Owner: Codex
  - Definition of Done: CI workflow executes full-repo boundary scan script and policy catches P1 target paths.
  - Blocking: None

## Parking Lot
- [x] None

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] P1 gamma ownership boundary hardening + full-repo import gate (2026-03-06 21:51 ET)
