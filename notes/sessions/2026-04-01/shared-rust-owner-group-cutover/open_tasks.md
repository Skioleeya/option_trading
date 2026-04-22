# Open Tasks

## Priority Queue
- [ ] P0: create a cross-repo owner-group migration wave for the remaining `shared/*` Rust cutover
  - Owner: Codex
  - Definition of Done:
    - migration scope explicitly includes `shared/*` plus all live consumers in `l1_compute/`, `l2_decision/`, `l3_assembly/`, `app/`, tests, and SOPs
  - Blocking: cannot be completed as a `shared`-only slice
- [ ] P1: classify remaining `shared/contracts/*`, `shared/models/*`, `shared/system/*`, and `shared/services/*` by consumer set and cutover order
  - Owner: Codex
  - Definition of Done:
    - each owner group is mapped to downstream consumers and required consumer rewrite files
  - Blocking: none

## Parking Lot
- [ ] normalize historical notes/archive references to removed cloud-ref paths in a later documentation cleanup wave
- [ ] decide whether the first cross-repo migration wave should start from `shared/contracts/*` or `shared/system/*`

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Proved with measured import evidence that the remaining `shared/*` Python owners cannot be truthfully completed as a `shared`-only Rust cutover slice (2026-04-01 14:40 ET)
