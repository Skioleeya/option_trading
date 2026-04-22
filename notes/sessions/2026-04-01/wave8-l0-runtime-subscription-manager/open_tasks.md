# Open Tasks

## Priority Queue
- [ ] P1: Retire versioned Wave 4-8 generated-extension candidate fallbacks. SUPERSEDED-BY: `2026-04-01/wave9-l0-orchestration-helper-cluster`
  - Owner: Codex
  - Definition of Done: the default `_native_generated/l0_rust.pyd` path is refreshable again and the runtime no longer needs wave-specific probing.
  - Blocking: external process still locks the default generated extension path.
- [ ] P1: Continue `shared/services/l0_runtime/services/*` migration with the next bounded owner cluster. SUPERSEDED-BY: `2026-04-01/wave9-l0-orchestration-helper-cluster`
  - Owner: Codex
  - Definition of Done: one additional services cluster moves to Rust-backed owner semantics without widening beyond L0.
  - Blocking: Wave 8 closure and next cluster choice.
- [ ] P2: Remove residual thin Python subscription facades when all direct consumers have shifted.
  - Owner: Codex
  - Definition of Done: `services/subscription/manager.py` becomes removable or trivially generated.
  - Blocking: later consumer cutovers.

## Parking Lot
- [ ] Evaluate whether metadata TTL cache should remain Python-owned or move to Rust in a later slice.
- [ ] Decide whether `services/orchestration/support.py` or `services/pollers/*` yields the cleaner next bounded cluster.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Wave 8 subscription manager helper cluster completed (2026-04-01 17:05:00 -04:00)
