# Open Tasks

## Priority Queue
- [ ] P1: Retire versioned Wave 4/5/6/7 generated-extension candidate fallbacks. SUPERSEDED-BY: `2026-04-01/wave8-l0-runtime-subscription-manager`
  - Owner: Codex
  - Definition of Done: the default `_native_generated/l0_rust.pyd` path is refreshable again and the runtime no longer needs wave-specific probing.
  - Blocking: external process still locks the default generated extension path.
- [ ] P1: Continue `shared/services/l0_runtime/services/*` migration with the next bounded owner cluster. SUPERSEDED-BY: `2026-04-01/wave8-l0-runtime-subscription-manager`
  - Owner: Codex
  - Definition of Done: one additional services cluster moves to Rust-backed owner semantics without widening beyond L0.
  - Blocking: Wave 7 closure and next cluster choice.
- [ ] P2: Remove residual thin Python sync/repair facades when all direct consumers have shifted.
  - Owner: Codex
  - Definition of Done: `sync/support.py` and `repair/price_repair.py` become removable wrappers.
  - Blocking: later consumer cutovers.

## Parking Lot
- [ ] Evaluate whether `iter_batches()` should remain Python-only or move into a later Rust helper slice.
- [ ] Decide whether `iv_baseline_sync.py` or `subscription/manager.py` yields the cleaner next bounded cluster.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Wave 7 sync/repair helper cluster completed (2026-04-01 16:45:00 -04:00)
