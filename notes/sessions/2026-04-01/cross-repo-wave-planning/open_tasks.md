# Open Tasks

## Priority Queue
- [ ] P0: start Wave 1 execution for `shared/contracts/*` plus all live consumers
  - Owner: Codex
  - Definition of Done:
    - contract owner table is frozen
    - consumer rewrite set is explicit
    - implementation session excludes models/system/services
  - Blocking: planning-only slice must remain code-free
- [ ] P1: prepare Wave 2 execution backlog for `shared/models/*` plus all live consumers
  - Owner: Codex
  - Definition of Done:
    - model owner table and consumer list are extracted from the approved plan
  - Blocking: Wave 1 must define the reusable execution template
- [ ] P2: partition Wave 3 into executable owner clusters before any runtime work begins
  - Owner: Codex
  - Definition of Done:
    - `shared/system/*` and `shared/services/*` are broken into smaller migration clusters with mapped consumer sets
  - Blocking: none

## Parking Lot
- [ ] decide whether Wave 1 should introduce a dedicated Rust contract crate or a narrower Rust-backed export surface first
- [ ] decide whether `metric_semantics.py` should move via generated artifact or direct native owner surface

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Formalized the three-wave cross-repo migration plan and aligned it with measured consumer evidence (2026-04-01 14:50 ET)
