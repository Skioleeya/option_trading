# Open Tasks

## Priority Queue
- [ ] P1: Remove residual `shared/contracts` references in historical docs and notes where accuracy matters
  - Owner: Codex
  - Definition of Done: Live SOP/OpenSpec records point to `shared_rust.contracts`; stale operational references are cleaned or superseded.
  - Blocking: None.
- [ ] P1: Remove residual `shared.models` references in historical docs and notes where accuracy matters
  - Owner: Codex
  - Definition of Done: Live SOP/OpenSpec records point to `shared_rust.models`; stale operational references are cleaned or superseded.
  - Blocking: None.
- [ ] P2: Decide whether `shared_rust/contracts.pyd` remains checked in or moves to a deterministic build step
  - Owner: Codex
  - Definition of Done: Runtime artifact policy is explicit and aligned with strict validation expectations.
  - Blocking: Depends on broader `shared_rust` rollout strategy.
- [ ] P2: Decide whether `shared_rust/models.pyd` remains checked in or moves to a deterministic build step
  - Owner: Codex
  - Definition of Done: Runtime artifact policy is explicit and aligned with strict validation expectations.
  - Blocking: Depends on broader `shared_rust` rollout strategy.

## Parking Lot
- [ ] SUPERSEDED-BY: 2026-04-01/wave12-shared-rust-foundation
- [ ] SUPERSEDED-BY: 2026-04-01/wave12-shared-rust-foundation

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Replaced `shared.contracts.*` with Rust-only `shared_rust.contracts` and deleted the Python contract package (2026-04-01 18:02:00 -04:00)
- [x] Replaced `shared.models.*` with Rust-only `shared_rust.models` and deleted the Python model package (2026-04-01 17:44:00 -04:00)
