# Open Tasks

## Priority Queue
- [ ] P1: start Wave 2 for `shared/models/*` plus all live consumers
  - Owner: Codex
  - Definition of Done:
    - `shared/models/*` source-of-truth moves behind a Rust-backed surface and L1/L2 consumer imports are green
  - Blocking: Wave 1 session must stay closed and validated first
- [ ] P2: partition Wave 3 `shared/system/*` and `shared/services/*` into executable owner clusters before implementation
  - Owner: Codex
  - Definition of Done:
    - system and services owner groups each have bounded consumer sets and test gates
  - Blocking: none

## Parking Lot
- [ ] decide whether `shared/contracts/_native_contracts.py` should remain as a stable thin wrapper or be folded into a future generated contract package
- [ ] evaluate whether `shared/contracts/__init__.py` can be further reduced once more consumers move to direct Rust-backed imports

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Completed Wave 1 contract ownership cutover: `shared/contracts/*` now consume Rust native exports and all measured Wave 1 regressions are green (2026-04-01 15:10 ET)
