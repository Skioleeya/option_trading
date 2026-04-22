# Open Tasks

## Priority Queue
- [ ] P1: Start the next bounded `l0_runtime/services/*` cluster. SUPERSEDED-BY: `2026-04-01/wave8-l0-runtime-subscription-manager`
  - Owner: Codex
  - Definition of Done: Select a single `services/*` subcluster and move its pure helper/merge semantics into Rust-backed helpers with passing gates.
  - Blocking: Close the current state-cluster session.
- [ ] P1: Retire the legacy locked native extension path. SUPERSEDED-BY: `2026-04-01/wave8-l0-runtime-subscription-manager`
  - Owner: Codex
  - Definition of Done: The live runtime no longer needs the versioned `wave4/wave5` artifact fallback to avoid the locked default `.pyd`.
  - Blocking: External process lock ownership must be resolved safely.
- [ ] P2: Reduce Python API shell depth in `ChainStateStore` once downstream owner clusters are cut over.
  - Owner: Codex
  - Definition of Done: Remaining Python code only manages object API and diagnostics without duplicate merge branches.
  - Blocking: Additional `l0_runtime` owner clusters still depend on the current store API.

## Parking Lot
- [ ] Revisit `live_state.py` only after more of `l0_runtime/services/*` is native-backed.
- [ ] Collapse versioned native artifact loading into the default generated path once file-lock ownership is controlled.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Cut over `ChainStateStore` merge semantics to Rust-backed helpers with direct store regressions passing (2026-04-01 15:52:00 -04:00)
