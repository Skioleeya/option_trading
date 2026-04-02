# Open Tasks

## Priority Queue
- [ ] P1: Start the next bounded `shared/services/l0_runtime` owner cluster after Wave 4 closure.
  - Owner: Codex
  - Definition of Done: Select and execute the next `l0_runtime` cluster outside normalize/projection with the same Rust-backed bounded-cutover pattern and passing gates.
  - Blocking: Wave 4 session closure and context sync.
- [ ] P1: Retire the legacy locked native extension path. SUPERSEDED-BY: `2026-04-01/wave5-l0-runtime-state-cluster`
  - Owner: Codex
  - Definition of Done: The live runtime no longer depends on `shared/services/l0_runtime/_native_generated/l0_rust.pyd`, and versioned artifact loading is no longer needed.
  - Blocking: Identify and stop the process holding the legacy `.pyd` lock, then converge loader strategy safely.
- [ ] P2: Reduce Python wrapper surface in `l0_runtime/normalize/*` after consumer cutover stabilizes.
  - Owner: Codex
  - Definition of Done: Thin facades remain import-compatible but contain no duplicated parse/normalize logic.
  - Blocking: Downstream consumer verification on the new Rust-backed semantics.

## Parking Lot
- [ ] Decide whether to collapse `wave4` extension loading into the default generated path once file-lock ownership is controllable.
- [ ] Revisit `l0_runtime/state/*` as a separate bounded owner slice.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Completed Wave 4 sanitize/events Rust-backed cutover with 30 targeted pytest passes (2026-04-01 15:35:55 -04:00)
