# Open Tasks

## Priority Queue
- [ ] P1: Retire versioned Wave 4/5/6 generated-extension candidate fallbacks. SUPERSEDED-BY: `2026-04-01/wave8-l0-runtime-subscription-manager`
  - Owner: Codex
  - Definition of Done: `shared/services/l0_runtime/_native_generated/l0_rust.pyd` becomes refreshable again and the loader no longer needs wave-specific artifact probing.
  - Blocking: External process still locks the legacy default generated extension path.
- [ ] P1: Continue `shared/services/l0_runtime/services/*` owner migration. SUPERSEDED-BY: `2026-04-01/wave8-l0-runtime-subscription-manager`
  - Owner: Codex
  - Definition of Done: sync/subscription/orchestration helpers move to Rust-backed owners without widening into non-L0 scopes.
  - Blocking: Wave 6 closure and next bounded cluster selection.
- [ ] P2: Delete residual Python facades once all live consumers are cut over.
  - Owner: Codex
  - Definition of Done: `sdk_bootstrap.py`, `longport_option_contracts.py`, and `quote_runtime` facades become removable without breaking imports.
  - Blocking: Additional consumer migration waves.

## Parking Lot
- [ ] Measure whether quote REST JSON decoding can be removed entirely from the remaining Python facades.
- [ ] Evaluate whether Wave 6 native row exports should move from JSON-shaped Python dicts to typed Rust/PyO3 objects in a later slice.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Wave 6 quote API Rust cutover completed (2026-04-01 16:25:00 -04:00)
