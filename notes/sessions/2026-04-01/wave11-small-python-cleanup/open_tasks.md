# Open Tasks

## Priority Queue
- [ ] P1: Retire versioned Wave 4-10 generated-extension candidate fallbacks.
  - Owner: Codex
  - Definition of Done: the default `_native_generated/l0_rust.pyd` path is refreshable again and the runtime no longer needs wave-specific probing.
  - Blocking: external process still locks the default generated extension path.
- [ ] P1: Continue deleting sub-100-line thin Python wrappers where Rust already owns the business logic.
  - Owner: Codex
  - Definition of Done: the next bounded slice removes additional wrapper files without reintroducing Python owner logic.
  - Blocking: verify remaining wrapper clusters are still behavior-neutral.
- [ ] P2: Split `shared/services/l0_runtime/services/orchestration/orchestrator.py` before any owner migration there.
  - Owner: Codex
  - Definition of Done: main-loop responsibilities are decomposed into submodules and the file is back under the 400-line ceiling.
  - Blocking: bounded split session not started yet.

## Parking Lot
- [ ] Decide whether `sync/_native_sync_support.py` and `state/_native_state_support.py` should be folded into the centralized facade or kept split for cohesion.
- [ ] Evaluate whether `services/native_support.py` should later split by domain once more wrapper groups are deleted.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Wave 11 small Python cleanup removed five thin wrappers (2026-04-01 17:00:23 -04:00)
