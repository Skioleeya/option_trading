# Open Tasks

## Priority Queue
- [x] P1: complete `refactor-dependency-20260402-services-root-retirement`
  - Owner: Codex
  - Definition of Done: delete `shared_rust/services_root.pyd`, keep `shared_rust.services` imports healthy, and pass strict gate.
- [x] P2: complete `refactor-dependency-20260402-tactical-triad-shared-rust-export`
  - Owner: Codex
  - Definition of Done: add `shared_rust_services/src/tactical.rs`, register tactical exports in `lib.rs`, rebuild service artifact, and pass tactical export smokes.
- [x] P4: complete `impl-20260402-active-options-pure-shim-retirement`
  - Owner: Codex
  - Definition of Done: cut consumers to `shared_rust.services`, remove pure shim files, and clear residual import scan.
- [x] P0: remediate strict gate blockers surfaced in this session
  - Owner: Codex
  - Definition of Done: OpenSpec parent/child gate and debt duplicate gate both pass in strict validation.

## Parking Lot
- [x] Item: none

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] WAVE A parallel execution finished: P1/P2/P4 implemented and strict validation green (2026-04-02 15:27 ET)
