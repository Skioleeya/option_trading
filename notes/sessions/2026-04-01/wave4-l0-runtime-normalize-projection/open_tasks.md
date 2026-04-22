# Open Tasks

## Priority Queue
- [x] P0: cut over the bounded `shared/services/l0_runtime` normalize-bridge and projection-snapshot helper cluster.
  - Owner: Codex
  - Definition of Done: Rust native helper owners replace Python-local market-event bridge and snapshot projection semantics behind stable Python import surfaces, targeted regressions are green, SOP/OpenSpec/session updated.
  - Blocking: none
- [ ] P1: cut over the remaining `shared/services/l0_runtime` normalize stateful helper cluster (`sanitization.py` + `normalize/events/*`).
  - Owner: Codex
  - Definition of Done: stateful parse/application semantics move behind Rust-backed or otherwise bounded owners without breaking L0 source-time, event ordering, or OI/spot update rules.
  - Blocking: requires bounded decomposition so parser logic does not drag in `source/runtime` or `state/*` owners.
- [ ] P1: select the next bounded `shared/services/l0_runtime` owner cluster after normalize/projection helper completion.
  - Owner: Codex
  - Definition of Done: next slice is explicitly chosen and documented as one of `services/*`, `source/runtime/*`, or `state/*` with mapped consumers/tests.
  - Blocking: depends on whether the parser/events slice is taken next or deferred.

## Parking Lot
- [ ] Decide whether `rust_event_bridge.py` compatibility alias should be retired after direct import convergence.
- [ ] Decide whether L0 helper exports should eventually split from the L0 ingest extension into a dedicated native package.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Wave 4 normalize-bridge and projection-snapshot helper cluster completed (2026-04-01 15:17:08 -04:00)
