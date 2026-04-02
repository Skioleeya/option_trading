# Open Tasks

## Priority Queue
- [x] P0: complete Wave 2 for `shared/models/*` plus live L1/L2 consumers.
  - Owner: Codex
  - Definition of Done: Rust-native model spec owner in place, stable consumer imports preserved, targeted regressions green, SOP/OpenSpec/session updated.
  - Blocking: none
- [ ] P1: start Wave 3 for `shared/system/*` / `shared/services/*` plus mapped consumers.
  - Owner: Codex
  - Definition of Done: system/service owner groups migrated or retired through cross-repo wave execution.
  - Blocking: requires a new dedicated implementation session.
- [ ] P2: decide whether `shared/models/_native_models.py` remains as a long-term thin accessor or folds into a generated package later.
  - Owner: Codex
  - Definition of Done: ownership of the helper is documented and either stabilized or retired in later waves.
  - Blocking: depends on Wave 3+ shape.

## Parking Lot
- [ ] Evaluate whether `shared/models/__init__.py` should eventually export `FlowEngine*` once all consumers are fully Rust-native.
- [ ] Revisit whether a dedicated `models` native extension package is preferable after `shared/system/*` and `shared/services/*` are migrated.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Wave 2 model owner cutover completed (2026-04-01 16:05:00 -04:00)
