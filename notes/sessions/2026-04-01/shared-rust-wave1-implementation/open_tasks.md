# Open Tasks

## Priority Queue
- [ ] P1: start the first true Rust owner-group replacement inside `shared/contracts/*` or `shared/models/*`
  - Owner: Codex
  - Definition of Done:
    - one active contract/model owner has a Rust single-source replacement plan and an executable Python retirement path
  - Blocking: must avoid introducing dual-owner Python/Rust logic
- [ ] P1: classify remaining `shared/models/*` leaves into `delete` vs `Rust-first`
  - Owner: Codex
  - Definition of Done:
    - each remaining model file is labeled as active owner, compatibility shim, or dead leaf
  - Blocking: requires the same import/export/dynamic-loader proof used in Wave 0
- [ ] P2: classify `shared/cache/oi_snapshot.py` as runtime owner vs later Rust replacement leaf
  - Owner: Codex
  - Definition of Done:
    - dependency classification is recorded in the next audit slice
  - Blocking: none

## Parking Lot
- [ ] decide whether archived notes/spec references to removed cloud-ref paths should be normalized in a later documentation cleanup wave
- [ ] evaluate whether `shared/contracts/metric_semantics.py` should be migrated via generated artifact or direct native binding

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Deleted the last dead `shared/config_cloud_ref` Python files and the zero-hit `shared/models/active_option.py` after live reference scans passed (2026-04-01 14:15 ET)
